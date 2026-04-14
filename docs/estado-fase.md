# 🗺️ ESTADO DE FASE: FASE 5 - ECOSISTEMA AGÉNTICO (MCP) 🏗️

## 1. Resumen de Fase
- **Objetivo:** Transformar FluxAgentPro de un ejecutor estático a una plataforma agéntica que agentes externos (Claude, GPT, etc.) puedan operar vía el estándar Model Context Protocol (MCP). Incluye la exposición de flows como herramientas MCP, autenticación inter-agente, y un catálogo formal de integraciones REST (TIPO C).
- **Fase Anterior:** Fase 4 - Capa de Inteligencia Visual y Analítica [FINALIZADA ✅]
- **Pasos de la Fase 5:**
    1. **5.0 [Diseño]:** Análisis y blueprint de integración MCP. [COMPLETADO ✅]
    2. **5.0.1 [Prerrequisitos]:** `get_secret_async`, dependencia `mcp>=1.0.0`, migración 025 RLS. [COMPLETADO ✅]
    3. **5.1 [Backend]:** Servidor MCP Stdio + Flow-to-Tool adapter + 5 tools estáticas. [COMPLETADO ✅]
    4. **5.2 [Backend]:** Handlers de ejecución + Auth Bridge (PyJWT). [PENDIENTE — SIGUIENTE]
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
    - **Auth/JWT** (`src/api/middleware.py`): Verificación JWT con ES256 (JWKS) + HS256 (secret), `verify_org_membership()`, soporte `fap_admin` cross-org. Usa **PyJWT** (no python-jose).
    - **API REST completa:** Endpoints para flows, tasks, approvals, agents, webhooks, chat, analytical, integrations.
    - **ServiceConnectorTool** (`src/tools/service_connector.py`): Tool genérica TIPO C. Lee definiciones de `service_tools`, resuelve secretos vía Vault, ejecuta HTTP con `httpx`, sanitiza output (Regla R3), audita en `domain_events`. Registrada con `@register_tool("service_connector", ...)`. Validada ✅.
    - **Output Sanitizer** (`src/mcp/sanitizer.py`): Última línea de defensa para Regla R3. 7 patrones regex. Recurre en dict/list. Si falla internamente, retorna error genérico.
    - **Health Check Scheduler** (`src/scheduler/health_check.py`): `run_health_checks()` async. ⚠️ Job no conectado aún al scheduler/lifespan — invocación manual requerida.
    - **API Integrations** (`src/api/routes/integrations.py`): 3 endpoints — `/available`, `/active`, `/tools/{service_id}`. Router registrado en `main.py`.
    - **Import Script** (`scripts/import_service_catalog.py`): Carga `data/service_catalog_seed.json` (~50 tools, ~20 proveedores).
    - **Service Catalog DB** (`supabase/migrations/024_service_catalog.sql`): 3 tablas con RLS correcto.
    - **MCP Server Stdio** (`src/mcp/server.py`): Entry point `python -m src.mcp.server --org-id <UUID>`. Implementa `list_tools` (estáticas + dinámicas) y `call_tool` (dispatch a handlers).
    - **MCP Config** (`src/mcp/config.py`): `MCPConfig` con Pydantic BaseSettings, prefijo `MCP_`. Soporta Stdio y SSE (SSE pendiente Sprint 4).
    - **MCP Tools** (`src/mcp/tools.py`): 5 tools estáticas (`list_flows`, `list_agents`, `get_agent_detail`, `get_server_time`, `list_capabilities`) con handlers completos. Output sanitizado vía `sanitize_output()`.
    - **Flow-to-Tool Adapter** (`src/mcp/flow_to_tool.py`): Genera un Tool MCP por cada flow registrado combinando FlowRegistry + FLOW_INPUT_SCHEMAS. Ejecución es placeholder (Sprint 1 = solo consulta).
    - **Migración 025** (`supabase/migrations/025_agent_catalog_rls_update.sql`): `agent_catalog` RLS actualizado al patrón moderno con `service_role` bypass.
    - **Claude Desktop Config** (`claude_desktop_config.json`): Template con placeholders — requiere configuración con valores reales.

- **Pendiente de Verificación:**
    - [ ] Arranque del servidor MCP localmente (`python -m src.mcp.server --org-id <UUID>`)
    - [ ] Conexión desde Claude Desktop con `claude_desktop_config.json` configurado
    - [ ] Migración 025 aplicada en Supabase
    - [ ] Health check scheduler conectado al lifespan

- **No Existe Aún (Pasos 5.2 y 5.3):**
    - **`src/mcp/handlers.py`** — Lógica de ejecución real de flows (actualmente placeholder que rechaza ejecución).
    - **`src/mcp/auth.py`** — Auth Bridge con PyJWT para validar tokens de agentes externos.
    - **`src/mcp/exceptions.py`** — Mapeo de errores internos a códigos JSON-RPC estándar.
    - **Servidor SSE** — Transporte alternativo para agentes remotos (Sprint 4).
    - **HITL desde Claude** — Approve/reject flows desde el agente externo.

