# 🧠 PROCESO DE ANÁLISIS TÉCNICO (ANALISTA) v3

**Paso Asignado:** Paso 1 - Tools internas
**Agente:** kilo
**Fecha:** 2026-04-15

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|----------|
| 1 | Tabla `tasks` con columna `status` TEXT | `grep -rn "CREATE TABLE.*tasks" supabase/migrations/` | ✅ VERIFICADO | migrations/001_set_config_rpc.sql:62-73, `status TEXT NOT NULL DEFAULT 'pending'` |
| 2 | Tabla `service_catalog` existe | `grep -r "service_catalog" supabase/migrations/` | ✅ VERIFICADO | migrations/024_service_catalog.sql, tabla con `required_secrets` |
| 3 | Tabla `secrets` existe para vault | `grep -r "CREATE TABLE.*secrets" supabase/migrations/` | ✅ VERIFICADO | migrations/027_secrets_write_policy.sql, tabla con `secret_value` |
| 4 | Tabla `org_service_integrations` existe | `grep -r "org_service_integrations" supabase/migrations/` | ✅ VERIFICADO | migrations/005_org_mcp_servers.sql, tabla con `service_id` y `status` |
| 5 | Función `IntegrationResolver.activate_service()` | `grep -rn "def activate_service" src/flows/integration_resolver.py` | ✅ VERIFICADO | integration_resolver.py:177, método async que upsert a `org_service_integrations` |
| 6 | Función `IntegrationResolver.store_credential()` | `grep -rn "def store_credential" src/flows/integration_resolver.py` | ✅ VERIFICADO | integration_resolver.py:186, método async que llama `upsert_secret` |
| 7 | Función `upsert_secret()` en vault | `grep -rn "def upsert_secret" src/db/vault.py` | ✅ VERIFICADO | vault.py:105, función que upsert a tabla `secrets` |
| 8 | Patrón MCP tools en `STATIC_TOOLS` | `grep -rn "STATIC_TOOLS" src/mcp/tools.py` | ✅ VERIFICADO | tools.py:23, lista de Tool objects con name, description, inputSchema |
| 9 | Patrón handlers en `handlers.py` | `grep -rn "handle_execute_flow" src/mcp/handlers.py` | ✅ VERIFICADO | handlers.py:22, funciones async que retornan dict |
| 10 | Routing de tools en `handle_tool_call` | `grep -rn "handlers.get" src/mcp/tools.py` | ✅ VERIFICADO | tools.py:156-167, diccionario de handlers mapeados por name |
| 11 | `ArchitectFlow._build_resolution_response()` | `grep -rn "def _build_resolution_response" src/flows/architect_flow.py` | ✅ VERIFICADO | architect_flow.py:467, método que construye respuesta de diagnóstico |
| 12 | Campo `result` en tabla `tasks` para guardar definición | `grep -rn "result.*JSONB" supabase/migrations/` | ✅ VERIFICADO | migrations/001_set_config_rpc.sql:68, `result JSONB` |
| 13 | Dependencia `mcp` en pyproject.toml | `grep -rn "mcp" pyproject.toml` | ✅ VERIFICADO | pyproject.toml:30, `"mcp>=1.0.0,<2.0.0"` |
| 14 | Patrón `sanitize_output()` para respuestas | `grep -rn "sanitize_output" src/mcp/tools.py` | ✅ VERIFICADO | tools.py:16, import y uso en _make_result |
| 15 | `get_service_client()` para DB operations | `grep -rn "get_service_client" src/db/session.py` | ✅ VERIFICADO | session.py, función que retorna cliente con service_role |
| 16 | Patrón `BaseFlow` con `_update_task_status` | `grep -rn "_update_task_status" src/flows/base_flow.py` | ⚠️ NO VERIFICABLE | No encontré implementación, pero BaseFlow debe tener método para actualizar status. Asumo existe según patrón de flows. |
| 17 | `ArchitectFlow` llama `resolver.resolve()` con `model_dump()` | `grep -rn "resolver.resolve" src/flows/architect_flow.py` | ✅ VERIFICADO | architect_flow.py:137-138, `resolution = await resolver.resolve(workflow_def.model_dump())` |

