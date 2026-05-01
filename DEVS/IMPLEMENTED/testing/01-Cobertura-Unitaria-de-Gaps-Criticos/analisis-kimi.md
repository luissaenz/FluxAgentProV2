# 🧠 Análisis Técnico — Paso 1: Cobertura Unitaria de Gaps Críticos

> **Agente:** kimi  
> **Paso:** Paso 1 — Cobertura Unitaria de Gaps Críticos  
> **Fecha:** 2026-05-01  
> **Fuente:** `proyecto-config.json`, `plan.md`, `phase-state.md`, código fuente real  

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|----------|
| 1 | `MCPPool._is_circuit_open` existe | grep en `src/tools/mcp_pool.py` | ✅ | Línea 60-66. Retorna `True` si `failures >= 5` y `elapsed < 60` |
| 2 | `MCPPool._record_failure` existe | grep en `src/tools/mcp_pool.py` | ✅ | Línea 68-69. Incrementa `failures` y actualiza `last_check` |
| 3 | `MCPPool._reset_circuit_breaker` existe | grep en `src/tools/mcp_pool.py` | ✅ | Línea 72-73. Resetea `failures = 0.0` |
| 4 | `MCPPool.get_tools` lanza `MCPConnectionError` con circuito abierto | grep en `src/tools/mcp_pool.py` | ✅ | Línea 101-106. Mensaje incluye `server_name` y tiempo restante |
| 5 | `MCPPool.reset()` existe (para limpieza en tests) | grep en `src/tools/mcp_pool.py` | ✅ | Línea 211-213. Clase `_instance = None` |
| 6 | `MCPConnectionError` es clase propia | grep en `src/tools/mcp_pool.py` | ✅ | Línea 31-32. Hereda de `Exception` |
| 7 | `ServiceConnectorTool._run` existe | grep en `src/tools/service_connector.py` | ✅ | Línea 60-171. Firma: `_run(self, tool_id: str, input_data: dict = None) -> str` |
| 8 | `VaultError` importado de `src.db.vault` | grep en `src/tools/service_connector.py` | ✅ | Línea 22. Clase usada en try/except línea 99 |
| 9 | `get_secret` importado de `src.db.vault` | grep en `src/tools/service_connector.py` | ✅ | Línea 22. Usado en línea 98 |
| 10 | `sanitize_output` importado de `src.mcp.sanitizer` | grep en `src/tools/service_connector.py` | ✅ | Línea 23. Usado en línea 148 |
| 11 | `httpx.HTTPStatusError` maneja código de estado | grep en `src/tools/service_connector.py` | ✅ | Línea 142-143. `f"Error HTTP: {e.response.status_code}"` |
| 12 | `httpx.RequestError` incluye `ConnectError` | grep en `src/tools/service_connector.py` | ✅ | Línea 144-145. `f"Error HTTP: {str(e)}"`. `ConnectError` hereda de `RequestError` |
| 13 | Respuesta no-JSON se trunca a 500 chars | grep en `src/tools/service_connector.py` | ✅ | Línea 139-141. `result = response.text[:500]` |
| 14 | `DynamicWorkflow._check_approval_rule` solo soporta `>` y `<` | grep en `src/flows/dynamic_flow.py` | ✅ | Líneas 137-156. Solo ramas `if ">" in condition` y `elif "<" in condition` |
| 15 | ❌ BUG: `>=` se parsea como `>` → `float("= 50000")` → ValueError silencioso → retorna `False` | Verificación manual | ❌ | `dynamic_flow.py:137`: `if ">" in condition:` hace match con `">="` porque `">"` está presente. `condition.split(">", 1)` produce `["monto ", "= 50000"]`. `float("= 50000".strip())` lanza `ValueError` capturado por `except` externo → retorna `False` |
| 16 | `StepDefinition.approval_threshold` existe pero NO se usa en `_run_crew` | grep en `src/flows/workflow_definition.py` | ✅ | Línea 47: campo definido. Línea 73 vacía en `dynamic_flow.py` — no referenciado |
| 17 | `sanitize_output` maneja `str`, `dict`, `list`, passthrough | grep en `src/mcp/sanitizer.py` | ✅ | Líneas 39-47. `isinstance` checks + default return data |
| 18 | `SECRET_PATTERNS` tiene 7 patrones | grep en `src/mcp/sanitizer.py` | ✅ | Líneas 17-25. sk_live, sk_test, Bearer, Basic, xox[bpsa]-, ghp_, AIza |
| 19 | `conftest.py` tiene fixtures necesarias | grep en `tests/conftest.py` | ✅ | `mock_service_client` (L112), `mock_tenant_client` (L174), `global_llm_mock` (L274), `mock_mcp_pool` (L303), `mock_service_connector` (L319) |
| 20 | `tests/unit/test_mcp_pool_circuit.py` NO existe | glob en tests/ | ❌ | Archivo inexistente. Crear nuevo |
| 21 | `tests/unit/test_service_connector.py` NO existe | glob en tests/ | ❌ | Archivo inexistente. Crear nuevo |
| 22 | `tests/unit/test_approval_operators.py` NO existe | glob en tests/ | ❌ | Archivo inexistente. Crear nuevo |
| 23 | `tests/unit/test_sanitizer.py` NO existe | glob en tests/ | ❌ | Archivo inexistente. Crear nuevo |
| 24 | `tests/integration/test_dynamic_flow.py` existe — cubre `>` (true/false), condición inválida, resultado no numérico | grep en test_dynamic_flow.py | ✅ | Clase `TestApprovalRuleEvaluation`: test_check_approval_rule_greater_than_true, greater_than_false, with_invalid_condition, with_non_numeric_result |
| 25 | `test_dynamic_flow.py` NO cubre `<` standalone, condición vacía, múltiples resultados | Verificación manual | ❌ | Solo 4 tests en `TestApprovalRuleEvaluation`. Faltan U3.1-U3.4 del plan |
| 26 | Tests SE5.13-SE5.16 ya existen y PASAN | pytest ejecución | ✅ | `test_security_guard.py`: líneas 101-126. 4 tests de diagnóstico de vulnerabilidad `__import__` — todos PASAN |
| 27 | Suite actual: 429 tests | `pytest --co` | ✅ | Conteo real. 429 tests recolectados |
| 28 | ❌ `test_full_latency_validation` FALLA — requiere DB real | pytest ejecución | ❌ | `tests/integration/test_3_5_latency.py::TestLatencyValidation::test_full_latency_validation` — integridad 14/15. Tiene `pytestmark = skipif(not SUPABASE_URL)` pero corre si `.env` existe |
| 29 | 3 errores de lint (import ordering) | `ruff check` | ⚠️ | `validate_tools.py:69`, `server.py:7`, `mcp_pool.py:149`. Auto-fixeables con `ruff --fix` |
| 30 | `OrgBaseTool` es clase base de `ServiceConnectorTool` | grep en service_connector.py | ✅ | Línea 24: `from src.tools.base_tool import OrgBaseTool`. Línea 44: hereda |
| 31 | `register_tool` decorador en `ServiceConnectorTool` | grep en service_connector.py | ✅ | Línea 37-43: `@register_tool("service_connector", ...)` |
| 32 | `MCPPool.get_tools` es `async` | grep en mcp_pool.py | ✅ | Línea 77: `async def get_tools(...)` |
| 33 | `DynamicWorkflow._run_crew` es `async` | grep en dynamic_flow.py | ✅ | Línea 66: `async def _run_crew(self)` |
| 34 | `sanitize_output` retorna `Any` | grep en sanitizer.py | ✅ | Línea 28: `def sanitize_output(data: Any) -> Any` |

