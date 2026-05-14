# 🧠 Análisis Técnico — Paso 03: Endpoints CRUD para Templates de Agentes

> **Agente:** ring  
> **Fecha:** 2026-05-13  
> **Archivo destino:** `DEVS/IN_PROGRESS/analisis-paso-03-ring.md`

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | grep en `supabase/migrations/` | ❌ NO EXISTE | No hay migración que la cree. Debe crearse como migración 030 |
| 2 | Archivo `src/api/routes/templates.py` | ls en `src/api/routes/` | ❌ NO EXISTE | Los archivos existentes: agents.py, bundles.py, flows.py, tools.py, etc. No existe templates.py |
| 3 | Router registrado en `src/api/__init__.py` | cat `src/api/__init__.py` | ⚠️ DISCREPANCIA | `__init__.py` solo contiene un docstring. Todos los routers se registran en `src/api/main.py` (líneas 98-112) |
| 4 | Endpoint `GET /api/tools/available` como referencia | cat `src/api/routes/tools.py` | ✅ VERIFICADO | Patrón APIRouter + Depends(require_org_id) + Pydantic models |
| 5 | Migración `agent_catalog` como referencia de RLS | cat `supabase/migrations/004_agent_catalog.sql` | ✅ VERIFICADO | RLS tenant_isolation con `current_setting('app.org_id')` |
| 6 | Migración moderna con service_role bypass | cat `supabase/migrations/025_agent_catalog_rls_update.sql` | ✅ VERIFICADO | Patrón actualizado: `auth.role() = 'service_role' OR org_id::text = current_org_id()` |
| 7 | Seed script como referencia | cat `scripts/seed_system_bundles.py` | ✅ VERIFICADO | Usa `BundleManager`, `ImportService`, `SYSTEM_ORG_ID` |
| 8 | Modelos Bundle como referencia | cat `src/services/bundle_schemas.py` | ✅ VERIFICADO | `AgentExportItem` tiene `role`, `soul_json`, `allowed_tools`, `max_iter` |
| 9 | `current_org_id()` function | grep en migraciones | ✅ VERIFICADO | Usado en mig 025 en lugar de `current_setting('app.org_id')` |

### Discrepancias encontradas:

1. **D-01: Router en `__init__.py` vs `main.py`** — El plan (paso 03, tarea 2) indica registrar en `src/api/__init__.py`, pero el patrón real del proyecto registra todos los routers en `src/api/main.py` (líneas 98-112). **Resolución:** registrar en `main.py` siguiendo el patrón existente.

2. **D-02: `suggested_tools TEXT[]` vs modelo existente** — El plan menciona `suggested_tools TEXT[]` pero `AgentExportItem` en `bundle_schemas.py:107` usa `allowed_tools: List[str]`. Son conceptualmente similares. **Resolución:** usar `suggested_tools TEXT[]` en la DB (como dice el plan) y exponer como `suggested_tools` en la API, diferenciando del campo `allowed_tools` de `agent_catalog`.

3. **D-03: Lectura "pública" requiere auth** — Los criterios dicen "RLS: lectura pública, escritura solo system", pero los endpoints usan `require_org_id`. **Resolución:** crear un endpoint público sin auth para listing básico, y uno admin con auth para system templates. Alternativamente, aplicar RLS que permita SELECT sin org_id para `is_system: true`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tabla `agent_templates` — DDL propuesto

```sql
CREATE TABLE IF NOT EXISTS agent_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE,  -- NULL = system template
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT NOT NULL DEFAULT 'general',
    soul_json       JSONB NOT NULL DEFAULT '{}',
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter        INTEGER DEFAULT 5,
    is_system       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

### Integridad referencial
- `org_id` → `organizations(id)` ON DELETE CASCADE. Templates de sistema (`is_system: true`) tendrán `org_id = NULL` (sin tenant).
- **Nota:** el `agent_catalog` existente tiene `org_id UUID NOT NULL` — los templates son diferentes: son compartibles cross-org cuando `is_system: true`.

### RLS policies (2 capas)

**Política 1 — Lectura pública para system templates:**
```sql
CREATE POLICY "agent_templates_read_public" ON agent_templates
    FOR SELECT USING (is_system = TRUE);
