# Análisis Técnico — Paso 3: E2E — Flujos Completos con Mocks

**Agente:** qwen
**Paso:** 3
**Fecha:** 2026-05-01
**Archivo destino:** `DEVS/IN_PROGRESS/analisis-3-qwen.md`

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `DynamicWorkflow._run_crew()` existe | `src/flows/dynamic_flow.py:66` | ✅ | Línea 66-126, async method |
| 2 | `DynamicWorkflow._check_approval_rule()` existe | `src/flows/dynamic_flow.py:128` | ✅ | Línea 128-185, soporta >=, <=, ==, >, < |
| 3 | `BaseCrew.run_async()` existe | `src/crews/base_crew.py:169` | ✅ | Línea 169-205, async method |
| 4 | `BaseFlow.request_approval()` existe | `src/flows/base_flow.py:267` | ✅ | Línea 267-339, HITL pause |
| 5 | `BaseFlow.resume()` existe | `src/flows/base_flow.py:341` | ✅ | Línea 341-403, HITL resume |
| 6 | `MCPPool.get_tools()` existe | `src/tools/mcp_pool.py:77` | ✅ | Línea 77-191, async con circuit breaker |
| 7 | `MCPPool.reset()` existe | `src/tools/mcp_pool.py:211` | ✅ | Línea 211-213, classmethod |
| 8 | `AgentFactory.resolve_tools()` existe | `src/crews/factory.py:28` | ✅ | Línea 28-78, sync/async mode |
| 9 | `global_llm_mock` fixture existe | `tests/conftest.py:274` | ✅ | Autouse, mockea crewai.Agent/Task/Crew |
| 10 | `mock_service_client` fixture existe | `tests/conftest.py:111` | ✅ | 8 patch points |
| 11 | `mock_mcp_pool` fixture existe | `tests/conftest.py:303` | ✅ | Retorna 3 mock tools |
| 12 | `mock_event_store` fixture existe | `tests/conftest.py:219` | ✅ | Mockea get_tenant_client |
| 13 | `mock_tenant_client` fixture existe | `tests/conftest.py:174` | ✅ | Context manager mock |
| 14 | `sanitize_output()` existe | `src/mcp/sanitizer.py:28` | ✅ | Línea 28-50, 7 patrones |
| 15 | `ServiceConnectorTool._run()` existe | `src/tools/service_connector.py:60` | ✅ | Línea 60-170, 6 ramas error |
| 16 | `test_mcp_resilience.py` existe | `tests/integration/test_mcp_resilience.py` | ✅ | I2.1-I2.3 implementados |
| 17 | `test_handover_real.py` existe | `tests/integration/test_handover_real.py` | ✅ | I3.1-I3.3 implementados |
| 18 | `test_dynamic_flow.py` existe | `tests/integration/test_dynamic_flow.py` | ✅ | Approval rules, execution, registration |
| 19 | `WorkflowDefinition` Pydantic model | `src/flows/workflow_definition.py:57` | ✅ | Validación completa con cycle detection |
| 20 | `flow_registry` singleton | `src/flows/registry.py:370` | ✅ | `has()`, `get()`, `clear()` |
| 21 | `test_scenario_6_full_stack.py` existe | `tests/e2e/test_scenario_6_full_stack.py` | ✅ | 8 tests, bundle + validation |
| 22 | `test_mvp_certification.py` existe | `tests/e2e/test_mvp_certification.py` | ✅ | 7 criterios MVP |
| 23 | `test_scenario_5_multi_agent.py` existe | `tests/e2e/test_scenario_5_multi_agent.py` | ✅ | 5 tests multi-agent |
| 24 | `tests/e2e/` directorio existe | `tests/e2e/` | ✅ | 12 archivos .py |
| 25 | `BaseFlow.execute()` existe | `src/flows/base_flow.py:106` | ✅ | Lifecycle completo con error handling |
| 26 | `BaseFlowState` existe | `src/flows/state.py` | ✅ | Importado en base_flow.py:28 |
| 27 | `EventStore` existe | `src/events/store.py` | ✅ | Importado en base_flow.py:27 |
| 28 | `conftest.py` `sample_org_id` fixture | `tests/conftest.py:24` | ✅ | UUID fixture |

