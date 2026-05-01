# 🏛️ ANÁLISIS UNIFICADO — Paso 3: E2E — Flujos Completos con Mocks

**Fuente:** `DEVS/plan.md` Paso 3 (pág. 8-9)
**Proyecto:** `proyecto-config.json` — raíz `D:\Develop\Personal\FluxAgentPro-v2`
**Fecha:** 2026-05-01
**Agentes consolidados:** DS, GLM, KILO, QWEN
**Ruta backend:** `D:\Develop\Personal\FluxAgentPro-v2\src`
**Ruta tests e2e:** `D:\Develop\Personal\FluxAgentPro-v2\tests\e2e`
**Ruta archivo destino:** `D:\Develop\Personal\FluxAgentPro-v2\DEVS\IN_PROGRESS\analisis-FINAL.md`

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:-------|:---------------|:------------------------|:-------------|:-----------------|:------------|
| **DS** | ✅ 20 elementos | 4 (D1-D4) | ✅ `fap test-step 3` | ✅ Líneas exactas en 20/20 | **4.8** |
| **GLM** | ✅ 18 elementos | 6 (G1-G6) | ✅ `fap test-e2e` | ✅ Líneas exactas en 18/18 | **4.5** |
| **KILO** | ✅ 12 elementos | 1 (K1) | ✅ `fap test-step 3` | ⚠️ Grep-level, sin líneas específicas | **3.5** |
| **QWEN** | ✅ 28 elementos | 3 (Q1-Q3) | ✅ `fap test-e2e` | ✅ Líneas exactas en 28/28 + solapamiento | **4.7** |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|-------------|---------|-------------------------|------------|
| 1 | Plan omite estado `RUNNING` entre `PENDING` y `AWAITING_APPROVAL`. Plan: PENDING→AWAITING_APPROVAL→COMPLETED. Real: PENDING→RUNNING→AWAITING_APPROVAL→COMPLETED. | DS, GLM | ✅ `src/flows/state.py:20-28` | Test E3.2 verifica estado final tras `resume()`, no secuencia de transiciones. Documentar en criterios de aceptación que el ciclo real incluye RUNNING. |
| 2 | Plan dice E3.1 "warning in log" tras MCP fallo. Real: `factory.py:59` usa `logger.error`, no `logger.warning`. | DS | ✅ `src/crews/factory.py:59` | Criterio E3.1 ajustado a "logger.error fue llamado". No afecta implementación — test verifica log + skip. |
| 3 | `_on_approved()` por defecto NO continúa el workflow — llama `self.state.complete({"approval": "accepted"})` y termina. Plan asume que `resume()` reanuda ejecución de steps restantes. | DS, QWEN | ✅ `src/flows/base_flow.py:405-415` | E3.2 debe testear que tras `resume("approved")` el estado es COMPLETED con `{"approval": "accepted"}` — NO que steps continúan. Comportamiento documentado como feature request futuro. |
| 4 | Plan desactualizado: dice "tests/e2e/ tiene 6 escenarios". Real: 12 archivos .py. | QWEN | ✅ `tests/e2e/` ls | Los 3 tests E3.1-E3.3 ejercen combinaciones NO cubiertas por los 12 existentes. No hay duplicación. |
| 5 | Plan desactualizado: bug `>=`/`<=`/`==` marcado como "no implementados". Real: código actual soporta correctamente en `dynamic_flow.py:144-150`. | GLM, KILO, QWEN | ✅ `src/flows/dynamic_flow.py:144-150` | No requiere acción. El fix ya fue aplicado (post-plan v3.1). |
| 6 | `approval_threshold` en `StepDefinition` (`workflow_definition.py:47`) definido pero no usado en `_run_crew()`. | QWEN | ✅ `src/flows/workflow_definition.py:47`, `src/flows/dynamic_flow.py:66-126` | Deuda técnica documentada. Fuera de scope de Paso 3. |
| 7 | E3.3 casi duplicado de I3.1 (`test_handover_real.py`). I3.1: 2 steps. E3.3 necesita 3 steps. | DS, GLM, QWEN | ✅ `tests/integration/test_handover_real.py:69` | E3.3 válido: 3 steps demuestra profundidad de contexto que 2 steps no prueba. Diferencia real: 3 niveles vs 2. |

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo:** Crear `tests/e2e/test_production_flows.py` con 3 tests E2E mockeados (E3.1 Degraded MCP, E3.2 Approval Gate HITL, E3.3 Multi-step Handover) que verifican flujos completos sin LLM real, DB real ni MCP real.
- **Correcciones críticas al plan:**
  - Plan omite estado `RUNNING` en la transición HITL — documentado en criterios.
  - `_on_approved()` marca COMPLETED, no reanuda steps — E3.2 debe reflejar esto.
  - Bug `>=`/`<=`/`==` ya fixeado — plan desactualizado.
