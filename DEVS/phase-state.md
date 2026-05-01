# Phase State — `details4agents`

> **Generado:** 2026-04-30
> **Fuente de verdad:** Código en `src/`, migraciones en `supabase/migrations/`, `pyproject.toml`
> **Nota:** `estado-fase.md` es la fuente canonica de estado para Fase V.
> **Consumidores:** Analista, Unificador, Implementador, Validador

---

## 1. Resumen de Fase

**Fase:** `details4agents`
**Objetivo:** Habilitar la generación avanzada de agentes con soporte MCP (`mcp:server:tool`), integraciones vía `service_connector`, y workflows multi-agente dinámicos. El ArchitectFlow debe reconocer y generar bundles con estas capacidades.

**Pasos planificados (de `DEVS/plan.md`):**

| Paso | Nombre | Dependencias | Estado |
|------|--------|-------------|--------|
| 1 | Mejora de la Infraestructura de Herramientas | Ninguna | ✅ Completado |
| 2 | Upgrade del Cerebro (ArchitectFlow) | Paso 1 | ✅ Completado |
| 3 | Validación y Pruebas (6 Escenarios) | Paso 2 | ⬜ Pendiente |
| 4 | Documentación y Cierre | Paso 3 | ⬜ Pendiente |

---

## 2. Estado Actual del Proyecto

### Rutas activas (de `proyecto-config.json`)
- `paths.backend:` `D:\Develop\Personal\FluxAgentPro-v2\src`
- `paths.frontend:` `D:\Develop\Personal\FluxAgentPro-v2\dashboard`
- `paths.migrations:` `D:\Develop\Personal\FluxAgentPro-v2\supabase\migrations`
- `paths.api_routes:` `D:\Develop\Personal\FluxAgentPro-v2\src\api\routes`
- `paths.devs:` `D:\Develop\Personal\FluxAgentPro-v2\DEVS`
- `paths.devs_in_progress:` `D:\Develop\Personal\FluxAgentPro-v2\DEVS\IN_PROGRESS`
- `paths.devs_implemented:` `D:\Develop\Personal\FluxAgentPro-v2\DEVS\IMPLEMENTED`
- `paths.registry_tools:` `D:\Develop\Personal\FluxAgentPro-v2\src\tools\registry.py`
- `paths.registry_flows:` `D:\Develop\Personal\FluxAgentPro-v2\src\flows\registry.py`
- `paths.cli:` `D:\Develop\Personal\FluxAgentPro-v2\src\cli`
- `paths.scheduler:` `D:\Develop\Personal\FluxAgentPro-v2\src\scheduler`
- `paths.middleware:` `D:\Develop\Personal\FluxAgentPro-v2\src\api\middleware.py`
- `phase.phase_name:` `details4agents`

### Stack detectado
- **Backend:** Python (>=3.12,<3.14) + FastAPI (>=0.115.0)
- **Frontend:** TypeScript + Next.js
- **DB:** Supabase (PostgreSQL) via Supabase client (direct queries + RPC)
- **Auth:** PyJWT (>=2.0.0) — ES256 + HS256 con JWKS
- **Package manager:** uv

### Implementado y funcional (verificado contra código)

