'use client'

import { useState } from 'react'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useTasks } from '@/hooks/useTasks'
import { Badge } from '@/components/ui/Badge'
import { STATUS_BADGES } from '@/lib/constants'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

export default function TasksPage() {
  const { orgId } = useCurrentOrg()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [flowFilter, setFlowFilter] = useState<string>('')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading } = useTasks(orgId, {
    status: statusFilter || undefined,
    flow_type: flowFilter || undefined,
    limit,
    offset: page * limit,
  })

  const tasks = data?.items || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / limit)

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900">Historial de Tareas</h2>

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0) }}
          className="rounded-lg border px-3 py-2 text-sm"
        >
          <option value="">Todos los estados</option>
          <option value="pending">Pendiente</option>
          <option value="running">Ejecutando</option>
          <option value="awaiting_approval">HITL</option>
          <option value="completed">Completado</option>
          <option value="failed">Error</option>
          <option value="rejected">Rechazado</option>
        </select>
        <input
          type="text"
          value={flowFilter}
          onChange={(e) => { setFlowFilter(e.target.value); setPage(0) }}
          placeholder="Filtrar por flow_type..."
          className="rounded-lg border px-3 py-2 text-sm"
        />
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">ID</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Flow</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Estado</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Creado</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-sm text-gray-400">
                  Cargando...
                </td>
              </tr>
            ) : tasks.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-sm text-gray-400">
                  No hay tareas
                </td>
              </tr>
            ) : (
              tasks.map((task) => {
                const badge = STATUS_BADGES[task.status] || STATUS_BADGES['pending']
                return (
                  <tr key={task.task_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link
                        href={`/tasks/${task.task_id}`}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        {task.task_id.slice(0, 12)}...
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{task.flow_type}</td>
                    <td className="px-4 py-3">
                      <Badge className={badge.className}>{badge.label}</Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {formatDistanceToNow(new Date(task.created_at), {
                        addSuffix: true,
                        locale: es,
                      })}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {total} tareas en total
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="rounded-lg border px-3 py-1 text-sm disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="px-3 py-1 text-sm text-gray-500">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="rounded-lg border px-3 py-1 text-sm disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
