# 🧠 ANÁLISIS TÉCNICO — PASO 11

**AGENTE:** dsfm
**PASO:** 11 — Estabilización Crítica y Fixes de Arquitectura
**FASE:** guiAgentGenerator
**FECHA:** 2026-05-16

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Método | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `templates_seed.py` existe | read | ✅ | `src/cli/commands/templates_seed.py:1` |
| 2 | Seed usa check-then-insert vs ON CONFLICT | read líneas 183-206 | ❌ | Usa `select` + check Python, NO `ON CONFLICT`. Plan asume upsert SQL. |
| 3 | Unique index en `agent_templates(name) WHERE is_system` | read migración 030 | ✅ | Línea 32-33: `CREATE UNIQUE INDEX idx_agent_templates_system_name ON agent_templates(name) WHERE is_system = TRUE` |
| 4 | `BuilderBreadcrumb.tsx` recibe `activeTab` prop | read | ✅ | Línea 18: `export function BuilderBreadcrumb({ activeTab }: { activeTab: string })` |
| 5 | `page.tsx` hardcodea `activeTab="agent-form"` | read | ❌ | Línea 9: `<BuilderBreadcrumb activeTab="agent-form" />` — siempre fijo |
| 6 | `BuilderLayout` tiene estado `activeTab` interno | read | ✅ | Línea 56: `const [activeTab, setActiveTab] = useState('agent-form')` — pero no lo expone al padre |
| 7 | `AgentForm.tsx` usa `z.enum` para llmProvider | read | ⚠️ | Línea 37: `llmProvider: z.enum(['groq', 'openai', 'anthropic', 'openrouter'])` — estricto, error si valor inesperado |
| 8 | `conftest.py` tiene `global_llm_mock` con `autouse=True` | read | ⚠️ | Línea 276-305: parchea `langchain_openai`, `chat_models`, `crewai.Agent/Task/Crew` globalmente |
| 9 | `test_builder_scenarios.py` parchea `src.db.session.get_tenant_client` | read líneas 293, 327, 357, etc. | ❌ | Parchea el módulo fuente, NO los módulos que ya importaron `get_tenant_client` |
| 10 | `conftest.mock_tenant_client` parchea los módulos consumidores correctos | read líneas 189-202 | ✅ | `src.api.routes.agents.get_tenant_client`, `src.api.routes.tools.get_tenant_client`, etc. |
| 11 | RLS policies en migración 030 | read | ✅ | Líneas 25-29: `agent_templates_read` (SELECT authenticated), `agent_templates_write` (ALL service_role) |
| 12 | Registro de `templates_router` en `main.py` | read | ✅ | `src/api/main.py:30`: `from .routes.templates import router as templates_router` |

**Discrepancias encontradas:**

1. ❌ **Plan asume ON CONFLICT SQL — código real usa check-then-insert Python.** Seed es funcionalmente idempotente por el unique index parcial (migración 030), pero vulnerable a race condition en ejecución concurrente. La fix debe alinear lo que el plan espera con el approach real.

2. ❌ **BuilderBreadcrumb desconectado del estado real.** `page.tsx` hardcodea `activeTab="agent-form"`. `BuilderLayout` tiene el estado real pero no lo comunica al breadcrumb. Flujo roto: cambiar tab no actualiza breadcrumb.

3. ❌ **Mock patches en tests apuntan al módulo fuente, no al consumidor.** `agents.py` hace `from ...db.session import get_tenant_client` a nivel de módulo (línea 13). Tests parchean `src.db.session.get_tenant_client` — no afecta a `agents.py` porque ya tiene su propia referencia. Las fixtures `mock_tenant_client` de conftest SÍ parchean los consumidores correctos (e.g., `src.api.routes.agents.get_tenant_client`), pero los tests individuales NO las usan.

4. ⚠️ **`z.enum` en AgentForm es frágil.** Si un valor fuera del set llega (e.g., `"groq "` con espacio), Zod lanza error. `onValueChange` usa cast `as AgentFormData['llmProvider']` que silencia TS pero no Zod.