| Componente | Archivo(s) | Estado | Notas |
|---|---|---|---|
| **ToolRegistry** | `src/tools/registry.py` | ✅ Funcional | Registro con metadata, lookup tenant-scoped, DB fallback, filesystem fallback, strict mode |
| **FlowRegistry** | `src/flows/registry.py` | ✅ Funcional | Registro con `depends_on`, `category`, DB lookup (workflow_templates), tenant cache |
| **AgentFactory** | `src/crews/factory.py` | ✅ Funcional | `create_agent()`, `create_agent_async()`, `resolve_tools()` con soporte MCP |
| **BaseCrew** | `src/crews/base_crew.py` | ✅ Funcional | `run()`, `run_async()`, `kickoff_async()`, `_resolve_tools()` delega a factory |
| **MCPPool** | `src/tools/mcp_pool.py` | ✅ Funcional | Singleton, circuit breaker (5 fallos → 60s), retry con tenacity, lazy import crewai-tools |
| **MCP Server** | `src/mcp/server.py`, `src/mcp/tools.py`, `src/mcp/handlers.py` | ✅ Funcional | Stdio + SSE, sanitizer, auth, flow-to-tool bridge |
| **BaseFlow** | `src/flows/base_flow.py` | ✅ Funcional | State machine, persist_state, emit_event, with_error_handling, validate_input |
| **DynamicWorkflow** | `src/flows/dynamic_flow.py` | ✅ Funcional | Multi-step execution, context passing |
| **MultiCrewFlow** | `src/flows/multi_crew_flow.py` | ✅ Funcional | Orquestación secuencial de crews |
| **ArchitectFlow** | `src/flows/architect_flow.py` | ✅ Funcional | Generación de agentes desde spec |
| **WorkflowDefinition** | `src/flows/workflow_definition.py` | ✅ Funcional | Pydantic model con validación de steps y agent roles |
| **SecurityGuard** | `src/services/security_guard.py` | ✅ Funcional | AST scan, restricted compilation, forbidden imports |
| **BundleManager** | `src/services/bundle_manager.py` | ✅ Funcional | Process ZIP, integrity check (SHA256), security scan |
| **EventStore** | `src/events/store.py` | ✅ Funcional | Event persistence, flush |
| **Auth Middleware** | `src/api/middleware.py` | ✅ Funcional | JWT verify (ES256/HS256), org membership, `require_org_id` |
| **CLI (fap)** | `src/cli/main.py` + `src/cli/commands/` | ✅ Funcional | init, login, validate, package, publish, run, scaffold, dev, export-agents, **validate-tools** |
| **API Routes** | `src/api/routes/` | ✅ Funcional | agents, bundles, flows, workflows, chat, approvals, tasks, tickets, webhooks, mcp, integrations |
| **Scheduler** | `src/scheduler/` | ✅ Funcional | health_check, bartenders_jobs |
| **DB Session** | `src/db/session.py` | ✅ Funcional | get_service_client, get_tenant_client, get_anon_client |
| **Vault** | `src/db/vault.py` | ✅ Funcional | get_secret, get_secret_async, list_secrets |
| **Memory** | `src/db/memory.py` | ✅ Funcional | Embed, save, search, cleanup expired |
| **ServiceConnector** | `src/tools/service_connector.py` | ✅ Funcional | HTTP integrations via service_catalog |
| **Config** | `src/config.py` | ✅ Funcional | Pydantic settings, get_llm() |

### Parcialmente implementado

| Componente | Qué falta |
|---|---|
| **ArchitectFlow — soporte MCP en prompt** | El plan (Paso 2) requiere actualizar el system_prompt del Architect para reconocer `mcp:server:tool` y `service_connector`. Pendiente del Paso 2. |

### No existe aún

| Componente | Notas |
|---|---|
| **Suite de 6 Escenarios** | Pendiente del Paso 3. |
| **Documentación de fase** | Pendiente del Paso 4. |

### Tablas DB (verificadas en migraciones)

| Tabla | Migración | Columnas clave |
|---|---|---|
| `agent_catalog` | `004_agent_catalog.sql` | id, org_id, role, is_active, soul_json, allowed_tools (TEXT[]), max_iter |
| `org_mcp_servers` | `005_org_mcp_servers.sql` | id, org_id, name, command, args (JSONB), secret_name, is_active |
| `workflow_templates` | `006_workflow_templates.sql` | id, org_id, flow_type, definition (JSONB), is_python, code_source, is_active |
| `service_catalog` | `024_service_catalog.sql` | id, org_id, name, base_url, auth_type, secret_name, is_active |
| `snapshots` | `002_governance.sql` | id, org_id, task_id, state, status, approval_status, approved_by |
| `tasks` | `002_governance.sql` | id, org_id, flow_type, flow_id, status, result |
| `events` | `002_governance.sql` | id, org_id, task_id, event_type, payload, created_at |
| `secrets` | `002_governance.sql` | id, org_id, name, value, created_at |
| `memory_vectors` | `002_memory_vectors.sql` | id, org_id, content, embedding, metadata, valid_to |
| `skill_catalog` | `0029_python_flows.sql` | id, org_id, name, code_source, is_active |
| `flow_presentations` | `016_flow_presentations.sql` | id, org_id, flow_type, presentation_data |
| `tickets` | `019_tickets.sql` | id, org_id, flow_id, status, priority, assigned_to |
| `organizations` | `002_governance.sql` | id, name, settings (JSONB), created_at |

### Discrepancias plan vs código

| # | Plan dice | Código real | Resolución |
|---|---|---|---|
| D1 | "Modificar `BaseCrew._resolve_tools` para manejar MCP" | `_resolve_tools` es dead code — `run()` usa `AgentFactory.create_agent()` directamente | Corregido en analisis-FINAL.md Paso 1. Resolución centralizada en `AgentFactory.resolve_tools()` |
| D2 | Plan asume `create_agent()` no soporta tools instanciadas | Ya crea instancias con `tool_cls(org_id=self.org_id)` | Corregido en analisis-FINAL.md. Se agregó `create_agent_async()` para modo MCP |

