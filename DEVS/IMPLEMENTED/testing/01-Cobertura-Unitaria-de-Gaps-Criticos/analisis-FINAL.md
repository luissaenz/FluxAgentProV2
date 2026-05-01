# 🏛️ Análisis Unificado — Paso 1: Cobertura Unitaria de Gaps Críticos

> **Fecha:** 2026-05-01
> **Fuentes:** `analisis-kimi.md`, `analisis-qwen.md`, `analisis-ds.md`
> **Config:** `proyecto-config.json` — rutas confirmadas
> **Fase:** Certificación — Paso 1

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|---:|:---|:---|:---|---:|
| **kimi** | ✅ 34/34 items | 4 mayores (bug approval, test_latency ausente, lint, approval_threshold no usado) | ✅ `fap test-step` | ✅ líneas exactas + grep | **4.5** |
| **qwen** | ✅ 25/25 items | 4 (D1: test_3_5_latency no existe, D2: 6 ramas no 7, D3: bug `>=`/`<=`/`==`, D4: mock_service_connector fixture) | ✅ `fap test-step` | ✅ líneas + grep + verificación manual | **4.3** |
| **ds** | ✅ 27/27 items | 4 (D1: 6 ramas no 7, D2: `>=`/`<=`/`==` bug, D3: failures como float, D4: approval_threshold no usado) | ✅ `fap test paso1` | ✅ lectura detallada de código | **4.4** |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|:---:|---|---|
| 1 | Plan dice `test_3_5_latency.py` falla en `tests/` raíz. Archivo NO existe en repo. | kimi, qwen | ✅ `glob tests/**/test_3_5_latency*` → vacío | Remove del gate P0. Bug ya no existe. No requiere acción. |
| 2 | Plan dice `_run()` tiene 7 ramas error. Código tiene 6 ramas únicas: HTTP 401 + 500 comparten `except httpx.HTTPStatusError`. | kimi, qwen, ds | ✅ `src/tools/service_connector.py:142-145` | Tests U2.4 (401) + U2.5 (500) válidos — mismo branch, status dif. 6 ramas, 7 tests. Plan corrige: 6 branches, 7 assertions. |
| 3 | `_check_approval_rule` parsea `>=` como `>` → `float("= 50000")` → ValueError silencioso → False. | kimi, qwen, ds | ✅ `src/flows/dynamic_flow.py:137`: `if ">" in condition:` | Bug confirmado. Fix en Paso 2 (feature: implementar `>=`, `<=`, `==`). Tests Paso 1 NO cubren. |
| 4 | `StepDefinition.approval_threshold` (workflow_definition.py:47) existe pero NO se usa en `_run_crew()`. | kimi, ds | ✅ `grep -r approval_threshold src/` → solo definición | Documentar como deuda técnica. Fuera de scope Paso 1. |
| 5 | 3 lint errors auto-fixeables (import ordering) | kimi | ✅ `validate_tools.py:69`, `server.py:7`, `mcp_pool.py:149` | Pre-flight: `ruff check --fix src/`. Baja severidad. |
| 6 | Nombres DX tool difieren entre agentes | kimi (`fap test-step`), qwen (`fap test-step`), ds (`fap test paso1`) | — | Unificar: `fap test-step 1` con flag opcional `--cov`. |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo:** Crear 27 tests unitarios cubriendo 4 gaps críticos sin cobertura: circuit breaker de MCPPool (5 tests), error paths de ServiceConnector (7 tests), operadores `<`/edge cases de approval rules (4 tests), sanitizer de secretos (11 tests). Todo mockeado — sin DB real, sin LLM real, sin MCP real.

**Correcciones al plan:**
- `test_3_5_latency.py` no existe en repo → eliminar del gate P0
- Ramas error de `_run()`: 6 únicas (plan dice 7) — HTTP 401/500 mismo branch. Tests U2.4/U2.5 status diferentes sobre mismo branch.
- Bug `>=`/`<=`/`==` confirmado en `dynamic_flow.py:137`. No se testea en Paso 1 — va a Paso 2.
- 3 lint errors auto-fixeables → corregir como pre-flight.

