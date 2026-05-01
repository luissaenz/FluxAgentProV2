# Análisis Técnico — Paso 1: Cobertura Unitaria de Gaps Críticos

**Agente:** qwen
**Paso:** 1 (incluye sub-pasos 1.1-1.4)
**Fecha:** 2026-05-01

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `MCPPool._is_circuit_open` existe | `src/tools/mcp_pool.py:61` | ✅ | Línea 61-66 |
| 2 | `MCPPool._record_failure` existe | `src/tools/mcp_pool.py:68` | ✅ | Línea 68-70 |
| 3 | `MCPPool._reset_circuit_breaker` existe | `src/tools/mcp_pool.py:72` | ✅ | Línea 72-73 |
| 4 | `MCPPool.get_tools` existe | `src/tools/mcp_pool.py:77` | ✅ | Línea 77-191 |
| 5 | `MCPPool.reset` existe | `src/tools/mcp_pool.py:211` | ✅ | Línea 211-213 |
| 6 | `MCPConnectionError` existe | `src/tools/mcp_pool.py:31` | ✅ | Línea 31-33 |
| 7 | `ServiceConnectorTool._run` existe | `src/tools/service_connector.py:60` | ✅ | Línea 60-170 |
| 8 | `ServiceConnectorTool` usa `OrgBaseTool` | `src/tools/service_connector.py:44` | ✅ | Línea 44 |
| 9 | `ServiceConnectorTool` usa `@register_tool` | `src/tools/service_connector.py:37` | ✅ | Línea 37-43 |
| 10 | `DynamicWorkflow._check_approval_rule` existe | `src/flows/dynamic_flow.py:128` | ✅ | Línea 128-159 |
| 11 | `sanitize_output` existe | `src/mcp/sanitizer.py:28` | ✅ | Línea 28-50 |
| 12 | `SECRET_PATTERNS` tiene 7 patrones | `src/mcp/sanitizer.py:17-25` | ✅ | 7 patrones confirmados |
| 13 | `test_mcp_exceptions.py` existe | `tests/unit/test_mcp_exceptions.py` | ✅ | 4 tests, NO cubre circuit breaker |
| 14 | `test_security_guard.py` existe | `tests/unit/test_security_guard.py` | ✅ | 14 tests existentes + SE5.13-16 |
| 15 | `test_dynamic_flow.py` existe | `tests/integration/test_dynamic_flow.py` | ✅ | Cubre `>` approval, NO `<` standalone |
| 16 | `conftest.py` fixtures | `tests/conftest.py` | ✅ | `sample_org_id`, `mock_service_client`, `mock_tenant_client`, `global_llm_mock`, `mock_mcp_pool` |
| 17 | `test_mcp_pool_circuit.py` NO existe | glob `**/test_mcp_pool*` | ✅ Confirmado | Archivo a crear |
| 18 | `test_service_connector.py` NO existe | glob `**/test_service_connector*` | ✅ Confirmado | Archivo a crear |
| 19 | `test_sanitizer.py` NO existe | glob `**/test_sanitizer*` | ✅ Confirmado | Archivo a crear |
| 20 | `test_approval_operators.py` NO existe | glob `**/test_approval*` | ✅ Confirmado | Archivo a crear |
| 21 | `tests/stress/` NO existe | glob `tests/stress/**` | ✅ Confirmado | Directorio no existe (Paso 4) |
| 22 | `time` importado en `mcp_pool.py` | `src/tools/mcp_pool.py:19` | ✅ | `import time` — mockeable |
| 23 | `httpx` importado en `service_connector.py` | `src/tools/service_connector.py:17` | ✅ | `import httpx` |
| 24 | `VaultError` importado en `service_connector.py` | `src/tools/service_connector.py:22` | ✅ | `from src.db.vault import VaultError` |
| 25 | `OrgBaseTool` existe | `src/tools/base_tool.py:18` | ✅ | Clase base con `org_id` |

**Discrepancias encontradas:**

