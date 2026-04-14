# 🧠 Análisis Técnico — Sprint 3: Handlers Productivos MCP

**Agente:** Qwen Code
**Fecha:** 2026-04-14
**Paso:** Sprint 3 completo (3.0 handlers + 3.1 auth + 3.2 exceptions + 3.3 tools)

---

## 0. Verificación contra Código Fuente

### Tabla de verificación (≥ 18 elementos — paso toca 6+ archivos)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/mcp/handlers.py` no existe | `ls src/mcp/` → 6 archivos, ninguno handlers.py | ✅ | El archivo debe crearse desde cero |
| 2 | `src/mcp/auth.py` no existe | `ls src/mcp/` → 6 archivos, ninguno auth.py | ✅ | El archivo debe crearse desde cero |
| 3 | `src/mcp/exceptions.py` no existe | `ls src/mcp/` → 6 archivos, ninguno exceptions.py | ✅ | El archivo debe crearse desde cero |
| 4 | Tabla `tasks` existe | Migración 001 L62, columnas: id, org_id, flow_type, status, payload, result, error, correlation_id | ✅ | 001_set_config_rpc.sql L62-73 |
| 5 | Tabla `tasks` extendida (HITL) | Migración 002 L16-27: approval_required, approval_status, approval_payload, tokens_used, flow_id, retries | ✅ | 002_governance.sql L16-27 |
| 6 | Tabla `pending_approvals` existe | Migración 002 L50-65: id, org_id, task_id, flow_type, description, payload, status, decided_by | ✅ | 002_governance.sql L50-65 |
| 7 | Tabla `snapshots` existe | Migración 001 L76-83 + 002 L30-33 (aggregate_type, aggregate_id, version) | ✅ | 001 L76, 002 L30 |
| 8 | Tabla `domain_events` existe | Migración 001 L87-97: aggregate_type, aggregate_id, event_type, payload, actor, sequence | ✅ | 001 L87-97 |
| 9 | `FlowRegistry` con `get()`, `list_flows()`, `get_metadata()` | registry.py L148 (get), L173 (list_flows), L96 (get_metadata) | ✅ | src/flows/registry.py |
| 10 | `BaseFlow.execute()` existe y es el entry point | base_flow.py L100 `async def execute()` → validate → create_task → start → _run_crew → complete | ✅ | src/flows/base_flow.py L100-150 |
| 11 | `BaseFlow.request_approval()` existe (HITL) | base_flow.py L213 `async def request_approval()` → serializa, crea pending_approval, emite evento | ✅ | src/flows/base_flow.py L213-270 |
| 12 | `BaseFlow.resume()` existe | base_flow.py L272 `async def resume()` → restaura snapshot, decide approved/rejected | ✅ | src/flows/base_flow.py L272-320 |
| 13 | `get_tenant_client()` para queries con RLS | db/session.py L158 context manager, usa `set_config` RPC | ✅ | src/db/session.py L158-170 |
| 14 | `get_service_client()` para bypass RLS | db/session.py L44, usa service-role key | ✅ | src/db/session.py L44-52 |
| 15 | `EventStore` con `append()` + `flush()` + `append_sync()` | events/store.py L74 (append), L96 (flush), L130 (append_sync) | ✅ | src/events/store.py |
| 16 | `sanitize_output()` existe | mcp/sanitizer.py L32, 7 patrones regex | ✅ | src/mcp/sanitizer.py L32-50 |
| 17 | `MCPConfig` con `org_id` | mcp/config.py L19 `org_id: str = ""` | ✅ | src/mcp/config.py L8-19 |
| 18 | `_handle_flow_tool_placeholder()` existe en tools.py | tools.py L226 — retorna error "no habilitada en Sprint 1" | ✅ | src/mcp/tools.py L226-234 |
| 19 | `handle_tool_call()` dispatch en tools.py | tools.py L67 — dict de handlers, routing por nombre | ✅ | src/mcp/tools.py L67-100 |
| 20 | `build_flow_tools()` genera tools dinámicas | flow_to_tool.py L18 — itera FlowRegistry, crea Tool MCP | ✅ | src/mcp/flow_to_tool.py L18-45 |
| 21 | `FLOW_INPUT_SCHEMAS` vacío | api/routes/flows.py L74 `FLOW_INPUT_SCHEMAS: Dict = {}` | ✅ | src/api/routes/flows.py L74 |
| 22 | python-jose en pyproject.toml | pyproject.toml L19 `python-jose[cryptography]>=3.3.0` | ✅ | pyproject.toml L19 |
| 23 | `_get_jwks_client()` en middleware.py | api/middleware.py L62 singleton PyJWKClient | ✅ | src/api/middleware.py L62-85 |
| 24 | `verify_supabase_jwt()` en middleware.py | api/middleware.py L240 ES256/HS256 verification | ✅ | src/api/middleware.py L240-310 |
| 25 | `get_secret_async()` en vault.py | db/vault.py L78 usa `asyncio.to_thread` | ✅ | src/db/vault.py L78-92 |
| 26 | `ServiceConnectorTool` patrón de tool | tools/service_connector.py — OrgBaseTool, @register_tool, sanitize_output, domain_events audit | ✅ | src/tools/service_connector.py |
| 27 | Tabla `workflow_templates` existe | Migración 006: id, org_id, name, flow_type, definition, version, status, is_active | ✅ | 006_workflow_templates.sql |
| 28 | Tabla `agent_catalog` existe | Migración 004: id, org_id, role, is_active, soul_json, allowed_tools, max_iter | ✅ | 004_agent_catalog.sql |
| 29 | `DynamicWorkflow` existe | flows/dynamic_flow.py L30 — `class DynamicWorkflow(BaseFlow)`, `register()` classmethod | ✅ | src/flows/dynamic_flow.py L30-60 |
| 30 | `BaseFlowState` con HITL fields | flows/state.py — approval_payload, approval_decision, approval_decided_by | ✅ | src/flows/state.py L50-58 |

