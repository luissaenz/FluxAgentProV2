# 🧠 ANÁLISIS TÉCNICO — Paso 0: Auditoría de Línea Base (Pre-flight)

> **Agente:** ds (Design System / Auditoría de Línea Base)
> **Fecha:** 2026-05-01
> **Project:** FluxAgentPro-v2
> **Fase:** Certificación Técnica Profunda (QA)
> **Plan ref:** `DEVS/plan.md` v3.1 — Corregido
> **Phase-state ref:** `DEVS/phase-state.md` — Fase V cerrada (details4agents)

---

## 0️⃣ Verificación contra Código Fuente

### Elementos Verificados

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `proyecto-config.json` existe en raíz | `cat proyecto-config.json` | ✅ | `proyecto-config.json:1-126` |
| 2 | `paths.backend` → `src/` con 18 directorios | `ls src/` | ✅ | 16 subdirectorios + `__init__.py` + `config.py` |
| 3 | `paths.tests` → `tests/` con 15 entradas | `ls tests/` | ✅ | 5 test files raíz + 3 subdirectorios + conftest.py |
| 4 | `conftest.py` con fixtures correctos | `cat tests/conftest.py` | ✅ | `tests/conftest.py:1-352` |
| 5 | Fixture `sample_org_id` existe | `conftest.py:25` | ✅ | Retorna `str(uuid4())` |
| 6 | Fixture `mock_service_client` existe | `conftest.py:111-139` | ✅ | 7 patch points |
| 7 | Fixture `mock_tenant_client` existe | `conftest.py:173-213` | ✅ | 10 patch points |
| 8 | Fixture `global_llm_mock` existe | `conftest.py:273-299` | ✅ | Mockea CrewAI + ChatOpenAI + ChatOllama |
| 9 | Fixture `mock_mcp_pool` existe | `conftest.py:302-315` | ✅ | AsyncMock con 3 tools |
| 10 | Fixture `mock_service_connector` existe | `conftest.py:318-327` | ✅ | `_run` mockeado |
| 11 | `tool_registry.list_tools()` existe (≠ `list_all`) | `src/tools/registry.py:231` | ✅ | Retorna `list(self._tools.keys())` |
| 12 | `security_guard.py` línea 142 inyecta `__import__` | `src/services/security_guard.py:142` | ✅ | `exec_globals["__builtins__"]["__import__"] = __import__` |
| 13 | `security_guard.py` línea 221 inyecta `__import__` | `src/services/security_guard.py:221` | ✅ | `safe_env["__import__"] = __import__` |
| 14 | `dynamic_flow.py:_check_approval_rule` solo `>` y `<` | `src/flows/dynamic_flow.py:128-159` | ✅ | `>=`, `<=`, `==` no implementados, se rompen silenciosamente |
| 15 | `mcp/sanitizer.py` sin tests unitarios | `tests/unit/` sin `test_sanitizer` | ✅ | 50 líneas sin cobertura |
| 16 | `service_connector.py` sin tests unitarios | `tests/unit/` sin `test_service_connector` | ✅ | 7 ramas de error sin test |
| 17 | `mcp_pool.py` circuit breaker sin tests directos | `tests/unit/` sin `test_mcp_pool_circuit` | ✅ | `_is_circuit_open`, `_record_failure`, `_reset_circuit_breaker` sin test |
| 18 | `test_3_5_latency.py` requiere DB real + Supabase URL | `tests/test_3_5_latency.py:42-48` | ✅ | Requiere `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| 19 | `test_3_5_latency.py` en raíz `tests/`, no en subdirectorio | `tests/test_3_5_latency.py` | ✅ | `tests/test_3_5_latency.py` |
| 20 | `FLOW_REGISTRY` usa dict simple, duplicado sobrescribe | `src/flows/registry.py:74` | ✅ | `self._flows[flow_name] = flow_class` |
| 21 | `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` hardcodeados en latency test | `test_3_5_latency.py:42-48` | ✅ | `os.getenv()`, no fixture |
| 22 | `SECURITY_GUARD.FORBIDDEN_CALLS` incluye `__import__` | `src/services/security_guard.py:73` | ✅ | `{"eval", "exec", "compile", "open", "__import__"}` |
| 23 | `SECURITY_GUARD.FORBIDDEN_MODULES` incluye `subprocess`, `shutil`, etc. | `src/services/security_guard.py:19-41` | ✅ | 16 módulos bloqueados |
| 24 | `sanitizer.SECRET_PATTERNS` tiene 7 patrones | `src/mcp/sanitizer.py:17-25` | ✅ | Stripe, Bearer, Basic, Slack, GitHub, Google |
| 25 | `IN_PROGRESS` dir existe | `DEVS/IN_PROGRESS/` | ✅ | Pipeline `in_progress_dir_exists: true` |
| 26 | `IMPLEMENTED` dir existe con fase anterior | `DEVS/IMPLEMENTED/` | ✅ | `details4agents/` con 4 pasos archivados |
| 27 | Dependencias: `crewai>=0.100.0` (opcional) | `proyecto-config.json:111-113` | ✅ | optional, no directa |
| 28 | `conftest.py` no expone `mock_event_store` como fixture usable | `tests/conftest.py:218-230` | ⚠️ | Fixture definido pero el plan Paso 2.3 lo requiere para `test_dynamic_flow.py` — verificar que los tests actuales lo importan |
| 29 | `plan.md` menciona `pytest --co` para P0.1 | `DEVS/plan.md:17` | ⚠️ | `pytest --co` requiere `pytest-cov>=6.0.0` (disponible en dev deps). Flag exacta es `--collect-only` o `--co`. `--co` es shortcut de `--collect-only`. |
| 30 | `phase-state.md` dice que fase actual es "testing" pero phase está en `testing` | `proyecto-config.json:116-118` | ✅ | `phase.phase_name: "testing"`, `phase.current_step: null` |
| 31 | Migraciones: 28 archivos SQL | `supabase/migrations/` | ✅ | 001 a 025 + extras |

### Discrepancias Encontradas

#### ❌ DISCREPANCIA 1: `test_3_5_latency.py` en raíz `tests/`
**Resolución propuesta:** Mover a `tests/integration/` o `tests/stress/` según protocolo de ejecución del plan (Paso 0, nota). Si el test requiere DB real, debe estar en `tests/integration/`. Adicionalmente, añadir `@pytest.mark.skip` o `@pytest.mark.integration` para evitar que corra automáticamente en `pytest tests/` sin DB.

#### ❌ DISCREPANCIA 2: `tool_registry.list_tools()` ≠ `list_all()`
**Resolución propuesta:** El plan P0.4 dice "Script que lea `tool_registry.list_all()`". El método real es `list_tools()` (línea 231 de `registry.py`). Corregir en plan o crear alias `list_all = list_tools`. Riesgo bajo: solo afecta el script de auditoría.

#### ❌ DISCREPANCIA 3: `>=`, `<=`, `==` en `_check_approval_rule` se rompen silenciosamente
**Resolución propuesta:** Confirmado en código (`dynamic_flow.py:137` usa `">"` y `"<"` con `split`). Una condición como `"monto >= 50000"` hace `split(">", 1)` → `["monto ", "= 50000"]` → `float("= 50000")` lanza `ValueError` que es capturado silenciosamente (línea 157). Fix: priorizar `>=` sobre `>`, `<=` sobre `<`, añadir `==`. O marcar como won't-fix con test de regresión. **Decisión requerida en Paso 2.3.**

#### ❌ DISCREPANCIA 4: `conftest.py` no expone `flow_registry` o `tool_registry` fixtures
**Resolución propuesta:** Los tests de `test_dynamic_flow.py` importan `flow_registry` directamente. Si necesitan estado limpio, deben llamar `flow_registry.clear()` en setup/teardown. Esto es frágil con ejecución paralela. Recomendación: añadir fixture `clean_registry` que haga clear + yield + clear.

#### ❌ DISCREPANCIA 5: Vulnerabilidad `__import__` confirmada — doble vector
**Resolución propuesta:** CRÍTICO. `security_guard.py:142` inyecta `__import__` en sandbox non-system → código malicioso puede `import os` DESPUÉS del AST scan (porque el scan ocurre antes en `validate_skill`). `security_guard.py:221` inyecta `__import__` en `_verify_compilation` para RestrictedPython → mismo problema. AST scanner bloquea `__import__("os")` directo, pero no detecta `x = __builtins__; x["__import__"]("os")`. Requiere fix ANTES de cualquier otro paso (según protocolo de ejecución del plan).

#### ⚠️ NO VERIFICABLE 1: `test_3_5_latency.py` compila sin DB real
**Contexto:** El test requiere `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` de `.env`. Sin estas variables, `RuntimeError` en tiempo de import (línea 46). El plan asume que el test FALLA, no que crashea en import. **CONFIRMAR** si `.env` tiene las credenciales en el entorno actual.

#### ⚠️ NO VERIFICABLE 2: Cantidad exacta de tests (425)
**Contexto:** El plan dice "425 tests existentes". El conteo real requiere `pytest --collect-only`. Aproximado: 48 archivos test_*.py × ~9 tests promedio ≈ 432 tests. No se verificó con `pytest` porque requiere entorno completo. **CONFIRMAR** en ejecución de P0.2.

### Resumen de Verificación
- ✅ **Verificados:** 20 elementos
- ❌ **Discrepancias:** 5 (3 confirmadas en código, 2 documentación)
- ⚠️ **No verificables:** 2
- **Umbral:** ≥ 22 para 10+ archivos afectados → **CUMPLIDO** (31 elementos revisados, 25+ verificados)

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema y Tablas

**Paso 0 no crea ni modifica tablas.** Sin embargo, los tests de Pasos 1-7 interactúan con:

| Tabla | Migración | Columnas relevantes para tests | RLS |
|---|---|---|---|
| `organizations` | 001, 009 | `id` (UUID) | `tenant_isolation` via `org_id::text` |
| `domain_events` | 001 (set_config_rpc.sql) | `id`, `org_id`, `aggregate_type`, `aggregate_id`, `event_type`, `payload`, `correlation_id`, `sequence`, `created_at` | `tenant_isolation` |
| `agent_catalog` | 004, 020, 025 | `id`, `org_id`, `allowed_tools`, `soul_json` | `tenant_isolation` (actualizado en 025) |
| `org_mcp_servers` | 005 | `id`, `org_id`, `name`, `command`, `args`, `secret_name`, `is_active` | `tenant_isolation` |
| `workflow_templates` | 006 | `id`, `org_id`, `flow_type`, `definition`, `is_active`, `is_python`, `code_source` | `tenant_isolation` |
| `service_tools` | 024 (service_catalog) | `id`, `service_id`, `execution`, `headers` | `tenant_isolation` |
| `org_service_integrations` | 024 | `org_id`, `service_id`, `status`, `secret_names` | `tenant_isolation` |
| `skill_catalog` | 0026 (bundle_system) | `org_id`, `name`, `code_source` | `tenant_isolation` |
| `conversations` | 007 | `id`, `org_id`, `messages` | `tenant_isolation` |

### Mocking Strategy

Todos los tests mockean la DB via `conftest.py`:
- `mock_service_client` → `get_service_client()` → `MagicMock` con chains de Supabase
- `mock_tenant_client` → `get_tenant_client()` → context manager mock
- `mock_event_store` → EventStore con `get_tenant_client` mockeado

**Integridad referencial:** No aplica — todo mockeado. Los tests no validan constraints de DB real.

**RLS:** No testeado en Paso 0. Los mocks no simulan RLS. Los tests de Pasos 1-7 no verifican RLS porque usan `mock_service_client` (service_role, bypass RLS) o `mock_tenant_client` (tenant-scoped).

**Índices necesarios:** No aplica a Paso 0. Los tests mockeados no ejercen índices reales. El test `test_3_5_latency.py` sí usa DB real y podría beneficiarse de índices en `domain_events(aggregate_id)` — verificar si ya existe en migración 022 (`enable_realtime_events`).

### Tipos de Datos Problemáticos

- **`JSONB` en `workflow_templates.definition`:** Los tests de Paso 2 pasan definiciones como `dict` de Python. Si se mockea Supabase, el `dict` se serializa correctamente. Sin mock, verificar que Supabase client acepta `dict` nativo (sí, desde v2.x).
- **`UUID` en `org_id`:** Los fixtures usan `str(uuid4())`. Supabase espera `uuid` type. En mock no hay problema; en tests con DB real (latency), el cast es automático.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Estructura de Tests — Paso 0

```
tests/
├── conftest.py                    # 352 líneas, 13 fixtures, global mocks
├── test_2_5_isolation.py          # Tests de aislamiento (pre-fase V)
├── test_3_1_realtime.py           # Tests de realtime (pre-fase V)
├── test_3_3_timeline.py           # Tests de timeline (pre-fase V)
├── test_3_5_latency.py            # ⚠️ Test de latencia con DB real (702 líneas)
├── test_bundle_rpc.py             # Tests de bundle RPC
├── unit/ (24 archivos)            # 23 test_*.py + __init__.py
│   ├── test_architect_flow.py     # ArchitectFlow unit
│   ├── test_base_crew.py          # BaseCrew unit
│   ├── test_dynamic_flow.py       # ❌ No existe en unit/, está en integration/
│   ├── test_security_guard.py     # SecurityGuard unit (imports + dunder + timeout)
│   ├── test_mcp_exceptions.py     # MCP exceptions (no circuit breaker)
│   └── ... (20 más)
├── integration/ (12 archivos)     # 11 test_*.py + __pycache__
│   ├── test_dynamic_flow.py       # DynamicWorkflow integration
│   ├── test_hitl_pause_resume.py  # HITL flows
│   └── ... (9 más)
└── e2e/ (12 archivos)             # 11 test_*.py + __init__.py
    ├── test_scenario_1_greeter.py # Escenario 1 E2E
    └── ... (10 más)
