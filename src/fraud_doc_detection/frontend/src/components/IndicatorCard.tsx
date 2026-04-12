import { useState } from 'react'
import { ChevronDown, ChevronUp, AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react'
import type { FraudIndicator, IndicatorSeverity } from '../types'

const severityConfig: Record<
  IndicatorSeverity,
  { icon: React.ReactNode; border: string; bg: string; title: string; badge: string; badgeText: string }
> = {
  high: {
    icon: <AlertTriangle size={15} className="text-red-600" />,
    border: 'border-red-200',
    bg: 'bg-red-50',
    title: 'text-red-800',
    badge: 'bg-red-100 text-red-700 border border-red-200',
    badgeText: 'High',
  },
  medium: {
    icon: <AlertCircle size={15} className="text-yellow-600" />,
    border: 'border-yellow-200',
    bg: 'bg-yellow-50',
    title: 'text-yellow-800',
    badge: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
    badgeText: 'Medium',
  },
  low: {
    icon: <Info size={15} className="text-blue-600" />,
    border: 'border-blue-200',
    bg: 'bg-blue-50',
    title: 'text-blue-800',
    badge: 'bg-blue-100 text-blue-700 border border-blue-200',
    badgeText: 'Low',
  },
  safe: {
    icon: <CheckCircle size={15} className="text-green-600" />,
    border: 'border-green-200',
    bg: 'bg-green-50',
    title: 'text-green-800',
    badge: 'bg-green-100 text-green-700 border border-green-200',
    badgeText: 'Safe',
  },
}

export function IndicatorCard({ indicator }: { indicator: FraudIndicator }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = severityConfig[indicator.severity]

  return (
    <div className={`border rounded overflow-hidden ${cfg.border}`}>
      <button
        className={`w-full flex items-start gap-3 p-3 text-left ${cfg.bg} hover:brightness-95 transition-all`}
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="mt-0.5 flex-shrink-0">{cfg.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-semibold ${cfg.title}`}>{indicator.title}</span>
            <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${cfg.badge}`}>
              {cfg.badgeText}
            </span>
          </div>
          <p className="text-xs text-[#555555] mt-0.5 leading-relaxed line-clamp-2">
            {indicator.description}
          </p>
        </div>
        <div className="flex-shrink-0 text-[#888888] mt-0.5">
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-3 bg-white border-t border-[#e8e8e8] space-y-2">
          <p className="text-xs text-[#555555] leading-relaxed">{indicator.description}</p>
          {indicator.details && (
            <div className="bg-[#f5f5f5] rounded p-2.5 border border-[#e0e0e0]">
              <p className="text-[11px] font-mono text-[#666666]">{indicator.details}</p>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-[#888888]">Confidence score</span>
            <div className="flex items-center gap-2">
              <div className="w-24 h-1.5 bg-[#f0f0f0] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    indicator.confidence >= 80
                      ? 'bg-red-500'
                      : indicator.confidence >= 60
                      ? 'bg-yellow-500'
                      : 'bg-blue-400'
                  }`}
                  style={{ width: `${indicator.confidence}%` }}
                />
              </div>
              <span className="text-[11px] font-medium text-[#555555]">
                {indicator.confidence.toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
