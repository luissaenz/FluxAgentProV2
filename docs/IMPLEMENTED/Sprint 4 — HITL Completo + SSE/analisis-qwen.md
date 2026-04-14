# Análisis Técnico — Sprint 3, Paso 4: Registro de Tools Productivas MCP
**Agente:** qwen
**Alcance:** Registro de 5 tools productivas (`execute_flow`, `get_task`, `approve_task`, `reject_task`, `create_workflow`) como tools MCP estáticas en `src/mcp/tools.py` con handlers funcionales en `src/mcp/handlers.py`.

---

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `execute_flow` tool definida | `src/mcp/tools.py` L62-73 — Tool con `flow_type` + `input_data` | ✅ VERIFICADO | tools.py, inputSchema correcto |
| 2 | `get_task` tool definida | `src/mcp/tools.py` L74-83 — Tool con `task_id` required | ✅ VERIFICADO | tools.py |
| 3 | `approve_task` tool definida | `src/mcp/tools.py` L84-94 — Tool con `task_id` + `notes` | ✅ VERIFICADO | tools.py |
| 4 | `reject_task` tool definida | `src/mcp/tools.py` L95-105 — Tool con `task_id` + `reason` | ✅ VERIFICADO | tools.py |
| 5 | `create_workflow` tool definida | `src/mcp/tools.py` L106-116 — Tool con `description` required | ✅ VERIFICADO | tools.py |
| 6 | Tabla `tasks` existe | Migración 001 L62 — `id UUID PK, org_id, flow_type, status, payload, result, error` | ✅ VERIFICADO | 001_set_config_rpc.sql |
| 7 | Tabla `pending_approvals` existe | Migración 002 L50 — `id UUID PK, org_id, task_id, flow_type, status, payload, decided_by, decided_at` | ✅ VERIFICADO | 002_governance.sql |
| 8 | RLS en `tasks` | Migración 001 L106 — `tasks_org_access` usa `current_org_id()` | ✅ VERIFICADO | 001_set_config_rpc.sql |
| 9 | RLS en `pending_approvals` | Migración 002 L73 — `tenant_isolation_pending_approvals` usa `current_org_id()` | ✅ VERIFICADO | 002_governance.sql |
| 10 | `handle_execute_flow` implementado | `src/mcp/handlers.py` L21-60 — ejecuta flow con timeout 5s, retorna task_id + status | ✅ VERIFICADO | handlers.py |
| 11 | `handle_get_task` implementado | `src/mcp/handlers.py` L62-86 — consulta `tasks` con `org_id` filter | ✅ VERIFICADO | handlers.py |
| 12 | `handle_approve_task` implementado | `src/mcp/handlers.py` L88-95 — delega a `_handle_hitl_decision` | ✅ VERIFICADO | handlers.py |
| 13 | `handle_reject_task` implementado | `src/mcp/handlers.py` L97-104 — delega a `_handle_hitl_decision` | ✅ VERIFICADO | handlers.py |
| 14 | `handle_create_workflow` implementado | `src/mcp/handlers.py` L106-119 — wrapper para `architect_flow` | ✅ VERIFICADO | handlers.py |
| 15 | Router en `handle_tool_call` | `src/mcp/tools.py` L134-147 — mapea las 5 tools a handlers | ✅ VERIFICADO | tools.py |
| 16 | `flow_registry.get()` normaliza nombres | `src/flows/registry.py` L195 — `_normalize_flow_name` convierte PascalCase → snake_case | ✅ VERIFICADO | registry.py |
| 17 | `python-jose` disponible | `pyproject.toml` — `python-jose[cryptography]>=3.3.0` | ✅ VERIFICADO | pyproject.toml |
| 18 | `BaseFlow.execute()` lifecycle | `src/flows/base_flow.py` L102-154 — validate → create_task → start → run_crew → complete | ✅ VERIFICADO | base_flow.py |
| 19 | `BaseFlow.resume()` HITL | `src/flows/base_flow.py` L321-372 — restaura snapshot, emite evento, llama hook | ✅ VERIFICADO | base_flow.py |
| 20 | `BaseFlow.request_approval()` HITL | `src/flows/base_flow.py` L247-297 — pausa flow, crea pending_approval, emite evento | ✅ VERIFICADO | base_flow.py |
| 21 | `sanitize_output` disponible | `src/mcp/sanitizer.py` — 7 patrones regex, recursivo para dict/list | ✅ VERIFICADO | sanitizer.py |
| 22 | `get_service_client` bypass RLS | `src/db/session.py` L42-57 — usa service_role key | ✅ VERIFICADO | session.py |

