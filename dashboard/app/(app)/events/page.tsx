'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { createClient } from '@/lib/supabase'
import { EventTimeline } from '@/components/events/EventTimeline'
import type { DomainEvent } from '@/lib/types'

export default function EventsPage() {
  const { orgId } = useCurrentOrg()
  const [filterTaskId, setFilterTaskId] = useState('')

  const { data: events, isLoading } = useQuery<DomainEvent[]>({
    queryKey: ['events', orgId],
    queryFn: async () => {
      const supabase = createClient()
      const { data } = await supabase
        .from('domain_events')
        .select('*')
        .eq('org_id', orgId)
        .order('created_at', { ascending: false })
        .limit(200)
      return data || []
    },
    enabled: !!orgId,
    staleTime: 2000,
  })

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Log de Eventos</h2>

      <div>
        <input
          type="text"
          value={filterTaskId}
          onChange={(e) => setFilterTaskId(e.target.value)}
          placeholder="Filtrar por task_id..."
          className="rounded-lg border px-3 py-2 text-sm dark:bg-gray-900 dark:border-gray-800 dark:text-gray-100"
        />
      </div>

      <div className="rounded-lg border bg-white p-6 dark:bg-gray-900 dark:border-gray-800">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          </div>
        ) : (
          <EventTimeline
            events={events || []}
            filterTaskId={filterTaskId || undefined}
          />
        )}
      </div>
    </div>
  )
}
