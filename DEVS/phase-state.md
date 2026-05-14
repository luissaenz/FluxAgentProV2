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
| 2 | Crear endpoint `POST /api/bundles/export` | ✅ Completado |
| 3 | Endpoints CRUD para templates de agentes | ✅ Completado |
| 4 | Builder visual — UI con ReactFlow | ✅ Completado |

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
| Endpoint `POST /api/bundles/export` | `src/api/routes/bundles.py:199-210` | Handler + validación goal/backstory | `Depends(require_org_id)` |
| `ExportService` orquestador | `src/services/export_service.py:21-66` | `export(payload) -> tuple[bytes, str]` | Reutiliza `BundleManager.create_bundle()` |
| Modelos export Pydantic | `src/services/bundle_schemas.py:102-116` | `AgentExportItem`, `ExportBundleRequest`, `SkillExportItem` | Validación campo por campo con Pydantic |
| CLI `fap bundle export` | `src/cli/commands/bundle_export.py:34-135` | Typer command `bundle export` | Dogfooding: usa `ExportService` |
| CLI registro `app.add_typer(bundle_app, ...)` | `src/cli/main.py:15,73` | Import + registro `bundle` sub-app | Sub-comando `bundle export` |
| Script helper `bundle_validator.py` | `scripts/bundle_validator.py` | Validar estructura ZIP exportado | Opcional, no bloqueante |
| Tests unitarios export | `tests/unit/test_bundle_export.py` | 7 tests: validación, generación, edge cases | 7/7 pasan |
| Tests integración round-trip | `tests/integration/test_bundle_export_roundtrip.py` | 3 tests: process_zip, mock import, estructura | 3/3 pasan |
| Tabla `agent_templates` | `supabase/migrations/030_agent_templates.sql:10-21` | Global sin `org_id`, RLS SELECT auth, ALL service_role | Índice parcial `UNIQUE(name) WHERE is_system=TRUE` |
| Endpoint `GET /api/templates` | `src/api/routes/templates.py:54-67` | Lista + filtro `?category=` + `count` | Sin `require_org_id` |
| Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:70-83` | Detalle con `soul_json`, 404 si no existe | `maybe_single()` |
| Modelos Pydantic templates | `src/api/routes/templates.py:25-51` | `TemplateInfo`, `TemplateListResponse`, `TemplateDetailResponse` | Consistente con `tools.py` |
| CLI `fap templates seed` | `src/cli/commands/templates_seed.py:140-220` | Seed 8 system templates + `--dry-run` + `--reset` | Check-then-insert idempotente |
| CLI registro `templates` sub-app | `src/cli/main.py:33,58` | Import + `add_typer(templates_app, name="templates")` | Sub-comando `templates seed` |
| Tests unitarios templates | `tests/unit/test_templates.py` | 7 tests: list, filter, detail, 404, auth, soul_json | 7/7 pasan |
| Endpoint `POST /agents` | `src/api/routes/agents.py:51-92` | `AgentCreate` + `AgentResponse` + upsert logic | `require_org_id` + `TenantClient` (corrección D4 RLS) |
| CLI `fap agent create` | `src/cli/commands/agent_create.py:30-134` | Typer `agent` sub-app | `--role`, `--goal`, `--backstory`, `--tools`, `--dry-run`, `--org-id`, LLM flags |
| CLI registro `agent` sub-app | `src/cli/main.py:14,77` | Import + `add_typer(agent_app, name="agent")` | Sub-comando `agent create` |
| Página `/builder` | `dashboard/app/(app)/builder/page.tsx` | Entry page `'use client'` | Orquesta `BuilderLayout` |
| `BuilderLayout` component | `dashboard/components/builder/BuilderLayout.tsx` | Split 60/40 responsive | `lg:grid-cols-[60%_40%]`, stack vertical mobile |
| `AgentForm` component | `dashboard/components/builder/AgentForm.tsx` | 11 campos: react-hook-form + zodResolver | useQuery `GET /api/tools/available`, `POST /agents` |
| `BuilderCanvas` component | `dashboard/components/builder/BuilderCanvas.tsx` | ReactFlow vacío `dynamic import ssr:false` | Placeholder Paso 07 |
| `ToolMultiSelect` component | `dashboard/components/builder/ToolMultiSelect.tsx` | Checkboxes + búsqueda + badges por source | Custom sin deps extra |
| Sidebar "Builder" entry | `dashboard/components/nav-main.tsx:50` | `{ title: 'Builder', url: '/builder', icon: Wand2 }` | Añadido a `defaultNavItems` |
| Constante `PROVIDER_MODELS` | `dashboard/lib/constants.ts:16-21` | Mapa estático con 4 providers | groq, openai, anthropic, openrouter |
| Deps frontend `reactflow` v11 | `dashboard/package.json` | ReactFlow v11 para builder canvas | No @xyflow/react v12 (rename) |
| Deps frontend `zod` | `dashboard/package.json` | Validación Zod en AgentForm | `@hookform/resolvers` ya instalado (v5.2.2) |

### 📦 Archivado — Paso 1

| Archivos | Destino |
|---|---|
| `analisis-FINAL.md`, `analisis-*-*.md` (6 análisis), `validacion.md` | `DEVS/IMPLEMENTED/guiAgentGenerator/01-Crear-endpoint-GET-api-tools-available/` |

### 📦 Archivado — Paso 2

| Archivos | Destino |
|---|---|
| `analisis-FINAL.md`, `analisis-*-*.md` (6 análisis), `validacion.md` | `DEVS/IMPLEMENTED/guiAgentGenerator/02-Crear-endpoint-POST-api-bundles-export/` |

### 📦 Archivado — Paso 3

| Archivos | Destino |
|---|---|
| `analisis-FINAL.md`, `analisis-*-*.md` (6 análisis), `validacion.md` | `DEVS/IMPLEMENTED/guiAgentGenerator/03-Endpoints-CRUD-para-templates-de-agentes/` |

### 📦 Archivado — Paso 4

| Archivos | Destino |
|---|---|
| `analisis-FINAL.md`, `analisis-*-*.md` (8 análisis), `validacion.md` | `DEVS/IMPLEMENTED/guiAgentGenerator/04-Builder-visual-UI-con-ReactFlow/` |

### 📝 Correcciones al plan aplicadas

| ID | Corrección | Código |
|---|---|---|
| D1 | `ToolMetadata` sin `category` → derivar de `tags[0]`. NO modificar dataclass. | `tools.py:87` — `meta.tags[0] if meta.tags else "general"` |
| D2 | MCP no tiene `list_all_tools()` → iterar `org_mcp_servers` + `asyncio.gather()` | `tools.py:109-146` |
| D3 | Timeout <500ms irreal con MCP → local <500ms, MCP timeout 5s, degradado graceful | `tools.py:124` — `timeout=5`, catch exceptions |
| D4 | Router en `main.py`, NO en `__init__.py` | `main.py:31,112` |
| D5 | `list_tools()` retorna solo nombres → `get_metadata()` por cada uno | `tools.py:75-78` |
| D6 | Tools DB-loaded sin warmup en listado → documentado como limitación MVP | Sin implementar (correcto) |

#### Paso 02 — POST /api/bundles/export

| ID | Corrección | Código |
|---|---|---|
| D1 | `StreamingResponse` → `Response` (ZIP en memoria, no streaming real) | `bundles.py:241` — `Response(content=zip_bytes)` |
| D2 | `skills [{name,code}]` → `Dict[str,str]` para `create_bundle()` | `export_service.py:52-60` — convierte + `.py` en key (necesario round-trip) |
| D3 | `ExportService` como orquestador separado (patrón `ImportService`) | `export_service.py:21-66` |
| D4 | `flows` excluido de MVP, pasar `flows=[]` | `export_service.py:65` — `flows=[]` |

#### Paso 03 — Endpoints CRUD para templates de agentes

| ID | Corrección | Código |
|---|---|---|
| D1 | Router en `main.py` (NO `__init__.py`) | `main.py:30,113` — import + `include_router` |
| D2 | Tabla GLOBAL sin `org_id` (patrón `service_catalog`) | `030_agent_templates.sql:10-21` — sin columna `org_id` |
| D3 | Seed vía CLI + script, NO en migración SQL | `templates_seed.py` + `cli/main.py:33,58` |
| D4 | Endpoints sin `require_org_id` (catálogo público) | `templates.py:54-67,70-83` — sin `Depends(require_org_id)` |
| D5 | Idempotencia seed → check-then-insert (no upsert) | `templates_seed.py:183-193` — `SELECT` + `INSERT` condicional por índice parcial `UNIQUE WHERE` |
| D6 | Emojis reemplazados por Rich markup (cp1252 compat) | `templates_seed.py:191,208,211` — `OK`, `FAIL`, `-` |

#### Paso 04 — Builder visual — UI con ReactFlow

| ID | Corrección | Código |
|---|---|---|
| D1 | `reactflow` v11 instalado, no `@xyflow/react` v12 (rename drástico) | `package.json` + `BuilderCanvas.tsx` |
| D3 | `Input type="number"` para max_iter, no Slider (componente no existe en shadcn/ui) | `AgentForm.tsx:275-284` |
| D4 | **CRÍTICA: `POST /agents` con `TenantClient`** para RLS — el plan decía "guardar directo desde frontend sin nuevo endpoint" pero `app.org_id` solo lo setea middleware backend | `agents.py:51-92` — `require_org_id` + `get_tenant_client(org_id)` |
| D5 | `ToolMultiSelect` custom con checkboxes + badges, sin deps externas (Command/Popover no instalados) | `ToolMultiSelect.tsx` — búsqueda/filtro + agrupación por source |
| D7 | `soul_json` plano: `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}` | `agent_create.py:79-88` + `AgentForm.tsx:117-131` |
| D8 | Upsert vía update-if-exists + insert si no existe (no `.upsert()` directo con Supabase) | `agents.py:62-92` |
| D9 | Nav sidebar "Builder" añadido en Paso 04 (no paso 09) | `nav-main.tsx:50` |
| D10 | `PROVIDER_MODELS` estático en `constants.ts` con 4 providers | `constants.ts:16-21` |
| D11 | `model` no se migra; `llm_model` va en `soul_json.llm_model` | `AgentForm.tsx:117-131` — `soul_json` plano |

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
- `agent_templates(id UUID, name TEXT NOT NULL, description TEXT, category TEXT NOT NULL, soul_json JSONB, suggested_tools TEXT[], max_iter INTEGER, is_system BOOLEAN, ...)` — tabla global sin `org_id`, RLS SELECT auth, ALL service_role

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
| `/agents` (POST create) | `src/api/routes/agents.py` | POST | `require_org_id` — crea/upsert agente con `soul_json` + `allowed_tools` + `max_iter` |
| `/bundles/...` | `src/api/routes/bundles.py` | * | `require_org_id` |
| `/mcp/...` | `src/api/routes/mcp.py` | * | `require_org_id` |
| `/integrations/...` | `src/api/routes/integrations.py` | * | `require_org_id` |
| `/api/templates` | `src/api/routes/templates.py` | GET | None (catálogo público) |
| `/api/templates/{id}` | `src/api/routes/templates.py` | GET | None (catálogo público) |
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

**5. Patrón tabla global sin `org_id` — catálogo público**
```sql
-- Migración 030_agent_templates.sql:10,25-29
CREATE TABLE IF NOT EXISTS agent_templates (...);
-- Sin columna org_id
CREATE POLICY "agent_templates_read" ON agent_templates
    FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "agent_templates_write" ON agent_templates
    FOR ALL USING (auth.role() = 'service_role');
