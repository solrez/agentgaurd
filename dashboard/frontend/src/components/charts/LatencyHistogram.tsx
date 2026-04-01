import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'
import type { LatencyBucket } from '../../types'

export function LatencyHistogram({ data }: { data: LatencyBucket[] }) {
  if (!data.length) return <div className="text-slate-600 text-xs font-mono text-center py-10">No data</div>

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="range_label" tick={{ fontSize: 9, fill: '#475569', fontFamily: 'JetBrains Mono' }} />
          <YAxis tick={{ fontSize: 10, fill: '#475569', fontFamily: 'JetBrains Mono' }} width={30} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontFamily: 'JetBrains Mono', fontSize: '11px' }}
          />
          <Bar dataKey="count" fill="#0ea5e9" fillOpacity={0.7} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