**Decisión DX tool:** `fap test-step` (unificado de propuestas kimi + qwen + ds). Ejecuta tests de un paso específico con comando único. Tarea 0 obligatoria.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Desarrollador corre `fap test-step 1` (Tarea 0 cumple dogfooding)
2. `pytest` recolecta 27 tests de 4 archivos nuevos
3. Tests de MCPPool circuit breaker verifican: estado cerrado (0-4 fallos), abierto (≥5 fallos, <60s), half-open (>60s), error inmediato con circuito abierto, reset tras éxito en half-open
4. Tests de ServiceConnector verifican: tool no encontrada, servicio inactivo, VaultError, HTTP 401, HTTP 500, ConnectError, non-JSON response truncado
5. Tests de approval verifican: `<` true, `<` false, condición vacía, múltiples resultados
6. Tests de sanitizer verifican: 7 patrones de secreto, dict anidado, lista, primitivos passthrough, string limpio
7. Todos pasan 100%. Cobertura: `mcp_pool.py` >80%, `service_connector.py` >70%, `sanitizer.py` 100%
8. Gate Paso 1 cumplido → avanzar a Paso 2

### Edge Cases MVP

- Circuit breaker half-open: success → reset; failure → re-open
- ServiceConnector: non-JSON response truncado a 500 chars sin crash
- Approval: condición vacía retorna False sin excepción
- Approval: múltiples resultados, uno cumple → True
- Sanitizer: input no-string/no-dict/no-list → passthrough (42, None, True)
- Sanitizer: string sin secretos → sin cambio
- Sanitizer: excepción en procesamiento → `"[ERROR: output no pudo ser procesado]"`

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

| Ruta real | Tipo | Descripción | Interfaces clave |
|---|---|---|---|
| `{paths.tests_unit}/test_mcp_pool_circuit.py` | Creación | 5 tests circuit breaker de MCPPool | `MCPPool._is_circuit_open()`, `._record_failure()`, `._reset_circuit_breaker()`, `.get_tools()`, `.reset()` |
| `{paths.tests_unit}/test_service_connector.py` | Creación | 7 tests error paths de ServiceConnectorTool._run() | `ServiceConnectorTool._run(tool_id, input_data)` |
| `{paths.tests_unit}/test_approval_operators.py` | Creación | 4 tests operadores approval faltantes | `DynamicWorkflow._check_approval_rule(rule, results)` |
| `{paths.tests_unit}/test_sanitizer.py` | Creación | 11 tests sanitize_output | `sanitize_output(data: Any) -> Any` |

**Patrones a seguir:** `/src/tools/mcp_pool.py`, `/src/tools/service_connector.py`, `/src/flows/dynamic_flow.py`, `/src/mcp/sanitizer.py`

