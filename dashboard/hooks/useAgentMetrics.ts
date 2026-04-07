import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useCurrentOrg } from './useCurrentOrg'

export interface AgentMetrics {
  agent_role: string
  agent_id: string
  tokens_used: number
}

export function useAgentMetrics() {
  const { orgId } = useCurrentOrg()

  return useQuery<AgentMetrics[]>({
    queryKey: ['agent-metrics', orgId],
    queryFn: async () => {
      const result = await api.get('/flow-metrics/by-agent')
      return result || []
    },
    enabled: !!orgId,
  })
}