# 🧠 Análisis Técnico — Paso 2: Integración: Resiliencia y Feature Gaps

**Agente:** `ds`  
**Fecha:** 2026-05-01  
**Fase:** `testing` (Fase VI)  
**Archivo salida:** `DEVS/IN_PROGRESS/analisis-2-ds.md`  

---

## 0️⃣ Verificación contra Código Fuente

### Alcance del paso
| Archivos afectados | 2 crear + 1 modificar condicional = 3 archivos |
|---|---|
| **Umbral mínimo** | ≥ 12 elementos |
| **Verificados** | **20 elementos** |

### Tabla de verificación

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `MCPPool._is_circuit_open()` | Inspección | ✅ | `src/tools/mcp_pool.py:60-66` |
| 2 | `MCPPool._record_failure()` | Inspección | ✅ | `src/tools/mcp_pool.py:68-70` |
| 3 | `MCPPool._reset_circuit_breaker()` | Inspección | ✅ | `src/tools/mcp_pool.py:72-73` |
| 4 | `MCPPool.get_tools()` | Inspección | ✅ | `src/tools/mcp_pool.py:77-190` |
| 5 | `DynamicWorkflow._check_approval_rule()` | Inspección | ✅ | `src/flows/dynamic_flow.py:128-159` |
| 6 | `DynamicWorkflow._run_crew()` | Inspección | ✅ | `src/flows/dynamic_flow.py:66-126` |
| 7 | `BaseCrew.run_async()` | Inspección | ✅ | `src/crews/base_crew.py:169-205` |
| 8 | `mock_service_client` fixture | Inspección | ✅ | `tests/conftest.py:111-140` |
| 9 | `mock_mcp_pool` fixture | Inspección | ✅ | `tests/conftest.py:303-316` |
| 10 | `global_llm_mock` fixture (mockea CrewAI) | Inspección | ✅ | `tests/conftest.py:274-300` |
| 11 | `mock_event_store` fixture | Inspección | ✅ | `tests/conftest.py:219-231` |
| 12 | Tabla `org_mcp_servers` | grep migrations | ✅ | `supabase/migrations/005_org_mcp_servers.sql:9` |
| 13 | Tabla `workflow_templates` | grep migrations | ✅ | `supabase/migrations/006_workflow_templates.sql:6` |
| 14 | Tabla `agent_catalog` | grep migrations | ✅ | `supabase/migrations/004_agent_catalog.sql` |
| 15 | `test_dynamic_flow.py` integración existe | Inspección | ✅ | `tests/integration/test_dynamic_flow.py` (421 líneas, 12 tests) |
| 16 | `test_approval_operators.py` unitario existe | Inspección | ✅ | `tests/unit/test_approval_operators.py` (72 líneas, 4 tests) |
| 17 | `test_mcp_pool_circuit.py` unitario existe | Inspección | ✅ | `tests/unit/test_mcp_pool_circuit.py` (94 líneas, 5 tests) |
| 18 | `test_mcp_resilience.py` NO existe aún | glob `tests/integration/` | ✅ | Archivo a crear — sin colisión |
| 19 | `test_handover_real.py` NO existe aún | glob `tests/integration/` | ✅ | Archivo a crear — sin colisión |
| 20 | `fap test-step` CLI existe | Inspección | ✅ | `src/cli/commands/test_step.py` — extender para paso 2 |

### Discrepancias encontradas