### Discrepancias encontradas:

1. **❌ BUG en `_check_approval_rule` (línea 137):** `if ">" in condition:` hace match con `>=` antes de evaluarlo correctamente. `float("= 50000")` lanza `ValueError` → retorna `False` silenciosamente. **Resolución propuesta:** Fix parser para priorizar `>=` sobre `>` (verificar `>=` antes de `>`, idem `<=` antes de `<`). Esto es una DECISIÓN del paso 2, no parte del paso 1.

2. **❌ `test_full_latency_validation` falla:** Test de integración que requiere DB real. No bloquea paso 1 (tests unitarios). **Resolución:** Ignorar en paso 1. Documentado en plan como bug conocido (P0).

3. **⚠️ 3 errores de lint auto-fixeables:** Import ordering en `validate_tools.py`, `server.py`, `mcp_pool.py`. **Resolución:** Ejecutar `ruff check --fix src/` como pre-flight del paso 0.

4. **⚠️ `approval_threshold` en `StepDefinition` (workflow_definition.py:47) no se usa en `_run_crew`:** El workflow usa `approval_rules[].condition` (string). **Resolución:** Fuera de scope de paso 1 (testing). Documentar como deuda técnica.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas afectadas (solo lectura en tests)

Paso 1 es **exclusivamente unitario** — no modifica schema. Las tablas referenciadas son mockeadas:

- **`org_mcp_servers`** — Usada por `MCPPool.get_tools()`. Query: `select("*").eq("org_id", org_id).eq("name", server_name).eq("is_active", True).maybe_single()`. Mockeada via `mock_service_client`.
- **`service_tools`** — Usada por `ServiceConnectorTool._run()`. Query: `select("*, service_catalog!inner(id, auth_type, base_url)").eq("id", tool_id).maybe_single()`. Mockeada.
- **`org_service_integrations`** — Usada por `ServiceConnectorTool._run()`. Query: `select("*").eq("org_id", org_id).eq("service_id", service_id).eq("status", "active").maybe_single()`. Mockeada.
- **`domain_events`** — Usada por `ServiceConnectorTool._run()` para audit. Insert best-effort. Mockeada.

### Integridad referencial

- `service_tools.service_id` → `service_catalog.id` (JOIN inner en query).
- `org_service_integrations.service_id` → referencia a `service_catalog`.
- Sin cambios de schema. Tests unitarios no tocan DB real.

### RLS policies

- `org_mcp_servers`: RLS `tenant_isolation_org_mcp_servers` (org_id-based).
- `org_service_integrations`: RLS `org_integration_access` (org_id-based).
- `service_tools`: SIN RLS (tabla global).
- `domain_events`: RLS `tenant_insert/select_domain_events`.

**Todos los tests usan `mock_service_client` (service_role), no hay verificación RLS en tests unitarios.** Esto es correcto — RLS se prueba en integración.

### Índices

Relevantes para mocking:
- `idx_mcp_servers_org` en `org_mcp_servers(org_id)`.
- `idx_service_tools_service` en `service_tools(service_id)`.

### Tipos de datos problemáticos

- `org_mcp_servers.command` (string): usado en `StdioServerParameters`. En tests, mockear como `command` en config dict.
- `service_tools.execution` (JSONB): usado como dict con `url`, `method`, `headers`. Mock como dict plano.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 1.1 Circuit Breaker de MCPPool — `tests/unit/test_mcp_pool_circuit.py`

**Funciones a testear:**

| Función | Firma | Línea |
|---------|-------|-------|
| `_is_circuit_open(self, key: str) -> bool` | Retorna True si `failures >= 5` Y `elapsed < 60s` | 60-66 |
| `_record_failure(self, key: str) -> None` | Incrementa `failures`, actualiza `last_check` | 68-69 |
| `_reset_circuit_breaker(self, key: str) -> None` | Resetea `failures = 0.0` | 72-73 |
| `get_tools(self, org_id, server_name, timeout=30, max_retries=3)` → async list | Lanza `MCPConnectionError` si circuito abierto | 77-191 |
| `reset(cls) -> None` | Limpia singleton | 211-213 |

**Patrones existentes:**
- Singleton pattern: `MCPPool.get()` retorna `_instance` o lo crea.
- `_health` es `defaultdict` con estructura `{"failures": 0.0, "last_check": 0.0}`.
- Tests necesitan `MCPPool.reset()` entre cada test para limpiar singleton.

