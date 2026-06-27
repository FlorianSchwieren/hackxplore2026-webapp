import { memo } from 'react'
import { LineChart, Line, ResponsiveContainer } from 'recharts'

interface StatCardProps {
  label: string
  value: number | string
  delta?: string
  deltaPositive?: boolean
  history?: Array<{ date: string; value: number }>
  color?: string
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

  return (
    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-colors">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-3xl font-bold tabular-nums text-white">{displayValue}</p>
      {delta && (
        <p className={`text-xs mt-0.5 ${deltaPositive ? 'text-accent-green' : 'text-red-400'}`}>
          {deltaPositive ? '↑' : '↓'} {delta}
        </p>
      )}
      {history && history.length > 0 && (
        <div className="mt-3 -mx-1">
          <ResponsiveContainer width="100%" height={40}>
            <LineChart data={history}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
})

export default StatCard
