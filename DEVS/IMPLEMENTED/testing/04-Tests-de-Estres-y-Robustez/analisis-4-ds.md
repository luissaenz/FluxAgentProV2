# Análisis Técnico — Paso 4: Estrés y Condiciones de Borde (Solo código propio)

**Agente:** opencode  
**Fecha:** 2026-05-01  
**Plan de referencia:** `DEVS/plan.md` — Paso 4  
**Phase-state:** `DEVS/phase-state.md`  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `tests/stress/` existe | glob `tests/stress/*` | ❌ DISCREPANCIA | Directorio no existe. Debe crearse con `__init__.py`. |
| 2 | `MCPPool` en `src/tools/mcp_pool.py` | Read código | ✅ | Línea 35. Singleton con `get()`, `reset()`, `_health`, contador `failures`. |
| 3 | `MCPPool.reset()` existe | Read línea 210-212 | ✅ | `reset()` setea `cls._instance = None`. Limpio. |
| 4 | `MCPPool._is_circuit_open` existe | Read línea 60-66 | ✅ | Threshold 5 fallos, ventana 60s. |
| 5 | `AgentFactory.resolve_tools()` existe | Read `src/crews/factory.py:28` | ✅ | Resuelve tools por nombre. Soporta `mcp:` prefix y registry lookup. |
| 6 | `DynamicWorkflow` en `src/flows/dynamic_flow.py` | Read | ✅ | Hereda `BaseFlow`. `_run_crew()` async. `_template_definition` dict. |
| 7 | `DynamicWorkflow.register()` existe | Read línea 38-61 | ✅ | Registra en `flow_registry._flows` con `flow_type` como key. Sobrescribe si duplicado. |
| 8 | `sanitize_output()` en `src/mcp/sanitizer.py` | Read línea 28 | ✅ | Función pura. Recursiva en dict/list. 7 patrones regex. |
| 9 | `WorkflowDefinition` en `src/flows/workflow_definition.py` | Read línea 57 | ✅ | Pydantic BaseModel. Validación de `flow_type` snake_case, dependencias, ciclos. |
| 10 | `tool_registry` singleton en `src/tools/registry.py` | Read línea 272 | ✅ | `_tools: Dict[str, Type]`. `register()`, `get()`, `list_tools()`. |
| 11 | `flow_registry` singleton en `src/flows/registry.py` | Read línea 370 | ✅ | `_flows: Dict[str, Type]`. `register()`, `clear()`, `list_flows()`. |
| 12 | Fixtures `mock_service_client`, `mock_tenant_client` | Read `tests/conftest.py` | ✅ | Disponibles. Parchean 8+ puntos de import. |
| 13 | Fixture `mock_mcp_pool` | Read `tests/conftest.py:303-316` | ✅ | `AsyncMock` retorna 3 tools mock. |
| 14 | Fixture `global_llm_mock` | Read `tests/conftest.py:274-300` | ✅ | Autouse. Mockea ChatOpenAI, ChatOllama, Agent, Task, Crew. |
| 15 | `asyncio_mode = "auto"` en pyproject.toml | Read línea 55 | ✅ | Tests async no requieren `@pytest.mark.asyncio` explícito. |
| 16 | phase-state.md numbering vs plan.md | Ambos leídos | ❌ DISCREPANCIA | Phase-state: Paso 4 = "Hardening de API Pública". Plan.md: Paso 4 = "Estrés y Condiciones de Borde". Phase-state desactualizado. |
| 17 | Bug `>=`/`<=`/`==` status | `dynamic_flow.py:128-185` | ✅ | **YA FIXEADO.** Código tiene parser correcto con prioridad de operadores compuestos. Phase-state línea 62 aún lo marca como bug — desactualizado. |

**Discrepancias encontradas:**

1. ❌ **`tests/stress/` no existe.** Directorio debe crearse con `__init__.py` + 2 archivos de test.
2. ❌ **phase-state.md fuera de sincronía.** Paso 4 descrito como "Hardening de API Pública" pero plan.md lo define como "Estrés y Condiciones de Borde". Números de pasos 2-7 no coinciden entre phase-state y plan.
3. ❌ **Bug `>=`/`<=`/`==` ya fixeado** en `dynamic_flow.py:128-185` pero phase-state línea 62 lo reporta como pendiente. Documentación desactualizada.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