---

## 3. Contratos Técnicos Vigentes

### Patrones de código en uso

**Patrón RLS:**
- Variable: `current_setting('app.org_id', TRUE)` o `current_org_id()` (helper RPC)
- Cast: `org_id::text` para comparación con setting string
- Verificado en: `004_agent_catalog.sql:23`, `005_org_mcp_servers.sql:26`

**Patrón registro de tools:**
- Decorador: `@tool_registry.register(name, description, ...)` o `@register_tool(name, ...)`
- Verificado en: `src/tools/registry.py:39-70`, `src/tools/registry.py:276-287`
- Lookup: `tool_registry.get(name, org_id=org_id)` → tenant-scoped → global → DB → filesystem

**Patrón registro de flows:**
- Decorador: `@flow_registry.register(name, depends_on, category, description)` o `@register_flow(...)`
- Verificado en: `src/flows/registry.py:47-93`
- Lookup: `flow_registry.get(name, org_id=org_id)` → scoped → global → DB (workflow_templates)

**Patrón auth en endpoints:**
- Dependencies: `Depends(require_org_id)`, `Depends(verify_supabase_jwt)`, `Depends(verify_org_membership)`
- Verificado en: `src/api/middleware.py:66-152`
- Algoritmo: ES256 (JWKS) + HS256 (legacy), detección automática desde JWT header

**Patrón scheduler:**
- Jobs definidos en: `src/scheduler/bartenders_jobs.py`, `src/scheduler/health_check.py`
- Framework: APScheduler (`apscheduler>=3.10.0`)

**Patrón MCP tool resolution (nuevo — Paso 1):**
- Formato: `mcp:{server_name}:{tool_name}` (3 partes por split `:` max 2)
- Resolución: `AgentFactory.resolve_tools(allowed_tools, org_id, async_mode=True/False)`
- Path sync: omite MCP tools con warning
- Path async: conecta vía `MCPPool.get().get_tools(org_id, server)` → filtra por `tool.name`
- Verificado en: `src/crews/factory.py:18-133`

### Convenciones de naming (de `proyecto-config.json`)
- Backend: `snake_case` (funciones/variables), `PascalCase` (clases)
- Archivos: `snake_case`
- DB tables: `snake_case`
- Imports: absolutos (`src.xxx.xxx`)
- Modelos: Pydantic BaseModel + dataclasses
- Tests: `test_*.py`

### Estructura de carpetas del proyecto
```
src/
├── api/
│   ├── main.py              # FastAPI app
│   ├── middleware.py         # Auth dependencies
│   └── routes/               # Endpoint modules
├── cli/
│   ├── main.py              # Typer entry point (fap)
│   ├── config.py            # CLI config
│   ├── utils.py             # CLI utilities
│   └── commands/            # CLI subcommands
├── crews/
│   ├── base_crew.py         # Single-agent crew execution
│   ├── factory.py           # Agent/Task factory with MCP support
│   └── bartenders/          # Domain-specific crews
├── db/
│   ├── session.py           # Supabase client factories
│   ├── vault.py             # Secrets management
│   ├── memory.py            # Vector memory
│   └── client.py            # Low-level client
├── events/
│   └── store.py             # Event persistence
├── flows/
│   ├── base_flow.py         # Base flow class
│   ├── registry.py          # Flow registry
│   ├── architect_flow.py    # Agent generation
│   ├── dynamic_flow.py      # JSON-defined workflows
│   ├── multi_crew_flow.py   # Multi-agent orchestration
│   └── workflow_definition.py # Pydantic workflow model
├── guardrails/
│   └── base_guardrail.py    # Approval + quota guards
├── mcp/
│   ├── server.py            # MCP server
│   ├── tools.py             # MCP tool definitions
│   ├── handlers.py          # MCP request handlers
│   ├── sanitizer.py         # Input sanitization
│   ├── auth.py              # MCP auth (JWT)
│   └── flow_to_tool.py      # Bridge: Flow → MCP Tool
├── scheduler/
│   ├── health_check.py      # System health monitoring
│   └── bartenders_jobs.py   # Domain-specific cron jobs
├── services/
│   ├── bundle_manager.py    # Bundle processing
│   ├── security_guard.py    # Code safety scanner
│   ├── import_service.py    # Bundle import
│   └── integrity.py         # Integrity checks
├── tools/
│   ├── registry.py          # Tool registry
│   ├── base_tool.py         # Base tool class
│   ├── mcp_pool.py          # MCP connection pool
│   ├── service_connector.py # HTTP integrations
│   ├── builtin.py           # Built-in tools
│   ├── analytical.py        # Analytical tools
│   └── demo/                # Demo tools
└── config.py                # Pydantic settings
```

