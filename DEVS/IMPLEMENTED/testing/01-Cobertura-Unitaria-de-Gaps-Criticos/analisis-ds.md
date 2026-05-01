# Análisis Técnico — Paso 1: Cobertura Unitaria de Gaps Críticos

**Agente:** ds
**Paso:** 1 (Cobertura Unitaria de Gaps Críticos)
**Fecha:** 2026-05-01
**Fuente:** plan.md §Paso 1 (v3.1)

---

## 0️⃣ Verificación contra Código Fuente

### Elementos Verificados

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `MCPPool._is_circuit_open()` existe | grep `src/tools/mcp_pool.py` | ✅ | línea 60-66 |
| 2 | `MCPPool._record_failure()` existe | grep `src/tools/mcp_pool.py` | ✅ | línea 68-70 |
| 3 | `MCPPool._reset_circuit_breaker()` existe | grep `src/tools/mcp_pool.py` | ✅ | línea 72-73 |
| 4 | `MCPPool.get_tools()` firma real: `(org_id, server_name, timeout=30, max_retries=3)` | leer `src/tools/mcp_pool.py` | ✅ | línea 77-83 |
| 5 | Circuit breaker umbral: `health["failures"] < 5` = cerrado | leer `src/tools/mcp_pool.py:63` | ✅ | `< 5` retorna False |
| 6 | Circuit breaker half-open tras 60s: `elapsed < 60` | leer `src/tools/mcp_pool.py:66` | ✅ | `elapsed >= 60` retorna False |
| 7 | `MCPPool.reset()` existe | grep `src/tools/mcp_pool.py` | ✅ | línea 211-213 |
| 8 | `ServiceConnectorTool._run()` existe | grep `src/tools/service_connector.py` | ✅ | línea 60-171 |
| 9 | `_run()` tool_id inexistente retorna `"no encontrada"` | leer `src/tools/service_connector.py:72-73` | ✅ | |
| 10 | `_run()` servicio inactivo retorna `"no está activo"` | leer `src/tools/service_connector.py:88-91` | ✅ | |
| 11 | `_run()` VaultError capturado | leer `src/tools/service_connector.py:99-100` | ✅ | `except VaultError as e` |
| 12 | `_run()` HTTPStatusError capturado | leer `src/tools/service_connector.py:142-143` | ✅ | incluye status code |
| 13 | `_run()` RequestError capturado | leer `src/tools/service_connector.py:144-145` | ✅ | |
| 14 | `_run()` non-JSON response truncado a 500 chars | leer `src/tools/service_connector.py:139-141` | ✅ | `response.text[:500]` |
| 15 | `DynamicWorkflow._check_approval_rule()` existe | grep `src/flows/dynamic_flow.py` | ✅ | línea 128-159 |
| 16 | `>` operator soportado | leer `src/flows/dynamic_flow.py:137-146` | ✅ | |
| 17 | `<` operator soportado | leer `src/flows/dynamic_flow.py:147-156` | ✅ | |
| 18 | `>=`, `<=`, `==` se rompen silenciosamente | leer `src/flows/dynamic_flow.py:137` | ❌ | `">" in condition` matchea `>=` → ValueError silencioso |
| 19 | `sanitize_output()` existe | grep `src/mcp/sanitizer.py` | ✅ | línea 28-50 |
| 20 | 7 SECRET_PATTERNS definidos | leer `src/mcp/sanitizer.py:17-25` | ✅ | `sk_live_`, `sk_test_`, `Bearer`, `Basic`, Slack, GitHub, Google |
| 21 | `sanitize_output()` recursivo en dict | leer `src/mcp/sanitizer.py:43-44` | ✅ | `{k: sanitize_output(v) ...}` |
| 22 | `sanitize_output()` recursivo en list | leer `src/mcp/sanitizer.py:45-46` | ✅ | |
| 23 | `sanitize_output()` passthrough para primitivos | leer `src/mcp/sanitizer.py:47` | ✅ | |
| 24 | `test_mcp_pool_circuit.py` NO existe | glob | ✅ | archivo nuevo |
| 25 | `test_service_connector.py` NO existe | glob | ✅ | archivo nuevo |
| 26 | `test_approval_operators.py` NO existe | glob | ✅ | archivo nuevo |
| 27 | `test_sanitizer.py` NO existe | glob | ✅ | archivo nuevo |

**Total verificados:** 27 (umbral para 4 archivos nuevos: ≥12) ✅

