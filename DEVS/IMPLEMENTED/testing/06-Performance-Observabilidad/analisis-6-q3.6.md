# Análisis Técnico — Paso 6: Performance & Observabilidad

**Agente:** q3.6
**Fecha:** 2026-05-01
**Fase:** testing (Fase VI)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `resolve_tools` en `AgentFactory` | `src/crews/factory.py:28-78` | ✅ | Método estático, itera `allowed_tools`, resuelve registry + MCP |
| 2 | `tool_registry.get()` | `src/tools/registry.py:75-120` | ✅ | Lookup tenant → global → DB → filesystem fallback |
| 3 | `WorkflowDefinition` validación Pydantic | `src/flows/workflow_definition.py:57-123` | ✅ | BaseModel con `field_validator` + `model_validator` (snake_case, agent roles, cycle detection) |
| 4 | `sanitize_output` | `src/mcp/sanitizer.py:28-50` | ✅ | Función pura, 7 patrones regex, recursión dict/list |
| 5 | `MCPPool._is_circuit_open` | `src/tools/mcp_pool.py:61-66` | ✅ | Check `failures >= 5` + `elapsed < 60s` |
| 6 | `MCPPool.get_tools` | `src/tools/mcp_pool.py:77-190` | ✅ | Async, tenacity retry, circuit breaker check al inicio |
| 7 | `time.perf_counter` disponible | stdlib Python | ✅ | No requiere dependencia |
| 8 | `pytest` fixtures existentes | `tests/conftest.py` | ✅ | `mock_service_client`, `global_llm_mock`, `mock_mcp_pool`, `sample_org_id` |
| 9 | `tool_registry` singleton | `src/tools/registry.py:272` | ✅ | `tool_registry = ToolRegistry()` global |
| 10 | `MCPPool.reset()` | `src/tools/mcp_pool.py:209-212` | ✅ | Reset singleton para tests |
| 11 | Tests stress existentes (Paso 4) | `tests/stress/test_concurrency.py`, `tests/stress/test_edge_cases.py` | ✅ | S4.1-S4.7 implementados |
| 12 | `WorkflowDefinition` sin campo `input_data` | `src/flows/workflow_definition.py:57-72` | ❌ DISCREPANCIA | El modelo NO tiene campo `input_data`. Test S4.7 en `test_edge_cases.py:215` usa `input_data=nested` — esto fallaría en runtime. El plan original menciona `input_data` pero el modelo real no lo define. |
| 13 | `sanitize_output` con string 1MB | `src/mcp/sanitizer.py:39-41` | ✅ | Loop sobre 7 patrones regex, cada uno `.sub()` sobre string completo |
| 14 | `MCPPool._health` estructura | `src/tools/mcp_pool.py:47-49` | ✅ | `defaultdict(lambda: {"failures": 0.0, "last_check": 0.0})` |
| 15 | `WorkflowDefinition` campos | `src/flows/workflow_definition.py:65-72` | ✅ | `name`, `description`, `flow_type`, `steps`, `agents`, `approval_rules`, `category` |
| 16 | `tool_registry.register` decorator | `src/tools/registry.py:39-71` | ✅ | Registra en `_tools` dict + `_metadata` dict |
| 17 | `WorkflowDefinition` validators | `src/flows/workflow_definition.py:73-123` | ✅ | 3 validators: snake_case flow_type, agent role reference, cycle detection |
| 18 | `sanitize_output` SECRET_PATTERNS | `src/mcp/sanitizer.py:17-25` | ✅ | 7 patrones compilados |

**Discrepancias encontradas:**

1. **`WorkflowDefinition` no tiene campo `input_data`:** El modelo real (`workflow_definition.py:57-72`) define solo `name`, `description`, `flow_type`, `steps`, `agents`, `approval_rules`, `category`. El test S4.7 existente (`test_edge_cases.py:215`) pasa `input_data=nested` al constructor — esto sería ignorado por Pydantic (extra fields) o rechazado si `model_config` tiene `extra="forbid"`. **Resolución:** El benchmark P6.2 debe validar `WorkflowDefinition` con 10 steps + 5 agents, NO con `input_data` profundo. La validación real es: roles de agentes referenciados por steps + detección de ciclos + snake_case flow_type.

