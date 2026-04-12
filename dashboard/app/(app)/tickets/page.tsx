'use client'

import { useState } from 'react'
import { useTickets, useExecuteTicket, useDeleteTicket } from '@/hooks/useTickets'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { PageHeader } from '@/components/shared/PageHeader'
import { DataTable } from '@/components/data-table'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Play, Pencil, Trash2 } from 'lucide-react'
import { ColumnDef } from '@tanstack/react-table'
import type { Ticket } from '@/lib/types'
import { CreateTicketForm } from '@/components/tickets/CreateTicketForm'
import { EditTicketForm } from '@/components/tickets/EditTicketForm'
import Link from 'next/link'

const PRIORITY_BADGES: Record<string, string> = {
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  medium: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  urgent: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
}

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  urgent: 'Urgente',
}

export default function TicketsPage() {
  const { orgId } = useCurrentOrg()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTicket, setEditingTicket] = useState<Ticket | null>(null)

  const { data: ticketsData, isLoading } = useTickets(orgId, {
    status: statusFilter === 'all' || !statusFilter ? undefined : statusFilter,
  })
  const executeTicket = useExecuteTicket()
  const deleteTicket = useDeleteTicket()

  const columns: ColumnDef<Ticket>[] = [
    {
      accessorKey: 'title',
      header: 'Titulo',
      cell: ({ row }) => (
        <Link
          href={`/tickets/${row.original.id}`}
          className="font-medium text-primary hover:underline"
        >
          {row.getValue('title')}
        </Link>
      ),
    },
    {
      accessorKey: 'flow_type',
      header: 'Flow',
      cell: ({ row }) => (row.getValue('flow_type') as string) || '—',
    },
    {
      accessorKey: 'priority',
      header: 'Prioridad',
      cell: ({ row }) => {
        const p = row.getValue('priority') as string
        return (
          <Badge className={PRIORITY_BADGES[p]}>
            {PRIORITY_LABELS[p] || p}
          </Badge>
        )
      },
    },
    {
      accessorKey: 'status',
      header: 'Estado',
      cell: ({ row }) => <StatusLabel status={row.getValue('status')} />,
    },
    {
      accessorKey: 'task_id',
      header: 'Task',
      cell: ({ row }) => {
        const taskId = row.getValue('task_id') as string | null
        return taskId ? (
          <Link
            href={`/tasks/${taskId}`}
            className="font-mono text-xs text-muted-foreground hover:underline"
          >
            {taskId.slice(0, 8)}...
          </Link>
        ) : (
          '—'
        )
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const ticket = row.original
        const isExecuting = executeTicket.isPending && executeTicket.variables?.ticketId === ticket.id
        const canExecute =
          ticket.status !== 'in_progress' &&
          ticket.status !== 'done' &&
          ticket.status !== 'cancelled' &&
          !!ticket.flow_type

        const handleDelete = () => {
          if (confirm('¿Estás seguro de que deseas eliminar este ticket permanentemente?')) {
            deleteTicket.mutate(ticket.id)
          }
        }

        return (
          <div className="flex items-center gap-1 justify-end">
            {canExecute && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => executeTicket.mutate({ ticketId: ticket.id, ticketTitle: ticket.title })}
                disabled={executeTicket.isPending}
                className={isExecuting ? 'animate-pulse text-primary h-8 w-8' : 'h-8 w-8 text-muted-foreground hover:text-primary'}
                title="Ejecutar"
              >
                {isExecuting ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
            )}

            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-primary"
              title="Editar"
              onClick={() => setEditingTicket(ticket)}
            >
              <Pencil className="h-4 w-4" />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-destructive"
              title="Eliminar"
              onClick={handleDelete}
              disabled={deleteTicket.isPending}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        )
      },
    },
  ]

  return (
    <>
      <PageHeader
        title="Tickets"
        description="Solicitudes de trabajo para los agentes"
        action={
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Ticket
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Crear Ticket</DialogTitle>
              </DialogHeader>
              <CreateTicketForm onSuccess={() => setDialogOpen(false)} />
            </DialogContent>
          </Dialog>
        }
      />

      <div className="mb-4 flex gap-2">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Todos los estados" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="backlog">Backlog</SelectItem>
            <SelectItem value="todo">Todo</SelectItem>
            <SelectItem value="in_progress">En progreso</SelectItem>
            <SelectItem value="done">Hecho</SelectItem>
            <SelectItem value="blocked">Bloqueado</SelectItem>
            <SelectItem value="cancelled">Cancelado</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Dialog open={!!editingTicket} onOpenChange={(open) => !open && setEditingTicket(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Editar Ticket</DialogTitle>
          </DialogHeader>
          {editingTicket && (
            <EditTicketForm
              ticket={editingTicket}
              onSuccess={() => setEditingTicket(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <DataTable
        data={ticketsData?.items ?? []}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No hay tickets aun. Crea uno para empezar."
        pageSize={20}
      />
    </>
  )
}