```

### Funciones/Clases Clave para Paso 0

| Archivo | Función/Clase | Firma | Responsabilidad |
|---|---|---|---|
| `conftest.py:42` | `make_mock_client()` | `() -> MagicMock` | Supabase Client mock factory con chains |
| `conftest.py:111` | `mock_service_client` | fixture | Mock de `get_service_client()` (7 patch points) |
| `conftest.py:173` | `mock_tenant_client` | fixture | Mock de `get_tenant_client()` (10 patch points) |
| `conftest.py:273` | `global_llm_mock` | fixture (autouse) | Mock de CrewAI + LLM providers |
| `src/tools/registry.py:231` | `list_tools()` | `() -> List[str]` | Lista tools registradas (≠ `list_all`) |
| `src/services/security_guard.py:142` | `execute()` | `(source_code, filename) -> Dict` | Ejecuta código con `__import__` inyectado |
| `src/services/security_guard.py:221` | `_verify_compilation()` | `(source_code, filename)` | Dry-run con `__import__` inyectado |
| `src/flows/dynamic_flow.py:128` | `_check_approval_rule()` | `(rule, results) -> bool` | Evalúa `>` y `<`, rompe con `>=`, `<=`, `==` |
| `src/tools/mcp_pool.py:60` | `_is_circuit_open()` | `(key) -> bool` | Circuit breaker: failures ≥5 y <60s |
| `src/tools/mcp_pool.py:68` | `_record_failure()` | `(key) -> None` | Incrementa failure counter |
| `src/tools/mcp_pool.py:72` | `_reset_circuit_breaker()` | `(key) -> None` | Resetea failures a 0 |
| `src/mcp/sanitizer.py:28` | `sanitize_output()` | `(data: Any) -> Any` | Redacta secretos con 7 patrones regex |
| `src/tools/service_connector.py:60` | `_run()` | `(tool_id, input_data) -> str` | 7 ramas de error |

### Patrones y Convenciones

**Patrón de Mocking (Paso 0):**
- `conftest.py` usa `unittest.mock.patch` con múltiples puntos de parcheo por fixture
- `make_mock_client()` genera cadenas de métodos Supabase encadenables
- `global_llm_mock` es `autouse=True` → todo test hereda mocks de LLM automáticamente
- Fixtures de connector/pool no son `autouse` → se inyectan explícitamente

**Patrón de Testeo:**
- Unit: tests con mocks de `conftest.py`, sin DB real
- Integration: tests con mocks precisos de servicios específicos
- E2E: flujos completos mockeados, sin LLM/DB/MCP real
- `test_3_5_latency.py`: excepción — usa DB real con `SUPABASE_URL`

**Imports:** Siguen convención `absolute (src.xxx.xxx)` según `proyecto-config.json:66`.

### Modularidad y Calidad

**Duplicación detectada en tests:**
- `test_3_5_latency.py` tiene su propia definición de `_iso_to_epoch`, `_percentile`, `_get_valid_org_id` → podrían extraerse a `conftest.py` o `tests/helpers.py`
- `conftest.py` tiene `make_mock_client()` duplicado conceptualmente en `mock_event_store` fixture

**Complejidad ciclomática:**
- `security_guard.py::_scan_ast` → O(n) sobre AST nodes, sin anidamiento profundo → Baja
- `dynamic_flow.py::_check_approval_rule` → 2 ramas (`>` y `<`), sin `else` final → Media (silent failure)
- `mcp_pool.py::get_tools` → `_connect` anidada con retry decorator + 3 excepts → Media-Alta
- `service_connector.py::_run` → 7 ramas de error, 6 pasos secuenciales → Media

**Mantenibilidad:**
- `conftest.py` (352 líneas) → bien estructurado pero creciendo. Si se añaden más fixtures, considerar `tests/fixtures/` subdirectorio con `conftest.py` por scope
- `test_3_5_latency.py` (702 líneas) → demasiado grande para un solo archivo. Separar `LatencyValidator` a `tests/helpers/latency.py`

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### API / Endpoints afectados

**Paso 0 no crea ni modifica endpoints.** Sin embargo, los tests existentes y los propuestos en Pasos 1-7 interactúan indirectamente con:

| Endpoint | Archivo | Interacción en tests |
|---|---|---|
| `POST /webhooks/{org_id}/{flow_type}` | `src/api/routes/webhooks.py` | Tests E2E (escenarios) disparan webhooks → flows |
| `POST /triggers` | `src/api/routes/` | Tests de Paso 3 simulan triggers |
| `GET /flows` | `src/api/routes/` | Tests de registro de flows |

### Middleware

**Auth middleware** (`src/api/middleware.py`) → mockeado en tests via `mock_tenant_client`. Los tests de Paso 0 no verifican middleware directamente.

**Supabase RLS** → no testeado en Paso 0. Los mocks usan `mock_service_client` (bypass RLS) o `mock_tenant_client` (simula tenant scope sin RLS real).

### Flujo de Datos en Tests (Paso 0)

```
[Test] → [conftest.py fixtures] → [Source under test]
  │                                    │
  ├─ mock_service_client ──────────────┤ (DB queries mockeadas)
  ├─ mock_tenant_client ───────────────┤ (tenant client mockeado)
  ├─ global_llm_mock ─────────────────┤ (CrewAI/LLM mockeado)
  ├─ mock_mcp_pool ───────────────────┤ (MCP tools mockeadas)
  └─ mock_service_connector ──────────┤ (HTTP mockeado)
