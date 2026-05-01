# Análisis Técnico — Paso 0: Auditoría de Línea Base (Pre-flight)

**Agente:** qwen  
**Fecha:** 2026-05-01  
**Fase:** testing  
**Paso:** 0 — Auditoría de Línea Base (Pre-flight)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `MCPPool._is_circuit_open()` | `src/tools/mcp_pool.py:62` — umbral 5 fallos, 60s half-open | ✅ | mcp_pool.py:62-66 |
| 2 | `MCPPool._record_failure()` | `src/tools/mcp_pool.py:68` — incrementa failures + timestamp | ✅ | mcp_pool.py:68-70 |
| 3 | `MCPPool._reset_circuit_breaker()` | `src/tools/mcp_pool.py:72` — resetea failures a 0 | ✅ | mcp_pool.py:72-73 |
| 4 | `MCPPool.reset()` | `src/tools/mcp_pool.py:211` — resetea singleton | ✅ | mcp_pool.py:211-213 |
| 5 | `MCPPool.get_tools()` con circuito abierto | `src/tools/mcp_pool.py:101-106` — lanza `MCPConnectionError` | ✅ | mcp_pool.py:101-106 |
| 6 | `ServiceConnectorTool._run()` | `src/tools/service_connector.py:60` — 7 ramas de error reales | ✅ | service_connector.py:60-171 |
| 7 | `ServiceConnectorTool` tool_id inexistente | `service_connector.py:72-73` — retorna "no encontrada" | ✅ | service_connector.py:72-73 |
| 8 | `ServiceConnectorTool` servicio inactivo | `service_connector.py:88-91` — retorna "no está activo" | ✅ | service_connector.py:88-91 |
| 9 | `ServiceConnectorTool` VaultError | `service_connector.py:97-100` — captura VaultError | ✅ | service_connector.py:97-100 |
| 10 | `ServiceConnectorTool` HTTP error | `service_connector.py:142-145` — HTTPStatusError + RequestError | ✅ | service_connector.py:142-145 |
| 11 | `ServiceConnectorTool` respuesta no-JSON | `service_connector.py:140-141` — `response.text[:500]` | ✅ | service_connector.py:140-141 |
| 12 | `sanitize_output()` | `src/mcp/sanitizer.py:28` — 7 patrones SECRET_PATTERNS | ✅ | sanitizer.py:17-25 |
| 13 | `DynamicWorkflow._check_approval_rule()` | `src/flows/dynamic_flow.py:128` — solo soporta `>` y `<` | ✅ | dynamic_flow.py:128-159 |
| 14 | Bug `>=` en approval_rule | `dynamic_flow.py:137` — `">" in "monto >= 50000"` → True → `float("= 50000")` → ValueError | ✅ | dynamic_flow.py:137-139 |
| 15 | `SecurityGuard.execute()` inyecta `__import__` | `src/services/security_guard.py:142` — `exec_globals["__builtins__"]["__import__"] = __import__` | ✅ | security_guard.py:142 |
| 16 | `SecurityGuard._verify_compilation()` inyecta `__import__` | `security_guard.py:221` — `safe_env["__import__"] = __import__` | ✅ | security_guard.py:221 |
| 17 | `FORBIDDEN_CALLS` incluye `__import__` | `security_guard.py:73` | ✅ | security_guard.py:73 |
| 18 | `test_3_5_latency.py` requiere DB real | `tests/test_3_5_latency.py:42-48` — exige `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | ✅ | test_3_5_latency.py:42-48 |
| 19 | `conftest.py` fixture `sample_org_id` | `tests/conftest.py:24-26` | ✅ | conftest.py:24-26 |
| 20 | `conftest.py` fixture `mock_service_client` | `tests/conftest.py:111-139` | ✅ | conftest.py:111-139 |
| 21 | `conftest.py` fixture `mock_tenant_client` | `tests/conftest.py:173-212` | ✅ | conftest.py:173-212 |
| 22 | `conftest.py` fixture `global_llm_mock` | `tests/conftest.py:273-299` | ✅ | conftest.py:273-299 |
| 23 | `conftest.py` fixture `mock_mcp_pool` | `tests/conftest.py:302-315` | ✅ | conftest.py:302-315 |
| 24 | `conftest.py` fixture `mock_service_connector` | `tests/conftest.py:318-327` | ✅ | conftest.py:318-327 |
| 25 | `WorkflowDefinition` Pydantic | `src/flows/workflow_definition.py:57` — validación completa | ✅ | workflow_definition.py:57-123 |
| 26 | `Step.approval_threshold` no se usa | `dynamic_flow.py:66-126` — `_run_crew` usa `approval_rules[].condition`, nunca `approval_threshold` | ✅ | dynamic_flow.py:118 |

**Discrepancias encontradas:**

1. **DISCREPANCIA D1 — `test_3_5_latency.py` bloquea Paso 0:** El archivo `tests/test_3_5_latency.py` requiere variables de entorno `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` (línea 42-48). Si no están configuradas, lanza `RuntimeError` al importarse, lo que causa que `pytest --co` falle (P0.1). El plan reconoce este bug (línea 26 del plan) pero la resolución es ambigua: dice "añadir `@pytest.mark.skip` si es test de integración real". **Resolución propuesta:** Añadir `pytest.importorskip` o `pytest.skip` condicional al inicio del módulo para que no bloquee `pytest --co` cuando no hay DB configurada.

2. **DISCREPANCIA D2 — Vulnerabilidad `__import__` confirmada en código:** El plan (línea 28) marca la vulnerabilidad como "confirmada teóricamente". Verificación contra código confirma: `security_guard.py:142` inyecta `__import__` en `execute()` y `security_guard.py:221` en `_verify_compilation()`. El AST scanner bloquea `__import__("os")` directo, pero el código malicioso que accede vía `__builtins__["__import__"]` NO es detectado por el AST (no es un `ast.Call` directo). **Resolución propuesta:** Ejecutar tests SE5.13-SE5.16 primero (antes de Paso 0 completo). Si confirman exploit → fix `security_guard.py` antes de continuar.

3. **DISCREPANCIA D3 — Operadores `>=`, `<=`, `==` se rompen silenciosamente:** `dynamic_flow.py:137` usa `">" in condition`. Si condition es `"monto >= 50000"`, el `">"` está presente → split por `">"` da `["monto ", "= 50000"]` → `float("= 50000")` lanza `ValueError` → catch en línea 157 → log warning → retorna `False`. No es que "no estén implementados", es que **crashea silenciosamente**. **Resolución propuesta:** Fix parser para priorizar `>=` sobre `>` (check `">="` antes de `">"`).

4. **DISCREPANCIA D4 — `test_security_guard.py` existente puede solapar con tests propuestos:** El plan dice que `test_security_guard.py` ya cubre: `os`, `sys`, `urllib`, `eval`, `open`, dunder, timeout, bypass builtins. Los tests SE5.1-SE5.10 propuestos agregan `subprocess`, `shutil`, `ctypes`, `socket`, `gc`, `inspect`, `requests`, `__import__`, `compile`, `exec`. Verificar que no existan ya antes de implementar.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Alcance del Paso 0:** No toca schema directamente. Solo verifica importabilidad, suite existente, lint, y fixtures. Sin embargo, los pasos subsecuentes (1-7) sí tocan las siguientes tablas:

### Tablas implicadas en pasos futuros:

| Tabla | Migración | Uso |
|---|---|---|
| `domain_events` | 001_set_config_rpc.sql:87-97 | Eventos de auditoría (Paso 3, 4, 6) |
| `org_mcp_servers` | 005_org_mcp_servers.sql | Config MCP servers (Paso 1, 2) |
| `service_tools` | 024_service_catalog.sql | Definición de tools tipo C (Paso 1) |
| `org_service_integrations` | 024_service_catalog.sql | Integraciones activas por org (Paso 1) |
| `workflow_templates` | 006_workflow_templates.sql | Templates de DynamicWorkflow (Paso 2) |
| `skill_catalog` | 004_agent_catalog.sql | Skills dinámicas desde DB (Paso 5) |
| `agent_catalog` | 004_agent_catalog.sql | Catálogo de agentes (Paso 0, referencia) |

### Schema relevante para verificación:

- **RLS:** Todas las tablas usan `tenant_isolation` via `org_id::text` contra `app.org_id` (phase-state.md §3).
- **Índices:** Migración 004 tiene índices en `agent_catalog`. Migración 024 tiene índices en `service_tools` y `org_service_integrations`.
- **No se requieren cambios de schema para Paso 0.**

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos críticos del Paso 0:

| Archivo | Función en Paso 0 | Estado |
|---|---|---|
| `src/tools/mcp_pool.py` | Circuit breaker sin test directo | ✅ Existe, 213 líneas |
| `src/tools/service_connector.py` | 7 ramas de error sin test | ✅ Existe, 171 líneas |
| `src/mcp/sanitizer.py` | 50 líneas sin cobertura | ✅ Existe, 50 líneas |
| `src/flows/dynamic_flow.py` | Bug en `_check_approval_rule` | ✅ Existe, 193 líneas |
| `src/services/security_guard.py` | Vulnerabilidad `__import__` | ✅ Existe, 288 líneas |
| `tests/conftest.py` | Fixtures globales | ✅ Existe, 352 líneas |
| `tests/test_3_5_latency.py` | Test que bloquea P0.1 | ✅ Existe, 702 líneas |

### Patrones existentes verificados:

- **Model definition:** Pydantic `BaseModel` + `dataclass` (confirmado en `workflow_definition.py`, `service_connector.py`).
- **Route definition:** FastAPI `APIRouter` decorators (confirmado en `src/api/routes/`).
- **Auth pattern:** Middleware + JWT validation (`src/api/middleware.py`).
- **Test pattern:** `pytest` con fixtures en `conftest.py`, mocks globales de Supabase/LLM/CrewAI.
- **Naming:** `snake_case` para funciones/variables, `PascalCase` para clases (confirmado en código).
- **Import style:** Absolute imports `src.xxx.xxx` (confirmado en todos los archivos).

### Funciones/clases que necesitan test (Paso 0 identifica):

| Función/Clase | Archivo | Líneas | Sin test |
|---|---|---|---|
| `MCPPool._is_circuit_open` | mcp_pool.py:62 | 5 | ✅ |
| `MCPPool._record_failure` | mcp_pool.py:68 | 3 | ✅ |
| `MCPPool._reset_circuit_breaker` | mcp_pool.py:72 | 2 | ✅ |
| `MCPPool.get_tools` (circuit breaker path) | mcp_pool.py:77 | 115 | ✅ |
| `ServiceConnectorTool._run` (error paths) | service_connector.py:60 | 111 | ✅ |
| `sanitize_output` | sanitizer.py:28 | 22 | ✅ |
| `SecurityGuard.execute` (vector `__import__`) | security_guard.py:126 | 29 | ⚠️ Parcialmente testeado |
| `SecurityGuard._verify_compilation` (vector `__import__`) | security_guard.py:206 | 54 | ⚠️ Parcialmente testeado |
| `DynamicWorkflow._check_approval_rule` (bug `>=`) | dynamic_flow.py:128 | 32 | ⚠️ Parcialmente testeado |

### Tests existentes que cubren parcialmente:

- `tests/unit/test_mcp_exceptions.py` — solo testa excepciones MCP del protocolo, NO circuit breaker.
- `tests/unit/test_security_guard.py` — cubre imports forbidden, dunder, timeout, bypass. NO cubre `__import__` injection en `execute()` ni `_verify_compilation()`.
- `tests/unit/test_dynamic_flow.py` (no existe como archivo separado) — la lógica de approval está en `dynamic_flow.py` pero no hay test específico.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Paso 0 no crea/modifica endpoints. Pero verifica:

- **Importabilidad de `src/api/main.py`:** FastAPI app entry point. Debe importar sin error.
- **Importabilidad de `src/api/middleware.py`:** Middleware de auth. Debe importar sin error.
- **Importabilidad de rutas en `src/api/routes/`:** Todos los route modules deben importar.

### Endpoints que los pasos futuros tocarán:

| Endpoint | Paso | Uso |
|---|---|---|
| N/A | Paso 0 | No aplica — solo auditoría |
| N/A | Paso 1-6 | Tests unitarios/integración, no tocan API |
| N/A | Paso 7 | Documentación, no cambia endpoints |

### Flujo de datos verificado:

- **Auth → Middleware → Routes:** `src/api/middleware.py` usa `verify_jwt` + org isolation. Confirmado en conventions del `proyecto-config.json`.
- **DB → Backend:** `src/db/session.py` provee `get_service_client()` (service_role, bypass RLS) y `get_tenant_client()` (tenant-scoped). Confirmado en uso en `mcp_pool.py`, `service_connector.py`, `registry.py`.
- **No hay cuellos de botella identificados en Paso 0.**

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo Paso 0:

```
[pytest --co] → importa todos src/ modules → verifica 0 errores import
[pytest tests/] → corre 425 tests existentes → verifica 100% pass
[ruff check] → lint estricto → verifica 0 errores
[tool_registry.list_all()] → reporta tools disponibles
[pytest --fixtures] → verifica fixtures disponibles
```

### Gaps identificados:

1. **`test_3_5_latency.py` bloquea import:** Si `SUPABASE_URL` no está configurada, el módulo lanza `RuntimeError` al importarse. Esto rompe P0.1 (`pytest --co`).

2. **No hay `Makefile`:** El plan dice "Se crea en Paso 7". Sin Makefile, correr `pytest tests/` manualmente es propenso a error.

3. **No hay `TESTING.md`:** Se crea en Paso 7. Sin docs, nuevos devs no saben cómo correr tests.

### DX & Tooling — Herramienta Propuesta: **`fap preflight`**

- **Qué automatiza:** Ejecuta las 5 verificaciones del Paso 0 (P0.1-P0.5) en un solo comando, con output legible y reporte de estado. Evita tener que correr 5 comandos separados manualmente.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:** `uv run fap preflight`
- **Impacto para el usuario final:** Reduce 5 comandos manuales a 1. Output claro: ✅/❌ por cada check. Si algo falla, muestra el error exacto y sugiere fix.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

```
### Herramienta Propuesta: fap preflight
- **Qué automatiza:** Ejecuta P0.1-P0.5 en secuencia, reporta estado, bloquea si gate falla
- **Tipo:** CLI command (Typer)
- **Cómo se usa:** `uv run fap preflight`
- **Impacto para el usuario final:** 1 comando vs 5 manuales. Output claro con ✅/❌. Sugiere fixes si falla.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] Todos los módulos en src/ importan sin error (pytest --co retorna 0 errores)
✅ [TEST] Suite existente (425 tests) pasa 100% (0 failures, 0 errors) — excepto test_3_5_latency.py marcado como skip
✅ [LINT] ruff check src/ tests/ retorna 0 errores
✅ [REGISTRY] tool_registry.list_all() retorna lista no vacía de tools registrados
✅ [FIXTURES] pytest --fixtures muestra: sample_org_id, mock_service_client, mock_tenant_client, global_llm_mock, mock_mcp_pool
✅ [DX] Herramienta fap preflight ejecuta sin errores y reduce paso manual de 5 comandos a 1
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `test_3_5_latency.py` bloquea `pytest --co` | Alta | Requiere `SUPABASE_URL` al import-time, no al test-time | Añadir `pytest.importorskip` o env-var guard al inicio del módulo |
| Vulnerabilidad `__import__` en `security_guard.py` | Crítica | Inyección de `__import__` en builtins post-AST-scan | Ejecutar SE5.13-SE5.16 primero. Si confirman exploit → fix antes de merge |
| Bug silencioso en `_check_approval_rule` con `>=` | Media | Parser usa `">" in condition` que matchea `>=` | Fix parser para check `">="` antes de `">"` |
| Singleton `MCPPool` compartido entre tests | Media | `MCPPool._instance` persiste entre tests si no se resetea | Usar `MCPPool.reset()` en teardown de cada test |
| `conftest.py` mockea demasiados puntos | Baja | 8+ patch points para `get_service_client`, frágil si cambia estructura | Documentar patch points, agregar test que verifique que todos los puntos son válidos |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Implementar `fap preflight` CLI command | FULLSTACK/DX | Media | 2h | Ninguna |
| 1 | Fix `test_3_5_latency.py` para no bloquear import | CODE | Baja | 0.5h | Ninguna |
| 2 | Ejecutar `pytest --co` y documentar resultado | CODE | Baja | 0.5h | Tarea 1 |
| 3 | Ejecutar `pytest tests/` y documentar resultado | CODE | Baja | 1h | Tarea 2 |
| 4 | Ejecutar `ruff check src/ tests/` y fix si necesario | CODE | Baja | 0.5h | Ninguna |
| 5 | Ejecutar `tool_registry.list_all()` y documentar tools | BACKEND | Baja | 0.5h | Ninguna |
| 6 | Ejecutar `pytest --fixtures` y verificar 5 fixtures | CODE | Baja | 0.5h | Ninguna |
| 7 | Ejecutar diagnóstico SE5.13-SE5.16 (vulnerabilidad `__import__`) | BACKEND/SECURITY | Alta | 2h | Ninguna |
| 8 | Documentar resultado completo de Paso 0 | FULLSTACK | Baja | 0.5h | Tareas 2-7 |

