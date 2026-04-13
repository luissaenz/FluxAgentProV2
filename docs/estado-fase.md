# 🗺️ ESTADO DE FASE: FASE 5 - ECOSISTEMA AGÉNTICO (MCP) 🏗️

## 1. Resumen de Fase
- **Objetivo:** Transformar FluxAgentPro de un ejecutor estático a una plataforma agéntica que agentes externos (Claude, GPT, etc.) puedan operar vía el estándar Model Context Protocol (MCP). Incluye la exposición de flows como herramientas MCP, autenticación inter-agente, y un catálogo formal de integraciones REST (TIPO C).
- **Fase Anterior:** Fase 4 - Capa de Inteligencia Visual y Analítica [FINALIZADA ✅]
- **Pasos de la Fase 5:**
    1. **5.0 [Diseño]:** Análisis y blueprint de integración MCP. [COMPLETADO ✅]
    2. **5.0.1 [Prerrequisitos]:** `get_secret_async`, dependencia `mcp>=1.0.0`, enriquecer FlowRegistry. [PENDIENTE]
    3. **5.1 [Backend]:** Servidor MCP Stdio + Flow-to-Tool adapter. [PENDIENTE]
    4. **5.2 [Backend]:** Handlers de ejecución + Auth Bridge (PyJWT). [PENDIENTE]
    5. **5.2.5 [DB+Backend]:** Service Catalog TIPO C (3 tablas + import + ServiceConnectorTool). [COMPLETADO ✅]
    6. **5.3 [Backend+Frontend]:** Endpoint SSE + HITL completo + MCPConfig. [PENDIENTE]
- **Dependencias entre pasos:** 5.0 → 5.0.1 → 5.1 → 5.2 → 5.2.5 (puede ir en paralelo con 5.2) → 5.3

## 2. Estado Actual del Proyecto

- **Implementado y Funcional (heredado de Fases 1-4):**
    - **FlowRegistry** (`src/flows/registry.py`): Registro centralizado con `list_flows()`, `get_metadata()` (retorna `depends_on`, `category`), `get_hierarchy()`. Validación DFS de ciclos al arranque.
    - **BaseFlow** (`src/flows/base_flow.py`): Lifecycle completo con HITL (`request_approval()`, `resume()`), snapshot/restore de estado, y tracking de tokens.
    - **ArchitectFlow** (`src/flows/architect_flow.py`): Genera workflows desde NL, persiste en `workflow_templates`, crea agentes en `agent_catalog`, registra dinámicamente en `FLOW_REGISTRY`.
    - **MCPPool** (`src/tools/mcp_pool.py`): Singleton con circuit breaker (5 fallos → 60s pausa), retry exponencial, resolución de secretos del Vault como env vars. Conexión a servidores MCP externos (TIPO B).
    - **Vault** (`src/db/vault.py`): Gestión de secretos cifrados per-org. Cumple Regla R3 (secretos nunca llegan al LLM). Solo expone `get_secret()` síncrono.
    - **OrgBaseTool** (`src/tools/base_tool.py`): Clase base para herramientas con resolución automática de secretos y aislamiento por `org_id`.
    - **ToolRegistry** (`src/tools/registry.py`): Metadatos operacionales por herramienta (timeout, retry, tags).
    - **Auth/JWT** (`src/api/middleware.py`): Verificación JWT con ES256 (JWKS) + HS256 (secret), `verify_org_membership()`, soporte `fap_admin` cross-org. Usa **PyJWT** (no python-jose).
    - **API REST completa:** Endpoints para flows, tasks, approvals, agents, webhooks, chat, analytical, integrations.
    - **Fases 1-4 completas:** Tickets, Agent Panel, Real-time Transcripts, Visual Analytics.
    - **ServiceConnectorTool** (`src/tools/service_connector.py`): Tool genérica TIPO C. Lee definiciones de `service_tools`, resuelve secretos vía Vault, ejecuta HTTP con `httpx`, sanitiza output (Regla R3), audita en `domain_events`. Registrada con `@register_tool("service_connector", ...)`. Validada ✅.
    - **Output Sanitizer** (`src/mcp/sanitizer.py`): Última línea de defensa para Regla R3. 7 patrones regex (Stripe, Bearer, Basic, Slack, GitHub, Google). Recurre en dict/list. Si falla internamente, retorna error genérico (nunca output sin sanitizar).
    - **Health Check Scheduler** (`src/scheduler/health_check.py`): `run_health_checks()` async. Recorre integraciones activas con `health_check_url`, ejecuta GET con `httpx.AsyncClient`, actualiza `last_health_status` en DB. ⚠️ Job no conectado aún al scheduler/lifespan — invocación manual requerida.
    - **API Integrations** (`src/api/routes/integrations.py`): 3 endpoints — `GET /api/integrations/available` (catálogo global), `GET /api/integrations/active` (integraciones org con `verify_org_membership`), `GET /api/integrations/tools/{service_id}` (tools por servicio). Router registrado en `main.py:98`.
    - **Import Script** (`scripts/import_service_catalog.py`): Carga `data/service_catalog_seed.json` (62KB, ~50 tools, ~20 proveedores). Corrige schemas JSON (`required` booleano → array). Verifica integridad post-import (0 huérfanos, tool_profiles completos).
    - **Service Catalog DB** (`supabase/migrations/024_service_catalog.sql`): 3 tablas — `service_catalog` (global, SIN RLS), `org_service_integrations` (per-org, CON RLS con patrón `service_role` bypass + `current_org_id()` ::text), `service_tools` (global, SIN RLS). FK → `organizations(id)`.

