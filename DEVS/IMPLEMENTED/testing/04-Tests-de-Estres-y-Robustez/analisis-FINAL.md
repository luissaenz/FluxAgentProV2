# 🏛️ Análisis Unificado — Paso 4: Estrés y Condiciones de Borde

**Fuente:** Consolidación de 4 análisis independientes
**Agentes:** ds (opencode) / kimi2.6 / mm2.5 / qwen
**Fecha:** 2026-05-01
**Plan referencia:** `DEVS/plan.md` Paso 4
**Config:** `proyecto-config.json` leído y aplicado

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **ds (opencode)** | ✅ 17 elementos c/archivo+línea | 3 (tests/stress, phase-state desync, bug >=/<=/== ya fixeado) | ✅ `fap test-stress` | ✅ Líneas exactas, patrones de código reusables, firmas completas | **4.8** |
| **kimi2.6** | ✅ 20 elementos c/archivo+línea | 5 (tests/stress, WorkflowDefinition≠register, sanitize sin re.compile, sin límite recursión, org_id="" sin tratamiento) | ✅ `fap stress-bench` (genera fixtures) | ✅ Muy detallado, identifica bottleneck re.compile, RecursionError potencial | **4.9** |
| **mm2.5** | ✅ 8 elementos (solo grep) | 0 (tests/stress no detectado — error grave) | ❌ `pytest -n auto` (preexistente, no innova) | ⚠️ Básica, superficial, sin read profundo | **2.5** |
| **qwen** | ✅ 18 elementos | 3 (tests/stress, sanitize lento 10MB, org_id="" sin validar) | ✅ `fap stress-test` (+benchmark) | ✅ Buena cobertura, menos específica que ds/kimi | **4.0** |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `tests/stress/` no existe. Plan asume directorio. | ds, kimi2.6, qwen (mm2.5 ❌ omitió) | ✅ `ls tests/` — ausente | Crear `tests/stress/` + `__init__.py` + 2 archivos test (`test_concurrency.py`, `test_edge_cases.py`) |
| 2 | **phase-state.md desincronizado.** Paso 4 descrito como "Hardening de API Pública". Nombres Pasos 2-7 no coinciden con plan.md. | ds (único) | ✅ `DEVS/phase-state.md:20` vs `DEVS/plan.md:176` | Ignorar phase-state para este paso. Plan.md es fuente de verdad. Post-análisis: corregir phase-state |
| 3 | **Bug `>=`/`<=`/`==` ya fixeado** en código (`dynamic_flow.py:128-185`) pero phase-state línea 62 aún lo marca como pendiente. | ds (único) | ✅ `src/flows/dynamic_flow.py:128-185` parser correcto con prioridad operadores compuestos | Actualizar phase-state línea 62. Bug resuelto en código real. |
| 4 | **Plan dice "WorkflowDefinition con flow_type duplicado"** pero `WorkflowDefinition` es schema Pydantic, no tiene método `register`. | kimi2.6 (único) | ✅ `src/flows/workflow_definition.py` vs `src/flows/dynamic_flow.py:38-61` | Test S4.4 debe usar `DynamicWorkflow.register` o `flow_registry.register`, no `WorkflowDefinition.register` |
| 5 | **`sanitize_output` sin `re.compile` global.** 7 `re.sub` sobre 10MB = re-compila patrones en cada llamada. | kimi2.6, qwen | ✅ `src/mcp/sanitizer.py:17-25` import `re` sin `re.compile` | Pre-compilar `SECRET_PATTERNS` con `re.compile` en módulo. Incluir como Tarea 4 del plan. |
| 6 | **`sanitize_output` sin límite de recursión.** Dicts con referencias circulares → `RecursionError` (~1000 frames). | kimi2.6 (único) | ✅ `src/mcp/sanitizer.py:43-46` recursión directa sin protección | Agregar protección circular (track `id()` set) o convertir a iterativo con `deque`. Post-MVP. |
| 7 | **`org_id=""` en `resolve_tools` sin tratamiento especial.** Comportamiento silencioso no documentado. | kimi2.6, qwen | ✅ `src/crews/factory.py:29` `tool_registry.get` con `org_id=""` → `if org_id:` False → lookup global | Test S4.6 documenta comportamiento: retorna lista sin crash. Post-MVP: validar formato UUID. |
| 8 | **`StepDefinition.approval_threshold` campo muerto.** Existe en schema pero `_run_crew()` no lo referencia. | mm2.5 (único) | ✅ `src/flows/workflow_definition.py:47` vs `src/flows/dynamic_flow.py` | No relevante para Paso 4. Documentar como deuda técnica. No implementar ahora. |
| 9 | **`resolve_tools` 500 tools — criterio "sin memory leak visible" vago.** Sin GC profiling no hay medición objetiva. | ds (único) | ✅ Análisis de semántica del criterio | Cambiar criterio a "no retiene referencias a tools tras salir de scope" + `sys.getsizeof()` parcial |

