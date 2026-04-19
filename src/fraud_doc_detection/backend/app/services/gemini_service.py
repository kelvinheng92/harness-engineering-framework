"""
Gemini API wrapper for document understanding tasks.
Uses google-generativeai with gemini-1.5-flash (free tier).
"""
import io
import json
import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import PIL.Image
import google.generativeai as genai

from app.core.config import settings

MODEL_NAME = "gemini-2.0-flash"


def _configure() -> None:
    """Configure Gemini with the current API key."""
    genai.configure(api_key=settings.gemini_api_key)


def _pdf_to_pil_images(pdf_path: str, max_pages: int = 8, scale: float = 1.5) -> list[PIL.Image.Image]:
    """Convert PDF pages to PIL Images for Gemini."""
    doc = fitz.open(pdf_path)
    images: list[PIL.Image.Image] = []
    mat = fitz.Matrix(scale, scale)
    try:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=mat)
            img = PIL.Image.open(io.BytesIO(pix.tobytes("png")))
            img.load()  # force load before BytesIO goes out of scope
            images.append(img)
    finally:
        doc.close()
    return images


def _extract_text(pdf_path: str) -> str:
    """Extract full text from a PDF (used as supplementary context)."""
    doc = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text() for page in doc).strip()
    finally:
        doc.close()


def _build_parts(pdf_path: str, max_pages: int = 8) -> list[Any]:
    """Build the content parts list for a Gemini request (PIL images + text)."""
    _configure()
    parts: list[Any] = _pdf_to_pil_images(pdf_path, max_pages=max_pages)
    text = _extract_text(pdf_path)
    if text:
        parts.append(f"\n--- Extracted text ---\n{text[:12000]}")
    return parts


def _call_gemini(prompt: str, pdf_path: str, max_pages: int = 8, text_only: bool = False) -> str:
    """Send a prompt + document to Gemini and return the text response."""
    from google.api_core.exceptions import ResourceExhausted
    model = genai.GenerativeModel(MODEL_NAME)
    if text_only:
        text = _extract_text(pdf_path)
        parts: list[Any] = [f"--- Document text ---\n{text[:20000]}\n\n{prompt}"]
    else:
        parts = _build_parts(pdf_path, max_pages=max_pages)
        parts.append(prompt)
    try:
        response = model.generate_content(parts)
        return response.text
    except ResourceExhausted as exc:
        raise RuntimeError(
            f"Gemini free tier quota exceeded. Please wait a minute and retry, "
            f"or check your quota at aistudio.google.com. Detail: {exc}"
        ) from exc


def _call_gemini_json(prompt: str, pdf_path: str, max_pages: int = 8, text_only: bool = False) -> Any:
    """Call Gemini and parse the JSON response (strips markdown fences)."""
    raw = _call_gemini(prompt, pdf_path, max_pages=max_pages, text_only=text_only)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


def classify_document(pdf_path: str) -> dict[str, Any]:
    """
    Classify a PDF as bank_statement, annual_report, or other.

    Returns:
        {"document_type": str, "confidence": float, "reason": str}
    """
    prompt = """Analyse this document and classify it.

Return ONLY a JSON object (no markdown) with these exact keys:
{
  "document_type": "bank_statement" | "annual_report" | "income_tax" | "other",
  "confidence": <float 0-1>,
  "reason": "<one sentence explaining the classification>"
}

Rules:
- "bank_statement": issued by a bank, shows account transactions, balances, account holder details.
- "annual_report": issued by a company, contains audited financial statements, director's report, auditor's report for a fiscal year.
- "income_tax": a tax return, notice of assessment, tax form (e.g. IR8A, Form B, IRS 1040, W-2, NOA), or any government tax document showing income and tax payable.
- "other": anything not covered above."""
    # Use text-only for classification — much cheaper on tokens, sufficient for doc type detection
    return _call_gemini_json(prompt, pdf_path, text_only=True)


