import {
  BarChart, Bar, PieChart, Pie, Cell, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { SENTIMENT_COLORS, URGENCY_COLORS, CHURN_COLORS } from '@/lib/utils'
import type { AggregatedStats, Transcript } from '@/types'

const DARK = { fill: '#cbd5e1', stroke: '#334155' }
const TOOLTIP_STYLE = {
  backgroundColor: '#1e293b', border: '1px solid #334155',
  borderRadius: 8, color: '#f1f5f9', fontSize: 12,
}

// ── Topic Frequency ───────────────────────────────────────────────────────────

export function TopicsChart({ data, onTopicClick }: {
  data: AggregatedStats['topic_frequency']
  onTopicClick?: (topic: string) => void
}) {
  const top12 = data.slice(0, 12)

  return (
    <ResponsiveContainer width="100%" height={380}>
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <BarChart data={top12} layout="vertical" margin={{ left: 12, right: 24, top: 8, bottom: 8 }}
        onClick={(e: any) => onTopicClick?.(e?.activePayload?.[0]?.payload?.topic)}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
        <XAxis type="number" tick={{ ...DARK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="topic" tick={{ ...DARK, fontSize: 11 }} axisLine={false}
          tickLine={false} width={130} />
        <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: '#ffffff08' }} />
        <Bar dataKey="count" radius={[0, 4, 4, 0]} cursor="pointer">
          {top12.map((_entry, i) => (
            <Cell key={i} fill={i === 0 ? '#ef4444' : '#3b82f6'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Sentiment Donut ───────────────────────────────────────────────────────────

export function SentimentPie({ distribution, total }: {
  distribution: AggregatedStats['sentiment_distribution']
  total: number
}) {
  const data = Object.entries(distribution).map(([name, v]) => ({ name, value: v.count }))
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={70} outerRadius={110}
          dataKey="value" paddingAngle={2}>
          {data.map(({ name }, i) => (
            <Cell key={i} fill={SENTIMENT_COLORS[name as keyof typeof SENTIMENT_COLORS] ?? '#94a3b8'} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v as number} calls`, '']} />
        <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle"
          fill="#f1f5f9" fontSize={22} fontWeight={700}>{total}</text>
        <text x="50%" y="50%" dy={22} textAnchor="middle" dominantBaseline="middle"
          fill="#94a3b8" fontSize={12}>calls</text>
      </PieChart>
    </ResponsiveContainer>
  )
}

// ── Sentiment by Call Type ────────────────────────────────────────────────────

export function SentimentByTypeChart({ data }: { data: AggregatedStats['sentiment_by_call_type'] }) {
  const callTypes = Object.keys(data)
  const chartData = callTypes.map(ct => ({
    name: ct,
    ...data[ct],
  }))
  const sentiments = ['positive', 'neutral', 'mixed', 'negative']

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} margin={{ top: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey="name" tick={{ ...DARK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ ...DARK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
        {sentiments.map(s => (
          <Bar key={s} dataKey={s} stackId="a" fill={SENTIMENT_COLORS[s as keyof typeof SENTIMENT_COLORS] ?? '#94a3b8'}
            name={s.charAt(0).toUpperCase() + s.slice(1)} radius={s === 'negative' ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Urgency ───────────────────────────────────────────────────────────────────

export function UrgencyChart({ distribution }: { distribution: AggregatedStats['urgency_distribution'] }) {
  const order = ['low', 'medium', 'high', 'critical']
  const data = order.filter(u => distribution[u]).map(u => ({
    name: u.charAt(0).toUpperCase() + u.slice(1),
    count: distribution[u].count,
    fill: URGENCY_COLORS[u as keyof typeof URGENCY_COLORS],
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey="name" tick={{ ...DARK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ ...DARK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} label={{ position: 'top', fill: '#94a3b8', fontSize: 11 }}>
          {data.map((_entry, i) => <Cell key={i} fill={_entry.fill} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Churn Risk ────────────────────────────────────────────────────────────────

export function ChurnRiskChart({ distribution }: { distribution: AggregatedStats['churn_risk_distribution'] }) {
  const order = ['none', 'low', 'medium', 'high']
  const data = order.filter(c => distribution[c] != null).map(c => ({
    name: c.charAt(0).toUpperCase() + c.slice(1),
    count: distribution[c],
    fill: CHURN_COLORS[c as keyof typeof CHURN_COLORS],
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey="name" tick={{ ...DARK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ ...DARK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} label={{ position: 'top', fill: '#94a3b8', fontSize: 11 }}>
          {data.map((_entry, i) => <Cell key={i} fill={_entry.fill} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Negative Topics ───────────────────────────────────────────────────────────

export function NegativeTopicsChart({ data }: { data: AggregatedStats['top_negative_topics'] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data.slice(0, 8)} margin={{ top: 8, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey="topic" tick={{ ...DARK, fontSize: 10 }} axisLine={false} tickLine={false}
          angle={-25} textAnchor="end" interval={0} />
        <YAxis tick={{ ...DARK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="count" fill="#ef4444" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Timeline ──────────────────────────────────────────────────────────────────

export function TimelineChart({ transcripts }: { transcripts: Transcript[] }) {
  const data = transcripts
    .filter(t => t.start_time && t.sentiment_score != null)
    .map(t => ({
      date: t.start_time.slice(0, 10),
      score: t.sentiment_score,
      sentiment: t.sentiment ?? 'neutral',
      name: t.title,
      size: Math.min(t.duration_minutes ?? 20, 90),
    }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="date" tick={{ ...DARK, fontSize: 10 }} axisLine={false} tickLine={false}
          angle={-20} textAnchor="end" height={40} />
        <YAxis dataKey="score" domain={[0.5, 5.5]} tick={{ ...DARK, fontSize: 11 }}
          axisLine={false} tickLine={false} label={{ value: 'Score', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }} />
        <Tooltip contentStyle={TOOLTIP_STYLE}
          formatter={(value, name) => [
            name === 'score' ? `${value}/5` : value,
            name === 'score' ? 'Sentiment Score' : name,
          ]}
          labelFormatter={(_, payload) => (payload as any[])?.[0]?.payload?.name ?? ''} />
        {(['positive', 'neutral', 'mixed', 'negative'] as const).map(s => (
          <Scatter key={s} name={s}
            data={data.filter(d => d.sentiment === s)}
            fill={SENTIMENT_COLORS[s]} fillOpacity={0.8} />
        ))}
        <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
