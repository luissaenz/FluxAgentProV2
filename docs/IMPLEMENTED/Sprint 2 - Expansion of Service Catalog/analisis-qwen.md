# 🧠 ANÁLISIS TÉCNICO — Paso 5.2: Handlers de Ejecución + Auth Bridge (MCP)

## 0. Verificación contra Código Fuente (OBLIGATORIA)

### Tabla de verificación (alcance: 3 archivos nuevos + 3 existentes modificados = ≥ 12 elementos)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/mcp/handlers.py` no existe | `glob src/mcp/handlers.py` → no encontrado | ✅ | El archivo debe crearse desde cero |
| 2 | `src/mcp/auth.py` no existe | `glob src/mcp/auth.py` → no encontrado | ✅ | El archivo debe crearse desde cero |
| 3 | `src/mcp/exceptions.py` no existe | `glob src/mcp/exceptions.py` → no encontrado | ✅ | El archivo debe crearse desde cero |
| 4 | `execute_flow` existe en webhooks.py | `grep -rn "async def execute_flow" src/api/routes/webhooks.py` → línea 104 | ✅ | webhooks.py L104-148, firma: `(flow_type, org_id, input_data, correlation_id, callback_url)` |
| 5 | `get_task` endpoint existe | `grep -rn "async def get_task" src/api/routes/tasks.py` → línea 62 | ✅ | tasks.py L62, ruta `GET /tasks/{task_id}`, usa `verify_org_membership` |
| 6 | Approval endpoint existe | `grep -rn "process_approval" src/api/routes/approvals.py` → línea 82 | ✅ | approvals.py L82, ruta `POST /approvals/{task_id}`, usa `verify_org_membership` |
| 7 | `verify_org_membership` existe en middleware | `grep -rn "async def verify_org_membership" src/api/middleware.py` → línea 280 | ✅ | middleware.py L280-330, retorna `{"user_id", "org_id", "role"}` |
| 8 | `require_org_id` existe en middleware | `grep -rn "async def require_org_id" src/api/middleware.py` → línea 110 | ✅ | middleware.py L110-121, lee header `X-Org-ID` |
| 9 | `_get_jwks_client` existe en middleware | `grep -rn "def _get_jwks_client" src/api/middleware.py` → línea 78 | ✅ | middleware.py L78-105, singleton PyJWKClient con cache 5 min |
| 10 | `pyjwt` importado (no python-jose) | `grep -rn "import jwt" src/api/middleware.py` → línea 54 | ✅ | middleware.py L54: `import jwt as pyjwt` — confirma uso de PyJWT |
| 11 | `MCPConfig` existe con `org_id` | `grep -rn "org_id" src/mcp/config.py` → línea 18 | ✅ | config.py L18: `org_id: str = ""` |
| 12 | `_handle_flow_tool_placeholder` existe | `grep -rn "_handle_flow_tool_placeholder" src/mcp/tools.py` → línea 234 | ✅ | tools.py L234-244, retorna placeholder error de Sprint 1 |
| 13 | `handle_tool_call` existe como dispatch | `grep -rn "async def handle_tool_call" src/mcp/tools.py` → línea 66 | ✅ | tools.py L66-108, routing por nombre de tool |
| 14 | `sanitize_output` existe | `grep -rn "def sanitize_output" src/mcp/sanitizer.py` → línea 32 | ✅ | sanitizer.py L32-57, 7 patrones regex |
| 15 | `get_service_client` existe | `grep -rn "def get_service_client" src/db/session.py` → línea 40 | ✅ | session.py L40-57, service-role bypass RLS |
| 16 | `get_tenant_client` existe | `grep -rn "def get_tenant_client" src/db/session.py` → línea 166 | ✅ | session.py L166-180, context manager con RLS |
| 17 | `BaseFlow.execute` existe | `grep -rn "async def execute" src/flows/base_flow.py` → línea 103 | ✅ | base_flow.py L103-159, lifecycle completo con HITL |
| 18 | `BaseFlow.resume` existe | `grep -rn "async def resume" src/flows/base_flow.py` → línea 255 | ✅ | base_flow.py L255-289, reanuda flow tras aprobación |
| 19 | Tabla `tasks` existe | Mig 002: `CREATE TABLE tasks` | ✅ | 002_governance.sql, columnas: `id, org_id, flow_type, status, payload, result, error, correlation_id` |
| 20 | Tabla `pending_approvals` existe | Mig 002: `CREATE TABLE pending_approvals` | ✅ | 002_governance.sql, columnas: `id, org_id, task_id, flow_type, description, payload, status` |
| 21 | `flow_registry.get()` existe | `grep -rn "def get" src/flows/registry.py` → línea 175 | ✅ | registry.py L175-186, retorna Flow class por nombre |
| 22 | `@register_tool` decorador existe | `grep -rn "def register_tool" src/tools/registry.py` → línea 110 | ✅ | registry.py L110-121, firma: `(name, description, requires_approval, timeout, retry, tags)` |

