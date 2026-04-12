# Análisis Técnico — Paso 3.4: Integración en la Vista de Tarea (Live Transcript)

## 1. Diseño Funcional

### Happy Path
1. El usuario navega a la página de detalle de una tarea (`/tasks/{id}`).
2. La página muestra la información actual de la tarea (estado, resultado, error) junto con un sistema de pestañas (tabs).
3. Las pestañas disponibles son:
   - **"Detalles"**: La vista actual con información de la tarea y el timeline de eventos estático (ya existente).
   - **"Live Transcript"**: El componente `TranscriptTimeline` integrado, mostrando eventos en tiempo real.
4. Si la tarea está en ejecución (`is_running === true`), la pestaña "Live Transcript" muestra un indicador visual claro (badge pulsante "En vivo") y el canal de Supabase se conecta automáticamente.
5. Si la tarea está en estado terminal (`is_running === false`), la pestaña "Live Transcript" muestra el historial completo de eventos sin intentar conexión en tiempo real, pero mantiene la capacidad de reconectar si la tarea se re-ejecuta.
6. El usuario puede alternar entre pestañas sin perder el estado de la suscripción en tiempo real (el canal permanece activo mientras la página esté montada).

### Edge Cases (MVP)
- **Tarea sin eventos aún**: El transcript muestra un mensaje "Esperando eventos del agente..." con indicador de carga sutil.
- **Tarea finalizada con eventos**: El transcript muestra el historial completo sin activar suscripción realtime (solo lectura).
- **Re-ejecución de tarea**: Si el usuario ejecuta nuevamente una tarea desde la vista de detalle, el transcript debe detectar el cambio de `is_running` y reactivar la suscripción automáticamente (ya soportado por `useTranscriptTimeline`).
- **Cambio de tarea (navegación)**: Si el usuario navega a otra tarea, el canal anterior se limpia correctamente antes de crear el nuevo (ya manejado por el cleanup del hook).

### Manejo de Errores
- **Error de conexión a Supabase**: Se muestra el banner amarillo con mensaje "Error de conexión en tiempo real. Los eventos históricos siguen disponibles." + botón "Reintentar". Ya implementado en `TranscriptTimeline`.
- **Error del endpoint de snapshot (`GET /transcripts/{id}`)**: React Query maneja el estado de error; se muestra un mensaje genérico "No se pudo cargar el transcript" con opción de reintentar.
- **Task no encontrada**: La página ya maneja este caso con "Tarea no encontrada".

## 2. Diseño Técnico

### Componentes Existentes a Reutilizar
| Componente | Ruta | Rol |
|---|---|---|
| `TranscriptTimeline` | `@/components/transcripts/TranscriptTimeline` | Componente principal del transcript con realtime |
| `useTranscriptTimeline` | `@/hooks/useTranscriptTimeline` | Hook de datos: snapshot REST + suscripción Supabase |
| `TimelineEvent` | `@/components/transcripts/TimelineEvent` | Renderizado individual de eventos |

### Componentes Existentes a Modificar
| Componente | Ruta | Modificación |
|---|---|---|
| `TaskDetailPage` | `dashboard/app/(app)/tasks/[id]/page.tsx` | Añadir sistema de pestañas (Tabs) con dos tabs: "Detalles" y "Live Transcript" |

### Nueva Estructura de la Página de Tarea

```
TaskDetailPage
├── Header (BackButton + Título + StatusLabel)
├── TabsRoot
│   ├── TabTrigger: "Detalles"
│   ├── TabTrigger: "Live Transcript" (con badge "LIVE" si is_running)
│   ├── TabContent: "Detalles"
│   │   ├── Card: Información de la tarea
│   │   └── Card: Timeline de Eventos (estático, existente)
│   └── TabContent: "Live Transcript"
│       └── TranscriptTimeline (taskId, orgId)
```

### Interfaces

**TaskDetailPage** (modificada):
- Input: `useParams<{ id: string }>()` (sin cambios)
- Queries existentes mantenidas: `task`, `events`
- Nueva query: `transcript` snapshot para obtener `is_running` y mostrar el badge "LIVE" en el tab

### Modelo de Datos

No se requieren cambios al modelo de datos. Se reutilizan:
- `Task` (ya consultado vía `GET /tasks/{id}`)
- `TranscriptSnapshot` (ya consultado vía `GET /transcripts/{id}`) — se necesita solo el campo `is_running` para el badge del tab.

### Integración con Componente Existente

Actualmente existe una página separada `/tasks/{id}/transcript` que renderiza `TranscriptTimeline` de forma aislada. El paso 3.4 **no elimina** esta ruta, sino que **integra** el transcript como una pestaña dentro de la vista principal de la tarea. Esto permite:

1. Que el usuario que prefiere vista dedicada siga accediendo a `/tasks/{id}/transcript`.
2. Que el usuario que quiere contexto + transcript en un solo lugar use la pestaña integrada.

**Decisión**: La página `/tasks/{id}/transcript` se mantiene como fallback. El link "Ver Transcript" en el header de `TaskDetailPage` se conserva.

## 3. Decisiones

### D3.4.1: Sistema de pestañas con `Tabs` de shadcn/ui
**Decisión**: Usar el componente `Tabs` de shadcn/ui (ya presente en el proyecto) en lugar de implementar un tab system custom.
**Justificación**: Consistencia con el design system existente, accesibilidad garantizada (ARIA), menor superficie de bugs.

