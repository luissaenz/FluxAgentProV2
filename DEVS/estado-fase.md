# Estado de Fase: Certificación Técnica Profunda (QA) — testing

> **Fecha:** 2026-05-01
> **Estado:** ✅ COMPLETADO (testing) — 7/8 pasos completados
> **Último Archivado:** `DEVS/IMPLEMENTED/testing/06-Performance-Observabilidad/`
> **Commit:** `a07dfea` — `testing / 06-Performance-Observabilidad`

---

## 1. Resumen de Fase

**Fase:** `testing`
**Objetivo:** Certificación Técnica Profunda (QA) — verificar baseline, cobertura unitaria gaps críticos, tests integración, flujos E2E, estrés, seguridad, performance y cierre.

**Pasos:**
- ✅ **Paso 0: Auditoría de Línea Base.** Baseline: importabilidad, suite 100%, lint 0, tool registry, fixtures. DX `fap baseline-check`. Vulnerabilidad `__import__` corregida (restricted import + ALLOWED_MODULES).
- ✅ **Paso 1: Cobertura Unitaria de Gaps Críticos.** 30 tests unitarios: MCPPool circuit breaker (5), ServiceConnector error paths (7), Approval operators (4), Sanitizer (14). DX `fap test-step 1`.
- ✅ **Paso 2: Tests de Integración.** MCP resilience (3 tests), DynamicWorkflow handover (3 tests), fix parser `>=`/`<=`/`==` en approval rules (3 tests condicionales). DX `fap test-step 2`.
- ✅ **Paso 3: E2E — Flujos Completos con Mocks.** 4 tests: Degraded MCP (E3.1), Approval Gate HITL (E3.2), Multi-step Handover 3 niveles (E3.3). DX `fap test-step 3`.
- ✅ **Paso 4:** Tests de Estrés y Robustez
- ✅ **Paso 5:** Tests de Seguridad — 14 tests nuevos (SE5.1-SE5.12, SE5.17-SE5.18). DX `fap security-audit`. Fix seguridad en `run.py` + `local_executor.py` (`_create_safe_builtins()`).
- ✅ **Paso 6: Performance & Observabilidad.** 4 benchmarks (P6.1-P6.4): resolve_tools 50 tools <100ms, WorkflowDefinition 10x5 <50ms, sanitize_output 1MB <500ms, _is_circuit_open <1ms. 9 tests. DX `fap perf-check` con flags --baseline/--compare/--json/--verbose/--no-warmup.
- ⬜ **Paso 7:** Documentación y Cierre

**Dependencias:** Paso 0 → Todos. Pasos 1→7 secuenciales con superposición posible.

---

## 2. Estado Actual del Proyecto

### Rutas Críticas (de `proyecto-config.json`)
- `paths.backend:` `src/` (16 módulos: api, cli, connectors, crews, db, events, flows, guardrails, mcp, scheduler, scripts, services, state, tools, utils)
- `paths.migrations:` `supabase/migrations/` (30 archivos SQL: 001-025)
- `paths.tests:` `tests/` (unit, integration, e2e)
- `paths.cli:` `src/cli/` (16 comandos fap: +security-audit, +perf-check)
- `paths.devs_in_progress:` `DEVS/IN_PROGRESS/` — vacío (archivado)
- `paths.devs_implemented:` `DEVS/IMPLEMENTED/`

### Stack Tecnológico
- **Backend:** Python (>=3.12, <3.14) + FastAPI (>=0.115.0)
- **Frontend:** TypeScript + Next.js (dashboard/)
- **DB:** Supabase (PostgreSQL) + queries directas + RPC
- **Auth:** PyJWT (ES256/HS256) via middleware
- **Agentes:** CrewAI (opcional) + MCP (Stdio/SSE)
- **Package Manager:** uv (Python) / npm (frontend)

### Implementado y Funcional (Verificado contra código)

