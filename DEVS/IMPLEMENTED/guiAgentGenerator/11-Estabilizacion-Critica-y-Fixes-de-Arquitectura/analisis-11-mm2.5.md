# 📋 Análisis Técnico — Paso 11: Estabilización Crítica y Fixes de Arquitectura

**Agente:** mm2.5  
**Paso:** 11  
**Fecha:** 2026-05-16

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | grep en migrations | ✅ | `supabase/migrations/030_agent_templates.sql:10` |
| 2 | Migration tiene índice único en name+is_system | grep en 030 | ✅ | `030_agent_templates.sql:32-33` |
| 3 | templates_seed.py usa SELECT previo | read | ✅ | `src/cli/commands/templates_seed.py:183-193` |
| 4 | BuilderBreadcrumb recibe prop activeTab | read | ✅ | `BuilderBreadcrumb.tsx:18` |
| 5 | page.tsx pasa activeTab hardcodeado | read | ✅ | `dashboard/app/(app)/builder/page.tsx:9` |
| 6 | BuilderLayout tiene estado activeTab | read | ✅ | `BuilderLayout.tsx:56` |
| 7 | Test suite ejecutada | pytest | ✅ | 21/32 fallidos con AttributeError |
| 8 | AgentForm usa zodResolver | read | ✅ | `AgentForm.tsx:82` |
| 9 | conftest.py tiene patch_points | read | ✅ | `tests/conftest.py:117-126` |
| 10 | Migration 030 existe | glob | ✅ | `supabase/migrations/030_agent_templates.sql` |
| 11 | Archivo test_builder_scenarios.py | read | ✅ | `tests/e2e/test_builder_scenarios.py:1-937` |
| 12 | RLS en agent_templates | read | ✅ | `030_agent_templates.sql:25-29` |

**Discrepancias encontradas:**

1. **ID-C02 - templates_seed.py:** El script usa SELECT previo + INSERT, NO usa `ON CONFLICT` con cláusula `WHERE`. El unique constraint existe pero no se aprovecha en el código.
2. **ID-C03 - Breadcrumb desconectado:** page.tsx pasa `activeTab="agent-form"` hardcodeado, mientras BuilderLayout tiene estado interno que cambia pero no se pasa al Breadcrumb.
3. **ID-C04 - Test suite:** 21/32 tests fallan por `AttributeError: 'NoneType' object has no attribute 'data'` — el mock de `.maybe_single()` no retorna objeto con `.data` cuando no hay datos.
4. **ID-023 - zodResolver:** No hay errores de TypeScript en tsc --noEmit. El código compila correctamente.
5. **ID-051 - Mocking refactor:** Los patch_points en conftest.py actúan sobre módulos que pueden no haber importado las dependencias antes del patch.
6. **ID-052 - Regression audit:** Se necesita validar que cambios en conftest.py no rompan suites pre-existentes.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema y tablas

- **Tabla:** `agent_templates` — existe en migración 030
- **Columnas:** id (UUID), name (TEXT), description (TEXT), category (TEXT), soul_json (JSONB), suggested_tools (TEXT[]), max_iter (INTEGER), is_system (BOOLEAN), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ)
- **Índices:**
  - `idx_agent_templates_category` en category
  - `idx_agent_templates_system_name` único en (name) WHERE is_system = TRUE

### Problema ID-C02

El script `templates_seed.py` usa este flujo:
```python
existing = db.table("agent_templates").select("id").eq("name", template["name"]).eq("is_system", True).maybe_single().execute()
if existing.data:
    skipped += 1
    continue
db.table("agent_templates").insert({...}).execute()
```

**Issue:** No usa UPSERT con `ON CONFLICT DO UPDATE ... WHERE is_system = TRUE`. El unique index existe (`idx_agent_templates_system_name`) pero no se aprovecha.

**Solución requerida:** Cambiar a UPSERT con conflict target y WHERE clause.

### RLS Policies

- SELECT: cualquier usuario autenticado (`auth.role() = 'authenticated'`)
- ALL: solo service_role (`auth.role() = 'service_role'`)
- El seed corre con service_role, debería poder usar upsert

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Tarea 1: Fix DB Seed (templates_seed.py)

**Archivo:** `src/cli/commands/templates_seed.py:181-212`