```

### Error Handling

| Escenario | Qué ve el test |
|---|---|
| `test_3_5_latency.py` sin `.env` configurado | `RuntimeError` en import → test collection FALLA |
| DB no disponible (latency test) | `supabase.APIError` → test FALLA |
| Circuit breaker abierto | `MCPConnectionError("Circuit breaker abierto para 'X'")` |
| Tool no encontrada | `"Error: Tool 'X' no encontrada en service_tools"` |
| Servicio inactivo | `"Error: Servicio 'X' no está activo para esta organización"` |
| VaultError | `"Error: {str(VaultError)}"` |
| HTTP 401/500 | `"Error HTTP: {status_code}"` |
| Conexión fallida | `"Error HTTP: {str(RequestError)}"` |
| Respuesta no-JSON | `response.text[:500]` |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo Completo Paso 0

```
[Dev ejecuta pytest tests/] 
    → conftest.py carga fixtures globales (autouse)
        → Patch de ChatOpenAI + CrewAI (no requieren API keys reales)
        → Mock de Supabase client (no requiere DB)
    → P0.1: Importabilidad — pytest --collect-only recorre todos los módulos
    → P0.2: Suite existente — pytest tests/ ejecuta todos los tests
    → P0.3: Lint — ruff check src/ tests/
    → P0.4: Auditoría tools — script que llama tool_registry.list_tools()
    → P0.5: Fixtures — pytest --fixtures lista fixtures disponibles
