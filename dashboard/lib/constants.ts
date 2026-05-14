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

export const TEMPLATE_CATEGORIES = ['Research', 'Development', 'Support', 'General'] as const

export const TEMPLATE_CACHE_MS = 5 * 60 * 1000

export const PROVIDER_MODELS: Record<string, string[]> = {
  groq: ["llama-3.1-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
  openai: ["gpt-4o", "gpt-4o-mini"],
  anthropic: ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
  openrouter: ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"],
}

export const STATUS_BADGES: Record<string, { label: string; variant: 'success' | 'warning' | 'destructive' | 'info' | 'secondary' | 'default' }> = {
  pending: { label: 'Pendiente', variant: 'secondary' },
  running: { label: 'Ejecutando', variant: 'info' },
  awaiting_approval: { label: 'HITL', variant: 'warning' },
  completed: { label: 'Completado', variant: 'success' },
  failed: { label: 'Error', variant: 'destructive' },
  rejected: { label: 'Rechazado', variant: 'destructive' },
  cancelled: { label: 'Cancelado', variant: 'secondary' },
  approved: { label: 'Aprobado', variant: 'success' },
}
