# Análisis Técnico — Paso 2: Integración — Resiliencia y Feature Gaps

**Agente:** qwen
**Paso:** 2
**Fecha:** 2026-05-01
**Fase:** testing (Fase VI)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `MCPPool._is_circuit_open` | `src/tools/mcp_pool.py:61-65` | ✅ | Línea 61: `def _is_circuit_open(self, key: str) -> bool:` |
| 2 | `MCPPool._record_failure` | `src/tools/mcp_pool.py:68-70` | ✅ | Línea 68: `def _record_failure(self, key: str) -> None:` |
| 3 | `MCPPool._reset_circuit_breaker` | `src/tools/mcp_pool.py:72-73` | ✅ | Línea 72: `def _reset_circuit_breaker(self, key: str) -> None:` |
| 4 | `MCPPool.get_tools` | `src/tools/mcp_pool.py:77-190` | ✅ | Método async con retry + circuit breaker |
| 5 | `MCPConnectionError` | `src/tools/mcp_pool.py:31-32` | ✅ | Clase Exception custom |
| 6 | `MCPPool.reset` | `src/tools/mcp_pool.py:209-211` | ✅ | `classmethod reset(cls) -> None` |
| 7 | Circuit breaker threshold = 5 fallos | `src/tools/mcp_pool.py:63` | ✅ | `if health["failures"] < 5:` |
| 8 | Circuit breaker window = 60s | `src/tools/mcp_pool.py:66` | ✅ | `return elapsed < 60` |
| 9 | `DynamicWorkflow._check_approval_rule` | `src/flows/dynamic_flow.py:128-159` | ✅ | Solo parsea `>` y `<` |
| 10 | Bug `>=`/`<=`/`==` confirmado | `src/flows/dynamic_flow.py:137` | ✅ | `if ">" in condition:` captura `>=` → `split(">")` → `float("= 50000")` → ValueError |
| 11 | `DynamicWorkflow._run_crew` | `src/flows/dynamic_flow.py:66-126` | ✅ | Itera steps, pasa `previous_results`, evalua approval_rules |
| 12 | `test_mcp_pool_circuit.py` existe | `tests/unit/test_mcp_pool_circuit.py` | ✅ | 5 tests unitarios (U1.1-U1.5) |
| 13 | `test_approval_operators.py` existe | `tests/unit/test_approval_operators.py` | ✅ | 4 tests unitarios (U3.1-U3.4) |
| 14 | `test_dynamic_flow.py` existe | `tests/integration/test_dynamic_flow.py` | ✅ | 421 líneas, cubre registration, execution, approval |
| 15 | `test_hitl_pause_resume.py` existe | `tests/integration/test_hitl_pause_resume.py` | ✅ | Cubre request_approval, resume, _on_approved, _on_rejected |
| 16 | `conftest.py` fixtures | `tests/conftest.py` | ✅ | `mock_service_client`, `mock_tenant_client`, `mock_event_store`, `global_llm_mock`, `mock_mcp_pool`, `sample_org_id` |
| 17 | `test_mcp_resilience.py` NO existe | `tests/integration/` listing | ❌ | Archivo no existe — crear |
| 18 | `test_handover_real.py` NO existe | `tests/integration/` listing | ❌ | Archivo no existe — crear |
| 19 | `BaseFlow.request_approval` | `src/flows/base_flow.py:267-337` | ✅ | HITL pause con serialización |
| 20 | `BaseFlow.resume` | `src/flows/base_flow.py:341-403` | ✅ | Restauración + decisión |
| 21 | `BaseCrew` import en dynamic_flow | `src/flows/dynamic_flow.py:20` | ✅ | `from ..crews.base_crew import BaseCrew` |
| 22 | `flow_registry` | `src/flows/registry.py` | ✅ | Verificado vía `test_dynamic_flow.py:113` |
| 23 | Tenacity retry en MCPPool | `src/tools/mcp_pool.py:23,108-112` | ✅ | `@retry(wait=wait_exponential(...), stop=stop_after_attempt(...))` |
| 24 | `previous_results` pasado a crew | `src/flows/dynamic_flow.py:99` | ✅ | `"previous_results": results` en inputs |

**Discrepancias encontradas:**

