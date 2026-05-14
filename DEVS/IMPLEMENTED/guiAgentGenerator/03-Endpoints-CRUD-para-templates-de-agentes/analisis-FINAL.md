# 🏛️ Análisis Unificado — Paso 03: Endpoints CRUD para templates de agentes

**Fase:** `guiAgentGenerator` | **Paso:** 03 | **Fecha:** 2026-05-13
**Fuente:** 6 análisis unificados (dsp, glm, laguna, ziq, ring, GF)
**Config:** `proyecto-config.json` leído y verificado

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **dsp** | ✅ 18 elementos | 4 (D1-D4) con resolución | ✅ `fap templates seed` + `list` | ✅ file:line precisa | **4.8** |
| **glm** | ✅ 18 elementos | 7 (D1-D7) más detallado | ✅ `fap templates list` | ✅ análisis profundo | **4.5** |
| **laguna** | ✅ 10 elementos | 5 discrepancias | ✅ template-seeder script | ✅ buena evidencia | **4.2** |
| **ziq** | ✅ 18 elementos | 5 discrepancias | ✅ `fap templates seed` CLI | ✅ sólido | **4.0** |
| **ring** | ✅ 9 elementos | 3 (D-01, D-02, D-03) | ✅ seed_templates.py | ✅ OK | **3.8** |
| **GF** | ✅ 6 elementos | 2 (básicas) | ✅ `fap templates seed` | ⚠️ mínimo | **3.2** |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | Router en `__init__.py` vs `main.py` | TODOS | ✅ `src/api/main.py:98-112` | Registrar en `main.py` — patrón real |
| 2 | `org_id` en `agent_templates` | dsp, glm, ring, GF | ✅ `024_service_catalog.sql:8-22` (tabla global sin org_id) | **SIN org_id para MVP.** Sigue patrón `service_catalog`. Templates son catálogo global. Añadir si se requieren custom post-MVP. |
| 3 | RLS policies: pública vs tenant | dsp, GF, glm, ring | ✅ `024_service_catalog.sql:46-50` | SELECT público (auth.role()='authenticated'), INSERT/UPDATE/DELETE solo service_role |
| 4 | Auth en endpoints (`require_org_id`) | dsp, GF, ring, glm | ✅ `integrations.py` (sin require_org_id) = patrón correcto | **SIN require_org_id** en GET. Lectura pública. dsp: `integrations.py` sin tenant → mismo patrón |
| 5 | Seed method: script vs migración SQL | dsp, glm, laguna, ziq | ✅ `scripts/seed_system_bundles.py` + `014_bartenders_seed_config.sql` | **CLI `fap templates seed`** + script `scripts/seed_agent_templates.py`. dsp's approach wins |
| 6 | Número de migración: 026 vs 030 | dsp, ring, GF, laguna | ✅ `ls supabase/migrations/` → última es 029 | **030** — verificado por 3 agentes |
| 7 | `suggested_tools` vs `allowed_tools` naming | ring | ✅ `bundle_schemas.py:107` usa `allowed_tools` | Plantilla usa `suggested_tools` (semántica diferente: sugerencia vs asignación). Correcto mantener separados. |
| 8 | `is_system` BOOLEAN no verificable | ring, laguna | ❌ No hay `is_system` en tablas existentes | Seguir patrón propuesto: `BOOLEAN DEFAULT FALSE`. Nuevo campo. |
| 9 | Contenido seed: español vs inglés | ring, dsp | ⚠️ Sin código de referencia | **Inglés.** Consistente con `agent_catalog` existente y `bundle_schemas.py`. |
| 10 | Seed duplicado en re-ejecución | dsp, glm, laguna | ✅ `014_bartenders_seed_config.sql:41-50` usa `ON CONFLICT DO NOTHING` | Idempotente con `UNIQUE(name)` parcial para system templates |

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo:** Crear tabla `agent_templates` en Supabase + endpoints `GET /api/templates` (listado con filtro) y `GET /api/templates/{id}` (detalle) para alimentar TemplatePicker (Paso 05) del builder visual.
- **Decisiones críticas:** (1) Tabla global sin `org_id` (patrón `service_catalog`), (2) Endpoints públicos sin `require_org_id` para lectura, (3) RLS: SELECT para autenticados, escritura solo `service_role`, (4) Migración **030**, (5) Seed vía CLI `fap templates seed` con script `scripts/seed_agent_templates.py`.
- **Correcciones al plan:** Router registrado en `main.py` (no `__init__.py`), endpoints sin `require_org_id`, seed via CLI en vez de migración SQL directa.
- **Herramienta DX seleccionada:** `fap templates seed` — CLI command que inserta 8 templates predefinidos. Fusiona propuestas de dsp (seed script), ziq (CLI command) y laguna (template-seeder).

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. User abre builder → TemplatePicker (Paso 05) hace `GET /api/templates`
2. Backend consulta `agent_templates` via `get_service_client()` (bypass RLS, tabla global)
3. Filtra por `?category=` si se especifica
4. Retorna `TemplateListResponse` con array ligero (sin `soul_json`)
5. User hace click "Use Template" en una card
6. Frontend hace `GET /api/templates/{id}`
7. Backend retorna `TemplateDetailResponse` con `soul_json` completo
8. AgentForm se auto-rellena con role/goal/backstory/suggested_tools/max_iter
9. User edita si desea y guarda en `agent_catalog`

