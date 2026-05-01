# Análisis Técnico — Paso 3: E2E — Flujos Completos con Mocks

**Agente:** ds
**Paso:** 3
**Fecha:** 2026-05-01
**Plan:** `DEVS/plan.md` (Paso 3, pág. 8-9)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `tests/e2e/test_production_flows.py` existe | grep en `tests/e2e/` | ✅ NO existe | Archivo debe crearse |
| 2 | `tests/e2e/` directorio existe | `ls tests/e2e/` | ✅ EXISTE | Contiene 10 archivos + `__init__.py` |
| 3 | `DynamicWorkflow` clase existe | `src/flows/dynamic_flow.py` | ✅ EXISTE | Línea 30: `class DynamicWorkflow(BaseFlow)` |
| 4 | `DynamicWorkflow._run_crew()` existe | `src/flows/dynamic_flow.py` | ✅ EXISTE | Línea 66: `async def _run_crew(self)` |
| 5 | `DynamicWorkflow._check_approval_rule()` existe | `src/flows/dynamic_flow.py` | ✅ EXISTE | Línea 128, soporta `>=`/`<=`/`==` corregido |
| 6 | `BaseFlow.request_approval()` existe | `src/flows/base_flow.py` | ✅ EXISTE | Línea 267 |
| 7 | `BaseFlow.resume()` existe | `src/flows/base_flow.py` | ✅ EXISTE | Línea 341 |
| 8 | `BaseFlow._on_approved()` existe | `src/flows/base_flow.py` | ✅ EXISTE | Línea 405 — marca COMPLETED con `{"approval": "accepted"}` |
| 9 | `AgentFactory.resolve_tools()` existe | `src/crews/factory.py` | ✅ EXISTE | Línea 28, decorador `@staticmethod` |
| 10 | `MCPPool.get_tools()` existe | `src/tools/mcp_pool.py` | ✅ EXISTE | Línea 77, `async def get_tools(...)` |
| 11 | `MCPPool.get()` singleton existe | `src/tools/mcp_pool.py` | ✅ EXISTE | Línea 48 `@classmethod` |
| 12 | `FlowStatus.AWAITING_APPROVAL` existe | `src/flows/state.py` | ✅ EXISTE | Línea 24 `awaiting_approval` |
| 13 | `FlowStatus.PENDING`/`COMPLETED` existen | `src/flows/state.py` | ✅ EXISTE | Líneas 21, 23 |
| 14 | `global_llm_mock` fixture en conftest.py | `tests/conftest.py` | ✅ EXISTE | Línea 274, `autouse=True` |
| 15 | `mock_service_client` fixture | `tests/conftest.py` | ✅ EXISTE | Línea 111 |
| 16 | `mock_mcp_pool` fixture | `tests/conftest.py` | ✅ EXISTE | Línea 303 |
| 17 | `mock_tenant_client` fixture | `tests/conftest.py` | ✅ EXISTE | Línea 174 |
| 18 | `test_handover_real.py` (Paso 2) existe | `tests/integration/` | ✅ EXISTE | Cubre I3.1-I3.3 (2-step handover, 0 steps, partial failure) |
| 19 | `test_dynamic_flow.py` existe | `tests/integration/` | ✅ EXISTE | Cubre _run_crew, approval trigger, registration |
| 20 | 6 e2e escenarios existentes | `tests/e2e/test_scenario_*.py` | ✅ EXISTEN | 6 archivos (greeter, integration, mcp, hybrid, multi_agent, full_stack) |

**Elementos verificados: 20/20 (umbral mínimo 12 para 1-2 archivos afectados)**

