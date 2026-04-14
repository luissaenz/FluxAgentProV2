# ANÁLISIS TÉCNICO — Sprint 3 (Handlers Productivos)

**Agente:** oc  
**Fecha:** 2026-04-14  
**Paso:** Sprint 3 — Handlers de ejecución, Auth Bridge y mapeo de errores JSON-RPC

---

## 0. VERIFICACIÓN CONTRA CÓDIGO FUENTE

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|------------|
| 1 | `src/mcp/handlers.py` crear | `ls src/mcp/` | ❌ | No existe — archivo pendiente Sprint 3 |
| 2 | `src/mcp/auth.py` crear | `ls src/mcp/` | ❌ | No existe — archivo pendiente Sprint 3 |
| 3 | `src/mcp/exceptions.py` crear | `ls src/mcp/` | ❌ | No existe — archivo pendiente Sprint 3 |
| 4 | Tabla `tasks` existe | `migrations/001 L62` | ✅ | `CREATE TABLE tasks (id UUID, org_id UUID, flow_type TEXT, status, payload, result, error...)` |
| 5 | Tabla `snapshots` existe | `migrations/001 L76` | ✅ | `CREATE TABLE snapshots (task_id UUID PRIMARY KEY, org_id, flow_type, status, state_json...)` |
| 6 | FlowRegistry existe | `src/flows/registry.py` | ✅ | `flow_registry.get(name)`, `create(name, **kwargs)` disponibles |
| 7 | BaseFlow.execute() existe | `src/flows/base_flow.py L103` | ✅ | `async def execute(self, input_data, correlation_id)` retorna `BaseFlowState` |
| 8 | `_get_jwks_client()` en middleware | `src/api/middleware.py L73` | ✅ | Singleton PyJWKClient con cache 5min, headers con apikey |
| 9 | `python-jose` en dependencies | `pyproject.toml L20` | ✅ | `python-jose[cryptography]>=3.3.0` |
| 10 | `mcp>=1.0.0,<2.0.0` en dependencies | `pyproject.toml L30` | ✅ | Dependencia directa |
| 11 | `httpx>=0.28.0` disponible | `pyproject.toml L23` | ✅ | Dependencia directa |
| 12 | `service_catalog` tablas existen | `migrations/024` | ✅ | `service_catalog`, `org_service_integrations`, `service_tools` |
| 13 | Sanitizer existe | `src/mcp/sanitizer.py` | ✅ | `sanitize_output(data)` — 7 patrones regex |
| 14 | EventStore existe | `src/events/store.py` | ✅ | `emit_event("flow.completed", {...})` en BaseFlow |
| 15 | `handle_tool_call` en tools.py | `src/mcp/tools.py L68` | ✅ | `async def handle_tool_call(name, arguments, config)` |
| 16 | Pending approvals tabla | `base_flow.py L296` | ✅ | Referencia a `pending_approvals` para HITL |
| 17 | FlowStatus enum | `src/flows/state.py` | ✅ | Enum con estados: RUNNING, COMPLETED, FAILED, AWAITING_APPROVAL |
| 18 | MCPConfig existente | `src/mcp/config.py` | ✅ | `org_id`, `transport`, `require_auth` |

**Discrepancias encontradas:**

| # | Elemento | Discrepancia | Resolución |
|---|---------|--------------|------------|
| D1 | Plan usa `PyJWT` | El código usa `python-jose` (módulo `jwt`) | Usar `python-jose` — verificar `pyproject.toml L20` |
| D2 | Herramientas productivas no registradas | `tools.py` L83-89 solo registra 5 estáticas + placeholder flows | Agregar handlers para `execute_flow`, `get_task`, `approve_task`, `reject_task`, `create_workflow` en `handle_tool_call` |
| D3 | Flow execution no implementado | `_handle_flow_tool_placeholder` L259-273 retorna error "no está habilitada" | Reemplazar con lógica real que llame a `flow_registry.create(name).execute(input_data)` |

---

## 1. DISEÑO FUNCIONAL

### 1.1 Objetivo del Sprint
Habilitar que Claude Desktop pueda ejecutar flows reales, consultar estado de tareas, y gestionar workflows mediante herramientas productivas vía MCP.

### 1.2 Herramientas Productivas a Implementar

| Tool | Descripción | Input Schema |
|------|-------------|--------------|
| `execute_flow` | Ejecutar un flow por nombre con parámetros | `{ "flow_name": string, "input_data": object }` |
| `get_task` | Consultar estado de una tarea por ID | `{ "task_id": string }` |
| `approve_task` | Aprobar una tarea pausada para aprobación | `{ "task_id": string }` |
| `reject_task` | Rechazar una tarea pausada | `{ "task_id": string, "reason": string }` |
| `create_workflow` | Crear workflow compuesto desde definición | `{ "workflow_definition": object }` |

### 1.3 Happy Path — `execute_flow`

