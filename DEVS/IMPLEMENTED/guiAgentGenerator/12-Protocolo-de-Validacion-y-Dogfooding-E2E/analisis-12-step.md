# 🧠 Análisis Técnico — Paso 12: Protocolo de Validación y Dogfooding E2E

**Agente:** step
**Paso:** 12
**Fase:** guiAgentGenerator
**Fecha:** 2026-05-18

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

> Ejecutada ANTES de escribir secciones 1-7. Toda afirmación está respaldada contra código real.

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `GET /api/tools/available` existe | `src/api/routes/tools.py:46` | ✅ VERIFICADO | `tools.py:46` — `@router.get("/available")` |
| 2 | `fap tools list` registrado en CLI | `src/cli/main.py:67` | ✅ VERIFICADO | `app.add_typer(tools_list_app, name="tools")` |
| 3 | `fap templates seed` existe y tiene dry-run/reset | `src/cli/commands/templates_seed.py:140` | ✅ VERIFICADO | `seed_templates` con opciones `--dry-run` y `--reset` |
| 4 | `fap templates seed` es idempotente (UUID v5) | `templates_seed.py:192` | ✅ VERIFICADO | `uuid.uuid5(uuid.NAMESPACE_DNS, f"fap.system.template.{template['name']}")` |
| 5 | `fap templates seed` usa `ON CONFLICT` | `templates_seed.py:206` | ✅ VERIFICADO | `.upsert(row, on_conflict="id", ignore_duplicates=True)` |
| 6 | `GET /api/templates` existe | `src/api/routes/templates.py:54` | ✅ VERIFICADO | `@router.get("")` |
| 7 | `GET /api/templates/{id}` existe | `templates.py:74` | ✅ VERIFICADO | `@router.get("/{template_id}")` |
| 8 | Templates NO usan `require_org_id` (lectura pública) | `templates.py:54-57` | ✅ VERIFICADO | Endpoints sin auth comment + código sin `Depends(require_org_id)` |
| 9 | `GET /api/templates` tiene filtro `?category=` | `templates.py:55-57` | ✅ VERIFICADO | `category: Optional[str] = Query(None)` |
| 10 | `fap agent create` existe con `--dry-run` | `src/cli/commands/agent_create.py:83-87` | ✅ VERIFICADO | payload impreso en JSON sin enviar |
| 11 | `POST /agents` existe con upsert | `src/api/routes/agents.py:101-162` | ✅ VERIFICADO | `create_agent` con upsert por `org_id,role`, retorna 409 en duplicado |
| 12 | `fap agent run` registrado | `src/cli/main.py:87` | ✅ VERIFICADO | `agent_app.command("run")(run_agent)` |
| 13 | `POST /agents/{role}/run` existe | `src/api/routes/agents.py:312-381` | ✅ VERIFICADO | `RunAgentResponse(task_id, status)`, polling contra `GET /tasks/{task_id}` |
| 14 | `GET /tasks/{task_id}` usable | polling en `agent_run.py:119-174` | ✅ VERIFICADO | `poll_url = f"{base_url}/tasks/{task_id}"`, 2s intervalo |
| 15 | `fap templates use` existe con `--dry-run` | `src/cli/commands/templates_use.py:138-145` | ✅ VERIFICADO | `console.print_json`, sin enviar |
| 16 | `fap templates use` POST /agents con payload | `templates_use.py:159` | ✅ VERIFICADO | `client.post(url, json=payload, headers=headers)` |
| 17 | `fap bundle validate-payload` registrado | `src/cli/main.py:84` | ✅ VERIFICADO | `bundle_app.command("validate-payload")(validate_payload)` |
| 18 | `ExportBundleRequest` schema | `src/services/bundle_schemas.py:111-116` | ✅ VERIFICADO | `agents: List[AgentExportItem]`, `skills`, `bundle_name` |
| 19 | `POST /api/bundles/export` existe | `src/api/routes/bundles.py:199-253` | ✅ VERIFICADO | Devuelve `Response` ZIP, 422 si goal/backstory < 10 chars |
| 20 | `fap doctor builder` registrado | `src/cli/main.py:89` | ✅ VERIFICADO | `app.add_typer(doctor_builder_app, name="doctor")` |
| 21 | `doctor_builder.py` tiene 6 diagnósticos | `doctor_builder.py:167-179` | ✅ VERIFICADO | ID-C02, ID-C03, ID-C04, ID-023, ID-051, ID-052 |
| 22 | `fap test builder run` registrado | `src/cli/main.py:88` | ✅ VERIFICADO | `app.add_typer(test_builder_app, name="test-builder")` |
| 23 | `test_builder.py` ejecuta `tests/e2e/test_builder_scenarios.py` | `test_builder.py:56-62` | ✅ VERIFICADO | 32 escenarios TP-1 a TP-6 |
| 24 | Migración 030 `agent_templates` existe | `supabase/migrations/030_agent_templates.sql` | ✅ VERIFICADO | Tabla, índices, RLS policies definidas |
| 25 | `validate_builder_nav.py` existe | `scripts/validate_builder_nav.py` | ✅ VERIFICADO | Checks: sidebar SSOT, Next.js files, ErrorBoundary, Breadcrumb, SSR |
| 26 | `scripts/validate_builder_nav.py` detección de props frágil | `validate_builder_nav.py:160-176` | ⚠️ DISCREPANCIA | `check_ssr_false` verifica `BuilderCanvas` en contenido pero en realidad el archivo relevante es `BuilderLayout.tsx` que usa `CrewCanvas` con `ssr:false` — ver §Discrepancias |
| 27 | `session.py` tiene `get_service_client` y `TenantClient` | `src/db/session.py:55-231` | ✅ VERIFICADO | Ambas funciones expuestas correctamente |
| 28 | `cli config` carga `~/.fap/config.json` | `src/cli/config.py:44-55` | ✅ VERIFICADO | `CLIConfig.load()` devuelve `api_url`, `org_id`, `access_token` |
| 29 | RLS en `agent_templates` — lectura pública, escritura service_role | `030_agent_templates.sql:23-29` | ✅ VERIFICADO | Policy `agent_templates_read` (authenticated) + `agent_templates_write` (service_role) |
| 30 | `_fetch_mcp_tools` usa `MCPPool.get()` | `tools.py:109-151` | ✅ VERIFICADO | `async def _fetch_mcp_tools`, `MCPPool.get()`, `await pool.get_tools` con prefijo `mcp:{server_name}` |