### Discrepancias Encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | Plan: estado E3.2 como `PENDING → AWAITING_APPROVAL → COMPLETED`. Real: `execute()` pasa por `RUNNING` antes de `AWAITING_APPROVAL`. Flujo real: PENDING → RUNNING → AWAITING_APPROVAL → COMPLETED. | No afecta test si se mockea `execute()` y se prueba `resume()` directamente. El test debería verificar el estado final tras `resume()`, no la secuencia de transiciones. Documentar en criterios. |
| D2 | Plan: E3.1 "warning in log" tras MCP fallo. Real: `factory.py:59` loggea a nivel `logger.error`, no `warning`. | Ajustar criterio E3.1 a "error in log" o aceptar ambos. No afecta implementación — test verifica que no crashea. |
| D3 | E3.3 casi duplicado de I3.1 (`test_handover_real.py:69`). I3.1 prueba 2-step handover con `_run_crew()` directo. E3.3 necesita 3 steps. | E3.3 sigue siendo válido — 3 steps demuestra profundidad de contexto que 2 steps no prueba. Diferencia real: 3 niveles vs 2. Reducir duplicación reusando template builder. |
| D4 | `_on_approved()` por defecto NO continúa el workflow — llama `self.state.complete({"approval": "accepted"})` y termina. El plan asume que `resume()` reanuda ejecución de steps restantes. Real: solo marca como COMPLETED. | E3.2 debe testear que tras `resume("approved")` el estado es COMPLETED con resultado `{"approval": "accepted"}` — NO que los steps continúan. Si se requiere ejecución post-aprobación, es feature request futuro. |

---

## 1️⃣ Análisis de Datos

Paso 3 no crea ni modifica schema de DB. 100% mockeado.

- ✅ **Tablas afectadas:** Ninguna. Tests corren contra mocks (`mock_service_client`, `mock_tenant_client`).
- ✅ **Migraciones:** No aplica. Sin cambios en `supabase/migrations/`.
- ✅ **RLS:** No aplica.
- ✅ **Índices:** No aplica.
- ✅ **Datos existentes:** No afectados.

**Schema ER:** No aplica (sin cambios de datos).

---

## 2️⃣ Análisis de Código

### Archivo a crear

| Archivo | Tipo | Líneas estimadas |
|---|---|---|
| `tests/e2e/test_production_flows.py` | Nuevo test E2E | ~200-250 líneas |

### Estructura propuesta

```
tests/e2e/test_production_flows.py
├── Imports (pytest, AsyncMock, MagicMock, patch, DynamicWorkflow, AgentFactory)
├── CONSTANTES: Templates de workflow (3 templates)
│   ├── DEGRADED_MCP_TEMPLATE (1 step con 2 MCP tools)
│   ├── APPROVAL_GATE_TEMPLATE (1 step + 1 approval rule > 50000)
│   └── MULTI_STEP_TEMPLATE (3 steps: analyst → processor → reviewer)
├── TestE3_1DegradedMCP (class)
│   └── test_resolve_tools_partial_failure
├── TestE3_2ApprovalGateHITL (class)
│   ├── test_approval_flow_pending_to_awaiting
│   └── test_approval_flow_resume_completes
└── TestE3_3MultiStepHandover (class)
    └── test_three_step_context_preservation
```

### Patrones a seguir

| Patrón | Fuente | Cómo aplica |
|---|---|---|
| Mocking de `BaseCrew` via `patch("src.flows.dynamic_flow.BaseCrew")` | `test_dynamic_flow.py:92` | Idéntico para E3.2 y E3.3 |
| `crew_side_effect` que retorna mock distinto por `role` | `test_handover_real.py:94` | Idéntico para E3.3 (3 roles) |
| `DynamicWorkflow(org_id=...)` + asignar `_template_definition` manual | `test_dynamic_flow.py:73-77` | Patrón estándar |
| `MCPPool.get()` mockeado via `mock_mcp_pool` fixture | `conftest.py:303` | E3.1 necesita mock parcial (1 tool retorna, 1 falla) |
| `resolve_tools()` llamado directamente con `allowed_tools` | `factory.py:28` | E3.1 testea directamente `resolve_tools`, no el workflow completo |

### Modularidad

- E3.1: Testea `AgentFactory.resolve_tools()` directamente + el loop `resolve_tools` en `_run_crew()`. La función ya maneja fallos MCP via try/except (línea 56-60 de `factory.py`).
- E3.2: Testea `DynamicWorkflow.execute()` + `BaseFlow.resume()`. Depende de mocking de `BaseCrew` y `get_service_client`.
- E3.3: Testea `DynamicWorkflow._run_crew()` con 3 steps. Casi idéntico a `test_handover_real.py` pero 3 steps en vez de 2.

### Riesgo de duplicación