### Discrepancias encontradas

1. ❌ **DISCREPANCIA: El plan general dice "Auth Bridge (PyJWT)" pero el archivo `src/mcp/auth.py` no existe aún.**
   - Evidencia: `glob src/mcp/auth.py` → 0 resultados. El estado-fase.md §2 lo lista como "No Existe Aún".
   - Resolución: Crear `src/mcp/auth.py` reutilizando los helpers de `middleware.py` (`_get_jwks_client`, `_verify_es256`, `_verify_hs256`). No reinventar — importar y adaptar.

2. ❌ **DISCREPANCIA: `execute_flow` es una función async en webhooks.py, no un handler MCP.**
   - Evidencia: webhooks.py L104: `async def execute_flow(...)` — es una función de background, no un MCP handler.
   - Resolución: Los handlers MCP deben envolver `execute_flow` adaptando la interfaz: MCP handlers reciben `(name, arguments, config)` y retornan `CallToolResult`, mientras `execute_flow` retorna `Dict[str, Any]`.

3. ⚠️ **DISCREPANCIA: El plan menciona `python-jose` en pyproject.toml pero el código usa PyJWT.**
   - Evidencia: pyproject.toml L19: `"python-jose[cryptography]>=3.3.0"` pero middleware.py L54: `import jwt as pyjwt`.
   - Resolución: Para MCP auth, usar PyJWT directamente. `python-jose` puede eliminarse de deps en limpieza futura. Documentar en Decisiones.

4. ⚠️ **DISCREPANCIA: `_handle_flow_tool_placeholder` rechaza toda ejecución de flows en Sprint 1.**
   - Evidencia: tools.py L234-244 — retorna `isError=True` con mensaje "Sprint 1 solo consulta".
   - Resolución: Paso 5.2 debe reemplazar este placeholder con handlers productivos que realmente ejecuten flows. El placeholder debe eliminarse o transformarse.

---

## 1. Diseño Funcional

### Happy Path (Paso 5.2 completo)

**A. Handlers de ejecución (MCP `call_tool` para flow tools):**

1. Agente externo (Claude Desktop) envía `tools/call` con nombre de flow (ej: `generic_flow`) y argumentos.
2. `server.py:handle_call_tool()` routea al handler correspondiente.
3. El handler nuevo en `handlers.py`:
   - Recibe `(flow_name, arguments, config)` donde `config.org_id` viene del CLI.
   - Valida que el flow existe en `flow_registry`.
   - Instancia el flow: `flow_class(org_id=config.org_id)`.
   - Ejecuta `await flow.execute(input_data=arguments, correlation_id=f"mcp-{flow_name}-{uuid4().hex[:8]}")`.
   - Retorna `CallToolResult` con el resultado sanitizado.
4. Si el flow requiere HITL (approval), el flow se pausa y el handler retorna un resultado indicando que requiere aprobación.
5. El supervisor aprueba/rechaza vía dashboard `POST /approvals/{task_id}` (ya existente).
6. El flow se reanuda en background.

**B. Auth Bridge (MCP auth para agentes externos):**

1. Agente externo presenta JWT de Supabase en header `Authorization: Bearer <token>`.
2. El Auth Bridge verifica el token:
   - Detecta algoritmo (ES256 vs HS256) del header.
   - ES256 → usa JWKS (`_get_jwks_client()` del middleware).
   - HS256 → usa `SUPABASE_JWT_SECRET` de settings.
3. Extrae `user_id` del claim `sub`.
4. Verifica membresía con `verify_org_membership` (org_id + user_id).
5. Retorna contexto de auth: `{user_id, org_id, role}`.

### Edge Cases Relevantes para MVP

