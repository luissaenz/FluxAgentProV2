'use client'

import type { DomainEvent } from '@/lib/types'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { Activity } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const EVENT_BADGES: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'info' }> = {
  'flow.created': { variant: 'info' },
  'flow.completed': { variant: 'success' },
  'flow.rejected': { variant: 'destructive' },
  'flow.resumed': { variant: 'info' },
  'approval.requested': { variant: 'warning' },
  'approval.approved': { variant: 'success' },
  'approval.rejected': { variant: 'destructive' },
}

interface EventTimelineProps {
  events: DomainEvent[]
  filterTaskId?: string
}

export function EventTimeline({ events, filterTaskId }: EventTimelineProps) {
  const filtered = filterTaskId
    ? events.filter((e) => e.aggregate_id === filterTaskId)
    : events

  if (filtered.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Activity className="mb-2 h-12 w-12 opacity-50" />
        <p className="text-sm">No hay eventos</p>
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {filtered.map((event, idx) => {
        const badgeConfig = EVENT_BADGES[event.event_type] || { variant: 'secondary' as const }
        const isLast = idx === filtered.length - 1

        return (
          <div key={event.id} className="flex gap-4">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center">
              <div className={cn('h-3 w-3 rounded-full', `bg-${badgeConfig.variant}`)} />
              {!isLast && <div className="w-0.5 flex-1 bg-border" />}
            </div>

            {/* Content */}
            <div className="flex-1 pb-6">
              <div className="flex items-center gap-2">
                <Badge variant={badgeConfig.variant} className="text-xs">
                  {event.event_type}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(event.created_at), {
                    addSuffix: true,
                    locale: es,
                  })}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {event.aggregate_type}:{event.aggregate_id.slice(0, 8)}...
                {event.actor && ` by ${event.actor}`}
              </p>
              {event.payload && Object.keys(event.payload).length > 0 && (
                <div className="mt-1">
                  <CodeBlock code={event.payload} />
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
