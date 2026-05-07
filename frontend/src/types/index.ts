export type CallType = 'support' | 'external' | 'internal'
export type Sentiment = 'positive' | 'neutral' | 'mixed' | 'negative'
export type Urgency = 'low' | 'medium' | 'high' | 'critical'
export type ChurnRisk = 'none' | 'low' | 'medium' | 'high'

export interface KeyMoment {
  type: string
  text: string
}

export interface Transcript {
  id: string
  title: string
  call_type: CallType
  organizer: string
  start_time: string
  duration_minutes: number
  participants: string[]
  num_speakers: number
  summary: string
  action_items: string[]
  existing_topics: string[]
  overall_sentiment: string
  sentiment_score: number | null
  key_moments: KeyMoment[]
  full_transcript?: string
  num_sentences: number
  // Enriched fields
  topic?: string
  sub_topic?: string
  sentiment?: Sentiment
  emotion?: string
  urgency?: Urgency
  intent?: string
  key_entities?: string[]
  churn_risk?: ChurnRisk
}

export interface TopicFrequency { topic: string; count: number }
export interface SentimentCount  { count: number; pct: number }

export interface AtRiskAccount {
  title: string
  account: string
  churn_risk: ChurnRisk
  sentiment: Sentiment
  urgency: Urgency
  summary: string
}

export interface ExecutiveInsights {
  key_insights: string[]
  operational_risks: string[]
  churn_indicators: string[]
  customer_pain_points: string[]
  recommendations: string[]
}

export interface AggregatedStats {
  total_transcripts: number
  topic_frequency: TopicFrequency[]
  sentiment_distribution: Record<string, SentimentCount>
  sentiment_by_call_type: Record<string, Record<string, number>>
  urgency_distribution: Record<string, SentimentCount>
  churn_risk_distribution: Record<string, number>
  top_negative_topics: TopicFrequency[]
  high_urgency_topics: TopicFrequency[]
  intent_distribution: Record<string, number>
  emotion_distribution: Record<string, number>
  churn_risk_accounts: AtRiskAccount[]
  avg_sentiment_score_by_type: Record<string, number>
  executive_insights: ExecutiveInsights
}

export interface TranscriptsResponse {
  transcripts: Transcript[]
  total: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface Filters {
  callTypes: CallType[]
  sentiments: Sentiment[]
  urgencies: Urgency[]
  dateFrom: string
  dateTo: string
  search: string
}
