# 🧠 Análisis Técnico — Paso 03: Endpoints CRUD para templates de agentes

**Agente:** dsp  
**Fecha:** 2026-05-13  
**Fase:** `guiAgentGenerator`  
**Archivo de referencia:** `DEVS/plan.md` — Paso 03  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | grep en `supabase/migrations/` | ❌ | No existe. Crear migración `030_agent_templates.sql` |
| 2 | Archivo `src/api/routes/templates.py` | ls `src/api/routes/` | ❌ | No existe. 17 archivos en routes/, ninguno `templates.py` |
| 3 | Router `templates` en `main.py` | grep en `src/api/main.py` | ❌ | Sin import ni `include_router`. 14 routers registrados, ninguno templates |
| 4 | Seed data con 8 templates | grep seed/script en `scripts/` | ❌ | `seed_system_bundles.py` (bundles) y `seed_bundle.py`. Ninguno para templates |
| 5 | `current_org_id()` function | `supabase/migrations/001_set_config_rpc.sql:37-45` | ✅ | Función PL/pgSQL estable. Usada en 24+ políticas RLS |
| 6 | RLS pattern moderno | `supabase/migrations/025_agent_catalog_rls_update.sql:11-14` | ✅ | `auth.role() = 'service_role' OR org_id::text = current_org_id()` |
| 7 | `get_service_client()` disponible | `src/db/session.py:55-73` | ✅ | Singleton lazy. Usado por 15+ módulos para queries bypass RLS |
| 8 | `get_tenant_client()` disponible | `src/db/session.py:214-231` | ✅ | Context manager. Usado en `agents.py`, `integrations.py` |
| 9 | Patrón router registration | `src/api/main.py:20-34` imports + `:98-113` `include_router` | ✅ | Import al inicio + `include_router` al final. NO en `__init__.py` |
| 10 | Patrón endpoint list con Pydantic | `src/api/routes/integrations.py:18-23` | ✅ | `get_service_client()` → `.table().select().eq().execute()` |
| 11 | Patrón endpoint detail by ID | `src/api/routes/agents.py:54-51` (get_agent_detail) | ✅ | `.eq("id", id).eq("org_id", org_id).maybe_single()` |
| 12 | Tabla global sin RLS (referencia) | `supabase/migrations/024_service_catalog.sql:8-22` | ✅ | `service_catalog` — global, sin `org_id`, sin RLS |
| 13 | Migración más reciente | `supabase/migrations/029_python_flows.sql` | ✅ | Próximo número: `030` |
| 14 | Convención nombres DB | `proyecto-config.json:65` | ✅ | `snake_case` — consistente con `agent_templates` |
| 15 | Convención imports backend | `proyecto-config.json:66` | ✅ | Absolutos: `from src.x.y import Z` |
| 16 | Dependencia `supabase>=2.10.0` | `proyecto-config.json:87` | ✅ | Cliente Supabase disponible para queries directas |
| 17 | Tabla `agent_catalog` (referencia schema) | `supabase/migrations/004_agent_catalog.sql:6-17` | ✅ | `id UUID, org_id UUID, role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INT` |
| 18 | Tabla `workflow_templates` (referencia template) | `supabase/migrations/006_workflow_templates.sql:6-44` | ✅ | `name, description, definition JSONB, version INT, is_validated BOOLEAN` |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| **D1** | Plan: "Registrar router en `src/api/__init__.py`". Real: routers se registran en `src/api/main.py` (corrección D4 de fase, documentada en `phase-state.md:73`) | Registrar en `main.py`: import + `include_router`. `__init__.py` solo tiene docstring. |
| **D2** | Plan: tabla `agent_templates` sin columna `org_id`. Todas las demás tablas del proyecto tienen `org_id` con RLS tenant isolation. | Intencional: templates son catálogo global compartido (como `service_catalog`). Sin `org_id` = sin tenant isolation. Documentar como decisión de arquitectura. |
| **D3** | Plan: "RLS aplicado: lectura pública, escritura solo system". Pero API solo define GET (read-only). Sin endpoints POST/PUT/DELETE. | `is_system` es metadata, no enforcement API. Escritura vía seed script directo. RLS protege contra modificaciones accidentales desde cliente anónimo. |
| **D4** | Plan: seed con 8 templates pero sin definir ubicación del script ni mecanismo de ejecución. Comando `seed` en `proyecto-config.json` apunta a `seed_system_bundles.py`. | Crear `scripts/seed_agent_templates.py` + agregar comando `seed-templates` en `proyecto-config.json`. Referencia: `seed_system_bundles.py` usa `ImportService`. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema — Tabla `agent_templates`

