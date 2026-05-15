'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Approval } from '@/lib/types'

export function useApprovals(orgId: string) {
  const queryClient = useQueryClient()

  const query = useQuery<Approval[]>({
    queryKey: ['approvals', orgId],
    queryFn: () => api.get('/approvals'),
    enabled: !!orgId,
    staleTime: 2000,
  })

  const approve = useMutation({
    mutationFn: async ({ task_id, notes }: { task_id: string; notes?: string }) =>
      api.post(`/approvals/${task_id}`, { action: 'approve', notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals', orgId] })
      queryClient.invalidateQueries({ queryKey: ['tasks', orgId] })
    },
  })

  const reject = useMutation({
    mutationFn: async ({ task_id, notes }: { task_id: string; notes?: string }) =>
      api.post(`/approvals/${task_id}`, { action: 'reject', notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals', orgId] })
      queryClient.invalidateQueries({ queryKey: ['tasks', orgId] })
    },
  })

  return { ...query, approve, reject }
}
