# Análisis Técnico — Paso 11: Estabilización Crítica y Fixes de Arquitectura

**Agente:** qwen
**Fecha:** 2026-05-16
**Fase:** guiAgentGenerator
**Prioridad:** Crítica

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql` línea 10 | ✅ | Migración 030, CREATE TABLE |
| 2 | Cláusula `ON CONFLICT` en templates_seed.py | `src/cli/commands/templates_seed.py` líneas 181-206 | ❌ | Usa SELECT + INSERT manual, NO usa `ON CONFLICT` |
| 3 | `BuilderBreadcrumb` recibe `activeTab` como prop | `dashboard/components/builder/BuilderBreadcrumb.tsx` línea 18 | ✅ | `export function BuilderBreadcrumb({ activeTab }: { activeTab: string })` |
| 4 | `BuilderLayout` mantiene estado `activeTab` | `dashboard/components/builder/BuilderLayout.tsx` línea 56 | ✅ | `const [activeTab, setActiveTab] = useState('agent-form')` |
| 5 | `page.tsx` hardcodea `activeTab="agent-form"` | `dashboard/app/(app)/builder/page.tsx` línea 9 | ✅ | `<BuilderBreadcrumb activeTab="agent-form" />` |
| 6 | `BuilderBreadcrumb` NO conectado a Tabs de BuilderLayout | `BuilderBreadcrumb.tsx` vs `BuilderLayout.tsx` | ❌ | Componentes separados, sin contexto compartido |
| 7 | `test_builder_scenarios.py` existe | `tests/e2e/test_builder_scenarios.py` | ✅ | 937 líneas, 6 clases de test |
| 8 | `conftest.py` patch points | `tests/conftest.py` líneas 117-126 | ✅ | 8 patch points para `get_service_client` |
| 9 | `AgentForm.tsx` usa `zodResolver` | `dashboard/components/builder/AgentForm.tsx` línea 6, 82 | ✅ | `resolver: zodResolver(agentFormSchema)` |
| 10 | Zod schema define `llmProvider` como enum | `AgentForm.tsx` línea 37 | ✅ | `z.enum(['groq', 'openai', 'anthropic', 'openrouter'])` |
| 11 | `zod` versión en package.json | `dashboard/package.json` línea 47 | ⚠️ | `zod: ^4.4.3` — Zod v4 tiene breaking changes vs v3 |
| 12 | `@hookform/resolvers` versión | `dashboard/package.json` línea 13 | ⚠️ | `^5.2.2` — compatible con Zod v4 pero requiere validación |
| 13 | `mock_service_client` fixture usa `patch.start()` manual | `conftest.py` líneas 128-140 | ✅ | Stack de patches con start/stop manual |
| 14 | `mock_auth` fixture usa `dependency_overrides` | `test_builder_scenarios.py` líneas 176-186 | ✅ | Override de `verify_org_membership` |
| 15 | Migración 030 tiene índice único parcial | `030_agent_templates.sql` línea 32-33 | ✅ | `CREATE UNIQUE INDEX ... WHERE is_system = TRUE` |
| 16 | `templates_seed.py` usa `uuid5` para IDs deterministas | `templates_seed.py` línea 197 | ✅ | `uuid.uuid5(uuid.NAMESPACE_DNS, f"fap.system.template.{template['name']}")` |
| 17 | `AgentForm` tipo `AgentFormData` exportado | `AgentForm.tsx` línea 47 | ✅ | `export type AgentFormData = z.infer<typeof agentFormSchema>` |
| 18 | `BuilderLayout` importa `AgentFormData` | `BuilderLayout.tsx` línea 7 | ✅ | `import { AgentForm, type AgentFormData }` |
| 19 | `mapTemplateToFormValues` retorna `AgentFormData` | `BuilderLayout.tsx` líneas 27-49 | ✅ | Función completa con mapeo de todos los campos |
| 20 | `templates.py` usa `get_service_client` directo | `src/api/routes/templates.py` línea 59 | ✅ | Sin tenant context, patrón lectura pública |

**Discrepancias encontradas:**

1. **ID-C02 — templates_seed.py no es idempotente con `ON CONFLICT`:** El script hace SELECT + INSERT manual (líneas 183-206). Funciona pero es race-condition prone. La migración 030 ya tiene `UNIQUE INDEX idx_agent_templates_system_name` — el seed debería usar `upsert()` o `INSERT ... ON CONFLICT` vía RPC. **Resolución:** Cambiar a `db.table("agent_templates").upsert({...}).execute()` con `on_conflict` o mantener SELECT+INSERT pero añadir manejo de conflicto explícito.

2. **ID-C03 — Breadcrumb desconectado del estado de Tabs:** `BuilderBreadcrumb` está en `page.tsx` (línea 9) con `activeTab` hardcodeado. `BuilderLayout` tiene el estado real de tabs (línea 56) pero no lo expone al padre. **Resolución:** Crear contexto React `BuilderTabContext` o elevar estado a `page.tsx` y pasar `activeTab` + `setActiveTab` como props.

3. **ID-023 — Zod v4 breaking change:** `package.json` usa `zod ^4.4.3`. Zod v4 cambia la API de `z.enum()` y `z.infer`. `@hookform/resolvers@5.2.2` soporta Zod v4 pero el schema actual usa sintaxis v3 (`z.enum([...])`). **Resolución:** Verificar compatibilidad. Si hay error de tipos, migrar schema a API v4 o pin Zod a v3.

4. **ID-051 — Patch points pueden no cubrir todos los imports:** `conftest.py` parchea 8 puntos para `get_service_client` pero `test_builder_scenarios.py` usa `patch("src.db.session.get_tenant_client", ...)` inline (línea 293). Los patches del conftest usan `patch.start()` antes de que los módulos de test se importen — si el módulo ya importó la dependencia, el patch no aplica. **Resolución:** Mover patches a `pytest_plugins` o usar `monkeypatch.setattr` en fixtures con scope correcto.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas
- **`agent_templates`** (migración 030) — tabla global sin `org_id`, RLS: SELECT authenticated, ALL service_role.

### Schema actual verificado
```sql
agent_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    soul_json JSONB NOT NULL DEFAULT '{}',
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter INTEGER DEFAULT 5,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
)
```

### Índices
- `idx_agent_templates_category` — B-tree en `category`
- `idx_agent_templates_system_name` — UNIQUE parcial: `WHERE is_system = TRUE`

### Problema de idempotencia
El seed script (`templates_seed.py`) genera UUIDs deterministas con `uuid5`. Esto permite idempotencia lógica pero no usa el mecanismo de DB. El índice parcial único solo protege templates con `is_system=TRUE`.

**Riesgo:** Si se ejecuta `--reset` y luego `seed` concurrentemente, puede haber duplicados temporales.

### RLS Policies
- `agent_templates_read`: SELECT para `authenticated`
- `agent_templates_write`: ALL para `service_role`

El seed usa `get_service_client()` que bypassa RLS — correcto para seed system.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Fix ID-C02: templates_seed.py

**Archivo:** `src/cli/commands/templates_seed.py`

**Problema:** Líneas 181-206 hacen:
```python
existing = db.table("agent_templates").select("id").eq("name", ...).eq("is_system", True).execute()
if existing.data:
    skipped += 1
    continue
