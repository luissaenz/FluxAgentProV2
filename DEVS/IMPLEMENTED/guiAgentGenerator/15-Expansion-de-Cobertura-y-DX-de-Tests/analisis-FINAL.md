# Análisis Unificado — Paso 15: Expansión de Cobertura y DX de Tests

> **Fase:** guiAgentGenerator — Paso 15/15 (ÚLTIMO)
> **Prioridad:** Media
> **Origen:** ID-023b, ID-002, ID-020, ID-053, ID-054
> **Generado:** 2026-05-18 — Análisis directo sobre código fuente (IN_PROGRESS vacío)

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación

No hay análisis de agentes individuales en IN_PROGRESS. Este análisis se genera directamente del plan.md + verificación contra código real.

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada | Resolución |
|---|---|---|---|---|
| D1 | Plan dice "tests unitarios para AgentForm" (ID-020) pero dashboard/ NO tiene infraestructura de tests (sin Jest/Vitest/testing-library) | Análisis directo | ✅ `dashboard/package.json` — sin test runner | NO implementar tests de componentes React. En su lugar: extraer schema zod a módulo compartido y testear lógica de validación como funciones puras TypeScript via tsx. Setup completo de Vitest + testing-library excede alcance MVP (requiere ~8h adicionales de infraestructura) |
| D2 | Plan asume que test_3_5_latency.py se puede estabilizar fácilmente pero requiere Supabase real y tiene thresholds extremadamente laxos (P95 < 5000ms) | Análisis directo | ✅ `tests/integration/test_3_5_latency.py:46-54` | Agregar fallback mock para tests sin credenciales Supabase. No modificar thresholds (son para entorno real). Crear fixture que detecte ausencia de credenciales y skip con mensaje claro. |
| D3 | Plan dice "migrar mocks locales a fixtures globales en conftest.py" (ID-053) pero la mayoría ya están en conftest.py global | Análisis directo | ✅ `tests/conftest.py` — 338 líneas con 10+ fixtures | Consolidar patches inline restantes: en test_3_5_latency.py hay imports locales sin mock. En test_builder_scenarios.py hay helpers inline (`_mock_db`) que duplican patrones de conftest.py global. |
| D4 | No existe fap coverage ni comando similar para reporte visual de cobertura | Análisis directo | ✅ `src/cli/commands/` — 37 comandos, ninguno de coverage | Crear `fap coverage report` como Tarea 0. |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo:** Cerrar la fase guiAgentGenerator asegurando mantenibilidad a largo plazo mediante:
1. Tests unitarios para `GET /api/tools/available` (backend — ID-002)
2. Tests de validación del schema Zod del AgentForm (frontend — ID-020 adaptado)
3. Estabilización del test de latencia (test_3_5_latency.py — ID-023b)
4. Consolidación de mocks inline a fixtures reutilizables (ID-053)
5. Herramienta DX de cobertura visual integrada en `fap` CLI (ID-054 — Tarea 0)

**Correcciones críticas al plan:**
- ⚠️ ID-020 (Frontend Coverage): Plan pide tests unitarios para AgentForm pero NO existe infraestructura de tests frontend. Se escala a: extraer schema zod → testear como función pura TypeScript via `tsx`. Setup completo de Vitest/testing-library queda como mejora 🔵 post-MVP.
- ⚠️ ID-023b: No requiere cambiar thresholds de latencia (son válidos para entorno real). Requiere skip graceful sin credenciales.

**Herramienta DX seleccionada:** `fap coverage report` — comando CLI que ejecuta pytest con --cov, genera reporte por módulo con umbrales, y opcionalmente produce HTML visual. Se integra con `fap test builder` para añadir cobertura al reporte existente.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path
1. Desarrollador ejecuta `fap coverage report` → ve tabla Rich con % por módulo + status ✅/❌ por umbral
2. Desarrollador ejecuta `fap test builder --cov` → tests E2E + reporte de cobertura combinado
3. Tests unitarios de tools.py cubren: lista vacía, filtro source, filtro category, MCP graceful degradation
4. Tests de schema Zod cubren: validación de role/goal/backstory, valores default, campos opcionales
5. test_3_5_latency.py corre sin credenciales → salta con mensaje claro (no falla)

