import { useState } from 'react'
import { Table2, Loader2, RefreshCw, Plus, X } from 'lucide-react'
import type { KVExtractionResult, DocumentType, KeyValuePair } from '../types'

interface KVPanelProps {
  documentId: string
  documentType: DocumentType
  result: KVExtractionResult | null
  loading: boolean
  error: string | null
  onExtract: (keys: string[]) => void
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

const SUGGESTED_KEYS: Record<DocumentType, string[]> = {
  bank_statement: ['Account Holder', 'Opening Balance', 'Closing Balance', 'Total Credits', 'Total Debits', 'Statement Period'],
  income_tax: ['Assessable Income', 'Tax Payable', 'Tax Relief', 'Chargeable Income', 'Filing Date', 'NOA Year'],
  payslip: ['Gross Salary', 'Net Pay', 'CPF Employee', 'CPF Employer', 'Total Allowances', 'Total Deductions'],
  cpf_statement: ['Ordinary Account', 'Special Account', 'Medisave Account', 'Total Balance', 'Contribution Period'],
  investment_statement: ['Portfolio Value', 'Total Returns', 'Unrealised P&L', 'Realised P&L', 'Dividend Income'],
  credit_report: ['Credit Score', 'Total Outstanding', 'Monthly Repayment', 'Credit Utilisation', 'Defaults'],
  annual_report: ['Revenue', 'Net Profit', 'Total Assets', 'Total Liabilities', 'EBITDA', 'EPS'],
  financial_statement: ['Revenue', 'Net Profit', 'Total Assets', 'Total Liabilities', 'Cash Flow'],
  other: ['Total Amount', 'Issue Date', 'Reference Number', 'Account Holder', 'Balance'],
}

const TX_COLS = ['Date', 'Description', 'Debit', 'Credit', 'Balance']

function parseTransactionRow(value: string): string[] {
  const parts = value.split('|').map(s => s.trim())
  while (parts.length < 5) parts.push('')
  return parts.slice(0, 5)
}

/**
 * Detect whether pairs follow a repeating field-group pattern.
 * Returns the ordered column names if detected, otherwise [].
 * Example: [TX date, Posting date, Description, Amount, TX date, ...] → 4 columns.
 */
function detectFieldCycle(pairs: KeyValuePair[]): string[] {
  if (pairs.length < 2) return []
  const firstKey = pairs[0].key
  for (let i = 1; i < pairs.length && i < 12; i++) {
    if (pairs[i].key === firstKey) {
      return pairs.slice(0, i).map(p => p.key)
    }
  }
  return []
}

function groupByFieldCycle(pairs: KeyValuePair[], fields: string[]): Record<string, string>[] {
  const rows: Record<string, string>[] = []
  const n = fields.length
  for (let i = 0; i + n <= pairs.length; i += n) {
    const row: Record<string, string> = {}
    for (let j = 0; j < n; j++) {
      row[fields[j]] = pairs[i + j].value
    }
    rows.push(row)
  }
  return rows
}

function amountClass(value: string): string {
  if (value.startsWith('+')) return 'text-green-700 font-medium'
  if (value.startsWith('-')) return 'text-red-600 font-medium'
  return 'text-[#333333]'
}

function isAmountKey(key: string): boolean {
  const k = key.toLowerCase()
  return k.includes('amount') || k.includes('debit') || k.includes('credit') || k.includes('balance')
}

function isDescriptionKey(key: string): boolean {
  return key.toLowerCase().includes('description')
}

function TransactionTable({ cat, pairs }: { cat: string; pairs: KeyValuePair[] }) {
  const isPiped = pairs.some(p => p.value.includes('|'))
  const fieldCycle = !isPiped ? detectFieldCycle(pairs) : []
  const isGrouped = fieldCycle.length > 0
  const rowCount = isGrouped
    ? Math.floor(pairs.length / fieldCycle.length)
    : pairs.length

  return (
    <div className="bg-white rounded border border-[#e0e0e0]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#f0f0f0]">
        <span className="text-sm font-semibold text-[#333333]">{cat}</span>
        <span className="text-xs text-[#888888]">{rowCount} rows</span>
      </div>

      {/* ── Grouped columnar table (repeating field cycle) ── */}
      {isGrouped && (() => {
        const rows = groupByFieldCycle(pairs, fieldCycle)
        return (
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-[#fafafa] border-b border-[#f0f0f0]">
                  {fieldCycle.map(col => (
                    <th
                      key={col}
                      className="px-3 py-2 text-left text-[10px] font-semibold text-[#888888] uppercase tracking-wider whitespace-nowrap"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr
                    key={i}
                    className={`border-b border-[#f5f5f5] last:border-0 ${i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'}`}
                  >
                    {fieldCycle.map(col => {
                      const val = row[col] ?? ''
                      const isDesc = isDescriptionKey(col)
                      const isAmt = isAmountKey(col)
                      return (
                        <td
                          key={col}
                          className={`px-3 py-2 whitespace-nowrap ${isDesc ? 'max-w-[220px] truncate' : ''} ${isAmt ? amountClass(val) : 'text-[#333333]'}`}
                          title={isDesc ? val : undefined}
                        >
                          {val || <span className="text-[#cccccc]">—</span>}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      })()}

      {/* ── Pipe-delimited table (legacy format) ── */}
      {isPiped && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-[#fafafa] border-b border-[#f0f0f0]">
                {TX_COLS.map(col => (
                  <th
                    key={col}
                    className="px-3 py-2 text-left text-[10px] font-semibold text-[#888888] uppercase tracking-wider whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pairs.map((pair, i) => {
                const cols = parseTransactionRow(pair.value)
                return (
                  <tr
                    key={i}
                    className={`border-b border-[#f5f5f5] last:border-0 ${i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'}`}
                  >
                    {cols.map((col, j) => (
                      <td
                        key={j}
                        className={`px-3 py-2 text-[#333333] whitespace-nowrap ${
                          j === 1 ? 'max-w-[200px] truncate' : ''
                        } ${
                          j === 2 && col ? 'text-red-600 font-medium' :
                          j === 3 && col ? 'text-green-700 font-medium' : ''
                        }`}
                        title={j === 1 ? col : undefined}
                      >
                        {col || <span className="text-[#cccccc]">—</span>}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Fallback: plain key-value rows ── */}
      {!isPiped && !isGrouped && pairs.map((pair, i) => (
        <div
          key={i}
          className={`flex items-start gap-3 px-4 py-2.5 ${i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'}`}
        >
          <span className="text-xs text-[#888888] w-36 flex-shrink-0 pt-0.5">{pair.key}</span>
          <span className="text-xs font-medium text-[#333333] break-words flex-1">{pair.value}</span>
        </div>
      ))}
    </div>
  )
}

export function KVPanel({ documentType, result, loading, error, onExtract }: KVPanelProps) {
  const [inputValue, setInputValue] = useState('')
  const [additionalKeys, setAdditionalKeys] = useState<string[]>([])

  const suggestions = SUGGESTED_KEYS[documentType] ?? []

  function addKey(key: string) {
    const trimmed = key.trim()
    if (trimmed && !additionalKeys.includes(trimmed)) {
      setAdditionalKeys(prev => [...prev, trimmed])
    }
    if (key === inputValue) setInputValue('')
  }

  function removeKey(key: string) {
    setAdditionalKeys(prev => prev.filter(k => k !== key))
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') { e.preventDefault(); addKey(inputValue) }
  }

  function handleExtract() {
    onExtract(additionalKeys)
  }

  const grouped = result
    ? result.pairs.reduce<Record<string, typeof result.pairs>>((acc, pair) => {
        const cat = pair.category || 'General'
        if (cat.toLowerCase() === 'footer') return acc
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
          <p className="text-xs text-[#888888] mt-1">AI is reading the document</p>
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
            onClick={handleExtract}
            className="mt-3 text-xs px-3 py-1.5 rounded border border-red-300 text-red-700 hover:bg-red-100 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  /* ── Empty state ─────────────────────────────────────────── */
  if (!result) {
    return (
      <div className="flex flex-col gap-3">
        <div className="bg-white rounded border border-[#e0e0e0] p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-full bg-[#f0f0f0] flex items-center justify-center">
              <Table2 size={18} className="text-[#aaaaaa]" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#333333]">Extract Key Values</p>
              <p className="text-xs text-[#888888]">AI will extract structured fields from this {DOC_TYPE_LABEL[documentType]}</p>
            </div>
          </div>

          {/* Suggestions */}
          <div className="mb-4">
            <p className="text-xs text-[#888888] mb-2">Suggested fields to extract</p>
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map(s => {
                const active = additionalKeys.includes(s)
                return (
                  <button
                    key={s}
                    onClick={() => active ? removeKey(s) : addKey(s)}
                    className={`text-xs px-2.5 py-1 rounded border transition-colors ${
                      active
                        ? 'bg-[#C8102E] text-white border-[#C8102E]'
                        : 'bg-white text-[#555555] border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E]'
                    }`}
                  >
                    {s}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Custom key input */}
          <p className="text-xs text-[#888888] mb-2">Or add your own fields</p>
          <div className="flex gap-1.5 mb-3">
            <input
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. Net Income"
              className="flex-1 text-xs px-2.5 py-1.5 rounded border border-[#e0e0e0] focus:outline-none focus:border-[#C8102E] text-[#333333] placeholder-[#bbbbbb]"
            />
            <button
              onClick={() => addKey(inputValue)}
              disabled={!inputValue.trim()}
              className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded border border-[#e0e0e0] text-[#555555] hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Plus size={11} />
              Add
            </button>
          </div>

          {additionalKeys.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {additionalKeys.map(k => (
                <span key={k} className="flex items-center gap-1 text-xs bg-[#fff0f2] text-[#C8102E] border border-[#f5c0c8] rounded px-2 py-0.5">
                  {k}
                  <button onClick={() => removeKey(k)} className="hover:opacity-70"><X size={10} /></button>
                </span>
              ))}
            </div>
          )}

          <button
            onClick={handleExtract}
            className="w-full py-2 bg-[#C8102E] text-white text-sm rounded hover:bg-[#a50d26] transition-colors font-medium"
          >
            Extract Now
          </button>
        </div>
      </div>
    )
  }

  /* ── Results state ───────────────────────────────────────── */
  const categories = Object.keys(grouped)

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="bg-white rounded border border-[#e0e0e0] p-4">
        <div className="flex items-center justify-between mb-2">
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
            onClick={handleExtract}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-[#e0e0e0] bg-white hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors"
          >
            <RefreshCw size={12} />
            Re-extract
          </button>
        </div>
        <p className="text-xs text-[#888888]">
          {result.pairs.length} fields · {categories.length} categories
        </p>
      </div>

      {/* Re-extract with specific fields */}
      <div className="bg-white rounded border border-[#e0e0e0] p-4">
        <p className="text-xs font-medium text-[#333333] mb-2">Suggested fields</p>
        <div className="flex flex-wrap gap-1.5 mb-3">
          {suggestions.map(s => {
            const active = additionalKeys.includes(s)
            return (
              <button
                key={s}
                onClick={() => active ? removeKey(s) : addKey(s)}
                className={`text-xs px-2.5 py-1 rounded border transition-colors ${
                  active
                    ? 'bg-[#C8102E] text-white border-[#C8102E]'
                    : 'bg-white text-[#555555] border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E]'
                }`}
              >
                {s}
              </button>
            )
          })}
        </div>
        <div className="flex gap-1.5">
          <input
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Custom field (press Enter)"
            className="flex-1 text-xs px-2.5 py-1.5 rounded border border-[#e0e0e0] focus:outline-none focus:border-[#C8102E] text-[#333333] placeholder-[#bbbbbb]"
          />
          <button
            onClick={() => addKey(inputValue)}
            disabled={!inputValue.trim()}
            className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded border border-[#e0e0e0] text-[#555555] hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Plus size={11} />
            Add
          </button>
        </div>
        {additionalKeys.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {additionalKeys.map(k => (
              <span key={k} className="flex items-center gap-1 text-xs bg-[#fff0f2] text-[#C8102E] border border-[#f5c0c8] rounded px-2 py-0.5">
                {k}
                <button onClick={() => removeKey(k)} className="hover:opacity-70"><X size={10} /></button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Category tables */}
      {categories.map((cat) => {
        const pairs = grouped[cat]
        const isTransactions = cat.toLowerCase().includes('transaction')

        if (isTransactions) {
          return <TransactionTable key={cat} cat={cat} pairs={pairs} />
        }

        return (
          <div key={cat} className="bg-white rounded border border-[#e0e0e0]">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#f0f0f0]">
              <span className="text-sm font-semibold text-[#333333]">{cat}</span>
              <span className="text-xs text-[#888888]">{pairs.length} fields</span>
            </div>
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
        )
      })}
    </div>
  )
}