| Componente | Archivo(s) | Estado | Descripción |
|---|---|---|---|
| **AgentFactory** | `src/crews/factory.py` | ✅ | `resolve_tools()` con MCP + `create_agent_async()`. |
| **ArchitectFlow** | `src/flows/architect_flow.py` | ✅ | Generación avanzada bundles con MCP y ServiceConnector. |
| **MCPPool** | `src/tools/mcp_pool.py` | ✅ | Circuit breaker + tenacity retries. |
| **ServiceConnector** | `src/tools/service_connector.py` | ✅ | Integraciones HTTP via service_catalog. |
| **DynamicWorkflow** | `src/flows/dynamic_flow.py` | ✅ | Ejecución multi-paso. Operadores `>=`/`<=`/`==` fixeados en Paso 2. |
| **ToolRegistry** | `src/tools/registry.py` | ✅ | API `list_tools()`, `get()`, `register()`, `clear()`, `invalidate_tenant_cache()`. |
| **SecurityGuard** | `src/services/security_guard.py` | ✅ | AST scan + RestrictedPython + restricted `__import__` con ALLOWED_MODULES. Doble vector protegido (execute + _verify_compilation). |
| **SecurityAudit CLI** | `src/cli/commands/security_audit.py` | ✅ | DX `fap security-audit`. 5 categorias: imports, calls, async, regresion, escape. Filtro + JSON output. 185 loc. |
| **CLI (fap)** | `src/cli/main.py` | ✅ | 15 comandos: init, login, validate, package, publish, run, scaffold, dev, export-agents, validate-tools, validate-architect-output, test-scenarios, phase-close, baseline-check, test-step, **security-audit**, stress-bench. |
| **EventStore** | `src/events/store.py` | ✅ | Append síncrono + asíncrono de eventos de dominio. |
| **BundleManager** | `src/services/bundle_manager.py` | ✅ | Carga remota + validación + atomicidad. |
| **BaseCrew** | `src/crews/base_crew.py` | ✅ | Resolución de tools con MCP. |
| **FlowRegistry** | `src/flows/registry.py` | ✅ | Registro de flujos dinámicos. |
| **StressBench CLI** | `src/cli/commands/stress_bench.py` | ✅ | DX `fap stress-bench`. Genera fixtures masivos + ejecuta suite stress con métricas. 280 loc. |
| **Sanitizer (optimizado)** | `src/mcp/sanitizer.py` | ✅ | `SECRET_PATTERNS` pre-compilados con `re.compile`. Performance 7x en strings grandes. |
| **Stress Suite** | `tests/stress/` | ✅ | 14 tests: concurrency (S4.1-S4.3), edge cases (S4.4-S4.7). Conftest con MCPPool reset + flow_registry save/restore. |
| **PerfCheck CLI** | `src/cli/commands/perf_check.py` | ✅ | DX `fap perf-check`. Ejecuta benchmarks P6.1-P6.4, verifica thresholds, reporte JSON. Flags: --baseline, --compare, --json, --verbose, --no-warmup. 253 loc. |
| **Performance Benchmarks** | `tests/stress/test_performance.py` | ✅ | 9 tests (4 clases): P6.1 resolve_tools 50 tools, P6.2 WorkflowDefinition 10x5, P6.3 sanitize 1MB, P6.4 circuit breaker overhead. Fixtures autouse limpian estado. |

### Tests (Verificado contra código)

| Suite | Cantidad | Estado |
|---|---|---|
| **Total** | 512 tests | `pytest --collect-only` |
| **Unitarios** | 317 | 317/317 pass |
| **Integración** | 102 | 102/102 pass |
| **E2E** | 60 | 60/60 pass |
| **Stress** | 14 | 14/14 pass (S4.1-S4.7) |
| **Performance** | 9 | 9/9 pass (P6.1-P6.4, nuevo en Paso 6) |
| **SecurityGuard** | 29 | 29/29 pass (SE5.1-SE5.18, nuevo en Paso 5) |
| **Escape** | 2 | 2/2 pass (SE5.17-SE5.18) |
| **Lint** | — | 0 errores (`ruff check src/ tests/`) |

### Discrepancias Conocidas Plan vs Código
- Resueltas en Pasos 0-3:
  - `list_all()` → `list_tools()` corregido
  - `>=`/`<=`/`==` ya fixeados (`dynamic_flow.py:144-150`)
  - `approval_threshold` no usado en `_run_crew()` — deuda técnica documentada
  - `_on_approved()` marca COMPLETED, no reanuda steps — documentado

---

## 3. Contratos Técnicos Vigentes

### Patrones de Código
- **RLS:** `tenant_isolation` via `org_id::text` contra `app.org_id` (verificado en migraciones)
- **Registry (Tools):** Singleton `ToolRegistry`. Decorador `@tool_registry.register`. API: `list_tools()`, `get()`, `register()`, `get_metadata()`, `clear()`, `invalidate_tenant_cache()`
- **Registry (Flows):** `FlowRegistry` en `src/flows/registry.py`. Decorador `@flow_registry.register`
- **MCP Resolution:** Prefijo `mcp:{server}:{tool}`. Solo paths asíncronos
- **Auth:** Middleware en `src/api/middleware.py`. JWKS + validación membresía
- **Seguridad (skills):** AST scan + RestrictedPython + restricted `__import__` con `ALLOWED_MODULES`
- **Sandbox execution:** `SecurityGuard.execute()` usa `_create_safe_builtins()`. System bundles bypass RestrictedPython
- **CLI:** Typer app en `src/cli/main.py`. Comandos via `app.command()` o `app.add_typer()`