- **Decisión DX:** `fap test-step 3` (extender comando existente) sobre `fap test-e2e` (nuevo comando). Consistente con patrón `fap test-step 1` ya implementado.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Usuario invoca `fap test-step 3`
2. `pytest tests/e2e/test_production_flows.py -v` ejecuta 3 tests
3. **E3.1:** `AgentFactory.resolve_tools()` con 2 MCP tools → 1 tool ok, 1 falla → tools contiene 1 elemento, logger.error fue llamado, sin crash
4. **E3.2:** `DynamicWorkflow.execute()` con approval rule activada → estado `AWAITING_APPROVAL` → `resume(task_id, "approved")` → estado `COMPLETED` con `{"approval": "accepted"}`
5. **E3.3:** `DynamicWorkflow._run_crew()` con 3 steps (analyst→processor→reviewer) → cada step recibe `previous_results` acumulados → results final contiene 3 keys
6. `fap test-step 3` reporta 3/3 pass en <15s total

### Edge Cases MVP

- MCP pool con fallo parcial (1 tool funciona, 1 no) — no crash, tools disponibles se usan
- Approval rule activada sin snapshot en DB — mock snapshot retorna data válida
- 3 steps handover con contexto preservado — validación de `previous_results` en step_3
- `MCPPool` singleton no contamina tests adyacentes — fixture `MCPPool.reset()` autouse
- `global_llm_mock` autouse no interfiere con mocks específicos de `BaseCrew` — parchear con `patch("src.flows.dynamic_flow.BaseCrew")`

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### Archivo nuevo: `tests/e2e/test_production_flows.py`

| Propiedad | Valor |
|-----------|-------|
| **Ruta real** | `D:\Develop\Personal\FluxAgentPro-v2\tests\e2e\test_production_flows.py` |
| **Tipo de cambio** | Creación |
| **Líneas est.** | ~200-250 |
| **Descripción** | 3 tests E2E mockeados: Degraded MCP, Approval Gate HITL, Multi-step Handover |

**Estructura:**

```
tests/e2e/test_production_flows.py
├── Imports (pytest, AsyncMock, MagicMock, patch, DynamicWorkflow, AgentFactory, FlowStatus, BaseCrew, MCPPool, MCPConnectionError)
├── Fixtures
│   ├── reset_mcp_pool (autouse) — MCPPool.reset() antes/después cada test
│   └── sample_org_id (de conftest.py)
├── TestE3_1DegradedMCP (class)
│   └── test_resolve_tools_partial_failure
├── TestE3_2ApprovalGateHITL (class)
│   ├── test_approval_flow_pending_to_awaiting
│   └── test_approval_flow_resume_completes
└── TestE3_3MultiStepHandover (class)
    └── test_three_step_context_preservation
```

**Interfaces clave:**

```python
# E3.1
async def test_resolve_tools_partial_failure(
    mock_service_client, mock_tenant_client, mock_event_store, sample_org_id
)

# E3.2
async def test_approval_flow_pending_to_awaiting(
    mock_service_client, mock_tenant_client, mock_event_store, sample_org_id
)
async def test_approval_flow_resume_completes(
    mock_service_client, mock_tenant_client, mock_event_store, sample_org_id
)

# E3.3
async def test_three_step_context_preservation(
    mock_service_client, mock_tenant_client, mock_event_store, sample_org_id
)
```

**Patrones a seguir:**