### Edge Cases MVP
- tools.py: MCPPool.get() lanza excepción → graceful degradation, retorna solo tools locales
- tools.py: org sin MCP servers configurados → retorna solo tools locales sin error
- Schema Zod: goal < 10 chars → error de validación
- Schema Zod: backstory < 10 chars → error de validación
- Schema Zod: role vacío → error de validación
- Coverage: módulo sin tests → muestra 0% sin crash
- Coverage: umbral no definido → usa default 75%

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### T0 — `fap coverage report` (DX & Tooling)
- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/src/cli/commands/coverage_report.py`
- **Tipo:** Creación
- **Descripción:** Comando CLI que ejecuta pytest con coverage, analiza resultados por módulo, muestra tabla Rich con status por umbral
- **Interfaces clave:**
  ```python
  @coverage_app.command("report")
  def coverage_report(
      module: Optional[str] = None,      # Filtrar por módulo (src/api/routes/tools, etc.)
      threshold: float = 75.0,            # Umbral mínimo (%)
      html: bool = False,                  # Generar reporte HTML
      diff: bool = False,                  # Mostrar solo módulos debajo del umbral
  ) -> None
  ```
- **Patrón a seguir:** `src/cli/commands/test_builder.py` — estructura Typer + subprocess + Rich console
- **Registro:** `src/cli/main.py` — `coverage_app = typer.Typer(); app.add_typer(coverage_app, name="coverage")`

#### T1 — Tests unitarios para tools.py
- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/tests/unit/test_tools.py`
- **Tipo:** Creación
- **Descripción:** Unit tests para el endpoint `GET /api/tools/available`. Sigue el patrón de `test_templates.py` (TestClient + patch get_service_client + patch tool_registry)
- **Interfaces clave:**
  ```python
  class TestToolsEndpoint:
      def test_list_empty(self, client): ...
      def test_list_local_tools(self, client): ...
      def test_list_filter_source_local(self, client): ...
      def test_list_filter_source_mcp(self, client): ...
      def test_list_filter_category(self, client): ...
      def test_mcp_graceful_degradation(self, client): ...
      def test_tools_count_matches(self, client): ...
  ```
- **Patrón a seguir:** `tests/unit/test_templates.py` — `_mock_db()` helpers, `patch("src.api.routes.tools.get_service_client")`, `patch("src.api.routes.tools.tool_registry")`

#### T2 — Tests de schema Zod (AgentForm validation)
- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/lib/agent-schema.ts` (extracción) + `/home/daniel/develop/Personal/FluxAgentProV2/scripts/test-agent-schema.mjs` (test script)
- **Tipo:** Creación + Refactor (extracción)
- **Descripción:** Extraer el schema Zod de AgentForm.tsx a `lib/agent-schema.ts`. Crear script de test en Node.js que valida el schema sin React.
- **Interfaces clave:**
  ```typescript
  // dashboard/lib/agent-schema.ts
  export const agentFormSchema = z.object({
    role: z.string().min(1, 'Role is required'),
    goal: z.string().min(10, 'Goal must be at least 10 characters'),
    backstory: z.string().min(10, 'Backstory must be at least 10 characters'),
    llmProvider: z.string(),
    llmModel: z.string(),
    allowedTools: z.array(z.string()),
    maxIter: z.number().int().min(1).max(10),
    verbose: z.boolean(),
    reasoning: z.boolean(),
    injectDate: z.boolean(),
    memory: z.boolean(),
  })
  export type AgentFormData = z.infer<typeof agentFormSchema>
  ```

#### T3 — Estabilización test_3_5_latency.py
- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/tests/integration/test_3_5_latency.py`
- **Tipo:** Modificación
- **Descripción:** Agregar fixture condicional que detecte ausencia de SUPABASE_URL/SUPABASE_SERVICE_KEY y salte tests con skip claro. El skip condicional ya existe como `pytestmark = pytest.mark.skipif(...)` pero mejorarlo con fixture que verifique conectividad real antes de ejecutar.
- **Cambio concreto:** Agregar fixture `supabase_available` que verifica conectividad real + fixture `supabase_client` que usa skip si no hay credenciales

