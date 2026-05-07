import { useState } from 'react'
import { Search, Download, ChevronRight, X } from 'lucide-react'
import { useTranscripts, useTranscript } from '@/hooks/useTranscripts'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { SENTIMENT_BG, URGENCY_BG, CHURN_BG, formatDuration, formatDate } from '@/lib/utils'
import type { Transcript } from '@/types'

function TranscriptRow({ t, selected, onClick }: {
  t: Transcript; selected: boolean; onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-border/50 transition-colors hover:bg-white/3
        ${selected ? 'bg-blue-950/30 border-l-2 border-l-blue-500' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate">{t.title}</p>
          <p className="text-xs text-muted mt-0.5 truncate">{t.summary?.slice(0, 90)}…</p>
        </div>
        <ChevronRight className="w-4 h-4 text-muted shrink-0 mt-0.5" />
      </div>
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-[10px] text-muted">{formatDate(t.start_time)}</span>
        <span className="text-[10px] text-muted">{formatDuration(t.duration_minutes)}</span>
        {t.sentiment && <Badge label={t.sentiment} className={`${SENTIMENT_BG[t.sentiment]} text-[10px]`} />}
        {t.urgency   && <Badge label={t.urgency}   className={`${URGENCY_BG[t.urgency]} text-[10px]`} />}
        {t.churn_risk && t.churn_risk !== 'none' &&
          <Badge label={`churn: ${t.churn_risk}`} className={`${CHURN_BG[t.churn_risk]} text-[10px]`} />}
      </div>
    </button>
  )
}

function DetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const { data: t, isLoading } = useTranscript(id)
  const [showTranscript, setShowTranscript] = useState(false)

  if (isLoading) return (
    <div className="flex items-center justify-center h-40">
      <Spinner />
    </div>
  )
  if (!t) return null

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-surface border-b border-border px-5 py-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-100 leading-snug">{t.title}</h2>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            {t.sentiment  && <Badge label={t.sentiment}  className={SENTIMENT_BG[t.sentiment]} />}
            {t.urgency    && <Badge label={t.urgency}    className={URGENCY_BG[t.urgency]} />}
            {t.churn_risk && <Badge label={`churn: ${t.churn_risk}`} className={CHURN_BG[t.churn_risk]} />}
          </div>
        </div>
        <button onClick={onClose} className="text-muted hover:text-slate-200 shrink-0">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="px-5 py-4 space-y-5">
        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-3">
          {[
            ['Call Type', t.call_type],
            ['Duration',  formatDuration(t.duration_minutes)],
            ['Date',      formatDate(t.start_time)],
            ['Speakers',  t.num_speakers],
            ['Topic',     t.topic ?? '—'],
            ['Sub-Topic', t.sub_topic ?? '—'],
            ['Intent',    t.intent?.replace(/_/g, ' ') ?? '—'],
            ['Emotion',   t.emotion ?? '—'],
          ].map(([k, v]) => (
            <div key={k as string}>
              <p className="text-[10px] text-muted uppercase tracking-wider">{k}</p>
              <p className="text-sm text-slate-300 mt-0.5 capitalize">{v}</p>
            </div>
          ))}
        </div>

        {/* Sentiment score */}
        {t.sentiment_score != null && (
          <div>
            <p className="text-xs text-muted mb-1.5">Sentiment Score</p>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${((t.sentiment_score - 1) / 4) * 100}%`,
                    background: t.sentiment ? '#3b82f6' : '#64748b',
                  }}
                />
              </div>
              <span className="text-xs text-muted">{t.sentiment_score}/5</span>
            </div>
          </div>
        )}

        {/* Summary */}
        <div>
          <p className="text-xs text-muted mb-1">Summary</p>
          <p className="text-sm text-slate-300 leading-relaxed">{t.summary}</p>
        </div>

        {/* Key entities */}
        {t.key_entities && t.key_entities.length > 0 && (
          <div>
            <p className="text-xs text-muted mb-2">Key Entities</p>
            <div className="flex flex-wrap gap-1.5">
              {t.key_entities.map((e: string, i: number) => (
                <span key={i} className="px-2 py-0.5 rounded text-xs bg-blue-950/50 text-blue-300 border border-blue-800/40">
                  {e}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Action items */}
        {t.action_items?.length > 0 && (
          <div>
            <p className="text-xs text-muted mb-2">Action Items</p>
            <ul className="space-y-1">
              {t.action_items.map((item: string, i: number) => (
                <li key={i} className="text-xs text-slate-300 flex gap-2">
                  <span className="text-blue-400 shrink-0">→</span>{item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Key moments */}
        {t.key_moments?.length > 0 && (
          <div>
            <p className="text-xs text-muted mb-2">Key Moments</p>
            <div className="space-y-1.5">
              {t.key_moments.map((m: { type: string; text: string }, i: number) => {
                const icons: Record<string, string> = {
                  churn_signal: '⚠️', technical_issue: '🔧',
                  concern: '❗', positive_pivot: '✅',
                }
                return (
                  <div key={i} className="flex gap-2 text-xs text-slate-300">
                    <span>{icons[m.type] ?? '•'}</span>
                    <span><strong className="text-slate-200">{m.type.replace(/_/g, ' ')}:</strong> {m.text}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Full transcript */}
        <div>
          <button
            onClick={() => setShowTranscript(v => !v)}
            className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300"
          >
            <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showTranscript ? 'rotate-90' : ''}`} />
            {showTranscript ? 'Hide' : 'Show'} full transcript
          </button>
          {showTranscript && t.full_transcript && (
            <pre className="mt-3 p-3 bg-[#0f172a] rounded-lg text-xs text-slate-400 font-mono
              whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto border border-border">
              {t.full_transcript}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}

export function Explorer() {
  const [search, setSearch] = useState('')
  const [callType, setCallType] = useState('All')
  const [sentiment, setSentiment] = useState('All')
  const [urgency, setUrgency] = useState('All')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data, isLoading } = useTranscripts({
    callTypes:  callType  !== 'All' ? [callType as any] : undefined,
    sentiments: sentiment !== 'All' ? [sentiment as any] : undefined,
    urgencies:  urgency   !== 'All' ? [urgency as any] : undefined,
    search:     search || undefined,
  })

  const transcripts: Transcript[] = data?.transcripts ?? []

  function exportCsv() {
    const headers = ['id', 'title', 'call_type', 'sentiment', 'urgency', 'churn_risk', 'topic', 'summary']
    const rows = transcripts.map(t => headers.map(h => JSON.stringify((t as any)[h] ?? '')).join(','))
    const csv = [headers.join(','), ...rows].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    const a = document.createElement('a'); a.href = url; a.download = 'transcripts.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  const SelectFilter = ({ value, onChange, options }: {
    value: string; onChange: (v: string) => void; options: string[]
  }) => (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="bg-surface border border-border rounded-lg px-3 py-1.5 text-sm text-slate-300
        focus:outline-none focus:border-blue-500 cursor-pointer"
    >
      {['All', ...options].map(o => <option key={o}>{o}</option>)}
    </select>
  )

  return (
    <div className="flex gap-4 h-[calc(100vh-130px)]">
      {/* Left: list */}
      <div className="w-80 shrink-0 flex flex-col bg-surface rounded-xl border border-border overflow-hidden">
        {/* Search + filters */}
        <div className="p-3 border-b border-border space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search transcripts…"
              className="w-full bg-[#0f172a] border border-border rounded-lg pl-8 pr-3 py-1.5
                text-sm text-slate-200 placeholder:text-muted focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <SelectFilter value={callType}  onChange={setCallType}  options={['support','external','internal']} />
            <SelectFilter value={sentiment} onChange={setSentiment} options={['positive','neutral','mixed','negative']} />
            <SelectFilter value={urgency}   onChange={setUrgency}   options={['low','medium','high','critical']} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted">{data?.total ?? 0} results</span>
            <button onClick={exportCsv}
              className="flex items-center gap-1 text-xs text-muted hover:text-slate-200 transition-colors">
              <Download className="w-3 h-3" />Export CSV
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex justify-center p-8"><Spinner /></div>
          ) : transcripts.length === 0 ? (
            <p className="text-muted text-sm p-4 text-center">No transcripts match</p>
          ) : (
            transcripts.map(t => (
              <TranscriptRow
                key={t.id} t={t}
                selected={selectedId === t.id}
                onClick={() => setSelectedId(t.id === selectedId ? null : t.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Right: detail */}
      <div className="flex-1 bg-surface rounded-xl border border-border overflow-hidden">
        {selectedId ? (
          <DetailPanel id={selectedId} onClose={() => setSelectedId(null)} />
        ) : (
          <div className="flex items-center justify-center h-full text-muted text-sm">
            Select a transcript to view details
          </div>
        )}
      </div>
    </div>
  )
}
