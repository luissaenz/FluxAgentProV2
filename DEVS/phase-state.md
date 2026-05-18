# 🗺️ Contexto de Fase — FluxAgentPro-v2

> **Documento fuente de verdad para todos los agentes.** Verificado contra código real.

---

## 1. Resumen de Fase

**Fase activa:** `guiAgentGenerator` — ✅ **COMPLETADA** (15/15 pasos completados)
**Objetivo:** Replicar experiencia de creación visual de agentes (Crew Studio) dentro del dashboard FAP, sobre stack propio (Next.js + ReactFlow + FastAPI + Supabase).

### Pasos en orden

| # | Paso | Estado |
|---|------|--------|
| 1 | Crear endpoint `GET /api/tools/available` | ✅ Completado |
| 2 | Crear endpoint `POST /api/bundles/export` | ✅ Completado |
| 3 | Endpoints CRUD para templates de agentes | ✅ Completado |
| 4 | Builder visual — UI con ReactFlow | ✅ Completado |
| 5 | Template Picker — librería de templates | ✅ Completado |
| 6 | Agent Playground — prueba en tiempo real | ✅ Completado |
| 7 | Canvas visual — ensamblaje de crews | ✅ Completado |
| 8 | ExportDialog + flujo completo de exportación | ✅ Completado |
| 9 | Navegación, breadcrumbs e integración | ✅ Completado |
| 10 | Tests E2E del builder | ✅ Completado |
| 11 | Estabilización Crítica y Fixes de Arquitectura | ✅ Completado |
| 12 | Protocolo de Validación y Dogfooding E2E | ✅ Completado |
| 13 | Robustez y Refactorización del Backend (DX) | ✅ Completado |
| 14 | Optimización de UX y Rendimiento Frontend | ✅ Completado |
| 15 | Expansión de Cobertura y DX de Tests | ✅ Completado |

### Dependencias entre pasos
- Paso 2 requiere Paso 1 (tools list para export)
- Paso 4 requiere Pasos 1-3 (tools + export + templates para builder)
- Paso 6 requiere Paso 4 (AgentForm creado con `onRoleChange`) + `POST /agents/{role}/run` existente
- Paso 7 requiere Paso 4 (AgentForm + BuilderLayout) + `GET /agents` + `POST /bundles/export` existentes
- Paso 8 requiere Paso 2 (`POST /api/bundles/export` existente) + Paso 7 (CrewCanvas con `canvasToExportPayload()`) + Paso 4 (AgentForm con campos completos)
- Paso 9 requiere Pasos 4, 7 y 8 (integración de componentes navegación en rutas existentes)
- Paso 10 requiere Pasos 4, 6, 7 y 8 (escenarios de integración para todas las piezas del builder)
- Paso 11 requiere los Pasos 9 y 10 para corregir bugs de inyección de mocks, tipado en frontend, e idempotencia del seed de templates.
- Paso 12 requiere Pasos 1-11 (usa endpoints, CLI commands, y scripts existentes para validación E2E cruzada).
- Paso 13 requiere Pasos 1-12 (refactoriza código existente de backend y CLI; no crea funcionalidad nueva).
- Paso 14 requiere Pasos 1-13 (optimiza componentes y hooks existentes del frontend builder; no crea funcionalidad nueva).
- Paso 15 requiere Pasos 1-14 (añade tests unitarios, tooling de cobertura, y consolida mocks; no crea funcionalidad nueva).

---

## 2. Estado Actual del Proyecto

> Verificado contra código fuente en `src/` y `supabase/migrations/`.

### ✅ Implementado y funcional