Paso 4 **no toca schema de DB**. Tests de estrés y edge cases operan 100% sobre código Python con mocks. No hay migraciones, tablas nuevas, RLS policies, ni índices.

**Lo que sí usa (pero no modifica):**
- `tool_registry._tools` — dict en memoria
- `flow_registry._flows` — dict en memoria
- `MCPPool._health` — dict en memoria
- `MCPPool._instance` — singleton classvar

**Impacto en datos existentes:** Ninguno. Tests mockean todas las conexiones a DB (`mock_service_client`, `mock_tenant_client`).

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a crear

| Archivo | Tipo | Tests |
|---|---|---|
| `tests/stress/__init__.py` | Package init | Vacío |
| `tests/stress/test_concurrency.py` | Tests | S4.1, S4.2, S4.3 |
| `tests/stress/test_edge_cases.py` | Tests | S4.4, S4.5, S4.6, S4.7 |

### Patrones existentes a reusar

1. **Patrón de reset singleton** — `tests/unit/test_mcp_pool_circuit.py:17-22`:
   ```python
   @pytest.fixture(autouse=True)
   def _reset_pool():
       MCPPool.reset()
       yield
       MCPPool.reset()
   ```
   → Idéntico para S4.3. También necesario en S4.1 y S4.2 para evitar contaminación.

2. **Patrón de mock de AgentFactory.resolve_tools** — `tests/e2e/test_production_flows.py:150-164`:
   ```python
   with patch.object(AgentFactory, "_resolve_mcp_tool") as mock_resolve:
       mock_resolve.side_effect = [mock_tool, Exception("...")]
   ```
   → Para S4.1 (500 tools). Mejor: registrar 500 tools en tool_registry directamente o parchear `tool_registry._tools`.

3. **Patrón de mock de DynamicWorkflow** — `tests/e2e/test_production_flows.py:272-294`:
   ```python
   flow.state = MagicMock()
   flow.persist_state = AsyncMock()
   flow.emit_event = AsyncMock()
   with patch("src.flows.dynamic_flow.BaseCrew") as MockBaseCrew:
       MockBaseCrew.side_effect = crew_side_effect
   ```
   → Para S4.2 (50 concurrent DynamicWorkflow instances).

4. **Patrón de sanitize_output directo** — `tests/unit/test_sanitizer.py` (import directo, función pura):
   ```python
   from src.mcp.sanitizer import sanitize_output
   ```
   → Para S4.5 (string 10MB).

5. **Patrón de DynamicWorkflow.register** — implícito en `src/flows/dynamic_flow.py:38-61`:
   El registro es un simple assignment a `flow_registry._flows[flow_type_lower]` que sobrescribe sin warning. Dict nativo de Python — comportamiento esperado.
   → Para S4.4 (flow_type duplicado).

### Análisis de firmas relevantes

```python
# MCPPool
MCPPool.get() -> MCPPool                            # Singleton accessor
MCPPool.reset() -> None                              # Singleton reset (classmethod)
MCPPool._is_circuit_open(key: str) -> bool           # Check circuit state
MCPPool._record_failure(key: str) -> None            # Increment failure count
MCPPool._reset_circuit_breaker(key: str) -> None     # Reset failures to 0
MCPPool.get_tools(org_id, server_name, timeout=30, max_retries=3) -> list  # Main API

# AgentFactory
AgentFactory.resolve_tools(allowed_tools: list[str], org_id: str, *, async_mode: bool = False) -> list

# DynamicWorkflow
DynamicWorkflow.__init__(org_id, user_id=None, **kwargs)
DynamicWorkflow.register(flow_type: str, definition: Dict) -> None  # classmethod
DynamicWorkflow._run_crew() -> Dict[str, Any]
DynamicWorkflow._template_definition: Dict[str, Any]
DynamicWorkflow._flow_type: str

# WorkflowDefinition (Pydantic)
WorkflowDefinition(name, description, flow_type, steps, agents, ...)  # validates on init

# sanitize_output
sanitize_output(data: Any) -> Any  # Pure function, recursive
```