**Discrepancias encontradas:**

1. **⚠️ Plan dice `tests/e2e/test_production_flows.py` nuevo — pero `tests/e2e/` ya tiene 12 archivos.** El plan original (v3.1) fue diseñado antes de que existieran `test_scenario_*.py`. Los 3 tests E2E propuestos (E3.1-E3.3) ejercen combinaciones NO cubiertas por los 6 escenarios existentes. Ver §4 para análisis de solapamiento.

2. **⚠️ `approval_threshold` en `StepDefinition` (workflow_definition.py:47) sigue sin usarse en `_run_crew()`.** El workflow usa `approval_rules[].condition` (string). El campo `approval_threshold` del step se define pero nunca se lee. Deuda técnica confirmada.

3. **⚠️ `_check_approval_rule()` ya soporta >=, <=, == (dynamic_flow.py:144-150).** El plan v3.1 dice "bug conocido: >=/<=/== no parseados" pero el código actual YA los soporta correctamente. El fix ya se aplicó. Los tests condicionales del Paso 2 (I4.1-I4.3) ahora son viables sin fix previo.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Alcance:** Paso 3 es puramente E2E con mocks. No toca DB real, no crea tablas, no modifica schema.

- ✅ **Tablas tocadas:** Ninguna directamente. Todos los accesos a DB son mockeados via `mock_service_client` y `mock_tenant_client`.
- ✅ **Schema impacto:** Cero. Los tests E2E propuestos usan templates hardcodeados de `WorkflowDefinition`, no leen/escriben DB.
- ✅ **RLS policies:** No aplicable — todo mockeado.
- ✅ **Índices:** No aplicable.

**Diagrama ER conceptual (solo para referencia de los flujos E2E):**

```
workflow_templates (definition JSONB)
    ↓
DynamicWorkflow._run_crew()
    ↓
BaseCrew.run_async() → crewai.Crew.kickoff_async()
    ↓
AgentFactory.resolve_tools() → MCPPool.get_tools() (si mcp: prefix)
    ↓
results dict → persist_state() → snapshots table
    ↓
emit_event() → domain_events table
```

**Conclusión DATA:** Sin impacto. Paso 3 es 100% código en memoria con mocks.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 2.1 Tests E2E propuestos — E3.1 "Degraded MCP"

**Descripción:** `resolve_tools` con 2 tools MCP: pool retorna 1, otra falla.

**Archivos involucrados:**
- `src/crews/factory.py` — `resolve_tools()` (línea 28-78)
- `src/tools/mcp_pool.py` — `get_tools()` (línea 77-191)
- `tests/e2e/test_production_flows.py` — NUEVO

**Patrón existente confirmado:** `test_mcp_resilience.py` ya testa circuit breaker a nivel integración. `test_scenario_6_full_stack.py` ya testa bundle con MCP tools. Pero **ningún test E2E** simula degradación parcial (1 tool funciona, 1 falla).

**Funciones/clases nuevas propuestas:**
- `TestProductionFlows` class en `test_production_flows.py`
- `test_degraded_mcp()` — E3.1
- `test_approval_gate_hitl()` — E3.2
- `test_multi_step_handover()` — E3.3

**Firmas esperadas:**
```python
@pytest.mark.asyncio
async def test_degraded_mcp(mock_service_client, mock_tenant_client, mock_event_store, sample_org_id):
    """E3.1: resolve_tools con MCP parcial — 1 tool ok, 1 falla."""
```

**Patrón de mocking:**
- `mock_service_client` para DB queries de `org_mcp_servers`
- `patch("crewai_tools.MCPServerAdapter")` para simular conexión MCP
- `global_llm_mock` (autouse) para crewai.Agent/Task/Crew
- `MCPPool.reset()` en fixture autouse

