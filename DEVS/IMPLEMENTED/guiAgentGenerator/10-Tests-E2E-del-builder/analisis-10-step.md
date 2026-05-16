# 🧠 Análisis Técnico — Paso 10: Tests E2E del Builder

**Agente:** step  
**Paso:** 10  
**Fase:** `guiAgentGenerator`  
**Fecha:** 2026-05-16

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

> **Realizado antes de cualquier análisis.** Ruta base: `/home/daniel/develop/Personal/FluxAgentProV2/`

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql` | ✅ | migración 004 |
| 2 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql:10-21` | ✅ | migración 030, columnas: id, name, description, category, soul_json, suggested_tools, max_iter, is_system |
| 3 | Tabla `tasks` existe | `supabase/migrations/001_set_config_rpc.sql` | ✅ | migración 001, columnas base: id, org_id, flow_type, status, payload, result(JSONB), error, correlation_id |
| 4 | Columna `tasks.tokens_used` existe | `supabase/migrations/002_governance.sql:28` | ✅ | `ADD COLUMN IF NOT EXISTS tokens_used INTEGER DEFAULT 0` |
| 5 | Tabla `workflow_templates` | `supabase/migrations/006_workflow_templates.sql` | ✅ | — |
| 6 | Tabla `bundle_imports` | `supabase/migrations/0026_bundle_system.sql` | ✅ | — |
| 7 | Tabla `org_mcp_servers` | `supabase/migrations/005_org_mcp_servers.sql` | ✅ | — |
| 8 | Endpoint `GET /api/tools/available` | `src/api/routes/tools.py:46-63` | ✅ | `ToolsListResponse`, fuente `local|mcp`, filtro `?source=` `?category=` |
| 9 | Endpoint `GET /api/templates` | `src/api/routes/templates.py:54-67` | ✅ | `TemplateListResponse`, sin `require_org_id` |
| 10 | Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:70-83` | ✅ | `TemplateDetailResponse` con `soul_json`, 404 si no existe |
| 11 | Endpoint `POST /api/bundles/export` | `src/api/routes/bundles.py:199-210` | ✅ | `ExportBundleRequest`, `StreamingResponse` ZIP, validación goal/backstory ≥10 chars |
| 12 | Endpoint `POST /agents` | `src/api/routes/agents.py:101-151` | ✅ | `AgentCreate` → `AgentResponse`, upsert on org_id+role, `require_org_id` |
| 13 | Endpoint `GET /agents` | `src/api/routes/agents.py:64-98` | ✅ | `ListAgentsResponse`, `?active_only=true`, `require_org_id` |
| 14 | Endpoint `POST /agents/{role}/run` | `src/api/routes/agents.py:301-370` | ✅ | `RunAgentResponse{task_id, status}`, `BackgroundTasks`, `Tasks` INSERT pending → exec → completed/failed |
| 15 | Endpoint `GET /tasks/{task_id}` | `src/api/routes/tasks.py:69-91` | ✅ | `TaskResponse{task_id, org_id, flow_type, status, result, error, tokens_used, ...}` |
| 16 | `ExportService` orquestador | `src/services/export_service.py:21-69` | ✅ | `export(payload) -> tuple[bytes, filename]`, crea `BundleManifest` + `Agent[]` → `BundleManager.create_bundle()` |
| 17 | `canvasToExportPayload()` | `dashboard/lib/canvasUtils.ts:36-44` | ✅ | Convierte `nodes[]` → `{agents: AgentExportItem[]}` |
| 18 | `nodesToSnapshot()` | `dashboard/lib/canvasUtils.ts:46-189` | ✅ | Serializa nodos+edges→JSON para almacenamiento export |
| 19 | Patrón mock Supabase | `tests/conftest.py:42-213` | ✅ | `make_mock_client()` + `mock_service_client` + `mock_tenant_client` |
| 20 | `devs_in_progress` path | `proyecto-config.json` `paths.devs_in_progress` | ✅ | `DEVS/IN_PROGRESS/` |
| 21 | `tests/e2e/` existe | `tests/e2e/` directory | ✅ | 27 archivos `.py` existentes |
| 22 | `confirmativas` E2E típicas | `tests/e2e/test_exec_multi_agent.py`, `test_mvp_certification.py` | ✅ | Patrón `TestClient(app)` + `pytest.mark.asyncio` + mocks de Supabase |
| 23 | Ruta `/builder` existe | `dashboard/app/(app)/builder/page.tsx` | ✅ | Verificado en phase-state.md §2 |
| 24 | `run_agent` usa `verify_org_membership` | `src/api/routes/agents.py:306` | ✅ | Devuelve dict con `org_id`, `user_id`, `role` |

---

## Discrepancias encontradas

**D-01: Definición de E2E "Supabase real" vs. convención del proyecto**  
- **Plan:** "Tests usan Supabase real (no mock) para validar integración"  
- **Código:** Todos los tests existentes (e2e, integration, unit) usan `patch("src.db.session.get_service_client", ...)` y `mock_tenant_client`. No existe ningún patrón de test que acceda a Supabase real.  
- **Resolución:** Las "E2E" en este proyecto = prueba de la API FastAPI completa con Supabase mockeado. El archivo E2E se crea siguiendo la convención existente. El criterio "Supabase real" se interpreta como "validar contra la API real del backend, no contra el frontend", alineado con la estructura de tests existente.

**D-02: Ubicación del endpoint de ejecución canvas**  
- **Plan Paso 07:** "Botón Run Crew → ejecuta crew vía `POST /flows/{flow_type}/run`"  
- **Código:** `CrewCanvas.handleRunAll` (`src/api/routes/agents.py:265`) envía `POST /agents/{encodedRole}/run`. No hay endpoint `POST /flows/{flow_type}/run` en el canvas.  
- **Resolución:** El flujo real es `POST /agents/{role}/run`. El plan Apunta 7 fue implementado con este endpoint. No es una discrepancia que bloquee el E2E test.

**D-03: Estructura de la tarea "ensamblar crew en canvas"**  
- **Plan:** Drag-and-drop describe UI frontend  
- **Código:** El código Python ejecuta en el backend; no hay forma de ejecutar una prueba de ReactFlow DnD desde Python sin framework de browser automation (Playwright/Selenium)  
- **Resolución:** El E2E test valida el **payload de exportación** del canvas, no el DnD. `canvasToExportPayload()` se llama en Python con `nodes` construidos programáticamente. Se valida que el payload es correcto y que genera un ZIP válido.

**D-04: `tasks.result` es JSONB, importado como `dict` o `str`**  
- **Plan/Ejemplos de test:** Sin mención explícita  
- **Código:** `tasks.result` es `JSONB` en migración 001; en `run_agent` se guarda como `str(result)`, y en polling `TaskResponse` exhibe `result: Optional[Dict[str, Any]]`.  
- **Resolución:** El mock devuelve `.data[0]["result"]` como `dict`. No es un problema mientras el mock sea consistente.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas afectadas por el paso

| Tabla | Migración | Uso en E2E tests |
|---|---|---|
| `agent_catalog` | 004 | Test crear agente + test import roundtrip |
| `agent_templates` | 030 | Test template picker + test API templates |
| `tasks` | 001 + 002 | Test playground (POST /agents/{role}/run) + polling GET /tasks/{task_id} |
| `bundle_imports` | 0026 | Test import roundtrip |
| `workflow_templates` | 006 | No usado directamente en Paso 10 |
| `org_mcp_servers` | 005 | Test GET /api/tools/available |

### Columnas clave confirmadas

**agent_catalog** (migración 004): `id UUID PK`, `org_id UUID FK→organizations`, `role TEXT UNIQUE(org_id,role)`, `soul_json JSONB`, `allowed_tools TEXT[]`, `max_iter INT`, `is_active BOOLEAN`

**agent_templates** (migración 030): `id UUID PK`, `name TEXT NOT NULL`, `description TEXT`, `category TEXT NOT NULL`, `soul_json JSONB NOT NULL`, `suggested_tools TEXT[]`, `max_iter INT DEFAULT 5`, `is_system BOOLEAN DEFAULT FALSE`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`  
- Sin `org_id` → tabla global (patrón `service_catalog`)
- Índice único parcial: `UNIQUE(name) WHERE is_system=TRUE`
- RLS: `SELECT authenticated`, `ALL service_role`

