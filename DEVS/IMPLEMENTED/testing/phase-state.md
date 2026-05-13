# Phase State: Deep Technical Certification (QA) — testing → Patch agents
# Estado de Fase: Certificación Técnica Profunda (QA) — testing → Patch agents

> **Fecha / Date:** 2026-05-05
> **Estado / Status:** 🔄 EN PROGRESO — Plan.md Pasos 1-6 implementados (4/6 ✅: Fix MCP deadlock, Registrar agente, Tool calling real, ExcelWriterTool). Análisis multi-agente Paso 7 archivado + validado (✅ APROBADO, 25/25 criterios). Paso 8 completado: config sincronizado, `fap sync-config` funcional, validación ✅ APROBADO.
> **Último Commit / Last Commit:** `3c47fe6` — `patch_agents / 06-ExcelWriterTool`
> **📝 CORREGIDO (2026-05-05):** `proyecto-config.json` ahora refleja `phase_name: "patch_agents"`, `current_step: "06-ExcelWriterTool"`. Fase activa registrada correctamente via `fap sync-config --fix`.

---

## 1. Resumen de Fase / Phase Summary

**Fase / Phase:** `testing`
**Objetivo / Goal:** Certificación Técnica Profunda (QA) — verificar baseline, cobertura unitaria gaps críticos, tests integración, flujos E2E, estrés, seguridad, performance y cierre.

**Pasos / Steps:**
- ✅ **Paso 0: Auditoría de Línea Base.** Baseline: importabilidad, suite 100%, lint 0, tool registry, fixtures. DX `fap baseline-check`. Vulnerabilidad `__import__` corregida (restricted import + ALLOWED_MODULES).
- ✅ **Paso 1: Cobertura Unitaria de Gaps Críticos.** 30 tests unitarios: MCPPool circuit breaker (5), ServiceConnector error paths (7), Approval operators (4), Sanitizer (14). DX `fap test-step 1`.
- ✅ **Paso 2: Tests de Integración.** MCP resilience (3 tests), DynamicWorkflow handover (3 tests), fix parser `>=`/`<=`/`==` en approval rules (3 tests condicionales). DX `fap test-step 2`.
- ✅ **Paso 3: E2E — Flujos Completos con Mocks.** 4 tests: Degraded MCP (E3.1), Approval Gate HITL (E3.2), Multi-step Handover 3 niveles (E3.3). DX `fap test-step 3`.
- ✅ **Paso 4:** Tests de Estrés y Robustez
- ✅ **Paso 5:** Tests de Seguridad — 14 tests nuevos (SE5.1-SE5.12, SE5.17-SE5.18). DX `fap security-audit`. Fix seguridad en `run.py` + `local_executor.py` (`_create_safe_builtins()`).
- ✅ **Paso 6: Performance & Observabilidad.** 4 benchmarks (P6.1-P6.4): resolve_tools 50 tools <100ms, WorkflowDefinition 10x5 <50ms, sanitize_output 1MB <500ms, _is_circuit_open <1ms. 9 tests. DX `fap perf-check` con flags --baseline/--compare/--json/--verbose/--no-warmup.
- ✅ **Paso 7: Documentación y Cierre.** TESTING.md (comandos por paso, mocking strategy, fixtures), CHANGELOG.md (Keep a Changelog), Makefile targets `test-all`/`test-fast`/`coverage` con `uv run` cross-platform, `fap phase-close` generalizado para Fase VI con `--phase testing --certify`, `fap test-step` extendido (pasos 4/6/7), coverage config en `pyproject.toml` (threshold 75%), README actualizado a Fase VI. DX `fap phase-close testing --certify` + `make test-all`.
- 🆕 **Paso Hotfix: Fix Post-Certificación (Plan v3.2 — Paso 3).** Corregir desincronización nombres de pasos en TESTING.md + CHANGELOG.md. Fuente de verdad = phase-state.md + carpetas IMPLEMENTED. Correcciones al plan: nombres Pasos 4-5 del plan.md hotfix no coinciden con fase real. DX `fap sync-step-names --check --source [phase-state|plan]` con flags `--check`/`--fix`/`--dry-run`.
- 🆕 **Fase "Patch agents" (en progreso).** Nueva fase post-testing para aplicar fixes del plan v3.2. Pasos ejecutados: Fix Lint I001, Fix `test_3_5_latency.py` (skipif), Alinear nombres TESTING.md. Pasos pendientes: Fix seguridad `registry.py` (Paso 0), Mover `baseline.py` (Paso 4).
- ✅ **Implementación plan.md pasos 1-6 (commit `349d9eb`).** Paso 1: Fix deadlock MCP (`resolve_tools_async`/`_resolve_mcp_tool_async` en factory.py). Paso 2: Registrar agente (`PresupuestoFlow` registrado). Paso 3: Tool calling real (`ToolCallTracer`, `fap test-tool-call`, `ExcelReaderTool`). Paso 6: `ExcelWriterTool` + dependencia `openpyxl`.
- ✅ **Análisis Paso 7 — Cierre (commit `7827d78`).** 6 análisis multi-agente (ds, Y, mm, kilo) archivados + validación (✅ APROBADO, 25/25 criterios). 8 sub-pasos analizados: 7.1 Remover parche MCP test, 7.2 Bundle seed, 7.3 Test GET agente API, 7.4 Tool calling check en Flow.execute, 7.5 Consolidar tests duplicados, 7.6 Deprecar tests legacy, 7.7 Test import seed, 7.8 Test unitario validate_input.
- `proyecto-config.json` no actualizado para reflejar nueva fase — desincronización documentada.

**Dependencias / Dependencies:** Paso 0 → Todos. Pasos 1→7 secuenciales con superposición posible.

---

## 2. Estado Actual del Proyecto / Current Project State

### Rutas Críticas / Critical Paths (de `proyecto-config.json`)
- `paths.backend:` `src/` (16 módulos: api, cli, connectors, crews, db, events, flows, guardrails, mcp, scheduler, scripts, services, state, tools, utils)
- `paths.migrations:` `supabase/migrations/` (30 archivos SQL: 001-025)
- `paths.tests:` `tests/` (unit, integration, e2e)
- `paths.cli:` `src/cli/` (20+ comandos fap: +security-audit, +perf-check, +test-tool-call)
- `paths.devs_in_progress:` `DEVS/IN_PROGRESS/` — vacío (archivado en commit `7827d78`)
- `paths.devs_implemented:` `DEVS/IMPLEMENTED/`

