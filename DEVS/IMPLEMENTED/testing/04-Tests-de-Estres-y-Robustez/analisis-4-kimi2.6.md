# ANALISIS PASO 4 — AGENTE: kimi2.6

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `resolve_tools` en `AgentFactory` | `src/crews/factory.py:28` | ✅ | Firma: `resolve_tools(allowed_tools, org_id, async_mode=False)` |
| 2 | `DynamicWorkflow` clase | `src/flows/dynamic_flow.py:27` | ✅ | Hereda `BaseFlow`. `_run_crew()` async |
| 3 | `MCPPool` singleton | `src/tools/mcp_pool.py:35` | ✅ | `get()` crea instancia si `_instance is None` |
| 4 | `MCPPool.reset()` | `src/tools/mcp_pool.py:209` | ✅ | `cls._instance = None`. Limpia singleton |
| 5 | `MCPPool._is_circuit_open` | `src/tools/mcp_pool.py:60` | ✅ | Chequea `failures >= 5` y `elapsed < 60` |
| 6 | `sanitize_output` función | `src/mcp/sanitizer.py:28` | ✅ | Recursión dict/list + regex secrets |
| 7 | `WorkflowDefinition` modelo | `src/flows/workflow_definition.py:57` | ✅ | Pydantic BaseModel. `flow_type` snake_case validator |
| 8 | `flow_registry._flows` es dict plano | `src/flows/registry.py:40` | ✅ | Asignación directa `self._flows[name] = cls`. Segundo registro sobrescribe sin error |
| 9 | `DynamicWorkflow.register` | `src/flows/dynamic_flow.py:39` | ✅ | Crea subclase `RegisteredFlow`. Escribe en `flow_registry._flows` |
| 10 | `AgentFactory.resolve_tools` con `org_id=""` | `src/crews/factory.py:29` | ⚠️ | `tool_registry.get` con `org_id=""` → `if org_id:` evalúa False → salta a lookup global. No crash, comportamiento no documentado |
| 11 | `sanitize_output` sin límite de recursión | `src/mcp/sanitizer.py:43-46` | ⚠️ | Recursión directa en dict/list. JSON 20 niveles pasa (limite Python ~1000), pero sin protección explícita |
| 12 | `tests/stress/` directorio | `ls tests/` | ❌ | No existe. Solo `unit/`, `integration/`, `e2e/` |
| 13 | `test_concurrency.py` | `ls tests/stress/` | ❌ | No existe. Plan asume archivo nuevo |
| 14 | `test_edge_cases.py` | `ls tests/stress/` | ❌ | No existe. Plan asume archivo nuevo |
| 15 | `BaseCrew.run_async` acepta `inputs` | `src/crews/base_crew.py:169` | ✅ | `run_async(task_description, inputs, expected_output)` |
| 16 | `DynamicWorkflow._run_crew` pasa `previous_results` | `src/flows/dynamic_flow.py:96-101` | ✅ | `inputs={"step_inputs": ..., "previous_results": results, "original_input": ...}` |
| 17 | `MCPPool._health` defaultdict | `src/tools/mcp_pool.py:47` | ✅ | `defaultdict(lambda: {"failures": 0.0, "last_check": 0.0})` |
| 18 | `MCPPool._adapters` dict vacío al iniciar | `src/tools/mcp_pool.py:46` | ✅ | `self._adapters: Dict[str, object] = {}` |
| 19 | `WorkflowDefinition` no tiene método `register` | `src/flows/workflow_definition.py` | ⚠️ | Plan menciona "WorkflowDefinition con flow_type duplicado en registry". Registro real lo hace `DynamicWorkflow.register` o `@flow_registry.register`. `WorkflowDefinition` es solo schema Pydantic |
| 20 | `SECRET_PATTERNS` 7 regexes | `src/mcp/sanitizer.py:17-25` | ✅ | Stripe, Bearer, Basic, Slack, GitHub, Google |

**Discrepancias encontradas:**

1. **❌ `tests/stress/` no existe.** Plan asume directorio `tests/stress/` para `test_concurrency.py` y `test_edge_cases.py`. Crear directorio + `__init__.py` antes de tests.
2. **❌ `test_concurrency.py` y `test_edge_cases.py` no existen.** Archivos nuevos obligatorios.
3. **⚠️ `WorkflowDefinition` es schema Pydantic, no tiene método `register`.** Plan dice "WorkflowDefinition con flow_type duplicado en registry". Registro duplicado real ocurre en `flow_registry._flows` (dict plano) cuando `DynamicWorkflow.register` o `@flow_registry.register` se llaman 2 veces con mismo nombre. Test S4.4 debe usar `DynamicWorkflow.register` o `flow_registry.register`, no `WorkflowDefinition.register`.
4. **⚠️ `sanitize_output` recursión sin límite.** Python recursion limit ~1000. 20 niveles pasa, pero función no protege contra `RecursionError`. Si input tiene referencias circulares → crash infinito.
5. **⚠️ `org_id=""` en `resolve_tools` no tiene tratamiento especial.** `tool_registry.get` con `org_id=""` → `if org_id:` es False → lookup global. En modo no-strict, fallback a filesystem. Test S4.6 debe definir comportamiento esperado (retornar lista vacía o warning, no crash).

