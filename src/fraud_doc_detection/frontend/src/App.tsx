import { useState, useEffect, useCallback } from 'react'
import { Shield, Loader2, AlertCircle, Brain } from 'lucide-react'
import { Sidebar } from './components/Sidebar'
import { UploadZone } from './components/UploadZone'
import { AnalysisPanel } from './components/AnalysisPanel'
import { PDFViewer } from './components/PDFViewer'
import { SettingsPage } from './components/SettingsPage'
import { KVPanel } from './components/KVPanel'
import { ChatPanel } from './components/ChatPanel'
import {
  uploadDocument,
  analyzeDocument,
  listDocuments,
  deleteDocument,
  getDocumentFileUrl,
  classifyDocument,
  extractKeyValues,
  askQuestion,
  getChatHistory,
  clearChat,
  getStatus,
} from './utils/api'
import type {
  AnalysisResult, DocumentListItem, DocumentType,
  KVExtractionResult, ChatMessage,
} from './types'

type AppState = 'empty' | 'uploading' | 'classifying' | 'analyzing' | 'done' | 'error'
type Page = 'main' | 'settings'
type FeatureTab = 'fraud' | 'kv' | 'chat'

const DOC_TYPE_LABEL: Record<DocumentType, string> = {
  bank_statement: 'Bank Statement',
  annual_report: 'Annual Report',
  income_tax: 'Income Tax',
  payslip: 'Payslip',
  cpf_statement: 'CPF Statement',
  investment_statement: 'Investment Statement',
  credit_report: 'Credit Report',
  financial_statement: 'Financial Statement',
  other: 'Financial Document',
}

const DOC_TYPE_COLOR: Record<DocumentType, string> = {
  bank_statement: 'bg-blue-50 text-blue-700 border-blue-200',
  annual_report: 'bg-purple-50 text-purple-700 border-purple-200',
  income_tax: 'bg-green-50 text-green-700 border-green-200',
  payslip: 'bg-orange-50 text-orange-700 border-orange-200',
  cpf_statement: 'bg-teal-50 text-teal-700 border-teal-200',
  investment_statement: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  credit_report: 'bg-red-50 text-red-700 border-red-200',
  financial_statement: 'bg-violet-50 text-violet-700 border-violet-200',
  other: 'bg-gray-50 text-gray-600 border-gray-200',
}