### Stack Tecnológico / Tech Stack
- **Backend:** Python (>=3.12, <3.14) + FastAPI (>=0.115.0)
- **Frontend:** TypeScript + Next.js (dashboard/)
- **DB:** Supabase (PostgreSQL) + queries directas + RPC
- **Auth:** PyJWT (ES256/HS256) via middleware
- **Agentes / Agents:** CrewAI (opcional) + MCP (Stdio/SSE)
- **Package Manager:** uv (Python) / npm (frontend)

### Implementado y Funcional / Implemented & Working (Verificado contra código / Code-verified)

| Componente / Component | Archivo(s) / File(s) | Estado / Status | Descripción / Description |
|---|---|---|---|
| **AgentFactory** | `src/crews/factory.py` | ✅ | `resolve_tools()` con MCP + `create_agent_async()`. |
| **ArchitectFlow** | `src/flows/architect_flow.py` | ✅ | Generación avanzada bundles con MCP y ServiceConnector. |
| **MCPPool** | `src/tools/mcp_pool.py` | ✅ | Circuit breaker + tenacity retries. |
| **ServiceConnectorTool** | `src/tools/service_connector.py` | ✅ | Integraciones HTTP via service_catalog. Clase real `ServiceConnectorTool` (no `ServiceConnector`). |
| **DynamicWorkflow** | `src/flows/dynamic_flow.py` | ✅ | Ejecución multi-paso. Operadores `>=`/`<=`/`==` fixeados en Paso 2. |
| **ToolRegistry** | `src/tools/registry.py` | ✅ | API `list_tools()`, `get()`, `register()`, `clear()`, `invalidate_tenant_cache()`. |
| **SecurityGuard** | `src/services/security_guard.py` | ✅ | AST scan + RestrictedPython + restricted `__import__` con ALLOWED_MODULES. Doble vector protegido (execute + _verify_compilation). |
| **SecurityAudit CLI** | `src/cli/commands/security_audit.py` | ✅ | DX `fap security-audit`. 5 categorias: imports, calls, async, regresion, escape. Filtro + JSON output. 185 loc. |
| **CLI (fap)** | `src/cli/main.py` | ✅ | 20+ comandos: init, login, validate, package, publish, run, scaffold, dev, export-agents, validate-tools, validate-architect-output, test-scenarios, phase-close, baseline-check, test-step, **security-audit**, stress-bench, lint-fix, check-env, sync-step-names, **test-tool-call**. |
| **EventStore** | `src/events/store.py` | ✅ | Append síncrono + asíncrono de eventos de dominio. |
| **BundleManager** | `src/services/bundle_manager.py` | ✅ | Carga remota + validación + atomicidad. |
| **BaseCrew** | `src/crews/base_crew.py` | ✅ | Resolución de tools con MCP. |
| **FlowRegistry** | `src/flows/registry.py` | ✅ | Registro de flujos dinámicos. |
| **StressBench CLI** | `src/cli/commands/stress_bench.py` | ✅ | DX `fap stress-bench`. Genera fixtures masivos + ejecuta suite stress con métricas. 280 loc. |
| **Sanitizer (optimizado)** | `src/mcp/sanitizer.py` | ✅ | `SECRET_PATTERNS` pre-compilados con `re.compile`. Performance 7x en strings grandes. |
| **Stress Suite** | `tests/stress/` | ✅ | 14 tests: concurrency (S4.1-S4.3), edge cases (S4.4-S4.7). Conftest con MCPPool reset + flow_registry save/restore. |
| **PerfCheck CLI** | `src/cli/commands/perf_check.py` | ✅ | DX `fap perf-check`. Ejecuta benchmarks P6.1-P6.4, verifica thresholds, reporte JSON. Flags: --baseline, --compare, --json, --verbose, --no-warmup. 253 loc. |
| **Performance Benchmarks** | `tests/stress/test_performance.py` | ✅ | 9 tests (4 clases): P6.1 resolve_tools 50 tools, P6.2 WorkflowDefinition 10x5, P6.3 sanitize 1MB, P6.4 circuit breaker overhead. Fixtures autouse limpian estado. |
| **TESTING.md** | `TESTING.md` | ✅ | Documentación completa de testing: comandos por paso (0-7), mocking strategy, fixtures, edge cases. 126 líneas. |
| **CHANGELOG.md** | `CHANGELOG.md` | ✅ | Registro de cambios formato Keep a Changelog. Entries por paso 0-7. 64 líneas. |
| **Makefile (extendido)** | `Makefile` | ✅ | Targets `test-all`/`test-fast`/`coverage`. `uv run` cross-platform. 177 líneas. |
| **PhaseClose CLI (extendido)** | `src/cli/commands/phase_close.py` | ✅ | `fap phase-close --phase testing --certify --full`. Ejecuta lint→unit→integration→e2e→security→stress→perf→coverage→report. Backward compat Fase V. |
| **TestStep CLI (extendido)** | `src/cli/commands/test_step.py` | ✅ | `fap test-step 4` (stress), `fap test-step 6` (perf), `fap test-step 7` (docs check). Coverage files para pasos 4 y 6. |
| **SyncStepNames CLI** | `src/cli/commands/sync_step_names.py` | ✅ | DX `fap sync-step-names --check` con source configurable (phase-state/plan). Flags `--check`/`--fix`/`--dry-run`. Escanea headings `### Paso N:` y `#### Paso N —` en TESTING.md + CHANGELOG.md. 158 loc. |
| **LintFix CLI** | `src/cli/commands/lint_fix.py` | ✅ | Creado en Patch agents / 01-Fix Lint I001 (`9e3736f`). CLI para auto-fix imports con Ruff. 65 loc. |
| **CheckEnv CLI** | `src/cli/commands/check_env.py` | ✅ | Creado en Patch agents / 02-Fix test_3_5_latency.py (`215c383`). Verifica variables de entorno Supabase. 118 loc. |
| **ExcelReaderTool** | `src/tools/excel_reader.py` | ✅ | Lee .xlsx local y retorna JSON. Registrado vía `@register_tool("excel_reader")`. 105 loc. Committed en `349d9eb`. |
| **ExcelWriterTool** | `src/tools/excel_writer.py` | ✅ | Escribe JSON array a .xlsx. Soporta overwrite/append. Registrado vía `@register_tool("excel_writer")`. 108 loc. |
| **PresupuestoFlow** | `src/flows/presupuesto_flow.py` | ✅ | Flow formal registrado como `@register_flow("presupuesto")`. Ejecuta agente presupuestador via BaseCrew. 68 loc. |
| **ToolCallTracer** | `src/crews/base_crew.py` | ✅ | Traza invocaciones a tools durante ejecución. `get_last_tool_calls()` retorna dict tool_name→count. 265 loc total. |
| **resolve_tools_async** | `src/crews/factory.py` | ✅ | Variante async de `resolve_tools()` para MCP tools. `_resolve_mcp_tool_async()` usa await. Evita deadlock. 291 loc. |
| **ToolCallTest CLI** | `src/cli/commands/tool_call_test.py` | ✅ | DX `fap test-tool-call`. Verifica tool calling con dry-run o LLM real. Flags: `--agent`, `--tool`, `--file`, `--dry-run`, `--json`, `--llm`. 177 loc. |
| **Excel Reader/Writer unit tests** | `tests/unit/test_factory.py` | ✅ | TestExcelReaderResolution: 3 tests async para resolución de excel_reader tool. Clase TestResolveToolsAsync + TestResolveMCPToolAsync (~150 lines nuevas). |
| **E2E Tool Calling Real** | `tests/e2e/test_tool_calling_real.py` | ✅ | Test E2E sin patches CrewAI. LLM real (Groq) llama excel_reader. Verifica `tool_calls >= 1` y datos reales en output. 136 loc. Requiere GROQ_API_KEY. |
| **E2E PresupuestoFlow** | `tests/e2e/test_presupuesto_flow.py` | ✅ | Verifica registro en FlowRegistry + ejecución con LLM real. `test_execute_with_real_llm` + `test_flow_registered` + `test_validate_input`. 120 loc. |
| **BaseFlow.last_tool_calls** | `src/flows/base_flow.py:430-440` | ✅ | Property `last_tool_calls` que delega a `BaseCrew.get_last_tool_calls()`. Retorna `{}` si no hay crew. Nueva en commit `7827d78`. |
| **GET /agents/by-role/{role}** | `src/api/routes/agents.py:31-40` | ✅ | Endpoint público que consulta `agent_catalog` por role name. Usa `get_tenant_client`. Nueva en commit `7827d78`. |
| **seed_bundle.py** | `scripts/seed_bundle.py` | ✅ | DX tooling: copia `presupuesto-bundle/` a `data/seed/presupuesto-bundle/`, recalcula SHA256, verifica integridad. 71 loc. Nueva en commit `7827d78`. |
| **Bundle seed** | `data/seed/presupuesto-bundle/` | ✅ | Manifest + agent JSON con SHA256 verificado (`8bdc4257...`). Para import automatizado via `POST /api/bundles/import`. Nueva en commit `7827d78`. |
| **test_register_agent.py (extendido)** | `tests/e2e/test_register_agent.py` | ✅ | Test GET agente via API (`test_get_agent_via_api_returns_correct_data` valida ≥5 campos) + test import seed bundle (`test_import_seed_bundle_via_api`). Nuevos en commit `7827d78`. |
| **Test unitario PresupuestoFlow** | `tests/unit/test_presupuesto_flow.py` | ✅ | 4 tests: validate_input acepta/rechaza campos. Nuevo en commit `7827d78`. |
| **test_real_tool_calling.py** | `tests/e2e/test_real_tool_calling.py` | ❌ ELIMINADO | Duplicado de `test_tool_calling_real.py`. Eliminado en commit `7827d78`. |
| **SyncConfig CLI** | `src/cli/commands/sync_config.py` | ✅ | DX `fap sync-config` con --check/--fix/--dry-run. Detecta drift en phase_name, current_step, pipeline flags. 243 loc. Nueva en commit `3c47fe6`. |

