'use client'

import { SectionCards } from '@/components/section-cards'
import { DataTable } from '@/components/data-table'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { useTasks } from '@/hooks/useTasks'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
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
  const tasks = tasksData?.items?.slice(0, 10) || []

  return (
    <>
      {/* SectionCards actúa como hero — no necesita PageHeader arriba */}
      <SectionCards />
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