1. **DISCREPANCIA D1:** Plan dice `test_3_5_latency.py` está en `tests/` raíz. **NO EXISTE.** Verificado con glob y read directo. El plan v3.1 menciona bug conocido en este archivo pero el archivo fue eliminado o renombrado. → Resolución: Eliminar referencia del gate de Paso 0 o marcar como ya corregido.

2. **DISCREPANCIA D2:** Plan dice `service_connector.py:_run` tiene 7 ramas de error. Código real tiene 6 ramas retornando string error: (1) tool no encontrada L72, (2) servicio no activo L88, (3) VaultError L99, (4) HTTPStatusError L142, (5) RequestError L144, (6) non-JSON response L140-141. La rama 7 del plan original (HTTP ConnectError específico) está cubierta por `RequestError` genérico (L144). → Resolución: 6 tests suficientes, no 7. U2.6 cubrir `RequestError` genérico.

3. **DISCREPANCIA D3:** Plan dice `_check_approval_rule` solo soporta `>` y `<`. Código real L128-159 confirma: solo `>` y `<` con `split()`. `>=`, `<=`, `==` NO están implementados — el plan es correcto en que se rompen silenciosamente. → Resolución: Tests U3.1-U3.4 correctos. Operadores `>=`, `<=`, `==` van en Paso 2 como feature fix.

4. **DISCREPANCIA D4:** Plan menciona `mock_service_connector` fixture en conftest.py. **CONFIRMADO** en L318-327. Pero el fixture retorna un MagicMock con `_run` mockeado, no el conector real. Para tests de error paths del conector real, se necesita instanciar `ServiceConnectorTool` directamente, no usar el fixture. → Resolución: Tests U2.1-U2.7 instancian `ServiceConnectorTool(org_id=sample_org_id)` directamente.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Paso 1 NO toca schema DB directamente.** Son tests unitarios mockeados. Impacto en datos: NULO.

- **Tablas referenciadas (mockeadas):** `org_mcp_servers` (MCPPool), `service_tools` + `service_catalog` + `org_service_integrations` (ServiceConnector), `domain_events` (auditoría ServiceConnector).
- **RLS:** Todos los tests usan `mock_service_client` (service_role, bypass RLS). Correcto para tests unitarios.
- **Sin migraciones nuevas.** Sin cambios de schema.
- **Integridad referencial:** No aplicable — tests mockean respuestas DB.

**Conclusión ETAPA 1:** Sin impacto en datos. Tests 100% mockeados.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 1.1 Circuit Breaker — `tests/unit/test_mcp_pool_circuit.py`

**Archivo a crear.** 5 tests unitarios.

**Funciones bajo test:**
- `_is_circuit_open(key: str) -> bool` — L61-66. Lógica: failures < 5 → False. failures >= 5 y elapsed < 60s → True.
- `_record_failure(key: str)` — L68-70. Incrementa failures, setea last_check = time.time().
- `_reset_circuit_breaker(key: str)` — L72-73. Setea failures = 0.0.
- `get_tools()` — L77-191. Usa circuit breaker + retry con tenacity.

**Patrón de mocking:** `unittest.mock.patch("src.tools.mcp_pool.time.time")` para controlar tiempo sin espera real. `MCPPool.reset()` entre tests para limpiar singleton.

**Firmas de test esperadas:**
```python
def test_circuit_closed_with_0_to_4_failures()
def test_circuit_open_with_5_failures_under_60s()
def test_circuit_half_open_after_60s()
def test_get_tools_raises_when_circuit_open()
def test_get_tools_resets_circuit_on_success_after_half_open()
```

**Dependencias:** `MCPPool`, `MCPConnectionError`, `time`.

### 1.2 ServiceConnector Error Paths — `tests/unit/test_service_connector.py`

**Archivo a crear.** 6 tests (no 7 — ver Discrepancia D2).

**Función bajo test:** `_run(self, tool_id: str, input_data: dict = None) -> str` — L60-170.

