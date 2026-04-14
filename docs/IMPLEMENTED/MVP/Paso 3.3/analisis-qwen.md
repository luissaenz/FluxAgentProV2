# Análisis Técnico — Paso 3.3: Crear componente `TranscriptTimeline.tsx`

**Agente:** qwen  
**Fecha:** 2026-04-12  
**Fase:** 3 — Real-time Run Transcripts  
**Alcance:** Componente frontend de suscripción en tiempo real para eventos `flow_step`, `agent_thought` y `tool_output`.

---

## 1. Diseño Funcional

### Happy Path Detallado

1. El usuario navega a la página de transcript de una tarea (`/tasks/{id}/transcript`).
2. El componente `TranscriptTimeline.tsx` se monta con `taskId` y `orgId`.
3. **Fase snapshot:** Se invoca `GET /transcripts/{taskId}` para obtener eventos históricos. Se muestran en orden cronológico con indicación visual del tipo de evento.
4. **Fase streaming:** Se establece una suscripción Supabase Realtime al canal `transcript:{taskId}` filtrando por `aggregate_id=eq.{taskId}` en la tabla `domain_events`.
5. Cada evento recibido se añade a la timeline en la posición correcta (ordenado por `sequence`).
6. La vista hace **auto-scroll** al evento más reciente cuando el usuario no ha hecho scroll manual hacia arriba.
7. Si la tarea está en ejecución (`is_running: true`), se muestra un indicador "En vivo" con animación.
8. Cuando la tarea alcanza un estado terminal, el indicador "En vivo" desaparece y se muestra el estado final.

### Edge Cases Relevantes para MVP

| Escenario | Comportamiento |
|---|---|
| **Task no encontrada / 404** | Mostrar mensaje: "Transcript no encontrado. La tarea puede haber sido eliminada o no pertenece a tu organización." |
| **Error de conexión Realtime** | Mostrar badge "Desconectado" en gris. Reintentar automáticamente cada 5 segundos (máx 3 reintentos). Si falla, mostrar botón "Reconectar". |
| **Eventos duplicados en stream** | Deduplicar por `event.id`. Si el `sequence` ya existe, ignorar. |
| **Snapshot con `has_more: true`** | Mostrar mensaje "Mostrando primeros N eventos. Carga más debajo." con botón "Cargar anteriores" que incrementa `after_sequence` hacia atrás (paginación inversa). |
| **Task en estado terminal al cargar** | No iniciar suscripción Realtime. Solo mostrar snapshot histórico. Mostrar estado final con badge estático. |
| **Payload vacío o null** | No renderizar bloque de código. Solo mostrar badge de tipo y timestamp. |
| **Sin eventos aun** | Mostrar estado vacío: "Esperando eventos del agente..." con spinner sutil. |

### Manejo de Errores — Qué Ve el Usuario

- **Error 503 del backend:** Banner amarillo: *"El transcript no está disponible temporalmente. Reintentando..."* con reintentos automáticos.
- **Error de red genérico:** Banner rojo: *"Error de conexión. Verifica tu red e intenta de nuevo."* con botón "Reintentar".
- **Error de suscripción Realtime (CHANNEL_ERROR):** Badge gris "Sin conexión en tiempo real". El snapshot histórico sigue visible.
- **Timeout de suscripción (>10s sin conectar):** Mensaje informativo debajo del header: *"La conexión en tiempo real tarda más de lo esperado. Los eventos aparecerán cuando se establezca."*

---

## 2. Diseño Técnico

### Componentes

#### 2.1 `TranscriptTimeline.tsx` (componente principal)

**Responsabilidad:** Orquestar la obtención de datos (snapshot + streaming) y renderizar la línea temporal visual.

**Props:**
```
- taskId: string (obligatorio)
- orgId: string (obligatorio)
```

**Estado interno:**
- `events: TranscriptEvent[]` — lista ordenada por `sequence`.
- `isLoading: boolean` — cargando snapshot inicial.
- `isLive: boolean` — conexión Realtime activa y recibiendo eventos.
- `connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error'` — estado de la suscripción.
- `autoScroll: boolean` — si el usuario ha hecho scroll manual hacia arriba (default: true, se desactiva al hacer scroll up).