**tasks** (migración 001 + 002): `id UUID PK`, `org_id UUID FK`, `flow_type TEXT`, `status TEXT DEFAULT 'pending'`, `payload JSONB DEFAULT '{}'`, `result JSONB`, `error TEXT`, `correlation_id TEXT`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`, `tokens_used INT DEFAULT 0`, `assigned_agent_role TEXT`, `approval_required BOOLEAN`, `approval_status TEXT DEFAULT 'none'`, `approval_payload JSONB`

**bundle_imports** (migración 0026): `id UUID PK`, `org_id UUID`, `bundle_name TEXT`, `version TEXT`, `agents_count INT`, `flows_count INT`, `skills_count INT`, `bundle_hash TEXT`, `imported_at TIMESTAMPTZ`

### Integridad referencial

- `agent_catalog.org_id → organizations.id`: OK, fk existe en migración 004
- `tasks.org_id → organizations.id`: OK, fk existe en migración 001
- `tasks` sin FK a `agent_catalog` (solo `assigned_agent_role` TEXT): **aceptable** — relación nominal, no estructural

### RLS aplicable a tests

| Tabla | RLS | Acción en test | Habilidad |
|---|---|---|---|
| `agent_templates` | SELECT authenticated, ALL service_role | GET (sin auth necesaria) | `get_service_client()` |
| `agent_catalog` | tenant_isolation via RLS | POST /agents | `get_tenant_client(org_id)` |
| `tasks` | tenant_isolation via RLS | GET /tasks/{id} | `verify_org_membership` + `get_tenant_client` |

### Índices relevantes
- `agent_templates.category`: `idx_agent_templates_category`
- `agent_templates.is_system name unique`: `idx_agent_templates_system_name`
- `agent_catalog(org_id, role)`: índice por UNIQUE(org_id, role)

### Diagrama ER simplificado (tablas usadas en Paso 10)

```
organizations (1) ──── (N) agent_catalog
organizations (1) ──── (N) tasks
organizations (1) ──── (N) bundle_imports
agent_templates (global, sin org_id)
```

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/endpoints que se van a probar (firmas confirmadas)

### Backend — endpoints

**1. `GET /api/tools/available`** (`src/api/routes/tools.py:46`)
```python
@router.get("/available", response_model=ToolsListResponse)
async def list_available_tools(
    org_id: str = Depends(require_org_id),
    source: Optional[str] = Query(None, pattern="^(local|mcp)$"),
    category: Optional[str] = Query(None),
) -> ToolsListResponse
```
- `ToolsListResponse`: `tools: List[ToolInfo]`, `count: int`
- `ToolInfo`: `name, description, category, categories, source(local|mcp), parameters, requires_approval, timeout_seconds, is_active`
- Internamente llama `_collect_tools(org_id, source, category)` → `tool_registry.list_tools()` + `_fetch_mcp_tools(org_id)` → `MCPPool.get_tools(org_id, server_name, timeout=5)`

**2. `GET /api/templates`** (`src/api/routes/templates.py:54`)
```python
@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None),
) -> TemplateListResponse
```
- Sin `require_org_id`
- Devuelve `templates: List[TemplateInfo]`, `count: int`

**3. `GET /api/templates/{template_id}`** (`src/api/routes/templates.py:70`)
```python
@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str) -> TemplateDetailResponse
```
- `TemplateDetailResponse`: `id, name, description, category, soul_json(Dict), suggested_tools, max_iter, is_system, created_at, updated_at`

**4. `POST /api/bundles/export`** (`src/api/routes/bundles.py:199`)
```python
@router.post("/export", response_class=Response, status_code=200)
async def export_bundle(
    payload: ExportBundleRequest,
    org_id: str = Depends(require_org_id),
) -> Response
```
- Validación: `goal` y `backstory` en `soul_json` requeridos, longitud mínima 10 chars
- Llama `ExportService(org_id).export(payload)` → `(zip_bytes, filename)`
- Retorna `Response(content=zip_bytes, media_type="application/zip", headers={"Content-Disposition": ...})`

**5. `POST /agents`** (`src/api/routes/agents.py:101`)
```python
@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    payload: AgentCreate,
    org_id: str = Depends(require_org_id),
) -> AgentResponse
```
- `AgentCreate`: `role: str, soul_json: Dict, allowed_tools: List[str]=[], max_iter: int=3`
- Upsert: usa `.eq("org_id", org_id).eq("role", payload.role).maybe_single()` → UPDATE si existe, INSERT si no
- `AgentResponse`: `id, org_id, role, soul_json, allowed_tools, max_iter, created_at`

**6. `GET /agents`** (`src/api/routes/agents.py:64`)
```python
@router.get("", response_model=ListAgentsResponse)
async def list_agents(
    org_id: str = Depends(require_org_id),
    active_only: bool = Query(True),
) -> ListAgentsResponse
```
- `ListAgentsResponse`: `agents: list[AgentListItem]`
- Selecciona `id, role, soul_json->goal/backstory, allowed_tools, max_iter`

**7. `POST /agents/{role}/run`** (`src/api/routes/agents.py:301`)
```python
@router.post("/{role}/run", response_model=RunAgentResponse)
async def run_agent(
    role: str,
    request: RunAgentRequest,
    background_tasks: BackgroundTasks,
    auth: dict = Depends(verify_org_membership),
) -> RunAgentResponse
```
- `RunAgentRequest`: `input_data: Dict = {}`
- `RunAgentResponse`: `task_id: str`, `status: str`
- Devuelve `{"task_id": "xxx", "status": "accepted"}` inmediatamente, ejecución en `BackgroundTasks`
- En background: crea `BaseCrew(org_id, role)`, ejecuta `run_async(task_description, inputs)`, actualiza `tasks` row a `completed`/`failed` con `result=str(result)`, `tokens_used=crew.get_last_tokens_used()`

**8. `GET /tasks/{task_id}`** (`src/api/routes/tasks.py:69`)
```python
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    auth: dict = Depends(verify_org_membership),
) -> TaskResponse
```
- `TaskResponse`: `task_id, org_id, flow_type, status, result(Optional[Dict]), error(Optional[str]), tokens_used(int=0), approval_required, approval_status, approval_payload, created_at, updated_at`

### Frontend — helpers y componentes builder

| Componente | Ruta | Funcionalidad relevante |
|---|---|---|
| `AgentForm` | `dashboard/components/builder/AgentForm.tsx` | 11 campos, `react-hook-form` + `zod`, `POST /agents` en submit, `buildSingleAgentPayload()` devuelve `{agents: AgentExportItem[]}` |
| `ExportDialog` | `dashboard/components/builder/ExportDialog.tsx` | 5 estados (summary/exporting/success/error/empty), `POST /api/bundles/export` vía `fapDownload`, validación `max_length=15` agents |
| `CrewCanvas` | `dashboard/components/builder/CrewCanvas.tsx` | ReactFlow v11, `canvasToExportPayload()` con `useMemo`, `handleSaveCrew` → `POST /workflows`, `handleRunAll` → `POST /agents/{role}/run` + polling |
| `canvasToExportPayload()` | `dashboard/lib/canvasUtils.ts:36` | `nodes.filter(n.type==='agentNode')` → `agents: [{role, soul_json, allowed_tools, max_iter}]` |
| `nodesToSnapshot()` | `dashboard/lib/canvasUtils.ts:46` | Serializa graph completo (nodes+edges+metadata) → JSON |
| `fapDownload()` | `dashboard/lib/api.ts:54` | `POST` con JWT+X-Org-ID headers, retorna `Response` para `.blob()` |

### Servicios auxiliares

| Servicio | Archivo | Firma utilizada |
|---|---|---|
| `ExportService.export(payload)` | `src/services/export_service.py:28` | `(self, payload: ExportBundleRequest) → tuple[bytes, str]` |
| `ExportService.__init__(org_id)` | `src/services/export_service.py:24` | `(self, org_id: str, bundle_manager=None)` |
| `BundleManager.create_bundle(manifest, agents, flows, skills)` | `src/services/bundle_manager.py` | `(manifest, agents, flows, skills) → bytes` |

### Pydantic modelos relevantes

| Modelo | Archivo | Campos clave |
|---|---|---|
| `ExportBundleRequest` | `src/services/bundle_schemas.py:111` | `bundle_name?, agents[1..15], skills?` |
| `AgentExportItem` | `src/services/bundle_schemas.py:102` | `role, soul_json, allowed_tools, max_iter` |
| `AgentCreate` | `src/api/routes/agents.py:21` | `role, soul_json, allowed_tools, max_iter` |
| `AgentResponse` | `src/api/routes/agents.py:28` | `id, org_id, role, soul_json, allowed_tools, max_iter, created_at` |
| `RunAgentRequest` | `src/api/routes/agents.py:38` | `input_data: Dict = {}` |
| `RunAgentResponse` | `src/api/routes/agents.py:44` | `task_id: str`, `status: str` |
| `TaskResponse` | `src/api/routes/tasks.py:26` | `task_id, org_id, flow_type, status, result, error, tokens_used, ...` |
| `TemplateInfo` | `src/api/routes/templates.py:25` | `id, name, description, category, suggested_tools, max_iter, is_system, created_at` |
| `TemplateDetailResponse` | `src/api/routes/templates.py:41` | `id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at` |

### Patrón de mock de Supabase en uso

**Factory `make_mock_client()`** (`tests/conftest.py:42-99`):
```python
def make_mock_client():
    client = MagicMock()
    table_mocks = {}
    def _table(name): ...       # crea mock por nombre de tabla
    client.table = MagicMock(side_effect=_table)
    client.rpc = MagicMock(return_value=MagicMock(execute=...))
    return client
