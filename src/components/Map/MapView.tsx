import { useCallback, useMemo, useState } from 'react'
import MapGL, { NavigationControl } from 'react-map-gl/maplibre'
import type { MapMouseEvent, ViewStateChangeEvent } from 'react-map-gl/maplibre'
import Supercluster from 'supercluster'
import { useMapContext } from '@/context/MapContext'
import { useTrees } from '@/lib/queries/useTrees'
import { useSensors } from '@/lib/queries/useSensors'
import TreeMarker from './TreeMarker'
import SensorMarker from './SensorMarker'
import ClusterMarker from './ClusterMarker'
import MapFilterPanel from './MapFilterPanel'

const STADIA_KEY = import.meta.env.VITE_STADIA_API_KEY as string | undefined

// Use Stadia dark style when API key is present, otherwise fall back to
// OpenFreeMap (free, no auth, works on any domain)
const MAP_STYLE = STADIA_KEY
  ? `https://tiles.stadiamaps.com/styles/alidade_smooth_dark.json?api_key=${STADIA_KEY}`
  : 'https://tiles.openfreemap.org/styles/liberty'

const KARLSRUHE = { longitude: 8.3841496, latitude: 49.0005022 }

interface ViewState {
  longitude: number
  latitude: number
  zoom: number
  pitch?: number
  bearing?: number
}

export default function MapView() {
  const { mapRef, filters, selectedEntity, selectTree, selectSensor, clearSelection } = useMapContext()
  const { data: trees = [] } = useTrees()
  const { data: sensors = [] } = useSensors()

  const [viewState, setViewState] = useState<ViewState>({
    longitude: KARLSRUHE.longitude,
    latitude: KARLSRUHE.latitude,
    zoom: 13,
  })

  const filteredTrees = useMemo(
    () => trees.filter((t) => filters.treeStatus[t.humidity_status]),
    [trees, filters.treeStatus]
  )

  const filteredSensors = useMemo(
    () => sensors.filter((s) => filters.sensorStatus[s.status]),
    [sensors, filters.sensorStatus]
  )

  // Supercluster for trees
  const treePoints = useMemo(
    () =>
      filteredTrees.map((t) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [t.lng, t.lat] },
        properties: { id: t.id, kind: 'tree' as const },
      })),
    [filteredTrees]
  )

  const treeClusters = useMemo(() => {
    if (viewState.zoom >= 12) return null
    const index = new Supercluster({ radius: 60, maxZoom: 12 })
    index.load(treePoints)
    const bbox: [number, number, number, number] = [
      viewState.longitude - 0.5,
      viewState.latitude - 0.35,
      viewState.longitude + 0.5,
      viewState.latitude + 0.35,
    ]
    return { index, clusters: index.getClusters(bbox, Math.floor(viewState.zoom)) }
  }, [treePoints, viewState.zoom, viewState.longitude, viewState.latitude])

  const handleMove = useCallback((e: ViewStateChangeEvent) => {
    setViewState(e.viewState)
  }, [])

  const handleMapClick = useCallback(
    (e: MapMouseEvent) => {
      // Only clear if clicking the map background (not a marker)
      const target = e.originalEvent.target as HTMLElement
      if (target.closest('[data-marker]')) return
      clearSelection()
    },
    [clearSelection]
  )

  return (
    <div className="absolute inset-0">
      <MapGL
        ref={mapRef}
        {...viewState}
        onMove={handleMove}
        onClick={handleMapClick}
        mapStyle={MAP_STYLE}
        minZoom={10}
        maxZoom={19}
        style={{ width: '100%', height: '100%' }}
      >
        <NavigationControl position="bottom-right" style={{ marginBottom: '16px', marginRight: '16px' }} />

        {/* Tree markers or clusters */}
        {viewState.zoom >= 12 || !treeClusters
          ? filteredTrees.map((tree) => (
              <TreeMarker
                key={tree.id}
                tree={tree}
                isSelected={selectedEntity.type === 'tree' && selectedEntity.id === tree.id}
                onClick={() => selectTree(tree.id)}
              />
            ))
          : treeClusters.clusters.map((cluster) => {
              const [lng, lat] = cluster.geometry.coordinates
              if (cluster.properties.cluster) {
                return (
                  <ClusterMarker
                    key={`cluster-${cluster.id}`}
                    longitude={lng}
                    latitude={lat}
                    count={cluster.properties.point_count as number}
                    onClick={() => {
                      const zoom = treeClusters.index.getClusterExpansionZoom(cluster.id as number)
                      mapRef.current?.flyTo({ center: [lng, lat], zoom, duration: 800 })
                    }}
                  />
                )
              }
              const tree = filteredTrees.find((t) => t.id === cluster.properties.id)
              if (!tree) return null
              return (
                <TreeMarker
                  key={tree.id}
                  tree={tree}
                  isSelected={selectedEntity.type === 'tree' && selectedEntity.id === tree.id}
                  onClick={() => selectTree(tree.id)}
                />
              )
            })}

        {/* Sensor markers — always individual (only 15) */}
        {filteredSensors.map((sensor) => (
          <SensorMarker
            key={sensor.id}
            sensor={sensor}
            isSelected={selectedEntity.type === 'sensor' && selectedEntity.id === sensor.id}
            onClick={() => selectSensor(sensor.id)}
          />
        ))}
      </MapGL>

      <MapFilterPanel />
    </div>
  )
}