### Discrepancias encontradas

1. **❌ DISCREPANCIA: Plan dice PyJWT pero el código usa python-jose**
   - Evidencia: `pyproject.toml` L19 → `python-jose[cryptography]>=3.3.0`, `middleware.py` importa `jwt` (alias de PyJWT para decode) pero la verificación ES256/HS256 usa la API de PyJWT directamente. El plan Sprint 3 dice "Auth Bridge con PyJWT" pero la dependencia real es `python-jose`.
   - **Resolución:** Auth Bridge debe usar `python-jose` para generar tokens (JWTEncoder), no PyJWT. PyJWT ya se usa para verificación (`jwt.decode`). Para crear tokens de auth MCP, usar `python-jose.jose.jwt.encode`.

2. **❌ DISCREPANCIA: `execute_flow` en webhooks.py no es directamente invocable desde MCP**
   - Evidencia: `src/api/routes/webhooks.py` L92 `async def execute_flow()` — necesita `BackgroundTasks` de FastAPI, no es un callable puro. El MCP server corre en Stdio, sin FastAPI.
   - **Resolución:** Los handlers MCP deben instanciar el flow directamente via `flow_registry.get(flow_type)(org_id=config.org_id)` y llamar `flow.execute(input_data, correlation_id)`. No usar `execute_flow` de webhooks.

3. **⚠️ NO VERIFICABLE: La migración 025 se dice "aplicada" en el plan pero no tengo acceso a la DB real para confirmar.**
   - **Acción de verificación:** Ejecutar `supabase migration list` para confirmar.

4. **❌ DISCREPANCIA: FLOW_INPUT_SCHEMAS está vacío — las flow tools dinámicas no tienen schema de input**
   - Evidencia: `src/api/routes/flows.py` L74 `FLOW_INPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {}`. `flow_to_tool.py` L27 genera schema vacío si no hay entrada.
   - **Resolución:** Los handlers MCP deben validar input manualmente o derivar schema del flow_type. Documentar en el diseño que `execute_flow` acepta `input_data: dict` genérico.