### Calidad y mantenibilidad

- **Alta cohesión:** Cada test cubre UN escenario de estrés/edge case. Sin solapamiento.
- **Bajo acoplamiento:** Todos los tests dependen de mocks. Sin dependencias externas.
- **Código existente es estable:** S4.1-S4.7 ejercitan código ya implementado y testeado en Pasos 0-1. No hay riesgo de romper algo no cubierto.
- **Riesgo de falso positivo en S4.2:** Si el mock de BaseCrew es demasiado simple (no simula latencia real), el test de concurrencia puede no detectar race conditions. Considerar usar `asyncio.sleep(0.01)` simulado en el mock para aproximar concurrencia real.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

Paso 4 **no toca APIs, endpoints, ni middleware**. No hay cambios en:
- Rutas FastAPI
- Middleware de auth
- Contratos HTTP
- Payloads de request/response

Los tests ejercitan **capa de lógica interna**:
- `AgentFactory.resolve_tools()` — resolución de tools
- `DynamicWorkflow._run_crew()` — ejecución de flujos
- `MCPPool` — circuit breaker y reset
- `sanitize_output()` — sanitización de strings
- `WorkflowDefinition` — validación Pydantic
- `flow_registry.register()` — registro de flows

**S4.1 (500 tools):** `resolve_tools` itera sobre `allowed_tools` y llama a `tool_registry.get()` para cada uno. Con 500 tools registradas, esto es O(n) lookup en dict. Sin IO, sin red. <2s es alcanzable.

**S4.2 (50 DynamicWorkflow concurrentes):** Cada instancia crea su propio `BaseCrew` (mockeado). `persist_state()` y `emit_event()` son mockedos. Sin locks compartidos. El único singleton compartido es `MCPPool` — y los tests de estrés lo resetean antes. Riesgo de falso negativo si el mock de BaseCrew no es thread-safe.

**S4.5 (10MB string):** `sanitize_output()` itera sobre 7 patrones regex sobre el string completo. 10MB × 7 patrones = ~70MB de procesamiento regex. <5s es factible con Python `re` nativo (C-backend). No OOM porque no hay copias intermedias grandes.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
S4.1: define 500 tools → AgentFactory.resolve_tools() → <2s, no memory leak
S4.2: 50× DynamicWorkflow(asyncio.gather) → _run_crew() (mock) → todos completan, 0 deadlocks
S4.3: MCPPool.reset() ×100 → singleton limpio cada vez → sin error
S4.4: DynamicWorkflow.register("same", def1) → register("same", def2) → def2 sobrescribe def1
S4.5: sanitize_output(str(10MB)) → <5s, sin OOM
S4.6: resolve_tools([...], org_id="") → lookup global (sin tenant prefix)
S4.7: WorkflowDefinition con input 20 niveles anidados → validación pasa, sin stack overflow
```

### Coherencia

Paso 4 es **coherente con la arquitectura existente**:
- Usa los mismos mocking patterns de Pasos 0-3
- Tests de estrés sobre código propio, no dependencias externas (alineado con objetivo del paso)
- No requiere LLM real, DB real, ni MCP real
- S4.3 (100× reset) es específico por el patrón singleton de MCPPool

### Gaps y ambigüedades

1. **S4.1 — "sin memory leak visible":** Criterio vago. Sin GC profiling, no hay forma objetiva de medir memory leak en un test. **Resolver:** Usar `sys.getsizeof()` parcial y verificar que garbage collector no retiene referencias. O cambiar criterio a "no retiene referencias a tools tras salir de scope".

2. **S4.2 — "0 deadlocks, todos completan":** `asyncio.gather()` con 50 corrutinas que internamente llaman `asyncio.gather()` (en BaseCrew). Potencial anidamiento de event loops si no se mockea correctamente. **Riesgo:** `RuntimeError: cannot run event loop` si se mezclan threads. **Mitigación:** Usar `asyncio.gather(return_exceptions=True)` y verificar que ninguna corrutina retorna excepción.

3. **S4.6 — "comportamiento definido" con `org_id` vacío:** `resolve_tools` pasa `org_id=""` a `tool_registry.get()`, que hace lookup sin prefijo de tenant. Esto funciona pero no hay documentación explícita de este comportamiento. Es un edge case no documentado.

4. **S4.7 — "sin stack overflow, sin timeout":** WorkflowDefinition validation es Pydantic, que maneja anidación profunda bien. Pero "20 niveles de profundidad" en `input_data` no es validado por Pydantic (es un field `Dict[str, Any]` sin validación de profundidad). **El test verifica que Pydantic no crashea, no que maneje el anidamiento correctamente.** Considerar si basta con que no explote.

### DX & Tooling

```
### Herramienta Propuesta: fap test-stress [test_id]
- **Qué automatiza:** Ejecuta tests de estrés/edge cases de Paso 4 con reporte de tiempo. S4.1 y S4.5 tienen thresholds temporales que requieren benchmarking manual sin la herramienta.
- **Tipo:** CLI command (extensión de `fap test-step` existente)
- **Cómo se usa:** `fap test-stress 4.1` → ejecuta S4.1 con `--benchmark` y reporta tiempo. `fap test-stress` → ejecuta todo Paso 4.
- **Impacto para el usuario final:** QA no necesita calcular thresholds manualmente. Herramienta falla si S4.1 >2s o S4.5 >5s.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