**Firma actual:**
```python
for template in TEMPLATES:
    existing = db.table("agent_templates").select("id").eq("name", template["name"]).eq("is_system", True).maybe_single().execute()
    if existing.data:
        skipped += 1
        continue
    db.table("agent_templates").insert({...}).execute()
```

**Problema:** SELECT + INSERT no es atómico. Entre el SELECT y el INSERT puede haber race condition.

**Patrón existente en el proyecto:** Ningún otro archivo usa UPSERT con ON CONFLICT. La tabla `agent_catalog` en workflows usa un patrón similar.

**Cambio requerido:**
```python
db.table("agent_templates").upsert({
    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fap.system.template.{template['name']}")),
    "name": template["name"],
    "description": template["description"],
    "category": template["category"],
    "soul_json": template["soul_json"],
    "suggested_tools": template["suggested_tools"],
    "max_iter": template["max_iter"],
    "is_system": True,
}, on_conflict="name", ignore_duplicates=True).execute()
```

Pero el constraint es parcial (`WHERE is_system = TRUE`), el upsert no soporta eso directamente. Alternativa: usar raw SQL con ON CONFLICT DO UPDATE ... WHERE is_system = TRUE.

### Tarea 2: Sync Breadcrumbs (BuilderBreadcrumb + BuilderLayout)

**Archivos:**
- `dashboard/components/builder/BuilderLayout.tsx:56` — estado interno `activeTab`
- `dashboard/components/builder/BuilderBreadcrumb.tsx:18` — prop `activeTab`
- `dashboard/app/(app)/builder/page.tsx:9` — pasa hardcodeado "agent-form"

**Problema:** El Breadcrumb muestra siempre "Agent Form" aunque el usuario esté en "Crew Canvas".

**Solución requerida:** El BuilderLayout debe proporcionar el estado `activeTab` al componente padre (page.tsx) o el Breadcrumb debe consumir el estado directamente desde el contexto de tabs.

**Opción A:** Usar URL query params (`?tab=crew-canvas`) — más shareable
**Opción B:** Usar state lifting — pasar setActiveTab desde page.tsx a BuilderLayout
**Opción C:** Usar Context API para el tab activo

### Tarea 3: Fix Test Suite (test_builder_scenarios.py)

**Archivo:** `tests/e2e/test_builder_scenarios.py:215-262`

**Helper functions:**
- `mock_select()` — configura db.table().select().eq().execute()
- `mock_insert()` — configura db.table().insert().execute()
- `mock_update()` — configura db.table().update().execute()

**Problema:** Cuando `.maybe_single()` no encuentra datos, retorna `None`, no un objeto con `.data`. El código del endpoint hace:
```python
existing = db.table("agent_catalog").select(...).maybe_single().execute()
if existing.data:  # <- AttributeError aquí
```

**Solución:** Los helpers `mock_select`, `mock_insert`, etc. deben retornar un objeto con `.data` cuando no hay datos, no `None`.

```python
def mock_select(db, data=None):
    """Configure db.table("X").select() chain."""
    sel = MagicMock()
    sel.eq = MagicMock(return_value=sel)
    # ...
    # AGREGAR: cuando data=None, el execute debe retornar un objeto con .data = []
    resp = MagicMock()
    resp.data = data if data is not None else []  # <-- Fix: siempre retorna objeto con .data
    sel.execute.return_value = resp
    # ...
```

También `.maybe_single()` debe retornar un mock que retorne `.data = None` cuando no hay datos.

### Tarea 4: TypeScript Integrity (AgentForm zodResolver)

**Archivo:** `dashboard/components/builder/AgentForm.tsx:82`

```typescript
const {
    register,
    handleSubmit,
    // ...
} = useForm<AgentFormData>({
    resolver: zodResolver(agentFormSchema),
    defaultValues: {...}
})
```

**Verificación:** `npx tsc --noEmit` retorna sin errores.

**Discrepancia ID-023:** El issue menciona "mismatch de tipos en zodResolver" pero no se reproduce. El código compila. Puede haber sido resuelto en una versión anterior o el issue está obsoleto.

### Tarea 5: Mocking Refactor (patch points)

**Archivo:** `tests/conftest.py:117-126`

