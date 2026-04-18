import axios from 'axios'
import type {
  AnalysisResult, UploadResponse, DocumentListItem,
  ClassificationResult, KVExtractionResult, QAResponse,
  ChatMessage, StatusResponse,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// ─── Status / Settings ───────────────────────────────────────────────────────

export async function getStatus(): Promise<StatusResponse> {
  const { data } = await api.get<StatusResponse>('/status')
  return data
}

export async function saveApiKey(apiKey: string, provider: string): Promise<void> {
  await api.post('/settings/key', { api_key: apiKey, provider })
}

// ─── Upload ──────────────────────────────────────────────────────────────────

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<UploadResponse>('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ─── Document list / file / delete ───────────────────────────────────────────

export async function listDocuments(): Promise<DocumentListItem[]> {
  const { data } = await api.get<DocumentListItem[]>('/documents')
  return data
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/document/${documentId}`)
}

export async function clearCache(): Promise<void> {
  await api.delete('/cache')
}

export function getDocumentFileUrl(documentId: string): string {
  return `/api/document/${documentId}/file`
}

// ─── Fraud Detection ─────────────────────────────────────────────────────────

export async function analyzeDocument(documentId: string): Promise<AnalysisResult> {
  const { data } = await api.post<AnalysisResult>(`/analyze/${documentId}`)
  return data
}

export async function getAnalysis(documentId: string): Promise<AnalysisResult> {
  const { data } = await api.get<AnalysisResult>(`/analyze/${documentId}`)
  return data
}

// ─── Classification ──────────────────────────────────────────────────────────

export async function classifyDocument(documentId: string): Promise<ClassificationResult> {
  const { data } = await api.post<ClassificationResult>(`/classify/${documentId}`)
  return data
}

// ─── Key-Value Extraction ────────────────────────────────────────────────────

export async function extractKeyValues(documentId: string): Promise<KVExtractionResult> {
  const { data } = await api.post<KVExtractionResult>(`/extract/${documentId}`)
  return data
}

export async function getKeyValues(documentId: string): Promise<KVExtractionResult> {
  const { data } = await api.get<KVExtractionResult>(`/extract/${documentId}`)
  return data
}

// ─── Document Q&A ────────────────────────────────────────────────────────────

export async function askQuestion(documentId: string, question: string): Promise<QAResponse> {
  const { data } = await api.post<QAResponse>(`/chat/${documentId}`, { question })
  return data
}

export async function getChatHistory(documentId: string): Promise<ChatMessage[]> {
  const { data } = await api.get<ChatMessage[]>(`/chat/${documentId}`)
  return data
}

export async function clearChat(documentId: string): Promise<void> {
  await api.delete(`/chat/${documentId}`)
}