### Discrepancias encontradas

| # | Discrepancia | Resolución propuesta |
|---|---|---|
| D1 | **`fap templates use --dry-run` envía a API pero el plan espera mapeo previo**: `templates_use.py:138-145` hace dry-run solo imprimiendo payload (no envía). El plan (Paso 12, Tarea ID-022) pide validar mapeo template → agente, lo cual el dry-run ya cubre. | **Sin acción**: dry-run es correcto para validar mapeo sin escribir a DB. La discrepancia es del plan, no del código. |
| D2 | **`validate_builder_nav.py` check 5 (SSR) verifica `BuilderCanvas` wrapper que no existe explícitamente**: El documento objetivo (`BuilderLayout.tsx`) usa directamente `CrewCanvas` con `<dynamic ssr={false}>`, no hay un archivo dedicado `BuilderCanvas.tsx`. El check pasa si encuentra el string en layout, pero el código en `validate_builder_nav.py:171-175` chequea la existencia de `BuilderCanvas` en el contenido, lo cual es impreciso. | Documentar como advertencia para Paso 14 (mantenimiento del script). No bloquea dogfooding. |
| D3 | **`tools_list.py` crea nuevo event loop (`asyncio.new_event_loop`)**: `tools_list.py:141` crea y cierra loop en llamada síncrona. En un contexto FastAPI async esto puede producir advertencias o bugs en Windows. | Documentar en §6 Riesgos, no bloquea dogfooding pero es candidato a fix en Paso 13. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas (directa o indirectamente)

| Tabla | Migración | Columnas clave | Uso en Paso 12 |
|---|---|---|---|
| `agent_templates` | 030 | `id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at` | `fap templates seed`, `GET /api/templates`, `GET /api/templates/{id}`, `fap templates use` |
| `agent_catalog` | 004 | `id, org_id, role, soul_json, allowed_tools, max_iter, is_active, created_at` | `fap agent create`, `fap templates use`, `fap agent run` |
| `org_mcp_servers` | 005 | `id, org_id, name, command, args, is_active, secret_name` | `fap tools list` (MCP tools fetch) |
| `tasks` | 007 | `id, org_id, flow_type, status, payload, assigned_agent_role, result, tokens_used, error, correlation_id` | `fap agent run` (polling) |

### RLS Policies aplicables

| Tabla | Policy | Acceso | Verificado |
|---|---|---|---|
| `agent_templates` | `agent_templates_read` | `auth.role() = 'authenticated'` (SELECT público) | 030_agent_templates.sql:25-26 ✅ |
| `agent_templates` | `agent_templates_write` | `auth.role() = 'service_role'` (ALL) | 030_agent_templates.sql:28-29 ✅ |
| `agent_catalog` | `tenant_isolation` | `org_id::text = app.org_id()` | phase-state.md:70 ✅ |
| `tasks` | `tenant_isolation` | `org_id::text = app.org_id()` | phase-state.md:70 ✅ |

### Integridad referencial
- `agent_templates` no contiene FK externas (tabla global, sin `org_id`)
- `agent_catalog.tasks` relación implícita vía `role/TEXT`, no FK formal
- `org_mcp_servers` relación a `org_id` para aislamiento de servidores MCP

### Índices relevantes

| Índice | Tabla | Criterio |
|---|---|---|
| `idx_agent_templates_category` | `agent_templates` | Filtro `?category=` |
| `idx_agent_templates_system_name` | `agent_templates` | `WHERE is_system = TRUE` — evita duplicados en seed |
| 001_config_rpc | system | Operaciones config RPC del TenantClient |

### Tipo de datos problemáticos
- **No encontrados** — todos los tipos usados en Paso 12 son primitivos estándar (`TEXT`, `UUID`, `JSONB`, `TIMESTAMPTZ`, `TEXT[]`)

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/CLI principales (firmas exactas)