```
1. Claude llama execute_flow(flow_name="cotizacion_flow", input_data={...})
2. Handler verifica flow existe en FlowRegistry
3. Crea instancia: flow_registry.create(flow_name, org_id=config.org_id)
4. Ejecuta: state = await flow.execute(input_data, correlation_id=uuid4())
5. Persiste resultado en task.result
6. Retorna CallToolResult con JSON sanitizado:
   {
     "task_id": "uuid",
     "status": "completed|failed|pending_approval",
     "result": {...},
     "error": null
   }
```

### 1.4 Edge Cases MVP

| Escenario | Manejo |
|-----------|--------|
| Flow no existe | Retornar error "Flow 'x' not found" (no 500) |
| Input inválido | `validate_input()` retorna False → error "Input validation failed" |
| Flow requiere aprobación | Estado "pending_approval" → retornar con flag `approval_required: true` |
| Timeout de execution | BaseFlow tiene `max_retries`, propagate error como "Execution failed after N retries" |
| Org_id no coincide | MCP server ya tiene `config.org_id` del CLI arg, verificar ownership |

### 1.5 Happy Path — `get_task`

```
1. Claude llama get_task(task_id="uuid")
2. Consulta tabla tasks con service_client (bypass RLS para MCP)
3. Retorna:
   {
     "task_id": "uuid",
     "flow_type": "cotizacion_flow",
     "status": "completed|failed|pending|running|pending_approval",
     "result": {...},
     "error": "...",
     "created_at": "ISO",
     "updated_at": "ISO"
   }
```

### 1.6 Happy Path — `approve_task` / `reject_task`

```
1. Claude llama approve_task(task_id="uuid") o reject_task(task_id, reason)
2. Verifica task existe y status == "pending_approval"
3. Llama BaseFlow.resume(task_id, decision, decided_by)
4. Retorna resultado post-decisión
```

---

## 2. DISEÑO TÉCNICO

### 2.1 Estructura de Archivos

```
src/mcp/
├── __init__.py         # exports
├── config.py           # ✅ existente
├── server.py           # ✅ existente
├── sanitizer.py        # ✅ existente
├── tools.py            # ⚠️ agregar handlers
├── flow_to_tool.py    # ✅ existente
├── handlers.py        # 🆕 NUEVO — lógica de ejecución
├── auth.py            # 🆕 NUEVO — auth bridge (JWT)
└── exceptions.py      # 🆕 NUEVO — mapeo errores JSON-RPC
```

### 2.2 `src/mcp/handlers.py` — Handlers de Ejecución

```python
#sketch (no implementación, solo diseño)
async def handle_execute_flow(args: dict, config: MCPConfig) -> CallToolResult:
    """Ejecuta un flow y retorna el resultado."""
    flow_name = args.get("flow_name")
    input_data = args.get("input_data", {})
    
    if not flow_name:
        return _error("flow_name es requerido")
    
    # Verificar existe
    try:
        flow_cls = flow_registry.get(flow_name)
    except ValueError:
        return _error(f"Flow '{flow_name}' no encontrado")
    
    # Crear y ejecutar
    flow = flow_cls(org_id=config.org_id)
    try:
        state = await flow.execute(input_data, correlation_id=str(uuid4()))
    except Exception as e:
        return _error(f"Execution failed: {e}")
    
    # Mapear resultado
    return _ok({
        "task_id": state.task_id,
        "status": state.status.value,
        "result": state.output_data,
        "error": state.error,
        "approval_required": state.approval_payload is not None
    })
```

### 2.3 `src/mcp/auth.py` — Auth Bridge

- **Propósito:** Validar JWT en contexto MCP (para escenarios donde el servidor se conecta a otros servicios que requieren auth).
- **Reutilización:** Importar `_get_jwks_client()` de `src.api.middleware` — ya existe y funciona.
- **Nuevo:** Agregar función `validate_mcp_token(token: str) -> dict` que llama al middleware logic.

```python
#sketch
from src.api.middleware import _get_jwks_client

def validate_mcp_token(token: str) -> dict:
    """Valida JWT para uso interno MCP."""
    # Reutilizar lógica de middleware
    # Retorna payload o lanza excepción
```

### 2.4 `src/mcp/exceptions.py` — Mapeo JSON-RPC

```python
#sketch
MCP_ERROR_CODES = {
    "INVALID_PARAMS": -32602,
    "FLOW_NOT_FOUND": -32001,
    "EXECUTION_FAILED": -32002,
    "TASK_NOT_FOUND": -32003,
    "APPROVAL_REQUIRED": -32004,
}

class MCPError(Exception):
    def __init__(self, code: str, message: str):
        self.code = MCP_ERROR_CODES.get(code, -32000)
        self.message = message

def map_exception(exc: Exception) -> dict:
    """Convierte excepciones internas a formato JSON-RPC."""
    # FlowNotFound → -32001
    # ValueError → -32602
    # TimeoutError → -32002
```

### 2.5 Integración con `tools.py`

```python
# En tools.py L83, agregar:
handlers = {
    "execute_flow": _handle_execute_flow,
    "get_task": _handle_get_task,
    "approve_task": _handle_approve_task,
    "reject_task": _handle_reject_task,
    "create_workflow": _handle_create_workflow,
    # ... existentes
}
```

