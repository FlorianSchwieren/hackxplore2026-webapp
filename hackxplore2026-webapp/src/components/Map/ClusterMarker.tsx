import { Marker } from 'react-map-gl/maplibre'

interface ClusterMarkerProps {
  longitude: number
  latitude: number
  count: number
  onClick: () => void
}

export default function ClusterMarker({ longitude, latitude, count, onClick }: ClusterMarkerProps) {
  const size = count < 10 ? 36 : count < 50 ? 44 : 52

  return (
    <Marker longitude={longitude} latitude={latitude} anchor="center" onClick={(e) => { e.originalEvent.stopPropagation(); onClick() }}>
      <div
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          backgroundColor: 'rgba(34, 197, 94, 0.15)',
          border: '2px solid rgba(34, 197, 94, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          boxShadow: '0 0 16px rgba(34, 197, 94, 0.3)',
        }}
      >
        <span style={{ color: '#22c55e', fontSize: 13, fontWeight: 600 }}>{count}</span>
      </div>
    </Marker>
  )
}
