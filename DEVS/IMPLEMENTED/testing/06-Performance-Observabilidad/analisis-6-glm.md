# Análisis Técnico — Paso 6: Performance & Observabilidad

> **Paso:** 6 — Performance & Observabilidad
> **Agente:** glm
> **Fecha:** 2026-05-01
> **Fase:** VI — testing

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentFactory.resolve_tools()` existe | firma: `resolve_tools(allowed_tools: list[str], org_id: str, *, async_mode: bool = False) -> list` | ✅ VERIFICADO | `src/crews/factory.py:28-78` |
| 2 | `WorkflowDefinition` clases y validators | `AgentDefinition`, `StepDefinition`, `ApprovalRule`, `WorkflowDefinition` con `flow_type_must_be_snake_case`, `each_step_references_valid_agent`, `no_circular_dependencies` | ✅ VERIFICADO | `src/flows/workflow_definition.py:15-123` |
| 3 | `sanitize_output()` firma | `sanitize_output(data: Any) -> Any` — función pura, 7 `SECRET_PATTERNS` | ✅ VERIFICADO | `src/mcp/sanitizer.py:28-50` |
| 4 | `MCPPool._is_circuit_open()` firma | `_is_circuit_open(self, key: str) -> bool` — chequa `health["failures"] < 5` y `elapsed < 60` | ✅ VERIFICADO | `src/tools/mcp_pool.py:60-66` |
| 5 | `MCPPool.get_tools()` firma | `async def get_tools(self, org_id: str, server_name: str, timeout: int = 30, max_retries: int = 3) -> list` | ✅ VERIFICADO | `src/tools/mcp_pool.py:77-190` |
| 6 | `tool_registry.get()` lookup orden | tenant-scoped → global → DB → filesystem fallback | ✅ VERIFICADO | `src/tools/registry.py:75-120` |
| 7 | `ToolRegistry._instances` cache | `get_or_create()` cachea instancias singleton por nombre lowercase | ✅ VERIFICADO | `src/tools/registry.py:223-228` |
| 8 | Stress test S4.1 ya existe | `test_resolve_tools_500_completes_under_2s` — threshold 2s, 500 tools | ✅ VERIFICADO | `tests/stress/test_concurrency.py:94-108` |
| 9 | Stress test S4.5 ya existe | `test_sanitize_10mb_under_5s` — threshold 5s, 10MB | ✅ VERIFICADO | `tests/stress/test_edge_cases.py:132-147` |
| 10 | Stress test S4.7 ya existe | `test_workflow_definition_deep_validation_no_timeout` — threshold 2s | ⚠️ PARCIAL | `tests/stress/test_edge_cases.py:222-240` — usa `_make_nested_dict(20)` dict, NO es WorkflowDefinition con 10 steps/5 agents |
| 11 | `MCPPool.reset()` disponible | `@classmethod reset(cls) -> None` — limpia singleton | ✅ VERIFICADO | `src/tools/mcp_pool.py:210-212` |
| 12 | `time.time` usado en circuit breaker | `_record_failure` y `_is_circuit_open` usan `time.time()` directamente | ✅ VERIFICADO | `src/tools/mcp_pool.py:65-70` |
| 13 | Conftest `mock_mcp_pool` fixture | Retorna `MagicMock` con `AsyncMock(return_value=mock_tools)` | ✅ VERIFICADO | `tests/conftest.py:304-316` |
| 14 | `conftest.py` stress tests | `_reset_pool` (autouse) y `_clean_flow_registry` (autouse) | ✅ VERIFICADO | `tests/stress/conftest.py:14-30` |
| 15 | `WorkflowDefinition` NO tiene campo `input_data` | Schema solo tiene: `name, description, flow_type, steps, agents, approval_rules, category` | ❌ DISCREPANCIA | `test_edge_cases.py:215-217` usa `input_data=nested` pero `WorkflowDefinition` no tiene ese campo |
| 16 | `pytest-timeout` en dev deps | `pytest-timeout>=1.5.0` en pyproject.toml | ✅ VERIFICADO | `pyproject.toml:51` |
| 17 | `_MockStressTool` en test_concurrency | Clase auxiliar para stress, acepta `org_id` | ✅ VERIFICADO | `tests/stress/test_concurrency.py:35-39` |
| 18 | `ALLOWED_MODELS` en guardrails | `{"claude-sonnet-4-20250514", "claude-opus-4-20250514", "gpt-4o", "gpt-4-turbo", "groq/llama-3.3-70b-versatile"}` | ✅ VERIFICADO | `src/flows/workflow_guardrails.py:16-22` |

### Discrepancias encontradas:

1. **❌ `input_data` en WorkflowDefinition**: `test_edge_cases.py:215-217` pasa `input_data=nested` a `WorkflowDefinition()`, pero la clase NO define campo `input_data`. Pydantic con `model_config = {}` (sin `extra="allow"`) rechazará campos extra. **P6.2 NO debe repetir este error.** Paso 4 S4.7 ya tiene este bug. P6.2 debe usar schema correcto.

2. **⚠️ Umbral P6.1 vs S4.1**: S4.1 ya testea 500 tools en <2s. P6.1 pide 50 tools en <100ms. Son tests distintos (benchmark fino vs stress), pero la relación es coherente: 500/2s ≈ 250 tools/s implica 50 tools en ~200ms. P6.1 con threshold <100ms requerirá mock más liviano (sin DB/HTTP).

3. **⚠️ Umbral P6.3 vs S4.5**: S4.5 testea 10MB en <5s. P6.3 pide 1MB en <500ms. Proporcionalmente S4.5 → 1MB en ~0.5s = 500ms. P6.3 pide lo mismo pero con input 10x menor. Debería pasar holgadamente.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

Paso 6 es **exclusivamente benchmark/performance**. No modifica schema, no crea tablas, no altera datos.

- ✅ **Schema**: Sin cambios. Tests de performance leen estado existente (registries, health dict) sin escribir en DB.
- ✅ **Integridad referencial**: N/A — no hay FK afectadas.
- ✅ **RLS policies**: N/A — no hay acceso DB real.
- ✅ **Índices**: N/A — no hay queries SQL.
- ✅ **Tipos de datos**: Los benchmarks operan sobre tipos existentes (`list[str]` para tools, `str` para sanitizer, `dict` para WorkflowDefinition).

**Conclusión DATA**: Etapa sin impacto en datos.门槛 de DB real son 0.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases bajo benchmark

| Componente | Archivo | Firma | Complejidad |
|---|---|---|---|
| `AgentFactory.resolve_tools()` | `src/crews/factory.py:28` | `(allowed_tools: list[str], org_id: str, *, async_mode: bool) -> list` | Baja — iteración + lookup |
| `WorkflowDefinition` | `src/flows/workflow_definition.py:57` | Pydantic model con 2 field_validators + 2 model_validators | Media — DFS en ciclos |
| `sanitize_output()` | `src/mcp/sanitizer.py:28` | `(data: Any) -> Any` | Baja — 7 regex sobre str + recursión |
| `MCPPool._is_circuit_open()` | `src/tools/mcp_pool.py:60` | `(self, key: str) -> bool` | Muy baja — 2 comparaciones |

### Patrones a seguir

- ✅ **Tests existentes de performance/stress** en `tests/stress/` usan patrón: `time.perf_counter()` para medir, `autouse=True` fixtures para cleanup, `_register_mock_tools()` para inyectar mocks en registry.
- ✅ **P6.1** debe usar mismo patrón que S4.1 (`_register_mock_tools`) pero con 50 tools y threshold <100ms.
- ✅ **P6.2** debe construir `WorkflowDefinition` con 10 steps + 5 agents (estructura real, no nested dict).
- ✅ **P6.3** debe generar string 1MB con patrones de secreto intercalados.
- ✅ **P6.4** debe medir `_is_circuit_open()` directamente, no `get_tools()` completo.

### Decisiones de ubicación

- **Nuevo archivo**: `tests/stress/test_performance.py` — sigue patrón existente `tests/stress/test_*.py`.
- **No modificar** tests existentes. S4.1/S4.5/S4.7 son stress tests (umbrales amplios). P6.1/P6.3 son benchmarks precisos (umbrales estrictos). Coexisten.

### Calidad y modularidad

- ⚠️ **Duplicación parcial con S4.1/S4.5**: `_make_10mb_string()` de `test_edge_cases.py` se reutiliza conceptualmente en P6.3. Considerar importar helper o mover a `conftest.py` de stress.
- ⚠️ **`_make_step_definition()` y `_make_agent_definition()`** ya existen en `test_concurrency.py` y `test_edge_cases.py`. Deberían estar en `conftest.py` de stress para reutilización. Para P6.2, necesidad de versiones con `depends_on` (S4.7 no tiene).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints: N/A

Paso 6 es 100% internos (registry, Pydantic, sanitizer, MCPPool). No crea/modifica endpoints.

### Middleware: N/A

### Flujos de datos

**P6.1 `resolve_tools` (50 tools)**:
1. `AgentFactory.resolve_tools(["tool_0", ...], org_id, async_mode=False)` itera 50 nombres
2. Cada nombre → `tool_registry.get(name, org_id=org_id)` → lookup en dict `_tools`
3. Cada lookup → `cls(org_id=org_id)` → instanciación
4. **Cuello de botella**: instanciación × 50 clases. Mock `_MockStressTool` es trivial, pero clases reales con `__init__` pueden ser más lentas.
5. **Mocking crítico**: `tool_registry.get()` no debe tocar DB (usar `_tools[name]` directamente). En el benchmark P6.1 con 50 mock tools en `_tools`, el path es L1 (dict lookup) sin DB.

**P6.2 `WorkflowDefinition` validación**:
1. Pydantic parsea JSON → crea objetos `StepDefinition` × 10 + `AgentDefinition` × 5
2. `flow_type_must_be_snake_case` — regex match
3. `each_step_references_valid_agent` — O(steps × agents) = O(50)
4. `no_circular_dependencies` — DFS O(V+E) sobre graph de steps
5. **Cuello de botella**: Para 10 steps, el DFS es trivial. Tiempo dominado por Pydantic parsing.

**P6.3 `sanitize_output` (1MB)**:
1. Si `data` es `str` → itera 7 regex `.sub()` sobre string de 1MB
2. Si `data` es `dict`/`list` → recursión
3. **Cuello de botella**: 7 regex passes sobre 1MB cada una = ~7MB procesados. CPython `re` es C-level, debería estar en sub-500ms.

**P6.4 `MCPPool._is_circuit_open`**:
1. Accede a `self._health[key]` (defaultdict)
2. Compara `health["failures"] < 5` y `time.time() - health["last_check"] < 60`
2. **No hay I/O, no hay DB**. Debe ser <1ms trivialmente.
3. ⚠️ El plan dice "MCPPool.get_tools con circuito cerrado vs abierto". Pero el threshold <1ms es para el **check**, no `get_tools()`. El test debe medir `_is_circuit_open()` directamente, no el flujo completo de `get_tools`.

### Contratos

| Test | Input | Output esperado | Tipo |
|---|---|---|---|
| P6.1 | `resolve_tools(50_nombres, org_id, async_mode=False)` | `list` de 50 tools, elapsed <100ms | Benchmark |
| P6.2 | `WorkflowDefinition(**10_steps_5_agents)` | Instancia válida, elapsed <50ms | Benchmark |
| P6.3 | `sanitize_output(str_1MB)` | `str` con `[REDACTED]`, elapsed <500ms | Benchmark |
| P6.4 | `_is_circuit_open(key)` con failures=0 y failures=5 | `bool`, elapsed <1ms por check | Benchmark |

### Error handling

- P6.1: Si `tool_registry.get()` → `ValueError` para tool inexistente, test falla. Todos los 50 nombres deben existir en `_tools`.
- P6.3: Si sanitizer lanza excepción → test falla. Caso de error ya cubierto en `test_sanitizer.py` S4.10.
- P6.4: `_is_circuit_open()` no lanza excepciones. Siempre retorna `bool`.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: N/A

Paso 6 tests son unitarios/benchmark aislados. No hay flujo DB → Backend → Frontend.

### Coherencia: Deciciones de data/code/backend apoyan al MVP

- ✅ Benchmarks son deterministas (mock puro, sin LLM/DB/MCP).
- ✅ Umbrales son razonables: <100ms para 50 tools, <50ms para Pydantic validation, <500ms para 1MB sanitización, <1ms para circuit check.
- ✅ Tests existentes (S4.1, S4.5, S4.7) usan mocks coherentes — P6 reutiliza patrones.

### Gaps

- ⚠️ **No hay tests de observabilidad**: El título del paso es "Performance & **Observabilidad**" pero el plan solodefine benchmarks de latencia. Falta:
  - Logging estructurado: verificar que `structlog` emite campos correctos en puntos críticos
  - Métricas: no hay emitores de métricas (Prometheus, statsd, etc.)
  - Correlación: `correlation_id` se propaga en `BaseFlowState` pero no se verifica en benchmarks
- ⚠️ **Nombre del archivo sugiere más que latencia**: Si el paso se llama "Performance & Observabilidad", los tests deberían verificar ambos. Actualmente solo cubre performance.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap bench
- **Qué automatiza:** Ejecuta benchmarks de performance con thresholds predefinidos y reporta métricas comparativas entre runs
- **Tipo:** CLI command (extensión de `fap`)
- **Cómo se usa:** `fap bench --step 6` o `fap bench --all` para ejecutar todos los benchmarks
- **Impacto para el usuario final:** Elimina ejecución manual de pytest con flags específicos. Reporta automáticamente qué benchmarks pasan/fallan y times absolutos vs thresholds.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No se modifica schema de DB — tests son read-only sobre estructuras en memoria
✅ [CODE] P6.1: resolve_tools con 50 mock tools completa en <100ms
✅ [CODE] P6.2: WorkflowDefinition con 10 steps + 5 agents valida en <50ms
✅ [CODE] P6.3: sanitize_output con string 1MB completa en <500ms y redacta secretos
✅ [CODE] P6.4: MCPPool._is_circuit_open() check en <1ms tanto cerrado como abierto
✅ [BACKEND] Todos los benchmarks usan mocks puros, sin LLM/DB/MCP reales
✅ [BACKEND] P6.4 mide tiempo del check de circuit breaker, no del flujo completo get_tools()
✅ [FULLSTACK] Tests están en tests/stress/test_performance.py, siguen patrón existente
✅ [DX] Herramienta fap bench ejecuta benchmarks con un comando y reporta thresholds
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| P6.1 threshold <100ms puede fallar en CI lento | Media | CI runners tienen varianza de ±50ms | Usar `time.perf_counter()`,มริun 3 iteraciones y tomar mínimo. Documentar que threshold asume máquina local moderna |
| P6.2 Pydantic v2 overhead variable | Baja | Pydantic validation depende de complejidad del schema | 10 steps + 5 agents es schema mínimo. Umbral <50ms holgado para Pydantic v2 |
| P6.3 regex sanitización 7 passes sobre 1MB | Media | Si `SECRET_PATTERNS` crece en futuro, tiempo escala linealmente | Threshold <500ms da margen 7×. Si añaden patrones, recalcular |
| P6.4误解 de scope | Alta | Plan dice "MCPPool.get_tools con circuito cerrado vs abierto" pero threshold <1ms es imposible para flujo async completo | Test debe medir `_is_circuit_open()` directamente, NO `get_tools()`. Documentar decisión |
| Duplicación con tests existentes S4.1/S4.5 | Baja | Mismo componente, distinto threshold | Extraer helpers comunes a `conftest.py` de stress |
| `input_data` no es campo de `WorkflowDefinition` | Alta | S4.7 usa campo inexistente, P6.2 no debe repetir error | P6.2 solo usa campos del schema real |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap bench` CLI command | FULLSTACK/DX | Media | 2h | Ninguna | → verificar: `fap bench --step 6` ejecuta P6.1-P6.4 y reporta thresholds |
| 1 | Crear `tests/stress/test_performance.py` con estructura base | CODE | Baja | 0.5h | Tarea 0 | → verificar: `pytest tests/stress/test_performance.py --co` muestra 4 test classes sin errores |
| 2 | Extraer helpers comunes a `tests/stress/conftest.py` (`_make_step_definition`, `_make_agent_definition`, `_make_1mb_string`) | CODE | Baja | 0.5h | Tarea 1 | → verificar: helpers importables desde `test_performance.py` y `test_edge_cases.py` |
| 3 | P6.1: `TestP6_1ResolveToolsBenchmark` — 50 tools, <100ms | CODE/BACKEND | Media | 1h | Tarea 2 | → verificar: `pytest tests/stress/test_performance.py::TestP6_1ResolveToolsBenchmark -v` pasa y reporta tiempo |
| 4 | P6.2: `TestP6_2WorkflowDefinitionBenchmark` — 10 steps + 5 agents, <50ms | CODE/BACKEND | Media | 1h | Tarea 2 | → verificar: `pytest tests/stress/test_performance.py::TestP6_2WorkflowDefinitionBenchmark -v` pasa con tiempo <50ms |
| 5 | P6.3: `TestP6_3SanitizeBenchmark` — 1MB string, <500ms | CODE/BACKEND | Media | 1h | Tarea 2 | → verificar: `pytest tests/stress/test_performance.py::TestP6_3SanitizeBenchmark -v` pasa con tiempo <500ms |
| 6 | P6.4: `TestP6_4CircuitBreakerBenchmark` — `_is_circuit_open` <1ms | CODE/BACKEND | Media | 1h | Tarea 2 | → verificar: `pytest tests/stress/test_performance.py::TestP6_4CircuitBreakerBenchmark -v` pasa con check <1ms |
| 7 | Validar `fap bench --step 6` ejecuta P6.1-P6.4 y reporta resultados | FULLSTACK | Baja | 0.5h | Tareas 0-6 | → verificar: `fap bench --step 6` corre sin errores y muestra tiempos vs thresholds |

**Tiempo total estimado:** 7.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Observabilidad real**: Integrar `structlog` metrics en `resolve_tools`, `sanitize_output`, `MCPPool` para emitir latencia percentiles en producción
- **Benchmark CI**: Añadir `fap bench` al pipeline CI como gate de performance (no solo pass/fail sino regresión)
- **Perfilado continuo**: Considerar `pytest-benchmark` para track de latencia entre commits
- **P6.4 extendido**: Benchmark de `get_tools()` completa con mock de `MCPServerAdapter` para medir overhead real incluyendo retry tenacity
- **Reparar S4.7**: `input_data` no es campo de `WorkflowDefinition`. El test existente tiene un bug silencioso (Pydantic `model_config` sin `extra="allow"` rechaza campos extra)
- **Añadir `extra="allow"` si se necesita `input_data`**: O eliminar del test. Decisión pendiente