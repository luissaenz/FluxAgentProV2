# � ANÁLISIS FINAL UNIFICADO — Tools Internas de Onboarding (Paso 3)

**Fuentes:** analisis-atg.md, analisis-kilo.md, analisis-oc.md
**Fecha:** 2026-04-15

---

## 0. Evaluación de Análisis

| Agente | §0 elementos | Discrepancias | Score |
|:---|:---|:---|:---|
| **ATG** | 18 | 3 (firma activate_service, FlowStatus enum, task status) | **4** |
| **Kilo** | 17 | 4 (handlers en handlers.py vs tools.py, routing, extracted_definition, config.org_id) | **4** |
| **OC** | 15 | 4 (firma activate_service, retry no existe, validación service_catalog, FlowStatus) | **4** |

### Discrepancias Consolidadas

| # | Discrepancia | Resolución |
|:---|:---|:---|
| 1 | **`activate_service()` solo acepta `service_id`, no `secret_names`** | ATG y OC lo detectaron. Handler pasa `secret_names` por separado vía segundo call o se agrega al método. Para MVP: activar sin secret_names, usuario configura después con `store_credential`. |
| 2 | **Handlers: ¿tools.py o handlers.py?** | Kilo detectó que tools.py tiene handlers estáticos, handlers.py tiene flows complejos. **Decisión: seguir patrón actual** — handlers simples (activate, store) en tools.py como funciones privadas `_handle_*`, retry_workflow (más complejo) también en tools.py por cohesión con las tools que registra. |
| 3 | **ArchitectFlow marca `completed` en vez de pausar** | Unanimidad. Cambiar a `resolution_pending`. Guardar `extracted_definition` en `task.result`. |
| 4 | **`FlowStatus` enum no tiene `RESOLUTION_PENDING`** | ATG detectó. `tasks.status` es TEXT libre sin CHECK — no necesita migración. Si FlowStatus enum se usa en BaseFlow, agregar el valor. Si solo es TEXT libre en DB, no hay cambio. |
| 5 | **`retry_workflow` reutiliza lógica de ArchitectFlow** | OC propuso instanciar ArchitectFlow internamente. Kilo y ATG coinciden. Reutilizar `_persist_template`, `_persist_agents`, `_register_dynamic_flow` vía instancia. |

---

## 1. Resumen Ejecutivo

Tres tools MCP que cierran el ciclo de onboarding de integraciones. Exponen los métodos ya implementados de IntegrationResolver como acciones invocables por Claude, y modifican ArchitectFlow para pausar (no completar) cuando faltan dependencias.

---

## 2. Diseño Funcional

### Happy Path

```
1. ArchitectFlow detecta needs_activation + needs_credentials
2. Guarda extracted_definition en task.result
3. Marca task como resolution_pending (NO completed)
4. Claude informa al usuario qué falta
5. Usuario proporciona token → Claude invoca store_credential
6. Claude invoca activate_service
7. Claude invoca retry_workflow(task_id)
8. Resolver re-ejecuta → is_ready=True → persiste workflow
9. "Workflow creado exitosamente"
```

### Edge Cases

| Escenario | Comportamiento |
|:---|:---|
| Service no existe en catálogo | activate_service retorna error descriptivo |
| Credencial ya existe | upsert_secret actualiza sin error |
| retry_workflow en task no resolution_pending | Error: "Task en estado X, no puede reintentarse" |
| retry_workflow pero aún faltan deps | Retorna diagnóstico actualizado (still_not_ready) |
| Servicio ya activado | upsert no duplica (on_conflict) |
| secret_value vacío | Error: "secret_value no puede estar vacío" |

---

## 3. Diseño Técnico

### 3.1 — Tres tools en STATIC_TOOLS (`src/mcp/tools.py`)

**activate_service:**
- Input: `{service_id: string}` (required)
- Handler: valida service existe en service_catalog → llama IntegrationResolver.activate_service()
- Output: `{status: "activated", service_id, org_id}`

**store_credential:**
- Input: `{secret_name: string, secret_value: string}` (both required)
- Handler: llama IntegrationResolver.store_credential() → NUNCA retorna el valor
- Output: `{status: "stored", secret_name, message}`

**retry_workflow:**
- Input: `{task_id: string}` (required)
- Handler: recupera task con status=resolution_pending → extrae extracted_definition → re-ejecuta resolve() → si ready: apply_mapping + persist
- Output: `{status: "workflow_created", task_id, flow_type}` o `{status: "still_not_ready", needs_*}`