5. **❌ DISCREPANCIA: `get_flow_tool_names()` en flow_to_tool.py retorna nombres en minúsculas pero `tools.py` los registra como handlers sin conversión**
   - Evidencia: `flow_to_tool.py` L51 retorna `flow_registry.list_flows()` (ya en minúsculas). `tools.py` L83 itera sobre estos y registra `_handle_flow_tool_placeholder`.
   - **Resolución:** Los handlers productivos deben usar los mismos nombres en minúsculas. No hay conflicto, pero documentar que `execute_flow` tool recibirá `flow_type` en minúsculas.

---

## 1. Diseño Funcional

### 1.0 `src/mcp/handlers.py` — Handlers productivos de ejecución

#### Tool: `execute_flow`
**Descripción:** Ejecuta un flow registrado con input arbitrario.

**Happy path:**
1. Claude envía `execute_flow(flow_type="generic_flow", input_data={"text": "analiza esto"})`
2. Handler valida que `flow_type` existe en `FlowRegistry`
3. Instancia el flow: `flow = flow_registry.get(flow_type)(org_id=config.org_id)`
4. Genera `correlation_id = f"mcp-{flow_type}-{uuid4().hex[:8]}"`
5. Ejecuta `state = await flow.execute(input_data, correlation_id)`
6. Si flow se pausa (HITL), retorna `{"status": "awaiting_approval", "task_id": "...", "approval_payload": {...}}`
7. Si flow completa, retorna `{"status": "completed", "task_id": "...", "result": {...}, "tokens_used": N}`
8. Output sanitizado con `sanitize_output()`

**Edge cases:**
- `flow_type` no existe → JSON-RPC Error: `{"code": -32602, "message": "Flow 'X' not found. Available: [...]"}`
- Input validation falla → Error: `{"code": -32602, "message": "Input validation failed: ..."}`
- Flow se pausa (HITL) → Retorno parcial con task_id para polling
- Timeout del flow (>30s) → Error con task_id para consultar después
- DB connection error → Error genérico, no exponer detalles internos

**Manejo de errores (lo que ve Claude):**
```json
// Éxito
{"status": "completed", "task_id": "uuid", "result": {...}, "tokens_used": 450}

// HITL pause
{"status": "awaiting_approval", "task_id": "uuid", "approval_description": "Revisar cotización"}

// Error
{"error": "Flow 'X' not found. Available: [generic_flow, architect_flow]"}
```

#### Tool: `get_task`
**Descripción:** Consulta el estado de una tarea por task_id.

**Happy path:**
1. `get_task(task_id="uuid")`
2. Query: `db.table("tasks").select("*").eq("id", task_id).eq("org_id", config.org_id).maybe_single()`
3. Retorna `{"task_id": "...", "status": "completed", "result": {...}, "tokens_used": N, "created_at": "...", "updated_at": "..."}`
4. Si no existe → Error: `{"error": "Task 'X' not found"}`

#### Tool: `approve_task`
**Descripción:** Aprueba una tarea pausada en HITL.

**Happy path:**
1. `approve_task(task_id="uuid", notes="OK")`
2. Verifica que `pending_approvals` existe con status "pending" para ese task_id
3. Actualiza `pending_approvals.status = "approved"`
4. Obtiene flow_type del pending_approval
5. Instancia flow y llama `await flow.resume(task_id, "approved", decided_by="mcp")`
6. Retorna `{"status": "approved", "task_id": "...", "message": "Flow resumed"}`

**Edge case:**
- Approval ya procesado → Error: `{"error": "Task already processed"}`
- Flow no en registry → Error con detalle

#### Tool: `reject_task`
**Descripción:** Rechaza una tarea pausada en HITL.

**Happy path:** Similar a `approve_task` pero con `decision = "rejected"`.

#### Tool: `create_workflow`
**Descripción:** Crea un workflow nuevo vía ArchitectFlow desde descripción en lenguaje natural.

