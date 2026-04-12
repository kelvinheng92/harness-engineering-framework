export type IndicatorSeverity = 'high' | 'medium' | 'low' | 'safe'

export interface FraudIndicator {
  id: string
  title: string
  description: string
  severity: IndicatorSeverity
  details?: string
  confidence: number
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
}