```

**Política 2 — Lectura/escritura por tenant:**
```sql
CREATE POLICY "agent_templates_tenant_isolation" ON agent_templates
    FOR ALL USING (
        auth.role() = 'service_role'
        OR (org_id::text = current_org_id() AND is_system = FALSE)
    );
```

**Política 3 — Solo system_role puede crear system templates:**
```sql
CREATE POLICY "agent_templates_system_write" ON agent_templates
    FOR INSERT WITH CHECK (auth.role() = 'service_role');
```

### Índices necesarios
```sql
CREATE INDEX idx_agent_templates_category ON agent_templates(category) WHERE is_system = TRUE;
CREATE INDEX idx_agent_templates_org ON agent_templates(org_id) WHERE is_system = FALSE;
```

### Seed data — 8 templates predefinidos

| # | Name | Category | Soul (role/goal/backstory) | Suggested Tools |
|---|------|----------|---------------------------|-----------------|
| 1 | Research Agent | Research | role: "Research Agent", goal: "Investiga y sintetiza información de múltiples fuentes", backstory: "Analista experto en búsqueda profunda" | ["fetch_url", "read_file"] |
| 2 | Code Reviewer | Development | role: "Code Reviewer", goal: "Revisa código buscando bugs, seguridad y mejores prácticas", backstory: "Senior engineer con ojo para el detalle" | ["code_reviewer", "linter"] |
| 3 | Data Analyst | Analytics | role: "Data Analyst", goal: "Analiza datasets y genera insights accionables", backstory: "Especialista en estadística y visualización" | ["excel_reader", "data_formatter"] |
| 4 | Customer Support | Support | role: "Customer Support", goal: "Resuelve consultas de clientes con empatía y precisión", backstory: "Agente de soporte con conocimiento del producto" | ["knowledge_base", "ticket_creator"] |
| 5 | Document Writer | Content | role: "Document Writer", goal: "Genera documentos claros y bien estructurados", backstory: "Escritor técnico profesional" | ["read_file", "write_file"] |
| 6 | Translator | General | role: "Translator", goal: "Traduce texto manteniendo tono y contexto", backstory: "Políglota especializado en localización" | [] |
| 7 | Summarizer | General | role: "Summarizer", goal: "Resume documentos largos en forma concisa", backstory: "Especialista en síntesis de información" | ["read_file"] |
| 8 | General Assistant | General | role: "General Assistant", goal: "Asistente versátil para tareas diversas", backstory: "Agente generalista adaptable" | [] |

Todos con `is_system: true`, `org_id: NULL`.

### Impacto en datos existentes
- No hay migración de datos necesaria (tabla nueva).
- La tabla `agent_catalog` (mig 004) ya contiene agentes reales del tenant — los templates son un concepto diferente (blueprints, no instancias).

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a crear

**A. `supabase/migrations/030_agent_templates.sql`**
- Crea tabla `agent_templates` con columnas definidas arriba
- RLS policies (3 políticas)
- Índices optimizados para queries por categoría y tenant
- Comentarios en tabla y columnas siguiendo patrón mig 020

**B. `src/api/routes/templates.py`** — Nuevo archivo

Patrón a seguir: `src/api/routes/flows.py` (mismo estilo, APIRouter con modelos Pydantic inline)

```python
"""src/api/routes/templates.py — Endpoints para librería de templates de agentes."""

from __future__ import annotations
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.middleware import require_org_id
from src.db.session import get_tenant_client

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    soul_json: dict
    suggested_tools: List[str]
    max_iter: int
    is_system: bool


class TemplatesListResponse(BaseModel):
    templates: List[TemplateResponse]


@router.get("/", response_model=TemplatesListResponse)
async def list_templates(
    category: Optional[str] = None,
):
    """Listar templates disponibles. Filtra por categoría si se indica."""
    # Sin require_org_id — lectura pública para system templates
    ...


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
):
    """Obtener un template específico por ID."""
    ...
