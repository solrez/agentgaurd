import { useCallback } from 'react'
import { api } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { DecisionPieChart } from '../components/charts/DecisionPieChart'
import { TimelineChart } from '../components/charts/TimelineChart'
import { LatencyHistogram } from '../components/charts/LatencyHistogram'
import { ValidatorBarChart } from '../components/charts/ValidatorBarChart'
import type { DecisionDistribution, TimeseriesPoint, TopTarget, ValidatorEffectiveness, LatencyBucket } from '../types'

export function Analytics() {
  const fetchDecisions = useCallback(() => api.get<DecisionDistribution[]>('/api/analytics/decisions'), [])
  const fetchTimeline = useCallback(() => api.get<TimeseriesPoint[]>('/api/analytics/timeline'), [])
  const fetchTopTargets = useCallback(() => api.get<TopTarget[]>('/api/analytics/top-targets'), [])
  const fetchValidators = useCallback(() => api.get<ValidatorEffectiveness[]>('/api/analytics/validators'), [])
  const fetchLatency = useCallback(() => api.get<LatencyBucket[]>('/api/analytics/latency'), [])

  const { data: decisions, loading: l1 } = usePolling(fetchDecisions, 10000)
  const { data: timeline, loading: l2 } = usePolling(fetchTimeline, 10000)
  const { data: topTargets, loading: l3 } = usePolling(fetchTopTargets, 10000)
  const { data: validators, loading: l4 } = usePolling(fetchValidators, 10000)
  const { data: latency, loading: l5 } = usePolling(fetchLatency, 10000)

  if (l1 && l2 && l3 && l4 && l5) return <Spinner />

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-display font-bold text-slate-100 tracking-tight">Analytics</h2>
        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-600 mt-1">Deep insights into guard behavior</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card className="p-5 animate-fade-in-up opacity-0 delay-1">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-4">Decision Distribution</h3>
          <DecisionPieChart data={decisions ?? []} />
        </Card>

        <Card className="p-5 animate-fade-in-up opacity-0 delay-2">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-4">Actions Over Time</h3>
          <TimelineChart data={timeline ?? []} />
        </Card>

        <Card className="p-5 animate-fade-in-up opacity-0 delay-3">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-4">Latency Distribution</h3>
          <LatencyHistogram data={latency ?? []} />
        </Card>

        <Card className="p-5 animate-fade-in-up opacity-0 delay-4">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-4">Validator Effectiveness</h3>
          <ValidatorBarChart data={validators ?? []} />
        </Card>

        <Card className="p-5 col-span-2 animate-fade-in-up opacity-0 delay-5">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-4">Top Blocked Targets</h3>
          <div className="space-y-2">
            {(topTargets ?? []).map((t) => (
              <div key={t.target} className="flex items-center gap-3">
                <span className="text-xs font-mono text-slate-300 w-48 truncate">{t.target}</span>
                <div className="flex-1 h-5 bg-slate-800 rounded overflow-hidden relative">
                  <div
                    className="h-full bg-rose-500/40 rounded"
                    style={{ width: `${Math.max(t.block_rate * 100, 2)}%` }}
                  />
                  <span className="absolute right-2 top-0.5 text-[10px] font-mono text-slate-400">
                    {t.block_count}/{t.total_count}
                  </span>
                </div>
                <span className="text-xs font-mono text-rose-400 w-14 text-right">
                  {(t.block_rate * 100).toFixed(0)}%
                </span>
              </div>
            ))}
            {(topTargets ?? []).length === 0 && (
              <div className="text-xs font-mono text-slate-600 text-center py-6">No data yet</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
