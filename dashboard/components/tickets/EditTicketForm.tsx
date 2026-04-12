'use client'

import { useState } from 'react'
import { useUpdateTicket } from '@/hooks/useTickets'
import { useFlows } from '@/hooks/useFlows'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Ticket, TicketPriority } from '@/lib/types'

interface EditTicketFormProps {
  ticket: Ticket
  onSuccess: () => void
}

export function EditTicketForm({ ticket, onSuccess }: EditTicketFormProps) {
  const { data: flows, isLoading: loadingFlows } = useFlows()
  const updateTicket = useUpdateTicket()

  const [title, setTitle] = useState(ticket.title)
  const [description, setDescription] = useState(ticket.description || '')
  const [flowType, setFlowType] = useState(ticket.flow_type || '')
  const [priority, setPriority] = useState<TicketPriority>(ticket.priority)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!title.trim()) {
      setError('El titulo es obligatorio')
      return
    }

    try {
      await updateTicket.mutateAsync({
        ticketId: ticket.id,
        body: {
          title,
          description: description.trim() || null,
          flow_type: flowType || null,
          priority,
        },
      })
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al actualizar ticket')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="edit-ticket-title">Titulo *</Label>
        <Input
          id="edit-ticket-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Descripcion breve"
        />
      </div>

      <div>
        <Label htmlFor="edit-ticket-description">Descripcion</Label>
        <Textarea
          id="edit-ticket-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Detalles..."
          rows={3}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="edit-ticket-flow">Flow</Label>
          <Select value={flowType} onValueChange={setFlowType}>
            <SelectTrigger id="edit-ticket-flow">
              <SelectValue placeholder="Seleccionar Flow" />
            </SelectTrigger>
            <SelectContent>
              {loadingFlows ? (
                <SelectItem value="__loading__" disabled>Cargando...</SelectItem>
              ) : (
                flows?.map((f) => (
                  <SelectItem key={f.flow_type} value={f.flow_type}>
                    {f.name || f.flow_type}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="edit-ticket-priority">Prioridad</Label>
          <Select value={priority} onValueChange={(v) => setPriority(v as TicketPriority)}>
            <SelectTrigger id="edit-ticket-priority">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Baja</SelectItem>
              <SelectItem value="medium">Media</SelectItem>
              <SelectItem value="high">Alta</SelectItem>
              <SelectItem value="urgent">Urgente</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="outline" onClick={() => onSuccess()}>
          Cancelar
        </Button>
        <Button type="submit" disabled={updateTicket.isPending}>
          {updateTicket.isPending ? 'Guardando...' : 'Guardar Cambios'}
        </Button>
      </div>
    </form>
  )
}
