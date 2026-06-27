import { useCallback, useMemo, useState } from 'react'
import MapGL, {
  Layer,
  Marker,
  NavigationControl,
  Source,
  type LayerProps,
  type MapLayerMouseEvent,
  type ViewStateChangeEvent,
} from 'react-map-gl/maplibre'
import { useMapContext } from '@/context/MapContext'
import { useTrees } from '@/lib/queries/useTrees'
import { useSensors } from '@/lib/queries/useSensors'
import MapFilterPanel from './MapFilterPanel'
import type { Sensor, Tree } from '@/types'

import GreenTreeImg from '@/assets/icons/green-tree.png'
import RedTreeImg from '@/assets/icons/red-tree.png'
import YellowTreeImg from '@/assets/icons/yellow-tree.png'
import SensorImg from '@/assets/icons/sensor.png'

const STADIA_KEY = import.meta.env.VITE_STADIA_API_KEY as string | undefined
const MAP_STYLE = STADIA_KEY
  ? `https://tiles.stadiamaps.com/styles/alidade_smooth_dark.json?api_key=${STADIA_KEY}`
  : 'https://tiles.openfreemap.org/styles/liberty'

const KARLSRUHE = { longitude: 8.3841496, latitude: 49.0005022 }

const TREE_STATUS_COLORS: Record<string, string> = {
  dry: '#ef4444', low: '#f97316', normal: '#22c55e', moist: '#06b6d4',
}
const SENSOR_COLORS: Record<string, string> = {
  active: '#06b6d4', inactive: '#6b7280',
}

// ── Shared constants ─────────────────────────────────────────────────────────

const INDIVIDUAL_ICON_SIZE: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['zoom'],
  11, 0.10,
  14, 0.12,
  17, 0.14,
]

const CLUSTER_SETTINGS = { clusterMaxZoom: 16, clusterRadius: 60 } as const

// Icon size scales with cluster count
const CLUSTER_ICON_SIZE: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['get', 'point_count'],
  2,   0.12,
  20,  0.16,
  100, 0.20,
  500, 0.24,
]

// Pick the tree icon that matches the most urgent status in the cluster:
// any dry → red icon, any low → yellow icon, otherwise green
const TREE_CLUSTER_ICON: maplibregl.ExpressionSpecification = [
  'case',
  ['>', ['get', 'count_dry'], 0], 'tree-red',
  ['>', ['get', 'count_low'], 0], 'tree-yellow',
  'tree-green',
]

// ── Layer definitions ────────────────────────────────────────────────────────

// Tree clusters → tree icon (coloured by urgency) + count badge top-right
const treeClusterLayer: LayerProps = {
  id: 'tree-clusters',
  type: 'symbol',
  source: 'trees',
  filter: ['has', 'point_count'],
  layout: {
    'icon-image': TREE_CLUSTER_ICON,
    'icon-anchor': 'center',
    'icon-allow-overlap': true,
    'icon-size': CLUSTER_ICON_SIZE,
    'text-field': '{point_count_abbreviated}',
    'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
    'text-size': 11,
    'text-anchor': 'center',
    'text-offset': [1.3, -1.3] as [number, number],
    'text-allow-overlap': true,
    'text-ignore-placement': true,
  },
  paint: {
    'icon-opacity': 0.88,
    'text-color': '#ffffff',
    'text-halo-color': '#1a1a1a',
    'text-halo-width': 1.8,
  },
}

// Sensor clusters → sensor icon + count badge
const sensorClusterLayer: LayerProps = {
  id: 'sensor-clusters',
  type: 'symbol',
  source: 'sensors',
  filter: ['has', 'point_count'],
  layout: {
    'icon-image': 'sensor-icon',
    'icon-anchor': 'center',
    'icon-allow-overlap': true,
    'icon-size': CLUSTER_ICON_SIZE,
    'text-field': '{point_count_abbreviated}',
    'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
    'text-size': 11,
    'text-anchor': 'center',
    'text-offset': [1.3, -1.3] as [number, number],
    'text-allow-overlap': true,
    'text-ignore-placement': true,
  },
  paint: {
    'icon-opacity': 0.88,
    'text-color': '#ffffff',
    'text-halo-color': '#1a1a1a',
    'text-halo-width': 1.8,
  },
}

