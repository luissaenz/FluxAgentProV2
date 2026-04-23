# 🗺️ ESTADO DE FASE: FASE 5 - ECOSISTEMA AGÉNTICO (MCP) 🏗️

## 1. Resumen de Fase
- **Objetivo:** Transformar FluxAgentPro de un ejecutor estático a una plataforma agéntica que agentes externos (Claude, GPT, etc.) puedan operar vía el estándar Model Context Protocol (MCP). Incluye la exposición de flows como herramientas MCP, autenticación inter-agente, y un catálogo formal de integraciones REST (TIPO C).
- **Fase Anterior:** Fase 4 - Capa de Inteligencia Visual y Analítica [FINALIZADA ✅]
- **Pasos de la Fase 5:**
    1. **5.0 [Diseño]:** Análisis y blueprint de integración MCP. [COMPLETADO ✅]
    2. **5.0.1 [Prerrequisitos]:** `get_secret_async`, dependencia `mcp>=1.0.0`, migración 025 RLS. [COMPLETADO ✅]
    3. **5.1 [Backend]:** Servidor MCP Stdio + Flow-to-Tool adapter + 5 tools estáticas. [COMPLETADO ✅]
    4. **5.2 [Backend]:** Handlers de ejecución + Auth Bridge (PyJWT) + Gateway JSON-RPC. [COMPLETADO ✅]
    5. **5.2.1 [Backend]:** Excepciones MCP (Normalización, Logging y Sanitización R3). [COMPLETADO ✅]
    6. **5.2.5 [DB+Backend]:** Service Catalog TIPO C (3 tablas + import + ServiceConnectorTool). [COMPLETADO ✅]
    7. **5.3 [Backend+Frontend]:** Endpoint SSE + Handshake MCP + Connection Manager + Health Check Lifespan. [COMPLETADO ✅]
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
    - **MCP Exceptions** (`src/mcp/exceptions.py`): Jerarquía robusta de errores MCP normalizada a JSON-RPC 2.0. Incluye logging estratégico para errores internos (-32603) y sanitización automática de mensajes hacia el cliente (Regla R3).
    - **API REST completa:** Endpoints para flows, tasks, approvals, agents, webhooks, chat, analytical, integrations, mcp.
    - **ServiceConnectorTool** (`src/tools/service_connector.py`): Tool genérica TIPO C. Lee definiciones de `service_tools`, resuelve secretos vía Vault, ejecuta HTTP con `httpx`, sanitiza output (Regla R3), audita en `domain_events`. Registrada con `@register_tool("service_connector", ...)`. Validada ✅.
    - **Output Sanitizer** (`src/mcp/sanitizer.py`): Última línea de defensa para Regla R3. 7 patrones regex. Recurre en dict/list. Si falla internamente, retorna error genérico.
    - **Health Check Scheduler** (`src/scheduler/health_check.py`): Monitoreo asíncrono de salud. Conectado exitosamente al lifespan de `main.py` (arranca en background al iniciar la API). ✅.
    - **SSE Connection Manager** (`src/mcp/sse.py`): Gestor Singleton de colas de eventos asíncronos con aislamiento por `org_id`. Soporta broadcast de cambios de estado en tareas. ✅.
    - **API Integrations** (`src/api/routes/integrations.py`): 3 endpoints — `/available`, `/active`, `/tools/{service_id}`. Router registrado en `main.py`.
    - **Import Script** (`scripts/import_service_catalog.py`): Automatiza la carga del catálogo global con validación de integridad (proveedores ≥ 15, perfiles completos). ✅.
    - **Seed File** (`data/service_catalog_seed.json`): Catálogo robusto con 216 herramientas de 90 proveedores (GitHub, Stripe, Slack, etc.). Validado sintácticamente. ✅.
    - **Service Catalog Documentation** (`docs/service_catalog.md`): Guía técnica sobre el formato del catálogo, resolución de secretos y extensión de herramientas TIPO C. ✅.
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
    - **Actividades Recientes (Sprint 3 - Handlers Productivos):**
    - **`src/mcp/handlers.py`** — Lógica de ejecución real de flows y resume de HITL. Validado ✅.
    - **`src/mcp/tools.py`** — Conexión real de flows y herramientas `get_task`, `approve_task`, `reject_task`. Validado ✅.
    - **`docs/api_mcp.md`** — Documentación técnica de la API MCP. ✅.
    - **`tests/integration/test_mcp_handlers.py`** — Suite de tests de integración (4/4 passed). ✅.

## 3. Contratos Técnicos Vigentes