### Edge Cases MVP

- **Sin templates:** Lista vacía → 200 con `{"templates": [], "count": 0}`
- **Template no existe:** 404 `{"detail": "Template not found"}`
- **ID malformado:** 404 (no revelar formato)
- **DB inaccesible:** 500 con `logger.exception`
- **Categoría inexistente:** 200 con lista vacía (no error)
- **Seed re-ejecutado:** Idempotente via `UNIQUE(name)` partial index

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### Archivo: `supabase/migrations/030_agent_templates.sql` (CREAR)

- **Tipo de cambio:** Creación
- **Descripción:** Tabla global `agent_templates` con RLS, índices, y seed de 8 templates

```sql
CREATE TABLE IF NOT EXISTS agent_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT NOT NULL,              -- Research, Development, Support, General
    soul_json       JSONB NOT NULL DEFAULT '{}', -- {role, goal, backstory}
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter        INTEGER DEFAULT 5,
    is_system       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "agent_templates_read" ON agent_templates
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "agent_templates_write" ON agent_templates
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX idx_agent_templates_category ON agent_templates(category);
CREATE UNIQUE INDEX idx_agent_templates_system_name
    ON agent_templates(name) WHERE is_system = TRUE;
```

- **Interfaces clave:** Columnas definidas arriba
- **Patrones a seguir:** `supabase/migrations/024_service_catalog.sql:8-22` (tabla global), `004_agent_catalog.sql:6-17` (estructura)

#### Archivo: `src/api/routes/templates.py` (CREAR)

- **Tipo de cambio:** Creación
- **Descripción:** Router con 2 endpoints GET + modelos Pydantic

**Modelos Pydantic:**
```python
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

class TemplateDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    soul_json: Dict[str, Any]
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
    """Listar templates. ?category= opcional. Sin auth."""
    db = get_service_client()
    query = db.table("agent_templates").select("*")
    if category:
        query = query.eq("category", category)
    data = query.execute()
    return TemplateListResponse(
        templates=[TemplateInfo(**t) for t in data.data],
        count=len(data.data)
    )

@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str) -> TemplateDetailResponse:
    """Obtener template por ID. 404 si no existe."""
    db = get_service_client()
    result = db.table("agent_templates").select("*")\
        .eq("id", template_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(404, "Template not found")
    return TemplateDetailResponse(**result.data)
```

- **Interfaces clave:** Firmas arriba
- **Patrones a seguir:** `src/api/routes/integrations.py:18-23` (listado simple con `get_service_client()`), `src/api/routes/tools.py:46-63` (Pydantic + count)

#### Archivo: `src/api/main.py` (MODIFICAR)

- **Tipo de cambio:** Modificación
- **Descripción:** Registrar router `templates_router`

```python
# Línea ~33 — agregar después de tools_router import
from .routes.templates import router as templates_router

# Línea ~113 — agregar app.include_router
app.include_router(templates_router, prefix="/api/templates")
```