| Componente | Archivo | Línea | Notas |
|---|---|---|---|
| CLI `fap templates seed` | `src/cli/commands/templates_seed.py` | `seed_templates` | Semilla idempotente por UUID v5 y con check preventivo de tabla |
| CLI `fap doctor builder` | `src/cli/commands/doctor_builder.py` | `doctor_builder` | Suite de 6 diagnósticos críticos automatizados con formato visual *Rich* |
| CLI `fap doctor backend` | `src/cli/commands/doctor_backend.py` | `doctor_backend` | Suite de 8 checks de salud del backend (tipado, sync doc-código, event loop, constantes, AsyncClient, emojis, typer.Option, DB sync). Comando: `uv run fap doctor backend --org-id <uuid>` |
| CLI `fap test builder` | `src/cli/commands/test_builder.py:31` | `test_builder_app` registrado en `main.py` | Ejecuta suite E2E + reporte HTML |
| Suite Escenarios E2E | `tests/e2e/test_builder_scenarios.py` | 32 tests (TP-1 a TP-6) | 938 líneas, usa `TestClient` para validar integridad |
| `BuilderTabContext` / Provider | `dashboard/components/builder/BuilderTabContext.tsx` | Context API | Mantiene el estado global de la pestaña seleccionada en el Builder |
| `BuilderBreadcrumb` component | `dashboard/components/builder/BuilderBreadcrumb.tsx` | Breadcrumbs contextuales para el Builder | Sincronizado dinámicamente mediante Context API |
| `BuilderErrorBoundary` component | `dashboard/components/builder/BuilderErrorBoundary.tsx` | Class component para ReactFlow | Captura fallos SSR y de ReactFlow |
| Mocks Globales Estabilizados | `tests/e2e/conftest.py` | Fixture `global_llm_mock` | Aislado a la suite E2E para evitar regresiones de tests unitarios |
| Validación de Mocks en Tests | `scripts/validate_builder_mocks.py` | Checks de patching | Asegura que los parches de base de datos apunten a los namespaces correctos |
| CLI `fap dogfood check` | `src/cli/commands/dogfood_check.py` | `dogfood_check` registrado en `main.py` | Orquestador unificado de 7 validaciones E2E con reporte Rich + JSON para CI/CD. Flags: `--org-id`, `--json`, `--dry-run`. Migrado a `httpx.AsyncClient` para consistencia async. |
| Script `validate_builder_nav.py` (corregido) | `scripts/validate_builder_nav.py` | 11 checks críticos de UI | Correcciones aplicadas: regex reparado (D2), variable `uses_navmain` usada en decision (D1), check SSR mejorado para verificar `BuilderCanvas.tsx` con `dynamic()` + `ssr: false` (D3 mejorada). Exit code 0. |
| `AgentResponse.created_at` obligatorio | `src/api/routes/agents.py:35` | `created_at: str` | Alineado con DB (NOT NULL DEFAULT now()). Backward-compatible. |
| SELECT con `created_at` en `list_agents` | `src/api/routes/agents.py:78` | `.select("id, role, soul_json, allowed_tools, max_iter, created_at")` | D2 crítico: sin esto AgentResponse fallaba |
| `.select("*")` tras UPDATE en agents | `src/api/routes/agents.py:142` | `.update({...}).eq("id", ...).select("*")` | Garantiza que `created_at` se retorna post-update |
| 503 handling en agents endpoints | `src/api/routes/agents.py:84-86,169-171,220-222` | 3 bloques try/except → HTTPException(503) | `GET /agents`, `POST /agents`, `GET /agents/{id}/detail` |
| CLI `fap agent run` async | `src/cli/commands/agent_run.py` | `_run_agent_async` + `asyncio.run()` wrapper | Migrado de `httpx.Client` sync a `httpx.AsyncClient` |
| CLI `fap crew save` async | `src/cli/commands/crew.py` | `_save_crew_async` + `asyncio.run()` wrapper | Migrado de `httpx.Client` sync a `httpx.AsyncClient` |
| Constantes centralizadas | `src/services/bundle_schemas.py:12-15` | `MIN_GOAL_LENGTH`, `MIN_BACKSTORY_LENGTH`, `MAX_FLOWS_PER_BUNDLE`, `MAX_SKILLS_PER_BUNDLE` | Importadas por `bundle_validate_payload.py`, `bundles.py`, `bundle_manager.py` |
| Hook `useClickOutside` | `dashboard/hooks/useClickOutside.ts` | `export function useClickOutside(ref, handler, enabled?)` | Hook reutilizable extraído de ToolMultiSelect. Usado en ToolMultiSelect, TemplatePicker. |
| Hook `useDebounce` | `dashboard/hooks/useDebounce.ts` | `export function useDebounce<T>(value, delay)` | Hook genérico de debounce. Usado en ToolMultiSelect (300ms) y TemplatePicker (300ms) para filtrado. |
| Módulo `template-mapper.ts` | `dashboard/lib/template-mapper.ts` | `mapTemplateToFormValues(template): AgentFormData` | Función pura extraída de BuilderLayout. Mapea TemplateDetail → AgentFormData con defaults seguros. |
| `HTTP_METHODS` + `MAX_EXPORT_AGENTS` | `dashboard/lib/constants.ts:27-35` | `HTTP_METHODS = { GET, POST, ... } as const; MAX_EXPORT_AGENTS = 15` | Constantes centralizadas eliminando strings mágicos en api.ts y hardcodeo `15` en ExportDialog. |
| `fapDownload` flexible | `dashboard/lib/api.ts:55,74` | `fapDownload(path, body, method?)` | Parámetro `method` opcional (default `'POST'`). Usa `HTTP_METHODS.POST` como default. |
| BuilderTabContext sync con URL | `dashboard/components/builder/BuilderTabContext.tsx` | `useSearchParams()` + `useRouter.replace()` | Sincronización bidireccional tabs↔URL `?tab=agent-form|crew-canvas`. Deep linking funcional. |
| Script `perf-audit.ts` | `scripts/perf-audit.ts` | `npx tsx scripts/perf-audit.ts --path <dir>` | Escaneo estático de regresiones de performance en TSX del builder. |
| Comando `fap coverage report` | `src/cli/commands/coverage_report.py` | `fap coverage report` | Ejecuta pytest con --cov --report=json, parsea resultados por módulo, muestra tabla Rich con status por umbral. Flags: `--module`, `--threshold`, `--html`, `--diff`. |
| Flag `--cov` en `fap test builder` | `src/cli/commands/test_builder.py:55` | `fap test builder run --cov` | Añade --cov=src a pytest y muestra tabla de cobertura después de tests. |
| Tests unitarios tools.py | `tests/unit/test_tools.py` | 8 tests | Cubre: lista vacía, tools locales, filtro source local/mcp, filtro category, inclusión MCP, graceful degradation MCP, count coincide. |
| Schema Zod extraído | `dashboard/lib/agent-schema.ts` | `agentFormSchema` + `AgentFormData` | Schema extraído de AgentForm.tsx a módulo compartido. Testeable sin React. |
| Test script schema Zod | `scripts/test-agent-schema.mjs` | `node scripts/test-agent-schema.mjs` | 12 tests de validación del schema (role, goal, backstory, maxIter, toggles, defaults, allowedTools). |
| Helpers mock centralizados | `tests/conftest.py` | `mock_db()`, `mock_db_filter()`, `mock_db_single()` | Migrados desde test_templates.py. Usados por test_templates.py y test_builder_scenarios.py. |
| test_3_5_latency.py estabilizado | `tests/integration/test_3_5_latency.py` | Skip graceful sin credenciales | Fixture `supabase_client` salta con pytest.skip si Supabase no está disponible, en vez de fallar con 500. Imports protegidos con try/except. |
| AgentPlayground scroll corregido | `dashboard/components/builder/AgentPlayground.tsx:180` | `<div ref={scrollRef} className="flex-1 overflow-y-auto">` | Reemplazo de ScrollArea Radix por div nativo para scroll automático confiable. |
| CSS ReactFlow dinámico | `dashboard/components/builder/CrewCanvas.tsx:86-89` | `useEffect(() => { import('reactflow/dist/style.css') }, [])` | Carga diferida de CSS de ReactFlow (antes import estático bloqueante). |

