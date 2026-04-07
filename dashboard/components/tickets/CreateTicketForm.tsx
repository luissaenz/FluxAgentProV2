'use client'

import { useState } from 'react'
import { useCreateTicket } from '@/hooks/useTickets'
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
import type { TicketPriority } from '@/lib/types'

interface CreateTicketFormProps {
  onSuccess: () => void
}

export function CreateTicketForm({ onSuccess }: CreateTicketFormProps) {
  const { data: flows, isLoading: loadingFlows } = useFlows()
  const createTicket = useCreateTicket()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [flowType, setFlowType] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('medium')
  const [inputJson, setInputJson] = useState('{}')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!title.trim()) {
      setError('El titulo es obligatorio')
      return
    }

    let inputData: Record<string, unknown> | undefined
    if (inputJson.trim() && inputJson !== '{}') {
      try {
        inputData = JSON.parse(inputJson)
      } catch {
        setError('El JSON de parametros no es valido')
        return
      }
    }

    try {
      await createTicket.mutateAsync({
        title,
        description: description || undefined,
        flow_type: flowType || undefined,
        priority,
        input_data: inputData,
      })
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear ticket')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="ticket-title">Titulo *</Label>
        <Input
          id="ticket-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Descripcion breve de la solicitud"
        />
      </div>

      <div>
        <Label htmlFor="ticket-description">Descripcion</Label>
        <Textarea
          id="ticket-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Detalles adicionales..."
          rows={2}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="ticket-flow">Flow</Label>
          <Select value={flowType} onValueChange={setFlowType}>
            <SelectTrigger id="ticket-flow">
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
          <Label htmlFor="ticket-priority">Prioridad</Label>
          <Select value={priority} onValueChange={(v) => setPriority(v as TicketPriority)}>
            <SelectTrigger id="ticket-priority">
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

      <div>
        <Label htmlFor="ticket-inputs">Parametros (JSON)</Label>
        <Textarea
          id="ticket-inputs"
          value={inputJson}
          onChange={(e) => setInputJson(e.target.value)}
          placeholder='{"clave": "valor"}'
          rows={4}
          className="font-mono text-sm"
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => onSuccess()}>
          Cancelar
        </Button>
        <Button type="submit" disabled={createTicket.isPending}>
          {createTicket.isPending ? 'Creando...' : 'Crear Ticket'}
        </Button>
      </div>
    </form>
  )
}