### 2.6 Modelos de Datos

- **tasks**: existente (migrations/001)
- **snapshots**: existente (migrations/001) — para HITL
- **pending_approvals**: referenced en base_flow.py L296 — verificar existe en migrations (no encontrado en listado — posible discrepancia)

---

## 3. DECISIONES

| # | Decisión | Justificación |
|---|----------|---------------|
| D1 | Usar `python-jose` no `PyJWT` | Código existente en `middleware.py` usa `python-jose` (módulo `jwt`), es la dependencia instalada. Plan usaba nombre genérico. |
| D2 | No crear nueva tabla `pending_approvals` ahora | Si no existe, flow execution fallará. **VERIFICAR** antes de implementar. |
| D3 | Reutilizar `_get_jwks_client()` de middleware | DRY — ya implementado y funcionando. No смысл duplicar. |
| D4 | No implementar `create_workflow` completo en Sprint 3 | Complexidad alta. Dejar como skeleton que retorna "Not implemented" — foco en execute_flow y get_task. |

**⚠️ DISCREPANCIA CRÍTICA:** Tabla `pending_approvals` referenciada en `base_flow.py L296` pero no encontrada en migraciones listadas. Necesita verificación antes de implementar handlers.

---

## 4. CRITERIOS DE ACEPTACIÓN

| # | Criterio | Verificable |
|---|----------|-------------|
| CA1 | `execute_flow` ejecuta flow real y retorna task_id | Sí — llamar con flow conocido |
| CA2 | `get_task` retorna estado correcto de tarea | Sí — comparar con DB |
| CA3 | `approve_task` reanuda flow pausado | Sí — crear task con status pending_approval |
| CA4 | `reject_task` marca flow como rechazado | Sí — verificar task.status = "failed" |
| CA5 | Errores no crashean servidor (JSON-RPC mapping) | Sí — provocar errores y verificar respuesta |
| CA6 | Output sanitizado (Regla R3) | Sí — verificar que keys/URLs no aparecen en respuesta |
| CA7 | Flow no encontrado retorna error específico | Sí — llamar con flow_name inválido |
| CA8 | Auth bridge funcional para tokens externos | Sí — pasar token JWT válido |

---

## 5. RIESGOS

| # | Riesgo | Impacto | Mitigación |
|---|--------|---------|------------|
| R1 | Tabla `pending_approvals` no existe | Bloquea HITL | Verificar existencia antes de implementar — si no existe, crear migración |
| R2 | Flow execution timeout | Flow nunca termina | Implementar timeout en handler, matar after N segundos |
| R3 | RLS bloquea query de tasks en MCP | Queries fallan | Usar `get_service_client()` (service_role bypass) — ya usado en tools.py |
| R4 | Dependencias circulares entre módulos | Import error | handlers.py no debe importar server.py |
| R5 | Flow con approval requiere dashboard | Flujo incompleto | Retornar flag `approval_required: true` — Claude puede通知 usuario |

---

## 6. PLAN

| # | Tarea | Complejidad | Tiempo | Dependencias |
|---|-------|-------------|--------|--------------|
| T1 | Crear `src/mcp/exceptions.py` — mapeo errores JSON-RCP | Baja | 1h | — |
| T2 | Crear `src/mcp/auth.py` — wrapper reusing `_get_jwks_client()` | Baja | 1h | T1 |
| T3 | Crear `src/mcp/handlers.py` — `handle_execute_flow` | Alta | 2.5h | T1, T2 |
| T4 | Crear `src/mcp/handlers.py` — `handle_get_task` | Media | 1.5h | T1 |
| T5 | Crear `src/mcp/handlers.py` — `handle_approve_task` / `handle_reject_task` | Media | 1.5h | T3 ( estado task) |
| T6 | Registrar handlers en `tools.py:handle_tool_call` | Baja | 0.5h | T3, T4, T5 |
| T7 | Verificar `pending_approvals` existe en DB | — | — | Pre-T3 |
| T8 | Testing end-to-end: execute_flow → get_task | Alta | 2h | T6 |
| | **TOTAL** | | **~10h** | |

**Orden:** T7 (verificación previa) → T1 → T2 → T3 → T4 → T5 → T6 → T8

---

## 🔮 ROADMAP (NO IMPLEMENTAR AHORA)

1. **SSE Transport** — Agregar servidor HTTP con Server-Sent Events para transporte alternativo a Stdio (Sprint 4).
2. **HITL Dashboard Integration** — Endpoint que retorna URL para que supervisor apruebe desde UI.
3. **create_workflow** — Crear workflow compuesto desde definición JSON (actualmente skeleton).
4. **MCPConfig Panel** — UI en Dashboard para gestionar conexiones MCP.
5. **Flow scheduling** — Ejecutar flows en background con scheduler (actualmente solo ejecución sync).

---

**Fin del análisis — Listo para implementación.**