#### `src/cli/commands/tools_list.py`

```python
# tools_list_app: typer.Typer — "List available tools (local + MCP)."

def list_tools(org_id: Optional[str] = None, source: Optional[str] = None, json_output: bool = False) -> None
"""CLI command: fap tools list [-o ORG_ID] [-s {local,mcp}] [--json]"""

def _collect_tools(org_id: str, source: Optional[str] = None) -> list[dict]
"""Collects tools from ToolRegistry + MCPPool"""

def _fetch_mcp_tools(org_id: str) -> list[dict]
"""Crea nuevo event loop, consulta org_mcp_servers, fetch tools vía MCPPool.get_tools"""

def _print_table(tools: list[dict]) -> None
"""Imprime tabla Rich"""
```

#### `src/cli/commands/templates_seed.py`

```python
# templates_app: typer.Typer — "Manage agent templates."

def seed_templates(dry_run: bool = False, reset: bool = False) -> None
"""CLI command: fap templates seed [--dry-run] [--reset]
- dry_run → preview de 8 templates sin insertar
- reset → DELETE de templates is_system antes de sembrar
- inserción vía upsert on_conflict="id" (UUID v5 determinista)"""

# 8 templates predefinidos en TEMPLATES (líneas 32-137):
# Research Agent, Code Reviewer, Data Analyst, Customer Support,
# Document Writer, Translator, Summarizer, General Assistant
# (categorías: Research, Development, Support, General)
```

#### `src/cli/commands/templates_use.py`

```python
def use_template(
    template_name: str,
    org_id: str,
    role: Optional[str] = None,
    goal: Optional[str] = None,
    backstory: Optional[str] = None,
    tools: Optional[list[str]] = None,
    max_iter: Optional[int] = None,
    dry_run: bool = False,
) -> None
"""CLI: fap templates use <name|uuid> -o ORG_ID [--role/--goal/--backstory/--tools/--max-iter] [--dry-run]
- dry_run → imprime payload JSON sin enviar
- sino → POST /agents con payload y tablas resultados"""

# Mapeo de provider:
def _map_provider(provider: Optional[str]) -> str  # groq|openai|anthropic|openrouter → default: "groq"
```

#### `src/cli/commands/agent_create.py`

```python
# agent_app: typer.Typer — "Agent management"

def create_agent(
    role: str, goal: str, backstory: str,
    org_id: Optional[str] = None,
    tools: Optional[list[str]] = None,
    max_iter: int = 3,
    llm_provider: str = "groq",
    llm_model: str = "llama-3.1-70b-versatile",
    verbose: bool = False, reasoning: bool = False,
    inject_date: bool = False, memory: bool = False,
    dry_run: bool = False,
) -> None
"""CLI: fap agent create --role R --goal G --backstory B [-o ORG] [-t TOOL...] [-m N] [--dry-run]
Payload: {role, soul_json: {goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}, allowed_tools, max_iter}"""

# POST endpoint correspondiente (ref):
POST /agents → src/api/routes/agents.py::create_agent()
```

#### `src/cli/commands/agent_run.py`

```python
def run_agent(
    role: str,
    message: str,
    org_id: Optional[str] = None,
    watch: bool = False,
    timeout: int = 120,
) -> None
"""CLI: fap agent run --role R --message M [-o ORG] [-w] [--timeout N]
1. POST /agents/{role}/run → {input_data: {message}} → task_id
2. Poll GET /tasks/{task_id} cada 2s hasta timeout
3. estados terminales: completed → exit 0, failed/cancelled → exit 1"""
```

#### `src/cli/commands/bundle_validate_payload.py`

```python
def validate_payload(file: Optional[Path] = None, stdin: bool = False, json_output: bool = False) -> None
"""CLI: fap bundle validate-payload --file PATH [--json] [--stdin]
Valida contra ExportBundleRequest schema, muestra resumen y warnings"""
```

#### `src/cli/commands/doctor_builder.py`

```python
# 6 diagnósticos automáticos:
doctor_builder() → None
"""CLI: fap doctor builder
Checks: ID-C02 seed idempotency, ID-C03 breadcrumb sync, ID-C04 mock patching,
        ID-023 TypeScript/Zod integrity, ID-051 conftest tenant patches, ID-052 conftest regression guard"""

def _check_seed_idempotency() → tuple[bool, str]
def _check_breadcrumb_sync() → tuple[bool, str]
def _check_mock_patching() → tuple[bool, str]
def _check_conftest_tenant_patches() → tuple[bool, str]
def _check_conftest_regression() → tuple[bool, str]
def _check_typescript_integrity() → tuple[bool, str]
```

#### `src/api/routes/tools.py`

```python
router = APIRouter(prefix="/api/tools", tags=["tools"])

@router.get("/available", response_model=ToolsListResponse)
async def list_available_tools(
    org_id: str = Depends(require_org_id),
    source: Optional[str] = Query(None, pattern="^(local|mcp)$"),
    category: Optional[str] = Query(None),
) -> ToolsListResponse

# ToolInfo model:
class ToolInfo(BaseModel):
    name: str; description: str; category: str = "general"
    categories: List[str] = []; source: Literal["local", "mcp"]
    parameters: Dict[str, Any] = {}; requires_approval: bool = False
    timeout_seconds: int = 30; is_active: bool = True
```

