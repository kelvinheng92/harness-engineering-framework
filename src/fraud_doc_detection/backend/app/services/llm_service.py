"""
Unified LLM service supporting Groq, OpenRouter, and Gemini.
All providers expose the same three functions:
  - classify_document(pdf_path) -> dict
  - extract_key_values(pdf_path, doc_type) -> dict
  - answer_question(pdf_path, question, history) -> str
"""
import base64
import io
import json
import re
from typing import Any

import fitz  # PyMuPDF
import PIL.Image

from app.core.config import settings


# ─── PDF helpers ─────────────────────────────────────────────────────────────

def _extract_text(pdf_path: str, max_chars: int = 20000) -> str:
    doc = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text() for page in doc).strip()[:max_chars]
    finally:
        doc.close()


def _pdf_to_b64_images(pdf_path: str, max_pages: int = 8, scale: float = 1.5) -> list[str]:
    """Return list of base64-encoded PNG strings (one per page)."""
    doc = fitz.open(pdf_path)
    images: list[str] = []
    mat = fitz.Matrix(scale, scale)
    try:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=mat)
            images.append(base64.b64encode(pix.tobytes("png")).decode())
    finally:
        doc.close()
    return images


def _pdf_to_pil_images(pdf_path: str, max_pages: int = 8, scale: float = 1.5) -> list[PIL.Image.Image]:
    doc = fitz.open(pdf_path)
    images: list[PIL.Image.Image] = []
    mat = fitz.Matrix(scale, scale)
    try:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=mat)
            img = PIL.Image.open(io.BytesIO(pix.tobytes("png")))
            img.load()
            images.append(img)
    finally:
        doc.close()
    return images


def _parse_json(raw: str) -> Any:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


def _quota_error(exc: Exception) -> RuntimeError:
    msg = str(exc).lower()
    if "quota" in msg or "rate" in msg or "429" in msg or "resource_exhausted" in msg:
        return RuntimeError(
            "Free tier quota or rate limit exceeded. Wait a minute and retry, "
            "or switch providers in Settings."
        )
    return RuntimeError(str(exc))


# ─── OpenAI-compatible providers (Groq + OpenRouter) ─────────────────────────

_GROQ_BASE = "https://api.groq.com/openai/v1"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# Model selection per provider
_TEXT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "meta-llama/llama-4-maverick:free",
}
_VISION_MODELS = {
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",   # Groq's Llama 4 with vision
    "openrouter": "meta-llama/llama-4-maverick:free",       # Llama 4 Maverick vision
}


def _openai_client(provider: str):
    from openai import OpenAI
    base = _GROQ_BASE if provider == "groq" else _OPENROUTER_BASE
    extra = {"default_headers": {"HTTP-Referer": "http://localhost:5173"}} if provider == "openrouter" else {}
    return OpenAI(api_key=settings.active_key(), base_url=base, **extra)


def _call_openai_text(provider: str, prompt: str, pdf_path: str) -> str:
    """Text-only call via OpenAI-compatible API."""
    from openai import RateLimitError, APIStatusError
    client = _openai_client(provider)
    text = _extract_text(pdf_path)
    try:
        resp = client.chat.completions.create(
            model=_TEXT_MODELS[provider],
            messages=[{"role": "user", "content": f"Document:\n{text}\n\n{prompt}"}],
            temperature=0,
        )
        return resp.choices[0].message.content or ""
    except (RateLimitError, APIStatusError) as exc:
        raise _quota_error(exc) from exc
    except Exception as exc:
        raise _quota_error(exc) from exc


def _call_openai_vision(provider: str, prompt: str, pdf_path: str, max_pages: int = 8) -> str:
    """Vision call via OpenAI-compatible API (sends page images + text)."""
    from openai import RateLimitError, APIStatusError
    client = _openai_client(provider)
    b64_images = _pdf_to_b64_images(pdf_path, max_pages=max_pages)
    text = _extract_text(pdf_path)

    content: list[dict] = []
    for b64 in b64_images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
    content.append({"type": "text", "text": f"Extracted text:\n{text}\n\n{prompt}"})

    try:
        resp = client.chat.completions.create(
            model=_VISION_MODELS[provider],
            messages=[{"role": "user", "content": content}],
            temperature=0,
        )
        return resp.choices[0].message.content or ""
    except (RateLimitError, APIStatusError) as exc:
        raise _quota_error(exc) from exc
    except Exception as exc:
        # Vision might not be supported — fall back to text-only
        return _call_openai_text(provider, prompt, pdf_path)


def _call_openai_chat(
    provider: str,
    prompt: str,
    pdf_path: str,
    history: list[dict[str, str]],
) -> str:
    """Multi-turn chat via OpenAI-compatible API."""
    from openai import RateLimitError, APIStatusError
    client = _openai_client(provider)
    text = _extract_text(pdf_path)

    messages: list[dict] = [
        {"role": "system", "content": f"Document content:\n{text}"},
    ]
    for msg in history[-6:]:  # last 3 exchanges
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = client.chat.completions.create(
            model=_TEXT_MODELS[provider],
            messages=messages,
            temperature=0,
        )
        return resp.choices[0].message.content or ""
    except (RateLimitError, APIStatusError) as exc:
        raise _quota_error(exc) from exc
    except Exception as exc:
        raise _quota_error(exc) from exc


