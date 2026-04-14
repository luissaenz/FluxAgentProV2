# Análisis Técnico — Sprint 3: Handlers Productivos (execute_flow)

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|-----------|
| 1 | Tabla `organizations` existe | `grep -r "CREATE TABLE.*organizations" migrations/` | ✅ VERIFICADO | migrations/001_set_config_rpc.sql:15 |
| 2 | Tabla `agent_catalog` existe | `grep -r "CREATE TABLE.*agent_catalog" migrations/` | ✅ VERIFICADO | migrations/004_agent_catalog.sql:6 |
| 3 | Tabla `tasks` existe | `grep -r "CREATE TABLE.*tasks" migrations/` | ✅ VERIFICADO | migrations/001_set_config_rpc.sql:62 |
| 4 | Tabla `pending_approvals` existe | `grep -r "CREATE TABLE.*pending_approvals" migrations/` | ✅ VERIFICADO | migrations/002_governance.sql:50 |
| 5 | Tabla `workflow_templates` existe | `grep -r "CREATE TABLE.*workflow_templates" migrations/` | ✅ VERIFICADO | migrations/006_workflow_templates.sql:6 |
| 6 | Función `get_service_client()` existe | `grep -rn "def get_service_client" src/` | ✅ VERIFICADO | src/db/session.py:45 |
| 7 | Función `_get_jwks_client()` existe | `grep -rn "def _get_jwks_client" src/` | ✅ VERIFICADO | src/api/middleware.py:73 |
| 8 | Función `execute_flow()` existe | `grep -rn "def execute_flow" src/` | ✅ VERIFICADO | src/api/routes/webhooks.py:104 |
| 9 | `flow_registry.get()` existe | `grep -rn "def get" src/flows/registry.py` | ✅ VERIFICADO | src/flows/registry.py:75 |
| 10 | Endpoint `get_task` existe | `grep -rn "@router.get.*task_id" src/api/routes/tasks.py` | ✅ VERIFICADO | src/api/routes/tasks.py:61 |
| 11 | Endpoint `approve_task`/`reject_task` existe | `grep -rn "process_approval" src/api/routes/approvals.py` | ✅ VERIFICADO | src/api/routes/approvals.py:87 |
| 12 | Endpoint `create_workflow` existe | `grep -rn "create.*workflow" src/api/routes/workflows.py` | ❌ DISCREPANCIA | No existe endpoint POST en workflows.py |
| 13 | Librería `python-jose` disponible | `grep "python-jose" pyproject.toml` | ✅ VERIFICADO | pyproject.toml:20 |
| 14 | Librería `mcp` disponible | `grep "mcp" pyproject.toml` | ✅ VERIFICADO | pyproject.toml:30 |
| 15 | Archivos `handlers.py`, `auth.py`, `exceptions.py` no existen | `ls src/mcp/` | ✅ VERIFICADO | Solo config.py, flow_to_tool.py, __init__.py, sanitizer.py, server.py, tools.py |
| 16 | Archivo `tools.py` tiene patrones de handlers | `grep -rn "handle_tool_call" src/mcp/tools.py` | ✅ VERIFICADO | src/mcp/tools.py:68 |
| 17 | Función `sanitize_output()` existe | `grep -rn "def sanitize_output" src/mcp/sanitizer.py` | ✅ VERIFICADO | src/mcp/sanitizer.py:28 |
| 18 | `CallToolResult`, `TextContent` existen | `grep -rn "from mcp.types" src/mcp/tools.py` | ✅ VERIFICADO | src/mcp/tools.py:14 |
| 19 | Flujos retornan estado con task_id | `grep -rn "task_id" src/api/routes/webhooks.py` | ✅ VERIFICADO | src/api/routes/webhooks.py:126 |
| 20 | `require_org_id` existe | `grep -rn "def require_org_id" src/api/middleware.py` | ✅ VERIFICADO | src/api/middleware.py:103 |

**Discrepancias encontradas:**

- **D12: Endpoint `create_workflow` no existe.** El plan asume que existe un endpoint para crear workflows, pero en `src/api/routes/workflows.py` solo hay GET, DELETE. Resolución: Implementar tool `create_workflow` que ejecute ArchitectFlow para generar un workflow_template nuevo.

## 1. Diseño Funcional

El sprint implementa handlers productivos que permiten a Claude ejecutar flows reales en FAP, consultar estado de tareas, aprobar/rechazar tareas pendientes, y crear workflows vía ArchitectFlow.

**Happy path completo (todo el sprint):**
1. Claude invoca `execute_flow` con flow_type y input_data.
2. MCP valida auth (opcional en config), ejecuta flow en background, retorna task_id.
3. Claude consulta `get_task` con task_id para polling de estado.
4. Si flow requiere aprobación, crea pending_approval; Claude puede `approve_task` o `reject_task`.
5. Claude puede `create_workflow` para generar nuevo workflow_template vía ArchitectFlow.

**Edge cases:**
- Flow no existe: Error 404 con lista de flows disponibles.
- Auth falla: Error JSON-RPC con código estándar.
- Ejecución falla: Task en error con mensaje sanitizado.
- Aprobación ya procesada: Error 404.
- Workflow creation falla: Task en error.