**Ramas de error confirmadas:**
1. L72-73: tool no encontrada → `"Error: Tool '{tool_id}' no encontrada"`
2. L88-91: servicio no activo → `"Error: Servicio '{service_id}' no está activo"`
3. L99-100: VaultError → `"Error: {e}"`
4. L142-143: HTTPStatusError → `"Error HTTP: {status_code}"`
5. L144-145: RequestError → `"Error HTTP: {str(e)}"`
6. L140-141: non-JSON response → `response.text[:500]`

**Patrón de mocking:**
- `mock_service_client` fixture para DB queries.
- `patch("httpx.Client")` para HTTP calls.
- `patch("src.tools.service_connector.get_secret")` para Vault.
- Instanciar `ServiceConnectorTool(org_id=sample_org_id)` directamente.

### 1.3 Approval Operators — `tests/unit/test_approval_operators.py`

**Archivo a crear.** 4 tests.

**Función bajo test:** `_check_approval_rule(self, rule: Dict, results: Dict) -> bool` — L128-159.

**Tests existentes en `test_dynamic_flow.py`:**
- `>` true (L284-292)
- `>` false (L294-302)
- condición inválida (L304-313)
- resultado no numérico (L315-324)

**Tests faltantes (este archivo):**
- `<` standalone con valor menor → True
- `<` standalone con valor mayor → False
- condición vacía → False
- múltiples resultados, uno cumple

**Patrón:** Instanciar `DynamicWorkflow(org_id=sample_org_id)`, llamar `_check_approval_rule` directamente. Sin mocking de DB ni crews.

### 1.4 Sanitizer Edge Cases — `tests/unit/test_sanitizer.py`

**Archivo a crear.** 11 tests.

**Función bajo test:** `sanitize_output(data: Any) -> Any` — L28-50.

**SECRET_PATTERNS confirmados (7):**
1. `sk_live_[a-zA-Z0-9]+` — Stripe live
2. `sk_test_[a-zA-Z0-9]+` — Stripe test
3. `Bearer [a-zA-Z0-9\-._~+/]+=*` — Bearer tokens
4. `Basic [a-zA-Z0-9+/]+=*` — Basic auth
5. `xox[bpsa]-[a-zA-Z0-9\-]+` — Slack
6. `ghp_[a-zA-Z0-9]+` — GitHub PAT
7. `AIza[a-zA-Z0-9\-_]+` — Google API

**Tests:**
- U4.1-U4.7: cada patrón individual → `[REDACTED]`
- U4.8: dict anidado recursivo
- U4.9: lista con secreto
- U4.10: input no-string (int, None, bool) → passthrough
- U4.11: string sin secretos → sin cambio

**Patrón:** Import directo de `sanitize_output`. Sin mocking. Tests puros de función.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Paso 1 NO toca endpoints.** Son tests unitarios de lógica interna. Sin APIs nuevas, sin middleware, sin contratos.

**Impacto backend:** NULO. Los tests validan funciones internas que el backend YA usa.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo DB → Backend → Frontend → UX

Paso 1 no modifica flujo end-to-end. Solo agrega cobertura de tests.

### DX & Tooling — OBLIGATORIO

**Problema manual identificado:** Ejecutar subsets de tests del Paso 1 requiere comandos pytest largos y memorizar rutas de archivos. El desarrollador debe correr:
```
pytest tests/unit/test_mcp_pool_circuit.py tests/unit/test_service_connector.py tests/unit/test_approval_operators.py tests/unit/test_sanitizer.py -v
```

**Herramienta Propuesta:** `fap test-step 1`

- **Qué automatiza:** Ejecución de todos los tests de un paso específico del plan de certificación. Resuelve archivos del paso, corre pytest con flags correctos, muestra resumen por sub-paso.
- **Tipo:** Comando CLI (Typer)
- **Cómo se usa:** `fap test-step 1` → corre los 26 tests del Paso 1 con `-v --tb=short`. `fap test-step 1 --cov` → añade cobertura.
- **Impacto para el usuario final:** Elimina necesidad de memorizar rutas de tests. Un comando = todo el paso. Output con breakdown por sub-paso (1.1, 1.2, 1.3, 1.4).
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