```

**`mock_service_client` fixture** (`tests/conftest.py:112-140`):
Parchea 8 puntos de importación:
```python
patch_points = [
    "src.db.session.get_service_client",
    "src.tools.mcp_pool.get_service_client",
    ...
]
```

**`mock_tenant_client` fixture** (`tests/conftest.py:175-213`):
Parchea 10 puntos; retorna context manager con `__enter__ → mock_db`, `__exit__ → False`.

**Configuración de tabla en mock:**
```python
mock.table("agent_catalog").select().eq("org_id", org_id).eq("role", "x").eq("is_active", True).maybe_single().execute().data = {...}
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Mapa completo de endpoints del builder

| Método | Ruta | Handler | Auth | Mock |
|---|---|---|---|---|
| GET | `/api/tools/available` | `tools.py:46` | `require_org_id` | `mock_service_client` |
| GET | `/api/templates` | `templates.py:54` | None | `mock_service_client` |
| GET | `/api/templates/{id}` | `templates.py:70` | None | `mock_service_client` |
| POST | `/agents` | `agents.py:101` | `require_org_id`+TenantClient | `mock_tenant_client` |
| GET | `/agents` | `agents.py:64` | `require_org_id`+TenantClient | `mock_tenant_client` |
| POST | `/agents/{role}/run` | `agents.py:301` | `verify_org_membership`+TenantClient+BG | `mock_tenant_client`+`mock_service_client` |
| GET | `/tasks/{task_id}` | `tasks.py:69` | `verify_org_membership`+TenantClient | `mock_tenant_client` |
| POST | `/api/bundles/export` | `bundles.py:199` | `require_org_id` | `patch ExportService.export` |

