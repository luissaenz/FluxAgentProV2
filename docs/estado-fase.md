# 📝 ESTADO DE FASE: EXPANSIÓN (Sprint 5 — EN CURSO)

## 1. Resumen de Fase
- **Objetivo:** Fortalecer el **Ecosistema Agéntico MCP** mediante la resolución de herramientas reales, persistencia de secretos y autenticación robusta.
- **Lista de Pasos (Sprint 5):**
  1. **IntegrationResolver:** Validación y mapeo de tools alucinadas contra el catálogo real (COMPLETADO).
  2. **MCPRegistryClient:** Descubrimiento de servidores MCP en registros externos (COMPLETADO).
  3. **Auth PIN MCP:** Generación y validación de PIN para emparejamiento Claude-Dashboard (COMPLETADO).
  4. **Multi-agent Crew Resolution:** Soporte para resolución de dependencias en workflows de múltiples agentes (EN CURSO).
- **Dependencias:**
  - Sprint 4 ✅ (SSE + HITL OK).
  - Sprint 5.1 ✅ (Resolver Core OK).
  - Sprint 5.2 ✅ (External Discovery OK).
  - Sprint 5.3 ✅ (Auth PIN OK).

## 2. Estado Actual del Proyecto

- **Qué ya está implementado y funcional:**
  - **IntegrationResolver:** Clase `src/flows/integration_resolver.py` que realiza matching fuzzy de tools.
  - **MCPRegistryClient:** Clase `src/mcp/registry_client.py` que consulta el GitHub MCP Registry y parsea herramientas desde READMEs de forma segura (sin ejecución).
  - **Auth PIN MCP:** Endpoint `/api/v1/mcp/generate-pin` en `src/mcp/server_sse.py` funcional. Genera tokens seguros de 16 bytes y los persiste en Vault.
  - **Vault Write Support:** Función `upsert_secret` en `src/db/vault.py` y políticas RLS operativas.
  - **Inyección de Catálogo:** `ArchitectFlow` inyecta tools reales en el prompt del LLM.
  - **Búsqueda Externa en ArchitectFlow:** Si el resolver no encuentra una tool, el flow busca en el registro global y ofrece opciones de importación al usuario.

- **Qué está parcialmente implementado:**
  - **Workflow Validation:** Validación de schemas en agent definitions (Base funcional, falta rigurosidad en tipos complejos).

- **Qué no existe aún:**
  - **Streaming de Tokens LLM vía SSE:** En el roadmap.
  - **Observabilidad MCP:** Trazas JSON-RPC pendientes.

- **Discrepancias plan vs código:**
  - 📝 **CORRECCIÓN:** El plan original sugería activación por herramienta; el código implementa **activación por servicio** (modelo de datos vigente).
  - 📝 **CORRECCIÓN (D1):** `discover_tools` NO ejecuta servidores externos por seguridad; usa parseo estático de documentación.
  - 📝 **CORRECCIÓN (D2):** El endpoint de PIN reside en `server_sse.py` para compartir contexto de transporte, no en una ruta de auth separada.

## 3. Contratos Técnicos Vigentes

- **Modelos de Datos (Supabase):**
  - Tabla `org_mcp_servers`: Destino para importaciones de servidores Tipo B.
  - Tablas `service_catalog` / `service_tools`: Destino para importaciones Tipo C.

- **Interfaces de Código Nuevas:**
  - `IntegrationResolver.resolve(workflow_def)` -> `ResolutionResult`.
  - `MCPRegistryClient.search(query)` -> `list[MCPServerInfo]`.
  - `MCPRegistryClient.discover_tools(server)` -> `list[dict]`.
  - `upsert_secret(org_id, name, value)`.

- **Patrones de Código en Uso:**
  - **Pattern Discovery-Import:** Búsqueda externa gatillada por fallos en la resolución local.
  - **Pattern Safe Parsing:** Extracción de metadatos mediante regex sobre contenido markdown/raw de GitHub.

## 4. Decisiones de Arquitectura Tomadas
- **Bloqueo Preventivo:** Prohibido crear workflows con tools `not_found`.
- **Importación Inactiva:** Servidores importados nacen con `is_active: False` para requerir configuración manual del admin.
- **Seguridad de Descubrimiento:** Priorizar el parseo de README sobre la ejecución `tools/list` para servidores no confiables.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| Sprint 4 | ✅ | `middleware.py`, `server_sse.py` | Transporte SSE y HITL | Claude Web OK |
| Sprint 5.1 | ✅ | `integration_resolver.py`, `vault.py`, `architect_flow.py` | Matching fuzzy y Vault write | Paso 1 del plan |
| Sprint 5.2 | ✅ | `registry_client.py`, `architect_flow.py` | Búsqueda externa segura | Paso 2 del plan |
| Sprint 5.3 | ✅ | `server_sse.py`, `vault.py` | Generación de PIN y persistencia en Vault | Endpoint `/generate-pin` |

## 6. Criterios Generales de Aceptación MVP
- Happy path de creación de workflows con tools reales verificado.
- Resolución de herramientas alucinadas (local + global) funcional.
- Secretos almacenables y recuperables.
