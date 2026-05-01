# Analisis Tecnico — Paso 2: Tests de Integracion de Flujos Criticos

> **Agente:** glm | **Paso:** 2 | **Fase:** testing (VI)
> **Fecha:** 2026-05-01
> **NO UNIFICAR** — Documento independiente.

---

## 0️⃣ Verificacion contra Codigo Fuente (OBLIGATORIA)

| # | Elemento | Verificacion | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | `_is_circuit_open()` en `mcp_pool.py` | Existe y coincide con plan | ✅ | `mcp_pool.py:60-66` — 4 fallos cerrado, 5+ abierto, 60s half-open |
| 2 | `_record_failure()` en `mcp_pool.py` | Existe y actualiza health dict | ✅ | `mcp_pool.py:68-70` — incrementa failures, set last_check |
| 3 | `_reset_circuit_breaker()` en `mcp_pool.py` | Existe, reset failures=0 | ✅ | `mcp_pool.py:72-73` |
| 4 | `MCPPool.get_tools()` en `mcp_pool.py` | Firma: `(org_id, server_name, timeout, max_retries)` | ✅ | `mcp_pool.py:77-83` |
| 5 | `MCPConnectionError` en `mcp_pool.py` | Clase existe | ✅ | `mcp_pool.py:31-32` |
| 6 | `_check_approval_rule()` en `dynamic_flow.py` | Existe — BUG: solo parsea `>` y `<` | ✅ | `dynamic_flow.py:128-159` — `>` y `<` con `split()`, no maneja `>=`, `<=`, `==` |
| 7 | Bug `>=`/`<=`/`==` confirmado en `_check_approval_rule` | `>=` se parsea como `>` + `=50000` → ValueError silencioso → False | ✅ | `dynamic_flow.py:137` — `">" in condition` matchea `>=` antes que se evalue correctamente. `split(">",1)` con `"monto >= 50000"` da `["monto ", "= 50000"]` → `float("= 50000")` → ValueError capturado en `except` → False silencioso |
| 8 | `DynamicWorkflow._run_crew()` pasa `previous_results` | Sí, paso de contexto entre steps | ✅ | `dynamic_flow.py:99` — `inputs={"previous_results": results, ...}` |
| 9 | `previous_results` en `_run_crew()` también recibe `original_input` | Sí, campo adicional | ✅ | `dynamic_flow.py:100` |
| 10 | Template con 0 steps → `_run_crew()` retorna `{}` vacío | Steps vacío retorna results={}| ✅ | `dynamic_flow.py:74` `steps = template.get("steps", [])` + `results: Dict[str, Any] = {}` → loop nunca ejecuta → retorna `{}` |
| 11 | `base_flow.py` tiene `request_approval()` y `resume()` | Métodos HITL existen | ✅ | `base_flow.py:267-403` |
| 12 | `State.await_approval()` existe | Método en BaseFlowState | ✅ | `state.py:106-108` |
| 13 | FlowStatus.AWAITING_APPROVAL existe | Enum value | ✅ | `state.py:24` |
| 14 | `conftest.py` fixtures necesarias | mock_service_client, mock_tenant_client, mock_event_store, global_llm_mock | ✅ | `conftest.py:112-136`, `conftest.py:174-213`, `conftest.py:219-231`, `conftest.py:274-300` |
| 15 | `mock_mcp_pool` fixture existe | Sí, AsyncMock | ✅ | `conftest.py:304-316` |
| 16 | Paso 1 tests unitarios existen | 4 archivos confirmados | ✅ | `tests/unit/test_mcp_pool_circuit.py`, `test_service_connector.py`, `test_approval_operators.py`, `test_sanitizer.py` |
| 17 | `test_dynamic_flow.py` tests integración existen | Sí, con tests de registration, execution, approval, DB loading | ✅ | `tests/integration/test_dynamic_flow.py` — 421 líneas |
| 18 | `StepDefinition.approval_threshold` no usado en `_run_crew()` | Confirmado — campo existe pero no se referencia | ✅ | `workflow_definition.py:47` define campo, `dynamic_flow.py:66-126` no lo usa, usa `approval_rules[].condition` |
| 19 | `get_service_client()` importado en `mcp_pool.py` | From `..db.session` | ✅ | `mcp_pool.py:25` |
| 20 | `get_service_client()` y `get_tenant_client()` importados en `base_flow.py` | From `..db.session` | ✅ | `base_flow.py:26` |
| 21 | `flow_registry._flows` es dict — registro sobrescribe sin error | Confirmado | ✅ | `registry.py:41` — `self._flows: Dict[str, Type] = {}` → `_flows[flow_type_lower] = RegisteredFlow` sobrescribe |
| 22 | `test_hitl_pause_resume.py` e `test_hitl_additional.py` existen en integration/ | HITL tests existentes | ✅ | `tests/integration/test_hitl_pause_resume.py`, `tests/integration/test_hitl_additional.py` |