1. **DISCREPANCIA D1:** Plan dice Paso 2 tiene sub-pasos 2.1 (MCP Resilience), 2.2 (DynamicWorkflow handover), 2.3 (Feature operadores `>=`, `<=`, `==`). El plan original menciona tests I2.1-I2.3, I3.1-I3.3, I4.1-I4.3. Pero `phase-state.md` reenumera pasos: Paso 2 actual = "Tests de Integración de Flujos Críticos". Los sub-pasos del plan.md original (2.1, 2.2, 2.3) corresponden al Paso 2 actual. **Resolución:** Seguir plan.md sub-pasos 2.1-2.3 como contenido del análisis.

2. **DISCREPANCIA D2:** Plan.md original Paso 2.3 dice "Decisión requerida antes de escribir tests" sobre operadores `>=`, `<=`, `==`. `phase-state.md` línea 62 confirma: "Bug `>=`/`<=`/`==` documentado y diferido a Paso 2". **Resolución:** Este análisis incluye la implementación del fix del parser + tests como parte del paso.

3. **DISCREPANCIA D3:** `test_3_5_latency.py` está en `tests/` raíz, no en `tests/integration/`. Plan.md Paso 0 nota dice "Considerar mover". No afecta Paso 2 directamente pero es deuda técnica. **Resolución:** No abordar en este paso. Documentar como riesgo.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Alcance:** Paso 2 no toca schema DB directamente. Tests de integración usan mocks. Sin embargo, verificar tablas referenciadas:

- ✅ `org_mcp_servers` — usada en `mcp_pool.py:125`. Existe según `phase-state.md` sección "Esquemas DB Clave". Columnas: `org_id`, `name`, `is_active`, `command`, `args`, `secret_name`.
- ✅ `workflow_templates` — usada en `dynamic_flow.py:175`. Columnas: `flow_type`, `definition` (JSONB), `is_active`.
- ✅ `tasks` — usada en `base_flow.py:189`. Columnas: `id`, `org_id`, `flow_type`, `status`, `payload`, `correlation_id`, `approval_required`, `approval_status`, `approval_payload`, `tokens_used`.
- ✅ `snapshots` — usada en `base_flow.py:228-252`. Columnas: `task_id`, `org_id`, `flow_type`, `status`, `state_json`, `aggregate_id`, `aggregate_type`.
- ✅ `pending_approvals` — usada en `base_flow.py:308`. Columnas: `org_id`, `task_id`, `flow_type`, `description`, `payload`.

**RLS policies:** Todas las tablas usan tenant isolation via `org_id::text`. Los mocks de `conftest.py` (`mock_tenant_client`) simulan RLS correctamente.

**Índices:** No se requieren nuevos índices para tests de integración. Los existentes cubren queries de lookup por `org_id` + `name` (MCP servers) y `flow_type` + `is_active` (workflow templates).

**Impacto en datos existentes:** Ninguno. Tests 100% mockeados.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Sub-paso 2.1: MCP Resilience — `tests/integration/test_mcp_resilience.py`

**Archivos nuevos:** `tests/integration/test_mcp_resilience.py`

**Tests I2.1-I2.3:** Verifican ciclo completo del circuit breaker con `MCPPool.get_tools()`.

**Patrón de mocking confirmado:**
- `patch("src.tools.mcp_pool.get_service_client")` → mock de DB config lookup
- `patch("crewai_tools.MCPServerAdapter")` → mock de conexión MCP real
- `patch("time.time")` → control de temporización (60s window)
- `MCPPool.reset()` entre tests → limpiar singleton

**Firmas requeridas:**
```python
# I2.1: 5 fallos → circuito abierto → 6º intento falla inmediato
async def test_circuit_opens_after_five_consecutive_failures()

# I2.2: open → 60s → half-open → éxito → reset
async def test_circuit_full_cycle_open_to_half_open_to_close()

# I2.3: open → 60s → half-open → fallo → re-open
async def test_circuit_half_open_failure_reopens()
```

**Cohesión:** Tests integran `MCPPool.get_tools()` con mocks de DB + MCP adapter. No son unitarios aislados — ejercen el flujo completo de conexión → fallo → circuit breaker → recuperación.

**Acoplamiento:** Dependencia de `conftest.py` fixtures (`mock_service_client`). Pool singleton requiere `reset()` explícito.

### Sub-paso 2.2: DynamicWorkflow Handover — `tests/integration/test_handover_real.py`

**Archivos nuevos:** `tests/integration/test_handover_real.py`