// Individual trees — PNG icon coloured by status
const treePointsLayer: LayerProps = {
  id: 'tree-points',
  type: 'symbol',
  source: 'trees',
  filter: ['!', ['has', 'point_count']],
  layout: {
    'icon-image': [
      'match', ['get', 'status'],
      'dry',    'tree-red',
      'low',    'tree-yellow',
      'normal', 'tree-green',
      'moist',  'tree-green',
      'tree-green',
    ] as maplibregl.ExpressionSpecification,
    'icon-anchor': 'bottom',
    'icon-allow-overlap': true,
    'icon-size': INDIVIDUAL_ICON_SIZE,
  },
  paint: { 'icon-opacity': 0.88 },
}

// Individual sensors — PNG icon
const sensorPointsLayer: LayerProps = {
  id: 'sensor-points',
  type: 'symbol',
  source: 'sensors',
  filter: ['!', ['has', 'point_count']],
  layout: {
    'icon-image': 'sensor-icon',
    'icon-anchor': 'center',
    'icon-allow-overlap': true,
    'icon-size': INDIVIDUAL_ICON_SIZE,
  },
  paint: {
    'icon-opacity': [
      'match', ['get', 'status'], 'active', 0.88, 0.45,
    ] as maplibregl.ExpressionSpecification,
  },
}

// ── Image loader ─────────────────────────────────────────────────────────────

async function loadMapImages(map: maplibregl.Map) {
  const entries: Array<[string, string]> = [
    ['tree-green',  GreenTreeImg],
    ['tree-red',    RedTreeImg],
    ['tree-yellow', YellowTreeImg],
    ['sensor-icon', SensorImg],
  ]
  await Promise.all(
    entries.map(async ([name, url]) => {
      if (map.hasImage(name)) return
      const { data } = await map.loadImage(url)
      if (!map.hasImage(name)) map.addImage(name, data)
    })
  )
}

const STALE_MS = 24 * 60 * 60 * 1000

// ── Component ────────────────────────────────────────────────────────────────