*(Para componentes previos 1..8, ver histórico en DEVS/IMPLEMENTED)*

---

## 3. Contratos Técnicos Vigentes

### Stack detectado
- **Backend:** Python ≥3.12 + FastAPI (Pydantic v2)
- **Frontend:** TypeScript + Next.js (`dashboard/`)
- **DB:** Supabase (PostgreSQL) vía `supabase` Python client

### Modelos de datos (de migraciones reales)
- `agent_catalog(id UUID, org_id UUID, role TEXT, goal TEXT, backstory TEXT, llm_provider TEXT, llm_model TEXT, max_iter INTEGER, allowed_tools TEXT[], verbose BOOLEAN, reasoning BOOLEAN, inject_date BOOLEAN, memory BOOLEAN, is_active BOOLEAN, created_at TIMESTAMP WITH TIME ZONE)`
- `workflow_templates(id UUID, org_id UUID, flow_type TEXT, definition JSONB, created_at TIMESTAMP WITH TIME ZONE)`
- `agent_templates(id UUID, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INTEGER, is_system BOOLEAN, created_at TIMESTAMP WITH TIME ZONE)`

### Endpoints / APIs (rutas reales)
| Ruta | Método | Archivo | Auth | 503 handling |
|---|---|---|---|---|
| `/api/tools/available` | GET | `src/api/routes/tools.py` | `require_org_id` | No |
| `/api/bundles/export` | POST | `src/api/routes/bundles.py` | `require_org_id` | No |
| `/api/templates` | GET | `src/api/routes/templates.py` | ninguno (publico) | Sí |
| `/api/templates/{id}` | GET | `src/api/routes/templates.py` | ninguno (publico) | Sí |
| `/agents` | GET | `src/api/routes/agents.py` | `require_org_id` | Sí |
| `/agents` | POST | `src/api/routes/agents.py` | `require_org_id` | Sí |
| `/agents/{agent_id}/detail` | GET | `src/api/routes/agents.py` | `require_org_id` | Sí |
| `/agents/{role}/run` | POST | `src/api/routes/agents.py` | `require_org_id` | No |

