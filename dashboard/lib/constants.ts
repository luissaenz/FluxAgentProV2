export const KANBAN_COLUMNS = [
  { id: 'pending', label: 'Pendiente', color: 'bg-slate-400', textColor: 'text-slate-700 dark:text-slate-300' },
  { id: 'running', label: 'Ejecutando', color: 'bg-blue-500', textColor: 'text-blue-700 dark:text-blue-300' },
  { id: 'awaiting_approval', label: 'HITL (Espera)', color: 'bg-amber-500', textColor: 'text-amber-700 dark:text-amber-300' },
  { id: 'completed', label: 'Completado', color: 'bg-green-500', textColor: 'text-green-700 dark:text-green-300' },
  { id: 'failed', label: 'Error', color: 'bg-red-500', textColor: 'text-red-700 dark:text-red-300' },
  { id: 'rejected', label: 'Rechazado', color: 'bg-purple-500', textColor: 'text-purple-700 dark:text-purple-300' },
] as const

export const ROLES = {
  fap_admin: { label: 'FAP Admin', description: 'Acceso global a todas las organizaciones' },
  org_owner: { label: 'Owner', description: 'Gestión completa de la organización' },
  org_operator: { label: 'Operador', description: 'Lectura + aprobaciones' },
} as const

export const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  pending: { label: 'Pendiente', className: 'bg-slate-100 text-slate-700 dark:bg-slate-900/50 dark:text-slate-200' },
  running: { label: 'Ejecutando', className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-200' },
  awaiting_approval: { label: 'HITL', className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200' },
  completed: { label: 'Completado', className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-200' },
  failed: { label: 'Error', className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-200' },
  rejected: { label: 'Rechazado', className: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-200' },
  cancelled: { label: 'Cancelado', className: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400' },
  approved: { label: 'Aprobado', className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-200' },
}
