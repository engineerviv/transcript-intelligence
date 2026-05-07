import { createContext, useContext, useState, type ReactNode } from 'react'
import type { Filters, CallType, Sentiment, Urgency } from '@/types'

const ALL_CALL_TYPES:  CallType[]  = ['support', 'external', 'internal']
const ALL_SENTIMENTS:  Sentiment[] = ['positive', 'neutral', 'mixed', 'negative']
const ALL_URGENCIES:   Urgency[]   = ['low', 'medium', 'high', 'critical']

const DEFAULT_FILTERS: Filters = {
  callTypes:  ALL_CALL_TYPES,
  sentiments: ALL_SENTIMENTS,
  urgencies:  ALL_URGENCIES,
  dateFrom:   '',
  dateTo:     '',
  search:     '',
}

interface FilterContextValue {
  filters: Filters
  setFilters: (f: Partial<Filters>) => void
  resetFilters: () => void
  isDefault: boolean
}

const Ctx = createContext<FilterContextValue | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, set] = useState<Filters>(DEFAULT_FILTERS)

  const setFilters = (partial: Partial<Filters>) =>
    set((prev: Filters) => ({ ...prev, ...partial }))

  const resetFilters = () => set(DEFAULT_FILTERS)

  const isDefault = JSON.stringify(filters) === JSON.stringify(DEFAULT_FILTERS)

  return (
    <Ctx.Provider value={{ filters, setFilters, resetFilters, isDefault }}>
      {children}
    </Ctx.Provider>
  )
}

export function useFilters() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useFilters must be used inside FilterProvider')
  return ctx
}

export { ALL_CALL_TYPES, ALL_SENTIMENTS, ALL_URGENCIES }