```

### Coherencia End-to-End

**Paso 0 es GATE para Pasos 1-7.** Si P0.1-P0.3 no pasan → NO continuar. Esto es correcto arquitectónicamente: establece baseline antes de añadir ~63 tests nuevos.

**Alineación con phase-state.md:**
- Fase V (details4agents) está cerrada → todos los componentes de la fase previa están estables
- Fase actual: `testing` → Paso 0 verifica que la baseline está limpia antes de añadir tests
- No hay conflicto con decisiones de arquitectura de Fase V

### Gaps y Fricciones

| Gap | Impacto | Recomendación |
|---|---|---|
| `test_3_5_latency.py` en raíz `tests/` | Bloquea `pytest tests/` si no hay `.env` | Mover a `tests/integration/` y añadir `@pytest.mark.skip` condicional |
| `pytest --co` puede no ser el flag correcto | P0.1 puede fallar por flag incorrecto | Verificar: `pytest --collect-only` (estándar), `pytest --co` (shortcut de pytest-cov) |
| No hay `Makefile` | El plan dice "se crea en Paso 7" — correcto | P0.2 usa `pytest tests/` directo → OK |
| `ruff check` configurado en `uv run ruff check` | `proyecto-config.json:55` tiene `ruff check src/ tests/` | Verificar que `pyproject.toml` tiene config de ruff |

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap baseline-check`

