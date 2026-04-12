import type { IndicatorSeverity } from '../types'

const config: Record<IndicatorSeverity, { label: string; bg: string; text: string; border: string; dot: string }> = {
  high: {
    label: 'High Risk',
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
    dot: 'bg-red-600',
  },
  medium: {
    label: 'Medium Risk',
    bg: 'bg-yellow-50',
    text: 'text-yellow-700',
    border: 'border-yellow-200',
    dot: 'bg-yellow-500',
  },
  low: {
    label: 'Low Risk',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
    dot: 'bg-blue-500',
  },
  safe: {
    label: 'Safe',
    bg: 'bg-green-50',
    text: 'text-green-700',
    border: 'border-green-200',
    dot: 'bg-green-500',
  },
}

interface RiskBadgeProps {
  severity: IndicatorSeverity
  size?: 'sm' | 'md'
}

export function RiskBadge({ severity, size = 'md' }: RiskBadgeProps) {
  const c = config[severity]
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-medium border ${c.bg} ${c.text} ${c.border} ${
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'
      }`}
    >
      <span className={`rounded-full flex-shrink-0 ${c.dot} ${size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'}`} />
      {c.label}
    </span>
  )
}
