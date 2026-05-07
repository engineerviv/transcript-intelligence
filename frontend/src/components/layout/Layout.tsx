import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { FilterBar } from './FilterBar'

const TITLES: Record<string, string> = {
  '/':         'Dashboard',
  '/explorer': 'Explorer',
  '/insights': 'Executive Insights',
}

export function Layout() {
  const { pathname } = useLocation()
  const title = TITLES[pathname] ?? 'Dashboard'

  return (
    <div className="flex h-dvh bg-[#0f172a]">
      <Sidebar />

      <div className="flex-1 flex flex-col ml-56 min-w-0">
        {/* Header */}
        <header className="sticky top-0 z-20 bg-[#0f172a]/90 backdrop-blur border-b border-border">
          <div className="px-6 py-3">
            <h1 className="text-base font-semibold text-slate-100 mb-2.5">{title}</h1>
            {pathname !== '/explorer' && <FilterBar />}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto px-6 py-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