---

## 1️⃣ Resumen Ejecutivo

Paso 4 = tests estrés y edge cases sobre código propio existente. Sin cambios DB, sin endpoints nuevos, sin modificar código fuente. 7 tests (S4.1-S4.7) en 2 archivos bajo `tests/stress/`.

**Correcciones críticas al plan:**
- ⚠️ Plan menciona "WorkflowDefinition con flow_type duplicado" pero `WorkflowDefinition` es Pydantic schema. Test real usa `DynamicWorkflow.register` o `flow_registry.register`.
- ⚠️ Phase-state.md describe Paso 4 como "Hardening de API Pública". Error de nomenclatura. Ignorar.
- ⚠️ Bug `>=`/`<=`/`==` ya fixeado en código. Phase-state desactualizado.

**Decisión DX:** `fap stress-bench` — fusión de propuestas ds/kimi2.6/qwen. Genera fixtures masivos automáticamente y ejecuta suite con métricas.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

Secuencia completa del paso:
1. Implementador corre `fap stress-bench --tools 500 --workflows 50 --sanitizer-size 10MB --json-depth 20`
2. Herramienta crea directorio `tests/stress/` + `__init__.py`
3. Herramienta genera fixtures masivos (500 tools mock, 50 workflows, string 10MB, JSON 20 niveles)
4. Herramienta ejecuta `pytest tests/stress/` con métricas de tiempo
5. 7 tests pasan: S4.1-S4.3 (concurrencia) + S4.4-S4.7 (edge cases)
6. Reporte final: tiempos, pass/fail, comparación con baseline

### Edge Cases MVP

1. **S4.1:** 500 tools registradas en `tool_registry._tools` → `resolve_tools` itera O(n) lookup en dict. Sin memory leak post-scope.
2. **S4.2:** 50 `DynamicWorkflow` en `asyncio.gather`. Riesgo: mock de `BaseCrew` sin latencia simulada → falso positivo. **Mitigación:** `asyncio.sleep(0.01)` en mock `run_async`.
3. **S4.3:** `MCPPool.reset()` ×100. Singleton limpio cada vez. Verificar `_adapters == {}` y `_health` vacío tras reset.
4. **S4.4:** `DynamicWorkflow.register("same", def1)` → `register("same", def2)` → def2 sobrescribe. Dict nativo. Comportamiento documentado, no bug.
5. **S4.5:** `sanitize_output(string 10MB)` con 7 regex sobre 10MB. Riesgo: >5s en CI lento. **Mitigación:** reducir threshold a 5MB o warning no fail.
6. **S4.6:** `resolve_tools([...], org_id="")` → lookup global sin crash. Definir comportamiento: retorna lista vacía o tools globales.
7. **S4.7:** `WorkflowDefinition(input_data=dict_20_niveles)`. Pydantic valida tipos, no profundidad. No hay RecursionError porque Pydantic no itera recursivamente `Dict[str, Any]`.

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

