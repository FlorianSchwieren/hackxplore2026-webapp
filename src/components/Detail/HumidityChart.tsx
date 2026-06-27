import { memo } from 'react'
import { format } from 'date-fns'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { HumidityStatus, SensorReading } from '@/types'

const STATUS_COLORS: Record<HumidityStatus, string> = {
  dry: '#ef4444',
  low: '#f97316',
  normal: '#22c55e',
  moist: '#06b6d4',
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[rgba(15,15,15,0.95)] border border-white/[0.08] rounded-lg px-3 py-2 text-xs shadow-glass">
      <p className="text-gray-400">{label ? format(new Date(label), 'MMM d') : ''}</p>
      <p className="text-white font-semibold">{payload[0].value.toFixed(1)}%</p>
    </div>
  )
}

interface HumidityChartProps {
  readings: SensorReading[]
  status: HumidityStatus
}

const HumidityChart = memo(function HumidityChart({ readings, status }: HumidityChartProps) {
  const color = STATUS_COLORS[status]

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={readings} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(v: string) => format(new Date(v), 'MMM d')}
          tick={{ fill: '#6b7280', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          interval={5}
        />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fill: '#6b7280', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={40} stroke="#22c55e" strokeDasharray="4 4" strokeWidth={1} />
        <ReferenceLine y={20} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: color, strokeWidth: 0 }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
})

export default HumidityChart
