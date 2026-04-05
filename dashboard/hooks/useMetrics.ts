'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { OverviewMetrics } from '@/lib/types'

export function useMetrics(orgId: string) {
  return useQuery<OverviewMetrics>({
    queryKey: ['metrics', orgId],
    queryFn: () => api.get('/flow-metrics'),
    enabled: !!orgId,
    refetchInterval: 10_000,
    staleTime: 5_000,
  })
}
