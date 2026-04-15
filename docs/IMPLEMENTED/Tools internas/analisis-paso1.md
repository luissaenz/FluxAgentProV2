# 📋 ANÁLISIS TÉCNICO — Paso 1: Tools Internas de Onboarding

**Paso:** 1 (Tools internas)
**Estado:** Pendiente de implementación
**Alcance:** 4 archivos (tools.py, server.py, architect_flow.py, migrations/)

---

## §0. Verificación Contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `tasks` existe | `grep "CREATE TABLE.*tasks" migrations/001_*.sql` | ✅ | schema: `status TEXT NOT NULL DEFAULT 'pending'` (sin CHECK constraint) |
| 2 | `IntegrationResolver.activate_service()` existe | `grep -n "def activate_service" src/flows/integration_resolver.py` | ✅ | Línea 177: `async def activate_service(self, service_id: str)` |
| 3 | `IntegrationResolver.store_credential()` existe | `grep -n "def store_credential" src/flows/integration_resolver.py` | ✅ | Línea 186: `async def store_credential(self, secret_name: str, secret_value: str)` |
| 4 | `upsert_secret` en vault.py | `grep -n "def upsert_secret" src/db/vault.py` | ✅ | Línea 12 |
| 5 | `STATIC_TOOLS` en tools.py | `grep -n "STATIC_TOOLS" src/mcp/tools.py` | ✅ | Línea 23: lista de Tool definitions |
| 6 | `handle_tool_call` routing | `grep -n "def handle_tool_call" src/mcp/tools.py` | ✅ | Línea 126: dispatcher principal |
| 7 | `MCPConfig` tiene org_id | `grep -n "org_id" src/mcp/config.py` | ✅ | Línea 18: `org_id: str = ""` |
| 8 | `ArchitectFlow._build_resolution_response` | `grep -n "_build_resolution_response" src/flows/architect_flow.py` | ✅ | Línea 467 |
| 9 | `ArchitectFlow` usa `IntegrationResolver.resolve()` | `grep -n "resolver.resolve" src/flows/architect_flow.py` | ✅ | Línea 139: `resolution = await resolver.resolve(...)` |
| 10 | handlers registrados en server.py | `grep "handle_" src/mcp/server.py` → Solo lista tools | ⚠️ | Handlers NO se registran manualmente — routing happens inside `handle_tool_call` en tools.py |
| 11 | `BaseFlow.execute()` lifecycle | `grep -n "async def execute" src/flows/base_flow.py` | ✅ | Líneas 102-161: validate → create_task → start → run_crew → complete |
| 12 | `service_catalog` existe | `grep "CREATE TABLE.*service_catalog" migrations/024_*.sql` | ✅ | Migración 024 |

**Discrepancias encontradas:**

1. **D1: El plan propone `activate_service(service_id, secret_names)` pero el código real acepta solo `service_id`**
   - Evidencia: `integration_resolver.py:177` — `async def activate_service(self, service_id: str) -> None`
   - Resolución: El handler debe pasar `secret_names` por separado o la tool debe validar credenciales luego de activar

2. **D2: El plan dice que ArchitectFlow "termina el flow" pero el código actual YA retorna diagnóstico**
   - Evidencia: `architect_flow.py:180-181` — retorna `_build_resolution_response(resolution)` con `status: "resolution_required"`
   - Pero NO cambia el status de la tarea a `resolution_pending` — marca como completed
   - Resolución: Necesita modificar `architect_flow.py` para:
     - Guardar `extracted_definition` en el payload o result
     - Actualizar status a `resolution_pending` (no hay CHECK constraint,acepta TEXT libre)

3. **D3: No existe función `retry_workflow` en ningún archivo**
   - Evidencia: `grep -rn "retry_workflow" src/` → 0 resultados
   - Resolución: Debe crearse como nuevo handler

4. **D4: El handler de activate_service debe verificar que el servicio exista en service_catalog antes de activar**
   - Evidencia actual: `activate_service` hace upsert direto sin verificar existencia
   - Resolución: Agregar validación en el handler de la tool

