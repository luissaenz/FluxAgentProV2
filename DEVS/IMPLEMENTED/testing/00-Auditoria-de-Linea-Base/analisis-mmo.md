# Análisis Técnico — Paso 0: Auditoría de Línea Base (Pre-flight)

**Agente:** mmo
**Fecha:** 2026-05-01
**Fase:** Certificación Técnica Profunda (QA)

---

## 0️⃣ Verificación contra Código Fuente

> **Umbral:** ≥ 8 elementos verificados (1-2 archivos afectados por test)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `conftest.py` fixture `sample_org_id` | `tests/conftest.py:25` | ✅ VERIFICADO | Retorna `str(uuid4())` |
| 2 | `conftest.py` fixture `mock_service_client` | `tests/conftest.py:112` | ✅ VERIFICADO | Patchea 7 puntos de import, retorna `make_mock_client()` |
| 3 | `conftest.py` fixture `mock_tenant_client` | `tests/conftest.py:174` | ✅ VERIFICADO | Context manager mock, patchea 10 puntos |
| 4 | `conftest.py` fixture `global_llm_mock` | `tests/conftest.py:274` | ✅ VERIFICADO | `autouse=True`, mockea `ChatOpenAI`, `ChatOllama`, `crewai.Agent/Task/Crew` |
| 5 | `conftest.py` fixture `mock_mcp_pool` | `tests/conftest.py:303` | ✅ VERIFICADO | `AsyncMock` con 3 tools simuladas |
| 6 | `tool_registry.list_tools()` existe | `src/tools/registry.py:230` | ✅ VERIFICADO | Retorna `list(self._tools.keys())` |
| 7 | `test_3_5_latency.py` requiere DB real | `tests/test_3_5_latency.py:42-48` | ✅ VERIFICADO | `load_dotenv()` + `SUPABASE_URL/SUPABASE_SERVICE_KEY` obligatorios. **Fallará sin DB.** |
| 8 | `security_guard.py` inyecta `__import__` | `src/services/security_guard.py:142` | ✅ VERIFICADO | `exec_globals["__builtins__"]["__import__"] = __import__` en `execute()` non-system |
| 9 | `security_guard.py` inyecta `__import__` en `_verify_compilation` | `src/services/security_guard.py:221` | ✅ VERIFICADO | `safe_env["__import__"] = __import__` en dry-run |
| 10 | `MCPPool._is_circuit_open` lógica | `src/tools/mcp_pool.py:60-66` | ✅ VERIFICADO | `failures < 5` → False; `elapsed < 60` → True |
| 11 | `FORBIDDEN_CALLS` incluye `__import__` | `src/services/security_guard.py:73` | ✅ VERIFICADO | `{"eval", "exec", "compile", "open", "__import__"}` |
| 12 | AST scanner detecta `__import__("os")` como call | `src/services/security_guard.py:176-181` | ✅ VERIFICADO | `isinstance(node.func, ast.Name)` + `node.func.id in FORBIDDEN_CALLS` |

**Discrepancias encontradas:**

1. **`test_3_5_latency.py` es test de integración real, no unitario.** Requiere `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` en `.env`. Sin DB → `RuntimeError` en import time (línea 46-48). **Resolución:** Añadir `@pytest.mark.skip` o mover a `tests/integration/` con skip si no hay DB. El plan dice "corregir antes de continuar" — skip es aceptable para pre-flight.

2. **Vulnerabilidad `__import__` confirmada en DOS vectores.** `execute()` línea 142 inyecta `__import__` en builtins de sandbox non-system. `_verify_compilation()` línea 221 hace lo mismo. AST scanner bloquea `__import__("os")` directo PERO no detecta acceso indirecto vía `__builtins__["__import__"]`. **Resolución:** Tests SE5.13-SE5.16 son diagnóstico obligatorio. Si confirman exploit → fix antes de merge.

3. **`_check_approval_rule` rompe silenciosamente con `>=`, `<=`, `==`.** `dynamic_flow.py:137` hace `" > " in condition` → si condition es `"monto >= 50000"`, `">"` está presente → split produce `"= 50000"` → `float("= 50000")` → `ValueError` → `return False`. **Resolución:** Parser necesita fix (priorizar `>=` sobre `>`). Fuera de scope Paso 0, pero documentado para Paso 2.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema relevante para Paso 0