### D3.4.2: El transcript se monta solo cuando el tab está activo
**Decisión**: El componente `TranscriptTimeline` se renderiza condicionalmente solo cuando el tab "Live Transcript" está seleccionado (lazy mount).
**Justificación**: Evita suscripciones innecesarias a Supabase cuando el usuario no está viendo el transcript. Ahorra conexiones de WebSocket y ciclos de renderizado.

### D3.4.3: Badge "LIVE" en el tab condicional a `is_running`
**Decisión**: El tab "Live Transcript" muestra un pequeño indicador verde pulsante solo cuando la tarea está en ejecución.
**Justificación**: Señal visual inmediata para el usuario de que el transcript está recibiendo datos en tiempo real. Coherente con el contrato UI Design System definido en `estado-fase.md`.

### D3.4.4: No se elimina la ruta `/tasks/{id}/transcript`
**Decisión**: Mantener la ruta dedicada como acceso alternativo.
**Justificación**: Algunos usuarios pueden preferir la vista dedicada a pantalla completa. Eliminarla sería un breaking change sin beneficio para el MVP.

## 4. Criterios de Aceptación

- [ ] La página `tasks/[id]/page.tsx` muestra dos pestañas: "Detalles" y "Live Transcript".
- [ ] La pestaña "Detalles" conserva toda la funcionalidad actual (info de tarea + timeline de eventos estático).
- [ ] La pestaña "Live Transcript" renderiza el componente `TranscriptTimeline` con el `taskId` y `orgId` correctos.
- [ ] Cuando la tarea está en ejecución (`is_running === true`), el tab "Live Transcript" muestra un badge "LIVE" con animación pulsante verde.
- [ ] Cuando la tarea está en estado terminal, el tab "Live Transcript" no muestra el badge "LIVE" pero sigue mostrando el historial de eventos.
- [ ] El transcript se monta/desmonta correctamente al cambiar entre pestañas (verificar que la suscripción de Supabase se limpia al desmontar).
- [ ] El link "Ver Transcript" en el header sigue funcionando y lleva a `/tasks/{id}/transcript`.
- [ ] No hay errores de consola al navegar entre tareas o cambiar de pestaña.
- [ ] El auto-scroll del transcript funciona correctamente cuando el usuario está en la pestaña "Live Transcript".

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Fuga de conexiones Supabase**: Si el usuario cambia rápidamente de tab, podrían quedar canales huérfanos. | Alto | `TranscriptTimeline` ya tiene cleanup en `useEffect` que llama a `supabase.removeChannel`. Verificar que el desmontaje por cambio de tab triggera el cleanup correctamente. |
| **Doble query innecesaria**: La página ya hace `useQuery` para `task` y `events`. Añadir la query de snapshot de transcript aumenta la carga inicial. | Bajo | La query de snapshot es ligera (un endpoint REST simple). Se puede habilitar `staleTime` alto ya que `is_running` cambia poco frecuentemente. |
| **Conflicto visual entre los dos timelines**: La pestaña "Detalles" tiene `EventTimeline` (estático) y "Live Transcript" tiene `TranscriptTimeline` (realtime). El usuario podría confundirlos. | Medio | Diferenciar claramente con títulos: "Timeline de Eventos" vs "Live Transcript". El primero es histórico, el segundo es en vivo. |
| **Performance con muchos eventos**: Si una tarea genera cientos de eventos, el `TranscriptTimeline` podría volverse pesado. | Medio | Ya implementado: paginación con `loadMore`, virtualización pendiente como mejora post-MVP. |

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|---|---|---|
| 1 | Importar componentes `Tabs` de shadcn/ui en `TaskDetailPage` | Baja | — |
| 2 | Reestructurar el layout actual dentro de `TabsContent` para "Detalles" | Baja | Tarea 1 |
| 3 | Crear segundo `TabsContent` para "Live Transcript" con `TranscriptTimeline` | Baja | Tarea 1 |
| 4 | Añadir query de snapshot de transcript para obtener `is_running` y mostrar badge "LIVE" en el tab | Media | Tarea 3 |
| 5 | Verificar cleanup de suscripción al cambiar de tab | Media | Tarea 3 |
| 6 | Test manual: crear tarea, ejecutar, verificar transcript en tiempo real | Baja | Tareas 1-5 |
| 7 | Test manual: navegar entre tabs, verificar que no hay fugas de conexión | Baja | Tareas 1-5 |
| 8 | Actualizar `estado-fase.md` marcando paso 3.4 como completado | Baja | Tareas 6-7 |

**Orden recomendado**: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

---

## 🔮 Roadmap (NO implementar ahora)

- **Virtualización del Timeline**: Reemplazar el renderizado completo de eventos por virtualización (`react-virtuoso` o similar) cuando el número de eventos exceda ~100. Actualmente el paginado inverso con `loadMore` es suficiente para MVP.
- **Persistencia de estado de tab**: Guardar la pestaña activa en URL search params (`?tab=transcript`) para que al compartir el link el destinatario vea directamente el transcript.
- **Filtros en el Transcript**: Permitir filtrar eventos por tipo (`agent_thought`, `tool_output`, `flow_step`) con toggles en el header del transcript.
- **Búsqueda en Transcript**: Campo de búsqueda textual para encontrar eventos específicos por contenido de payload.
- **Exportar Transcript**: Botón para descargar el transcript como JSON o Markdown para auditorías.
- **Unificar las dos vistas de Timeline**: Evaluar si `EventTimeline` (estático) y `TranscriptTimeline` deberían converger en un solo componente con modo realtime opcional, reduciendo duplicación de código.
- **Notificación push**: Cuando el usuario está en otro tab y llegan eventos nuevos, mostrar una notificación tipo toast o incrementar un contador en el tab "Live Transcript".
