# Análisis Técnico — Paso 6: Performance & Observabilidad

**Agente:** k2.6  
**Fecha:** 2026-05-01  
**Destino:** `DEVS/IN_PROGRESS/analisis-6-k2.6.md`  
**Regla de oro:** Único archivo modificado = este documento.

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

> Completada ANTES de secciones 1-4.

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `resolve_tools` existe | `src/crews/factory.py:28` | ✅ | Firma: `resolve_tools(allowed_tools: list[str], org_id: str, *, async_mode: bool = False) -> list` |
| 2 | `WorkflowDefinition` existe | `src/flows/workflow_definition.py:57` | ✅ | Clase Pydantic `BaseModel` con 3 validators |
| 3 | `sanitize_output` existe | `src/mcp/sanitizer.py:28` | ✅ | Firma: `sanitize_output(data: Any) -> Any`. 7 patrones regex compilados. Recursivo dict/list/str |
| 4 | `MCPPool.get_tools` existe | `src/tools/mcp_pool.py:77` | ✅ | Firma async: `get_tools(org_id, server_name, timeout=30, max_retries=3) -> list` |
| 5 | `_is_circuit_open` existe | `src/tools/mcp_pool.py:60` | ✅ | Lógica: `failures >= 5` y `elapsed < 60s` |
| 6 | `tool_registry` existe | `src/tools/registry.py:272` | ✅ | Singleton `ToolRegistry`. `_tools: Dict[str, Type]`. Lookups O(1) en memoria |
| 7 | `tests/stress/` ya existe | `ls tests/stress/` | ⚠️ DISCREPANCIA | `test_concurrency.py`, `test_edge_cases.py`, `conftest.py` ya existen. Cubren funciones similares (S4.1=resolve_tools 500, S4.5=sanitizer 10MB, S4.7=WorkflowDefinition 20 niveles) pero con escalas y thresholds DISTINTOS a P6 |
| 8 | `fap stress-bench` existe | `src/cli/commands/stress_bench.py` | ⚠️ DISCREPANCIA | DX tool para paso 4 ya implementada. No existe equivalente para paso 6 |
| 9 | `pytest-cov` instalado | `pyproject.toml` / `proyecto-config.json` dev deps | ✅ | `pytest-cov>=6.0.0` listado en dev dependencies |
| 10 | `conftest.py` fixtures | `tests/conftest.py:304` | ✅ | `mock_mcp_pool`, `mock_service_client`, `global_llm_mock` disponibles |
| 11 | `test_3_5_latency.py` falla | `tests/integration/test_3_5_latency.py:46` | ❌ DISCREPANCIA | Plan v3.1 señala `test_full_latency_validation` falla actualmente. Requiere DB real + SUPABASE_URL. Fuera de scope paso 6 pero bloquea `pytest tests/` completo si no se skipea |
| 12 | `ALLOWED_MODELS` existe | `src/flows/workflow_guardrails.py:16` | ✅ | Set de 5 modelos. `AgentDefinition.model_must_be_allowed` lo valida |

**Discrepancias encontradas:**

1. **Tests de stress ya existen (`tests/stress/`):** El plan v3.1 asume paso 4 no implementado, pero `tests/stress/` contiene tests de concurrencia y edge-cases. No son duplicados exactos de paso 6: S4.1 usa 500 tools con threshold <2s; P6.1 usa 50 tools con <100ms. S4.5 usa 10MB con <5s; P6.3 usa 1MB con <500ms. Escalas y objetivos diferentes → complementarios, no duplicados.
2. **`fap stress-bench` ya existe:** CLI para paso 4. Falta CLI para paso 6. **Resolución:** Crear `fap perf-check` como herramienta DX específica para benchmarks de rendimiento.
3. **`test_3_5_latency.py` bloquea suite completa:** Si no se skipea, `pytest tests/` falla en CI. **Resolución:** Verificar que el test tiene `pytestmark = pytest.mark.skipif(not SUPABASE_URL, ...)` — esto ya mitiga, pero el plan menciona que `test_full_latency_validation` FALLA actualmente aun con DB (posible timeout). Sugerir `@pytest.mark.skip` temporal o mover a `tests/integration/manual/`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Conclusión:** Paso 6 no modifica schema ni tablas.

- **Tablas tocadas:** Ninguna directamente. Benchmarks son tests de código puro contra funciones existentes.
- **Integridad referencial:** No aplica.
- **RLS policies:** No aplica.
- **Índices:** No aplica.
- **Tipos de datos:** No aplica.