**Estrategia de mocking:**
- `unittest.mock.patch("time.time")` para controlar temporización sin esperas reales.
- `unittest.mock.patch("src.tools.mcp_pool.get_service_client")` para DB.
- NO mockear `MCPPool` directamente — testear métodos internos (`_is_circuit_open`, `_record_failure`, `_reset_circuit_breaker`) de forma aislada.
- Para `get_tools` con circuito abierto: mockear `_is_circuit_open` o setear `_health` directamente.

**Complejidad ciclomática:** baja. `_is_circuit_open` tiene 2 branches, `_run_crew` del circuit breaker es lineal.

**Imports necesarios:**
```python
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from src.tools.mcp_pool import MCPPool, MCPConnectionError
```

**Decisión de diseño:** Tests U1.1-U1.3 son unitarios puros sobre métodos internos. U1.4-U1.5 son de integración parcial (mock de `get_tools` pero con lógica de circuit breaker real).

### 1.2 ServiceConnector error paths — `tests/unit/test_service_connector.py`

**Función a testear:**

| Función | Firma | Línea |
|---------|-------|-------|
| `ServiceConnectorTool._run(self, tool_id: str, input_data: dict = None) -> str` | 7 ramas de error | 60-171 |

**Ramas de error identificadas en código real:**

| # | Ramas | Código resultado | Línea |
|---|-------|-----------------|-------|
| E1 | Tool no encontrada en `service_tools` | `f"Error: Tool '{tool_id}' no encontrada en service_tools"` | 73 |
| E2 | Servicio no activo en `org_service_integrations` | `f"Error: Servicio '{service_id}' no está activo para esta organización"` | 89-91 |
| E3 | `VaultError` al resolver secreto | `f"Error: {e}"` | 99-100 |
| E4 | `httpx.HTTPStatusError` (401, 500, etc.) | `f"Error HTTP: {e.response.status_code}"` | 142-143 |
| E5 | `httpx.RequestError` (incluye `ConnectError`) | `f"Error HTTP: {str(e)}"` | 144-145 |
| E6 | Respuesta no-JSON (texto plano) | `response.text[:500]` (truncado) | 139-141 |
| OK | Todo funciona → JSON sanitizado | `str(sanitize_output(result))` | 148 |

**Estrategia de mocking:**
- `ServiceConnectorTool` hereda de `OrgBaseTool` que requiere `org_id`.
- Instanciar con `ServiceConnectorTool(org_id="test_org_123")`.
- Mock `get_service_client()` para DB.
- Mock `httpx.Client` para HTTP.
- Mock `src.tools.service_connector.get_secret` para Vault.

**Imports necesarios:**
```python
from unittest.mock import patch, MagicMock
import pytest
import httpx
from src.tools.service_connector import ServiceConnectorTool
from src.db.vault import VaultError
```

**Decisión:** El plan menciona 7 ramas. Código real confirma 6 ramas de error + 1 happy path. U2.7 (respuesta no-JSON) no es un error per se sino un código path alternativo.

### 1.3 Approval operators faltantes — `tests/unit/test_approval_operators.py`

**Función a testear:**

| Función | Firma | Línea |
|---------|-------|-------|
| `DynamicWorkflow._check_approval_rule(self, rule: Dict, results: Dict) -> bool` | Evalúa condición string contra resultados | 128-159 |

**Tests existentes en `tests/integration/test_dynamic_flow.py`:**
- `test_check_approval_rule_greater_than_true` — `monto > 50000` con `100000` → True
- `test_check_approval_rule_greater_than_false` — `monto > 50000` con `30000` → False
- `test_check_approval_rule_with_invalid_condition` — `"invalid syntax >>>"` → False
- `test_check_approval_rule_with_non_numeric_result` — `"monto > 50000"` con `"not a number"` → False

**Tests faltantes (U3.1-U3.4):**
- U3.1: `<` con valor menor → True (`monto < 1000` con `500`)
- U3.2: `<` con valor mayor → False (`monto < 1000` con `5000`)
- U3.3: Condición vacía → False
- U3.4: Múltiples resultados, uno cumple (`total > 100` con `{"a": {"result": "50"}, "b": {"result": "200"}}`)