### Tests (Verificado contra código / Code-verified)

| Suite | Cantidad / Count | Estado / Status |
|---|---|---|
| **Total** | 512 tests | `pytest --collect-only` |
| **Unitarios / Unit** | 317 | 317/317 pass |
| **Integración / Integration** | 102 | 102/102 pass |
| **E2E** | 60 | 60/60 pass |
| **Stress** | 14 | 14/14 pass (S4.1-S4.7) |
| **Performance** | 9 | 9/9 pass (P6.1-P6.4, nuevo en Paso 6) |
| **SecurityGuard** | 29 | 29/29 pass (SE5.1-SE5.18, nuevo en Paso 5) |
| **Escape** | 2 | 2/2 pass (SE5.17-SE5.18) |
| **SyncStepNames (unit)** | 1 | 1/1 pass (test_sync_step_names.py) |
| **Patch agents (lint_fix + check_env)** | — | Commits `9e3736f`, `215c383`, `958f1ba` — sin tests dedicados nuevos |
| **Plan impl: Fix deadlock MCP + Tool Calling + Excel** | 4 (unit) + 2 (e2e) + 2 (flow) | Nuevos en `349d9eb`: 4 tests unit (resolve_tools_async, _resolve_mcp_tool_async, excel_reader resolver), 2 e2e (tool_calling_real, presupuesto_flow), 1 flow. |
| **Paso 7 — Cierre** | 4 (unit) + 1 (deleted) | Nuevos en `7827d78`: 4 tests unit (validate_input), 2+ tests e2e (GET agente, import seed), tool calling check en Flow.execute, MCP sin parche. `test_real_tool_calling.py` eliminado (duplicado). 2 tests legacy deprecados (skip). |
| **Lint** | — | 0 errores (`ruff check src/ tests/`) |