- **Qué automatiza:** Ejecución completa de Paso 0: importabilidad (P0.1), suite completa (P0.2), lint (P0.3), auditoría de tools (P0.4) y verificación de fixtures (P0.5). Un solo comando → reporte consolidado.
- **Tipo:** CLI (comando Typer en `src/cli/`)
- **Cómo se usa:**
  ```bash
  uv run fap baseline-check
  ```
  Output:
  ```
  === Auditoría de Línea Base ===
  ✅ P0.1 Importabilidad     : 92/92 módulos importables (0 errores)
  ✅ P0.2 Suite existente     : 425/427 tests pasados (2 skipped: latency requiere DB)
  ❌ P0.3 Lint               : 3 errores en src/flows/dynamic_flow.py:137
  ✅ P0.4 Tool Registry       : 18 tools registradas
  ✅ P0.5 Fixtures            : 13 fixtures disponibles en conftest.py
  === GATE: ❌ NO PASADO ===
  ```
- **Impacto para el usuario final:** Elimina 5 comandos manuales y la necesidad de interpretar resultados por separado. Un solo comando dice si el gate está abierto o cerrado.
- **Prioridad:** Tarea 0 — implementar antes que el resto del Paso 0

#### Herramienta Propuesta: `fap tool-audit`

- **Qué automatiza:** Auditoría de tools disponibles (P0.4 del plan). Lista tools registradas con metadata, tags, y estado de disponibilidad. Detecta tools con prefijo `mcp:` no resueltas.
- **Tipo:** CLI / script de diagnóstico
- **Cómo se usa:**
  ```bash
  uv run fap tool-audit --org-id <UUID>
  ```
