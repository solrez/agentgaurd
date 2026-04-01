import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  glow?: 'execute' | 'block' | 'escalate' | 'modify'
}

export function Card({ children, className = '', glow }: CardProps) {
  const glowClass = glow ? `glow-${glow}` : ''
  return (
    <div className={`bg-surface-1 border border-slate-700/50 rounded-lg ${glowClass} ${className}`}>
      {children}
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  icon: string
  color?: string
  delay?: number
}

export function MetricCard({ label, value, sub, icon, color = 'text-emerald-400', delay = 0 }: MetricCardProps) {
  return (
    <Card className={`p-5 animate-fade-in-up opacity-0 ${delay > 0 ? `delay-${delay}` : ''}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-2">{label}</p>
          <p className={`text-3xl font-display font-bold tracking-tight ${color}`}>{value}</p>
          {sub && <p className="text-xs text-slate-500 mt-1 font-mono">{sub}</p>}
        </div>
        <span className="text-2xl opacity-40">{icon}</span>
      </div>
    </Card>
  )
}