| # | Discrepancia | Tipo | Resolución propuesta |
|---|---|---|---|
| D1 | **Docstring vs código:** `_check_approval_rule` línea 133 dice "Solo soporta operadores básicos: >, <, >=, <=" pero el código solo implementa `>` y `<` con `if/elif` simple. `>=` y `<=` producen ValueError silencioso. | ❌ | Actualizar docstring para reflejar realidad actual O implementar los operadores faltantes. Si se implementan, el docstring ya es correcto. |
| D2 | **`>=`, `<=`, `==` bug:** `dynamic_flow.py:137` — `">" in condition` da True para `"monto >= 50000"` → `split(">")` produce `["monto ", "= 50000"]` → `float("= 50000")` → ValueError → False silencioso. Es un bug, no una feature ausente. | ❌ | DECISIÓN REQUERIDA: Fix parser antes de tests. Priorizar `>=` sobre `>`, `<=` sobre `<`, `==` como operador exacto. Ver §2.3 para plan de implementación. |
| D3 | **`approval_threshold` no usado:** `workflow_definition.py:47` define el campo en `StepDefinition` pero `_run_crew()` nunca lo referencia. | ⚠️ | Documentado como deuda técnica. No bloquea paso 2. Resolver en paso futuro. |
| D4 | **`MCPServerAdapter` no mockeado en conftest:** `conftest.py` mockea `crewai.Agent/Task/Crew` pero no `crewai_tools.MCPServerAdapter`. Los tests de integración de MCP necesitarán `patch("crewai_tools.MCPServerAdapter")` local. | ⚠️ | Agregar mock local en `test_mcp_resilience.py`. No modificar conftest global (evitar side effects en otros tests). |
| D5 | **`mock_service_client` parchea `src.tools.mcp_pool.get_service_client`:** Confirmado en `conftest.py:123`. Correcto para paso 2 — `get_tools()` usa `get_service_client()` para cargar config de `org_mcp_servers`. | ✅ | Sin acción. Verificado correcto. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema involucrado

| Tabla | Rol en paso 2 | Migración | RLS |
|---|---|---|---|
| `org_mcp_servers` | 2.1: `get_tools()` consulta config de servidor MCP | `005_org_mcp_servers.sql:9` | `tenant_isolation_org_mcp_servers` (línea 26) |
| `workflow_templates` | 2.2: `DynamicWorkflow` carga definiciones desde DB | `006_workflow_templates.sql:6` | `tenant_isolation` (línea 56) |
| `agent_catalog` | 2.1/2.2: `BaseCrew._load_agent_config()` | `004_agent_catalog.sql` | RLS por org_id |
| `tasks` | Indirecta: `persist_state()` | `002_governance.sql` | RLS |
| `snapshots` | Indirecta: `persist_state()` | `002_governance.sql` | RLS |
| `pending_approvals` | Indirecta: `request_approval()` (2.2). | `002_governance.sql` | RLS |
| `service_tools` | Indirecta: ServiceConnector (no es foco de paso 2). | `024_service_catalog.sql:59` | Sin RLS (global) |
| `org_service_integrations` | Indirecta: ServiceConnector (no es foco). | `024_service_catalog.sql:28` | RLS línea 47 |

### Integridad referencial

- `org_mcp_servers.org_id → organizations(id)` — ON DELETE CASCADE ✅
- `workflow_templates.org_id → organizations(id)` — ON DELETE CASCADE ✅
- Sin cambios de schema en este paso. No se crean ni alteran tablas.

### RLS policies aplicables

- **2.1:** `get_tools()` usa `get_service_client()` (service_role) — bypass de RLS. Config de MCP se lee con permisos elevados. Correcto para backend.
- **2.2:** `DynamicWorkflow` usa `get_tenant_client()` para persistencia — RLS activo. Verificado que `mock_tenant_client` fixture en tests parchea todos los puntos de import necesarios (`conftest.py:189-200`).

### Índices existentes

- `idx_mcp_servers_org ON org_mcp_servers(org_id)` — suficiente para `get_tools()` (filtra por org_id + name).
- `idx_workflow_templates_org_active ON workflow_templates(org_id) WHERE is_active = TRUE` — suficiente para `load_dynamic_flows_from_db()`.
- Sin necesidad de nuevos índices.

### Tipos de datos

- `org_mcp_servers.args` → `JSONB DEFAULT '[]'` — `get_tools()` usa `config.data.get("args", [])`. Coherente.
- `org_mcp_servers.secret_name` → `TEXT` (nullable) — `get_tools()` consulta condicional (`config.data.get("secret_name")`). Coherente.
- Sin problemas de tipos en este paso.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos nuevos

#### `tests/integration/test_mcp_resilience.py` (2.1)

**Tests:** I2.1, I2.2, I2.3  
**Qué verifican:** Ciclo completo del circuit breaker con `MCPPool.get_tools()` real (mockeado).

**Patrón a seguir:** `tests/unit/test_mcp_pool_circuit.py`  
- `MCPPool.reset()` en fixture `autouse=True`  
- `patch("time.time")` por test individual  
- `_make_pool_with_state()` helper para pre-configurar estado de salud  

