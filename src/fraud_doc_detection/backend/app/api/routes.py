import uuid
import aiofiles
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import (
    UploadResponse, AnalysisResult, DocumentListItem,
    ClassificationResult, KVExtractionResult, KeyValuePair,
    ExtractionRequest,
    QARequest, QAResponse, ChatMessage,
    ApiKeyRequest, StatusResponse, DocumentType,
)
from app.services.fraud_detector import DocumentFraudDetector
from app.services.ocr_service import OCRService
from app.services import llm_service
from app.core.config import settings

# Shared OCR service instance — reuses HTTP connections across requests
_ocr_service = OCRService()

router = APIRouter()

UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
KV_DIR = Path("results/kv")
REGISTRY_FILE = Path("results/registry.json")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
KV_DIR.mkdir(parents=True, exist_ok=True)

_chat_history: dict[str, list[dict]] = {}


def _load_registry() -> dict[str, dict]:
    """Load document registry from disk, dropping entries whose files are missing."""
    if not REGISTRY_FILE.exists():
        return {}
    try:
        data = json.loads(REGISTRY_FILE.read_text())
        return {k: v for k, v in data.items() if Path(v.get("file_path", "")).exists()}
    except Exception:
        return {}


def _save_registry() -> None:
    REGISTRY_FILE.write_text(json.dumps(_documents, indent=2))


_documents: dict[str, dict] = _load_registry()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_llm() -> None:
    if not settings.is_configured():
        raise HTTPException(
            status_code=503,
            detail=f"No API key configured for provider '{settings.llm_provider}'. Go to Settings.",
        )


def _get_doc_or_404(document_id: str) -> dict:
    doc = _documents.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


# ─── Status / Settings ───────────────────────────────────────────────────────

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Return current configuration status."""
    return StatusResponse(
        gemini_configured=settings.is_configured(),
        provider=settings.llm_provider,
    )


@router.post("/settings/key")
async def set_api_key(body: ApiKeyRequest):
    """Persist the active provider's API key and optional provider choice to .env."""
    env_path = Path(".env")
    key = body.api_key.strip()
    provider = (body.provider or settings.llm_provider).strip()

    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    env_key_name = {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "qwen": "QWEN_API_KEY",
    }.get(provider, "GROQ_API_KEY")

    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    def _upsert(lines: list[str], var: str, value: str) -> list[str]:
        for i, line in enumerate(lines):
            if line.startswith(f"{var}="):
                lines[i] = f"{var}={value}"
                return lines
        lines.append(f"{var}={value}")
        return lines

    lines = _upsert(lines, env_key_name, key)
    lines = _upsert(lines, "LLM_PROVIDER", provider)

    env_path.write_text("\n".join(lines) + "\n")
    settings.reload()
    return {"message": f"API key saved for provider '{provider}'."}


# ─── Upload ──────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_size = 0
    doc_id = str(uuid.uuid4())
    dest_path = UPLOAD_DIR / f"{doc_id}.pdf"

    async with aiofiles.open(dest_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            await f.write(chunk)

    if file_size > 50 * 1024 * 1024:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    _documents[doc_id] = {
        "document_id": doc_id,
        "filename": file.filename,
        "file_path": str(dest_path),
        "uploaded_at": _now(),
        "analyzed": False,
        "document_type": None,
    }
    _save_registry()

    return UploadResponse(
        document_id=doc_id,
        filename=file.filename,
        file_size=file_size,
        message="Document uploaded successfully. Ready for analysis.",
    )


# ─── Document list / file serving / delete ───────────────────────────────────

@router.get("/documents", response_model=List[DocumentListItem])
async def list_documents():
    """List all uploaded documents."""
    items = []
    for doc_id, info in _documents.items():
        result_path = RESULTS_DIR / f"{doc_id}.json"
        risk = None
        score = None
        if result_path.exists():
            try:
                data = json.loads(result_path.read_text())
                risk = data.get("overall_risk")
                score = data.get("fraud_score")
            except Exception:
                pass
        items.append(DocumentListItem(
            document_id=doc_id,
            filename=info["filename"],
            uploaded_at=info["uploaded_at"],
            overall_risk=risk,
            fraud_score=score,
            analyzed=info.get("analyzed", False),
            document_type=info.get("document_type"),
        ))
    return items


@router.get("/document/{document_id}/file")
async def get_document_file(document_id: str):
    """Serve the original PDF file."""
    doc_info = _get_doc_or_404(document_id)
    file_path = doc_info["file_path"]
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path=file_path, media_type="application/pdf", filename=doc_info["filename"])


@router.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """Delete a document, its uploads, results, KV cache, and chat history."""
    doc_info = _documents.pop(document_id, None)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found.")

    Path(doc_info["file_path"]).unlink(missing_ok=True)
    (RESULTS_DIR / f"{document_id}.json").unlink(missing_ok=True)
    (KV_DIR / f"{document_id}.json").unlink(missing_ok=True)
    _chat_history.pop(document_id, None)
    _save_registry()

    return {"message": "Document deleted successfully."}


@router.delete("/cache")
async def clear_cache():
    """Delete all documents, uploads, results, and chat history."""
    for doc_id, info in list(_documents.items()):
        Path(info["file_path"]).unlink(missing_ok=True)
        (RESULTS_DIR / f"{doc_id}.json").unlink(missing_ok=True)
        (KV_DIR / f"{doc_id}.json").unlink(missing_ok=True)
    _documents.clear()
    _chat_history.clear()
    _save_registry()
    return {"message": "All documents cleared."}


# ─── Fraud Detection ─────────────────────────────────────────────────────────