**Implementación sugerida:** Agregar subcomando `test-step` en `src/cli/` que mapee número de paso → lista de archivos de test → `pytest.main()`.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Sin cambios de schema requeridos — tests 100% mockeados
✅ [CODE] `test_mcp_pool_circuit.py` existe con 5 tests pasando
✅ [CODE] `test_service_connector.py` existe con 6 tests pasando
✅ [CODE] `test_approval_operators.py` existe con 4 tests pasando
✅ [CODE] `test_sanitizer.py` existe con 11 tests pasando
✅ [CODE] Cobertura `mcp_pool.py` >80%
✅ [CODE] Cobertura `service_connector.py` >70%
✅ [CODE] Cobertura `sanitizer.py` 100%
✅ [BACKEND] Sin endpoints nuevos — tests no tocan APIs
✅ [FULLSTACK] 26 tests nuevos totales pasan 100%
✅ [DX] Comando `fap test-step 1` ejecuta sin errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Singleton MCPPool contamina tests entre sí | Alta | `_instance` compartido entre tests si no se llama `MCPPool.reset()` | `MCPPool.reset()` en fixture con `autouse=True` o en teardown de cada test |
| `time.time()` mockeado afecta otros tests | Media | Patch global de `time.time` puede filtrarse | Usar `patch` como context manager o decorator por test, NO como fixture global |
| `ServiceConnectorTool` requiere `org_id` válido | Media | Hereda de `OrgBaseTool` que requiere `org_id` como campo Pydantic | Usar `sample_org_id` fixture de conftest.py |
| `httpx.Client` mock necesita simular `raise_for_status()` | Media | Tests de HTTPStatusError requieren mock que lance excepción | `mock_client.request.side_effect = httpx.HTTPStatusError(...)` |
| `sanitize_output` con string 10MB (Paso 4) no se valida aquí | Baja | Plan original menciona performance test — fuera de scope Paso 1 | Documentar como riesgo para Paso 4 |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Comando `fap test-step` | FULLSTACK/DX | Media | 2h | Ninguna |
| 1 | Crear `tests/unit/test_mcp_pool_circuit.py` (5 tests) | CODE | Media | 1.5h | Tarea 0 |
| 2 | Crear `tests/unit/test_service_connector.py` (6 tests) | CODE | Media | 2h | Tarea 0 |
| 3 | Crear `tests/unit/test_approval_operators.py` (4 tests) | CODE | Baja | 1h | Tarea 0 |
| 4 | Crear `tests/unit/test_sanitizer.py` (11 tests) | CODE | Baja | 1h | Tarea 0 |
| 5 | Ejecutar suite completa Paso 1, verificar gate 100% pass | FULLSTACK | Baja | 0.5h | Tareas 1-4 |
| 6 | Verificar umbrales de cobertura (>80% mcp_pool, >70% service_connector, 100% sanitizer) | CODE | Baja | 0.5h | Tarea 5 |

**Tiempo total estimado:** 8.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Fix `_check_approval_rule` para `>=`, `<=`, `==`** — Paso 2 del plan. Parser actual usa `split(" > ")` que rompe con `>=`.
- **Mover `test_3_5_latency.py` a `tests/integration/`** — si el archivo reaparece o se recrea.
- **Agregar `tests/stress/` directory** — necesario para Paso 4 del plan.
- **Performance test `sanitize_output` con 10MB** — Paso 4, no cubierto aquí.
- **Test de `MCPPool.get_tools()` con tenacity retry real** — integración, no unitario.

---

## Métricas de Calidad del Análisis

| Métrica | Resultado |
|---|---|
| `proyecto-config.json` leído | ✅ |
| Elementos verificados (§0) | 25 (umbral: ≥18 para 6-10 archivos) |
| Discrepancias detectadas | 4 (D1-D4) |
| Secciones completadas | 8 (0-7) |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 11, verificables |
| Riesgos identificados | 5 (técnico, integración, futuro) |
| Tareas en el plan | 7, atómicas, ordenadas |
| Suposiciones no verificadas | 0 |
| Propuesta DX / Tooling | 1 herramienta (`fap test-step`) |
| Estimación de tiempo | Sí, por tarea y total (8.5h) |