**Migración:** `supabase/migrations/030_agent_templates.sql`

```sql
CREATE TABLE IF NOT EXISTS agent_templates (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           TEXT NOT NULL,
    description    TEXT,
    category       TEXT NOT NULL,            -- Research, Development, Support, General
    soul_json      JSONB NOT NULL DEFAULT '{}',
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter       INTEGER DEFAULT 5,
    is_system      BOOLEAN DEFAULT FALSE,    -- TRUE = seed templates, FALSE = user-created (futuro)
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);
```

### Columnas — Detalle y justificación

| Columna | Tipo | Justificación |
|---|---|---|
| `id` | UUID PK | Consistente con todas las tablas del proyecto |
| `name` | TEXT NOT NULL | Nombre visible en TemplatePicker (Paso 05) |
| `description` | TEXT | Descripción para cards del TemplatePicker |
| `category` | TEXT NOT NULL | Filtro `?category=` en endpoint. Valores: Research, Development, Support, General |
| `soul_json` | JSONB NOT NULL | Espejo de `agent_catalog.soul_json`. Contiene `{role, goal, backstory}` |
| `suggested_tools` | TEXT[] | Tools sugeridas. El formulario las pre-selecciona pero el usuario puede cambiar |
| `max_iter` | INTEGER DEFAULT 5 | Default coincide con `agent_catalog.max_iter`. Consistencia inter-tabla |
| `is_system` | BOOLEAN DEFAULT FALSE | Distingue templates del sistema de los creados por usuario (MVP: todos system) |
| `created_at` | TIMESTAMPTZ | Auditoría |
| `updated_at` | TIMESTAMPTZ | Auditoría |

### Decisiones de schema:

1. **Sin `org_id`**: Templates son catálogo global. `service_catalog` (mig024) sigue mismo patrón. Si en futuro se requieren templates por org → migración separada que añada `org_id` + migre datos.
2. **Sin `UNIQUE` constraint en `name`**: Templates pueden repetir nombre (ej: dos "Research Agent" con diferente `soul_json`). Si se quiere unicidad → `UNIQUE(name, category)`.
3. **`soul_json` espejo de `agent_catalog`**: Misma estructura: `{role, goal, backstory}`. Esto permite que TemplatePicker (Paso 05) mapee directo a AgentForm (Paso 04) sin transformación.
4. **`suggested_tools` como `TEXT[]`**: Consistente con `agent_catalog.allowed_tools`. PostgreSQL array nativo.

### Integridad Referencial

- Sin foreign keys (tabla aislada, catálogo de referencia).
- Sin dependencia de `organizations` ni `agent_catalog`.

### RLS Policies

Tabla global → RLS mínima: lectura abierta, escritura restringida.

```sql
ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY;

-- Lectura pública (cualquier rol autenticado o anónimo)
CREATE POLICY "agent_templates_read" ON agent_templates
    FOR SELECT USING (true);

-- Escritura solo service_role
CREATE POLICY "agent_templates_insert" ON agent_templates
    FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "agent_templates_update" ON agent_templates
    FOR UPDATE USING (auth.role() = 'service_role');

CREATE POLICY "agent_templates_delete" ON agent_templates
    FOR DELETE USING (auth.role() = 'service_role');
```

> **NOTA:** `FOR SELECT USING (true)` permite lectura sin autenticación. Si se requiere auth → cambiar a `USING (auth.role() = 'authenticated')`.

### Índices

```sql
CREATE INDEX idx_agent_templates_category ON agent_templates(category);
CREATE INDEX idx_agent_templates_system ON agent_templates(is_system) WHERE is_system = TRUE;
```

- `category`: optimiza filtro `?category=`.
- `is_system` parcial: optimiza queries que solo buscan system templates (caso común).

