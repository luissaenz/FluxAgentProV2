# Análisis Técnico — Paso 6: Performance & Observabilidad

**Agente:** ds
**Fecha:** 2026-05-01
**Referencia:** `DEVS/plan.md` §Paso 6 (Performance & Observabilidad)
**Estado Fase:** testing — 2/8 pasos completados (phase-state.md)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentFactory.resolve_tools()` existe | grep en `src/crews/factory.py` | ✅ | factory.py:28 — `resolve_tools(allowed_tools: list[str], org_id: str, *, async_mode: bool = False) -> list` |
| 2 | `resolve_tools` acepta lista de strings y org_id | Firma real | ✅ | factory.py:28-30 — parámetros exactos coinciden |
| 3 | `WorkflowDefinition` existe como Pydantic model | grep en `src/flows/workflow_definition.py` | ✅ | workflow_definition.py:57 — `class WorkflowDefinition(BaseModel)` |
| 4 | `WorkflowDefinition` tiene fields: name, description, flow_type, steps, agents, approval_rules, category | Revisión de fields | ✅ | workflow_definition.py:65-71 — 7 fields definidos |
| 5 | `WorkflowDefinition` valida `flow_type` snake_case | field_validator | ✅ | workflow_definition.py:73-83 — regex `^[a-z][a-z0-9_]*$` |
| 6 | `WorkflowDefinition` valida referencias de agentes | model_validator | ✅ | workflow_definition.py:85-95 — `each_step_references_valid_agent` |
| 7 | `WorkflowDefinition` detecta dependencias circulares | model_validator (DFS) | ✅ | workflow_definition.py:97-122 — `no_circular_dependencies` con DFS |
| 8 | `sanitize_output()` existe | grep en `src/mcp/sanitizer.py` | ✅ | sanitizer.py:28 — `def sanitize_output(data: Any) -> Any:` |
| 9 | `sanitize_output` tiene 7 patrones SECRET_PATTERNS | Revisión de código | ✅ | sanitizer.py:17-25 — Stripe live/test, Bearer, Basic, Slack, GitHub, Google |
| 10 | `sanitize_output` soporta str/dict/list/primitive dispatch | Revisión de código | ✅ | sanitizer.py:39-47 — isinstance branching recursivo |
| 11 | `MCPPool.get_tools()` existe | grep en `src/tools/mcp_pool.py` | ✅ | mcp_pool.py:77 — `async def get_tools(self, org_id, server_name, timeout=30, max_retries=3) -> list` |
| 12 | `MCPPool._is_circuit_open()` existe | grep en `mcp_pool.py` | ✅ | mcp_pool.py:60-66 — check failures < 5, half-open tras 60s |
| 13 | `MCPPool.get_tools` chequea circuito abierto antes de conectar | Revisión de flujo | ✅ | mcp_pool.py:101-106 — raise `MCPConnectionError` si abierto |
| 14 | Tests P6.1 (resolve_tools 50 tools) existen | `grep -r "50.*tool" tests/stress/` | ❌ NO EXISTEN | No hay test con threshold 50 tools / <100ms |
| 15 | Tests P6.2 (WorkflowDefinition validation 10 steps, 5 agents) existen | `grep -r "10 steps\|5 agents\|10.*step.*5.*agent" tests/stress/` | ❌ NO EXISTEN | Ningún test con 10 steps / 5 agents y threshold <50ms |
| 16 | Tests P6.3 (sanitize_output 1MB <500ms) existen | `grep -r "1MB\|500ms\|1.*MB.*500" tests/stress/` | ❌ NO EXISTEN | S4.5 existe con 10MB <5s (params diferentes) |
| 17 | Tests P6.4 (MCPPool.get_tools overhead CB) existen | `grep -r "circuito.*abierto.*overhead\|circuit.*check\|<1ms" tests/stress/` | ❌ NO EXISTEN | Ningún test de overhead de circuit breaker |
| 18 | `tests/stress/conftest.py` existe y aísla MCPPool + flow_registry | ls `tests/stress/conftest.py` | ✅ | stress/conftest.py:14-31 — autouse fixtures `_reset_pool` y `_clean_flow_registry` |
| 19 | `tests/stress/__init__.py` existe | ls `tests/stress/__init__.py` | ✅ | Stress tests directory es package |
| 20 | `pytest-benchmark` instalado | grep en pyproject.toml | ❌ NO INSTALADO | pyproject.toml no tiene pytest-benchmark en dev deps |
| 21 | `pytest-timeout` instalado en dev deps | pyproject.toml | ⚠️ | pytest-timeout >=1.5.0 está en dev extras, no en `dev` explícito |
| 22 | `pytest.mark.timeout` configurado en tests existentes | grep `@pytest.mark.timeout` tests/stress/ | ❌ | Stress tests no usan timeout marker — riesgo de hang |

### Discrepancias Encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | Plan dice `time.perf_counter` para benchmarks; tests existentes (S4.x) usan `time.time()` | Menor — `time.time()` suficiente para benchmarks >1ms. P6.1 <100ms y P6.2 <50ms no requieren perf_counter. P6.4 <1ms SÍ requiere perf_counter. Usar `time.perf_counter_ns()` para P6.4. |
| D2 | Plan no especifica nombre de archivo para tests P6 | Crear `tests/stress/test_performance.py` siguiendo naming de stress tests existentes |
| D3 | `pytest-benchmark` no disponible en dependencias | Benchmarks deben usar `time.perf_counter()` + assertions manuales, mismo patrón que S4.x |
| D4 | S4.5 (10MB <5s) ya existe y es similar a P6.3 (1MB <500ms) pero con parámetros distintos | P6.3 NO es duplicado. Tiene threshold más ajustado. Agregar como tests separados en `test_performance.py` |
| D5 | S4.1 (500 tools <2s) ya existe y testea resolve_tools, similar a P6.1 (50 tools <100ms) | P6.1 es benchmark más fino. Agregar como test separado. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Impacto:** Nulo. Paso 6 no crea/modifica tablas, migraciones, RLS, índices ni constraints.

- ✅ Schema: Sin cambios. Tests de benchmark solo leen — no mutan — schema.
- ✅ Integridad referencial: Sin impacto. No hay foreign keys involucradas.
- ✅ RLS: Sin cambios.
- ✅ Índices: Sin cambios.
- ✅ Tipos de datos: Sin impacto.

**Conclusión:** DATA layer no afectado. Todos los benchmarks son puramente de código sin dependencia de base de datos.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones tocadas (medición, no modificación)

| Función | Archivo | Línea | Lo que testea P6 |
|---|---|---|---|
| `AgentFactory.resolve_tools()` | `src/crews/factory.py` | 28 | P6.1 — latencia con 50 tools en registry |
| `WorkflowDefinition.__init__()` | `src/flows/workflow_definition.py` | 57 | P6.2 — validación Pydantic con 10 steps + 5 agents |
| `sanitize_output()` | `src/mcp/sanitizer.py` | 28 | P6.3 — throughput sanitizer con string 1MB |
| `MCPPool.get_tools()` | `src/tools/mcp_pool.py` | 77 | P6.4 — overhead de circuit breaker check |
| `MCPPool._is_circuit_open()` | `src/tools/mcp_pool.py` | 60 | P6.4 — implementación de check |

### Análisis de performance por función

**P6.1 — resolve_tools 50 tools:**
- Itera `allowed_tools` (lista de 50 strings)
- Por cada string no `mcp:` → llama `tool_registry.get(name, org_id=org_id)` y luego `tool_cls(org_id=org_id)`
- `tool_registry.get()` es O(1) lookup en dict
- Instantiation de 50 objetos ligeros
- **Estimación:** << 100ms. S4.1 demuestra 500 tools en <2s → 50 tools deberían tomar ~200ms / 10 = ~20ms.
- **Riesgo:** Si algun tool tiene init pesado o IO, puede exceder threshold. Tests deben usar mock tools con init mínimo.

**P6.2 — WorkflowDefinition 10 steps + 5 agents:**
- Crea instancia Pydantic con 10 StepDefinition + 5 AgentDefinition + 1 ApprovalRule
- Ejecuta 2 model_validators: cross-reference de roles (O(n*m)) + detección de ciclos DFS (O(V+E) con V=10, E≤10)
- Pydantic v2 usa dataclass-like internals con validación en Rust (pydantic-core)
- **Estimación:** << 50ms. Modelo con 10 steps es trivial para pydantic-core.
- **Riesgo:** DFS validator podría ser O(2^V) en el peor caso si hay dependencias densas, pero con V=10 es despreciable.

**P6.3 — sanitize_output 1MB:**
- Itera 7 patrones regex sobre string de 1MB
- Cada pattern.sub() hace scan completo + reemplazos
- Con 7 patrones → 7 pases completos de 1MB = 7MB procesados
- Sin optimización (early exit, pattern fusion)
- **Estimación:** ~100-200ms en CPython 3.12. S4.5 demuestra 10MB <5s → 1MB debería ser ~100-300ms.
- **Riesgo:** Regex catastrófico si patterns tienen backtracing. Revisar: `re.compile(r"Bearer [a-zA-Z0-9\-._~+/]+=*")` — el `+` greedy seguido de `=*` puede causar backtracking en strings largos sin match. A 1MB, esto podría degradar performance significativamente.

**⚠️ RIESGO IDENTIFICADO — Pattern Bearer:**
```python
re.compile(r"Bearer [a-zA-Z0-9\-._~+/]+=*")
```
El `+` greedy seguido de `=*` causa backtracking cuando `=` no está presente. En un string de 1MB sin Bearer tokens, cada posición que matchea "Bearer " (o cerca) causa backtracking O(n). **Benchmark P6.3 es diagnóstico para detectar esta degradación.** Si P6.3 falla, fix: cambiar `+` a `+?` (lazy) o anclar a start/end con contextos.

**P6.4 — MCPPool.get_tools circuit check overhead:**
- `_is_circuit_open()`: 2 dict lookups + 1 float comparison + 1 subtraction + 1 compare
- En ruta abierta: solo `_is_circuit_open()` → dict lookups → return True → raise MCPConnectionError
- Sin IO, sin red
- **Estimación:** << 1ms. Probablemente ~0.001-0.01ms (microsegundos).
- **Riesgo mínimo.**

### Patrones de código existentes usables

- **Mock de tools:** `_register_mock_tools()` / `_unregister_mock_tools()` en `test_concurrency.py:41-58` — patrón directo de manipulación de `tool_registry._tools`.
- **Reset de pool:** `MCPPool.reset()` en fixtures de `stress/conftest.py:14-19` — autouse antes/después de cada test.
- **Benchmark con time:** `start = time.time()` + `elapsed = time.time() - start` + `assert elapsed < N` en S4.x.

### Modularidad

Benchmarks son tests independientes, sin acoplamiento entre sí. Cada test mide una función distinta. Alto paralelismo.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Impacto:** Nulo. Paso 6 no crea/modifica endpoints, middleware, rutas ni contratos de API.

- ✅ Endpoints: Sin cambios.
- ✅ Middleware: Sin cambios.
- ✅ Flujos: Benchmarks ejercen funciones internas, no via HTTP.
- ✅ Contratos: Sin cambios.
- ✅ Error handling: Sin cambios.

**Conclusión:** Backend layer no modificado. Todas las funciones bajo benchmark son de capa de servicios/utilidades internas.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
Plan Paso 6 (4 benchmarks)
├── P6.1 → AgentFactory.resolve_tools() → mide tiempo de resolución
├── P6.2 → WorkflowDefinition() → mide tiempo de validación Pydantic
├── P6.3 → sanitize_output() → mide throughput de sanitización
└── P6.4 → MCPPool.get_tools() → mide overhead de circuit breaker
```

