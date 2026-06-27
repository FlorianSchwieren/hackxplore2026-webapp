import { useQuery } from '@tanstack/react-query'
import { supabase, USE_MOCK } from '@/lib/supabase'
import { mockSensors } from '@/lib/mock/sensors'
import type { Sensor } from '@/types'

export function useSensors() {
  return useQuery({
    queryKey: ['sensors'],
    queryFn: async (): Promise<Sensor[]> => {
      if (USE_MOCK) return mockSensors
      const { data, error } = await supabase.from('sensors').select('*').order('name')
      if (error) throw error
      return data as Sensor[]
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
      const { data, error } = await supabase.from('sensors').select('*').eq('id', id).single()
      if (error) throw error
      return data as Sensor
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  })
}
