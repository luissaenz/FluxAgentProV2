# Plan de Certificación: Agentes Grado Producción (v3.1 — Corregido)

> **Reemplaza:** plan v3.0 (errores aritméticos, asunciones sobre suite corregidas, bug de seguridad ampliado).
> **Foco real:** Solo gaps genuinos. Zero duplicación. Tests de código propio, no de dependencias externas.
> **Suite actual:** 425 tests (unit + integration + e2e + sueltos). `conftest.py` con mocks globales de Supabase, LLM, CrewAI.
> **Auditoría de duplicación:** Cada test propuesto verificado contra tests existentes antes de incluir.

---

## Fase Única: Certificación Técnica Profunda (QA)

### Paso 0: Auditoría de Línea Base (Pre-flight)

**Objetivo:** Verificar que todo compila, importa y suite actual pasa limpio.

| # | Prueba | Herramienta | Criterio de Éxito |
|---|---|---|---|
| P0.1 | Importabilidad de todos los módulos `src/` | `pytest --co` | 0 errores de import |
| P0.2 | Suite existente completa | `pytest tests/` | 100% pass (0 failures, 0 errors) |
| P0.3 | Lint estricto | `ruff check src/ tests/` | 0 errores |
| P0.4 | Auditoría de tool_registry real | Script que lea `tool_registry.list_all()` | Reporte de tools disponibles |
| P0.5 | Verificar fixtures `conftest.py` | `pytest --fixtures` | `sample_org_id`, `mock_service_client`, `mock_tenant_client`, `global_llm_mock`, `mock_mcp_pool` disponibles |

**Gate:** Si P0.1-P0.3 no pasan → NO continuar. Corregir regresiones primero.

**⚠️ BUG CONOCIDO:** `test_3_5_latency.py::TestLatencyValidation::test_full_latency_validation` FALLA actualmente. Corregir antes de continuar (añadir `@pytest.mark.skip` si es test de integración real que requiere DB).

**⚠️ VULNERABILIDAD CRÍTICA CONFIRMADA:** `security_guard.py` inyecta `__import__` en sandbox non-system (línea 142 y 221). AST scanner no detecta acceso indirecto vía `__builtins__["__import__"]`. Tests SE5.13-SE5.16 son diagnóstico obligatorio. Si confirman exploit → fix antes de merge.

**Notas:**
- P0.4 (mypy) eliminado: no hay `pyproject.toml` configurado para mypy.
- P0.6 (migraciones SQL) eliminado: Supabase no tiene "DB temporal" local sin `supabase-cli`. Fuera de scope.
- No hay `Makefile`. Se usa `pytest` directo. `make test-all` se crea en Paso 7.
- `test_3_5_latency.py` está en `tests/` raíz, no en subdirectorio. Considerar mover a `tests/integration/` o `tests/stress/`.

---

### Paso 1: Cobertura Unitaria de Gaps Críticos

**Objetivo:** Tests unitarios para código sin cobertura. Solo lo que no existe ya.

#### 1.1 Circuit Breaker de MCPPool — `tests/unit/test_mcp_pool_circuit.py`

**Justificación:** `mcp_pool.py` tiene `_record_failure`, `_is_circuit_open`, `_reset_circuit_breaker` sin test directo. `test_mcp_exceptions.py` solo testa excepciones MCP del protocolo, no el circuit breaker.

| # | Prueba | Qué verifica | Criterio |
|---|---|---|---|
| U1.1 | `_is_circuit_open` = False con 0-4 fallos | Circuito cerrado | False |
| U1.2 | `_is_circuit_open` = True con >=5 fallos y <60s | Circuito abierto | True |
| U1.3 | `_is_circuit_open` = False tras 60s (half-open) | Mock de `time.time()` para evitar espera real | False tras avance simulado |
| U1.4 | `get_tools` lanza `MCPConnectionError` con circuito abierto | Sin intentar conexión | `MCPConnectionError` con mensaje "Circuit breaker abierto" |
| U1.5 | `get_tools` éxito tras half-open → `_reset_circuit_breaker` | Reset tras éxito | `failures == 0` |