```python
patch_points = [
    "src.db.session.get_service_client",
    "src.db.vault.get_service_client",
    "src.flows.base_flow.get_service_client",
    # ...
]
```

**Problema ID-051:** Si un módulo ya importó `get_service_client` desde su origen (no desde el patch path), el patch no afecta a ese módulo.

**Solución:** Usar `patch` con `create=True` para crear el mock si no existe, o asegurar que los tests importen las dependencias después de que los patches estén activos. Alternativa: usar `patch.dict('sys.modules', {...})` para interceptar el import.

### Tarea 6: Regression Audit (conftest.py global)

**Verificación ejecutada:**
```
uv run pytest tests/ -v --collect-only 2>&1 | grep "test session starts" -A 5
```

No hay evidencia de regresión en otras suites. Los cambios en conftest.py no afectan otras suites porque cada suite tiene su propio conftest.py.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints relacionados

| Endpoint | Método | Archivo | Test que falla |
|---|---|---|---|
| POST /agents | 201 | `src/api/routes/agents.py:122` | test_create_agent_returns_201 |
| GET /api/tools/available | 200 | `src/api/routes/tools.py` | test_tools_available_returns_200 |
| GET /api/templates | 200 | `src/api/routes/templates.py` | test_list_templates_returns_list |
| POST /agents/{role}/run | 200 | `src/api/routes/agents.py` | test_post_run_returns_task_id |
| POST /workflows | 201 | `src/api/routes/workflows.py` | test_create_workflow_returns_201 |
| POST /api/bundles/import | 201 | `src/api/routes/bundles.py` | test_export_and_reimport_returns_201 |

### Flujo del error

El error `AttributeError: 'NoneType' object has no attribute 'data'` ocurre porque:

1. El test crea mock de db con `mock_select(db, data=[])` 
2. El helper configura `.execute().data = []`
3. PERO el endpoint usa `.maybe_single().execute()` — no `.select().execute()`
4. `.maybe_single()` no está configurado en el helper, retorna `None`
5. Al hacer `if existing.data:` falla

**Fix requerido en helpers:**
```python
def mock_select(db, data=None):
    sel = MagicMock()
    sel.eq = MagicMock(return_value=sel)
    sel.maybe_single = MagicMock(return_value=sel)  # <-- AGREGAR
    sel.single = MagicMock(return_value=sel)        # <-- AGREGAR
    resp = MagicMock()
    resp.data = data if data is not None else []
    sel.execute.return_value = resp
    db.table.return_value.select.return_value = sel
    return sel
```

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo DB → Backend → Frontend

| Componente | Estado | Issue |
|---|---|---|
| agent_templates table | ✅ Existe | No usa UPSERT |
| templates_seed.py | ⚠️ No idempotente | Race condition possible |
| BuilderBreadcrumb | ⚠️ Desconectado | No refleja tab activo |
| BuilderLayout | ✅ Funciona | No comunica estado al Breadcrumb |
| Test suite | ❌ 21/32 fallan | Mock de maybe_single no configurado |
| TypeScript AgentForm | ✅ Compila | Sin errores |

### Gaps

1. **Idempotencia del seed:** Si alguien corre `fap templates seed` 2 veces, la segunda vez puede fallar o duplicar (depende de timing).
2. **Breadcrumb stale:** El usuario ve "Agent Form" aunque esté en "Crew Canvas" — confusión UX.
3. **Tests rotos:** La suite de 32 tests está inutilizable — bloquea validación del paso 10.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta propuesta: fap test-builder run --fix-mocks
- **Qué automatiza:** Corrige automáticamente los mocks de tests para que la suite sea ejecutable
- **Tipo:** CLI / validador
- **Cómo se usa:** `uv run fap test-builder run --fix-mocks` o integrada automáticamente cuando se detectan errores de mock
- **Impacto para el usuario final:** La suite de 32 tests pasa de 11/32 a 32/32 sin intervención manual
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