- **Patrones a seguir:** `src/api/main.py:31+112` (tools_router pattern)

#### Archivo: `src/cli/commands/templates_seed.py` (CREAR)

- **Tipo de cambio:** Creación
- **Descripción:** CLI command `fap templates seed` para seed de 8 templates

- **Patrones a seguir:** `src/cli/commands/tools_list.py:29-64`

#### Archivo: `src/cli/main.py` (MODIFICAR)

- **Tipo de cambio:** Modificación
- **Descripción:** Registrar sub-app `templates` con comando `seed`

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap templates seed
- **Qué automatiza:** Inserción de 8 templates predefinidos (Research Agent, Code Reviewer, etc.) en Supabase desde CLI.
- **Tipo:** CLI command (Typer sub-app `templates` con sub-comando `seed`)
- **Ubicación:** `src/cli/commands/templates_seed.py` + registro en `src/cli/main.py`
- **Cómo se usa:**
  ```bash
  fap templates seed
  fap templates seed --dry-run  # preview sin insertar
  fap templates seed --reset    # re-insertar todos
  ```
- **Impacto para el usuario final:** Elimina SQL manual en Supabase Studio. Setup de 15 min → 1s.
- **El implementador DEBE usarla** para poblar templates luego de ejecutar migración 030.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Tabla global sin `org_id`:** Sigue patrón `service_catalog` (mig 024). Templates son catálogo de referencia, no aislados por tenant. Post-MVP si se requieren templates por org → migración separada que añada `org_id`.

2. **Endpoints públicos SIN `require_org_id`:** Catálogo global de lectura. Consistente con `integrations.py`. Autenticación requeriría forzar `X-Org-ID` innecesario.

3. **RLS: SELECT para autenticados, solo service_role para escritura:** Balance entre seguridad y simplicidad. No exponer a anónimos, pero cualquier usuario autenticado puede leer.

4. **Seed vía CLI + script, NO en migración SQL:** Consistente con `seed_system_bundles.py`. Más flexible (dry-run, reset) y no bloquea migraciones.

5. **`soul_json` sin validación Pydantic en API:** DB almacena JSONB, endpoint lo retorna como `Dict[str, Any]`. Validación de estructura (`role/goal/backstory`) va en seed script. Post-MVP: validator en modelo.

6. **UNIQUE parcial en `name` para system templates:** Evita duplicados en re-seed. Custom templates (futuro) usarían `UNIQUE(org_id, name)`.

### Correcciones al plan