---

## 1️⃣ Análisis de Datos

Paso 4 = tests estrés/edge cases. **Sin cambios de schema DB.**

- **Tablas tocadas indirectamente:** `org_mcp_servers` (config MCP), `workflow_templates` (definiciones DynamicWorkflow), `agent_catalog` (config crew), `skill_catalog` (tools DB), `service_tools` (ServiceConnector). Ninguna modificación de schema requerida.
- **Integridad referencial:** No aplica. Tests usan mocks (fixtures `mock_service_client`, `mock_tenant_client`).
- **RLS:** No aplica. Tests de estrés no ejecutan queries reales contra Supabase.
- **Índices:** No relevante. Lookup de 500 tools es contra registry en memoria (`tool_registry._tools`: dict O(1)).
- **Tipos de datos problemáticos:** `input_data` en `DynamicWorkflow._run_crew` se pasa como `Dict[str, Any]` a `BaseCrew.run_async`. JSON 20 niveles de profundidad pasa por Pydantic `BaseModel` en `BaseFlowState` (`input_data: Dict[str, Any]`). No hay validación de profundidad en Pydantic por defecto. Riesgo: serialización a snapshot puede ser lenta con JSON masivo.

---

## 2️⃣ Análisis de Código

### Funciones/Clases testeadas

| Función/Clase | Archivo | Qué testea |
|---|---|---|
| `AgentFactory.resolve_tools` | `src/crews/factory.py:28` | S4.1: resolución masiva 500 tools mock. S4.6: `org_id=""` |
| `DynamicWorkflow._run_crew` | `src/flows/dynamic_flow.py:66` | S4.2: 50 instancias en `asyncio.gather`. S4.7: input JSON 20 niveles |
| `MCPPool.reset` | `src/tools/mcp_pool.py:209` | S4.3: 100 resets consecutivos |
| `DynamicWorkflow.register` | `src/flows/dynamic_flow.py:39` | S4.4: registro duplicado de `flow_type` |
| `sanitize_output` | `src/mcp/sanitizer.py:28` | S4.5: string 10MB |

### Patrones

- **Mocking:** Patrón confirmado en tests existentes. `MCPPool.reset()` en fixture `autouse=True`. `patch("time.time")` por test. `MagicMock` / `AsyncMock` para crews.
- **Async:** `pytest.mark.asyncio` + `async def` para tests async. Patrón usado en `test_mcp_pool_circuit.py`, `test_dynamic_flow.py`, `test_production_flows.py`.
- **Concurrencia:** `asyncio.gather` no usado aún en tests existentes. Nuevo patrón para S4.2.
- **Recursión:** `sanitize_output` usa recursión directa. S4.7 testea límite implícito.

### Modularidad

- Nuevos archivos en `tests/stress/` mantienen separación de concerns. `test_concurrency.py` = estrés concurrente. `test_edge_cases.py` = límites extremos.
- Sin modificar código fuente (`src/`). Solo tests.

### Calidad

- `sanitize_output` regex compila en cada llamada (`re.sub(pattern, ...)`). Con string 10MB y 7 patrones → 70 scans de regex sobre 10MB. Posible bottleneck. Python `re` usa backtracking. 10MB * 7 regexes puede ser lento (>5s) si patrones son complejos. Patrones actuales son simples (`[a-zA-Z0-9]+`), pero 10MB sigue siendo masivo.
- `AgentFactory.resolve_tools` itera `allowed_tools` en loop secuencial. 500 tools → 500 lookups en dict O(1) = rápido. Pero si tools son MCP, cada una hace `pool.get_tools` → potencialmente lento. S4.1 usa "todas mock registry", así que no hay IO real.

---

## 3️⃣ Análisis de Backend

### APIs / Endpoints

Paso 4 no crea endpoints nuevos. Tests estrés ejercitan funciones internas.

### Middleware

No aplica. Tests mockean DB/LLM/MCP.

### Flujos de datos

**S4.1 (resolve_tools 500):**
`allowed_tools: list[str]` → `AgentFactory.resolve_tools` → `tool_registry.get` (memory lookup) → `tool_cls(org_id=org_id)` → list[tool instances]. Sin IO.

**S4.2 (50 DynamicWorkflow concurrentes):**
`asyncio.gather(*[flow._run_crew() for _ in range(50)])` → cada flow crea `BaseCrew` → `crew.run_async()` → `kickoff_async()`. Todo mockeado vía `global_llm_mock` fixture. Flujo: inputs → crew mock → results dict.