### Coherencia

- P6.1 complementa S4.1 (500 tools <2s) con threshold más fino (50 tools <100ms). Relación estrés → benchmark.
- P6.3 complementa S4.5 (10MB <5s) con threshold más ajustado (1MB <500ms). Misma función, diferente escala.
- P4.2 (WorkflowDefinition con 20 niveles de nesting) ya valida que no hay RecursionError. P6.2 mide tiempo de validación real con carga estructural.
- **Todos los benchmarks son realizables con la arquitectura existente.** No requieren cambios en código fuente.

### Gaps y ambigüedades

1. **File name no especificado:** Plan no dice dónde crear los tests. Recomendación: `tests/stress/test_performance.py` — consistente con naming de stress tests, y comparte conftest.py existente que ya aísla MCPPool y flow_registry.

2. **P6.4 ambigüedad:** "MCPPool.get_tools con circuito cerrado vs abierto" — ¿debe medir ambos estados o solo la diferencia? Interpretación: medir tiempo de `get_tools()` en estado cerrado (pasa el check, intenta conectar) vs abierto (falla rápido). Pero conectar requiere mock de conexión. **Solución:** Medir solo el overhead del CB check inyectando estado directamente en `_health[key]`. No intentar conexión real — benchmark de overhead, no de integración.

