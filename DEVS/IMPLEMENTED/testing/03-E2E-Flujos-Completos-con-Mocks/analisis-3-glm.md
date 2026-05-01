# 🧠 Análisis Técnico — Paso 3: E2E — Flujos Completos con Mocks

> **Agente:** glm
> **Paso:** 3 (Plan v3.1 §3)
> **Fecha:** 2026-05-01
> **Referencia:** `DEVS/plan.md` Paso 3, `DEVS/phase-state.md`

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `DynamicWorkflow` existe | Read `src/flows/dynamic_flow.py` | ✅ VERIFICADO | `dynamic_flow.py:27` — clase con `_run_crew()`, `_check_approval_rule()` |
| 2 | `BaseFlow` existe | Read `src/flows/base_flow.py` | ✅ VERIFICADO | `base_flow.py:61` — clase abstracta con `execute()`, `request_approval()`, `resume()` |
| 3 | `BaseFlowState` / `FlowStatus` | Read `src/flows/state.py` | ✅ VERIFICADO | `state.py:19-28` — Enum `FlowStatus` con PENDING→RUNNING→AWAITING_APPROVAL→COMPLETED/FAILED |
| 4 | `MCPPool` con circuit breaker | Read `src/tools/mcp_pool.py` | ✅ VERIFICADO | `mcp_pool.py:35-213` — singleton, `_is_circuit_open()`, `get_tools()` async |
| 5 | `AgentFactory.resolve_tools()` | Read `src/crews/factory.py` | ✅ VERIFICADO | `factory.py:28-78` — método estático, `async_mode=False` skip MCP |
| 6 | `AgentFactory.create_agent_async()` | Read `src/crews/factory.py` | ✅ VERIFICADO | `factory.py:162-183` — crea Agent con `resolve_tools(async_mode=True)` |
| 7 | `BaseCrew.run_async()` | Read `src/crews/base_crew.py` | ✅ VERIFICADO | `base_crew.py:169-205` — `await crew.kickoff_async()` |
| 8 | `conftest.py` fixtures | Read `tests/conftest.py` | ✅ VERIFICADO | `conftest.py:1-353` — `mock_service_client`, `mock_tenant_client`, `mock_event_store`, `global_llm_mock`, `mock_mcp_pool` |
| 9 | `FlowRegistry` existe | Read `src/flows/registry.py` | ✅ VERIFICADO | `registry.py:32-367` — `_flows` dict, `get()`, `register()` |
| 10 | `EventStore` existe | Read `src/events/store.py` | ✅ VERIFICADO | `store.py:56-226` — `append()`, `flush()`, `append_sync()` |
| 11 | `test_dynamic_flow.py` existe | Read `tests/integration/test_dynamic_flow.py` | ✅ VERIFICADO | 421 líneas — test registro, ejecución secuencial, approval, persist_state, skip sin role |
| 12 | `test_handover_real.py` existe | Read `tests/integration/test_handover_real.py` | ✅ VERIFICADO | 187 líneas — I3.1-I3.3 handover, empty steps, partial failure |
| 13 | `test_hitl_pause_resume.py` existe | Read `tests/integration/test_hitl_pause_resume.py` | ✅ VERIFICADO | 283 líneas — request_approval, resume approved/rejected |
| 14 | `WorkflowDefinition` Pydantic model | Read `src/flows/workflow_definition.py` | ✅ VERIFICADO | `workflow_definition.py:57-123` — `StepDefinition`, `ApprovalRule`, validadores |
| 15 | `_check_approval_rule` soporta >=, <=, == | Read `src/flows/dynamic_flow.py:128-185` | ✅ VERIFICADO | Operadores compuestos priorizados correctamente (>= antes de >) |
| 16 | `test_mvp_certification.py` existe | Read `tests/e2e/test_mvp_certification.py` | ✅ VERIFICADO | E2E certification suite con TestClient FastAPI |
| 17 | `approvals.py` route existe | Read `src/api/routes/approvals.py` | ✅ VERIFICADO | `approvals.py:1-182` — POST `/approvals/{task_id}`, GET list |
| 18 | `test_mcp_resilience.py` existe | Read `tests/integration/test_mcp_resilience.py` | ✅ VERIFICADO (existe) | Paso 2 ya implementó integración MCP resilience |

**Discrepancias encontradas:**

