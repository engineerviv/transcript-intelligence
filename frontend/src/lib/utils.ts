import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { Sentiment, Urgency, ChurnRisk } from '@/types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const SENTIMENT_COLORS: Record<Sentiment, string> = {
  positive: '#22c55e',
  neutral:  '#94a3b8',
  mixed:    '#f59e0b',
  negative: '#ef4444',
}

export const URGENCY_COLORS: Record<Urgency, string> = {
  low:      '#22c55e',
  medium:   '#f59e0b',
  high:     '#f97316',
  critical: '#dc2626',
}

export const CHURN_COLORS: Record<ChurnRisk, string> = {
  none:   '#22c55e',
  low:    '#84cc16',
  medium: '#f59e0b',
  high:   '#ef4444',
}

export const SENTIMENT_BG: Record<Sentiment, string> = {
  positive: 'bg-green-500/10 text-green-400 ring-green-500/20',
  neutral:  'bg-slate-500/10 text-slate-400 ring-slate-500/20',
  mixed:    'bg-amber-500/10 text-amber-400 ring-amber-500/20',
  negative: 'bg-red-500/10 text-red-400 ring-red-500/20',
}

export const URGENCY_BG: Record<Urgency, string> = {
  low:      'bg-green-500/10 text-green-400 ring-green-500/20',
  medium:   'bg-amber-500/10 text-amber-400 ring-amber-500/20',
  high:     'bg-orange-500/10 text-orange-400 ring-orange-500/20',
  critical: 'bg-red-500/10 text-red-400 ring-red-500/20',
}

export const CHURN_BG: Record<ChurnRisk, string> = {
  none:   'bg-green-500/10 text-green-400 ring-green-500/20',
  low:    'bg-lime-500/10 text-lime-400 ring-lime-500/20',
  medium: 'bg-amber-500/10 text-amber-400 ring-amber-500/20',
  high:   'bg-red-500/10 text-red-400 ring-red-500/20',
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)}m`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}
