import { memo } from 'react'
import { format } from 'date-fns'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

interface StatCardProps {
  label: string
  value: number | string
  delta?: string
  deltaPositive?: boolean
  history?: Array<{ date: string; value: number }>
  color?: string
}

function MiniTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[rgba(15,15,15,0.97)] border border-white/[0.08] rounded-lg px-2.5 py-1.5 text-xs shadow-glass">
      {label && <p className="text-gray-400 mb-0.5">{format(new Date(label), 'MMM d')}</p>}
      <p className="text-white font-semibold">{payload[0].value.toLocaleString()}</p>
    </div>
  )
}

const StatCard = memo(function StatCard({
  label,
  value,
  delta,
  deltaPositive = true,
  history,
  color = '#22c55e',
}: StatCardProps) {
  const displayValue = typeof value === 'number' ? value.toLocaleString() : value
  // stable gradient ID per render (cards are fixed in number/order)
  const gradId = `sg-${label.replace(/\s+/g, '-').toLowerCase()}`

  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-colors overflow-hidden">
      <div className="px-4 pt-4 pb-2">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
        <p className="text-3xl font-bold tabular-nums text-white">{displayValue}</p>
        {delta && (
          <p className={`text-xs mt-0.5 ${deltaPositive ? 'text-accent-green' : 'text-red-400'}`}>
            {deltaPositive ? '↑' : '↓'} {delta}
          </p>
        )}
      </div>

      {history && history.length > 1 && (
        <div style={{ width: '100%', minWidth: 0 }}>
          <ResponsiveContainer width="99%" height={90}>
            <AreaChart data={history} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(v: string) => format(new Date(v), 'MMM d')}
                tick={{ fill: '#6b7280', fontSize: 9 }}
                tickLine={false}
                axisLine={false}
                interval={9}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 9 }}
                tickLine={false}
                axisLine={false}
                width={32}
                tickFormatter={(v: number) =>
                  v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
                }
              />
              <Tooltip content={<MiniTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#${gradId})`}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
})

export default StatCard