| Edge Case | Comportamiento |
|---|---|
| Flow no existe en registry | Retorna `CallToolResult(isError=True)` con mensaje "Flow X not found" |
| Input validation falla | Retorna error con detalles de validación |
| Flow execution falla (excepción) | Retorna error sanitizado, no expone stack traces |
| Secret no disponible en Vault | Retorna "Error: Secret X not found" (ya implementado en ServiceConnectorTool) |
| Org no tiene acceso al flow | Retorna 403 (si se agrega verificación de permisos) |
| Flow requiere aprobación | Retorna resultado con `status: "awaiting_approval"` y `task_id` |
| Token JWT expirado | Retorna 401 "Token has expired" |
| Token JWT con algoritmo no soportado | Retorna 401 "Unsupported algorithm" |

### Manejo de Errores — Qué Ve el Usuario

| Error Interno | Output al Agente |
|---|---|
| Flow no encontrado | `{"error": "Flow 'X' not found. Available: [...]"}` |
| Input inválido | `{"error": "Input validation failed: campo Y es requerido"}` |
| Error de ejecución | `{"error": "Execution failed: <mensaje sanitizado>"}` |
| Secret missing | `{"error": "Configuration error: secret not found"}` |
| Auth fallido | `{"error": "Authentication failed: <razón>"}` |
| DB connection error | `{"error": "Internal error: database connection failed"}` |

---

## 2. Diseño Técnico

### 2.1 Componentes Nuevos

#### `src/mcp/handlers.py` — Handlers de ejecución para flow tools

```
handlers.py
├── execute_flow_handler(flow_name, arguments, config) → CallToolResult
├── get_task_handler(task_id, config) → CallToolResult
├── approve_task_handler(task_id, action, config) → CallToolResult
└── reject_task_handler(task_id, config) → CallToolResult
```

**`execute_flow_handler`:**
- Input: `flow_name: str`, `arguments: dict`, `config: MCPConfig`
- Output: `CallToolResult` con resultado del flow o error
- Lógica:
  1. Validar flow existe: `flow_registry.has(flow_name)`
  2. Obtener flow class: `flow_registry.get(flow_name)`
  3. Instanciar: `flow = flow_class(org_id=config.org_id)`
  4. Generar correlation_id: `f"mcp-{flow_name}-{uuid4().hex[:8]}"`
  5. Ejecutar: `state = await flow.execute(arguments, correlation_id)`
  6. Sanitizar output: `sanitize_output(state.to_dict())`
  7. Retornar `CallToolResult`

**`get_task_handler`:**
- Input: `task_id: str`, `config: MCPConfig`
- Output: `CallToolResult` con estado de la task
- Lógica:
  1. Query DB: `get_tenant_client(config.org_id).table("tasks").select("*").eq("id", task_id)`
  2. Retornar resultado o error si no existe

**`approve_task_handler` / `reject_task_handler`:**
- Input: `task_id: str`, `config: MCPConfig` (+ `notes` opcional)
- Output: `CallToolResult` con confirmación
- Lógica:
  1. Verificar que la task existe y pertenece a la org
  2. Verificar que hay una approval pending
  3. Llamar `flow.resume(task_id, "approved"/"rejected", config.org_id)`
  4. Retornar confirmación

#### `src/mcp/auth.py` — Auth Bridge para agentes externos

```
auth.py
├── verify_mcp_token(token: str, org_id: str) → dict
├── MCPAuthError(Exception)
└── auth_context_from_token(token: str, org_id: str) → {"user_id", "org_id", "role"}
```

**`verify_mcp_token`:**
- Reutiliza `_get_jwks_client()` de `src/api/middleware.py`
- Reutiliza `_verify_es256()` y `_verify_hs256()` de `src/api/middleware.py`
- Retorna payload decodificado o lanza `MCPAuthError`

**`MCPAuthError`:**
- Subclase de Exception con código de error JSON-RPC

**`auth_context_from_token`:**
- Combina verificación JWT + org membership
- Retorna contexto listo para usar en handlers

#### `src/mcp/exceptions.py` — Mapeo de errores a JSON-RPC

```
exceptions.py
├── MCPErrorCode(Enum)
│   ├── INVALID_REQUEST = -32600
│   ├── METHOD_NOT_FOUND = -32601
│   ├── INVALID_PARAMS = -32602
│   ├── INTERNAL_ERROR = -32603
│   ├── AUTH_FAILED = -32001
│   ├── ORG_NOT_FOUND = -32002
│   ├── FLOW_NOT_FOUND = -32003
│   ├── VALIDATION_ERROR = -32004
│   └── EXECUTION_ERROR = -32005
├── to_jsonrpc_error(internal_exception) → {"code", "message", "data"}
└── MCPError(code, message, data=None)
```