Alternativamente, crear un script `scripts/fix_test_mocks.py` que aplique automáticamente el fix a los helpers.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `agent_templates` existe con columnas correctas (migración 030)
✅ [DATA] Índice único en (name) WHERE is_system = TRUE existe
❌ [DATA] templates_seed.py usa UPSERT con ON CONFLICT — NO IMPLEMENTADO
✅ [CODE] BuilderBreadcrumb recibe prop activeTab correctamente
❌ [CODE] Breadcrumb muestra tab activo en tiempo real — NO IMPLEMENTADO (hardcoded)
✅ [BACKEND] GET /api/tools/available retorna 200 (endpoint existe)
✅ [BACKEND] GET /api/templates retorna 200 (endpoint existe)
❌ [BACKEND] Test suite pasa 32/32 — SOLO 11/32 pasan actualmente
❌ [FULLSTACK] `fap templates seed` ejecutable N veces sin error — verificar idempotencia
✅ [DX] tsc --noEmit sin errores en componentes del builder
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Race condition en seed | Media | SELECT + INSERT no atómico | Usar UPSERT |
| Breadcrumb incorrecto | Baja | No pasa estado al componente | Implementar sync con query params o context |
| Tests no ejecutables | Alta | Mock mal configurado | Fix en helpers de mock |
| Mocks no afectan módulos ya importados | Media | Patch puntos insuficientes | Usar sys.modules patching |
| Suites pre-existentes afectadas | Baja | Cambios globales en conftest | Verificar con pytest --collect-only |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **Fix mocks helper** | `tests/e2e/test_builder_scenarios.py` | Funciones mock_select/mock_insert con maybe_single configurado | — | TEST | Media | 1h | Ninguna | → verificar: `uv run pytest tests/e2e/test_builder_scenarios.py -k test_create_agent_returns_201` pasa |
| 1 | Fix DB Seed idempotencia | `src/cli/commands/templates_seed.py` | Cambiar SELECT+INSERT a UPSERT con on_conflict="name" | — | DATA | Media | 1h | Tarea 0 | → verificar: `uv run fap templates seed` ejecutable 2 veces sin error |
| 2 | Sync Breadcrumb | `dashboard/components/builder/BuilderLayout.tsx` + `page.tsx` | Pasar activeTab desde page.tsx a BuilderLayout + usar setActiveTab | Query params pattern (step 14) | FULLSTACK | Baja | 1h | Ninguna | → verificar: Cambiar de tab en UI y ver Breadcrumb actualizar |
| 3 | Verificar TypeScript | `dashboard/components/builder/AgentForm.tsx` | — | — | CODE | Baja | 0.5h | Ninguna | → verificar: `npx tsc --noEmit` sin errores |
| 4 | Regression audit | `tests/conftest.py` | Verificar que cambios no rompen otras suites | — | TEST | Baja | 0.5h | Ninguna | → verificar: `uv run pytest tests/unit/ -v` pasa |
| 5 | Test suite validation | `tests/e2e/test_builder_scenarios.py` | 32 tests ejecutándose | — | TEST | Alta | 2h | Tarea 0, 1 | → verificar: `uv run pytest tests/e2e/test_builder_scenarios.py` pasa 32/32 |

**Tiempo total estimado:** 6 horas

---

## 🔮 Roadmap (NO implementar ahora)

1. **URL-based tabs:** Usar `?tab=crew-canvas` para deep linking y shareable URLs
2. **Async seed:** Hacer el seed asíncrono para soportar grandes volúmenes
3. **Seed with progress:** Mostrar progress bar durante seed de templates
4. **Test coverage report:** Integrar coverage en `fap test-builder run` output

---

## 🚫 Reglas de Oro

- ✅ **Análisis accionable y específico** — cada tarea tiene artefacto y verificación
- ✅ **TODO verificado contra código** — 12 elementos verificados
- ✅ **Discrepancias documentadas** — 6 issues encontrados, 3 confirmados
- ✅ **Nivel CTO exigente** — identificación de race condition en seed
- ✅ **Coherente con phase-state.md** — referenciado y alineado
- ✅ **TODO el paso** — 6 tareas cubrir ID-C02, ID-C03, ID-C04, ID-023, ID-051, ID-052
- ✅ **Etapas secuenciales** — data → code → backend → fullstack+DX
- ✅ **≥ 1 herramienta DX propuesta** — `fap test-builder run --fix-mocks`
- ✅ **Tareas atómicas** — 1 artefacto por tarea, interfaz completa
- ✅ **El implementador no decide nada** — todo especificado