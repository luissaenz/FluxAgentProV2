'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { createClient } from '@/lib/supabase'
import type { DomainEvent } from '@/lib/types'

export interface TranscriptEvent extends DomainEvent {
  sequence: number
}

interface TranscriptSnapshot {
  task_id: string
  flow_type: string | null
  status: string
  is_running: boolean
  sync: {
    last_sequence: number
    has_more: boolean
  }
  events: TranscriptEvent[]
}

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error'

const RETRY_INTERVAL_MS = 5000
const MAX_RETRIES = 3

export function useTranscriptTimeline(taskId: string, orgId: string) {
  const [events, setEvents] = useState<TranscriptEvent[]>([])
  const [isLive, setIsLive] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [hasMore, setHasMore] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  const channelRef = useRef<ReturnType<ReturnType<typeof createClient>['channel']> | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch snapshot inicial
  const { data: snapshot, isLoading } = useQuery<TranscriptSnapshot>({
    queryKey: ['transcript-snapshot', taskId],
    queryFn: () => api.get(`/transcripts/${taskId}`),
    enabled: !!taskId,
  })

  // Inicializar eventos desde el snapshot
  useEffect(() => {
    if (snapshot?.events) {
      setEvents(snapshot.events)
      setHasMore(snapshot.sync?.has_more ?? false)
    }
  }, [snapshot])

  // Configurar subscripcion Realtime
  const setupSubscription = useCallback(() => {
    if (!orgId || !taskId) return

    const supabase = createClient()

    // Limpiar canal previo si existe
    if (channelRef.current) {
      supabase.removeChannel(channelRef.current)
      channelRef.current = null
    }

    setConnectionStatus('connecting')

    const channel = supabase.channel(`transcript-timeline:${taskId}`)

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

          // Race condition mitigation: descartar eventos con sequence <= last_sequence del snapshot
          const lastSequence = snapshot?.sync?.last_sequence ?? 0
          if (newEvent.sequence <= lastSequence) return

          setEvents((prev) => {
            // Deduplicar por id
            if (prev.some((e) => e.id === newEvent.id)) return prev
            // Insertar y mantener orden por sequence
            const updated = [...prev, newEvent]
            updated.sort((a, b) => a.sequence - b.sequence)
            return updated
          })
          setIsLive(true)
          setRetryCount(0) // Reset retry count on successful event
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          setConnectionStatus('connected')
          setRetryCount(0)
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          setConnectionStatus('error')
          setIsLive(false)
        } else if (status === 'CLOSED') {
          setConnectionStatus('disconnected')
          setIsLive(false)
        }
      })

    channelRef.current = channel
  }, [orgId, taskId, snapshot])

  // Iniciar subscripcion cuando el snapshot esta listo y la task esta running
  useEffect(() => {
    if (!orgId || !taskId) return

    // Si la task esta en estado terminal, no iniciar streaming
    if (snapshot && !snapshot.is_running) {
      setConnectionStatus('disconnected')
      return
    }

    setupSubscription()

    return () => {
      if (channelRef.current) {
        const supabase = createClient()
        supabase.removeChannel(channelRef.current)
        channelRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [orgId, taskId, setupSubscription, snapshot?.is_running])

  // Reintento automatico con backoff simple
  useEffect(() => {
    if (connectionStatus !== 'error') return
    if (!snapshot?.is_running) return
    if (retryCount >= MAX_RETRIES) return

    reconnectTimeoutRef.current = setTimeout(() => {
      setRetryCount((prev) => prev + 1)
      setupSubscription()
    }, RETRY_INTERVAL_MS)

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connectionStatus, retryCount, setupSubscription, snapshot?.is_running])

  // Funcion de reconexion manual
  const reconnect = useCallback(() => {
    setRetryCount(0)
    setConnectionStatus('connecting')
    setupSubscription()
  }, [setupSubscription])

  // Funcion para cargar mas eventos (paginacion inversa)
  const loadMore = useCallback(async () => {
    if (!taskId || !hasMore) return

    try {
      // Cargar eventos desde el inicio (after_sequence=0, limit=500)
      // Los eventos ya cargados se mantienen; los nuevos se insertan al inicio
      const response = await api.get(`/transcripts/${taskId}?after_sequence=0&limit=500`)
      const moreEvents: TranscriptEvent[] = response?.events ?? []

      setEvents((prev) => {
        // Merge: nuevos eventos al inicio, deduplicar por id
        const combined = [...moreEvents, ...prev]
        const seen = new Set<string>()
        const unique: TranscriptEvent[] = []
        for (const e of combined) {
          if (!seen.has(e.id)) {
            seen.add(e.id)
            unique.push(e)
          }
        }
        unique.sort((a, b) => a.sequence - b.sequence)
        return unique
      })

      // El endpoint puede no devolver has_more en la paginacion secundaria
      // Asumimos que si trajo 500, puede haber mas
      setHasMore(moreEvents.length >= 500)
    } catch {
      // Error silencioso - el usuario puede reintentar
    }
  }, [taskId, hasMore])

  const isRunning = snapshot?.is_running ?? false

  return {
    events,
    isLoading,
    isRunning,
    isLive,
    connectionStatus,
    hasMore,
    loadMore,
    reconnect,
    flowType: snapshot?.flow_type ?? null,
    status: snapshot?.status ?? null,
  }
}
