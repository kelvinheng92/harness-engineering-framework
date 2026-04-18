import { Table2, Loader2, RefreshCw } from 'lucide-react'
import type { KVExtractionResult, DocumentType } from '../types'

interface KVPanelProps {
  documentId: string
  documentType: DocumentType
  result: KVExtractionResult | null
  loading: boolean
  error: string | null
  onExtract: () => void
}

const DOC_TYPE_LABEL: Record<DocumentType, string> = {
  bank_statement: 'Bank Statement',
  annual_report: 'Annual Report',
  income_tax: 'Income Tax Document',
  payslip: 'Payslip',
  cpf_statement: 'CPF Statement',
  investment_statement: 'Investment Statement',
  credit_report: 'Credit Report',
  financial_statement: 'Financial Statement',
  other: 'Financial Document',
}

export function KVPanel({ documentType, result, loading, error, onExtract }: KVPanelProps) {
  // Group pairs by category
  const grouped = result
    ? result.pairs.reduce<Record<string, typeof result.pairs>>((acc, pair) => {
        const cat = pair.category || 'General'
        if (!acc[cat]) acc[cat] = []
        acc[cat].push(pair)
        return acc
      }, {})
    : {}

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 size={32} className="text-[#C8102E] animate-spin mx-auto mb-3" />
          <p className="text-sm font-medium text-[#333333]">Extracting key values…</p>
          <p className="text-xs text-[#888888] mt-1">Gemini is reading the document</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="bg-red-50 border border-red-200 rounded p-4 max-w-sm w-full text-center">
          <p className="text-sm font-semibold text-red-700 mb-1">Extraction Failed</p>
          <p className="text-xs text-red-600">{error}</p>
          <button
            onClick={onExtract}
            className="mt-3 text-xs px-3 py-1.5 rounded border border-red-300 text-red-700 hover:bg-red-100 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center max-w-xs">
          <div className="w-12 h-12 rounded-full bg-[#f0f0f0] flex items-center justify-center mx-auto mb-4">
            <Table2 size={22} className="text-[#aaaaaa]" />
          </div>
          <p className="text-sm font-medium text-[#333333] mb-1">
            Extract Key Values
          </p>
          <p className="text-xs text-[#888888] mb-4">
            Gemini will extract structured fields from this {DOC_TYPE_LABEL[documentType]}.
          </p>
          <button
            onClick={onExtract}
            className="px-4 py-2 bg-[#C8102E] text-white text-sm rounded hover:bg-[#a50d26] transition-colors font-medium"
          >
            Extract Now
          </button>
        </div>
      </div>
    )
  }

  const categories = Object.keys(grouped)

  return (
    <div className="flex flex-col gap-3 h-full overflow-y-auto pb-6">
      {/* Header */}
      <div className="bg-white rounded border border-[#e0e0e0] p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#C8102E] flex items-center justify-center">
              <Table2 size={16} className="text-white" />
            </div>
            <div>
              <p className="text-xs text-[#888888]">Extracted from</p>
              <p className="text-sm font-semibold text-[#333333]">{DOC_TYPE_LABEL[documentType]}</p>
            </div>
          </div>
          <button
            onClick={onExtract}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-[#e0e0e0] bg-white hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors"
          >
            <RefreshCw size={12} />
            Re-extract
          </button>
        </div>
        <p className="text-xs text-[#888888] mt-3">
          {result.pairs.length} fields extracted · {categories.length} categories
        </p>
      </div>

      {/* Grouped tables — always expanded */}
      {categories.map((cat) => {
        const pairs = grouped[cat]
        return (
          <div key={cat} className="bg-white rounded border border-[#e0e0e0] overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#f0f0f0]">
              <span className="text-sm font-semibold text-[#333333]">{cat}</span>
              <span className="text-xs text-[#888888]">{pairs.length} fields</span>
            </div>
            <div>
              {pairs.map((pair, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-3 px-4 py-2.5 ${i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'}`}
                >
                  <span className="text-xs text-[#888888] w-36 flex-shrink-0 pt-0.5">{pair.key}</span>
                  <span className="text-xs font-medium text-[#333333] break-words flex-1">{pair.value}</span>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