db.table("agent_templates").insert({...}).execute()
```

**Firma actual de `seed_templates`:**
```python
def seed_templates(dry_run: bool = False, reset: bool = False) -> None
```

**Resolución propuesta:** Usar `upsert()` del cliente Supabase Python:
```python
db.table("agent_templates").upsert({
    "id": str(uuid.uuid5(...)),
    "name": template["name"],
    ...
}, on_conflict="name").execute()
```

Pero el cliente Python de Supabase no soporta `on_conflict` directamente. Alternativa: usar RPC o mantener SELECT+INSERT con `try/except` para conflicto.

**Patrón de referencia:** `supabase/migrations/030_agent_templates.sql` línea 32-33 — el índice unique parcial ya existe.

### Fix ID-C03: BuilderBreadcrumb sync

**Archivos involucrados:**
- `dashboard/app/(app)/builder/page.tsx` (línea 9)
- `dashboard/components/builder/BuilderBreadcrumb.tsx` (línea 18)
- `dashboard/components/builder/BuilderLayout.tsx` (línea 56, 73)

**Problema:** `BuilderBreadcrumb` en `page.tsx` recibe `"agent-form"` hardcoded. `BuilderLayout` tiene el estado real en `useState('agent-form')` y lo usa en `<Tabs value={activeTab} onValueChange={setActiveTab}>`.

**Firma actual de `BuilderBreadcrumb`:**
```tsx
export function BuilderBreadcrumb({ activeTab }: { activeTab: string })
```

**Firma actual de `BuilderLayout`:**
```tsx
export function BuilderLayout()
```

**Resolución propuesta:** Crear `BuilderTabContext`:
```tsx
// dashboard/components/builder/BuilderTabContext.tsx
import { createContext, useContext, useState, type ReactNode } from 'react'