| Test existente | E3.x similar | Diferencia |
|---|---|---|
| `test_dynamic_flow.py:test_triggers_approval_when_rule_matches` | E3.2 | Existente solo prueba que `request_approval` se llama. E3.2 prueba el ciclo completo `execute()` → AWAITING_APPROVAL → `resume()` → COMPLETED. |
| `test_handover_real.py:I3.1` | E3.3 | I3.1 = 2 steps. E3.3 = 3 steps. Diferencia real pero pequeña. |

---

## 3️⃣ Análisis de Backend

Paso 3 no crea endpoints ni modifica middleware. Mockeo completo de servicios.

### Superficie de mockeo requerida

| Servicio real | Mock | E3.x que lo usa |
|---|---|---|
| `get_service_client()` | `mock_service_client` fixture | E3.2 (resume usa snapshots) |
| `get_tenant_client()` | `mock_tenant_client` fixture | E3.2 (resume usa pending_approvals) |
| `BaseCrew.run_async()` | `AsyncMock` en patched `BaseCrew` | E3.2, E3.3 |
| `MCPPool.get_tools()` | `mock_mcp_pool` fixture (parcial) | E3.1 |
| `AgentFactory.resolve_tools()` | Mock de `_resolve_mcp_tool` para fallo parcial | E3.1 |
| `EventStore.append_sync()` | `mock_event_store` fixture | E3.2 |
| `time.time()` | `unittest.mock.patch` | No necesario (no hay circuit breaker en estos tests) |

### Flujo E3.2 (Approval Gate HITL)

```
test:
  1. Crear DynamicWorkflow(org_id) con APPROVAL_GATE_TEMPLATE
  2. Mock BaseCrew.run_async → retorna "100000" (activa approval rule > 50000)
  3. LLamar flow.execute()
  4. Verificar state.status == AWAITING_APPROVAL
  5. flow.state.task_id = "test-task-id" (o extraer de snapshot mock)
  6. Llamar flow.resume(task_id="test-task-id", decision="approved", decided_by="tester")
  7. Verificar state.status == COMPLETED
```

**Contrato del endpoint `resume()`:**
- Input: `task_id`, `decision` ("approved"/"rejected"), `decided_by`, `notes` (opcional)
- Busca snapshot por `aggregate_id` + `aggregate_type`
- Restaura estado desde snapshot
- Emite evento `approval.approved` o `approval.rejected`
- Llama `_on_approved()` o `_on_rejected()`
- Output: estado final del flow

### Flujo E3.1 (Degraded MCP)

```
test:
  1. Mock MCPPool.get() → mock pool donde get_tools retorna 1 tool
  2. Mock AgentFactory._resolve_mcp_tool → 1 tool ok, 1 lanza excepción
  3. Llamar AgentFactory.resolve_tools(["mcp:server:tool_a", "mcp:server:tool_b"], org_id, async_mode=True)
  4. Verificar: tools contiene 1 elemento
  5. Verificar: logger.error fue llamado (no crash)
```

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo End-to-End

```
E3.1 ──> AgentFactory.resolve_tools()
           ├── mcp:server:tool_a → MCPPool.get_tools() → mock retorna tool_a ✅
           └── mcp:server:tool_b → lanza Exception         → log error, continue ❌
           └── Resultado: 1 tool en lista, sin crash

E3.2 ──> DynamicWorkflow.execute()
           ├── _run_crew()
           │   ├── step_1 → BaseCrew.run_async() → "100000"
           │   ├── _check_approval_rule("monto > 50000", results) → True
           │   └── request_approval() → state.AWAITING_APPROVAL, return early
           ├── execute() detecta AWAITING_APPROVAL → return state
           └── resume(task_id, "approved")
               ├── restore snapshot
               ├── EventStore.append_sync("approval.approved")
               └── _on_approved() → state.COMPLETED

E3.3 ──> DynamicWorkflow._run_crew()
           ├── step_1 (analyst) → "Output A"
           ├── step_2 (processor) recibe previous_results → "Output B"
           ├── step_3 (reviewer) recibe previous_results con step_1 + step_2
           └── results = {step_1: ..., step_2: ..., step_3: ...}
```

### Coherencia Plan vs Arquitectura