**Diferencia clave vs unitarios:** Los tests de integración deben mockear `MCPServerAdapter`, `get_service_client` y `get_secret_async` para que `get_tools()` complete el flujo completo (no solo el check del circuit breaker).

**Estrategia de mocking:**
```python
# Mock de DB
mock_service_client.table("org_mcp_servers").select... → config válida
# Mock de MCP adapter
patch("crewai_tools.MCPServerAdapter") → adapter con tools
# Mock de time para control de temporización
patch("time.time")
# Mock de asyncio para evitar thread pool real
patch("asyncio.get_running_loop")
```

**Riesgo:** `MCPServerAdapter` es dependencia opcional (`crewai-tools`). Si no está instalada, `get_tools()` lanza `MCPConnectionError` específico. Los tests deben mockear la clase ANTES de que se intente importar.

#### `tests/integration/test_handover_real.py` (2.2)

**Tests:** I3.1, I3.2, I3.3  
**Qué verifican:** Contexto entre steps del DynamicWorkflow.

**Patrón a seguir:** `tests/integration/test_dynamic_flow.py`  
- Instanciar `DynamicWorkflow` directamente  
- `flow.state = MagicMock()`  
- `patch("src.flows.dynamic_flow.BaseCrew")` con mock que retorne valores configurables  
- Mock de `flow.persist_state` y `flow.emit_event` como AsyncMock  

**Tests ya cubiertos (no duplicar):**
- Ejecución secuencial → `test_executes_all_steps_sequentially`  
- Persistencia por step → `test_persists_state_after_each_step`  
- Eventos por step → `test_emits_event_after_each_step`  
- Skip sin agent_role → `test_skips_step_without_agent_role`  
- Approval trigger → `test_triggers_approval_when_rule_matches`  

**Gaps reales a cubrir (I3.1-I3.3):**
- **I3.1 — Contexto `previous_results`:** Verificar que step 2 recibe `inputs["previous_results"]` con output real de step 1. Actualmente `_run_crew()` pasa `previous_results: results` en línea 99. Este flujo NO está testeado explícitamente.
- **I3.2 — 0 steps:** Template con `steps: []` → `_run_crew()` no itera → retorna `{}`. Edge case NO testeado.
- **I3.3 — Fallo parcial:** Step 2 lanza excepción → step 1 resultado preservado en `results`. El comportamiento actual de `_run_crew()` es: la excepción se propaga sin captura → no hay `try/except` dentro del loop → el resultado de step 1 está en `results` pero nunca se retorna porque la excepción corta la ejecución.

### Archivos modificados (condicional)

#### `src/flows/dynamic_flow.py` — `_check_approval_rule()` (2.3)

**Bug actual (línea 137):**
```python
if ">" in condition:       # "monto >= 50000" → True → BUG
    _, threshold = condition.split(">", 1)
    threshold = float(threshold.strip())  # "= 50000" → ValueError
```

**Fix propuesto (parche mínimo):**
```python
# Orden de chequeo: operadores compuestos primero, simples después
if ">=" in condition:
    _, threshold = condition.split(">=", 1)
    operator = ">="
elif "<=" in condition:
    _, threshold = condition.split("<=", 1)
    operator = "<="
elif "==" in condition:
    _, threshold = condition.split("==", 1)
    operator = "=="
elif ">" in condition:
    _, threshold = condition.split(">", 1)
    operator = ">"
elif "<" in condition:
    _, threshold = condition.split("<", 1)
    operator = "<"
else:
    return False

threshold = float(threshold.strip())
for v in results.values():
    if isinstance(v, dict) and "result" in v:
        try:
            val = float(str(v["result"]))
            if operator == ">=" and val >= threshold: return True
            if operator == "<=" and val <= threshold: return True
            if operator == "==" and val == threshold: return True
            if operator == ">" and val > threshold: return True
            if operator == "<" and val < threshold: return True
        except (ValueError, TypeError):
            continue
```

**Impacto:** ~15 líneas de cambio. Cero riesgo para código existente (los tests existentes de `>` y `<` siguen pasando). 3 tests nuevos (I4.1-I4.3).

### Patrones y convenciones