### Patrones de código en uso

**1. Patrón E2E Integration (Backend)**
```python
# tests/e2e/test_builder_scenarios.py
with TestClient(app) as client:
    response = client.post("/agents", json=payload, headers=headers)
```

**2. Patrón Error Boundary (Frontend)**
```tsx
// dashboard/components/builder/BuilderErrorBoundary.tsx
export class BuilderErrorBoundary extends Component<Props, State> { ... }
```

**3. Idempotencia en Semillas (Sembrado Seguro):**
```python
# src/cli/commands/templates_seed.py
row = {
    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fap.system.template.{template['name']}")),
    ...
}
result = db.table("agent_templates").upsert(row, on_conflict="id", ignore_duplicates=True).execute()
```

**4. Patrón AsyncClient en CLI (Paso 13):**
```python
# src/cli/commands/agent_run.py — funciones async internas + wrapper sync
async def _run_agent_async(...) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json=payload, headers=headers)

def run_agent(...) -> None:
    ...
    asyncio.run(_run_agent_async(...))
```

**5. Patrón 503 en endpoints (Paso 13):**
```python
# src/api/routes/templates.py:59-67, agents.py:84-86,169-171,220-222
try:
    db = get_service_client()
    result = db.table(...).select(...).execute()
except Exception as exc:
    logger.error("DB error: %s", exc)
    raise HTTPException(503, "Database unavailable") from exc
```