## 3. Contratos Técnicos Vigentes

- **API existente reutilizable por MCP:**
    - `POST /webhooks/trigger` → handler `execute_flow`
    - `GET /flows/available` → handler `list_flows`
    - `GET /flows/hierarchy` → handler `get_flow_hierarchy`
    - `POST /flows/{flow_type}/run` → handler `execute_flow` (alternativo)
    - `GET /tasks/{task_id}` → handler `get_task`
    - `POST /approvals/{task_id}` → handler `approve_task` / `reject_task`
    - `GET /agents/{id}/detail` → handler `get_agent_detail`
    - `POST /chat/architect` → handler `create_workflow`
- **Tablas de DB relevantes:**
    - `secrets` — Credenciales cifradas con RLS per-org.
    - `agent_catalog` — Definición de agentes (RLS mig025 ✅).
    - `org_service_integrations` — Servicios habilitados per-org (RLS mig024 ✅).
    - `service_catalog` — Catálogo global de proveedores (SIN RLS).
    - `service_tools` — Definiciones de herramientas por proveedor (SIN RLS).
    - `domain_events` — Event sourcing / auditoría.
    - `workflow_templates`, `tasks`, `pending_approvals` — Datos operacionales.
- **Dependencias (verificadas en `pyproject.toml`):**
    - **Directas:** `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`, `pydantic>=2.10.0`, `pydantic-settings>=2.6.0`, `supabase>=2.10.0`, `anthropic>=0.40.0`, `openai>=1.58.0`, `python-jose[cryptography]>=3.3.0`, `python-dotenv>=1.0.0`, `httpx>=0.28.0`, `structlog>=24.4.0`, `litellm>=1.83.0`, `apscheduler>=3.10.0`, `python-dateutil>=2.9.0`, `mcp>=1.0.0,<2.0.0`.
    - **Opcionales (crew):** `crewai>=0.100.0`, `crewai-tools>=0.20.0`.
    - ⚠️ `python-jose` está en deps pero el código usa **PyJWT** (`import jwt as pyjwt` en `middleware.py:54`). Discrepancia heredada.
- **Patrones de código verificados:**
    - **RLS:** `auth.role() = 'service_role' OR org_id::text = current_org_id()`.
    - **Tool Registry:** Decorador `@register_tool(name, description, timeout_seconds, retry_count, tags)`.
    - **Auth en endpoints:** `require_org_id` (header `X-Org-ID`) y `verify_org_membership` (JWT + membresía).
    - **HTTP client:** `httpx` (sync y async). `requests` NO se usa en código nuevo.
    - **Auditoría:** `domain_events` con schema `(org_id, aggregate_type, aggregate_id, event_type, payload, actor, sequence)`.
    - **Vault:** `get_secret(org_id, secret_name)` síncrono + `get_secret_async(org_id, secret_name)` async.