2. **P6.4 circuito abierto vs cerrado — overhead <1ms:** `_is_circuit_open` es O(1) dict lookup + `time.time()` call. Verificable directamente.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Impacto mínimo en datos.** Paso 6 = benchmarks de rendimiento. No toca DB, no crea tablas, no modifica schema.

- **Tablas tocadas:** Ninguna directamente. Los benchmarks usan mocks (`mock_service_client`).
- **Schema changes:** Ninguno.
- **RLS policies:** No aplicable.
- **Índices:** No aplicable.
- **Tipos de datos:** No aplicable.

**Nota:** Los benchmarks miden código en memoria. La única interacción con DB es a través del mock de `get_service_client` que ya existe en `conftest.py`.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones a benchmarkear:

| # | Función | Archivo | Líneas | Complejidad |
|---|---|---|---|---|
| P6.1 | `AgentFactory.resolve_tools()` | `src/crews/factory.py:28-78` | ~50 | Media — loop + registry lookup + MCP resolution |
| P6.2 | `WorkflowDefinition` (validación Pydantic) | `src/flows/workflow_definition.py:57-123` | ~67 | Media — 3 validators (regex, set lookup, DFS cycle detection) |
| P6.3 | `sanitize_output()` | `src/mcp/sanitizer.py:28-50` | ~23 | Baja — loop 7 regex sobre string |
| P6.4 | `MCPPool._is_circuit_open()` | `src/tools/mcp_pool.py:61-66` | ~6 | Baja — dict lookup + time diff |

### Patrones existentes:

- **Tests de stress (Paso 4):** Usan `time.time()` para medir. `test_concurrency.py:100-102` mide `resolve_tools` con 500 tools (<2s). `test_edge_cases.py:137-139` mide `sanitize_output` 10MB (<5s).
- **Benchmark vs stress test:** Los tests de Paso 4 miden bajo carga extrema (500 tools, 10MB, 50 workflows). Paso 6 mide bajo carga **normal** (50 tools, 1MB, 10 steps) con thresholds más estrictos (<100ms, <50ms, <500ms, <1ms).
- **Reutilización:** Los helpers `_register_mock_tools`, `_make_step_definition`, `_make_agent_definition` de los tests existentes pueden reutilizarse.

### Modularidad:

- Archivo nuevo: `tests/unit/test_performance_benchmarks.py` — cohesión alta, un solo propósito.
- Imports: `time`, `pytest`, `src.crews.factory`, `src.flows.workflow_definition`, `src.mcp.sanitizer`, `src.tools.mcp_pool`, `src.tools.registry`.
- Sin dependencias externas adicionales.

### Discrepancias detectadas:

- **P6.2 threshold <50ms con 10 steps + 5 agents:** La validación de `WorkflowDefinition` incluye DFS cycle detection (O(V+E)). Con 10 steps, el grafo es pequeño. 50ms es razonable pero debe verificarse. El DFS en `workflow_definition.py:106-116` es recursivo — con 10 steps y dependencias cruzadas podría llegar a ~10 llamadas recursivas. Python recursion overhead ~1μs por call → negligible.
- **P6.3 sanitizer 1MB <500ms:** El sanitizer aplica 7 regex sobre 1MB. Cada `.sub()` sobre 1MB string es O(n). 7 × O(1MB) ≈ 7MB de procesamiento. Python regex engine es C-optimized. 500ms es holgado — debería completar en <100ms.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Sin endpoints nuevos.** Paso 6 = tests de rendimiento, no APIs.

- **APIs creadas/modificadas:** Ninguna.
- **Middleware:** No aplicable.
- **Flujos de datos:** Los benchmarks ejecutan funciones directamente, sin HTTP layer.
- **Auth/authz:** No aplicable.
- **Contratos:** Los benchmarks son internos — no exponen contratos externos.