**Tests I3.1-I3.3:** Verifican contexto entre steps, edge case 0 steps, fallo parcial.

**Patrón de mocking confirmado:**
- `mock_service_client`, `mock_tenant_client`, `mock_event_store` fixtures
- `patch("src.flows.dynamic_flow.BaseCrew")` → mock de crew execution
- `global_llm_mock` fixture ya mockea `crewai.Crew`, `crewai.Task`, `crewai.Agent`

**Firmas requeridas:**
```python
# I3.1: Step 2 recibe previous_results con output de step 1
async def test_step_receives_previous_results_context()

# I3.2: Template con 0 steps → no crashea
async def test_empty_steps_template_no_crash()

# I3.3: Step 2 falla → step 1 resultado preservado
async def test_partial_failure_preserves_previous_results()
```

**Verificación crítica:** `dynamic_flow.py:99` pasa `"previous_results": results` a cada crew. El `results` dict se construye incrementalmente (línea 107: `results[step_id] = {"result": str(result.raw)}`). Esto confirma que I3.1 es verificable.

**Bug potencial:** Si `crew.run_async()` lanza excepción, el loop en `_run_crew()` no captura — la excepción se propaga (no hay try/except dentro del for). Esto significa que I3.3 (fallo en step intermedio) verifica que results del step 1 ya están en el dict antes del crash. El `with_error_handling` decorator en `BaseFlow.execute()` captura la excepción y marca estado como FAILED.

### Sub-paso 2.3: Fix operadores `>=`, `<=`, `==` en `_check_approval_rule`

**Archivo a modificar:** `src/flows/dynamic_flow.py` (líneas 128-159)

**Bug confirmado:** 
- Línea 137: `if ">" in condition:` — si condition = `"monto >= 50000"`, `">"` está presente → entra al branch `>`
- Línea 138: `_, threshold = condition.split(">", 1)` — `"monto >= 50000".split(">", 1)` → `["monto >=", " 50000"]`
- Línea 139: `threshold = float(threshold.strip())` → `float("50000")` = 50000. OK en este caso.
- PERO: `"monto <= 1000"` → `">"` NO está presente → entra al branch `<` (línea 147)
- `"monto <= 1000".split("<", 1)` → `["monto <=", " 1000"]` → `float("1000")` = 1000. OK.
- `"monto == 50000"` → ni `>` ni `<` están presentes → retorna False silenciosamente.

**Análisis más profundo del bug:**
- `>=` funciona POR ACCIDENTE cuando el valor después de `>` es numérico puro. Pero la comparación usa `>` (mayor que), no `>=` (mayor o igual). Ej: `"monto >= 50000"` con valor 50000 → `50000 > 50000` → False. Debería ser True.
- `<=` funciona POR ACCIDENTE similar pero con `<`. Ej: `"monto <= 1000"` con valor 1000 → `1000 < 1000` → False. Debería ser True.
- `==` nunca funciona → retorna False siempre.

**Fix propuesto:** Reescribir el parser para priorizar operadores compuestos:

```python
def _check_approval_rule(self, rule: Dict[str, Any], results: Dict) -> bool:
    condition = rule.get("condition", "")
    if not condition:
        return False
    
    # Priorizar operadores compuestos antes que simples
    operators = [">=", "<=", "==", ">", "<"]
    
    for op in operators:
        if op in condition:
            parts = condition.split(op, 1)
            if len(parts) != 2:
                continue
            try:
                threshold = float(parts[1].strip())
            except (ValueError, TypeError):
                return False
            
            for v in results.values():
                if isinstance(v, dict) and "result" in v:
                    try:
                        value = float(str(v["result"]))
                    except (ValueError, TypeError):
                        continue
                    
                    if op == ">" and value > threshold:
                        return True
                    elif op == "<" and value < threshold:
                        return True
                    elif op == ">=" and value >= threshold:
                        return True
                    elif op == "<=" and value <= threshold:
                        return True
                    elif op == "==" and value == threshold:
                        return True
            break  # Solo evaluar primer operador encontrado
    
    return False
```

**Tests I4.1-I4.3:** Agregar a `tests/unit/test_approval_operators.py` (archivo existente de Paso 1):

```python
# I4.1: >= con valor igual → True
def test_approval_greater_than_or_equal_true()

# I4.2: <= con valor igual → True  
def test_approval_less_than_or_equal_true()

# I4.3: == con valor exacto → True
def test_approval_equal_true()
```

