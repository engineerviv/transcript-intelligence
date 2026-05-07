import { useAggregated } from '@/hooks/useAggregated'
import { Spinner } from '@/components/ui/Spinner'
import { SENTIMENT_COLORS } from '@/lib/utils'
import type { ExecutiveInsights, AggregatedStats } from '@/types'

const INSIGHT_CONFIG: Array<{
  key: keyof ExecutiveInsights
  label: string
  icon: string
  accent: string
  bg: string
}> = [
  { key: 'key_insights',         label: 'Key Insights',          icon: '💡', accent: 'border-blue-500',   bg: 'bg-blue-500/10'  },
  { key: 'operational_risks',    label: 'Operational Risks',     icon: '⚠️', accent: 'border-amber-500',  bg: 'bg-amber-500/10' },
  { key: 'churn_indicators',     label: 'Churn Indicators',      icon: '📉', accent: 'border-red-500',    bg: 'bg-red-500/10'   },
  { key: 'customer_pain_points', label: 'Customer Pain Points',  icon: '🎯', accent: 'border-purple-500', bg: 'bg-purple-500/10'},
  { key: 'recommendations',      label: 'Recommendations',       icon: '✅', accent: 'border-green-500',  bg: 'bg-green-500/10' },
]

function InsightCard({
  label, icon, accent, bg, items,
}: { label: string; icon: string; accent: string; bg: string; items: string[] }) {
  return (
    <div className={`bg-surface rounded-xl border border-border border-l-2 ${accent} p-5 flex flex-col gap-3`}>
      <div className="flex items-center gap-2">
        <span className="text-base">{icon}</span>
        <h3 className="text-sm font-semibold text-slate-200">{label}</h3>
        <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${bg} text-slate-300`}>
          {items.length}
        </span>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2.5 text-xs text-slate-300 leading-relaxed">
            <span className="text-slate-500 shrink-0 mt-0.5">{i + 1}.</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// Call-type × sentiment heatmap
function SentimentHeatmap({ data }: { data: AggregatedStats['sentiment_by_call_type'] }) {
  const callTypes = Object.keys(data)
  const sentiments = ['positive', 'neutral', 'mixed', 'negative'] as const

  const allValues = callTypes.flatMap(ct =>
    sentiments.map(s => data[ct]?.[s] ?? 0)
  )
  const maxVal = Math.max(...allValues, 1)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="pb-3 pr-3 text-left text-muted font-medium w-24">Call Type</th>
            {sentiments.map(s => (
              <th key={s} className="pb-3 px-2 text-center text-muted font-medium capitalize">{s}</th>
            ))}
          </tr>
        </thead>
        <tbody className="space-y-1">
          {callTypes.map(ct => (
            <tr key={ct}>
              <td className="py-1 pr-3 text-slate-400 capitalize font-medium">{ct}</td>
              {sentiments.map(s => {
                const val = data[ct]?.[s] ?? 0
                const intensity = val / maxVal
                const color = SENTIMENT_COLORS[s]
                return (
                  <td key={s} className="py-1 px-2 text-center">
                    <div
                      className="mx-auto flex items-center justify-center rounded-md h-10 w-14 font-semibold text-sm transition-all"
                      style={{
                        backgroundColor: val > 0
                          ? `${color}${Math.round(intensity * 200 + 30).toString(16).padStart(2,'0')}`
                          : '#1e293b',
                        color: intensity > 0.5 ? '#f1f5f9' : '#94a3b8',
                      }}
                      title={`${ct} · ${s}: ${val} calls`}
                    >
                      {val > 0 ? val : '—'}
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 flex-wrap">
        {sentiments.map(s => (
          <div key={s} className="flex items-center gap-1.5">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: SENTIMENT_COLORS[s] }}
            />
            <span className="text-xs text-muted capitalize">{s}</span>
          </div>
        ))}
        <span className="text-xs text-muted ml-auto">Cell color intensity = relative volume</span>
      </div>
    </div>
  )
}

// Intent + emotion distribution charts
function DistributionList({
  data, colorFn,
}: { data: Record<string, number>; colorFn?: (k: string) => string }) {
  const entries = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
  const max = entries[0]?.[1] ?? 1

  return (
    <div className="space-y-2">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-3">
          <span className="text-xs text-slate-400 w-36 truncate capitalize">{k.replace(/_/g,' ')}</span>
          <div className="flex-1 h-2 bg-slate-700/50 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${(v / max) * 100}%`,
                backgroundColor: colorFn ? colorFn(k) : '#3b82f6',
              }}
            />
          </div>
          <span className="text-xs text-muted w-8 text-right">{v}</span>
        </div>
      ))}
    </div>
  )
}