3. **Observabilidad no cubierta:** El paso se llama "Performance & Observabilidad" pero **no hay tests de observabilidad**. El plan menciona "metrics" pero P6.1-P6.4 son solo benchmarks de latencia. No hay tests de logging, métricas de structlog, tracing, ni emisión de eventos de performance. Esto es un gap.

4. **Sin CLI/tooling de benchmark:** No hay `fap benchmark` o comando similar para ejecutar solo los tests de performance. Tampoco hay script para hacer warmup (JIT compilation) antes de medir.

### DX & Tooling — Propuesta Obligatoria

```
### Herramienta Propuesta: `fap benchmark [paso]`
- **Qué automatiza:** Ejecuta benchmarks del Paso 6 (o paso específico) con warmup,
  reporta métricas formateadas (min/avg/max/p95), y compara contra thresholds del plan.
- **Tipo:** Comando CLI (extensión de src/cli/commands/)
- **Cómo se usa:**
  ```bash
  fap benchmark 6                    # todos los benchmarks del paso 6
  fap benchmark 6 --only p6.1,p6.3  # solo subconjunto
  fap benchmark 6 --json            # output machine-readable
  fap benchmark all                 # todos los pasos con benchmarks
  ```
- **Qué automatiza:**
  - Warmup (3 iteraciones descartadas)
  - Ejecución N iteraciones (configurable vía `--samples`, default 10)
  - Cálculo de min/avg/max/p95
  - Verificación contra threshold del plan
  - Reporte formateado con PASS/FAIL por benchmark
  - Output JSON para integración CI
- **Impacto para el usuario final:**
  - No necesita leer tests para saber si performance regresionó
  - Comparación histórica entre ejecuciones
  - Detección temprana de degradación (ej: regex catastrófico en sanitizer)
- **Prioridad:** Tarea 0 — implementar antes que los tests de benchmark. El CLI usará
  pytest internamente pero agregará warmup, muestreo y reporte.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] P6.1: resolve_tools(50 tools, org_id) completa en <100ms
✅ [CODE] P6.2: WorkflowDefinition validación con 10 steps + 5 agents completa en <50ms
✅ [CODE] P6.3: sanitize_output(string 1MB con secretos) completa en <500ms
✅ [CODE] P6.4: MCPPool.get_tools() con circuito abierto retorna en <1ms
✅ [CODE] P6.4: MCPPool.get_tools() overhead de check (cerrado vs abierto) <1ms
✅ [DX] fap benchmark 6 ejecuta los 4 benchmarks y reporta PASS/FAIL
✅ [DX] fap benchmark 6 --json produce output parseable
✅ [FULLSTACK] Todos los benchmarks corren sin LLM real, sin DB real, sin MCP real
✅ [STABILITY] Benchmarks no se afectan entre sí (orden independiente)
⚠️ [GAP] Observabilidad no cubierta — sin tests de logging estructurado ni métricas
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: Regex catastrófico en sanitizer | **Alta** | Pattern `Bearer [a-zA-Z0-9\-._~+/]+=*` con backtracking en strings 1MB sin Bearer tokens. Dependencia de implementation de `re` en CPython. | P6.3 como test diagnóstico. Si falla, fix pattern a `+?` o anclar con lookahead/lookbehind. |
| R2: Fluctuación de benchmark en CI | **Media** | Tiempos de CPU no deterministas en CI (contenedores compartidos, CPU steal). Thresholds pueden fallar intermitentemente. | Usar `pytest.mark.flaky(reruns=2)` para benchmarks O usar factor de tolerancia (±20%). Documentar en TESTING.md. |
| R3: P6.4 no mide lo que promete | **Media** | `get_tools()` en estado cerrado intenta conexión real. Benchmark mide overhead de CB + intento de conexión (con timeout). Sin mock, el tiempo incluye conexión fallida → threshold <1ms imposible. | Mockear conexión: pre-cargar `_adapters[key]` con MagicMock que tenga `.tools` vacío. Así CB check + return de tools mide solo overhead. |
| R4: Warmup no considerado | **Baja** | CPython JIT (PEP 744, Python 3.13+) puede optimizar funciones después de N llamadas. Primer benchmark mide Cold Start, no steady-state. | Agregar warmup explícito (3 iteraciones descartadas) en CLI `fap benchmark`. Para tests directos de pytest, al menos 1 iteración de warmup. |
| R5: P6.2 depende de pydantic-core versión | **Baja** | Actualizaciones de pydantic pueden cambiar performance de validación significativamente. Threshold <50ms puede fallar en versiones futuras. | Documentar versión de pydantic en TESTING.md. Si falla por upgrade, re-evaluar threshold. |
| R6: Observabilidad ausente crea gap en certificación | **Media** | Paso se titula "Performance & Observabilidad" pero plan solo cubre performance. Observabilidad (métricas, tracing, logs) no es testeada. | Agregar al menos 1 test de estructura de log (structlog output tiene campos esperados) o métrica de emisión. Sugerir en roadmap. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap benchmark` CLI | FULLSTACK/DX | Media | 2h | Ninguna | → verificar: `fap benchmark 6 --json` produce salida JSON con 4 entradas y thresholds |
| 1 | Crear `tests/stress/test_performance.py` con estructura base | CODE | Baja | 0.5h | Tarea 0 | → verificar: archivo existe, importable, `pytest --collect-only tests/stress/test_performance.py` descubre 4+ tests |
| 2 | Implementar P6.1: benchmark resolve_tools 50 tools <100ms | CODE | Baja | 1h | Tarea 1 | → verificar: `pytest tests/stress/test_performance.py::TestP6_1ResolveTools50 -v` pasa con tiempo <100ms |
| 3 | Implementar P6.2: benchmark WorkflowDefinition 10 steps + 5 agents <50ms | CODE | Baja | 1h | Tarea 1 | → verificar: Pydantic validation de 10 steps + 5 agents completa en <50ms |
| 4 | Implementar P6.3: benchmark sanitize_output 1MB <500ms | CODE | Baja | 1h | Tarea 1 | → verificar: `sanitize_output(string_1mb)` completa en <500ms. Si falla → revisar pattern Bearer (R1) |
| 5 | Implementar P6.4: benchmark MCPPool.get_tools overhead CB | CODE | Media | 1.5h | Tarea 1 | → verificar: mock de `_adapters[key]` con MagicMock + `.tools`, medir overhead de `_is_circuit_open()` tanto abierto como cerrado, ambos <1ms |
| 6 | Documentar en CLI + TESTING.md | FULLSTACK/DX | Baja | 0.5h | Tareas 0-5 | → verificar: `fap benchmark 6 --help` documenta flags, `TESTING.md` tiene sección "Performance Benchmarks (Paso 6)" |
| 7 | Validar flujo completo | FULLSTACK | Baja | 0.5h | Tareas 0-6 | → verificar: `fap benchmark 6` reporta 4/4 PASS, `pytest tests/stress/test_performance.py -v` 4/4 pass, sin LLM/DB/MCP real |