**Happy path:**
1. `create_workflow(description="Crea un flow para aprobar gastos > 1000")`
2. Instancia `ArchitectFlow(org_id=config.org_id)`
3. Ejecuta `state = await flow.execute({"description": description}, correlation_id)`
4. Retorna `{"flow_type": "nuevo_flow", "template_id": "...", "agents_created": ["..."], "message": "Workflow creado"}`

### 1.1 `src/mcp/auth.py` — Auth Bridge

**Propósito:** Generar y validar tokens JWT para MCP (Sprint 4 SSE). En Stdio no se usa, pero se necesita para cuando se habilite `require_auth=True` en MCPConfig.

**Funciones:**
- `generate_mcp_token(org_id: str, user_id: str, ttl: int) -> str` — crea token con python-jose
- `validate_mcp_token(token: str) -> dict` — valida y retorna claims
- `get_mcp_secret(org_id: str) -> str` — obtiene signing key de vault

**Algoritmo:** HS256 con secret del vault (simpler que ES256 para tokens internos).

### 1.2 `src/mcp/exceptions.py` — Mapeo de errores JSON-RPC

**Propósito:** Mapear excepciones internas a códigos JSON-RPC estándar.

| Código JSON-RPC | Significado | Causas internas |
|---|---|---|
| `-32601` | Method not found | Tool no registrada |
| `-32602` | Invalid params | Input validation failed, flow_type no existe |
| `-32603` | Internal error | DB error, flow execution error |
| `-32000` | Server error | Server shutdown, config error |
| `-32001` | Unauthorized | Token inválido (Sprint 4) |
| `-32002` | Forbidden | Org mismatch, no membership |

**Funciones:**
- `mcp_error(code: int, message: str, data: dict | None) -> CallToolResult` — crea resultado de error
- `from_exception(exc: Exception) -> CallToolResult` — mapea excepción Python a JSON-RPC error

### 1.3 Registro de tools en `tools.py`

Las 5 herramientas nuevas deben agregarse al dispatch de `handle_tool_call()` en `tools.py`:

```python
handlers = {
    # ... existentes ...
    "execute_flow": _handle_execute_flow,
    "get_task": _handle_get_task,
    "approve_task": _handle_approve_task,
    "reject_task": _handle_reject_task,
    "create_workflow": _handle_create_workflow,
}
```

Y las tool definitions en `STATIC_TOOLS` (o separadas como `PRODUCTIVE_TOOLS`).

---

## 2. Diseño Técnico

### 2.1 `src/mcp/handlers.py`

```
handlers.py
├── _handle_execute_flow(arguments, config) → CallToolResult
├── _handle_get_task(arguments, config) → CallToolResult
├── _handle_approve_task(arguments, config) → CallToolResult
├── _handle_reject_task(arguments, config) → CallToolResult
├── _handle_create_workflow(arguments, config) → CallToolResult
└── _make_result(data) → CallToolResult (helper, ya existe en tools.py)
```

**Dependencias internas:**
- `from ..flows.registry import flow_registry`
- `from ..db.session import get_tenant_client`
- `from ..mcp.sanitizer import sanitize_output`
- `from .exceptions import mcp_error, from_exception`
- `from uuid import uuid4`

**Patrón de cada handler:**
```python
async def _handle_execute_flow(arguments: dict, config: MCPConfig) -> CallToolResult:
    try:
        flow_type = arguments.get("flow_type")
        input_data = arguments.get("input_data", {})
        # validación, ejecución, retorno sanitizado
    except Exception as exc:
        return from_exception(exc)
```

### 2.2 `src/mcp/auth.py`

```
auth.py
├── MCPAuthError(Exception)
├── _get_signing_key(org_id: str) → str (desde vault o settings)
├── generate_mcp_token(org_id, user_id, ttl_seconds=3600) → str
├── validate_mcp_token(token: str) → dict {org_id, user_id, exp}
└── mcp_auth_dependency(token: str) → dict (FastAPI dependency pattern)
```

**Dependencias:**
- `from jose import jwt, JWTError` (python-jose)
- `from ..db.vault import get_secret_async`
- `from ..config import get_settings`