| Afirmación del plan | Verificación |
|---|---|
| "Todo mockeado — sin LLM real, sin DB real, sin MCP real" | ✅ Factible. Fixtures existentes cubren todos los servicios. |
| "Cada flujo <5s" | ✅ Sin IO real, solo mocks. Tests asíncronos con `pytest.mark.asyncio`. |
| "E3.2: PENDING → AWAITING_APPROVAL → COMPLETED" | ⚠️ Omite RUNNING intermedio (D1). Pero verificar estado final es suficiente. |
| "resolve_tools con 2 tools, pool retorna 1" | ✅ `factory.py:56-60` captura excepción y continúa. |
| "Multi-step: 3 steps, contexto preservado 3 niveles" | ✅ `_run_crew()` pasa `results` acumulativo a cada step. |

### DX & Tooling — OBLIGATORIO

```
### Herramienta Propuesta: `fap test-step 3`
- **Qué automatiza:** Ejecución de los 3 tests E2E del Paso 3 con un solo comando.
- **Tipo:** CLI (extensión de comando existente `fap test-step`)
- **Cómo se usa:** `fap test-step 3` → corre `pytest tests/e2e/test_production_flows.py -v`
- **Soporte cobertura:** `fap test-step 3 --cov` → añade `--cov=src --cov-report=term-missing`
- **Impacto para el usuario final:** No más escribir `pytest tests/e2e/test_production_flows.py -v --no-header -q`. Un comando = validación completa.
- **Prioridad:** Baja — `fap test-step 1` ya existe como patrón. Extender es trivial.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] `tests/e2e/test_production_flows.py` existe con 3 clases de test (E3.1, E3.2, E3.3)
✅ [CODE] Cada test es `@pytest.mark.asyncio` y usa fixtures mock (`mock_service_client`, `mock_tenant_client`, `mock_event_store`, `mock_mcp_pool`)
✅ [E3.1] `test_resolve_tools_partial_failure`: AgentFactory.resolve_tools con 2 MCP tools → 1 disponible, 1 falla → tools contiene 1 elemento, sin excepción propagada
✅ [E3.1] Logger registra error para MCP tool que falla
✅ [E3.2] `test_approval_flow_pending_to_awaiting`: execute() con approval rule activada → state.status == AWAITING_APPROVAL
✅ [E3.2] `test_approval_flow_resume_completes`: resume(task_id, "approved") → state.status == COMPLETED
✅ [E3.2] Estado final tras resume() tiene resultado de _on_approved (no de steps restantes)
✅ [E3.3] `test_three_step_context_preservation`: 3 steps ejecutados en orden
✅ [E3.3] step_2 recibe previous_results con step_1
✅ [E3.3] step_3 recibe previous_results con step_1 Y step_2
✅ [E3.3] results final contiene las 3 keys: step_1, step_2, step_3
✅ [DX] `fap test-step 3` ejecuta los 3 tests y reporta pass/fail
⛔ [PERF] Cada test completa en <5s (todo mockeado, sin IO real)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: E3.2 no prueba ciclo HITL completo porque `resume()` internamente busca snapshot en DB | Alta | `BaseFlow.resume()` línea 344-351: `svc.table("snapshots").select("*").eq("aggregate_id", task_id).maybe_single().execute()`. Sin mock snapshot real → `svc.table().select()...execute()` retorna `None` → `resume()` falla con `ValueError: No snapshot found`. | Mock de `snapshots` table en `mock_service_client` para que retorne snapshot válido cuando se consulta por `aggregate_id`. O alternativa: parchear `BaseFlow.resume()` directamente para evitar DB. |
| R2: E3.1 necesita mock más específico que `mock_mcp_pool` | Media | `mock_mcp_pool` fixture retorna 3 tools siempre. Para E3.1 necesitamos que 1 tool falle y otra no. El fixture actual no soporta fallo parcial. | Crear mock personalizado en el test: `mock_pool = AsyncMock(side_effect=[tool_list, Exception("MCP error")])` o similar. No reusar fixture directamente. |
| R3: E3.2 depende de `task_id` generado en `create_task_record` | Media | `execute()` llama `create_task_record()` que escribe en DB. Si se mockea `create_task_record` → no hay `task_id` → `resume()` no tiene qué task reanudar. | Estrategia 1: Mockear `create_task_record` y asignar `state.task_id` manualmente. Estrategia 2: Usar `flow.state.task_id = "test-id"` después de `execute()` pero antes de `resume()`. Recomendada: Estrategia 2. |
| R4: E3.3 duplicación con I3.1 (test_handover_real.py) | Baja | Mismo patrón: mock BaseCrew con crew_side_effect, ejecutar _run_crew, verificar previous_results. Diferencia solo en cantidad de steps. | Aceptar duplicación menor o extraer template builder reutilizable en conftest.py. No worth el refactor ahora. |
| R5: `global_llm_mock` fixture autouse puede interferir con mocks específicos | Baja | `autouse=True` parchea `ChatOpenAI`, `ChatOllama`, `crewai.Agent`, `crewai.Task`, `crewai.Crew`. Si un test necesita mock específico de Crew, puede haber conflicto. | `global_llm_mock` ya está diseñado para convivir con mocks específicos (parchea clases base, no instancias). Bajo riesgo real. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Extender `fap test-step` para Paso 3 | FULLSTACK/DX | Baja | 0.5h | Ninguna | → verificar: `fap test-step 3` corre `pytest tests/e2e/test_production_flows.py` sin errores |
| 1 | Crear `tests/e2e/test_production_flows.py` con imports y fixtures base | CODE | Baja | 0.5h | Tarea 0 | → verificar: archivo existe, importable (`pytest --co tests/e2e/test_production_flows.py`) |
| 2 | Implementar E3.1 — Test Degraded MCP | CODE | Media | 1h | Tarea 1 | → verificar: `pytest tests/e2e/test_production_flows.py::TestE3_1DegradedMCP` pasa, 1 tool en resultado, log de error verificado |
| 3 | Implementar E3.2 — Test Approval Gate HITL | CODE | Alta | 2h | Tarea 1 | → verificar: snapshot mock retorna data válida, `execute()` → AWAITING_APPROVAL, `resume("approved")` → COMPLETED |
| 4 | Implementar E3.3 — Test Multi-step Handover | CODE | Media | 1h | Tarea 1 | → verificar: 3 steps ejecutados, previous_results contiene step_1 y step_2 en step_3 |
| 5 | Validar suite completa Paso 3 | FULLSTACK | Baja | 0.5h | Tareas 2-4 | → verificar: `fap test-step 3` reporta 3/3 tests pass, cada test <5s, lint `ruff check tests/e2e/test_production_flows.py` 0 errores |

**Tiempo total estimado:** 5.5 horas

### Notas de implementación por tarea:

**Tarea 2 (E3.1):** No reusar `mock_mcp_pool` fixture directamente. Crear mock inline con `AsyncMock` que retorne lista parcial. Mockear `AgentFactory._resolve_mcp_tool` con `patch.object(AgentFactory, '_resolve_mcp_tool')` y `side_effect` que retorne tool para primer llamado y lance `Exception("MCP connection failed")` para segundo.

**Tarea 3 (E3.2):** Atención especial al mock de snapshot. `mock_service_client.table("snapshots").select(...).maybe_single().execute()` debe retornar `Mock(data={"aggregate_id": "test-task-id", "state_json": {...}})` — donde `state_json` es un snapshot válido de `BaseFlowState.to_snapshot_v2()`. Alternativa: parchear `BaseFlow.resume` directamente para evitar TODO el camino de DB.

**Tarea 4 (E3.3):** Reusar patrón `crew_side_effect` de `test_handover_real.py`. Template con 3 roles (analyst, processor, reviewer). Mock de BaseCrew retorna 3 instancias distintas con outputs encadenados.

---

## 🔮 Roadmap

- **Optimización E3.3:** Si se extrae el template builder a conftest.py, E3.3 y tests handover existentes pueden compartir lógica. Refactor futuro.
- **Feature post-Paso 3:** Si `_on_approved()` se modifica para continuar steps (en vez de solo marcar COMPLETED), E3.2 debe expandirse para verificar ejecución post-aprobación. Depende de decisión arquitectura.
- **MCP Degraded test a nivel integration:** E3.1 solo testea `resolve_tools` aislado. Test de integración que ejecute DynamicWorkflow entero con MCP parcial sería valioso (futuro Paso 2.5).