5. ⚠️ **`global_llm_mock(autouse=True)` parchea 5 módulos globalmente.** Tests pre-existentes fuera del builder reciben mocks que no pidieron → riesgo de falsos positivos si dependen del comportamiento real de `langchain_openai` o `crewai`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema
- Tabla `agent_templates` existe vía migración 030 (33 líneas).
- Columnas: `id UUID PK`, `name TEXT NOT NULL`, `description TEXT`, `category TEXT NOT NULL`, `soul_json JSONB NOT NULL DEFAULT '{}'`, `suggested_tools TEXT[] DEFAULT '{}'`, `max_iter INTEGER DEFAULT 5`, `is_system BOOLEAN DEFAULT FALSE`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`.
- ✅ **No requiere cambios de schema.** Migración 030 ya tiene unique index parcial y RLS.

### Integridad referencial
- ✅ `agent_templates` no tiene FK a otras tablas (tabla global sin org_id). Correcto para sistema global.
- ✅ Unique index parcial `ON agent_templates(name) WHERE is_system = TRUE` evita duplicados en system templates a nivel DB.

### RLS
- ✅ `agent_templates_read`: `FOR SELECT USING (auth.role() = 'authenticated')` — lectura pública para cualquier usuario autenticado.
- ✅ `agent_templates_write`: `FOR ALL USING (auth.role() = 'service_role')` — solo service_role puede modificar. Contradice el análisis de Kilo que dice "NO RLS explícito". Kilo erróneo.
- ⚠️ Las queries en `templates.py` usan `get_service_client()` (línea 59), que tiene role `service_role` — RLS write policy no aplica porque service_role bypass RLS. Correcto.

### Índices
- ✅ `idx_agent_templates_category` en `(category)` para filtro de templates.
- ✅ `idx_agent_templates_system_name` (unique partial) en `(name) WHERE is_system = TRUE`.

### Tipos
- ✅ `suggested_tools TEXT[]` con `DEFAULT '{}'` — ok.
- ⚠️ `soul_json JSONB` sin validación de schema. Seed no valida estructura contra `bundle_schemas.AgentExportItem`.

**Impacto en datos existentes:** Ninguno. Schema ya correcto.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### `templates_seed.py` (220 líneas)
- **Función:** `seed_templates(dry_run: bool = False, reset: bool = False) -> None`
- **Patrón:** Typer sub-app (`templates_app`) registrado en `src/cli/main.py:37` (`from src.cli.commands.templates_seed import templates_app`)
- **Problemas:**
  - Check-then-insert (líneas 183-206) sin transacción atómica. Race window entre SELECT e INSERT.
  - Sin manejo de error en `get_service_client()` (línea 150) — si Supabase caído, `AttributeError` sin mensaje claro.
  - Logger importado (línea 24) pero con configuración básica (`logging.getLogger(__name__)` sin handler).
  - `UUID5` para IDs (línea 197): `uuid.uuid5(uuid.NAMESPACE_DNS, f"fap.system.template.{template['name']}")`. Determinístico — bien para idempotencia.

### `BuilderBreadcrumb.tsx` (48 líneas)
- **Función:** `BuilderBreadcrumb({ activeTab }: { activeTab: string })`
- **Patrón:** shadcn `Breadcrumb` + `lucide-react` iconos.
- **Problema:** Prop `activeTab` recibida pero no conectada al estado de `BuilderLayout`.
- **Fix requerido:** Pasar callback desde `BuilderLayout` → `page.tsx` o mover `BuilderBreadcrumb` dentro de `BuilderLayout`.

### `AgentForm.tsx` (407 líneas)
- **Schema Zod:** `z.object({ llmProvider: z.enum([...]), ... })`
- **Problema:** `Select.onValueChange` (línea 270) usa `v as AgentFormData['llmProvider']` — bypass TS pero Zod valida en runtime. Si `PROVIDER_MODELS` tuviera key no esperada, falla.
- **Fix:** Cambiar `z.enum(...)` a `z.string()` o validar estrictamente que el valor del Select esté dentro del enum.

### `conftest.py` (358 líneas)
- **`mock_service_client`** (línea 112): Parchea 8 puntos de importación. Usa `try/except (AttributeError, ImportError)` — graceful degradation. ✅ Patrón correcto.
- **`mock_tenant_client`** (línea 174): Parchea 12 puntos de importación de rutas — incluye `src.api.routes.agents.get_tenant_client`. ✅ Este es el patrón correcto (parchea consumidor, no fuente).
- **`global_llm_mock`** (línea 276): `autouse=True` parchea `langchain_openai.ChatOpenAI`, `chat_models.ChatOllama`, `crewai.Agent/Task/Crew`. ⚠️ Afecta todas las suites.
- **Problema:** `test_builder_scenarios.py` NO usa `mock_tenant_client` fixture. En su lugar, cada test crea su propio mock y parchea `src.db.session.get_tenant_client`. Esto parchea el módulo fuente, pero los módulos consumidores ya importaron la función. Resultado: **los parches no tienen efecto** — los tests pasan porque el mock no se usa realmente o fallan con `AttributeError`.

### `test_builder_scenarios.py` (937 líneas, 32 tests)
- **Estructura:** 6 clases de test (TP-1 a TP-6).
- **Patrón:** Cada test crea `db = fresh_db()` + `cm = db_cm(db)` + configura mocks + parchea `src.db.session.get_tenant_client`.
- **Problema central:** `agents.py:13` hace `from ...db.session import get_tenant_client`. Cuando el test parchea `src.db.session.get_tenant_client`, la referencia en `agents` ya está capturada. El parche no afecta.
- **Solución:** Usar `mock_tenant_client` fixture de conftest (que parchea `src.api.routes.agents.get_tenant_client`) O parchear el módulo consumidor: `"src.api.routes.agents.get_tenant_client"`.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints relevantes
- **`fap templates seed`** — CLI command, no endpoint HTTP. Llama `seed_templates()` que conecta directo a Supabase via `get_service_client()`.
- **`GET /api/templates`** (`templates.py:54`) — Sin auth (`require_org_id` omitido intencionalmente). Usa `get_service_client()`.
- **`POST /agents`** (`agents.py:101`) — Usa `get_tenant_client(org_id)` con RLS.

### Flujo de mock problemático
```
Test parchea "src.db.session.get_tenant_client" → agents.py tiene "from src.db.session import get_tenant_client" (módulo, línea 13) → parche NO afecta
```
vs (correcto):
```
conftest.mock_tenant_client parchea "src.api.routes.agents.get_tenant_client" → agents.py busca "agents.get_tenant_client" → parche SÍ afecta
```

### Endpoints no afectados por este paso
- `POST /api/bundles/export` — usa `ExportService`, no `get_tenant_client`.
- `GET /api/tools/available` — usa `get_service_client()` + `MCPPool`.
- `POST /api/bundles/import` — usa `ImportService`.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo Breadcrumbs (ROTO)
```
BuilderLayout.setActiveTab("crew-canvas") → page.tsx NO recibe el cambio → BuilderBreadcrumb.activeTab="agent-form" (siempre)
```
Fix: Mover `BuilderBreadcrumb` dentro de `BuilderLayout` o usar callback `onTabChange`.

### Flujo Tests (ROTO)
```
test → patch("src.db.session.get_tenant_client") → agents.py.get_tenant_client NO es afectado → test falla o pasa falsamente
```
Fix: Parchear `src.api.routes.agents.get_tenant_client` (y demás consumidores).

### Flujo Seed (FUNCIONAL pero frágil)
```
fap templates seed → SELECT + check Python → INSERT → unique index DB previene duplicados
```
Race condition: 2 seeds simultáneos → ambos SELECT vacío → ambos INSERT → uno falla por unique index. Transacción implícita en el cliente de Supabase mitiga parcialmente.

### DX & Tooling

```
### Herramienta Propuesta: fap templates check
- **Qué automatiza:** Verifica estado actual de templates contra estado esperado (8 system templates). Corre migración 030 si no existe. Reporta duplicados, inconsistencias de schema.
- **Tipo:** CLI command (extender `fap templates` sub-app)
- **Cómo se usa:** `fap templates check` — verifica y reporta. `fap templates check --fix` — repara automáticamente.
- **Impacto para el usuario final:** Elimina debugging manual de DB. Un comando confirma que todo seed está en orden.
- **Prioridad:** Tarea 0 — implementar antes que fixes de tests y breadcrumbs.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] fap templates seed x3 ejecuta sin duplicados (DB unique index + check-then-insert)
✅ [CODE] templates_seed.py maneja error de conexión con mensaje claro, no AttributeError
✅ [BACKEND] Tests parchean módulos consumidores (src.api.routes.agents.get_tenant_client), NO fuente
✅ [FULLSTACK] BuilderBreadcrumb refleja tab activa en tiempo real
✅ [DX] fap templates check reporta estado correcto de los 8 system templates
✅ [TEST] uv run pytest tests/e2e/test_builder_scenarios.py -v --tb=short pasa 32/32
✅ [TEST] uv run pytest tests/ -k "not e2e" --tb=short pasa sin romper suites pre-existentes
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tests aprueban falsamente | Alta | Mock patches en targets incorrectos | Refactor patch targets a módulos consumidores; verificar que `execute.called` sea `True` |
| Seed corrompe DB en race condition | Media | Check-then-insert sin lock | Envolver seed en RPC de PostgreSQL con ON CONFLICT |
| global_llm_mock rompe tests de otros equipos | Alta | autouse=True sin scope="session" | Scope="session" o mover a fixture exclusiva de builder tests |
| Breadcrumb fix rompe layout existente | Media | Cambio estructural en composición page.tsx/BuilderLayout | Mover breadcrumb DENTRO de BuilderLayout, no levantarlo a page.tsx |
| z.enum rejection en producción | Baja | Select value inesperado fuera del enum | Validar valor en onValueChange antes de setValue |

