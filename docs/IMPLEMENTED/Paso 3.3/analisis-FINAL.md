# 🏛️ ANÁLISIS TÉCNICO FINAL: PASO 3.3 - Transcript Timeline UI

## 1. Resumen Ejecutivo
Se implementará el componente **`TranscriptTimeline.tsx`**, el corazón visual de la Fase 3, diseñado para proporcionar transparencia total durante la ejecución de tareas de IA. Este componente permite a los usuarios observar en tiempo real los pensamientos de los agentes (`agent_thought`), los pasos del flujo (`flow_step`) y los resultados de las herramientas (`tool_output`).

La arquitectura se basa en un modelo de **Sincronización Híbrida**: inicialmente carga un "snapshot" histórico del estado actual de la tarea y luego realiza un "hand-off" suave hacia un stream de **Supabase Realtime**, utilizando identificadores de secuencia para garantizar que no existan duplicados ni saltos en la línea de tiempo.

## 2. Diseño Funcional Consolidado

### Happy Path (Flujo Principal)
1. **Montaje:** El componente recibe un `taskId` y solicita el snapshot inicial al endpoint `GET /api/transcripts/{taskId}`.
2. **Render Inicial:** Los eventos históricos se muestran con una animación de entrada tipo "staggered" utilizando **Framer Motion**.
3. **Suscripción:** Se establece una conexión al canal Realtime de Supabase, filtrando por el `aggregate_id` (Task ID).
4. **Streaming en Vivo:** Cada nuevo evento insertado en la DB aparece instantáneamente en la UI con una animación de "slide-up + fade-in".
5. **Auto-Scroll Inteligente:** La vista se desplaza automáticamente al fondo solo si el usuario ya se encontraba al final de la lista, evitando interrumpir la lectura manual de eventos pasados.

### Edge Cases (MVP)
- **Carga de Historial Extenso:** Si `has_more` es true, se muestra un botón "Cargar anteriores" al inicio de la lista.
- **Desconexión Temporal:** Si el canal de Supabase se cae, la UI muestra un badge de "Reconectando..." y el hook intenta restablecer la conexión con backoff exponencial.
- **Payloads Masivos:** Los `tool_output` con JSONs grandes se truncan visualmente a 300 caracteres con un botón "Expandir" para ver el bloque de código completo.
- **Tarea Finalizada:** Si la tarea está en estado terminal (`done`, `failed`), el componente desactiva el listener de Realtime para optimizar recursos.

### Manejo de Errores
- **Error de API:** Si falla el snapshot inicial, se muestra un `EmptyState` con un botón de "Reintentar carga".
- **Fallo de Suscripción:** Si Realtime falla permanentemente tras 3 intentos, se muestra un aviso de "Modo Histórico (Sin Streaming)".

## 3. Diseño Técnico Definitivo

### Arquitectura de Capas
1. **Hook de Datos (`useTranscriptTimeline`):** Encapsula la lógica de fetch inicial, suscripción a Supabase y deduplicación por `sequence`.
2. **Componente Contenedor (`TranscriptTimeline`):** Gestiona el estado de scroll, indicadores de conexión y el layout general.
3. **Componente de Ítem (`TimelineEventItem`):** Renderiza la UI semántica basada en el `event_type`.

### Contratos de Datos (Frontend)
```typescript
type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

interface TranscriptEvent extends DomainEvent {
  sequence: number; // Garantía de ordenamiento del Paso 3.2
}

interface useTranscriptTimelineReturn {
  events: TranscriptEvent[];
  isLoading: boolean;
  isLive: boolean;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
}
```

### Animaciones Premium (Framer Motion)
| Elemento | Animación | Justificación |
|----------|-----------|---------------|
| **Nuevos Eventos** | `initial: { y: 20, opacity: 0 }, animate: { y: 0, opacity: 1 }` | Sensación de fluidez y "sistema vivo". |
| **Blinker "LIVE"** | `scale: [1, 1.1, 1], transition: { repeat: Infinity }` | Feedback instantáneo de suscripción activa. |
| **Skeleton Loading** | `animate-pulse` con delay escalonado | UX percibida más rápida. |