**Cohesión/Acoplamiento:** Tests E2E deben ser autocontenidos. Cada test crea su propio template, mockea sus dependencias, y verifica el flujo completo. Bajo acoplamiento entre tests.

**Imports necesarios:**
```python
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.flows.dynamic_flow import DynamicWorkflow
from src.crews.factory import AgentFactory
from src.tools.mcp_pool import MCPConnectionError, MCPPool
```

### 2.2 Tests E2E propuestos — E3.2 "Approval Gate HITL"

**Descripción:** Flujo con approval rule → `request_approval` → `resume()` → completa.

**Archivos involucrados:**
- `src/flows/base_flow.py` — `request_approval()` (línea 267), `resume()` (línea 341)
- `src/flows/dynamic_flow.py` — `_run_crew()` con approval_rules (línea 118-124)
- `tests/e2e/test_production_flows.py` — NUEVO

**Patrón existente:** `test_hitl_pause_resume.py` ya existe en integration. `test_dynamic_flow.py` ya testa `request_approval` trigger. Pero **ningún test E2E** cubre el ciclo completo: PENDING → AWAITING_APPROVAL → COMPLETED.

**Verificación clave:**
- `flow.state.status` debe transicionar: `pending` → `running` → `awaiting_approval` → `completed`
- `request_approval()` debe ser llamado cuando `_check_approval_rule()` retorna True
- `resume()` con decision="approved" debe completar el flow

**Discrepancia detectada:** `base_flow.py:412-415` — `_on_approved()` por defecto marca como COMPLETED con `{"approval": "accepted"}`. Esto significa que tras `resume()`, el flow NO continúa ejecutando steps restantes — simplemente completa. El ciclo HITL completo E2E debe reflejar esto: el flow se pausa, se aprueba, se marca completo. No hay "continuación" automática de steps.

### 2.3 Tests E2E propuestos — E3.3 "Multi-step handover"

**Descripción:** 3 steps, cada uno consume output del anterior. Contexto preservado 3 niveles.

**Archivos involucrados:**
- `src/flows/dynamic_flow.py` — `_run_crew()` con `previous_results` (línea 97-99)
- `tests/e2e/test_production_flows.py` — NUEVO

**Patrón existente:** `test_handover_real.py` ya testa 2 steps con contexto (I3.1). `test_scenario_5_multi_agent.py` ya testa 3 steps con `depends_on`. Pero **ningún test** verifica `previous_results` a 3 niveles de profundidad en un contexto E2E.

**Diferencia clave con integration tests:** Los integration tests mockean `BaseCrew` directamente. Los E2E deben usar `global_llm_mock` (autouse) que mockea crewai a nivel de import, no a nivel de clase. Esto significa que el test E2E debe verificar que el mock de crewai recibe los inputs correctos con `previous_results` acumulados.

### 2.4 Reutilización de patrones existentes

| Patrón | Archivo referencia | Uso en Paso 3 |
|---|---|---|
| `@pytest.mark.asyncio` | `test_mcp_resilience.py:54` | Todos los tests E3.x |
| `MCPPool.reset()` autouse | `test_mcp_resilience.py:36` | Fixture para E3.1 |
| `mock_service_client` | `conftest.py:111` | Todos los tests |
| `global_llm_mock` | `conftest.py:274` | Todos los tests (autouse) |
| Template dict hardcodeado | `test_handover_real.py:17` | E3.2, E3.3 |
| `patch("src.flows.dynamic_flow.BaseCrew")` | `test_dynamic_flow.py:168` | E3.2, E3.3 |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Alcance:** Paso 3 no crea endpoints nuevos. Es puramente testing E2E con mocks.

### 3.1 Endpoints indirectamente ejercidos

Los tests E2E ejercen el flujo interno que los siguientes endpoints usarían en producción:

| Endpoint indirecto | Ruta | Qué ejercita |
|---|---|---|
| POST `/webhooks/{org_id}/{flow_type}` | `src/api/routes/webhooks.py` | DynamicWorkflow execution via webhook |
| POST `/approvals/{task_id}` | `src/api/routes/approvals.py` | HITL resume cycle |
| POST `/api/bundles/import` | `src/api/routes/bundles.py` | Bundle import → workflow registration |