1. ⚠️ **Plan dice "3 flujos E2E" en archivo nuevo `test_production_flows.py`** — Archivo NO existe aún. Verificado: `tests/e2e/` no contiene `test_production_flows.py`. Confirma que es **creación nueva**.
2. ⚠️ **Plan E3.1 menciona `resolve_tools` con MCP pool** — El test necesitará mockear `AgentFactory._resolve_mcp_tool` o `MCPPool.get_tools` directamente. `resolve_tools()` en `factory.py:28-78` llama `_resolve_mcp_tool` que importa `MCPPool` lazy. Mockear MCPPool es el camino correcto.
3. ⚠️ **Plan E3.2 menciona estados PENDING → AWAITING_APPROVAL → COMPLETED** — `FlowStatus` enum confirma estos estados en `state.py:20-28`. Pero el flujo real es: PENDING → (execute→) RUNNING → AWAITING_APPROVAL → (resume→) COMPLETED. El test debe verificar esta transición completa.
4. ✅ **Bug >= / <= / == FIXED** — `dynamic_flow.py:128-185` ahora parsea correctamente operadores compuestos. No aplica como bug conocido; fue fixeado.
5. ⚠️ **`flows/registry.py:253-335` `_load_from_db`** usa `SecurityGuard(is_system=True)` para flujos Python. En test E3.3 no se prueba este path, pero es relevante si flujos dinámicos cargan desde DB.
6. ⚠️ **`BaseCrew.run_async()` llama `AgentFactory.create_agent_async()`** que requiere `get_settings().get_llm()`. El mock `global_llm_mock` parchea `crewai.Agent` pero NO parchea `get_settings()`. Los tests E2E necesitarán mockear `get_settings` o `AgentFactory.create_agent_async`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas (directa o indirectamente)

| Tabla | Operación | Contexto |
|---|---|---|
| `tasks` | INSERT (create_task_record), UPDATE (persist_state) | `base_flow.py:189-200`, `base_flow.py:227-253` |
| `snapshots` | UPSERT (persist_state, to_snapshot, to_snapshot_v2) | `base_flow.py:229-230`, `base_flow.py:292-303` |
| `pending_approvals` | INSERT (request_approval), SELECT/UPDATE (process_approval) | `base_flow.py:306-317`, `approvals.py:130-157` |
| `domain_events` | INSERT (flush, append_sync) | `store.py:127-143`, `store.py:183-213` |
| `workflow_templates` | SELECT (load_dynamic_flows_from_db, registry._load_from_db) | `dynamic_flow.py:197-205`, `registry.py:258-268` |
| `agent_catalog` | SELECT (BaseCrew._load_agent_config) | `base_crew.py:48-75` |
| `org_mcp_servers` | SELECT (MCPPool.get_tools) | `mcp_pool.py:122-132` |

### Schema y RLS

- Todas las operaciones usan `get_tenant_client(org_id)` que establece `app.org_id` para RLS → aislamiento tenant garantizado
- `pending_approvals` usa `org_id` para RLS → supervisor solo ve aprobaciones de su org
- Los tests E2E mockean `get_tenant_client` y `get_service_client` → RLS no se ejercita realmente, pero se verifica que se invoca con org_id correcto

### Índices necesarios

- Ya cubiertos por migraciones existentes (`009_fix_organizations_rls.sql`, `025_agent_catalog_rls_update.sql`)

### Tipos de datos

- `FlowStatus` es `str, Enum` con `use_enum_values=True` → serializa como string, compatible con DB `status` varchar
- `approval_payload` es `Optional[Dict[str, Any]]` → se almacena como JSONB en DB
- Sin problemas de tipo identificados para Paso 3

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases nuevas (en test file)

| Componente | Firma | Responsabilidad |
|---|---|---|
| `test_degraded_mcp` | `async def test_degraded_mcp(...)` | E3.1: Flow con MCP degradado (1 tool de 2 falla) |
| `test_approval_gate_hitl` | `async def test_approval_gate_hitl(...)` | E3.2: Ciclo HITL completo PENDING→AWAITING_APPROVAL→COMPLETED |
| `test_multi_step_handover` | `async def test_multi_step_handover(...)` | E3.3: 3 steps, cada uno consume previous_results |

### Patrones existentes a seguir

