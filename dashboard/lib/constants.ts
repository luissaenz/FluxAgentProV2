export const KANBAN_COLUMNS = [
  { id: 'pending', label: 'Pendiente', color: 'bg-slate-100', textColor: 'text-slate-700' },
  { id: 'running', label: 'Ejecutando', color: 'bg-blue-100', textColor: 'text-blue-700' },
  { id: 'awaiting_approval', label: 'HITL (Espera)', color: 'bg-amber-100', textColor: 'text-amber-700' },
  { id: 'completed', label: 'Completado', color: 'bg-green-100', textColor: 'text-green-700' },
  { id: 'failed', label: 'Error', color: 'bg-red-100', textColor: 'text-red-700' },
  { id: 'rejected', label: 'Rechazado', color: 'bg-purple-100', textColor: 'text-purple-700' },
] as const

export const ROLES = {
  fap_admin: { label: 'FAP Admin', description: 'Acceso global a todas las organizaciones' },
  org_owner: { label: 'Owner', description: 'Gestión completa de la organización' },
  org_operator: { label: 'Operador', description: 'Lectura + aprobaciones' },
} as const

export const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  pending: { label: 'Pendiente', className: 'bg-slate-100 text-slate-700' },
  running: { label: 'Ejecutando', className: 'bg-blue-100 text-blue-700' },
  awaiting_approval: { label: 'HITL', className: 'bg-amber-100 text-amber-700' },
  completed: { label: 'Completado', className: 'bg-green-100 text-green-700' },
  failed: { label: 'Error', className: 'bg-red-100 text-red-700' },
  rejected: { label: 'Rechazado', className: 'bg-purple-100 text-purple-700' },
  cancelled: { label: 'Cancelado', className: 'bg-gray-100 text-gray-700' },
  approved: { label: 'Aprobado', className: 'bg-green-100 text-green-700' },
}
