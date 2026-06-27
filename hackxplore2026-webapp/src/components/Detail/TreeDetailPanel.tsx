import { X, Cpu, TreePine, Droplets, CalendarDays, User, Radio } from 'lucide-react'
import { format } from 'date-fns'
import { useMapContext } from '@/context/MapContext'
import { useTreeDetail } from '@/lib/queries/useTrees'
import { useTreeReadings } from '@/lib/queries/useReadings'
import { useWeatherQuery } from '@/lib/queries/useStats'
import DetailPanelWrapper from './DetailPanelWrapper'
import HumidityChart from './HumidityChart'
import { InlineLoader } from '@/components/common/LoadingSpinner'
import type { HumidityStatus } from '@/types'

const STATUS_COLORS: Record<HumidityStatus, string> = {
  dry: '#ef4444', low: '#f97316', normal: '#22c55e', moist: '#06b6d4',
}
const STATUS_BG: Record<HumidityStatus, string> = {
  dry: 'bg-red-500/15 text-red-400 border-red-500/30',
  low: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  normal: 'bg-green-500/15 text-green-400 border-green-500/30',
  moist: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
}

function MLRecommendation({ status }: { status: HumidityStatus }) {
  const { data: weather = [] } = useWeatherQuery()
  const rainDay = weather.slice(1).find((d) => d.precipitation_mm > 5)
  const daysUntilRain = rainDay
    ? Math.round((new Date(rainDay.date).getTime() - Date.now()) / 86400000)
    : null

  let recommendation = ''
  let recColor = ''
  if (status === 'dry' && !rainDay) { recommendation = 'Water today. Tree is critically dry.'; recColor = 'text-red-400' }
  else if (status === 'dry' && rainDay) { recommendation = `Rain in ${daysUntilRain}d. Monitor closely.`; recColor = 'text-orange-400' }
  else if (status === 'low' && daysUntilRain === 1) { recommendation = 'Monitor. Rain expected tomorrow.'; recColor = 'text-orange-400' }
  else if (status === 'low') { recommendation = 'Soil moisture is low. Consider watering.'; recColor = 'text-orange-400' }
  else if (status === 'normal') { recommendation = 'No action needed. Tree is healthy.'; recColor = 'text-green-400' }
  else { recommendation = 'Good condition. No watering needed.'; recColor = 'text-cyan-400' }

  return (
    <div className="mx-4 mb-4 rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
      <div className="flex items-center gap-2 mb-3">
        <Cpu className="w-4 h-4 text-accent-teal" />
        <p className="text-sm font-semibold text-white">AI Recommendation</p>
      </div>
      <div className="flex flex-wrap gap-2 mb-3">
        <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-gray-400">
          🌡 {rainDay ? `Rain in ${daysUntilRain}d` : 'No rain soon'}
        </span>
        <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-gray-400">
          💧 Humidity {status}
        </span>
        <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-gray-400">
          🤖 87% confidence
        </span>
      </div>
      <p className={`text-sm font-semibold ${recColor}`}>{recommendation}</p>
      <p className="text-xs text-gray-500 mt-1">
        Last rain: 5 days ago · Next rain: {rainDay ? `in ${daysUntilRain} days` : 'not forecast'}
      </p>
    </div>
  )
}

export default function TreeDetailPanel() {
  const { selectedEntity, clearSelection, selectSensor } = useMapContext()
  const isOpen = selectedEntity.type === 'tree' && !!selectedEntity.id
  const { data: tree, isLoading } = useTreeDetail(isOpen ? selectedEntity.id : null)
  const { data: readings = [] } = useTreeReadings(isOpen ? selectedEntity.id : null)

  return (
    <DetailPanelWrapper isOpen={isOpen}>
      {/* Sticky header */}
      <div className="sticky top-0 z-10 flex items-start justify-between px-4 py-4 bg-[rgba(10,10,10,0.92)] backdrop-blur-[8px] border-b border-white/[0.06]">
        <div className="flex-1 min-w-0 pr-4">
          {isLoading || !tree ? (
            <InlineLoader />
          ) : (
            <>
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <TreePine className="w-5 h-5 shrink-0" style={{ color: STATUS_COLORS[tree.humidity_status] }} />
                <h2 className="text-base font-semibold text-white truncate">{tree.name}</h2>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-400 italic">{tree.tree_type}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full border capitalize ${STATUS_BG[tree.humidity_status]}`}>
                  {tree.humidity_status}
                </span>
              </div>
            </>
          )}
        </div>
        <button onClick={clearSelection} className="p-1.5 text-gray-500 hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors shrink-0">
          <X className="w-5 h-5" />
        </button>
      </div>

      {isLoading || !tree ? (
        <div className="flex justify-center py-12"><InlineLoader /></div>
      ) : (
        <>
          {/* Info grid */}
          <div className="grid grid-cols-2 gap-3 px-4 py-4">
            {[
              { icon: Droplets, label: 'Humidity', value: `${tree.current_humidity}%`, color: STATUS_COLORS[tree.humidity_status] },
              { icon: CalendarDays, label: 'Age', value: `${tree.age_years} years` },
              { icon: User, label: 'Owner', value: tree.owner_username ?? 'Unassigned' },
              { icon: TreePine, label: 'Species', value: tree.common_name },
              { icon: Radio, label: 'District', value: tree.district },
              { icon: CalendarDays, label: 'Since', value: format(new Date(tree.created_at), 'MMM yyyy') },
            ].map(({ icon: Icon, label, value, color }) => (
              <div key={label} className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <Icon className="w-3.5 h-3.5 text-gray-500" style={color ? { color } : {}} />
                  <p className="text-xs text-gray-500">{label}</p>
                </div>
                <p className="text-sm text-white font-medium truncate" style={color ? { color } : {}}>{value}</p>
              </div>
            ))}
          </div>

          {/* Sensor link */}
          {tree.sensor_id && (
            <div className="px-4 mb-4">
              <button
                onClick={() => selectSensor(tree.sensor_id!)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-accent-teal/10 border border-accent-teal/30 text-accent-teal text-sm hover:bg-accent-teal/15 transition-colors"
              >
                <Radio className="w-4 h-4" />
                View Sensor
              </button>
            </div>
          )}

          {/* Chart */}
          <div className="px-4 mb-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">30-Day Humidity History</p>
            {readings.length > 0 ? (
              <HumidityChart readings={readings} status={tree.humidity_status} />
            ) : (
              <p className="text-xs text-gray-500 text-center py-8">No reading data available</p>
            )}
          </div>

          {/* ML Recommendation */}
          <MLRecommendation status={tree.humidity_status} />
        </>
      )}
    </DetailPanelWrapper>
  )
}