**Discrepancias encontradas:**

1. **DISCREPANCIA (D1):** El plan asume que los handlers se implementan en `tools.py`, pero el código actual separa handlers en `handlers.py` (línea 136-139 en tools.py importa desde handlers). **Resolución:** Mantener patrón actual — implementar nuevos handlers en `handlers.py` y mapearlos en `handle_tool_call` de `tools.py`.

2. **DISCREPANCIA (D2):** El plan indica modificar `server.py` para registrar handlers en dispatcher, pero actualmente el routing se hace en `handle_tool_call` dentro de `tools.py`. **Resolución:** Seguir patrón actual — agregar mappings en `handle_tool_call` en `tools.py`, no modificar `server.py`.

3. **DISCREPANCIA (D3):** `ArchitectFlow` actualmente retorna `_build_resolution_response` y permite que `BaseFlow` marque la tarea como `completed` (línea 181), pero el plan requiere cambiar a `resolution_pending`. **Resolución:** Modificar `ArchitectFlow` para llamar `await self._update_task_status("resolution_pending")` antes de retornar, guardando `extracted_definition` en `state.output_data`.

4. **DISCREPANCIA (D4):** El plan usa `org_id` en handlers MCP, pero el código actual recibe `config` object con `org_id` attribute. **Resolución:** Usar `config.org_id` en handlers siguiendo patrón actual.

## 1. Diseño Funcional

### Happy Path Completo del Paso

1. **Usuario solicita workflow con tools faltantes:** "Quiero un agente que lea correos de Gmail"

2. **ArchitectFlow detecta dependencias:** IntegrationResolver identifica `gmail.read_emails` no encontrado, requiere activación de `gmail` service y credencial `gmail_oauth_token`

3. **ArchitectFlow pausa ejecución:** En lugar de completar con error, guarda definición extraída en `task.result` y marca tarea como `resolution_pending`

4. **Claude informa al usuario:** "Necesito activar Gmail y configurar credenciales OAuth. ¿Tienes el token?"

5. **Usuario proporciona credencial:** "Sí, es ya29.xxx..."

6. **Claude invoca tool `store_credential`:** `store_credential("gmail_oauth_token", "ya29.xxx")` guarda en vault

7. **Claude invoca tool `activate_service`:** `activate_service("gmail", ["gmail_oauth_token"])` marca service como `pending_setup`

8. **Claude invoca tool `retry_workflow`:** `retry_workflow(task_id)` re-ejecuta resolución con credenciales ahora disponibles

9. **ArchitectFlow reanuda y completa:** Resolver encuentra tools disponibles, persiste template y agentes, registra flow dinámicamente

10. **Workflow creado exitosamente:** Usuario puede ejecutar con endpoint correspondiente

### Edge Cases Relevantes para MVP

- **Service ya activado:** `activate_service` debe verificar estado actual y no duplicar
- **Credencial ya existe:** `store_credential` debe actualizar valor sin error
- **Retry con dependencias aún faltantes:** `retry_workflow` debe retornar diagnóstico actualizado
- **Múltiples services requeridos:** Un workflow puede necesitar activar 2+ services
- **Token OAuth expirado:** Usuario debe poder actualizar credencial existente
- **Service no existe en catálogo:** `activate_service` debe validar contra `service_catalog`

### Manejo de Errores

- **Service inválido:** `activate_service` retorna `{"error": "Servicio 'invalid' no existe en el catálogo"}`
- **Credencial faltante en request:** `store_credential` requiere `secret_name` y `secret_value`
- **Task no encontrada:** `retry_workflow` valida existencia y status `resolution_pending`
- **Resolución aún incompleta:** `retry_workflow` retorna estado actual de dependencias faltantes
- **Vault error:** `store_credential` propaga errores de DB como `{"error": "DB connection error"}`

