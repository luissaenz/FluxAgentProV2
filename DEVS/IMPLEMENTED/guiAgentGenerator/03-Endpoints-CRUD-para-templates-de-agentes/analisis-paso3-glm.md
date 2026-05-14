# 🧠 Análisis Técnico — Paso 03: Endpoints CRUD para templates de agentes

> **Agente:** glm | **Paso:** 03 | **Fase:** guiAgentGenerator

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | Tabla `agent_templates` NO existe en DB | grep en `supabase/migrations/` | ❌ DISCREPANCIA | No hay migración para `agent_templates`. Solo existe `.kilo/plans/` con diseño previo no implementado |
| 2 | Archivo `src/api/routes/templates.py` NO existe | ls en `src/api/routes/` | ❌ DISCREPANCIA | No existe. Crear nuevo. |
| 3 | Ruta `/api/templates` NO registrada | grep en `src/api/main.py` | ❌ DISCREPANCIA | `main.py` no importa/templates router |
| 4 | Tabla `organizations` existe | mig `001_set_config_rpc.sql:53` | ✅ VERIFICADO | FK válida |
| 5 | Tabla `agent_catalog` existe con RLS | mig `004_agent_catalog.sql:1-27` | ✅ VERIFICADO | Patrón RLS: `org_id::text = current_org_id()` |
| 6 | Patrón `TenantClient` para queries RLS | `src/db/session.py:96-231` | ✅ VERIFICADO | `with get_tenant_client(org_id) as db:` |
| 7 | Patrón `get_service_client()` para bypass RLS | `src/db/session.py:55-73` | ✅ VERIFICADO | `db = get_service_client()` |
| 8 | Patrón ruta CRUD: `workflows.py` | `src/api/routes/workflows.py:1-88` | ✅ VERIFICADO | `APIRouter`, `Depends(require_org_id)`, `get_tenant_client()` |
| 9 | Patrón Pydantic response: `ToolsListResponse` | `src/api/routes/tools.py:39-43` | ✅ VERIFICADO | `response_model=ToolsListResponse` con `count` |
| 10 | `require_org_id` middleware | `src/api/middleware.py:66-81` | ✅ VERIFICADO | `Depends(require_org_id)` extrae `X-Org-ID` |
| 11 | Función `current_org_id()` SQL helper | mig `001_set_config_rpc.sql:37-45` | ✅ VERIFICADO | Retorna `current_setting('app.org_id', TRUE)` |
| 12 | Patrón RLS moderno: `service_role` bypass | mig `025_agent_catalog_rls_update.sql:11-15` | ✅ VERIFICADO | `auth.role() = 'service_role' OR org_id::text = current_org_id()` |
| 13 | `agent_catalog.soul_json` es JSONB | mig `004_agent_catalog.sql:11` | ✅ VERIFICADO | `soul_json JSONB NOT NULL DEFAULT '{}'` — compatible con templates |
| 14 | `agent_catalog` tiene `allowed_tools TEXT[]` y `max_iter INT` | mig `004_agent_catalog.sql:12-13` | ✅ VERIFICADO | Mismos tipos que `suggested_tools TEXT[]` y `max_iter INT` |
| 15 | `__init__.py` en routes es stub | `src/api/routes/__init__.py:1` | ✅ VERIFICADO | Solo docstring. Routers se registran en `main.py` |
| 16 | Patrón seed: `014_bartenders_seed_config.sql` | mig `014_bartenders_seed_config.sql:1-64` | ✅ VERIFICADO | `INSERT ... ON CONFLICT DO NOTHING` en migración separada |
| 17 | Patrón router prefix: `/api/` + dominio | `tools.py:22`, `bundles.py:28` | ✅ VERIFICADO | `prefix="/api/tools"`, `prefix="/api/bundles"` |
| 18 | `script/seed_system_bundles.py` usa `ImportService` | `scripts/seed_system_bundles.py:9` | ✅ VERIFICADO | Patrón seed vía servicio Python (no SQL directo para bundles) |

### Discrepancias Encontradas

