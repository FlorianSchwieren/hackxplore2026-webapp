import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import { mapStatsOverview, mapStadtteilCounts, mapWeather, type ApiStadtteil, type ApiStatsOverview, type ApiWeather } from '@/lib/api/mappers'
import { USE_MOCK } from '@/lib/supabase'
import { mockDistrictSensorCounts, mockNetworkStats, mockUsers, mockWeather } from '@/lib/mock/stats'
import type { NetworkStats, UserProfile, WeatherDay } from '@/types'

export function useNetworkStats() {
  return useQuery({
    queryKey: ['network-stats'],
    queryFn: async (): Promise<NetworkStats> => {
      if (USE_MOCK) return mockNetworkStats
      const stats = await apiFetch<ApiStatsOverview>('/stats/overview')
      return mapStatsOverview(stats)
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useLeaderboard() {
  return useQuery({
    queryKey: ['leaderboard'],
    queryFn: async (): Promise<UserProfile[]> => {
      if (USE_MOCK) return mockUsers
      return []
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useWeatherQuery() {
  return useQuery({
    queryKey: ['weather'],
    queryFn: async (): Promise<WeatherDay[]> => {
      if (USE_MOCK) return mockWeather
      const payload = await apiFetch<ApiWeather>('/weather/forecast')
      return mapWeather(payload)
    },
    staleTime: 15 * 60 * 1000,
  })
}

export function useStadtteilStats() {
  return useQuery({
    queryKey: ['stadtteil-stats'],
    queryFn: async () => {
      if (USE_MOCK) return mockDistrictSensorCounts
      const rows = await apiFetch<ApiStadtteil[]>('/stats/by-stadtteil')
      return mapStadtteilCounts(rows)
    },
    staleTime: 10 * 60 * 1000,
  })
}