@router.post("/analyze/{document_id}", response_model=AnalysisResult)
async def analyze_document(document_id: str):
    """Run fraud detection on an uploaded document (bank statements only)."""
    doc_info = _get_doc_or_404(document_id)

    file_path = doc_info["file_path"]
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Document file missing from server.")

    result_path = RESULTS_DIR / f"{document_id}.json"
    if result_path.exists():
        return AnalysisResult(**json.loads(result_path.read_text()))

    detector = DocumentFraudDetector(file_path, ocr_service=_ocr_service)
    try:
        result = detector.run(document_id=document_id, filename=doc_info["filename"])
    finally:
        detector.close()

    result_path.write_text(result.model_dump_json())
    _documents[document_id]["analyzed"] = True
    _save_registry()
    return result


@router.get("/analyze/{document_id}", response_model=AnalysisResult)
async def get_analysis(document_id: str):
    """Retrieve cached fraud analysis results."""
    result_path = RESULTS_DIR / f"{document_id}.json"
    if result_path.exists():
        return AnalysisResult(**json.loads(result_path.read_text()))
    doc_info = _documents.get(document_id)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found.")
    raise HTTPException(status_code=202, detail="Analysis not yet run. POST to /analyze/{id} first.")


# ─── Classification ──────────────────────────────────────────────────────────

@router.post("/classify/{document_id}", response_model=ClassificationResult)
async def classify_document(document_id: str):
    """Classify a document as bank_statement, annual_report, or other using Gemini."""
    _require_llm()
    doc_info = _get_doc_or_404(document_id)
    file_path = doc_info["file_path"]

    try:
        result = llm_service.classify_document(file_path)
    except RuntimeError as exc:
        status = 429 if "quota" in str(exc).lower() else 500
        raise HTTPException(status_code=status, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Classification failed: {exc}")

    doc_type = result.get("document_type", "other")
    _documents[document_id]["document_type"] = doc_type
    _save_registry()

    return ClassificationResult(
        document_id=document_id,
        document_type=DocumentType(doc_type),
        confidence=float(result.get("confidence", 0.0)),
        reason=result.get("reason", ""),
    )


# ─── Key-Value Extraction ────────────────────────────────────────────────────

@router.post("/extract/{document_id}", response_model=KVExtractionResult)
async def extract_key_values(document_id: str, body: ExtractionRequest = ExtractionRequest()):
    """Extract structured key-value pairs from any financial document."""
    _require_llm()
    doc_info = _get_doc_or_404(document_id)

    doc_type = doc_info.get("document_type") or "other"

    additional_keys = body.additional_keys or None

    # Only use cache for full (non-targeted) extractions
    kv_path = KV_DIR / f"{document_id}.json"
    if not additional_keys and kv_path.exists():
        return KVExtractionResult(**json.loads(kv_path.read_text()))

    file_path = doc_info["file_path"]
    try:
        raw = llm_service.extract_key_values(file_path, doc_type, additional_keys)
    except RuntimeError as exc:
        status_code = 429 if "quota" in str(exc).lower() or "rate" in str(exc).lower() else 500
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    def _to_str(v: object) -> str:
        """Flatten any non-string value the LLM may return (list, dict, number)."""
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return ", ".join(f"{k}: {_to_str(val)}" for k, val in v.items())
        if isinstance(v, list):
            return ", ".join(_to_str(i) for i in v)
        return str(v)

    pairs = [
        KeyValuePair(
            key=_to_str(p.get("key", "")),
            value=_to_str(p.get("value", "")),
            category=_to_str(p.get("category", "General")),
        )
        for p in raw.get("pairs", [])
        if p.get("key") and p.get("value")
    ]

    result = KVExtractionResult(
        document_id=document_id,
        document_type=DocumentType(doc_type),
        pairs=pairs,
        extracted_at=_now(),
    )
    if not additional_keys:
        kv_path.write_text(result.model_dump_json())
    return result


@router.get("/extract/{document_id}", response_model=KVExtractionResult)
async def get_key_values(document_id: str):
    """Return cached key-value extraction result."""
    kv_path = KV_DIR / f"{document_id}.json"
    if kv_path.exists():
        return KVExtractionResult(**json.loads(kv_path.read_text()))
    raise HTTPException(status_code=404, detail="No extraction result found. POST to /extract/{id} first.")


# ─── Document Q&A ────────────────────────────────────────────────────────────

@router.post("/chat/{document_id}", response_model=QAResponse)
async def ask_question(document_id: str, body: QARequest):
    """Ask a question about the document using Gemini."""
    _require_llm()
    doc_info = _get_doc_or_404(document_id)

    file_path = doc_info["file_path"]
    history = _chat_history.get(document_id, [])

    try:
        answer = llm_service.answer_question(file_path, body.question, history)
    except RuntimeError as exc:
        status = 429 if "quota" in str(exc).lower() else 500
        raise HTTPException(status_code=status, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {exc}")

    ts = _now()
    history.append({"role": "user", "content": body.question, "timestamp": ts})
    history.append({"role": "assistant", "content": answer, "timestamp": ts})
    _chat_history[document_id] = history

    return QAResponse(
        answer=answer,
        timestamp=ts,
        history=[ChatMessage(**m) for m in history],
    )


@router.get("/chat/{document_id}", response_model=list[ChatMessage])
async def get_chat_history(document_id: str):
    """Return the chat history for a document."""
    _get_doc_or_404(document_id)
    return [ChatMessage(**m) for m in _chat_history.get(document_id, [])]


@router.delete("/chat/{document_id}")
async def clear_chat(document_id: str):
    """Clear the chat history for a document."""
    _get_doc_or_404(document_id)
    _chat_history.pop(document_id, None)
    return {"message": "Chat history cleared."}