**Discrepancias encontradas:**

1. ❌ **DISCREPANCIA: Bug `>=`/`<=`/`==` más grave de lo documentado.** El plan dice "se rompen silenciosamente". Verificación real: `"monto >= 50000"` → entra en `if ">" in condition` (True) → `split(">", 1)` = `["monto ", "= 50000"]` → `float("= 50000")` ValueError → capturado en `except (ValueError, TypeError)` → línea 158 `return False` silencioso. **No solo "no funciona" — evalúa como False cuando debería ser True.** Decisión requerida antes de implementar tests condicionales I4.1-I4.3.

2. ⚠️ **NO VERIFICABLE: Flujos HITL end-to-end.** `base_flow.py:request_approval()` usa `get_service_client()` + `get_tenant_client()` + `EventStore.append_sync()`. Tests I3.x necesitan mockar estos 3 puntos. El fixture `mock_event_store` mockea `get_tenant_client` pero **no** mockea `EventStore.append_sync()`. Se necesita patch adicional.

3. ⚠️ **NO VERIFICABLE: `MCPPool.get_tools()` usa `get_service_client()` Y `MCPServerAdapter` de `crewai_tools`.** Los tests I2.x necesitan mockar ambas importaciones. `conftest.py` no tiene fixture específico para mock de MCPServerAdapter.

4. ❌ **DISCREPANCIA: Plan I2.1 requiere 6º intento de `MCPPool.get_tools()` con circuit breaker abierto.** Pero `get_tools()` checkea `_is_circuit_open()` ANTES del retry decorator. Primer intento lanza `MCPConnectionError` inmediato — no entra al bloque `@retry`. Esto significa que el test I2.1 no necesita 6 intentos: con circuito abierto, el primer `get_tools()` lanza error sin intentar conexión. Confirmar.

---

## 1️⃣ Analisis de Datos (ETAPA 1)

### Schema: Tablas involucradas

**Tablas directamente tocadas por Paso 2:**

| Tabla | Uso en tests | Tipo de acceso |
|-------|-------------|----------------|
| `org_mcp_servers` | I2.x — MCPPool lee config del server | SELECT (mock) |
| `workflow_templates` | I3.x — DynamicWorkflow carga definiciones | SELECT (mock) |
| `tasks` | I3.x — BaseFlow.create_task_record() | INSERT/UPDATE (mock) |
| `snapshots` | I3.x — BaseFlow.persist_state() | UPSERT (mock) |
| `pending_approvals` | I3.x HITL — BaseFlow.request_approval() | INSERT (mock) |
| `domain_events` | ServiceConnector audit, flow events | INSERT (mock) |
| `agent_catalog` | BaseCrew._load_agent_config() | SELECT (mock) |
| `service_tools` | I2.x no directo, pero ServiceConnector los lee | SELECT (mock) |
| `org_service_integrations` | ServiceConnector verifica activación | SELECT (mock) |

**No hay cambios de schema en Paso 2.** Todos los tests son de integración con mocks — no requieren migraciones nuevas.

### Integridad referencial

- `workflow_templates.org_id → organizations.id` — FK vigente (migración 006)
- `org_mcp_servers.org_id → organizations.id` — FK vigente (migración 005)
- Tests usan `mock_service_client`/`mock_tenant_client` — sin DB real

