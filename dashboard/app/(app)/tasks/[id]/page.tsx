'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { BackButton } from '@/components/shared/BackButton'
import { EventTimeline } from '@/components/events/EventTimeline'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { PresentedTaskDetail } from '@/components/presentation/PresentedTaskDetail'
import { formatFlowType } from '@/lib/presentation/fallback'
import { usePresentationConfigs } from '@/hooks/usePresentationConfig'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { TranscriptTimeline } from '@/components/transcripts/TranscriptTimeline'
import { Radio, FileText } from 'lucide-react'
import { motion } from 'framer-motion'
import type { Task, DomainEvent } from '@/lib/types'

// PulseBadge animado para la pestaña Live Transcript
function PulseBadge() {
  return (
    <motion.div
      animate={{
        scale: [1, 1.2, 1],
        opacity: [0.7, 1, 0.7],
      }}
      transition={{
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    >
      <Radio className="h-3 w-3 text-green-400" />
    </motion.div>
  )
}

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

  const [activeTab, setActiveTab] = useState<string>('info')
  const hasAutoSwitched = useRef(false)

  // Sincronización inteligente de pestañas
  useEffect(() => {
    if (!task) return

    // Caso 1: Carga inicial - Si está running, ir a transcript
    if (!hasAutoSwitched.current && task.status === 'running') {
      setActiveTab('transcript')
      hasAutoSwitched.current = true
    }
    
    // Caso 2: Tarea finalizada mientras se estaba en transcript
    // No forzamos el cambio para no interrumpir la lectura del usuario, 
    // pero si la tarea finaliza y el usuario refresca, initialTab (si lo usáramos) sería info.
    
  }, [task?.status])

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

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          <TabsTrigger value="info" className="gap-2">
            <FileText className="h-4 w-4" />
            Información
          </TabsTrigger>
          <TabsTrigger value="transcript" className="gap-2">
            Live Transcript
            {task?.status === 'running' && <PulseBadge />}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="space-y-6">
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
                <CardTitle className="text-base">Auditoría de Sistema</CardTitle>
              </CardHeader>
              <CardContent>
                <EventTimeline events={events || []} filterTaskId={id} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="transcript">
          {orgId && (
            <TranscriptTimeline taskId={id} orgId={orgId} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
