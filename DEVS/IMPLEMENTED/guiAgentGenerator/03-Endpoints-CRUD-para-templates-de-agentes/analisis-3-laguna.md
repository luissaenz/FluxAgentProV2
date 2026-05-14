# Análisis Paso 3 - laguna

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `agent_catalog` tabla existe | grep en `supabase/migrations/004_agent_catalog.sql` | ✅ | id UUID, org_id UUID, role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INT |
| 2 | `workflow_templates` tabla existe | grep en `supabase/migrations/006_workflow_templates.sql` | ✅ | Similar patrón: id, org_id, name, description, definition JSONB |
| 3 | RLS patrón `tenant_isolation` | mig 004, 006, 010 | ✅ | `org_id::text = current_org_id()` o `org_id::text = current_setting('app.org_id')` |
| 4 | `get_service_client` existe | grep en `src/db/session.py` | ✅ | Bypass RLS para queries internas |
| 5 | `require_org_id` middleware | `src/api/middleware.py:66` | ✅ | FastAPI Depends, extrae X-Org-ID header |
| 6 | Router registro en main.py | `src/api/main.py:98-112` | ✅ | NO en `__init__.py` (plan D4 corregido) |
| 7 | `tools.py` patrón GET listado | `src/api/routes/tools.py:46-63` | ✅ | `@router.get("/available")` con `response_model=ToolsListResponse` |
| 8 | `flows.py` patrón GET listado | `src/api/routes/flows.py:76-110` | ✅ | `@router.get("/available")` con filtro `?category=` |
| 9 | `ExportService` existe | `src/services/export_service.py` | ✅ | Ya implementado en Paso 2 |
| 10 | `BundleRPCPayload.skills` tipo | `src/services/bundle_schemas.py:68` | ✅ | `Dict[str, str]` no `List[Dict[str,str]]` |

### Discrepancias encontradas:

1. **❌ Tabla `agent_templates` NO existe** - Debe crearse migración nueva.
2. **❌ Endpoint `GET /api/templates` NO existe** - `templates.py` no está en `src/api/routes/`.
3. **⚠️ UUID naming inconsistencia** - Plan dice `id UUID` pero migrations usan `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` consistente.
4. **⚠️ Seed templates: 8 sistemas no definidos** - Plan menciona "Research Agent, Code Reviewer..." pero sin definición de `soul_json` exacto.
5. **⚠️ `is_system BOOLEAN` RLS** - Plan dice "lectura pública, escritura solo system" - necesario policy diferenciado.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema Nuevo

**Tabla `agent_templates`** (nueva):
```sql
-- supabase/migrations/00X_create_agent_templates.sql
CREATE TABLE agent_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,                    -- ej: "Research Agent"
    description TEXT,
    category TEXT NOT NULL,                  -- ej: "Research", "Development"
    soul_json JSONB NOT NULL DEFAULT '{}',   -- {role, goal, backstory}
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter INT DEFAULT 5 CHECK (max_iter BETWEEN 1 AND 50),
    is_system BOOLEAN DEFAULT FALSE,       -- templates predefinidos
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID,
    UNIQUE(org_id, name)
);

-- RLS: todos pueden leer, solo system puede escribir para is_system=true
ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "agent_templates_tenant_isolation" ON agent_templates
    FOR ALL USING (
        auth.role() = 'service_role'
        OR org_id::text = current_org_id()
    );

-- Policy especial para templates is_system=true (solo system role puede modificar)
CREATE POLICY "agent_templates_system_read_only" ON agent_templates
    FOR UPDATE USING (is_system = FALSE);
```

### Relaciones
- `agent_templates.org_id` → `organizations.id` (FK con CASCADE)
- No hay FK a `agent_catalog` - los templates son plantillas, no instancias

### Indexes necesarios
```sql
CREATE INDEX idx_agent_templates_category ON agent_templates(category) WHERE is_active;
CREATE INDEX idx_agent_templates_system ON agent_templates(is_system);
```

### Tipos de datos
- `soul_json` JSONB - validar estructura {role, goal, backstory} en service layer

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a crear

1. **`supabase/migrations/026_create_agent_templates.sql`** (nuevo)
2. **`src/api/routes/templates.py`** (nuevo)

### Firma de schemas Pydantic

```python
# src/api/routes/templates.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AgentTemplate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    soul_json: Dict[str, Any]  # {role, goal, backstory}
    suggested_tools: List[str] = []
    max_iter: int = 5
    is_system: bool = False

class TemplatesListResponse(BaseModel):
    templates: List[AgentTemplate]
    count: int
```

### Firma endpoints

```python
@router.get("", response_model=TemplatesListResponse)
async def list_templates(
    org_id: str = Depends(require_org_id),
    category: Optional[str] = Query(None),
) -> TemplatesListResponse:
    """Listar templates de agentes.
    
    - category: filtro opcional por categoría
    - Incluye templates is_system=true (públicos)
    """

@router.get("/{template_id}", response_model=AgentTemplate)
async def get_template(
    template_id: str,
    org_id: str = Depends(require_org_id),
) -> AgentTemplate:
    """Obtener template específico por ID."""
```

### Patrón a seguir
- **Referencia**: `src/api/routes/tools.py :: list_available_tools`
- **Referencia**: `src/api/routes/flows.py :: list_available_flows`
- Ambos usan `require_org_id`, response_model, filtro category