**Nota:** `python-jose` se importa como `from jose import jwt`, NO como `import jwt` (que es PyJWT). El middleware usa PyJWT (`import jwt as pyjwt`) para verificación. Auth Bridge usa python-jose para creación.

### 2.3 `src/mcp/exceptions.py`

```
exceptions.py
├── MCPErrorCode(IntEnum) — códigos JSON-RPC
├── MCPError(Exception) — exception con code, message, data
├── mcp_error(code, message, data=None) → CallToolResult
├── from_exception(exc) → CallToolResult (dispatch por tipo de excepción)
└── _classify_exception(exc) → tuple[int, str] (code + message)
```

**Clasificación de excepciones:**
| Tipo de excepción interna | Código JSON-RPC | Mensaje |
|---|---|---|
| `ValueError` (flow no encontrado) | -32602 | "Invalid params: ..." |
| `KeyError` (param faltante) | -32602 | "Missing required param: ..." |
| `Exception` genérica de flow | -32603 | "Internal error executing flow" |
| `DB error` (Supabase) | -32603 | "Database error" |
| `TimeoutError` | -32603 | "Flow execution timed out" |
| `Unauthorized` (auth) | -32001 | "Invalid or expired token" |
| `PermissionError` (org mismatch) | -32002 | "Access denied" |

### 2.4 Modelos de datos (sin cambios)

No se necesitan nuevas tablas. Se usan las existentes:
- `tasks` → consulta de estado
- `pending_approvals` → aprobación HITL
- `snapshots` → estado serializado (ya manejado por BaseFlow)
- `domain_events` → auditoría (ya manejado por EventStore)

### 2.5 Tool definitions

Las 5 tools nuevas se agregan como `STATIC_TOOLS` en `tools.py` (o como lista separada `PRODUCTIVE_TOOLS` concatenada en `get_static_tools()`).

```python
Tool(name="execute_flow", description="Ejecutar un flow registrado...", inputSchema={
    "type": "object",
    "required": ["flow_type"],
    "properties": {
        "flow_type": {"type": "string", "description": "Nombre del flow (snake_case)"},
        "input_data": {"type": "object", "description": "Datos de entrada del flow"},
    }
})
```

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|---|---|
| 1 | **Handlers instancian flows directamente, no usan `execute_flow` de webhooks.py** | `execute_flow` en webhooks depende de `BackgroundTasks` de FastAPI. El MCP server corre en Stdio sin FastAPI. Instanciación directa via `flow_registry.get()` es portable. |
| 2 | **Ejecución sincrónica (no background) para `execute_flow`** | MCP es request-response. Claude espera la respuesta. Si el flow tarda, Claude recibe timeout. Para flows largos, el patrón es: ejecutar → si tarda, retornar task_id → Claude consulta con `get_task`. |
| 3 | **Auth Bridge usa HS256 con secret del vault, no ES256** | ES256 requiere JWKS endpoint (solo para tokens Supabase). Tokens MCP son internos — HS256 con secret compartida es suficiente y más simple. |
| 4 | **Auth deshabilitado por defecto (`require_auth=False` en MCPConfig)** | Sprint 3 usa Stdio (local, sin red). Auth se activa en Sprint 4 con SSE. |
| 5 | **python-jose para crear tokens, PyJWT para verificar** | python-jose está en pyproject.toml y soporta encode. PyJWT ya se usa en middleware para decode. Coexisten sin conflicto (imports distintos). |
| 6 | **`create_workflow` reusa ArchitectFlow existente** | No reinventar. ArchitectFlow ya valida, persiste template, registra agents y crea dynamic flow. El handler MCP solo envuelve la llamada. |
| 7 | **Sanitización obligatoria en TODOS los handlers** | Regla R3. Cada handler llama `sanitize_output()` antes de retornar, sin excepción. |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | `execute_flow` ejecuta `generic_flow` y retorna resultado completado | `python -c "await _handle_execute_flow({'flow_type': 'generic_flow', 'input_data': {'text': 'test'}}, config)"` → status=completed |
| 2 | `execute_flow` retorna error si `flow_type` no existe | Mismo test con `flow_type="nonexistent"` → isError=True, mensaje con flows disponibles |
| 3 | `get_task` retorna estado de tarea existente | Crear tarea con execute_flow, luego get_task con task_id → status matches |
| 4 | `get_task` retorna error si task_id no existe | get_task con UUID aleatorio → isError=True |
| 5 | `approve_task` reanuda flow pausable (HITL) | Flow con request_approval → approve_task → flow completa |
| 6 | `reject_task` marca flow como rechazado | Flow con request_approval → reject_task → status=failed |
| 7 | `create_workflow` crea workflow via ArchitectFlow | create_workflow con descripción NL → retorna flow_type, template_id |
| 8 | Todos los handlers sanitizan output | Input con secret pattern (`sk_live_...`) → output contiene `[REDACTED]` |
| 9 | `exceptions.py` mapea ValueError a -32602 | `from_exception(ValueError("test"))` → content con code -32602 |
| 10 | `exceptions.py` mapea Exception genérica a -32603 | `from_exception(RuntimeError("fail"))` → content con code -32603 |
| 11 | `auth.py` genera y valida token HS256 | `generate_mcp_token()` → `validate_mcp_token()` retorna claims correctos |
| 12 | Las 5 tools nuevas aparecen en `list_tools()` de MCP | Conectar MCP server → Claude ve execute_flow, get_task, approve_task, reject_task, create_workflow |
| 13 | No se crash el servidor ante DB error | Simular DB down → handler retorna error JSON-RPC, no exception no manejada |
| 14 | Correlation IDs trazables | Cada ejecución MCP genera `mcp-{flow_type}-{uuid}` visible en tasks.correlation_id |