### Seed Data — 8 templates

| # | name | category | soul_json (role/goal/backstory) | suggested_tools | max_iter | is_system |
|---|---|---|---|---|---|---|
| 1 | Research Agent | Research | `{role: "Research Agent", goal: "Find and analyze information...", backstory: "Expert researcher..."}` | `{fetch_url, search}` | 5 | TRUE |
| 2 | Code Reviewer | Development | `{role: "Code Reviewer", goal: "Review code for bugs...", backstory: "Senior developer..."}` | `{read_file, grep}` | 3 | TRUE |
| 3 | Data Analyst | Research | `{role: "Data Analyst", goal: "Analyze data and generate insights...", backstory: "Data scientist..."}` | `{sql_query, chart}` | 5 | TRUE |
| 4 | Customer Support | Support | `{role: "Customer Support", goal: "Help users resolve issues...", backstory: "Support specialist..."}` | `{search_kb, create_ticket}` | 3 | TRUE |
| 5 | Document Writer | General | `{role: "Document Writer", goal: "Write clear documentation...", backstory: "Technical writer..."}` | `{read_file, write_file}` | 3 | TRUE |
| 6 | Translator | General | `{role: "Translator", goal: "Translate text accurately...", backstory: "Multilingual translator..."}` | `{}` | 3 | TRUE |
| 7 | Summarizer | General | `{role: "Summarizer", goal: "Summarize long texts concisely...", backstory: "Expert at distilling information..."}` | `{}` | 2 | TRUE |
| 8 | General Assistant | General | `{role: "General Assistant", goal: "Assist with various tasks...", backstory: "Versatile AI assistant..."}` | `{}` | 3 | TRUE |

> **⚠️ NO VERIFICABLE:** Los `suggested_tools` referencian nombres del `ToolRegistry` (`fetch_url`, `search`, `read_file`, etc.). El seed debe usar nombres de tools que EXISTAN en el registry al momento de ejecución. Si una tool no existe → el template igual se crea (el array es sugerencia, no FK).

### Impacto en datos existentes

- **Ninguno**: tabla nueva, sin migración de datos.
- Seed inserta 8 filas. Idempotente con `ON CONFLICT DO NOTHING` o `INSERT ... WHERE NOT EXISTS`.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a crear/modificar

| Archivo | Acción | Tipo |
|---|---|---|
| `supabase/migrations/030_agent_templates.sql` | CREAR | Migración |
| `src/api/routes/templates.py` | CREAR | Endpoints |
| `src/api/main.py` | MODIFICAR | Registrar router |
| `scripts/seed_agent_templates.py` | CREAR | Seed script |

### `src/api/routes/templates.py` — Firmas y modelos

**Modelos Pydantic:**