### Detalles de implementación por tarea

**Tarea 1 — Estructura del archivo:**
```python
"""Performance benchmarks P6.1-P6.4.

P6.1: resolve_tools latency with 50 registry tools (<100ms)
P6.2: WorkflowDefinition validation with 10 steps, 5 agents (<50ms)
P6.3: sanitize_output throughput with 1MB string (<500ms)
P6.4: MCPPool.get_tools circuit breaker overhead (<1ms)
"""
```

- Ubicación: `tests/stress/test_performance.py`
- Hereda fixtures autouse de `tests/stress/conftest.py` (MCPPool reset, flow_registry restore)
- Sin dependencia de fixtures de conftest.py global

**Tarea 2 — P6.1 detalles:**
- Reusar helpers `_register_mock_tools` / `_unregister_mock_tools` de `test_concurrency.py`
- Pasar `count=50` y threshold `<100ms` (vs S4.1 que usa 500 tools / <2s)
- Usar `time.perf_counter_ns()` para precisión (no `time.time()`)
- Medir con warmup de 1 iteración descartada
```python
def test_resolve_tools_50_under_100ms(self):
    names = _register_mock_tools(50)
    org_id = str(uuid4())
    try:
        # warmup
        AgentFactory.resolve_tools(names[:1], org_id, async_mode=False)
        start = time.perf_counter_ns()
        tools = AgentFactory.resolve_tools(names, org_id, async_mode=False)
        elapsed_ns = time.perf_counter_ns() - start
        assert elapsed_ns < 100_000_000, f"Took {elapsed_ns/1e6:.1f}ms"
        assert len(tools) == 50
    finally:
        _unregister_mock_tools(names)
```