**Estrategia de mocking:** `unittest.mock.patch` sobre `time.time` para controlar temporización sin esperas reales. `MCPPool.reset()` entre tests para limpiar singleton.

#### 1.2 ServiceConnector error paths — `tests/unit/test_service_connector.py`

**Justificación:** Archivo no existe. `service_connector.py:_run` tiene 7 ramas de error sin test. `conftest.py` ya tiene `mock_service_client` y `mock_service_connector` fixtures.

| # | Prueba | Qué verifica | Criterio |
|---|---|---|---|
| U2.1 | `_run` con tool_id inexistente | `service_tools` sin match | Mensaje con "no encontrada" |
| U2.2 | `_run` con servicio inactivo | `org_service_integrations.status != "active"` | Mensaje con "no está activo" |
| U2.3 | `_run` con VaultError | `get_secret` lanza excepción | `str(VaultError)` en output |
| U2.4 | `_run` con HTTP 401 | `httpx.HTTPStatusError(401)` | `"Error HTTP: 401"` |
| U2.5 | `_run` con HTTP 500 | `httpx.HTTPStatusError(500)` | `"Error HTTP: 500"` |
| U2.6 | `_run` con `httpx.ConnectError` | Servicio inalcanzable | `"Error HTTP: "` + mensaje |
| U2.7 | `_run` con respuesta no-JSON | Body texto plano | Output truncado 500 chars, sin crash |

**Estrategia de mocking:** `mock_service_client` fixture para DB. `patch("httpx.Client")` para HTTP. `patch("src.tools.service_connector.get_secret")` para Vault.

#### 1.3 Approval operators faltantes — `tests/unit/test_approval_operators.py`

**Justificación:** `test_dynamic_flow.py` ya cubre `>` (true/false), condición inválida, resultado no numérico. **Faltan:** `<` standalone, condición vacía, múltiples resultados. Estos son 3 tests, no 8.

| # | Prueba | Qué verifica | Criterio |
|---|---|---|---|
| U3.1 | `<` con valor menor → True | `"monto < 1000"` con `"500"` | True |
| U3.2 | `<` con valor mayor → False | `"monto < 1000"` con `"5000"` | False |
| U3.3 | Condición vacía → False | `""` | False, sin excepción |
| U3.4 | Múltiples resultados, uno cumple | `"total > 100"` con `{"a": {"result": "50"}, "b": {"result": "200"}}` | True |

**Nota:** `>=`, `<=`, `==` NO están implementados en `dynamic_flow.py:128-159`. No se testean aquí. Ver Paso 2 para feature request.

#### 1.4 Sanitizer edge cases — `tests/unit/test_sanitizer.py` (nuevo)

**Justificación:** `mcp/sanitizer.py` no tiene tests. 50 líneas de código sin cobertura. `SECRET_PATTERNS` tiene 7 patrones: `sk_live_`, `sk_test_`, `Bearer`, `Basic`, `xox[bpsa]-` (Slack), `ghp_` (GitHub), `AIza` (Google).

| # | Prueba | Qué verifica | Criterio |
|---|---|---|---|
| U4.1 | String con `sk_live_` key → redactado | Patrón Stripe live | `[REDACTED]` en output |
| U4.2 | String con `sk_test_` key → redactado | Patrón Stripe test | `[REDACTED]` en output |
| U4.3 | String con `Bearer token` → redactado | Patrón Bearer | `[REDACTED]` |
| U4.4 | String con `Basic auth` → redactado | patrón Basic auth | `[REDACTED]` |
| U4.5 | String con `ghp_` token → redactado | GitHub PAT | `[REDACTED]` |
| U4.6 | String con `AIza` key → redactado | Google API key | `[REDACTED]` |
| U4.7 | String con `xoxb-` Slack token → redactado | Slack token | `[REDACTED]` |
| U4.8 | Dict anidado con secreto → redactado recursivo | `{"auth": "sk_live_abc"}` | Secreto redactado, estructura preservada |
| U4.9 | Lista con secreto → redactado | `["normal", "sk_test_xyz"]` | Segundo elemento redactado |
| U4.10 | Input no-string/no-dict/no-list → passthrough | `42`, `None`, `True` | Valor original sin cambio |
| U4.11 | String sin secretos → sin cambio | `"hello world"` | Output == input |

