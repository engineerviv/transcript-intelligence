import type { AggregatedStats, TranscriptsResponse, Transcript, ChatMessage } from '@/types'

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  return res.json()
}

export interface TranscriptFilters {
  callTypes?: string[]
  sentiments?: string[]
  urgencies?: string[]
  dateFrom?: string
  dateTo?: string
  search?: string
  limit?: number
  offset?: number
}

function buildQuery(filters: TranscriptFilters): string {
  const p = new URLSearchParams()
  if (filters.callTypes?.length)  p.set('call_type',  filters.callTypes.join(','))
  if (filters.sentiments?.length) p.set('sentiment',  filters.sentiments.join(','))
  if (filters.urgencies?.length)  p.set('urgency',    filters.urgencies.join(','))
  if (filters.dateFrom)           p.set('date_from',  filters.dateFrom)
  if (filters.dateTo)             p.set('date_to',    filters.dateTo)
  if (filters.search)             p.set('search',     filters.search)
  if (filters.limit != null)      p.set('limit',      String(filters.limit))
  if (filters.offset != null)     p.set('offset',     String(filters.offset))
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const api = {
  health:      ()                        => get<{ status: string; pipeline_ready: boolean; transcript_count: number }>('/health'),
  aggregated:  (filters: TranscriptFilters = {}) => get<AggregatedStats>(`/aggregated${buildQuery(filters)}`),
  transcripts: (filters: TranscriptFilters = {}) => get<TranscriptsResponse>(`/transcripts${buildQuery(filters)}`),
  transcript:  (id: string)             => get<Transcript>(`/transcripts/${id}`),

  chatStream(question: string, history: ChatMessage[]): ReadableStream<string> {
    let controller: ReadableStreamDefaultController<string>

    const stream = new ReadableStream<string>({
      start(c) { controller = c },
    })

    fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history }),
    }).then(async (res) => {
      if (!res.ok || !res.body) {
        controller.enqueue(`Error: ${res.status}`)
        controller.close()
        return
      }
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') { controller.close(); return }
          try {
            const { text, error } = JSON.parse(data)
            if (error) { controller.enqueue(`Error: ${error}`); controller.close(); return }
            if (text)  controller.enqueue(text)
          } catch { /* skip malformed */ }
        }
      }
      controller.close()
    }).catch((err) => {
      controller.enqueue(`Error: ${err.message}`)
      controller.close()
    })

    return stream
  },
}
