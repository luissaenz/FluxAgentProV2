'use client'

import { Badge } from '@/components/ui/badge'
import type { TaskStatus } from '@/lib/types'

const STATUS_CONFIG: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'info'; label: string }> = {
  // Task status
  pending:      { variant: 'info',      label: 'Pendiente' },
  running:      { variant: 'warning',   label: 'Ejecutando' },
  completed:    { variant: 'success',   label: 'Completado' },
  failed:       { variant: 'destructive', label: 'Error' },
  awaiting_approval: { variant: 'warning', label: 'HITL' },
  rejected:     { variant: 'destructive', label: 'Rechazado' },
  cancelled:    { variant: 'secondary', label: 'Cancelado' },
  // Ticket status
  backlog:      { variant: 'secondary', label: 'Backlog' },
  todo:         { variant: 'outline' as any, label: 'Todo' },
  in_progress:  { variant: 'default',   label: 'En progreso' },
  done:         { variant: 'success',   label: 'Hecho' },
  blocked:      { variant: 'destructive', label: 'Bloqueado' },
}

interface StatusLabelProps {
  status: string
}

export function StatusLabel({ status }: StatusLabelProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG['pending']
  return <Badge variant={config.variant}>{config.label}</Badge>
}