interface BuilderTabContextType {
  activeTab: string
  setActiveTab: (tab: string) => void
}

const BuilderTabContext = createContext<BuilderTabContextType | undefined>(undefined)

export function BuilderTabProvider({ children }: { children: ReactNode }) {
  const [activeTab, setActiveTab] = useState('agent-form')
  return (
    <BuilderTabContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </BuilderTabContext.Provider>
  )
}

export function useBuilderTab() {
  const ctx = useContext(BuilderTabContext)
  if (!ctx) throw new Error('useBuilderTab must be used within BuilderTabProvider')
  return ctx
}
```

**Imports necesarios en `page.tsx`:**
```tsx
import { BuilderTabProvider } from '@/components/builder/BuilderTabContext'
import { useBuilderTab } from '@/components/builder/BuilderTabContext'
```

**Imports necesarios en `BuilderBreadcrumb.tsx`:**
```tsx
import { useBuilderTab } from '@/components/builder/BuilderTabContext'
```

**Imports necesarios en `BuilderLayout.tsx`:**
```tsx
import { useBuilderTab } from '@/components/builder/BuilderTabContext'
```

### Fix ID-023: Zod type mismatch

**Archivo:** `dashboard/components/builder/AgentForm.tsx`

**Schema actual (líneas 33-45):**
```tsx
const agentFormSchema = z.object({
  role: z.string().min(1, 'Role is required'),
  goal: z.string().min(1, 'Goal is required'),
  backstory: z.string().min(1, 'Backstory is required'),
  llmProvider: z.enum(['groq', 'openai', 'anthropic', 'openrouter']),
  llmModel: z.string(),
  allowedTools: z.array(z.string()),
  maxIter: z.number().int().min(1).max(10),
  verbose: z.boolean(),
  reasoning: z.boolean(),
  injectDate: z.boolean(),
  memory: z.boolean(),
})
```

**Problema:** Zod v4 (`^4.4.3`) cambia `z.enum()` — ahora requiere `z.enum(['a', 'b'] as const)` o usa `z.literal()` combinado. `@hookform/resolvers@5.2.2` es compatible con Zod v4 pero el schema usa sintaxis v3.

**Resolución:** Opción A — Pin Zod a v3 (`"zod": "^3.24.0"`). Opción B — Migrar schema a v4:
```tsx
const agentFormSchema = z.object({
  role: z.string().min(1),
  goal: z.string().min(1),
  backstory: z.string().min(1),
  llmProvider: z.enum(['groq', 'openai', 'anthropic', 'openrouter'] as const),
  ...
})
```

**Patrón de referencia:** No hay otros schemas Zod en el dashboard para comparar. Verificar con `tsc --noEmit`.

### Fix ID-051: Mocking refactor

**Archivo:** `tests/conftest.py`

**Problema:** Los fixtures usan `patch.start()` manual (líneas 128-140). Si un test importa un módulo antes de que el fixture se ejecute, el patch no aplica al módulo ya importado.

**Fixture actual (`mock_service_client`):**
```python
@pytest.fixture
def mock_service_client():
    client = make_mock_client()
    patch_points = [
        "src.db.session.get_service_client",
        "src.db.vault.get_service_client",
        ...
    ]
    stack = []
    for p in patch_points:
        try:
            pt = patch(p, return_value=client)
            pt.start()
            stack.append(pt)
        except (AttributeError, ImportError):
            continue
    yield client
    for pt in stack:
        pt.stop()
