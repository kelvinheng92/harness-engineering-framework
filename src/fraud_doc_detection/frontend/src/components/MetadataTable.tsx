import { Check, X, AlertCircle, MinusCircle } from 'lucide-react'
import type { MetadataEntry } from '../types'

const StatusIcon = ({ status }: { status: MetadataEntry['status'] }) => {
  switch (status) {
    case 'match':
      return <Check size={13} className="text-green-600" />
    case 'mismatch':
      return <X size={13} className="text-red-600" />
    case 'suspicious':
      return <AlertCircle size={13} className="text-yellow-600" />
    case 'missing':
      return <MinusCircle size={13} className="text-[#aaaaaa]" />
    case 'annotation':
      return (
        <span className="text-[11px] px-1.5 py-0.5 bg-[#eef2ff] text-[#4f6bed] rounded font-medium border border-[#c7d2fe]">
          Info
        </span>
      )
  }
}

interface MetadataTableProps {
  entries: MetadataEntry[]
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export function MetadataTable({ entries, currentPage, totalPages, onPageChange }: MetadataTableProps) {
  return (
    <div className="bg-white rounded border border-[#e0e0e0] overflow-hidden">
      <div className="px-4 py-3 border-b border-[#e0e0e0] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[#333333]">Metadata</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="w-6 h-6 rounded border border-[#e0e0e0] flex items-center justify-center text-[#555555] hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-30 transition-colors text-xs"
          >
            {'<'}
          </button>
          <span className="text-xs text-[#666666] font-medium">
            {currentPage} / {totalPages}
          </span>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="w-6 h-6 rounded border border-[#e0e0e0] flex items-center justify-center text-[#555555] hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-30 transition-colors text-xs"
          >
            {'>'}
          </button>
        </div>
      </div>

      <table className="w-full text-xs table-fixed">
        <colgroup>
          <col style={{ width: '38%' }} />
          <col style={{ width: '46%' }} />
          <col style={{ width: '16%' }} />
        </colgroup>
        <thead>
          <tr className="bg-[#f5f5f5]">
            <th className="text-left px-4 py-2.5 font-semibold text-[#555555] border-b border-[#e0e0e0]">
              Field
            </th>
            <th className="text-left px-4 py-2.5 font-semibold text-[#555555] border-b border-[#e0e0e0]">
              Value
            </th>
            <th className="text-left px-4 py-2.5 font-semibold text-[#555555] border-b border-[#e0e0e0]">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, i) => (
            <tr
              key={i}
              className={`border-t border-[#f0f0f0] ${i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'}`}
            >
              <td className="px-4 py-2.5 align-top">
                <p className="font-medium text-[#333333] break-words">{entry.field}</p>
                {entry.original_text && (
                  <p className="text-[#888888] break-words mt-0.5">{entry.original_text}</p>
                )}
              </td>
              <td className="px-4 py-2.5 text-[#666666] align-top break-words">
                {entry.new_text || <span className="text-[#cccccc]">—</span>}
              </td>
              <td className="px-4 py-2.5 align-top">
                <StatusIcon status={entry.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
