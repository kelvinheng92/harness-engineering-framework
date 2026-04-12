from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum


class IndicatorSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SAFE = "safe"


class FraudIndicator(BaseModel):
    id: str
    title: str
    description: str
    severity: IndicatorSeverity
    details: Optional[str] = None
    confidence: float  # 0-100


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