**Estrategia mocking:**
- `MCPPool`: `unittest.mock.patch("time.time")` para control temporización. `MCPPool.reset()` entre tests. `mock_service_client` fixture para DB.
- `ServiceConnectorTool`: instanciar con `org_id="test_org_123"`. `patch("httpx.Client")` para HTTP. `patch("src.tools.service_connector.get_secret")` para Vault.
- `_check_approval_rule`: instanciar `DynamicWorkflow(org_id=sample_org_id)`. Sin mocking DB/crews — método síncrono puro.
- `sanitize_output`: import directo. Función pura sin IO. Sin mocking.

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap test-step
- **Qué automatiza:** Ejecuta tests de un paso específico del plan de certificación con comando único. Resuelve archivos del paso, corre pytest con flags correctos, valida gate (100% pass).
- **Tipo:** CLI (comando Typer en src/cli/)
- **Ubicación:** {paths.cli}/ (D:\Develop\Personal\FluxAgentPro-v2\src\cli\)
- **Cómo se usa:** `fap test-step 1` → corre los 27 tests del Paso 1 con `-v --tb=short`. `fap test-step 1 --cov` → añade cobertura por archivo.
- **Impacto para el usuario final:** Elimina necesidad de recordar rutas de 4 archivos de test y flags de pytest. Un comando = todo el paso.
- **El implementador DEBE usarla** para completar las tareas 1..4 del paso (dogfooding obligatorio).
```

---

## 4️⃣ Decisiones Tecnológicas

1. **No tocar schema DB:** Paso 1 es 100% unitario. Sin migraciones, sin tablas nuevas. Todo mockeado.
2. **Mock `time.time` en lugar de espera real 60s:** Inviable en CI. `unittest.mock.patch` con `autospec=True` por test (no fixture global).
3. **MCPPool.reset() obligatorio entre tests:** Singleton pattern. `_instance` persistente contamina tests si no se limpia. Fixture `autouse=True` o setup explícito.
4. **6 ramas error, 7 tests:** U2.4 (401) y U2.5 (500) comparten mismo `except httpx.HTTPStatusError`. Tests válidos — verifican status code diferente en mensaje.
5. **Non-JSON test valida truncamiento relativo, no valor absoluto:** Límite 500 chars hardcodeado. Test verifica `len(result) <= 500`, no string exacto.
6. **Bug `>=`/`<=`/`==` NO se testea en Paso 1:** Plan explícito: "No se testean aquí. Ver Paso 2". Fix de parser diferido (priorizar `>=` sobre `>` en split).
7. **Fixture `mock_service_client` compartido:** Ya existe en conftest.py (L112). Patchea `src.tools.mcp_pool.get_service_client`. Tests de MCPPool y ServiceConnector lo usan.
8. ⚠️ **`test_3_5_latency.py` eliminado del repo:** Plan v3.1 menciona bug en archivo inexistente. No requiere acción.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Tests usan mock_service_client — sin DB real
✅ [DATA] Sin migraciones nuevas — 0 cambios schema
✅ [CODE] test_mcp_pool_circuit.py existe: 5 tests (U1.1-U1.5) pasan 100%
✅ [CODE] test_service_connector.py existe: 7 tests (U2.1-U2.7) pasan 100%
✅ [CODE] test_approval_operators.py existe: 4 tests (U3.1-U3.4) pasan 100%
✅ [CODE] test_sanitizer.py existe: 11 tests (U4.1-U4.11) pasan 100%
✅ [CODE] MCPPool.reset() en setup/teardown de cada test circuit breaker
✅ [CODE] ServiceConnectorTool instanciado con org_id válido
✅ [CODE] Tests approval usan DynamicWorkflow(org_id=sample_org_id) — instancia directa
✅ [CODE] Tests sanitizer sin mocking — función pura
✅ [BACKEND] No se crean/modifican endpoints
✅ [BACKEND] ServiceConnector error paths retornan strings descriptivos (no exceptions)
✅ [BACKEND] MCPPool circuit breaker lanza MCPConnectionError cuando abierto
✅ [FULLSTACK] pytest exit code 0 — 27/27 tests pasan
✅ [FULLSTACK] Cobertura mcp_pool.py >80%, service_connector.py >70%, sanitizer.py 100%
✅ [DX] Herramienta `fap test-step 1` ejecuta sin errores y reduce comandos manuales
```

**Funcionales:**
- [x] Circuit breaker se abre tras 5 fallos consecutivos
- [x] Circuit breaker permite half-open tras 60s
- [x] ServiceConnector retorna error descriptivo para cada modo de fallo
- [x] Approval rule evalúa `<` correctamente
- [x] Sanitizer redacta 7 tipos de secreto
- [x] Sanitizer maneja estructuras anidadas (dict, list) recursivamente