### Discrepancias Encontradas

**❌ DISCREPANCIA 1: `flow_type` en `tasks` vs registro en `flow_registry`**
- **Plan asume:** `flow_type` en DB coincide con clave de registry ("generic_flow").
- **Código real:** `BaseFlow.flow_type` property (base_flow.py L407) retorna `self.__class__.__name__` → "GenericFlow". Pero `_normalize_flow_name` convierte "GenericFlow" → "generic_flow" para lookup.
- **Problema:** `handle_execute_flow` recibe `flow_type` del usuario (ej: "generic_flow"), busca en registry → OK. Pero `create_task_record` guarda `self.flow_type` ("GenericFlow") en `tasks.flow_type`. Cuando `handle_get_task` retorna el `flow_type` de la task, muestra "GenericFlow", no "generic_flow". Inconsistencia.
- **Impacto:** `create_workflow` retorna datos con `flow_type` inconsistente. HITL resume usa `task_res.data["flow_type"]` para buscar en registry → `_normalize_flow_name` lo corrige, pero es frágil.
- **Resolución:** No bloquea este paso (es preexistente). Documentar como riesgo. Si se corrige, cambiar `BaseFlow.flow_type` para usar `self.__class__.__name__.lower().replace("flow", "_flow")` o mejor: leer del metadata del registry.

**❌ DISCREPANCIA 2: `handle_get_task` usa `execute_with_retry` incorrectamente**
- **Plan asume:** `execute_with_retry` envuelve query builder.
- **Código real:** `handlers.py` L73-78 pasa el query builder directamente a `execute_with_retry`, pero `execute_with_retry` espera un callable o query builder con `.execute()`. El código funciona pero `execute_with_retry` en `db/session.py` L27 retorna `query_builder.execute()` — está correcto.
- **Resolución:** Funciona. No es discrepancia real, solo confirmación.

**❌ DISCREPANCIA 3: `_handle_hitl_decision` no sanitiza output**
- **Plan asume:** Regla R3 — todo output pasa por `sanitize_output()`.
- **Código real:** `_handle_hitl_decision` retorna dict crudo sin pasar por sanitizador. Los handlers individuales (`handle_approve_task`, `handle_reject_task`) también retornan dict sin sanitizar.
- **Impacto:** El sanitizador se aplica en `_make_result` de `tools.py`, pero solo para handlers que retornan `CallToolResult`. Los handlers de `handlers.py` retornan `Dict[str, Any]` y `tools.py` los envuelve en `_make_result` → SÍ sanitiza. OK.
- **Resolución:** Funciona correctamente. El flow de sanitización es: handler retorna dict → `handle_tool_call` llama `_make_result(res)` → `sanitize_output(data)` → retorna `CallToolResult`. Verificado en `tools.py` L163-168.

**⚠️ DISCREPANCIA 4: `handle_get_task` consulta tabla `tasks` que no tiene columna `result` con formato esperado**
- **Verificación:** Migración 001 L62 — `tasks` tiene columna `result JSONB`. `handle_get_task` L78 accede `result.data["result"]`. Correcto.
- **Resolución:** OK, no hay problema.

---