**Lógica de suscripción:**
1. Al montar: fetch snapshot → set `events`.
2. Crear canal Supabase: `supabase.channel('transcript-timeline:{taskId}')`.
3. Suscribirse a `postgres_changes` con `event: 'INSERT'`, `table: 'domain_events'`, `filter: 'aggregate_id=eq.{taskId}'`.
4. Al recibir evento nuevo: deduplicar por `id`, insertar en posición correcta por `sequence`, actualizar `isLive`.
5. Al desmontar: `supabase.removeChannel(channel)`.

> **Nota:** Se puede reutilizar el hook existente `useFlowTranscript` como base, pero este componente necesita **estado de conexión granular** y **auto-scroll inteligente**, que el hook actual no expone. Se propone **evolucionar** `useFlowTranscript` añadiendo `connectionStatus` como valor retornado, o crear un hook nuevo `useTranscriptTimeline` más especializado. Dado que el hook actual ya funciona, la decisión más segura es **crear un hook nuevo** `useTranscriptTimeline` que internamente use la misma lógica pero con estado extendido.

#### 2.2 `TimelineEvent.tsx` (sub-componente de cada evento)

**Responsabilidad:** Renderizar un evento individual con estilo semántico según `event_type`.

**Props:**
```
- event: TranscriptEvent
- isLatest: boolean — si es el evento más reciente (para highlight temporal)
```

**Render por tipo de evento:**

| `event_type` | Icono (lucide-react) | Color | Layout |
|---|---|---|---|
| `flow_step` | `GitCommit` | Azul (`blue-500`) | Badge + nombre del paso + duración si está en payload |
| `agent_thought` | `Brain` | Púrpura (`purple-500`) | Badge + texto del pensamiento (primer 200 chars, expandible) |
| `tool_output` | `Wrench` | Ámbar (`amber-500`) | Badge + nombre de herramienta + resultado truncado con CodeBlock |

### Interfaces de Datos

Se reutiliza `DomainEvent` de `@/lib/types`. Se añade la interfaz local:

```typescript
interface TranscriptEvent extends DomainEvent {
  sequence: number
}

interface TranscriptSnapshot {
  task_id: string
  flow_type: string | null
  status: string
  is_running: boolean
  sync: {
    last_sequence: number
    has_more: boolean
  }
  events: TranscriptEvent[]
}

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error'
```

### Hook: `useTranscriptTimeline`

**Archivo:** `dashboard/hooks/useTranscriptTimeline.ts`

**Signature:**
```typescript
function useTranscriptTimeline(taskId: string, orgId: string): {
  events: TranscriptEvent[]
  isLoading: boolean
  isRunning: boolean
  isLive: boolean
  connectionStatus: ConnectionStatus
  hasMore: boolean
  loadMore: () => Promise<void>
  reconnect: () => void
}
```

**Diferencia con `useFlowTranscript`:**
- Expone `connectionStatus` detallado.
- Expone `hasMore` y `loadMore()` para paginación.
- Expone `reconnect()` para reintentos manuales.
- Expone `isRunning` derivado del snapshot.

### Auto-Scroll

Se implementa con un `useRef` al contenedor `ScrollArea`. Lógica:
- `autoScrollRef = true` inicialmente.
- Al detectar scroll manual hacia arriba (`onScroll` con `scrollTop < scrollMax - threshold`): `autoScrollRef = false`.
- Al recibir evento nuevo: si `autoScrollRef === true`, hacer `scrollToBottom()`.
- Botón "Ir al final" aparece cuando `autoScrollRef === false` y hay eventos nuevos.

---

## 3. Decisiones

### D1: Hook nuevo vs. modificar `useFlowTranscript`
**Decisión:** Crear `useTranscriptTimeline.ts` como hook nuevo, sin tocar `useFlowTranscript`.  
**Justificación:** `useFlowTranscript` ya está en uso en el transcript page actual. Modificarlo introduce riesgo de regresión. El nuevo hook tendrá estado de conexión granular, paginación y reconexión manual — responsabilidades distintas.