Paso 0 es auditoría de línea base — NO crea/modifica tablas. Análisis se limita a verificar que tablas existentes soportan tests.

**Tablas tocadas por tests existentes:**

| Tabla | Migración | Tests que la usan | Estado |
|---|---|---|---|
| `organizations` | `001_set_config_rpc.sql` | `test_3_5_latency.py` (fixture `test_org_id`) | ✅ Existe |
| `domain_events` | `001_set_config_rpc.sql` | `test_3_5_latency.py` (CRUD directo) | ✅ Existe |
| `org_mcp_servers` | `005_org_mcp_servers.sql` | `mcp_pool.py` (config lookup) | ✅ Existe |
| `workflow_templates` | `006_workflow_templates.sql` | `dynamic_flow.py` (load from DB) | ✅ Existe |
| `skill_catalog` | — | `registry.py:_load_from_db` | ⚠️ NO VERIFICABLE — migración no encontrada en `supabase/migrations/`. Puede existir vía Supabase Studio o RPC. |
| `service_tools` | `024_service_catalog.sql` | `service_connector.py:_run` | ✅ Existe |
| `org_service_integrations` | `024_service_catalog.sql` | `service_connector.py:_run` | ✅ Existe |

**Integridad referencial:** No aplica — Paso 0 no modifica schema.

**RLS:** Tests usan `mock_service_client` (bypass RLS) o `mock_tenant_client` (context manager). No requieren RLS real.

**⚠️ Discrepancia:** Tabla `skill_catalog` no encontrada en migraciones. `registry.py:_load_from_db` (línea 131) hace query a esta tabla. Si no existe → `_load_from_db` falla silenciosamente (catch-all `except Exception` línea 188). **Impacto en Paso 0:** Ninguno — tests mockean DB. **Impacto futuro:** Skills desde DB no funcionarán.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases verificadas para Paso 0

| Función/Clase | Archivo | Firma | Responsabilidad |
|---|---|---|---|
| `SecurityGuard.validate_skill()` | `security_guard.py:105` | `(self, source_code: str, filename: str) -> bool` | AST scan + RestrictedPython compilation |
| `SecurityGuard.execute()` | `security_guard.py:126` | `(self, source_code: str, filename: str) -> Dict[str, Any]` | Validar + ejecutar código |
| `SecurityGuard._scan_ast()` | `security_guard.py:156` | `(self, source_code: str, filename: str)` | Static analysis de imports y calls |
| `SecurityGuard._verify_compilation()` | `security_guard.py:206` | `(self, source_code: str, filename: str)` | Dry-run con timeout |
| `MCPPool._is_circuit_open()` | `mcp_pool.py:60` | `(self, key: str) -> bool` | Check circuit breaker state |
| `MCPPool._record_failure()` | `mcp_pool.py:68` | `(self, key: str)` | Increment failure counter |
| `MCPPool._reset_circuit_breaker()` | `mcp_pool.py:72` | `(self, key: str)` | Reset failures a 0 |
| `ToolRegistry.list_tools()` | `registry.py:230` | `(self) -> List[str]` | Lista tools registradas |
| `sanitize_output()` | `sanitizer.py:28` | `(data: Any) -> Any` | Redact secrets en output |

### Patrones existentes

- **Fixture pattern:** `conftest.py` usa `MagicMock` + `patch()` con múltiples puntos de import. Patrón robusto — maneja `ImportError` gracefully.
- **Singleton pattern:** `MCPPool._instance` con `get()` classmethod. `reset()` para tests.
- **Registry pattern:** `ToolRegistry` singleton global `tool_registry` con decorator `@register_tool`.

### Imports y dependencias

- `conftest.py` importa `crewai`, `langchain_openai`, `langchain_community` — mockeados en `sys.modules` si no existen (líneas 264-270). **Correcto** — permite tests sin dependencias opcionales.
- `security_guard.py` importa `RestrictedPython` — dependencia directa en `pyproject.toml`. ✅
- `mcp_pool.py` importa `tenacity` — **NO está en `pyproject.toml` dependencies**. ⚠️ Probablemente transitive de `crewai` o `supabase`. Verificar.

