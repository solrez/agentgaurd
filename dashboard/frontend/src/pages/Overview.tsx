import { useCallback } from 'react'
import { api } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { Card, MetricCard } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Spinner } from '../components/ui/Spinner'
import { DecisionPieChart } from '../components/charts/DecisionPieChart'
import { TimelineChart } from '../components/charts/TimelineChart'
import type { OverviewMetrics, DecisionDistribution, TimeseriesPoint, AuditListResponse, Decision } from '../types'

export function Overview() {
  const fetchOverview = useCallback(() => api.get<OverviewMetrics>('/api/analytics/overview'), [])
  const fetchDecisions = useCallback(() => api.get<DecisionDistribution[]>('/api/analytics/decisions'), [])
  const fetchTimeline = useCallback(() => api.get<TimeseriesPoint[]>('/api/analytics/timeline'), [])
  const fetchRecent = useCallback(() => api.get<AuditListResponse>('/api/audit?page_size=8&sort=desc'), [])

  const { data: overview, loading: l1 } = usePolling(fetchOverview)
  const { data: decisions, loading: l2 } = usePolling(fetchDecisions)
  const { data: timeline, loading: l3 } = usePolling(fetchTimeline)
  const { data: recent, loading: l4 } = usePolling(fetchRecent)

  if (l1 || l2 || l3 || l4) return <Spinner />

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-display font-bold text-slate-100 tracking-tight">System Overview</h2>
        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-600 mt-1">Real-time guard status</p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard label="Total Actions" value={overview?.total_actions ?? 0} icon="~" color="text-slate-100" delay={1} />
        <MetricCard label="Block Rate" value={`${((overview?.block_rate ?? 0) * 100).toFixed(1)}%`} icon="!" color="text-rose-400" delay={2} />
        <MetricCard label="Avg Latency" value={`${(overview?.avg_latency_ms ?? 0).toFixed(1)}ms`} icon=">" color="text-sky-400" delay={3} />
        <MetricCard label="Active Agents" value={overview?.active_agents ?? 0} sub={`${overview?.actions_last_hour ?? 0} actions/hr`} icon="#" color="text-emerald-400" delay={4} />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card className="p-5 animate-fade-in-up opacity-0 delay-3">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-4">Decision Distribution</h3>
          <DecisionPieChart data={decisions ?? []} />
        </Card>
        <Card className="p-5 animate-fade-in-up opacity-0 delay-4">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-4">Actions Over Time</h3>
          <TimelineChart data={timeline ?? []} />
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="animate-fade-in-up opacity-0 delay-5">
        <div className="px-5 py-3 border-b border-slate-700/50">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">Recent Activity</h3>
        </div>
        <div className="divide-y divide-slate-800/50">
          {(recent?.entries ?? []).map((e) => (
            <div key={e.trace_id} className="px-5 py-3 flex items-center gap-4 hover:bg-slate-800/30 transition-colors">
              <Badge decision={e.decision as Decision} />
              <span className="text-xs text-slate-400 font-mono w-24 shrink-0">{e.action_type}</span>
              <span className="text-xs text-slate-300 font-mono truncate flex-1">{e.target}</span>
              <span className="text-[10px] text-slate-600 font-mono">{e.pipeline_latency_ms.toFixed(1)}ms</span>
              <span className="text-[10px] text-slate-600 font-mono">{e.timestamp_iso.slice(11, 19)}</span>
            </div>
          ))}
          {(recent?.entries ?? []).length === 0 && (
            <div className="px-5 py-8 text-center text-xs font-mono text-slate-600">No actions recorded yet</div>
          )}
        </div>
      </Card>
    </div>
  )
}