### D2: Animaciones con CSS vs. framer-motion
**Decisión:** Usar **CSS transitions + Tailwind** para animaciones (pulse, fade-in, slide-in). No usar framer-motion para este componente MVP.  
**Justificación:** El proyecto ya tiene framer-motion instalado pero cero componentes lo usan. Introducirlo aquí añade complejidad de bundle sin beneficio diferenciador para una timeline de texto. CSS `animate-pulse`, `animate-fade-in` y `transition-all` son suficientes para la UX premium buscada. Si en roadmap se quiere animaciones de entrada complejas (stagger, spring), se migra después.

### D3: Canal de suscripción naming
**Decisión:** Usar `transcript-timeline:{taskId}` como nombre de canal (no `transcript:{taskId}`).  
**Justificación:** Evitar colisión con otras suscripciones que puedan usar el mismo patrón en la app. Cada componente con su canal dedicado permite cleanup independiente.

### D4: Paginación inversa para `has_more`
**Decisión:** Si `has_more: true`, ofrecer botón "Cargar anteriores" que hace fetch con `after_sequence: 0` y `limit: 500` desde el endpoint.  
**Justificación:** El endpoint soporta `after_sequence` pero solo para eventos > ese valor. Para cargar anteriores, necesitamos el primer bloque (desde 0). Los eventos ya cargados se mantienen; los nuevos se insertan al inicio. Esto es suficiente para MVP. Paginación infinita con scroll se deja para roadmap.

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | El componente monta sin errores con `taskId` y `orgId` válidos | ✅/❌ |
| 2 | Muestra el snapshot inicial de eventos del endpoint `GET /transcripts/{taskId}` | ✅/❌ |
| 3 | Los eventos se ordenan correctamente por `sequence` ascendente | ✅/❌ |
| 4 | La suscripción Realtime recibe eventos nuevos y los añade a la UI sin recarga | ✅/❌ |
| 5 | No hay eventos duplicados en la lista (deduplicación por `id` funciona) | ✅/❌ |
| 6 | Cada tipo de evento (`flow_step`, `agent_thought`, `tool_output`) tiene estilo visual diferenciado (icono + color) | ✅/❌ |
| 7 | El indicador "En vivo" aparece cuando `is_running: true` y desaparece en estado terminal | ✅/❌ |
| 8 | El auto-scroll funciona: baja automáticamente al recibir eventos nuevos si el usuario no ha scrolleado arriba | ✅/❌ |
| 9 | Si la suscripción Realtime falla, se muestra estado de desconexión y botón de reconexión | ✅/❌ |
| 10 | Si no hay eventos, se muestra estado vacío con mensaje apropiado | ✅/❌ |
| 11 | El payload de cada evento se renderiza con `CodeBlock` solo si existe y no está vacío | ✅/❌ |
| 12 | El componente hace cleanup del canal Supabase al desmontar | ✅/❌ |
| 13 | Respeta aislamiento multi-tenant (solo eventos del `org_id` activo) | ✅/❌ |

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Supabase Realtime no envía payloads completos** | Los eventos llegan sin campos necesarios | Ya mitigado: Paso 3.1 configuró `REPLICA IDENTITY FULL`. Validar con script `test_3_1_realtime.py`. |
| **Canal de suscripción se desconecta silenciosamente** | El usuario deja de ver eventos nuevos sin saberlo | Implementar heartbeat visual: si no llegan eventos en >30s y `is_running: true`, mostrar "Verificando conexión..." |
| **Race condition entre snapshot y primer evento del stream** | Evento duplicado o perdido | Deduplicación por `id` + comparar `sequence` contra `last_sequence` del snapshot. Descartar eventos del stream con `sequence <= last_sequence`. |
| **Gran volumen de eventos (>500) causa render lento** | UI se congela o laggea | El endpoint ya trunca a 500 + `has_more`. Para MVP es suficiente. Si hay más, paginación con "Cargar anteriores". Virtualización se deja para roadmap. |
| **El hook `useFlowTranscript` existente y el nuevo hook compiten por el mismo canal** | Interferencia entre componentes | Usar nombre de canal diferente (`transcript-timeline:{taskId}` vs `transcript:{taskId}`). Cada canal es independiente en Supabase. |