const EMOTION_COLORS: Record<string, string> = {
  frustrated: '#ef4444', satisfied: '#22c55e', neutral: '#64748b',
  anxious: '#f97316', confused: '#a78bfa', happy: '#34d399',
  disappointed: '#f43f5e', concerned: '#fb923c',
}

export function Insights() {
  const { data: agg, isLoading } = useAggregated()

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <Spinner className="w-8 h-8" />
    </div>
  )
  if (!agg) return <p className="text-muted text-sm">No data available. Run the pipeline first.</p>

  const insights = agg.executive_insights

  return (
    <div className="space-y-6">
      {/* Top 2 cards wide */}
      <div className="grid grid-cols-2 gap-4">
        {INSIGHT_CONFIG.slice(0, 2).map(cfg => (
          <InsightCard
            key={cfg.key as string}
            label={cfg.label}
            icon={cfg.icon}
            accent={cfg.accent}
            bg={cfg.bg}
            items={insights[cfg.key] ?? []}
          />
        ))}
      </div>

      {/* Middle 3 equal */}
      <div className="grid grid-cols-3 gap-4">
        {INSIGHT_CONFIG.slice(2).map(cfg => (
          <InsightCard
            key={cfg.key as string}
            label={cfg.label}
            icon={cfg.icon}
            accent={cfg.accent}
            bg={cfg.bg}
            items={insights[cfg.key] ?? []}
          />
        ))}
      </div>

      {/* Heatmap + distributions */}
      <div className="grid grid-cols-5 gap-4">
        {/* Heatmap spans 3 */}
        <div className="col-span-3 bg-surface rounded-xl border border-border p-5">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-slate-200">Call Type × Sentiment Heatmap</h2>
            <p className="text-xs text-muted mt-0.5">Volume of calls per sentiment, broken down by call type</p>
          </div>
          <SentimentHeatmap data={agg.sentiment_by_call_type} />
        </div>

        {/* Intent + Emotion distributions span 2 */}
        <div className="col-span-2 space-y-4">
          <div className="bg-surface rounded-xl border border-border p-5">
            <h2 className="text-sm font-semibold text-slate-200 mb-3">Intent Distribution</h2>
            <DistributionList data={agg.intent_distribution} />
          </div>
          <div className="bg-surface rounded-xl border border-border p-5">
            <h2 className="text-sm font-semibold text-slate-200 mb-3">Emotion Distribution</h2>
            <DistributionList
              data={agg.emotion_distribution}
              colorFn={k => EMOTION_COLORS[k] ?? '#3b82f6'}
            />
          </div>
        </div>
      </div>

      {/* High urgency topics */}
      {agg.high_urgency_topics?.length > 0 && (
        <div className="bg-surface rounded-xl border border-border p-5">
          <h2 className="text-sm font-semibold text-slate-200 mb-1">High-Urgency Topics</h2>
          <p className="text-xs text-muted mb-4">Topics most commonly flagged as high or critical urgency</p>
          <div className="flex flex-wrap gap-2">
            {agg.high_urgency_topics.slice(0, 12).map((t: { topic: string; count: number }, i: number) => (
              <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-950/40 border border-red-800/30">
                <span className="text-xs text-red-300 font-medium">{t.topic}</span>
                <span className="text-xs text-red-500">{t.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