### 3.2 Flujo de datos E2E

```
E3.1 "Degraded MCP":
  input_data → DynamicWorkflow.execute()
    → validate_input() → True
    → create_task_record() → mock
    → _run_crew()
      → BaseCrew.run_async()
        → AgentFactory.resolve_tools(async_mode=True)
          → MCPPool.get_tools() → 1 tool ok, 1 falla (mock)
            → tools list con 1 elemento
        → crew.kickoff_async() → mock result
      → results["step_1"] = {"result": "..."}
      → persist_state() → mock
      → emit_event() → mock
    → return state (COMPLETED)

E3.2 "Approval Gate HITL":
  input_data → DynamicWorkflow.execute()
    → _run_crew()
      → BaseCrew.run_async() → mock result "100000"
      → _check_approval_rule("monto > 50000", results) → True
      → request_approval() → state = AWAITING_APPROVAL
      → return results (flow pausa)
    → state.status = AWAITING_APPROVAL
  → flow.resume(task_id, "approved", "supervisor")
    → _on_approved() → state = COMPLETED
    → emit_event("flow.completed")

E3.3 "Multi-step handover":
  input_data → DynamicWorkflow.execute()
    → _run_crew()
      → step_1: BaseCrew(role="analyst").run_async() → "Result A"
        → results["step_1"] = {"result": "Result A"}
      → step_2: BaseCrew(role="processor").run_async(
          inputs={"previous_results": {"step_1": {"result": "Result A"}}}
        ) → "Result B"
        → results["step_2"] = {"result": "Result B"}
      → step_3: BaseCrew(role="reviewer").run_async(
          inputs={"previous_results": {"step_1": ..., "step_2": ...}}
        ) → "Result C"
        → results["step_3"] = {"result": "Result C"}
    → return results (COMPLETED)
```

### 3.3 Contratos entre servicios

| Contrato | Input esperado | Output esperado |
|---|---|---|
| `BaseCrew.run_async()` | `task_description`, `inputs` (con `previous_results`) | `CrewOutput` con `.raw` attribute |
| `MCPPool.get_tools()` | `org_id`, `server_name` | `list[tool]` o `MCPConnectionError` |
| `DynamicWorkflow._check_approval_rule()` | `rule`, `results` | `bool` |
| `BaseFlow.request_approval()` | `description`, `payload` | `None` (state → AWAITING_APPROVAL) |
| `BaseFlow.resume()` | `task_id`, `decision`, `decided_by` | `None` (state → COMPLETED o FAILED) |

### 3.4 Error handling

| Escenario | Qué ve el cliente |
|---|---|
| MCP tool falla en E3.1 | Warning en log, lista de tools con 1 elemento, sin crash |
| Approval no aprobado en E3.2 | State = FAILED, error = "Rejected by supervisor: {decided_by}" |
| Step sin agent_role | Warning en log, step omitido, flow continúa |
| CrewConfigError (agent no encontrado) | `CrewConfigError` propagada, state → FAILED |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### 4.1 Flujo completo DB → Backend → Frontend → UX

Paso 3 es puramente backend testing con mocks. No hay componente frontend directo. Sin embargo, los flujos E2E validados son la base para:

- **UX de webhooks:** El usuario envía un webhook → flow ejecuta → resultado persiste → frontend consulta estado.
- **UX de aprobación:** Flow pausa → supervisor ve pending approval en UI → decide → flow continúa.
- **UX de multi-step:** Usuario ve progreso step-by-step en dashboard.

### 4.2 Coherencia con arquitectura existente

✅ **Plan es realizable con arquitectura actual.** Los 3 tests E2E propuestos ejercen caminos ya implementados:
- `DynamicWorkflow._run_crew()` soporta steps, approval_rules, previous_results
- `BaseFlow.request_approval()` y `resume()` implementan HITL completo
- `AgentFactory.resolve_tools()` soporta MCP tools con async_mode