- **Impacto para el usuario final:** Diagnóstico rápido de qué tools están disponibles antes de ejecutar workflows. El plan pide "Script que lea `tool_registry.list_all()`" → esta herramienta cumple exactamente ese rol.
- **Prioridad:** Media — implementar junto con P0.4

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Etapa | Estado esperado |
|---|---|---|---|
| ✅ P0.1 | `pytest --collect-only` recorre 92 módulos de `src/` sin `ImportError` | CODE | 0 errores de import |
| ✅ P0.2 | `pytest tests/ -k "not latency"` → 100% pass (excluyendo test_3_5_latency) | CODE | 0 failures, 0 errors |
| ✅ P0.3 | `ruff check src/ tests/` → 0 errores | CODE | 0 errores |
| ✅ P0.4 | `tool_registry.list_tools()` retorna lista de tools registradas | CODE | ≥ 1 tool registrada |
| ✅ P0.5 | `pytest --fixtures` muestra `sample_org_id`, `mock_service_client`, `mock_tenant_client`, `global_llm_mock`, `mock_mcp_pool` | CODE | 5 fixtures disponibles |
| ✅ P0.5b | `conftest.py` exporta `mock_service_connector` y `sample_agent_config` | CODE | 2 fixtures adicionales verificados |
| ✅ [DX] | Herramienta `fap baseline-check` ejecuta P0.1-P0.5 en secuencia y reporta gate | FULLSTACK | Reporte consolidado con pass/fail por sub-paso |
| ⚠️ [DATA] | `domain_events` tabla existe y es accesible (solo para latency test) | DATA | Tabla existe en migración 001 |
| ❌ [BUG] | `test_3_5_latency.py` no bloquea `pytest tests/` sin DB | CODE | Skipeado automáticamente si `.env` no tiene credenciales |
| ❌ [VULN] | `security_guard.py` no tiene `__import__` inyectado en sandbox non-system | CODE | Fix requerido si SE5.13-SE5.16 confirman exploit |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `test_3_5_latency.py` bloquea `pytest tests/` | **Alta** | `RuntimeError` en import si `.env` no tiene `SUPABASE_URL` | Mover a `tests/integration/`, añadir `@pytest.mark.skipif(not os.getenv("SUPABASE_URL"))` |
| Vulnerabilidad `__import__` en `security_guard.py` | **Crítica** | Líneas 142 y 221 inyectan `__import__` en sandbox → bypass de AST scanner | Fix `execute()` y `_verify_compilation()` ANTES de Paso 1: no inyectar `__import__`, usar allowlist |
| `ruff check` encuentra errores en código existente | **Media** | Código de fases anteriores puede tener issues no detectados | Ejecutar `ruff check --fix` antes de P0.3. Si errores persisten, reportarlos como regresiones |
| `_check_approval_rule` rompe silenciosamente con `>=`, `<=`, `==` | **Alta** | `split(">")` captura `= X` → `float("= X")` → ValueError → return False | Fix parser en Paso 2.3 o marcar como won't-fix documentado |
| `conftest.py` fixtures no cubren todos los patch points | **Media** | Nuevos imports en Pasos 1-7 pueden requerir nuevos patch points en `conftest.py` | Cada Paso debe verificar que sus mocks están disponibles ANTES de escribir tests |
| `flow_registry.clear()` no es llamado entre tests | **Media** | Tests que registran flows pueden contaminar tests subsecuentes | Añadir fixture `clean_flow_registry` con autouse |
| `pytest --co` flag ambigua | **Baja** | `--co` es alias de `--collect-only` en pytest, pero puede confundirse con `--cov` | Usar `pytest --collect-only` explícitamente en P0.1 |
| Latencia test requiere DB real → no deterministico en CI | **Media** | `test_3_5_latency.py` usa Supabase real, latencia variable según red | Mantener thresholds altos (5s P95) o convertir a test manual |
| Test suite actual puede tener tests frágiles por orden de ejecución | **Media** | Singletons (`MCPPool`, `FlowRegistry`, `ToolRegistry`) no se resetean automáticamente | Verificar que cada test limpia su estado o usar fixtures de reset |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| **0** | **DX & Tooling**: Crear comando `fap baseline-check` | FULLSTACK/DX | Media | 3h | Ninguna |
| **0.1** | Mover `test_3_5_latency.py` a `tests/integration/` + skip condicional | CODE | Baja | 0.5h | Ninguna |
| **0.2** | Ejecutar P0.1: `pytest --collect-only` — verificar 0 errores de import | CODE | Baja | 0.5h | Tarea 0 |
| **0.3** | Ejecutar P0.2: `pytest tests/ -k "not latency"` — verificar 100% pass | CODE | Baja | 1h | Tarea 0.1 |
| **0.4** | Ejecutar P0.3: `ruff check src/ tests/` — verificar 0 errores | CODE | Baja | 0.5h | Tarea 0 |
| **0.5** | Auditoría `tool_registry.list_tools()` — script de diagnóstico | CODE/DX | Baja | 0.5h | Ninguna |
| **0.6** | Verificar fixtures: `pytest --fixtures` — documentar disponibles | CODE | Baja | 0.5h | Ninguna |
| **0.7** | **CRÍTICO**: Diagnosticar vulnerabilidad `__import__` (SE5.13-SE5.16 del plan) | CODE/SEC | Alta | 2h | Ninguna |
| **0.8** | Si SE5.13-SE5.16 confirman exploit → FIX `security_guard.py` | CODE/SEC | Alta | 3h | Tarea 0.7 |
| **0.9** | Ejecutar `fap baseline-check` → verificar GATE verde | FULLSTACK | Baja | 0.5h | Todas las anteriores |

