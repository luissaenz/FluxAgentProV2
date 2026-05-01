# Análisis Unificado — Paso 6: Performance & Observabilidad

> **Fuente:** Consolidación de 4 análisis (k2.6, q3.6, ds, glm)
> **Fecha:** 2026-05-01
> **Fase:** testing — Fase VI
> **Destino:** `DEVS/IN_PROGRESS/analisis-FINAL.md`

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| k2.6 | ✅ 12 elementos | 3 | ✅ `fap perf-check` | ✅ Archivos + líneas específicas | 4.2 |
| q3.6 | ✅ 18 elementos | 1 | ✅ `fap benchmark` | ✅ Archivos + líneas + rangos | 4.5 |
| ds | ✅ 22 elementos | 5 | ✅ `fap benchmark [paso]` | ✅ Archivos + líneas + código ejemplo | 4.8 |
| glm | ✅ 18 elementos | 3 | ✅ `fap bench` | ✅ Archivos + líneas + flujos detallados | 4.3 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|:---:|:---:|---|
| 1 | `tests/stress/` ya existe con tests similares (S4.1, S4.5, S4.7) pero thresholds/escalas distintos | k2.6, ds, glm | ✅ `tests/stress/test_concurrency.py`, `test_edge_cases.py` | P6 tests son complementarios, no duplicados. S4.x = stress (500 tools, 10MB, <2s-5s). P6.x = benchmark fino (50 tools, 1MB, <100ms-500ms). Coexisten. |
| 2 | `WorkflowDefinition` NO tiene campo `input_data` — test S4.7 existente usa campo inexistente | q3.6, glm | ✅ `src/flows/workflow_definition.py:65-72` — solo 7 fields definidos | P6.2 debe usar schema real. NO incluir `input_data`. S4.7 tiene bug silencioso (Pydantic sin `extra="allow"` rechaza campos extra). |
| 3 | `fap stress-bench` ya existe (Paso 4) pero no hay equivalente para P6 | k2.6 | ✅ `src/cli/commands/stress_bench.py` existe | Crear herramienta DX nueva específica para P6: `fap perf-check` / `fap benchmark`. |
| 4 | `pytest-benchmark` NO está en dev dependencies | ds | ✅ `pyproject.toml` no lo incluye | Usar `time.perf_counter()` + assertions manuales, mismo patrón que S4.x. No agregar dependencia. |
| 5 | Pattern regex `Bearer [a-zA-Z0-9\-._~+/]+=*` causa backtracking catastrófico en strings 1MB | ds | ✅ `src/mcp/sanitizer.py:20` — `+` greedy seguido de `=*` | P6.3 actúa como diagnóstico. Si falla, fix: cambiar `+` a `+?` (lazy) o anclar. Documentar en riesgos. |
| 6 | P6.4 ambigüedad: ¿medir `_is_circuit_open()` directo o `get_tools()` completo? | k2.6, ds, glm | ✅ `src/tools/mcp_pool.py:60-66` | Medir `_is_circuit_open()` directamente para overhead puro. Test separado de `get_tools` con circuito abierto para latencia de rechazo. `get_tools()` completo con circuito cerrado requiere mock de adapter para evitar conexión real. |
| 7 | Ubicación de tests P6 no especificada en plan | k2.6, q3.6, ds, glm | — | Consenso: `tests/stress/test_performance.py` — aprovecha `conftest.py` existente con fixtures autouse para MCPPool reset y flow_registry cleanup. |
| 8 | Observabilidad no cubierta — paso se llama "Performance & **Observabilidad**" pero plan solo tiene benchmarks | ds, glm | ✅ Plan solo define P6.1-P6.4 (latencia) | Gap real. No bloquea P6. Documentar en roadmap. Sugerir agregar tests de structlog en paso futuro. |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo:** Crear 4 benchmarks de rendimiento (P6.1-P6.4) para componentes core del sistema, garantizando que mantienen latencia baja bajo carga controlada. Implementar herramienta DX para ejecución y reporte automatizado.