| Patrón | Fuente | Cómo aplica |
|--------|--------|-------------|
| `DynamicWorkflow(org_id=...)` + `_template_definition` manual | `tests/integration/test_dynamic_flow.py:73-77` | E3.2, E3.3 instanciación sin DB |
| `crew_side_effect` que retorna mock distinto por `role` | `tests/integration/test_handover_real.py:94` | E3.3 para 3 roles (analyst, processor, reviewer) |
| Mock inline con `AsyncMock(side_effect=...)` para MCP parcial | NO reusar `mock_mcp_pool` fixture | E3.1 — mock personalizado que retorna 1 tool y lanza Exception en 2do |
| `BaseFlowState(correlation_id=..., task_id=..., org_id=...)` | `tests/integration/test_hitl_pause_resume.py:39-44` | E3.2 estado pre-inicializado para resume |
| `flow.state.task_id = "test-id"` tras execute() y antes de resume() | DS Estrategia 2 | E3.2 evitar mock de `create_task_record` |
| `patch("src.flows.dynamic_flow.BaseCrew")` | `tests/integration/test_dynamic_flow.py:168` | E3.2, E3.3 — mockear crew sin interferencia de `global_llm_mock` |
| `MCPPool.reset()` autouse fixture | `tests/integration/test_mcp_resilience.py:36` | Tests E3.x — evitar contaminación singleton (QWEN riesgo) |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

**Decisión unificada:** Extender `fap test-step` (DS/KILO), no crear nuevo comando `fap test-e2e` (GLM/QWEN).

```
### Herramienta: fap test-step 3
- **Qué automatiza:** Ejecución de los 3 tests E2E del Paso 3 con un solo comando
- **Tipo:** CLI (extensión de comando existente fap test-step)
- **Ubicación:** D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\test_step.py
- **Cómo se usa:** `fap test-step 3` → corre `pytest tests/e2e/test_production_flows.py -v --tb=short`
- **Soporte cobertura:** `fap test-step 3 --cov` → añade `--cov=src --cov-report=term-missing`
- **Impacto para el usuario final:** No más escribir `pytest tests/e2e/test_production_flows.py -v --tb=short --no-header -q`. Un comando = validación completa Paso 3.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Mock inline para E3.1 vs mock_mcp_pool fixture:** No reusar `mock_mcp_pool` fixture (retorna 3 tools siempre). Crear `AsyncMock(side_effect=[tool_list, Exception("MCP error")])` inline para fallo parcial. Basado en análisis DS R2.
2. **Estrategia snapshot para E3.2:** Usar `flow.state.task_id = "test-id"` tras `execute()` (DS Estrategia 2). Evita mockear `create_task_record`. Mock de `snapshots` table en `mock_service_client` para que `resume()` encuentre snapshot válido. Basado en DS R1.
3. **MCPPool.reset() autouse:** Fixture obligatoria para evitar contaminación singleton entre tests. Basado en QWEN R2.
4. **patch("src.flows.dynamic_flow.BaseCrew") para E3.2/E3.3:** En vez de mock `global_llm_mock` que mockea crewai a nivel import. `patch` específico evita interferencia. Basado en QWEN R1, GLM G6.
5. **fap test-step 3 sobre fap test-e2e:** Consistente con patrón ya implementado en Paso 1. No requiere nuevo comando CLI. Documentación y dogfooding más simples.
6. **Correcciones al plan:**
   - ⚠️ El plan dice transición PENDING→AWAITING_APPROVAL→COMPLETED pero el código real usa PENDING→RUNNING→AWAITING_APPROVAL→COMPLETED. Se documenta estado RUNNING pero el test verifica solo estado final.
   - ⚠️ El plan dice "warning in log" para E3.1 pero el código real usa `logger.error`. Se implementa verificación de `logger.error`.
   - ⚠️ El plan dice "bug conocido: >=/<=/== no parseados" pero el código real ya los soporta (`dynamic_flow.py:144-150`). No requiere acción.
   - ⚠️ El plan asume `resume()` reanuda steps pero `_on_approved()` marca COMPLETED. E3.2 verifica COMPLETED, no continuación de steps.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Sin impacto en schema — tests 100% mockeados con fixtures de conftest.py
✅ [CODE] tests/e2e/test_production_flows.py existe con 3 clases de test (E3.1, E3.2, E3.3)
✅ [CODE] Cada test es @pytest.mark.asyncio y usa fixtures mock (mock_service_client, mock_tenant_client, mock_event_store)
✅ [CODE] Tests siguen patrones de test_handover_real.py y test_hitl_pause_resume.py
✅ [BACKEND] E3.1: resolve_tools con 2 MCP tools → 1 disponible, 1 falla → tools contiene 1 elemento, sin crash, logger.error fue llamado
✅ [BACKEND] E3.2: execute() con approval rule activada → state.status == AWAITING_APPROVAL
✅ [BACKEND] E3.2: resume(task_id, "approved") → state.status == COMPLETED con resultado {"approval": "accepted"}
✅ [BACKEND] E3.3: 3 steps ejecutados en orden, step_2 recibe previous_results con step_1, step_3 recibe previous_results con step_1 Y step_2
✅ [BACKEND] E3.3: results final contiene las 3 keys: step_1, step_2, step_3
✅ [FULLSTACK] Cada test completa en <5s (todo mockeado, sin IO real)
✅ [FULLSTACK] 100% pass: `pytest tests/e2e/test_production_flows.py -v` → 3/3 tests
✅ [DX] fap test-step 3 ejecuta los 3 tests y reporta pass/fail sin errores
```

