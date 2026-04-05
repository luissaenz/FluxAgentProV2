'use client'

import { SectionCards } from '@/components/section-cards'
import { DataTable } from '@/components/data-table'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { useTasks } from '@/hooks/useTasks'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useMetrics } from '@/hooks/useMetrics'
import { useFlowMetrics } from '@/hooks/useFlowMetrics'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ColumnDef } from '@tanstack/react-table'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import type { Task } from '@/lib/types'
import Link from 'next/link'

const columns: ColumnDef<Task>[] = [
  {
    accessorKey: 'task_id',
    header: 'ID',
    cell: ({ row }) => (
      <Link href={`/tasks/${row.getValue('task_id')}`} className="font-medium text-primary hover:underline">
        {(row.getValue('task_id') as string).slice(0, 12)}...
      </Link>
    ),
  },
  {
    accessorKey: 'flow_type',
    header: 'Flow',
  },
  {
    accessorKey: 'status',
    header: 'Estado',
    cell: ({ row }) => <StatusLabel status={row.getValue('status')} />,
  },
  {
    accessorKey: 'created_at',
    header: 'Creado',
    cell: ({ row }) =>
      formatDistanceToNow(new Date(row.getValue('created_at')), {
        addSuffix: true,
        locale: es,
      }),
  },
]

export default function OverviewPage() {
  const { orgId, currentOrg } = useCurrentOrg()
  const { data: tasksData, isLoading } = useTasks(orgId)
  const { data: metrics, isLoading: loadingMetrics } = useMetrics(orgId)
  const { data: flows, isLoading: loadingFlows } = useFlowMetrics(orgId)
  const tasks = tasksData?.items?.slice(0, 10) || []

  return (
    <>
      {/* SectionCards actúa como hero — no necesita PageHeader arriba */}
      <SectionCards />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Flows activos */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Flows Registrados</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingFlows ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : !flows?.length ? (
              <p className="text-sm text-muted-foreground">
                No hay flows registrados aun.
              </p>
            ) : (
              <div className="space-y-2">
                {flows.map((flow) => (
                  <div
                    key={flow.flow_type}
                    className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                  >
                    <div className="flex flex-col">
                      <span className="font-medium">{flow.flow_type}</span>
                      <span className="text-xs text-muted-foreground">
                        {flow.total_runs} ejecuciones · {flow.total_tokens.toLocaleString()} tokens
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {flow.running > 0 && (
                        <Badge variant="secondary">{flow.running} activos</Badge>
                      )}
                      {flow.failed > 0 && (
                        <Badge variant="destructive">{flow.failed} errores</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Activity feed */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Actividad Reciente</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingMetrics ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : !metrics?.events.recent.length ? (
              <p className="text-sm text-muted-foreground">
                Sin eventos recientes.
              </p>
            ) : (
              <div className="space-y-1">
                {metrics.events.recent.map((event, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-xs py-1 border-b last:border-0"
                  >
                    <span className="font-mono text-muted-foreground">
                      {event.event_type}
                    </span>
                    <span className="text-muted-foreground">
                      {formatDistanceToNow(new Date(event.created_at), {
                        addSuffix: true,
                        locale: es,
                      })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div>
        <h3 className="mb-4 text-lg font-semibold">Tareas recientes</h3>
        <DataTable
          data={tasks}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No hay tareas aún"
          pageSize={10}
        />
      </div>
    </>
  )
}