### Puntos críticos

- **S4.2 es el más riesgoso:** 50 corrutinas async concurrentes. Si el mock de BaseCrew no es perfectamente hermético, puede haber race conditions en el estado compartido de MCPPool. Considerar segregar: resetear MCPPool entre cada gather.
- **S4.5 requiere atención:** String de 10MB es grande para un test. 7 regex passes sobre 10MB es CPU-bound. En CI lento, puede exceder 5s. Considerar reducir threshold o marcar como benchmark informativo.
- **S4.7 es trivial:** Pydantic valida tipos no profundidad. 20 niveles de dict anidado pasa sin issue. El test es más una verificación de que no hay bug en Pydantic que un edge case real de código propio.

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] S4.1: resolve_tools con 500 tools registradas completa en <2s
✅ [CODE] S4.1: resolve_tools con 500 tools no retiene referencias (verify reference cleanup)
✅ [CODE] S4.2: 50 DynamicWorkflow en asyncio.gather completan sin excepción
✅ [CODE] S4.2: 50 DynamicWorkflow retornan Dict[str, Any] con resultados
✅ [CODE] S4.3: MCPPool.reset() llamado 100 veces consecutivas sin error
✅ [CODE] S4.3: Tras 100 resets, MCPPool.get() retorna instancia limpia (_health vacío)
✅ [CODE] S4.4: DynamicWorkflow.register("test_flow", def1).register("test_flow", def2) sobrescribe sin error
✅ [CODE] S4.4: flow_registry._flows["test_flow"] contiene def2 (no def1)
✅ [CODE] S4.5: sanitize_output(string 10MB) completa en <5s
✅ [CODE] S4.5: sanitize_output(string 10MB) no lanza MemoryError
✅ [CODE] S4.6: resolve_tools con org_id="" no lanza excepción
✅ [CODE] S4.6: resolve_tools con org_id="" retorna lista (vacía o con tools)
✅ [CODE] S4.7: WorkflowDefinition con input_data de 20 niveles no lanza RecursionError
✅ [CODE] S4.7: WorkflowDefinition validation pasa sin timeout
✅ [DX] fap test-stress ejecuta Paso 4 completo y reporta breakdown por test
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| S4.2 falso positivo: mocks no detectan race conditions | Alta | Mock de BaseCrew sin latencia simulada → no hay concurrencia real | Añadir `asyncio.sleep(0.01)` en mock de `run_async` para aproximar latencia |
| S4.5 timeout en CI lento | Media | 10MB × 7 regex patterns = ~70MB proceso. CPU-bound en CI compartido | Reducir a 5MB o marcar threshold como informativo (warning no fail) |
| S4.7 no detecta bug real de profundidad | Baja | Pydantic no limita profundidad de Dict[str, Any]. Test pasa incluso si hay bug downstream | No es un riesgo real — workflow consume input_data arbitrario sin recursión |
| phase-state.md fuera de sincronía | Media | Phase-state describe Pasos 2-7 con nombres distintos al plan. Implementador puede confundirse | Ignorar phase-state para este paso. Plan.md es fuente de verdad. Esperar actualización post-análisis. |
| `MCPPool` singleton contaminado entre tests de diferentes módulos | Media | Si `tests/stress/test_concurrency.py` y `tests/unit/test_mcp_pool_circuit.py` se ejecutan en同一 sesión | `MCPPool.reset()` en fixture `autouse=True` de cada archivo. Ya es patrón establecido. |
| 500 tools en registry puede ser lento si registry hace DB lookup | Baja | `tool_registry.get()` tiene fallback a DB. Si 500 tools no están en memoria, cada una hace DB query | Usar tool_registry.register() para poblar memoria ANTES de test. Sin DB calls. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap test-stress` command | FULLSTACK/DX | Media | 1h | Ninguna | → verificar: `fap test-stress 4.1` ejecuta sin errores y reporta tiempo |
| 1 | Crear `tests/stress/__init__.py` + `test_concurrency.py` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `pytest tests/stress/test_concurrency.py -v` descubre 3 tests |
| 2 | Implementar S4.1: `resolve_tools` con 500 tools | CODE | Media | 1h | Tarea 1 | → verificar: test pasa con <2s. 500 tools registradas en tool_registry antes de resolve |
| 3 | Implementar S4.2: 50 DynamicWorkflow en asyncio.gather | CODE | Alta | 2h | Tarea 1 | → verificar: 50 corrutinas completan sin excepción. Mock de BaseCrew con latencia simulada |
| 4 | Implementar S4.3: MCPPool.reset() 100 veces | CODE | Baja | 0.5h | Tarea 1 | → verificar: sin error tras 100 resets. `MCPPool.get()._health` vacío |
| 5 | Crear `tests/stress/test_edge_cases.py` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `pytest tests/stress/test_edge_cases.py -v` descubre 4 tests |
| 6 | Implementar S4.4: flow_type duplicado | CODE | Baja | 0.5h | Tarea 5 | → verificar: segundo register sobrescribe sin error. `_flows` contiene segunda definición |
| 7 | Implementar S4.5: sanitize_output 10MB | CODE | Media | 1h | Tarea 5 | → verificar: test pasa <5s. String 10MB con patrones intercalados |
| 8 | Implementar S4.6: org_id="" en resolve_tools | CODE | Baja | 0.5h | Tarea 5 | → verificar: resolve_tools con org_id="" retorna lista sin excepción |
| 9 | Implementar S4.7: input_data 20 niveles | CODE | Baja | 0.5h | Tarea 5 | → verificar: WorkflowDefinition no lanza RecursionError con dict 20 niveles |
| 10 | Validar suite completa con metrics | FULLSTACK | Baja | 0.5h | Tareas 1-9 | → verificar: `pytest tests/stress/ -v --timeout=30` pasa 7/7. Sin degradación de memoria >50MB |

**Tiempo total estimado:** 7.5 horas

---

## 🔮 Roadmap

- **S4.1 benchmark preciso:** Si CI corre consistentemente >2s, considerar reducir a 300 tools o hacer el threshold configurable.
- **S4.6 documentar comportamiento:** `org_id=""` en `resolve_tools` debería documentarse explícitamente como "global lookup" en docstring.
- **phase-state.md sync:** Actualizar phase-state.md para reflejar el plan.md v3.1 correcto. Los nombres de Pasos 2-7 divergen.
- **Bug doc `>=`/`<=`/`==`:** Actualizar phase-state.md línea 62 para reflejar que el fix ya existe en código.