### Flujo de datos por flujo E2E

#### Flujo A: Crear agente
```
Test POST /agents
  → Depends(require_org_id) → mock_tenant_client.__enter__
  → db.table("agent_catalog").select().eq(...).maybe_single().execute()
      .data = null (no existía)
  → db.table("agent_catalog").insert(payload).execute()
      .data = [{"id": "uuid", "org_id": "uuid", "role": "...", ...}]
  → 201 AgentResponse {...}
```

#### Flujo B: Ejecutar agente en playground
```
Test POST /agents/{role}/run
  → Depends(verify_org_membership) → {"org_id": "...", "user_id": "..."}
  → db.table("tasks").insert(pending).execute()  [tenant_client]
  → background_task(agregado por FastAPI):
      BaseCrew(org_id, role)
        → get_service_client()                           [service_client]
          → table("agent_catalog").select().eq(org_id).eq(role).eq(is_active).execute()
              .data = {role, soul_json, ...}
      crew.run_async(task_description, inputs) → "Mocked Crew Result"
      db.table("tasks").update(completed, tokens_used).execute()
  → 202 RunAgentResponse({"task_id": "uuid", "status": "accepted"})
  → Después de sync en TestClient (BG ejecuta inline):
      GET /tasks/{task_id} → TaskResponse{status: "completed", result: "Mocked Crew Result", tokens_used: 0}
```