**Tiempo total estimado:** 8.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Fix `security_guard.py`:** Si SE5.13-SE5.16 confirman exploit, implementar Opción A (restricted `__import__` con allowlist).
- **Fix `_check_approval_rule`:** Implementar soporte correcto para `>=`, `<=`, `==` con parser que priorice operadores compuestos.
- **Mover `test_3_5_latency.py` a `tests/integration/`:** Es un test de integración real (requiere DB), no debería estar en raíz de `tests/`.
- **Agregar `Makefile` con targets:** `test`, `test-fast`, `test-all`, `lint`, `coverage` (Paso 7 del plan).
- **Crear `TESTING.md`:** Documentar estrategia de mocking, cómo correr cada paso, fixtures disponibles (Paso 7 del plan).

---

## 📊 Métrica de Calidad Auto-Evaluada

| Métrica | Mínimo | Actual |
|---|---|---|
| `proyecto-config.json` leído antes de explorar | 100% | ✅ |
| Elementos verificados (§0) | ≥ 8 | ✅ 26 elementos |
| Discrepancias detectadas | ≥ 1 | ✅ 4 discrepancias |
| Secciones completadas | 8 secciones (0-7) | ✅ 8 secciones |
| Etapas cubiertas | 4 etapas | ✅ data, code, backend, fullstack+DX |
| Criterios de aceptación | ≥ 1 por sub-paso | ✅ 6 criterios (P0.1-P0.5 + DX) |
| Riesgos identificados | ≥ 3 | ✅ 5 riesgos |
| Tareas en el plan | ≥ 4 | ✅ 8 tareas |
| Suposiciones no verificadas | ≤ 2 | ✅ 0 suposiciones no verificadas |
| Propuesta DX / Tooling | ≥ 1 | ✅ `fap preflight` |
| Estimación de tiempo | Sí | ✅ 8.5h total, por tarea |