**D1 — `agent_templates` NO tiene `org_id` en el plan**
- Plan define: `id UUID, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INT, is_system BOOLEAN`
- **Falta `org_id`**. Templates del sistema (`is_system=true`) son globales (sin org_id o `org_id=NULL`), pero templates custom de usuarios necesitan `org_id` para aislamiento. Sin esto, no hay RLS.
- **Resolución:** Agregar `org_id UUID REFERENCES organizations(id)` con `NULL` permitido. `is_system=true` → `org_id=NULL`. `is_system=false` → `org_id=UUID del tenant`.

**D2 — Falta `created_at` / `updated_at`**
- Plan no los menciona. Toda tabla del proyecto tiene timestamps (`created_at TIMESTAMPTZ DEFAULT now()`).
- **Resolución:** Agregar `created_at TIMESTAMPTZ DEFAULT now()` y `updated_at TIMESTAMPTZ DEFAULT now()`.

**D3 — Falta índice por `category`**
- Plan menciona filtro `?category=`. Sin índice, query escanea toda la tabla.
- **Resolución:** Agregar `CREATE INDEX idx_agent_templates_category ON agent_templates(category) WHERE is_system = TRUE;`

**D4 — Falta UNIQUE constraint**
- Los templates del sistema deben ser únicos por nombre. Si no, seed duplica en re-run.
- **Resolución:** Agregar `UNIQUE(org_id, name)` para custom + `UNIQUE NULLS NOT DISTINCT (name) WHERE is_system = TRUE` para system. Alternativa simple: `UNIQUE(name) WHERE is_system = TRUE` como partial unique index.

**D5 — Seed en migración vs seed en script Python**
- El plan dice "Seed inicial con 8 templates predefinidos" sin especificar método.
- Las migraciones `014` y `017` usan SQL `INSERT ... ON CONFLICT DO NOTHING` para seeds estáticos.
- **Resolución:** Seed en migración SQL separada (patrón consistente con `014_bartenders_seed_config.sql`). Los 8 templates son datos estáticos, tipo config del sistema.

**D6 — `GET /api/templates/{id}` sin protección solo lectura pública**
- Plan dice "RLS aplicado: lectura pública, escritura solo system". Pero `require_org_id` exige header `X-Org-ID`.
- Los templates del sistema NO tienen `org_id`, entonces `require_org_id` no sirve para filtrar.
- **Resolución:** Endpoint `GET /api/templates` sin auth para `is_system=true` + `Depends(require_org_id)` para custom templates. Simplificación MVP: todo el endpoint usa `Depends(require_org_id)`. Templates del sistema se leen con `org_id=NULL` usando `get_service_client()`. Templates custom con `TenantClient`.

**D7 — Router NO se registra en `__init__.py`**
- Fase anterior demostró que routers se registran en `main.py`, no en `__init__.py` (corrección D4 del Paso 1).
- **Resolución:** Registrar en `main.py:31+` con `from .routes.templates import router as templates_router` y `app.include_router(templates_router)`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema: Tabla Nueva `agent_templates`

```sql
CREATE TABLE IF NOT EXISTS agent_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT 'general',
    soul_json       JSONB NOT NULL DEFAULT '{}',
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter        INT DEFAULT 5,
    is_system       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

### Integridad Referencial
- `org_id → organizations(id) ON DELETE CASCADE` — Eliminar org elimina templates custom.
- Templates del sistema (`is_system=true`) tienen `org_id=NULL`. FK permite NULL → OK con `REFERENCES organizations(id)` (sin `NOT NULL`).
- No FK a `agent_catalog` — templates son previos a la instanciación. Relación lógica, no referencial.

### RLS Policies
```sql
ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY;

-- Lectura: todos pueden leer system templates
CREATE POLICY "templates_read_system" ON agent_templates
    FOR SELECT USING (is_system = TRUE);

-- Lectura: tenant lee sus propios templates
CREATE POLICY "templates_read_own" ON agent_templates
    FOR SELECT USING (
        NOT is_system AND org_id::text = current_org_id()
    );