**Tarea 3 — P6.2 detalles:**
- Construir 10 StepDefinitions con diferentes `agent_role`s (de 5 agents disponibles)
- 5 AgentDefinitions con roles: agent_a..agent_e
- Incluir 2 ApprovalRules para overhead adicional
- Medir solo validación Pydantic (construcción de dict no incluida)
```python
def test_workflow_definition_10_steps_5_agents_under_50ms(self):
    steps = [_make_step_definition(f"agent_{i % 5}") for i in range(10)]
    agents = [_make_agent_definition(f"agent_{i}") for i in range(5)]
    definition = {
        "name": "Perf Test Flow", "description": "x" * 10,
        "flow_type": "perf_test", "steps": steps, "agents": agents,
    }
    start = time.perf_counter_ns()
    wd = WorkflowDefinition(**definition)
    elapsed_ns = time.perf_counter_ns() - start
    assert elapsed_ns < 50_000_000, f"Validation took {elapsed_ns/1e6:.1f}ms"
```

**Tarea 4 — P6.3 detalles:**
- String de 1MB = 1_048_576 bytes
- Reusar `_make_10mb_string()` de `test_edge_cases.py` o crear helper similar para 1MB
- Medir solo `sanitize_output()`
```python
def test_sanitize_1mb_under_500ms(self):
    text = _make_1mb_string(1_048_576)
    start = time.perf_counter_ns()
    result = sanitize_output(text)
    elapsed_ns = time.perf_counter_ns() - start
    assert elapsed_ns < 500_000_000, f"Sanitize took {elapsed_ns/1e6:.1f}ms"
    assert "[REDACTED]" in result
```