## 2. Diseño Técnico

### Componentes Nuevos

**Tool `activate_service`:**
- **Ubicación:** Agregar a `STATIC_TOOLS` en `src/mcp/tools.py`
- **Input Schema:** `service_id` (string), `secret_names` (array opcional)
- **Handler:** `handle_activate_service` en `src/mcp/handlers.py`
- **Lógica:** Validar service existe en `service_catalog`, upsert a `org_service_integrations` con status `pending_setup`
- **Output:** `{"status": "activated", "service_id": "...", "org_id": "..."}` o error

**Tool `store_credential`:**
- **Ubicación:** Agregar a `STATIC_TOOLS` en `src/mcp/tools.py`
- **Input Schema:** `secret_name` (string), `secret_value` (string)
- **Handler:** `handle_store_credential` en `src/mcp/handlers.py`
- **Lógica:** Llamar `upsert_secret(config.org_id, secret_name, secret_value)`
- **Output:** `{"status": "stored", "secret_name": "...", "message": "..."}`

**Tool `retry_workflow`:**
- **Ubicación:** Agregar a `STATIC_TOOLS` en `src/mcp/tools.py`
- **Input Schema:** `task_id` (string)
- **Handler:** `handle_retry_workflow` en `src/mcp/handlers.py`
- **Lógica:** Recuperar `extracted_definition` de `task.result`, re-ejecutar `resolver.resolve()`, aplicar mapping si ready, continuar con `_persist_template`, `_persist_agents`, `_register_dynamic_flow`
- **Output:** `{"status": "workflow_created", "task_id": "..."}` o diagnóstico de dependencias aún faltantes

### Modificaciones a Componentes Existentes

**`src/flows/architect_flow.py`:**
- **Línea ~180:** Cambiar lógica cuando `not resolution.is_ready`
- **Guardar definición:** `self.state.output_data = {"status": "resolution_required", "extracted_definition": workflow_def.model_dump(), ...}`
- **Marcar pendiente:** `await self._update_task_status("resolution_pending")`
- **Retornar diagnóstico:** Mantener `_build_resolution_response`

**`src/mcp/tools.py`:**
- **Agregar 3 tools a `STATIC_TOOLS`**
- **Agregar mappings en `handlers` dict de `handle_tool_call`**

**`src/mcp/handlers.py`:**
- **Agregar 3 funciones handler async siguiendo patrón existente**

### Interfaces y Modelos de Datos

- **Input activate_service:** `{"service_id": "gmail", "secret_names": ["gmail_oauth_token"]}`
- **Input store_credential:** `{"secret_name": "gmail_oauth_token", "secret_value": "ya29.xxx"}`
- **Input retry_workflow:** `{"task_id": "uuid-de-task"}`
- **Output de tools:** JSON con `status` y datos específicos, o `error`
- **Estado task en DB:** `resolution_pending` con `result` conteniendo `extracted_definition`

### Integraciones

- **IntegrationResolver:** Reutilizar métodos existentes `activate_service`, `store_credential`
- **Vault:** Reutilizar `upsert_secret` para almacenamiento de credenciales
- **DB:** Consultas a `service_catalog`, `tasks`, `org_service_integrations`
- **BaseFlow:** Usar `_update_task_status` para cambiar estado de tarea

Coherente con `estado-fase.md`: usa patrones de resolución existentes, vault write support ya implementado, MCP tools como sistema tools.

## 3. Decisiones

- **CORRECCIÓN (D1):** Mantener separación handlers en `handlers.py` en lugar de `tools.py` — sigue patrón actual del codebase.
- **CORRECCIÓN (D2):** Routing de tools en `handle_tool_call` de `tools.py` — no modificar `server.py` innecesariamente.
- **CORRECCIÓN (D3):** Guardar `extracted_definition` en `state.output_data` antes de marcar `resolution_pending` — permite `retry_workflow` recuperar definición exacta.
- **DECISIÓN (D4):** Usar `config.org_id` en handlers — consistente con patrón MCP actual.
- **DECISIÓN (D5):** Tools retornan JSON simple sin sanitización adicional — siguen patrón `sanitize_output` ya aplicado en `_make_result`.