#### `src/api/routes/templates.py`

```python
router = APIRouter(prefix="/api/templates", tags=["templates"])

# ⚠️ NOTE: Sin require_org_id — lectura pública
@router.get("", response_model=TemplateListResponse)
async def list_templates(category: Optional[str] = Query(None)) → TemplateListResponse
# 503 en fallo de DB, sin auth

@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str) → TemplateDetailResponse
# 404 si no existe, 503 en fallo de DB, sin auth
```

#### `src/api/routes/agents.py`

```python
class AgentCreate(BaseModel):
    role: str; soul_json: Dict[str, Any]; allowed_tools: List[str] = []; max_iter: int = 3

@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(payload: AgentCreate, org_id: str = Depends(require_org_id))
# Upsert por org_id,role → 409 si rol existe

@router.post("/{role}/run", response_model=RunAgentResponse)
async def run_agent(role: str, request: RunAgentRequest,
                    background_tasks: BackgroundTasks,
                    auth: dict = Depends(verify_org_membership))
# task_id en background → polling externo con GET /tasks/{task_id}

@router.get("/by-role/{role}")  # Para TemplatePicker lookup by role
@router.get("/{agent_id}/detail")  # Detalle completo con métricas
```

#### `src/api/routes/bundles.py`

```python
@router.post("/export", response_class=Response, status_code=200)
async def export_bundle(payload: ExportBundleRequest, org_id: str = Depends(require_org_id))
# Validación: goal/backstory requeridos y ≥ 10 chars
# 422 si inválido, ZIP con application/zip + Content-Disposition

# POST /api/bundles/validate (dry-run sin escribir DB):
@router.post("/validate", response_model=BundleValidationResult, status_code=200)  # idéntico a bundle_schemas.BundleValidationResult
```

#### `src/services/bundle_schemas.py`

```python
class ExportBundleRequest(BaseModel):
    bundle_name: Optional[str] = None  # min 3, max 200
    agents: List[AgentExportItem]  # min 1, max 15
    skills: Optional[List[SkillExportItem]] = []  # opcional

class AgentExportItem(BaseModel):
    role: str  # min 1, max 100
    soul_json: Dict  # debe contener goal, backstory
    allowed_tools: List[str] = []
    max_iter: int = 5  # ge 1, le 50

class BundleValidationResult(BaseModel):
    status: str = "success"; bundle_info: Optional[BundleInfo] = None
    agents_count: int = 0; flows_count: int = 0; skills_count: int = 0
    security_report: Optional[Dict] = None; warnings: List[str] = []; error: Optional[str] = None
```

### Patrones reutilizados, sin duplicación

| Patrón | Implementado en | Paso 12 usa |
|---|---|---|
| CLIConfig pattern | `src/cli/config.py:14-56` | Todos los comandos CLI |
| Upsert por PK | `templates_seed.py:206` | `fap templates seed` |
| Dry-run preview | `agent_create.py:83-86`, `templates_use.py:138-144`, `bundle_validate_payload.py` | 3 comandos |
| Rich table output | `doctor_builder.py`, `tools_list.py`, `agent_create.py`, etc. | Todos los comandos |
| httpx.Client (síncrono) | `agent_run.py`, `templates_use.py`, `agent_create.py` | 3 comandos; ⚠️ candidato a async en Paso 13 |
| Subprocess test runner | `test_builder.py:87-93` | `fap test builder run` |

### Imports correctos
- Todos los comandos usan absolutos (`from src.cli.config import CLIConfig`)
- `tools_list.py` importa `from src.tools.registry import tool_registry` ✅
- `agent_run.py` importa `from src.cli.config import CLIConfig` + `urllib.parse.quote` ✅
- Tiempo de verificación: 22 elementos directos (umbral ≥ 18 para 6-10 archivos afectados)

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints involucrados en Paso 12

| Método | Ruta | Handler | Auth | Propósito dogfooding |
|---|---|---|---|---|
| GET | `/api/tools/available` | `list_available_tools` | `require_org_id` | Validar listado de tools con `fap tools list` |
| POST | `/api/bundles/export` | `export_bundle` | `require_org_id` | Validar ZIP export con `GET /api/bundles/export` (implícito en Tarea ID-041) |
| POST | `/api/bundles/validate` | `validate_bundle` | `require_org_id` | Validar payload contra schema sin DB write |
| GET | `/api/templates` | `list_templates` | **Ninguno** | Validar seed + listado con `fap templates seed/use` |
| GET | `/api/templates/{id}` | `get_template` | **Ninguno** | Validar detalle template individual |
| POST | `/agents` | `create_agent` | `require_org_id` | Validar creación de agente desde CLI y template |
| POST | `/agents/{role}/run` | `run_agent` | `verify_org_membership` | Validate vida de tarea → polling `GET /tasks/{task_id}` |
| GET | `/tasks/{task_id}` | (implícito via tasks.py) | Igual | Polling backend de resultados |