### 2.2 Modificaciones a Existentes

#### `src/mcp/tools.py`

- **Modificar** `_handle_flow_tool_placeholder` → redirigir a `execute_flow_handler` de `handlers.py`.
- **Agregar** nuevas herramientas estáticas para `get_task`, `approve_task`, `reject_task` si se desean como tools separadas (no flow tools dinámicas).

**Cambio específico:**
```python
# tools.py L95-102 — actualmente:
for flow_name in get_flow_tool_names():
    handlers[flow_name] = _handle_flow_tool_placeholder

# Cambiar a:
from .handlers import execute_flow_handler
for flow_name in get_flow_tool_names():
    handlers[flow_name] = execute_flow_handler
```

#### `src/mcp/server.py`

- **No requiere cambios** — el dispatch ya está en `handle_tool_call` que es genérico.
- Si se agregan nuevas tools estáticas (`get_task`, `approve_task`), registrarlas en `handle_list_tools` y routear en `handle_call_tool`.

### 2.3 Interfaces

**execute_flow_handler:**
- Input: `{"flow_name": str, "arguments": {...}}`
- Output: `{"status": str, "task_id": str, "result": dict | None, "error": str | None, "awaiting_approval": bool}`

**get_task_handler:**
- Input: `{"task_id": str}`
- Output: `{"task_id": str, "status": str, "result": dict | None, "error": str | None, "flow_type": str}`

**verify_mcp_token:**
- Input: `token: str`, `org_id: str`
- Output: `{"user_id": str, "org_id": str, "role": str, "payload": dict}`

### 2.4 Modelos de Datos

No se requieren modelos nuevos. Se usan:
- `tasks` (tabla existente, mig 002)
- `pending_approvals` (tabla existente, mig 002)
- `snapshots` (tabla existente, mig 002)

---

## 3. Decisiones

| # | Decisión | Justificación | Corrige Plan |
|---|---|---|---|
| 1 | **Reutilizar helpers de middleware.py para auth** en vez de duplicar lógica | `_get_jwks_client`, `_verify_es256`, `_verify_hs256` ya están implementados y probados. Duplicar violaría DRY. | No corrige, pero el plan asumía "Auth Bridge" como algo nuevo — en realidad es una capa delgada sobre middleware existente. |
| 2 | **Usar PyJWT directamente**, no python-jose | El código ya importa `jwt as pyjwt` (middleware.py L54). python-jose está en pyproject.toml pero no se usa en código nuevo. | Corrige plan — pyproject.toml L19 dice python-jose pero el código usa PyJWT. |
| 3 | **Handlers MCP envuelven `execute_flow`** en vez de reimplementar | `execute_flow` ya maneja lifecycle completo (validate, create_task, run, persist). Reimplementar sería error-prone. | No corrige — consistente con plan. |
| 4 | **No agregar permisos por flow en MVP** | El plan no menciona permisos granulares por flow. Para MVP, cualquier miembro de la org puede ejecutar cualquier flow. | No corrige — MVP scope. |
| 5 | **MCPError usa códigos JSON-RPC estándar** (-32600 a -32603) + custom (-32001 a -32005) | Compatibilidad con clientes MCP estándar. Los custom codes son para errores de negocio. | No corrige — consistente con plan §5.2. |
| 6 | **Flow execution en handlers es async directo**, no via background task | MCP `call_tool` es async y espera respuesta. Background tasks de FastAPI no aplican aquí. | Corrige plan — el plan no diferenciaba entre ejecución sync (API) y async (MCP). |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | `src/mcp/handlers.py` existe con `execute_flow_handler` implementado | ✅/❌ |
| 2 | `src/mcp/auth.py` existe con `verify_mcp_token` funcional | ✅/❌ |
| 3 | `src/mcp/exceptions.py` existe con `MCPError` y códigos JSON-RPC | ✅/❌ |
| 4 | `execute_flow_handler` ejecuta un flow y retorna resultado sanitizado | ✅/❌ (test: llamar tool `generic_flow` con input válido) |
| 5 | `execute_flow_handler` retorna error si flow no existe | ✅/❌ (test: llamar con flow inexistente → isError=True) |
| 6 | `get_task_handler` retorna estado de una task existente | ✅/❌ (test: crear task, consultar por ID) |
| 7 | `approve_task_handler` reanuda un flow pausado | ✅/❌ (test: flow con HITL, aprobar, verificar resume) |
| 8 | `verify_mcp_token` valida token ES256 correctamente | ✅/❌ (test: token válido → retorna user_id) |
| 9 | `verify_mcp_token` rechaza token expirado | ✅/❌ (test: token expirado → MCPAuthError) |
| 10 | `verify_mcp_token` rechaza token de org no miembro | ✅/❌ (test: token válido pero org distinta → MCPAuthError) |
| 11 | `_handle_flow_tool_placeholder` es reemplazado por handler real | ✅/❌ (test: tools.py ya no usa placeholder para flows) |
| 12 | Output de handlers pasa por `sanitize_output()` | ✅/❌ (test: resultado con secret pattern → [REDACTED]) |
| 13 | Errores MCP se mapean a códigos JSON-RPC | ✅/❌ (test: error → `{"code": -32602, "message": "..."}`) |
| 14 | No se exponen internals en errores (stack traces, paths) | ✅/❌ (test: forzar excepción interna → error genérico) |
| 15 | `python -m src.mcp.server --org-id <UUID>` inicia sin errores | ✅/❌ |
| 16 | Claude Desktop puede ejecutar un flow simple vía MCP | ✅/❌ (test E2E: enviar tool call, verificar resultado en DB) |