## 4. Decisiones Tecnológicas

| Decisión | Elección | Justificación |
|----------|----------|---------------|
| **Hook** | `useTranscriptTimeline.ts` (NUEVO) | Evita regresiones en el hook genérico `useFlowTranscript` y permite manejar estados de conexión complejos. |
| **Animación** | **Framer Motion** | Requerimiento de "Aesthetics Wow". Las transiciones de Layout de React no bastan para este nivel de acabado. |
| **Deduplicación** | Lógica por `sequence` | El backend garantiza que `sequence` es incremental. Filtramos `realtime_evt.sequence > snapshot.last_sequence`. |
| **Scroll** | `ScrollArea` (Shadcn) + `useRef` | Control total sobre el posicionamiento sin disparar re-renders innecesarios por scroll. |

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El componente muestra al menos 3 tipos de eventos: `flow_step`, `agent_thought`, `tool_output`.
- [ ] Los pensamientos del agente (`agent_thought`) se visualizan con estilo itálico y fondo suave.
- [ ] Las salidas de herramientas (`tool_output`) aparecen formateadas como bloques de código/JSON.
- [ ] El indicador "En vivo" (verde) pulsa mientras la suscripción a Supabase Realtime está activa.
- [ ] Si la tarea finaliza, el indicador cambia a estado estático (Gris/Done).

### Técnicos
- [ ] Ubicación: `dashboard/components/transcripts/TranscriptTimeline.tsx`.
- [ ] No existen eventos duplicados al pasar del snapshot inicial al stream en vivo.
- [ ] Los eventos mantienen el orden estricto por `sequence` independientemente de su llegada.
- [ ] La suscripción a Supabase se cierra (`unsubscribe`) correctamente al desmontar el componente.
- [ ] Respeta aislamiento multi-tenant: el filtro `aggregate_id = taskId` es mandatorio en la suscripción.

### Robustez
- [ ] El componente maneja estados de error de red sin romper la página completa.
- [ ] Payloads gigantes (>2000 chars) no causan lag en las animaciones de entrada.

## 6. Plan de Implementación

1. **Tarea 1 [Core]:** Crear `dashboard/hooks/useTranscriptTimeline.ts`. Implementar fetch de snapshot y lógica de deduplicación Realtime. (Complejidad: ALTA)
2. **Tarea 2 [UI Atoms]:** Implementar `TimelineEventItem.tsx` con estilos diferenciados y Framer Motion. (Complejidad: MEDIA)
3. **Tarea 3 [UI Container]:** Crear `TranscriptTimeline.tsx` integrando el hook y el componente `ScrollArea` con auto-scroll. (Complejidad: MEDIA)
4. **Tarea 4 [Integration]:** Sustituir la visualización actual en `dashboard/app/(app)/tasks/[id]/transcript/page.tsx` por el nuevo componente. (Complejidad: BAJA)
5. **Tarea 5 [Validation]:** Crear script `LAST/test_3_3_timeline.py` para verificar suscripción y latencia. (Complejidad: MEDIA)

## 7. Riesgos y Mitigaciones
- **Riesgo:** Inundación de eventos (10+ por segundo) saturando el CPU del navegador.
- **Mitigación:** Usar `framer-motion` con `layoutEffect` para optimizar re-renders y limitar el historial visible en memoria a los últimos 200 eventos si no se scrolla.
- **Riesgo:** Inconsistencia de Realtime por RLS mal configurado.
- **Mitigación:** La tarea 5 validará explícitamente la recepción de eventos con el canal configurado.

## 8. 🔮 Roadmap (Post-MVP)
- **Timeline Interactivo:** Click en un paso para ver el "reproducir" parcial del estado del agente en ese punto.
- **Virtualización:** Si el transcript llega a miles de eventos, usar `@tanstack/react-virtual`.
- **Filtros de Auditoría:** Toggle para ocultar `agent_thought` y ver solo resultados técnicos.