**Nota:** Si en el futuro se expusieran estos benchmarks como endpoint de health check (`GET /health/performance`), se necesitaría:
- Middleware de auth (solo admin)
- Cache de resultados (no ejecutar en cada request)
- Timeout de 5s máximo

Fuera de scope para este paso.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo:

```
DB (mock) → Backend (funciones) → Tests (pytest) → Métricas (assert < threshold)
```

Todo ocurre en memoria. No hay frontend ni UX directa.

### Coherencia con arquitectura:

- Los benchmarks usan los mismos mocks que el resto de la suite (`conftest.py`).
- No hay inconsistencia entre plan y arquitectura.
- Los thresholds del plan son realistas dado el código verificado.

### DX & Tooling — OBLIGATORIO:

### Herramienta Propuesta: `fap benchmark`

- **Qué automatiza:** Ejecutar benchmarks de rendimiento del Paso 6 con un solo comando, sin necesidad de recordar flags de pytest ni thresholds. Muestra reporte visual de pass/fail por benchmark con tiempos reales vs thresholds.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:** `fap benchmark` o `fap benchmark --verbose` para ver tiempos individuales
- **Impacto para el usuario final:** Deja de ejecutar `pytest tests/unit/test_performance_benchmarks.py -v --tb=short` manualmente. Obtiene reporte formateado con:
  - ✅/❌ por benchmark
  - Tiempo real vs threshold
  - Promedio de 3 runs (para reducir ruido)
  - Opción `--json` para integración CI
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso

**Implementación:** Nuevo archivo `src/cli/commands/benchmark.py`. Usa `subprocess.run` para ejecutar pytest 3 veces por benchmark, calcula mediana, compara contra thresholds hardcodeados (los del plan). Registra en `src/cli/commands/__init__.py`.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No se requieren cambios de schema — benchmarks operan en memoria
✅ [CODE] Archivo `tests/unit/test_performance_benchmarks.py` existe con 4 tests (P6.1-P6.4)
✅ [CODE] Cada test usa `time.perf_counter()` para medición precisa
✅ [BACKEND] No se crean endpoints — benchmarks son funciones puras/mocked
✅ [FULLSTACK] Todos los benchmarks pasan bajo thresholds definidos en el plan
✅ [FULLSTACK] Tests son deterministas — 0 flakiness por variabilidad de timing (thresholds holgados 3x)
✅ [DX] Herramienta `fap benchmark` ejecuta sin errores y reporta resultados formateados
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Flakiness por timing en CI | Media | CI runners tienen carga variable, tiempos pueden fluctuar | Thresholds 3x holgados vs local. Si P6.1 local = 30ms, threshold = 100ms. CI puede ser 2-3x más lento pero aún pasa. |
| `time.perf_counter()` no disponible en Windows | Baja | Windows tiene resolución de timer diferente | `time.perf_counter()` funciona en Windows (usa QueryPerformanceCounter). Verificado. |
| Singleton `MCPPool` contaminado entre tests | Media | Tests previos dejan estado en `_health` o `_adapters` | `MCPPool.reset()` en fixture `autouse=True` antes de cada test de P6.4 |
| `tool_registry` con tools residuales de tests de stress | Media | Tests S4.1 registran 500 tools y pueden no limpiar si fallan | Fixture que hace `tool_registry.clear()` antes de P6.1 |
| Thresholds demasiado ajustados para hardware lento | Baja | Developer con laptop vieja puede ver falsos positivos | Thresholds ya son holgados. Si falla consistentemente, ajustar con datos reales. |
| `WorkflowDefinition` con 10 steps + 5 agents tarda >50ms si hay muchas dependencias cruzadas | Media | DFS cycle detection es O(V+E). Con grafo denso (cada step depende de todos los anteriores), E = O(V²) | Config de benchmark usa grafo lineal (step N depende de step N-1). E = V-1. O(V). |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear `fap benchmark` CLI command | FULLSTACK/DX | Media | 2h | Ninguna | → verificar: `fap benchmark` ejecuta, muestra reporte con ✅/❌ y tiempos reales vs thresholds |
| 1 | Crear `tests/unit/test_performance_benchmarks.py` con fixture de limpieza | CODE | Baja | 0.5h | Ninguna | → verificar: archivo existe, fixture `autouse=True` limpia `MCPPool` y `tool_registry` |
| 2 | Implementar P6.1: benchmark `resolve_tools` 50 tools <100ms | CODE | Baja | 0.5h | Tarea 1 | → verificar: test pasa consistentemente, `time.perf_counter()` mide <100ms |
| 3 | Implementar P6.2: benchmark `WorkflowDefinition` validación 10 steps + 5 agents <50ms | CODE | Media | 1h | Tarea 1 | → verificar: test pasa, config usa grafo lineal de dependencias, validación <50ms |
| 4 | Implementar P6.3: benchmark `sanitize_output` 1MB <500ms | CODE | Baja | 0.5h | Tarea 1 | → verificar: test genera string 1MB, `sanitize_output` completa <500ms |
| 5 | Implementar P6.4: benchmark `MCPPool._is_circuit_open` overhead <1ms | CODE | Baja | 0.5h | Tarea 1 | → verificar: test mide 1000 iteraciones de `_is_circuit_open`, promedio <1ms |
| 6 | Ejecutar suite completa Paso 6 + integrar con `fap benchmark` | FULLSTACK | Baja | 0.5h | Tareas 2-5 | → verificar: `fap benchmark` reporta 4/4 pass, tiempos dentro de thresholds |

