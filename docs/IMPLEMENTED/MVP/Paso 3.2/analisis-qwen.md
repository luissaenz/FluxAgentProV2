# Análisis Técnico — Paso 3.2: Refinar endpoint de Transcripts

## 1. Diseño Funcional

### Problema que resuelve
El endpoint `GET /transcripts/{task_id}` ya existe y funciona para el snapshot histórico, pero el plan pide **optimizar la consulta del snapshot inicial** antes de que el streaming entre. Actualmente el endpoint hace dos queries secuenciales: (1) verifica que la task existe, (2) obtiene los eventos. No hay mecanismo para indicar al cliente si el task sigue "en vivo" (running) o ya finalizó, lo cual es crítico para que el frontend decida si activar la suscripción Realtime.

### Happy path
1. Cliente llama `GET /transcripts/{task_id}` con header `org_id`.
2. Backend valida que la task pertenece al org (tenant isolation vía RLS).
3. Backend retorna un payload unificado con: task metadata + eventos históricos ordenados por secuencia + flag `is_running` que indica si la task está activa.
4. El hook `useFlowTranscript` recibe el flag `is_running` y solo activa la suscripción Realtime si es `true` (ahorro de recursos).

### Edge cases
- **Task no existe:** HTTP 404 (ya implementado).
- **Task existe pero sin eventos:** Retorna array vacío — válido, la task puede estar en `pending` sin eventos emitidos aún.
- **Task en estado terminal (`done`, `blocked`, `failed`):** El flag `is_running=false` le dice al frontend que no necesita suscribirse a Realtime.
- **Org mismatch (RLS):** Si la task no pertenece al org del requestor, `maybe_single()` retorna `null` → 404. La RLS protege el aislamiento.
- **Límite de eventos excedido:** Query actual tiene `limit` configurable (default 200, max 1000). Para transcripts muy largos, el cliente puede paginar.

### Manejo de errores
| Escenario | Respuesta actual | Respuesta refinada |
|-----------|-----------------|-------------------|
| Task no encontrada | `404 "Task not found"` | Sin cambio |
| Org no proporcionido | Middleware rechaza antes | Sin cambio |
| DB timeout / error | Excepción no manejada (500 genérico) | Agregar try/except → `503 "Transcript temporarily unavailable"` con retry guidance |
| RLS bloquea acceso | Retorna `null` → 404 | Sin cambio (comportamiento correcto) |

---

## 2. Diseño Técnico

### Componentes modificados

#### `src/api/routes/transcripts.py` — Endpoint `get_flow_transcript`

**Cambios propuestos:**

```
Response actual:
{
  "task_id": str,
  "flow_type": str,
  "status": str,
  "events": [...]
}

Response refinada:
{
  "task_id": str,
  "flow_type": str,
  "status": str,
  "is_running": bool,       // NUEVO
  "events_count": int,      // NUEVO — total real, no solo los retornados
  "events": [...],
  "has_more": bool          // NUEVO — si se truncó por limit
}
```

**Lógica de implementación:**

1. **Unificar las dos queries en una sola transacción lógica:** Actualmente se abre y cierra `get_tenant_client` dos veces (una para task, otra para events). Se puede optimizar reutilizando el mismo contexto si ambos queries usan el mismo `org_id`.

2. **Calcular `is_running`:** Derivado de `task.status NOT IN ('done', 'blocked', 'failed', 'cancelled')`. Estos estados terminales ya están definidos en el sistema (ver `base_flow.py`).

3. **Contar eventos totales:** Hacer un `count()` separado o usar `count()` de postgrest en la misma query para saber si hay más eventos disponibles.

4. **Agregar manejo de errores explícito:** Envolver la lógica en `try/except` y retornar 503 en caso de fallo de DB.

5. **No cambiar la query base:** La query actual ya está optimizada — usa el índice `idx_domain_events_aggregate(aggregate_type, aggregate_id)` que existe en la migración 001.

### No se requieren cambios en:
- **Database:** Los índices ya existen (`idx_domain_events_aggregate`, `idx_domain_events_correlation`).
- **EventStore:** Sin cambios.
- **Frontend hook `useFlowTranscript`:** Ya maneja la combinación histórico + realtime. Solo necesita consumir el nuevo campo `is_running`.
- **Frontend `transcript/page.tsx`:** Puede usar `is_running` para mostrar/ocultar el badge "En vivo" basado en datos del server en lugar de depender solo del estado de la suscripción.

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|----------|--------------|
| 1 | **No implementar SSE/streaming HTTP por ahora** | La Fase 3 usa Supabase Realtime (ya configurado en Paso 3.1) para el streaming lado cliente. El backend solo provee el snapshot inicial. Implementar SSE duplicaría la infraestructura y no agrega valor al MVP. |
| 2 | **Mantener el índice existente sin crear nuevos** | `idx_domain_events_aggregate(aggregate_type, aggregate_id)` ya cubre el patrón de consulta `WHERE aggregate_id = ? ORDER BY sequence`. No se necesita índice adicional para el MVP. |
| 3 | **Derivar `is_running` de estados terminales conocidos** | No requiere cambio en el schema. Los estados terminales ya están definidos en el código existente. Alternativa: agregar columna `is_terminal` a tasks — overkill para MVP. |
| 4 | **No cambiar la firma de la API, solo extender el response** | Agregar campos al response JSON es backwards compatible. Los campos existentes se mantienen. |
| 5 | **No unificar las dos queries en una sola conexión DB** | `get_tenant_client` es un context manager liviano. Abrirlo dos veces no tiene impacto significativo en performance. Unificarlas agregaría complejidad sin beneficio medible. Se mantiene la simplicidad. |

