import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import { mapReading, type ApiReading } from '@/lib/api/mappers'
import { USE_MOCK } from '@/lib/supabase'
import { mockReadings } from '@/lib/mock/readings'
import type { SensorReading } from '@/types'

export function useTreeReadings(treeId: string | null) {
  return useQuery({
    queryKey: ['tree-readings', treeId],
    queryFn: async (): Promise<SensorReading[]> => {
      if (!treeId) return []
      if (USE_MOCK) return mockReadings.filter((r) => r.tree_id === treeId)
      const payload = await apiFetch<{ tree_id: string; readings: ApiReading[] }>(
        `/trees/${treeId}/readings?days=30&limit=90`,
      )
      return payload.readings.map((reading) => mapReading(treeId, reading))
    },
    enabled: !!treeId,
    staleTime: 60 * 1000,
  })
}

export function useSensorReadings(_sensorId: string | null, treeId: string | null) {
  return useTreeReadings(treeId)
}
