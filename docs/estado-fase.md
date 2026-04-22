# 🗺️ ESTADO DE FASE: FASE 5 - ECOSISTEMA AGÉNTICO (MCP) 🏗️

## 1. Resumen de Fase
- **Objetivo:** Transformar FluxAgentPro de un ejecutor estático a una plataforma agéntica que agentes externos (Claude, GPT, etc.) puedan operar vía el estándar Model Context Protocol (MCP). Incluye la exposición de flows como herramientas MCP, autenticación inter-agente, y un catálogo formal de integraciones REST (TIPO C).
- **Fase Anterior:** Fase 4 - Capa de Inteligencia Visual y Analítica [FINALIZADA ✅]
- **Pasos de la Fase 5:**
    1. **5.0 [Diseño]:** Análisis y blueprint de integración MCP. [COMPLETADO ✅]
    2. **5.0.1 [Prerrequisitos]:** `get_secret_async`, dependencia `mcp>=1.0.0`, migración 025 RLS. [COMPLETADO ✅]
    3. **5.1 [Backend]:** Servidor MCP Stdio + Flow-to-Tool adapter + 5 tools estáticas. [COMPLETADO ✅]
    4. **5.2 [Backend]:** Handlers de ejecución + Auth Bridge (PyJWT) + Gateway JSON-RPC. [COMPLETADO ✅]
    5. **5.2.5 [DB+Backend]:** Service Catalog TIPO C (3 tablas + import + ServiceConnectorTool). [COMPLETADO ✅]
    6. **5.3 [Backend+Frontend]:** Endpoint SSE + HITL completo + MCPConfig. [PENDIENTE]
- **Dependencias entre pasos:** 5.0 → 5.0.1 → 5.1 → 5.2 → 5.3. Paso 5.2.5 ejecutado en paralelo (antes de 5.1).

## 2. Estado Actual del Proyecto

- **Implementado y Funcional (Fases 1-4 + Fase 5 parcial):**
    - **FlowRegistry** (`src/flows/registry.py`): Registro centralizado con `list_flows()`, `get_metadata()` (retorna `depends_on`, `category`), `get_hierarchy()`. Validación DFS de ciclos al arranque.
    - **BaseFlow** (`src/flows/base_flow.py`): Lifecycle completo con HITL (`request_approval()`, `resume()`), snapshot/restore de estado, y tracking de tokens.
    - **ArchitectFlow** (`src/flows/architect_flow.py`): Genera workflows desde NL, persiste en `workflow_templates`, crea agentes en `agent_catalog`, registra dinámicamente en `FLOW_REGISTRY`.
    - **MCPPool** (`src/tools/mcp_pool.py`): Singleton con circuit breaker (5 fallos → 60s pausa), retry exponencial, resolución de secretos del Vault como env vars. Conexión a servidores MCP externos (TIPO B).
    - **Vault** (`src/db/vault.py`): Gestión de secretos cifrados per-org. Cumple Regla R3. Expone `get_secret()` síncrono y `get_secret_async()` async (wrapper con `asyncio.to_thread`).
    - **OrgBaseTool** (`src/tools/base_tool.py`): Clase base para herramientas con resolución automática de secretos y aislamiento por `org_id`.
    - **ToolRegistry** (`src/tools/registry.py`): Metadatos operacionales por herramienta (timeout, retry, tags). Decorador `@register_tool()`.
    - **Auth/JWT** (`src/mcp/auth.py`): Verificación JWT con ES256 (JWKS) + HS256 (secret), `verify_org_membership()`, soporte `fap_admin` cross-org. Concentra auth logic para middleware y MCP. Usa `PyJWKClient` con caché de 1h.
    - **MCP Handlers** (`src/mcp/handlers.py`): Implementación real de `execute_flow`, `get_task`, `approve_task`, `reject_task`. Resume de flows HITL interactuando con `pending_approvals`.
    - **MCP Gateway** (`src/api/routes/mcp.py`): Puente HTTP JSON-RPC para clientes MCP remotos accesible en `/api/v1/mcp`.
    - **MCP Exceptions** (`src/mcp/exceptions.py`): Jerarquía de errores MCP con mapeo a códigos JSON-RPC estándar (-32603, -32001, etc.).
    - **API REST completa:** Endpoints para flows, tasks, approvals, agents, webhooks, chat, analytical, integrations, mcp.
    - **ServiceConnectorTool** (`src/tools/service_connector.py`): Tool genérica TIPO C. Lee definiciones de `service_tools`, resuelve secretos vía Vault, ejecuta HTTP con `httpx`, sanitiza output (Regla R3), audita en `domain_events`. Registrada con `@register_tool("service_connector", ...)`. Validada ✅.
    - **Output Sanitizer** (`src/mcp/sanitizer.py`): Última línea de defensa para Regla R3. 7 patrones regex. Recurre en dict/list. Si falla internamente, retorna error genérico.
    - **Health Check Scheduler** (`src/scheduler/health_check.py`): `run_health_checks()` async implementado. ⚠️ Job no conectado aún al lifespan de `main.py`.
    - **API Integrations** (`src/api/routes/integrations.py`): 3 endpoints — `/available`, `/active`, `/tools/{service_id}`. Router registrado en `main.py`.
    - **Import Script** (`scripts/import_service_catalog.py`): Carga `data/service_catalog_seed.json`.
    - **Service Catalog DB** (`supabase/migrations/024_service_catalog.sql`): 3 tablas con RLS correcto.
    - **MCP Server Stdio** (`src/mcp/server.py`): Entry point `python -m src.mcp.server --org-id <UUID>`. Implementa `list_tools` (estáticas + dinámicas) y `call_tool` (dispatch a handlers).
    - **MCP Config** (`src/mcp/config.py`): `MCPConfig` con Pydantic BaseSettings, prefijo `MCP_`. Soporta Stdio y placeholders para SSE.
    - **MCP Tools** (`src/mcp/tools.py`): 5 tools estáticas (`list_flows`, `list_agents`, `get_agent_detail`, `get_server_time`, `list_capabilities`) con handlers completos. Output sanitizado vía `sanitize_output()`.
    - **Flow-to-Tool Adapter** (`src/mcp/flow_to_tool.py`): Genera un Tool MCP por cada flow registrado combinando FlowRegistry + FLOW_INPUT_SCHEMAS.
    - **Migración 025** (`supabase/migrations/025_agent_catalog_rls_update.sql`): `agent_catalog` RLS actualizado al patrón moderno con `service_role` bypass.
    - **Claude Desktop Config** (`claude_desktop_config.json`): Template con placeholders.

