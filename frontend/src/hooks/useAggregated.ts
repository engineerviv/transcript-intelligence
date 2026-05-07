import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useAggregated() {
  return useQuery({
    queryKey: ['aggregated'],
    queryFn: api.aggregated,
    staleTime: 5 * 60 * 1000,
  })
}