## 4. Decisiones de Arquitectura Tomadas
- **Servidor MCP Dual (Paso 5.0):** Stdio para Claude Desktop y SSE para Claude API / integraciones remotas. Ambos comparten el mismo core de handlers.
- **Auth Bridge con PyJWT (Paso 5.0):** Reutiliza `_get_jwks_client()` del middleware existente. Soporta ES256 + HS256.
- **Flow-to-Tool combina dos fuentes (Paso 5.1):** `FlowRegistry.get_metadata()` aporta metadatos; `FLOW_INPUT_SCHEMAS` aporta JSON Schemas. Post-desacople NOA, los schemas están vacíos (aceptable para Sprint 1, solo consulta).
- **Regla R3 — Defensa en profundidad:** Vault resuelve secretos server-side. `sanitizer.py` como última línea de defensa.
- **Identidad por CLI flag:** Stdio recibe `--org-id` al iniciar. SSE usará header `X-Org-ID`.
- **Service Catalog TIPO C separado de TIPO B:** TIPO B = MCPPool (servidores MCP externos). TIPO C = ServiceConnectorTool (APIs REST genéricas).
- **Migraciones SQL incrementales:** Última migración: `025_agent_catalog_rls_update.sql`.
- **Correcciones documentadas:** 6 discrepancias del plan original resueltas en `docs/MCP Fase 1/analisis-FINAL.md`.
- **Sprint 1 solo consulta:** Flow tools dinámicas se exponen en `tools/list` pero la ejecución retorna placeholder hasta Sprint 3.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 5.0  | ✅ | `LAST/mcp-analisis-final-v3.mcp` (v3.3), `docs/mcp-analisis-final.md`, `docs/mcp-analisis-finalV2.md`, `docs/MCP-PHASE/` (6 archivos) | Servidor dual, PyJWT auth, FLOW_INPUT_SCHEMAS, Regla R3 sanitizer | Blueprint verificado contra código real. 7 discrepancias identificadas y corregidas en v3.3. |
| 5.0.1 | ✅ | `pyproject.toml` (mcp dep), `src/db/vault.py` (get_secret_async), `supabase/migrations/025_agent_catalog_rls_update.sql` | `mcp>=1.0.0,<2.0.0` como dep directa, `get_secret_async` con `asyncio.to_thread`, RLS moderno para agent_catalog | Los 3 prerrequisitos implementados. |
| 5.1  | ✅ | `src/mcp/server.py`, `src/mcp/config.py`, `src/mcp/tools.py`, `src/mcp/flow_to_tool.py`, `claude_desktop_config.json` | 5 tools estáticas, flow-to-tool dinámico, MCPConfig con BaseSettings | Servidor Stdio funcional. Ejecución de flows es placeholder (Sprint 3). Pendiente verificación E2E con Claude Desktop. |
| 5.2  | ⏳ | — | — | Handlers productivos + Auth Bridge. SIGUIENTE paso a implementar. |
| 5.2.5  | ✅ | `supabase/migrations/024_service_catalog.sql`, `data/service_catalog_seed.json`, `scripts/import_service_catalog.py`, `src/mcp/__init__.py`, `src/mcp/sanitizer.py`, `src/tools/service_connector.py`, `src/tools/__init__.py` (mod), `src/scheduler/health_check.py`, `src/api/routes/integrations.py`, `src/api/main.py` (mod) | httpx, @register_tool, domain_events, RLS moderno, verify_org_membership | 18/18 criterios de aceptación cumplidos. Validación APROBADA. |
| 5.3  | ⏳ | — | — | SSE + HITL completo. |
| 4.5  | ✅ | `test_4_5_precision.py`, `seed_precision_data.py` | Golden Set Validation | Precisión certificada. |
| 4.4  | ✅ | `AnalyticalAssistantChat.tsx`, `layout.tsx`, `analytical_chat.py` | FAB Global / Sheet UI | Chat analítico operativo. |
| 4.3  | ✅ | `analytical_crew.py`, `analytical.py`, `analytical_chat.py` | Asincronía LLM / Multi-fallback | Backend analítico certificado. |
| 4.2  | ✅ | `FlowHierarchyView.tsx`, `page.tsx`, `types.ts` | Error Auto-expand / Framer Motion | Visualización diagnóstica aprobada. |
| 4.1  | ✅ | `registry.py`, `main.py`, `flows.py`, `architect_flow.py` | Code-as-Schema / DFS Cycle Detection | Jerarquía de procesos validada. |
| 3.5  | ✅ | `test_3_5_latency.py`, `get_server_time.sql` | Certificación de Latencia P95 | Validado. |

## 6. Criterios Generales de Aceptación MVP (Fase 5)
- [x] **5.0.1:** `import mcp` funciona y `get_secret_async()` resuelve secretos correctamente.
- [x] **5.1:** `tools/list` retorna ≥3 herramientas al conectar desde Claude Desktop vía Stdio.
- [ ] **5.2:** Claude construye y ejecuta un flujo simple en FAP desde el chat (E2E).
- [x] **5.2.5:** Un agente ejecuta `stripe.create_customer` leyendo la definición de `service_tools` y resolviendo el secreto del Vault, sin código hardcodeado para Stripe.
- [ ] **5.3:** Flujo HITL end-to-end funcional desde Claude con aprobación vía Dashboard.
- [ ] Los errores MCP se mapean a códigos JSON-RPC estándar sin exponer internals.
- [x] La Regla R3 se mantiene en todas las respuestas al agente externo (sanitizer activo).

## 7. Estructura del Módulo MCP

```
src/mcp/
├── __init__.py         # ✅ Paso 5.2.5
├── sanitizer.py        # ✅ Paso 5.2.5 — Output sanitizer (Regla R3)
├── config.py           # ✅ Paso 5.1  — MCPConfig BaseSettings
├── server.py           # ✅ Paso 5.1  — Entry point Stdio
├── tools.py            # ✅ Paso 5.1  — 5 tools estáticas + handler dispatch
├── flow_to_tool.py     # ✅ Paso 5.1  — Flow-to-Tool translator
├── handlers.py         # ⏳ Paso 5.2  — Execute flow / get task / approve
├── auth.py             # ⏳ Paso 5.2  — Auth Bridge (PyJWT)
└── exceptions.py       # ⏳ Paso 5.2  — Error mapping → JSON-RPC
```

---
*Documento actualizado por el protocolo CONTEXTO — Pasos 5.0.1 y 5.1 COMPLETADOS.*
*Última actualización: 2026-04-13 (post-implementación Sprint 1 completo)*
