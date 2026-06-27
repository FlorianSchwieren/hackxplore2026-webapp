import { useNavigate } from 'react-router-dom'
import { ArrowLeft, AlertTriangle, TrendingUp, CloudRain, MapPin, Sun, Cloud, Droplets } from 'lucide-react'
import {
  ComposedChart, Area, Bar, BarChart,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { format, addDays } from 'date-fns'

const CHART_CARD = 'bg-[rgba(15,15,15,0.6)] rounded-2xl border border-white/[0.06] p-5'
const GRID_COLORS = { stroke: '#1f2937' }
const AXIS_TICK = { fill: '#6b7280', fontSize: 11 }

const TODAY = new Date('2026-06-27')

const RISK_TRAJECTORY = [
  { date: format(addDays(TODAY, 0), 'yyyy-MM-dd'), trees_at_risk: 23, rain_mm: 0 },
  { date: format(addDays(TODAY, 1), 'yyyy-MM-dd'), trees_at_risk: 27, rain_mm: 0 },
  { date: format(addDays(TODAY, 2), 'yyyy-MM-dd'), trees_at_risk: 29, rain_mm: 4.2 },
  { date: format(addDays(TODAY, 3), 'yyyy-MM-dd'), trees_at_risk: 25, rain_mm: 1.0 },
  { date: format(addDays(TODAY, 4), 'yyyy-MM-dd'), trees_at_risk: 30, rain_mm: 0 },
  { date: format(addDays(TODAY, 5), 'yyyy-MM-dd'), trees_at_risk: 36, rain_mm: 0 },
  { date: format(addDays(TODAY, 6), 'yyyy-MM-dd'), trees_at_risk: 41, rain_mm: 0 },
]

const WEATHER_STRIP = [
  { day: 'Fri', icon: 'sun',   temp: 29, precip: 0 },
  { day: 'Sat', icon: 'sun',   temp: 31, precip: 0 },
  { day: 'Sun', icon: 'cloud', temp: 26, precip: 4.2 },
  { day: 'Mon', icon: 'rain',  temp: 22, precip: 1.0 },
  { day: 'Tue', icon: 'sun',   temp: 27, precip: 0 },
  { day: 'Wed', icon: 'sun',   temp: 30, precip: 0 },
  { day: 'Thu', icon: 'sun',   temp: 33, precip: 0 },
]

const DISTRICT_RISK = [
  { district: 'Innenstadt-Ost',  trees: 18 },
  { district: 'Innenstadt-West', trees: 13 },
  { district: 'Südstadt',        trees: 7 },
  { district: 'Weststadt',       trees: 3 },
]

type RiskLevel = 'HIGH' | 'MEDIUM'

const AT_RISK_TREES: {
  name: string
  district: string
  risk: RiskLevel
  shortage_in_days: number
  drivers: string[]
  moisture_pct: number
}[] = [
  { name: 'Blattfürst Heinrich',   district: 'Innenstadt-Ost',  risk: 'HIGH',   shortage_in_days: 2, drivers: ['dry sensor', 'hot forecast'],              moisture_pct: 14 },
  { name: 'Gräfin Laubwerk',       district: 'Innenstadt-West', risk: 'HIGH',   shortage_in_days: 2, drivers: ['dry sensor', 'owner absent'],              moisture_pct: 18 },
  { name: 'Baron von Äst',         district: 'Innenstadt-Ost',  risk: 'HIGH',   shortage_in_days: 3, drivers: ['dry sensor', 'owner absent', 'hot forecast'], moisture_pct: 21 },
  { name: 'Lady Chlorophyll',      district: 'Südstadt',        risk: 'HIGH',   shortage_in_days: 3, drivers: ['dry sensor', 'hot forecast'],              moisture_pct: 23 },
  { name: 'Wurzelkönig Berthold',  district: 'Innenstadt-West', risk: 'MEDIUM', shortage_in_days: 5, drivers: ['low moisture'],                            moisture_pct: 31 },
  { name: 'Tannenherzogin Ursula', district: 'Weststadt',       risk: 'MEDIUM', shortage_in_days: 5, drivers: ['owner absent'],                            moisture_pct: 35 },
  { name: 'Ritter Moosbart',       district: 'Innenstadt-Ost',  risk: 'MEDIUM', shortage_in_days: 6, drivers: ['low moisture', 'hot forecast'],            moisture_pct: 38 },
  { name: 'Prinzessin Birke',      district: 'Südstadt',        risk: 'MEDIUM', shortage_in_days: 7, drivers: ['low moisture'],                            moisture_pct: 42 },
]

function WeatherIcon({ type }: { type: string }) {
  if (type === 'rain')  return <CloudRain className="w-5 h-5 text-accent-teal" />
  if (type === 'cloud') return <Cloud className="w-5 h-5 text-gray-400" />
  return <Sun className="w-5 h-5 text-yellow-400" />
}

function ChartTooltipStyle({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name?: string; color?: string }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[rgba(15,15,15,0.97)] border border-white/[0.08] rounded-xl px-3 py-2 text-xs shadow-glass">
      {label && <p className="text-gray-400 mb-1">{format(new Date(label), 'MMM d')}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color ?? '#fff' }} className="font-semibold">
          {p.name && `${p.name}: `}{typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  )
}