### Discrepancias Conocidas / Known Discrepancies Plan vs Código
- Resueltas en Pasos 0-3:
  - `list_all()` → `list_tools()` corregido
  - `>=`/`<=`/`==` ya fixeados (`dynamic_flow.py:144-150`)
  - `approval_threshold` no usado en `_run_crew()` — deuda técnica documentada
  - `_on_approved()` marca COMPLETED, no reanuda steps — documentado
- **📝 CORREGIDO (2026-05-05):** Fase "Patch agents" registrada en `proyecto-config.json` con `phase_name: "patch_agents"`, `current_step: "06-ExcelWriterTool"`. HEAD tiene 4 commits bajo "Patch agents" (`64cf7c5` → setup, `9e3736f` → lint, `215c383` → latency skipif, `958f1ba` → sync step names). `proyecto-config.json` actualizado (2026-05-05 via `fap sync-config --fix`).
- **NUEVA: Commit `5f25aac` es huérfano.** `testing / 00-Fix-Post-Certificacion` no es ancestro de HEAD. Contenido (sync_step_names.py, TESTING.md fixes) overlap con `958f1ba`.
- **NUEVA: Plan.md v3.2 Pasos 0 y 4 no ejecutados.** Fix seguridad `registry.py._load_from_db()` (Paso 0) y mover `baseline.py` a `commands/` (Paso 4) están pendientes.
- **NUEVA: `ServiceConnectorTool` ≠ `ServiceConnector`.** `src/tools/service_connector.py` define clase `ServiceConnectorTool` (no `ServiceConnector`). Plan y phase-state refieren nombre incorrecto. Sin impacto funcional — rename cosmético.
- **📝 CORRECCIÓN (2026-05-03):** Commit `349d9eb` archivó análisis NUEVOS para "Paso 3: Tool Calling Real" en `IMPLEMENTED/testing/00-Fix-Post-Certificacion/`, sobrescribiendo análisis previos de "Alinear nombres". Contenido actual = análisis multi-agente Paso 3 del plan.md (Fix MCP deadlock, Registrar agente, Tool calling real).
- **📝 CORREGIDO (2026-05-05):** `proyecto-config.json` actualizado con `phase_name: "patch_agents"`, `current_step: "06-ExcelWriterTool"` via `fap sync-config --fix`. Desincronización desde commit `64cf7c5` resuelta.
- **📝 CORRECCIÓN (2026-05-03):** `DEVS/sugest.md` documenta ID-002 (imports no utilizados en excel_writer.py) e ID-003 (BaseFlowState en presupuesto_flow.py). Ambos fueron corregidos antes de commit `349d9eb` — lint 0 confirma. Sugest.md contiene análisis previo no actualizado.
- **📝 CORREGIDO (2026-05-05):** `proyecto-config.json` `current_step` era `04-flow-execute-con-llm-real` (no reflejaba Paso 6 completado en `349d9eb` ni análisis Paso 7 archivado en `7827d78`). ✅ Corregido a `"06-ExcelWriterTool"` via `fap sync-config --fix`.
- **📝 CORRECCIÓN (2026-05-05):** Análisis archivado bajo `IMPLEMENTED/patch_agents/06-ExcelWriterTool/` pero su contenido es análisis de **Paso 7 (Cierre)**, no Paso 6 (ExcelWriterTool). Esto ocurre porque el `current_step` del config (04-flow-execute-con-llm-real) no coincide con el último paso completado real (06-ExcelWriterTool). Sin impacto funcional — el análisis fue validado (✅ APROBADO, 25/25).

---

## 3. Contratos Técnicos Vigentes / Active Technical Contracts

### Patrones de Código / Code Patterns
- **RLS:** `tenant_isolation` via `org_id::text` contra `app.org_id` (verificado en migraciones)
- **Registry (Tools):** Singleton `ToolRegistry`. Decorador `@tool_registry.register`. API: `list_tools()`, `get()`, `register()`, `get_metadata()`, `clear()`, `invalidate_tenant_cache()`
- **Registry (Flows):** `FlowRegistry` en `src/flows/registry.py`. Decorador `@flow_registry.register` o `@register_flow("name")`.
- **Excel Tools (Aybar):** `ExcelReaderTool` y `ExcelWriterTool` en `src/tools/`. Lee/escribe .xlsx en `PROJECT-Aybar/`. `openpyxl` backend. BaseTool con `BASE_DIR = Path(...)/PROJECT-Aybar`.
- **ToolCallTracer:** Wrapper `tool._run` con `@functools.wraps` para contar llamadas. `trace()` aplica wrapper, `restore()` lo remueve. Usado en `BaseCrew.run()` y `run_async()`.
- **Resolución Async MCP:** `resolve_tools_async()` llama `_resolve_mcp_tool_async()` que usa `MCPPool.get_tools()` con await. Sync mode skipea MCP con warning.
- **MCP Resolution:** Prefijo `mcp:{server}:{tool}`. Solo paths asíncronos
- **Auth:** Middleware en `src/api/middleware.py`. JWKS + validación membresía
- **Seguridad (skills):** AST scan + RestrictedPython + restricted `__import__` con `ALLOWED_MODULES`
- **Sandbox execution:** `SecurityGuard.execute()` usa `_create_safe_builtins()`. System bundles bypass RestrictedPython
- **CLI:** Typer app en `src/cli/main.py`. Comandos via `app.command()` o `app.add_typer()`
- **last_tool_calls property:** `BaseFlow.last_tool_calls` (`src/flows/base_flow.py:430-440`) delega a `_last_crew.get_last_tool_calls()`. Retorna `{}` si no hay crew. Nuevo en commit `7827d78`.
- **Agent by-role endpoint:** `GET /api/agents/by-role/{role}` (`src/api/routes/agents.py:31-40`). Consulta `agent_catalog` con `get_tenant_client`. Nuevo en commit `7827d78`.
- **Seed bundle tooling:** `scripts/seed_bundle.py`. Copia bundle → `data/seed/` + recalcula SHA256. Uso: `python scripts/seed_bundle.py`. Nuevo en commit `7827d78`.