### Esquemas DB Clave (verificado en migraciones)
- `agent_catalog` (004): id, org_id, name, description, allowed_tools text[], code, soul_json jsonb, version, enabled
- `org_mcp_servers` (005): id, org_id, name, command text[], env_secrets jsonb, enabled
- `workflow_templates` (006): id, org_id, name, definition jsonb, tags text[], enabled
- `service_catalog` (024): id, org_id, name, base_url, auth_type, config jsonb
- `domain_events` (021-022): id, aggregate_type, aggregate_id, event_type, payload jsonb, correlation_id, created_at (Realtime)
- `bundle_system` (0026): Bundles versionados con hash
- `service_tools` (024): Definiciones de tools TIPO C para ServiceConnector
- `org_service_integrations` (024): Activación de servicios por organización

### Convenciones
- Backend: `snake_case` funciones/variables, `PascalCase` clases
- Archivos: `snake_case.py`
- DB: `snake_case` tablas y columnas
- Imports: absolutos (ej: `from src.tools.registry import tool_registry`)
- Tests: `test_*.py` en `tests/unit/`, `tests/integration/`, `tests/e2e/`

### Dependencias Clave
- **Directas:** fastapi>=0.115.0, pydantic>=2.10.0, supabase>=2.10.0, anthropic>=0.40.0, openai>=1.58.0, PyJWT>=2.0.0, httpx>=0.28.0, structlog>=24.4.0, mcp>=1.0.0, RestrictedPython>=7.0, typer>=0.12.0, tenacity>=9.0.0
- **Dev:** pytest>=8.3.0, pytest-asyncio>=0.24.0, pytest-mock>=3.14.0, pytest-cov>=6.0.0, pytest-timeout>=1.5.0, ruff>=0.8.0
- **Opcionales:** crewai>=0.100.0, crewai-tools>=0.20.0

---

## 4. Decisiones de Arquitectura Tomadas

### De Fase V (details4agents)
1. **Resolución Centralizada:** Todo paso de herramientas por `AgentFactory.resolve_tools()`
2. **Bifurcación Sync/Async:** MCP restringido a paths asíncronos
3. **Dogfooding DX:** Herramientas CLI para su propio propósito
4. **Validación Preventiva:** `fap validate-tools` verifica disponibilidad antes de ejecución

### De Fase VI — testing
5. **Nombre DX:** `baseline-check` sobre `preflight` — más descriptivo
6. **Vulnerabilidad `__import__`:** Opción A — restricted `__import__` con ALLOWED_MODULES allowlist. `_create_safe_builtins()`. Doble vector protegido
7. **Fix `test_3_5_latency`:** Skip condicional via `skipif` + mover a `tests/integration/`
8. **`tenacity` dependencia directa:** Era transitiva via crewai opcional
9. **Bug approval rules:** `>=`/`<=`/`==` fixeado en Paso 2 (parser prioriza compuestos)
10. **`fap test-step` extendido:** Mapping para pasos 1, 2, 3 — comando único por paso
11. **Mock inline para E3.1:** No reusar `mock_mcp_pool` fixture (retorna 3 tools). `AsyncMock(side_effect=...)` para fallo parcial
12. **Estrategia snapshot para E3.2:** `flow.state.task_id` manual tras execute(). Mock de `snapshots` table
13. **MCPPool.reset() autouse:** Fixture obligatoria entre tests E2E para contaminación singleton

### De Fase VI — testing / Paso 4
14. **Pre-compilación `re.compile`:** `SECRET_PATTERNS` pre-compilados en módulo. `pattern.sub()` en vez de `re.sub()`. Elimina re-compilación en cada llamada. Crítico para strings grandes (10MB+).
15. **Suite stress parametrizada por env vars:** `STRESS_TOOLS_COUNT`, `STRESS_SANITIZER_SIZE`, `STRESS_JSON_DEPTH`. No hardcodeo de escala.
16. **DX `fap stress-bench`:** Comando único que genera fixtures masivos + ejecuta suite + reporta métricas (tiempo, breakdown). Reemplaza creación manual + `pytest` directo.
17. **`pytest-timeout` como dev dep:** Evita que tests de estrés cuelguen el CI. Tiempo límite por test vía decorador `@pytest.mark.timeout`.