def extract_key_values(pdf_path: str, document_type: str) -> dict[str, Any]:
    """
    Extract structured key-value pairs from a bank statement or annual report.

    Returns:
        {"pairs": [{"key": str, "value": str, "category": str}]}
    """
    if document_type == "bank_statement":
        instructions = """Extract key information from this bank statement.
Return ONLY a JSON object (no markdown):
{
  "pairs": [
    {"key": "<field name>", "value": "<field value>", "category": "<category>"}
  ]
}

Categories and fields to extract (include only those present):
- "Account Info": Account Holder Name, Bank Name, Account Number (mask — show last 4 digits only as XXXX-XXXX-1234), Account Type, Branch, SWIFT/BIC
- "Statement Period": Statement Date, Period From, Period To
- "Balances": Opening Balance, Closing Balance, Available Balance
- "Summary": Total Credits, Total Debits, Number of Transactions
- "Contact": Bank Address, Customer Service Number"""
    elif document_type == "annual_report":
        instructions = """Extract key information from this annual report.
Return ONLY a JSON object (no markdown):
{
  "pairs": [
    {"key": "<field name>", "value": "<field value>", "category": "<category>"}
  ]
}

Categories and fields to extract (include only those present):
- "Company Info": Company Name, Registration Number, Fiscal Year End, Stock Exchange, Ticker Symbol
- "Revenue & Profit": Total Revenue, Gross Profit, Operating Profit, Net Profit/Loss, EBITDA
- "Per Share": Earnings Per Share (EPS), Dividend Per Share, Net Asset Value Per Share
- "Balance Sheet": Total Assets, Total Liabilities, Total Equity, Cash & Equivalents
- "Audit": Auditor Name, Audit Opinion
- "Governance": CEO/MD Name, CFO Name, Board Chairman"""
    elif document_type == "income_tax":
        instructions = """Extract key information from this income tax document.
Return ONLY a JSON object (no markdown):
{
  "pairs": [
    {"key": "<field name>", "value": "<field value>", "category": "<category>"}
  ]
}

Categories and fields to extract (include only those present):
- "Taxpayer Info": Taxpayer Name, NRIC/Tax Reference Number (mask — show last 4 chars only), Assessment Year, Tax Form Type
- "Income": Employment Income, Business Income, Rental Income, Other Income, Total Income
- "Deductions": CPF/Provident Fund Contributions, Reliefs & Rebates, Total Deductions, Chargeable Income
- "Tax": Tax Payable, Tax Rate, Rebates, Net Tax Payable, Tax Refund
- "Employer": Employer Name, Employer Reference Number
- "Issuing Authority": Issued By, Issue Date, Assessment Reference"""
    else:
        instructions = """Extract all key information and important fields from this document.
Return ONLY a JSON object (no markdown):
{
  "pairs": [
    {"key": "<field name>", "value": "<field value>", "category": "<category>"}
  ]
}

Group related fields under descriptive category names. Extract any names, dates, amounts,
reference numbers, and other structured information present in the document."""

    return _call_gemini_json(instructions, pdf_path, max_pages=10)


def answer_question(
    pdf_path: str,
    question: str,
    history: list[dict[str, str]],
) -> str:
    """
    Answer a user question about the document using Gemini.

    Args:
        pdf_path: Path to the uploaded PDF.
        question: The user's question.
        history: List of prior {"role": "user"|"assistant", "content": str} messages.

    Returns:
        The assistant's answer as a string.
    """
    history_text = ""
    if history:
        recent = history[-6:]  # last 3 exchanges
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in recent
        )
        history_text = f"\n\nConversation so far:\n{history_text}\n"

    prompt = f"""You are a document analysis assistant. The user has uploaded a document.
Answer the user's question accurately using only information from the document.
If the answer is not in the document, say so clearly.
Keep your answer concise and factual.{history_text}

User question: {question}"""

    return _call_gemini(prompt, pdf_path, max_pages=10)