### Esquemas DB Clave / Key DB Schemas (verificado en migraciones)
- `agent_catalog` (004): id, org_id, name, description, allowed_tools text[], code, soul_json jsonb, version, enabled
- `org_mcp_servers` (005): id, org_id, name, command text[], env_secrets jsonb, enabled
- `workflow_templates` (006): id, org_id, name, definition jsonb, tags text[], enabled
- `service_catalog` (024): id, org_id, name, base_url, auth_type, config jsonb
- `domain_events` (021-022): id, aggregate_type, aggregate_id, event_type, payload jsonb, correlation_id, created_at (Realtime)
- `bundle_system` (0026): Bundles versionados con hash
- `service_tools` (024): Definiciones de tools TIPO C para ServiceConnector
- `org_service_integrations` (024): Activación de servicios por organización

### Convenciones / Conventions
- Backend: `snake_case` funciones/variables, `PascalCase` clases
- Archivos / Files: `snake_case.py`
- DB: `snake_case` tablas y columnas
- Imports: absolutos (ej: `from src.tools.registry import tool_registry`)
- Tests: `test_*.py` en `tests/unit/`, `tests/integration/`, `tests/e2e/`

### Dependencias Clave / Key Dependencies
- **Directas / Direct:** fastapi>=0.115.0, pydantic>=2.10.0, supabase>=2.10.0, anthropic>=0.40.0, openai>=1.58.0, PyJWT>=2.0.0, httpx>=0.28.0, structlog>=24.4.0, mcp>=1.0.0, RestrictedPython>=7.0, typer>=0.12.0, tenacity>=9.0.0, **openpyxl>=3.1.0** (nuevo en `349d9eb`)
- **Dev:** pytest>=8.3.0, pytest-asyncio>=0.24.0, pytest-mock>=3.14.0, pytest-cov>=6.0.0, pytest-timeout>=1.5.0, ruff>=0.8.0
- **Opcionales / Optional:** crewai>=0.100.0, crewai-tools>=0.20.0

---

## 4. Decisiones de Arquitectura / Architecture Decisions

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

### De Fase VI — testing / Hotfix Post-Certificación (Plan v3.2 — Paso 3)
29. **`fap sync-step-names`:** Herramienta DX para sincronización de nombres de pasos en TESTING.md + CHANGELOG.md. Source configurable: `phase-state` (default) o `plan`. Flags: `--check` (exit 1 si drift), `--fix` (aplica correcciones), `--dry-run`. Previene desincronización documental recurrente sin depender de verificación manual.
30. **Fuente de verdad = fase real (carpetas IMPLEMENTED + phase-state.md), no plan.md hotfix:** Plan.md v3.2 Tarea 3.1 contiene nombres incorrectos para Pasos 4-5. Código real archivado gana sobre especificación del plan.
31. **Scope multi-doc extendido:** CHANGELOG.md incluido en fix, aunque plan.md no lo contempla. Mismo root cause → mismo remedio.

