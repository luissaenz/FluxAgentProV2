# 📋 ANÁLISIS TÉCNICO — Paso 3.3: Componente TranscriptTimeline.tsx

## Paso Asignado
**Paso 3.3 [Frontend]:** Crear componente `TranscriptTimeline.tsx` con lógica de suscripción vía Supabase para eventos `flow_step`, `agent_thought` y `tool_output`.

---

## 1. Diseño Funcional

### 1.1 Happy Path
1. Usuario abre la página de transcript (`/tasks/{id}/transcript`) o la pestaña "Live Transcript" en `/tasks/{id}`
2. Se carga el snapshot histórico desde `GET /transcripts/{task_id}` (ya implementado en paso 3.2)
3. Hook `useFlowTranscript` se suscribe al canal de Supabase para `domain_events`
4. Cada nuevo evento INSERT con `aggregate_id = task_id` se recibe en tiempo real
5. Los eventos se combinan con el historial, deduplican por ID, ordenan por `sequence`
6. La UI renderiza la lista actualizada dinámicamente
7. Indicador visual muestra estado "En vivo" durante la suscripción activa
8. Cuando la tarea entra en estado terminal (`done`, `failed`, `cancelled`, `blocked`), el indicador se desactiva

### 1.2 Edge Cases (MVP)
| Escenario | Manejo |
|-----------|-------|
| Task no existe | API retorna 404, UI muestra mensaje adecuado |
| Realtime falla | Fallback a polling cada 5s o indicador de error |
| Eventos fuera de orden (sequence menor) | Filtrar eventos con sequence ≤ last_sequence del snapshot |
| Task TERMINA mientras el usuario observa | El indicador "En vivo" se desactiva tras actualizar status |
| Gran volumen de eventos (>1000) | El hook ya maneja truncamiento via `has_more` |
| Conexión perdida temporalmente | Reconexión automática de Supabase channel |
| duplicate events en realtime | Deduplicación por ID antes de renderizar |

### 1.3 Manejo de Errores
- **Visual:** Si la suscripción falla, mostrar indicador "Desconectado" con opción de reintentar
- **Toast:** Notificación de error de conexión (solo si es reciente, no spam)
- **Fallback:** Si realtime no responde en 5s, hacer polling al endpoint `/transcripts/{task_id}?after_sequence={last}`

---

## 2. Diseño Técnico

### 2.1 Componentes Existentes (REUTILIZAR)
| Archivo | Rol |
|---------|-----|
| `dashboard/hooks/useFlowTranscript.ts` | Hook que combina snapshot API + realtime subscription |
| `dashboard/app/(app)/tasks/[id]/transcript/page.tsx` | Página que renderiza eventos |
| `dashboard/components/events/EventTimeline.tsx` | Componente UI para timeline (referencia de estilos) |
| `dashboard/lib/supabase.ts` | Cliente Supabase browser |
| `src/api/routes/transcripts.py` | Endpoint snapshot (ya implementado) |

### 2.2 Nuevo Componente: `TranscriptTimeline.tsx`
**Ubicación:** `dashboard/components/events/TranscriptTimeline.tsx`

```tsx
interface TranscriptTimelineProps {
  events: TranscriptEvent[]  // tipo ya definido en useFlowTranscript
  isLive?: boolean
  onRetry?: () => void
}
```

**Responsabilidades:**
1. Renderizar lista de eventos filtrados por tipos: `flow_step`, `agent_thought`, `tool_output`
2. Aplicar animaciones visuales diferenciadas por tipo de evento
3. Auto-scroll al último evento nuevo cuando isLive=true
4. Mostrar indicador de conexión (Live/Desconectado)
5. Permitir refresh manual

### 2.3 Diferenciación Visual por Tipo (MVP)
| Event Type | Badge | icono | Animación entrada |
|-----------|-------|------|-------------------|
| `flow_step` | info | GitBranch | slide-in desde izquierda |
| `agent_thought` | secondary | Lightbulb | fade-in suave |
| `tool_output` | success | Wrench | slide-in desde derecha |

### 2.4 Extensiones Necesarias
- **Hook `useFlowTranscript`:** Añadir manejo de reconnect automático con backoff
- **Hook:** Exponer `lastSequence` para permitir polling fallback
- **Tipos:** Confirmar que `DomainEvent` incluye `sequence` (revisar en `lib/types.ts`)

### 2.5 Integración en Vista de Tarea (Paso 3.4)
El componente se usará en:
- `/tasks/[id]/transcript` (ya existe página, substituir render)
- Nueva pestaña "Live Transcript" en `/tasks/[id]/page.tsx`