### Dependencias instaladas (de `pyproject.toml`)

**Directas:**
- fastapi>=0.115.0, uvicorn[standard]>=0.32.0
- pydantic>=2.10.0, pydantic-settings>=2.6.0
- supabase>=2.10.0
- anthropic>=0.40.0, openai>=1.58.0
- PyJWT>=2.0.0, python-dotenv>=1.0.0
- httpx>=0.28.0, structlog>=24.4.0
- apscheduler>=3.10.0, python-dateutil>=2.9.0
- mcp>=1.0.0,<2.0.0, sse-starlette>=0.21.0
- RestrictedPython>=7.0, typer>=0.12.0
- packaging>=24.0, watchdog>=4.0.0

**Opcionales (`[crew]`):**
- crewai>=0.100.0, crewai-tools>=0.20.0

**Dev:**
- pytest>=8.3.0, pytest-asyncio>=0.24.0, pytest-mock>=3.14.0, pytest-cov>=6.0.0, ruff>=0.8.0

---

## 4. Decisiones de Arquitectura Tomadas

### Patrones en uso
- **Estado:** `BaseFlowState` (dataclass) con transiciones start→complete/fail, persistida en `snapshots` table
- **Persistencia:** Supabase direct queries + RPC functions. Sin ORM.
- **Auth:** Middleware FastAPI con JWKS (ES256) + fallback HS256. Tenant isolation via `org_id` en RLS policies.
- **Tool Resolution:** Centralizada en `AgentFactory.resolve_tools()` — fuente única para regular + MCP tools.
- **MCP:** Conexiones persistentes via `MCPPool` con circuit breaker (5 fallos → 60s cooldown). Tools MCP solo en path async.

### Tecnologías elegidas
- **CrewAI** como framework de agentes (dependencia opcional). Permite instalaciones sin CrewAI para uso solo con Flows nativos.
- **MCP (Model Context Protocol)** para integraciones externas estandarizadas. Stdio + SSE.
- **Typer** para CLI (`fap`). Comandos registrados en `src/cli/main.py`.
- **RestrictedPython** para sandboxing de skills dinámicas desde DB.

### Correcciones al plan documentadas
1. **Resolución de tools:** El plan original apuntaba a `BaseCrew._resolve_tools` como punto de modificación. Verificación contra código reveló que es dead code — `run()` y `run_async()` usan `AgentFactory.create_agent()` directamente. Corrección aplicada en Paso 1: `resolve_tools()` centralizado en `factory.py`.
2. **Sync/Async bifurcation:** `MCPPool.get_tools()` es async pero `create_agent()` es sync. Solución: `create_agent()` (sync_mode=False) omite MCP tools; `create_agent_async()` (async_mode=True) las resuelve.

### Herramientas DX detectadas
| Herramienta | Comando | Función |
|---|---|---|
| `fap validate-tools` | `fap validate-tools --tool "..." --org-id ...` | Valida `allowed_tools` contra registry y MCP servers antes de runtime |
| `fap validate` | `fap validate <bundle_path>` | Valida estructura, integridad y seguridad de bundles |
| `ruff check` | `ruff check src/ tests/` | Linting rápido |
| `pytest` | `pytest tests/unit/` | Tests unitarios |

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Decisiones Tomadas | Notas |
|------|--------|----------------------|-------------------|-------|
| 1 — Mejora de la Infraestructura de Herramientas | ✅ APROBADO | `DEVS/IMPLEMENTED/details4agents/01-mejora-infraestructura-herramientas/` | Resolución centralizada en `factory.py`. MCP solo en path async. `crewai-tools` como dependencia opcional con `ImportError` graceful. | 15/15 criterios cumplidos. 21 tests pass. 0 lint errors. |

---

## 6. Criterios Generales de Aceptación MVP

- [x] Happy path funciona end-to-end.
- [x] Errores se manejan sin crash (try/except con feedback al usuario).
- [x] Datos se persisten correctamente.
- [x] Validaciones de input presentes.
- [x] Código ejecuta sin errores ni warnings nuevos.
- [x] Herramientas DX detectadas/propuestas: `fap validate-tools`.
- **NO se requiere para MVP:** retry con backoff, caching avanzado, rate limiting, observabilidad avanzada, optimización de performance extrema.