#### T4 — Consolidación de mocks inline
- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/tests/conftest.py` + tests individuales
- **Tipo:** Modificación (conftest.py + archivos de test)
- **Descripción:** Mover helpers de mockeo duplicados a conftest.py global. Los helpers `_mock_db`, `_mock_db_filter`, `_mock_db_single` de test_templates.py aparecen también inline en test_builder_scenarios.py. Centralizar en conftest.py

#### T5 — Integración de cobertura en fap test builder
- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/src/cli/commands/test_builder.py`
- **Tipo:** Modificación
- **Descripción:** Añadir flag `--cov` al comando `fap test builder run` que ejecuta con pytest-cov y muestra tabla de cobertura después de los resultados de tests. Integrar con fap coverage report.

---

### DX & Tooling — Tarea 0

```
### Herramienta: `fap coverage report`
- **Qué automatiza:** Ejecutar pytest con coverage y analizar resultados por módulo manualmente (antes: `uv run pytest --cov=src --cov-report=term-missing` + parsear output manualmente)
- **Tipo:** Comando CLI (Typer + Rich + subprocess)
- **Ubicación:** src/cli/commands/coverage_report.py
- **Cómo se usa:**
  ```bash
  fap coverage report                          # Reporte completo
  fap coverage report --module src/api/routes/tools  # Solo un módulo
  fap coverage report --threshold 80           # Umbral personalizado
  fap coverage report --html                   # + reporte HTML
  fap coverage report --diff                   # Solo módulos debajo del umbral
  ```
- **Impacto para el usuario final:** Reduce de "correr pytest con flags y parsear output" a un solo comando con visualización Rich. Detecta regresiones de cobertura antes de commit.
- **El implementador DEBE usarla** para verificar cobertura de T1, T2 antes de darlos por finalizados.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **NO instalar Vitest/testing-library para tests de AgentForm:** El setup completo (Vitest + jsdom + testing-library + mocks de Next.js/react-query) requiere ~8h. Se escala a tests de schema Zod como funciones puras TypeScript via Node.js nativo. Post-MVP puede añadirse como mejora.

2. **tsx para ejecutar tests TypeScript sin transpilación:** Usar `npx tsx` (ya disponible vía npm) para ejecutar tests del schema Zod sin configurar Jest/Vitest.

3. **Coverage vía pytest-cov existente:** No instalar nuevas herramientas. pytest-cov ya está en dev dependencies. Solo crear wrapper CLI.

4. **Extensión de conftest.py vs nuevo módulo de helpers:** Los helpers `_mock_db()` deben ir en conftest.py global (patrón existente). No crear nuevo archivo de helpers para mantener consistencia.

5. **test_3_5_latency.py NO modificar thresholds:** Los thresholds actuales (P95 < 5000ms) son válidos para entorno real con Supabase. Solo mejorar skip condicional.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] T0: `fap coverage report` ejecuta sin errores y muestra tabla Rich con % por módulo
✅ [CODE] T0: `fap coverage report --diff` muestra solo módulos debajo del umbral
✅ [CODE] T0: `fap coverage report --html` genera reporte HTML válido
✅ [BACKEND] T1: `test_tools.py` creado con ≥ 5 tests que cubren lista vacía, filtros, MCP graceful degradation
✅ [BACKEND] T1: `uv run pytest tests/unit/test_tools.py -v` pasa 100%
✅ [CODE] T2: Schema Zod extraído a `dashboard/lib/agent-schema.ts` — AgentForm.tsx importa desde ahí
✅ [CODE] T2: Script `scripts/test-agent-schema.mjs` valida schema con casos OK y error
✅ [BACKEND] T3: test_3_5_latency.py salta gracefulmente sin credenciales Supabase (no falla)
✅ [BACKEND] T4: Helpers `_mock_db()` movidos a tests/conftest.py — test_templates.py y test_builder_scenarios.py importan desde ahí
✅ [CODE] T5: `fap test builder run --cov` incluye tabla de cobertura en output
✅ [DX] `fap coverage report` usado para verificar cobertura de T1 y T2 (dogfooding)
✅ [DX] `fap coverage report` reduce tarea manual de "correr pytest --cov + analizar output" a un comando
```