---

## 1. Diseño Funcional

### 1.1 Happy Path Completo

```
1. Usuario: "Quiero un agente que lea correos de Google Sheets"
2. Claude invoca create_workflow({description: "..."})
3. ArchitectFlow genera workflow_def
4. IntegrationResolver.resolve() detecta:
   - needs_activation: ["google_sheets"]
   - needs_credentials: ["google_oauth_token"]
5. ArchitectFlow:
   - Guarda extracted_definition.model_dump() en result (para retry)
   - Actualiza task.status = "resolution_pending" (NO completed)
   - Retorna diagnosis _build_resolution_response(resolution)
6. BaseFlow marca RUNNING → (no completa porque status!=RUNNING)
7. Claude dice al usuario: "Falta activar Google Sheets y configurar token"
8. Usuario proporciona token: "ya29.xxx..."
9. Claude invoca store_credential({secret_name: "google_oauth_token", secret_value: "ya29..."})
   - Handler: upsert_secret(org_id, secret_name, secret_value)
   - Retorna: {status: "stored", secret_name: "...", message: "..."}
10. Claude invoca activate_service({service_id: "google_sheets"})
    - Handler: verifica existe en service_catalog
    - IntegrationResolver.activate_service("google_sheets")
    - upsert en org_service_integrations con status="pending_setup"
    - Retorna: {status: "activated", service_id: "google_sheets"}
11. Claude invoca retry_workflow({task_id: "..."})
    - Handler: busca task con status="resolution_pending"
    - Recupera extracted_definition del result
    - Re-ejecuta IntegrationResolver.resolve()
    - Si is_ready: apply_mapping, persist template/agents, registra flow
    - Si no is_ready: retorna nuevo diagnóstico
12. Claude: "Workflow creado exitosamente"
```

### 1.2 Edge Cases MVP

| Escenario | Manejo |
|---|---|
| Usuario intenta activate_service de servicio que NO existe | Retornar error: "Servicio 'X' no encontrado en catálogo" |
| Usuario intenta retry_workflow de task sin status resolution_pending | Retornar error | 
| Usuario intenta retry_workflow de task que ya fue completada | Retornar error: "Workflow ya creado, usa get_task para ver" |
| Credencial ya existe (update vs insert) | upsert_secret maneja update automatically |
| Workflow con mismo flow_type ya existe | _ensure_unique_flow_type agrega sufijo org |
| IntegrationResolver retorna error durante retry | Propagar error, marcar tarea como failed |

### 1.3 Mensajes de Error UX

| Caso | Mensaje |
|---|---|
| activate_service: servicio no existe | `{"error": "Servicio 'google_sheets' no encontrado en el catálogo. Ejecute list_services para ver disponibles."}` |
| store_credential: valor vacío | `{"error": "secret_value no puede estar vacío"}` |
| retry_workflow: task no encontrada | `{"error": "Task no encontrada"}` |
| retry_workflow: status incorrecto | `{"error": "Task en status 'completed', no se puede reintentar"}` |

---

## 2. Diseño Técnico

### 2.1 Nuevas Tools a agregar en `src/mcp/tools.py`

```python
# Agregar a STATIC_TOOLS (línea 23):

Tool(
    name="activate_service",
    description="Activa un servicio del catálogo de integraciones para la organización actual. "
                "Úsalo cuando el sistema indica que un servicio necesita activación.",
    inputSchema={
        "type": "object",
        "required": ["service_id"],
        "properties": {
            "service_id": {
                "type": "string",
                "description": "ID del servicio a activar (ej: google_sheets, gmail, stripe)"
            }
        }
    }
),

Tool(
    name="store_credential",
    description="Almacena una credencial (API key, token OAuth, etc.) en el vault seguro "
                "de la organización. El valor se encripta y nunca se muestra después.",
    inputSchema={
        "type": "object",
        "required": ["secret_name", "secret_value"],
        "properties": {
            "secret_name": {
                "type": "string",
                "description": "Nombre del secreto (ej: google_oauth_token, stripe_api_key)"
            },
            "secret_value": {
                "type": "string",
                "description": "Valor del secreto. Se almacena encriptado."
            }
        }
    }
),

Tool(
    name="retry_workflow",
    description="Re-ejecuta la resolución de un workflow que estaba pendiente de integraciones. "
                "Úsalo después de activar servicios y configurar credenciales.",
    inputSchema={
        "type": "object",
        "required": ["task_id"],
        "properties": {
            "task_id": {
                "type": "string",
                "description": "ID de la tarea del workflow que necesita re-resolución"
            }
        }
    }
),
```

