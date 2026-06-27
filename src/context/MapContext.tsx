import React, { createContext, useCallback, useContext, useReducer, useRef, useState } from 'react'
import type { MapRef } from 'react-map-gl/maplibre'
import type { MapFilters, SelectedEntity } from '@/types'

interface MapContextValue {
  selectedEntity: SelectedEntity
  selectTree: (id: string) => void
  selectSensor: (id: string) => void
  clearSelection: () => void
  filters: MapFilters
  toggleFilter: (category: 'sensorStatus' | 'treeStatus', key: string) => void
  resetFilters: () => void
  mapRef: React.RefObject<MapRef>
  flyTo: (lat: number, lng: number, zoom?: number) => void
  isStatsPanelOpen: boolean
  toggleStatsPanel: () => void
}

const MapContext = createContext<MapContextValue | null>(null)

const DEFAULT_FILTERS: MapFilters = {
  sensorStatus: { active: true, inactive: true },
  treeStatus: { dry: true, low: true, normal: true, moist: true },
}

type FilterAction =
  | { type: 'TOGGLE_SENSOR_STATUS'; key: string }
  | { type: 'TOGGLE_TREE_STATUS'; key: string }
  | { type: 'RESET' }

function filtersReducer(state: MapFilters, action: FilterAction): MapFilters {
  switch (action.type) {
    case 'TOGGLE_SENSOR_STATUS':
      return {
        ...state,
        sensorStatus: {
          ...state.sensorStatus,
          [action.key]: !state.sensorStatus[action.key as keyof typeof state.sensorStatus],
        },
      }
    case 'TOGGLE_TREE_STATUS':
      return {
        ...state,
        treeStatus: {
          ...state.treeStatus,
          [action.key]: !state.treeStatus[action.key as keyof typeof state.treeStatus],
        },
      }
    case 'RESET':
      return DEFAULT_FILTERS
    default:
      return state
  }
}

export function MapProvider({ children }: { children: React.ReactNode }) {
  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity>({ type: null, id: null })
  const [filters, dispatch] = useReducer(filtersReducer, DEFAULT_FILTERS)
  const [isStatsPanelOpen, setIsStatsPanelOpen] = useState(false)
  const mapRef = useRef<MapRef>(null)

  const selectTree = useCallback((id: string) => {
    setSelectedEntity({ type: 'tree', id })
  }, [])

  const selectSensor = useCallback((id: string) => {
    setSelectedEntity({ type: 'sensor', id })
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedEntity({ type: null, id: null })
  }, [])

  const toggleFilter = useCallback(
    (category: 'sensorStatus' | 'treeStatus', key: string) => {
      if (category === 'sensorStatus') {
        dispatch({ type: 'TOGGLE_SENSOR_STATUS', key })
      } else {
        dispatch({ type: 'TOGGLE_TREE_STATUS', key })
      }
    },
    []
  )

  const resetFilters = useCallback(() => {
    dispatch({ type: 'RESET' })
  }, [])

  const flyTo = useCallback((lat: number, lng: number, zoom = 16) => {
    mapRef.current?.flyTo({ center: [lng, lat], zoom, duration: 1200 })
  }, [])

  const toggleStatsPanel = useCallback(() => {
    setIsStatsPanelOpen((prev) => !prev)
  }, [])

  return (
    <MapContext.Provider
      value={{
        selectedEntity,
        selectTree,
        selectSensor,
        clearSelection,
        filters,
        toggleFilter,
        resetFilters,
        mapRef,
        flyTo,
        isStatsPanelOpen,
        toggleStatsPanel,
      }}
    >
      {children}
    </MapContext.Provider>
  )
}

export function useMapContext(): MapContextValue {
  const ctx = useContext(MapContext)
  if (!ctx) throw new Error('useMapContext must be used within MapProvider')
  return ctx
}