---

## 6. Plan

### Tareas Atómicas

| # | Tarea | Complejidad | Dependencias | Archivo(s) |
|---|---|---|---|---|
| 1 | Crear hook `useTranscriptTimeline.ts` con snapshot fetch + Realtime subscription + estado de conexión | Media | Ninguna | `dashboard/hooks/useTranscriptTimeline.ts` |
| 2 | Crear sub-componente `TimelineEvent.tsx` con estilos semánticos por tipo de evento | Baja | Tarea 1 (interfaz) | `dashboard/components/transcripts/TimelineEvent.tsx` |
| 3 | Crear componente principal `TranscriptTimeline.tsx` que consuma el hook y renderice la timeline con auto-scroll | Media | Tarea 1, Tarea 2 | `dashboard/components/transcripts/TranscriptTimeline.tsx` |
| 4 | Integrar `TranscriptTimeline` en la página de transcript (`tasks/[id]/transcript/page.tsx`), reemplazando la render actual | Baja | Tarea 3 | `dashboard/app/(app)/tasks/[id]/transcript/page.tsx` |
| 5 | Implementar manejo de reconexión manual y estados de error de conexión | Baja | Tarea 1 | `dashboard/hooks/useTranscriptTimeline.ts` + UI en Tarea 3 |
| 6 | Implementar paginación "Cargar anteriores" para `has_more` | Baja | Tarea 1 | `dashboard/hooks/useTranscriptTimeline.ts` |
| 7 | Crear script de validación `LAST/test_3_3_timeline.py` que verifique los 13 criterios de aceptación | Media | Tarea 4 | `LAST/test_3_3_timeline.py` |

### Orden Recomendado

```
T1 → T2 → T3 → T4 → T5 → T6 → T7
```

T5 y T6 pueden hacerse en paralelo tras T3. T7 es la última tarea de validación.

### Estimación Relativa

- **Baja:** T2, T4, T5, T6, T7
- **Media:** T1, T3
- **Alta:** Ninguna

---

## 🔮 Roadmap (NO implementar ahora)

| Mejora | Descripción | Por qué no ahora |
|---|---|---|
| **Virtualización de lista** | Usar `@tanstack/react-virtual` para renderizar solo eventos visibles. | Con <500 eventos el rendimiento es aceptable. Se activa cuando haya quejas de performance. |
| **Animaciones con framer-motion** | Entrada staggered de eventos, spring animations, layout transitions. | CSS transitions cubren el MVP. Framer-motion añade ~30KB al bundle. |
| **Búsqueda en transcript** | Input para filtrar eventos por texto dentro del payload. | Necesidad real solo con transcripts muy largos. |
| **Exportar transcript** | Botón para descargar transcript como `.json` o `.txt`. | Útil para debugging pero no crítico para MVP. |
| **Agrupación temporal** | Separadores visuales por minuto/hora ("Hace 2 min", "Hace 5 min"). | Mejora de UX, no funcional. |
| **Transcript colapsable** | Click en evento para expandir/colapsar payload. | Actualmente siempre visible. Con payloads grandes será necesario. |
| **WebSocket propio como fallback** | Si Supabase Realtime falla, usar WebSocket directo al backend. | Supabase Realtime es suficiente para MVP. Fallback es over-engineering ahora. |
| **Marcadores de hitos** | Permitir al usuario marcar eventos importantes ("bookmark"). | Feature de producto, no de infraestructura. |

### Decisiones de Diseño para No Bloquear Roadmap

1. **El hook `useTranscriptTimeline` separa la capa de datos de la de UI.** Esto permite swapar la fuente de datos (Supabase → WebSocket → polling) sin tocar componentes visuales.
2. **`TimelineEvent` es un componente puro y aislado.** Se puede envolver con framer-motion `motion.div` en el futuro sin cambios internos.
3. **El auto-scroll usa ref pattern, no state.** Esto facilita migrar a virtualización sin cambiar la lógica de scroll.
4. **Los estilos semánticos están en un mapa de configuración externo** (`EVENT_TYPE_STYLES`), no hardcodeados en el JSX. Añadir nuevos tipos de evento es añadir una entrada al mapa.