---

## 5. Riesgos

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| 1 | **Flow execution bloquea el event loop MCP** | Si un flow tarda >30s, Claude Desktop timeout. Stdio es sincrónico por naturaleza. | Documentar que flows largos deben consultarse vía `get_task`. Considerar timeout configurable en MCPConfig. |
| 2 | **ArchitectFlow depende de CrewAI que puede fallar sin API key** | Si anthropic_api_key/groq_api_key no está configurada, el LLM falla y el handler retorna error genérico. | Validar API keys antes de ejecutar. Retornar error claro: "LLM provider no configurado". |
| 3 | **HITL requiere que el flow esté pausable (request_approval)** | No todos los flows implementan request_approval. Solo los que lo necesitan. | `approve_task` verifica que exista pending_approval antes de intentar resume. Si no existe, error claro. |
| 4 | **python-jose y PyJWT coexisten con imports confusos** | `import jwt` = PyJWT, `from jose import jwt` = python-jose. Confusión puede causar bugs. | Usar alias explícitos: `import jwt as pyjwt` (ya usado en middleware), `from jose import jwt as jose_jwt`. |
| 5 | **RLS policies bloquean queries si org_id no se setea** | Si el handler usa `get_anon_client()` sin `set_config`, RLS rechaza. | Usar siempre `get_tenant_client(org_id)` o `get_service_client()` según contexto. |
| 6 | **Sprint 4 requiere SSE — Auth Bridge es pre-requisito** | Si Auth Bridge no se implementa bien en Sprint 3, Sprint 4 se bloquea. | Auth Bridge debe ser testeable independientemente (unit tests de generate/validate token). |
| 7 | **DynamicWorkflow no tiene validación de input real** | `DynamicWorkflow.validate_input` solo verifica `bool(input_data)`. Input malformado puede causar error en _run_crew. | Los handlers MCP deben validar input_data antes de pasar a dynamic flows. Documentar limitación. |

---

## 6. Plan de Implementación

### Tareas atómicas (orden recomendado)