**6. Patrón Hooks DX reutilizables (Paso 14):**
```typescript
// dashboard/hooks/useClickOutside.ts — extraído de lógica inline en ToolMultiSelect
export function useClickOutside(ref: RefObject<HTMLElement | null>, handler: () => void, enabled?: boolean): void {
  useEffect(() => {
    if (enabled === false) return
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) handler()
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [ref, handler, enabled])
}

// dashboard/hooks/useDebounce.ts — hook genérico
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debouncedValue
}
```

**7. Patrón Coverage Report CLI (Paso 15):**
```python
# src/cli/commands/coverage_report.py — wrapper pytest --cov + Rich table
def _run_coverage(...) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "pytest", "--cov=src", "--cov-report=json", ...]
    result = subprocess.run(cmd, ...)
    # Parse coverage.json → módulos con statements/covered/percent/pass
    return cov_data

@coverage_app.command("report")
def coverage_report(module=None, threshold=75.0, html=False, diff=False):
    cov_data = _run_coverage(module=module, threshold=threshold, html=html)
    _render_table(cov_data, threshold, diff=diff)
```

**8. Patrón Schema Zod extraído + tests Node.js (Paso 15):**
```typescript
// dashboard/lib/agent-schema.ts — schema puro sin dependencia React
export const agentFormSchema = z.object({ ... })
export type AgentFormData = z.infer<typeof agentFormSchema>

// scripts/test-agent-schema.mjs — valida schema con Node.js
// node scripts/test-agent-schema.mjs
// 12 tests: valid payload, empty role, short goal, short backstory, maxIter bounds, toggles, defaults, allowedTools
```

---

## 4. Decisiones de Arquitectura Tomadas

