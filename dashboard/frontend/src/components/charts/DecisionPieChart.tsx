import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import type { DecisionDistribution } from '../../types'

const COLORS: Record<string, string> = {
  execute: '#10b981',
  block: '#f43f5e',
  escalate: '#f59e0b',
  modify: '#0ea5e9',
}

export function DecisionPieChart({ data }: { data: DecisionDistribution[] }) {
  if (!data.length) return <div className="text-slate-600 text-xs font-mono text-center py-10">No data</div>

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            dataKey="count"
            nameKey="decision"
            stroke="none"
          >
            {data.map((entry) => (
              <Cell key={entry.decision} fill={COLORS[entry.decision] || '#64748b'} fillOpacity={0.8} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontFamily: 'JetBrains Mono', fontSize: '11px' }}
            labelStyle={{ color: '#94a3b8' }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-4 -mt-2">
        {data.map((d) => (
          <div key={d.decision} className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[d.decision] }} />
            {d.decision} ({d.count})
          </div>
        ))}
      </div>
    </div>
  )
}
