Paso 1: Tools internas
1. **Dead code** — activate_service/store_credential implementados pero nunca llamados
2. **Sin interfaz** — el usuario no puede ejecutar las acciones correctivas
3. **Dead end** — ArchitectFlow termina el flow en vez de pausar y esperar resolución

Las tools internas resuelven los 3: exponen los métodos como tools MCP invocables por Claude, y el flujo de ArchitectFlow se modifica para pausar (no completar) cuando falta resolución.

---

## Definición: Tools internas de onboarding

### Qué son

Dos tools MCP que exponen `IntegrationResolver.activate_service()` y `store_credential()` como acciones invocables por Claude durante una conversación. No son tools de agentes CrewAI — son tools del MCP Server que Claude usa directamente.

### Dónde se registran

En `src/mcp/tools.py` junto a las tools estáticas existentes (`list_flows`, `list_agents`, etc.). Son tools de sistema, no de negocio.

### Flujo completo post-integración

```
1. Usuario: "Quiero un agente que lea correos de Google Sheets"

2. ArchitectFlow genera workflow → IntegrationResolver detecta:
   - needs_activation: ["google_sheets"]
   - needs_credentials: ["google_oauth_token"]

3. ArchitectFlow PAUSA (no completa) → retorna diagnóstico a Claude

4. Claude le dice al usuario:
   "Necesito activar Google Sheets y configurar credenciales.
    ¿Tenés un token OAuth de Google?"

5. Usuario: "Sí, es ya29.xxx..."

6. Claude invoca: store_credential("google_oauth_token", "ya29.xxx")
   → Tool guarda en Vault

7. Claude invoca: activate_service("google_sheets", ["google_oauth_token"])
   → Tool activa servicio para la org

8. Claude invoca: retry_workflow(task_id)
   → ArchitectFlow re-ejecuta resolve() → is_ready=True → persiste workflow

9. Claude: "Workflow creado. ¿Lo ejecuto ahora?"
```

### Tools a crear

**Tool 1: `activate_service`**

```python
# En src/mcp/tools.py

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
            },
            "secret_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Nombres de los secretos requeridos por el servicio"
            }
        }
    }
)
```

Handler:
```python
async def handle_activate_service(org_id: str, args: dict) -> str:
    resolver = IntegrationResolver(org_id)
    service_id = args["service_id"]
    secret_names = args.get("secret_names", [])

    # Verificar que el servicio existe en el catálogo
    db = get_service_client()
    service = db.table("service_catalog").select("id, name").eq("id", service_id).maybe_single().execute()
    if not service.data:
        return json.dumps({"error": f"Servicio '{service_id}' no existe en el catálogo"})

    await resolver.activate_service(service_id, secret_names)
    return json.dumps({"status": "activated", "service_id": service_id, "org_id": org_id})
```

**Tool 2: `store_credential`**

```python
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
)
```

Handler:
```python
async def handle_store_credential(org_id: str, args: dict) -> str:
    resolver = IntegrationResolver(org_id)
    secret_name = args["secret_name"]
    secret_value = args["secret_value"]

    await resolver.store_credential(secret_name, secret_value)

    # NUNCA retornar el valor — solo confirmación
    return json.dumps({
        "status": "stored",
        "secret_name": secret_name,
        "message": f"Credencial '{secret_name}' almacenada correctamente"
    })
```

**Tool 3: `retry_workflow` (necesaria para cerrar el ciclo)**

```python
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
)
```

Handler:
```python
async def handle_retry_workflow(org_id: str, args: dict) -> str:
    task_id = args["task_id"]
    db = get_service_client()

    # Recuperar la tarea con la definición guardada
    task = db.table("tasks").select("*").eq("id", task_id).eq("org_id", org_id).single().execute()
    if not task.data:
        return json.dumps({"error": "Tarea no encontrada"})

    if task.data["status"] != "resolution_pending":
        return json.dumps({"error": f"Tarea en estado '{task.data['status']}', esperaba 'resolution_pending'"})

    # Recuperar workflow_def guardado en result
    workflow_def = task.data.get("result", {}).get("extracted_definition")
    if not workflow_def:
        return json.dumps({"error": "No se encontró definición de workflow guardada"})

    # Re-ejecutar resolución
    resolver = IntegrationResolver(org_id)
    resolution = await resolver.resolve(workflow_def)

    if not resolution.is_ready:
        return json.dumps({
            "status": "still_not_ready",
            "needs_activation": resolution.needs_activation,
            "not_found": resolution.not_found,
            "needs_credentials": resolution.needs_credentials,
        })

    # Aplicar mapping y persistir
    mapped_def = resolver.apply_mapping(workflow_def, resolution.tool_mapping)

    # Continuar con la lógica de persistencia de ArchitectFlow
    # (crear template, upsert agentes, registrar flow)
    # ... reutilizar _persist_template y _persist_agents del ArchitectFlow

    return json.dumps({"status": "workflow_created", "task_id": task_id})
```

### Cambio en ArchitectFlow: pausar en vez de completar

El cambio más importante. Actualmente cuando `is_ready=False`, ArchitectFlow retorna el diagnóstico y el BaseFlow marca la tarea como `completed`. Esto debe cambiar a `resolution_pending`:

```python
# architect_flow.py — donde hoy retorna _build_resolution_response

if not resolution.is_ready:
    # Guardar definición extraída para retry posterior
    self.state.output_data = {
        "status": "resolution_required",
        "extracted_definition": workflow_def.model_dump(),
        "resolution": { ... },
        "message": "...",
    }
    # Marcar tarea como pendiente de resolución (NO completed)
    await self._update_task_status("resolution_pending")
    return self.state.output_data
```

Esto requiere que `tasks.status` acepte el valor `resolution_pending`. Verificar si la columna es TEXT libre o tiene CHECK constraint.

### Archivos afectados

| Archivo | Cambio |
|:---|:---|
| `src/mcp/tools.py` | **MODIFICAR** — agregar 3 tools + 3 handlers |
| `src/mcp/server.py` | **MODIFICAR** — registrar handlers en dispatcher |
| `src/flows/architect_flow.py` | **MODIFICAR** — cambiar `completed` a `resolution_pending` cuando is_ready=False |
| `supabase/migrations/` | **POSIBLE** — si tasks.status tiene CHECK constraint, agregar `resolution_pending` |

### Esfuerzo estimado

| Tarea | Tiempo |
|:---|:---|
| Tool `activate_service` + handler | 45min |
| Tool `store_credential` + handler | 45min |
| Tool `retry_workflow` + handler | 1.5h |
| Modificar ArchitectFlow (pausar vs completar) | 1h |
| Registrar tools en server.py | 15min |
| Migración si tasks.status tiene constraint | 15min |
| Tests | 1.5h |
| **Total** | **~6h** |