### 2.2 Nuevos Handlers

```python
# En src/mcp/tools.py, agregar a handlers dict (línea 156):

handlers = {
    # ... existing ...
    "activate_service": _handle_activate_service,
    "store_credential": _handle_store_credential,
    "retry_workflow": _handle_retry_workflow,
}

# Implementaciones:

async def _handle_activate_service(arguments: dict, config) -> CallToolResult:
    """Activa un servicio para la org."""
    service_id = arguments.get("service_id")
    if not service_id:
        return CallToolResult(
            content=[TextContent(type="text", text='{"error": "service_id requerido"}')],
            isError=True,
        )

    db = get_service_client()
    # Verificar existe en service_catalog
    svc = db.table("service_catalog").select("id, name").eq("id", service_id).maybe_single().execute()
    if not svc.data:
        return CallToolResult(
            content=[TextContent(type="text", text=f'{{"error": "Servicio \\'{service_id}\\' no encontrado en el catálogo"}}')],
            isError=True,
        )

    # Integrator resolver
    from ..flows.integration_resolver import IntegrationResolver
    resolver = IntegrationResolver(org_id=config.org_id)
    await resolver.activate_service(service_id)

    return _make_result({
        "status": "activated",
        "service_id": service_id,
        "org_id": config.org_id,
    })


async def _handle_store_credential(arguments: dict, config) -> CallToolResult:
    """Almacena credencial en Vault."""
    secret_name = arguments.get("secret_name")
    secret_value = arguments.get("secret_value")

    if not secret_name or not secret_value:
        return CallToolResult(
            content=[TextContent(type="text", text='{"error": "secret_name y secret_value requeridos"}')],
            isError=True,
        )

    from ..flows.integration_resolver import IntegrationResolver
    resolver = IntegrationResolver(org_id=config.org_id)
    await resolver.store_credential(secret_name, secret_value)

    return _make_result({
        "status": "stored",
        "secret_name": secret_name,
        "message": f"Credencial '{secret_name}' almacenada correctamente",
    })


async def _handle_retry_workflow(arguments: dict, config) -> CallToolResult:
    """Re-ejecuta resolución de workflow pendiente."""
    task_id = arguments.get("task_id")
    if not task_id:
        return CallToolResult(
            content=[TextContent(type="text", text='{"error": "task_id requerido"}')],
            isError=True,
        )

    db = get_service_client()
    task = db.table("tasks").select("*").eq("id", task_id).eq("org_id", config.org_id).maybe_single().execute()
    if not task.data:
        return CallToolResult(
            content=[TextContent(type="text", text='{"error": "Tarea no encontrada"}')],
            isError=True,
        )

    if task.data["status"] != "resolution_pending":
        return CallToolResult(
            content=[TextContent(type="text", text=f'{{"error": "Tarea en estado \\'{task.data["status"]}\\' no puede reintentarse"}}')],
            isError=True,
        )

    # Extraer definición guardada
    workflow_def = task.data.get("result", {}).get("extracted_definition")
    if not workflow_def:
        return CallToolResult(
            content=[TextContent(type="text", text='{"error": "No se encontró definición de workflow guardada"}')],
            isError=True,
        )

    # Re-ejecutar resolución
    from ..flows.integration_resolver import IntegrationResolver
    resolver = IntegrationResolver(org_id=config.org_id)
    resolution = await resolver.resolve(workflow_def)

    if not resolution.is_ready:
        return _make_result({
            "status": "still_not_ready",
            "needs_activation": resolution.needs_activation,
            "not_found": resolution.not_found,
            "needs_credentials": resolution.needs_credentials,
        })

    # Workflow listo — aplicar mapeo y persistir (reutilizar lógica de ArchitectFlow)
    # NOTA: Esto requiere instanciar ArchitectFlow internamente o extraer lógica a función reusable
    from ..flows.architect_flow import ArchitectFlow
    from ..flows.workflow_definition import WorkflowDefinition

    mapped_def = resolver.apply_mapping(workflow_def, resolution.tool_mapping)
    workflow_def_obj = WorkflowDefinition(**mapped_def)

    # Asegurar flow_type único
    flow_instance = ArchitectFlow(org_id=config.org_id, user_id="mcp-system")
    safe_flow_type = flow_instance._ensure_unique_flow_type(workflow_def_obj.flow_type)
    workflow_def_obj.flow_type = safe_flow_type

    # Persistir template y agentes
    template_id = await flow_instance._persist_template(workflow_def_obj)
    agents_created = await flow_instance._persist_agents(workflow_def_obj)
    flow_instance._register_dynamic_flow(safe_flow_type, workflow_def_obj)

    # Actualizar task a completed
    db.table("tasks").update({
        "status": "completed",
        "result": {
            "flow_type": safe_flow_type,
            "template_id": template_id,
            "agents_created": agents_created,
        }
    }).eq("id", task_id).execute()

    return _make_result({
        "status": "workflow_created",
        "task_id": task_id,
        "flow_type": safe_flow_type,
        "template_id": template_id,
    })
```