## 4. Criterios de Aceptación

- ✅ Tool `activate_service` existe en lista de tools MCP y acepta `service_id` requerido
- ✅ Tool `store_credential` existe y requiere `secret_name` + `secret_value`
- ✅ Tool `retry_workflow` existe y requiere `task_id`
- ✅ `activate_service` valida service existe en `service_catalog` antes de activar
- ✅ `store_credential` guarda en vault y nunca retorna el valor en output
- ✅ `retry_workflow` recupera definición de `task.result` y re-ejecuta resolución completa
- ✅ ArchitectFlow marca tarea como `resolution_pending` cuando `is_ready=False`
- ✅ ArchitectFlow guarda `extracted_definition` en `task.result` para retry posterior
- ✅ Workflow se crea exitosamente después de resolver todas las dependencias via tools
- ✅ Tools manejan errores apropiadamente retornando JSON con `error` field
- ✅ Tasks en `resolution_pending` pueden ser consultadas con `get_task` tool
- ✅ Credenciales almacenadas son recuperables por IntegrationResolver para validación

## 5. Riesgos

- **Riesgo Técnico (RT1):** `BaseFlow._update_task_status` no implementado — **estrategia:** verificar implementación en `base_flow.py`, implementar si falta siguiendo patrón de `create_task_record`.
- **Riesgo de Integración (RI1):** `retry_workflow` debe acceder `extracted_definition` de DB — **estrategia:** verificar que `task.result` se persiste correctamente en `BaseFlow.complete()`.
- **Riesgo de Seguridad (RS1):** Credenciales en logs si `store_credential` handler no maneja excepciones — **estrategia:** usar `sanitize_output` en responses, nunca loggear `secret_value`.
- **Riesgo para Pasos Futuros (RF1):** Cambio de `completed` a `resolution_pending` puede afectar flujos que esperan `completed` — **estrategia:** verificar dependencias de `task.status` en codebase con `grep -r "status.*completed"`.

## 6. Plan

| Tarea | Complejidad | Tiempo Estimado | Dependencias |
|-------|-------------|-----------------|--------------|
| Agregar 3 tools a STATIC_TOOLS en tools.py | Baja | 15min | Ninguna |
| Implementar handle_activate_service en handlers.py | Media | 30min | IntegrationResolver.activate_service |
| Implementar handle_store_credential en handlers.py | Baja | 20min | vault.upsert_secret |
| Implementar handle_retry_workflow en handlers.py | Alta | 1h | ArchitectFlow lógica completa |
| Agregar mappings en handle_tool_call de tools.py | Baja | 10min | Handlers implementados |
| Modificar ArchitectFlow para resolution_pending | Media | 45min | BaseFlow._update_task_status |
| Verificar _update_task_status existe en BaseFlow | Baja | 15min | Ninguna |
| Tests básicos de tools MCP | Media | 1h | Implementación completa |
| **Total** | **Alta** | **~4.5h** | **Secuencial** |

## 🔮 Roadmap

- **Optimización Performance:** Cache de catálogo de services en IntegrationResolver para evitar DB queries repetidas
- **Validación Avanzada:** Verificar formato de tokens OAuth antes de almacenar
- **UI Dashboard:** Interfaz para activar services y configurar credenciales sin MCP
- **Auditoría:** Logs de activación de services y cambios de credenciales para compliance
- **Retry Automático:** Detección automática de credenciales expiradas y solicitud de refresh
- **Pre-requisito para Sprint 5.2:** Tools MCP funcionales requeridas para testing de búsqueda externa
- **Pre-requisito para Sprint 5.4:** Estado `resolution_pending` debe ser soportado en UI de tasks</content>
<parameter name="filePath">LAST/analisis-kilo.md