---

## 5. Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| 1 | **`execute_flow` está diseñado para background tasks de FastAPI, no para MCP async directo.** La función usa `BackgroundTasks` en la API pero MCP necesita respuesta inmediata. | Media | Alto | Envolver `execute_flow` en un handler que retorne el resultado directamente (no background). El flow puede ser largo — considerar timeout de MCP (default 30s). |
| 2 | **Flows largos exceden timeout de MCP.** Algunos flows (ArchitectFlow, crew-based) pueden tardar >30s. El servidor MCP Stdio puede timeout. | Alta | Alto | Para MVP, documentar que flows largos retornan `task_id` y el agente debe hacer polling con `get_task`. Flows cortos (sync) retornan resultado directo. |
| 3 | **Auth helpers en middleware.py son FastAPI-specific** (usan `HTTPException`, `Depends`). Reutilizarlos en MCP requiere adaptación. | Media | Medio | Extraer la lógica pura de verificación JWT a funciones independientes que no dependan de FastAPI. Los helpers actuales quedan como wrappers FastAPI. |
| 4 | **ServiceConnectorTool usa sync `httpx`** mientras MCP es async. Si un flow usa ServiceConnectorTool, bloquea el event loop. | Media | Medio | Para MVP, aceptable (std io es single-threaded de todas formas). Para SSE futuro, migrar ServiceConnectorTool a async httpx. |
| 5 | **RLS en `pending_approvals`** — el MCP server usa `get_tenant_client` que setea RLS, pero `resume()` usa `get_service_client` (bypass). | Baja | Medio | Verificar que `resume()` funciona con service_role client. Ya está implementado en base_flow.py L255 — usa `get_service_client()` para leer snapshot. |
| 6 | **Discrepancia python-jose vs PyJWT en dependencias.** Si alguien intenta importar de python-jose en código nuevo, fallará. | Baja | Bajo | Documentar en `estado-fase.md` que PyJWT es la librería activa. python-jose es heredado y puede eliminarse. |
| 7 | **Riesgo futuro (Paso 5.3 SSE):** El auth actual es por CLI flag (`--org-id`). Para SSE se necesitará auth por token en header. | Media | Medio | Diseñar `auth.py` para que `verify_mcp_token` sea reusable tanto para Stdio (token pasado como argumento) como para SSE (token en header). |
| 8 | **Correlation ID collision.** Si dos requests MCP concurrentes generan correlation IDs similares, las tasks se cruzan. | Baja | Alto | Usar UUID completo en correlation_id: `f"mcp-{flow_name}-{uuid4()}"` (no slice corto). |

---

## 6. Plan

### Tareas Atómicas

