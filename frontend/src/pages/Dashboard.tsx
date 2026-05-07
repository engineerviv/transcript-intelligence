import { useState } from 'react'
import { useAggregated } from '@/hooks/useAggregated'
import { useTranscripts } from '@/hooks/useTranscripts'
import { KpiCard } from '@/components/dashboard/KpiCard'
import {
  TopicsChart, SentimentPie, SentimentByTypeChart,
  UrgencyChart, ChurnRiskChart, NegativeTopicsChart, TimelineChart,
} from '@/components/dashboard/Charts'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { SENTIMENT_BG, URGENCY_BG, CHURN_BG } from '@/lib/utils'
import type { AtRiskAccount } from '@/types'

function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
      {sub && <p className="text-xs text-muted mt-0.5">{sub}</p>}
    </div>
  )
}

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-surface rounded-xl border border-border p-5 ${className ?? ''}`}>
      {children}
    </div>
  )
}

export function Dashboard() {
  const { data: agg, isLoading: aggLoading } = useAggregated()
  const { data: txData, isLoading: txLoading } = useTranscripts()
  const [selectedAccount, setSelectedAccount] = useState<AtRiskAccount | null>(null)

  if (aggLoading || txLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="w-8 h-8" />
      </div>
    )
  }

  if (!agg) return <p className="text-muted text-sm">No data available. Run the pipeline first.</p>

  const transcripts = txData?.transcripts ?? []
  const total = txData?.total ?? 0

  // KPI values — derived from filtered transcripts so they update with filters
  const negPct = Math.round(
    transcripts.filter(t => t.sentiment === 'negative' || t.sentiment === 'mixed').length
    / Math.max(total, 1) * 100
  )
  const highUrg = transcripts.filter(t => t.urgency === 'high' || t.urgency === 'critical').length
  const topicCounts = transcripts.reduce<Record<string, number>>((acc, t) => {
    if (t.topic) acc[t.topic] = (acc[t.topic] ?? 0) + 1
    return acc
  }, {})
  const topTopic = Object.entries(topicCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'N/A'
  const atRiskCount = transcripts.filter(t => t.churn_risk === 'high').length

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid grid-cols-5 gap-4">
        <KpiCard value={total}      label="Transcripts"        sub="filtered" />
        <KpiCard value={topTopic}   label="Top Issue Category" />
        <KpiCard value={`${negPct}%`} label="Negative / Mixed" higherIsBad />
        <KpiCard value={highUrg}    label="High Urgency Calls"  higherIsBad />
        <KpiCard value={atRiskCount} label="At-Risk Accounts"   higherIsBad />
      </div>

      {/* Row 1: Topics + Sentiment */}
      <div className="grid grid-cols-5 gap-4">
        <Card className="col-span-3">
          <SectionHeader title="Top Topics by Frequency" sub="Click a bar to filter Explorer" />
          <TopicsChart data={agg.topic_frequency} />
        </Card>
        <Card className="col-span-2">
          <SectionHeader title="Sentiment Distribution" />
          <SentimentPie distribution={agg.sentiment_distribution} total={total} />
        </Card>
      </div>

      {/* Row 2: Sentiment by type + Urgency */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <SectionHeader title="Sentiment by Call Type" />
          <SentimentByTypeChart data={agg.sentiment_by_call_type} />
        </Card>
        <Card>
          <SectionHeader title="Urgency Distribution" />
          <UrgencyChart distribution={agg.urgency_distribution} />
        </Card>
      </div>

      {/* Row 3: Timeline */}
      <Card>
        <SectionHeader title="Call Activity Timeline"
          sub="Each point = one call · size = duration · color = sentiment" />
        <TimelineChart transcripts={transcripts} />
      </Card>

      {/* Row 4: Negative topics + Churn risk */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <SectionHeader title="Top Negative/Mixed Sentiment Topics" />
          <NegativeTopicsChart data={agg.top_negative_topics} />
        </Card>
        <Card>
          <SectionHeader title="Churn Risk Distribution" />
          <ChurnRiskChart distribution={agg.churn_risk_distribution} />
        </Card>
      </div>

      {/* At-risk accounts */}
      <Card>
        <SectionHeader title="⚠️ At-Risk Accounts"
          sub="External calls flagged with medium or high churn risk" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                {['Account', 'Churn Risk', 'Sentiment', 'Urgency', 'Summary'].map(h => (
                  <th key={h} className="pb-2 pr-4 text-xs text-muted font-medium uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {agg.churn_risk_accounts.map((acct: AtRiskAccount, i: number) => (
                <>
                  <tr
                    key={i}
                    onClick={() => setSelectedAccount(selectedAccount?.account === acct.account ? null : acct)}
                    className="border-b border-border/50 hover:bg-white/3 cursor-pointer transition-colors"
                  >
                    <td className="py-2.5 pr-4 font-medium text-slate-200">{acct.account}</td>
                    <td className="py-2.5 pr-4">
                      <Badge label={acct.churn_risk} className={CHURN_BG[acct.churn_risk]} />
                    </td>
                    <td className="py-2.5 pr-4">
                      <Badge label={acct.sentiment} className={SENTIMENT_BG[acct.sentiment]} />
                    </td>
                    <td className="py-2.5 pr-4">
                      <Badge label={acct.urgency} className={URGENCY_BG[acct.urgency]} />
                    </td>
                    <td className="py-2.5 text-muted text-xs max-w-xs truncate">{acct.summary}</td>
                  </tr>
                  {selectedAccount?.account === acct.account && (
                    <tr key={`${i}-detail`} className="bg-blue-950/20">
                      <td colSpan={5} className="px-4 py-3 text-sm text-slate-300">
                        <p className="font-medium text-slate-200 mb-1">📋 {acct.title}</p>
                        <p className="text-muted text-xs">{acct.summary}</p>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