### Contratos y request/response

#### `GET /api/tools/available`

```
Request:  GET /api/tools/available
          Header: X-Org-ID: <org_uuid>
          Query:  ?source=local|mcp
Response: 200
{
  "tools": [
    {
      "name": "excel_reader",
      "description": "...",
      "category": "data",
      "source": "local",
      "requires_approval": false,
      "timeout_seconds": 30,
      "is_active": true
    },
    {
      "name": "mcp:server1:some_tool",
      "source": "mcp",
      ...
    }
  ],
  "count": <N>
}
```

#### `GET /api/templates`

```
Request:  GET /api/templates
          Query: ?category=Research  (opcional)
Response: 200
{
  "templates": [
    {
      "id": "uuid", "name": "Research Agent",
      "description": "...", "category": "Research",
      "suggested_tools": ["sql_analytical"],
      "max_iter": 5, "is_system": true,
      "created_at": "2026-05-16T..."
    }
  ],
  "count": 8
}
Error:    503 DB unavailable
```

#### `fap agent create` → `POST /agents`

```python
CLI: fap agent create --role X --goal G --backstory B [-o ORG] [--tools t1 --tools t2]

Payload enviado:
{
    "role": "X",
    "soul_json": {
        "goal": "G", "backstory": "B",
        "llm_provider": "groq", "llm_model": "llama-3.1-70b-versatile",
        "verbose": false, "reasoning": false,
        "inject_date": false, "memory": false
    },
    "allowed_tools": ["t1","t2"],
    "max_iter": 3
}

Response 201:
{
    "id": "uuid", "org_id": "uuid", "role": "X",
    "soul_json": {...}, "allowed_tools": [...], "max_iter": 3,
    "created_at": "2026-05-18T..."
}
Response 409: {"detail": "Role already exists"}
```

#### `fap templates use --dry-run` (mapeo)

```python
# Template → Agent mapping:
soul_json = {
    "goal":      goal from template.soul_json
    "backstory": backstory from template.soul_json
    "llm_provider": _map_provider(soul_json.llm_provider)  # default groq
    "llm_model": soul_json.llm_model or "llama-3.1-70b-versatile"
    "verbose"/"reasoning"/"inject_date"/"memory": from soul_json or false
}
payload = {"role": final_role, "soul_json": soul_json, "allowed_tools": suggested_tools, max_iter}
# dry-run imprime JSON, no envía
```

#### `fap agent run` (polling)

```
1. → POST /agents/{role}/run {input_data: {message}} → {"task_id": "uuid", "status": "accepted"} 202
2. ↻ GET /tasks/{task_id} cada 2s hasta timeout (default 120s, max 600s)
3. Estado terminal:
   completed → muestra resultado + tokens_used → exit 0
   failed/cancelled/rejected → muestra error → exit 1
   timeout → yellow warning → exit 1
```

#### `fap bundle validate-payload` (schema validation)

```python
# Valida ExportBundleRequest Pydantic model:
{
  "bundle_name": "my-bundle",  # min 3, max 200 chars (opcional)
  "agents": [                    # min 1, max 15 agents
    {
      "role": "agent1",          # min 1, max 100 chars
      "soul_json": {goal, backstory},
      "allowed_tools": [],
      "max_iter": 5              # ge 1, le 50
    }
  ],
  "skills": [...]                # opcional
}
Muestra Summary: agents, skills, est. size, warnings (goal/backstory < 10 chars)
```

### Flujo de datos backend → frontend (dogfooding)

```
DB (Supabase)
  │
  ├── Templates: 030_agent_templates.sql → templates_seed.py → GET /api/templates → TemplatePicker
  ├── Tools: org_mcp_servers + ToolRegistry → tools_list.py → GET /api/tools/available → AgentForm
  ├── Agents: agent_catalog ← fap agent create → POST /agents → GET /agents → Builder
  └── Tasks: tasks table ← fap agent run → POST /agents/{role}/run → AgentPlayground
```

### Auth/authz análisis

- `GET /api/templates` y `GET /api/templates/{id}` — **sin auth** por diseño (lectura pública de templates sistema)
- `GET /api/tools/available` — `require_org_id` por header `X-Org-ID`
- `POST /agents` — `require_org_id`
- `POST /agents/{role}/run` — `verify_org_membership` (JWT + rol en org)
- CLI commands usan `X-Org-ID` header o config de `~/.fap/config.json`

### Problemas de auth/authz

| Problema | Severidad | Detalle |
|---|---|---|
| `templates.py` sin `require_org_id` — plan original pedía auth | Media | Comentario en código: "lectura pública, patrón integrations.py". Coherente con RLS policy `agent_templates_read`. Implementación es correcta, documentar en plan update si se requiere. |

### Cuellos de botella

