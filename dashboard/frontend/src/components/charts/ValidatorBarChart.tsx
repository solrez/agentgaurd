import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'
import type { ValidatorEffectiveness } from '../../types'

export function ValidatorBarChart({ data }: { data: ValidatorEffectiveness[] }) {
  if (!data.length) return <div className="text-slate-600 text-xs font-mono text-center py-10">No data</div>

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10, fill: '#475569', fontFamily: 'JetBrains Mono' }} />
          <YAxis dataKey="validator_name" type="category" tick={{ fontSize: 10, fill: '#94a3b8', fontFamily: 'JetBrains Mono' }} width={70} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontFamily: 'JetBrains Mono', fontSize: '11px' }}
          />
          <Bar dataKey="times_run" fill="#334155" radius={[0, 4, 4, 0]} name="Total runs" />
          <Bar dataKey="blocks_triggered" fill="#f43f5e" fillOpacity={0.7} radius={[0, 4, 4, 0]} name="Blocks" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