| Patrón | Archivo referencia | Uso en Paso 3 |
|---|---|---|
| Mock de `BaseCrew` con `side_effect` por role | `test_handover_real.py:92-101` | E3.1, E3.3 — mismo patrón para mockear múltiples crews |
| `DynamicWorkflow(org_id=...)` + `_template_definition` + `_flow_type` | `test_dynamic_flow.py:151-153` | E3.1, E3.2, E3.3 — instanciación directa sin DB |
| `flow.state = MagicMock()` + `flow.persist_state = AsyncMock()` | `test_dynamic_flow.py:154-155` | Todos — inicialización de estado mockeado |
| `flow.request_approval` mock con `AsyncMock` | `test_dynamic_flow.py:352-353` | E3.2 — HITL pause/resume |
| `BaseFlowState(correlation_id=..., task_id=..., org_id=..., flow_type=..., input_data=...)` | `test_hitl_pause_resume.py:39-44` | E3.2 — creación de estado real (no MagicMock) para HITL |
| `mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=1)` | `test_hitl_pause_resume.py:47` | E3.2 — mock de `next_event_sequence` RPC |
| `mock_mcp_pool` fixture | `conftest.py:304-316` | E3.1 — mock del pool MCP |

### Modularidad

- Tests E2E se ubicarán en `tests/e2e/test_production_flows.py` — nuevo archivo
- Usan fixtures existentes de `conftest.py` — sin necesidad de fixtures nuevas
- Tests son independientes entre sí — se pueden ejecutar en paralelo

### Imports necesarios

```python
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.flows.dynamic_flow import DynamicWorkflow
from src.flows.base_flow import BaseFlow
from src.flows.state import BaseFlowState, FlowStatus
from src.flows.registry import flow_registry
from src.crews.base_crew import BaseCrew
from src.tools.mcp_pool import MCPConnectionError
```

### Complejidad ciclomática

- E3.1 (Degraded MCP): Media — requiere mockear `AgentFactory.resolve_tools` o `MCPPool.get_tools` para simular fallo parcial + `BaseCrew` para ejecución
- E3.2 (HITL): Alta — requiere ciclo completo: execute → request_approval → resume. Necesita mockear: `create_task_record`, `persist_state`, `emit_event`, `request_approval` parcialmente, `resume`
- E3.3 (Multi-step handover): Media — 3 mocks de `BaseCrew` con `side_effect`, verificar `previous_results` en call args

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs/endpoints tocados

| Endpoint | Método | Uso en Paso 3 | Mockeado? |
|---|---|---|---|
| `POST /api/bundles/import` | POST | No — fuera de scope de E2E flujos | N/A |
| `POST /approvals/{task_id}` | POST | E3.2 — resume de HITL vía API | Sí — test unitario de `flow.resume()`, no TestClient HTTP |
| `GET /approvals` | GET | No — listado de aprobaciones | N/A |

### Flujo E3.1 — Degraded MCP

```
1. Crear DynamicWorkflow con template que tiene 2 MCP tools
2. Mockear MCPPool.get_tools → 1 tool success, 1 tool falla con MCPConnectionError
3. Mockear BaseCrew.run_async → retorna resultado exitoso
4. Ejecutar flow.execute()
5. Verificar: flow completa con 1 tool disponible, sin crash
6. Verificar: logger.warning capturó el fallo del tool degradado
```

**Contrato:** `AgentFactory.resolve_tools()` con `async_mode=True` debe:
- Resolver tools del registry normalmente
- Para MCP tools: llamar `MCPPool.get_tools()` → si falla una, loguear error y continuar con las que funcionan
- **PROBLEMA:** `factory.py:68` — `except Exception as e: logger.error(...)` — solo loguea, NO añade la tool fallida. Pero el test E3.1 espera que el workflow use las tools disponibles. Verificar que el flujo no crashea.

### Flujo E3.2 — Approval Gate HITL

```
1. Crear DynamicWorkflow con approval_rules que matcheen
2. Mockear BaseCrew para retornar valor que dispara approval
3. Ejecutar flow.execute() → debería pausar en AWAITING_APPROVAL
4. Verificar: state.status == AWAITING_APPROVAL
5. Llamar flow.resume(task_id, decision="approved", decided_by="supervisor")
6. Verificar: state.status == COMPLETED
7. Verificar transición completa: PENDING → RUNNING → AWAITING_APPROVAL → COMPLETED
```

**Contrato:** `BaseFlow.execute()` → `request_approval()` → pausa → `resume()` → `_on_approved()` → `complete()`

**Nota crítica:** `execute()` en `base_flow.py:106` tiene decorador `@with_error_handling`. Si `request_approval()` lanza excepción (ej: `EventStoreError`), el estado se marca como FAILED. El test debe mockear `EventStore.append_sync` para que no falle.

### Flujo E3.3 — Multi-step Handover

```
1. Crear DynamicWorkflow con 3 steps (step_1, step_2, step_3)
2. Mockear BaseCrew con side_effect por role → outputs diferentes
3. Ejecutar flow._run_crew()
4. Verificar: step_3 recibió previous_results con step_1 y step_2
5. Verificar: results dict contiene los 3 outputs
```