- **Parcialmente Implementado:**
    - **`get_secret_async`:** Se importa en `mcp_pool.py` pero **no está definida** en `vault.py`. Solo existe la versión síncrona. Debe crearse un wrapper async (prerrequisito 5.0.1).
    - **`FLOW_INPUT_SCHEMAS`:** Definidos como diccionario estático en `src/api/routes/flows.py` (líneas 70-130). No están integrados en `FlowRegistry.get_metadata()` — el Flow-to-Tool adapter (5.1) deberá combinar ambas fuentes.

- **No Existe Aún:**
    - **Servidor MCP** (`src/mcp/server.py`, `handlers.py`, `tools.py`, `flow_to_tool.py`, `auth.py`, `config.py`, `exceptions.py`): El directorio `src/mcp/` existe con `__init__.py` y `sanitizer.py` (creados en 5.2.5), pero el servidor MCP propiamente dicho (Stdio/SSE) aún no está implementado.
    - **Dependencia directa `mcp>=1.0.0`:** Solo existe como transitiva vía `crewai-tools`. **PENDIENTE** agregar en `pyproject.toml`.
    - **`get_secret_async`:** Se importa en `mcp_pool.py` pero **no está definida** en `vault.py`. Solo existe la versión síncrona. Debe crearse un wrapper async (prerrequisito 5.0.1). ⚠️ `health_check.py` usa `get_secret()` síncrono dentro de función async como workaround.

