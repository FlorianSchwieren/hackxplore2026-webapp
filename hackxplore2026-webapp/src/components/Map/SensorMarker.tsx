import { memo } from 'react'
import { Marker } from 'react-map-gl/maplibre'
import type { Sensor } from '@/types'

function SignalSvg() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="15" r="2" fill="white" />
      <path
        d="M8.5 12C9.5 10.5 10.7 9.5 12 9.5C13.3 9.5 14.5 10.5 15.5 12"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M5 8.5C7 6 9.3 4.5 12 4.5C14.7 4.5 17 6 19 8.5"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
        opacity="0.6"
      />
    </svg>
  )
}

function WarningBadge() {
  return (
    <div
      style={{
        position: 'absolute',
        top: -3,
        right: -3,
        width: 10,
        height: 10,
        borderRadius: '50%',
        backgroundColor: '#f97316',
        border: '1.5px solid #0a0a0a',
      }}
    />
  )
}

interface SensorMarkerProps {
  sensor: Sensor
  isSelected: boolean
  onClick: () => void
}

const SensorMarker = memo(function SensorMarker({ sensor, isSelected, onClick }: SensorMarkerProps) {
  const isActive = sensor.status === 'active'
  const color = isActive ? '#06b6d4' : '#6b7280'
  const size = isSelected ? 38 : 30

  const lastActivityMs = Date.now() - new Date(sensor.last_activity).getTime()
  const staleActivity = isActive && lastActivityMs > 24 * 60 * 60 * 1000

  return (
    <Marker longitude={sensor.lng} latitude={sensor.lat} anchor="center" onClick={(e) => { e.originalEvent.stopPropagation(); onClick() }}>
      <div
        style={{ position: 'relative', width: size, height: size, cursor: 'pointer' }}
        title={`${sensor.name} — ${sensor.status}`}
      >
        <div
          style={{
            width: size,
            height: size,
            borderRadius: '50%',
            backgroundColor: color,
            border: isSelected ? '2px solid white' : '1.5px solid rgba(255,255,255,0.3)',
            boxShadow: isSelected
              ? `0 0 0 3px ${color}60, 0 0 20px ${color}80`
              : `0 0 8px ${color}50, 0 2px 4px rgba(0,0,0,0.4)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: isActive ? 1 : 0.55,
            transition: 'all 0.2s',
          }}
        >
          <SignalSvg />
        </div>
        {staleActivity && <WarningBadge />}
      </div>
    </Marker>
  )
})

export default SensorMarker
