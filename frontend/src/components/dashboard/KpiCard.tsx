import { cn } from '@/lib/utils'

interface KpiCardProps {
  value: string | number
  label: string
  sub?: string
  deltaValue?: number
  higherIsBad?: boolean
}

export function KpiCard({ value, label, sub, deltaValue, higherIsBad = false }: KpiCardProps) {
  const hasDelta = deltaValue != null && deltaValue !== 0
  const isPositive = higherIsBad ? (deltaValue ?? 0) < 0 : (deltaValue ?? 0) > 0
  const arrow = (deltaValue ?? 0) > 0 ? '↑' : '↓'
  const deltaColor = hasDelta
    ? isPositive ? 'text-green-400' : 'text-red-400'
    : 'text-muted'

  return (
    <div className="bg-surface rounded-xl border border-border p-5 text-center">
      <div className={cn(
        'font-bold text-slate-100 leading-tight break-words',
        typeof value === 'string' && value.length > 10 ? 'text-lg' : 'text-2xl',
      )}>{value}</div>
      <div className="text-[11px] text-muted uppercase tracking-wider mt-1.5">{label}</div>
      {sub && <div className="text-xs text-muted mt-0.5">{sub}</div>}
      {hasDelta && (
        <div className={cn('text-xs mt-1 font-medium', deltaColor)}>
          {arrow} {Math.abs(deltaValue!)} vs last run
        </div>
      )}
    </div>
  )
}