- **Documentación de Diseño (completada ✅):**
    - `docs/mcp-analisis-final.md` — Consolidación inicial (60KB).
    - `docs/mcp-analisis-finalV2.md` — Plan detallado de Service Catalog TIPO C (26KB, 740 líneas).
    - `docs/MCP-PHASE/` — 6 análisis individuales (ATG, Claude, Kilo, OC, y 2 finales fusionados).
    - `LAST/mcp-analisis-final-v3.mcp` — Blueprint definitivo v3.3, verificado contra código fuente.

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
- **Tablas de DB existentes relevantes:**
    - `org_mcp_servers` — Config de servidores MCP externos por org (TIPO B).
    - `secrets` — Credenciales cifradas con RLS per-org.
    - `agent_catalog` — Definición de agentes con SOUL, tools y modelo.
    - `workflow_templates` — Templates de workflows generados por ArchitectFlow.
    - `tasks` — Ejecuciones de flows con estado y payload.
    - `pending_approvals` — HITL approvals con aislamiento por org.
    - `domain_events` — Event sourcing. Schema: `(id, org_id, aggregate_type, aggregate_id, event_type, payload, actor, sequence, correlation_id, created_at)`. Usado por `ServiceConnectorTool` para auditoría de ejecuciones TIPO C.
    - `service_catalog` — Catálogo global de proveedores (~20). SIN RLS. PK: `TEXT`. Migración 024. ✅ IMPLEMENTADO.
    - `org_service_integrations` — Servicios habilitados per-org. CON RLS (`auth.role() = 'service_role' OR org_id::text = current_org_id()`). FK → `organizations(id)`. Migración 024. ✅ IMPLEMENTADO.
    - `service_tools` — Definiciones de herramientas por proveedor (~50 tools). SIN RLS. Migración 024. ✅ IMPLEMENTADO.
- **Dependencias instaladas (de `pyproject.toml`):**
    - **Directas:** `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`, `pydantic>=2.10.0`, `pydantic-settings>=2.6.0`, `supabase>=2.10.0`, `anthropic>=0.40.0`, `openai>=1.58.0`, `python-jose[cryptography]>=3.3.0`, `python-dotenv>=1.0.0`, `httpx>=0.28.0`, `structlog>=24.4.0`, `litellm>=1.83.0`, `apscheduler>=3.10.0`, `python-dateutil>=2.9.0`.
    - **Opcionales (crew):** `crewai>=0.100.0`, `crewai-tools>=0.20.0`. Trae `mcp>=1.0.0` como transitiva.
    - **PENDIENTE:** Agregar `mcp>=1.0.0` como dependencia directa en `pyproject.toml`.
    - ⚠️ `python-jose` está en deps pero el código usa **PyJWT** (`import jwt as pyjwt` en `middleware.py:54`). Discrepancia heredada — `python-jose` podría eliminarse como dependencia directa.
- **Endpoints API nuevos (Paso 5.2.5):**
    - `GET /api/integrations/available` → `require_org_id` → catálogo global de servicios.
    - `GET /api/integrations/active` → `verify_org_membership` → integraciones activas de la org.
    - `GET /api/integrations/tools/{service_id}` → `require_org_id` → tools disponibles por servicio.
- **Estructura de carpetas (módulo MCP — parcialmente creado):**
    ```
    src/mcp/
    ├── __init__.py         # ✅ Creado (Paso 5.2.5)
    ├── sanitizer.py        # ✅ Creado (Paso 5.2.5) — Output sanitizer (Regla R3)
    ├── server.py           # ⏳ Pendiente (Paso 5.1)
    ├── handlers.py         # ⏳ Pendiente (Paso 5.2)
    ├── tools.py            # ⏳ Pendiente (Paso 5.1)
    ├── flow_to_tool.py     # ⏳ Pendiente (Paso 5.1)
    ├── auth.py             # ⏳ Pendiente (Paso 5.2)
    ├── config.py           # ⏳ Pendiente (Paso 5.1)
    └── exceptions.py       # ⏳ Pendiente (Paso 5.2)
    ```
