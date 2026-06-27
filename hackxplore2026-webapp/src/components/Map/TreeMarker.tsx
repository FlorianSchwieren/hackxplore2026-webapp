import { memo } from 'react'
import { Marker } from 'react-map-gl/maplibre'
import { motion } from 'framer-motion'
import type { Tree, HumidityStatus } from '@/types'

const STATUS_COLORS: Record<HumidityStatus, string> = {
  dry: '#ef4444',
  low: '#f97316',
  normal: '#22c55e',
  moist: '#06b6d4',
}

function TreeSvg() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 3C8.5 3 6 6 6 9C6 11.5 7.5 13.5 9.5 14.8L9 21H15L14.5 14.8C16.5 13.5 18 11.5 18 9C18 6 15.5 3 12 3Z"
        fill="white"
        opacity="0.95"
      />
    </svg>
  )
}

interface TreeMarkerProps {
  tree: Tree
  isSelected: boolean
  onClick: () => void
}

const TreeMarker = memo(function TreeMarker({ tree, isSelected, onClick }: TreeMarkerProps) {
  const color = STATUS_COLORS[tree.humidity_status]
  const size = isSelected ? 44 : 36

  return (
    <Marker longitude={tree.lng} latitude={tree.lat} anchor="center" onClick={(e) => { e.originalEvent.stopPropagation(); onClick() }}>
      <motion.div
        style={{ width: size, height: size, cursor: 'pointer' }}
        animate={
          tree.humidity_status === 'dry'
            ? { scale: [1, 1.15, 1], opacity: [1, 0.8, 1] }
            : { scale: 1, opacity: 1 }
        }
        transition={
          tree.humidity_status === 'dry'
            ? { duration: 2, repeat: Infinity, ease: 'easeInOut' }
            : {}
        }
        whileHover={{ scale: 1.1 }}
        title={`${tree.name} — ${tree.humidity_status} (${tree.current_humidity}%)`}
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
              : `0 0 8px ${color}60, 0 2px 4px rgba(0,0,0,0.4)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <TreeSvg />
        </div>
      </motion.div>
    </Marker>
  )
})

export default TreeMarker
