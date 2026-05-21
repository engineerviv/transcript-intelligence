import { useQuery } from '@tanstack/react-query'
import { api, type TranscriptFilters } from '@/lib/api'
import { useFilters } from '@/context/FilterContext'

export function useAggregated() {
  const { filters } = useFilters()

  const params: TranscriptFilters = {
    callTypes:  filters.callTypes,
    sentiments: filters.sentiments,
    urgencies:  filters.urgencies,
    dateFrom:   filters.dateFrom || undefined,
    dateTo:     filters.dateTo   || undefined,
    search:     filters.search   || undefined,
  }

  return useQuery({
    queryKey: ['aggregated', params],
    queryFn:  () => api.aggregated(params),
    staleTime: 5 * 60 * 1000,
  })
}
