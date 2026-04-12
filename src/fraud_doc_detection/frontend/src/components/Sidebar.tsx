import { Home, FileText, Settings, HelpCircle, Trash2 } from 'lucide-react'
import type { DocumentListItem } from '../types'

type Page = 'main' | 'settings'

interface SidebarProps {
  documents: DocumentListItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  activePage: Page
  onNavigate: (page: Page) => void
}

const riskDot: Record<string, string> = {
  high: 'bg-red-600',
  medium: 'bg-yellow-500',
  low: 'bg-blue-500',
  safe: 'bg-green-500',
}

export function Sidebar({ documents, selectedId, onSelect, onDelete, activePage, onNavigate }: SidebarProps) {
  return (
    <aside className="w-56 bg-white flex flex-col h-full flex-shrink-0 border-r border-[#e0e0e0]">
      {/* Logo */}
      <div className="px-5 py-4 border-b border-[#e0e0e0]">
        <div className="flex items-center gap-2">
          {/* OCBC-style logo mark */}
          <div className="w-8 h-8 rounded-full bg-[#C8102E] flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-[10px] tracking-tight leading-none">FS</span>
          </div>
          <div>
            <p className="text-[#C8102E] font-bold text-sm leading-none tracking-tight">FraudShield</p>
            <p className="text-[#666666] text-[10px] leading-none mt-0.5">Document Intelligence</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <NavItem
          icon={<Home size={14} />}
          label="Dashboard"
          active={activePage === 'main'}
          onClick={() => onNavigate('main')}
        />

        <div className="mt-5 mb-2 px-2">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-[#999999]">
            Applications
          </span>
        </div>

        {documents.length === 0 && (
          <p className="px-2 py-2 text-xs text-[#999999] italic">No documents yet</p>
        )}

        {documents.map((doc) => (
          <div
            key={doc.document_id}
            className={`flex items-center gap-1 rounded mb-0.5 group border-l-2 transition-all ${
              selectedId === doc.document_id
                ? 'bg-[#fbeaed] border-[#C8102E]'
                : 'border-transparent hover:bg-[#f5f5f5]'
            }`}
          >
            <button
              onClick={() => onSelect(doc.document_id)}
              className={`flex-1 flex items-center gap-2 px-2 py-2 text-left min-w-0 ${
                selectedId === doc.document_id ? 'text-[#C8102E]' : 'text-[#555555] group-hover:text-[#333333]'
              }`}
            >
              <FileText size={13} className="flex-shrink-0" />
              <span className="flex-1 text-xs truncate">{doc.filename}</span>
              {doc.overall_risk && (
                <span
                  className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${riskDot[doc.overall_risk] || 'bg-gray-400'}`}
                />
              )}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(doc.document_id) }}
              className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-600 text-[#aaaaaa] transition-all mr-1"
              title="Delete"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-3 py-3 border-t border-[#e0e0e0] space-y-0.5">
        <NavItem
          icon={<Settings size={14} />}
          label="Settings"
          active={activePage === 'settings'}
          onClick={() => onNavigate('settings')}
        />
        <NavItem icon={<HelpCircle size={14} />} label="Help" />
      </div>
    </aside>
  )
}

function NavItem({
  icon,
  label,
  active = false,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  active?: boolean
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-2 py-2 rounded text-left transition-all border-l-2 ${
        active
          ? 'bg-[#fbeaed] text-[#C8102E] border-[#C8102E]'
          : 'text-[#555555] hover:bg-[#f5f5f5] hover:text-[#333333] border-transparent'
      }`}
    >
      {icon}
      <span className="flex-1 text-xs font-medium">{label}</span>
    </button>
  )
}