**Técnicos:**
- [x] `time.time` mockeado — ningún test espera tiempo real
- [x] Singleton MCPPool limpio entre tests
- [x] `fap test-step 1` implementado en CLI y funcional

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---:|---:|---|
| 0 | **DX & Tooling:** `fap test-step` — comando CLI que corre tests de paso específico | Media | 1.5h | Ninguna |
| 1 | Crear `tests/unit/test_mcp_pool_circuit.py` — 5 tests circuit breaker | Media | 1.5h | Tarea 0 |
| 2 | Crear `tests/unit/test_service_connector.py` — 7 tests error paths | Alta | 2h | Tarea 0 |
| 3 | Crear `tests/unit/test_approval_operators.py` — 4 tests approval | Baja | 0.75h | Tarea 0 |
| 4 | Crear `tests/unit/test_sanitizer.py` — 11 tests sanitizer | Baja | 1h | Tarea 0 |
| 5 | Pre-flight: `ruff check --fix src/` (3 lint errors) | Baja | 0.1h | Ninguna |
| 6 | Validar gate: `fap test-step 1` → 27/27 pass, cobertura thresholds | Baja | 0.5h | Tareas 1-4 |
| **TOTAL** | | | **~7.35h** | |

**Orden:** Tarea 5 (lint fix) en paralelo con Tarea 0. Tareas 1-4 en paralelo tras Tarea 0. Tarea 6 depende de 1-4.

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Singleton MCPPool contamina tests | Alta | `_instance` compartido entre tests | `MCPPool.reset()` en setup/teardown de cada test circuit breaker |
| `time.time` mock afecta otros tests | Media | Patch global de `time` puede filtrarse | Usar `patch` como context manager/decorator por test. NO fixture global `autouse` |
| `_run()` requiere instanciar ServiceConnectorTool completo | Media | Herencia de `OrgBaseTool` requiere `org_id` y Pydantic init | Usar `sample_org_id` fixture de conftest.py. Verificar constructor de OrgBaseTool |
| Bug `>=`/`<=`/`==` no detectado en Paso 1 | Alta | Tests Paso 1 NO cubren operadores compuestos | Plan consciente — diferido a Paso 2 con fix de parser |
| `httpx.Client` mock con context manager | Media | `with httpx.Client(...)` pattern requiere mock que soporte `__enter__` | Usar `with patch("httpx.Client") as mock_client: mock_client.return_value.__enter__.return_value = mock_response` |
| Test non-JSON truncamiento cambia si límite 500 se modifica | Baja | Límite hardcodeado en `service_connector.py:140` | Test debe verificar truncamiento (result[:500]), no comparar contra 500 fijo |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Circuit breaker cerrado (4 fallos) → `_is_circuit_open` False | 4 fallos, elapsed 10s | `False` |
| TP-2 | Circuit breaker abierto (5 fallos, <60s) → `_is_circuit_open` True | 5 fallos, elapsed 30s | `True` |
| TP-3 | Circuit breaker half-open (>60s) → `_is_circuit_open` False | 5 fallos, elapsed 61s | `False` |
| TP-4 | `get_tools` con circuito abierto → `MCPConnectionError` inmediato | Circuito abierto | `MCPConnectionError("Circuit breaker abierto...")` |
| TP-5 | ServiceConnector tool no encontrada | tool_id="fake" | `"Error: Tool 'fake' no encontrada"` |
| TP-6 | ServiceConnector HTTP 401 | response.status_code=401 | `"Error HTTP: 401"` |
| TP-7 | ServiceConnector non-JSON response → truncado ≤500 chars | response.text=long_string | `len(result) <= 500`, sin crash |
| TP-8 | Approval `<` with menor → True | `"monto < 1000"`, `"500"` | `True` |
| TP-9 | Approval condición vacía → False | `""`, any results | `False` (sin excepción) |
| TP-10 | Sanitizer Stripe live key → redactado | `"sk_live_abc123"` | `"[REDACTED]"` |
| TP-11 | Sanitizer dict anidado → estructura preservada, secreto redactado | `{"auth": "sk_test_xyz"}` | `{"auth": "[REDACTED]"}` |
| TP-12 | Sanitizer passthrough int/None/bool | `42`, `None`, `True` | `42`, `None`, `True` |

**Comando ejecución:** `fap test-step 1` o `pytest tests/unit/test_mcp_pool_circuit.py tests/unit/test_service_connector.py tests/unit/test_approval_operators.py tests/unit/test_sanitizer.py -v`

---

*Unificado de análisis kimi (4.5), qwen (4.3), ds (4.4). Discrepancias resueltas explícitamente. Tooling DX unificado como `fap test-step`.*