-- Escritura: solo system_role o member del org
CREATE POLICY "templates_insert_own" ON agent_templates
    FOR INSERT WITH CHECK (
        NOT is_system AND org_id::text = current_org_id()
    );

CREATE POLICY "templates_update_own" ON agent_templates
    FOR UPDATE USING (
        NOT is_system AND org_id::text = current_org_id()
    );

CREATE POLICY "templates_delete_own" ON agent_templates
    FOR DELETE USING (
        NOT is_system AND org_id::text = current_org_id()
    );

-- Bypass para service_role (operaciones internas, seed, etc.)
CREATE POLICY "templates_service_role" ON agent_templates
    FOR ALL USING (auth.role() = 'service_role');
```

### Índices
```sql
-- Para GET /api/templates?category=X (system templates)
CREATE INDEX idx_agent_templates_system_category
    ON agent_templates(category) WHERE is_system = TRUE;

-- Para listar templates de un org
CREATE INDEX idx_agent_templates_org
    ON agent_templates(org_id) WHERE is_system = FALSE;

-- Para búsqueda por nombre
CREATE INDEX idx_agent_templates_name
    ON agent_templates(name);

-- Partial unique: system templates no duplican nombres
CREATE UNIQUE INDEX idx_agent_templates_system_unique_name
    ON agent_templates(name) WHERE is_system = TRUE;

-- Unique: custom templates no duplican dentro del org
CREATE UNIQUE INDEX idx_agent_templates_org_unique_name
    ON agent_templates(org_id, name) WHERE is_system = FALSE;
```

### Tipos de Datos Problemáticos
- `soul_json JSONB DEFAULT '{}'` — Debevalidar que contiene `role`, `goal`, `backstory`. Pero la validación va en la capa API, no en DB constraint (consistente con `agent_catalog.soul_json`). Los system templates se seedean con valores correctos.
- `suggested_tools TEXT[]` — Array PostgreSQL requiere cuidado en Supabase client: pasar como `list[str]` en Python, se serializa como `TEXT[]` automáticamente.

### Diagrama ER

```
organizations (1) ──< agent_templates (N)
                     ┌──────────────────────────┐
                     │ id: UUID PK              │
                     │ org_id: UUID FK→orgs     │ ← NULL para system
                     │ name: TEXT NOT NULL       │
                     │ description: TEXT         │
                     │ category: TEXT             │
                     │ soul_json: JSONB          │ ← {role, goal, backstory}
                     │ suggested_tools: TEXT[]    │
                     │ max_iter: INT DEFAULT 5   │
                     │ is_system: BOOLEAN         │ ← TRUE=fijos, FALSE=custom
                     │ created_at, updated_at    │
                     └──────────────────────────┘
```

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/Clases Nuevas

**Modelos Pydantic** (`src/api/routes/templates.py`):

```python
class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    category: str
    soul_json: Dict
    suggested_tools: List[str]
    max_iter: int
    is_system: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class TemplateListResponse(BaseModel):
    templates: List[TemplateInfo]
    count: int

class TemplateDetailResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    soul_json: Dict
    suggested_tools: List[str]
    max_iter: int
    is_system: bool
    org_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

**Router** (`src/api/routes/templates.py`):

```python
router = APIRouter(prefix="/api/templates", tags=["templates"])

@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    org_id: str = Depends(require_org_id),
    category: Optional[str] = Query(None),
): ...

@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: str,
    org_id: str = Depends(require_org_id),
): ...
```

### Patrones: Se Siguen los Existentes

1. **Router + Pydantic models en mismo archivo** → Patrón: `tools.py` define `ToolInfo` + `ToolsListResponse` + router en mismo archivo.
2. **`Depends(require_org_id)`** → Patrón: todas las rutas usan este dependency. `tools.py:48`, `bundles.py:207`.
3. **`get_tenant_client(org_id)` para queries con RLS** → Patrón: `workflows.py:35`, `agents.py:38`.
4. **`get_service_client()` para bypass RLS** → Patrón: `tools.py:111` para leer sin tenant isolation.
5. **`maybe_single()` para fetch by ID** → Patrón: `workflows.py:62-66`.
6. **Response con `count`** → Patrón: `tools.py:63` (`ToolsListResponse(tools=..., count=...)`).
7. **Router registrado en `main.py`** → Patrón: `main.py:20-34` (imports) + `main.py:98-112` (include_router).