✅ **Decisiones de data/code/backend apoyan al MVP.** Los fixtures de `conftest.py` están diseñados para este tipo de tests E2E mockeados.

### 4.3 Gaps y fricción

| Gap | Descripción | Impacto |
|---|---|---|
| `approval_threshold` no usado | StepDefinition tiene el campo pero `_run_crew()` no lo lee | Bajo — documentado como deuda técnica |
| `resume()` no continúa steps | `_on_approved()` marca COMPLETED, no reanuda ejecución | Medio — el ciclo HITL E2E debe reflejar esto |
| Solapamiento con integration tests | `test_handover_real.py` ya cubre 2-step handover | Bajo — E2E agrega 3-step + contexto E2E completo |

### 4.4 DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: `fap test-e2e`
- **Qué automatiza:** Ejecutar solo los 3 tests E2E del Paso 3 con un comando, sin correr toda la suite. Reduce tiempo de feedback de ~45s (suite completa) a ~5s (solo E2E Paso 3).
- **Tipo:** Comando CLI (Typer)
- **Cómo se usa:** `fap test-e2e 3` o `fap test-e2e --step 3 --cov`
- **Impacto para el usuario final:** El desarrollador no necesita recordar el path exacto del archivo de tests ni los flags de pytest. Un comando simple ejecuta los tests E2E del paso con cobertura opcional.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

**Implementación propuesta:** Extender `src/cli/commands/test_step.py` (ya existente para `fap test-step`) para soportar un subcomando `test-e2e` que ejecute `pytest tests/e2e/test_production_flows.py -v` con cobertura opcional.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No hay impacto en schema — tests 100% mockeados
✅ [CODE] `tests/e2e/test_production_flows.py` existe con 3 tests (E3.1, E3.2, E3.3)
✅ [CODE] Cada test usa fixtures de `conftest.py` (global_llm_mock, mock_service_client, mock_tenant_client)
✅ [BACKEND] E3.1: Workflow con MCP degradado completa sin crash, loguea warning
✅ [BACKEND] E3.2: Ciclo HITL completo — PENDING → AWAITING_APPROVAL → COMPLETED
✅ [BACKEND] E3.3: 3 steps con contexto preservado — previous_results contiene step_1 y step_2 en step_3
✅ [FULLSTACK] Cada test E2E <5s de ejecución (todo mockeado)
✅ [FULLSTACK] 100% pass — 3/3 tests pasan
✅ [DX] Herramienta `fap test-e2e 3` ejecuta sin errores y reduce paso manual de ejecutar tests E2E
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `global_llm_mock` autouse interfiere con mocks específicos de BaseCrew | Media | `global_llm_mock` mockea `crewai.Crew` a nivel de import, pero algunos tests necesitan verificar call_args de BaseCrew | Usar `patch("src.flows.dynamic_flow.BaseCrew")` que override el mock global dentro del contexto del test |
| `MCPPool` singleton contamina tests E2E | Alta | MCPPool es singleton; si un test no llama `reset()`, el siguiente hereda estado | Fixture autouse con `MCPPool.reset()` antes y después de cada test (patrón ya usado en `test_mcp_resilience.py`) |
| `request_approval()` requiere RPC mock complejo | Media | `request_approval()` llama `svc.rpc("next_event_sequence", ...)` y `EventStore.append_sync()` | Mockear `svc.rpc` y `EventStore.append_sync` por separado; usar `mock_service_client` + `patch("src.events.store.EventStore.append_sync")` |
| `resume()` no continúa steps automáticamente | Media | `_on_approved()` marca COMPLETED, no reanuda `_run_crew()` | El test E3.2 debe verificar que el flow se pausa, se aprueba, y se marca COMPLETED — no que continúa ejecutando steps restantes. Documentar comportamiento esperado. |
| Solapamiento con tests existentes | Baja | `test_handover_real.py` ya cubre 2-step handover | E3.3 usa 3 steps (no 2) y verifica contexto a 3 niveles — diferenciación clara |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Comando `fap test-e2e` | FULLSTACK/DX | Baja | 1h | Ninguna | → verificar: `fap test-e2e 3` ejecuta `pytest tests/e2e/test_production_flows.py -v` sin errores |
| 1 | Fixture autouse `reset_mcp_pool` para tests E2E | CODE | Baja | 0.5h | Ninguna | → verificar: `MCPPool._instance is None` antes y después de cada test E3.1 |
| 2 | Test E3.1 "Degraded MCP" | BACKEND/FULLSTACK | Media | 2h | Tarea 1 | → verificar: test pasa, lista de tools contiene 1 elemento, warning en log, sin crash con `pytest tests/e2e/test_production_flows.py::test_degraded_mcp -v` |
| 3 | Test E3.2 "Approval Gate HITL" | BACKEND/FULLSTACK | Alta | 3h | Tarea 1 | → verificar: state transiciona PENDING → AWAITING_APPROVAL → COMPLETED, `request_approval` llamado 1 vez, `resume` con "approved" completa con `pytest tests/e2e/test_production_flows.py::test_approval_gate_hitl -v` |
| 4 | Test E3.3 "Multi-step handover" | BACKEND/FULLSTACK | Media | 2h | Tarea 1 | → verificar: `previous_results` en step_3 contiene keys "step_1" y "step_2" con resultados reales con `pytest tests/e2e/test_production_flows.py::test_multi_step_handover -v` |
| 5 | Validar flujo E2E completo (3 tests juntos) | FULLSTACK | Baja | 1h | Tareas 2-4 | → verificar: `pytest tests/e2e/test_production_flows.py -v` pasa 3/3 tests en <15s total |
| 6 | Verificar no solapamiento con tests existentes | CODE | Baja | 0.5h | Ninguna | → verificar: `pytest tests/e2e/ tests/integration/ --co` muestra tests únicos, sin duplicación de cobertura |