**Correcciones críticas al plan:**
1. `WorkflowDefinition` no tiene campo `input_data` — P6.2 debe usar schema real (7 fields).
2. Pattern regex `Bearer` en sanitizer tiene riesgo de backtracking catastrófico — P6.3 es diagnóstico.
3. P6.4 debe medir `_is_circuit_open()` directo, no `get_tools()` completo.
4. Observabilidad (logging, métricas, tracing) no está cubierta — gap para paso futuro.

**Decisión DX:** Fusionar propuestas en **`fap perf-check`** — CLI Typer que ejecuta benchmarks, verifica thresholds, genera reporte JSON comparativo con baseline. Hereda lo mejor de cada propuesta: warmup de ds, 3-run median de q3.6, baseline de k2.6, multi-paso de glm.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Developer ejecuta `fap perf-check` → herramienta corre `pytest tests/stress/test_performance.py -v`
2. Cada benchmark (P6.1-P6.4) mide función objetivo con `time.perf_counter()` o `time.perf_counter_ns()`
3. Thresholds se verifican automáticamente (<100ms, <50ms, <500ms, <1ms)
4. Reporte JSON generado en `reports/perf_report.json` con tiempos reales vs thresholds
5. Opcional: `fap perf-check --baseline` guarda baseline; `--compare` detecta regresiones

### Edge Cases MVP

1. **Flakiness en CI:** runners compartidos → usar múltiples repeticiones (3-10), tomar mínimo o P95, threshold con margen 20%
2. **Singleton contaminado:** `MCPPool` y `tool_registry` deben limpiarse entre tests con fixtures autouse
3. **Pattern Bearer backtracking:** si P6.3 falla, diagnosticar regex catastrófico y proponer fix
4. **Cold start vs steady-state:** warmup de 1-3 iteraciones descartadas antes de medir
5. **`input_data` en WorkflowDefinition:** NO usar — campo inexistente. Usar schema real.

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. `tests/stress/test_performance.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\stress\test_performance.py`
- **Tipo:** Creación
- **Descripción:** 4 benchmarks P6.1-P6.4 en archivo único. Usa fixtures autouse de `tests/stress/conftest.py`.
- **Patrones a seguir:** `time.perf_counter_ns()` para P6.4 (<1ms), `time.perf_counter()` para resto. Assertions manuales (sin pytest-benchmark). Helpers reutilizados de `test_concurrency.py` y `test_edge_cases.py`.

#### 2. `src/cli/commands/perf_check.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\perf_check.py`
- **Tipo:** Creación
- **Descripción:** CLI Typer `fap perf-check`. Ejecuta benchmarks, verifica thresholds, genera reporte JSON.
- **Interfaces clave:** Comando Typer con flags `--baseline`, `--compare`, `--json`, `--verbose`
- **Patrones a seguir:** `src/cli/commands/test_step.py` — estructura de comando Typer existente.

#### 3. `src/cli/commands/__init__.py` (MODIFICACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\__init__.py`
- **Tipo:** Modificación — registrar nuevo comando `perf-check`
- **Descripción:** Importar y registrar `perf_check` app Typer en router CLI existente.

#### 4. `tests/stress/conftest.py` (MODIFICACIÓN OPCIONAL)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\stress\conftest.py`
- **Tipo:** Modificación — agregar helpers reutilizables
- **Descripción:** Mover `_make_step_definition`, `_make_agent_definition`, `_make_1mb_string` a conftest para reutilización entre test files.

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap perf-check
- **Qué automatiza:** Ejecución de benchmarks P6.1-P6.4 con un solo comando, verificación de thresholds, generación de reporte JSON comparativo, y detección de regresiones contra baseline.
- **Tipo:** CLI / comando Typer.
- **Ubicación:** `src/cli/commands/perf_check.py`
- **Cómo se usa:**
  ```bash
  fap perf-check              # Corre tests/stress/test_performance/, reporta pass/fail
  fap perf-check --baseline   # Guarda reports/perf_baseline.json
  fap perf-check --compare    # Compara contra baseline, alerta regresiones
  fap perf-check --json       # Output machine-readable
  fap perf-check --verbose    # Muestra tiempos individuales por benchmark
  ```