### De Fase "Patch agents" (en progreso, plan v3.2)
32. **`fap lint-fix` como comando dedicado:** `src/cli/commands/lint_fix.py` — corrección autónoma de imports desordenados, no dependiente de `ruff`` directo en terminal. Simplifica DX para CI.
33. **`fap check-env` para pre-requisitos:** `src/cli/commands/check_env.py` — verifica `SUPABASE_URL` + `SUPABASE_ANON_KEY` antes de ejecutar tests de integración. Previene falsos fallos.
34. **Naming de fase inconsistente:** Fase llamada "Patch agents" en commits pero proyecto-config.json aún usa "testing". Sin unified phase context — riesgo de confusión downstream.

### De Implementación plan.md Pasos 1-6 (commit `349d9eb`)
35. **`resolve_tools_async()` + `_resolve_mcp_tool_async()`:** Variante async de resolución MCP que evita deadlock por `run_coroutine_threadsafe().result()`. Usa `await MCPPool.get().get_tools()` directamente. Sync mode skipea MCP con warning (backward compat).
36. **`ToolCallTracer` como utilidad interna:** No clase separada en su propio módulo. Integrada en `BaseCrew` como wrapper de `tool._run`. `trace()`/`restore()` para limpieza post-ejecución. `get_last_tool_calls()` para verificación en tests.
37. **ExcelReaderTool + ExcelWriterTool como `OrgBaseTool`:** Heredan de `OrgBaseTool` con `org_id` para tenant isolation. `BASE_DIR = Path(...)/PROJECT-Aybar/` como destino fijo. `openpyxl` como backend (no pandas — evitar dependencia pesada).
38. **`PresupuestoFlow` registrado como `@register_flow("presupuesto")`:** Sigue patrón existente de `ArchitectFlow`. `validate_input()` propio. `_run_crew()` crea `BaseCrew(role="presupuestador")` y ejecuta con datos del input. Output: `{"result": str(crew_output), "flow_type": "presupuesto"}`.
39. **`fap test-tool-call` como DX:** Sigue patrón `check_env.py`. Dos modos: `--dry-run` (solo verifica config sin LLM) y full (ejecuta BaseCrew.run_async() con LLM real + ToolCallTracer). Verifica tool_registry + GROQ_API_KEY antes de ejecución.
40. **E2E tool calling sin patches CrewAI:** `test_tool_calling_real.py` salva clases reales `_REAL_CREW/_REAL_TASK/_REAL_AGENT` a nivel módulo ANTES de imports que disparan `global_llm_mock`. Contra-parchea con `patch("crewai.Crew", _REAL_CREW)` dentro del test. Verifica `tool_calls >= 1` como criterio de aprobación.

### De Análisis Paso 7 — Cierre (archivado en `7827d78`)
41. **`BaseFlow.last_tool_calls` como property:** Property simple que retorna `{}` por defecto. No modifica `_run_crew()`. Sin impacto en flujos existentes. Unánime entre 4 agentes.
42. **`seed_bundle.py` sobre `fap seed-import`:** Script standalone > CLI command. Menos overhead (sin registro en `cli/main.py`). Suficiente para operación única.
43. **Opción B para tests legacy (deprecar):** Unánime. Tests legacy dan falso positivo de tool calling. `test_tool_calling_real.py` ya cubre con mejor calidad.
44. **Eliminar `test_real_tool_calling.py`, actualizar `test_real_agent_pipeline.py`:** `test_real_agent_pipeline.py` prueba pipeline completo (no solo tool calling). Mayor cobertura mantenerlo.
45. **Ruta `GET /api/agents/by-role/{role}`:** Endpoint real agregado (plan asumía `GET /api/agents/{role}` sin verificar). Verificado en código.
46. **Mover tests validate_input de e2e a unit:** Tests de validación pura pertenecen a `tests/unit/`. E2E conserva solo integración.

### Deuda técnica documentada (nuevo `DEVS/sugest.md`)
- **ID-001:** `proyecto-config.json` desactualizado — `phase_name: "testing"` en vez de fase activa. ✅ RESUELTO (2026-05-05 via `fap sync-config --fix`).
- **ID-002:** `excel_writer.py` imports no utilizados — F401. Corregido en `349d9eb` (lint 0). Sugest.md contiene análisis previo a fix.
- **ID-003:** `presupuesto_flow.py` import `BaseFlowState` sin usar — F401. Corregido en `349d9eb` (lint 0).

### Correcciones al Plan / Plan Corrections
- `plan.md:21`: `list_all()` → `list_tools()` (P0.4)
- `plan.md:83`: `>=, <=, ==` "NO implementados" → "se rompen silenciosamente" (ya fixeado en Paso 2)
- Plan dice "warning in log" → código usa `logger.error` (E3.1)
- Plan asume `resume()` reanuda steps → `_on_approved()` marca COMPLETED
- `phase-state.md` línea 20 describe Paso 4 como "Hardening de API Pública" pero plan.md define "Tests de Estrés y Robustez". Desincronización documentada en análisis Paso 4.
- Plan.md §5.1 lista SE5.1-SE5.10 como "expandir test_security_guard.py" y SE5.17-SE5.18 como archivo nuevo. Implementación sigue el plan al 100%.
- Hotfix plan.md v3.2 Tarea 3.1 propone nombres Pasos 4-5 que NO coinciden con fase real: plan dice "Estrés y Condiciones de Borde" / "Seguridad — Hardening" pero fase real usó "Tests de Estrés y Robustez" / "Tests de Seguridad — Hardening". Resuelto: usar fase real (carpetas IMPLEMENTED + phase-state.md) como fuente de verdad.
- Plan.md v3.2 no incluye CHANGELOG.md en scope del fix de nombres. Extendido para cobertura documental completa.
- **📝 CORRECCIÓN (2026-05-02):** `src/tools/service_connector.py` clase real es `ServiceConnectorTool`, no `ServiceConnector`. No afecta funcionalidad — rename cosmético para alinear con documentación.
- **📝 CORRECCIÓN (2026-05-02):** `proyecto-config.json` desactualizado. Fase activa es "Patch agents" (3 pasos completados), no "testing" (completada). Config necesita `phase_name`, `current_step`, `steps_completed` actualizados.

---

## 5. Registro de Pasos Completados / Completed Steps Log

### Fase VI — testing

| Paso | Estado / Status | Archivos Archivados En / Archived At | Commit | Decisiones Tomadas / Decisions Made | Notas / Notes |
|---|---|---|---|---|---|
| 0 — Auditoría de Línea Base | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/00-Auditoria-de-Linea-Base/` | `17349a5` | D1-D6. `baseline-check` creado. SE5.13-SE5.16 implementados. | Lint 0. Suite base 100%. Validación: ✅ |
| 1 — Cobertura Unitaria de Gaps Críticos | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/01-Cobertura-Unitaria-de-Gaps-Criticos/` | `2e90aec` | 30 tests unitarios. DX `fap test-step 1`. | 30/30 pass. Validación: ✅ |
| 2 — Tests de Integración | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/02-Tests-de-Integracion/` | `b5d23af` | Fix parser `>=`/`<=`/`==`. 3 resilience + 3 handover + 3 condicional. DX `fap test-step 2`. | Fix approval operators. Lint I001 corregido. Validación: ✅ |
| 3 — E2E Flujos Completos con Mocks | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/03-E2E-Flujos-Completos-con-Mocks/` | `7a750ca` | 4 tests E2E (Degraded MCP, HITL, 3-step Handover). DX `fap test-step 3`. | 4/4 pass. Lint 0. Validación: ✅ |
| 4 — Tests de Estrés y Robustez | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/04-Tests-de-Estres-y-Robustez/` | `af6b16f` | 14 tests stress (S4.1-S4.7). DX `fap stress-bench`. `re.compile` en sanitizer. pytest-timeout. | 14/14 pass. Lint 0. 6 análisis + validación archivados. Validación: ✅ |
| 5 — Tests de Seguridad | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/05-Tests-de-Seguridad/` | `534481f` | 14 tests (SE5.1-SE5.12, SE5.17-SE5.18). DX `fap security-audit`. Fix `safe_builtins` en `run.py` + `local_executor.py`. `fap test-step 5`. | 14/14 pass. Lint 0. 6 análises + 1 validación archivados. Validación: ✅ |
| 6 — Performance & Observabilidad | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/06-Performance-Observabilidad/` | `a07dfea` | 4 benchmarks (P6.1-P6.4). DX `fap perf-check` con --baseline/--compare/--json/--verbose/--no-warmup. Reports JSON en `reports/`. Fixtures autouse en conftest para aislamiento. Correcciones FINAL aplicadas (sin input_data, _is_circuit_open directo). | 9/9 pass. Lint 0. Validación: ✅. |
| 7 — Documentación y Cierre | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/07-Documentacion-y-Cierre/` | `64e1834` | TESTING.md + CHANGELOG.md creados. Makefile targets `test-all`/`test-fast`/`coverage` + `uv run`. `fap phase-close` generalizado Fase VI. `fap test-step` extendido pasos 4/6/7. Coverage config pyproject.toml (75%). README actualizado. | 14/14 criterios MVP cumplidos. Validación: ✅ |
| 00-Fix-Post-Certificacion (Hotfix v3.2 — Paso 3) | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/00-Fix-Post-Certificacion/` | `5f25aac` | `sync_step_names.py` creado. TESTING.md + CHANGELOG.md corregidos (Paso 3-5 nombres reales de fase). DX `fap sync-step-names --check --source phase-state`. Correcciones al plan: nombres plan.md v3.2 Tarea 3.1 no coinciden con fase real. | 6/6 agentes analizados. Validación: ✅ APROBADO. 9/9 criterios. Lint 0. |

