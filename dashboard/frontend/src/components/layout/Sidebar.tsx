import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../../api/client'

const links = [
  { to: '/', label: 'Overview', icon: '>' },
  { to: '/activity', label: 'Activity', icon: '#' },
  { to: '/analytics', label: 'Analytics', icon: '%' },
  { to: '/config', label: 'Config', icon: '~' },
  { to: '/escalations', label: 'Escalations', icon: '!' },
]

export function Sidebar() {
  const [pendingCount, setPendingCount] = useState(0)

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const data = await api.get<{ count: number }>('/api/escalation/count')
        setPendingCount(data.count)
      } catch { /* ignore */ }
    }
    fetchCount()
    const id = setInterval(fetchCount, 10000)
    return () => clearInterval(id)
  }, [])

  return (
    <aside className="w-56 h-screen fixed left-0 top-0 bg-surface-0 border-r border-slate-800/80 flex flex-col z-50">
      {/* Logo */}
      <div className="p-5 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
            <span className="text-emerald-400 text-xs font-bold font-mono">AG</span>
          </div>
          <div>
            <h1 className="text-sm font-display font-bold text-slate-100 tracking-tight">AgentGuard</h1>
            <p className="text-[9px] font-mono uppercase tracking-[0.25em] text-slate-600">mission control</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-0.5">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md text-xs font-mono transition-all duration-150 group ${
                isActive
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 border border-transparent'
              }`
            }
          >
            <span className="w-5 text-center opacity-60 group-hover:opacity-100 text-sm">{link.icon}</span>
            <span className="tracking-wide">{link.label}</span>
            {link.to === '/escalations' && pendingCount > 0 && (
              <span className="ml-auto bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                {pendingCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Status */}
      <div className="p-4 border-t border-slate-800/80">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] font-mono text-slate-600 uppercase tracking-wider">System active</span>
        </div>
      </div>
    </aside>
  )
}