**Manejo de errores:**
- Errores internos: Mapeados a códigos JSON-RPC estándar (InvalidRequest, InternalError).
- Outputs: Siempre sanitizados para prevenir leaks.
- Logging: Errores loggeados con contexto, pero no expuestos al LLM.

## 2. Diseño Técnico

**Componentes nuevos:**
- `src/mcp/handlers.py`: Lógica de ejecución real para flows, tasks, approvals, workflows.
- `src/mcp/auth.py`: Bridge con python-jose, reutiliza `_get_jwks_client()` del middleware.
- `src/mcp/exceptions.py`: Mapeo de excepciones internas a códigos JSON-RPC.

**Modificaciones:**
- `src/mcp/tools.py`: Agregar tools `execute_flow`, `get_task`, `approve_task`, `reject_task`, `create_workflow` al STATIC_TOOLS y handlers dict.

**Interfaces (basadas en código verificado):**
- `execute_flow`: Input {flow_type: str, input_data: dict}, Output {task_id: str, status: str}
- `get_task`: Input {task_id: str}, Output TaskResponse (task_id, status, result, error, etc.)
- `approve_task`/`reject_task`: Input {task_id: str, notes?: str}, Output {status: str, decision: str}
- `create_workflow`: Input {name: str, description: str, requirements: str}, Output {task_id: str}

Modelos de datos: Reutilizan tablas existentes (tasks, pending_approvals, workflow_templates) con RLS org_id.

Integraciones: Ejecuta flows vía flow_registry.get(), approvals vía process_approval endpoint, workflows vía ArchitectFlow.

Coherente con estado-fase: Usa patrones de auth JWT ES256, RLS tenant, sanitización R3.

## 3. Decisiones

- **D1: Auth opcional para MCP.** Basado en config.require_auth=False por defecto. Corrige plan §3.2 — auth no requerida inicialmente para compatibilidad con Claude Desktop.
- **D2: Reutilizar execute_flow de webhooks.** Evidencia: src/api/routes/webhooks.py:104 ya implementa background execution. Evita duplicación.
- **D3: Mapeo de errores JSON-RPC.** Patrón estándar: InvalidParams=400, InternalError=500, etc. Evidencia: mcp.types define códigos.
- **D4: create_workflow ejecuta ArchitectFlow.** Resuelve discrepancia D12 — tool invoca flow existente para generar workflow_template.

## 4. Criterios de Aceptación

- ✅ MCP server inicia sin errores con --org-id.
- ✅ Tool `execute_flow` ejecuta flow real y retorna task_id válido.
- ✅ Tool `get_task` retorna estado correcto de task (pending/completed/error).
- ✅ Tool `approve_task` marca pending_approval como approved y resume flow.
- ✅ Tool `reject_task` marca pending_approval como rejected y falla flow.
- ✅ Tool `create_workflow` inicia ArchitectFlow y crea workflow_template.
- ✅ Errores mapeados a códigos JSON-RPC estándar.
- ✅ Outputs sanitizados (sin secrets/keys).
- ✅ Auth opcional funciona sin token y con token JWT.

## 5. Riesgos

- **R1: Flow execution timeouts.** Riesgo: Flows largos bloquean MCP. Mitigación: Background execution ya implementada en execute_flow.
- **R2: Auth failures en producción.** Riesgo: JWKS fetch falla. Mitigación: Reutilizar _get_jwks_client con cache 5min.
- **R3: Sanitización insuficiente.** Riesgo: Leak de datos sensibles. Mitigación: Aplicar sanitize_output a todos outputs, verificar patterns regex.
- **R4: Workflow creation ambigua.** Riesgo: create_workflow sin endpoint claro. Mitigación: Implementar como wrapper de ArchitectFlow, documentar en roadmap.

## 6. Plan

- **T1: Implementar src/mcp/exceptions.py.** Crear mapeo de excepciones a JSON-RPC. Baja complejidad, 30min.
- **T2: Implementar src/mcp/auth.py.** Bridge JWT con _get_jwks_client. Baja complejidad, 45min.
- **T3: Implementar src/mcp/handlers.py.** Handlers para execute_flow, get_task, approve/reject, create_workflow. Media complejidad, 2h.
- **T4: Modificar src/mcp/tools.py.** Agregar nuevas tools a STATIC_TOOLS y handlers dict. Baja complejidad, 30min.
- **T5: Verificar integración.** Ejecutar tools desde MCP server, validar happy path. Baja complejidad, 30min.

**Estimación total: 4h.** Dependencias: T1→T2→T3→T4→T5.

## 🔮 Roadmap

- **Optimización: Caching de flow metadata.** Reducir queries repetidas en list_flows.
- **Mejora: Streaming de outputs largos.** Para flows con outputs grandes, implementar chunking.
- **Feature: Batch execution.** Tool para ejecutar múltiples flows en paralelo.
- **Pre-requisito para Sprint 4:** Handlers estables para integrar SSE transporte.</content>
<parameter name="filePath">/home/daniel/develop/Personal/FluxAgentProV2/LAST/analisis-kilo.md