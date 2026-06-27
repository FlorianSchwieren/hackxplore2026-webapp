import { useQuery } from '@tanstack/react-query'
import { apiFetch, KARLSRUHE_BBOX } from '@/lib/api/client'
import { mapTree, type ApiTree, type ApiTreeDetail } from '@/lib/api/mappers'
import { USE_MOCK } from '@/lib/supabase'
import { mockTrees } from '@/lib/mock/trees'
import type { Tree } from '@/types'

export function useTrees() {
  return useQuery({
    queryKey: ['trees'],
    queryFn: async (): Promise<Tree[]> => {
      if (USE_MOCK) return mockTrees
      const payload = await apiFetch<{ count: number; trees: ApiTree[] }>(
        `/trees?bbox=${KARLSRUHE_BBOX}&limit=2000`,
      )
      return payload.trees.map((tree) => mapTree(tree))
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
      const detail = await apiFetch<ApiTreeDetail>(`/trees/${id}`)
      return mapTree(detail, detail)
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  })
}
