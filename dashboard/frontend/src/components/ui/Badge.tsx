import type { Decision } from '../../types'

const styles: Record<Decision, string> = {
  execute: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 glow-execute',
  block: 'bg-rose-500/15 text-rose-400 border-rose-500/30 glow-block',
  escalate: 'bg-amber-500/15 text-amber-400 border-amber-500/30 glow-escalate',
  modify: 'bg-sky-500/15 text-sky-400 border-sky-500/30 glow-modify',
}

export function Badge({ decision }: { decision: Decision }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded border text-xs font-mono font-medium uppercase tracking-wider ${styles[decision] || styles.execute}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${decision === 'execute' ? 'bg-emerald-400' : decision === 'block' ? 'bg-rose-400' : decision === 'escalate' ? 'bg-amber-400' : 'bg-sky-400'}`} />
      {decision}
    </span>
  )
}