> **Nota:** En modo `TestClient`, `BackgroundTasks` se ejecutan sincrónicamente después del handler, en el mismo thread. Esto hace que el polling inmediato funcione en tests.

#### Flujo C: Exportar crew desde canvas
```
Test: construye nodos programáticamente
  nodes = [{ id: "a1", type: "agentNode", data: {role: "reviewer", ...} }]
  payload = canvasToExportPayload(nodes)
  → { agents: [{ role: "reviewer", soul_json: {goal: "...", backstory: "..."}, ... }] }

Test POST /api/bundles/export
  → Depends(require_org_id)
  → Validation: goal≥10 chars, backstory≥10 chars → OK
  → patch("src.services.export_service.ExportService") → mock
    mock_instance.export.return_value = (VALID_ZIP_BYTES, "export_test.zip")
  → Response(media_type="application/zip")
  → zipfile.ZipFile(buffer) → valida agents/, manifest.json, hashes
```

#### Flujo D: Template picker
```
Test GET /api/templates → TemplateListResponse
  mock.table("agent_templates").select().execute().data = [TEMPLATE_DATA]
  → 200, verifica nombre y categoría

Test GET /api/templates/{id} → TemplateDetailResponse
  mock.table("agent_templates").select().eq(id).maybe_single().execute().data = TEMPLATE_DETAIL
  → 200, verifica soul_json, nombre, categories
```

### Contratos verificados (error handling)

| Endpoint | Error | Código | Mock necesario |
|---|---|---|---|
| `POST /agents` | Duplicate role → 409 | → upsert UPDATE (no error en código actual) | — |
| `POST /agents` | Sin org → 400 | `require_org_id` | X-Org-ID header en TestClient |
| `POST /flutter` | goal missing → 422 | bundles.py:218 | Sin org/validación |
| `GET /taskd/{id}` | Not found → 404 | tasks.py:89 | secuencia.result.data = [] |
| `GET /templates/{id}` | Not found → 404 | templates.py:82 | maybe_single.data = None |

### Middleware aplicables en tests E2E

| Middleware | Ubicación | Uso en test |
|---|---|---|
| `verify_org_membership` | `src/api/middleware.py:135` | Requiere header `Authorization: Bearer <token>` en POST `/agents/{role}/run`; `X-Org-ID` en todos |
| `require_org_id` | `src/api/middleware.py:66` | Requiere header `X-Org-ID` en 6 de 8 endpoints |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo Builder E2E validado

```
Supabase DB
  └─ agent_catalog, agent_templates, tasks, bundle_imports
       ↑↓
FastAPI Backend
  ├── GET /api/tools/available        → ToolsListResponse
  ├── GET /api/templates              → TemplateListResponse
  ├── GET /api/templates/{id}         → TemplateDetailResponse
  ├── POST /agents                    → AgentResponse (201)
  ├── GET /agents                     → ListAgentsResponse
  ├── POST /agents/{role}/run         → RunAgentResponse (202)
  ├── GET /tasks/{task_id}            → TaskResponse (polling)
  ├── POST /api/bundles/export        → Response(media_type=zip)
  ├── POST /api/bundles/import        → BundleRPCResult (201)
  └── services/export_service.py      → BundleManager.create_bundle() → ZIP
      ↑↓
Dashboard Frontend
  ├── AgentForm.tsx           → buildSingleAgentPayload() → agents[]
  ├── TemplatePicker.tsx      → GET /api/templates → applyTemplate()
  ├── AgentPlayground.tsx     → POST /agents/{role}/run → polling GET /tasks/{id}
  ├── CrewCanvas.tsx          → canvasToExportPayload() → POST /api/bundles/export
  └── ExportDialog.tsx        → fapDownload("/api/bundles/export")
```

