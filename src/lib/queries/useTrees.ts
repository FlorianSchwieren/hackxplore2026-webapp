import { useQuery } from '@tanstack/react-query'
import { supabase, USE_MOCK } from '@/lib/supabase'
import { mockTrees } from '@/lib/mock/trees'
import type { Tree } from '@/types'

export function useTrees() {
  return useQuery({
    queryKey: ['trees'],
    queryFn: async (): Promise<Tree[]> => {
      if (USE_MOCK) return mockTrees
      const { data, error } = await supabase.from('trees').select('*').order('name')
      if (error) throw error
      return data as Tree[]
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useTreeDetail(id: string | null) {
  return useQuery({
    queryKey: ['tree', id],
    queryFn: async (): Promise<Tree | null> => {
      if (!id) return null
      if (USE_MOCK) return mockTrees.find((t) => t.id === id) ?? null
      const { data, error } = await supabase.from('trees').select('*').eq('id', id).single()
      if (error) throw error
      return data as Tree
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  })
}