- **API MCP (JSON-RPC 2.0):**
    - `POST /api/v1/mcp` (Gateway HTTP)
    - Herramientas Stdio: `list_flows`, `[flow_name]`, `get_task`, `approve_task`, `reject_task`, `list_agents`, `get_agent_detail`, `get_server_time`, `list_capabilities`.
- **API existente reutilizable por MCP:**
    - `POST /webhooks/trigger` → handler `execute_flow`
    - `GET /flows/available` → handler `list_flows`
    - `GET /tasks/{task_id}` → handler `get_task` (vía snapshots)
    - `POST /approvals/{task_id}` → handler `approve_task` / `reject_task`
- **Tablas de DB relevantes:**
    - `secrets` — Credenciales cifradas con RLS per-org.
    - `tasks`, `snapshots`, `pending_approvals` — Datos operacionales de ejecución y HITL.
- **Dependencias (verificadas en `pyproject.toml`):**
    - **Directas:** `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`, `pydantic>=2.10.0`, `pydantic-settings>=2.6.0`, `supabase>=2.10.0`, `PyJWT>=2.0.0`, `httpx>=0.28.0`, `mcp>=1.0.0`.
- **Patrones de código verificados:**
    - **HITL:** Uso de `request_approval()` en flows y `resume()` en handlers.
    - **State Source:** `snapshots` como fuente de verdad para `get_task`.
    - **Auth Bridge:** `verify_org_membership` centralizado para Stdio y HTTP.

## 4. Decisiones de Arquitectura Tomadas
- **Conexión Real Stdio:** El servidor Stdio ya no usa placeholders; despacha ejecuciones reales a través de `handle_execute_flow`.
- **Aislamiento por Org:** El servidor Stdio recibe `--org-id` flag. El gateway HTTP usa header `X-Org-ID`.
- **Regla R3:** Implementada en `sanitizer.py` y aplicada forzosamente en todos los handlers de herramientas.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 5.0  | ✅ | Documentación de diseño | Servidor dual, PyJWT auth | Blueprint verificado. |
| 5.0.1 | ✅ | `pyproject.toml`, `src/db/vault.py` | MCP dep, async secrets | Prerrequisitos listos. |
| 5.1  | ✅ | `src/mcp/server.py`, `tools.py` | 5 tools estáticas, flow-to-tool | Servidor Stdio funcional. |
| 5.2  | ✅ | `src/mcp/handlers.py`, `tools.py`, `tests/...` | Handlers reales, HITL integration | Handlers productivos completados. |
| 5.2.1 | ✅ | `src/mcp/exceptions.py`, `tools.py`, `server.py` | Normalización JSON-RPC, Logging, Catch global | Errores MCP robustecidos. |
| 5.2.5 | ✅ | Migration 024, `service_connector.py` | Service Catalog TIPO C | Integración REST genérica certificada. |
| 5.2.6 | ✅ | `data/service_catalog_seed.json`, `docs/...` | Archivo Seed + Docs | 216 herramientas listas para importación. |
| 5.3  | ✅ | `src/mcp/sse.py`, `src/api/routes/mcp.py`, `main.py` | Transporte SSE, Handshake MCP, Lifespan fix | Comunicación asíncrona bidireccional habilitada. |

## 6. Criterios Generales de Aceptación MVP (Fase 5)
- [x] **5.1:** `tools/list` retorna herramientas al conectar desde Claude Desktop.
- [x] **5.2:** Handlers `execute_flow` y `get_task` funcionales y conectados a Stdio.
- [x] **5.2:** HITL funcional (aprobación/rechazo) mediante herramientas MCP.
- [x] **5.3:** Transporte SSE funcional con handshake `endpoint` para clientes web/remotos.
- [x] Los errores MCP se mapean a códigos JSON-RPC estándar y están centralizados.
- [x] Dependencia `sse-starlette` añadida a `pyproject.toml`.

## 7. Estructura del Módulo MCP

```
src/mcp/
├── __init__.py         # Módulo
├── sanitizer.py        # Output sanitizer (Regla R3)
├── config.py           # MCPConfig BaseSettings
├── server.py           # Entry point Stdio
├── tools.py            # Handlers de herramientas (estáticas + dinámicas)
├── flow_to_tool.py     # Flow-to-Tool translator
├── handlers.py         # Business logic (Execute/Approve/Get)
├── auth.py             # Auth Bridge (PyJWT)
├── sse.py              # SSE Connection Manager (Broadcast)
└── exceptions.py       # Error mapping → JSON-RPC
```

---
*Documento actualizado por el protocolo CONTEXTO — Paso 5.2.6 COMPLETADO.*
*Última actualización: 2026-04-22 (post-validación de Archivo Seed)*