- **Patrones de código en uso (verificados contra código fuente):**
    - **RLS:** `auth.role() = 'service_role' OR org_id::text = current_org_id()` — cast a `::text`, helper SQL en `001_set_config_rpc.sql:37-44`. Bypass de `service_role` obligatorio desde migración 010.
    - **Tool Registry:** Decorador `@register_tool(name, description, timeout_seconds, retry_count, tags)` — convenience en `registry.py:110-121`. Import en `__init__.py` para trigger.
    - **Auth en endpoints:** `require_org_id` (header `X-Org-ID`, sin JWT) para lectura ligera. `verify_org_membership` (JWT + membresía org) para operaciones autenticadas. Definidos en `middleware.py:103` y `middleware.py:356`.
    - **Scheduler:** Jobs en `src/scheduler/`. `bartenders_jobs.py` usa `AsyncIOScheduler`. `health_check.py` define `run_health_checks()` async pero ⚠️ no está registrado como job aún.
    - **HTTP client:** `httpx` (síncrono con `httpx.Client`, async con `httpx.AsyncClient`). `requests` NO se usa en código nuevo.
    - **Auditoría:** Inserts en `domain_events` con schema `(org_id, aggregate_type, aggregate_id, event_type, payload, actor, sequence)`. Best-effort con try/except.
    - **Vault:** `get_secret(org_id, secret_name)` síncrono, lanza `VaultError`. Usa `service_role` client.

