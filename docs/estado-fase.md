# 🗺️ ESTADO DE FASE: FASE 5 - ECOSISTEMA AGÉNTICO (MCP) 🏗️

## 1. Resumen de Fase
- **Objetivo:** Transformar FluxAgentPro de un ejecutor estático a una plataforma agéntica que agentes externos (Claude, GPT, etc.) puedan operar vía el estándar Model Context Protocol (MCP). Incluye la exposición de flows como herramientas MCP, autenticación inter-agente, y un catálogo formal de integraciones REST (TIPO C).
- **Fase Anterior:** Fase 4 - Capa de Inteligencia Visual y Analítica [FINALIZADA ✅]
- **Pasos de la Fase 5:**
    1. **5.0 [Diseño]:** Análisis y blueprint de integración MCP. [COMPLETADO ✅]
    2. **5.0.1 [Prerrequisitos]:** `get_secret_async`, dependencia `mcp>=1.0.0`, enriquecer FlowRegistry. [PENDIENTE]
    3. **5.1 [Backend]:** Servidor MCP Stdio + Flow-to-Tool adapter. [PENDIENTE]
    4. **5.2 [Backend]:** Handlers de ejecución + Auth Bridge (PyJWT). [PENDIENTE]
    5. **5.2.5 [DB+Backend]:** Service Catalog TIPO C (3 tablas + import + ServiceConnectorTool). [PENDIENTE]
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
    - **API REST completa:** Endpoints para flows, tasks, approvals, agents, webhooks, chat, analytical.
    - **Fases 1-4 completas:** Tickets, Agent Panel, Real-time Transcripts, Visual Analytics.

- **Parcialmente Implementado:**
    - **`get_secret_async`:** Se importa en `mcp_pool.py` pero **no está definida** en `vault.py`. Solo existe la versión síncrona. Debe crearse un wrapper async (prerrequisito 5.0.1).
    - **`FLOW_INPUT_SCHEMAS`:** Definidos como diccionario estático en `src/api/routes/flows.py` (líneas 70-130). No están integrados en `FlowRegistry.get_metadata()` — el Flow-to-Tool adapter (5.1) deberá combinar ambas fuentes.

- **No Existe Aún:**
    - **`src/mcp/`:** Directorio del servidor MCP (server.py, handlers.py, tools.py, flow_to_tool.py, auth.py, config.py, sanitizer.py).
    - **Service Catalog (TIPO C):** Tablas `service_catalog`, `org_service_integrations`, `service_tools`.
    - **`ServiceConnectorTool`:** OrgBaseTool genérico para integraciones TIPO C.
    - **Dependencia directa `mcp>=1.0.0`:** Solo existe como transitiva vía `crewai-tools`.

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
- **Tablas NUEVAS (pendientes de migración `024_service_catalog.sql`):**
    - `service_catalog` — Catálogo global de proveedores (Stripe, WhatsApp, etc.). SIN RLS.
    - `org_service_integrations` — Servicios habilitados per-org. CON RLS. FK → `organizations` (⚠️ verificar nombre real de tabla).
    - `service_tools` — Definiciones de herramientas por proveedor (~50 tools). SIN RLS.
- **Dependencias instaladas:**
    - `anthropic>=0.40.0` — SDK con soporte MCP built-in.
    - `crewai>=0.100.0` — **Opcional** (en `[project.optional-dependencies].crew`). Requiere `pip install -e ".[crew]"`.
    - `crewai-tools>=0.20.0` — **Opcional**. Trae `mcp>=1.0.0` como transitiva.
    - **PENDIENTE:** Agregar `mcp>=1.0.0` como dependencia directa en `pyproject.toml`.
- **Estructura de carpetas (módulo MCP, a crear):**
    ```
    src/mcp/
    ├── __init__.py
    ├── server.py          # Servidor dual (Stdio + SSE)
    ├── handlers.py        # Lógica de cada handler MCP
    ├── tools.py           # Definiciones de las 15 tools
    ├── flow_to_tool.py    # Traductor FlowRegistry → MCP Tools
    ├── auth.py            # Auth Bridge (PyJWT ES256/HS256 + org membership)
    ├── config.py          # MCPConfig settings
    ├── sanitizer.py       # Output sanitizer (Regla R3)
    └── exceptions.py      # Mapeo FAP → JSON-RPC error codes
    ```

## 4. Decisiones de Arquitectura Tomadas
- **Servidor MCP Dual (Paso 5.0):** Stdio para Claude Desktop (sesiones locales) y SSE para Claude API / integraciones remotas. Ambos comparten el mismo core de handlers.
- **Auth Bridge con PyJWT (Paso 5.0):** Reutiliza el singleton `_get_jwks_client()` del middleware existente. Soporta ES256 (JWKS) + HS256 (legacy). Verifica membresía org vía `org_members` — no usa el claim `org_id` del token (que no existe en Supabase JWT).
- **Flow-to-Tool combina dos fuentes (Paso 5.0):** `FlowRegistry.get_metadata()` aporta `category` y `depends_on`; `FLOW_INPUT_SCHEMAS` aporta los JSON Schemas de input. Mejora futura: enriquecer `register()` para unificar.
- **Regla R3 — Defensa en profundidad (Paso 5.0):** Los secretos se resuelven server-side (Vault → env var o header). El output al agente pasa por `sanitizer.py` como última línea de defensa con regex patterns para tokens conocidos.
- **Identidad por CLI flag (Paso 5.0):** Para Stdio, el `org_id` se recibe como `--org-id` al iniciar el servidor. Para SSE, como header `X-Org-ID`. No se implementa `switch_org` en MVP.
- **Service Catalog TIPO C separado de TIPO B (Paso 5.0):** TIPO B (MCPPool, `org_mcp_servers`) es para servidores MCP externos. TIPO C (`service_catalog`, `ServiceConnectorTool`) es para APIs REST genéricas definidas en DB.
- **Migraciones SQL incrementales:** La próxima migración será `024_service_catalog.sql` (siguiendo la secuencia 001-023 existente).

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 5.0  | ✅ | `LAST/mcp-analisis-final-v3.mcp` (v3.3), `docs/mcp-analisis-final.md`, `docs/mcp-analisis-finalV2.md`, `docs/MCP-PHASE/` (6 archivos) | Servidor dual, PyJWT auth, FLOW_INPUT_SCHEMAS, Regla R3 sanitizer, estimaciones ajustadas 32-41h | Blueprint verificado contra código real. 7 discrepancias identificadas y corregidas en v3.3. |
| 5.0.1 | ⏳ | — | `get_secret_async` wrapper, `mcp>=1.0.0` como dep directa | Prerrequisitos técnicos antes de Fase 5.1 |
| 5.1  | ⏳ | — | — | Servidor Stdio + Flow-to-Tool + `tools/list` |
| 5.2  | ⏳ | — | — | Handlers + Auth Bridge |
| 5.2.5  | ⏳ | — | — | Service Catalog TIPO C |
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
*Documento actualizado por el protocolo CONTEXTO — Transición de Fase 4 (COMPLETADA) a Fase 5 (ECOSISTEMA AGÉNTICO MCP).*
*Última actualización: 2026-04-13*