```

**Problema específico en `test_builder_scenarios.py`:** Los tests usan `patch("src.db.session.get_tenant_client", return_value=cm)` inline dentro del test (línea 293). Esto funciona porque el patch se aplica dentro del `with` block. Pero si `conftest.py` también parchea el mismo punto, hay conflicto.

**Resolución:** Unificar patch points en `conftest.py` y usar `@pytest.fixture(autouse=True)` con `monkeypatch.setattr` en lugar de `patch.start()`:
```python
@pytest.fixture(autouse=True)
def mock_all_db_clients(monkeypatch):
    client = make_mock_client()
    monkeypatch.setattr("src.db.session.get_service_client", lambda: client)
    monkeypatch.setattr("src.db.session.get_anon_client", lambda: client)
    # ... más puntos
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints tocados indirectamente
- `GET /api/templates` — `src/api/routes/templates.py:54` — Sin auth, lectura pública
- `GET /api/templates/{id}` — `src/api/routes/templates.py:70` — Sin auth, 404 si no existe

### Middleware aplicable
Los endpoints de templates NO usan `require_org_id` (ver `templates.py` línea 7). Patrón consistente con `integrations.py`.

### Problema de error handling (ID-010 del plan original)
`templates.py` no maneja excepciones de DB. Si `get_service_client()` falla o la query lanza excepción, el cliente recibe 500 genérico.

**Resolución para este paso:** Añadir try/except con `HTTPException(503)`:
```python
@router.get("", response_model=TemplateListResponse)
async def list_templates(category: Optional[str] = Query(None)) -> TemplateListResponse:
    try:
        db = get_service_client()
        query = db.table("agent_templates").select("*")
        if category:
            query = query.eq("category", category)
        data = query.execute()
        return TemplateListResponse(
            templates=[TemplateInfo(**t) for t in data.data],
            count=len(data.data),
        )
    except Exception as exc:
        logger.error("Failed to list templates: %s", exc)
        raise HTTPException(status_code=503, detail="Template service unavailable")
```

### Contratos verificados
| Endpoint | Input | Output | Auth |
|---|---|---|---|
| `GET /api/templates` | `?category=` (query) | `TemplateListResponse` | Ninguna |
| `GET /api/templates/{id}` | `template_id` (path) | `TemplateDetailResponse` | Ninguna |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
[CLI: fap templates seed] → [Supabase: agent_templates] → [GET /api/templates] → [TemplatePicker] → [AgentForm]
                                                                                       ↓
