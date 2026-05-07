import { useQuery } from '@tanstack/react-query'
import { api, type TranscriptFilters } from '@/lib/api'
import { useFilters } from '@/context/FilterContext'

export function useTranscripts(extra: TranscriptFilters = {}) {
  const { filters } = useFilters()

  const params: TranscriptFilters = {
    callTypes:  filters.callTypes,
    sentiments: filters.sentiments,
    urgencies:  filters.urgencies,
    dateFrom:   filters.dateFrom || undefined,
    dateTo:     filters.dateTo   || undefined,
    search:     filters.search   || undefined,
    limit: 500,
    ...extra,
  }

  return useQuery({
    queryKey: ['transcripts', params],
    queryFn:  () => api.transcripts(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useTranscript(id: string | null) {
  return useQuery({
    queryKey: ['transcript', id],
    queryFn:  () => api.transcript(id!),
    enabled:  !!id,
    staleTime: 5 * 60 * 1000,
  })
}