### 2.3 Modificación en ArchitectFlow

Ubicación: `src/flows/architect_flow.py`, método `_run_crew()`, líneas 141-181

**Cambio requerido:**

```python
# REEMPLAZAR la sección donde retorna _build_resolution_response (líneas 180-181):

# Currently:
#   logger.warning("ArchitectFlow: Resolución incompleta para org %s", self.org_id)
#   return self._build_resolution_response(resolution)

# NEW CODE:
if not resolution.is_ready:
    # Guardar definición extraída para retry posterior
    # Marcar tarea como resolution_pending (NO completed)
    self.state.output_data = {
        "status": "resolution_required",
        "is_ready": False,
        "extracted_definition": workflow_def.model_dump(),
        "resolution": {
            "available": resolution.available,
            "needs_activation": resolution.needs_activation,
            "not_found": resolution.not_found,
            "needs_credentials": resolution.needs_credentials,
            "tool_mapping": resolution.tool_mapping,
        },
    }
    # Update task status to resolution_pending
    with get_tenant_client(self.org_id, self.state.user_id) as db:
        db.table("tasks").update({
            "status": "resolution_pending",
            "result": self.state.output_data,
        }).eq("id", self.state.task_id).execute()

    # Emitir evento
    await self.emit_event("flow.resolution_pending", {"task_id": self.state.task_id})

    return self.state.output_data
```

**Nota:** El estado `resolution_pending` no existe en `FlowStatus` enum. Debe agregarse si el sistema usa el enum. Si el status se maneja como string libre (TEXT), no hay cambio necesario.

### 2.4 No se requiere migración