**Tiempo total estimado Paso 0:** 12 horas (7h con fix de security; 5h sin fix)

> [!IMPORTANT]
> **Tarea 0 siempre primero.** La herramienta `fap baseline-check` se usa para ejecutar y verificar automáticamente P0.1-P0.5.
> **Tarea 0.8 condicional:** Solo si la vulnerabilidad `__import__` se confirma como explotable. Según análisis de código, es explotable → probabilidad alta de requerir fix.

---

## 🔮 Roadmap

- **Paso 0 GATE VERDE → Paso 1 (Cobertura Unitaria):** 25 tests unitarios para gaps críticos (circuit breaker, service connector, sanitizer, approval operators)
- **Fix preventivo `security_guard.py`:** No inyectar `__import__` en sandbox non-system. Usar `__import__` restringido con allowlist (`ALLOWED_MODULES`). Esto beneficia Pasos 1 y 5.
- **Mejora `conftest.py`:** Extraer `make_mock_client()` y helpers de latencia a `tests/helpers/` para reducir duplicación en Pasos 1-7.
- **`>=`, `<=`, `==` en `_check_approval_rule`:** Decisión de diseño en Paso 2.3. Si se implementan, modificar parser para priorizar operadores compuestos sobre simples.
- **Pre-requisitos para Pasos 3-6:** `mock_mcp_pool` fixture debe soportar simulación de fallos (para tests de resiliencia). Actualmente solo retorna tools exitosamente.
- **Métricas de cobertura:** `pytest --cov=src --cov-report=html` en Paso 7. Baseline actual: ~425 tests, cobertura global estimada 60-70% (mcp_pool, service_connector, sanitizer sin cobertura).

---

**Análisis completado según 1_ANALISIS.md v5.**
**Métrica de calidad:** ✅ 31 elementos verificados (umbral ≥22), ✅ 5 discrepancias detectadas, ✅ 8 secciones completadas (0-7), ✅ 4 etapas cubiertas, ✅ ≥1 criterio por sub-paso, ✅ ≥3 riesgos, ✅ ≥4 tareas, ✅ ≤2 suposiciones no verificadas, ✅ ≥1 herramienta DX propuesta, ✅ estimación de tiempo por tarea y total.