**Funcionales:**
- [ ] E3.1: Workflow con MCP degradado sobrevive sin crash
- [ ] E3.2: Ciclo HITL completo: execute → pause → resume → complete
- [ ] E3.3: Contexto multi-step preservado a 3 niveles de profundidad

**Técnicos:**
- [ ] MCPPool.reset() fixture autouse activa antes/después de cada test
- [ ] Sin fugas de mocking entre tests (singleton MCPPool limpio)
- [ ] ruff check tests/e2e/test_production_flows.py → 0 errores

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|-------|------------|-------------|--------------|
| 0 | **DX & Tooling:** Extender `fap test-step` para Paso 3 | Media | 1h | Ninguna |
| 1 | Crear `tests/e2e/test_production_flows.py` scaffold: imports, clases base, fixtures | Baja | 0.5h | Tarea 0 |
| 2 | Implementar E3.1 — Test Degraded MCP (resolve_tools con fallo parcial) | Media | 1.5h | Tarea 1 |
| 3 | Implementar E3.2 — Test Approval Gate HITL (execute → AWAITING_APPROVAL → resume → COMPLETED) | Alta | 2h | Tarea 1 |
| 4 | Implementar E3.3 — Test Multi-step Handover (3 steps, previous_results acumulados) | Media | 1.5h | Tarea 1 |
| 5 | Validación completa: `pytest tests/e2e/test_production_flows.py -v` + lint | Baja | 0.5h | Tareas 2-4 |
| **TOTAL** | | | **7h** | |

### Notas de implementación por tarea:

**Tarea 0 (DX):** Editar `src/cli/commands/test_step.py`. Añadir mapping `{3: "tests/e2e/test_production_flows.py"}`. Consistente con `fap test-step 1`.

**Tarea 2 (E3.1):**
- No reusar `mock_mcp_pool` fixture. Crear mock inline: `AsyncMock(side_effect=[["tool_a"], Exception("MCP connection failed")])`
- Mockear `AgentFactory._resolve_mcp_tool` con `patch.object(AgentFactory, '_resolve_mcp_tool')` + `side_effect` que retorne tool para 1er llamado y lance Exception para 2do
- Verificar `logger.error` fue llamado con `assert` sobre mock de logger

**Tarea 3 (E3.2):**
- CRÍTICO: Mock de snapshot en `mock_service_client.table("snapshots").select(...).maybe_single().execute()` debe retornar `Mock(data={"aggregate_id": "test-task-id", "state_json": {...}})`
- Asignar `flow.state.task_id = "test-id"` MANUALMENTE tras execute() (DS Estrategia 2)
- Mockear `EventStore.append_sync` para evitar `EventStoreError` (GLM observación)
- Mockear `svc.rpc("next_event_sequence", ...)` para `request_approval()`
- Usar `BaseFlowState(...)` real (no MagicMock) para estado (patrón test_hitl_pause_resume.py)