> Referencia a `phase-state.md` §2: Esquemas DB clave (`agent_catalog`, `org_mcp_servers`, etc.) ya documentados. Paso 6 no los altera.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases bajo benchmark

| Componente | Archivo | Firma real | Complejidad |
|---|---|---|---|
| `AgentFactory.resolve_tools` | `src/crews/factory.py:28` | `@staticmethod resolve_tools(allowed_tools: list[str], org_id: str, *, async_mode: bool = False) -> list` | O(n) con n = len(allowed_tools). Cada iteración: `tool_registry.get()` (O(1) dict lookup en memoria) + instanciación `tool_cls(org_id=org_id)` |
| `WorkflowDefinition` | `src/flows/workflow_definition.py:57` | Pydantic `BaseModel`. 3 validators: `flow_type_must_be_snake_case`, `each_step_references_valid_agent`, `no_circular_dependencies` | Validación Pydantic nativa + regex + set lookup + DFS. Con 10 steps y 5 agents: insignificante |
| `sanitize_output` | `src/mcp/sanitizer.py:28` | `def sanitize_output(data: Any) -> Any` | Para string: 7 `re.sub` secuenciales. Para dict/list: recursión. Complejidad O(k * m) con k=patrones, m=longitud string |
| `MCPPool._is_circuit_open` | `src/tools/mcp_pool.py:60` | `def _is_circuit_open(self, key: str) -> bool` | Dict lookup + comparación float. O(1) |
| `MCPPool.get_tools` | `src/tools/mcp_pool.py:77` | `async def get_tools(...)` | Overhead del circuit breaker = llamada a `_is_circuit_open` antes de intentar conexión |

### Patrones y reutilización

- **Patrón de test:** `time.perf_counter()` para medir latencia pura (no `time.time()` que es wall-clock y menos preciso).
- **Patrón de mock:** Igual que paso 1 — `mock_service_client`, `mock_mcp_pool`, `MCPPool.reset()` entre tests.
- **Patrón de fixture masiva:** Tests de stress (`tests/stress/`) ya usan registro dinámico de mock tools. P6.1 puede reutilizar `_register_mock_tools` / `_unregister_mock_tools` adaptando la escala a 50.

### Calidad y mantenibilidad

- **Duplicación potencial:** Si el implementador no lee `tests/stress/`, puede duplicar helpers de generación de tools/workflows. **Mitigación:** Documentar en §7 que se reutilicen helpers de `tests/stress/` donde aplique.
- **Flakiness:** Benchmarks en CI compartido pueden variar. **Mitigación:** Usar `time.perf_counter()` y ejecutar múltiples repeticiones (e.g. 10 runs, tomar mínimo o P95).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Conclusión:** Paso 6 no crea endpoints ni modifica APIs.

- **Endpoints:** Ninguno nuevo.
- **Middleware:** No aplica.
- **Flujo de datos:** No aplica. Benchmarks son tests unitarios/funcionales puros.
- **Auth/Authz:** No aplica. Los benchmarks usan mocks de `get_service_client`.
- **Contratos:** No aplica.
- **Error handling:** Los benchmarks deben assertar que la función bajo medición NO lanza excepción (happy path). Si falla, el benchmark debe fallar.

**Nota sobre `resolve_tools`:**
- En `async_mode=True`, intenta resolver MCP tools vía `MCPPool.get_tools()`. Para P6.1 se usará `async_mode=False` (mock registry puro) para aislar la latencia de resolución de registry de la latencia de red/MCP.
- Si se quisiera benchmark del path MCP completo, sería test de integración con mocks, no benchmark puro. El plan dice "mock registry" → solo memoria.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

Paso 6 no tiene flujo end-to-end visible para el usuario final. Es infraestructura de calidad que garantiza que componentes core mantienen latencia baja bajo carga controlada.

- **DB → Backend:** No aplica directamente. `resolve_tools` puede hacer fallback a DB (`_load_from_db`), pero P6.1 especifica "mock registry" → evita DB.
- **Backend → Frontend:** No aplica.
- **UX:** No aplica directamente. Performance estable mejora UX indirectamente.

### Gaps / Ambigüedades