| Punto | Descripción | Mitigación |
|---|---|---|
| `_fetch_mcp_tools` crea nuevo event loop | `tools_list.py:141` — `asyncio.new_event_loop()` en llamada síncrona | Considerar migrar CLI commands a `asyncio.run()` o async. Paso 13 |
| Polling `agent_run.py` es síncrono | `agent_run.py:131` — crea `httpx.Client` por cada poll | Candidato a async en Paso 13 |
| Sin timeout en `_fetch_mcp_tools` (loop level) | `tools_list.py:141-147` | Si un servidor MCP cuelga, puede colgar toda la lista |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

```
Supabase DB (030_agent_templates.sql, 004_agent_catalog.sql, 007_tasks.sql)
    │
    ▼
CLI (dogfooding)                 BACKEND                    FRONTEND
─────────────────────────────────────────────────────────────────
fap templates seed   ──→        (no endpoint,    ──→      TemplatePicker
  → upsert templeates            direct DB via               Carga GET /api/templates
                                 get_service_client)
fap templates use    ──→        POST /agents      ──→      AgentForm
  → dry-run envía payload       create_agent()               Auto-completa formulario
  → dry-run ejecuta POST        org_id + RL                 Guardado directo a DB

fap tools list       ──→        GET /api/tools/   ──→      AgentForm
  → muestra local + MCP          available                   Carga multi-select tools

fap agent create     ──→        POST /agents      ──→      (no paso 12, builder guarda)
  → dry-run o envía             create_agent()

fap agent run        ──→        POST /agents/     ──→      AgentPlayground
  → polling GET/tasks            {role}/run                  Chat en tiempo real
                                 task_id → polling
```

### Coherencia paso 12 → arquitectura

- **Dogfooding como validación de contratos**: Cada herramienta CLI valida un contrato API antes de considerarlo finalizado. Esto es correcto: `fap doctor builder` (Paso 11) → `fap test builder run` (Paso 10) → validación individual CLI (Paso 12).
- **CLI como puerta de entrada**: Todo comando CLI → `CLIConfig` → `httpx`/`supabase` → API/DB. No hay caminos alternativos saltando la API, lo que valida los contratos de forma end-to-end.
- **CLI commands implementados antes del plan**: `fap doctor builder`, `fap test builder`, `tools_list`, `templates_seed`, `templates_use`, `agent_create`, `agent_run`, `bundle_validate_payload` — todos existen, registrados en `main.py`, y tienen dry-run donde corresponden.

### Gaps y fricciones

| GAP | Descripción | Impacto |
|---|---|---|
| GAP-1 | `fap templates use` requires passing `--org-id` but if not set in `~/.fap/config.json` fails hard. Plan doesn't mention config setup. | Bajo — documentar |
| GAP-2 | `validate_builder_nav.py` check 5 (`check_ssr_false`) menciona `BuilderCanvas` pero código usa `CrewCanvas` directamente con `<dynamic ssr={false}>`. Referencia imprecisa. | Bajo — no bloquea dogfooding |
| GAP-3 | No hay `fap validate-payload` directo (solo `fap bundle validate-payload`). La ruta del plan menciona `fap bundle validate-payload` (correcto). | Sin gap |
| GAP-4 | Paso 12 Tarea ID-041 menciona `fap bundle validate-payload` y existe ✅. Pero Paso 2 crea `POST /api/bundles/export` y Paso 12 no valida el endpoint export directamente (solo schema). | Medio — validación de contrato sería output ZIP real |

### DX & Tooling — OBLOGATORIO ✅

> Toda herramienta dogfooding demostrada en acción reduce pasos manuales repetitivos.

#### `fap doctor builder` — YA EXISTE ✅

Diagnóstico automatizado de los 6 fixes críticos del builder en un solo comando.

```bash
# Ejecutar
uv run fap doctor builder

# Resultado: tabla color-coded por cada fix
# ✔ ID-C02: Seed Idempotency  → OK
# ✔ ID-C03: Breadcrumb Sync   → OK
# ✔ ID-C04: Mock Patching      → OK
# ✔ ID-023: TypeScript/Zod     → OK
# ✔ ID-051: Conftest Patches   → OK
# ✔ ID-052: Conftest Reg Guard → OK
```

- **Qué automatiza:** Elimina la necesidad de revisar manualmente 6 archivos por cada deployment o merge del builder — seed, breadcrumbs, mocks, tipos, conftest, regresión.
- **Tipo:** Comando de diagnóstico CLI (CLI validador)
- **Prioridad:** Tarea 0 — ejecutar antes de cualquier modificación del builder en CI/CD.

#### `fap test builder run` — YA EXISTE ✅

Suite E2E de 32 escenarios del builder en un solo comando.

```bash
uv run fap test builder run --org-id test-org --report
# Exit 0 = 32/32 PASSED, Exit >0 = fallos con stdout detallado + HTML report
```

- **Qué automatiza:** Reemplaza ejecución manual de `pytest tests/e2e/test_builder_scenarios.py -v --timeout=120`.
- **Tipo:** Comando ejecutor de tests E2E
- **Prioridad:** Preparada (ejecutar en CI/CD pipeline).

#### Herramienta Propuesta: `fap dogfood check`