## 4. Decisiones de Arquitectura Tomadas
- **Servidor MCP Dual (Paso 5.0):** Stdio para Claude Desktop (sesiones locales) y SSE para Claude API / integraciones remotas. Ambos comparten el mismo core de handlers.
- **Auth Bridge con PyJWT (Paso 5.0):** Reutiliza el singleton `_get_jwks_client()` del middleware existente. Soporta ES256 (JWKS) + HS256 (legacy). Verifica membresía org vía `org_members` — no usa el claim `org_id` del token (que no existe en Supabase JWT).
- **Flow-to-Tool combina dos fuentes (Paso 5.0):** `FlowRegistry.get_metadata()` aporta `category` y `depends_on`; `FLOW_INPUT_SCHEMAS` aporta los JSON Schemas de input. Mejora futura: enriquecer `register()` para unificar.
- **Regla R3 — Defensa en profundidad (Paso 5.0, implementado en 5.2.5):** Los secretos se resuelven server-side (Vault → env var o header). El output al agente pasa por `sanitizer.py` como última línea de defensa con regex patterns para tokens conocidos. ✅ `sanitizer.py` implementado y verificado.
- **Identidad por CLI flag (Paso 5.0):** Para Stdio, el `org_id` se recibe como `--org-id` al iniciar el servidor. Para SSE, como header `X-Org-ID`. No se implementa `switch_org` en MVP.
- **Service Catalog TIPO C separado de TIPO B (Paso 5.0, implementado en 5.2.5):** TIPO B (MCPPool, `org_mcp_servers`) es para servidores MCP externos. TIPO C (`service_catalog`, `ServiceConnectorTool`) es para APIs REST genéricas definidas en DB. ✅ Implementado y validado.
- **Migraciones SQL incrementales:** Última migración: `024_service_catalog.sql`. La próxima será `025_*.sql`.
- **Correcciones al plan general documentadas (Paso 5.2.5):** El `analisis-FINAL.md` documenta 6 discrepancias del plan `mcp-analisis-finalV2.md` verificadas contra código real. Los futuros pasos DEBEN consultar `analisis-FINAL.md` y no el plan original para: RLS patterns (§A.3), HTTP library (§C.2 — `httpx` no `requests`), decorador de registro (§C.3), ubicación de jobs (§D.1 — `src/scheduler/`), middleware auth (§D.2 — no existe `get_current_user`), tabla de auditoría (§D.3 — `domain_events` no `activity_logs`).
- **`ServiceConnectorTool` es síncrono (Paso 5.2.5):** `_run()` hereda de CrewAI `BaseTool` (síncrono). Usa `get_secret()` síncrono y `httpx.Client` síncrono. Decisión coherente: `get_secret_async` es prerrequisito 5.0.1 pendiente.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 5.0  | ✅ | `LAST/mcp-analisis-final-v3.mcp` (v3.3), `docs/mcp-analisis-final.md`, `docs/mcp-analisis-finalV2.md`, `docs/MCP-PHASE/` (6 archivos) | Servidor dual, PyJWT auth, FLOW_INPUT_SCHEMAS, Regla R3 sanitizer, estimaciones ajustadas 32-41h | Blueprint verificado contra código real. 7 discrepancias identificadas y corregidas en v3.3. |
| 5.0.1 | ⏳ | — | `get_secret_async` wrapper, `mcp>=1.0.0` como dep directa | Prerrequisitos técnicos antes de Fase 5.1 |
| 5.1  | ⏳ | — | — | Servidor Stdio + Flow-to-Tool + `tools/list` |
| 5.2  | ⏳ | — | — | Handlers + Auth Bridge |
| 5.2.5  | ✅ | `supabase/migrations/024_service_catalog.sql`, `data/service_catalog_seed.json`, `scripts/import_service_catalog.py`, `src/mcp/__init__.py`, `src/mcp/sanitizer.py`, `src/tools/service_connector.py`, `src/tools/__init__.py` (mod), `src/scheduler/health_check.py`, `src/api/routes/integrations.py`, `src/api/main.py` (mod) | httpx (no requests), @register_tool decorador, domain_events (no activity_logs), RLS con current_org_id()::text + service_role bypass, verify_org_membership (no get_current_user), src/scheduler/ (no src/jobs/) | 6 correcciones al plan aplicadas. 18/18 criterios de aceptación cumplidos. Validación APROBADA (`LAST/validacion.md`). Issues no-bloqueantes: scheduler health check no conectado al lifespan. |
| 5.3  | ⏳ | — | — | SSE + HITL completo |
| 4.5  | ✅ | `test_4_5_precision.py`, `seed_precision_data.py` | Golden Set Validation / Controlled Seeding | Precisión certificada (Success Rate 90/50). |
| 4.4  | ✅ | `AnalyticalAssistantChat.tsx`, `layout.tsx`, `analytical_chat.py` | FAB Global / Sheet UI | Chat analítico operativo y validado. |
| 4.3  | ✅ | `analytical_crew.py`, `analytical.py`, `analytical_chat.py` | Asincronía LLM / Multi-fallback | Backend analítico certificado. |
| 4.2  | ✅ | `FlowHierarchyView.tsx`, `page.tsx`, `types.ts` | Error Auto-expand / Framer Motion | Visualización diagnóstica aprobada. |
| 4.1  | ✅ | `registry.py`, `main.py`, `flows.py`, `architect_flow.py` | Code-as-Schema / DFS Cycle Detection | Jerarquía de procesos validada. |
| 3.5  | ✅ | `test_3_5_latency.py`, `get_server_time.sql` | Certificación de Latencia P95 | Validado tras resolver issues de Cold Start. |

## 6. Criterios Generales de Aceptación MVP (Fase 5)
- [ ] **5.0.1:** `import mcp` funciona y `get_secret_async()` resuelve secretos correctamente.
- [ ] **5.1:** `tools/list` retorna ≥3 herramientas al conectar desde Claude Desktop vía Stdio.
- [ ] **5.2:** Claude construye y ejecuta un flujo simple en FAP desde el chat (E2E).
- [ ] **5.2.5:** Un agente ejecuta `stripe.create_customer` leyendo la definición de `service_tools` y resolviendo el secreto del Vault, sin código hardcodeado para Stripe.
- [ ] **5.3:** Flujo HITL end-to-end funcional desde Claude con aprobación vía Dashboard.
- [ ] Los errores MCP se mapean a códigos JSON-RPC estándar sin exponer internals.
- [ ] La Regla R3 se mantiene en todas las respuestas al agente externo (sanitizer activo).

---
*Documento actualizado por el protocolo CONTEXTO — Paso 5.2.5 (Service Catalog TIPO C) COMPLETADO y VALIDADO.*
*Última actualización: 2026-04-13T19:23 (post-validación 5.2.5)*
