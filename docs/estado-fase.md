# 🗺️ ESTADO DE FASE: FASE 5 - ECOSISTEMA AGÉNTICO (MCP) 🏗️

## 1. Resumen de Fase
- **Objetivo:** Transformar FluxAgentPro de un ejecutor estático a una plataforma agéntica que agentes externos (Claude, GPT, etc.) puedan operar vía el estándar Model Context Protocol (MCP). Incluye la exposición de flows como herramientas MCP, autenticación inter-agente, y un catálogo formal de integraciones REST (TIPO C).
- **Fase Anterior:** Fase 4 - Capa de Inteligencia Visual y Analítica [FINALIZADA ✅]
- **Pasos de la Fase 5:**
    1. **5.0 [Diseño]:** Análisis y blueprint de integración MCP. [COMPLETADO ✅]
    2. **5.0.1 [Prerrequisitos]:** `get_secret_async`, dependencia `mcp>=1.0.0`, enriquecer FlowRegistry. [EN PROGRESO 🚧]
    3. **5.1 [Backend]:** Servidor MCP Stdio + Flow-to-Tool adapter. [PENDIENTE]
    4. **5.2 [Backend]:** Handlers de ejecución + Auth Bridge (PyJWT). [PENDIENTE]
    5. **5.2.5 [DB+Backend]:** Service Catalog TIPO C (3 tablas + import + ServiceConnectorTool). [COMPLETADO ✅]
    6. **5.3 [Backend+Frontend]:** Endpoint SSE + HITL completo + MCPConfig. [PENDIENTE]
- **Dependencias entre pasos:** 5.0 → 5.0.1 → 5.1 → 5.2 → 5.2.5 (puede ir en paralelo con 5.2) → 5.3

## 2. Estado Actual del Proyecto

- **Implementado y Funcional (heredado de Fases 1-4 + Parcial 5.0.1):**
    - **FlowRegistry** (`src/flows/registry.py`): Registro centralizado con `list_flows()`, `get_metadata()` (retorna `depends_on`, `category`), `get_hierarchy()`. Validación DFS de ciclos al arranque. ✅ Verificado.
    - **Dependencia `mcp>=1.0.0`** (`pyproject.toml`): Agregada como dependencia directa. ✅ Verificado.
    - **Migración 025** (`supabase/migrations/025_agent_catalog_rls_update.sql`): RLS de `agent_catalog` actualizado al patrón moderno con bypass de `service_role`. ✅ Verificado.
    - **BaseFlow** (`src/flows/base_flow.py`): Lifecycle completo con HITL.
    - **ArchitectFlow** (`src/flows/architect_flow.py`): Generación de workflows dinámicos.
    - **MCPPool** (`src/tools/mcp_pool.py`): Singleton con circuit breaker y resolución de secretos.
    - **Vault** (`src/db/vault.py`): Gestión de secretos per-org. Solo expone `get_secret()` síncrono.
    - **Auth/JWT** (`src/api/middleware.py`): Verificación JWT con PyJWT.
    - **ServiceConnectorTool** (`src/tools/service_connector.py`): Tool genérica TIPO C validada.
    - **Output Sanitizer** (`src/mcp/sanitizer.py`): Sanitización de secretos Regla R3.
    - **API Integrations** (`src/api/routes/integrations.py`): Catálogo y gestión de integraciones REST.
    - **Service Catalog DB** (`supabase/migrations/024_service_catalog.sql`): Tablas `service_catalog`, `org_service_integrations`, `service_tools`.

- **Parcialmente Implementado / Con Errores:**
    - **`get_secret_async`:** 🛑 **BUG CRÍTICO DETECTADO.** `mcp_pool.py:26` intenta importar `get_secret_async` de `vault.py`, pero la función NO existe en `vault.py`. Esto causa un `ImportError`. Debe implementarse el wrapper async.
    - **`FlowRegistry` Enrichment:** Aunque soporta `category` y `depends_on`, aún no integra `input_schema`.
    - **`FLOW_INPUT_SCHEMAS`:** Localizado en `src/api/routes/flows.py:72`. Actualmente es un diccionario VACÍO (post-desacople de NOA). Debe ser el insumo para enriquecer el Registry.

- **No Existe Aún:**
    - **Servidor MCP Core** (`src/mcp/server.py`, `handlers.py`, etc.): El directorio existe pero los archivos del servidor están pendientes.
    - **Health Check Scheduler Job:** Definido en `src/scheduler/health_check.py` pero no registrado en el lifespan de la app.

## 3. Contratos Técnicos Vigentes

- **API existente reutilizable por MCP:**
    - `POST /webhooks/trigger` → execution flow.
    - `GET /flows/available`, `GET /flows/hierarchy`.
    - `POST /flows/{flow_type}/run`.
- **Tablas de DB relevantes:**
    - `secrets`, `agent_catalog` (RLS mig025 ✅), `org_service_integrations` (RLS mig024 ✅), `domain_events`.
- **Dependencias (verificadas en `pyproject.toml`):**
    - `fastapi`, `supabase`, `anthropic`, `openai`, `mcp>=1.0.0` (Directa ✅), `pyjwt`, `httpx`, `apscheduler`.
    - ⚠️ `python-jose` sigue en deps pero el código usa `pyjwt`. Se mantiene por compatibilidad legacy.
- **Patrones de código verificados:**
    - **RLS:** `auth.role() = 'service_role' OR org_id::text = current_org_id()`.
    - **Tool Registry:** Decorador `@register_tool`.
    - **Auth:** Middleware `verify_org_membership` y `require_org_id`.

## 4. Decisiones de Arquitectura Tomadas
- **Aseguramiento de Regla R3 (Sanitizer):** Implementación de `sanitizer.py` como middleware de salida para cualquier agente externo.
- **Desacople de Bartenders NOA:** Remoción de schemas específicos del core para permitir un `FLOW_INPUT_SCHEMAS` dinámico o vía Registry.
- **Consistencia de RLS:** Migración 025 estandariza `agent_catalog` con el resto del ecosistema (service_role bypass).
- **Correcciones al plan:** Se prioriza la corrección del `ImportError` en `get_secret_async` como primer paso del Sprint 1.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 5.0  | ✅ | `LAST/mcp-analisis-final-v3.mcp` | Servidor dual, PyJWT auth | Blueprint v3.3 verificado. |
| 5.0.1 | 🚧 | `pyproject.toml`, `mig025` | `mcp` como dep directa | Deps y DB Listos. Pendiente `get_secret_async` (Error import) y enriquecer Registry. |
| 5.2.5 | ✅ | `mig024`, `service_connector.py`, `integrations.py` | TIPO C con httpx y RLS moderno | 100% funcional y validado. |
| 4.5  | ✅ | `test_4_5_precision.py` | Golden Set Validation | Precisión certificada. |

## 6. Criterios Generales de Aceptación MVP (Fase 5)
- [ ] **5.0.1:** `get_secret_async()` resuelve secretos correctamente y Registry expone schemas.
- [ ] **5.1:** `tools/list` funciona desde Claude Desktop.
- [ ] **5.2:** Claude ejecuta un flow end-to-end.
- [ ] **5.3:** HITL funcional desde Claude.
- [ ] Los errores MCP se mapean a códigos JSON-RPC estándar sin exponer internals.
- [ ] La Regla R3 se mantiene en todas las respuestas al agente externo (sanitizer activo).

---
*Documento actualizado por el protocolo CONTEXTO — Paso 5.0.1 EN PROGRESO.*
*Última actualización: 2026-04-14 (post-reconocimiento parcial 5.0.1)*
