import { useState, useCallback } from 'react'
import { api } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Spinner } from '../components/ui/Spinner'
import type { AuditListResponse, Decision } from '../types'

export function ActivityFeed() {
  const [page, setPage] = useState(1)
  const [decision, setDecision] = useState('')
  const [actionType, setActionType] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const fetcher = useCallback(() => {
    const params = new URLSearchParams({ page: String(page), page_size: '20', sort: 'desc' })
    if (decision) params.set('decision', decision)
    if (actionType) params.set('action_type', actionType)
    return api.get<AuditListResponse>(`/api/audit?${params}`)
  }, [page, decision, actionType])

  const { data, loading } = usePolling(fetcher, 3000)

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-display font-bold text-slate-100 tracking-tight">Activity Feed</h2>
        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-600 mt-1">All agent actions</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 animate-fade-in-up">
        <select
          value={decision}
          onChange={e => { setDecision(e.target.value); setPage(1) }}
          className="bg-surface-2 border border-slate-700/50 rounded px-3 py-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-emerald-500/50"
        >
          <option value="">All decisions</option>
          <option value="execute">Execute</option>
          <option value="block">Block</option>
          <option value="escalate">Escalate</option>
          <option value="modify">Modify</option>
        </select>
        <select
          value={actionType}
          onChange={e => { setActionType(e.target.value); setPage(1) }}
          className="bg-surface-2 border border-slate-700/50 rounded px-3 py-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-emerald-500/50"
        >
          <option value="">All types</option>
          <option value="api_call">API Call</option>
          <option value="db_query">DB Query</option>
          <option value="tool_call">Tool Call</option>
          <option value="code_execution">Code Exec</option>
          <option value="file_write">File Write</option>
          <option value="send_message">Message</option>
        </select>
        {data && (
          <span className="ml-auto text-[10px] font-mono text-slate-600 self-center">
            {data.total} entries
          </span>
        )}
      </div>

      {loading && !data ? <Spinner /> : (
        <Card>
          <div className="divide-y divide-slate-800/50">
            {(data?.entries ?? []).map((e) => (
              <div key={e.trace_id}>
                <button
                  onClick={() => setExpanded(expanded === e.trace_id ? null : e.trace_id)}
                  className="w-full px-5 py-3 flex items-center gap-4 hover:bg-slate-800/30 transition-colors text-left"
                >
                  <span className="text-[10px] text-slate-600 font-mono w-16 shrink-0">{e.timestamp_iso.slice(11, 19)}</span>
                  <Badge decision={e.decision as Decision} />
                  <span className="text-xs text-slate-400 font-mono w-24 shrink-0">{e.action_type}</span>
                  <span className="text-xs text-slate-300 font-mono truncate flex-1">{e.target}</span>
                  {e.agent_id && <span className="text-[10px] text-slate-600 font-mono">@{e.agent_id}</span>}
                  <span className="text-[10px] text-slate-600 font-mono">{e.pipeline_latency_ms.toFixed(1)}ms</span>
                  <span className="text-slate-600 text-xs">{expanded === e.trace_id ? '-' : '+'}</span>
                </button>
                {expanded === e.trace_id && (
                  <div className="px-5 pb-4 pt-1 bg-slate-900/50 border-t border-slate-800/30 animate-fade-in-up">
                    <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                      <div>
                        <span className="text-slate-600">Trace ID: </span>
                        <span className="text-slate-400">{e.trace_id}</span>
                      </div>
                      <div>
                        <span className="text-slate-600">Validators: </span>
                        <span className="text-slate-400">{e.validators_run.join(', ') || 'none'}</span>
                      </div>
                      {e.reasons.length > 0 && (
                        <div className="col-span-2">
                          <span className="text-slate-600">Reasons: </span>
                          {e.reasons.map((r, i) => (
                            <div key={i} className="text-rose-400/80 mt-1 pl-2 border-l border-rose-500/20">{r}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {(data?.entries ?? []).length === 0 && (
              <div className="px-5 py-12 text-center text-xs font-mono text-slate-600">No matching entries</div>
            )}
          </div>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-xs font-mono border border-slate-700/50 rounded text-slate-400 hover:bg-slate-800/50 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            prev
          </button>
          <span className="text-xs font-mono text-slate-500">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-xs font-mono border border-slate-700/50 rounded text-slate-400 hover:bg-slate-800/50 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            next
          </button>
        </div>
      )}
    </div>
  )
}