### Modularidad
- Un solo archivo nuevo: `src/api/routes/templates.py` (router + modelos).
- Migración nueva: `supabase/migrations/026_agent_templates.sql`.
- Seed migración: `supabase/migrations/027_agent_templates_seed.sql`.
- Línea nueva en `src/api/main.py` (import + include_router).
- Sin servicio separado — la lógica es simple (2 endpoints de lectura). Si se añade CRUD completo POST/PUT/DELETE en futuro, se extrae servicio.

### Imports Exactos
```python
from __future__ import annotations
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from src.api.middleware import require_org_id
from src.db.session import get_service_client, get_tenant_client
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints

| Método | Ruta | Descripción | Auth | Input | Output |
|--------|------|-------------|------|-------|--------|
| GET | `/api/templates` | Listar templates (system + custom del org) | `require_org_id` | `?category=` (query param, opcional) | `TemplateListResponse` con `count` |
| GET | `/api/templates/{template_id}` | Obtener template por ID | `require_org_id` | Path param `template_id` UUID | `TemplateDetailResponse` |

### Middleware
- `require_org_id` extrae `X-Org-ID` del header. Si falta → 400.
- Para templates del sistema (`is_system=true`, `org_id=NULL`): se usa `get_service_client()` para bypasear RLS.
- Para templates custom: se usa `TenantClient` con `org_id` del header.

### Flujo de Datos — GET /api/templates

```
Request → require_org_id (extrae org_id)
        → get_service_client().table("agent_templates")
            .select("*")
            .eq("is_system", True)  ← system templates
        → get_tenant_client(org_id).table("agent_templates")
            .select("*")
            .eq("is_system", False)
            .eq("org_id", org_id)   ← custom templates del org
        → Combinar resultados
        → Si ?category=X, filtrar en Python (ambos ya traen category)
        → TemplateListResponse(templates=..., count=...)
```

**Optimización:** Usar `get_service_client()` para todo con filtro manual `eq("org_id", org_id)` + `eq("is_system", True)` en una sola query, como hace `tools.py:111`. Así evitamos 2 queries.

### Flujo de Datos — GET /api/templates/{template_id}

```
Request → require_org_id
        → get_service_client()
            .table("agent_templates")
            .select("*")
            .eq("id", template_id)
            .maybe_single()
            .execute()
        → Si is_system=false AND org_id != header org_id → 403 Forbidden
        → Si no existe → 404
        → TemplateDetailResponse(...)
