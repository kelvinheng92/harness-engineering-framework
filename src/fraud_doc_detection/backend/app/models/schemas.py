from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum


class HighlightBox(BaseModel):
    """Bounding box for a specific region of interest inside a PDF page.

    Coordinates are in PDF points with top-left origin (PyMuPDF device space).
    page_width / page_height are the MediaBox dimensions of that page in points,
    used by the frontend to compute the pixel→point scale factor.
    """
    page: int         # 1-indexed
    x0: float
    y0: float
    x1: float
    y1: float
    label: str        # short tooltip shown on hover
    page_width: float
    page_height: float


# ─── Shared ──────────────────────────────────────────────────────────────────

class IndicatorSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SAFE = "safe"


class DocumentType(str, Enum):
    BANK_STATEMENT = "bank_statement"
    ANNUAL_REPORT = "annual_report"
    INCOME_TAX = "income_tax"
    PAYSLIP = "payslip"
    CPF_STATEMENT = "cpf_statement"
    INVESTMENT_STATEMENT = "investment_statement"
    CREDIT_REPORT = "credit_report"
    FINANCIAL_STATEMENT = "financial_statement"
    OTHER = "other"


# ─── Fraud Detection ─────────────────────────────────────────────────────────

class FraudIndicator(BaseModel):
    id: str
    title: str
    description: str
    severity: IndicatorSeverity
    details: Optional[str] = None
    confidence: float  # 0-100
    highlights: List[HighlightBox] = []


class MetadataEntry(BaseModel):
    field: str
    original_text: Optional[str] = None
    new_text: Optional[str] = None
    status: Literal["match", "mismatch", "suspicious", "missing", "annotation"]


class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    page_count: int = 0
    file_size: int = 0
    is_encrypted: bool = False
    has_digital_signature: bool = False
    pdf_version: Optional[str] = None


class AnalysisResult(BaseModel):
    document_id: str
    filename: str
    overall_risk: IndicatorSeverity
    fraud_score: float  # 0-100, higher = more suspicious
    indicators: List[FraudIndicator]
    metadata_entries: List[MetadataEntry]
    metadata: DocumentMetadata
    summary: str
    page_count: int
    analyzed_at: str


# ─── Upload / Document List ───────────────────────────────────────────────────

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    file_size: int
    message: str


class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    uploaded_at: str
    overall_risk: Optional[IndicatorSeverity] = None
    fraud_score: Optional[float] = None
    analyzed: bool = False
    document_type: Optional[DocumentType] = None


# ─── Classification ──────────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    document_id: str
    document_type: DocumentType
    confidence: float
    reason: str


# ─── Key-Value Extraction ────────────────────────────────────────────────────

class ExtractionRequest(BaseModel):
    additional_keys: List[str] = []


class KeyValuePair(BaseModel):
    key: str
    value: str
    category: str


class KVExtractionResult(BaseModel):
    document_id: str
    document_type: DocumentType
    pairs: List[KeyValuePair]
    extracted_at: str


# ─── Document Q&A ────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class QARequest(BaseModel):
    question: str


class QAResponse(BaseModel):
    answer: str
    timestamp: str
    history: List[ChatMessage]


# ─── Settings ────────────────────────────────────────────────────────────────

class ApiKeyRequest(BaseModel):
    api_key: str
    provider: str = ""


class StatusResponse(BaseModel):
    gemini_configured: bool   # kept for frontend compat
    provider: str = "groq"