- **Naming:** `test_mcp_resilience.py`, `test_handover_real.py` — snake_case ✅
- **Imports:** `from src.tools.mcp_pool import MCPConnectionError, MCPPool` — absolutos ✅
- **Async tests:** `@pytest.mark.asyncio` — consistente con tests existentes ✅
- **Fixtures:** Usar `mock_service_client`, `mock_tenant_client`, `mock_event_store`, `sample_org_id` de conftest ✅
- **MCPPool.reset():** Obligatorio entre tests. Ya probado en unitarios. ✅

### Duplicación

| Test propuesto | ¿Duplica test existente? | Veredicto |
|---|---|---|
| I2.1 (5 fallos → abierto → 6º falla) | Parcialmente U1.4, pero I2.1 verifica el ciclo completo (5 fallos reales + 6º intento), no solo estado pre-cargado | Complementario ✅ |
| I2.2 (half-open → éxito → reset) | U1.3 + U1.5, pero I2.2 verifica flujo completo con mock de `MCPServerAdapter` | Complementario ✅ |
| I2.3 (half-open → fallo → re-abre) | Sin equivalente unitario directo | Nuevo ✅ |
| I3.1 (previous_results entre steps) | No existe test que verifique el contenido de `inputs["previous_results"]` | Nuevo ✅ |
| I3.2 (0 steps) | No existe | Nuevo ✅ |
| I3.3 (fallo parcial preserva resultados) | No existe | Nuevo ✅ |
| I4.1-I4.3 (>=, <=, ==) | No existen — los tests actuales solo cubren `>` y `<` | Nuevos ✅ |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs/endpoints

Paso 2 no crea ni modifica endpoints. Es puramente tests de integración internos.

### Middleware aplicable

No aplica. Los tests mockean las capas de DB y MCP, no pasan por middleware HTTP.

### Flujo de datos en tests

**2.1 — MCP Resilience:**
```
Test → MCPPool.get_tools(org_id, server_name)
     → get_service_client() [MOCKEADO]
     → DB query org_mcp_servers [MOCKEADO]
     → MCPServerAdapter(params) [MOCKEADO]
     → return tools list
     → _record_failure / _reset_circuit_breaker
```

**2.2 — DynamicWorkflow Handover:**
```
Test → DynamicWorkflow._run_crew()
     → BaseCrew(org_id, role) [MOCKEADO]
     → crew.run_async(description, inputs={previous_results, ...})
     → persist_state() [MOCKEADO]
     → emit_event() [MOCKEADO]
     → _check_approval_rule()
```

### Contratos

Sin cambios en contratos externos. Los mocks deben respetar la interfaz real:
- `BaseCrew.run_async()` → retorna objeto con `.raw` (string)
- `MCPPool.get_tools()` → lanza `MCPConnectionError` en fallo
- `get_service_client().table().select().eq().eq().eq().maybe_single().execute()` → `.data` dict o `None`

### Error handling en tests

- **I2.1:** `MCPConnectionError` con mensaje "Circuit breaker abierto" debe lanzarse sin intentar conexión.
- **I2.3:** Tras half-open + fallo → `_record_failure` incrementa contador a 6 → `_is_circuit_open` True de nuevo.
- **I3.3:** Excepción en step 2 → step 1 resultado se pierde (no hay captura). Esto es un **comportamiento documentado**, no un bug. El test debe verificar el comportamiento real, no el ideal.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
DB (org_mcp_servers, workflow_templates, agent_catalog)
    ↓ [get_service_client / get_tenant_client — MOCKEADO]
Backend (MCPPool.get_tools, DynamicWorkflow._run_crew, BaseCrew.run_async)
    ↓ [crewai_tools.MCPServerAdapter — MOCKEADO]
Tests (pytest + asyncio + unittest.mock)
    ↓
