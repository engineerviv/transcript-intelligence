import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { FilterProvider } from '@/context/FilterContext'
import { Layout } from '@/components/layout/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Explorer } from '@/pages/Explorer'
import { Insights } from '@/pages/Insights'
import { ChatWidget } from '@/components/chat/ChatWidget'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5 * 60 * 1000, retry: 1 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <FilterProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="/explorer" element={<Explorer />} />
              <Route path="/insights" element={<Insights />} />
            </Route>
          </Routes>
          <ChatWidget />
        </BrowserRouter>
      </FilterProvider>
    </QueryClientProvider>
  )
}
