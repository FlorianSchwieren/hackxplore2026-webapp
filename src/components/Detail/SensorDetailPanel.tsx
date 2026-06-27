import { X, Radio, CalendarDays, Activity, Battery, BatteryLow, TreePine } from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'
import { useMapContext } from '@/context/MapContext'
import { useSensorDetail } from '@/lib/queries/useSensors'
import { useSensorReadings } from '@/lib/queries/useReadings'
import { useTrees } from '@/lib/queries/useTrees'
import DetailPanelWrapper from './DetailPanelWrapper'
import HumidityChart from './HumidityChart'
import { InlineLoader } from '@/components/common/LoadingSpinner'
import type { HumidityStatus } from '@/types'

const STATUS_BG: Record<string, string> = {
  active: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  inactive: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
}

const HUMIDITY_STATUS_BG: Record<HumidityStatus, string> = {
  dry: 'bg-red-500/15 text-red-400',
  low: 'bg-orange-500/15 text-orange-400',
  normal: 'bg-green-500/15 text-green-400',
  moist: 'bg-cyan-500/15 text-cyan-400',
}

export default function SensorDetailPanel() {
  const { selectedEntity, clearSelection, selectTree } = useMapContext()
  const isOpen = selectedEntity.type === 'sensor' && !!selectedEntity.id
  const { data: sensor, isLoading } = useSensorDetail(isOpen ? selectedEntity.id : null)
  const { data: readings = [] } = useSensorReadings(isOpen ? selectedEntity.id : null)
  const { data: allTrees = [] } = useTrees()

  const coveredTrees = sensor
    ? allTrees.filter((t) => sensor.covered_tree_ids.includes(t.id))
    : []

  // Use first tree's status for chart color, fallback to normal
  const chartStatus: HumidityStatus = coveredTrees[0]?.humidity_status ?? 'normal'

  return (
    <DetailPanelWrapper isOpen={isOpen}>
      {/* Header */}
      <div className="sticky top-0 z-10 flex items-start justify-between px-4 py-4 bg-[rgba(10,10,10,0.92)] backdrop-blur-[8px] border-b border-white/[0.06]">
        <div className="flex-1 min-w-0 pr-4">
          {isLoading || !sensor ? (
            <InlineLoader />
          ) : (
            <>
              <div className="flex items-center gap-2 mb-1">
                <Radio className="w-5 h-5 text-accent-teal shrink-0" />
                <h2 className="text-base font-semibold text-white truncate">{sensor.name}</h2>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full border capitalize ${STATUS_BG[sensor.status]}`}>
                {sensor.status}
              </span>
            </>
          )}
        </div>
        <button onClick={clearSelection} className="p-1.5 text-gray-500 hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors shrink-0">
          <X className="w-5 h-5" />
        </button>
      </div>

      {isLoading || !sensor ? (
        <div className="flex justify-center py-12"><InlineLoader /></div>
      ) : (
        <>
          {/* Info grid */}
          <div className="grid grid-cols-2 gap-3 px-4 py-4">
            {[
              { icon: Radio, label: 'Model', value: sensor.model_type },
              {
                icon: Activity,
                label: 'Last Active',
                value: formatDistanceToNow(new Date(sensor.last_activity), { addSuffix: true }),
              },
              { icon: CalendarDays, label: 'Installed', value: format(new Date(sensor.installed_at), 'MMM d, yyyy') },
              {
                icon: sensor.battery_level !== null && sensor.battery_level < 20 ? BatteryLow : Battery,
                label: 'Battery',
                value: sensor.battery_level !== null ? `${sensor.battery_level}%` : 'Wired',
                color: sensor.battery_level !== null && sensor.battery_level < 20 ? '#f97316' : undefined,
              },
            ].map(({ icon: Icon, label, value, color }) => (
              <div key={label} className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <Icon className="w-3.5 h-3.5 text-gray-500" style={color ? { color } : {}} />
                  <p className="text-xs text-gray-500">{label}</p>
                </div>
                <p className="text-sm text-white font-medium" style={color ? { color } : {}}>{value}</p>
              </div>
            ))}
          </div>

          {/* Covered trees */}
          {coveredTrees.length > 0 && (
            <div className="px-4 mb-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                Covered Trees ({coveredTrees.length})
              </p>
              <div className="flex flex-col gap-2">
                {coveredTrees.map((tree) => (
                  <button
                    key={tree.id}
                    onClick={() => selectTree(tree.id)}
                    className="flex items-center gap-3 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] transition-colors text-left"
                  >
                    <TreePine className="w-4 h-4 text-gray-400 shrink-0" />
                    <span className="text-sm text-white flex-1 truncate">{tree.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${HUMIDITY_STATUS_BG[tree.humidity_status]}`}>
                      {tree.humidity_status}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chart */}
          <div className="px-4 mb-6">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">30-Day Reading History</p>
            {readings.length > 0 ? (
              <HumidityChart readings={readings} status={chartStatus} />
            ) : (
              <p className="text-xs text-gray-500 text-center py-8">No reading data available</p>
            )}
          </div>
        </>
      )}
    </DetailPanelWrapper>
  )
}
