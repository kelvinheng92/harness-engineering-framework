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
    """Parse JSON from LLM response, tolerating markdown fences and surrounding prose."""
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"```", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # LLM may have wrapped JSON in prose — find the first {...} or [...] block
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            return json.loads(match.group(1))
        raise RuntimeError(
            f"LLM returned a non-JSON response. Raw output:\n{raw[:500]}"
        )


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
_QWEN_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# Model selection per provider
_TEXT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "meta-llama/llama-4-maverick:free",
    "qwen": "qwen3.6-flash-2026-04-16",
}
_VISION_MODELS = {
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
    "openrouter": "meta-llama/llama-4-maverick:free",
    "qwen": "qwen3.6-flash-2026-04-16",
}


def _openai_client(provider: str):
    from openai import OpenAI
    bases = {
        "groq": _GROQ_BASE,
        "openrouter": _OPENROUTER_BASE,
        "qwen": _QWEN_BASE,
    }
    base = bases.get(provider, _GROQ_BASE)
    extra = {"default_headers": {"HTTP-Referer": "http://localhost:5173"}} if provider == "openrouter" else {}
    return OpenAI(api_key=settings.active_key(), base_url=base, **extra)


def _qwen_extra() -> dict:
    """Extra body params for Qwen — disables built-in chain-of-thought thinking."""
    return {"extra_body": {"enable_thinking": False}}


def _call_openai_text(
    provider: str,
    prompt: str,
    pdf_path: str,
    text: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Text-only call via OpenAI-compatible API.

    Pass ``text`` to reuse already-extracted content and avoid a second PDF read.
    """
    from openai import RateLimitError, APIStatusError
    client = _openai_client(provider)
    if text is None:
        text = _extract_text(pdf_path)
    extra = _qwen_extra() if provider == "qwen" else {}
    try:
        resp = client.chat.completions.create(
            model=_TEXT_MODELS[provider],
            messages=[{"role": "user", "content": f"Document:\n{text}\n\n{prompt}"}],
            temperature=0,
            max_tokens=max_tokens,
            **extra,
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
    b64_images = _pdf_to_b64_images(pdf_path, max_pages=max_pages, scale=1.0)
    text = _extract_text(pdf_path)
    extra = _qwen_extra() if provider == "qwen" else {}

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
            **extra,
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
    text = _extract_text(pdf_path, max_chars=8_000)

    messages: list[dict] = [
        {"role": "system", "content": f"Document content:\n{text}"},
    ]
    for msg in history[-6:]:  # last 3 exchanges
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    extra = _qwen_extra() if provider == "qwen" else {}
    try:
        resp = client.chat.completions.create(
            model=_TEXT_MODELS[provider],
            messages=messages,
            temperature=0,
            max_tokens=1_024,
            **extra,
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
- Values must be plain strings — no nested objects.
- EXCLUDE footer text, page numbers, legal disclaimers, and boilerplate — do NOT create a "Footer" category.
- Do NOT extract individual transaction rows."""

_QA_SYSTEM = """You are a document analysis assistant. Answer the user's question using only information from the document. If the answer is not in the document, say so clearly. Be concise and factual."""


# ─── Public API ──────────────────────────────────────────────────────────────

def classify_document(pdf_path: str) -> dict[str, Any]:
    provider = settings.llm_provider
    if provider == "gemini":
        raw = _call_gemini_text(_CLASSIFY_PROMPT, pdf_path)
    else:
        # Classification only needs a short JSON blob — cap context and output.
        text = _extract_text(pdf_path, max_chars=4_000)
        raw = _call_openai_text(provider, _CLASSIFY_PROMPT, pdf_path, text=text, max_tokens=128)
    return _parse_json(raw)


_KV_TARGETED_PROMPT = """Extract ONLY these fields from the document: {keys}

Return ONLY this JSON — no markdown, no extra text, nothing else:
{{"pairs": [{{"key": "<field name from the list above>", "value": "<value found>", "category": "Extracted Fields"}}]}}

Rules (strictly enforced):
- Include ONLY the fields listed. Any other field is forbidden.
- Do NOT include transactions, summaries, headers, footers, or any unrequested data.
- If a field is not found, omit it — do not guess or substitute.
- Values must be plain strings."""


def extract_key_values(pdf_path: str, doc_type: str, additional_keys: "list[str] | None" = None) -> dict[str, Any]:
    is_targeted = bool(additional_keys)
    if is_targeted:
        keys_str = ", ".join(f'"{k}"' for k in additional_keys)  # type: ignore[arg-type]
        prompt = _KV_TARGETED_PROMPT.format(keys=keys_str)
        # Targeted fields (balances, dates, names) are almost always in the
        # document header — 6 000 chars is plenty and halves inference time.
        text_limit = 6_000
        max_tokens = 512
    else:
        prompt = _KV_PROMPT
        text_limit = 12_000
        max_tokens = 4_096

    provider = settings.llm_provider
    if provider == "gemini":
        raw = _call_gemini_vision(prompt, pdf_path)
    else:
        # Extract text once — reuse for both the length check and the LLM call.
        # Fall back to vision only for image-only PDFs (little extractable text).
        text = _extract_text(pdf_path, max_chars=text_limit)
        if len(text.strip()) >= 100:
            raw = _call_openai_text(provider, prompt, pdf_path, text=text, max_tokens=max_tokens)
        else:
            raw = _call_openai_vision(provider, prompt, pdf_path, max_pages=4)
    return _parse_json(raw)


def answer_question(pdf_path: str, question: str, history: list[dict[str, str]]) -> str:
    prompt = f"{_QA_SYSTEM}\n\nQuestion: {question}"
    provider = settings.llm_provider
    if provider == "gemini":
        return _call_gemini_chat(prompt, pdf_path, history)
    else:
        return _call_openai_chat(provider, prompt, pdf_path, history)