```

### Contratos

**GET /api/templates** — Happy Path:
```json
// Request: GET /api/templates?category=Research
// Headers: X-Org-ID: <uuid>
// Response 200:
{
  "templates": [
    {
      "id": "uuid-1",
      "name": "Research Agent",
      "description": "Specialized in web research and analysis",
      "category": "Research",
      "soul_json": {"role": "researcher", "goal": "...", "backstory": "..."},
      "suggested_tools": ["fetch_url", "search_web"],
      "max_iter": 5,
      "is_system": true,
      "created_at": "2026-05-13T00:00:00Z",
      "updated_at": "2026-05-13T00:00:00Z"
    },
    {
      "id": "uuid-2",
      "name": "Custom Analyzer",
      "description": "...",
      "category": "Research",
      "soul_json": {...},
      "suggested_tools": ["mcp:brave:search"],
      "max_iter": 3,
      "is_system": false,
      "created_at": "...",
      "updated_at": "...",
    }
  ],
  "count": 2
}
```

**GET /api/templates/{id}** — Happy Path:
```json
// Request: GET /api/templates/<uuid>
// Headers: X-Org-ID: <uuid>
// Response 200:
{
  "id": "uuid-1",
  "name": "Research Agent",
  "description": "Specialized in web research and analysis",
  "category": "Research",
  "soul_json": {"role": "researcher", "goal": "...", "backstory": "..."},
  "suggested_tools": ["fetch_url", "search_web"],
  "max_iter": 5,
  "is_system": true,
  "org_id": null,
  "created_at": "2026-05-13T00:00:00Z",
  "updated_at": "2026-05-13T00:00:00Z"
}
```

**Error responses:**
- `400` — X-Org-ID ausente (middleware `require_org_id`)
- `404` — Template no encontrado
- `403` — Template custom de otro org

### Error Handling
- Template no encontrado → `HTTPException(404, "Template not found")`
- Acceso a template de otro org → `HTTPException(403, "Not authorized to access this template")`
- Error de DB → `HTTPException(500, ...)` con logger.exception (patrón `bundles.py:248-252`)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo Completo: DB → Backend → Frontend → UX

```
[Supabase DB]                    [FastAPI Backend]                [Next.js Frontend]
agent_templates ────────────→ GET /api/templates ────────────→ TemplatePicker.tsx
  │ is_system=true               │ combina system+custom          │ grid de cards
  │ is_system=false              │ con category filter             │ filtro por categoría
  └──────────────────────────→ GET /api/templates/{id} ────→ AgentForm.tsx
                                 │ soul_json completo              │ auto-fill formulario
