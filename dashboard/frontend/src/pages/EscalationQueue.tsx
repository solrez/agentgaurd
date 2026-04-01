import { useCallback, useState } from 'react'
import { api } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import type { EscalationEntry } from '../types'

export function EscalationQueue() {
  const fetcher = useCallback(() => api.get<EscalationEntry[]>('/api/escalation'), [])
  const { data, loading, refetch } = usePolling(fetcher, 5000)
  const [acting, setActing] = useState<string | null>(null)

  const resolve = async (traceId: string, action: 'approve' | 'reject') => {
    setActing(traceId)
    try {
      await api.post(`/api/escalation/${traceId}`, { action, reason: '' })
      refetch()
    } catch { /* ignore */ }
    finally { setActing(null) }
  }

  if (loading && !data) return <Spinner />

  const pending = (data ?? []).filter(e => e.status === 'pending')

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-display font-bold text-slate-100 tracking-tight">Escalation Queue</h2>
        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-600 mt-1">
          {pending.length} pending review{pending.length !== 1 ? 's' : ''}
        </p>
      </div>

      {pending.length === 0 ? (
        <Card className="p-12 text-center animate-fade-in-up">
          <div className="text-3xl mb-3 opacity-20">~</div>
          <p className="text-sm font-mono text-slate-500">No pending escalations</p>
          <p className="text-xs font-mono text-slate-700 mt-1">All clear. Actions requiring review will appear here.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {pending.map((e, i) => (
            <Card key={e.trace_id} className={`p-5 animate-fade-in-up opacity-0 delay-${Math.min(i + 1, 5)}`} glow="escalate">
              <div className="flex items-start gap-4">
                {/* Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs font-mono text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
                      {e.action_type}
                    </span>
                    <span className="text-xs font-mono text-slate-300">{e.target}</span>
                    {e.agent_id && (
                      <span className="text-[10px] font-mono text-slate-600">@{e.agent_id}</span>
                    )}
                  </div>
                  <div className="space-y-1">
                    {e.reasons.map((r, ri) => (
                      <p key={ri} className="text-xs font-mono text-slate-400 pl-2 border-l-2 border-amber-500/30">{r}</p>
                    ))}
                  </div>
                  <p className="text-[10px] font-mono text-slate-600 mt-2">{e.timestamp_iso}</p>
                </div>

                {/* Actions */}
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => resolve(e.trace_id, 'approve')}
                    disabled={acting === e.trace_id}
                    className="px-4 py-2 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded text-xs font-mono hover:bg-emerald-500/25 transition-colors disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => resolve(e.trace_id, 'reject')}
                    disabled={acting === e.trace_id}
                    className="px-4 py-2 bg-rose-500/15 text-rose-400 border border-rose-500/30 rounded text-xs font-mono hover:bg-rose-500/25 transition-colors disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