Validación (asserts sobre resultados, excepciones, estados)
```

### Coherencia

- **2.1 cierra el gap** entre tests unitarios de circuit breaker (solo estados) y el comportamiento real de `get_tools()` (DB + adapter + retry).
- **2.2 cierra el gap** entre tests de dynamic_flow existentes (ejecución básica) y escenarios de fallo parcial + contexto.
- **2.3 corrige un bug real** que produce falsos negativos silenciosos en reglas de approval.

### Alineación con phase-state.md

- Bug `>=`/`<=`/`==` documentado en `phase-state.md:62` — diferido a Paso 2. **Este es el momento de resolverlo.**
- `approval_threshold` no usado documentado en `phase-state.md:63` — deuda técnica. No se toca en paso 2.
- `fap test-step` existe para paso 1 — extender para paso 2.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap test-step 2
- **Qué automatiza:** Ejecución de los 6-9 tests del paso 2 con un solo comando. El usuario no tiene que recordar nombres de archivo ni flags de pytest.
- **Tipo:** Comando CLI (extensión de comando existente)
- **Cómo se usa:** fap test-step 2 [--cov] [--verbose]
- **Impacto para el usuario final:** Elimina la necesidad de ejecutar manualmente:
    pytest tests/integration/test_mcp_resilience.py tests/integration/test_handover_real.py -v
  Y si se implementan >=, <=, ==, añade automáticamente:
    pytest tests/integration/test_dynamic_flow.py -k "greater_equal or less_equal or equal"
- **Prioridad:** Tarea 0 — implementar antes que los tests mismos (dogfooding).
```

**Extensión requerida en `src/cli/commands/test_step.py`:**
- Mapear `step=2` → `tests/integration/test_mcp_resilience.py tests/integration/test_handover_real.py`
- Si `--with-operators` → añadir `tests/integration/test_dynamic_flow.py -k "I4"`
- Soporte `--cov` (pytest-cov) ya existe para paso 1, reutilizar.

---

## 5️⃣ Criterios de Aceptación

### 2.1 — MCP Resilience

- [ ] **[CODE]** `test_mcp_resilience.py` existe en `tests/integration/`
- [ ] **[CODE]** I2.1: 5 fallos consecutivos → 6º intento lanza `MCPConnectionError` sin intentar conexión
- [ ] **[CODE]** I2.2: Circuito half-open → éxito → `_reset_circuit_breaker` (failures == 0)
- [ ] **[CODE]** I2.3: Circuito half-open → fallo → circuito re-abre (failures >= 5)
- [ ] **[BACKEND]** `get_tools()` flujo completo mockeado: DB config + adapter + retry
- [ ] **[DATA]** `org_mcp_servers` mock retorna config válida (command, args, secret_name)
- [ ] **[FULLSTACK]** Todos los tests usan `time.time` mockeado — sin esperas reales

### 2.2 — DynamicWorkflow Handover

- [ ] **[CODE]** `test_handover_real.py` existe en `tests/integration/`
- [ ] **[CODE]** I3.1: Step 2 recibe `inputs["previous_results"]` con output real de step 1
- [ ] **[CODE]** I3.2: Template con `steps: []` → retorna `{}` sin excepción
- [ ] **[CODE]** I3.3: Step 2 falla → step 1 resultado preservado (o documentar pérdida)
- [ ] **[BACKEND]** `BaseCrew` mockeado retorna `MagicMock(raw="...")` consistente
- [ ] **[DATA]** `workflow_templates` definición mockeada con estructura correcta

### 2.3 — Operadores >=, <=, == (CONDICIONAL — solo si se implementan)

- [ ] **[CODE]** `>=` operador: valor igual al threshold → True
- [ ] **[CODE]** `<=` operador: valor igual al threshold → True
- [ ] **[CODE]** `==` operador: valor exacto → True
- [ ] **[CODE]** Tests existentes de `>` y `<` siguen pasando (no regresión)
- [ ] **[CODE]** `>=` con valor menor → False (no regresión de `>`)
- [ ] **[CODE]** `<=` con valor mayor → False (no regresión de `<`)

### DX