export default function ForecastPage() {
  const navigate = useNavigate()

  return (
    <div className="h-screen overflow-y-auto bg-surface text-white pb-16 panel-scroll">
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
        <span className="text-sm font-semibold text-white">7-Day Forecast</span>
        <span className="ml-2 text-xs text-gray-500 bg-white/[0.04] border border-white/[0.06] rounded-full px-2 py-0.5">mock · model-v0</span>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 space-y-8">

        {/* 1. Hero KPI Strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Trees at Risk Today',        value: '23',         icon: AlertTriangle, color: '#ef4444' },
            { label: 'Predicted Critical by Day 7', value: '41',        icon: TrendingUp,    color: '#f97316' },
            { label: 'Rain Expected',               value: 'Sun · 4.2 mm', icon: CloudRain,  color: '#06b6d4' },
            { label: 'High-Risk Districts',         value: '3',          icon: MapPin,        color: '#f97316' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="rounded-xl bg-white/[0.04] border border-white/[0.06] p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4" style={{ color }} />
                <p className="text-xs text-gray-500">{label}</p>
              </div>
              <p className="text-2xl font-bold tabular-nums text-white">{value}</p>
            </div>
          ))}
        </div>

        {/* 2. 7-Day Risk Trajectory */}
        <div className={CHART_CARD}>
          <p className="text-sm font-semibold text-white mb-1">Trees at Risk — 7-Day Projection</p>
          <p className="text-xs text-gray-500 mb-4">Rain on Sunday briefly reduces risk; heat continues driving critical state beyond.</p>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={RISK_TRAJECTORY} margin={{ top: 4, right: 48, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid {...GRID_COLORS} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(v: string) => format(new Date(v), 'MMM d')}
                tick={AXIS_TICK}
                tickLine={false}
                axisLine={false}
              />
              <YAxis yAxisId="left" tick={AXIS_TICK} tickLine={false} axisLine={false} />
              <YAxis yAxisId="right" orientation="right" tick={{ ...AXIS_TICK, fill: '#06b6d4' }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v} mm`} />
              <Tooltip content={<ChartTooltipStyle />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280', paddingTop: 8 }} />
              <Bar yAxisId="right" dataKey="rain_mm" name="Rain (mm)" fill="#06b6d4" fillOpacity={0.5} radius={[2, 2, 0, 0]} barSize={18} />
              <Area yAxisId="left" type="monotone" dataKey="trees_at_risk" name="Trees at Risk" stroke="#ef4444" strokeWidth={2} fill="url(#riskGrad)" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* 3. Weather Strip */}
        <div>
          <p className="text-sm font-semibold text-white mb-3">Weather Outlook</p>
          <div className="grid grid-cols-7 gap-2">
            {WEATHER_STRIP.map((w) => (
              <div
                key={w.day}
                className={`rounded-xl border p-3 flex flex-col items-center gap-1.5 ${
                  w.precip > 0
                    ? 'bg-accent-teal/[0.08] border-accent-teal/20'
                    : 'bg-white/[0.03] border-white/[0.06]'
                }`}
              >
                <p className="text-xs text-gray-400">{w.day}</p>
                <WeatherIcon type={w.icon} />
                <p className="text-sm font-semibold text-white">{w.temp}°</p>
                {w.precip > 0 ? (
                  <p className="text-xs text-accent-teal">{w.precip} mm</p>
                ) : (
                  <p className="text-xs text-gray-600">— mm</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 4. District Risk + At-Risk Trees side by side on desktop */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* District Risk BarChart */}
          <div className={CHART_CARD}>
            <p className="text-sm font-semibold text-white mb-1">Predicted Trees Needing Water by Day 7</p>
            <p className="text-xs text-gray-500 mb-4">Per district</p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={DISTRICT_RISK} layout="vertical" margin={{ left: 0 }}>
                <CartesianGrid {...GRID_COLORS} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={AXIS_TICK} tickLine={false} axisLine={false} />
                <YAxis
                  dataKey="district"
                  type="category"
                  tick={{ ...AXIS_TICK, fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  width={130}
                />
                <Tooltip content={<ChartTooltipStyle />} />
                <Bar dataKey="trees" name="Trees" fill="#ef4444" fillOpacity={0.8} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Placeholder for future district map */}
          <div className={`${CHART_CARD} flex flex-col justify-between`}>
            <p className="text-sm font-semibold text-white mb-1">Intervention Summary</p>
            <p className="text-xs text-gray-500 mb-4">Recommended actions for the next 48 hours</p>
            <div className="space-y-3 flex-1">
              {[
                { label: 'Dispatch to Innenstadt-Ost',  detail: '8 trees critical within 2 days', color: '#ef4444' },
                { label: 'Notify Innenstadt-West users', detail: 'Owner absences cover 5 trees — request coverage', color: '#f97316' },
                { label: 'Rain on Sunday — hold action', detail: 'Skip Südstadt watering Sat; re-evaluate Mon', color: '#06b6d4' },
              ].map((item) => (
                <div key={item.label} className="flex items-start gap-3 rounded-lg bg-white/[0.03] border border-white/[0.04] p-3">
                  <div className="w-2 h-2 rounded-full mt-1 shrink-0" style={{ backgroundColor: item.color }} />
                  <div>
                    <p className="text-xs font-medium text-white">{item.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 5. At-Risk Tree List */}
        <div>
          <p className="text-sm font-semibold text-white mb-3">At-Risk Trees</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {AT_RISK_TREES.map((tree) => (
              <div key={tree.name} className="rounded-xl bg-white/[0.03] border border-white/[0.06] overflow-hidden">
                <div className="p-4">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <p className="text-sm font-semibold text-white">{tree.name}</p>
                    <span
                      className={`shrink-0 text-xs font-bold px-2 py-0.5 rounded-full ${
                        tree.risk === 'HIGH'
                          ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                          : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                      }`}
                    >
                      {tree.risk}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mb-3">
                    <MapPin className="w-3 h-3 text-gray-500 shrink-0" />
                    <p className="text-xs text-gray-500">{tree.district}</p>
                    <span className="text-gray-600">·</span>
                    <p className="text-xs text-gray-500">shortage in {tree.shortage_in_days}d</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {tree.drivers.map((d) => (
                      <span key={d} className="text-xs text-gray-400 bg-white/[0.06] border border-white/[0.08] rounded-full px-2 py-0.5">
                        {d}
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <Droplets className="w-3 h-3 text-gray-500 shrink-0" />
                    <p className="text-xs text-gray-500 w-12">{tree.moisture_pct}%</p>
                    <div className="flex-1 h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${tree.moisture_pct}%`,
                          backgroundColor: tree.moisture_pct < 25 ? '#ef4444' : tree.moisture_pct < 40 ? '#f97316' : '#22c55e',
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
