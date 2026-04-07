'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { createClient } from '@/lib/supabase'
import type { DomainEvent } from '@/lib/types'

interface TranscriptEvent extends DomainEvent {
  sequence: number
}

export function useFlowTranscript(orgId: string, taskId: string) {
  const [liveEvents, setLiveEvents] = useState<TranscriptEvent[]>([])
  const [isLive, setIsLive] = useState(false)

  // Historico desde API
  const { data: historicalData, isLoading } = useQuery<{
    task_id: string
    flow_type: string
    status: string
    events: TranscriptEvent[]
  }>({
    queryKey: ['transcript', orgId, taskId],
    queryFn: () => api.get(`/transcripts/${taskId}`),
    enabled: !!orgId && !!taskId,
  })

  // Realtime subscription
  useEffect(() => {
    if (!orgId || !taskId) return

    const supabase = createClient()
    const channel = supabase.channel(`transcript:${taskId}`)

    channel
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'domain_events',
          filter: `aggregate_id=eq.${taskId}`,
        },
        (payload) => {
          const newEvent = payload.new as TranscriptEvent
          setLiveEvents((prev) => {
            // Evitar duplicados
            if (prev.some((e) => e.id === newEvent.id)) return prev
            return [...prev, newEvent]
          })
          setIsLive(true)
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          setIsLive(true)
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          setIsLive(false)
        }
      })

    return () => {
      supabase.removeChannel(channel)
      setIsLive(false)
    }
  }, [orgId, taskId])

  // Combinar historico + live
  const allEvents = [...(historicalData?.events ?? []), ...liveEvents]

  // Deduplicar por id
  const seen = new Set<string>()
  const uniqueEvents = allEvents.filter((e) => {
    if (seen.has(e.id)) return false
    seen.add(e.id)
    return true
  })

  // Ordenar por sequence
  uniqueEvents.sort((a, b) => (a.sequence || 0) - (b.sequence || 0))

  return {
    events: uniqueEvents,
    flowType: historicalData?.flow_type,
    status: historicalData?.status,
    isLoading,
    isLive,
  }
}