| # | Tarea | Complejidad | Tiempo est. | Dependencias |
|---|---|---|---|---|
| 1 | Crear `src/mcp/exceptions.py` — MCPError, mcp_error(), from_exception() | Baja | 45 min | Ninguna |
| 2 | Crear `src/mcp/auth.py` — generate/validate token HS256 | Media | 1.5h | Tarea 1 (MCPError) |
| 3 | Crear `src/mcp/handlers.py` — execute_flow handler | Alta | 2.5h | Tarea 1 (exceptions) |
| 4 | Crear `src/mcp/handlers.py` — get_task handler | Baja | 30 min | Tarea 3 |
| 5 | Crear `src/mcp/handlers.py` — approve_task handler | Media | 1h | Tarea 3, BaseFlow.resume() |
| 6 | Crear `src/mcp/handlers.py` — reject_task handler | Baja | 30 min | Tarea 5 |
| 7 | Crear `src/mcp/handlers.py` — create_workflow handler | Media | 1h | Tarea 3, ArchitectFlow |
| 8 | Modificar `src/mcp/tools.py` — agregar 5 tool definitions + dispatch | Baja | 45 min | Tareas 3-7 |
| 9 | Modificar `src/mcp/flow_to_tool.py` — routing de flow tools a handlers reales (no placeholder) | Media | 1h | Tarea 3 |
| 10 | Tests unitarios de handlers (execute_flow, get_task) | Media | 2h | Tareas 3-4 |
| 11 | Tests unitarios de auth.py (generate/validate token) | Baja | 1h | Tarea 2 |
| 12 | Tests unitarios de exceptions.py (mapeo de excepciones) | Baja | 30 min | Tarea 1 |
| 13 | Test end-to-end: conectar MCP server, ejecutar generic_flow | Alta | 2h | Todas las anteriores |

**Total estimado:** ~13h (rango 10-16h según complejidad de debugging)

### Orden de ejecución:
```
T1 (exceptions) → T2 (auth)
                → T3 (execute_flow) → T4 (get_task) → T5 (approve_task) → T6 (reject_task)
                                                          → T7 (create_workflow)
                                                          → T8 (tools.py register)
                                                          → T9 (flow_to_tool routing)
                                                          → T10-12 (tests unitarios)
                                                          → T13 (E2E)
```

---

## 🔮 Roadmap (NO implementar ahora)

### Pre-requisitos para pasos futuros descubiertos durante exploración:

1. **Sprint 4 (HITL + SSE):** Auth Bridge (T2) es pre-requisito. El SSE server necesitará validar tokens MCP en cada conexión. El `require_auth=True` en MCPConfig debe activarse.

2. **Sprint 5 (Expansión catálogo):** No bloqueado por Sprint 3. Pero los handlers MCP deben ser estables con 226+ tools dinámicas. `build_flow_tools()` itera todo FlowRegistry — si hay 226 flows, la lista inicial tarda. Considerar paginación de tools en el futuro.

3. **Health check del scheduler:** `src/scheduler/health_check.py` existe pero no está conectado al lifespan del MCP server. Para producción, el health check debería correr periódicamente mientras el MCP server está activo.

4. **FLOW_INPUT_SCHEMAS vacío:** Los flow tools dinámicas no tienen schema de input. Claude no sabe qué parámetros enviar. Roadmap: poblar FLOW_INPUT_SCHEMAS con schemas Pydantic de cada flow para que `build_flow_tools()` genere inputSchema correcto.

5. **DynamicFlow input validation:** `DynamicWorkflow.validate_input` solo verifica `bool(input_data)`. Para producción, debería validar contra el schema del workflow template.

6. **Token tracking en handlers MCP:** Los flows trackean tokens en `state.tokens_used`, pero el handler de `execute_flow` debe retornarlos explícitamente. Ya contemplado en el diseño.

7. **MCP Config panel en Dashboard (Sprint 4):** La UI para gestionar conexiones MCP necesitará leer MCPConfig y mostrar estado del servidor.

### Decisiones de diseño pensando en el futuro:
- Auth Bridge usa HS256 pero la estructura del token incluye `org_id` y `user_id` — compatible con el middleware existente que espera estos claims.
- Los handlers retornan `task_id` en todos los casos (éxito y error) — permite polling asíncrono futuro.
- `exceptions.py` usa códigos JSON-RPC estándar — si en el futuro se agrega otro transporte (WebSocket), el mapeo es reutilizable.
