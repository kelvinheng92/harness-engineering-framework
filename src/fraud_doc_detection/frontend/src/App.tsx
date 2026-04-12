import { useState, useEffect, useCallback } from 'react'
import { Shield, Loader2, AlertCircle } from 'lucide-react'
import { Sidebar } from './components/Sidebar'
import { UploadZone } from './components/UploadZone'
import { AnalysisPanel } from './components/AnalysisPanel'
import { PDFViewer } from './components/PDFViewer'
import { SettingsPage } from './components/SettingsPage'
import {
  uploadDocument,
  analyzeDocument,
  listDocuments,
  deleteDocument,
  getDocumentFileUrl,
} from './utils/api'
import type { AnalysisResult, DocumentListItem } from './types'

type AppState = 'empty' | 'uploading' | 'analyzing' | 'done' | 'error'
type Page = 'main' | 'settings'

export default function App() {
  const [page, setPage] = useState<Page>('main')
  const [state, setState] = useState<AppState>('empty')
  const [documents, setDocuments] = useState<DocumentListItem[]>([])
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await listDocuments()
      setDocuments(docs)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleUpload = async (file: File) => {
    setState('uploading')
    setError(null)
    setAnalysisResult(null)
    try {
      const upload = await uploadDocument(file)
      setState('analyzing')
      await loadDocuments()
      const result = await analyzeDocument(upload.document_id)
      setSelectedDocId(upload.document_id)
      setAnalysisResult(result)
      await loadDocuments()
      setState('done')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'An unexpected error occurred.'
      setError(msg)
      setState('error')
    }
  }

  const handleSelectDocument = async (docId: string) => {
    if (docId === selectedDocId) return
    setSelectedDocId(docId)
    setAnalysisResult(null)
    setState('analyzing')
    setError(null)
    try {
      const result = await analyzeDocument(docId)
      setAnalysisResult(result)
      setState('done')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load analysis.'
      setError(msg)
      setState('error')
    }
  }

  const handleReanalyze = async () => {
    if (!selectedDocId) return
    setState('analyzing')
    setError(null)
    try {
      const result = await analyzeDocument(selectedDocId)
      setAnalysisResult(result)
      setState('done')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Re-analysis failed.'
      setError(msg)
      setState('error')
    }
  }

  const fileUrl = selectedDocId ? getDocumentFileUrl(selectedDocId) : null
  const selectedDoc = documents.find((d) => d.document_id === selectedDocId)

  return (
    <div className="flex h-screen overflow-hidden bg-[#f5f5f5]">
      {/* Sidebar */}
      <Sidebar
        documents={documents}
        selectedId={selectedDocId}
        onSelect={(id) => { setPage('main'); handleSelectDocument(id) }}
        activePage={page}
        onNavigate={setPage}
      />

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar — OCBC style */}
        <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-[#e0e0e0] flex-shrink-0">
          <div className="flex items-center gap-2 text-sm text-[#666666]">
            <span className="text-[#999999]">Home</span>
            <span className="text-[#cccccc]">/</span>
            <span className="font-medium text-[#333333]">
              {page === 'settings'
                ? 'Settings'
                : selectedDoc?.filename ?? 'Document Analysis'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <nav className="hidden md:flex items-center gap-5 text-sm text-[#555555]">
              <a className="hover:text-[#C8102E] transition-colors cursor-pointer">Overview</a>
              <a className="hover:text-[#C8102E] transition-colors cursor-pointer">Reports</a>
              <a className="hover:text-[#C8102E] transition-colors cursor-pointer">Security</a>
            </nav>
            <button className="text-sm font-semibold text-[#C8102E] border border-[#C8102E] px-4 py-1.5 rounded hover:bg-[#fbeaed] transition-colors">
              Sign In
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Settings page */}
          {page === 'settings' && <SettingsPage />}

          {/* Upload / Empty state */}
          {page === 'main' && state === 'empty' && (
            <div className="flex-1 flex items-center justify-center p-12 bg-[#f5f5f5]">
              <div className="w-full max-w-xl">
                <div className="text-center mb-8">
                  <div className="w-14 h-14 rounded-full bg-[#C8102E] flex items-center justify-center mx-auto mb-4">
                    <Shield size={26} className="text-white" />
                  </div>
                  <h1 className="text-2xl font-bold text-[#333333]">Document Fraud Detection</h1>
                  <p className="text-[#666666] mt-2 text-sm">
                    Upload a PDF to detect signs of forgery, manipulation, and fraud using AI analysis.
                  </p>
                </div>
                <UploadZone onUpload={handleUpload} uploading={false} />
              </div>
            </div>
          )}

          {/* Uploading state */}
          {page === 'main' && state === 'uploading' && (
            <div className="flex-1 flex items-center justify-center bg-[#f5f5f5]">
              <div className="text-center">
                <Loader2 size={40} className="text-[#C8102E] animate-spin mx-auto mb-4" />
                <p className="text-[#333333] font-medium">Uploading document...</p>
                <p className="text-[#888888] text-sm mt-1">This may take a moment</p>
              </div>
            </div>
          )}

          {/* Analyzing state */}
          {page === 'main' && state === 'analyzing' && (
            <div className="flex-1 flex items-center justify-center bg-[#f5f5f5]">
              <div className="text-center">
                <div className="relative w-14 h-14 mx-auto mb-4">
                  <div className="absolute inset-0 rounded-full border-4 border-[#f5d0d6]" />
                  <div className="absolute inset-0 rounded-full border-4 border-[#C8102E] border-t-transparent animate-spin" />
                  <Shield size={22} className="absolute inset-0 m-auto text-[#C8102E]" />
                </div>
                <p className="text-[#333333] font-semibold">Analysing document...</p>
                <p className="text-[#888888] text-sm mt-1">Running fraud detection algorithms</p>
                <div className="mt-4 flex flex-col gap-1.5 text-xs text-[#888888] text-left max-w-[220px] mx-auto">
                  {[
                    'Extracting metadata...',
                    'Analysing font consistency...',
                    'Checking text layers...',
                    'Scanning PDF structure...',
                    'Running fraud scoring...',
                  ].map((step, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div
                        className="w-1.5 h-1.5 rounded-full bg-[#C8102E] animate-pulse"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Error state */}
          {page === 'main' && state === 'error' && (
            <div className="flex-1 flex items-center justify-center p-12 bg-[#f5f5f5]">
              <div className="w-full max-w-xl space-y-6">
                <div className="bg-white border border-[#e0e0e0] rounded p-4 flex items-start gap-3">
                  <AlertCircle size={18} className="text-[#C8102E] flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-[#C8102E]">Analysis Failed</p>
                    <p className="text-xs text-[#666666] mt-0.5">{error}</p>
                  </div>
                </div>
                <UploadZone onUpload={handleUpload} uploading={false} />
              </div>
            </div>
          )}

          {/* Done state: split view */}
          {page === 'main' && state === 'done' && analysisResult && fileUrl && (
            <>
              {/* Analysis panel */}
              <div className="w-[600px] flex-shrink-0 border-r border-[#e0e0e0] bg-[#f5f5f5] p-4 overflow-y-auto">
                {/* Quick upload another */}
                <label className="flex items-center gap-2 px-3 py-2.5 rounded bg-white border border-[#e0e0e0] hover:border-[#C8102E] cursor-pointer transition-colors mb-4 group">
                  <input
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0]
                      if (f) handleUpload(f)
                    }}
                  />
                  <Shield size={14} className="text-[#C8102E]" />
                  <span className="text-xs text-[#666666] group-hover:text-[#C8102E] transition-colors">
                    Analyse another document
                  </span>
                </label>

                <AnalysisPanel
                  result={analysisResult}
                  onReanalyze={handleReanalyze}
                  analyzing={false}
                />
              </div>

              {/* PDF Viewer */}
              <div className="flex-1 overflow-hidden">
                <PDFViewer url={fileUrl} filename={analysisResult.filename} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