### RLS policies

- `workflow_templates`: `tenant_isolation` por `org_id::text = current_setting('app.org_id', TRUE)`
- `org_mcp_servers`: `tenant_isolation_org_mcp_servers` por `current_org_id()`
- Tests de integración no necesitan validar RLS (son con mock) — pero documentar que I3.x HITL usa `get_tenant_client()` que activa RLS en producción.

---

## 2️⃣ Analisis de Codigo (ETAPA 2)

### Funciones/Clases nuevas: Test files

| Archivo | Propósito | Patrón |
|---------|-----------|---------|
| `tests/integration/test_mcp_resilience.py` | I2.1-I2.3: Circuit breaker integración | `unittest.mock.patch` + `pytest.mark.asyncio` |
| `tests/integration/test_handover_real.py` | I3.1-I3.3: DynamicWorkflow contexto y edge cases | `mock_service_client` + `global_llm_mock` + `patch("BaseCrew")` |
| Posible fix: `src/flows/dynamic_flow.py` | Si se decide implementar `>=`, `<=`, `==` | Parser modificado en `_check_approval_rule` |

### Patrones: siguen los existentes

- **MCPPool tests** → Patrón de `test_mcp_pool_circuit.py`: `MCPPool.reset()` fixture autouse, `patch("time.time")`, `_make_pool_with_state()` helper
- **DynamicWorkflow tests** → Patrón de `test_dynamic_flow.py`: `mock_service_client`, `mock_tenant_client`, `mock_event_store`, `patch("BaseCrew")`, instanciar `DynamicWorkflow(org_id=...)` directo
- **ServiceConnector tests** → Patrón de `test_service_connector.py`: `mock_service_client` + `patch("httpx.Client")` + `patch("src.tools.service_connector.get_secret")`

### Modularidad

- `test_mcp_resilience.py` → Inyecta estado de health para circuit breaker, luego ejecuta `get_tools()` real. Cohesión alta.
- `test_handover_real.py` → Instancia DynamicWorkflow con template, mockea BaseCrew. Cohesión alta.
- **Decisión I4.x**: Si se implementa fix de `>=`/`<=`/`==`, tests condicionales van en `test_handover_real.py` o archivo separado. Recomendación: `test_approval_operators.py` expandir con I4.1-I4.3 por cohesión temática.

### Calidad: Complejidad de mocking

**I2.x MCP Resilience — Mocking requerido:**
- `patch("src.tools.mcp_pool.get_service_client")` → para config de server
- `patch("src.tools.mcp_pool.get_secret_async")` → para Vault
- `patch("crewai_tools.MCPServerAdapter")` + `patch("mcp.StdioServerParameters")` → para conexión MCP
- `patch("time.time")` → para control de temporización

⚠️ **Riesgo:** Importaciones dentro de función (`from crewai_tools import MCPServerAdapter` en `mcp_pool.py:149-154`). Hay que mockar antes del import, o el `try/except ImportError` podría interferir. Estrategia: mockar en `src.tools.mcp_pool` namespace.

**I3.x Handover — Mocking requerido:**
- `mock_service_client` (conftest fixture)
- `mock_tenant_client` (conftest fixture)
- `mock_event_store` (conftest fixture)
- `patch("src.flows.dynamic_flow.BaseCrew")` → para crew runs
- HITL: `patch("src.flows.base_flow.EventStore.append_sync")` → para HITL pause/resume
- `patch("src.flows.base_flow.get_service_client")` → para snapshots HITL
- `patch("src.flows.base_flow.get_tenant_client")` → para pending_approvals

### Imports y dependencias

- `mcp_pool.py` importa `get_service_client` de `..db.session` y `get_secret_async` de `..db.vault`
- `dynamic_flow.py` importa `BaseCrew` de `..crews.base_crew`, `BaseFlow` de `.base_flow`, `flow_registry` de `.registry`
- `base_flow.py` importa `get_service_client`, `get_tenant_client`, `execute_with_retry` de `..db.session`