## 1. Diseño Funcional

### Happy Path

**`execute_flow`:**
1. Claude envía `execute_flow(flow_type="generic_flow", input_data={"text": "..."})`.
2. Handler valida `flow_type` no vacío.
3. Busca `flow_class = flow_registry.get(flow_type)` — normaliza nombre si viene en PascalCase.
4. Si no encontrado → `FlowNotFoundError` con lista de flows disponibles.
5. Instancia flow: `flow_class(org_id=config.org_id, user_id="mcp-system")`.
6. Ejecuta `flow.execute(input_data)` con timeout 5s.
7. Si completa en <5s → retorna `{task_id, status, result}`.
8. Si excede 5s → retorna `{task_id, status="pending", message}` — usuario debe hacer polling con `get_task`.

**`get_task`:**
1. Claude envía `get_task(task_id="uuid")`.
2. Handler consulta `tasks` filtrando por `task_id` + `org_id`.
3. Si no existe → `LookupError`.
4. Retorna `{status, result (sanitizado), error}`.

**`approve_task` / `reject_task`:**
1. Claude envía `approve_task(task_id="uuid", notes="...")` o `reject_task(task_id="uuid", reason="...")`.
2. Handler verifica task existe y está en `status="pending_approval"`.
3. Actualiza `pending_approvals.status` a "approved"/"rejected".
4. Llama `flow_instance.resume(task_id, decision, decided_by)` en background.
5. Retorna `{status="processing", message}`.

**`create_workflow`:**
1. Claude envía `create_workflow(description="Crear un flow que...")`.
2. Handler delega a `handle_execute_flow(flow_type="architect_flow", input_data={"description": ...})`.
3. ArchitectFlow genera template, persiste en `workflow_templates`, registra agentes, registra dynamic flow.
4. Retorna `{flow_type, template_id, agents_created, steps_count, message}`.

### Edge Cases

| Edge Case | Tool | Manejo |
|---|---|---|
| `flow_type` no existe | `execute_flow` | `FlowNotFoundError` con lista de flows disponibles |
| `input_data` inválido para flow | `execute_flow` | `ValueError` desde `validate_input` → `InvalidInputError` |
| `task_id` no existe | `get_task` | `LookupError` → MCPError code -32602 |
| Task no está en `pending_approval` | `approve/reject` | `ValueError` → MCPError code -32603 |
| Flow tarda >5s | `execute_flow` | Retorna pending, usuario hace polling |
| `description` muy corta (<10 chars) | `create_workflow` | `ValueError` desde ArchitectFlow.validate_input |

### Manejo de Errores (qué ve el usuario)

- **JSON-RPC Error:** `map_exception_to_mcp_error` convierte excepciones a códigos estándar:
  - `ValueError/TypeError/KeyError` → code -32602 (Invalid params)
  - `LookupError` → code -32602 (Invalid params)
  - Otros → code -32603 (Internal error)
- **isError=True:** `CallToolResult` con `isError=True` y JSON serializado del error.
- **Sanitización:** Todo output pasa por `sanitize_output()` (Regla R3) antes de retornar.

---

## 2. Diseño Técnico

### Componentes Involucrados

**1. `src/mcp/tools.py` — Tool Definitions + Router**
- Ya contiene las 5 tools en `STATIC_TOOLS` list.
- `handle_tool_call()` rutea a handlers correctos.
- Dinámicos: flow tools se rutean a `handle_execute_flow` por nombre.

**2. `src/mcp/handlers.py` — Lógica de Ejecución**
- `handle_execute_flow`: timeout 5s, ejecución async, retorna dict.
- `handle_get_task`: consulta `tasks` con `get_service_client()` (bypass RLS) + filtro org_id.
- `handle_approve_task` / `handle_reject_task`: delegan a `_handle_hitl_decision`.
- `_handle_hitl_decision`: verifica estado, actualiza `pending_approvals`, llama `flow.resume()`.
- `handle_create_workflow`: wrapper para `architect_flow`.

