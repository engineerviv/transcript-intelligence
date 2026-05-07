import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Search, Lightbulb } from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/',         icon: LayoutDashboard, label: 'Dashboard'  },
  { to: '/explorer', icon: Search,          label: 'Explorer'   },
  { to: '/insights', icon: Lightbulb,       label: 'Insights'   },
]

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 w-56 bg-surface border-r border-border flex flex-col z-30">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white text-xs font-bold">TI</div>
          <div>
            <div className="text-sm font-semibold text-slate-100 leading-tight">Transcript</div>
            <div className="text-xs text-muted leading-tight">Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => cn(
              'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? 'bg-blue-600/20 text-blue-400'
                : 'text-subtle hover:bg-white/5 hover:text-slate-200',
            )}
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-border">
        <p className="text-xs text-muted">AegisCloud · 2026</p>
      </div>
    </aside>
  )
}