| Ruta real | Tipo de cambio | Descripción | Interfaces clave | Patrones a seguir |
|---|---|---|---|---|
| `D:\Develop\Personal\FluxAgentPro-v2\tests\stress\__init__.py` | Creación | Package init vacío | — | `tests/unit/__init__.py` |
| `D:\Develop\Personal\FluxAgentPro-v2\tests\stress\test_concurrency.py` | Creación | S4.1: resolve_tools 500 tools. S4.2: 50 DynamicWorkflow concurrentes. S4.3: MCPPool.reset ×100 | MCPPool.get/reset, DynamicWorkflow, AgentFactory.resolve_tools | `tests/e2e/test_production_flows.py:150-164` (mock resolve_tools), `tests/unit/test_mcp_pool_circuit.py:17-22` (reset fixture) |
| `D:\Develop\Personal\FluxAgentPro-v2\tests\stress\test_edge_cases.py` | Creación | S4.4: flow_type duplicado. S4.5: sanitize 10MB. S4.6: org_id="". S4.7: JSON 20 niveles | sanitize_output, DynamicWorkflow.register, flow_registry, WorkflowDefinition | `tests/unit/test_sanitizer.py` (import directo sanitize_output) |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap stress-bench
- **Qué automatiza:** Generación de fixtures masivos (500 mocks tools, 50 workflows, string 10MB, JSON 20 niveles) + ejecución suite stress con métricas de tiempo y memoria. Implementador actualmente debe manualmente crear cada fixture.
- **Tipo:** CLI command (typer) — extensión de `fap`
- **Ubicación:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\stress_bench.py`
- **Cómo se usa:**
  - `fap stress-bench` — ejecuta suite completa con defaults (500/50/10MB/20)
  - `fap stress-bench --tools 100 --workflows 10 --sanitizer-size 5MB --json-depth 15` — parámetros custom
  - `fap stress-bench --test S4.1` — test específico
  - `fap stress-bench --iterations 3 --benchmark` — promedia 3 ejecuciones, guarda baseline
- **Impacto para el usuario final:** Implementador deja de escribir fixtures masivos a mano. Comando genera, ejecuta, y reporta si thresholds tiempo/memoria se cumplen. Detecta regresiones de performance automáticamente.
- **El implementador DEBE usarla** para ejecutar Paso 4 completo tras implementar tests.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Patrón de reset singleton obligatorio:** `MCPPool.reset()` en fixture `autouse=True` en cada archivo test. Idéntico a `tests/unit/test_mcp_pool_circuit.py:17-22`. Evita contaminación entre tests.
2. **Mock de concurrencia con latencia simulada:** S4.2 debe usar `asyncio.sleep(0.01)` en mock de `BaseCrew.run_async` para aproximar latencia real. Sin esto, 50 corrutinas pueden completar secuencialmente sin detectar race conditions.
3. **Pre-compilar `SECRET_PATTERNS` con `re.compile`** en `src/mcp/sanitizer.py`. Sin este fix, S4.5 (10MB × 7 regex) puede exceder threshold 5s en CI. Tarea separada (Tarea 4).
4. **`asyncio.gather(return_exceptions=True)`** en S4.2. Permite verificar que ninguna corrutina retorna excepción, en lugar de propagar la primera.
5. **Corrección al plan:** Plan dice "WorkflowDefinition con flow_type duplicado en registry". El registro real lo hace `DynamicWorkflow.register` (línea 38) o `@flow_registry.register`. `WorkflowDefinition` es solo schema Pydantic. Se implementa test S4.4 contra `DynamicWorkflow.register`.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] S4.1: resolve_tools con 500 tools registradas completa en <2s
✅ [CODE] S4.1: resolve_tools con 500 tools no retiene referencias post-scope
✅ [CODE] S4.2: 50 DynamicWorkflow en asyncio.gather completan sin excepción
✅ [CODE] S4.2: 50 DynamicWorkflow retornan Dict[str, Any] con resultados
✅ [CODE] S4.3: MCPPool.reset() 100 veces consecutivas sin error
✅ [CODE] S4.3: Tras 100 resets, MCPPool.get() retorna instancia limpia (_health vacío, _adapters vacío)
✅ [CODE] S4.4: DynamicWorkflow.register("test_flow", def1).register("test_flow", def2) sobrescribe sin error
✅ [CODE] S4.4: flow_registry._flows["test_flow"] contiene def2 (no def1)
✅ [CODE] S4.5: sanitize_output(string 10MB) completa en <5s
✅ [CODE] S4.5: sanitize_output(string 10MB) no lanza MemoryError
✅ [CODE] S4.6: resolve_tools con org_id="" no lanza excepción
✅ [CODE] S4.6: resolve_tools con org_id="" retorna lista (vacía o con tools)
✅ [CODE] S4.7: WorkflowDefinition con input_data 20 niveles anidados no lanza RecursionError
✅ [CODE] S4.7: WorkflowDefinition validation pasa sin timeout
✅ [DX] fap stress-bench ejecuta Paso 4 completo y reporta breakdown por test
✅ [CODE] SECRET_PATTERNS pre-compilados con re.compile (Tarea 4)
```