**Gate:** 100% pass Paso 1. Cobertura `mcp_pool.py` >80%, `service_connector.py` >70%, `sanitizer.py` 100%.

---

### Paso 2: Integración — Resiliencia y Feature Gaps

**Objetivo:** Probar caminos de fallo con mocks precisos. Implementar operadores faltantes si se deciden.

#### 2.1 MCP Resilience — `tests/integration/test_mcp_resilience.py`

**Justificación:** Tests de integración real del circuit breaker con `MCPPool.get_tools()`, no unitarios aislados.

| # | Prueba | Qué verifica | Criterio |
|---|---|---|---|
| I2.1 | 5 fallos consecutivos → circuito abierto → 6º intento falla inmediato | Circuit breaker se activa y bloquea | `MCPConnectionError` en 6º sin intentar conexión |
| I2.2 | Circuito abierto → avance time 60s → half-open permite 1 intento → éxito → reset | Ciclo completo open→half-open→close | `failures == 0` tras éxito |
| I2.3 | Circuito abierto → avance time 60s → half-open permite 1 intento → fallo → open de nuevo | Half-open con fallo re-abre | `failures >= 5` tras fallo |

**Estrategia de mocking:** `patch("src.tools.mcp_pool.get_service_client")` para simular config de servidor. `patch("crewai_tools.MCPServerAdapter")` para simular conexión. `patch("time.time")` para control de temporización.

#### 2.2 DynamicWorkflow handover — `tests/integration/test_handover_real.py`

**Justificación:** `test_dynamic_flow.py` ya cubre ejecución secuencial, persistencia, eventos, skip sin agent_role, approval trigger. **Falta:** contexto entre steps (previous_results), 0 steps, fallo en step intermedio.

| # | Prueba | Qué verifica | Criterio |
|---|---|---|---|
| I3.1 | Step 2 recibe `previous_results` con output de step 1 | Contexto pasado correctamente | `previous_results["step_1"]` contiene resultado real |
| I3.2 | Template con 0 steps → no crashea | Edge case | Retorna `{}`, sin excepción |
| I3.3 | Step 2 falla (crew lanza excepción) → step 1 resultado preservado | Fallo parcial no pierde contexto | `results["step_1"]` presente, excepción propagada o capturada |

**Estrategia de mocking:** `mock_service_client`, `mock_tenant_client`, `mock_event_store` fixtures. `BaseCrew` mockeado vía `global_llm_mock` fixture.

#### 2.3 Feature: operadores `>=`, `<=`, `==` en approval rules

**BUG DETECTADO:** `_check_approval_rule` usa `" > " in condition` y `" < " in condition`. Si condition es `"monto >= 50000"`, `">"` está presente → parsea como `>` con threshold `= 50000` → `float("= 50000")` lanza `ValueError` → retorna `False` silenciosamente. No es que "no estén implementados", es que **se rompen silenciosamente**.

**Decisión requerida antes de escribir tests:**
- ¿Se implementan `>=`, `<=`, `==` en `_check_approval_rule`?
- Si SÍ → implementar primero (fix parser para priorizar `>=` sobre `>`), luego agregar 3 tests en `test_dynamic_flow.py`.
- Si NO → marcar como bug conocido y agregar test de regresión.

**Conditional tests (solo si se implementan):**

| # | Prueba | Qué verifica | Criterio |
|---|---|---|---|
| I4.1 | `>=` con valor igual → True | `"monto >= 50000"` con `50000` | True |
| I4.2 | `<=` con valor igual → True | `"monto <= 1000"` con `1000` | True |
| I4.3 | `==` con valor exacto → True | `"monto == 50000"` con `50000` | True |