---

## 3. Decisiones

### 3.1 Decisiones Nuevas
| Decisión | Justificación |
|---------|--------------|
| NO crear nueva suscripción Realtime | El hook `useFlowTranscript` ya la tiene. REUTILIZAR. |
| Componente como presentacional | El hook maneja lógica de estado. El componente solo renderiza. |
| Auto-scroll solo si usuario está al final | UX: no interrumpir si el usuario está revisando historial |
| Indicador "En vivo" con tono verde | Convención visual consistente con resto del dashboard |

### 3.2 Confirmaciones (vs estado-fase)
- El contrato de `/transcripts/{task_id}` ya incluye `sync.last_sequence` — usar para filtro anti-duplicados ✅
- Tipos de eventos por defecto ya son `flow_step, agent_thought, tool_output` ✅
- El aislamiento multi-tenant se maneja en API, no en frontend ✅

---

## 4. Criterios de Aceptación (✓/✗)

| # | Criterio | Verificable mediante |
|---|---------|-------------------|
| 1 | El componente renderiza eventos históricos al cargar | Apertura de `/tasks/{id}/transcript` muestra lista |
| 2 | Eventos nuevos aparecen sin recarga de página | Ejecución de flow en paralelo |
| 3 | Diferenciación visual clara por tipo de evento | Inspección visual de badges/iconos |
| 4 | Indicador "En vivo" aparece durante suscripción activa | Observar badge verde pulsante |
| 5 | No hay duplicados en la lista | Console log de eventos con mismo ID |
| 6 | Los eventos se ordenan correctamente por sequence | Inspección de orden visual |
| 7 | Auto-scroll al nuevo evento cuando está al final | Scroll manual al final + nuevo evento |
| 8 | Manejo de desconexión con opción de reintentar | Simular desconexión de red |
| 9 | El componente es reutilizable en любой vista | Import en otra página funciona |
| 10 | Latencia UI < 1s desde evento DB | Timestamp comparison |

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|-------|-------------|---------|-----------|
| Realtime no conecta en producción | Media | Alto | Fallback a polling con retry automático |
| Eventos fuera de orden por race condition | Baja | Medio | Filtrar sequence ≤ lastSequence del snapshot |
| Memory leak por múltiples suscripciones | Baja | Alto | Cleanup en useEffect return (ya implementado) |
| Gran volumen de eventos afecta render | Media | Medio | Memoización con React.memo/useMemo |

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Dependencia |
|----|------|------------|-------------|
| 1 | Crear `TranscriptTimeline.tsx` | Media | Tipos existentes |
| 2 | Añadir animaciones CSS para entry | Baja | Componente creado |
| 3 | Mejorar `useFlowTranscript`: reconnect + fallback | Media | Ninguna |
| 4 | Integrar en página transcript existente | Baja | Paso 1 |
| 5 | Test E2E: ejecutar flow y observar realtime | Media | Pasos 1-4 |

### Tarea 1 Detalle: TranscriptTimeline.tsx
```
- Props: events, isLive, onRetry
- Render: lista de TranscriptEventItem (subcomponente)
- Cada item: badge por tipo, icono, contenido formateado
- Auto-scroll: usar useRef + scrollIntoView si isLive
- Indicador de estado: badge "En vivo" / "Desconectado"
```

### Tarea 3 Detalle: Mejoras al Hook
```
- Añadir reconnect con exponential backoff (max 3 intentos)
- Añadir estado de error para UI
- Exponer función manual refresh
```

---

## 🔮 Roadmap (NO Implementar Ahora)

| Item | Razón para postergar |
|------|---------------------|
| Soporte para filtrar por tipo de evento en UI | MVP prioriza simplicidad |
| Búsqueda dentro de payloads | Requiere indexing, no crítico |
| Export transcript como PDF/Markdown | Feature nice-to-have |
| Transcript en modo auditoría (solo lectura) | Post-MVP |
| Tema oscuro para código en payloads | Diseño existentes suficiente |
| Soporte para eventos de otros tipos (approval.*) | Scope definido: solo tipos del paso |

---

## 📎 Referencias Contrato Estado-Fase

- Endpoint: `GET /transcripts/{task_id}` → `{ sync: { last_sequence, has_more }, events: [...] }`
- Tipos por defecto: `flow_step, agent_thought, tool_output`
- Estados terminales: `done, failed, cancelled, blocked`
- Cliente: `createBrowserClient` de `@supabase/ssr` (ya importado en `lib/supabase.ts`)

---

*Análisis generado para el agente OC. Listo para implementación.*