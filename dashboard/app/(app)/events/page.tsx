'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { createClient } from '@/lib/supabase'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
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
      <h2 className="text-2xl font-bold tracking-tight">Log de Eventos</h2>

      <div>
        <Input
          type="text"
          value={filterTaskId}
          onChange={(e) => setFilterTaskId(e.target.value)}
          placeholder="Filtrar por task_id..."
          className="w-[300px]"
        />
      </div>

      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <LoadingSpinner label="Cargando eventos..." />
          ) : (
            <EventTimeline
              events={events || []}
              filterTaskId={filterTaskId || undefined}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