| # | Tarea | Archivos | Complejidad | Tiempo Estimado | Dependencias |
|---|---|---|---|---|---|
| 1 | **Crear `src/mcp/exceptions.py`** con `MCPError`, `MCPErrorCode` enum, y `to_jsonrpc_error()` | `src/mcp/exceptions.py` | Baja | 1 hora | Ninguna |
| 2 | **Extraer lógica de auth de middleware.py** a funciones reutilizables (sin dependencia de FastAPI) | `src/api/middleware.py` (refactor), `src/mcp/auth.py` | Media | 3 horas | Tarea 1 (para usar MCPError) |
| 3 | **Crear `src/mcp/auth.py`** con `verify_mcp_token`, `MCPAuthError`, `auth_context_from_token` | `src/mcp/auth.py` | Media | 2 horas | Tarea 2 |
| 4 | **Crear `src/mcp/handlers.py`** con `execute_flow_handler` | `src/mcp/handlers.py` | Media | 3 horas | Tarea 1, Tarea 3 |
| 5 | **Crear `get_task_handler`** en handlers.py | `src/mcp/handlers.py` | Baja | 1 hora | Tarea 4 |
| 6 | **Crear `approve_task_handler` y `reject_task_handler`** en handlers.py | `src/mcp/handlers.py` | Media | 2 horas | Tarea 4 |
| 7 | **Modificar `tools.py`** para reemplazar `_handle_flow_tool_placeholder` con handlers reales | `src/mcp/tools.py` | Baja | 1 hora | Tarea 4, 5, 6 |
| 8 | **Agregar tools estáticas** para `get_task`, `approve_task`, `reject_task` (opcionales) | `src/mcp/tools.py` | Baja | 1 hora | Tarea 5, 6 |
| 9 | **Integrar auth en handlers** — verificar org membership antes de ejecutar | `src/mcp/handlers.py` | Baja | 1 hora | Tarea 3 |
| 10 | **Testing unitario** — tests para cada handler y auth | `tests/test_mcp_handlers.py`, `tests/test_mcp_auth.py` | Media | 4 horas | Tareas 1-9 |
| 11 | **Testing E2E** — ejecutar flow simple desde MCP server | Manual / script | Media | 2 horas | Tareas 1-9 |
| 12 | **Actualizar `estado-fase.md`** con nuevo estado | `docs/estado-fase.md` | Baja | 30 min | Tareas 1-11 |

**Total estimado:** ~21.5 horas

**Orden de ejecución recomendado:**
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

**Dependencias críticas:**
- Tarea 3 depende de Tarea 2 (auth helpers)
- Tarea 4 depende de Tarea 1 (MCPError) y Tarea 3 (auth)
- Tarea 7 depende de Tareas 4, 5, 6 (handlers completos)
- Tarea 10 (tests) depende de todo lo anterior

---

## 🔮 Roadmap (NO implementar ahora)

### Optimizaciones y mejoras futuras

1. **Async-first ServiceConnectorTool:** Migrar de `httpx.Client` (sync) a `httpx.AsyncClient` para no bloquear el event loop cuando MCP use transporte SSE.

2. **Permisos granulares por flow:** Actualmente cualquier miembro de la org ejecuta cualquier flow. Futuro: tabla `org_flow_permissions` con `org_id, flow_type, role_required`.

3. **Streaming de resultados:** MCP soporta `sampling/createMessage` con streaming. Para flows largos, se podría retornar progreso incremental en vez de polling.

4. **Webhook callbacks desde MCP:** Cuando un flow requiere aprobación, podría enviar un callback al agente externo (vía SSE) en vez de requerir polling.

5. **Eliminación de python-jose:** `python-jose[cryptography]` en pyproject.toml no se usa en código activo (se usa PyJWT). Eliminar para reducir dependencias.

6. **MCP Resource API:** Exponer `tasks`, `snapshots`, `domain_events` como MCP Resources (no solo Tools) para que agentes externos puedan consultar historial sin ejecutar actions.

7. **Rate limiting por org:** Para SSE futuro, agregar rate limiting en auth layer para prevenir abuso.

8. **HITL desde Claude:** Actualmente la aprobación se hace vía dashboard. Futuro: Claude puede aprobar/rechazar directamente desde el chat MCP con herramientas `approve_task` / `reject_task`.

### Pre-requisitos para pasos futuros descubiertos

- **Paso 5.3 (SSE):** Requiere que `auth.py` soporte verificación de token sin dependencia de FastAPI (Tarea 2 de este paso es pre-requisito).
- **Paso 5.3 (HITL completo):** Requiere que los handlers de aprobación estén implementados (Tarea 6 de este paso).
- **Future: Multi-org MCP servers:** Si se necesitan múltiples servidores MCP (uno por org), el auth ya está diseñado para soportarlo vía `verify_mcp_token(token, org_id)`.