### Coherencia: plan vs código

| Aspecto | Plan Paso 10 | Código real | Alineado |
|---|---|---|---|
| 9 sub-tests específicos | Sí | Sí | ✅ |
| `GET /api/tools/available` | tools reales | tools.py:46-63 | ✅ |
| `POST /api/bundles/export` | ZIP válido | bundles.py:199-210 | ✅ |
| `GET /api/templates` | devuelve templates | templates.py:54-67 | ✅ |
| `POST /agents` | guardar Supabase | agents.py:101-151 | ✅ |
| Template picker | rellena formulario | TemplatePicker.tsx | ✅ (backend confirmado) |
| Agent playground | probar agente | AgentPlayground.tsx → POST /agents/{role}/run | ✅ |
| Canvas crew | drag+conectar export | CrewCanvas.tsx → canvasToExportPayload | ✅ |
| Import roundtrip | exportar→importar | POST /api/bundles/export + POST /api/bundles/import | ✅ |
| Cobertura flujo completo | crear→probar→ensamblar→export→import | Cubierto por 9 tests | ✅ |

### Gaps detectados

| # | Gap | Severidad | Nota |
|---|---|---|---|
| G1 | `AgentMetaData` tabla opcional | Baja | Endpoint `GET /agents/{id}/detail` usa `agent_metadata` pero no afecta Paso 10 |
| G2 | `get_settings()` singleton | Media | TestClient → lifespan → `warmup_all_active_tenants()` llama `get_settings()` antes de que mock entre en vigor | 
| G3 | Multi-org en tests | Baja | Todos los tests usan org_id único por test |
| G4 | `tasks.result` como `str` vs `dict` en mock | Baja | Mock debe retornar `dict` para TaskResponse (`result: Optional[Dict]`) |

---

### Herramienta DX Propuesta: `fap builder test`

- **Qué automatiza:** Ejecuta los 9 tests E2E del builder en un solo comando con configuración de entorno estandarizada, sin tener que recordar flags de pytest ni rutas.
- **Tipo:** Sub-comando Typer en `src/cli/main.py` + wrapper de pytest
- **Cómo se usa:**
  ```bash
  fap builder test              # ejecuta 9 tests con pytest -k builder
  fap builder test --verbose    # verbose
  fap builder test --coverage   # con reporte de cobertura
  fap builder test --e2e-only   # solo tests marcados e2e
  ```
- **Impacto para el usuario final:** Un solo comando para validar que todo el flujo builder funciona después de cambios. No requiere recordar ni escribir `uv run pytest tests/e2e/ -k builder -v`.
- **Prioridad:** Tarea 0 — implementar antes de escribir tests

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Tipo | Verificable |
|---|---|---|---|
| AC01 | `test_tools_endpoint_returns_available` pasa | [BACKEND] | `uv run pytest tests/e2e/test_builder_e2e.py -k test_tools_endpoint_returns_available` → ✅ |
| AC02 | `test_bundle_export_generates_valid_zip` pasa | [BACKEND] | `$-k test_bundle_export` → ZIP parseable con zipfile |
| AC03 | `test_templates_endpoint_returns_templates` pasa | [BACKEND] | `$-k test_templates` → count ≥ 1 |
| AC04 | `test_create_agent_persists_in_supabase` pasa | [DATA] | POST /agents → 201, GET /agents → aparece en lista |
| AC05 | `test_template_picker_fills_form_data` pasa | [FULLSTACK] | GET template → detalles en TemplateDetailResponse |
| AC06 | `test_playground_executes_agent_returns_response` pasa | [BACKEND] | POST /agents/{role}/run → task_id, polling GET /tasks/{id} → completed |
| AC07 | `test_crew_canvas_export_validates_structure` pasa | [FULLSTACK] | `canvasToExportPayload()` → agents[] → export ZIP válido |
| AC08 | `test_roundtrip_export_import` pasa | [FULLSTACK] | Export ZIP → POST /api/bundles/import → 201, agents en catálogo |
| AC09 | Todos los tests pasan en batch | [INTEGRATION] | `uv run pytest tests/e2e/test_builder_e2e.py -k builder` → 9/9 ✅ |
| AC10 | DX Tooling: `fap builder test` se ejecuta sin errores | [DX] | `fap builder test` → salida limpia |

---

## 6️⃣ Riesgos

| # | Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|---|
| R01 | `BackgroundTasks` inline en TestClient vs. modo real | Media | En FastAPI `TestClient`, `BackgroundTasks` se ejecutan sincrónicamente dentro del thread del handler; en producción se ejecutan en threadpool. El test valida el caso inline pero no valida concurrencia. | Agregar `await asyncio.sleep(0)` o probar con `httpx.AsyncClient` + `anyio` para async real. Aceptar limitación: el sprint 10 es sobre flujo builder, no sobre concurrencia de BG. |
| R02 | `result` tipo mismatch mock → TaskResponse | Media | Mock devuelve `result: str` (str de Python), `TaskResponse.model_validate` espera `Optional[Dict[str, Any]]`. JSON serialización string→object posiblemente falle. | Mock debe retornar `.data[0]["result"]` como `dict`: `{"raw": "agent result string"}`. |
| R03 | MCP tools en `GET /api/tools/available` | Media | `_fetch_mcp_tools()` llama `MCPPool.get()`; si `get()` no está mockeado generará excepción. | Mock `src.tools.mcp_pool.MCPPool.get` para retornar pool mock con `get_tools` AsyncMock retornando `[]` (sin tools MCP) o lista con tools de prueba. |
| R04 | `agent_templates` global sin org_id — seed sincronía | Baja | Arrays de datos mock pueden entrar en race condition si `eq("name", name)` y `eq("is_system", true)` no filtran correctamente | Configurar mock con `eq` side_effect que busque por `name` |
| R05 | Tamaño de ZIP en test import | Baja | Si `create_full_stack_bundle()` incluye demasiados agentes puede exceder `max_bundle_size_mb=10` de config | Limitar test payload a 1-2 agentes |
| R06 | `run_agent_endpoint` + `verify_org_membership` → JWT | Baja | Endpoints con `verify_org_membership` requieren header `Authorization: Bearer <token>` que SuperAdmin valida contra JWKS endpoint real→ 401 sin config | Mock `src.mcp.auth.decode_jwt` para retornar `{"user_id": "test-user", "role": "fap_admin", "org_id": "test-org"}` |
| R07 | E2E tests sin router backend único | Baja | `TestClient(app)` carga todos los routers al importar `src.api.main`; si hay rutas conflictivas entre steps puede fallar | Asignar puerto/test env separado o usar `--confcutdir` para aislar E2E |
| R08 | Tests E2E vs CI/CD runner sin Supabase real | Media | Plan pide "Supabase real" → CI sin credenciales de Supabase fallará | CI configurar `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` como secrets; o mantener mock y ajustar criterio de aceptación |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica:** 1 tarea = 1 archivo/función/clase. Interfaz exacta en cada tarea. Patrón de referencia explícito. Verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear comando `fap builder test` | `src/cli/commands/builder_test.py` | `def builder_test_command(verbose: bool = False, coverage: bool = False, e2e_only: bool = False) -> None` | `src/cli/commands/templates_seed.py :: @templates_app.command("seed")` — patrón Typer sub-app | DX | Media | 1h | Ninguna | `fap builder test --help` ejecuta sin errores |
| 1 | Crear archivo de tests E2E del builder | `tests/e2e/test_builder_e2e.py` | 9 tests en 3 clases: `TestBuilderAPIEndpoints`, `TestBuilderAPIRoundtrip`, `TestBuilderPlayground` | `tests/e2e/test_mvp_certification.py :: TestMVPCertification` + `tests/unit/test_templates.py :: _mock_db()` | CODE | Media | 3h | Tarea 0 | `uv run pytest tests/e2e/test_builder_e2e.py -k builder -v` → 9/9 ✅ |
| 2 | Test: `GET /api/tools/available` devuelve tools reales | `test_builder_e2e.py :: TestBuilderAPIEndpoints::test_tools_endpoint_returns_available` (dentro de Tarea 1) | `def test_tools_endpoint_returns_available(self, api_client, mock_service_client)` → response.status_code == 200, `body["count"] >= 0`, `body["tools"]` es list | `tests/unit/test_templates.py :: test_list_all` | BACKEND | Baja | 0.5h | Tarea 1 | `uv run pytest ... -k test_tools_endpoint_returns_available` ✅ |
| 3 | Test: `POST /api/bundles/export` genera ZIP válido | `test_builder_e2e.py :: TestBuilderAPIEndpoints::test_bundle_export_generates_valid_zip` (dentro de Tarea 1) | `def test_bundle_export_generates_valid_zip(self, api_client)` → response.status_code == 200, `zipfile.ZipFile(buffer)` válido, `manifest.json` existe, `agents/` no vacío | `tests/e2e/test_bundle_export_roundtrip.py :: test_export_bundle_valid_structure` | BACKEND | Media | 1h | Tarea 1 | `uv run pytest ... -k test_bundle_export` ✅ |
| 4 | Test: `GET /api/templates` devuelve templates | `test_builder_e2e.py :: TestBuilderAPIEndpoints::test_templates_returns_system_templates` (dentro de Tarea 1) | `def test_templates_returns_system_templates(self, api_client, mock_service_client)` → status 200, `body["count"] >= 1`, `body["templates"][0]` tiene `name`, `category`, `soul_json` | `tests/unit/test_templates.py :: test_list_all` | BACKEND | Baja | 0.5h | Tarea 1 | `uv run pytest ... -k test_templates_returns_system_templates` ✅ |
| 5 | Test: crear agente guardado en Supabase | `test_builder_e2e.py :: TestBuilderCreateAgent::test_create_agent_persists_in_catalog` (dentro de Tarea 1) | `def test_create_agent_persists_in_catalog(self, api_client, mock_tenant_client)` → POST 201, luego GET 200 con mismo role | `tests/unit/test_templates.py :: test_get_by_id_found` + `agents.py:64-98` | DATA | Media | 1h | Tarea 1 | `uv run pytest ... -k test_create_agent_persists` ✅ |
| 6 | Test: template picker rellena formulario | `test_builder_e2e.py :: TestBuilderCreateAgent::test_template_picker_fills_form` (dentro de Tarea 1) | `def test_template_picker_fills_form(self, api_client, mock_service_client)` → GET /templates/{id} → status 200, soul_json contiene role/goal/backstory | `tests/unit/test_templates.py :: test_get_by_id_includes_soul_json` | FULLSTACK | Media | 1h | Tarea 1 | `uv run pytest ... -k test_template_picker_fills_form` ✅ |
| 7 | Test: playground ejecuta agente | `test_builder_e2e.py :: TestBuilderPlayground::test_playground_executes_and_polls` (dentro de Tarea 1) | `def test_playground_executes_and_polls(self, api_client, mock_tenant_client, mock_service_client)` → POST 202, polling GET completed, `result`, `tokens_used` | `tests/e2e/test_exec_agent_integration.py :: test_integration_flow_completes` | BACKEND | Alta | 1.5h | Tarea 1 | `uv run pytest ... -k test_playground_executes_and_polls` ✅ |
| 8 | Test: canvas export válido | `test_builder_e2e.py :: TestBuilderCrewExport::test_crew_canvas_export_valid_structure` (dentro de Tarea 1) | `def test_crew_canvas_export_valid_structure(self, api_client)` → ZIP parseable, `manifest.version=="2.0"`, `manifest.bundle_info` existe, `agents/` con JSONs válidos | `dashboard/lib/canvasUtils.ts::canvasToExportPayload` + `tests/e2e/test_bundle_export_roundtrip.py` | FULLSTACK | Media | 1h | Tarea 1 | `uv run pytest ... -k test_crew_canvas_export` ✅ |
| 9 | Test: import roundtrip | `test_builder_e2e.py :: TestBuilderCrewExport::test_roundtrip_export_import` (dentro de Tarea 1) | `def test_roundtrip_export_import(self, api_client, mock_tenant_client)` → ZIP generado → POST /api/bundles/import → 201, response.agents_count ≥ 1 | `tests/e2e/test_bundle_export_roundtrip.py::test_export_import_roundtrip` | FULLSTACK | Media | 1.5h | Tarea 1 | `uv run pytest ... -k test_roundtrip_export_import` ✅ |

