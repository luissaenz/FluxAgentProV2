'use client'

import { useEffect, useRef } from 'react'
import { createClient } from '@/lib/supabase'
import { useQueryClient } from '@tanstack/react-query'
import type { RealtimeChannel } from '@supabase/supabase-js'

const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 5

export function useRealtimeDashboard(orgId: string) {
  const queryClient = useQueryClient()
  const reconnectAttemptsRef = useRef(0)
  const channelsRef = useRef<RealtimeChannel[]>([])

  useEffect(() => {
    if (!orgId) return

    const supabase = createClient()

    const setupChannels = () => {
      try {
        // Channel 1: tasks
        const tasksChannel = supabase
          .channel(`dashboard-tasks-${orgId}`)
          .on(
            'postgres_changes',
            {
              event: '*',
              schema: 'public',
              table: 'tasks',
              filter: `org_id=eq.${orgId}`,
            },
            () => {
              queryClient.invalidateQueries({ queryKey: ['tasks', orgId] })
            }
          )
          .subscribe((status) => {
            if (status === 'SUBSCRIBED') {
              reconnectAttemptsRef.current = 0
            }
          })

        // Channel 2: pending_approvals
        const approvalsChannel = supabase
          .channel(`dashboard-approvals-${orgId}`)
          .on(
            'postgres_changes',
            {
              event: '*',
              schema: 'public',
              table: 'pending_approvals',
              filter: `org_id=eq.${orgId}`,
            },
            () => {
              queryClient.invalidateQueries({ queryKey: ['approvals', orgId] })
            }
          )
          .subscribe()

        // Channel 3: domain_events (INSERT only for efficiency)
        const eventsChannel = supabase
          .channel(`dashboard-events-${orgId}`)
          .on(
            'postgres_changes',
            {
              event: 'INSERT',
              schema: 'public',
              table: 'domain_events',
              filter: `org_id=eq.${orgId}`,
            },
            (payload) => {
              queryClient.setQueryData(
                ['events', orgId],
                (old: Record<string, unknown>[] | undefined) =>
                  [payload.new, ...(old ?? [])].slice(0, 200)
              )
            }
          )
          .subscribe()

        channelsRef.current = [tasksChannel, approvalsChannel, eventsChannel]
      } catch (error) {
        console.error('Realtime setup failed:', error)
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++
          setTimeout(setupChannels, RECONNECT_DELAY)
        }
      }
    }

    setupChannels()

    return () => {
      channelsRef.current.forEach((ch) => supabase.removeChannel(ch))
      channelsRef.current = []
    }
  }, [orgId, queryClient])
}