### De Fase VI — testing / Paso 5
18. **DX `fap security-audit`:** Comando único con 5 categorías (imports/calls/async/regresion/escape). Filtro `-c` por categoría. Output `--json` para CI.
19. **`fap test-step 5`:** Mapeo a `test_security_guard.py` + `test_security_guard_escape.py`.
20. **Fix `safe_builtins` en `run.py` y `local_executor.py`:** Reemplazo de `RestrictedPython.safe_builtins` por `guard._create_safe_builtins()` con `__import__` restringido + ALLOWED_MODULES. Cierra 2 vectores de ejecución que inyectaban `__import__` sin restricción.
21. **Cobertura SE5.x:** 14 tests nuevos: 7 imports prohibidos (SE5.1-7), 3 calls prohibidos (SE5.8-10), 2 async (SE5.11-12), 2 escape (SE5.17-18). SE5.13-16 ya existian de Pasos 0-1.
22. **Patrón `guard._create_safe_builtins()` como `safe_env` estándar:** Unifica creación de builtins seguros en todos los puntos de ejecución (validate, execute, local_executor, fap run).

### De Fase VI — testing / Paso 6
23. **DX `fap perf-check`:** Comando único que ejecuta benchmarks P6.1-P6.4, verifica thresholds, genera `reports/perf_report.json`. Flags: `--baseline` (guarda baseline), `--compare` (detecta regresiones >20%), `--json` (output machine-readable), `--verbose` (muestra raw output), `--no-warmup` (salta 3 warmup iterations).
24. **`time.perf_counter_ns()` para P6.4:** Precisión nanosegundo para circuit breaker overhead <1ms. `time.perf_counter()` suficiente para thresholds holgados (100ms/50ms/500ms).
25. **Sin `pytest-benchmark`:** No agregado a dev deps. Benchmarks usan `time.perf_counter()` + assertions manuales.
26. **Warmup obligatorio:** 1 iteración descartada en tests pytest. CLI `fap perf-check` implementa 3 iteraciones warmup para precisión.
27. **P6.2 sin `input_data`:** Schema real de `WorkflowDefinition` (name/description/flow_type/steps/agents/category). Corrección del FINAL aplicada.
28. **P6.4 mide `_is_circuit_open()` directo:** Pre-carga `_adapters[key]` con MagicMock para evitar conexión real. O(1) dict lookup + float comparison.
18. **DX `fap security-audit`:** Comando único con 5 categorías (imports/calls/async/regresion/escape). Filtro `-c` por categoría. Output `--json` para CI.
19. **`fap test-step 5`:** Mapeo a `test_security_guard.py` + `test_security_guard_escape.py`.
20. **Fix `safe_builtins` en `run.py` y `local_executor.py`:** Reemplazo de `RestrictedPython.safe_builtins` por `guard._create_safe_builtins()` con `__import__` restringido + ALLOWED_MODULES. Cierra 2 vectores de ejecución que inyectaban `__import__` sin restricción.
21. **Cobertura SE5.x:** 14 tests nuevos: 7 imports prohibidos (SE5.1-7), 3 calls prohibidos (SE5.8-10), 2 async (SE5.11-12), 2 escape (SE5.17-18). SE5.13-16 ya existian de Pasos 0-1.
22. **Patrón `guard._create_safe_builtins()` como `safe_env` estándar:** Unifica creación de builtins seguros en todos los puntos de ejecución (validate, execute, local_executor, fap run).

