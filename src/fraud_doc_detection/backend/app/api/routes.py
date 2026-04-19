import uuid
import aiofiles
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.models.schemas import UploadResponse, AnalysisResult, DocumentListItem
from app.services.fraud_detector import DocumentFraudDetector
from app.services.ocr_service import OCRService

# Shared OCR service instance — reuses HTTP connections across requests
_ocr_service = OCRService()

router = APIRouter()

UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# In-memory document registry (replace with DB in production)
_documents: dict[str, dict] = {}


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document for fraud analysis."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_size = 0
    doc_id = str(uuid.uuid4())
    dest_path = UPLOAD_DIR / f"{doc_id}.pdf"

    async with aiofiles.open(dest_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            file_size += len(chunk)
            await f.write(chunk)

    if file_size > 50 * 1024 * 1024:  # 50MB limit
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    _documents[doc_id] = {
        "document_id": doc_id,
        "filename": file.filename,
        "file_path": str(dest_path),
        "uploaded_at": datetime.utcnow().isoformat(),
        "analyzed": False,
    }

    return UploadResponse(
        document_id=doc_id,
        filename=file.filename,
        file_size=file_size,
        message="Document uploaded successfully. Ready for analysis.",
    )


@router.post("/analyze/{document_id}", response_model=AnalysisResult)
async def analyze_document(document_id: str):
    """Run fraud detection analysis on an uploaded document."""
    doc_info = _documents.get(document_id)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = doc_info["file_path"]
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Document file missing from server.")

    # Check cached result
    result_path = RESULTS_DIR / f"{document_id}.json"
    if result_path.exists():
        with open(result_path) as f:
            return AnalysisResult(**json.load(f))

    detector = DocumentFraudDetector(file_path, ocr_service=_ocr_service)
    try:
        result = detector.run(document_id=document_id, filename=doc_info["filename"])
    finally:
        detector.close()

    # Cache result
    with open(result_path, "w") as f:
        f.write(result.model_dump_json())

    _documents[document_id]["analyzed"] = True

    return result


@router.get("/analyze/{document_id}", response_model=AnalysisResult)
async def get_analysis(document_id: str):
    """Retrieve cached analysis results."""
    result_path = RESULTS_DIR / f"{document_id}.json"
    if result_path.exists():
        with open(result_path) as f:
            return AnalysisResult(**json.load(f))

    doc_info = _documents.get(document_id)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found.")

    raise HTTPException(status_code=202, detail="Analysis not yet completed. POST to run analysis.")


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
                with open(result_path) as f:
                    data = json.load(f)
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
        ))
    return items


@router.get("/document/{document_id}/file")
async def get_document_file(document_id: str):
    """Serve the original PDF file."""
    doc_info = _documents.get(document_id)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = doc_info["file_path"]
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=doc_info["filename"],
    )


@router.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its analysis results."""
    doc_info = _documents.pop(document_id, None)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found.")

    Path(doc_info["file_path"]).unlink(missing_ok=True)
    (RESULTS_DIR / f"{document_id}.json").unlink(missing_ok=True)

    return {"message": "Document deleted successfully."}