### 3.2 — Handlers (`src/mcp/tools.py`)

Los 3 handlers se implementan como funciones privadas `_handle_*` en tools.py, siguiendo el patrón actual del archivo. Se agregan al dict `handlers` dentro de `handle_tool_call`.

**activate_service handler:**
```python
async def _handle_activate_service(arguments: dict, config) -> CallToolResult:
    service_id = arguments.get("service_id")
    if not service_id:
        return _make_error("service_id requerido")

    # Validar existe en catálogo
    db = get_service_client()
    svc = db.table("service_catalog").select("id, name").eq("id", service_id).maybe_single().execute()
    if not svc.data:
        return _make_error(f"Servicio '{service_id}' no encontrado en el catálogo")

    resolver = IntegrationResolver(org_id=config.org_id)
    await resolver.activate_service(service_id)
    return _make_result({"status": "activated", "service_id": service_id, "org_id": config.org_id})
```

**store_credential handler:**
```python
async def _handle_store_credential(arguments: dict, config) -> CallToolResult:
    secret_name = arguments.get("secret_name")
    secret_value = arguments.get("secret_value")
    if not secret_name or not secret_value:
        return _make_error("secret_name y secret_value requeridos")

    resolver = IntegrationResolver(org_id=config.org_id)
    await resolver.store_credential(secret_name, secret_value)
    return _make_result({
        "status": "stored",
        "secret_name": secret_name,
        "message": f"Credencial '{secret_name}' almacenada correctamente",
    })
```

**retry_workflow handler:**
```python
async def _handle_retry_workflow(arguments: dict, config) -> CallToolResult:
    task_id = arguments.get("task_id")
    if not task_id:
        return _make_error("task_id requerido")

    db = get_service_client()
    task = db.table("tasks").select("*").eq("id", task_id).eq("org_id", config.org_id).maybe_single().execute()
    if not task.data:
        return _make_error("Tarea no encontrada")
    if task.data["status"] != "resolution_pending":
        return _make_error(f"Tarea en estado '{task.data['status']}', esperaba 'resolution_pending'")

    workflow_def = task.data.get("result", {}).get("extracted_definition")
    if not workflow_def:
        return _make_error("No se encontró definición de workflow guardada")

    # Re-resolver
    resolver = IntegrationResolver(org_id=config.org_id)
    resolution = await resolver.resolve(workflow_def)

    if not resolution.is_ready:
        return _make_result({
            "status": "still_not_ready",
            "needs_activation": resolution.needs_activation,
            "not_found": resolution.not_found,
            "needs_credentials": resolution.needs_credentials,
        })

    # Persistir workflow reutilizando lógica de ArchitectFlow
    mapped_def = resolver.apply_mapping(workflow_def, resolution.tool_mapping)
    workflow_def_obj = WorkflowDefinition(**mapped_def)

    flow_instance = ArchitectFlow(org_id=config.org_id, user_id="mcp-system")
    safe_flow_type = flow_instance._ensure_unique_flow_type(workflow_def_obj.flow_type)
    workflow_def_obj.flow_type = safe_flow_type

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
        },
    }).eq("id", task_id).execute()

    return _make_result({
        "status": "workflow_created",
        "task_id": task_id,
        "flow_type": safe_flow_type,
        "template_id": template_id,
    })
```

### 3.3 — Modificación en ArchitectFlow

**Archivo:** `src/flows/architect_flow.py`
**Ubicación:** Donde actualmente retorna `_build_resolution_response` (~L180)

```python
if not resolution.is_ready:
    # Guardar definición para retry posterior
    output = {
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
        "message": self._build_resolution_response(resolution)["message"],
    }

    # Marcar tarea como resolution_pending (NO completed)
    db = get_service_client()
    db.table("tasks").update({
        "status": "resolution_pending",
        "result": output,
    }).eq("id", self.state.task_id).execute()

    return output
```

### 3.4 — FlowStatus enum (si aplica)

Si `src/flows/state.py` tiene enum FlowStatus usado en transiciones:

```python
class FlowStatus(str, Enum):
    # ... existentes ...
    RESOLUTION_PENDING = "resolution_pending"
```

Si tasks.status es TEXT libre sin validación por enum → no hay cambio.