La tabla `tasks.status` es `TEXT NOT NULL DEFAULT 'pending'` sin CHECK constraint. Acepta cualquier valor de texto. No se necesita migración.

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|---|---|
| D1 | **Handlers en tools.py, no en handlers.py** | tools.py ya tiene el patrón de handlers estáticos. handlers.py contiene flows complejos. Las tools internas son simples wrappers de IntegrationResolver. |
| D2 | **retry_workflow reinstancia lógica de ArchitectFlow** | Evita código duplicado. Alternativa: extraer `_persist_template`, `_persist_agents` a módulo compartido. Trade-off: alta cohesión vs DRY. **Elegido:** reutilizar flow instance interno (más simple para MVP). |
| D3 | **No agregar nuevo estado a FlowStatus enum** | status en DB es TEXT libre. El enum solo se usa en BaseFlowState para transiciones internas. resolution_pending es estado de tarea, no de flow execution. |
| D4 | **Verificar service_catalog antes de activate_service** | previene upsert de servicios inexistentes que causarían errores posteriores. |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| CA1 | `activate_service` retorna status="activated" para servicio válido | Invocar tool → JSON con status ✅ |
| CA2 | `activate_service` retorna error para servicio inexistente | Invocar tool → error ✅ |
| CA3 | `store_credential` retorna status="stored" | Invocar tool → JSON con status ✅ |
| CA4 | `store_credential` no retorna nunca el valor | Verificar response no contiene secret_value ✅ |
| CA5 | `retry_workflow` retorna workflow_created para task resolution_pending lista | integration resolver returns is_ready=True ✅ |
| CA6 | `retry_workflow` retorna error para task sin status resolution_pending | Different status → error ✅ |
| CA7 | ArchitectFlow marca task status como resolution_pending cuando is_ready=False | Query DB task status ✅ |
| CA8 | retry_workflow guarda workflow en DB (template + agents) | Query workflow_templates y agent_catalog ✅ |

---

## 5. Riesgos

| # | Riesgo | Estrategia |
|---|---|---|
| R1 | **retry_workflow重复执行时状态竞争** |retry_workflow hace check-and-update atómico con status check. Si hay并发, segundo retorna error. |
| R2 | **Extracted definition guardada en result puede superar límites JSONB** | WorkflowDefinition tiene límites implícitos. Si es muy grande, fallback guardar en tabla separada. Monitorear en implement. |
| R3 | **activate_service no valida secretos requeridos** | MVP: solo activa. Post-MVP: wizard de configuración. |
| R4 | **Retry después de activate_service puede fallar por otros missing** | retry_workflow retorna diagnóstico completo igual que ArchitectFlow. |
| R5 | **No hay forma de cancelar un workflow pending** | Roadmap: agregar tool cancel_workflow. |

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Estimación | Dependencia |
|---|---|---|---|---|
| T1 | Agregar 3 tool definitions a STATIC_TOOLS | Baja | 15 min | — |
| T2 | Implementar handlers `_handle_activate_service`, `_handle_store_credential`, `_handle_retry_workflow` | Media | 45 min | T1 |
| T3 | Agregar handlers al dict en `handle_tool_call` | Baja | 10 min | T2 |
| T4 | Modificar ArchitectFlow: guardar extracted_definition y status=resolution_pending | Media | 30 min | — |
| T5 | Test manual: flujo completo (create → pause → activate → retry) | Alta | 60 min | T4 |
| T6 | Test unitario handlers (opcional, según infraestructura) | Media | 30 min | T2 |
| | **Total** | | | **~3h 10min** | |

---

## 7. Roadmap (Post-MVP)

1. **Workflow Cancel Tool** — permite cancelar un workflow en resolution_pending
2. **Wizard de Configuración** — dopo activate_service, guiar al usuario por setup de credenciales requeridas
3. **Notificaciones** — avisar al usuario cuando un servicio requiere atención
4. **Streaming de Resolución** — feedback en tiempo real mientras resolve()
5. **Múltiples retry** — tracking de cuántos intentos y éxito histórico

---

## §Anexo: Evidencia de Verification

```
$ grep "CREATE TABLE.*tasks" supabase/migrations/001_set_config_rpc.sql
62: CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    flow_type       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',  ← TEXT libre,sin CHECK

$ grep "def activate_service" src/flows/integration_resolver.py
177:     async def activate_service(self, service_id: str) -> None:

$ grep "def store_credential" src/flows/integration_resolver.py  
186:     async def store_credential(self, secret_name: str, secret_value: str) -> None:

$ grep "def upsert_secret" src/db/vault.py
12: def upsert_secret(org_id: str, name: str, value: str) -> None:

$ grep -n "STATIC_TOOLS" src/mcp/tools.py
23: STATIC_TOOLS = [

$ grep -n "resolution_required" src/flows/architect_flow.py
492: "status": "resolution_required",
```