```

### Coherencia End-to-End
- **DB:** `soul_json` en `agent_templates` usa misma estructura que `agent_catalog.soul_json` → compatible con Paso 04 (builder).
- **API:** `suggested_tools` son nombres de herramientas que coinciden con `GET /api/tools/available` → compatible con multi-select del builder.
- **UX:** Template selector (Paso 05) consumirá `GET /api/templates` → mismo formato.

### Gaps
- **Sin endpoint POST/PUT/DELETE para templates custom.** El plan solo pide GET. Crear templates custom queda fuera del scope MVP, pero la tabla soporta `is_system=false` + `org_id`. Se puede añadir en Paso 04 o posterior sin breaking change.
- **Seed data estática.** Los 8 templates son hardcoded en SQL. Si se necesita modificar, requiere nueva migración. Aceptable para MVP.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap templates list
- **Qué automatiza:** Listar templates disponibles desde CLI sin abrir dashboard. Dogfooding del endpoint para debugging during development.
- **Tipo:** CLI (Typer sub-app)
- **Cómo se usa:** `fap templates list --org-id <uuid> [--category Research] [--json]`
- **Impacto para el usuario final:** Desarrollador puede verificar templates sin curl/Postman. Consistente con `fap tools list` existente.
- **Prioridad:** Tarea 0 — implementar antes que el resto
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `agent_templates` creada con migración 026
✅ [DATA] Columnas: id, org_id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at
✅ [DATA] RLS: lectura pública system templates + tenant isolation para custom
✅ [DATA] Índices: category, org_id, nombre (unique partial)
✅ [DATA] Seed migración 027 con 8 templates (is_system=true)
✅ [CODE] Archivo `src/api/routes/templates.py` existe con router + modelos Pydantic
✅ [CODE] Router registrado en `src/api/main.py` con prefix `/api/templates`
✅ [CODE] Modelos: TemplateInfo, TemplateListResponse, TemplateDetailResponse
✅ [CODE] Patrón consistente con `tools.py`: response con `count`, `Depends(require_org_id)`
✅ [BACKEND] GET /api/templates responde 200 con array de templates (system + custom)
✅ [BACKEND] GET /api/templates?category=Research filtra por categoría
✅ [BACKEND] GET /api/templates/{id} responde 200 con template completo
✅ [BACKEND] GET /api/templates/{id} con ID inexistente → 404
✅ [BACKEND] Template custom de otro org → 403
✅ [BACKEND] Templates del sistema (is_system=true) visibles para cualquier org
✅ [FULLSTACK] `soul_json` compatible con `agent_catalog.soul_json` (mismo formato {role, goal, backstory})
✅ [FULLSTACK] `suggested_tools` usa nombres de herramientas que existen en ToolRegistry
✅ [DX] `fap templates list` ejecuta sin errores y lista templates en terminal
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| RLS query lenta con大量 system templates | Baja | No hay índice compuesto categoría+Sistema | Índice partial `WHERE is_system = TRUE` cubre el caso |
| Templates del sistema sin org_id rompen `require_org_id` si se filtra por org | Alta | RLS usa `current_org_id()` que no funciona para NULL org_id | Usar `get_service_client()` para system templates + filtrar custom por org_id manualmente |
| Seed SQL con ON CONFLICT puede fallar si migra con datos previos | Baja | Re-ejecución de migración con datos | `ON CONFLICT DO NOTHING` previene duplicados |
| `suggested_tools` referencia tools que pueden no existir en ToolRegistry | Media | Templates son genéricos, tools son dinámicos por org | Frontend debe filtrar suggested_tools contra `GET /api/tools/available` |
| Soul_json válido en seed pero incompatible con algún LLM provider | Baja | Templates son sugerencias, no configuración estricta | El builder (Paso 04) permite editar antes de guardar |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|--------------|--------------|
| 0 | **DX & Tooling: fap templates list** | `src/cli/commands/templates_list.py` | `def list_templates(org_id: str, category: Optional[str], json_output: bool): ...` | `src/cli/commands/tools_list.py` | DX | Baja | 0.5h | Ninguna | → verificar: `uv run fap templates list --help` ejecuta sin errores |
| 1 | Crear migración tabla `agent_templates` | `supabase/migrations/026_agent_templates.sql` | Columnas: `id UUID PK DEFAULT gen_random_uuid()`, `org_id UUID FK REFERENCES organizations(id) ON DELETE CASCADE`, `name TEXT NOT NULL`, `description TEXT NOT NULL DEFAULT ''`, `category TEXT NOT NULL DEFAULT 'general'`, `soul_json JSONB NOT NULL DEFAULT '{}'`, `suggested_tools TEXT[] DEFAULT '{}'`, `max_iter INT DEFAULT 5`, `is_system BOOLEAN NOT NULL DEFAULT FALSE`, `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()`. + RLS policies (5: select system, select own, insert own, update own, delete own, service_role bypass). + Índices (4: system_category, org_id, name, system_unique_name, org_unique_name) | `supabase/migrations/004_agent_catalog.sql` + `supabase/migrations/025_agent_catalog_rls_update.sql` | DATA | Baja | 0.5h | Ninguna | → verificar: Migración ejecuta sin errores en Supabase Studio |
| 2 | Crear seed migración con 8 templates | `supabase/migrations/027_agent_templates_seed.sql` | 8 INSERTs: Research Agent (category="Research"), Code Reviewer (category="Development"), Data Analyst (category="Development"), Customer Support (category="Support"), Document Writer (category="Writing"), Translator (category="Writing"), Summarizer (category="Research"), General Assistant (category="General"). Cada uno con `is_system=TRUE`, `org_id=NULL`, `soul_json` con role/goal/backstory completos, `suggested_tools` con tools existentes del ToolRegistry, `max_iter=5` | `supabase/migrations/014_bartenders_seed_config.sql` | DATA | Baja | 0.5h | Tarea 1 | → verificar: `SELECT count(*) FROM agent_templates WHERE is_system = TRUE;` retorna 8 |
| 3 | Crear modelos Pydantic para templates | `src/api/routes/templates.py` (primera parte) | `TemplateInfo(BaseModel)`: id:str, name:str, description:str, category:str, soul_json:Dict, suggested_tools:List[str], max_iter:int, is_system:bool, created_at:Optional[str]=None, updated_at:Optional[str]=None. `TemplateListResponse(BaseModel)`: templates:List[TemplateInfo], count:int. `TemplateDetailResponse(BaseModel)`: idem TemplateInfo + org_id:Optional[str]=None | `src/api/routes/tools.py:25-44` | CODE | Baja | 0.25h | Ninguna | → verificar: `from src.api.routes.templates import TemplateListResponse` importa sin error |
| 4 | Crear endpoint GET /api/templates | `src/api/routes/templates.py` (segunda parte) | `async def list_templates(org_id: str = Depends(require_org_id), category: Optional[str] = Query(None)) -> TemplateListResponse` — Usa `get_service_client()` para obtener system templates + custom templates del org. Filtra `category` en Python si se pasa. | `src/api/routes/tools.py:46-63` (list_available_tools) + `src/api/routes/workflows.py:29-49` (list_workflows) | BACKEND | Media | 1h | Tarea 3 | → verificar: `uv run pytest tests/unit/test_templates.py -v` pasa |
| 5 | Crear endpoint GET /api/templates/{id} | `src/api/routes/templates.py` (tercera parte) | `async def get_template(template_id: str, org_id: str = Depends(require_org_id)) -> TemplateDetailResponse` — Usa `get_service_client()` para fetch by ID. Si `is_system=false` y `org_id != header org_id` → 403. Si no existe → 404. | `src/api/routes/workflows.py:52-71` (get_workflow) | BACKEND | Media | 0.5h | Tarea 4 | → verificar: `uv run pytest tests/unit/test_templates.py -v -k test_get_template` pasa |
| 6 | Registrar router en main.py | `src/api/main.py` | Añadir: `from .routes.templates import router as templates_router` (línea ~33) + `app.include_router(templates_router)` (línea ~113) | `src/api/main.py:31+112` (patrón tools_router) | CODE | Baja | 0.1h | Tarea 5 | → verificar: `uv run python -c "from src.api.main import app; print(len(app.routes))"` sin error y `/api/templates` aparece en routes |
| 7 | CLI: fap templates list | `src/cli/commands/templates_list.py` | `def list_templates(org_id: str = typer.Option(...), category: Optional[str] = typer.Option(None), json_output: bool = typer.Option(False)): ...` — Usa `httpx.get(f"{API_URL}/api/templates", headers={"X-Org-ID": org_id})`. Tabla bonita en terminal (rich), o JSON con `--json`. | `src/cli/commands/tools_list.py:29-64` | BACKEND | Baja | 0.5h | Tarea 6 | → verificar: `uv run fap templates list --org-id test --json` ejecuta sin errores (puede dar 400 si org no existe, pero no crash) |
| 8 | Registrar CLI sub-app | `src/cli/main.py` | Añadir: `from src.cli.commands.templates_list import templates_app` + `app.add_typer(templates_app, name="templates")` | `src/cli/main.py:35+56` (patrón tools) | CODE | Baja | 0.1h | Tarea 7 | → verificar: `uv run fap templates list --help` muestra help sin errores |
| 9 | Tests unitarios | `tests/unit/test_templates.py` | Test list_templates con mock (system + custom). Test get_template by ID. Test category filter. Test 404. Test 403 cross-org. Test seed count. | `tests/unit/test_bundle_export.py` | CODE | Media | 1h | Tareas 4-5 | → verificar: `uv run pytest tests/unit/test_templates.py -v` pasa todos |
| 10 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-9 | → verificar: Criterios §5 [DATA], [BACKEND], [DX] pasan todos |

**Tiempo total estimado:** 5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **POST/PUT/DELETE endpoints para templates custom** — permitir a usuarios crear templates propios desde el builder. Tabla ya soporta `is_system=false`.
- **Cache de templates** — si el listado se vuelve lento con muchos templates, agregar `lru_cache` con TTL (similar a `ToolRegistry`).
- **Fuzzy search en templates** — reemplazar filtro exacto `?category=` por búsqueda `?q=` con ILIKE sobre name/description.
- **Template versioning** — columna `version INT DEFAULT 1` para trackear actualizaciones de system templates sin romper instancias existentes.
- **Relación template → agent_instanciado** — agregar `template_id UUID REFERENCES agent_templates(id)` a `agent_catalog` para rastrear desde qué template se creó un agente.