'use client'

import { useState } from 'react'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useTasks } from '@/hooks/useTasks'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

export default function TasksPage() {
  const { orgId } = useCurrentOrg()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [flowFilter, setFlowFilter] = useState<string>('')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading } = useTasks(orgId, {
    status: statusFilter === 'all' ? undefined : statusFilter,
    flow_type: flowFilter || undefined,
    limit,
    offset: page * limit,
  })

  const tasks = data?.items || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / limit)

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold tracking-tight">Historial de Tareas</h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(0) }}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los estados</SelectItem>
            <SelectItem value="pending">Pendiente</SelectItem>
            <SelectItem value="running">Ejecutando</SelectItem>
            <SelectItem value="awaiting_approval">HITL</SelectItem>
            <SelectItem value="completed">Completado</SelectItem>
            <SelectItem value="failed">Error</SelectItem>
            <SelectItem value="rejected">Rechazado</SelectItem>
          </SelectContent>
        </Select>

        <Input
          value={flowFilter}
          onChange={(e) => { setFlowFilter(e.target.value); setPage(0) }}
          placeholder="Filtrar por flow_type..."
          className="w-[250px]"
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <LoadingSpinner label="Cargando tareas..." />
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Flow</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Creado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    <EmptyState description="No hay tareas" />
                  </TableCell>
                </TableRow>
              ) : (
                tasks.map((task) => (
                  <TableRow key={task.task_id} className="cursor-pointer hover:bg-muted/50">
                    <TableCell>
                      <Link href={`/tasks/${task.task_id}`} className="font-medium text-primary hover:underline">
                        {task.task_id.slice(0, 12)}...
                      </Link>
                    </TableCell>
                    <TableCell>{task.flow_type}</TableCell>
                    <TableCell><StatusLabel status={task.status} /></TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDistanceToNow(new Date(task.created_at), {
                        addSuffix: true,
                        locale: es,
                      })}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {total} tareas en total
          </p>
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  href="#"
                  onClick={(e) => { e.preventDefault(); setPage(Math.max(0, page - 1)) }}
                  className={page === 0 ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
              {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                let pageIndex: number
                if (totalPages <= 5) {
                  pageIndex = i
                } else if (page < 3) {
                  pageIndex = i
                } else if (page > totalPages - 4) {
                  pageIndex = totalPages - 5 + i
                } else {
                  pageIndex = page - 2 + i
                }
                return (
                  <PaginationItem key={pageIndex}>
                    <a
                      href="#"
                      onClick={(e) => { e.preventDefault(); setPage(pageIndex) }}
                      className={`flex h-10 items-center justify-center rounded-md px-3 text-sm transition-colors ${
                        pageIndex === page
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-muted'
                      }`}
                    >
                      {pageIndex + 1}
                    </a>
                  </PaginationItem>
                )
              })}
              <PaginationItem>
                <PaginationNext
                  href="#"
                  onClick={(e) => { e.preventDefault(); setPage(Math.min(totalPages - 1, page + 1)) }}
                  className={page >= totalPages - 1 ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}
    </div>
  )
}