**Tiempo total estimado:** ~10 horas (Tarea 0 + Tarea 1 de una sola vez, con YYY)

---

## 🔮 Roadmap (NO implementar ahora)

- **R02.1:** Implementar tests async reales con `httpx.AsyncClient` + `anyio` para validar concurrencia de `BackgroundTasks`
- **R05.1:** Agregar test con `register_flow` temporal en conftest para probar `flows/{flow_type}/run` end-to-end
- **G1.1:** Evaluar si `agent_metadata` tabla debe crearse y poblar en seed

---

## 🚫 Reglas de Oro (auto-chequeo)

- ✅ Análisis accionable y específico — cada discrepancy y gap tiene una acción concreta
- ✅ TODO verificado contra código — 24 elementos verificados §0
- ✅ Si el plan contradice el código — 4 discrepancias documentadas y resueltas
- ✅ Nivel CTO exigente — rutas exactas, firmas, columnas confirmadas
- ✅ Coherente con phase-state.md — estado confirmado
- ✅ TODO el paso — 9 sub-tareas cubiertas en §7
- ✅ Etapas secuenciales — §1→§2→§3→§4 aplicadas
- ✅ ≥ 1 herramienta DX — `fap builder test` en §7 Tarea 0
- ✅ Tareas atómicas — 1 archivo, 1 clase, 9 métodos
- ✅ Interfaz exacta — cada test tiene firma completa de función
- ✅ Verificación inline — cada tarea tiene `uv run pytest ... -k <test_name>` ✅
- ✅ ≤ 2 suposiciones — 4 discrepancias (D-01 a D-04), todas documentadas y resueltas
- ✅ 1 herramienta DX propuesta — `fap builder test`
