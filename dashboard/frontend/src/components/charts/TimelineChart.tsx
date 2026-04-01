import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'
import type { TimeseriesPoint } from '../../types'

export function TimelineChart({ data }: { data: TimeseriesPoint[] }) {
  if (!data.length) return <div className="text-slate-600 text-xs font-mono text-center py-10">No data</div>

  const formatted = data.map(d => ({
    ...d,
    label: d.timestamp.slice(11, 16) || d.timestamp.slice(5, 10),
  }))

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={formatted}>
          <defs>
            <linearGradient id="colorActions" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#475569', fontFamily: 'JetBrains Mono' }} />
          <YAxis tick={{ fontSize: 10, fill: '#475569', fontFamily: 'JetBrains Mono' }} width={30} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontFamily: 'JetBrains Mono', fontSize: '11px' }}
          />
          <Area type="monotone" dataKey="count" stroke="#10b981" fill="url(#colorActions)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