**Tarea 4 (E3.3):**
- Reusar patrón `crew_side_effect` de `test_handover_real.py:94`
- Template con 3 roles: analyst → processor → reviewer
- Mock de `BaseCrew` con `side_effect` retorna outputs encadenados: "Output A" → "Output B" → "Output C"
- Verificar que en 3er llamado, `inputs["previous_results"]` contiene keys "step_1" y "step_2"

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| E3.2: No hay snapshot en DB → resume() falla con `ValueError: No snapshot found` | **Alta** | `BaseFlow.resume()` busca snapshot en tabla `snapshots`. Sin mock → `None` → crash. | Mockear `snapshots` table en `mock_service_client` para retornar snapshot válido. O usar `flow.state.task_id` manual + mock de `svc.table().select().execute()`. **DS R1 — critical.** |
| E3.1: `mock_mcp_pool` fixture retorna 3 tools siempre, no soporta fallo parcial | Media | Fixture existente no diseñado para degradación parcial. | Crear mock inline con `AsyncMock(side_effect=...)`. No reusar fixture. **DS R2.** |
| E3.2: Dependencia de `task_id` generado en `create_task_record` | Media | `execute()` llama `create_task_record()` que escribe en DB mockeada. `task_id` no disponible para resume(). | Asignar `flow.state.task_id = "test-id"` manualmente tras execute() y antes de resume(). **DS R3 — Estrategia 2 recomendada.** |
| `global_llm_mock` interfiere con mocks específicos de BaseCrew | Media | `autouse=True` parchea crewai a nivel import. Tests que necesitan verificar `call_args` de BaseCrew pueden tener conflicto. | Usar `patch("src.flows.dynamic_flow.BaseCrew")` que override el mock global dentro del contexto del test. **DS R5, QWEN R1.** |
| `MCPPool` singleton contamina tests E2E | **Alta** | Singleton global; test anterior deja estado en MCPPool → test siguiente hereda circuito abierto/fallos. | Fixture autouse con `MCPPool.reset()` antes y después de cada test. **QWEN R2.** |
| E3.3 duplicación con I3.1 (`test_handover_real.py`) | Baja | Mismo patrón de mocking, diferencia solo en cantidad de steps. | Aceptar duplicación menor. E3.3 = 3 steps (no 2) con contexto E2E completo. No worth refactor ahora. **DS R4.** |
| `request_approval()` requiere RPC mock complejo (`next_event_sequence`) | Media | `base_flow.py:306-317` llama `svc.rpc("next_event_sequence", ...)` + `EventStore.append_sync()`. Sin mock → fallo. | Mockear `svc.rpc` + `EventStore.append_sync` por separado. Usar `mock_service_client` + `patch("src.events.store.EventStore.append_sync")`. **QWEN R3.** |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|----|------|-------|-----------------|
| TP-1 | E3.1 Degraded MCP: `resolve_tools` con 2 MCP tools, 1 falla | `resolve_tools(["mcp:server:tool_a", "mcp:server:tool_b"], org_id, async_mode=True)` | Lista tools con 1 elemento, `logger.error` llamado 1 vez, sin excepción propagada |
| TP-2 | E3.2 Approval Gate HITL: ciclo completo `execute()` → `resume("approved")` | Template con approval rule `monto > 50000`, mock retorna "100000" | `state.status == AWAITING_APPROVAL` tras execute, `state.status == COMPLETED` con `{"approval": "accepted"}` tras resume |
| TP-3 | E3.3 Multi-step Handover: 3 steps con contexto acumulativo | Template 3 steps (analyst, processor, reviewer) con mocks encadenados | `step_3` recibe `previous_results` con keys `step_1` y `step_2`, results final contiene 3 keys |
| TP-4 | Aislamiento MCPPool singleton | Ejecutar E3.1 → E3.2 → E3.3 en secuencia | Cada test corre independiente, sin contaminación de estado MCPPool entre tests |

**Comando para ejecutar tests E2E:** `pytest tests/e2e/test_production_flows.py -v --tb=short`
**Comando para lint:** `ruff check tests/e2e/test_production_flows.py`
**Comando vía DX:** `fap test-step 3`

---

## 📊 Métrica de Calidad del FINAL

| Métrica | Estado |
|:--------|:-------|
| `proyecto-config.json` leído antes de generar | ✅ |
| Discrepancias consolidadas con resolución | ✅ 7/7 detectadas |
| Correcciones al plan documentadas | ✅ 4 encontradas |
| Propuesta DX incluida en §3 y Tarea 0 en §6 | ✅ `fap test-step 3` |
| Criterio DX en §5 | ✅ |
| Secciones completadas | ✅ 9 secciones (0-8) |
| Casos de testing | ✅ 4 casos concretos |
| Tiempo estimado por tarea | ✅ 100% |