**Nota sobre `Step.approval_threshold`:** El campo existe en `StepDefinition` (`workflow_definition.py:47`) pero **no se usa** en `DynamicWorkflow._run_crew()`. El workflow usa `approval_rules[].condition` (string). Si se quiere usar `approval_threshold`, hay que modificar `_run_crew()`. Fuera de scope de testing puro.

**Gate:** 100% pass Paso 2. Circuit breaker validado con mock de `time.time()` (espera real de 60s es inviable en CI).

---

### Paso 3: E2E — Flujos Completos con Mocks

**Objetivo:** 3 flujos E2E ejerciendo combinaciones no cubiertas por los 6 escenarios existentes. **Todo mockeado** — sin LLM real, sin DB real, sin MCP real.

**Archivo nuevo:** `tests/e2e/test_production_flows.py`

**Estrategia de mocking:** `conftest.py` ya tiene `global_llm_mock` (mockea `crewai.Agent`, `crewai.Task`, `crewai.Crew`, `ChatOpenAI`, `ChatOllama`). `mock_service_client` para DB. `mock_mcp_pool` para MCP.

| # | Prueba | Descripción | Criterio |
|---|---|---|---|
| E3.1 | **"Degraded MCP"** — `resolve_tools` con 2 tools MCP: pool retorna 1, otra falla | Workflow usa tools disponibles, loguea fallo | Lista de tools contiene 1, warning en log, sin crash |
| E3.2 | **"Approval Gate HITL"** — Flujo con approval rule → `request_approval` → `resume()` → completa | Ciclo HITL completo | Estado: PENDING → AWAITING_APPROVAL → COMPLETED |
| E3.3 | **"Multi-step handover"** — 3 steps, cada uno consume output del anterior | Contexto preservado 3 niveles | `previous_results` contiene step_1 y step_2 en step_3 |

**Gate:** 100% pass Paso 3. Cada flujo <5s (todo mockeado).

---

### Paso 4: Estrés y Condiciones de Borde (Solo código propio)

**Objetivo:** Condiciones extremas en código controlado. **No tests de dependencias externas** (CrewAI max_iter, LLM rate limits).

#### 4.1 Concurrencia — `tests/stress/test_concurrency.py`

| # | Prueba | Descripción | Criterio |
|---|---|---|---|
| S4.1 | `resolve_tools` con 500 tools (todas mock registry) | Resolución masiva | <2s, sin memory leak visible |
| S4.2 | 50 `DynamicWorkflow` en `asyncio.gather` (todos mockeados) | Concurrencia de flows | 0 deadlocks, todos completan |
| S4.3 | `MCPPool.reset()` llamado 100 veces consecutivas | Singleton reset repetido | Sin error, singleton limpio |

**Eliminados del plan original:**
- S4.3 original (`BaseCrew max_iter=1000`): test de CrewAI, no código propio.
- S4.4 original (`WorkflowDefinition` 100 steps): ya cubierto por validación Pydantic, no es stress test.

#### 4.2 Edge cases — `tests/stress/test_edge_cases.py`

| # | Prueba | Descripción | Criterio |
|---|---|---|---|
| S4.4 | `WorkflowDefinition` con `flow_type` duplicado en registry | `DynamicWorkflow.register` con mismo flow_type 2 veces | Segundo registro sobrescribe sin error ni warning — comportamiento documentado, no bug |
| S4.5 | `sanitize_output` con string de 10MB | Sanitización de output masivo | Completado en <5s, sin OOM |
| S4.6 | `org_id` vacío en `resolve_tools` | Tool resolution con org_id="" | Sin crash, comportamiento definido |
| S4.7 | `input_data` con JSON 20 niveles de profundidad | Datos anidados extremos en workflow | Sin stack overflow, sin timeout |

**Eliminados del plan original:**
- S4.5 original (1000 bundles): depende de DB real, lento, no aporta valor sobre test unitario de bundle_manager.
- S4.6 original (100 reconexiones MCPPool): requiere mock de `MCPServerAdapter` complejo, bajo ROI.
- S4.8 original (hash mismatch): ya cubierto por `test_bundle_manager.py`.
- S4.9 original (org_id malformado): cubierto por S4.6.

**Gate:** 100% pass Paso 4. Sin degradación de memoria >50MB.