**⚠️ Discrepancia:** `tenacity` no es dependencia directa. Si `crewai` no está instalado (es optional), `mcp_pool.py` fallará al importar. **Impacto:** Tests que importan `mcp_pool` directamente pueden fallar sin `[crew]` extras.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints relevantes para Paso 0

Paso 0 no crea endpoints. Verifica que endpoints existentes no interfieren con tests.

| Endpoint | Archivo | Método | Tests asociados |
|---|---|---|---|
| `POST /webhooks/{org_id}/{flow_type}` | `src/api/routes/` | POST | `test_dynamic_flow.py` (integration) |
| MCP server endpoints | `src/mcp/server.py` | SSE/JSON-RPC | `test_mcp_handlers.py` (integration) |

### Middleware

- `src/api/middleware.py` — JWT validation. No relevante para Paso 0 (tests mockean auth).

### Flujos de datos

```
Test → conftest.py (mock DB/LLM/MCP) → src/* → assertions
```

No hay flujo backend real en tests unitarios. Integration tests usan mocks más realistas pero aún sin DB real.

### Error handling en tests

- `test_3_5_latency.py` — **NO tiene error handling para DB ausente.** `RuntimeError` en import time (línea 46-48). Esto bloquea `pytest --co` si no hay `.env` configurado.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo Paso 0

```
P0.1: pytest --co (import check) → ¿todos los módulos importan?
P0.2: pytest tests/ (suite completa) → ¿100% pass?
P0.3: ruff check src/ tests/ (lint) → ¿0 errores?
P0.4: Script tool_registry.list_all() → ¿qué tools hay?
P0.5: pytest --fixtures → ¿conftest fixtures disponibles?
```

### Coherencia

- **P0.1 y P0.2 dependen de `.env` configurado.** `test_3_5_latency.py` hace `load_dotenv()` + check de env vars en import time. Sin `.env` → `RuntimeError` → `pytest --co` falla.
- **P0.4 necesita script.** Plan dice "Script que lea `tool_registry.list_all()`" — pero `ToolRegistry` tiene `list_tools()`, no `list_all()`. Verificar API real.

### Gaps

1. **Gate P0.1-P0.3 imposible sin fix de `test_3_5_latency.py`.** Archivo está en `tests/` raíz → `pytest tests/` lo incluye. Si no hay DB → falla en import → suite completa falla.
2. **`tool_registry.list_all()` no existe.** API real es `list_tools()`. Plan tiene error de nombre.

### DX & Tooling

