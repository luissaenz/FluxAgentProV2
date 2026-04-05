'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { FlowTypeMetrics, FlowRun } from '@/lib/types'

export function useFlowMetrics(orgId: string) {
  return useQuery<FlowTypeMetrics[]>({
    queryKey: ['flow-metrics-by-type', orgId],
    queryFn: () => api.get('/flow-metrics/by-type'),
    enabled: !!orgId,
    refetchInterval: 10_000,
    staleTime: 5_000,
  })
}

export function useFlowRuns(orgId: string, flowType: string) {
  return useQuery<FlowRun[]>({
    queryKey: ['flow-runs', orgId, flowType],
    queryFn: () => api.get(`/flow-metrics/by-type/${flowType}/runs`),
    enabled: !!orgId && !!flowType,
    staleTime: 5_000,
  })
}
