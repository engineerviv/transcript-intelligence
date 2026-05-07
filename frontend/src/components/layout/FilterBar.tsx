import { X } from 'lucide-react'
import { useFilters, ALL_CALL_TYPES, ALL_SENTIMENTS, ALL_URGENCIES } from '@/context/FilterContext'
import { cn } from '@/lib/utils'
import type { CallType, Sentiment, Urgency } from '@/types'

function ToggleGroup<T extends string>({
  options, selected, onChange, colorFn,
}: {
  options: T[]
  selected: T[]
  onChange: (v: T[]) => void
  colorFn?: (v: T) => string
}) {
  const toggle = (v: T) => {
    const next = selected.includes(v) ? selected.filter(x => x !== v) : [...selected, v]
    if (next.length > 0) onChange(next)
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map(v => {
        const active = selected.includes(v)
        const color = colorFn?.(v)
        return (
          <button
            key={v}
            onClick={() => toggle(v)}
            className={cn(
              'px-2.5 py-1 rounded-full text-xs font-medium border transition-all',
              active
                ? 'border-transparent text-white'
                : 'border-border text-muted hover:border-slate-500 hover:text-slate-300',
            )}
            style={active && color ? { background: color + '33', borderColor: color + '66', color } : undefined}
          >
            {v}
          </button>
        )
      })}
    </div>
  )
}

export function FilterBar() {
  const { filters, setFilters, resetFilters, isDefault } = useFilters()

  const SENTIMENT_COLORS: Record<string, string> = {
    positive: '#22c55e', neutral: '#94a3b8', mixed: '#f59e0b', negative: '#ef4444',
  }
  const URGENCY_COLORS: Record<string, string> = {
    low: '#22c55e', medium: '#f59e0b', high: '#f97316', critical: '#dc2626',
  }
  const CT_COLORS: Record<string, string> = {
    support: '#3b82f6', external: '#a855f7', internal: '#64748b',
  }

  return (
    <div className="flex items-center gap-6 flex-wrap">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted uppercase tracking-wider w-16 shrink-0">Type</span>
        <ToggleGroup<CallType>
          options={ALL_CALL_TYPES}
          selected={filters.callTypes}
          onChange={v => setFilters({ callTypes: v })}
          colorFn={v => CT_COLORS[v]}
        />
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted uppercase tracking-wider w-16 shrink-0">Sentiment</span>
        <ToggleGroup<Sentiment>
          options={ALL_SENTIMENTS}
          selected={filters.sentiments}
          onChange={v => setFilters({ sentiments: v })}
          colorFn={v => SENTIMENT_COLORS[v]}
        />
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted uppercase tracking-wider w-16 shrink-0">Urgency</span>
        <ToggleGroup<Urgency>
          options={ALL_URGENCIES}
          selected={filters.urgencies}
          onChange={v => setFilters({ urgencies: v })}
          colorFn={v => URGENCY_COLORS[v]}
        />
      </div>
      {!isDefault && (
        <button
          onClick={resetFilters}
          className="flex items-center gap-1 text-xs text-muted hover:text-slate-200 transition-colors ml-auto"
        >
          <X className="w-3 h-3" />
          Reset
        </button>
      )}
    </div>
  )
}
