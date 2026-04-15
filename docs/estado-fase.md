# 📝 ESTADO DE FASE: EXPANSIÓN (Sprint 5 — EN CURSO)

## 1. Resumen de Fase
- **Objetivo:** Fortalecer el **Ecosistema Agéntico MCP** mediante la resolución de herramientas reales, persistencia de secretos y autenticación robusta.
- **Lista de Pasos (Sprint 5):**
  1. **IntegrationResolver:** Validación y mapeo de tools alucinadas contra el catálogo real (COMPLETADO).
  2. **MCPRegistryClient:** Descubrimiento de servidores MCP en registros externos (COMPLETADO).
  3. **Auth PIN MCP:** Generación y validación de PIN para emparejamiento (COMPLETADO).
  4. **Internal Onboarding Tools:** MCP Tools para activar servicios y cargar credenciales (COMPLETADO).
  5. **Multi-agent Crew Resolution:** Soporte para resolución de dependencias en workflows complejos (EN CURSO).
- **Dependencias:**
  - Sprint 4 ✅ (SSE + HITL OK).
  - Integración MCP completa requiere los pasos 1-4.

## 2. Estado Actual del Proyecto

- **Qué ya está implementado y funcional:**
  - **IntegrationResolver:** Clase `src/flows/integration_resolver.py` que realiza matching fuzzy y validación de activación/secretos.
  - **MCPRegistryClient:** Clase `src/mcp/registry_client.py` que consulta el GitHub MCP Registry de forma estática.
  - **Auth PIN MCP:** Endpoint `/api/v1/mcp/generate-pin` funcional con persistencia en Vault.
  - **Internal Onboarding Tools:** 3 herramientas MCP (`activate_service`, `store_credential`, `retry_workflow`) en `src/mcp/tools.py` que permiten cerrar el ciclo de onboarding desde el chat.
  - **Resolution Pending Flow:** `ArchitectFlow` pausa y guarda `extracted_definition` en `tasks.result` cuando faltan dependencias (status `resolution_pending`).
  - **Vault Write Support:** Funciones `upsert_secret` y `list_secrets` en `src/db/vault.py` operativas.

- **Qué está parcialmente implementado:**
  - **Workflow Validation:** Validación de schemas en agent definitions básica.
  - **Dynamic Flow Lifecycle:** Re-resolución en `retry_workflow` funcional pero limitada a ejecuciones simples (no multi-step complejo aún).

- **Qué no existe aún:**
  - **Streaming de Tokens LLM vía SSE.**
  - **Tool cancel_workflow** para abortar tareas en `resolution_pending`.

- **Discrepancias plan vs código:**
  - 📝 **CORRECCIÓN:** El plan sugería `activate_service` con `secrets`; el código separa `activate_service` de `store_credential` para mayor seguridad y simplicidad.
  - 📝 **CORRECCIÓN:** `retry_workflow` restaura el estado y el `EventStore` de la tarea original para mantener la trazabilidad.

## 3. Contratos Técnicos Vigentes

- **Modelos de Datos (Supabase):**
  - Tabla `tasks`: Columna `result` almacena `extracted_definition` para retries.
  - Tablas `org_service_integrations` / `snapshots`.

- **Interfaces de Código Nuevas:**
  - `IntegrationResolver.activate_service(service_id)` -> `None`.
  - `IntegrationResolver.store_credential(name, value)` -> `None`.
  - `ArchitectFlow.state.resolution_pending()` -> Transiciona a status `resolution_pending`.

- **Patrones de Código en Uso:**
  - **Pattern Pause-and-Retry:** El flujo se detiene en validación técnica, se guarda la definición y se reanuda vía tool externa (`retry_workflow`).
  - **Pattern Private Handlers:** Handlers de tools MCP como funciones privadas `_handle_*` en `tools.py`.

## 4. Decisiones de Arquitectura Tomadas
- **Aislamiento de Secretos:** `store_credential` nunca retorna el valor del secreto al LLM ni al usuario tras guardarlo.
- **Persistencia de Definición:** La definición del workflow se persiste como resultado de la tarea original para evitar pérdida de contexto en el reintento.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| Sprint 5.1 | ✅ | `integration_resolver.py` | Matching fuzzy | Paso 1 |
| Sprint 5.2 | ✅ | `registry_client.py` | Búsqueda externa segura | Paso 2 |
| Sprint 5.3 | ✅ | `server_sse.py`, `vault.py` | Auth PIN | Paso 3 |
| Sprint 5.4 | ✅ | `tools.py`, `architect_flow.py`, `state.py` | Tools Onboarding e HITL técnico | Ciclo completo OK |

## 6. Criterios Generales de Aceptación MVP
- Happy path de creación de workflows (Architect -> Pause -> Store -> Activate -> Retry -> Success) verificado.
- Resolución de herramientas alucinadas local y global operativa.
- Secretos cifrados en Vault.