---

## 3️⃣ Analisis de Backend (ETAPA 3)

### APIs/Endpoints: No hay endpoints nuevos en Paso 2

Paso 2 es **testing puro** — no agrega endpoints. Los tests verifican componentes internos:
- `MCPPool.get_tools()` — método de instancia async
- `DynamicWorkflow._run_crew()` — método de instancia async
- `DynamicWorkflow._check_approval_rule()` — método de instancia síncrono
- `BaseFlow.request_approval()` — método async
- `BaseFlow.resume()` — método async

### Middleware aplicable

- `require_org_id()` — dependency injection en routes FastAPI (no usado directo en tests)
- `verify_supabase_jwt()` — no mockeado en tests de integración (flujo level, no HTTP level)

### Flujos de datos

**I2.x MCP Resilience:**
```
1. MCPPool.get_tools(org_id, server_name)
2. → _is_circuit_open(key) check
3. → Si abierto: raise MCPConnectionError (sin intentar conexión)
4. → Si cerrado: _connect() con retry (tenacity)
5.   → get_service_client().table("org_mcp_servers").select()...
6.   → get_secret_async() para Vault
7.   → MCPServerAdapter(params).__enter__() en thread pool
8.   → Éxito: _reset_circuit_breaker(); return tools
9.   → Fallo: _record_failure(); propagate o retry
```

**I3.x DynamicWorkflow Handover:**
```
1. DynamicWorkflow(org_id)._run_crew()
2. → Por cada step en template:
3.   → BaseCrew(org_id, role=step.agent_role)
4.   → crew.run_async(description, inputs={previous_results, original_input})
5.   → results[step_id] = {"result": str(result.raw)}
6.   → persist_state() + emit_event()
7.   → Evaluar approval_rules con _check_approval_rule()
8. → return results
```

**I3.x HITL (si aplica en test handover, probablemente no — HITL es flujo completo):**
```
1. Flow.execute(input_data)
2. → validate_input + create_task_record
3. → _run_crew() → si approval_rule match → request_approval()
4.   → state.await_approval()
5.   → persist_state() + EventStore.append_sync("approval.requested")
6. → Flow se pausa (return)
7. → POST /approvals/{task_id} → resume()
8.   → Restaurar snapshot
9.   → _on_approved() o _on_rejected()
```

### Contratos

**`MCPPool.get_tools()` contrato:**
- Input: `org_id: str`, `server_name: str`, `timeout: int = 30`, `max_retries: int = 3`
- Output: `list` (tool objects)
- Raises: `MCPConnectionError` — circuit breaker abierto o retries agotados
- Side effects: Modifica `_health` dict, `_adapters` dict

**`DynamicWorkflow._run_crew()` contrato:**
- Input: `self.state.input_data` (dict), `self._template_definition` (dict)
- Output: `Dict[str, Any]` — results por step_id
- Side effects: persist_state(), emit_event(), posible request_approval()

**`_check_approval_rule()` contrato (BUG):**
- Input: `rule: Dict[str, Any]` con `condition` y `description`, `results: Dict`
- Output: `bool`
- BUG: `>=`, `<=`, `==` se evalúan como False silenciosamente

### Error handling

- `MCPPool.get_tools()` — `MCPConnectionError` propagado con mensajes descriptivos
- `DynamicWorkflow._run_crew()` — si crew falla, excepción propagada al caller (`execute()` con `@with_error_handling`)
- `base_flow.py` — `@with_error_handling` decorator: captura Exception → marca state FAILED → persist_state → re-raise

---

## 4️⃣ Analisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Tests

```
[Migración SQL] → workflow_templates, org_mcp_servers (RLS)
        ↓
[DynamicWorkflow._run_crew()] → lee template.steps
        ↓
[BaseCrew.run_async()] → lee agent_catalog (RLS)
        ↓
[results dict] → _check_approval_rule() → True?
        ↓                                ↓
[persist_state + emit]           [request_approval → HITL]
        ↓                                ↓
[results dict retornado]    [Flow pausado → reanudado vía resume()]
```

