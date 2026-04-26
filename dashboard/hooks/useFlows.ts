import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useCurrentOrg } from './useCurrentOrg'

export interface FlowInfo {
  flow_type: string
  name: string
  description?: string
  input_schema?: Record<string, unknown>
  category?: string
}

export interface UseFlowsOptions {
  category?: string
  excludeSystem?: boolean
}

export function useFlows(options: UseFlowsOptions = {}) {
  const { orgId } = useCurrentOrg()

  return useQuery<FlowInfo[]>({
    queryKey: ['flows', orgId, options.category, options.excludeSystem],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (options.category) params.append('category', options.category)
      if (options.excludeSystem) params.append('exclude_system', 'true')
      
      const result = await api.get(`/flows/available?${params.toString()}`)
      return result.flows || []
    },
    enabled: !!orgId,
  })
}

export async function runFlow(flowType: string, inputData: Record<string, unknown>) {
  const result = await api.post(`/flows/${flowType}/run`, {
    input_data: inputData,
  })
  return result
}