**Tests de regresión adicionales (recomendados):**
- `>=` con valor mayor → True
- `<=` con valor menor → True
- `==` con valor diferente → False

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**APIs/endpoints:** Paso 2 no crea ni modifica endpoints. Tests de integración ejercen flujos internos.

**Middleware:** No aplica. Tests mockean directamente las capas de servicio.

**Flujo de datos:**

```
Sub-paso 2.1 (MCP Resilience):
  MCPPool.get_tools() → DB lookup (mock) → MCP adapter (mock) → tools list
  Circuit breaker: _record_failure → _is_circuit_open → MCPConnectionError
  
Sub-paso 2.2 (Handover):
  DynamicWorkflow._run_crew() → loop steps → BaseCrew.run_async() → results dict
  Contexto: results[step_id] → previous_results en siguiente step
  
Sub-paso 2.3 (Approval operators):
  _check_approval_rule(rule, results) → parse condition → compare → bool
  Sin IO externo. Función pura síncrona.
```

**Contratos:**
- `MCPPool.get_tools(org_id, server_name)` → `list[tool]` o `MCPConnectionError`
- `DynamicWorkflow._run_crew()` → `Dict[str, Any]` con `{step_id: {"result": str}}`
- `_check_approval_rule(rule, results)` → `bool`

**Error handling:**
- MCP: `MCPConnectionError` con mensaje descriptivo (circuit breaker, timeout, config missing)
- Handover: Excepción propagada desde `BaseCrew.run_async()` → capturada por `with_error_handling` → estado FAILED
- Approval: ValueError silencioso → False (fix elimina esto)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
DB (org_mcp_servers) → MCPPool.get_tools() → circuit breaker → tools para AgentFactory
                                                              ↓
workflow_templates → DynamicWorkflow.register() → _run_crew() → previous_results entre steps
                                                              ↓
approval_rules → _check_approval_rule() → request_approval() → HITL pause
                                                              ↓