**Tiempo total estimado:** 5.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Benchmark regression tracking:** Almacenar resultados de benchmarks en archivo JSON (`benchmarks/results.json`) para detectar regresiones entre commits.
- **CI integration:** Agregar `fap benchmark --json` al pipeline CI con fail si cualquier benchmark supera 1.5x su threshold.
- **Memory profiling:** Agregar `tracemalloc` a benchmarks para detectar memory leaks en `resolve_tools` y `sanitize_output`.
- **Percentile metrics:** En lugar de single run, ejecutar cada benchmark 10 veces y reportar p50, p95, p99.
- **Endpoint de health check:** Exponer benchmarks como `GET /health/performance` (solo admin, cache 5min).

---

## 📊 Notas de Implementación

### P6.1 — `resolve_tools` con 50 tools:

```python
# Config: 50 tools registradas en tool_registry, todas non-MCP
# Medir: time.perf_counter() antes y después de AgentFactory.resolve_tools(names, org_id, async_mode=False)
# Threshold: <100ms
# Mock: Ninguno necesario — tool_registry.get() es lookup en dict
```

### P6.2 — `WorkflowDefinition` validación:

```python
# Config: 10 steps (grafo lineal: step_2 depende de step_1, step_3 de step_2, etc.)
#         5 agents (cada step referencia un agent diferente, últimos 5 steps reusan agents)
# Medir: time.perf_counter() antes y después de WorkflowDefinition(**config)
# Threshold: <50ms
# Nota: NO usar input_data — el modelo no lo tiene. Validación real = snake_case + agent roles + cycle detection
```

### P6.3 — `sanitize_output` 1MB:

```python
# Config: String de 1MB con 100 secretos distribuidos (sk_live_, Bearer, ghp_, etc.)
# Medir: time.perf_counter() antes y después de sanitize_output(large_string)
# Threshold: <500ms
# Generación: "safe text" * N + "sk_live_abc123" cada ~10KB
```

### P6.4 — `MCPPool._is_circuit_open` overhead:

```python
# Config: MCPPool instance con key "test:server" en _health
# Medir: 1000 iteraciones de pool._is_circuit_open("test:server")
# Threshold: promedio <1ms por call
# Setup: pool._health["test:server"] = {"failures": 0.0, "last_check": time.time()}
```