- ⚠️ Plan dice router en `__init__.py` → código real usa `main.py`. Se implementa en `main.py`.
- ⚠️ Plan omite `org_id` pero tampoco aclara si tabla es global → **global** (patrón `service_catalog`).
- ⚠️ Plan dice "Registrar router en `src/api/__init__.py`" → corregido: `src/api/main.py`.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Migración `030_agent_templates.sql` existe y ejecuta sin errores
✅ [DATA] Tabla `agent_templates` con: id UUID PK, name TEXT NOT NULL, description TEXT, category TEXT NOT NULL, soul_json JSONB, suggested_tools TEXT[], max_iter INT, is_system BOOLEAN, created_at, updated_at
✅ [DATA] RLS: SELECT para authenticated, ALL solo service_role
✅ [DATA] Índices: idx_agent_templates_category, idx_agent_templates_system_name (unique partial)
✅ [DATA] Seed de 8 system templates: Research Agent, Code Reviewer, Data Analyst, Customer Support, Document Writer, Translator, Summarizer, General Assistant
✅ [DATA] Seed idempotente: ejecutar 2 veces → mismos 8 templates (sin duplicados)
✅ [CODE] `src/api/routes/templates.py` existe con router `prefix="/api/templates"`
✅ [CODE] Modelos Pydantic: TemplateInfo, TemplateListResponse, TemplateDetailResponse
✅ [CODE] `GET /api/templates` handler con filtro `?category=` funcional
✅ [CODE] `GET /api/templates/{id}` handler con 404 para IDs inexistentes
✅ [CODE] Respuesta incluye `count` (consistente con tools.py)
✅ [BACKEND] Router registrado en `main.py` (import + include_router)
✅ [BACKEND] `GET /api/templates` responde 200 con array (vacío si no hay templates)
✅ [BACKEND] `GET /api/templates/{id}` responde 200 con soul_json completo o 404
✅ [BACKEND] Filtro `?category=Research` filtra correctamente
✅ [BACKEND] Endpoints sin `require_org_id` — accesibles sin X-Org-ID
✅ [FULLSTACK] soul_json compatible con agent_catalog.soul_json (mismo formato {role, goal, backstory})
✅ [FULLSTACK] suggested_tools usa nombres de herramientas existentes en ToolRegistry
✅ [DX] `fap templates seed` ejecuta sin errores y verifica 8 templates insertados
```

**Funcionales:**
- [ ] Template list 200 con array
- [ ] Template detail 200 con soul_json completo
- [ ] 404 en template inexistente
- [ ] Category filter funcional
- [ ] Seed idempotente

**Técnicos:**
- [ ] Migración 030 ejecuta sin error
- [ ] RLS policies activas
- [ ] Router registrado en main.py
- [ ] Tests unitarios ≥ 3 casos
- [ ] `fap templates seed` funcional

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| **0** | **DX & Tooling:** `fap templates seed` — CLI command + seed script (8 templates) | Media | 1.5h | Ninguna |
| 1 | Crear migración `030_agent_templates.sql` (tabla + RLS + índices) | Baja | 0.5h | Tarea 0 |
| 2 | Crear `src/api/routes/templates.py` con modelos Pydantic | Media | 0.5h | Tarea 1 |
| 3 | Implementar `GET /api/templates` con filtro category | Media | 0.5h | Tarea 2 |
| 4 | Implementar `GET /api/templates/{id}` con 404 | Baja | 0.3h | Tarea 3 |
| 5 | Registrar router en `src/api/main.py` (import + include_router) | Baja | 0.1h | Tarea 4 |
| 6 | Tests unitarios: list, detail, filter, 404, seed idempotente | Media | 1h | Tareas 3-4 |
| 7 | Validar flujo end-to-end: seed → list → detail → filter | Baja | 0.5h | Tareas 0-6 |
| | **TOTAL** | | **4.4h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap templates seed` para poblar templates antes de validar endpoints.

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Templates globales sin `org_id` imposibilitan templates custom | Media | Decisión MVP sacrifica custom templates | Post-MVP: migración 031 añade `org_id` + migra system a `org_id=NULL` |
| Seed con tools que no existen en ToolRegistry | Baja | suggested_tools son strings, no FK | Frontend filtra contra `GET /api/tools/available`. Seed usa tools del registry existente. |
| `soul_json` inconsistente entre seed → AgentForm | Media | Sin validación de estructura en DB | Seed script valida role/goal/backstory antes de insertar. Tests de seed verifican estructura. |
| Colisión migración 030 con otro branch | Baja | Dos ramas crean 030 simultáneo | Verificar `supabase/migrations/` antes de merge. Usar siguiente número disponible. |
| Sin cache en endpoint → DB hit cada request | Baja | 8 filas, latencia insignificante MVP | Documentado. Post-MVP: `lru_cache` con TTL si necesario. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | List templates (vacíos) | `GET /api/templates` sin seed | `{"templates": [], "count": 0}` — 200 |
| TP-2 | List templates (post-seed) | `GET /api/templates` tras seed | `{"templates": [8 items], "count": 8}` — 200 |
| TP-3 | Filter by category | `GET /api/templates?category=Research` | Solo templates con `category=Research` |
| TP-4 | Get template by ID (found) | `GET /api/templates/{valid_id}` | Template con `soul_json` completo — 200 |
| TP-5 | Get template by ID (not found) | `GET /api/templates/{invalid_id}` | `{"detail": "Template not found"}` — 404 |
| TP-6 | Seed idempotent | `fap templates seed` × 2 | `SELECT COUNT(*)` = 8 ambas veces |
| TP-7 | Sin auth funciona | `GET /api/templates` sin X-Org-ID | 200 (no 400/403) |
| TP-8 | soul_json estructura válida | Todos los templates seeded | Cada uno tiene `role`, `goal`, `backstory` |

Comando para ejecutar tests: `uv run pytest tests/unit/ -v --timeout=60`