**BUG CONFIRMADO:** `>=`, `<=`, `==` se rompen silenciosamente. La línea 137 `if ">" in condition:` hace match con `>=`. **Decisión del plan:** No testear operadores que se rompen (no implementados). Marcar como bug conocido. Tests U3.1-U3.4 son para `<` y edge cases, no para `>=`, `<=`, `==`.

**Nota:** `_check_approval_rule` itera sobre `results.values()` donde cada `v` es un dict con clave `"result"`. Para que un valor sea evaluado, `v["result"]` debe ser convertible a `float`.

### 1.4 Sanitizer edge cases — `tests/unit/test_sanitizer.py`

**Función a testear:**

| Función | Firma | Línea |
|---------|-------|-------|
| `sanitize_output(data: Any) -> Any` | Reemplaza patrones de secretos con `[REDACTED]` | 28-50 |

**Patrones SECRET_PATTERNS (7):**

| # | Patrón | Ejemplo |
|---|--------|---------|
| P1 | `sk_live_[a-zA-Z0-9]+` | `sk_live_abc123` |
| P2 | `sk_test_[a-zA-Z0-9]+` | `sk_test_xyz789` |
| P3 | `Bearer [a-zA-Z0-9\-._~+/]+=`* | `Bearer abc123token` |
| P4 | `Basic [a-zA-Z0-9+/]+=`* | `Basic dXNlcjpwYXNz` |
| P5 | `xox[bpsa]-[a-zA-Z0-9\-]+` | `xoxb-1234567890-xxx` |
| P6 | `ghp_[a-zA-Z0-9]+` | `ghp_abc123def456` |
| P7 | `AIza[a-zA-Z0-9\-_]+` | `AIzaSyB1234567890` |

**Estructura del código:**
- Línea 39-42: `isinstance(data, str)` → iterar patrones + `re.sub`.
- Línea 43-44: `isinstance(data, dict)` → recursión sobre values.
- Línea 45-46: `isinstance(data, list)` → recursión sobre items.
- Línea 47: `return data` (passthrough para int, None, bool, etc.).
- Línea 48-50: `except Exception` → `"[ERROR: output no pudo ser procesado]"`.

**Tests plan (U4.1-U4.11):**
- U4.1-U4.7: Cada patrón individual → `[REDACTED]`.
- U4.8: Dict anidado con secreto → recursión, estructura preservada.
- U4.9: Lista con secreto → segundo elemento redactado.
- U4.10: Passthrough para `42`, `None`, `True`.
- U4.11: String sin secretos → sin cambio.

**Import:**
```python
from src.mcp.sanitizer import sanitize_output, SECRET_PATTERNS
```

**Complejidad baja.** 50 líneas. No hay mocking requerido — función pura.

### Modularidad y cohesión

- Los 4 archivos de test son independientes entre sí. Sin acoplamiento.
- `test_mcp_pool_circuit.py` usa `MCPPool` directamente (cohesión alta).
- `test_service_connector.py` usa `ServiceConnectorTool` + mocks de DB/HTTP (cohesión media-alta).
- `test_approval_operators.py` usa `DynamicWorkflow._check_approval_rule` (cohesión alta).
- `test_sanitizer.py` usa `sanitize_output` directamente (cohesión alta, función pura).

### Imports y dependencias

| Archivo test | Depende de | Mocks necesarios |
|-------------|-----------|-----------------|
| `test_mcp_pool_circuit.py` | `MCPPool`, `MCPConnectionError` | `time.time`, `get_service_client`, `MCPServerAdapter` |
| `test_service_connector.py` | `ServiceConnectorTool`, `VaultError` | `get_service_client`, `httpx.Client`, `get_secret` |
| `test_approval_operators.py` | `DynamicWorkflow` | Ninguno — método síncrono puro |
| `test_sanitizer.py` | `sanitize_output`, `SECRET_PATTERNS` | Ninguno — función pura |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs/Endpoints

Paso 1 es **exclusivamente unitario**. No crea ni modifica endpoints. Implicaciones indirectas:

- `ServiceConnectorTool` se registra como tool tipo C vía `@register_tool("service_connector")`. Los tests unitarios verifican su lógica interna sin tocar la API.
- `MCPPool.get_tools()` se consume en `AgentFactory.resolve_tools()`. Un circuit breaker que no funciona correctamente causaría `MCPConnectionError` en producción cuando no debería.
- `DynamicWorkflow._check_approval_rule()` afecta el flujo de aprobación HITL (human-in-the-loop). Un bug en `>=`/`<=`/`==` causaría aprobaciones que no se disparan cuando deberían.

### Middleware

- `ServiceConnectorTool._run()` usa `self.org_id` (de `OrgBaseTool`). En tests, se inyecta vía constructor: `ServiceConnectorTool(org_id="test_org_123")`.
- No hay middleware de auth en tests unitarios.

### Flujos de datos

**MCPPool circuit breaker:**

```
Request → get_tools()
  → _is_circuit_open(key)?
    → YES: raise MCPConnectionError (inmediato, sin intentar conexión)
    → NO: intentar conexión con retry (tenacity)
      → Success: _reset_circuit_breaker(key), return tools
      → Failure: _record_failure(key), raise MCPConnectionError
```

**ServiceConnector error paths:**

```
_run(tool_id, input_data)
  → DB query service_tools → no match → "Error: Tool no encontrada"
  → DB query org_service_integrations → no active → "Error: Servicio no activo"
  → Vault get_secret → VaultError → "Error: {e}"
  → httpx.Client.request
    → HTTPStatusError → "Error HTTP: {status_code}"
    → RequestError → "Error HTTP: {str(e)}"
    → Success: response.json() OR response.text[:500]
  → sanitize_output(result)
  → Audit to domain_events (best-effort)
  → return str(sanitized)
```

**Approval rule evaluation:**

```
_check_approval_rule(rule, results)
  → condition = rule.get("condition", "")
  → > in condition?
    → parse threshold, iterate results
    → any result > threshold? → True
  → < in condition?
    → parse threshold, iterate results
    → any result < threshold? → True
  → else/exception → False
```

### Error handling

| Component | Error → Respuesta | Test cubierto? |
|-----------|------------------|---------------|
| MCPPool | Circuit open → `MCPConnectionError("Circuit breaker abierto...")` | U1.4 (nuevo) |
| MCPPool | Timeout → `MCPConnectionError("Timeout conectando...")` | No en paso 1 (integración) |
| MCPPool | General error → `MCPConnectionError("Error conectando...")` | No en paso 1 (integración) |
| ServiceConnector | Tool no encontrada → string error | U2.1 (nuevo) |
| ServiceConnector | Servicio inactivo → string error | U2.2 (nuevo) |
| ServiceConnector | VaultError → string error | U2.3 (nuevo) |
| ServiceConnector | HTTP 401/500 → string error | U2.4/U2.5 (nuevo) |
| ServiceConnector | ConnectError → string error | U2.6 (nuevo) |
| ServiceConnector | Respuesta no-JSON → truncado 500 chars | U2.7 (nuevo) |
| Sanitizer | Excepción → `"[ERROR: output no pudo ser procesado]"` | U4 (nuevo) |

### Contratos entre servicios

- `ServiceConnectorTool` → `get_service_client()`: Retorna Supabase client con service_role (bypass RLS).
- `ServiceConnectorTool` → `get_secret()`: Retorna secreto del Vault. Lanza `VaultError`.
- `ServiceConnectorTool` → `sanitize_output()`: Retorna dato sanitizado.
- `MCPPool` → `get_service_client()`: Para obtener config de `org_mcp_servers`.
- `MCPPool` → `get_secret_async()`: Para resolver `API_TOKEN` del Vault.
- `DynamicWorkflow` → `BaseCrew`: Crea crew con `org_id` y `role`.

### Cuellos de botella

- `ServiceConnectorTool._run()` es síncrono. Bloquea el event loop si el HTTP request es lento. No es problema para tests unitarios (mockeados). Documentar para paso futuro.
- `MCPPool.get_tools()` es async. Tests unitarios de circuit breaker pueden ser síncronos (métodos `_is_circuit_open`, `_record_failure`, `_reset_circuit_breaker`). Método `get_tools` requiere `asyncio` o `pytest.mark.asyncio`.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: Tests Unitarios