| Decisión | Detalle | Verificación |
|---|---|---|
| **Idempotencia por PK (`id`) en Semillas** | Se reemplazó el upsert por `name` por un upsert directo hacia el PK `id` (UUID v5 determinista). Esto resolvió el error de base de datos `42P10` generado por la indexación parcial `WHERE is_system = TRUE`. | `templates_seed.py` |
| **Control Preventivo en CLI** | El comando de seed valida proactivamente que la tabla exista mediante una consulta ultra-rápida (`select.limit(1)`) antes de proceder, optimizando el DX operativa. | `templates_seed.py` |
| Breadcrumbs Reactivos | Sincronizados con el estado de las pestañas mediante Context API (`BuilderTabContext`), no con rutas físicas. | `BuilderBreadcrumb.tsx` |
| Testing sin Navegador | Uso de `TestClient` para validar lógica de negocio sin overhead de Playwright. | `test_builder_scenarios.py` |
| Dogfooding Tooling | El implementador debe usar `fap test builder` para verificar integridad. | `src/cli/commands/test_builder.py` |
| **Aislamiento en Mocks E2E** | La fixture `global_llm_mock` se encapsuló en `tests/e2e/conftest.py` en lugar de la raíz global de tests, previniendo falsos positivos en las suites unitarias del núcleo de la aplicación. | `tests/e2e/conftest.py` |
| **Validación Orquestada Unificada** | Un solo comando `fap dogfood check` centraliza 7 flujos de validación (doctor, seed, HTTP-vs-CLI, dry-run, agent create, bundle validate, UI integrity). Descarta scripts dispersos como `dogfood_validator.py`. | `dogfood_check.py` |
| **Validación Cruzada HTTP vs CLI** | `fap dogfood check` consume endpoints REST reales (`GET /api/tools/available`, `POST /agents`) vía `httpx` y compara estructuralmente contra respuestas locales para detectar desincronización de contratos. | `dogfood_check.py:111-150` |
| **SSR Check mejorado sobre FINAL (D3)** | La corrección D3 del análisis recomendaba buscar `CrewCanvas` en `BuilderLayout.tsx`, pero el componente real es `BuilderCanvas`. El implementador corrigió la premisa: verifica `BuilderCanvas.tsx` para confirmar `dynamic(CrewCanvas, { ssr: false })`. | `validate_builder_nav.py:163-200` |
| **`AgentResponse.created_at` obligatorio (Paso 13, D1+D2)** | Se cambió de `Optional[str]` a `str` obligatorio, alineando Pydantic con DB (NOT NULL). Se agregó `created_at` a todos los SELECT y `.select("*")` tras UPDATE para evitar errores de serialización. | `agents.py:35,78,142` |
| **`httpx.AsyncClient` como estándar en CLI (Paso 13, D6)** | Todos los comandos CLI que consumen API HTTP migrados de `httpx.Client` sync a `httpx.AsyncClient` con `asyncio.run()` wrapper. Consistencia con backend async. Afecta: `agent_run.py`, `crew.py`, `dogfood_check.py`. | `agent_run.py`, `crew.py`, `dogfood_check.py` |
| **Constantes centralizadas en `bundle_schemas.py` (Paso 13, D7+D10+D11)** | `MIN_GOAL_LENGTH`, `MIN_BACKSTORY_LENGTH`, `MAX_FLOWS_PER_BUNDLE`, `MAX_SKILLS_PER_BUNDLE` definidas en un solo lugar. Importadas por `bundle_validate_payload.py`, `bundles.py`, `bundle_manager.py`. Elimina hardcodeo en 3 archivos. | `bundle_schemas.py:12-15` |
| **Herramienta DX: `fap doctor backend` (Paso 13, T0)** | 8 checks de salud del backend: tipado estricto, sync doc-código, salud de event loop, procedencia de constantes, cobertura AsyncClient, CLI sin emojis, estilo typer.Option, sync DB-modelos. Uso: `uv run fap doctor backend --org-id <uuid>`. | `doctor_backend.py` |
| **Hooks DX bundle: `useClickOutside` + `useDebounce` (Paso 14, T0)** | Hooks reutilizables para click-outside y debounce. Eliminan lógica inline repetitiva (~10 líneas/componente). Usados en ToolMultiSelect y TemplatePicker (dogfooding). | `useClickOutside.ts`, `useDebounce.ts` |
| **`cmdk` pospuesto (Paso 14)** | El plan sugería evaluar migración a `cmdk`. 7/7 agentes de análisis confirmaron que no está instalado. El ToolMultiSelect actual (60 líneas, useMemo) funciona correctamente. `cmdk` añadiría ~15KB sin beneficio inmediato. Re-evaluar si se necesita Command Palette global. | `package.json` |
| **Memoización selectiva en CrewCanvas (Paso 14)** | Solo se memoizan `duplicatedRoles`, `nodesWithWarnings`, `sidebarAgents` (iteran arrays, O(n)). `hasAgentNodes` y `exportDisabled` son O(1) — no justifican overhead de `useMemo`. | `CrewCanvas.tsx:343-369` |
| **Sincronización tabs↔URL con `router.replace` (Paso 14)** | Usar `replace` evita acumular entradas en historial del navegador por cada cambio de pestaña. El botón "atrás" lleva a la página anterior al builder, no a la pestaña anterior. | `BuilderTabContext.tsx:52` |
| **`<div>` nativo reemplaza `<ScrollArea>` Radix en AgentPlayground (Paso 14)** | ScrollArea encapsula viewport real, haciendo scroll manual inestable. `<div>` con `overflow-y-auto` da control directo y predecible. | `AgentPlayground.tsx:180` |
| **`fap coverage report` como DX tool (Paso 15, T0)** | Comando CLI que ejecuta pytest con --cov, parsea coverage.json y muestra tabla Rich por módulo. Evita correr pytest con flags manualmente y parsear output. | `coverage_report.py` |
| **NO instalar Vitest/testing-library (Paso 15, T2)** | Setup completo requiere ~8h. Se escala a tests de schema Zod como funciones puras TypeScript via Node.js. Schema extraído a `lib/agent-schema.ts`. Post-MVP puede añadirse. | `agent-schema.ts`, `test-agent-schema.mjs` |
| **Mock helpers centralizados (Paso 15, T4)** | `mock_db()`, `mock_db_filter()`, `mock_db_single()` movidos de test_templates.py a tests/conftest.py. Evita duplicación en futuros tests. | `conftest.py` |
| **test_3_5_latency.py skip graceful (Paso 15, T3)** | Fixture `supabase_client` skip con pytest.skip si Supabase no está disponible. Imports protegidos con try/except. No modifica thresholds (son para entorno real). | `test_3_5_latency.py` |

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Notas |
|------|--------|----------------------|--------|-------|
| 01..08 | ✅ Completados | (Ver histórico) | (Ver histórico) | — |
| 09-Navegacion-breadcrumbs-integracion | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/09-Navegacion-breadcrumbs-e-integracion/` | `57a75de` | Integración del sidebar, skeletons y error boundaries para ReactFlow. |
| 10-Tests-E2E-del-builder | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/10-Tests-E2E-del-builder/` | `037deb9` | Suite de 32 escenarios pasando al 100% de éxito. |
| 11-Estabilizacion-Critica-y-Fixes-de-Arquitectura | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/11-Estabilizacion-Critica-y-Fixes-de-Arquitectura/` | `f56d9d7` | Resolución definitiva de error 42P10, sync dinámico de tabs y checks de mocks robustos. |
| 12-Protocolo-de-Validacion-y-Dogfooding-E2E | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/12-Protocolo-de-Validacion-y-Dogfooding-E2E/` | `e414bf1` | Comando `fap dogfood check` unificado. Script `validate_builder_nav.py` corregido (D1-D2-D3). Validación cruzada HTTP vs CLI. 9/9 criterios MVP. Validación APROBADA. |
| 13-Robustez-y-Refactorizacion-del-Backend-DX | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/13-Robustez-y-Refactorizacion-del-Backend-DX/` | `08daa11` | 11 correcciones del FINAL aplicadas. Herramienta DX `fap doctor backend` creada (8 checks). Migración a `httpx.AsyncClient` en CLI. Centralización de constantes. 503 handling en agents. 14/14 criterios MVP. Validación APROBADA. |
| 14-Optimizacion-de-UX-y-Rendimiento-Frontend | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/14-Optimizacion-de-UX-y-Rendimiento-Frontend/` | `31868ab` | 30/30 criterios MVP cumplidos. Hooks DX bundle (useClickOutside + useDebounce) creados con dogfooding verificado. Deep linking tabs↔URL implementado. CSS ReactFlow diferido. 9 optimizaciones de performance aplicadas (memoización, lazy loading, debounce, dynamic CSS). Memoización selectiva en CrewCanvas. Scroll corregido en AgentPlayground. Script perf-audit.ts para detección pre-commit de regresiones. 14/14 correcciones del FINAL aplicadas. Validación APROBADA. |
| 15-Expansion-de-Cobertura-y-DX-de-Tests | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/15-Expansion-de-Cobertura-y-DX-de-Tests/` | `d801edb` | Fase guiAgentGenerator COMPLETADA (15/15). DX Tooling `fap coverage report` creado con tabla Rich por módulo + flags --module/--threshold/--html/--diff. 8 tests unitarios para tools.py endpoint (lista, filtros, MCP graceful degradation). Schema Zod de AgentForm extraído a lib/agent-schema.ts con 12 tests de validación via Node.js. Flag --cov integrado en fap test builder. Helpers mock_db centralizados en conftest.py. test_3_5_latency.py estabilizado con skip graceful sin credenciales Supabase. |

---

## 6. Criterios Generales de Aceptación MVP

- ✅ Happy path funciona end-to-end (verificado vía CLI manual).
- ✅ Errores manejados sin crash.
- ✅ **Herramienta DX:** `fap test builder` funcional para ejecución de suite E2E.
- ✅ **Estabilidad de Semilla:** El comando `uv run fap templates seed` es 100% reutilizable de forma concurrente y segura.
- ✅ **Compilación Limpia:** `tsc --noEmit` y `ruff` pasan sin una sola falla.
- ✅ **DX Diagnóstico visual:** `fap doctor builder` provee visualización premium de 6 puntos de salud críticos.
- ✅ **Suite de tests verde:** 382 tests unitarios y 32 tests de integración/E2E ejecutándose con total éxito en entornos locales y pipelines. `fap test builder run --cov` incluye tabla de cobertura post-ejecución.
- ✅ **Dogfooding Automatizado:** `fap dogfood check` ejecuta 7 validaciones E2E en ~10 segundos con reporte Rich + salida JSON para CI/CD. Reduce verificación manual de 15 min a comando único.
- ✅ **Backend tipado consistente:** `AgentResponse.created_at` es `str` obligatorio, alineado con DB NOT NULL.
- ✅ **CLI asíncrono unificado:** Todos los comandos CLI que consumen API HTTP usan `httpx.AsyncClient` con `asyncio.run()` wrapper. Sin llamadas a `new_event_loop()`.
- ✅ **Constantes centralizadas:** Límites de validación en `bundle_schemas.py` — sin hardcodeo en `bundle_validate_payload.py`, `bundles.py` ni `bundle_manager.py`.
- ✅ **503 handling en agents:** Los 3 endpoints críticos (`GET /agents`, `POST /agents`, `GET /agents/{id}/detail`) retornan 503 si DB falla.
- ✅ **DX Tooling extendida:** `fap doctor backend` ejecuta 8 checks de salud del backend en ~5 segundos. Reduce verificación manual de 11 puntos a un comando.
- ✅ **Hooks DX bundle (Paso 14):** `useClickOutside` y `useDebounce` creados como hooks reutilizables. Usados en ToolMultiSelect y TemplatePicker (dogfooding). Eliminan lógica inline repetitiva.
- ✅ **Deep linking en Builder (Paso 14):** Tabs del builder sincronizadas con URL `?tab=agent-form|crew-canvas`. URL compartible. Refrescar página preserva pestaña activa.
- ✅ **CSS ReactFlow diferido (Paso 14):** CSS de ReactFlow cargado dinámicamente vía `useEffect` — no bloquea bundle principal. FCP no degradado.
- ✅ **Memoización selectiva (Paso 14):** 3 derivados memoizados en CrewCanvas (O(n)), 2 dejados sin memoizar (O(1)). 3 derivados memoizados en AgentForm. Zero `useMemo` innecesario.
- ✅ **Performance audit tool (Paso 14):** Script `perf-audit.ts` detecta regresiones de performance pre-commit. Detecta imports CSS síncronos, click-outside inline, y posible falta de memoización.
- ✅ **DX Tooling cobertura (Paso 15):** `fap coverage report` ejecuta pytest con --cov y muestra tabla Rich por módulo con status ✅/❌ por umbral. Reduce "pytest --cov + parsear output" a un comando.
- ✅ **Backend coverage tests (Paso 15):** 8 tests unitarios para `GET /api/tools/available` cubren lista vacía, filtros source/category, inclusión MCP, y graceful degradation. `uv run pytest tests/unit/test_tools.py -v` pasa 100%.
- ✅ **Schema Zod testeable (Paso 15):** Schema extraído a `lib/agent-schema.ts`. `node scripts/test-agent-schema.mjs` ejecuta 12 tests de validación sin React ni infraestructura frontend.
- ✅ **Mock consolidation (Paso 15):** Helpers `mock_db()`/`mock_db_filter()`/`mock_db_single()` centralizados en `tests/conftest.py`. test_templates.py y test_builder_scenarios.py importan desde ahí.
- ✅ **Latency test estabilizado (Paso 15):** test_3_5_latency.py salta gracefulmente sin credenciales Supabase. No falla en CI sin DB real.
- ✅ **Fase guiAgentGenerator COMPLETADA (Paso 15):** 15/15 pasos implementados, validados y archivados. Último commit: `d801edb`.
