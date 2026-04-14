# Análisis Técnico — Paso 3.2: Refinar Endpoint de Transcripts

## Agente: claude
## Fase: 3 — Real-time Run Transcripts
## Fecha: 2026-04-12

---

## 1. Diseño Funcional

### 1.1 Problema que Resuelve

El endpoint actual `GET /transcripts/{task_id}` entrega un snapshot completo de todos los eventos de dominio para una tarea. Sin embargo, presenta dos problemas para el caso de uso de streaming en tiempo real:

1. **Sin filtro por tipo de evento:** Retorna todos los eventos (incluyendo `approval.requested`, `task.completed`, etc.) cuando el transcript solo necesita mostrar `flow_step`, `agent_thought` y `tool_output`.
2. **Sin soporte para pagination cursor-based:** El frontend no puede hacer "catch-up" eficiente — si obtiene los últimos 200 eventos y luego se subscribe al realtime, puede recibir duplicados de eventos que ya recibió.

### 1.2 Happy Path Detallado

**Flujo actual (problemático):**
1. Frontend llama `GET /transcripts/{task_id}` → recibe hasta 200 eventos (todos los tipos)
2. Frontend se suscribe al canal realtime `transcript:{task_id}`
3. Cuando llega un nuevo evento, se añade a la lista local
4. **Problema:** Los últimos N eventos del snapshot pueden llegar también por realtime como duplicados

**Flujo optimizado (objetivo):**
1. Frontend llama `GET /transcripts/{task_id}?types=flow_step,agent_thought,tool_output&after_sequence=0`
2. Recibe solo los eventos relevantes para el transcript (filtrados por tipo)
3. Frontend guarda `last_sequence` del último evento recibido
4. Frontend se subscribe al canal realtime
5. Cuando llega un nuevo evento por realtime, lo añade SIN duplicados (comparando por `id` o `sequence`)
6. Si el frontend necesita hacer "catch-up" (paginación), usa `?after_sequence=X&limit=Y`

### 1.3 Edge Cases

| Escenario | Comportamiento Esperado |
|-----------|------------------------|
| Task no existe | HTTP 404 con mensaje claro |
| Task existe pero no tiene eventos | Retornar `events: []` con status 200 |
| Secuencia específica no existe (`after_sequence` > max) | Retornar `events: []` (no error) |
| Tipos no reconocidos en `types` | Ignorar silently, no fallar |
| Task en curso con eventos siendo escritos | El snapshot captura todos los eventos hasta el momento de la llamada; realtime recibirá los nuevos |
| Payload muy grande en algún evento | El endpoint no trunca; frontend debe manejar visualización |

### 1.4 Manejo de Errores

| Situación | Respuesta HTTP | Mensaje |
|-----------|---------------|---------|
| Task no existe | 404 | `"Task not found"` |
| org_id no proporcionado o inválido | 401 | `"Missing or invalid organization context"` |
| Error de base de datos | 500 | `"Failed to retrieve transcript"` + log en servidor |

---

## 2. Diseño Técnico

### 2.1 Modificación al Endpoint Existente

**Archivo:** `src/api/routes/transcripts.py`

**Parámetros nuevos (query string):**
- `types` (opcional): Lista de `event_type` separados por coma. Valores válidos: `flow_step`, `agent_thought`, `tool_output`, `approval.requested`, `task.completed`, `task.failed`. Default: todos.
- `after_sequence` (opcional): Entero >= 0. Retorna solo eventos con `sequence > after_sequence`. Útil para pagination y deduplicación. Default: 0 (todos).
- `limit` (ya existe): 1-1000, default 200.

**Respuesta sin cambios en estructura:**
```json
{
  "task_id": "uuid",
  "flow_type": "bartenders_preventa",
  "status": "running",
  "events": [
    {
      "id": "uuid",
      "event_type": "agent_thought",
      "aggregate_type": "flow",
      "aggregate_id": "task-uuid",
      "payload": {"content": "Analizando opciones..."},
      "sequence": 42,
      "created_at": "2026-04-12T10:30:00Z"
    }
  ]
}
```