```

**C. Modificación de `src/api/main.py`** — Agregar import + include_router

```python
# Agregar después de la línea 31 (tools_router)
from .routes.templates import router as templates_router
# Agregar antes de app.include_router(tools_router):
app.include_router(templates_router)
```

### Modelos Pydantic

| Modelo | Archivo | Campos |
|--------|---------|--------|
| `TemplateResponse` | `templates.py` (inline) | `id: UUID`, `name: str`, `description: Optional[str]`, `category: str`, `soul_json: dict`, `suggested_tools: List[str]`, `max_iter: int`, `is_system: bool` |
| `TemplatesListResponse` | `templates.py` (inline) | `templates: List[TemplateResponse]` |

### Decisiones de diseño
- Los modelos Pydantic se definen inline en `templates.py` (no en un archivo separado como `bundle_schemas.py`) porque son simples y solo se usan en este endpoint. Seguir el patrón de `flows.py` donde `FlowInfo` y `FlowsListResponse` están en el mismo archivo.
- `soul_json` se expone como `dict` (no como modelo estricto) para flexibilidad — el frontend parseará `role`, `goal`, `backstory` internamente.
- No se requiere `require_org_id` para lectura — las políticas RLS manejan el acceso basado en `is_system`.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET | `/api/templates` | Lista templates (filtro `?category=`) | Ninguno (RLS permite lectura pública de system templates) |
| GET | `/api/templates/{id}` | Template específico completo | Ninguno (RLS aplica) |

### Contratos

**GET /api/templates**
- Query params: `category` (opcional, string)
- Response 200:
```json
{
  "templates": [
    {
      "id": "uuid-string",
      "name": "Research Agent",
      "description": "...",
      "category": "research",
      "soul_json": {"role": "...", "goal": "...", "backstory": "..."},
      "suggested_tools": ["fetch_url", "read_file"],
      "max_iter": 5,
      "is_system": true
    }
  ]
}
```

**GET /api/templates/{id}**
- Response 200: single `TemplateResponse`
- Response 404: `{"detail": "Template not found"}`

### Error handling
- 404 si el template_id no existe
- 500 en caso de error de DB (con logging)

### Flujo de datos
```
Frontend → GET /api/templates?category=Research
  → FastAPI handler list_templates()
    → get_tenant_client() [solo para system templates, sin filtro org_id]
    → db.table("agent_templates").select("*").eq("is_system", True)
    → [filtrar por category si se indicó]
    → return TemplatesListResponse
```

### Cuellos de botella potenciales
- Ninguno significativo — solo queries de lectura, sin joins complejos.
- El filtro `category` se aplica en memoria (número pequeño de templates) o con un índice si crece.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo
```
[User abre Builder] → [TemplatePicker.tsx (Paso 05)] → GET /api/templates
  → [Response con templates] → [Card grid con nombre, descripción, categoría]
  → [Click "Use Template"] → [AgentForm.tsx se auto-completa con soul_json + tools + max_iter]