### Discrepancias

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | Plan dice "7 ramas de error" en `_run()`. Código tiene 6 paths únicos: HTTP 401 y 500 comparten mismo `except httpx.HTTPStatusError`. | Tests U2.4/U2.5 son válidos: mismo branch, status code diferente. No afecta cobertura. |
| D2 | `>=`, `<=`, `==` en `_check_approval_rule` se rompen silenciosamente. `">" in condition` → matchea `>=` → `float("= 50000")` → ValueError → retorna False. | Bug conocido. Plan §2.3 documenta. Tests del paso 1 no cubren estos operadores (plan dice "No se testean aquí. Ver Paso 2"). |
| D3 | `MCPPool._health` usa `defaultdict(lambda: {"failures": 0.0, ...})` — failure count es float. | Sin impacto funcional. `0.0 < 5` funciona igual. |
| D4 | `StepDefinition.approval_threshold` existe en modelo (workflow_definition.py:47) pero NO se usa en `_run_crew()`. | Plan documenta: "fuera de scope de testing puro". |

---

## 1️⃣ Análisis de Datos

**Schema afectado:** Ninguno. Paso 1 es exclusivamente unit testing — no crea tablas, migraciones ni modifica data.

**Tablas referenciadas indirectamente (por código bajo test):**
- `org_mcp_servers`: usada por `MCPPool.get_tools()` (mcp_pool.py:124-132). Confirmada en `supabase/migrations/005_org_mcp_servers.sql`.
- `service_tools`: usada por `ServiceConnectorTool._run()` (service_connector.py:65-71). Confirmada en `024_service_catalog.sql`.
- `org_service_integrations`: usada por `_run()` (service_connector.py:79-87).
- `domain_events`: audit trail en `_run()` (service_connector.py:152).
- `skill_catalog`: usada por `ToolRegistry._load_from_db()` (registry.py:130-137).

**RLS:** No afecta tests unitarios (todo mockeado via `mock_service_client`).

**Impacto en datos existentes:** Ninguno.

---

## 2️⃣ Análisis de Código

### Funciones/clases bajo test

#### MCPPool (`src/tools/mcp_pool.py`)
| Función | Línea | Firma | Responsabilidad |
|---|---|---|---|
| `_is_circuit_open` | 60 | `(key: str) -> bool` | Retorna True si ≥5 fallos y <60s desde último fallo |
| `_record_failure` | 68 | `(key: str) -> None` | Incrementa contador de fallos y timestamp |
| `_reset_circuit_breaker` | 72 | `(key: str) -> None` | Resetear contador a 0 |
| `get_tools` | 77 | `(org_id, server_name, timeout=30, max_retries=3) -> list` | Obtener tools MCP con circuit breaker + retry |
| `reset` | 211 | `() -> None` classmethod | Resetear singleton (útil en tests) |

**Patrón:** Singleton + defaultdict para health tracking. Health dict structure: `{"failures": float, "last_check": float}`.

**Mockeo requerido para tests:**
- `time.time` → `unittest.mock.patch` para controlar temporización (evitar espera real de 60s)
- `MCPPool.reset()` entre tests para limpiar singleton state
- `get_service_client` → fixture `mock_service_client` (ya en conftest.py)
- Opcional: `get_secret_async` si se prueba `get_tools` path completo

#### ServiceConnectorTool (`src/tools/service_connector.py`)
| Función | Línea | Firma | Responsabilidad |
|---|---|---|---|
| `_run` | 60 | `(tool_id: str, input_data: dict = None) -> str` | Ejecuta integración HTTP del catálogo |

**6 paths de error verificados:**
1. tool_id inexistente → `"no encontrada"` (l:72-73)
2. servicio inactivo → `"no está activo"` (l:88-91)
3. VaultError en `get_secret` → `"Error: {str(e)}"` (l:99-100)
4. HTTP 4xx/5xx → `"Error HTTP: {status_code}"` (l:142-143)
5. httpx.RequestError (ConnectError) → `"Error HTTP: {str(e)}"` (l:144-145)
6. Non-JSON response → `response.text[:500]` sin crash (l:139-141)

**Mockeo requerido:**
- `mock_service_client` fixture para DB
- `patch("httpx.Client")` para HTTP calls
- `patch("src.tools.service_connector.get_secret")` para Vault