**3. `src/mcp/exceptions.py` — Error Mapping**
- `MCPError` base class con `code`, `data`, `to_dict()`.
- `FlowNotFoundError`, `InvalidInputError` subclasses.
- `map_exception_to_mcp_error()` convierte excepciones genéricas.

**4. `src/mcp/auth.py` — Token Generation**
- `create_internal_token()` genera JWT con `python-jose`.
- No usado directamente por handlers actuales, pero disponible para futura auth.

**5. `src/flows/` — Flow Registry + BaseFlow**
- `flow_registry.get()` normaliza nombres de flow.
- `BaseFlow.execute()` maneja lifecycle completo.
- `BaseFlow.resume()` maneja reanudación HITL.

### Interfaces (Inputs/Outputs)

| Tool | Input | Output (éxito) | Output (error) |
|---|---|---|---|
| `execute_flow` | `flow_type: str`, `input_data: dict` | `{task_id, status, result}` | `FlowNotFoundError`, `ValueError` |
| `get_task` | `task_id: str` | `{status, result, error}` | `LookupError` |
| `approve_task` | `task_id: str`, `notes: str` | `{status="processing", message}` | `ValueError`, `LookupError` |
| `reject_task` | `task_id: str`, `reason: str` | `{status="processing", message}` | `ValueError`, `LookupError` |
| `create_workflow` | `description: str` | `{flow_type, template_id, agents_created, steps_count, message}` | `ValueError`, `FlowNotFoundError` |

### Modelos de Datos (referencia)

**`tasks` table** (migración 001):
```
id UUID PK, org_id UUID, flow_type TEXT, status TEXT,
payload JSONB, result JSONB, error TEXT, correlation_id TEXT,
created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
```

**`pending_approvals` table** (migración 002):
```
id UUID PK, org_id UUID, task_id UUID FK, flow_type TEXT,
description TEXT, payload JSONB, status TEXT CHECK,
decided_by TEXT, decided_at TIMESTAMPTZ, expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ
```

### Integraciones Verificadas

- **Flow Registry → handlers:** `flow_registry.get()` normaliza PascalCase → snake_case. Funciona con "GenericFlow" y "generic_flow".
- **RLS bypass:** `get_service_client()` usa service_role key para queries que necesitan acceso cross-org (solo filtro manual por org_id).
- **Sanitización:** `_make_result()` en `tools.py` aplica `sanitize_output()` a todo output antes de retornar.
- **HITL resume:** `flow.resume()` se ejecuta en background con `asyncio.create_task()`. Si falla, el error no se propaga al caller.

---

## 3. Decisiones

**D1. Tools registradas como estáticas en `tools.py`, no dinámicas.**
- Las 5 tools están en `STATIC_TOOLS` list, no se generan dinámicamente.
- Justificación: Son herramientas de infraestructura, no varían por flow registrado.
- Coherente con `tools.py` existente (5 tools ya estáticas de Sprint 1).

**D2. `execute_flow` usa timeout de 5s con fallback a polling.**
- Si el flow completa en <5s, retorna resultado directo.
- Si excede 5s, retorna `status="pending"` y el usuario debe hacer polling con `get_task`.
- Justificación: MCP Stdio no soporta streaming parcial. Timeout garantiza respuesta inmediata.
- Corrige plan: el plan original no especifica timeout ni polling mechanism.

**D3. HITL resume se ejecuta en background (`asyncio.create_task`).**
- El handler retorna inmediatamente con `status="processing"`.
- Si el resume falla, el error se pierde (no se propaga al caller).
- Justificación: No bloquear la respuesta MCP. El flow continúa en background.
- **Riesgo:** Si resume falla, el usuario no recibe feedback. Mitigar con logging (ya presente).