### Coherencia: Decisiones de data/code/backend apoyan al MVP

- ✅ Tests de integración No tocan DB real — todo mockeado con `conftest.py`
- ✅ Patrones de mocking consistes entre Paso 1 y Paso 2
- ⚠️ HITL tests (si I3.x necesita flow completo) requieren más mocking que lo que los fixtures actuales proveen (EventStore.append_sync, get_service_client para snapshots)

### Gaps identificados

1. **No hay fixture para `EventStore.append_sync()`.** Los tests HITL en `test_hitl_pause_resume.py` pueden tener este problema también. Para I3.x si testea flow completo HITL, se necesita patch.
2. **Bug `>=`/`<=`/`==` bloquea tests condicionales I4.1-I4.3.** Decisión:
   - **Opción A (recomendada):** Fix parser primero → luego tests I4.1-I4.3 validan fix.
   - **Opción B:** Marcar como won't-fix → agregar test de regresión documentando bug.
3. **I2.x requiere mock de `crewai_tools.MCPServerAdapter`.** Importación lazy dentro de `get_tools()` — mock debe estar en namespace `src.tools.mcp_pool` antes de llamar.
4. **`test_3_5_latency.py` en raíz de tests/ no se movió.** Plan Paso 0 lo menciona. Verificar si está corregido o sigue fallando.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap test-integration
- **Qué automatiza:** Ejecutar todos los tests de integración del paso actual con un solo comando, con soporte para verbose, coverage y filtro por archivo.
- **Tipo:** Comando CLI (extensión de fap)
- **Cómo se usa:** `fap test-integration 2` o `fap test-integration 2 --cov`
- **Impacto para el usuario final:** Elimina la necesidad de recordar rutas específicas de archivos test y comandos pytest complejos. Un solo comando para validar todo el paso.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso para dogfooding.
```

---

## 5️⃣ Criterios de Aceptacion

```
✅ [DATA] No se requieren migraciones nuevas para Paso 2
✅ [DATA] Todas las tablas mockeadas correctamente en tests (org_mcp_servers, workflow_templates, tasks, snapshots, pending_approvals, domain_events, agent_catalog)
✅ [CODE] test_mcp_resilience.py existe con tests I2.1-I2.3
✅ [CODE] test_handover_real.py existe con tests I3.1-I3.3
✅ [CODE] Bug >= / <= / == en _check_approval_rule documentado con decisión tomada
✅ [CODE] Si se implementa fix de approval operators: tests I4.1-I4.3 pasan en test_approval_operators.py
✅ [BACKEND] I2.1: 5 fallos consecutivos → circuit breaker abierto → 6º intento lanza MCPConnectionError sin intentar conexión
✅ [BACKEND] I2.2: Circuito abierto → 60s elapsed → half-open → éxito → reset (failures==0)
✅ [BACKEND] I2.3: Circuito abierto → 60s elapsed → half-open → fallo → circuito re-abre (failures>=5)
✅ [BACKEND] I3.1: Step 2 recibe previous_results con output de step 1
✅ [BACKEND] I3.2: Template con 0 steps retorna {} sin excepción
✅ [BACKEND] I3.3: Step 2 falla → step 1 resultado preservado en results dict
✅ [FULLSTACK] Todos los tests de integración pasan con mocks (sin DB, sin LLM, sin MCP real)
✅ [FULLSTACK] Circuit breaker validado con time.time mockeado (no espera real)
✅ [DX] fap test-integration 2 ejecuta todos los tests del paso con un comando
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigacion |
|--------|-----------|-------|------------|
| Mock de MCPServerAdapter complejo | Alta | Importación lazy dentro de `get_tools()` en try/except. Patch puede no aplicarse si import falla primero | Patch en namespace `src.tools.mcp_pool` ANTES de cualquier llamada. Alternativamente: mockar `_connect()` internamente |
| Bug `>=`/`<=`/`==` requiere decisión antes de tests I4 | Alta | Tests I4.1-I4.3 son condicionales a implementación del fix. Sin decisión, no se pueden escribir | Decidir Opción A (fix) o B (won't-fix) ANTES de escribir I4 tests |
| HITL flow completo requiere mocking de EventStore.append_sync | Media | `base_flow.py:request_approval()` llama `EventStore.append_sync()` — fixture actual no lo mockea | Agregar `patch("src.flows.base_flow.EventStore.append_sync")` o `patch("src.events.store.EventStore.append_sync")` |
| Contaminación de estado entre tests de integración | Media | `MCPPool` es singleton → `_health` y `_adapters` persisten entre tests | `MCPPool.reset()` en fixture autouse. `flow_registry.clear()` en setup/teardown |
| I2.x con `asyncio.wait_for` en `get_tools()` | Baja | Timeout en test podría causar flakiness si mock no retorna a tiempo | Usar `asyncio.get_running_loop()` mock o patch `asyncio.wait_for` |
| `test_3_5_latency.py` sigue fallando | Baja | Plan Paso 0 lo menciona como failing | Verificar estado actual. Si falla, marcar con `@pytest.mark.skip` antes de Paso 2 |

---

## 7️⃣ Plan de Implementacion

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|-------|----------|-------------|-------------|--------------|
| 0 | **DX & Tooling:** Implementar `fap test-integration` | FULLSTACK/DX | Media | 1h | Ninguna |
| 1 | Decisión: ¿Fix `>=`/`<=`/`==` en `_check_approval_rule`? | CODE | Baja | 0.5h | Ninguna |
| 2 | Crear `test_mcp_resilience.py` con I2.1-I2.3 | BACKEND | Alta | 3h | Tarea 0 |
| 3 | Crear `test_handover_real.py` con I3.1-I3.3 | BACKEND | Alta | 2h | Tarea 0 |
| 4 | (Condicional) Fix `_check_approval_rule` para `>=`, `<=`, `==` | CODE | Media | 1h | Tarea 1 decidida = A |
| 5 | (Condicional) Expandir `test_approval_operators.py` con I4.1-I4.3 | CODE | Media | 0.5h | Tarea 4 |
| 6 | (Condicional) Agregar test regresión si won't-fix | CODE | Baja | 0.5h | Tarea 1 decidida = B |
| 7 | Verificar `test_3_5_latency.py` — skip o fix | BACKEND | Baja | 0.5h | Ninguna |
| 8 | Ejecutar suite completa + validar | FULLSTACK | Baja | 0.5h | Tareas 2-7 |

**Tiempo total estimado:** 6.5-9.5 horas (dependiendo de decisión I4)

---

## 🔮 Roadmap (NO implementar ahora)

- **Optimización:** Refactorizar `_check_approval_rule` para usar parser robusto (AST o regex con precedencia de operadores). El fix actual si se hace es mínimo — solo agregar `>=` antes de `>` y `<=` antes de `<`. Pero un parser apropiado eliminaría la deuda técnica.
- **Mejora:** Agregar `approval_threshold` como alternativa numérica a `condition` string — campo ya existe en `StepDefinition` pero no se usa.
- **Mejora:** HITL tests E2E completos (Paso 3) con flujo pause → approve → resume → complete.
- **Pre-requisito Paso 3:** Los mocks de HITL desarrollados en Paso 2 son base directa para Paso 3 E2E.
- **Mejora futura:** `MCPPool` conexión async nativa (sin `run_in_executor`) cuando `crewai_tools` soporte async.

---

## 🚫 Reglas de Oro — Verificacion

- ✅ Análisis accionable y específico, no genérico
- ✅ TODO verificado contra código, no supuestos
- ✅ Discrepancias con plan documentadas (4 encontradas)
- ✅ Plan contradice código → código gana (bug `>=` más grave que "se rompe silenciosamente")
- ✅ Nivel CTO exigente en rigor
- ✅ Coherente con phase-state.md — Paso 2 es el próximo paso
- ✅ TODO el paso cubierto (I2.1-I2.3, I3.1-I3.3, I4.1-I4.3 condicional)
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta (`fap test-integration`)