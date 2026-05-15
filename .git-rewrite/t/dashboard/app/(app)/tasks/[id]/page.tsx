'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { EventTimeline } from '@/components/events/EventTimeline'
import { Badge } from '@/components/ui/Badge'
import { STATUS_BADGES } from '@/lib/constants'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import type { Task, DomainEvent } from '@/lib/types'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { orgId } = useCurrentOrg()

  const { data: task, isLoading } = useQuery<Task>({
    queryKey: ['task', id],
    queryFn: () => api.get(`/tasks/${id}`),
    enabled: !!id,
  })

  const { data: events } = useQuery<DomainEvent[]>({
    queryKey: ['events', orgId],
    queryFn: async () => {
      const { createClient } = await import('@/lib/supabase')
      const supabase = createClient()
      const { data } = await supabase
        .from('domain_events')
        .select('*')
        .eq('aggregate_id', id)
        .order('created_at', { ascending: true })
      return data || []
    },
    enabled: !!id && !!orgId,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!task) {
    return <p className="py-12 text-center text-gray-500">Tarea no encontrada</p>
  }

  const badge = STATUS_BADGES[task.status] || STATUS_BADGES['pending']

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/tasks" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h2 className="text-2xl font-bold text-gray-900">Tarea: {task.task_id.slice(0, 12)}...</h2>
        <Badge className={badge.className}>{badge.label}</Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Task info */}
        <div className="rounded-lg border bg-white p-6">
          <h3 className="mb-4 font-semibold text-gray-900">Información</h3>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs font-medium text-gray-500">ID</dt>
              <dd className="text-sm text-gray-900">{task.task_id}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500">Flow Type</dt>
              <dd className="text-sm text-gray-900">{task.flow_type}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500">Estado</dt>
              <dd><Badge className={badge.className}>{badge.label}</Badge></dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500">Creado</dt>
              <dd className="text-sm text-gray-900">{task.created_at}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500">Actualizado</dt>
              <dd className="text-sm text-gray-900">{task.updated_at}</dd>
            </div>
            {task.result && (
              <div>
                <dt className="text-xs font-medium text-gray-500">Resultado</dt>
                <dd>
                  <pre className="mt-1 overflow-x-auto rounded bg-gray-50 p-2 text-xs">
                    {JSON.stringify(task.result, null, 2)}
                  </pre>
                </dd>
              </div>
            )}
            {task.error && (
              <div>
                <dt className="text-xs font-medium text-gray-500">Error</dt>
                <dd className="text-sm text-red-600">{task.error}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Event timeline */}
        <div className="rounded-lg border bg-white p-6">
          <h3 className="mb-4 font-semibold text-gray-900">Timeline de Eventos</h3>
          <EventTimeline events={events || []} filterTaskId={id} />
        </div>
      </div>
    </div>
  )
}
