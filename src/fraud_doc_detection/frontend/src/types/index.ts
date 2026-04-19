export type IndicatorSeverity = 'high' | 'medium' | 'low' | 'safe'
export type DocumentType =
  | 'bank_statement'
  | 'annual_report'
  | 'income_tax'
  | 'payslip'
  | 'cpf_statement'
  | 'investment_statement'
  | 'credit_report'
  | 'financial_statement'
  | 'other'

export interface HighlightBox {
  page: number
  x0: number
  y0: number
  x1: number
  y1: number
  label: string
  page_width: number
  page_height: number
}

export interface FraudIndicator {
  id: string
  title: string
  description: string
  severity: IndicatorSeverity
  details?: string
  confidence: number
  highlights?: HighlightBox[]
}

export interface MetadataEntry {
  field: string
  original_text?: string
  new_text?: string
  status: 'match' | 'mismatch' | 'suspicious' | 'missing' | 'annotation'
}

export interface DocumentMetadata {
  title?: string
  author?: string
  creator?: string
  producer?: string
  creation_date?: string
  modification_date?: string
  page_count: number
  file_size: number
  is_encrypted: boolean
  has_digital_signature: boolean
  pdf_version?: string
}

export interface AnalysisResult {
  document_id: string
  filename: string
  overall_risk: IndicatorSeverity
  fraud_score: number
  indicators: FraudIndicator[]
  metadata_entries: MetadataEntry[]
  metadata: DocumentMetadata
  summary: string
  page_count: number
  analyzed_at: string
}

export interface UploadResponse {
  document_id: string
  filename: string
  file_size: number
  message: string
}

export interface DocumentListItem {
  document_id: string
  filename: string
  uploaded_at: string
  overall_risk?: IndicatorSeverity
  fraud_score?: number
  analyzed: boolean
  document_type?: DocumentType
}

export interface ClassificationResult {
  document_id: string
  document_type: DocumentType
  confidence: number
  reason: string
}

export interface KeyValuePair {
  key: string
  value: string
  category: string
}

export interface KVExtractionResult {
  document_id: string
  document_type: DocumentType
  pairs: KeyValuePair[]
  extracted_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface QAResponse {
  answer: string
  timestamp: string
  history: ChatMessage[]
}

export interface StatusResponse {
  gemini_configured: boolean
  provider: string
}
