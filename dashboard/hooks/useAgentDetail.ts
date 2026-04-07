'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AgentDetail } from '@/lib/types'

export function useAgentDetail(orgId: string, agentId: string) {
  return useQuery<AgentDetail>({
    queryKey: ['agent-detail', orgId, agentId],
    queryFn: () => api.get(`/agents/${agentId}/detail`),
    enabled: !!orgId && !!agentId,
    refetchInterval: 15_000,
    staleTime: 10_000,
  })
}
