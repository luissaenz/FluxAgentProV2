# 🗺️ Contexto de Fase — FluxAgentPro-v2

> **Documento fuente de verdad para todos los agentes.** Verificado contra código real.

---

## 1. Resumen de Fase

**Fase activa:** `guiAgentGenerator`
**Objetivo:** Replicar experiencia de creación visual de agentes (Crew Studio) dentro del dashboard FAP, sobre stack propio (Next.js + ReactFlow + FastAPI + Supabase).

### Pasos en orden

| # | Paso | Estado |
|---|------|--------|
| 1 | Crear endpoint `GET /api/tools/available` | ✅ Completado |
| 2 | Crear endpoint `POST /api/bundles/export` | ⬜ Pendiente |
| 3 | Endpoints CRUD para templates de agentes | ⬜ Pendiente |
| 4 | Builder visual — UI con ReactFlow | ⬜ Pendiente |

### Dependencias entre pasos
- Paso 2 requiere Paso 1 (tools list para export)
- Paso 4 requiere Pasos 1-3 (tools + export + templates para builder)

---

## 2. Estado Actual del Proyecto

> Verificado contra código fuente en `src/` y `supabase/migrations/`.

### ✅ Implementado y funcional

| Componente | Archivo | Línea | Notas |
|---|---|---|---|
| Endpoint `GET /api/tools/available` | `src/api/routes/tools.py:46-63` | Handler + modelos Pydantic | Retorna `ToolsListResponse` con `ToolInfo[]` |
| Router registrado en API | `src/api/main.py:31,112` | Import + `include_router` | No en `__init__.py` (corrección D4) |
| ToolRegistry singleton | `src/tools/registry.py:272` | `tool_registry = ToolRegistry()` | `list_tools()` + `get_metadata()` |
| MCPPool singleton | `src/tools/mcp_pool.py:42-56` | `get()` classmethod | Circuit breaker + retry exponential |
| Auth middleware `require_org_id` | `src/api/middleware.py:66` | FastAPI Depends | Extrae `X-Org-ID` header |
| CLI `fap tools list` | `src/cli/commands/tools_list.py:29-64` | Typer sub-app `tools` | `--org-id`, `--source`, `--json` |
| CLI registro `app.add_typer(tools, ...)` | `src/cli/main.py:35,56` | Import + registro | Sub-comando `tools list` |
| Flujo warmup + health checks | `src/api/main.py:48-77` | lifespan handler | warmup_all_active_tenants() + run_health_checks() |
| Tool register decorator | `src/tools/registry.py:276-287` | `@register_tool(...)` | Uso en `src/tools/builtin` |
| MCP server query | `src/tools/mcp_pool.py:122-131` | `get_service_client()` | `.table("org_mcp_servers").select("*")` |

### 📦 Archivado — Paso 1

| Archivos | Destino |
|---|---|
| `analisis-FINAL.md`, `analisis-*-*.md` (6 análisis), `validacion.md` | `DEVS/IMPLEMENTED/guiAgentGenerator/01-Crear-endpoint-GET-api-tools-available/` |

### 📝 Correcciones al plan aplicadas

| ID | Corrección | Código |
|---|---|---|
| D1 | `ToolMetadata` sin `category` → derivar de `tags[0]`. NO modificar dataclass. | `tools.py:87` — `meta.tags[0] if meta.tags else "general"` |
| D2 | MCP no tiene `list_all_tools()` → iterar `org_mcp_servers` + `asyncio.gather()` | `tools.py:109-146` |
| D3 | Timeout <500ms irreal con MCP → local <500ms, MCP timeout 5s, degradado graceful | `tools.py:124` — `timeout=5`, catch exceptions |
| D4 | Router en `main.py`, NO en `__init__.py` | `main.py:31,112` |
| D5 | `list_tools()` retorna solo nombres → `get_metadata()` por cada uno | `tools.py:75-78` |
| D6 | Tools DB-loaded sin warmup en listado → documentado como limitación MVP | Sin implementar (correcto) |

---

## 3. Contratos Técnicos Vigentes