**S4.5 (sanitize_output 10MB):**
`str(10MB)` → `re.sub` × 7 patrones → `str` output. CPU-bound. Posible slowdown.

### Contratos

- `AgentFactory.resolve_tools` → `list` (puede contener `MagicMock` en tests).
- `DynamicWorkflow._run_crew` → `Dict[str, Any]` (results por step_id).
- `sanitize_output` → `Any` (mismo tipo que input, con secrets reemplazados).

### Error handling

- `resolve_tools` loguea warning para tools no encontradas (`logger.warning`). No lanza excepción. Test S4.6 con `org_id=""` debe verificar que no crashea.
- `sanitize_output` captura `Exception` genérico y retorna `"[ERROR: output no pudo ser procesado]"`. Test S4.5 debe verificar que no crashea con 10MB.
- `MCPPool.reset` no lanza excepciones. Limpia `_instance = None`. Test S4.3 debe verificar estado limpio.

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo end-to-end

Paso 4 valida robustez del sistema bajo carga extrema. No hay interacción usuario directa, pero los tests garantizan que:

- `resolve_tools` no degrada con catálogo masivo (S4.1).
- Múltiples workflows concurrentes no bloquean el event loop (S4.2).
- `MCPPool` singleton tolera resets repetidos (S4.3).
- Registry de flows acepta re-registro sin crash (S4.4).
- Sanitización de output no OOM con payload masivo (S4.5).
- `org_id` vacío no rompe tool resolution (S4.6).
- JSON profundo no causa stack overflow en workflow execution (S4.7).

### Alineación plan vs arquitectura

Plan realizable. Todos los componentes existen. Tests puramente additive.

### Gaps

1. `sanitize_output` regex re-compila en cada llamada. No usa `re.compile` global. 10MB × 7 regexes = potencial bottleneck.
2. `DynamicWorkflow._run_crew` acumula `results` dict en memoria. 50 workflows concurrentes × N steps × result size = posible acumulación de memoria si resultados son grandes. En tests mockeados, resultados son strings pequeños.
3. `tool_registry.get` con `org_id=""` no valida formato UUID. Pasa directo a lookup global. Comportamiento silencioso.

### DX & Tooling (OBLIGATORIO)

```markdown
### Herramienta Propuesta: `fap stress-bench`
- **Qué automatiza:** Generación de fixtures masivos y ejecución de suite stress con métricas de tiempo/memoria integradas. Implementador actualmente debe manualmente crear 500 mocks de tools, 50 instancias de workflow, strings de 10MB, y JSON de 20 niveles.
- **Tipo:** CLI / comando
- **Cómo se usa:** `fap stress-bench --tools 500 --workflows 50 --sanitizer-size 10MB --json-depth 20`
- **Impacto para el usuario final:** Implementador deja de escribir fixtures masivos a mano. Comando genera mocks, ejecuta tests stress, reporta si thresholds tiempo/memoria se cumplen. Detecta regresiones de performance automáticamente.
- **Prioridad:** Tarea 0 — implementar antes que resto del paso
```

---

## 5️⃣ Criterios de Aceptación