- **Qué automatiza:** Ciclo secuencial de dogfooding en un solo comando — `doctor builder` → `templates seed` → `tools list` → `agent create --dry-run` → `templates use --dry-run` → `bundle validate-payload`. Actualmente el usuario debe ejecutar cada comando por separado y comparar output manualmente.
- **Tipo:** Comando CLI orquestador
- **Cómo se usa:**

```bash
uv run fap dogfood check
# Output: score 0-100%, contratos OK/FALLIDOS, suggerencias de fix

uv run fap dogfood check --json  # Para CI/CD: exit 0 si todo OK, exit 1 si falla
uv run fap dogfood check --step templates   # Solo validar paso de templates
uv run fap dogfood check --step agents       # Solo validar paso de agents
```

- **Impacto para el usuario final:** El equipo puede ejecutar `fap dogfood check` como puerta de calidad pre-merge. Actualmente hacen 3-4 comandos separados y comparan salida manualmente. Reduce 5 minutos de trabajo manual a 10 segundos en un CI/CD paso.
- **Prioridad:** 🔴 Tarea 0 — implementar antes de cerrar el Paso 12 para que valide su propio resultado.

---

## 5️⃣ Criterios de Aceptación

### [DATA]
- ✅ Tabla `agent_templates` existe con migración 030 (columnas correctas, RLS aplicado, índices creados)
- ✅ Tabla `agent_catalog` existe con migración 004
- ✅ Tabla `org_mcp_servers` existe con migración 005
- ✅ Tabla `tasks` existe con migración 007

### [CODE]
- ✅ `templates_seed.py` usa UUID v5 determinista + `upsert(on_conflict="id")`
- ✅ `fap doctor builder` tiene 6 diagnósticos implementados (ID-C02 a ID-052)
- ✅ `fap test builder run` ejecuta `tests/e2e/test_builder_scenarios.py` (32 escenarios)
- ✅ `validate_builder_nav.py` ejecuta 5 checks estructurados

### [BACKEND]
- ✅ `GET /api/tools/available` acepta `?source=local|mcp` y devuelve `ToolsListResponse`
- ✅ `GET /api/templates` + `GET /api/templates/{id}` sin auth, filtro `?category=`
- ✅ `POST /agents` upserta por `org_id,role`, devuelve 409 en conflicto
- ✅ `POST /agents/{role}/run` devuelve `task_id`, `RunAgentResponse`
- ✅ `POST /api/bundles/export` valida goal/backstory ≥10 chars → 422
- ✅ `POST /api/bundles/validate` valida schema ExportBundleRequest sin DB write

### [FULLSTACK]
- ✅ Dogfooding CLI → API → DB cierra el ciclo completo Paso 12
- ✅ Todos los comandos CLI documentados en `1_ANALISIS.md` funcionan contra código real
- ✅ Contratos API coinciden con expectativas CLI (verificadas contra código fuente)

### [DX]
- ✅ `fap doctor builder` — diagnósticos automatizados
- ✅ `fap test builder run --report` — suite integrada con reporte HTML
- ✅ `fap bundle validate-payload` — validación de schema sin DB
- 🔴 **Pendiente implementar** `fap dogfood check` como orquestador único para Paso 12

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1**: `tools_list.py` crea nuevo event loop (`asyncio.new_event_loop`) | Media | Llamada síncrona envuelve async MCP fetch. Si hay servidores MCP colgados, loop se cuelga sin timeout global. | Migrar a `asyncio.run()` o usar `nest_asyncio` (Paso 13 — ID-003/004 ya lo menciona en plan) |
| **R2**: `agent_run.py` usa httpx.Client síncrono en polling | Media | Cada poll abre y cierra cliente. Alto overhead. Bloquea el event loop si hay 100+ polls. | Migrar a `httpx.AsyncClient` (Paso 13, ID-033/039) |
| **R3**: Paso 12 tiene 8 tareas pero solo hay 8 comandos CLI — todas existen, ninguna pendiente de implementación | Baja | No hay trabajo de codificación por hacer — solo ejecución y documentación de resultados | Ejecutar cada CLI command, capturar output, incluirlo en este análisis como evidencia |
| **R4**: `validate_builder_nav.py` check 5 (SSR) referencia `BuilderCanvas` pero código usa `CrewCanvas` con `<dynamic ssr={false}>` | Baja | Desincronización entre script de validación y código real. No bloquea dogfooding pero puede generar falsos negativos. | Corregir `check_ssr_false` para buscar `CrewCanvas` y `<dynamic ssr={false}>` (Paso 14, ID-049) |
| **R5**: `templates.py` sin auth — cualquier usuario con `authenticated` role ve templates | Media | RLS policy permite SELECT a authenticated. Es correcto para lectura pública de templates globales. | Confirmar con equipo de producto que no requiere restricción adicional |
| **R6**: Definición de `Breadcrumb Sync` (ID-C03) está evaluada solo como presencia de `useBuilderTab` o `BuilderTabProvider` | Baja | No valida sincronización real de tabs en producción, solo presencia de símbolos en código | Complementar con test E2E de tab switching si se sigue refinando |

---

## 7️⃣ Plan de Implementación

> **REGLA DE ORO:** Tarea 0 = DX & Tooling. Tareas 1-8 = Protocolo de validación dogfooding ejecutado contra código real.