**Contrato:** `DynamicWorkflow._run_crew()` pasa `previous_results` en `inputs` a cada `crew.run_async()`. Línea `dynamic_flow.py:96-101`:

```python
result = await crew.run_async(
    task_description=description,
    inputs={
        "step_inputs": step.get("inputs", {}),
        "previous_results": results,
        "original_input": self.state.input_data,
    },
)
```

### Error handling

| Escenario | Código afectado | Comportamiento esperado |
|---|---|---|
| MCP pool completamente caído | `factory.py:67-68` | `logger.error` + skip, sin crash |
| `MCPPool.get_tools()` lanza `MCPConnectionError` | `mcp_pool.py:101-106` | Circuito abierto → `MCPConnectionError` |
| Approval sin snapshot | `base_flow.py:367` | `ValueError("No snapshot found")` |
| EventStore falla en `append_sync` | `store.py:222-225` | `EventStoreError` → flujo se detiene |
| Step sin agent_role | `dynamic_flow.py:83-84` | `logger.warning` + skip |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

```
[DB: workflow_templates] → load_dynamic_flows_from_db()
                              ↓
[DB: agent_catalog]  ←── BaseCrew._load_agent_config()
                              ↓
                    DynamicWorkflow._run_crew()
                              ↓
[DB: tasks] ← create_task_record()  ←  BaseFlow.execute()
                              ↓
              [BaseCrew.run_async() con resolve_tools()]
                              ↓
              [approval_rules check] → request_approval()
                              ↓
[DB: pending_approvals] ← INSERT
                              ↓
[DB: domain_events] ← EventStore.append_sync()
                              ↓
              [PAUSA — Espera decisión supervisor]
                              ↓
[API: POST /approvals/{task_id}] → flow.resume()
                              ↓
[DB: snapshots UPDATE] → state: COMPLETED
```

### Coherencia

- ✅ Schema soporta HITL: `pending_approvals`, `snapshots` con `aggregate_id`, `domain_events`
- ✅ `FlowStatus` enum cubre transiciones: PENDING → RUNNING → AWAITING_APPROVAL → COMPLETED/FAILED
- ✅ `BaseFlowState.from_snapshot()` reconstruye estado desde DB para resume
- ⚠️ **Gap:** `request_approval()` usa `get_service_client()` para RPC y `get_tenant_client()` para INSERT — mezcla service/tenant client. En tests se mockean ambos, pero en producción hay que asegurar consistencia.

### Alineación con arquitectura

- ✅ Los 3 tests E2E son factibles con mocking existente
- ✅ `conftest.py` provee todos los mocks necesarios
- ⚠️ **El test E3.2 requiere mockear `BaseFlow.create_task_record()`** o proporcionar un `flow.state` pre-inicializado — similar a `test_hitl_pause_resume.py`

### DX & Tooling (OBLIGATORIO)

### Herramienta Propuesta: `fap test-e2e`