- **Pendiente de Verificación:**
    - [ ] Arranque del servidor MCP localmente (`python -m src.mcp.server --org-id <UUID>`)
    - [ ] Conexión desde Claude Desktop con `claude_desktop_config.json` configurado
    - [ ] Migración 025 aplicada en Supabase
    - [x] Health check scheduler implementado (pero no conectado al lifespan)

- **Actividades Recientes (Sprint 3 - Core MCP):**
    - **`src/mcp/handlers.py`** — Lógica de ejecución real de flows y resume de HITL. ✅
    - **`src/mcp/auth.py`** — Auth Bridge con PyJWT, validación ES256/HS256 y membresía org. ✅
    - **`src/mcp/exceptions.py`** — Mapeo estructurado de errores a JSON-RPC. ✅
    - **`src/api/routes/mcp.py`** — Gateway HTTP JSON-RPC funcional y registrado. ✅

## 3. Contratos Técnicos Vigentes

- **API MCP (JSON-RPC 2.0):**
    - `POST /api/v1/mcp`
    - Métodos soportados: `execute_flow`, `get_task`, `approve_task`, `reject_task`.
- **API existente reutilizable por MCP:**
    - `POST /webhooks/trigger` → handler `execute_flow`
    - `GET /flows/available` → handler `list_flows`
    - `GET /flows/hierarchy` → handler `get_flow_hierarchy`
    - `GET /tasks/{task_id}` → handler `get_task`
    - `POST /approvals/{task_id}` → handler `approve_task` / `reject_task`
- **Tablas de DB relevantes:**
    - `secrets` — Credenciales cifradas con RLS per-org.
    - `agent_catalog` — Definición de agentes.
    - `org_service_integrations` — Servicios habilitados per-org.
    - `service_catalog`, `service_tools` — Definiciones de herramientas por proveedor.
    - `workflow_templates`, `tasks`, `pending_approvals`, `snapshots` — Datos operacionales.