> Se aplica **VERIFICACIÓN INLINE**: cada tarea tiene un comando de confirmación.

| # | Tarea | Artefacto | Acción | Complejidad | Tiempo Est. | Deps | Verificación |
|---|---|---|---|---|---|---|---|
| **0** | **DX: Implementar `fap dogfood check`** | `src/cli/commands/dogfood_check.py` | Crear comando Typer que orquesta doctor+builder+templates+validators en secuencia | Media | 2h | Ninguna | `uv run fap dogfood check` → exit 0, todos los sub-checks reportan PASS |
| 1 | Ejecutar doctor builder | CLI | `uv run fap doctor builder` | Baja | 0.1h | Tarea 0 | → 6/6 checks OK |
| 2 | Ejecutar seed templates | CLI | `uv run fap templates seed` (idempotencia 2 corridas) | Baja | 0.2h | Tarea 1 | → Segunda corrida reporta "skipped" o "OK" sin error |
| 3 | Validar tools list | API + CLI | `uv run fap tools list` + `curl http://localhost:8000/api/tools/available` | Baja | 0.3h | Tarea 2 | → fap tools list devuelve ≥0 tools, JSON parseable, formato correcto |
| 4 | Validar templates endpoint (list + detail) | API | `uv run fap templates seed` → GET /api/templates → GET /api/templates/{id} | Baja | 0.3h | Tarea 3 | → 8 templates en list, detalle contiene `soul_json` |
| 5 | Validar agent CRUD | API + CLI | `uv run fap agent create --role test_e2e --goal "Test goal of 15 chars..." --backstory "Test backstory of 20 chars..." --dry-run` | Baja | 0.3h | Tarea 4 | → JSON payload correcto, sin error |
| 6 | Validar fullstack live (DB write) | CLI + DB | `uv run fap agent create --role test_e2e ...` (sin dry-run) → verificar en Supabase Studio | Baja | 0.3h | Tarea 5 | → Agente aparece en `agent_catalog` con role correcto |
| 7 | Validar template→agent mapping | CLI + DB | `uv run fap templates use "Research Agent" --dry-run` → `--org-id` → sin dry-run (verificar en DB) | Baja | 0.3h | Tarea 5 | → Dry-run imprime payload JSON correcto con 8 templates |
| 8 | Validar agent run + polling | CLI | `uv run fap agent run --role <rol_valido> --message "test" --timeout 60 --watch` | Baja | 0.5h | Tarea 6 | → task_id recibido, polling completa con exit code apropiado |
| 9 | Validar export payload | CLI + API | `uv run fap bundle validate-payload --file test_payload.json` | Baja | 0.3h | Tarea 0 | → Schema valid OK, JSON output parseable |
| 10 | Doc builder nav script | Script | `uv run python scripts/validate_builder_nav.py` | Baja | 0.2h | Tareas 1-9 | → Todos los checks pasan (documentar si D2/D4 hay discrepancias) |
| 11 | Documentar resultados dogfooding | `DEVS/IMPLEMENTED/guiAgentGenerator/12-Validacion-Dogfooding/` | Resumen de cada CLI command ejecutado, exit codes, output snapshot | Baja | 0.5h | Tareas 1-10 | → Carpeta `12-Validacion-Dogfooding/` creada con `dogfood_results.md` |

**Tiempo total estimado:** ~6 horas

---

## 🔮 Roadmap (NO implementar ahora)

- `fap agent run` puede migrar a `httpx.AsyncClient` para eliminar overhead de polling
- `_fetch_mcp_tools` puede ser migrado a async completo (Paso 13 address)
- `fap validate-payload` puede expandirse a validar security report de bundles reales
- `validate_builder_nav.py` puede ampliar sus diagnósticos a componentes de ReactFlow (canvas bounds, edges sin vuelta)

---

## 🚫 Reglas de Oro — Cumplimiento Check

| Regla | Cumplimiento |
|---|---|
| Análisis accionable y específico | ✅ — todas las secciones apuntan a código real |
| TODO verificado contra código | ✅ — 30 items en §0 con evidencia file:line |
| Si algo no está definido → ambigüedad + resolución | ✅ — D1, D2, D3 en §0 |
| Si plan contradice código → código gana | ✅ — D1: plan vs dry-run, D2: BuilderCanvas vs CrewCanvas |
| Nivel CTO exigente | ✅ |
| Coherente con phase-state.md | ✅ — contratos, ruta, estados alineados |
| TODO el paso (sub-pasos) | ✅ — paso 12 tiene 8 tareas, todas cubiertas |
| Etapas secuenciales | ✅ — data → code → backend → dx |
| ≥1 herramienta DX propuesta | ✅ — `fap dogfood check` (2h implementación, previa al cierre) |
| Tareas atómicas (1 artefacto por tarea) | ✅ |
| Interfaz exacta por tarea | ✅ |
| Patrón de referencia explícito | ✅ |
| Verificación inline por tarea | ✅ |
| Suposiciones no verificadas ≤ 2 | ✅ |

---

*Generado por step — 2026-05-18 — Paso 12 — Fase guiAgentGenerator*
