'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { BackButton } from '@/components/shared/BackButton'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { EventTimeline } from '@/components/events/EventTimeline'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { PresentedTaskDetail } from '@/components/presentation/PresentedTaskDetail'
import { formatFlowType } from '@/lib/presentation/fallback'
import { usePresentationConfigs } from '@/hooks/usePresentationConfig'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import type { Task, DomainEvent } from '@/lib/types'

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { orgId } = useCurrentOrg()

  const { data: configs } = usePresentationConfigs(orgId)

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
    return <LoadingSpinner label="Cargando tarea..." />
  }

  if (!task) {
    return <p className="py-12 text-center text-muted-foreground">Tarea no encontrada</p>
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center gap-3">
        <BackButton href="/tasks" label="Volver" />
        <h2 className="text-2xl font-bold tracking-tight">Tarea: {task.task_id.slice(0, 12)}...</h2>
        <StatusLabel status={task.status} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Task info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Información</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">ID</dt>
                <dd className="text-sm font-mono">{task.task_id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Flow Type</dt>
                <dd className="text-sm">{formatFlowType(task.flow_type)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Estado</dt>
                <dd><StatusLabel status={task.status} /></dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Creado</dt>
                <dd className="text-sm">{task.created_at}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Actualizado</dt>
                <dd className="text-sm">{task.updated_at}</dd>
              </div>
              {task.result && (
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Resultado</dt>
                  <dd className="mt-1">
                    <PresentedTaskDetail
                      result={task.result}
                      config={configs?.[task.flow_type]}
                    />
                  </dd>
                </div>
              )}
              {task.error && (
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Error</dt>
                  <dd className="text-sm text-destructive">{task.error}</dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>

        {/* Event timeline */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Timeline de Eventos</CardTitle>
          </CardHeader>
          <CardContent>
            <EventTimeline events={events || []} filterTaskId={id} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
