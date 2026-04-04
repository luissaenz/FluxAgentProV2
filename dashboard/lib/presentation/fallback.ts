/**
 * Fallback helpers for presenting agent output without presentation_config.
 * Converts raw flow_type and snake_case keys into human-readable labels.
 */

const FLOW_LABELS: Record<string, string> = {
  PreventaFlow: 'Preventa',
  ReservaFlow: 'Reserva',
  AlertaClimaFlow: 'Alerta Clima',
  CierreFlow: 'Cierre',
  CotizacionFlow: 'Cotizaci\u00f3n',
  architect_flow: 'Arquitecto',
  multi_crew: 'Multi-Crew',
}

/** "PreventaFlow" -> "Preventa", "architect_flow" -> "Arquitecto" */
export function formatFlowType(flowType: string): string {
  if (FLOW_LABELS[flowType]) return FLOW_LABELS[flowType]
  // Remove trailing "Flow" and split PascalCase or snake_case
  return flowType
    .replace(/Flow$/, '')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim()
}

/** "opcion_recomendada" -> "Opcion Recomendada" */
export function snakeCaseToTitle(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Extract a one-line summary from task result for card display.
 * Tries common patterns: evento_id, status, total, monto, etc.
 */
export function extractCardSummary(result: Record<string, unknown> | null): string | null {
  if (!result) return null

  const parts: string[] = []

  // Try to find an identifier
  const idKey = ['evento_id', 'cotizacion_id', 'orden_id', 'auditoria_id'].find(
    (k) => typeof result[k] === 'string'
  )
  if (idKey) parts.push(String(result[idKey]))

  // Try to find a monetary amount
  const amountKey = [
    'opcion_recomendada',
    'escandallo_total',
    'ganancia_neta',
    'total_ars',
  ].find((k) => typeof result[k] === 'number')
  if (amountKey) {
    const val = result[amountKey] as number
    parts.push(`$${val.toLocaleString('es-AR')}`)
  }

  // Try status
  if (typeof result['status'] === 'string' && !parts.length) {
    parts.push(result['status'] as string)
  }

  return parts.length > 0 ? parts.join(' \u2014 ') : null
}
