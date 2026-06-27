import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, TreePine, Radio, Database, Users, Activity, MapPin } from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import { useNetworkStats, useLeaderboard, useStadtteilStats } from '@/lib/queries/useStats'
import { useTrees } from '@/lib/queries/useTrees'
import { useSensors } from '@/lib/queries/useSensors'

const CHART_CARD = 'bg-[rgba(15,15,15,0.6)] rounded-2xl border border-white/[0.06] p-5'
const GRID_COLORS = { stroke: '#1f2937' }

// Gradient IDs
function GreenGradient({ id }: { id: string }) {
  return (
    <defs>
      <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
        <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
      </linearGradient>
    </defs>
  )
}

const AXIS_TICK = { fill: '#6b7280', fontSize: 11 }

function ChartTooltipStyle({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name?: string }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[rgba(15,15,15,0.97)] border border-white/[0.08] rounded-xl px-3 py-2 text-xs shadow-glass">
      {label && <p className="text-gray-400 mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="text-white font-semibold">{p.name && `${p.name}: `}{typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</p>
      ))}
    </div>
  )
}

// Derived stats are computed inside StatsPage from live hooks.

const RANK_COLORS = ['#fbbf24', '#94a3b8', '#d97706']

export default function StatsPage() {
  const navigate = useNavigate()
  const { data: stats } = useNetworkStats()
  const { data: leaderboard = [] } = useLeaderboard()
  const { data: trees = [] } = useTrees()
  const { data: sensors = [] } = useSensors()
  const { data: districtCounts = [] } = useStadtteilStats()

  const treeStatusPie = useMemo(() => {
    const counts = {
      dry: trees.filter((t) => t.humidity_status === 'dry').length,
      low: trees.filter((t) => t.humidity_status === 'low').length,
      normal: trees.filter((t) => t.humidity_status === 'normal').length,
      moist: trees.filter((t) => t.humidity_status === 'moist').length,
    }
    return [
      { name: 'Dry', value: counts.dry, color: '#ef4444' },
      { name: 'Low', value: counts.low, color: '#f97316' },
      { name: 'Normal', value: counts.normal, color: '#22c55e' },
      { name: 'Moist', value: counts.moist, color: '#06b6d4' },
    ]
  }, [trees])

  const { sensorStatusPie, activeSensorPct } = useMemo(() => {
    const active = sensors.filter((s) => s.status === 'active').length
    const total = sensors.length
    return {
      activeSensorPct: total > 0 ? Math.round((active / total) * 100) : 0,
      sensorStatusPie: [
        { name: 'Active', value: active, color: '#06b6d4' },
        { name: 'Inactive', value: total - active, color: '#374151' },
      ],
    }
  }, [sensors])

  const modelData = useMemo(() => {
    const modelCounts = sensors.reduce<Record<string, number>>((acc, s) => {
      acc[s.model_type] = (acc[s.model_type] ?? 0) + 1
      return acc
    }, {})
    return Object.entries(modelCounts).map(([name, value]) => ({ name, value }))
  }, [sensors])

  const districtsCovered = districtCounts.filter((d) => d.sensor_count > 0).length

  return (
    <div className="min-h-screen bg-surface text-white pb-16">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-[rgba(10,10,10,0.9)] backdrop-blur-[16px] border-b border-white/[0.06] h-14 flex items-center px-6 gap-4">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Map
        </button>
        <span className="text-sm text-gray-600">·</span>
        <span className="text-sm font-semibold text-white">Network Statistics</span>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 space-y-8">
        {/* Hero stat cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: 'Daily Users', value: stats?.daily_users ?? 0, icon: Users, color: '#22c55e' },
            { label: 'Total Sensors', value: stats?.total_sensors ?? 0, icon: Radio, color: '#06b6d4' },
            { label: 'Data Points', value: stats?.data_points ?? 0, icon: Database, color: '#22c55e' },
            { label: 'Registered Trees', value: stats?.registered_trees ?? 0, icon: TreePine, color: '#22c55e' },
            {
              label: 'Active Sensors',
              value: `${activeSensorPct}%`,
              icon: Activity,
              color: '#06b6d4',
            },
            { label: 'Districts Covered', value: districtsCovered, icon: MapPin, color: '#22c55e' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="rounded-xl bg-white/[0.04] border border-white/[0.06] p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4" style={{ color }} />
                <p className="text-xs text-gray-500">{label}</p>
              </div>
              <p className="text-2xl font-bold tabular-nums text-white">
                {typeof value === 'number' ? value.toLocaleString() : value}
              </p>
            </div>
          ))}
        </div>

        {/* Time-series charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className={CHART_CARD}>
            <p className="text-sm font-semibold text-white mb-4">Daily Users Over Time</p>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={stats?.daily_users_history ?? []}>
                <GreenGradient id="usersGrad" />
                <CartesianGrid {...GRID_COLORS} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickFormatter={(v: string) => format(new Date(v), 'MMM d')} tick={AXIS_TICK} tickLine={false} axisLine={false} interval={6} />
                <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltipStyle />} />
                <Area type="monotone" dataKey="value" name="Users" stroke="#22c55e" strokeWidth={2} fill="url(#usersGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className={CHART_CARD}>
            <p className="text-sm font-semibold text-white mb-4">Sensors Installed Over Time</p>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={stats?.sensors_history ?? []}>
                <defs>
                  <linearGradient id="sensorsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid {...GRID_COLORS} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickFormatter={(v: string) => format(new Date(v), 'MMM d')} tick={AXIS_TICK} tickLine={false} axisLine={false} interval={6} />
                <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltipStyle />} />
                <Area type="monotone" dataKey="value" name="Sensors" stroke="#06b6d4" strokeWidth={2} fill="url(#sensorsGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Data points full width */}
        <div className={CHART_CARD}>
          <p className="text-sm font-semibold text-white mb-4">
            Data Points Collected Per Day
            {stats && (
              <span className="text-accent-green text-xs ml-2 font-normal">
                ↑ {stats.data_points_monthly_delta_pct}% this month
              </span>
            )}
          </p>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={stats?.data_points_history ?? []}>
              <GreenGradient id="dpGrad" />
              <CartesianGrid {...GRID_COLORS} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tickFormatter={(v: string) => format(new Date(v), 'MMM d')} tick={AXIS_TICK} tickLine={false} axisLine={false} interval={4} />
              <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip content={<ChartTooltipStyle />} />
              <Area type="monotone" dataKey="value" name="Data Points" stroke="#22c55e" strokeWidth={2} fill="url(#dpGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Distribution section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Sensor models */}
          <div className={CHART_CARD}>
            <p className="text-sm font-semibold text-white mb-4">Sensor Models</p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={modelData} layout="vertical" margin={{ left: 0 }}>
                <CartesianGrid {...GRID_COLORS} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={AXIS_TICK} tickLine={false} axisLine={false} />
                <YAxis dataKey="name" type="category" tick={{ ...AXIS_TICK, fontSize: 10 }} tickLine={false} axisLine={false} width={110} />
                <Tooltip content={<ChartTooltipStyle />} />
                <Bar dataKey="value" name="Count" fill="#06b6d4" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Active vs inactive */}
          <div className={CHART_CARD}>
            <p className="text-sm font-semibold text-white mb-4">Sensor Status</p>
            <div className="relative flex items-center justify-center" style={{ height: 180 }}>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={sensorStatusPie} cx="50%" cy="50%" innerRadius="55%" outerRadius="75%" dataKey="value" startAngle={90} endAngle={-270}>
                    {sensorStatusPie.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltipStyle />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-bold text-white">{activeSensorPct}%</span>
                <span className="text-xs text-gray-400">Active</span>
              </div>
            </div>
            <div className="flex justify-center gap-4 mt-2">
              {sensorStatusPie.map((e) => (
                <div key={e.name} className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: e.color }} />
                  <span className="text-xs text-gray-400">{e.name} ({e.value})</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tree status */}
          <div className={CHART_CARD}>
            <p className="text-sm font-semibold text-white mb-4">Tree Status Distribution</p>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={treeStatusPie} cx="50%" cy="50%" outerRadius="70%" dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                  {treeStatusPie.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltipStyle />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Leaderboard + Districts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Leaderboard */}
          <div className={CHART_CARD}>
            <p className="text-sm font-semibold text-white mb-4">Top Users by Assigned Trees</p>
            <div className="space-y-2">
              {leaderboard.map((user, idx) => {
                const maxCount = leaderboard[0]?.assigned_trees_count ?? 1
                return (
                  <div key={user.id} className="flex items-center gap-3">
                    <span
                      className="w-6 text-center text-sm font-bold tabular-nums shrink-0"
                      style={{ color: RANK_COLORS[idx] ?? '#6b7280' }}
                    >
                      {idx + 1}
                    </span>
                    <span className="text-sm text-white flex-1 truncate">{user.username}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${(user.assigned_trees_count / maxCount) * 100}%`,
                            backgroundColor: RANK_COLORS[idx] ?? '#6b7280',
                          }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 tabular-nums w-4 text-right">{user.assigned_trees_count}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Districts */}
          <div className={CHART_CARD}>
            <p className="text-sm font-semibold text-white mb-4">Sensors by District</p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={districtCounts} layout="vertical" margin={{ left: 0 }}>
                <CartesianGrid {...GRID_COLORS} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={AXIS_TICK} tickLine={false} axisLine={false} />
                <YAxis dataKey="district" type="category" tick={{ ...AXIS_TICK, fontSize: 10 }} tickLine={false} axisLine={false} width={130} />
                <Tooltip content={<ChartTooltipStyle />} />
                <Bar dataKey="sensor_count" name="Sensors" fill="#22c55e" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