---

### Paso 5: Seguridad — Hardening

**Objetivo:** Tests que no existen ya. `test_security_guard.py` ya cubre: `os`, `sys`, `urllib`, `eval`, `open`, dunder, timeout, bypass builtins.

#### 5.1 Imports faltantes en test existente — expandir `tests/unit/test_security_guard.py`

Tests que **no existen** y son relevantes (agregar al archivo existente):

| # | Prueba | Descripción | Criterio |
|---|---|---|---|
| SE5.1 | `import subprocess` → bloqueado | FORBIDDEN_MODULES | `SecurityError` con "Forbidden import 'subprocess'" |
| SE5.2 | `import shutil` → bloqueado | FORBIDDEN_MODULES | `SecurityError` |
| SE5.3 | `import ctypes` → bloqueado | FORBIDDEN_MODULES | `SecurityError` |
| SE5.4 | `import socket` → bloqueado | FORBIDDEN_MODULES | `SecurityError` |
| SE5.5 | `import gc` → bloqueado | FORBIDDEN_MODULES | `SecurityError` |
| SE5.6 | `import inspect` → bloqueado | FORBIDDEN_MODULES | `SecurityError` |
| SE5.7 | `import requests` → bloqueado | FORBIDDEN_MODULES | `SecurityError` |
| SE5.8 | `__import__("os")` → bloqueado | FORBIDDEN_CALLS | `SecurityError` con "Forbidden function call '__import__'" |
| SE5.9 | `compile("1+1", "", "eval")` → bloqueado | FORBIDDEN_CALLS | `SecurityError` |
| SE5.10 | `exec("x=1")` → bloqueado | FORBIDDEN_CALLS | `SecurityError` |

#### 5.2 Async en system vs non-system — `tests/unit/test_security_guard.py` (expandir)

| # | Prueba | Descripción | Criterio |
|---|---|---|---|
| SE5.11 | `async def` en `is_system=False` → bloqueado | RestrictedPython no soporta async | `SecurityError` en compilación |
| SE5.12 | `async def` en `is_system=True` → permitido | System bundles bypass RestrictedPython | `validate_skill` retorna True |

#### 5.3 SecurityGap crítico: `execute()` Y `_verify_compilation()` inyectan `__import__`

**VULNERABILIDAD IDENTIFICADA — DOS vectores:**

1. `security_guard.py:142`: `exec_globals["__builtins__"]["__import__"] = __import__` — inyecta `__import__` en sandbox de non-system bundles.
2. `security_guard.py:221`: `safe_env["__import__"] = __import__` — inyecta `__import__` en `_verify_compilation()` para RestrictedPython.

Ambos paths permiten `import os` dentro de código ejecutado. El AST scanner (`_scan_ast`) bloquea `import os` directo, pero si el código malicioso se ejecuta DESPUÉS del scan (lo cual ocurre en `execute()` y `_verify_compilation()`), tiene acceso a `__import__`.

**CRÍTICO:** `FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "__import__"}`. El AST scan detecta `__import__("os")` como call → bloquea. PERO `exec_globals["__builtins__"]["__import__"]` inyecta la referencia DESPUÉS del scan. Código como `x = __builtins__; x["__import__"]("os")` no sería detectado por el AST scanner (no es una `ast.Call` directa sobre `__import__`).

| # | Prueba | Descripción | Criterio |
|---|---|---|---|
| SE5.13 | `execute()` con código que hace `import os` → ¿se ejecuta? | Verificar si inyección de `__import__` permite imports prohibidos | **Debe fallar** (SecurityError). Si pasa → bug crítico |
| SE5.14 | `execute()` con `__builtins__["open"]` → ¿se ejecuta? | Verificar bypass de builtins | **Debe fallar**. Si pasa → bug crítico |
| SE5.15 | `_verify_compilation()` con código que usa `__import__` inyectado → ¿se ejecuta? | Verificar segundo vector (línea 221) | **Debe fallar** (SecurityError). Si pasa → bug crítico |
| SE5.16 | Código sin `import` directo pero con `x = __builtins__; x["__import__"]("os")` → ¿se bloquea? | Bypass indirecto de AST scanner | **Debe fallar** (SecurityError). Si pasa → bug crítico |