---

## 4. Criterios de Aceptación

- [ ] El response de `GET /transcripts/{task_id}` incluye el campo `is_running` (boolean).
- [ ] El response incluye el campo `events_count` (int) con el total de eventos para esa task.
- [ ] El response incluye el campo `has_more` (boolean) indicando si se truncó por el parámetro `limit`.
- [ ] Si la task está en estado `done`, `blocked`, `failed` o `cancelled`, `is_running` es `false`.
- [ ] Si la task está en estado `running` o `pending_approval`, `is_running` es `true`.
- [ ] Si la task no existe, el endpoint retorna `404` sin excepciones no manejadas.
- [ ] Si la DB falla (timeout, conexión), el endpoint retorna `503` con mensaje descriptivo.
- [ ] Los eventos retornados están ordenados por `sequence` ascendente.
- [ ] La query respeta RLS — una task de otra org retorna 404.
- [ ] El parámetro `limit` sigue funcionando (default 200, max 1000).

---

## 5. Riesgos

| # | Riesgo | Mitigación |
|---|--------|-----------|
| 1 | **Race condition: task termina entre la query del snapshot y la suscripción Realtime** | El frontend ya maneja esto: si se suscribe y no llegan eventos, el canal expira. El flag `is_running` es una señal, no una garantía. Para MVP es suficiente. |
| 2 | **PostgREST `count()` puede ser lento en tablas grandes** | No usar `count()` genérico. En su lugar, hacer una query con `limit + 1` y si retorna más de `limit` items, inferir `has_more=true`. Opcional: agregar campo `total_events` solo si se necesita para UI de paginación. **Decisión para MVP:** omitir `events_count` si afecta performance, mantener solo `has_more` vía query `limit + 1`. |
| 3 | **El campo `is_running` puede quedar desactualizado si el task cambia de estado rápidamente** | Es inherentemente eventual. El snapshot refleja el estado al momento de la consulta. El streaming Realtime corrige la divergencia. Documentar en el response. |
| 4 | **Si el índice `idx_domain_events_aggregate` no cubre `ORDER BY sequence`, la query puede hacer sort en memoria** | Verificar con EXPLAIN ANALYZE. Si el sort es in-memory y costoso, agregar índice compuesto `(aggregate_id, sequence)`. **Acción diferida al Paso 3.5** (test de latencia). |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|-------|:-----------:|-------------|
| 6.1 | Agregar campo `is_running` al response (lógica: status ∉ terminales) | Baja | — |
| 6.2 | Agregar manejo de errores con try/except → HTTP 503 | Baja | — |
| 6.3 | Agregar campo `has_more` (query limit+1 para detectar truncamiento) | Media | — |
| 6.4 | Agregar campo `events_count` opcional (solo si no impacta performance) | Media | 6.3 |
| 6.5 | Actualizar tipos TypeScript en `useFlowTranscript.ts` para consumir `is_running` | Baja | 6.1 |
| 6.6 | Verificar con EXPLAIN ANALYZE que la query usa el índice correctamente | Baja | — |

**Orden recomendado:** 6.1 → 6.2 → 6.3 → 6.5 → 6.4 → 6.6

**Notas de implementación:**
- Tareas 6.1-6.4 son puramente backend y pueden implementarse en un solo PR.
- Tarea 6.5 depende de 6.1 pero es trivial (agregar campo a la interfaz TypeScript).
- Tarea 6.6 es de validación y debe hacerse con datos realistas (no solo con datos de test).

---

## 🔮 Roadmap (NO implementar ahora)

1. **Server-Sent Events (SSE) directo del backend:** Para entornos sin Supabase o donde Realtime no esté disponible, un endpoint `GET /transcripts/{task_id}/stream` con SSE ofrecería streaming puro desde el backend. Requiere `StreamingResponse` de FastAPI y un mecanismo de polling largo o pub/sub interno.

2. **Paginación de transcripts:** Para tasks con miles de eventos, implementar paginación cursor-based (`?after_sequence=1234`) en lugar de limit/offset.

3. **Filtrado por tipo de evento:** `?event_type=agent_thought,tool_output` permitiría al frontend suscribirse solo a eventos relevantes.

4. **Índice compuesto `(aggregate_id, sequence)`:** Si EXPLAIN ANALYZE revela que el índice actual `idx_domain_events_aggregate(aggregate_type, aggregate_id)` no cubre el ORDER BY sequence de forma eficiente, crear este índice compuesto optimizaría la query a un index scan puro.

5. **Cache de snapshot:** Para transcripts de tasks ya finalizadas (inmutables), un cache Redis/CDN del response completo eliminaría la query a DB en lecturas repetidas.

6. **WebSocket dedicado para transcripts:** Si Supabase Realtime demuestra latencia inconsistente en producción, un WebSocket propio con buffer de reconexión daría control total sobre la entrega de eventos.