- **Qué automatiza:** Ejecutar solo los tests E2E del paso actual con un solo comando, sin necesidad de recordar fixtures o métodos de mocking específicos
- **Tipo:** Comando CLI (extensión de `fap test-step`)
- **Cómo se usa:** `fap test-e2e 3` → ejecuta `pytest tests/e2e/test_production_flows.py -v --tb=short`
- **Impacto para el usuario final:** Deja de ejecutar manualmente `pytest` con rutas específicas. Un comando para validar todo el paso E2E.
- **Prioridad:** Tarea 0 — implementar antes que los tests

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `tasks` soporta estados PENDING, RUNNING, AWAITING_APPROVAL, COMPLETED, FAILED
✅ [DATA] Tabla `pending_approvals` INSERT y SELECT funcionan vía mock_tenant_client
✅ [DATA] Tabla `domain_events` soporta append_sync vía mock
✅ [CODE] Archivo `tests/e2e/test_production_flows.py` creado con 3 tests (E3.1, E3.2, E3.3)
✅ [CODE] Cada test usa fixtures de conftest.py — sin mocks ad-hoc duplicados
✅ [CODE] Tests siguen patrón de test_handover_real.py y test_hitl_pause_resume.py
✅ [BACKEND] E3.1: Flow con MCP degradado completa sin crash, loguea warning
✅ [BACKEND] E3.1: Lista de tools contiene solo las disponibles (sin las fallidas)
✅ [BACKEND] E3.2: Flow transiciona PENDING → RUNNING → AWAITING_APPROVAL → COMPLETED
✅ [BACKEND] E3.2: request_approval() called con description y payload correctos
✅ [BACKEND] E3.2: resume() con "approved" llama _on_approved() y marca COMPLETED
✅ [BACKEND] E3.3: Step 3 recibe previous_results con step_1 y step_2
✅ [BACKEND] E3.3: results dict contiene outputs de los 3 steps
✅ [FULLSTACK] Cada flujo E2E < 5s (todo mockeado)
✅ [FULLSTACK] 100% tests pasan: `pytest tests/e2e/test_production_flows.py -v`
✅ [DX] `fap test-step 3` (o `fap test-e2e 3`) ejecuta los 3 tests sin errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| E3.2 HITL ciclo completo mockea demasiado | Alta | `create_task_record` + `persist_state` + `emit_event` + `request_approval` + `resume` → 5+ mocks encadenados | Seguir patrón `test_hitl_pause_resume.py`: mockear solo DB, dejar lógica real. Inicializar `flow.state` manualmente para evitar `create_task_record` |
| `AgentFactory.resolve_tools` en E3.1 | Media | `resolve_tools` con `async_mode=True` importa `_resolve_mcp_tool` lazy → mockear `MCPPool.get()` + `MCPPool.get_tools` directamente | Usar `patch("src.crews.factory.MCPPool")` o mockear `AgentFactory._resolve_mcp_tool` directamente |
| `global_llm_mock` parchea `crewai.Agent` pero no `AgentFactory.create_agent_async` | Media | `create_agent_async` llama `get_settings().get_llm()` internamente | En E2E, mockear `BaseCrew` directamente (como en tests existentes), no `AgentFactory` |
| Test no determinista por `asyncio` timing | Baja | Tests async con `await` pueden tener timing sutil | Todos los mocks son síncronos/AsyncMock → deterministas |
| Incompatibilidad con tests existentes en `test_dynamic_flow.py` | Baja | Nuevos tests E3.1/E3.3 pueden duplicar cobertura de tests I2.x/I3.x | Tests E2E son de flujo COMPLETO (execute → result), los de integración testean componentes aislados. No hay duplicación |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX**: Extender `fap test-step` para soportar paso E2E (o crear `fap test-e2e`) | FULLSTACK/DX | Baja | 30min | Ninguna | → verificar: `fap test-step 3` ejecuta `pytest tests/e2e/test_production_flows.py -v` |
| 1 | Crear `tests/e2e/test_production_flows.py` con estructura y fixtures | CODE | Baja | 20min | Ninguna | → verificar: archivo existe, `pytest --co tests/e2e/test_production_flows.py` muestra 3 tests |
| 2 | E3.1 — Degraded MCP: flow con 2 tools MCP, 1 falla | CODE/BACKEND | Media | 1h | Tarea 1 | → verificar: test pasa, flujo completa sin crash, warning en log |
| 3 | E3.2 — Approval Gate HITL: ciclo PENDING → AWAITING_APPROVAL → COMPLETED | CODE/BACKEND | Alta | 1.5h | Tarea 1 | → verificar: transición de estados completa, `request_approval` called, resume approved |
| 4 | E3.3 — Multi-step Handover: 3 steps con previous_results | CODE/BACKEND | Media | 1h | Tarea 1 | → verificar: step_3 recibe previous_results con step_1 y step_2 |
| 5 | Validación completa: `pytest tests/e2e/test_production_flows.py -v` | FULLSTACK | Baja | 15min | Tareas 2-4 | → verificar: 3/3 tests pasan, sin errores, cada test < 5s |
| 6 | Lint: `ruff check src/ tests/` → 0 errores | CODE | Baja | 10min | Tareas 1-4 | → verificar: `ruff check src/ tests/` retorna 0 errores |

**Tiempo total estimado:** 3.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Optimizar tests E2E para ejecutar con TestClient HTTP real (POST /approvals/{task_id}) — requiere levantar app FastAPI
- Añadir test E2E que valide flujo con `flow_registry.get()` cargando desde DB mockeada
- Considerar `pytest-asyncio` mode="auto" para simplificar marcadores
- Migrar `test_3_5_latency.py` a `tests/integration/` o `tests/stress/` como recomienda plan.md
- Añadir test E3.4: flujo con `DynamicWorkflow` registrado dinámicamente desde template de DB (cubre `_load_from_db` path)
- Validación de que `AgentFactory.create_agent_async` funciona correctamente con `get_settings().get_llm()` mockeado