**D4. `create_workflow` delega en `handle_execute_flow` con `flow_type="architect_flow"`.**
- No implementa lógica propia, solo adapta input.
- Justificación: ArchitectFlow ya existe y funciona. Reutilizar evita duplicación.
- **Discrepancia con plan:** El plan asume `create_workflow` como tool independiente. En código es un wrapper. Funcionalmente equivalente.

**D5. Auth JWT no se usa en handlers actuales.**
- `create_internal_token()` existe en `auth.py` pero ningún handler lo genera ni valida.
- Justificación: Sprint 3 es MVP sin auth externa. Se usará en Sprint 4 (SSE).
- Coherente con `estado-fase.md`: "Auth Bridge genera internal tokens" pero no se consume aún.

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | `execute_flow` ejecuta un flow registrado y retorna resultado en <5s | ✅ Sí: enviar `{"flow_type": "generic_flow", "input_data": {"text": "test"}}` → recibir `{task_id, status, result}` |
| 2 | `execute_flow` retorna pending si flow tarda >5s | ✅ Sí: enviar flow con delay → recibir `{task_id, status="pending", message}` |
| 3 | `execute_flow` retorna error si `flow_type` no existe | ✅ Sí: enviar `flow_type="nonexistent"` → recibir `isError=True` con `FlowNotFoundError` |
| 4 | `get_task` retorna status y result de una task existente | ✅ Sí: consultar task_id válido → recibir `{status, result, error}` |
| 5 | `get_task` retorna error si task_id no existe | ✅ Sí: consultar task_id inexistente → recibir `isError=True` |
| 6 | `approve_task` actualiza task pendiente y reanuda flow | ✅ Sí: crear task con `pending_approval`, aprobar → recibir `status="processing"` |
| 7 | `approve_task` retorna error si task no está en `pending_approval` | ✅ Sí: aprobar task completada → recibir `isError=True` |
| 8 | `reject_task` rechaza task pendiente y marca flow como failed | ✅ Sí: rechazar task con `pending_approval` → recibir `status="processing"` |
| 9 | `create_workflow` genera workflow template vía ArchitectFlow | ✅ Sí: enviar descripción válida → recibir `{flow_type, template_id, agents_created}` |
| 10 | `create_workflow` retorna error si descripción muy corta o vacía | ✅ Sí: enviar `description=""` → recibir `isError=True` |
| 11 | Todo output pasa por `sanitize_output()` (Regla R3) | ✅ Sí: verificar que `_make_result` envuelve todos los retornos en `tools.py` |
| 12 | Errores mapeados a JSON-RPC Error codes | ✅ Sí: verificar que `map_exception_to_mcp_error` se usa en `handle_tool_call` |
| 13 | Las 5 tools aparecen en `list_tools()` de MCP | ✅ Sí: conectar servidor → recibir tool list con 5 tools + dinámicas |

---

## 5. Riesgos

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| 1 | **`flow_type` inconsistente en DB vs registry** (Discrepancia 1) | Medio: queries por `flow_type` pueden fallar si no normalizan | `_normalize_flow_name` corrige lookup, pero datos en DB son inconsistentes. Corregir en futuro sprint cambiando `BaseFlow.flow_type`. |
| 2 | **HITL resume en background sin error handling** (`asyncio.create_task`) | Alto: si resume falla, usuario no recibe feedback | Agregar try/except en `asyncio.create_task` callback que loguee error y actualice task status. |
| 3 | **`handle_get_task` usa `get_service_client()` (bypass RLS)** | Bajo: filtra manualmente por `org_id`, pero si omite el filtro, expone datos cross-org | Verificado: el `.eq("org_id", config.org_id)` está presente. Mantener. |
| 4 | **`execute_flow` timeout de 5s arbitrario** | Medio: flows complejos (ArchitectFlow) pueden tardar >30s. Polling es incómodo para el usuario | Aceptable para MVP. Sprint 4 (SSE) permitirá streaming largo. |
| 5 | **`create_workflow` no valida permisos del usuario** | Bajo: actúa como `mcp-system`. En MVP no hay auth de usuario. Sprint 4 agregará auth. |
| 6 | **No hay tests para handlers MCP** | Alto: cualquier regresión pasa desapercibida. | Crear tests unitarios para cada handler en `tests/test_mcp_handlers.py` como tarea separada (no parte de este paso). |
| 7 | **`pending_approvals` RLS usa `current_org_id()` pero handler usa `get_service_client()`** | Medio: si RPC no setea org_id correctamente, query puede fallar | Verificado: `get_service_client()` bypass RLS — el filtro `.eq("org_id", config.org_id)` es manual y correcto. |