# ─── Gemini provider ─────────────────────────────────────────────────────────

def _call_gemini_text(prompt: str, pdf_path: str) -> str:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted
    genai.configure(api_key=settings.gemini_api_key)
    text = _extract_text(pdf_path)
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        resp = model.generate_content(f"Document:\n{text}\n\n{prompt}")
        return resp.text
    except ResourceExhausted as exc:
        raise _quota_error(exc) from exc
    except Exception as exc:
        raise _quota_error(exc) from exc


def _call_gemini_vision(prompt: str, pdf_path: str, max_pages: int = 8) -> str:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted
    genai.configure(api_key=settings.gemini_api_key)
    pil_images = _pdf_to_pil_images(pdf_path, max_pages=max_pages)
    text = _extract_text(pdf_path)
    model = genai.GenerativeModel("gemini-2.0-flash")
    parts: list[Any] = pil_images + [f"Extracted text:\n{text}\n\n{prompt}"]
    try:
        resp = model.generate_content(parts)
        return resp.text
    except ResourceExhausted as exc:
        raise _quota_error(exc) from exc
    except Exception as exc:
        raise _quota_error(exc) from exc


def _call_gemini_chat(prompt: str, pdf_path: str, history: list[dict[str, str]]) -> str:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted
    genai.configure(api_key=settings.gemini_api_key)
    text = _extract_text(pdf_path)
    history_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in history[-6:]
    )
    full_prompt = f"Document:\n{text}\n\n{history_text}\n\nUser: {prompt}"
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        resp = model.generate_content(full_prompt)
        return resp.text
    except ResourceExhausted as exc:
        raise _quota_error(exc) from exc
    except Exception as exc:
        raise _quota_error(exc) from exc


# ─── Prompts ──────────────────────────────────────────────────────────────────

_CLASSIFY_PROMPT = """Analyse this document and classify it into one of these financial document types.

Return ONLY a JSON object (no markdown, no extra text):
{
  "document_type": "<type>",
  "confidence": <float 0-1>,
  "reason": "<one sentence>"
}

Types:
- "bank_statement": issued by a bank; shows account transactions, deposits, withdrawals, balances.
- "annual_report": company annual report with audited financials, P&L, balance sheet, director's report.
- "income_tax": tax return, notice of assessment, IR8A, Form B, IRS 1040, W-2, or any government tax document showing income and tax payable.
- "payslip": employee payslip / salary slip showing gross pay, deductions, net pay for a pay period.
- "cpf_statement": CPF (Central Provident Fund) or similar provident fund contribution statement.
- "investment_statement": brokerage account, portfolio, mutual fund, or securities statement.
- "credit_report": credit bureau report showing credit score, loan history, outstanding debts.
- "financial_statement": standalone company financial statement (P&L, balance sheet, cash flow) not part of a full annual report.
- "other": any other document not listed above."""

_KV_PROMPT = """Extract every key-value pair from this document.

Return ONLY this JSON (no markdown, no extra text):
{"pairs": [{"key": "field name", "value": "field value", "category": "section name"}]}

Rules:
- Include ALL fields: names, dates, amounts, IDs, balances, totals, rates, addresses, reference numbers.
- Mask sensitive IDs: show only last 4 characters (e.g. account numbers, NRIC, tax ref).
- Group related fields under a short category name (e.g. "Account Info", "Balances", "Tax").
- Values must be plain strings — no nested objects."""

_QA_SYSTEM = """You are a document analysis assistant. Answer the user's question using only information from the document. If the answer is not in the document, say so clearly. Be concise and factual."""


# ─── Public API ──────────────────────────────────────────────────────────────

def classify_document(pdf_path: str) -> dict[str, Any]:
    provider = settings.llm_provider
    if provider == "gemini":
        raw = _call_gemini_text(_CLASSIFY_PROMPT, pdf_path)
    else:
        raw = _call_openai_text(provider, _CLASSIFY_PROMPT, pdf_path)
    return _parse_json(raw)


def extract_key_values(pdf_path: str, doc_type: str) -> dict[str, Any]:
    prompt = _KV_PROMPT
    provider = settings.llm_provider
    if provider == "gemini":
        raw = _call_gemini_vision(prompt, pdf_path)
    else:
        # Try vision first, falls back to text automatically on failure
        raw = _call_openai_vision(provider, prompt, pdf_path)
    return _parse_json(raw)


def answer_question(pdf_path: str, question: str, history: list[dict[str, str]]) -> str:
    prompt = f"{_QA_SYSTEM}\n\nQuestion: {question}"
    provider = settings.llm_provider
    if provider == "gemini":
        return _call_gemini_chat(prompt, pdf_path, history)
    else:
        return _call_openai_chat(provider, prompt, pdf_path, history)