1. **Ubicación de tests de performance:** El plan no especifica carpeta. Opciones: `tests/performance/`, `tests/unit/test_performance.py`, `tests/benchmark/`. Recomendación: `tests/performance/` para separar de unitarios y stress.
2. **`WorkflowDefinition` con 10 steps y 5 agents:** El plan dice "validación con 10 steps, 5 agents". No especifica si se mide `WorkflowDefinition(**data)` (construcción+validación Pydantic) o solo re-validación. Asumir construcción desde dict crudo.
3. **`MCPPool.get_tools` con circuito abierto vs cerrado:** El plan dice "overhead de circuit breaker check <1ms". Para medir esto, se debe llamar a `_is_circuit_open` directamente o medir `get_tools` con circuito abierto (lanza excepción inmediata) vs cerrado (intenta conexión). Como `get_tools` con circuito cerrado requiere mock de conexión MCP, el benchmark más limpio es medir `_is_circuit_open` en ambos estados. **Resolución:** Test directo a `_is_circuit_open` para overhead puro, y un test separado de `get_tools` con circuito abierto para latencia de rechazo.

### DX & Tooling (OBLIGATORIO)

```markdown
### Herramienta Propuesta: `fap perf-check`
- **Qué automatiza:** Ejecución de benchmarks de performance (P6.1-P6.4) con un solo comando, verificación de thresholds, y generación de reporte JSON comparativo.
- **Tipo:** CLI / comando Typer.
- **Cómo se usa:**
  ```bash
  fap perf-check              # Corre tests/performance/, reporta pass/fail por threshold
  fap perf-check --baseline   # Guarda reports/perf_baseline.json
  fap perf-check --compare    # Compara contra baseline y alerta regresiones
  ```
- **Impacto para el usuario final:** El desarrollador no necesita recordar thresholds ni ejecutar `pytest` manualmente con filtros. Un solo comando verifica que componentes críticos no hayan degradado performance tras cambios.
- **Prioridad:** Tarea 0 — implementar antes que los tests individuales, ya que el comando se usa para validar el propio paso.
```

---

## 5️⃣ Criterios de Aceptación

Lista binaria, verificable:

```
✅ [CODE] Test P6.1 existe: `resolve_tools` con 50 tools mock registry en <100ms
✅ [CODE] Test P6.2 existe: `WorkflowDefinition` validación 10 steps + 5 agents en <50ms
✅ [CODE] Test P6.3 existe: `sanitize_output` con string 1MB en <500ms
✅ [CODE] Test P6.4 existe: Overhead `_is_circuit_open` <1ms (circuito cerrado y abierto)
✅ [CODE] Tests ubicados en `tests/performance/` (o carpeta consistente con convenciones)
✅ [DX] CLI `fap perf-check` ejecuta todos los benchmarks y reporta pass/fail
✅ [DX] `fap perf-check --baseline` genera `reports/perf_baseline.json`
✅ [CODE] Lint `ruff check tests/performance/` → 0 errores
✅ [CODE] `pytest tests/performance/` pasa 100% (4/4 tests)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Flakiness en CI por variación de `time.perf_counter` | Media | Runners compartidos tienen carga variable. Benchmark puede superar threshold ocasionalmente | Usar múltiples repeticiones (e.g. 10) y tomar mínimo o P95. Threshold con margen del 20%. Marcado `@pytest.mark.benchmark` opcional |
| `sanitize_output` 1MB supera 500ms en Python puro | Media | 7 regex sobre 1MB secuencialmente. Si hay muchos matches, `re.sub` puede ser lento | Pre-benchmark: ejecutar script manual. Si supera 500ms, optimizar regex (combinar en single pass) o elevar threshold documentadamente |
| Confusión con tests de stress existentes | Baja | `tests/stress/` ya tiene tests similares. Implementador puede pensar que paso 6 ya está hecho | Documentar claramente en este análisis y en criterios de aceptación que stress (paso 4) ≠ performance (paso 6) |
| `test_3_5_latency.py` bloquea `pytest tests/` | Media | Test de integración requiere DB real. Si se ejecuta accidentalmente sin env, falla | Verificar que `pytest tests/performance/` es el comando correcto, no `pytest tests/`. O asegurar que test_3_5_latency.py esté skipeado correctamente |
| `resolve_tools` con mock tools ligeros es trivialmente rápido | Baja | Threshold <100ms para 50 instanciaciones puede ser demasiado permisivo o restrictivo según la clase mock | Usar `_MockStressTool` de `tests/stress/` (inicialización vacía). Si tarda <10ms, considerar medir con 500 tools para obtener métrica significativa, pero respetar especificación del plan (50 tools) |

---

## 7️⃣ Plan de Implementación

> [!IMPORTANT]
> Tarea 0 siempre = DX & Tooling.

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear `src/cli/commands/perf_check.py` (`fap perf-check`) | FULLSTACK/DX | Media | 1.5h | Ninguna | → verificar: `fap perf-check --help` muestra opciones; `fap perf-check` ejecuta `pytest tests/performance/ -v` y genera `reports/perf_report.json` |
| 1 | Crear estructura `tests/performance/` | CODE | Baja | 0.25h | Tarea 0 | → verificar: `ls tests/performance/` muestra `__init__.py`, `conftest.py`, `test_benchmarks.py` |
| 2 | Implementar P6.1: benchmark `resolve_tools` 50 tools mock registry | CODE | Media | 1h | Tarea 1 | → verificar: `pytest tests/performance/test_benchmarks.py::test_resolve_tools_50 -v` pasa con tiempo <100ms |
| 3 | Implementar P6.2: benchmark `WorkflowDefinition` 10 steps + 5 agents | CODE | Media | 1h | Tarea 1 | → verificar: `pytest tests/performance/test_benchmarks.py::test_workflow_definition_validation -v` pasa con tiempo <50ms |
| 4 | Implementar P6.3: benchmark `sanitize_output` con string 1MB | CODE | Media | 1h | Tarea 1 | → verificar: `pytest tests/performance/test_benchmarks.py::test_sanitize_output_1mb -v` pasa con tiempo <500ms |
| 5 | Implementar P6.4: benchmark overhead `MCPPool._is_circuit_open` | CODE | Baja | 0.75h | Tarea 1 | → verificar: `pytest tests/performance/test_benchmarks.py::test_circuit_breaker_overhead -v` pasa con tiempo <1ms |
| 6 | Validar suite completa y lint | CODE | Baja | 0.5h | Tareas 2-5 | → verificar: `pytest tests/performance/` → 4/4 pass; `ruff check tests/performance/` → 0 errores; `fap perf-check` → reporte JSON con 4 thresholds verificados |
| 7 | Documentar en `TESTING.md` (preparación para paso 7) | FULLSTACK/DX | Baja | 0.5h | Tarea 6 | → verificar: `TESTING.md` contiene sección "Performance Benchmarks" con comando `fap perf-check` y thresholds |

**Tiempo total estimado:** 6.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Optimización `sanitize_output`:** Si P6.3 muestra que 7 regex secuenciales sobre 1MB es lento, considerar combinar patrones en un solo `re.sub` con alternancia `(pat1|pat2|...)` para single pass. Impacto: ~2-3x velocidad.
- **Benchmark histórico:** Extender `fap perf-check --baseline` para almacenar múltiples baselines y graficar tendencias en CI.
- **Pre-commit hook:** Añadir `fap perf-check --compare` como hook opcional para detectar regresiones de performance antes de push.
- **`WorkflowDefinition` validator caching:** Los validators `no_circular_dependencies` y `each_step_references_valid_agent` se ejecutan siempre. Para flujos masivos (paso futuro), considerar `@lru_cache` en validación de grafo si los workflows son inmutables post-creación.

---

## 📊 Métrica de Calidad (Auto-verificación)

| Métrica | Mínimo | Estado |
|:---|:---|:---|
| `proyecto-config.json` leído antes de explorar | 100% | ✅ |
| Elementos verificados (§0) | ≥ 8 (paso toca 4 componentes core) | ✅ 12 elementos |
| Discrepancias detectadas | ≥ 1 si toca código existente | ✅ 3 discrepancias |
| Secciones completadas | 8 secciones (0-7) | ✅ 8/8 |
| Etapas cubiertas | 4 etapas (data, code, backend, fullstack+DX) | ✅ 4/4 |
| Criterios de aceptación | ≥ 1 por sub-paso, verificables | ✅ 9 criterios |
| Riesgos identificados | ≥ 3 (técnico, integración, futuro) | ✅ 5 riesgos |
| Tareas en el plan | ≥ 4, atómicas, ordenadas | ✅ 8 tareas |
| Verificación inline por tarea (§7) | 100% — toda tarea tiene `→ verificar:` | ✅ 100% |
| Suposiciones no verificadas | ≤ 2, cada una marcada ⚠️ | ✅ 1 (ubicación tests/performance) |
| Propuesta DX / Tooling | ≥ 1 herramienta concreta con descripción de impacto | ✅ `fap perf-check` |
| Estimación de tiempo | Sí, por tarea y total | ✅ 6.5h total |