**Funcionales:**
- [x] Backend: tools endpoint tiene cobertura de tests unitarios
- [x] Frontend: schema Zod de AgentForm es testeable sin React
- [x] Infra: test de latencia no falla en CI sin Supabase
- [x] DX: cobertura visible en un comando

**Técnicos:**
- [x] `ruff check src/ tests/` sin warnings nuevos
- [x] `tsc --noEmit` sin errores (schema export compatible)
- [x] Todos los tests pre-existentes siguen pasando (Q2)
- [x] Cobertura de `src/api/routes/tools.py` ≥ 80% (de 0%)
- [x] Cobertura de `src/` global no degrada (mantiene ≥ 75%)

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap coverage report` | Media | 2.0h | Ninguna |
| 1 | Tests unitarios para `GET /api/tools/available` | Media | 1.5h | T0 (verificar cobertura) |
| 2 | Tests de schema Zod de AgentForm | Baja | 0.5h | T0 (verificar cobertura) |
| 3 | Estabilización test_3_5_latency.py | Baja | 0.5h | Ninguna |
| 4 | Consolidación de mocks inline a conftest.py | Baja | 0.5h | Ninguna |
| 5 | Integración `--cov` en `fap test builder` | Baja | 0.5h | T0 |
| **TOTAL** | | | **5.5h** | |

> **IMPORTANTE:** Tarea 0 (DX & Tooling) debe ejecutarse primero. El implementador DEBE usar `fap coverage report` para verificar cobertura de T1 y T2.

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| pytest-cov no instalado en CI | Baja | `pytest-cov` en dev deps pero podría faltar | Agregar check en `fap coverage report` que instale si falta |
| Tests de schema Zod frágiles si cambia schema | Baja | AgentForm puede cambiar schema en futuros pasos | Tests validan estructura, no valores específicos de campos |
| test_3_5_latency.py timeout en CI | Media | Requiere Supabase real + Realtime, puede timeout | Skip automático sin credenciales; ya tiene timeout de 5min |
| fap coverage report falla si no hay tests | Baja | Módulo sin tests → coverage reporta NaN | Manejar gracefully: mostrar warning + 0% |
| Duplicación de helpers _mock_db entre conftest.py y test existentes | Baja | Migración parcial puede dejar duplicados | Verificar que todos los imports apuntan a conftest.py; eliminar helpers inline |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | T0: coverage report full | `fap coverage report` | Tabla Rich con todos los módulos de src/ + % + status |
| TP-2 | T0: coverage report --diff | `fap coverage report --diff` | Solo módulos con % < threshold |
| TP-3 | T1: tools list empty | GET /api/tools/available con mock vacío | 200, tools=[], count=0 |
| TP-4 | T1: tools list with source filter | GET /api/tools/available?source=local | 200, solo tools locales |
| TP-5 | T1: MCP graceful degradation | MCPPool.get() lanza excepción | 200, tools locales sin error |
| TP-6 | T2: schema Zod goal < 10 chars | `agentFormSchema.safeParse({ goal: "short" })` | success: false, error en goal |
| TP-7 | T2: schema Zod valid payload | Payload completo y válido | success: true, data parseada |
| TP-8 | T3: latency test sin credenciales | SUPABASE_URL no configurado | Skip con mensaje claro (exit code 0) |
| TP-9 | T5: fap test builder --cov | `fap test builder run --cov` | Tests pasan + tabla de cobertura al final |

**Comando para ejecutar tests:**
```bash
# Tests unitarios backend
uv run pytest tests/unit/test_tools.py -v

# Tests schema Zod frontend
npx tsx scripts/test-agent-schema.mjs

# Coverage completo
uv run fap coverage report

# Builder tests con cobertura
fap test builder run --cov --org-id test-org
```
