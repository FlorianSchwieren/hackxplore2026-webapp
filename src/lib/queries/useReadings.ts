import { useQuery } from '@tanstack/react-query'
import { supabase, USE_MOCK } from '@/lib/supabase'
import { mockReadings } from '@/lib/mock/readings'
import type { SensorReading } from '@/types'

export function useTreeReadings(treeId: string | null) {
  return useQuery({
    queryKey: ['readings', 'tree', treeId],
    queryFn: async (): Promise<SensorReading[]> => {
      if (!treeId) return []
      if (USE_MOCK) return mockReadings.filter((r) => r.tree_id === treeId)
      const since = new Date()
      since.setDate(since.getDate() - 30)
      const { data, error } = await supabase
        .from('sensor_readings')
        .select('*')
        .eq('tree_id', treeId)
        .gte('timestamp', since.toISOString())
        .order('timestamp', { ascending: true })
        .limit(90)
      if (error) throw error
      return data as SensorReading[]
    },
    enabled: !!treeId,
    staleTime: 60 * 1000,
  })
}

export function useSensorReadings(sensorId: string | null) {
  return useQuery({
    queryKey: ['readings', 'sensor', sensorId],
    queryFn: async (): Promise<SensorReading[]> => {
      if (!sensorId) return []
      if (USE_MOCK) return mockReadings.filter((r) => r.sensor_id === sensorId)
      const since = new Date()
      since.setDate(since.getDate() - 30)
      const { data, error } = await supabase
        .from('sensor_readings')
        .select('*')
        .eq('sensor_id', sensorId)
        .gte('timestamp', since.toISOString())
        .order('timestamp', { ascending: true })
        .limit(90)
      if (error) throw error
      return data as SensorReading[]
    },
    enabled: !!sensorId,
    staleTime: 60 * 1000,
  })
}