**Funcionales:**
- [ ] tests/stress/test_concurrency.py descubre 3 tests (S4.1, S4.2, S4.3)
- [ ] tests/stress/test_edge_cases.py descubre 4 tests (S4.4, S4.5, S4.6, S4.7)
- [ ] pytest tests/stress/ -v pasa 7/7

**Técnicos:**
- [ ] Ruff check tests/stress/ 0 errores
- [ ] Sin degradación de memoria >50MB entre inicio y fin de suite
- [ ] S4.1 <2s, S4.2 0 excepciones, S4.5 <5s

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap stress-bench` command | Media | 1.5h | Ninguna |
| 1 | Crear `tests/stress/__init__.py` | Baja | 0.1h | Tarea 0 |
| 2 | Implementar `tests/stress/test_concurrency.py` (S4.1-S4.3) | Alta | 2h | Tarea 1 |
| 3 | Implementar `tests/stress/test_edge_cases.py` (S4.4-S4.7) | Alta | 2h | Tarea 1 |
| 4 | Pre-compilar `SECRET_PATTERNS` con `re.compile` en `sanitizer.py` | Baja | 0.5h | Ninguna |
| 5 | Validar suite completa con métricas | Baja | 0.5h | Tareas 0-4 |
| **TOTAL** | | | **6.6h** | |

> [!IMPORTANT]
> **Tarea 0 = DX & Tooling.** Implementador DEBE ejecutarla primero. Usar `fap stress-bench` para el resto del paso (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| S4.2 falso positivo: mocks sin latencia → no detectan race conditions | Alta | Mock BaseCrew sin `asyncio.sleep(0.01)` simulado | Añadir `asyncio.sleep(0.01)` en mock `run_async` |
| S4.5 timeout en CI lento (10MB × 7 regex >5s) | Media | 70MB procesamiento regex, CPU-bound | Reducir a 5MB o threshold informativo (warning no fail). Fix re.compile ayuda |
| MCPPool singleton contaminado entre módulos test | Media | Tests de diferentes archivos en同一 sesión pytest | `MCPPool.reset()` en fixture `autouse=True` de cada archivo |
| `sanitize_output` RecursionError con JSON circular | Media | Dict con ref circular → recursión infinita | Test S4.7 usa JSON profundo no circular. Protección circular post-MVP |
| `DynamicWorkflow.register` sobrescribe metadata sin merge | Baja | `flow_registry._metadata` se re-asigna completo | S4.4 documenta: "comportamiento esperado, no bug" |
| phase-state.md desincronizado confunde al implementador | Baja | Nombres de pasos incorrectos | Ignorar phase-state. Plan.md es fuente de verdad |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | S4.1: 500 tools en registry | `allowed_tools` 500 nombres, `org_id` válido | `<2s`, lista 500 tools, sin referencias post-scope |
| TP-2 | S4.2: 50 workflows concurrentes | 50 `DynamicWorkflow` instances en `asyncio.gather` | 50 resultados `Dict[str, Any]`, 0 excepciones |
| TP-3 | S4.3: 100× MCPPool.reset | `MCPPool.reset()` × 100, luego `MCPPool.get()` | Sin error, `_health == {}`, `_adapters == {}` |
| TP-4 | S4.4: flow_type duplicado | `register("x", def1)`, `register("x", def2)` | `_flows["x"] == def2`, sin excepción |
| TP-5 | S4.5: sanitize 10MB | String 10MB con secretos intercalados | `<5s`, secretos redactados, sin MemoryError |
| TP-6 | S4.6: org_id vacío | `resolve_tools([...], org_id="")` | Lista (vacía o con tools), sin excepción |
| TP-7 | S4.7: JSON 20 niveles | `WorkflowDefinition(input_data={l1:{l2:...l20}})` | Sin RecursionError, sin timeout |

Comando para ejecutar tests: `pytest tests/stress/ -v --timeout=30`
Comando para lint: `ruff check tests/stress/`