- [ ] **[DX]** `fap test-step 2` ejecuta todos los tests del paso 2 con un comando
- [ ] **[DX]** `fap test-step 2 --cov` incluye reporte de cobertura
- [ ] **[DX]** `fap test-step 2 --with-operators` (condicional) incluye tests de >=, <=, ==

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **Tests I2.x dependen de `crewai-tools` instalado** | Alta | `MCPServerAdapter` se importa dentro de `get_tools()`. Si el paquete no está instalado, la excepción `ImportError` se captura y se lanza `MCPConnectionError`. Pero el mock debe aplicarse ANTES de la importación real. | Usar `patch("crewai_tools.MCPServerAdapter")` a nivel de módulo en los tests, no dentro de la función. |
| **I3.3: Comportamiento real vs esperado** | Media | `_run_crew()` no captura excepciones dentro del loop. Si step 2 falla, `results` contiene step 1 pero la excepción se propaga y `results` nunca se retorna. | Documentar el comportamiento real. Si se quiere cambiar (try/except dentro del loop), requiere modificación de `_run_crew()` y está fuera del scope de testing puro. El test debe verificar el comportamiento actual. |
| **Regresión en `>` y `<` si se implementan >=, <=, ==** | Media | Cambiar el orden de chequeo en `_check_approval_rule` podría romper condiciones existentes si no se priorizan correctamente los operadores compuestos. | Orden estricto: `>=`, `<=`, `==` primero, luego `>`, luego `<`. Tests existentes son la red de seguridad. |
| **`MCPServerAdapter.__enter__` es síncrono** | Media | `get_tools()` ejecuta `__enter__` en thread pool (`run_in_executor`). Los tests deben mockear `asyncio.get_running_loop` o aceptar que el adapter mockeado no necesita thread pool real. | Mockear `MCPServerAdapter` para que `__enter__` sea no-op. Ejecutar `_sync_enter` directamente sin thread pool. |
| **Contaminación de singleton entre tests** | Baja | `MCPPool` es singleton. Si un test no hace reset, contamina al siguiente. | `MCPPool.reset()` en fixture `autouse=True` (patrón ya probado en unitarios). |
| **Solapamiento con tests existentes** | Baja | `test_dynamic_flow.py` integración ya cubre approval trigger y ejecución secuencial. Los nuevos tests deben enfocarse en gaps no cubiertos. | Cada test I3.x verificado contra tests existentes en §2 (tabla de duplicación). |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| **0** | **DX: Extender `fap test-step` para paso 2** | FULLSTACK/DX | Baja | 0.5h | Ninguna |
| **1** | Crear `tests/integration/test_mcp_resilience.py` con I2.1-I2.3 | CODE | Alta | 3h | Tarea 0 |
| **2** | Crear `tests/integration/test_handover_real.py` con I3.1-I3.3 | CODE | Media | 2h | Tarea 0 |
| **3** | **[DECISIÓN]** Fix `_check_approval_rule()` para >=, <=, == en `dynamic_flow.py` | CODE | Media | 1.5h | Ninguna (puede paralelizarse con 1-2) |
| **4** | Agregar I4.1-I4.3 a `tests/integration/test_dynamic_flow.py` | CODE | Baja | 0.5h | Tarea 3 |
| **5** | Validar paso 2 completo: `fap test-step 2` (6-9 tests) | FULLSTACK | Baja | 0.5h | Tareas 1-4 |
| **6** | Lint + verificar no regresión en tests existentes | FULLSTACK | Baja | 0.5h | Tarea 5 |

**Tiempo total estimado:** 8.5 horas (7h sin operadores >=, <=, ==)

### Orden de ejecución recomendado

1. **Tarea 0** (DX) → dogfooding desde el inicio
2. **Tarea 3** (fix operadores) → desbloquea Tarea 4; puede paralelizarse con Tareas 1-2
3. **Tareas 1-2** (tests) → en paralelo, no dependen entre sí
4. **Tarea 4** (tests condicionales) → solo si Tarea 3 se completa
5. **Tarea 5** (validación) → `fap test-step 2`
6. **Tarea 6** (lint + regresión) → gate final

---

## 🔮 Roadmap (NO implementar ahora)

- **Try/except dentro del loop de `_run_crew()`:** Si step N falla, preservar resultados de steps 1..N-1 y marcarlos como partial. Requiere cambio de arquitectura en DynamicWorkflow.
- **Campo `approval_threshold`:** Actualmente definido pero no usado. Si se implementa, `_run_crew()` debe comparar `step.approval_threshold` contra el resultado numérico. Alternativa: eliminarlo del schema si no se va a usar.
- **Métricas de circuit breaker:** Exponer `_health` stats vía endpoint de monitoreo para debugging en producción.
- **Extender `fap test-step` con `--all`:** Ejecutar todos los pasos en secuencia (0→7).

---

**Resumen:** Paso 2 agrega 6 tests de integración (3 MCP resilience + 3 handover) + 3 condicionales (operadores). Bug crítico en `_check_approval_rule` debe resolverse como pre-requisito de los tests condicionales. DX tool `fap test-step 2` como Tarea 0. Sin cambios de schema. Todo mockeado, sin dependencias externas reales.