- ✅ [CODE] Archivo `tests/stress/test_concurrency.py` existe con S4.1, S4.2, S4.3
- ✅ [CODE] Archivo `tests/stress/test_edge_cases.py` existe con S4.4, S4.5, S4.6, S4.7
- ✅ [BACKEND] S4.1: `resolve_tools` con 500 tools mock resuelve en <2s
- ✅ [BACKEND] S4.2: 50 `DynamicWorkflow` en `asyncio.gather` completan sin deadlock
- ✅ [BACKEND] S4.3: `MCPPool.reset()` 100 veces consecutivas sin error, singleton limpio
- ✅ [FULLSTACK] S4.4: `DynamicWorkflow.register` con `flow_type` duplicado sobrescribe sin error ni warning
- ✅ [FULLSTACK] S4.5: `sanitize_output` con string 10MB completa en <5s sin OOM
- ✅ [FULLSTACK] S4.6: `resolve_tools` con `org_id=""` no crashea, comportamiento definido
- ✅ [FULLSTACK] S4.7: `DynamicWorkflow` con `input_data` JSON 20 niveles de profundidad completa sin stack overflow
- ✅ [DX] `fap stress-bench` ejecuta sin errores y genera fixtures automáticamente

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `sanitize_output` regex sin `re.compile` → lento con 10MB | Media | 7 `re.sub` sobre string 10MB en cada llamada. Patrones simples pero volumen masivo. | Pre-compilar `SECRET_PATTERNS` con `re.compile` en módulo. Test S4.5 sirve como baseline. Si falla threshold → fix antes de merge. |
| `asyncio.gather` con 50 workflows mockeados puede colgar si mock incompleto | Media | `BaseCrew.run_async` llama `crew.kickoff_async()`. Si `global_llm_mock` no cubre algún import lazy, test puede timeout. | Forzar `global_llm_mock` fixture (autouse en conftest.py). Agregar `pytest.mark.timeout(30)` en S4.2. |
| `tests/stress/` nuevo → pytest no descubre sin `__init__.py` | Baja | Directorio sin `__init__.py` puede ser ignorado por `pytest --co`. | Crear `tests/stress/__init__.py`. Verificar con `pytest --co tests/stress/`. |
| `sanitize_output` recursión sin límite → `RecursionError` con JSON circular | Media | Dict con referencia circular (`a["b"] = a`) → recursión infinita en `sanitize_output`. Python límite ~1000. | Test S4.7 usa JSON profundo pero no circular. Agregar protección circular opcional en `sanitize_output` (ver `id()` tracking). |
| `MCPPool.reset()` no cierra adapters abiertos | Baja | `reset()` solo pone `_instance = None`. `_adapters` del instance anterior quedan sin cerrar. En tests no importa (mockeados), pero en producción es leak. | Test S4.3 verifica que nuevo `MCPPool.get()` tiene `_adapters == {}` y `_health` limpio. Documentar que `reset()` no es graceful shutdown. |
| `DynamicWorkflow.register` duplicado sobrescribe metadata sin merge | Baja | `flow_registry._metadata[flow_type_lower]` se re-asigna completamente. Si primer registro tenía `depends_on` y segundo no, se pierde. | Test S4.4 documenta comportamiento: "sobrescribe sin error — comportamiento documentado, no bug". Aceptar como diseño. |

---

## 7️⃣ Plan de Implementación

> [!IMPORTANT]
> Tarea 0 siempre = DX & Tooling. Ejecutar primero.

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap stress-bench` | FULLSTACK/DX | Media | 1h | Ninguna | → verificar: comando `fap stress-bench --tools 500 --workflows 50 --sanitizer-size 10MB --json-depth 20` genera fixtures y termina sin error. `fap stress-bench --help` muestra opciones. |
| 1 | Crear `tests/stress/__init__.py` | CODE | Baja | 0.1h | Tarea 0 | → verificar: `pytest --co tests/stress/` lista 7 tests (3 concurrencia + 4 edge cases). |
| 2 | Implementar `tests/stress/test_concurrency.py` (S4.1-S4.3) | CODE | Alta | 2h | Tarea 1 | → verificar: `pytest tests/stress/test_concurrency.py -v` pasa 3/3. S4.1 tiempo <2s. S4.2 0 deadlocks. S4.3 `_adapters == {}` y `_health` limpio tras 100 resets. |
| 3 | Implementar `tests/stress/test_edge_cases.py` (S4.4-S4.7) | CODE | Alta | 2h | Tarea 1 | → verificar: `pytest tests/stress/test_edge_cases.py -v` pasa 4/4. S4.5 <5s sin OOM. S4.7 sin `RecursionError`. |
| 4 | Pre-compilar `SECRET_PATTERNS` en `sanitize_output` (fix performance) | CODE | Baja | 0.5h | Ninguna | → verificar: `ruff check src/mcp/sanitizer.py` 0 errores. S4.5 sigue pasando y posiblemente más rápido. |
| 5 | Validar gate Paso 4 | FULLSTACK | Baja | 0.5h | Tareas 2-4 | → verificar: `pytest tests/stress/` 100% pass. `ruff check tests/stress/` 0 errores. Memoria no crece >50MB entre inicio y fin de suite (usar `tracemalloc` o `pytest-memray` si disponible). |

**Tiempo total estimado:** 6.1 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Optimización `sanitize_output`:** Convertir a iterativo con `deque` para eliminar riesgo `RecursionError` en payloads circulares. Mejora seguridad, no funcionalidad.
- **Benchmark automático:** Integrar `fap stress-bench` en CI para detectar regresiones de performance en cada PR.
- **`MCPPool.reset()` graceful:** Agregar cierre de adapters antes de `_instance = None` para evitar leaks en producción.
- **Validación `org_id`:** Agregar validación de formato UUID en `tool_registry.get` y `flow_registry.get` para rechazar `org_id=""` explícitamente en lugar de fallback silencioso.

---

## 🚫 Reglas de Oro — Estado

- ✅ Análisis accionable y específico
- ✅ TODO verificado contra código (20 elementos en §0)
- ✅ ≥4 discrepancias detectadas y documentadas
- ≥1 herramienta DX propuesta (`fap stress-bench`)
- ✅ Cada tarea con verificación inline (`→ verificar:`)
- ✅ TODO el paso cubierto (S4.1-S4.7)
- ✅ Etapas secuenciales data → code → backend → fullstack+DX