**Tarea 5 — P6.4 detalles:**
- NO requiere conexión MCP real
- Inyectar estado en `_health[key]` para simular circuito abierto y cerrado
- Pre-cargar `_adapters[key]` con MagicMock que tenga `.tools` para evitar que get_tools intente conectar
- Medir ambas rutas (abierto y cerrado), ambas deben ser <1ms
```python
@pytest.mark.asyncio
async def test_circuit_breaker_check_overhead_open_under_1ms(self):
    pool = MCPPool.get()
    org_id, server = str(uuid4()), "test-server"
    key = f"{org_id}:{server}"
    # Seed circuit open: 5 failures, recent
    pool._health[key] = {"failures": 5.0, "last_check": time.time()}
    start = time.perf_counter_ns()
    with pytest.raises(MCPConnectionError):
        await pool.get_tools(org_id, server)
    elapsed_ns = time.perf_counter_ns() - start
    assert elapsed_ns < 1_000_000, f"Open circuit check took {elapsed_ns/1e3:.1f}µs"

@pytest.mark.asyncio
async def test_circuit_breaker_check_overhead_closed_under_1ms(self):
    pool = MCPPool.get()
    org_id, server = str(uuid4()), "test-server"
    key = f"{org_id}:{server}"
    # Seed circuit closed and adapter cached (no real connection)
    pool._health[key] = {"failures": 0.0, "last_check": time.time()}
    mock_adapter = MagicMock()
    mock_adapter.tools = []
    pool._adapters[key] = mock_adapter
    start = time.perf_counter_ns()
    tools = await pool.get_tools(org_id, server)
    elapsed_ns = time.perf_counter_ns() - start
    assert elapsed_ns < 1_000_000, f"Closed circuit check took {elapsed_ns/1e3:.1f}µs"
    assert tools == [], "Should return cached adapter tools"
```