[BuilderLayout] ← Tabs state ← [BuilderTabContext] → [BuilderBreadcrumb]
```

### Puntos críticos
1. **Breadcrumb-Tabs disconnect:** El usuario cambia de tab en BuilderLayout pero el breadcrumb no se actualiza porque está en un componente padre con valor hardcoded.
2. **Seed idempotencia:** Ejecutar `fap templates seed` múltiples veces funciona (SELECT check) pero no es atómico.
3. **Zod v4 incompatibilidad:** Puede romper `tsc --noEmit` y la validación del formulario en runtime.

### DX & Tooling

### Herramienta Propuesta: `fap doctor builder`
- **Qué automatiza:** Diagnóstico automático de los 6 problemas críticos del Paso 11 en un solo comando. Verifica: seed idempotencia, breadcrumb sync, TypeScript errors, test suite status, mock coverage, Zod compatibility.
- **Tipo:** CLI command
- **Cómo se usa:** `fap doctor builder` — ejecuta checks secuenciales y reporta OK/FAIL con detalle.
- **Impacto para el usuario final:** Evita ejecutar 6 comandos separados para verificar estabilidad. Un solo comando da el estado de salud del builder.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

### Herramienta Propuesta: `fap fix builder`
- **Qué automatiza:** Aplica automáticamente los fixes del Paso 11 (idempotencia seed, breadcrumb context, Zod pin, mock unification).
- **Tipo:** CLI wizard
- **Cómo se usa:** `fap fix builder --dry-run` (preview) o `fap fix builder --apply` (aplica cambios).
- **Impacto para el usuario final:** Reduce el paso de 6 tareas manuales a 1 comando.
- **Prioridad:** Tarea 1 — después de `doctor`.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] `fap templates seed` ejecutable N veces sin error ni duplicados
✅ [DATA] Migración 030 mantiene índice único parcial funcional
✅ [CODE] `BuilderBreadcrumb` refleja cambios de tab en tiempo real
✅ [CODE] `tsc --noEmit` sin errores en componentes del builder
✅ [CODE] `AgentForm.tsx` compila con resolver de Zod sin warnings de tipo
✅ [BACKEND] Endpoints de templates manejan errores de DB con 503
✅ [BACKEND] `templates_seed.py` usa mecanismo atómico (upsert o try/except conflicto)
✅ [FULLSTACK] Breadcrumb muestra tab activo correctamente en UI
✅ [FULLSTACK] Test suite `fap test builder run` pasa 32/32 escenarios
✅ [DX] `fap doctor builder` ejecuta sin errores y reporta estado de los 6 fixes
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Zod v4 breaking change rompe build | Alta | `z.enum()` API cambió en v4, `@hookform/resolvers` puede no inferir tipos correctamente | Pin a Zod v3.24 o migrar schema completo a v4 con `as const` |
| Mock patches conflictivos entre conftest y tests | Alta | `patch.start()` en conftest vs `with patch()` inline en tests causan doble-patch o no-patch | Unificar en `monkeypatch.setattr` con fixture autouse |
| Breadcrumb context rompe SSR | Media | React Context en componente server puede causar hydration mismatch | Usar `'use client'` en Provider y envolver solo componentes cliente |
| Seed upsert falla con índice parcial | Media | `upsert()` con `on_conflict="name"` puede no respetar el índice parcial `WHERE is_system=TRUE` | Usar `on_conflict="idx_agent_templates_system_name"` o mantener SELECT+INSERT con try/except |
| Tests 32/32 no alcanzable sin refactor mayor | Media | Algunos tests dependen de infra real (Supabase) que puede no estar disponible en CI | Mockear a nivel de fixture, no inline |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap doctor builder` | `src/cli/commands/doctor_builder.py` | `def doctor_builder(dry_run: bool) -> None` — 6 checks secuenciales | `src/cli/commands/test_builder.py :: run_builder_tests()` | DX | Media | 1h | Ninguna | → verificar: `fap doctor builder` ejecuta y muestra 6 checks con OK/FAIL |
| 1 | Fix idempotencia seed | `src/cli/commands/templates_seed.py` | `def seed_templates(dry_run: bool, reset: bool) -> None` — cambiar INSERT a try/except con manejo de conflicto unique | `src/cli/commands/templates_seed.py` existente, líneas 181-206 | DATA | Baja | 0.5h | Tarea 0 | → verificar: `fap templates seed` ejecutable 3 veces seguidas sin error |
| 2 | Crear BuilderTabContext | `dashboard/components/builder/BuilderTabContext.tsx` | `export function BuilderTabProvider({ children }: { children: ReactNode })`, `export function useBuilderTab(): { activeTab: string, setActiveTab: (tab: string) => void }` | `dashboard/components/builder/BuilderLayout.tsx` (patrón useState existente) | CODE | Baja | 0.5h | Tarea 0 | → verificar: importable desde `@/components/builder/BuilderTabContext` sin error |
| 3 | Refactor page.tsx con Provider | `dashboard/app/(app)/builder/page.tsx` | `export default function BuilderPage()` — envuelve contenido con `BuilderTabProvider` | `dashboard/app/(app)/layout.tsx` (patrón de providers existentes) | CODE | Baja | 0.5h | Tarea 2 | → verificar: `tsc --noEmit` sin errores en page.tsx |
| 4 | Refactor BuilderBreadcrumb con context | `dashboard/components/builder/BuilderBreadcrumb.tsx` | `export function BuilderBreadcrumb()` — eliminar prop `activeTab`, usar `useBuilderTab()` | `dashboard/components/builder/AgentForm.tsx` (patrón de hooks existentes) | CODE | Baja | 0.5h | Tarea 2 | → verificar: breadcrumb cambia al cambiar tab en UI |
| 5 | Refactor BuilderLayout con context | `dashboard/components/builder/BuilderLayout.tsx` | `export function BuilderLayout()` — reemplazar `useState` local por `useBuilderTab()` | `dashboard/components/builder/BuilderLayout.tsx` línea 56, 73 | CODE | Baja | 0.5h | Tarea 2 | → verificar: tabs funcionan igual que antes |
| 6 | Fix Zod type mismatch | `dashboard/package.json` | Pin `"zod": "^3.24.0"` o migrar schema v4 con `as const` en `AgentForm.tsx` línea 37 | `dashboard/package.json` existente | CODE | Baja | 0.5h | Tarea 0 | → verificar: `tsc --noEmit` sin errores en AgentForm.tsx |
| 7 | Unificar mock patches en conftest | `tests/conftest.py` | `@pytest.fixture(autouse=True) def mock_all_db_clients(monkeypatch)` — reemplazar `mock_service_client` y `mock_anon_client` con `monkeypatch.setattr` | `tests/conftest.py` líneas 111-168 (fixtures existentes) | CODE | Media | 1h | Tarea 0 | → verificar: `uv run pytest tests/e2e/test_builder_scenarios.py -v` sin AttributeError |
| 8 | Refactor test_builder_scenarios.py patches | `tests/e2e/test_builder_scenarios.py` | Eliminar `with patch("src.db.session.get_tenant_client", ...)` inline, usar fixture global | `tests/e2e/test_builder_scenarios.py` líneas 293, 327, 357, etc. | CODE | Media | 1h | Tarea 7 | → verificar: 32/32 tests pasan con `fap test builder run` |
| 9 | Añadir error handling en templates endpoint | `src/api/routes/templates.py` | `async def list_templates()` y `async def get_template()` — try/except con `HTTPException(503)` | `src/api/routes/agents.py` (patrón de error handling existente) | BACKEND | Baja | 0.5h | Tarea 0 | → verificar: `uv run pytest tests/unit/test_templates.py -v` pasa |
| 10 | Validación end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-9 | → verificar: criterios §5 pasan todos |

**Tiempo total estimado:** 7 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Migrar `BuilderTabContext` a query params (`?tab=agent-form`) para deep linking (Paso 14 ID-050)
- Añadir `fap fix builder --apply` que aplique todos los fixes automáticamente
- Mejorar reporte HTML de `fap test builder` con métricas de cobertura por escenario
- Centralizar constantes de validación de schemas en `lib/constants.ts` (Paso 13 ID-047)