```

### Consistencia con el plan
- ✅ La tabla `agent_templates` incluye todos los campos del plan (id, name, description, category, soul_json, suggested_tools, max_iter, is_system)
- ✅ Los endpoints cubren listar y obtener individual
- ✅ El seed incluye 8 templates system
- ⚠️ El plan menciona "filtro ?category=" — se implementa como query param
- ⚠️ El plan dice "Registrar router en `__init__.py`" — se corrige a `main.py`

### Gaps detectados
1. **El plan no especifica el contenido exacto de los 8 templates** — se proponen valores razonables basados en el criterio "Research, Code Reviewer, Data Analyst, Customer Support, Document Writer, Translator, Summarizer, General Assistant"
2. **No se menciona si templates pueden ser creados por usuarios (POST/PUT/DELETE)** — los criterios dicen "escritura solo system", pero no hay endpoints de escritura definidos. Esto es intencional para MVP (solo lectura desde frontend, escritura vía seed/migración).
3. **El frontend no necesita nuevos componentes en este paso** — el TemplatePicker (Paso 05) se crea después.

### DX & Tooling

**Herramienta Propuesta: `seed_templates` helper**
- **Qué automatiza:** Insertar/actualizar los 8 templates de sistema en la base de datos local o remota sin escribir SQL manual
- **Tipo:** Script Python
- **Cómo se usa:** `python scripts/seed_templates.py [--org-id UUID] [--reset]`
- **Impacto para el usuario final:** El desarrollador no necesita insertar manualmente 8 filas en Supabase para probar el builder. El script también sirve para recrear el seed en entornos de prueba.
- **Prioridad:** Tarea 0 — implementar antes que los endpoints para validar la migración

### Diagrama de flujo end-to-end (ASCII)

```
┌─────────────────────────────────────────────────────┐
│  Frontend (Dashboard /builder)                      │
│                                                     │
│  TemplatePicker.tsx ──GET /api/templates?cat=──┐    │
│                                     │           │    │
│                                     ▼           │    │
│                         ┌───────────────────┐   │    │
│                         │  FastAPI           │   │    │
│                         │  templates.py      │   │    │
│                         │                    │   │    │
│                         │  get_tenant_client │   │    │
│                         │       │            │   │    │
│                         │       ▼            │   │    │
│                         │  Supabase SQL:    │   │    │
│                         │  SELECT * FROM    │   │    │
│                         │  agent_templates  │   │    │
│                         │  WHERE is_system  │   │    │
│                         │    = TRUE          │   │    │
│                         └───────────────────┘   │    │
│                                     │            │    │
│                                     ▼            │    │
│  TemplatePicker muestra cards ──────────────────┘    │
│       │                                                │
│       │ "Use Template" click                           │
│       ▼                                                │
│  AgentForm auto-fill ← soul_json + suggested_tools    │
└─────────────────────────────────────────────────────┘
```

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Verificable | Etapa |
|---|----------|-------------|-------|
| CA-01 | Tabla `agent_templates` creada con migración versionada (030) | `\d agent_templates` en psql ✅ | DATA |
| CA-02 | `GET /api/templates` devuelve array de templates (mínimo 8) con `is_system: true` | curl → status 200, `len(body.templates) >= 8` ✅ | BACKEND |
| CA-03 | `GET /api/templates/{id}` devuelve template completo con `soul_json` | curl con ID válido → status 200, tiene `soul_json` ✅ | BACKEND |
| CA-04 | Filtro `?category=` funciona — `/api/templates?category=Research` retorna solo templates de Research | curl → solo resultados con esa categoría ✅ | BACKEND |
| CA-05 | RLS: lectura sin auth permite ver templates `is_system: true` | curl sin X-Org-ID → status 200 ✅ | DATA |
| CA-06 | RLS: escritura solo service_role | INSERT sin service role → 403 ✅ | DATA |
| CA-07 | Seed contiene exactamente 8 templates con nombres correctos | Contar filas en DB → 8 ✅ | DATA |
| CA-08 | Campo `suggested_tools` es array de strings | `type(body.templates[0].suggested_tools) == "array"` ✅ | BACKEND |
| CA-09 | `soul_json` contiene `goal` y `backstory` en cada template | Validar estructura en response ✅ | BACKEND |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| R-01 | Media | Conflicto entre "lectura pública" y `require_org_id` en endpoints. Si se aplica `require_org_id`, los usuarios no autenticados no pueden ver templates. | No aplicar `require_org_id` en los GET de templates. Dejar que RLS filtre por `is_system = TRUE`. Para templates de tenant, requerir auth. |
| R-02 | Baja | Los 8 templates son estáticos y pueden quedar desactualizados respecto a los capabilities reales de tools. | Documentar que el seed es un snapshot. Agregar un TODO para endpoint POST /templates (post-MVP) que permita actualización. |
| R-03 | Media | `org_id: NULL` en templates system puede causar problemas con RLS si la política no se escribe correctamente. | Testear explícitamente que `org_id IS NULL` + `is_system = TRUE` es legible sin header org. Escribir test unitario. |
| R-04 | Baja | Nombre de migración 030 podría colisionar si otro branch ya creó una migración 030. | Verificar que no existe 030 en el repo antes de merge. Usar siguiente número disponible. |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica — OBLIGATORIAS:**
> 1. Una tarea = un artefacto
> 2. Interfaz completa en cada tarea
> 3. Patrón de referencia explícito
> 4. Verificación inline
> 5. Test de atomicidad: si el implementador puede completar sin decidir diseño → OK

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|--------------|--------------|
| 0 | **DX: Script `seed_templates.py`** | `scripts/seed_templates.py` | `def seed(org_id: str = SYSTEM_ORG_ID, reset: bool = False) -> int` retorna count | `scripts/seed_system_bundles.py:14` | DX | Baja | 0.5h | Ninguna | `python scripts/seed_templates.py --help` ejecuta sin errores |
| 1 | Crear migración `agent_templates` | `supabase/migrations/030_agent_templates.sql` | DDL completo: tabla + RLS (3 policies) + índices + comentarios | `025_agent_catalog_rls_update.sql` (RLS modern) + `004_agent_catalog.sql` (estructura) | DATA | Media | 0.5h | Tarea 0 | `\d agent_templates` en psql + SELECT count(*) = 8 tras seed |
| 2 | Crear módulo `templates.py` con GET / y /{id} | `src/api/routes/templates.py` | `list_templates(category?) -> TemplatesListResponse`, `get_template(template_id) -> TemplateResponse` | `src/api/routes/flows.py:76-110` (list endpoint) | CODE | Media | 1h | Ninguna | `import src.api.routes.templates` sin error |
| 3 | Registrar router en `main.py` | `src/api/main.py` | Agregar `from .routes.templates import router as templates_router` + `app.include_router(templates_router)` | `src/api/main.py:111` (tools_router) | BACKEND | Baja | 0.25h | Tarea 2 | `curl localhost:8000/api/templates` → 200 (tras `uv run src.api.main:app`) |
| 4 | Validación end-to-end de flujo DB → API | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-3 | `curl /api/templates` retorna 8 templates con `soul_json` completo |

**Tiempo total estimado:** 2.25 horas

### Notas de implementación

- **Tarea 0 (DX):** Ejecutar PRIMERO. Permite verificar que la migración + seed funcionan antes de escribir el endpoint.
- **Tarea 1:** La migración debe crear también un trigger `handle_updated_at` si se desea (consultar si hay trigger global o es por tabla — ver mig 020 para referencia).
- **Tarea 2:** No usar `require_org_id` en los GET. El control de acceso lo maneja RLS. Para templates de tenant (futuro), se añadirá auth cuando se implemente la creación.
- **Tarea 3:** Registrar ANTES de `tools_router` en `main.py` para mantener orden alfabético.

---

## 🔮 Roadmap (NO implementar ahora)

- **Post-MVP:** Endpoints POST/PUT/DELETE para gestión de templates por admin
- **Post-MVP:** Endpoint `GET /api/templates/export` para exportar templates como bundle
- **Post-MVP:** Versión del TemplatePicker con edición inline (drag & drop reorder de campos soul_json)
- **Mejora futura:** Cache en memoria de templates system con invalidación por evento de DB
- **Decisión pendiente:** ¿Los templates de tenant (no-system) necesitan `org_id` obligatorio o se asocian automáticamente? → Definir en Paso 08

---

## 🚫 Reglas de Oro verificadas

- ✅ Análisis accionable: cada tarea tiene artefacto, interfaz y verificación concreta
- ✅ TODO verificado contra código real (no suposiciones)
- ✅ Discrepancias documentadas con resolución (D-01, D-02, D-03)
- ✅ Coherente con `phase-state.md` — no contradice decisiones previas
- ✅ 4 etapas cubiertas: data, code, backend, fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta (`seed_templates.py`)
- ✅ Tareas atómicas: 1 tarea = 1 artefacto
- ✅ Interfaz exacta por tarea: firmas completas
- ✅ Patrón de referencia explícito: archivo + línea concretos
- ✅ Verificación inline por tarea