```
Tablas globales sin tenant isolation. SELECT requiere autenticación, escritura solo `service_role`. Mismo patrón que `service_catalog` (mig 024).

**6. Patrón seed vía CLI — check-then-insert idempotente**
```python
# src/cli/commands/templates_seed.py:183-193
existing = db.table("agent_templates").select("id")\
    .eq("name", template["name"]).eq("is_system", True).execute()
if existing.data:
    console.print(f"  [dim]-[/dim] {template['name']} (already exists, skipped)")
    skipped += 1
    continue
db.table("agent_templates").insert({...}).execute()
```
Seed idempotente compatible con índices parciales `UNIQUE(...) WHERE`. Reemplaza `upsert()` que no soporta `WHERE` en PostgREST.

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
| Response vs StreamingResponse | `BundleManager.create_bundle()` genera ZIP en memoria → `Response(content=bytes)`. Sin beneficio de streaming. Post-MVP >50MB migrar a `StreamingResponse`. | `bundles.py:241` |
| ExportService en archivo separado | Consistente con `ImportService`. Separa concerns: handler maneja HTTP, service maneja lógica negocio. Permite test unitario sin FastAPI. | `export_service.py:21-66` |
| Skills key incluye `.py` | `create_bundle()` escribe `skills/{filename}` y `_parse_file_content()` requiere `.py` suffix. Usar `s.name` sin extensión rompería round-trip import. | `export_service.py:55-58` |
| Validación goal/backstory en handler | Responsabilidad del endpoint (contrato HTTP), no del service. Incluye longitud mínima 10 chars (mitigación §258). | `bundles.py:215-238` |
| Sin registro en `bundle_imports` | Export stateless. No persiste registro de exportación. | `export_service.py:28-70` |
| Tabla global `agent_templates` sin `org_id` | Catálogo público de templates. Mismo patrón que `service_catalog` (mig 024). Post-MVP: custom templates por org → migración adicional con `org_id`. | `030_agent_templates.sql:10-21` |
| Endpoints públicos sin `require_org_id` | Templates son catálogo de referencia. Consistente con `integrations.py`. Autenticación vía RLS (auth.role() = 'authenticated'). | `templates.py:54-67,70-83` |
| RLS: SELECT auth, ALL service_role | Lectura requiere autenticación. Escritura solo service_role (seed vía CLI). | `030_agent_templates.sql:25-29` |
| Seed vía CLI + script, NO en migración SQL | Consistente con `seed_system_bundles.py`. `--dry-run`, `--reset`. Check-then-insert idempotente. | `templates_seed.py:140-220` |
| Índice parcial `UNIQUE(name) WHERE is_system = TRUE` | Solo system templates son únicos por nombre. Custom templates (futuro) usarán `UNIQUE(org_id, name)`. | `030_agent_templates.sql:32-33` |
| `soul_json` sin validación Pydantic en API | DB almacena JSONB, endpoint retorna `Dict[str, Any]`. Validación de estructura en seed script. Post-MVP: validator. | `templates.py:37-41` |
| Response incluye `count` | Consistente con `tools.py`. `TemplateListResponse.count`. | `templates.py:38,66` |
| `POST /agents` con `TenantClient` obligatorio | RLS `agent_catalog_tenant_isolation` usa `current_setting('app.org_id')` — solo el backend puede setear esta variable vía RPC. Frontend browser client NO puede. Sin este endpoint el Save Agent falla con 42501. Corrección crítica D4 al plan. | `agents.py:51-92` |
| Upsert update-or-insert | `UNIQUE(org_id, role)` hace que `.insert()` falle en duplicado. Flow: SELECT existente → UPDATE si existe, INSERT si no. Permite re-guardar/editar sin error 409. | `agents.py:62-92` |
| `soul_json` plano sin anidación | Estructura: `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}`. Sin sub-objeto `config`. Consistente con cómo `agents/page.tsx:62` ya accede a `soul_json` como `Record<string, string>`. | `agent_create.py:79-88` |
| `reactflow` v11, no `@xyflow/react` v12 | v12 cambió API drásticamente. v11 estable por consistencia con plan y mayoría de agentes. Migración a v12 post-MVP si necesario. | `BuilderCanvas.tsx` — `import('reactflow')` |
| `Input type="number"` para max_iter, no Slider | Componente `Slider` no existe en shadcn/ui. Misma funcionalidad sin dep extra (`@radix-ui/react-slider`). Slider visual post-MVP. | `AgentForm.tsx:275-284` |
| `ToolMultiSelect` custom sin deps externas | Checkboxes nativos + búsqueda/filtro + badges. Sin `cmdk`, `@radix-ui/react-popover`, ni `@radix-ui/react-checkbox` — no instalados. Post-MVP: Command combobox. | `ToolMultiSelect.tsx` |
| `PROVIDER_MODELS` estático en frontend | Sin endpoint para listar modelos por provider en MVP. Mapa con ≥2 modelos/provider. Post-MVP: `GET /api/llm/models?provider=`. | `constants.ts:16-21` |
| Nav sidebar "Builder" en Paso 04 | Ruta `/builder` accesible desde el momento en que existe la página. No pospuesto a Paso 09. | `nav-main.tsx:50` |

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Decisiones Tomadas | Notas |
|---|---|---|---|---|---|
| 01-Crear-endpoint-GET-api-tools-available | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/01-Crear-endpoint-GET-api-tools-available/` | `b26dbe9` | ToolInfo con Literal source; MCP con timeout 5s; category derivada de tags[0]; router en main.py | Validación aprobada. 1 🟡 (dogfooding no verificado). |
| 02-Crear-endpoint-POST-api-bundles-export | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/02-Crear-endpoint-POST-api-bundles-export/` | `af35a0a` | ExportService orquestador; Response vs StreamingResponse; skills key con `.py` para round-trip; validación goal/backstory + min_length en handler | Validación aprobada. 0 issues. |
| 03-Endpoints-CRUD-para-templates-de-agentes | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/03-Endpoints-CRUD-para-templates-de-agentes/` | `992a1d1` | Tabla global sin org_id; endpoints públicos sin auth; seed CLI idempotente; índice parcial UNIQUE WHERE; check-then-insert compatible con partial index | Validación rechazada (ID-001 upsert + partial index). Corregido a check-then-insert. Queda pendiente verificación live Supabase post-migración 030. |
| 04-Builder-visual-UI-con-ReactFlow | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/04-Builder-visual-UI-con-ReactFlow/` | `6d9539c` | POST /agents con TenantClient (RLS fix D4); reactflow v11 + dynamic import ssr:false; AgentForm react-hook-form + zod; ToolMultiSelect custom; PROVIDER_MODELS estático; soul_json plano; upsert update-or-insert; sidebar Builder en nav-main.tsx | Implementación completa. 0 errores lint backend + frontend. Criterios de aceptación cubiertos. Tarea 0 DX: `fap agent create`. |

---

## 6. Criterios Generales de Aceptación MVP

- ✅ Happy path funciona end-to-end
- ✅ Errores manejados sin crash (try/except con feedback)
- ✅ Datos persistidos correctamente (tool_registry + org_mcp_servers)
- ✅ Validaciones de input presentes (Query regex, require_org_id)
- ✅ Código ejecuta sin errores ni warnings nuevos
- ✅ Tooling DX: `fap tools list` — listado de tools desde CLI sin dashboard
- ✅ Tooling DX: `fap bundle export` — exporta agentes DB a ZIP desde CLI
- ✅ Tests automatizados implementados: 7 unit + 3 integración (round-trip)
- ✅ ZIP exportado es re-importable vía `POST /api/bundles/import` (round-trip verificado)
- ✅ Tests unitarios templates: 7/7 (list, filter, detail, 404, auth, soul_json)
- ✅ Migración `030_agent_templates.sql` con tabla + RLS + índices
- ✅ Seed idempotente: check-then-insert compatible con índice parcial `UNIQUE WHERE`
- ✅ POST /agents con TenantClient: RLS respetada vía backend (corrección D4 al plan)
- ✅ AgentForm 11 campos con react-hook-form + zodResolver: validación inline
- ✅ BuilderLayout split 60/40 responsive con Tailwind: ReactFlow izquierda + formulario derecha
- ✅ BuilderCanvas ReactFlow placeholder con dynamic import + ssr:false
- ✅ ToolMultiSelect custom con búsqueda/filtro + agrupación por source (local/mcp)
- ✅ Sidebar con entrada "Builder" navegable a `/builder`
- ✅ PROVIDER_MODELS con 4 providers y ≥2 modelos cada uno
- ✅ Zod rechaza submit sin role/goal/backstory con error inline
- ✅ Zod rechaza max_iter <1 o >10
- ✅ LLM Provider select cambia dinámicamente opciones de LLM Model

### Herramientas DX detectadas/propuestas
| Herramienta | Ubicación | Automatiza |
|---|---|---|
| `fap tools list` | `src/cli/commands/tools_list.py` | Listar tools locales + MCP desde terminal. `--org-id`, `--source`, `--json` |
| `fap validate-tools` | `src/cli/commands/validate_tools.py` | Validar tools contra agent configs (existente pre-Paso 1) |
| `fap bundle export` | `src/cli/commands/bundle_export.py` | Exportar agentes DB a ZIP bundle desde CLI. `--org-id`, `--output`, `--include-skills`, `--roles` |
| `fap templates seed` | `src/cli/commands/templates_seed.py` | Insertar 8 system templates en Supabase desde CLI. `--dry-run`, `--reset`. Setup 15min → 1s. |
| `fap agent create` | `src/cli/commands/agent_create.py` | Crear agente desde terminal vía POST /agents. `--role`, `--goal`, `--backstory`, `--tools`, `--max-iter`, `--llm-provider`, `--llm-model`, `--verbose`, `--reasoning`, `--inject-date`, `--memory`, `--dry-run`. Dogfooding: validar backend antes de UI. |
| `bundle_validator.py` | `scripts/bundle_validator.py` | Validar estructura de ZIP exportado sin consumir endpoint |
| Builder UI (`/builder`) | `dashboard/app/(app)/builder/page.tsx` | Interfaz visual split 60/40: canvas ReactFlow + formulario de agente con 11 campos. Save vía POST /agents con RLS. |