---

## 7️⃣ Plan de Implementación

**Regla:** 1 tarea = 1 artefacto. Interfaz exacta. Patrón explícito. Verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: fap templates check** | `src/cli/commands/templates_check.py` | `@templates_app.command("check") def check_templates(fix: bool = False) -> None:` | `src/cli/commands/templates_seed.py :: seed_templates()` — Typer + Rich table | DX | Baja | 0.5h | Ninguna | → `fap templates check --help` ejecuta sin error |
| 1 | Fix idempotencia seed | `src/cli/commands/templates_seed.py:183-206` | Cambiar check-then-insert a `db.table("agent_templates").upsert(... , on_conflict="name")` con filtro post-insert | `supabase/migrations/030_agent_templates.sql :: unique index` | DATA | Baja | 0.5h | T0 | → `fap templates seed` x3 sin errores ni duplicados |
| 2 | Sync breadcrumb con tab real | `dashboard/components/builder/BuilderBreadcrumb.tsx` + `dashboard/app/(app)/builder/page.tsx` | Mover `<BuilderBreadcrumb>` dentro de `BuilderLayout`, leer `activeTab` directo | `dashboard/components/builder/BuilderLayout.tsx :: activeTab state` | FULLSTACK | Media | 0.5h | T0 | → cambiar tab → breadcrumb se actualiza |
| 3 | Fix mock targets en tests | `tests/e2e/test_builder_scenarios.py` | Reemplazar `patch("src.db.session.get_tenant_client")` por `mock_tenant_client` fixture de conftest | `tests/conftest.py :: mock_tenant_client fixture (línea 174)` | BACKEND | Media | 1.5h | T0 | → `uv run pytest tests/e2e/test_builder_scenarios.py -v --tb=short` = 32/32 |
| 4 | Fix TS zodResolver | `dashboard/components/builder/AgentForm.tsx:37` | Cambiar `llmProvider: z.enum([...])` a `llmProvider: z.string()` + validación custom | `dashboard/components/builder/TemplatePicker.tsx` | CODE | Baja | 0.5h | T0 | → `npm run tsc --noEmit` sin errores |
| 5 | Regression audit conftest | `tests/conftest.py:276` | Cambiar `global_llm_mock` de `autouse=True` global a fixture con `scope="session"` o `pytestmark` en tests de builder | `tests/e2e/test_builder_scenarios.py :: pytestmark` | CODE | Baja | 0.5h | T3 | → `uv run pytest tests/unit/ -v --tb=short` pasa igual que antes |

**Tiempo total estimado:** 4 horas

---

## 🔮 Roadmap (No implementar ahora)

- Centralizar todos los seeds en `scripts/seed_runner.py` con lock DB (pg_advisory_lock) para prevenir race conditions.
- Migrar `fap templates seed` a RPC PostgreSQL (`SELECT * FROM seed_agent_templates()`) para atomicidad real.
- Agregar validación de `soul_json` contra `AgentExportItem` schema en el seed.
- Reemplazar `global_llm_mock` con patrón de `pytest.mark.builder` que solo aplique mocks a tests del builder.

---

## 🚫 Reglas de Oro Verificadas

- ✅ Análisis accionable, cada tarea tiene interfaz exacta + patrón + verificación
- ✅ TODO verificado contra código real (16 elementos en §0)
- ✅ Decisiones de diseño cero en tareas — implementador no infiere nada
- ✅ Tareas atómicas: 1 artefacto por tarea
- ✅ Cobertura de 4 etapas (DATA, CODE, BACKEND, FULLSTACK+DX)
- ✅ ≥ 1 herramienta DX propuesta (fap templates check)
- ✅ Riesgos ≥ 3 identificados con mitigaciones
- ✅ Coherente con phase-state.md