- **Impacto para el usuario final:** No necesita recordar thresholds ni ejecutar pytest manualmente. Un comando verifica que componentes críticos no degradaron performance. Reporte JSON para integración CI.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso (dogfooding obligatorio).
```

---

## 4️⃣ Decisiones Tecnológicas

1. **`time.perf_counter_ns()` para P6.4, `time.perf_counter()` para resto:** P6.4 requiere precisión sub-milisegundo. `perf_counter_ns()` evita conversión float y da resolución nanosegundo. Resto de benchmarks tienen thresholds holgados → `perf_counter()` suficiente.

2. **Tests en `tests/stress/test_performance.py`:** Aprovecha `conftest.py` existente con fixtures autouse (`_reset_pool`, `_clean_flow_registry`). No requiere nueva infraestructura de test.

3. **Sin `pytest-benchmark`:** No está en dev dependencies. Benchmarks usan `time.perf_counter()` + assertions manuales, mismo patrón que S4.x existentes. Evita dependencia nueva.

4. **P6.2 usa schema real de `WorkflowDefinition`:** NO incluir `input_data`. Schema real: `name`, `description`, `flow_type`, `steps`, `agents`, `approval_rules`, `category`.

5. **P6.4 mide `_is_circuit_open()` directo:** Threshold <1ms es imposible para `get_tools()` completo (async, retry, connection). El check de circuit breaker es O(1) dict lookup + float comparison → trivialmente <1ms.

6. **Warmup obligatorio:** 1 iteración descartada en tests pytest. CLI `fap perf-check` implementa 3 iteraciones de warmup para mediciones más precisas.

7. **⚠️ Correcciones al plan:**
   - ⚠️ El plan dice "MCPPool.get_tools con circuito cerrado vs abierto" pero el threshold <1ms aplica al **check** (`_is_circuit_open`), no al flujo completo. Se implementa medición directa del check.
   - ⚠️ El plan menciona validación de `WorkflowDefinition` con `input_data` pero el modelo real NO tiene ese campo. Se implementa con schema real.
   - ⚠️ El plan no especifica ubicación de tests. Se decide `tests/stress/test_performance.py` por consistencia con tests existentes.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] P6.1: resolve_tools(50 tools mock registry, org_id, async_mode=False) completa en <100ms
✅ [CODE] P6.2: WorkflowDefinition(**10_steps_5_agents) valida en <50ms (schema real, sin input_data)
✅ [CODE] P6.3: sanitize_output(string 1MB con secretos) completa en <500ms
✅ [CODE] P6.4: MCPPool._is_circuit_open(key) overhead <1ms (circuito abierto y cerrado)
✅ [CODE] Tests ubicados en `tests/stress/test_performance.py`
✅ [DX] `fap perf-check` ejecuta todos los benchmarks y reporta pass/fail
✅ [DX] `fap perf-check --baseline` genera `reports/perf_baseline.json`
✅ [DX] `fap perf-check --compare` detecta regresiones contra baseline
✅ [CODE] `pytest tests/stress/test_performance.py` pasa 100% (4/4 benchmarks)
✅ [CODE] Lint `ruff check tests/stress/test_performance.py src/cli/commands/perf_check.py` → 0 errores
✅ [CODE] Benchmarks usan mocks puros — sin LLM/DB/MCP reales
✅ [CODE] Benchmarks son independientes — orden de ejecución no afecta resultados
```

**Funcionales:**
- [ ] P6.1: 50 tools mock registry resueltas en <100ms
- [ ] P6.2: WorkflowDefinition con 10 steps + 5 agents valida en <50ms
- [ ] P6.3: Sanitizer procesa 1MB en <500ms y redacta secretos
- [ ] P6.4: Circuit breaker check <1ms en ambos estados (abierto/cerrado)
- [ ] `fap perf-check` reporta 4/4 pass con tiempos reales