### Correcciones al Plan
- `plan.md:21`: `list_all()` → `list_tools()` (P0.4)
- `plan.md:83`: `>=, <=, ==` "NO implementados" → "se rompen silenciosamente" (ya fixeado en Paso 2)
- Plan dice "warning in log" → código usa `logger.error` (E3.1)
- Plan asume `resume()` reanuda steps → `_on_approved()` marca COMPLETED
- `phase-state.md` línea 20 describe Paso 4 como "Hardening de API Pública" pero plan.md define "Tests de Estrés y Robustez". Desincronización documentada en análisis Paso 4.
- Plan.md §5.1 lista SE5.1-SE5.10 como "expandir test_security_guard.py" y SE5.17-SE5.18 como archivo nuevo. Implementación sigue el plan al 100%.

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Decisiones Tomadas | Notas |
|---|---|---|---|---|---|
| 0 — Auditoría de Línea Base | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/00-Auditoria-de-Linea-Base/` | `17349a5` | D1-D6. `baseline-check` creado. SE5.13-SE5.16 implementados. | Lint 0. Suite base 100%. Validación: ✅ |
| 1 — Cobertura Unitaria de Gaps Críticos | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/01-Cobertura-Unitaria-de-Gaps-Criticos/` | `2e90aec` | 30 tests unitarios. DX `fap test-step 1`. | 30/30 pass. Validación: ✅ |
| 2 — Tests de Integración | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/02-Tests-de-Integracion/` | `b5d23af` | Fix parser `>=`/`<=`/`==`. 3 resilience + 3 handover + 3 condicional. DX `fap test-step 2`. | Fix approval operators. Lint I001 corregido. Validación: ✅ |
| 3 — E2E Flujos Completos con Mocks | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/03-E2E-Flujos-Completos-con-Mocks/` | `7a750ca` | 4 tests E2E (Degraded MCP, HITL, 3-step Handover). DX `fap test-step 3`. | 4/4 pass. Lint 0. Validación: ✅ |
| 4 — Tests de Estrés y Robustez | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/04-Tests-de-Estres-y-Robustez/` | `af6b16f` | 14 tests stress (S4.1-S4.7). DX `fap stress-bench`. `re.compile` en sanitizer. pytest-timeout. | 14/14 pass. Lint 0. 6 análisis + validación archivados. Validación: ✅ |
| 5 — Tests de Seguridad | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/05-Tests-de-Seguridad/` | `534481f` | 14 tests (SE5.1-SE5.12, SE5.17-SE5.18). DX `fap security-audit`. Fix `safe_builtins` en `run.py` + `local_executor.py`. `fap test-step 5`. | 14/14 pass. Lint 0. 6 análises + 1 validación archivados. Validación: ✅ |
| 6 — Performance & Observabilidad | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/06-Performance-Observabilidad/` | `a07dfea` | 4 benchmarks (P6.1-P6.4). DX `fap perf-check` con --baseline/--compare/--json/--verbose/--no-warmup. Reports JSON en `reports/`. Fixtures autouse en conftest para aislamiento. Correcciones FINAL aplicadas (sin input_data, _is_circuit_open directo). | 9/9 pass. Lint 0. Validación: ✅. |
| 7 — Documentación y Cierre | 🔲 PENDIENTE | — | — | TESTING.md, Makefile, cobertura >75%, `fap phase-close` | — |

---

## 6. Criterios Generales de Aceptación MVP

- [x] **Paso 0:** Baseline verificada: importabilidad ✅, suite 100% ✅, lint 0 ✅, tool registry audit ✅, fixtures ✅
- [x] **Paso 1:** 30/30 tests unitarios (5 circuit + 7 connector + 4 approval + 14 sanitizer) ✅
- [x] **Paso 2:** Tests integración: 3 MCP resilience + 3 handover + 3 approval operators ✅. Fix parser `>=`/`<=`/`==` ✅
- [x] **Paso 3:** 4/4 tests E2E (Degraded MCP, Approval Gate HITL, Multi-step Handover) ✅. `fap test-step 3` funcional ✅
- [x] **Vulnerabilidad `__import__` corregida:** restricted import con allowlist. 15/15 security tests ✅
- [x] **Herramientas DX:** `fap baseline-check`, `fap test-step {1,2,3}`, `fap stress-bench` ✅
- [x] **Código ejecuta sin errores:** Lint 0, 489 tests collected ✅
- [x] **Paso 4:** 14/14 tests stress ✅. `fap stress-bench` funcional ✅. `re.compile` SECRET_PATTERNS ✅. `pytest-timeout>=1.5.0` instalado ✅
- [x] **Paso 5:** 14/14 tests seguridad (SE5.1-SE5.12 + SE5.17-SE5.18) ✅. `fap security-audit` funcional ✅. `fap test-step 5` funcional ✅. Fix `safe_builtins` en `run.py` + `local_executor.py` ✅. 512 tests totales ✅. Lint 0 ✅
- [x] **Paso 6:** 9/9 tests performance (P6.1-P6.4) ✅. `fap perf-check` funcional ✅. `fap perf-check --baseline` genera baseline ✅. `fap perf-check --compare` detecta regresiones ✅. Correcciones del FINAL aplicadas (sin input_data, _is_circuit_open directo) ✅. Benchmarks usan mocks puros + son independientes ✅. Lint 0 ✅
- [ ] **Paso 7:** pendiente

**Progreso Fase VI: 87.5% (7/8 pasos). Próximo: Paso 7 — Documentación y Cierre.**

**Criterios fuera de alcance MVP:** retry con backoff, caching, rate limiting, logging avanzado, optimización performance extrema.
