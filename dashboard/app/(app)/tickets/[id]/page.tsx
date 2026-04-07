'use client'

import { useParams } from 'next/navigation'
import { useTicket, useExecuteTicket } from '@/hooks/useTickets'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { BackButton } from '@/components/shared/BackButton'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Play } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
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

export default function TicketDetailPage() {
  const { id } = useParams() as { id: string }
  const { orgId } = useCurrentOrg()
  const { data: ticket, isLoading } = useTicket(orgId, id)
  const executeTicket = useExecuteTicket()

  if (isLoading) {
    return <p className="py-12 text-center text-muted-foreground">Cargando...</p>
  }
  if (!ticket) {
    return <p className="py-12 text-center text-muted-foreground">Ticket no encontrado</p>
  }

  const canExecute =
    ticket.status !== 'in_progress' &&
    ticket.status !== 'done' &&
    ticket.status !== 'cancelled' &&
    !!ticket.flow_type

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <BackButton href="/tickets" />
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{ticket.title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge className={PRIORITY_BADGES[ticket.priority]}>
              {PRIORITY_LABELS[ticket.priority]}
            </Badge>
            <StatusLabel status={ticket.status} />
            {ticket.flow_type && (
              <Badge variant="outline">{ticket.flow_type}</Badge>
            )}
          </div>
        </div>
        {canExecute && (
          <Button
            onClick={() => executeTicket.mutate(ticket!.id)}
            disabled={executeTicket.isPending}
          >
            <Play className="mr-2 h-4 w-4" />
            Ejecutar
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Informacion</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {ticket.description && (
              <div>
                <strong>Descripcion:</strong>
                <p className="text-muted-foreground mt-1">{ticket.description}</p>
              </div>
            )}
            <div>
              <strong>Creado:</strong>{' '}
              {formatDistanceToNow(new Date(ticket.created_at), {
                addSuffix: true,
                locale: es,
              })}
            </div>
            <div>
              <strong>Actualizado:</strong>{' '}
              {formatDistanceToNow(new Date(ticket.updated_at), {
                addSuffix: true,
                locale: es,
              })}
            </div>
            {ticket.resolved_at && (
              <div>
                <strong>Resuelto:</strong>{' '}
                {formatDistanceToNow(new Date(ticket.resolved_at), {
                  addSuffix: true,
                  locale: es,
                })}
              </div>
            )}
            {ticket.task_id && (
              <div>
                <strong>Task:</strong>{' '}
                <Link
                  href={`/tasks/${ticket.task_id}`}
                  className="text-primary hover:underline"
                >
                  {ticket.task_id.slice(0, 12)}...
                </Link>
              </div>
            )}
            {ticket.assigned_to && (
              <div>
                <strong>Asignado a:</strong> {ticket.assigned_to}
              </div>
            )}
            {ticket.notes && (
              <div>
                <strong>Notas:</strong>
                <p className="text-muted-foreground mt-1">{ticket.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {ticket.input_data && Object.keys(ticket.input_data).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Parametros</CardTitle>
            </CardHeader>
            <CardContent>
              <CodeBlock code={ticket.input_data} />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