**Técnicos:**
- [ ] `time.perf_counter_ns()` usado en P6.4
- [ ] Fixtures autouse limpian MCPPool y tool_registry entre tests
- [ ] Warmup de 1 iteración en tests pytest
- [ ] Helpers comunes (`_make_step_definition`, `_make_agent_definition`, `_make_1mb_string`) en conftest o importados

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `src/cli/commands/perf_check.py` (`fap perf-check`) | Media | 2h | Ninguna |
| 1 | Crear `tests/stress/test_performance.py` con estructura base y fixtures de limpieza | Baja | 0.5h | Tarea 0 |
| 2 | Extraer helpers comunes a `tests/stress/conftest.py` (`_make_step_definition`, `_make_agent_definition`, `_make_1mb_string`) | Baja | 0.5h | Tarea 1 |
| 3 | Implementar P6.1: benchmark `resolve_tools` 50 tools <100ms | Media | 1h | Tarea 2 |
| 4 | Implementar P6.2: benchmark `WorkflowDefinition` 10 steps + 5 agents <50ms | Media | 1h | Tarea 2 |
| 5 | Implementar P6.3: benchmark `sanitize_output` 1MB <500ms | Media | 1h | Tarea 2 |
| 6 | Implementar P6.4: benchmark `MCPPool._is_circuit_open` overhead <1ms (abierto + cerrado) | Media | 1.5h | Tarea 2 |
| 7 | Validar suite completa + lint + `fap perf-check` | Baja | 0.5h | Tareas 3-6 |
| 8 | Documentar en TESTING.md sección "Performance Benchmarks (Paso 6)" | Baja | 0.5h | Tarea 7 |
| **TOTAL** | | | **8.5h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap perf-check` para validar el resto del paso (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Flakiness en CI por variación de CPU | Media | Runners compartidos, carga variable | 3-10 repeticiones, tomar mínimo/P95. Threshold con margen 20%. `@pytest.mark.flaky(reruns=2)` opcional |
| Pattern Bearer regex backtracking catastrófico | Alta | `+` greedy + `=*` en strings 1MB sin Bearer tokens | P6.3 como diagnóstico. Si falla: cambiar `+` a `+?` o anclar con lookahead. Documentar en roadmap |
| Singleton MCPPool contaminado entre tests | Media | Tests previos dejan estado en `_health` o `_adapters` | Fixture autouse con `MCPPool.reset()` antes de cada test P6.4 |
| `tool_registry` con tools residuales de S4.1 | Media | Tests S4.1 registran 500 tools y pueden no limpiar | Fixture con `tool_registry._tools.clear()` antes de P6.1 |
| P6.4 mide mal si no se mockea adapter | Media | `get_tools()` con circuito cerrado intenta conexión real | Pre-cargar `_adapters[key]` con MagicMock `.tools = []`. Medir `_is_circuit_open()` directo |
| `input_data` bug de S4.7 se replica en P6.2 | Alta | `WorkflowDefinition` no tiene campo `input_data` | P6.2 usa schema real (7 fields). Documentar decisión explícitamente |
| Observabilidad no cubierta crea gap | Media | Paso se llama "Performance & Observabilidad" pero solo hay benchmarks | Documentar en roadmap. Sugerir tests de structlog en paso futuro |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | resolve_tools 50 tools | 50 nombres mock en `tool_registry._tools`, `org_id` uuid, `async_mode=False` | Lista de 50 tools, elapsed <100ms |
| TP-2 | WorkflowDefinition 10 steps + 5 agents | Dict con 10 StepDefinition (grafo lineal), 5 AgentDefinition, flow_type snake_case | Instancia válida, elapsed <50ms |
| TP-3 | sanitize_output 1MB | String 1MB con ~100 secretos distribuidos (sk_live_, Bearer, ghp_, etc.) | String con `[REDACTED]`, elapsed <500ms |
| TP-4 | Circuit breaker overhead (cerrado) | `_health[key] = {"failures": 0.0, "last_check": time.time()}`, `_adapters[key]` mock | `_is_circuit_open(key)` retorna False, elapsed <1ms |
| TP-5 | Circuit breaker overhead (abierto) | `_health[key] = {"failures": 5.0, "last_check": time.time()}` | `_is_circuit_open(key)` retorna True, elapsed <1ms |
| TP-6 | fap perf-check ejecución | `fap perf-check` en terminal | 4/4 benchmarks pass, reporte `reports/perf_report.json` generado |
| TP-7 | fap perf-check baseline | `fap perf-check --baseline` | `reports/perf_baseline.json` con tiempos de referencia |
| TP-8 | Independencia de orden | Ejecutar tests en orden inverso | Mismos resultados, sin contaminación entre tests |

**Comando para ejecutar tests:** `pytest tests/stress/test_performance.py -v`
**Comando DX:** `fap perf-check`