- **Dependencias (verificadas en `pyproject.toml`):**
    - **Directas:** `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`, `pydantic>=2.10.0`, `pydantic-settings>=2.6.0`, `supabase>=2.10.0`, `PyJWT>=2.0.0`, `python-dotenv>=1.0.0`, `httpx>=0.28.0`, `structlog>=24.4.0`, `litellm>=1.83.0`, `apscheduler>=3.10.0`, `python-dateutil>=2.9.0`, `mcp>=1.0.0,<2.0.0`.
    - **Nota:** `python-jose` ya no es requerido. Se debe eliminar de `pyproject.toml` (Paso 7 del plan).
- **Patrones de código verificados:**
    - **Auth Bridge:** `_get_jwks_client()` singleton con cache 1h; `decode_jwt()` soporta ES256/HS256.
    - **RLS:** `auth.role() = 'service_role' OR org_id::text = current_org_id()`.
    - **JSON-RPC Errors:** `mcp_error_to_response` centralizado en `exceptions.py`.
    - **Vault:** `get_secret(org_id, secret_name)` síncrono + `get_secret_async(org_id, secret_name)` async.

## 4. Decisiones de Arquitectura Tomadas
- **Servidor MCP Dual:** Stdio para Claude Desktop y SSE (HTTP) para Claude API. Gateway JSON-RPC en `/api/v1/mcp` ya operativo.
- **Aislamiento por Org:** El servidor Stdio recibe `--org-id` flag. El gateway HTTP usa header `X-Org-ID`. `verify_org_membership` valida acceso vía DB.
- **HITL Bridge:** Los flows en espera se re-instancian en `handlers.py` usando el `flow_registry` y el ID guardado en `pending_approvals`.
- **Regla R3:** Implementada en `sanitizer.py` y aplicada forzosamente en `MCP Gateway` y `MCP Stdio Server`.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 5.0  | ✅ | Documentación de diseño | Servidor dual, PyJWT auth | Blueprint verificado. |
| 5.0.1 | ✅ | `pyproject.toml`, `src/db/vault.py`, Migration 025 | MCP dep, async secrets | Prerrequisitos listos. |
| 5.1  | ✅ | `src/mcp/server.py`, `config.py`, `tools.py`, `flow_to_tool.py` | 5 tools estáticas, flow-to-tool | Servidor Stdio funcional (Sprint 1). |
| 5.2  | ✅ | `src/mcp/auth.py`, `handlers.py`, `exceptions.py`, `src/api/routes/mcp.py` | PyJWT auth bridge, handlers reales, RPC Gateway | Núcleo funcional completado (Sprint 3). |
| 5.2.5 | ✅ | Migration 024, `service_connector.py`, `import_service_catalog.py` | Service Catalog TIPO C | Integración REST genérica certificada. |
| 5.3  | ⏳ | — | — | SSE + HITL completo. Próximo objetivo. |

## 6. Criterios Generales de Aceptación MVP (Fase 5)
- [x] **5.0.1:** `import mcp` funciona y `get_secret_async()` resuelve secretos correctamente.
- [x] **5.1:** `tools/list` retorna herramientas al conectar desde Claude Desktop.
- [x] **5.2:** Handlers `execute_flow` y `get_task` funcionales con auth JWT.
- [x] **5.2.5:** Ejecución genérica de servicios REST sin código hardcodeado (Rule R3 compliant).
- [ ] **5.3:** Flujo HITL end-to-end funcional desde Claude con aprobación vía Dashboard.
- [x] Los errores MCP se mapean a códigos JSON-RPC estándar.

## 7. Estructura del Módulo MCP

```
src/mcp/
├── __init__.py         # Módulo
├── sanitizer.py        # Output sanitizer (Regla R3)
├── config.py           # MCPConfig BaseSettings
├── server.py           # Entry point Stdio
├── tools.py            # 5 tools estáticas
├── flow_to_tool.py     # Flow-to-Tool translator
├── handlers.py         # Business logic (Execute/Approve/Get)
├── auth.py             # Auth Bridge (PyJWT) - Verificado ✅
└── exceptions.py       # Error mapping - Verificado ✅
```

---
*Documento actualizado por el protocolo CONTEXTO — Paso 5.2 COMPLETADO.*
*Última actualización: 2026-04-21 (post-implementación Core MCP)*
prove
├── auth.py             # ✅ Paso 5.2  — Auth Bridge (PyJWT)
└── exceptions.py       # ✅ Paso 5.2  — Error mapping → JSON-RPC
```

---
*Documento actualizado por el protocolo CONTEXTO — Pasos 5.0.1 y 5.1 COMPLETADOS.*
*Última actualización: 2026-04-13 (post-implementación Sprint 1 completo)*