```python
# TemplateListResponse — respuesta de GET /api/templates
class TemplateInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    suggested_tools: List[str] = []
    max_iter: int = 5
    is_system: bool = False
    created_at: Optional[str] = None

class TemplateListResponse(BaseModel):
    templates: List[TemplateInfo]
    count: int

# TemplateDetailResponse — respuesta de GET /api/templates/{id}
class TemplateDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    soul_json: Dict[str, Any]    # objeto completo con role/goal/backstory
    suggested_tools: List[str] = []
    max_iter: int = 5
    is_system: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

**Endpoints:**

```python
@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None),
) -> TemplateListResponse:
    """Listar templates. Filtro opcional ?category=""."

@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str) -> TemplateDetailResponse:
    """Obtener template específico con soul_json completo."""
```

**Patrón de referencia:** `src/api/routes/integrations.py:18-23` (listado simple con `get_service_client()`).

**Imports necesarios:**

```python
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from src.db.session import get_service_client
```

### Patrón de código

Sigue patrón de `integrations.py` — el más simple del proyecto:
1. `get_service_client()` para bypass RLS (tabla global sin tenant)
2. `.table("agent_templates").select("*")` para listado
3. `.eq("category", category)` para filtro
4. `.eq("id", template_id).maybe_single()` para detalle
5. Sin `Depends(require_org_id)` — endpoint público (lectura)

### 💀 CRÍTICO — verificación de patrón:

- ✅ `integrations.py` usa `get_service_client()` sin tenant → mismo patrón para templates
- ✅ `integrations.py` NO usa `require_org_id` en `/available` → templates tampoco necesita
- ✅ `flows.py` usa `response_model` en decorator → consistente
- ✅ `tools.py` incluye `count` en respuesta → templates debe incluir `count`

### Modularidad

- **Alta cohesión**: archivo `templates.py` solo maneja templates. Sin dependencias circulares.
- **Bajo acoplamiento**: solo depende de `get_service_client` (db/session) y FastAPI. Sin dependencia de services.
- **Reutilización**: modelos Pydantic pueden ser importados por seed script para type safety.

### Calidad de código

- Complejidad ciclomática: 1-2 por endpoint (solo if/else de validación).
- Sin duplicación: endpoints usan patrón común (db → filter → return).
- 2 endpoints = 2 funciones. Simple.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints

| Método | Ruta | Handler | Response Model | Status |
|---|---|---|---|---|
| GET | `/api/templates` | `list_templates(category?)` | `TemplateListResponse` | 200 |
| GET | `/api/templates/{template_id}` | `get_template(template_id)` | `TemplateDetailResponse` | 200 / 404 |

### Detalle de endpoints

#### `GET /api/templates`

- **Query params:** `?category=Research|Development|Support|General`
- **Sin autenticación requerida** (lectura pública)
- **Happy path response:**
```json
{
  "templates": [
    {
      "id": "uuid",
      "name": "Research Agent",
      "description": "Find and analyze information from multiple sources",
      "category": "Research",
      "suggested_tools": ["fetch_url", "search"],
      "max_iter": 5,
      "is_system": true,
      "created_at": "2026-05-13T00:00:00Z"
    }
  ],
  "count": 1
}
```
- **Sin templates:** `{"templates": [], "count": 0}` (200, no 404)
- **Error:** solo 500 si DB inaccesible

#### `GET /api/templates/{template_id}`

- **Path param:** `template_id: str` (UUID)
- **Happy path response:**
```json
{
  "id": "uuid",
  "name": "Research Agent",
  "description": "...",
  "category": "Research",
  "soul_json": {
    "role": "Research Agent",
    "goal": "Find and analyze information from multiple sources",
    "backstory": "You are an expert researcher with years of experience..."
  },
  "suggested_tools": ["fetch_url", "search"],
  "max_iter": 5,
  "is_system": true,
  "created_at": "...",
  "updated_at": "..."
}
```
- **404:** `{"detail": "Template not found"}` si `template_id` no existe
- **Error:** 500 si DB inaccesible

### Middleware

- **Sin middleware de auth**: endpoint público de lectura.
- **Sin `require_org_id`**: templates son globales, no requieren tenant context.
- **Futuro**: si se añade POST/PUT/DELETE → requerir `verify_supabase_jwt` + verificar `is_service_role`.

### Flujo de datos

```
Supabase DB (agent_templates)
        │
        ▼
get_service_client() — bypass RLS
        │
        ▼
.table("agent_templates").select("*").eq("category", "Research").execute()
        │
        ▼
TemplateInfo (Pydantic) → JSON → Frontend (TemplatePicker — Paso 05)
```

### Contratos

- `GET /api/templates` → siempre 200 (array vacío si no hay templates)
- `GET /api/templates/{id}` → 200 con `soul_json` completo o 404
- `soul_json` siempre es objeto (nunca null/string) — garantizado por `DEFAULT '{}'` en DB
- `suggested_tools` siempre es array (nunca null) — garantizado por `DEFAULT '{}'` en DB

### Error handling

| Escenario | Status | Body |
|---|---|---|
| Template no encontrado | 404 | `{"detail": "Template not found"}` |
| ID malformado (no UUID) | 404 | `{"detail": "Template not found"}` (no revela formato) |
| DB inaccesible | 500 | `{"detail": "Internal server error"}` |
| Filtro inválido (categoría inexistente) | 200 | `{"templates": [], "count": 0}` (no error, solo sin resultados) |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

```
┌──────────────────────────────────────────────────────────────────┐
│ SEED (scripts/seed_agent_templates.py)                           │
│   │  Inserta 8 templates con is_system=true                      │
│   ▼  Usa get_service_client() directo a Supabase                │
│ agent_templates (Supabase)                                       │
│   │                                                              │
│   ▼  GET /api/templates?category=Research                        │
│ FastAPI (templates.py)                                           │
│   │  get_service_client() → .table().select()                    │
│   ▼  Response: TemplateListResponse (sin soul_json, ligero)      │
│ TemplatePicker (Paso 05) — grid de cards                         │
│   │  Click "Use Template"                                        │
│   ▼  GET /api/templates/{id}                                     │
│ TemplateDetailResponse (con soul_json completo)                  │
│   │  Mapeo directo a campos del formulario                      │
│   ▼                                                              │
│ AgentForm (Paso 04) — campos auto-rellenados                     │
│   │  User edita si quiere                                        │
│   ▼  Click "Save Agent"                                          │
│ agent_catalog (Supabase) — agente guardado                       │
└──────────────────────────────────────────────────────────────────┘
```

### Coherencia con MVP

- ✅ Paso 03 expone datos que Paso 05 consume directamente
- ✅ `TemplateInfo` (ligero, sin soul_json) para lista → eficiente en red
- ✅ `TemplateDetailResponse` (con soul_json) para detalle → solo cuando se necesita
- ✅ `soul_json` espejo de `agent_catalog.soul_json` → mapeo 1:1 sin transformación
- ✅ `suggested_tools` como `TEXT[]` → compatible con multi-select de AgentForm (Paso 04)
- ✅ Sin `org_id` = templates visibles para todos los usuarios sin configuración

### Gaps y fricciones

| Gap | Impacto | Mitigación |
|---|---|---|
| Sin endpoint POST para crear templates custom | Usuario no puede guardar sus propios templates | Post-MVP. Añadir `POST /api/templates` + `org_id` |
| Sin paginación en `GET /api/templates` | Con 8 templates no es problema. Con 100+ → lento | Post-MVP. Añadir `?offset=&limit=` |
| Sin cache en endpoint | Cada request pega a DB | MVP aceptable (8 filas). Post-MVP: `functools.lru_cache` con TTL |
| Sin validación de `soul_json` estructura | Template con `soul_json` malformado → AgentForm roto | Seed valida estructura. Futuro: Pydantic validator en modelo |
| Templates sin `org_id` no pueden ser private | Todos los templates son visibles para todos | Intencional para MVP (librería compartida) |

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap templates seed`

- **Qué automatiza:** Inserción de los 8 templates predefinidos en Supabase. Evita que el desarrollador tenga que ejecutar SQL manualmente en Supabase Studio o escribir inserts a mano.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:**
  ```bash
  uv run python -m src.cli.main templates seed
  ```
  O como sub-comando registrado:
  ```bash
  fap templates seed
  ```
- **Impacto para el usuario final:** El desarrollador pasa de escribir 8 INSERTs SQL manuales + verificar estructura JSONB a un solo comando. Tiempo: de ~15 min manual a <1s automatizado.
- **Prioridad:** Tarea 0 — implementar antes que los endpoints y la migración, para poder verificar que el seed funciona con la tabla creada.
- **Implementación:** Script `scripts/seed_agent_templates.py` con función `seed_templates()` + registro como comando Typer en `src/cli/main.py`.

**Flujo de uso:**
```
$ fap templates seed
🌱 Seeding agent templates...
✅ Template 1/8: Research Agent
✅ Template 2/8: Code Reviewer
...
✅ Template 8/8: General Assistant
📊 Total: 8 templates seeded (0 skipped, 0 failed)
```

#### Herramienta Propuesta: `fap templates list` (bonus DX)

- **Qué automatiza:** Listar templates desde terminal sin curl/Postman. Consume `GET /api/templates` internamente.
- **Tipo:** CLI command
- **Cómo se usa:**
  ```bash
  fap templates list --category Research --json
  ```
- **Prioridad:** Post-MVP (si el equipo lo valora). No bloquea el paso.

### Alineación con arquitectura existente

- ✅ Mismo patrón de seed que `seed_system_bundles.py`
- ✅ Mismo patrón de CLI que `fap tools list` y `fap bundle export`
- ✅ Mismo patrón de endpoints que `integrations.py` y `tools.py`
- ✅ Misma convención de nombres: `snake_case` para tabla, columnas, archivo

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA]   Migración `030_agent_templates.sql` existe y ejecuta sin errores
✅ [DATA]   Tabla `agent_templates` tiene columnas: id UUID PK, name TEXT NOT NULL, description TEXT, category TEXT NOT NULL, soul_json JSONB NOT NULL, suggested_tools TEXT[], max_iter INT, is_system BOOLEAN
✅ [DATA]   RLS policies: SELECT público, INSERT/UPDATE/DELETE solo service_role
✅ [DATA]   Índices: idx_agent_templates_category, idx_agent_templates_system (parcial)
✅ [DATA]   Seed script inserta 8 templates con is_system=true SIN errores
✅ [DATA]   Seed es idempotente (ejecutar 2 veces no duplica templates)
✅ [CODE]   `src/api/routes/templates.py` existe con router APIRouter(prefix="/api/templates")
✅ [CODE]   Model Pydantic `TemplateInfo` con campos: id, name, description, category, suggested_tools, max_iter, is_system
✅ [CODE]   Model Pydantic `TemplateDetailResponse` incluye soul_json y updated_at
✅ [CODE]   `GET /api/templates` handler con filtro `?category=` funcional
✅ [CODE]   `GET /api/templates/{template_id}` handler con 404 para IDs inexistentes
✅ [CODE]   Respuesta incluye campo `count` (consistente con tools.py y flows.py)
✅ [BACKEND] Router registrado en `src/api/main.py` (import + include_router)
✅ [BACKEND] `GET /api/templates` responde 200 con array (vacío si no hay templates)
✅ [BACKEND] `GET /api/templates/{id}` responde 200 con soul_json completo o 404
✅ [BACKEND] Filtro `?category=Research` filtra correctamente
✅ [BACKEND] Timeout < 300ms para listado (8 filas, sin join)
✅ [FULLSTACK] TemplatePicker (Paso 05) puede cargar templates desde API real
✅ [FULLSTACK] soul_json del template mapea 1:1 a campos de AgentForm (Paso 04)
✅ [DX] Comando `fap templates seed` ejecuta sin errores y verifica 8 templates insertados
✅ [DX] `uv run pytest tests/unit/ -k test_templates` pasa (si se implementan tests)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Templates sin `org_id` rompen patrón RLS | Media | Todas las tablas del proyecto usan tenant isolation. Templates globales es excepción. | Documentado en D2. Si futuros pasos requieren templates por org → migración 031 que añada `org_id`. |
| Seed tools inexistentes en ToolRegistry | Baja | `suggested_tools` referencia nombres de tools que pueden no estar registradas aún. | `suggested_tools` es array sugerencia, no FK. Sin validación en DB. TemplatePicker muestra tools aunque no existan → el multi-select las filtrará naturalmente. |
| `soul_json` con estructura inconsistente | Media | Si seed genera `soul_json` sin `role`/`goal`/`backstory` → AgentForm (Paso 04) falla al mapear. | Seed script valida estructura antes de insertar. Test unitario verifica que cada template tiene las 3 keys. |
| Colisión de nombres de template | Baja | Sin UNIQUE constraint en `name`, seed ejecutado 2+ veces duplica templates con mismos nombres. | Seed idempotente: `INSERT ... ON CONFLICT (name) DO NOTHING` o check previo. |
| Endpoint sin auth expone datos | Baja | Templates son datos públicos de referencia. No hay datos sensibles. | Si en futuro se añaden templates privados → añadir `require_org_id` + filtrar por org. |
| Migración `030` conflictúa con migraciones futuras no planificadas | Baja | Si otro equipo crea migración 030 antes que este paso → conflicto de numeración. | Verificar `supabase/migrations/` justo antes de crear el archivo. |
| CLI tool `fap templates seed` requiere Supabase corriendo | Alta | Seed necesita conexión a Supabase. Si el developer no tiene Supabase local → falla. | Documentar en README. Alternativa: seed via SQL Editor en Supabase Studio como fallback. Comando `migrate` en `proyecto-config.json` es "manual". |

---

## 7️⃣ Plan de Implementación

> [!CRITICAL]
> **Reglas de segmentación atómica aplicadas.** Una tarea = un artefacto. Interfaz completa. Patrón explícito. Verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| **0** | **DX: `fap templates seed`** | `scripts/seed_agent_templates.py` | `def seed_templates() -> int` — retorna count de templates insertados | `scripts/seed_system_bundles.py` — mismo patrón: sys.path + get_service_client + insert | DX | Media | 1.5h | Ninguna | → verificar: `uv run python scripts/seed_agent_templates.py` inserta 8 templates. Ejecutar 2 veces → solo 8 (idempotente) |
| **1** | Crear migración tabla `agent_templates` | `supabase/migrations/030_agent_templates.sql` | `CREATE TABLE agent_templates (id UUID PK, name TEXT NOT NULL, description TEXT, category TEXT NOT NULL, soul_json JSONB NOT NULL DEFAULT '{}', suggested_tools TEXT[] DEFAULT '{}', max_iter INT DEFAULT 5, is_system BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now())` | `supabase/migrations/004_agent_catalog.sql:6-17` — estructura tabla + `supabase/migrations/024_service_catalog.sql:8-22` — tabla global sin org_id | DATA | Baja | 0.5h | Tarea 0 | → verificar: ejecutar SQL en Supabase Studio → `SELECT * FROM agent_templates` devuelve 0 filas sin error |
| **2** | Añadir RLS + índices en migración | `supabase/migrations/030_agent_templates.sql` (mismo archivo) | `ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY; CREATE POLICY ... FOR SELECT USING (true); CREATE POLICY ... FOR INSERT WITH CHECK (auth.role() = 'service_role'); CREATE INDEX idx_agent_templates_category ON agent_templates(category);` | `supabase/migrations/024_service_catalog.sql:46-50` — RLS con service_role bypass | DATA | Baja | 0.3h | Tarea 1 | → verificar: `SELECT * FROM agent_templates` funciona desde cliente anónimo. `INSERT` desde anónimo → error |
| **3** | Crear módulo `templates.py` con modelos y endpoints | `src/api/routes/templates.py` | **Modelos:** `class TemplateInfo(BaseModel): id: str, name: str, description: Optional[str], category: str, suggested_tools: List[str], max_iter: int, is_system: bool, created_at: Optional[str]` \| `class TemplateListResponse(BaseModel): templates: List[TemplateInfo], count: int` \| `class TemplateDetailResponse(BaseModel): id: str, name: str, description: Optional[str], category: str, soul_json: Dict[str, Any], suggested_tools: List[str], max_iter: int, is_system: bool, created_at: Optional[str], updated_at: Optional[str]` \| **Endpoints:** `@router.get("", response_model=TemplateListResponse) async def list_templates(category: Optional[str] = Query(None))` → `db.table("agent_templates").select("*").eq("category", category).execute()` \| `@router.get("/{template_id}", response_model=TemplateDetailResponse) async def get_template(template_id: str)` → `.eq("id", template_id).maybe_single().execute()` → 404 si None | `src/api/routes/integrations.py:18-23` — listado simple con `get_service_client()` + `src/api/routes/tools.py:46-63` — Pydantic models + `count` en respuesta | CODE | Media | 1h | Tarea 2 | → verificar: `uv run python -c "from src.api.routes.templates import router; print(router.prefix)"` → `/api/templates` sin error |
| **4** | Registrar router en `main.py` | `src/api/main.py` | `from .routes.templates import router as templates_router` (línea 33) + `app.include_router(templates_router)` (línea 112, después de tools_router) | `src/api/main.py:20-34` imports + `:98-113` include_router. Mismo patrón que todos los routers existentes | CODE | Baja | 0.2h | Tarea 3 | → verificar: `uv run python -c "from src.api.main import app; print([r.prefix for r in app.routes if hasattr(r, 'prefix')])"` incluye `/api/templates` |
| **5** | Test unitario de endpoints | `tests/unit/test_templates.py` | `def test_list_templates_empty(): ...` → 200 con `{"templates": [], "count": 0}` \| `def test_list_templates_with_filter(): ...` → filtra por category \| `def test_get_template_found(): ...` → 200 con soul_json \| `def test_get_template_not_found(): ...` → 404 \| `def test_seed_templates_idempotent(): ...` → ejecutar seed 2 veces = 8 templates | `tests/unit/test_bundle_export.py` — patrón de tests unitarios con FastAPI TestClient o mock | CODE | Media | 1h | Tarea 4 | → verificar: `uv run pytest tests/unit/test_templates.py -v` pasa todos los tests |
| **6** | Validar flujo end-to-end | — | Seed 8 templates → `GET /api/templates` → verificar 8 templates → `GET /api/templates/{id}` → verificar `soul_json` con las 3 keys → filtro `?category=Research` → solo Research Agents | — | FULLSTACK | Baja | 0.5h | Tareas 0-5 | → verificar: todos los criterios §5 [DATA], [CODE], [BACKEND] pasan |

**Tiempo total estimado:** 5 horas

---

## 🔮 Roadmap (NO implementar ahora)

| Mejora | Descripción | Prioridad |
|---|---|---|
| `POST /api/templates` | Permitir a usuarios crear templates custom. Requiere añadir `org_id` y `created_by` a la tabla. | Paso 05 (si se requiere) |
| Paginación `?offset=&limit=` | Preparar para >100 templates | Post-MVP |
| Cache `lru_cache` + TTL | Reducir latencia en listado frecuente | Post-MVP |
| `fap templates list` CLI | Listar templates desde terminal | Post-MVP |
| Validación Pydantic de `soul_json` | Validator que chequea `role`, `goal`, `backstory` en `soul_json` al insertar/actualizar | Paso 04 (cuando AgentForm consuma templates) |
| Templates con `org_id` + visibilidad | Templates privados por organización. Compartir templates entre orgs. | Fase 2 |

---

## 🚫 Verificación de Reglas de Oro

- ✅ Análisis accionable y específico — cada tarea tiene firma exacta
- ✅ TODO verificado contra código — 18 elementos en §0
- ✅ Discrepancias documentadas — 4 discrepancias (D1-D4) con resolución
- ✅ Código gana sobre plan — D1, D3 corrigen el plan
- ✅ Coherente con phase-state.md — D4 (router en main.py) ya documentada
- ✅ TODO el paso — sub-pasos incluidos (migración + endpoints + seed)
- ✅ Etapas secuenciales — data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX — `fap templates seed` + bonus `fap templates list`
- ✅ Tareas atómicas — 6 tareas, cada una = un artefacto
- ✅ Interfaz exacta por tarea — cada tarea incluye firma completa
- ✅ Patrón de referencia explícito — archivo concreto + línea
- ✅ Verificación inline — comando concreto por tarea
- ✅ Suposiciones marcadas ⚠️ — 2 elementos NO VERIFICABLES (§0: #17 seed tools + D4 tools existence)

---

## 📊 Métrica de Calidad

| Métrica | Mínimo | Actual | Cumple |
|---|---|---|---|
| `proyecto-config.json` leído | 100% | ✅ | ✅ |
| Elementos verificados (§0) | ≥ 8 (1-2 archivos) | 18 | ✅ |
| Discrepancias detectadas | ≥ 1 | 4 (D1-D4) | ✅ |
| Secciones completadas | 8 (0-7) | 8 | ✅ |
| Etapas cubiertas | 4 | 4 | ✅ |
| Criterios de aceptación | ≥ 1 por sub-paso | 22 | ✅ |
| Riesgos identificados | ≥ 3 | 7 | ✅ |
| Tareas atómicas | 100% | 6/6 | ✅ |
| Interfaz exacta por tarea | 100% | 6/6 | ✅ |
| Patrón de referencia explícito | 100% | 6/6 | ✅ |
| Verificación inline | 100% | 6/6 | ✅ |
| Suposiciones no verificadas | ≤ 2 | 2 (⚠️) | ✅ |
| Propuesta DX | ≥ 1 | 2 | ✅ |
| Estimación de tiempo | Sí | 5h total | ✅ |