### Fase "Patch agents" — Implementación plan.md Pasos 1-6

| Paso | Estado / Status | Archivos Archivados En / Archived At | Commit | Decisiones Tomadas / Decisions Made | Notas / Notes |
|---|---|---|---|---|---|
| 00-Fix-Post-Certificacion — Análisis Paso 3: Tool Calling Real | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/00-Fix-Post-Certificacion/` | `349d9eb` | 6 archivos multi-agente archivados (analisis-3-ds, glm, FINAL, paso-3-qwen, paso3-kimi, validacion). Análisis cubre: Fix MCP deadlock, Registrar agente, Tool calling real, ExcelWriterTool. | Nuevos análisis (2026-05-03) sobrescriben previos. Lint 0 previa a commit. |
| Plan Paso 1 — Fix deadlock MCP | ✅ COMPLETADO | — | `349d9eb` | `resolve_tools_async()` + `_resolve_mcp_tool_async()` en factory.py. Tests: TestResolveToolsAsync (6), TestResolveMCPToolAsync (3). | Sync mode skipea MCP. Async mode usa await directo. 0 deadlock. |
| Plan Paso 2 — Registrar agente presupuestador | ✅ COMPLETADO | — | `349d9eb` | `PresupuestoFlow(BaseFlow)` registrado como `@register_flow("presupuesto")`. Test: `test_flow_registered`, `test_validate_input`, `test_execute_with_real_llm`. | Flow visible en FlowRegistry. |
| Plan Paso 3 — Tool calling real | ✅ COMPLETADO | — | `349d9eb` | `ToolCallTracer` en BaseCrew. `get_last_tool_calls()`. `fap test-tool-call`. `test_tool_calling_real.py` sin patches CrewAI. | ToolCallTracer wrapper tool._run. E2E requiere GROQ_API_KEY. |
| Plan Paso 6 — ExcelWriterTool | ✅ COMPLETADO | — | `349d9eb` | `ExcelWriterTool(OrgBaseTool)` con `@register_tool("excel_writer")`. Soportes overwrite/append. openpyxl backend. | Dependencia `openpyxl>=3.1.0` agregada. |
| 00 — Fix Seguridad `registry.py` (Paso 0 plan) | ⏳ PENDIENTE | — | — | Parchear `_load_from_db()` usar `_create_safe_builtins()`. Agregar tests regresión (R0.1-R0.3). | Crítico: vector `__import__` sin restricción en `registry.py`. |
| 04 — Mover `baseline.py` (Paso 4 plan) | ⏳ PENDIENTE | — | — | Mover `src/cli/baseline.py` → `src/cli/commands/baseline_check.py`. Actualizar import en `main.py`. | Consistencia estructural CLI. |
| Plan Paso 7 — Cierre (Análisis multi-agente) | ✅ ANÁLISIS COMPLETADO | `DEVS/IMPLEMENTED/patch_agents/06-ExcelWriterTool/` | `7827d78` | 6 decisones (D41-D46): `last_tool_calls`, `seed_bundle.py`, deprecar tests legacy, eliminar duplicado, endpoint by-role, mover validate_input a unit. | ✅ APROBADO — 25/25 criterios. 8 sub-pasos (7.1-7.8) listos para implementar. |
| Plan Paso 8 — Sincronizar proyecto-config con fase activa | ✅ COMPLETADO | `DEVS/IMPLEMENTED/patch_agents/06-ExcelWriterTool/` | `3c47fe6` | `fap sync-config` CLI. Correcciones: current_step→06-ExcelWriterTool, steps_total→8, steps_pending→4. plan.json step 08 agregado. phase-state.md §2 refs actualizadas. sugest.md limpiado. | ✅ APROBADO — 9/10 criterios. Lint 0. |

### Fase "Patch agents" — Hotfix Post-Certificación (previo, Plan v3.2 hotfix)

| Paso | Commit | Decisiones Tomadas / Decisions Made | Notas / Notes |
|---|---|---|---|
| Setup — Nuevo contexto de fase | `64cf7c5` | `proyecto-config.json` enriquecido. `plan.md` reescrito v3.2 Hotfix. | Config mantiene `phase_name: "testing"`. |
| 01 — Fix Lint I001 | `9e3736f` | `fap lint-fix`. Ruff auto-fix imports. | Análisis en `IMPLEMENTED/testing/00-Fix-Post-Certificacion/`. |
| 02 — Fix test_3_5_latency.py | `215c383` | `@pytest.mark.skipif`. `fap check-env`. | Test SKIPPED sin Supabase real. |
| 03 — Alinear nombres pasos TESTING.md | `958f1ba` | `sync_step_names.py`. TESTING.md/CHANGELOG.md corregidos. | Nombres alineados con fase real. |

### Fase V — details4agents

| Paso | Commit | Carpeta Archivado / Archived At | Nota / Note |
|---|---|---|---|
| 1 | `c9f8eff` | `01-mejora-infraestructura-herramientas/` | MCP Bridging |
| 2 | `c9f8eff` | `02-Upgrade-del-Cerebro/` | Prompt Architect |
| 3 | `4f61392` | `03-Suite-de-los-6-Escenarios/` | 6 Escenarios E2E |
| 4 | `c83fef5` | `04-Documentacion-y-Cierre/` | Certificación Final |

---

## 6. Criterios Generales de Aceptación MVP / MVP Acceptance Criteria

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
- [x] **Paso 7:** TESTING.md ✅, CHANGELOG.md ✅, Makefile `test-all`/`test-fast`/`coverage` ✅, `uv run` cross-platform ✅, `fap phase-close` generalizado ✅, `fap test-step` pasos 4/6/7 ✅, coverage threshold 75% ✅, README actualizado ✅, lint 0 ✅
- [x] **Hotfix Paso 3 (Plan v3.2):** `fap sync-step-names` creado ✅. TESTING.md:66,70,72,78 corregidos ✅. CHANGELOG.md:28,32,36 corregidos ✅. `fap sync-step-names --check --source phase-state` → exit 0 (0 discrepancias) ✅. Correcciones al plan: nombres reales de fase vs nombres erróneos en plan.md v3.2 Tarea 3.1 ✅. Lint 0 ✅

**Progreso Fase VI / Phase VI Progress: 100% (8/8 pasos + Hotfix post-certificación). Fase CERRADA.**

**Progreso Fase "Patch agents" (hotfix): 4/4 pasos completados (Setup, 01, 02, 03).**

**Progreso plan.md Pasos 1-6: 4/6 completados (Paso 1 Fix deadlock ✅, Paso 2 Registrar agente ✅, Paso 3 Tool calling ✅, Paso 6 ExcelWriter ✅). Pendientes: Paso 4 (Flow.execute real), Paso 5 (Flow registrado formal — PresupuestoFlow ya registrado, test E2E ok).**

**Progreso Paso 7 — Cierre: Análisis ✅ (commit `7827d78`, archivado en `IMPLEMENTED/patch_agents/06-ExcelWriterTool/`). Pendiente: implementación de 8 sub-pasos.**

**Progreso Paso 8 — Sincronizar config: ✅ COMPLETADO (commit `3c47fe6`). Config sincronizado, `fap sync-config` funcional, plan.json actualizado, phase-state.md referencias corregidas. Validación: ✅ APROBADO.**

### Checklist Fase "Patch agents" (hotfix plan v3.2):
- [x] **Setup:** `proyecto-config.json` enriquecido ✅ (commit `64cf7c5`)
- [x] **Paso 1:** Ruff auto-fix imports ejecutado ✅ (commit `9e3736f`)
- [x] **Paso 2:** `test_3_5_latency.py` → SKIPPED sin Supabase real ✅ (commit `215c383`)
- [x] **Paso 3:** TESTING.md nombres alineados con fase real ✅ (commit `958f1ba`)

### Checklist plan.md Pasos 1-6 (implementados en `349d9eb`):
- [x] **Paso 1 (Fix deadlock MCP):** `resolve_tools_async()` + `_resolve_mcp_tool_async()` en factory.py ✅. 9 tests unitarios (TestResolveToolsAsync + TestResolveMCPToolAsync). Sync skipea MCP con warning.
- [x] **Paso 2 (Registrar agente):** `PresupuestoFlow(@register_flow)` creado ✅. `validate_input()` verifica tipo_evento/pax/fecha. E2E test con LLM real en test_presupuesto_flow.py.
- [x] **Paso 3 (Tool calling real):** `ToolCallTracer` en BaseCrew ✅. `get_last_tool_calls()` verifica llamadas. `fap test-tool-call` DX tool. E2E test sin patches CrewAI en test_tool_calling_real.py.
- [x] **Paso 6 (ExcelWriterTool):** `ExcelWriterTool(OrgBaseTool)` con `@register_tool` ✅. Overwrite/append. openpyxl backend. Dependencia `openpyxl>=3.1.0` añadida.
- [ ] **Paso 4 (Flow.execute real):** Pendiente — ejecutar `Flow.execute()` completo con state transitions + event emission + persist_state.
- [ ] **Paso 5 (Flow registrado formal):** PresupuestoFlow ya registrado + test E2E ok. Pendiente verificar multi-turn + webhook trigger.
- [x] `proyecto-config.json` actualizado con `phase_name` y `current_step` correctos (via `fap sync-config --fix`).
- [x] **Paso 8 (Sincronizar config con fase activa):** `fap sync-config` CLI creado ✅. Config corregido (current_step→06-ExcelWriterTool, steps_total→8, steps_pending→4) ✅. plan.json step 08 agregado ✅. phase-state.md §2 referencias actualizadas ✅. sugest.md limpiado ✅. Lint 0 ✅. Validación: ✅ APROBADO.

### Checklist Paso 7 — Cierre (análisis completado en `7827d78`):
- [x] **Análisis multi-agente completado:** 6 análisis (ds, Y, mm, kilo) + FINAL + validación ✅
- [x] **Validación:** ✅ APROBADO — 25/25 criterios MVP cumplidos. Lint 0. 41 tests pass, 1 skip.
- [x] **Correcciones al plan (4):** BaseFlow.last_tool_calls, endpoint by-role, validate_input mover a unit, seed_bundle.py tooling ✅
- [x] **Archivado en:** `DEVS/IMPLEMENTED/patch_agents/06-ExcelWriterTool/` ✅ (commit `7827d78`)
- [ ] **Pendiente implementación:** 8 sub-pasos (7.1 Remover parche MCP test, 7.2 Bundle seed, 7.3 Test GET agente API, 7.4 Tool calling check Flow.execute, 7.5 Consolidar tests, 7.6 Deprecar legacy, 7.7 Test import seed, 7.8 Test unitario validate_input)

### Deuda técnica / Technical debt:
- **ID-001:** `proyecto-config.json` desactualizado — `phase_name: "testing"` persiste (debe ser `patch_agents`). `current_step: "04-flow-execute-con-llm-real"` no refleja Paso 6 completado ni Paso 7 análisis archivado. ✅ RESUELTO (2026-05-05 via `fap sync-config --fix`).
- **ID-002/ID-003:** Sugest.md documenta F401 lint en excel_writer y presupuesto_flow — corregidos en `349d9eb` (lint 0). Sugest.md pre-fix.
- **Riesgo:** Commit `5f25aac` huérfano. `proyecto-config.json` inconsistente desde `64cf7c5`.

### Herramientas DX detectadas/propuestas
- `fap test-tool-call` — Verifica tool calling con dry-run o LLM real (NUEVO en `349d9eb`)
- `scripts/seed_bundle.py` — Copia bundle a `data/seed/`, recalcula SHA256, verifica integridad. Uso: `python scripts/seed_bundle.py` (NUEVO en `7827d78`)

**Criterios fuera de alcance MVP / Out of MVP scope:** retry con backoff, caching, rate limiting, logging avanzado, optimización performance extrema.
