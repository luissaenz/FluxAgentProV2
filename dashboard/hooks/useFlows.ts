import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useCurrentOrg } from './useCurrentOrg'

export interface FlowInfo {
  flow_type: string
  name: string
  description?: string
  input_schema?: Record<string, unknown>
}

export function useFlows() {
  const { orgId } = useCurrentOrg()

  return useQuery<FlowInfo[]>({
    queryKey: ['flows', orgId],
    queryFn: async () => {
      const result = await api.get('/flows/available')
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