**Herramienta Propuesta: `fap baseline-check`**
- **Qué automatiza:** Ejecuta P0.1-P0.5 en secuencia con feedback claro. Elimina necesidad de correr 5 comandos manualmente.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:** `uv run fap baseline-check`
- **Impacto para el usuario final:** Un solo comando verifica todo el pre-flight. Sin él, usuario debe recordar 5 comandos y interpretar cada resultado.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tablas `organizations`, `domain_events`, `org_mcp_servers`, `workflow_templates`, `service_tools`, `org_service_integrations` existen en migraciones
✅ [DATA] `skill_catalog` — ⚠️ NO encontrada en migraciones. Verificar en DB.
✅ [CODE] conftest.py fixtures: sample_org_id, mock_service_client, mock_tenant_client, global_llm_mock, mock_mcp_pool — VERIFICADAS
✅ [CODE] tool_registry.list_tools() existe y retorna List[str]
✅ [CODE] security_guard.py inyecta __import__ en 2 locations (líneas 142, 221) — VULNERABILIDAD CONFIRMADA
✅ [CODE] test_3_5_latency.py requiere DB real — FALLA sin .env configurado
⚠️ [BACKEND] P0.1-P0.3 bloqueados por test_3_5_latency.py import time check
⚠️ [BACKEND] tenacity no es dependencia directa — puede fallar sin [crew] extras
✅ [FULLSTACK] Flujo pre-flight identificado: import → suite → lint → registry → fixtures
✅ [FULLSTACK] Plan referencia `list_all()` pero API real es `list_tools()` — DISCREPANCIA
✅ [DX] Herramienta `fap baseline-check` propuesta para automatizar P0.1-P0.5
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `test_3_5_latency.py` bloquea suite completa | **ALTA** | Import time `RuntimeError` sin DB | Añadir `@pytest.mark.skipif` o mover a `tests/integration/` con env check |
| Vulnerabilidad `__import__` en sandbox | **ALTA** | `execute()` y `_verify_compilation()` inyectan `__import__` en builtins | Tests SE5.13-SE5.16 diagnóstico. Si confirman → fix con allowlist de módulos |
| `tenacity` no es dependencia directa | **MEDIA** | Transitive dep vía `crewai` (optional) | Añadir `tenacity` a `dependencies` en `pyproject.toml` o skip tests que importan `mcp_pool` sin `[crew]` |
| `skill_catalog` tabla inexistente | **MEDIA** | No hay migración SQL para esta tabla | Crear migración o verificar si existe vía Supabase Studio |
| `_check_approval_rule` rompe con `>=`/`<=`/`==` | **MEDIA** | Parser no prioriza operadores de 2 chars | Fix parser en Paso 2 (documentado) |
| Tests lentos sin mocks precisos | **BAJA** | Algunos tests de integration pueden hacer HTTP real | Verificar que todos usan fixtures de conftest.py |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear `fap baseline-check` CLI command | FULLSTACK/DX | Media | 2h | Ninguna |
| 1 | Fix `test_3_5_latency.py`: añadir skip si no hay DB | CODE | Baja | 30min | Ninguna |
| 2 | Ejecutar P0.1: `pytest --co` — verificar 0 import errors | CODE | Baja | 15min | Tarea 1 |
| 3 | Ejecutar P0.2: `pytest tests/` — verificar 100% pass | CODE | Baja | 30min | Tareas 1-2 |
| 4 | Ejecutar P0.3: `ruff check src/ tests/` — verificar 0 errores | CODE | Baja | 15min | Ninguna |
| 5 | Ejecutar P0.4: Script `tool_registry.list_tools()` — reporte | CODE | Baja | 15min | Ninguna |
| 6 | Ejecutar P0.5: `pytest --fixtures` — verificar conftest fixtures | CODE | Baja | 15min | Ninguna |
| 7 | Documentar resultados de P0.1-P0.5 en este archivo | FULLSTACK | Baja | 30min | Tareas 2-6 |

**Tiempo total estimado:** ~4 horas

> **Nota:** Tarea 1 (fix test_3_5_latency.py) es GATE. Sin ella, P0.1-P0.2 no pueden ejecutarse limpiamente.

---

## 🔮 Roadmap (NO implementar ahora)

- **Fix vulnerabilidad `__import__`** (si SE5.13-SE5.16 confirman exploit): Crear `__import__` restringido con allowlist de módulos. Opción A del plan.
- **Fix parser `>=`/`<=`/`==`** en `_check_approval_rule`: Priorizar operadores de 2 chars sobre 1 char. Paso 2.
- **Migración `skill_catalog`**: Crear tabla si no existe. Necesario para skills desde DB.
- **Añadir `tenacity` a dependencies**: O hacer skip de tests MCP sin `[crew]` extras.
- **Mover `test_3_5_latency.py`** a `tests/integration/` o `tests/stress/`: No pertenece en raíz.

---

## 📊 Métrica de Calidad

| Métrica | Valor | Mínimo |
|:---|:---|:---|
| `proyecto-config.json` leído antes de explorar | ✅ | 100% |
| Elementos verificados (§0) | 12 | ≥ 8 |
| Discrepancias detectadas | 3 | ≥ 1 |
| Secciones completadas | 8 (0-7) | 8 |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) | 4 |
| Criterios de aceptación | 11 (mixto ✅/⚠️) | ≥ 1 por sub-paso |
| Riesgos identificados | 6 | ≥ 3 |
| Tareas en el plan | 8 | ≥ 4 |
| Suposiciones no verificadas | 1 (`skill_catalog` existe) | ≤ 2 |
| Propuesta DX / Tooling | 1 (`fap baseline-check`) | ≥ 1 |
| Estimación de tiempo | ✅ 4h total | Sí |

---

**Estado:** ANÁLISIS COMPLETADO. Listo para ejecución de Paso 0.
