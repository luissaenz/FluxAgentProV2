/**
 * Mapa estático de metadata de herramientas del frontend.
 * 
 * SUPUESTO: Dado que el tool_registry es de servidor y no queremos añadir
 * nuevos endpoints al backend en este sprint, el frontend maneja un mapa
 * de descripciones para las herramientas conocidas del dominio Bartenders.
 * 
 * Si una herramienta no está en este mapa, se usará su nombre técnico
 * formateado como fallback (ej: "noop" -> "No Op").
 */

export interface ToolMetadata {
  /** Nombre legible por humanos */
  displayName: string
  /** Descripción narrativa de qué hace la herramienta */
  description: string
  /** Tags para categorización visual */
  tags?: string[]
  /** Si requiere aprobación humana antes de ejecutarse */
  requiresApproval?: boolean
  /** Timeout en segundos */
  timeoutSeconds?: number
}

export const TOOL_REGISTRY_METADATA: Record<string, ToolMetadata> = {
  // ─── Herramientas Built-in ─────────────────────────────────────────────
  noop: {
    displayName: 'No Op',
    description: 'Herramienta de prueba que retorna el input sin modificar. Usada para validación del sistema.',
    tags: ['Core', 'Utility'],
    timeoutSeconds: 30,
  },

  // ─── Herramientas Bartenders: Clima ────────────────────────────────────
  obtener_factor_climatico: {
    displayName: 'Obtener Factor Climático',
    description: 'Consulta el factor de riesgo climático histórico para un mes y provincia específicos. Retorna el porcentaje de ajuste a aplicar sobre costos de productos y equipamiento en el escandallo.',
    tags: ['Clima', 'Presupuesto'],
    timeoutSeconds: 30,
  },
  verificar_pronostico_real: {
    displayName: 'Verificar Pronóstico Real',
    description: 'Verifica el pronóstico meteorológico real para un evento específico y lo compara con el histórico presupuestado. Si el desvío supera el 10%, activa ALERTA ROJA para disparar una orden de compra de emergencia.',
    tags: ['Clima', 'Alerta'],
    requiresApproval: false,
    timeoutSeconds: 30,
  },

  // ─── Herramientas Bartenders: Escandallo ───────────────────────────────
  calcular_escandallo: {
    displayName: 'Calcular Escandallo',
    description: 'Calcula el escandallo de costos completo para un evento en 4 bloques: productos, equipamiento, personal y logística. Aplica factor climático, mermas (5%) e imprevistos (3%). Retorna el costo base total que se usará para cotizar.',
    tags: ['Costos', 'Escandallo'],
    timeoutSeconds: 30,
  },

  // ─── Herramientas Bartenders: Inventario ───────────────────────────────
  calcular_stock_necesario: {
    displayName: 'Calcular Stock Necesario',
    description: 'Calcula la cantidad exacta de cada producto necesaria para un evento, según PAX y tipo de menú. Incluye un buffer de seguridad del 10%. No modifica el inventario.',
    tags: ['Inventario', 'Stock'],
    timeoutSeconds: 30,
  },
  reservar_stock_evento: {
    displayName: 'Reservar Stock para Evento',
    description: 'Reserva el stock físico necesario para un evento. Si algún item no tiene suficiente stock, lo marca y activa una alerta para que se genere una orden de compra. Nunca falla silenciosamente.',
    tags: ['Inventario', 'Reserva'],
    requiresApproval: true,
    timeoutSeconds: 30,
  },
  liberar_stock_evento: {
    displayName: 'Liberación de Stock de Evento',
    description: 'Libera el stock reservado para un evento cancelado o finalizado. Asegura la conciliación física del inventario tras la operación.',
    tags: ['Inventario', 'Conciliación'],
    requiresApproval: true,
    timeoutSeconds: 30,
  },

  // ─── Herramientas Bartenders: Staffing & Logística ─────────────────────
  asignar_equipo_staff: {
    displayName: 'Asignación de Staffing',
    description: 'Selecciona y asigna personal según PAX, especialidad (Premium/Base), calificación y disponibilidad geográfica.',
    tags: ['Personal', 'Staffing'],
    requiresApproval: true,
    timeoutSeconds: 30,
  },
  generar_hoja_ruta: {
    displayName: 'Generador Hoja de Ruta',
    description: 'Genera instrucciones logísticas detalladas para el equipo desplazado al evento, incluyendo horarios y puntos de contacto.',
    tags: ['Logística', 'Operaciones'],
    requiresApproval: false,
    timeoutSeconds: 15,
  },

  // ─── Herramientas Bartenders: Cierre & Auditoría ───────────────────────
  notificar_cierre_evento: {
    displayName: 'Auditoría de Cierre',
    description: 'Notifica la finalización del evento y dispara los procesos de auditoría de consumo y feedback del cliente.',
    tags: ['Auditoría', 'Notificación'],
    requiresApproval: false,
    timeoutSeconds: 15,
  },
}

/**
 * Obtiene la metadata de una herramienta por su nombre técnico.
 * Si no existe en el mapa, retorna un fallback con el nombre formateado.
 */
export function getToolMetadata(toolName: string): ToolMetadata {
  const metadata = TOOL_REGISTRY_METADATA[toolName]
  
  if (metadata) {
    return metadata
  }

  // Fallback: formatear nombre técnico como legible
  return {
    displayName: formatToolName(toolName),
    description: 'Herramienta técnica sin descripción narrativa disponible.',
    tags: ['configuracion-tecnica'],
  }
}

/**
 * Formatea un nombre técnico de herramienta en un nombre legible.
 * Ej: "obtener_clima" -> "Obtener Clima", "noop" -> "No Op"
 */
export function formatToolName(toolName: string): string {
  return toolName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
