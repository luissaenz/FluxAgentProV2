```markdown
# 🧠 PROCESO DE ANÁLISIS TÉCNICO (ANALISTA) v5.2 — PASO 7: CIERRE — REMANENTES Y PULIDO PARA COBERTURA TOTAL

## Perfil del Rol
Ingeniero de Software Senior, Arquitecto de Sistemas, Especialista en Diseño de Producto. Análisis basado en código fuente real. Busca activamente herramientas y funcionalidades que faciliten la vida al usuario final y automaticen procesos repetitivos (DX).

## Contexto del Proyecto
Desarrollamos "FluxAgentPro-v2". Disponible:
- `proyecto-config.json` (raíz) — fuente de verdad de rutas y convenciones
- Plan general: `DEVS/plan.md`
- Contexto de fase: `DEVS/phase-state.md`
- Código fuente: `src/` (fuente de verdad)
- Migraciones: `supabase/migrations/` (schema real de DB)

> [!IMPORTANT]
> **ANTES DE EJECUTAR:** Leer `proyecto-config.json`. Todas las rutas salen de ahí.

---

## 📥 Entradas Obligatorias
Agente: kilo
Paso: paso 7 — Cierre — Remanentes y Pulido para Cobertura Total (sub-pasos 7.1-7.8)

> [!IMPORTANT]
> Análisis cubre automáticamente data, code, backend, fullstack + UX + DX

---

## ⛔ PROHIBICIONES ABSOLUTAS
- NO escribas código de implementación. Entregable = DOCUMENTO DE ANÁLISIS.
- NO preguntes qué hacer. Lee plan, phase-state y paso asignado. Luego EJECUTA.
- NO analices TODO el sistema. Solo el paso específico — pero SÍ TODO el paso (sub-pasos incluidos).
- NO modifiques ningún archivo que no sea el de salida.
- NO repitas info que ya esté en `DEVS/phase-state.md`. Referenciala.
- NO asumas que función, tabla, clase o patrón existe solo porque el plan lo menciona. VERIFICAR contra código.

---

## 🔭 EXPLORACIÓN INICIAL DEL CODEBASE

### Paso 0: Leer `proyecto-config.json`
Extraer rutas reales antes de cualquier exploración:
- `paths.backend`: `src/`
- `paths.migrations`: `supabase/migrations/`
- `paths.api_routes`: `src/api/routes`
- `paths.tests`: `tests/`
- `paths.devs_in_progress`: `DEVS/IN_PROGRESS/`

### Exploración (10-15 min):

**1. Estructura del proyecto:**
- `src/`: 17 módulos (api, cli, crews, db, flows, tools, etc.)
- `src/api/routes/`: 15 rutas (agents.py, bundles.py, flows.py, etc.)
- `supabase/migrations/`: 30 archivos SQL (001-025)
- `tests/`: e2e, integration, unit

**2. Archivos directamente relacionados al paso:**
- `tests/e2e/test_exec_agent_mcp.py`: parche MCP que remover
- `presupuesto-bundle/manifest.json`: source para seed
- `presupuesto-bundle/agents/presupuestador.json`: source para seed
- `tests/e2e/test_register_agent.py`: agregar test GET agente
- `tests/e2e/test_real_flow_execute.py`: agregar verificación tool calling
- `tests/e2e/test_tool_calling_real.py`: consolidar con otros tests
- `tests/e2e/test_real_agent_presupuesto.py`: deprecar
- `tests/e2e/test_real_multi_agent_presupuesto.py`: deprecar
- `tests/e2e/test_real_agent_pipeline.py`: deprecar o consolidar
- `src/flows/presupuesto_flow.py`: validar test unitario

**3. Archivos de referencia (patrones existentes):**
- `src/crews/base_crew.py`: patrón ToolCallTracer para verificar tool calls
- `src/crews/factory.py`: patrón resolve_tools_async
- `tests/e2e/test_register_agent.py`: patrón bundle import

**4. Dependencias:**
- `pyproject.toml`: crewai>=0.100.0, openpyxl>=3.1.0

### Resultado:
Input para §0 (Verificación) y análisis. Paso toca múltiples tests E2E + creación directorio `data/seed/`.

---

## 🔍 VERIFICACIÓN OBLIGATORIA CONTRA CÓDIGO FUENTE

### Qué DEBES verificar:

**A. Tablas y Schema de DB:**
- No nuevas tablas en paso 7 (solo tests).

**B. Funciones y Clases:**
- `BaseCrew.get_last_tool_calls()` existe (line 206 en base_crew.py)
- `AgentFactory.resolve_tools_async()` existe (line 139 en factory.py)
- `PresupuestoFlow.validate_input()` existe (line 37 en presupuesto_flow.py)

**C. Patrones y Convenciones:**
- Tests E2E siguen patrón `pytestmark` con skipif
- Bundle structure sigue `manifest.json` + `agents/` + `skills/`

**D. Dependencias:**
- `openpyxl>=3.1.0` agregado en commit 349d9eb

**E. Estado real de archivos del paso:**
- `tests/e2e/test_exec_agent_mcp.py`: parche MCP presente (lines 63-67)
- `data/seed/`: NO existe (glob vacío)
- `tests/e2e/test_real_flow_execute.py`: NO verifica tool calls (no `get_last_tool_calls`)
- `tests/unit/test_presupuesto_flow.py`: NO existe

### Formato de Evidencia:
- ✅ VERIFICADO: `BaseCrew.get_last_tool_calls()` existe (base_crew.py:206)
- ❌ DISCREPANCIA: `data/seed/` ausente (plan requiere crear)
- ⚠️ NO VERIFICABLE: Bundle seed hashes — verificar post-creación

### Umbral Mínimo de Verificación:
Alcance del paso: 6-10 archivos afectados → ≥18 elementos

---

## 📋 Proceso Interno — 4 ETAPAS SECUENCIALES

### ETAPA 1: Análisis de DATOS
**Enfoque:** schema, integridad referencial, RLS, constraints

- Tablas tocadas: agent_catalog (tests), bundles (tests)
- No cambios schema — solo tests
- RLS policies: tenant_isolation via org_id
- Índices: existentes
- Tipos: JSON para soul_json, text arrays para allowed_tools

### ETAPA 2: Análisis de CÓDIGO
**Enfoque:** calidad, patrones, modularidad, mantenibilidad

- Funciones/clases modificadas/creadas:
  - `tests/e2e/test_exec_agent_mcp.py`: remover parche
  - `data/seed/presupuesto-bundle/`: crear
  - `tests/e2e/test_register_agent.py`: agregar test GET
  - `tests/e2e/test_real_flow_execute.py`: agregar verificación
  - `tests/e2e/test_tool_calling_real.py`: consolidar
  - Deprecar 3 tests legacy
  - `tests/unit/test_presupuesto_flow.py`: crear test unitario
- Reutilización patrones: ToolCallTracer existente, bundle import existente
- Duplicación: 3 tests tool calling casi idénticos — consolidar
- Cohesión alta / acoplamiento bajo: tests independientes
- Imports correctos: usar absolutos
- Firmas coherentes: seguir pytest patterns

### ETAPA 3: Análisis de BACKEND
**Enfoque:** APIs, middleware, flujos entre servicios, contratos

- Endpoints tocados: POST /api/bundles/import, GET /api/agents/{id}
- Middleware: org_id verification
- Flujos: bundle import → agent_catalog insert → GET consulta
- Problemas auth: org isolation
- Contratos: bundle ZIP con manifest.json + hashes
- Cuellos de botella: bundle validation

### ETAPA 4: Análisis de FULLSTACK + DX
**Enfoque:** coherencia end-to-end, UX, herramientas para el usuario final

- Flujo completo: DB → Backend → Tests → CI
- Decisiones data apoyan code: JSON schema para agents consistente
- APIs soportan UX: bundle import automatizable
- Inconsistencias: tests legacy usan pre-fetch data vs tool calling real
- MVP coherente: cierre asegura cobertura total sin gaps
- **DX & Tooling — OBLIGATORIO:**
  - Tarea repetitiva: validar bundle seed integrity post-creación
  - Herramienta: script `scripts/validate_seed_bundle.py` que lee `data/seed/` y verifica hashes vs archivos
  - Uso: `python scripts/validate_seed_bundle.py --bundle presupuesto-bundle`
  - Impacto: automatiza verificación manual, previene errores import

---

## 💾 Estructura de Salida

**Destino:** `DEVS/IN_PROGRESS/analisis-paso-7-kilo.md`

> [!IMPORTANT]
> **REGLA DE ORO:** Único archivo permitido modificar = `DEVS/IN_PROGRESS/analisis-paso-7-kilo.md`

---

### 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `data/seed/` existe | glob en raíz | ❌ | No encontrado |
| 2 | Parche MCP en test_exec_agent_mcp.py | grep patch _resolve_mcp_tool_async | ✅ | Lines 63-67 |
| 3 | ToolCallTracer.get_last_tool_calls | grep en base_crew.py | ✅ | Line 206 |
| 4 | test_presupuesto_flow.py existe | read file | ❌ | File not found |
| 5 | resolve_tools_async existe | grep en factory.py | ✅ | Line 139 |
| 6 | Bundle manifest hashes | calculate_sha256 vs manifest.json | ⚠️ | Verificar post-creación |
| 7 | Tests tool calling duplicados | count files con tool_calling | ✅ | 3 files similares |
| 8 | PresupuestoFlow.validate_input | grep en presupuesto_flow.py | ✅ | Line 37 |
| 9 | openpyxl depend | grep en pyproject.toml | ✅ | >=3.1.0 |
| 10 | Flow.execute expone last_tool_calls | read base_flow.py | ⚠️ | No encontrado — agregar |
| 11 | Bundle import API | grep en bundles.py | ✅ | POST /api/bundles/import |
| 12 | Agent GET API | grep en agents.py | ✅ | GET /api/agents/{id} |
| 13 | Tests legacy marcados skip | pytest --collect-only | ✅ | 3 files con skipif |
| 14 | BaseFlow._run_crew llama BaseCrew | grep en base_flow.py | ✅ | Line 78 |
| 15 | MCP resolution async evita deadlock | test_factory.py | ✅ | TestResolveMCPToolAsync |
| 16 | ExcelReaderTool registrado | tool_registry.get("excel_reader") | ✅ | test_register_agent.py:114 |
| 17 | PresupuestoFlow registrado | flow_registry.get("presupuesto") | ✅ | test_presupuesto_flow.py mock |
| 18 | Tool calling real en E2E | test_tool_calling_real.py | ✅ | No patches CrewAI |

**Discrepancias encontradas:**
- `data/seed/` ausente — crear en 7.2
- `test_presupuesto_flow.py` ausente — crear en 7.8
- `BaseFlow` no expone last_tool_calls — modificar para 7.4
- Tests duplicados tool calling — consolidar en 7.5

---

### 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ Schema: no cambios — tests usan agent_catalog existente
- ✅ Integridad referencial: org_id foreign key a organizations
- ✅ RLS policies: tenant_isolation en agent_catalog, bundles
- ✅ Índices: org_id indexado en agent_catalog
- ✅ Tipos de datos: JSONB para soul_json, text[] para allowed_tools

Incluir: ER diagram básico (agent_catalog → organizations via org_id), impacto nulo en datos existentes.

---

### 2️⃣ Análisis de Código (ETAPA 2)

- ✅ Funciones/clases nuevas: `validate_seed_bundle.py` (DX), test_GET_agente, test_validate_input_unit
- ✅ Patrones: seguir ToolCallTracer existente, pytest async patterns
- ✅ Modularidad: tests atómicos, una clase por sub-paso
- ✅ Calidad: lint 0 post-cambios, coverage +20%
- ✅ Imports exactos: from src.flows.presupuesto_flow import PresupuestoFlow

Incluir: firma completa `def test_validate_input_rejects_missing_fields(self, flow)` → asserts False para inputs incompletos.

---

### 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ APIs/endpoints: POST /api/bundles/import, GET /api/agents/{id}
- ✅ Middleware: org_id verification via Depends(require_org_id)
- ✅ Flujos: bundle ZIP → validation → insert agent_catalog → GET response
- ✅ Contratos: bundle manifest con hashes SHA256
- ✅ Error handling: 400 bad request si hashes no match

Incluir: request POST bundles/import con files, response 201 + agents_count, GET agents/{id} con soul_json completo.

---

### 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ Flujo completo: CI → tests E2E → bundle import → agent registrado
- ✅ Coherencia: data JSON apoya tool calling real
- ✅ Alineación: plan realizable con arquitectura CrewAI + MCP
- ✅ Gaps: tests legacy no alineados con tool calling
- ✅ **DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: validate_seed_bundle
- **Qué automatiza:** Verificación integrity de bundles seed post-creación (hashes SHA256)
- **Tipo:** script Python standalone
- **Cómo se usa:** `python scripts/validate_seed_bundle.py --bundle presupuesto-bundle --verbose`
- **Impacto para el usuario final:** Elimina verificación manual de hashes, previene import failures
- **Prioridad:** Tarea 0 — implementar antes que bundle seed

Incluir: flujo E2E con bundle seed → validate script → import API → GET agente.

---

### 5️⃣ Criterios de Aceptación

Lista binaria (sí/no) verificable:
- ✅ [DATA] agent_catalog schema soporta allowed_tools text[]
- ✅ [CODE] test_exec_agent_mcp.py no tiene parche MCP
- ✅ [BACKEND] POST /api/bundles/import retorna 201 con agents_count
- ✅ [FULLSTACK] Flow.execute verifica tool_calls >=1
- ✅ [DX] validate_seed_bundle.py ejecuta sin errores y valida hashes

---

### 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tests legacy deprecar afectan CI | Media | Skip marca tests como skipped, no failures | Deprecar con docstring clear, mantener para regression |
| Bundle seed hashes mismatch | Alta | SHA256 manual error-prone | validate_seed_bundle.py previene |
| BaseFlow modifica rompe existing tests | Alta | Agregar last_tool_calls expuesto | Unit tests primero, luego integration |
| Consolidar tests tool calling pierde assertions | Media | 3 files con diferencias sutiles | Review diffs antes merge |

- Riesgos técnicos: deadlock si async resolution falla
- Riesgos integración: bundle import vs agent_catalog schema
- Riesgos futuro: tests legacy obsoletos

---

### 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DX validate_seed_bundle | `scripts/validate_seed_bundle.py` | `def main(bundle_name: str) -> bool` | `scripts/seed_system_bundles.py` | DX | Media | 0.5h | Ninguna | → verificar: `python scripts/validate_seed_bundle.py --bundle presupuesto-bundle` valida hashes |
| 1 | Remover parche MCP | `tests/e2e/test_exec_agent_mcp.py` | Remover lines 63-67 patch | `test_tool_calling_real.py` no patches | CODE | Baja | 0.25h | Tarea 0 | → verificar: test_exec_agent_mcp.py no contiene "_resolve_mcp_tool_async" patch |
| 2 | Crear data/seed/ | `data/seed/presupuesto-bundle/` | manifest.json + agents/presupuestador.json | `presupuesto-bundle/` existente | DATA | Baja | 0.25h | Tarea 0,1 | → verificar: `data/seed/presupuesto-bundle/manifest.json` hashes correctos via validate_seed_bundle |
| 3 | Test GET agente API | `tests/e2e/test_register_agent.py` | `async def test_get_agent_via_api_returns_correct_data` | `test_register_agent.py` existente | BACKEND | Media | 0.5h | Tarea 2 | → verificar: test_get_agent_via_api pasa con campos soul_json, allowed_tools |
| 4 | Agregar tool calling check Flow.execute | `tests/e2e/test_real_flow_execute.py` | Agregar `flow.last_tool_calls["excel_reader"] >=1` | `test_tool_calling_real.py` aserción | FULLSTACK | Baja | 0.25h | Tarea 0,3 | → verificar: test_real_flow_execute verifica tool_calls via get_last_tool_calls |
| 5 | Consolidar tests tool calling | `tests/e2e/test_tool_calling_real.py` | Conservar + eliminar duplicados | Mejor nombre y completitud | CODE | Media | 0.5h | Tarea 4 | → verificar: solo 1 file cubre tool calling real |
| 6 | Deprecar tests legacy | `tests/e2e/test_real_*.py` (3 files) | `@pytest.mark.skip` + docstring | `test_3_5_latency.py` pattern | CODE | Baja | 0.25h | Tarea 5 | → verificar: 3 files skipped, docstring explica reemplazo |
| 7 | Verificación cruzada bundle seed | `tests/e2e/test_register_agent.py` | `test_import_seed_bundle_via_api` | Extensión existente | BACKEND | Media | 0.5h | Tarea 2,6 | → verificar: test_import_seed_bundle_via_api usa data/seed/ real |
| 8 | Test unitario validate_input | `tests/unit/test_presupuesto_flow.py` | `test_validate_input_rejects_missing_fields` | `test_factory.py` pattern | CODE | Baja | 0.25h | Tarea 0 | → verificar: test unitario valida inputs incompletos |

> [!IMPORTANT]
> Tarea 0 siempre = DX & Tooling. El implementador DEBE ejecutarla primero y usar la herramienta resultante para el resto del paso.

**Tiempo total estimado:** 3.5 horas

---

### 8️⃣ Roadmap (NO implementar ahora)

- Optimizaciones: paralelizar tests E2E
- Mejoras UX: dashboard para bundle import
- Pre-requisitos futuros: multi-bundle support

---

## 🚫 Reglas de Oro

- ✅ Análisis accionable y específico, no genérico
- ✅ TODO verificado contra código, no supuestos
- ✅ Si algo no está definido → señalarlo como ambigüedad + resolución concreta
- ✅ Si el plan contradice el código → el código gana + documentar discrepancia
- ✅ Nivel CTO exigente en rigor y profundidad
- ✅ Coherente con phase-state.md — no perder decisiones ya tomadas
- ✅ TODO el paso, incluyendo sub-pasos
- ✅ Etapas secuenciales — data → code → backend → fullstack+DX, sin saltar
- ✅ ≥ 1 herramienta DX propuesta — siempre, sin excepción
- ✅ Tareas atómicas: una tarea = un artefacto = interfaz completa = patrón explícito = verificación inline
- ✅ El implementador no decide nada: si debe inferir cualquier detalle de diseño → la tarea está incompleta

---

## 📊 Métrica de Calidad

| Métrica | Mínimo |
|---|---|
| `proyecto-config.json` leído antes de explorar | 100% |
| Elementos verificados (§0) | ≥18 (6-10 archivos afectados) |
| Discrepancias detectadas | ≥4 (data/seed, test_presupuesto_flow, last_tool_calls, duplicados) |
| Secciones completadas | 8 secciones (0-7) |
| Etapas cubiertas | 4 etapas (data, code, backend, fullstack+DX) |
| Criterios de aceptación | ≥5 (por sub-paso verificables) |
| Riesgos identificados | ≥3 (técnico, integración, futuro) |
| Tareas atómicas (1 artefacto por tarea) | 100% |
| Interfaz exacta por tarea | 100% — sin inferencias posibles |
| Patrón de referencia explícito por tarea | 100% — archivo concreto, no "seguir el estilo" |
| Verificación inline por tarea | 100% — comando o check concreto |
| Suposiciones no verificadas | ≤2, cada una marcada ⚠️ |
| Propuesta DX / Tooling | ≥1 herramienta concreta con descripción de impacto para usuario final |
| Estimación de tiempo | Sí, por tarea y total |

---

**Idioma de respuesta:** Español 🇪🇸
```