### Stack detectado
- **Backend:** Python ≥3.12 + FastAPI (Pydantic v2)
- **Frontend:** TypeScript + Next.js (`dashboard/`)
- **DB:** Supabase (PostgreSQL) vía `supabase` Python client
- **Auth:** PyJWT (ES256/HS256 via JWKS middleware)
- **Package manager:** `uv` (backend), `npm` (frontend)

### Modelos de datos (de migraciones reales)
- `organizations(id UUID, name TEXT, created_at TIMESTAMPTZ)`
- `org_members(id UUID, org_id UUID REFERENCES organizations, user_id UUID, role TEXT)`
- `agent_catalog(id UUID, org_id UUID, role TEXT, goal TEXT, backstory TEXT, ...)` — con RLS tenant_isolation
- `org_mcp_servers(id UUID, org_id UUID, name TEXT, command TEXT, args JSONB, secret_name TEXT, is_active BOOLEAN)`
- `skill_catalog(id UUID, org_id UUID, name TEXT, code_source TEXT, ...)`
- `flow_presentations`, `tickets`, `agent_metadata`, `service_catalog`, `conversations`, `workflow_templates`, etc.

### Endpoints / APIs (rutas reales)
| Ruta | Archivo | Método | Auth |
|---|---|---|---|
| `/api/tools/available?source=&category=` | `src/api/routes/tools.py` | GET | `require_org_id` |
| `/flows/available` | `src/api/routes/flows.py` | GET | `require_org_id` |
| `/flows/hierarchy` | `src/api/routes/flows.py` | GET | `require_org_id` |
| `/flows/{flow_type}/run` | `src/api/routes/flows.py` | POST | `require_org_id` |
| `/webhooks/...` | `src/api/routes/webhooks.py` | POST | `require_org_id` |
| `/tasks/...` | `src/api/routes/tasks.py` | * | `require_org_id` |
| `/approvals/...` | `src/api/routes/approvals.py` | * | `require_org_id` |
| `/chat/...` | `src/api/routes/chat.py` | * | `require_org_id` |
| `/agents/...` | `src/api/routes/agents.py` | * | `require_org_id` |
| `/bundles/...` | `src/api/routes/bundles.py` | * | `require_org_id` |
| `/mcp/...` | `src/api/routes/mcp.py` | * | `require_org_id` |
| `/integrations/...` | `src/api/routes/integrations.py` | * | `require_org_id` |
| `/health` | `src/api/main.py` | GET | None |

### Patrones de código en uso

**1. Patrón RLS — tenant_isolation**
```sql
-- Migración 004_agent_catalog.sql:22-23
CREATE POLICY "agent_catalog_tenant_isolation" ON agent_catalog
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
```
Variable `app.org_id` seteada por middleware JWT. Cast a text explícito.

**2. Patrón registro de tools — decorator**
```python
# src/tools/registry.py:276-287
@register_tool(name="fetch_url", description="...", tags=["web"])
class FetchURLTool(OrgBaseTool): ...
```
`ToolRegistry.register()` → `ToolMetadata()` almacenado en `_metadata[name]`. Singleton global `tool_registry`.

**3. Patrón auth en endpoints — FastAPI Depends**
```python
# src/api/middleware.py:66
async def require_org_id(request: Request) -> str:
    org_id = request.headers.get("x-org-id")
    if not org_id:
        raise HTTPException(400, "X-Org-ID header required")
    return org_id
```
Uso: `org_id: str = Depends(require_org_id)` en cada endpoint.

**4. Patrón scheduler — background tasks**
```python
# src/api/main.py:67-71
from src.scheduler.health_check import run_health_checks
asyncio.create_task(run_health_checks())
```
Jobs definidos en `src/scheduler/` (health_check.py, bartenders_jobs.py).

### Convenciones de naming (de proyecto-config.json)
- Backend: `snake_case`
- Archivos: `snake_case.py`
- DB tables: `snake_case`
- Imports: absolutos (`from src.x.y import Z`)
- Modelos: Pydantic `BaseModel` + dataclasses
- Rutas: FastAPI `APIRouter` con `@router` decorators
- Tests: `test_*.py`