#### `_check_approval_rule` (`src/flows/dynamic_flow.py`)
| Función | Línea | Firma | Responsabilidad |
|---|---|---|---|
| `_check_approval_rule` | 128 | `(rule: dict, results: dict) -> bool` | Evaluar condition string contra resultados |

**3 tests faltantes** (U3.1-U3.4):
- `<` con valor menor → True: `_check_approval_rule({"condition": "monto < 1000"}, {"step_1": {"result": "500"}})` → True
- `<` con valor mayor → False: `_check_approval_rule({"condition": "monto < 1000"}, {"step_1": {"result": "5000"}})` → False
- Condición vacía → False: `_check_approval_rule({"condition": ""}, ...)` → False (sin excepción)
- Múltiples resultados, uno cumple: `_check_approval_rule({"condition": "total > 100"}, {"a": {"result": "50"}, "b": {"result": "200"}})` → True

**Patrón:** `_check_approval_rule` itera `results.values()`, checkea cada `result` key. Si any match → True.
**Bug conocido:** `>=`/`<=`/`==` se rompen (plan §2.3). Tests U3.1-U3.4 usan solo `<` y `>`.

#### Sanitizer (`src/mcp/sanitizer.py`)
| Función | Línea | Firma | Responsabilidad |
|---|---|---|---|
| `sanitize_output` | 28 | `(data: Any) -> Any` | Redactar secretos en output vía regex |

**7 patrones + 4 tipos de data:**
- Strings: 7 regex secuenciales (líneas 17-25)
- Dicts: recursión en valores (línea 43-44)
- Lists: recursión en items (línea 45-46)
- Primitives: passthrough (línea 47)

**Mockeo:** Ninguno necesario — función pura, sin IO.

### Moduralidad y Calidad

- **Duplicación:** Cero. No hay tests existentes para ninguna de estas 4 unidades.
- **Cohesión:** Alta. Cada archivo de test cubre UNA unidad específica.
- **Acoplamiento:** Bajo. Tests usan mocks de conftest.py + unittest.mock.patch.
- **Convenciones:** Nombres snake_case, imports absolutos `src.xxx.xxx`, pytest fixtures de conftest.py.

---

## 3️⃣ Análisis de Backend

**Endpoints afectados:** Ninguno. Paso 1 es unit testing puro — no crea ni modifica APIs.

**Middleware:** No aplica.

**Errores/Excepciones relevantes:**
- `MCPConnectionError`: excepción propia de MCPPool (mcp_pool.py:31-32)
- `VaultError`: capturada en service_connector.py:99
- `httpx.HTTPStatusError`: capturada en service_connector.py:142
- `httpx.RequestError`: capturada en service_connector.py:144

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo End-to-End
```
Plan (Paso 1) → Tests Unitarios → pytest → Coverage Report
    ├── test_mcp_pool_circuit.py → MCPPool circuit breaker
    ├── test_service_connector.py → ServiceConnectorTool error paths
    ├── test_approval_operators.py → _check_approval_rule
    └── test_sanitizer.py → sanitize_output
```

### Coherencia
- Plan propone +25 tests (5+7+4+9). Código real soporta exactamente esos escenarios.
- Los 4 archivos de test NO existen → creación limpia.
- conftest.py ya tiene `mock_service_client`, `global_llm_mock`, `mock_mcp_pool`, `mock_service_connector` — fixtures listas.

### Gaps y Ambigüedades

| Gap | Descripción | Resolución |
|---|---|---|
| G1 | `mock_service_client` fixture patcha `src.tools.mcp_pool.get_service_client` (conftest.py:122). Tests de MCPPool pueden usarla directamente. | No requiere acción — fixture lista. |
| G2 | Plan U1.3 requiere `patch("time.time")`. Conftest.py no tiene fixture para esto. | Crear fixture local en `test_mcp_pool_circuit.py` o en conftest.py. Recomiendo local. |
| G3 | `_check_approval_rule` usa `float(threshold.strip())` — si threshold tiene caracteres no-numéricos, ValueError → False silencioso. Tests deben confirmar este comportamiento. | Documentado en plan como esperado. |
| G4 | ServiceConnector test U2.6: plan menciona `"Error HTTP: "` para ConnectError. Código: `f"Error HTTP: {str(e)}"` que incluye mensaje descriptivo. El test debe validar `"Error HTTP:" in result` no equality exacta. | Usar `assert "Error HTTP:" in result` en test. |

### DX & Tooling