export default function App() {
  const [page, setPage] = useState<Page>('main')
  const [state, setState] = useState<AppState>('empty')
  const [documents, setDocuments] = useState<DocumentListItem[]>([])
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [selectedDocType, setSelectedDocType] = useState<DocumentType | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<FeatureTab>('fraud')
  const [geminiConfigured, setGeminiConfigured] = useState(false)
  const [activeProvider, setActiveProvider] = useState('groq')

  // KV state
  const [kvResult, setKvResult] = useState<KVExtractionResult | null>(null)
  const [kvLoading, setKvLoading] = useState(false)
  const [kvError, setKvError] = useState<string | null>(null)

  // Chat state
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)

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
    getStatus().then((s) => { setGeminiConfigured(s.gemini_configured); setActiveProvider(s.provider ?? 'groq') }).catch(() => {})
  }, [loadDocuments])

  const resetPanelState = () => {
    setAnalysisResult(null)
    setKvResult(null)
    setKvError(null)
    setChatHistory([])
    setChatError(null)
    setActiveTab('fraud')
  }

  const handleUpload = async (file: File) => {
    setState('uploading')
    setError(null)
    resetPanelState()
    setSelectedDocId(null)
    setSelectedDocType(null)

    try {
      const upload = await uploadDocument(file)
      await loadDocuments()

      let docType: DocumentType = 'other'

      if (geminiConfigured) {
        setState('classifying')
        try {
          const cls = await classifyDocument(upload.document_id)
          docType = cls.document_type
        } catch {
          // classification failed, continue without type
        }
      }

      setSelectedDocType(docType)
      setSelectedDocId(upload.document_id)
      await loadDocuments()

      // Auto-run fraud detection for bank statements
      if (docType === 'bank_statement' || docType === 'other') {
        setState('analyzing')
        setActiveTab('fraud')
        try {
          const result = await analyzeDocument(upload.document_id)
          setAnalysisResult(result)
        } catch {
          // fraud detection failed (ok for non-bank docs)
        }
      } else {
        // Annual report: skip fraud detection, go straight to KV tab
        setActiveTab('kv')
      }

      setState('done')
      await loadDocuments()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'An unexpected error occurred.'
      setError(msg)
      setState('error')
    }
  }

  const handleSelectDocument = async (docId: string) => {
    if (docId === selectedDocId) return
    setSelectedDocId(docId)
    resetPanelState()
    setState('analyzing')
    setError(null)

    const doc = documents.find((d) => d.document_id === docId)
    let docType = (doc?.document_type ?? null) as DocumentType | null
    setSelectedDocType(docType)

    try {
      // Auto-classify if not done yet and AI is available
      if (!docType && geminiConfigured) {
        try {
          const cls = await classifyDocument(docId)
          docType = cls.document_type
          setSelectedDocType(docType)
          await loadDocuments()
        } catch {
          // classification failed, continue
        }
      }

      // Load fraud analysis if it was done before
      if (!docType || docType === 'bank_statement') {
        try {
          const result = await analyzeDocument(docId)
          setAnalysisResult(result)
          setActiveTab('fraud')
        } catch {
          // not analyzed yet
        }
      } else {
        setActiveTab('kv')
      }

      // Load chat history
      try {
        const history = await getChatHistory(docId)
        setChatHistory(history)
      } catch {
        // no history
      }

      setState('done')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load document.'
      setError(msg)
      setState('error')
    }
  }

  const handleDelete = async (docId: string) => {
    try {
      await deleteDocument(docId)
      await loadDocuments()
      if (docId === selectedDocId) {
        setSelectedDocId(null)
        setSelectedDocType(null)
        resetPanelState()
        setState('empty')
      }
    } catch {
      // ignore
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

  const handleExtractKV = async () => {
    if (!selectedDocId || !selectedDocType) return
    setKvLoading(true)
    setKvError(null)
    try {
      const result = await extractKeyValues(selectedDocId)
      setKvResult(result)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Extraction failed.'
      setKvError(msg)
    } finally {
      setKvLoading(false)
    }
  }

  const handleSendChat = async (question: string) => {
    if (!selectedDocId) return
    setChatLoading(true)
    setChatError(null)
    try {
      const response = await askQuestion(selectedDocId, question)
      setChatHistory(response.history)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Q&A failed.'
      setChatError(msg)
    } finally {
      setChatLoading(false)
    }
  }

  const handleClearChat = async () => {
    if (!selectedDocId) return
    try {
      await clearChat(selectedDocId)
      setChatHistory([])
    } catch {
      // ignore
    }
  }

  const fileUrl = selectedDocId ? getDocumentFileUrl(selectedDocId) : null
  const selectedDoc = documents.find((d) => d.document_id === selectedDocId)

  const canFraud = true
  // KV and Chat work for any document — backend auto-classifies if needed
  const canKV = geminiConfigured
  const canChat = geminiConfigured

  return (
    <div className="flex h-screen overflow-hidden bg-[#f5f5f5]">
      <Sidebar
        documents={documents}
        selectedId={selectedDocId}
        onSelect={(id) => { setPage('main'); handleSelectDocument(id) }}
        onDelete={handleDelete}
        activePage={page}
        onNavigate={setPage}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-[#e0e0e0] flex-shrink-0">
          <div className="flex items-center gap-2 text-sm text-[#666666]">
            <span className="text-[#999999]">Home</span>
            <span className="text-[#cccccc]">/</span>
            <span className="font-medium text-[#333333]">
              {page === 'settings' ? 'Settings' : selectedDoc?.filename ?? 'Document Intelligence'}
            </span>
            {selectedDocType && page === 'main' && (
              <span className={`text-[11px] px-2 py-0.5 rounded border font-medium ${DOC_TYPE_COLOR[selectedDocType]}`}>
                {DOC_TYPE_LABEL[selectedDocType]}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <Brain size={13} className={geminiConfigured ? 'text-green-600' : 'text-[#cccccc]'} />
              <span className="text-xs text-[#888888]">
                {geminiConfigured ? `${activeProvider} ready` : 'AI not configured'}
              </span>
            </div>
            <button className="text-sm font-semibold text-[#C8102E] border border-[#C8102E] px-4 py-1.5 rounded hover:bg-[#fbeaed] transition-colors">
              Sign In
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {page === 'settings' && <SettingsPage />}

          {page === 'main' && state === 'empty' && (
            <div className="flex-1 flex items-center justify-center p-12 bg-[#f5f5f5]">
              <div className="w-full max-w-xl">
                <div className="text-center mb-8">
                  <div className="w-14 h-14 rounded-full bg-[#C8102E] flex items-center justify-center mx-auto mb-4">
                    <Shield size={26} className="text-white" />
                  </div>
                  <h1 className="text-2xl font-bold text-[#333333]">Document Intelligence</h1>
                  <p className="text-[#666666] mt-2 text-sm">
                    Upload a bank statement or annual report for fraud detection, key value extraction, and AI-powered Q&A.
                  </p>
                  {!geminiConfigured && (
                    <div className="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 inline-block">
                      Configure your Gemini API key in Settings to enable AI features.
                    </div>
                  )}
                </div>
                <UploadZone onUpload={handleUpload} uploading={false} />
              </div>
            </div>
          )}

          {page === 'main' && state === 'uploading' && (
            <div className="flex-1 flex items-center justify-center bg-[#f5f5f5]">
              <div className="text-center">
                <Loader2 size={40} className="text-[#C8102E] animate-spin mx-auto mb-4" />
                <p className="text-[#333333] font-medium">Uploading document…</p>
              </div>
            </div>
          )}

          {page === 'main' && state === 'classifying' && (
            <div className="flex-1 flex items-center justify-center bg-[#f5f5f5]">
              <div className="text-center">
                <Brain size={40} className="text-[#C8102E] animate-pulse mx-auto mb-4" />
                <p className="text-[#333333] font-medium">Classifying document…</p>
                <p className="text-[#888888] text-sm mt-1">Gemini is identifying the document type</p>
              </div>
            </div>
          )}

          {page === 'main' && state === 'analyzing' && (
            <div className="flex-1 flex items-center justify-center bg-[#f5f5f5]">
              <div className="text-center">
                <div className="relative w-14 h-14 mx-auto mb-4">
                  <div className="absolute inset-0 rounded-full border-4 border-[#f5d0d6]" />
                  <div className="absolute inset-0 rounded-full border-4 border-[#C8102E] border-t-transparent animate-spin" />
                  <Shield size={22} className="absolute inset-0 m-auto text-[#C8102E]" />
                </div>
                <p className="text-[#333333] font-semibold">Analysing document…</p>
                <p className="text-[#888888] text-sm mt-1">Running fraud detection algorithms</p>
              </div>
            </div>
          )}

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

          {page === 'main' && state === 'done' && fileUrl && (
            <>
              {/* Left panel — feature tabs */}
              <div className="w-[600px] flex-shrink-0 border-r border-[#e0e0e0] bg-[#f5f5f5] flex flex-col overflow-hidden">
                {/* Upload another */}
                <div className="px-4 pt-4 pb-2 flex-shrink-0">
                  <label className="flex items-center gap-2 px-3 py-2.5 rounded bg-white border border-[#e0e0e0] hover:border-[#C8102E] cursor-pointer transition-colors group">
                    <input
                      type="file"
                      accept=".pdf"
                      className="hidden"
                      onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f) }}
                    />
                    <Shield size={14} className="text-[#C8102E]" />
                    <span className="text-xs text-[#666666] group-hover:text-[#C8102E] transition-colors">
                      Analyse another document
                    </span>
                  </label>
                </div>

                {/* Feature tabs */}
                <div className="flex px-4 gap-1 flex-shrink-0 border-b border-[#e0e0e0] bg-[#f5f5f5] pb-0">
                  <TabButton
                    label="Fraud Detection"
                    active={activeTab === 'fraud'}
                    disabled={!canFraud}
                    onClick={() => setActiveTab('fraud')}
                  />
                  <TabButton
                    label="Key Values"
                    active={activeTab === 'kv'}
                    disabled={!canKV}
                    title={!canKV ? (!geminiConfigured ? 'Configure Gemini API key in Settings' : 'Only for bank statements & annual reports') : undefined}
                    onClick={() => setActiveTab('kv')}
                  />
                  <TabButton
                    label="Ask Document"
                    active={activeTab === 'chat'}
                    disabled={!canChat}
                    title={!canChat ? (!geminiConfigured ? 'Configure Gemini API key in Settings' : 'Only for bank statements & annual reports') : undefined}
                    onClick={() => setActiveTab('chat')}
                  />
                </div>

                {/* Panel content */}
                <div className="flex-1 overflow-hidden flex flex-col">
                  {activeTab === 'fraud' && (
                    <div className="flex-1 overflow-y-auto p-4">
                      {analysisResult ? (
                        <AnalysisPanel
                          result={analysisResult}
                          onReanalyze={handleReanalyze}
                          analyzing={false}
                        />
                      ) : (
                        <div className="flex flex-col items-center justify-center h-full text-center gap-3">
                          <Shield size={32} className="text-[#e0e0e0]" />
                          {canFraud ? (
                            <>
                              <p className="text-sm text-[#888888]">No fraud analysis yet.</p>
                              <button
                                onClick={handleReanalyze}
                                className="px-4 py-2 bg-[#C8102E] text-white text-sm rounded hover:bg-[#a50d26] transition-colors font-medium"
                              >
                                Run Analysis
                              </button>
                            </>
                          ) : (
                            <p className="text-sm text-[#888888]">
                              Fraud detection is only available for bank statements.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'kv' && selectedDocId && selectedDocType && (
                    <div className="flex-1 overflow-y-auto p-4">
                      <KVPanel
                        documentId={selectedDocId}
                        documentType={selectedDocType}
                        result={kvResult}
                        loading={kvLoading}
                        error={kvError}
                        onExtract={handleExtractKV}
                      />
                    </div>
                  )}

                  {activeTab === 'chat' && selectedDocId && (
                    <ChatPanel
                      documentId={selectedDocId}
                      history={chatHistory}
                      loading={chatLoading}
                      error={chatError}
                      onSend={handleSendChat}
                      onClear={handleClearChat}
                    />
                  )}
                </div>
              </div>

              {/* PDF Viewer */}
              <div className="flex-1 overflow-hidden">
                <PDFViewer url={fileUrl} filename={selectedDoc?.filename ?? ''} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function TabButton({
  label,
  active,
  disabled,
  title,
  onClick,
}: {
  label: string
  active: boolean
  disabled?: boolean
  title?: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`px-3 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
        active
          ? 'border-[#C8102E] text-[#C8102E]'
          : disabled
          ? 'border-transparent text-[#cccccc] cursor-not-allowed'
          : 'border-transparent text-[#666666] hover:text-[#333333] hover:border-[#cccccc]'
      }`}
    >
      {label}
    </button>
  )
}