```
Developer → pytest tests/unit/test_mcp_pool_circuit.py → Tests pasan
Developer → pytest tests/unit/test_service_connector.py → Tests pasan
Developer → pytest tests/unit/test_approval_operators.py → Tests pasan
Developer → pytest tests/unit/test_sanitizer.py → Tests pasan
```

### Coherencia end-to-end

- Los 4 archivos de test cubren código que YA EXISTE en producción. No hay feature nueva — solo cobertura de gaps.
- `mcp_pool.py` tiene lógica de circuit breaker sin tests directos. Los tests de `test_mcp_exceptions.py` cubren excepciones MCP protocol, NO el circuit breaker.
- `service_connector.py` no tiene tests. Los 7 error paths no están verificados.
- `sanitizer.py` no tiene tests. 50 líneas sin cobertura.
- `_check_approval_rule` tiene 4 tests de integración pero faltan `<`, condición vacía, y múltiples resultados.

### Alineación con el plan

- ✅ Paso 1 es coherente con el código existente.
- ✅ Todos los métodos a testear existen con las firmas documentadas.
- ✅ Las fixtures de `conftest.py` son suficientes para los tests planificados.
- ⚠️ Bug de `>=`/`<=`/`==` confirmado. Plan indica: NO testear operadores que se rompen. Proponer fix en paso 2.

### Gaps identificados

1. **`ServiceConnectorTool` requiere `org_id` en constructor** — `OrgBaseTool` lo necesita. Tests deben pasar `org_id` al instanciar.
2. **`MCPPool` es singleton** — Tests deben llamar `MCPPool.reset()` en setup/teardown para evitar estado compartido.
3. **`_check_approval_rule` itera sobre `results.values()`** donde cada `v` debe ser `{"result": str_value}`. Los tests de U3 necesitan mockear esta estructura.
4. **`httpx.Client` se usa como context manager** — Mock debe respetar `with httpx.Client(...)` pattern.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap test-step
- **Qué automatiza:** Ejecutar un paso específico del plan de certificación con el comando correcto, reportar resultados y validar gates.
- **Tipo:** CLI (comando Typer en src/cli/)
- **Cómo se usa:** `fap test-step 1` → ejecuta `pytest tests/unit/test_mcp_pool_circuit.py tests/unit/test_service_connector.py tests/unit/test_approval_operators.py tests/unit/test_sanitizer.py -v`
- **Impacto para el usuario final:** Elimina la necesidad de recordar qué archivos corresponden a cada paso. Valida automáticamente el gate (100% pass). Reporta cobertura.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

Lista binaria verificable:

```
✅ [DATA] Tests usan `mock_service_client` para todas las queries DB — sin tocar DB real
✅ [DATA] Tests de ServiceConnector verifican queries correctas a `service_tools`, `org_service_integrations`, `domain_events`
✅ [DATA] No se requiere migración nueva — paso 1 es solo tests unitarios
✅ [CODE] Archivo `tests/unit/test_mcp_pool_circuit.py` existe con ≥5 tests (U1.1-U1.5)
✅ [CODE] Archivo `tests/unit/test_service_connector.py` existe con ≥7 tests (U2.1-U2.7)
✅ [CODE] Archivo `tests/unit/test_approval_operators.py` existe con ≥4 tests (U3.1-U3.4)
✅ [CODE] Archivo `tests/unit/test_sanitizer.py` existe con ≥11 tests (U4.1-U4.11)
✅ [CODE] MCPPool.reset() llamado en setup de cada test de circuit breaker
✅ [CODE] ServiceConnectorTool instanciado con org_id válido en cada test
✅ [CODE] Aprobación `_check_approval_rule` cubre operador `<` (U3.1, U3.2)
✅ [CODE] Aprobación cubre condición vacía (U3.3)
✅ [CODE] Aprobación cubre múltiples resultados (U3.4)
✅ [BACKEND] ServiceConnector error paths responden con strings descriptivos (no exceptions no capturadas)
✅ [BACKEND] MCPPool circuit breaker lanza MCPConnectionError cuando está abierto
✅ [BACKEND] ServiceConnector sanitiza output antes de retornar
✅ [FULLSTACK] Todos los 27 tests de paso 1 pasan: pytest exit code 0
✅ [FULLSTACK] Cobertura mcp_pool.py >80%, service_connector.py >70%, sanitizer.py 100%
✅ [DX] Herramienta `fap test-step` ejecuta paso específico con comando correcto y valida gate
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| `MCPPool` singleton persistse entre tests | Alta | `_instance` es de clase, no de instancia | `MCPPool.reset()` en fixture `autouse=True` o en setup de cada test |
| `ServiceConnectorTool._run` requiere `OrgBaseTool` con `org_id` | Media | Herencia de `OrgBaseTool`很可能 necesita config adicional | Verificar constructor de `OrgBaseTool` e instanciar con kwargs correctos |
| Bug `>=`/`<=`/`==` en approval rules confunde implementadores | Media | `_check_approval_rule` parsea `>=` como `>` + `= 50000` | Documentar en tests como Known Bug. Fix en paso 2 |
| `test_3_5_latency.py` falla en CI si .env existe | Baja | Test de integración requiere DB real | `skipif(not SUPABASE_URL)` ya existe. Agregar `@pytest.mark.integration` |
| Lint errors bloquean gate P0.3 | Baja | 3 errores de import ordering | Ejecutar `ruff check --fix src/` antes de paso 0 |
| `conftest.py` patches múltiples puntos de importación | Baja | Si paths cambian, fixtures se rompen sin error claro | Revisar patch_points en `mock_service_client` fixture |
| Tests de circuit breaker async vs sync | Media | `_is_circuit_open` es sync, `get_tools` es async | Tests U1.1-U1.3 son sync. U1.4-U1.5 necesitan `pytest.mark.asyncio` |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|------|----------|-------------|-------------|-------------|
| 0 | **DX & Tooling:** `fap test-step` CLI command | FULLSTACK/DX | Media | 1h | Ninguna |
| 1 | Crear `tests/unit/test_mcp_pool_circuit.py` (5 tests) | CODE | Media | 1.5h | Tarea 0 |
| 2 | Crear `tests/unit/test_service_connector.py` (7 tests) | CODE | Alta | 2h | Tarea 0 |
| 3 | Crear `tests/unit/test_approval_operators.py` (4 tests) | CODE | Baja | 0.5h | Tarea 0 |
| 4 | Crear `tests/unit/test_sanitizer.py` (11 tests) | CODE | Baja | 1h | Tarea 0 |
| 5 | Verificar gate: 100% pass, cobertura mcp_pool >80%, service_connector >70%, sanitizer 100% | FULLSTACK | Baja | 0.5h | Tareas 1-4 |
| 6 | Ejecutar `ruff check --fix src/` para limpiar 3 lint errors | CODE | Baja | 0.1h | Ninguna |

**Tiempo total estimado:** 6.5 horas

**Orden de ejecución:** Tarea 6 (lint fix) puede ejecutarse en paralelo con Tarea 0. Tareas 1-4 pueden ejecutarse en paralelo entre sí después de Tarea 0. Tarea 5 depende de 1-4.

---

## 🔮 Roadmap (NO implementar ahora)

- **Optimización:** `ServiceConnectorTool._run()` es síncrono — considerar versión async para no bloquear event loop en producción.
- **Fix `_check_approval_rule`:** Parser debe verificar `>=` antes de `>`, `<=` antes de `<`. Agregar soporte `==` como operador de comparación. Priorizar en paso 2.
- **`StepDefinition.approval_threshold`:** Campo existe en schema pero no se usa en `_run_crew`. Considerar migración o eliminación.
- **`fap test-step --coverage`:** Extender CLI para reportar cobertura por archivo después de ejecutar tests.
- **Test de integración real para MCPPool:** Los tests unitarios del circuit breaker no prueban la reconexión real. Agregar test de integración con mock de `MCPServerAdapter`.
- **Sanitizer:** Agregar patrones adicionales (AWS keys, private keys PEM). Considerar sanitización de passwords en URLs (`user:pass@host`).