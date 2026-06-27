import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import { mapSensor, type ApiSensor } from '@/lib/api/mappers'
import { USE_MOCK } from '@/lib/supabase'
import { mockSensors } from '@/lib/mock/sensors'
import type { Sensor } from '@/types'

export function useSensors() {
  return useQuery({
    queryKey: ['sensors'],
    queryFn: async (): Promise<Sensor[]> => {
      if (USE_MOCK) return mockSensors
      const rows = await apiFetch<ApiSensor[]>('/sensors')
      return rows.map(mapSensor)
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useSensorDetail(id: string | null) {
  return useQuery({
    queryKey: ['sensor', id],
    queryFn: async (): Promise<Sensor | null> => {
      if (!id) return null
      if (USE_MOCK) return mockSensors.find((s) => s.id === id) ?? null
      const rows = await apiFetch<ApiSensor[]>('/sensors')
      const sensor = rows.find((row) => row.id === id)
      return sensor ? mapSensor(sensor) : null
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  })
}