snapshots + pending_approvals → resume() → approved/rejected
```

### Coherencia

- ✅ Circuit breaker en MCPPool soporta resiliencia de flujos MCP
- ✅ Handover de contexto entre steps soporta workflows multi-paso
- ✅ Approval rules con operadores completos soportan gates de aprobación precisos
- ✅ Todo mockeado — sin LLM real, sin DB real, sin MCP real

### Gaps identificados

1. **Gap G1:** `approval_threshold` field en `StepDefinition` (`workflow_definition.py:47`) sigue sin usarse. Fuera de scope de Paso 2 pero es deuda técnica acumulada.
2. **Gap G2:** `test_3_5_latency.py` en raíz de `tests/` — debería estar en `tests/integration/` o `tests/stress/`. No bloquea Paso 2.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap test-step 2 (extensión)
- **Qué automatiza:** Ejecutar los tests de integración del Paso 2 con un solo comando, incluyendo el fix de approval operators y verificación de circuit breaker.
- **Tipo:** CLI command (extensión de existente `src/cli/commands/test_step.py`)
- **Cómo se usa:** `fap test-step 2` → corre tests de test_mcp_resilience.py + test_handover_real.py + test_approval_operators.py (con fix)
- **Impacto para el usuario final:** Evita tener que recordar qué archivos de test corresponden al Paso 2. Un comando, resultado claro con pass/fail breakdown por sub-paso.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

**Nota:** `fap test-step` ya existe (Paso 1). Solo requiere agregar mapeo de Paso 2 → archivos de test correspondientes.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tablas org_mcp_servers, workflow_templates, tasks, snapshots, pending_approvals verificadas como existentes en código
✅ [CODE] test_mcp_resilience.py existe con 3 tests (I2.1-I2.3) de circuit breaker integration
✅ [CODE] test_handover_real.py existe con 3 tests (I3.1-I3.3) de handover de contexto
✅ [CODE] _check_approval_rule soporta >=, <=, == sin errores silenciosos
✅ [CODE] test_approval_operators.py incluye tests I4.1-I4.3 para nuevos operadores
✅ [BACKEND] MCPPool.get_tools() con circuito abierto lanza MCPConnectionError sin intentar conexión
✅ [BACKEND] DynamicWorkflow._run_crew() pasa previous_results correctamente entre steps
✅ [BACKEND] _check_approval_rule("monto >= 50000", {"step_1": {"result": "50000"}}) → True
✅ [FULLSTACK] Flujo MCP resilience: 5 fallos → circuito abierto → 60s → half-open → éxito → reset
✅ [FULLSTACK] Flujo handover: step_1 output disponible en step_2 previous_results
✅ [FULLSTACK] Approval rule con >= evalúa correctamente valor igual al threshold
✅ [DX] fap test-step 2 ejecuta todos los tests del Paso 2 con un comando
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Singleton MCPPool contaminado entre tests | Alta | `MCPPool._instance` compartido si `reset()` no se llama | Fixture `autouse=True` con `MCPPool.reset()` en setup + teardown |
| `time.time` mock afecta otros tests | Media | Patch global de `time.time` puede interferir con tests paralelos | Patch scoped solo al test individual, no fixture global |
| Fix de approval operators rompe tests existentes | Media | Cambio de lógica de parsing puede alterar comportamiento de `>` y `<` | Tests U3.1-U3.4 de Paso 1 deben seguir pasando. Ejecutar como regressión |
| `crewai_tools.MCPServerAdapter` no disponible en test env | Media | Paquete opcional (`crew` extra en pyproject.toml) | Mockear import con `patch.dict(sys.modules)` si no instalado |
| `test_3_5_latency.py` en raíz causa confusión | Baja | Archivo fuera de estructura esperada | Documentar como deuda técnica, mover en paso posterior |
| `approval_threshold` sin usar crea confusión | Baja | Campo definido pero no referenciado en código | Documentar en phase-state.md como deuda. Fuera de scope Paso 2 |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Extender `fap test-step` para Paso 2 | FULLSTACK/DX | Baja | 1h | Ninguna |
| 1 | Fix `_check_approval_rule` para soportar `>=`, `<=`, `==` | CODE | Media | 1.5h | Ninguna |
| 2 | Tests I4.1-I4.3 + regresión en `test_approval_operators.py` | CODE | Baja | 1h | Tarea 1 |
| 3 | Crear `test_mcp_resilience.py` con I2.1-I2.3 | BACKEND | Alta | 3h | Tarea 0 |
| 4 | Crear `test_handover_real.py` con I3.1-I3.3 | FULLSTACK | Alta | 3h | Tarea 0 |
| 5 | Ejecutar regressión: tests Paso 1 deben seguir pasando | CODE | Baja | 0.5h | Tareas 1-4 |
| 6 | Ejecutar `fap test-step 2` y validar 100% pass | FULLSTACK | Baja | 0.5h | Tareas 1-5 |

**Tiempo total estimado:** 10.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Mover `test_3_5_latency.py` de `tests/` raíz a `tests/integration/` o `tests/stress/`
- Implementar uso de `approval_threshold` en `DynamicWorkflow._run_crew()` como alternativa a `approval_rules[].condition`
- Agregar test de regresión para bug `>=`/`<=`/`==` silencioso (asegurar que no reaparezca)
- Considerar migrar `_check_approval_rule` a evaluador de expresiones seguro (ej: `asteval` o parser dedicado) para soportar condiciones compuestas (`monto > 1000 AND tipo == "transferencia"`)
- Agregar métricas de circuit breaker (count de aperturas, tiempo en estado open) para observabilidad

---

## 📊 Métrica de Calidad (auto-evaluación)

| Métrica | Mínimo | Resultado |
|---|---|---|
| `proyecto-config.json` leído antes de explorar | 100% | ✅ |
| Elementos verificados (§0) | ≥ 12 (3-5 archivos) | ✅ 24 elementos |
| Discrepancias detectadas | ≥ 1 | ✅ 3 discrepancias |
| Secciones completadas | 8 (0-7) | ✅ 8 secciones |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) | ✅ 4 etapas |
| Criterios de aceptación | ≥ 1 por sub-paso | ✅ 12 criterios |
| Riesgos identificados | ≥ 3 | ✅ 6 riesgos |
| Tareas en el plan | ≥ 4 | ✅ 7 tareas |
| Suposiciones no verificadas | ≤ 2 | ✅ 0 suposiciones |
| Propuesta DX / Tooling | ≥ 1 | ✅ 1 herramienta |
| Estimación de tiempo | Sí, por tarea y total | ✅ 10.5h total |
