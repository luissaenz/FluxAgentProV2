'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { PaginatedTasks } from '@/lib/types'

interface TaskFilters {
  status?: string
  flow_type?: string
  limit?: number
  offset?: number
}

export function useTasks(orgId: string, filters?: TaskFilters) {
  return useQuery<PaginatedTasks>({
    queryKey: ['tasks', orgId, filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters?.status) params.set('status', filters.status)
      if (filters?.flow_type) params.set('flow_type', filters.flow_type)
      if (filters?.limit) params.set('limit', String(filters.limit))
      if (filters?.offset) params.set('offset', String(filters.offset))
      const qs = params.toString()
      return api.get(`/tasks${qs ? `?${qs}` : ''}`)
    },
    enabled: !!orgId,
    staleTime: 5000,
    retry: 2,
  })
}