export default function MapView() {
  const { mapRef, filters, selectedEntity, selectTree, selectSensor, clearSelection } =
    useMapContext()
  const { data: trees = [] } = useTrees()
  const { data: sensors = [] } = useSensors()
  const [imagesReady, setImagesReady] = useState(false)

  const filteredTrees = useMemo(
    () => trees.filter((t) => filters.treeStatus[t.humidity_status]),
    [trees, filters.treeStatus]
  )
  const filteredSensors = useMemo(
    () => sensors.filter((s) => filters.sensorStatus[s.status]),
    [sensors, filters.sensorStatus]
  )

  const treeGeoJSON = useMemo<GeoJSON.FeatureCollection>(
    () => ({
      type: 'FeatureCollection',
      features: filteredTrees.map((t) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [t.lng, t.lat] },
        properties: { id: t.id, status: t.humidity_status },
      })),
    }),
    [filteredTrees]
  )

  const sensorGeoJSON = useMemo<GeoJSON.FeatureCollection>(
    () => ({
      type: 'FeatureCollection',
      features: filteredSensors.map((s) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [s.lng, s.lat] },
        properties: {
          id: s.id,
          status: s.status,
          stale: s.status === 'active' && Date.now() - new Date(s.last_activity).getTime() > STALE_MS,
        },
      })),
    }),
    [filteredSensors]
  )

  const selectedTree = useMemo<Tree | null>(
    () => selectedEntity.type === 'tree' && selectedEntity.id
      ? (filteredTrees.find((t) => t.id === selectedEntity.id) ?? null)
      : null,
    [selectedEntity, filteredTrees]
  )
  const selectedSensor = useMemo<Sensor | null>(
    () => selectedEntity.type === 'sensor' && selectedEntity.id
      ? (filteredSensors.find((s) => s.id === selectedEntity.id) ?? null)
      : null,
    [selectedEntity, filteredSensors]
  )

  const handleLoad = useCallback((e: { target: maplibregl.Map }) => {
    loadMapImages(e.target).then(() => setImagesReady(true)).catch(console.error)
  }, [])

  const handleMove = useCallback((_e: ViewStateChangeEvent) => {}, [])

  const handleMapClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const map = mapRef.current?.getMap()
      if (!map) return

      const features = map.queryRenderedFeatures(e.point, {
        layers: ['tree-points', 'tree-clusters', 'sensor-points', 'sensor-clusters'],
      })

      if (!features.length) { clearSelection(); return }

      const f = features[0]

      // Zoom into cluster on click
      if ((f.layer.id === 'tree-clusters' || f.layer.id === 'sensor-clusters') && f.properties?.cluster) {
        const clusterId = f.properties.cluster_id as number
        const sourceId = f.layer.id === 'tree-clusters' ? 'trees' : 'sensors'
        const source = map.getSource(sourceId) as maplibregl.GeoJSONSource
        const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number]
        source.getClusterExpansionZoom(clusterId)
          .then((z) => mapRef.current?.flyTo({ center: coords, zoom: z, duration: 500 }))
          .catch(() => {})
        return
      }

      if (f.layer.id === 'sensor-points' && f.properties?.id) {
        selectSensor(f.properties.id as string); return
      }
      if (f.properties?.id) selectTree(f.properties.id as string)
    },
    [mapRef, selectTree, selectSensor, clearSelection]
  )

  const setCursor = useCallback(
    (cursor: string) => (e: MapLayerMouseEvent) => { e.target.getCanvas().style.cursor = cursor },
    []
  )

  return (
    <div className="absolute inset-0">
      <MapGL
        ref={mapRef}
        initialViewState={{ longitude: KARLSRUHE.longitude, latitude: KARLSRUHE.latitude, zoom: 13 }}
        onLoad={handleLoad}
        onMove={handleMove}
        onClick={handleMapClick}
        onMouseEnter={setCursor('pointer')}
        onMouseLeave={setCursor('')}
        mapStyle={MAP_STYLE}
        minZoom={10}
        maxZoom={19}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={['tree-points', 'tree-clusters', 'sensor-points', 'sensor-clusters']}
      >
        <NavigationControl position="bottom-right" style={{ marginBottom: '16px', marginRight: '16px' }} />

        {/* Trees — clustered with progressive zoom splitting */}
        <Source
          id="trees"
          type="geojson"
          data={treeGeoJSON}
          cluster
          {...CLUSTER_SETTINGS}
          clusterProperties={{
            count_dry:    ['+', ['case', ['==', ['get', 'status'], 'dry'],    1, 0]],
            count_low:    ['+', ['case', ['==', ['get', 'status'], 'low'],    1, 0]],
            count_normal: ['+', ['case', ['==', ['get', 'status'], 'normal'], 1, 0]],
            count_moist:  ['+', ['case', ['==', ['get', 'status'], 'moist'],  1, 0]],
          }}
        >
          {imagesReady && <Layer {...treeClusterLayer} />}
          {imagesReady && <Layer {...treePointsLayer} />}
        </Source>

        {/* Sensors — also clustered */}
        <Source
          id="sensors"
          type="geojson"
          data={sensorGeoJSON}
          cluster
          {...CLUSTER_SETTINGS}
        >
          {imagesReady && <Layer {...sensorClusterLayer} />}
          {imagesReady && <Layer {...sensorPointsLayer} />}
        </Source>

        {/* Selected tree — glow ring at icon base */}
        {selectedTree && (
          <Marker longitude={selectedTree.lng} latitude={selectedTree.lat} anchor="bottom">
            <div style={{
              width: 20, height: 20, borderRadius: '50%',
              border: '2.5px solid white', pointerEvents: 'none',
              boxShadow: `0 0 0 3px ${TREE_STATUS_COLORS[selectedTree.humidity_status]}80, 0 0 16px ${TREE_STATUS_COLORS[selectedTree.humidity_status]}`,
            }} />
          </Marker>
        )}

        {/* Selected sensor — glow ring */}
        {selectedSensor && (
          <Marker longitude={selectedSensor.lng} latitude={selectedSensor.lat} anchor="center">
            <div style={{
              width: 24, height: 24, borderRadius: '50%',
              border: '2.5px solid white', pointerEvents: 'none',
              boxShadow: `0 0 0 3px ${SENSOR_COLORS[selectedSensor.status]}80, 0 0 16px ${SENSOR_COLORS[selectedSensor.status]}`,
            }} />
          </Marker>
        )}
      </MapGL>

      <MapFilterPanel />
    </div>
  )
}