### 2.2 Cambios en la Lógica de Consulta

La consulta debe:
1. Filtrar por `aggregate_id = task_id` (ya existe)
2. Filtrar por `org_id = org_id` (ya existe, vía RLS + middleware)
3. **NUEVO:** Filtrar por `event_type IN (types)` si `types` está presente
4. **NUEVO:** Agregar `sequence > after_sequence` si `after_sequence > 0`
5. Ordenar por `sequence ASC` (ya existe)
6. Aplicar `LIMIT` (ya existe)

**Importante:** El filtro por tipos es inclusivo — si se especifican `types=flow_step,agent_thought` se retornan solo esos dos tipos. Si no se especifican, se retornan todos (comportamiento actual).

### 2.3 Compatibilidad hacia atrás

El endpoint actual no tiene parámetros de query, así que todas las llamadas existentes seguirán funcionando igual. El default behavior (todos los eventos, desde sequence 0) se mantiene.

### 2.4 Componentes Involucrados

| Componente | Cambio | Justificación |
|------------|--------|---------------|
| `src/api/routes/transcripts.py` | Modificar función `get_flow_transcript` | Añadir filtros de tipos y secuencia |
| `src/db/session.py` | Sin cambios | El `TenantClient` ya maneja RLS correctamente |
| Tests de validación | Crear script `LAST/test_3_2_transcript_optimization.py` | Validar que los filtros funcionan correctamente |

### 2.5 Integración con Frontend

El frontend actual en `dashboard/hooks/useFlowTranscript.ts` ya:
1. Obtiene el snapshot histórico
2. Se suscribe al realtime
3. Deduplica por `id`

**NO se requiere cambios en el frontend para el Paso 3.2** — la optimización es puramente de eficiencia de transferencia de datos (menos bytes en el snapshot).

Sin embargo, el frontend SÍ se beneficiaría si el endpoint soporta `types` para filtrar eventos irrelevantes del transcript, pero eso es una mejora opcional para el Paso 3.4 (integración en Vista de Tarea).

---

## 3. Decisiones

### Decisión 1: Filtrar por tipos de evento en el endpoint vs. filtrar en frontend

**Opción elegida:** Filtrar en el endpoint (backend).

**Justificación:**
- Reduce transferencia de datos (el snapshot inicial puede ser grande)
- El endpoint conoce el esquema de `domain_events` y puede optimizar la query
- Frontend no necesita procesar eventos que no va a mostrar

**Esta decisión NO contradice nada en `estado-fase.md`** — el documento solo establece que el endpoint debe optimizar el snapshot inicial, sin especificar el mecanismo.

### Decisión 2: Comportamiento de `after_sequence` cuando no existen eventos

**Opción elegida:** Retornar array vacío, no error.

**Justificación:**
- Es un caso válido (ej: tarea nueva sin eventos aún)
- Consistente con el comportamiento actual cuando no hay eventos
- El frontend puede manejar `events: []` sin lógica especial

### Decisión 3: Separación entre snapshot y streaming

**Opción elegida:** Mantener ambos en el mismo endpoint con parámetros de query.

**Justificación:**
- Un solo endpoint para obtener el historial
- Parámetros opcionales permiten flexibilidad
- Breaking change: Ninguno (todos los parámetros tienen default values)

---

## 4. Criterios de Aceptación