**⚠️ ACCIÓN REQUERIDA:** Si SE5.13, SE5.15 o SE5.16 pasan (código malicioso se ejecuta), **FIJAR `security_guard.py` ANTES de continuar**. El fix sería: no inyectar `__import__` en builtins, o usar un `__import__` restringido que solo permita módulos en `ALLOWED_MODULES`.

#### 5.4 Escape attempts — `tests/unit/test_security_guard_escape.py`

| # | Prueba | Descripción | Criterio |
|---|---|---|---|
| SE5.17 | `import importlib; importlib.import_module("os")` | Bypass vía importlib dinámico | `SecurityError` (importlib está en FORBIDDEN_MODULES) |
| SE5.18 | Payload hex-encoded `import os` | `\x69\x6d\x70\x6f\x72\x74\x20\x6f\x73` | `SecurityError` en RestrictedPython sandbox |

**Eliminados del plan original:**
- SE5.12 original (getattr indirecto): ya cubierto por test dunder existente.
- SE5.15 original (open en sandbox): ya cubierto por `test_forbidden_open`.
- SE5.16 original (monkey-patch builtins): ya cubierto por `test_bypass_attempt`.
- SE5.17 original (while True timeout): ya cubierto por `test_timeout_infinite_loop`.
- SE5.18 original (importlib): cubierto por SE5.15 aquí.
- SE5.19 original (hex payload): cubierto por SE5.16 aquí.
- SE5.20 original (clase dinámica): RestrictedPython ya lo bloquea, test redundante.

**Gate:** 100% pass Paso 5. SE5.13, SE5.15, SE5.16 son diagnósticos críticos. Si revelan vulnerabilidad → fix `security_guard.py` antes de merge.

---

### Paso 6: Performance & Observabilidad

**Objetivo:** Métricas de rendimiento en código propio. Sin LLM real.

| # | Prueba | Descripción | Criterio |
|---|---|---|---|
| P6.1 | Latencia de `resolve_tools` con 50 tools (mock registry) | Benchmark con `time.perf_counter` | <100ms |
| P6.2 | Latencia de `WorkflowDefinition` validación con 10 steps, 5 agents | Pydantic validation benchmark | <50ms |
| P6.3 | `sanitize_output` con string 1MB | Performance de sanitizer | <500ms |
| P6.4 | `MCPPool.get_tools` con circuito cerrado vs abierto | Overhead de circuit breaker check | <1ms para check |

**Eliminados del plan original:**
- P6.3 original (token tracking accuracy): requiere LLM real para verificar tokens. Fuera de scope.
- P6.4 original (log structure validation): vago, no hay criterio medible.
- P6.5 original (event emission no bloquea): requiere mock de event store lento, bajo ROI.

**Gate:** P6.1-P6.4 bajo thresholds.

---

### Paso 7: Documentación y Cierre

| # | Tarea | Descripción | Criterio |
|---|---|---|---|
| D7.1 | `TESTING.md` en raíz | Documentar cómo correr cada paso | Comando exacto por paso, estrategia de mocking |
| D7.2 | `Makefile` en raíz | Targets: `test`, `test-fast`, `test-all`, `lint`, `coverage` | `make test-all` corre Pasos 0-6 en orden |
| D7.3 | Reporte de cobertura final | `pytest --cov=src --cov-report=html` | Cobertura global >75% |
| D7.4 | `fap phase-close` | Cierre automatizado de fase | Archivado en `DEVS/IMPLEMENTED/certificacion/` |
| D7.5 | CHANGELOG | Registrar mejoras | Entry por cada paso |

---

## Criterios de Aceptación Final