### Archivos afectados

| Archivo | Cambio |
|:---|:---|
| `src/mcp/tools.py` | MODIFICAR — 3 tools en STATIC_TOOLS + 3 handlers + mappings en handle_tool_call |
| `src/flows/architect_flow.py` | MODIFICAR — resolution_pending en vez de completed + guardar extracted_definition |
| `src/flows/state.py` | POSIBLE — agregar RESOLUTION_PENDING si usa enum |

---

## 4. Decisiones

| # | Decisión | Justificación |
|:---|:---|:---|
| D1 | Handlers en tools.py (no handlers.py) | Patrón actual: tools.py tiene handlers estáticos como funciones privadas. handlers.py tiene flows complejos. (Kilo) |
| D2 | resolution_pending como status de task, no de flow | Diferencia semántica: "esperando config técnica" vs "esperando decisión humana". (ATG) |
| D3 | retry_workflow instancia ArchitectFlow internamente | Reutiliza _persist_template, _persist_agents, _register_dynamic_flow sin duplicar código. (OC, ATG) |
| D4 | activate_service sin secret_names en MVP | El método existente no los acepta. Usuario configura credenciales por separado con store_credential. |
| D5 | No se necesita migración DB | tasks.status es TEXT libre sin CHECK. (OC verificó, unanimidad) |
| D6 | store_credential NUNCA retorna el valor | Seguridad: sanitize_output ya aplicado en _make_result, pero doble protección por diseño. |

---

## 5. Criterios de Aceptación MVP

| # | Criterio |
|:---|:---|
| F1 | `activate_service` retorna `{status: "activated"}` para servicio válido |
| F2 | `activate_service` retorna error para servicio inexistente en catálogo |
| F3 | `store_credential` retorna `{status: "stored"}` sin revelar el valor |
| F4 | `store_credential` rechaza secret_value vacío |
| F5 | `retry_workflow` retorna `{status: "workflow_created"}` cuando todo resuelto |
| F6 | `retry_workflow` retorna `{status: "still_not_ready"}` con diagnóstico si faltan deps |
| F7 | `retry_workflow` retorna error si task no está en resolution_pending |
| T1 | ArchitectFlow marca task como resolution_pending cuando is_ready=False |
| T2 | ArchitectFlow guarda extracted_definition en task.result |
| T3 | Las 3 tools aparecen en tools/list del MCP server |
| T4 | Workflow se crea exitosamente en DB después del ciclo completo (pause → fix → retry) |

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Tiempo | Deps |
|:---|:---|:---|:---|:---|
| 1 | Agregar 3 tools a STATIC_TOOLS | Baja | 15min | — |
| 2 | Implementar _handle_activate_service + _handle_store_credential | Baja | 30min | T1 |
| 3 | Implementar _handle_retry_workflow (más complejo) | Media | 1h | T2 |
| 4 | Agregar mappings en handle_tool_call | Baja | 10min | T2-T3 |
| 5 | Modificar ArchitectFlow: resolution_pending + guardar extracted_definition | Media | 45min | — |
| 6 | Agregar RESOLUTION_PENDING a FlowStatus si usa enum | Baja | 10min | — |
| 7 | Test E2E: create → pause → activate → store → retry → created | Alta | 1h | T1-T6 |
| **Total** | | | **~4h** | |

---

## 7. Riesgos

| # | Riesgo | Mitigación |
|:---|:---|:---|
| R1 | retry_workflow pierde contexto si extracted_definition no se guardó bien | Verificar que task.result tiene el campo antes de procesar |
| R2 | Credencial en texto plano por MCP | Canal Stdio/SSE asumido seguro. Handler cifra inmediatamente vía upsert_secret. |
| R3 | Race condition en retry concurrent | Check status=resolution_pending es atómico con la query. Segundo retry retorna error. |
| R4 | ArchitectFlow._persist_template como método privado puede cambiar | Riesgo aceptable para MVP. Post-MVP: extraer a módulo compartido. |

---

## 8. � Roadmap

- Auto-retry al detectar evento secret.created
- Tool cancel_workflow para abortar workflows pendientes
- Dashboard UI para activar servicios y cargar credenciales sin chat
- Wizard de configuración post-activate_service
- Tracking de intentos de retry por task

---

*3 análisis evaluados, 5 discrepancias resueltas. Estimación: ~4h.*
