import axios from 'axios'
import type { AnalysisResult, UploadResponse, DocumentListItem } from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<UploadResponse>('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function analyzeDocument(documentId: string): Promise<AnalysisResult> {
  const { data } = await api.post<AnalysisResult>(`/analyze/${documentId}`)
  return data
}

export async function getAnalysis(documentId: string): Promise<AnalysisResult> {
  const { data } = await api.get<AnalysisResult>(`/analyze/${documentId}`)
  return data
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  const { data } = await api.get<DocumentListItem[]>('/documents')
  return data
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/document/${documentId}`)
}

export function getDocumentFileUrl(documentId: string): string {
  return `/api/document/${documentId}/file`
}