- [ ] Paso 0: 100% pass. Baseline establecida.
- [ ] Paso 1: +25 tests unitarios (5 circuit + 7 connector + 4 approval + 9 sanitizer). Gaps críticos cubiertos.
- [ ] Paso 2: +6 tests integración (3 MCP resilience + 3 handover). (+3 condicionales si se implementan operadores). **DECISIÓN:** Fix parser `>=`, `<=`, `==` antes de tests condicionales.
- [ ] Paso 3: +3 tests E2E. Flujos mockeados, deterministas.
- [ ] Paso 4: +7 tests estrés/borde. Solo código propio.
- [ ] Paso 5: +18 tests seguridad (10 imports + 2 async + 4 execute/compilation gap + 2 escape). **PRIORIDAD:** SE5.13-SE5.16 primero. Si pasan → bug crítico → fix `security_guard.py` antes de continuar.
- [ ] Paso 6: +4 benchmarks. Sin LLM real.
- [ ] Paso 7: Docs, Makefile, cobertura >75%, changelog.

**Total proyectado:** ~63 tests nuevos sobre los 425 existentes = **~488 tests total**.

---

## Protocolo de Ejecución

1. **Paso 0 primero.** Sin excepción. Si algo falla → corregir antes de continuar.
2. **Paso 5 (SE5.13-SE5.16) antes de Paso 1.** Vulnerabilidad `__import__` confirmada teóricamente. Tests diagnóstico primero. Si confirman exploit → **FIX `security_guard.py` ANTES de cualquier otro paso**.
3. **Pasos 1-7 en orden** (tras Paso 5 diagnóstico). Cada paso es gate para el siguiente.
4. **Todo mockeado.** Sin LLM real, sin DB real, sin MCP real. Usar fixtures de `conftest.py`.
5. **Circuit breaker:** usar `patch("time.time")`, NO esperar 60s reales.
6. **E2E deterministas:** WorkflowDefinitions hardcodeadas. NUNCA ArchitectFlow en tests automatizados.
7. **`make test-all`** ejecuta todo en orden y reporta breakdown por paso.
8. **DECISIÓN Paso 2:** Implementar `>=`, `<=`, `==` en `_check_approval_rule` o marcar como won't-fix. Parser actual rompe silenciosamente con estos operadores.

### Fix requerido para vulnerabilidad `__import__` (si SE5.13-SE5.16 confirman exploit):

**Opción A (recomendada):** No inyectar `__import__` en builtins. Usar allowlist de módulos en `execute()` y `_verify_compilation()`. Crear `__import__` restringido que solo permita módulos en `ALLOWED_MODULES`.

**Opción B:** Mantener inyección pero mejorar AST scanner para detectar acceso indirecto vía `__builtins__` (subscript + call pattern). Más complejo, menos seguro.

**Opción C:** Eliminar `_verify_compilation()` dry-run. Solo compilar con RestrictedPython, no ejecutar. Elimina vector línea 221. Vector línea 142 (`execute()`)仍需 fix.

---

## Resumen de Cambios vs v3.0

| Cambio | Razón |
|---|---|
| Suite actual: 55 → 427 tests | Conteo real de `pytest --co` |
| Test failing conocido: `test_3_5_latency` | Bloquea Paso 0, necesita fix |
| ServiceConnector: 8 → 7 ramas de error | Conteo real del código |
| Sanitizer: 7 → 11 tests | Los 7 patrones de `SECRET_PATTERNS` aparecen en tests individuales |
| Paso 1: 19 → 25 tests | Corrección aritmética + sanitizer expandido |
| `>=`, `<=`, `==` no son "no implementados" sino "se rompen silenciosamente" | `_check_approval_rule` parsea `>=` como `>` + `=`, ValueError silencioso |
| Vulnerabilidad `__import__` afecta AMBOS paths: `execute()` y `_verify_compilation()` | Línea 142 Y línea 221 inyectan `__import__` |
| SE5.13-14 → SE5.13-16 (3 tests diagnóstico) | Añadido test de `_verify_compilation()` bypass y bypass indirecto de AST |
| SE5.15-16 → SE5.17-18 | Renumerados tras insertar SE5.15-16 |
| S4.4: registry duplicado "sobrescribe" | Verificado en `flow_registry._flows` (dict simple) |
| Total: ~55 → ~63 tests nuevos | Corrección aritmética |
