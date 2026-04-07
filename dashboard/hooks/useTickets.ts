'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Ticket, TicketCreate, TicketUpdate } from '@/lib/types'

export function useTickets(
  orgId: string,
  filters?: { status?: string; flow_type?: string; priority?: string }
) {
  return useQuery<{ items: Ticket[]; total: number }>({
    queryKey: ['tickets', orgId, filters],
    queryFn: () => {
      const params = new URLSearchParams()
      if (filters?.status) params.set('status', filters.status)
      if (filters?.flow_type) params.set('flow_type', filters.flow_type)
      if (filters?.priority) params.set('priority', filters.priority)
      const qs = params.toString()
      return api.get(`/tickets${qs ? `?${qs}` : ''}`)
    },
    enabled: !!orgId,
    refetchInterval: 10_000,
    staleTime: 5_000,
  })
}

export function useTicket(orgId: string, ticketId: string) {
  return useQuery<Ticket>({
    queryKey: ['ticket', orgId, ticketId],
    queryFn: () => api.get(`/tickets/${ticketId}`),
    enabled: !!orgId && !!ticketId,
  })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: TicketCreate) => api.post('/tickets', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
    },
  })
}

export function useUpdateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ticketId, body }: { ticketId: string; body: TicketUpdate }) =>
      api.patch(`/tickets/${ticketId}`, body),
    onSuccess: (_data, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}

export function useExecuteTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ticketId: string) => api.post(`/tickets/${ticketId}/execute`),
    onSuccess: (_data, ticketId) => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}