### Imports exactos
```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from src.api.middleware import require_org_id
from src.db.session import get_service_client
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints a crear

| Método | Ruta | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/api/templates` | require_org_id | `?category=` query | `TemplatesListResponse` |
| GET | `/api/templates/{id}` | require_org_id | path param id | `AgentTemplate` |

### Payload happy path

```json
GET /api/templates?category=Research
{
  "templates": [
    {
      "id": "uuid-123",
      "name": "Research Agent",
      "description": "Agent specialized in research tasks",
      "category": "Research",
      "soul_json": {
        "role": "Researcher",
        "goal": "Conduct thorough research on given topics",
        "backstory": "Expert in academic research with PhD in Computer Science"
      },
      "suggested_tools": ["web_search", "pdf_reader"],
      "max_iter": 5,
      "is_system": true
    }
  ],
  "count": 1
}
```

### Error handling
- 404: template_id no existe
- 500: error DB

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end
```
Builder → GET /api/templates → TemplatePicker → User selecciona → Form auto-completa
```

### Herramienta Propuesta: template-seeder

- **Qué automatiza:** Crear templates iniciales desde archivo JSON o CSV, evitando seed manual.
- **Tipo:** Script CLI
- **Cómo se usa:**
  ```bash
  uv run python scripts/template_seeder.py --file templates_seed.json
  ```
- **Impacto:** Reduce tiempo de setup de 2h (manual SQL) a 5min (ejecución script)
- **Prioridad:** Tarea 0

### Seed templates definitivos

```python
SEED_TEMPLATES = [
    {
        "name": "Research Agent",
        "description": "Conducts thorough research on topics",
        "category": "Research",
        "soul_json": {
            "role": "Research Specialist",
            "goal": "Research topics thoroughly and synthesize findings into actionable insights",
            "backstory": "PhD in Information Science with 10+ years experience in academic research"
        },
        "suggested_tools": ["web_search", "paper_reader", "summarizer"],
        "max_iter": 5,
        "is_system": True
    },
    {
        "name": "Code Reviewer",
        "description": "Reviews code for quality and best practices",
        "category": "Development",
        "soul_json": {
            "role": "Senior Code Reviewer",
            "goal": "Review code submissions for quality, security, and maintainability",
            "backstory": "Senior software engineer with expertise in multiple programming languages and security best practices"
        },
        "suggested_tools": ["code_analyzer", "security_scanner"],
        "max_iter": 3,
        "is_system": True
    },
    # ... 6 más
]
```

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | [DATA] Tabla `agent_templates` creada con migración versionada | ✅ SQL ejecutado sin errores |
| 2 | [DATA] Seed contiene 8 templates con `is_system: true` | ✅ `SELECT COUNT(*) FROM agent_templates WHERE is_system = true` = 8 |
| 3 | [BACKEND] `GET /api/templates` devuelve array de templates | ✅ `curl localhost:8000/api/templates -H "X-Org-ID: test"` → 200 + JSON |
| 4 | [BACKEND] `GET /api/templates/{id}` devuelve template con soul_json | ✅ Devuelve JSON completo con todos los campos |
| 5 | [BACKEND] Filtro `?category=` funciona | ✅ `?category=Research` devuelve solo Research templates |
| 6 | [CODE] Router registrado en main.py | ✅ `include_router(templates_router)` presente |
| 7 | [DATA] RLS aplicado: lectura pública, escritura solo tenant | ✅ Policy verificada en migration |
| 8 | [DX] template-seeder implementado | ✅ Script ejecuta sin errores |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Contenido templates inadecuado | Media | 8 templates sin definición exacta de soul_json | Definir contenido específico antes de seed |
| RLS policy muy restrictiva | Media | `is_system=true` solo lectura puede bloquear updates | Policy claro: UPDATE solo si is_system=FALSE o service_role |
| Conflicto con agent_catalog | Baja | Tabla similar pero propósito diferente | Diferenciación clara: templates son plantillas, agent_catalog son instancias |
| Seed no idempotente | Baja | Re-ejecución crea duplicados | INSERT ... ON CONFLICT DO NOTHING o DELETE before insert |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo | Verificación |
|---|---|---|---|---|---|---|---|---|
| 0 | DX: template-seeder | `scripts/template_seeder.py` | `def seed_templates(templates: List[dict]) -> int` | Nuevo | DX | Baja | 0.5h | → `python scripts/template_seeder.py --dry-run` |
| 1 | Crear migración tabla | `supabase/migrations/026_create_agent_templates.sql` | Schema tabla + RLS policy | `004_agent_catalog.sql` | DATA | Baja | 0.5h | → `psql -f migration.sql` sin errores |
| 2 | Seed templates | `scripts/template_seeder.py` o función en migration | 8 templates INSERT | `014_bartenders_seed_config.sql` | DATA | Baja | 1h | → `SELECT COUNT(*) FROM agent_templates` = 8 |
| 3 | Crear templates.py | `src/api/routes/templates.py` | `@router.get("")`, `@router.get("/{id}")` | `src/api/routes/tools.py` | BACKEND | Media | 1h | → `curl localhost:8000/api/templates` devuelve 200 |
| 4 | Registrar router | `src/api/main.py` | `include_router(templates_router)` | `src/api/main.py:112` | BACKEND | Baja | 0.2h | → Import funciona sin error |
| 5 | Validar flujo completo | — | — | — | FULLSTACK | Baja | 0.5h | → Todas las verificaciones pasan |

**Tiempo total estimado:** 3.7 horas