### Estructura de carpetas
```
src/
├── api/           # FastAPI routes + middleware
│   ├── main.py    # App entry, CORS, lifespan
│   ├── middleware.py  # JWT + org_id
│   └── routes/    # Endpoints por dominio
├── cli/           # FAP CLI (typer)
│   ├── main.py    # Typer app + command registration
│   └── commands/  # Cada comando como módulo
├── db/            # Supabase session + vault
├── tools/         # ToolRegistry + MCP pool
├── flows/         # FlowRegistry + generic flow
├── crews/         # CrewAI orchestration
├── services/      # Business logic (warmup, security_guard)
├── scheduler/     # Background jobs
├── events/        # Real-time events
├── state/         # State management
├── connectors/    # External connectors
├── guardrails/    # Security guardrails
├── utils/         # Helpers
├── mcp/           # MCP SDK integration
├── scripts/       # Seed scripts
├── config.py      # Settings (pydantic-settings)
```

### Dependencias instaladas (de pyproject.toml)
**Directas:** fastapi, uvicorn, pydantic, pydantic-settings, supabase, anthropic, openai, openpyxl, PyJWT, python-dotenv, httpx, structlog, apscheduler, python-dateutil, mcp, sse-starlette, RestrictedPython, typer, packaging, watchdog, tenacity
**Dev:** pytest, pytest-asyncio, pytest-mock, pytest-cov, pytest-timeout, ruff
**Opcionales:** crewai, crewai-tools

---

## 4. Decisiones de Arquitectura Tomadas

| Decisión | Detalle | Verificación |
|---|---|---|
| Auth vía JWT + JWKS | PyJWT con ES256/HS256 negotiation. `require_org_id` extrae `X-Org-ID` header | `src/api/middleware.py:66` |
| RLS con `app.org_id` | Variable de sesión seteada por middleware, cast a text | `004_agent_catalog.sql:23` |
| ToolRegistry singleton | Patrón mirror de FlowRegistry. `tool_registry` global | `src/tools/registry.py:272` |
| MCPPool singleton | Conexiones persistentes + circuit breaker (5 fails → 60s rest) | `src/tools/mcp_pool.py:42-56` |
| `category` derivada de `tags[0]` | NO modificar `ToolMetadata` dataclass (evita breaking change) | `src/api/routes/tools.py:87` |
| MCP listing sin gather timeout | Timeout por llamada individual (5s), no wrapper global | `src/api/routes/tools.py:124,146` |
| Sin cache en MVP | Cache post-MVP con `functools.lru_cache` + TTL | Decisión 3 del análisis |
| CLI `fap tools list` como DX | Reemplaza curl/Postman. Typer sub-app en `src/cli/main.py` | `src/cli/commands/tools_list.py` |
| `get_service_client()` para queries DB | Bypass RLS con filtro manual `.eq("org_id", ...)`. Consistente con integrations/mcp_pool | `src/api/routes/tools.py:111` |
| Response incluye `count` | Consistente con `flows.py` pattern | `src/api/routes/tools.py:63` |

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Decisiones Tomadas | Notas |
|---|---|---|---|---|---|
| 01-Crear-endpoint-GET-api-tools-available | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/01-Crear-endpoint-GET-api-tools-available/` | `b26dbe9` | ToolInfo con Literal source; MCP con timeout 5s; category derivada de tags[0]; router en main.py | Validación aprobada. 1 🟡 (dogfooding no verificado). |

---

## 6. Criterios Generales de Aceptación MVP

- ✅ Happy path funciona end-to-end
- ✅ Errores manejados sin crash (try/except con feedback)
- ✅ Datos persistidos correctamente (tool_registry + org_mcp_servers)
- ✅ Validaciones de input presentes (Query regex, require_org_id)
- ✅ Código ejecuta sin errores ni warnings nuevos
- ✅ Tooling DX: `fap tools list` — listado de tools desde CLI sin dashboard
- ⬜ Pendiente para pasos futuros: tests automatizados (Tarea 4 del plan)

### Herramientas DX detectadas/propuestas
| Herramienta | Ubicación | Automatiza |
|---|---|---|
| `fap tools list` | `src/cli/commands/tools_list.py` | Listar tools locales + MCP desde terminal. `--org-id`, `--source`, `--json` |
| `fap validate-tools` | `src/cli/commands/validate_tools.py` | Validar tools contra agent configs (existente pre-Paso 1) |