| # | Criterio | Condición verificable |
|---|----------|----------------------|
| 1 | Task existente retorna eventos | Llamar `GET /transcripts/{existing_task_id}` retorna status 200 y array de eventos |
| 2 | Task inexistente retorna 404 | Llamar con ID inventado retorna 404 |
| 3 | Filtrado por tipos funciona | `GET /transcripts/{task_id}?types=agent_thought` retorna solo eventos de ese tipo |
| 4 | Filtrado por secuencia funciona | `GET /transcripts/{task_id}?after_sequence=X` retorna solo eventos con sequence > X |
| 5 | Combinación de filtros funciona | `GET /transcripts/{task_id}?types=flow_step,agent_thought&after_sequence=10&limit=50` |
| 6 | Compatibilidad hacia atrás | Llamar sin parámetros retorna todos los eventos (comportamiento actual) |
| 7 | Limit enforced | `GET /transcripts/{task_id}?limit=10` retorna máximo 10 eventos |
| 8 | Deduplicación en frontend funciona | eventos con mismo `id` no aparecen duplicados en la UI |
| 9 | RLS enforcement | Query solo retorna eventos del org_id del usuario autenticado |

---

## 5. Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|--------------|---------|------------|
| R1 | Nueva query con filtros es más lenta que query simple | Baja | Baja | Los filtros son件数 simples (`IN` y `>`), no afectan performance significativamente |
| R2 | Frontend no usa los nuevos parámetros y sigue descargando todos los eventos | Baja | Baja | El hook actual funciona, los cambios son backward-compatible. En 3.4 se optimizará el frontend |
| R3 | Tipos de evento no coinciden con lo que el frontend espera | Media | Media | Verificar con script de validación que los tipos usados en flows (`flow_step`, `agent_thought`, `tool_output`) están siendo emitidos correctamente |

---

## 6. Plan

### Tarea 1: Modificar endpoint `get_flow_transcript`
**Complejidad:** Baja
**Archivos:** `src/api/routes/transcripts.py`

Implementar:
1. Añadir parámetros de query `types` y `after_sequence`
2. Construir filtros dinámicamente en la query de Supabase
3. Validar que el querybuilder aplica los filtros correctamente

```python
# Pseudocódigo de la lógica de filtros
filters = []
if types:
    type_list = types.split(',')
    filters.append(f"event_type=in.({','.join(type_list)})")
if after_sequence and after_sequence > 0:
    filters.append(f"sequence=gt.{after_sequence}")
# Aplicar filtros al query...
```

### Tarea 2: Crear script de validación
**Complejidad:** Baja
**Archivos:** `LAST/test_3_2_transcript_optimization.py`

Validar:
- GET con cada combinación de parámetros
- Verificar que los filtros aplican correctamente
- Verificar 404 para task inexistente

### Dependencias
- Paso 3.1 completado (ya realizado — Realtime habilitado)
- Paso 3.3 (TranscriptTimeline.tsx) depende de este endpoint optimizado

---

## 🔮 Roadmap (NO implementar ahora)

### Mejoras para después del MVP

1. **Paginación con cursor:** Implementar `before_sequence` para ir hacia atrás en el historial (para tareas largas donde el usuario quiere ver eventos antiguos).

2. **Payload truncado:** Para eventos con payload muy grande (ej: logs extensos), ofrecer opción de payload resumido (`?payload_summary=true`) que solo retorna los primeros 500 caracteres.

3. **Filtros por fecha:** Añadir `from_date` y `to_date` para filtrar eventos por timestamp.

4. **WebSocket endpoint alternativo:** Para casos donde el cliente no puede usar Supabase Realtime (ej: server-to-server), ofrecer un endpoint SSE (`GET /transcripts/{task_id}/stream`) que hace streaming de eventos via Server-Sent Events.

5. **Agregación de eventos:** En lugar de retornar cada evento individual, permitir que el endpoint retorne "resúmenes" de eventos agrupados (ej: todos los `tool_output` de un step agrupados).

6. **Exportación:** Endpoint para exportar transcript completo en formato JSON o CSV para debugging o auditing.

---

## Nota de Implementador

El código de `src/api/routes/transcripts.py` actual ya tiene la estructura correcta para modificar — solo necesita añadir los filtros de query. La lógica de Supabase en el cliente soporta encadenamiento de filtros naturalmente.

**IMPORTANTE:** NO modificar `src/crews/` ni `src/flows/multi_crew_flow.py` — estos están protegidos según CLAUDE.md.