### Tiempo total estimado: **7 horas**

---

## 🔮 Roadmap

### Issues descubiertas durante análisis que afectan pasos futuros

1. **Observabilidad no cubierta:** Paso 6 se titula "Performance & Observabilidad" pero plan solo cubre benchmarks de performance. No hay tests de log structure, métricas de structlog, tracing, o emisión de eventos de diagnóstico. **Sugerencia:** Agregar como mejora post-certificación o expandir Paso 7 para cubrirlo.

2. **Pattern regex Bearer potencialmente catastrófico:** `Bearer [a-zA-Z0-9\-._~+/]+=*` en `sanitizer.py:20`. Backtracking O(n) en strings sin Bearer. El benchmark P6.3 es diagnóstico: si falla, fix pattern con `+?` o anclaje contextual.

3. **Sin warmup en benchmarks:** Tests de pytest miden cold start. Para mediciones precisas en CI, el CLI `fap benchmark` debe implementar warmup de N iteraciones descartadas. Considerar en Tarea 0.

4. **pytest-timeout en dev extras, no en dev:** `pyproject.toml` tiene `pytest-timeout>=1.5.0` pero no está listado en `[project.optional-dependencies] dev`. Verificar si está instalado. Si no, agregarlo como dependencia dev para tener hard timeouts en benchmarks (evitar hangs en CI).

### Decisiones de diseño

- **Benchmarks sin pytest-benchmark:** Se usa `time.perf_counter_ns()` + assertions manual, mismo patrón que tests existentes (S4.x). Esto evita agregar nueva dependencia y mantiene consistencia.
- **Ubicación en `tests/stress/`:** Los benchmarks son variantes de stress tests con thresholds más finos. Comparten helpers y conftest.
- **Sin mock DB para P6.1:** Se usa mismo patrón de registro directo en `tool_registry._tools` que S4.1. Esto evita mockear Supabase y mantiene el benchmark puro (solo CPU/memoria, sin IO).