---

## 6. Plan de Implementación

> **Nota:** Este paso ya está **implementado y funcional** en el código. El plan es para verificación y posibles correcciones.

| # | Tarea | Complejidad | Tiempo | Dependencias |
|---|---|---|---|---|
| 1 | Verificar que las 5 tools están registradas en `STATIC_TOOLS` | Baja | 5 min | Ninguna |
| 2 | Verificar que `handle_tool_call` rutea correctamente cada tool | Baja | 10 min | Tarea 1 |
| 3 | Verificar que handlers en `handlers.py` funcionan con flows reales | Media | 20 min | Tarea 2 |
| 4 | Verificar sanitización de output en todos los paths | Baja | 10 min | Tarea 3 |
| 5 | Verificar error mapping a JSON-RPC codes | Baja | 10 min | Tarea 3 |
| 6 | Corregir `BaseFlow.flow_type` para consistencia con registry (opcional) | Media | 30 min | Ninguna |
| 7 | Agregar try/except a `asyncio.create_task` en HITL resume | Baja | 15 min | Ninguna |

**Total estimado:** 1h 40min (verificación completa + 2 correcciones).
**Tareas 1-5:** Verificación (ya implementado).
**Tareas 6-7:** Correcciones recomendadas.

### Dependencias
- Tareas 1-5 son independientes entre sí (solo dependen de que el código existe).
- Tarea 6 (flow_type) requiere cambios en `base_flow.py` y posiblemente migración de datos.
- Tarea 7 (error handling) es independiente.

---

## 🔮 Roadmap (NO implementar ahora)

1. **Auth integration:** Usar `create_internal_token()` para validar identidad del caller en handlers. Requerido para Sprint 4 (SSE).
2. **Streaming output:** Cuando SSE esté disponible, `execute_flow` puede retornar progresos parciales en lugar de polling.
3. **`flow_type` consistency:** Unificar naming entre registry ("generic_flow") y DB ("GenericFlow"). Requiere migración de datos en `tasks.flow_type`.
4. **HITL error feedback:** Si `resume()` falla, actualizar task status y notificar al usuario. Actualmente el error se pierde en background.
5. **Rate limiting:** Prevenir abuso de `execute_flow` (ej: 10 ejecuciones/minuto por org).
6. **Task pagination:** `get_task` retorna una task. Para MVP basta. Futuro: `list_tasks` con filtros por status, flow_type, fecha.
7. **Webhook callbacks:** En lugar de polling con `get_task`, permitir que el flow notifique al caller cuando completa (requiere transporte HTTP, no Stdio).
8. **Tests MCP:** Crear suite de tests para handlers con mocks de DB y flows. Crítico para estabilidad del sistema.

### Pre-requisitos descubiertos para pasos futuros
- **Sprint 4 (SSE):** Requiere que `execute_flow` soporte streaming parcial. Actualmente retorna resultado completo o pending.
- **Sprint 4 (HITL Dashboard UI):** Requiere endpoint REST que liste `pending_approvals` con detalles. Actualmente solo accesible vía MCP tools.
- **Sprint 5 (Expansión catálogo):** No bloqueado por este paso. Solo depende del import script existente.
