import { useState } from 'react'
import { Shield, AlertTriangle, ChevronDown, RefreshCw } from 'lucide-react'
import type { AnalysisResult } from '../types'
import { RiskBadge } from './RiskBadge'
import { IndicatorCard } from './IndicatorCard'
import { MetadataTable } from './MetadataTable'

const METADATA_PAGE_SIZE = 4

interface AnalysisPanelProps {
  result: AnalysisResult
  onReanalyze: () => void
  analyzing: boolean
}

export function AnalysisPanel({ result, onReanalyze, analyzing }: AnalysisPanelProps) {
  const [metaPage, setMetaPage] = useState(1)
  const [showAllIndicators, setShowAllIndicators] = useState(false)

  const totalMetaPages = Math.ceil(result.metadata_entries.length / METADATA_PAGE_SIZE)
  const pagedEntries = result.metadata_entries.slice(
    (metaPage - 1) * METADATA_PAGE_SIZE,
    metaPage * METADATA_PAGE_SIZE,
  )

  const highIndicators = result.indicators.filter((i) => i.severity === 'high')
  const otherIndicators = result.indicators.filter((i) => i.severity !== 'high')
  const visibleOthers = showAllIndicators ? otherIndicators : otherIndicators.slice(0, 2)

  const scoreColor =
    result.fraud_score >= 60
      ? 'text-red-600'
      : result.fraud_score >= 30
      ? 'text-yellow-600'
      : result.fraud_score >= 10
      ? 'text-blue-600'
      : 'text-green-600'

  const scoreBarColor =
    result.fraud_score >= 60
      ? 'bg-red-600'
      : result.fraud_score >= 30
      ? 'bg-yellow-500'
      : result.fraud_score >= 10
      ? 'bg-blue-500'
      : 'bg-green-500'

  return (
    <div className="flex flex-col gap-3 h-full overflow-y-auto pb-6">
      {/* Header summary card */}
      <div className="bg-white rounded border border-[#e0e0e0] p-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#C8102E] flex items-center justify-center flex-shrink-0">
              <Shield size={16} className="text-white" />
            </div>
            <div>
              <p className="text-xs text-[#888888]">Document</p>
              <p className="text-sm font-semibold text-[#333333] truncate max-w-[180px]">{result.filename}</p>
            </div>
          </div>
          <button
            onClick={onReanalyze}
            disabled={analyzing}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-[#e0e0e0] bg-white hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={analyzing ? 'animate-spin' : ''} />
            Re-analyse
          </button>
        </div>

        <div className="flex items-center gap-3 mb-3">
          <RiskBadge severity={result.overall_risk} />
          <span className={`text-2xl font-bold ${scoreColor}`}>{result.fraud_score.toFixed(0)}</span>
          <span className="text-xs text-[#888888]">/ 100 risk score</span>
        </div>

        <div className="w-full h-1.5 bg-[#f0f0f0] rounded-full overflow-hidden mb-3">
          <div
            className={`h-full rounded-full transition-all ${scoreBarColor}`}
            style={{ width: `${result.fraud_score}%` }}
          />
        </div>

        <p className="text-xs text-[#555555] leading-relaxed">{result.summary}</p>
      </div>

      {/* Determining Indicator — main threat */}
      {highIndicators.length > 0 && (
        <div className="bg-white rounded border border-[#e0e0e0] p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={14} className="text-red-600" />
            <h3 className="text-sm font-semibold text-[#333333]">Determining Indicator</h3>
            <span className="ml-auto text-xs px-2 py-0.5 bg-red-50 text-red-600 rounded font-medium border border-red-200">
              {highIndicators.length} High Risk
            </span>
          </div>
          <div className="space-y-2">
            {highIndicators.map((ind) => (
              <IndicatorCard key={ind.id} indicator={ind} />
            ))}
          </div>
        </div>
      )}

      {/* Other indicators */}
      {otherIndicators.length > 0 && (
        <div className="bg-white rounded border border-[#e0e0e0] p-4">
          <h3 className="text-sm font-semibold text-[#333333] mb-3">Additional Indicators</h3>
          <div className="space-y-2">
            {visibleOthers.map((ind) => (
              <IndicatorCard key={ind.id} indicator={ind} />
            ))}
          </div>
          {otherIndicators.length > 2 && (
            <button
              onClick={() => setShowAllIndicators((v) => !v)}
              className="mt-3 flex items-center gap-1 text-xs text-[#C8102E] hover:text-[#a50d26] font-medium transition-colors"
            >
              <ChevronDown
                size={13}
                className={`transition-transform ${showAllIndicators ? 'rotate-180' : ''}`}
              />
              {showAllIndicators
                ? 'Show less'
                : `Show ${otherIndicators.length - 2} more indicators`}
            </button>
          )}
        </div>
      )}

      {result.indicators.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded p-4 text-center">
          <p className="text-sm font-medium text-green-700">No fraud indicators detected</p>
          <p className="text-xs text-green-600 mt-1">This document appears to be authentic</p>
        </div>
      )}

      {/* Metadata Table */}
      {result.metadata_entries.length > 0 && (
        <MetadataTable
          entries={pagedEntries}
          currentPage={metaPage}
          totalPages={totalMetaPages}
          onPageChange={setMetaPage}
        />
      )}

      {/* Doc info footer */}
      <div className="grid grid-cols-2 gap-2">
        <InfoTile label="Pages" value={String(result.page_count)} />
        <InfoTile label="File Size" value={formatBytes(result.metadata.file_size)} />
        <InfoTile label="Encrypted" value={result.metadata.is_encrypted ? 'Yes' : 'No'} />
        <InfoTile label="Digital Sig." value={result.metadata.has_digital_signature ? 'Present' : 'None'} />
      </div>
    </div>
  )
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded border border-[#e0e0e0] px-3 py-2.5">
      <p className="text-[10px] text-[#888888] uppercase tracking-wider">{label}</p>
      <p className="text-sm font-semibold text-[#333333] mt-0.5">{value}</p>
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