```
### Herramienta Propuesta: fap test-paso1
- **Qué automatiza:** Ejecuta SOLO los 4 archivos de test del Paso 1, con verbose output y reporte de cobertura específico.
- **Tipo:** Comando CLI (extensión de `fap`)
- **Cómo se usa:** `fap test paso1` o `fap test --step 1`
- **Impacto:** Elimina necesidad de escribir `pytest tests/unit/test_mcp_pool_circuit.py tests/unit/test_service_connector.py tests/unit/test_approval_operators.py tests/unit/test_sanitizer.py -v --cov=src.tools.mcp_pool --cov=src.tools.service_connector --cov=src.mcp.sanitizer --cov=src.flows.dynamic_flow` manualmente.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No se requieren cambios de schema (unit tests puros)
✅ [CODE] test_mcp_pool_circuit.py: 5 tests (U1.1-U1.5) pasan 100%
✅ [CODE] test_service_connector.py: 7 tests (U2.1-U2.7) pasan 100%
✅ [CODE] test_approval_operators.py: 4 tests (U3.1-U3.4) pasan 100%
✅ [CODE] test_sanitizer.py: 11 tests (U4.1-U4.11) pasan 100%
✅ [CODE] Tests usan conftest.py fixtures (mock_service_client, global_llm_mock) — sin mockeo manual repetido
✅ [CODE] U1.3 usa patch("time.time") — sin espera real de 60s
✅ [BACKEND] Sin endpoints creados/modificados (paso unitario)
✅ [FULLSTACK] Cobertura mcp_pool.py >80%, service_connector.py >70%, sanitizer.py 100%
✅ [DX] Herramienta `fap test paso1` creada y funcional
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: MCPPool singleton state contaminado entre tests | Media | `MCPPool._instance` persiste entre tests si no se resetea | Llamar `MCPPool.reset()` en setup/teardown de cada test |
| R2: `patch("time.time")` efecto global | Media | Mock de `time.time` en un test puede contaminar otros | Usar `autospec=True` y restaurar en teardown, o fixture autouse limitada |
| R3: Bug `>=`/`<=`/`==` no cubierto en Paso 1 | Alta | Tests U3.1-U3.4 no detectan el bug de operadores compuestos | Plan consciente — diferido a Paso 2 con decisión de implementación |
| R4: ServiceConnector non-JSON test no captura cambio de límite | Baja | Límite 500 chars hardcodeado. Si cambia, test no falla | Test debería verificar truncamiento relativo, no valor absoluto |
| R5: Sanitizer regex overlap | Baja | `Bearer` y `Basic` patterns pueden solaparse con strings normales | Tests usan strings aislados — no hay problema |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX Tooling:** `fap test paso1` — comando CLI para ejecutar solo tests del paso | FULLSTACK/DX | Baja | 30min | Ninguna |
| 1 | Crear `tests/unit/test_mcp_pool_circuit.py` — 5 tests circuit breaker | CODE | Media | 45min | Tarea 0 |
| 2 | Crear `tests/unit/test_service_connector.py` — 7 tests error paths | CODE | Alta | 1h | Tarea 0 |
| 3 | Crear `tests/unit/test_approval_operators.py` — 4 tests operadores | CODE | Baja | 30min | Tarea 0 |
| 4 | Crear `tests/unit/test_sanitizer.py` — 11 tests sanitizer | CODE | Media | 45min | Tarea 0 |
| 5 | Validar: `pytest tests/unit/test_mcp_pool_circuit.py tests/unit/test_service_connector.py tests/unit/test_approval_operators.py tests/unit/test_sanitizer.py -v` | FULLSTACK | Baja | 15min | Tareas 1-4 |

**Tiempo total estimado:** 3.75 horas

**Orden de implementación:** Tarea 0 → (Tareas 1-4 en paralelo) → Tarea 5

---

## 🔮 Roadmap

- **Paso 2 Planificado:** Integración — MCP resilience (I2.1-I2.3), handover (I3.1-I3.3), feature `>=`/`<=`/`==` (I4.1-I4.3 condicionales)
- **Mejora futura:** Mover `_check_approval_rule` a función separada para testabilidad sin instanciar DynamicWorkflow completo
- **Dependencia identificada:** Paso 2 necesita los tests del Paso 1 funcionando (son gate)
- **Bug conocido para release:** `>=`/`<=`/`==` break silently. No fix planificado en esta fase — documentar como known issue si no se implementa.