**Tiempo total estimado:** 10 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Fix `approval_threshold` usage:** Modificar `_run_crew()` para leer `step.get("approval_threshold")` como fallback si no hay `approval_rules`. Esto cerraría la deuda técnica documentada en phase-state.md.
- **`resume()` con continuación de steps:** Implementar lógica para que `resume()` reanude `_run_crew()` desde el step donde se pausó, en vez de marcar COMPLETED inmediatamente. Requeriría persistir `current_step_index` en el state.
- **E2E con API real:** Tests E2E que usen `TestClient` contra `src/api/main.py` para ejercer el flujo completo HTTP → webhook → flow execution → response. Actualmente los tests E2E son a nivel de clase, no de API.
- **Performance benchmark E2E:** Medir latencia de cada paso del workflow E2E con `time.perf_counter` para establecer baseline de performance.

---

## 📊 Métrica de Calidad (auto-evaluación)

| Métrica | Resultado |
|---|---|
| `proyecto-config.json` leído antes de explorar | ✅ |
| Elementos verificados (§0) | ✅ 28 elementos (umbral: 18+ para 6-10 archivos) |
| Discrepancias detectadas | ✅ 3 (solapamiento archivos, approval_threshold, >= fix ya aplicado) |
| Secciones completadas | ✅ 8 secciones (0-7) |
| Etapas cubiertas | ✅ 4 etapas (data, code, backend, fullstack+DX) |
| Criterios de aceptación | ✅ 9 criterios, todos verificables |
| Riesgos identificados | ✅ 5 riesgos (técnico, integración, futuro) |
| Tareas en el plan | ✅ 7 tareas, atómicas, ordenadas |
| Verificación inline por tarea (§7) | ✅ 100% — toda tarea tiene su `→ verificar:` |
| Suposiciones no verificadas | ✅ 0 |
| Propuesta DX / Tooling | ✅ `fap test-e2e` con descripción de impacto |
| Estimación de tiempo | ✅ Por tarea y total (10h) |
