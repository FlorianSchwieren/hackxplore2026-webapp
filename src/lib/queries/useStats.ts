import { useQuery } from '@tanstack/react-query'
import { USE_MOCK } from '@/lib/supabase'
import { mockNetworkStats, mockUsers, mockWeather } from '@/lib/mock/stats'
import type { NetworkStats, UserProfile, WeatherDay } from '@/types'

export function useNetworkStats() {
  return useQuery({
    queryKey: ['network-stats'],
    queryFn: async (): Promise<NetworkStats> => {
      if (USE_MOCK) return mockNetworkStats
      // TODO: fetch from Supabase aggregation or edge function
      return mockNetworkStats
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useLeaderboard() {
  return useQuery({
    queryKey: ['leaderboard'],
    queryFn: async (): Promise<UserProfile[]> => {
      if (USE_MOCK) return mockUsers
      // TODO: fetch from user_profiles ordered by assigned_trees_count
      return mockUsers
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useWeather(): WeatherDay[] {
  return mockWeather
}
