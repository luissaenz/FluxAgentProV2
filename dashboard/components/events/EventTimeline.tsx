'use client'

import type { DomainEvent } from '@/lib/types'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { Activity } from 'lucide-react'

const EVENT_COLORS: Record<string, string> = {
  'flow.created': 'bg-blue-500',
  'flow.completed': 'bg-green-500',
  'flow.rejected': 'bg-purple-500',
  'flow.resumed': 'bg-cyan-500',
  'approval.requested': 'bg-amber-500',
  'approval.approved': 'bg-green-500',
  'approval.rejected': 'bg-red-500',
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
      <div className="flex flex-col items-center justify-center py-12 text-gray-400 dark:text-gray-600">
        <Activity className="mb-2 h-12 w-12" />
        <p className="text-sm">No hay eventos</p>
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {filtered.map((event, idx) => {
        const dotColor = EVENT_COLORS[event.event_type] || 'bg-gray-400'
        const isLast = idx === filtered.length - 1

        return (
          <div key={event.id} className="flex gap-4">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center">
              <div className={`h-3 w-3 rounded-full ${dotColor}`} />
              {!isLast && <div className="w-0.5 flex-1 bg-gray-200 dark:bg-gray-800" />}
            </div>

            {/* Content */}
            <div className="flex-1 pb-6">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {event.event_type}
                </span>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {formatDistanceToNow(new Date(event.created_at), {
                    addSuffix: true,
                    locale: es,
                  })}
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {event.aggregate_type}:{event.aggregate_id.slice(0, 8)}...
                {event.actor && ` by ${event.actor}`}
              </p>
              {event.payload && Object.keys(event.payload).length > 0 && (
                <pre className="mt-1 overflow-x-auto rounded bg-gray-50 p-2 text-xs text-gray-600 dark:bg-gray-950 dark:text-gray-400">
                  {JSON.stringify(event.payload, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
