# Estado de Fase: Certificación Técnica Profunda (QA) — testing

> **Fecha:** 2026-05-01
> **Estado:** 🔄 EN PROGRESO (testing) — 1/7 pasos completados
> **Último Archivado:** `DEVS/IMPLEMENTED/testing/00-Auditoria-de-Linea-Base/`
> **Commit:** `58e4209` — `testing / 00-Auditoria-de-Linea-Base`

---

## 1. Resumen de Fase

**Fase:** `testing`
**Objetivo:** Certificación Técnica Profunda (QA) — verificar baseline del proyecto, cubrir gaps de testing, garantizar estabilidad y seguridad antes de producción.

**Pasos:**
- ✅ **Paso 0: Auditoría de Línea Base (Pre-flight).** Baseline: importabilidad, suite existente 100%, lint 0, tool registry audit, fixtures verificados. Herramienta DX `fap baseline-check` creada. Vulnerabilidad `__import__` corregida (restricted import + allowlist). Diagnóstico SE5.13-SE5.16 implementado. Plan.md corregido (P0.4 `list_all()` → `list_tools()`, documentación `>=`/`<=`/`==`).
- 🔲 **Paso 1:** Cobertura Unitaria de Gaps Críticos
- 🔲 **Paso 2:** Tests de Integración (MCP resilience, handover, approval)
- 🔲 **Paso 3:** Tests E2E de Flujos Multi-Agente
- 🔲 **Paso 4:** Tests de Estrés y Robustez
- 🔲 **Paso 5:** Tests de Seguridad
- 🔲 **Paso 6:** Performance & Observabilidad
- 🔲 **Paso 7:** Documentación y Cierre

**Dependencias entre pasos:**
- Paso 0 → Todos (gate: baseline debe pasar)
- Paso 5 (SE5.13-SE5.16) ya ejecutado como parte de Paso 0 (diagnóstico `__import__`)
- Pasos 1→7 secuenciales con superposición posible

---

## 2. Estado Actual del Proyecto

### Rutas Críticas (de `proyecto-config.json`)
- `paths.root:` `D:\Develop\Personal\FluxAgentPro-v2`
- `paths.backend:` `src/`
- `paths.migrations:` `supabase/migrations/`
- `paths.tests:` `tests/`
- `paths.cli:` `src/cli/`
- `paths.devs:` `DEVS/`
- `paths.devs_in_progress:` `DEVS/IN_PROGRESS/` (vacío — archivado)
- `paths.devs_implemented:` `DEVS/IMPLEMENTED/`

### Stack Tecnológico
- **Backend:** Python (>=3.12, <3.14) + FastAPI (>=0.115.0)
- **Frontend:** TypeScript + Next.js (dashboard/)
- **DB:** Supabase (PostgreSQL) + queries directas + RPC
- **Auth:** PyJWT (ES256/HS256) via middleware
- **Agentes:** CrewAI (opcional) + MCP (Stdio/SSE)
- **Package Manager:** uv (Python) / npm (frontend)
- **Runtime:** Python >=3.12, <3.14

### Implementado y Funcional (Verificado contra código)

| Componente | Archivo(s) | Estado | Descripción |
|---|---|---|---|
| **AgentFactory** | `src/crews/factory.py` | ✅ | `resolve_tools()` con MCP + `create_agent_async()`. |
| **ArchitectFlow** | `src/flows/architect_flow.py` | ✅ | Generación avanzada bundles con MCP y ServiceConnector. |
| **MCPPool** | `src/tools/mcp_pool.py` | ✅ | Circuit breaker + tenacity retries. |
| **ServiceConnector** | `src/tools/service_connector.py` | ✅ | Integraciones HTTP via `service_catalog`. |
| **DynamicWorkflow** | `src/flows/dynamic_flow.py` | ✅ | Ejecución multi-paso. Bug conocido: `>=`/`<=`/`==` se rompen silenciosamente (fix en Paso 2.3). |
| **ToolRegistry** | `src/tools/registry.py` | ✅ | API `list_tools()` (corregido: no `list_all()`). |
| **SecurityGuard** | `src/services/security_guard.py` | ✅ | AST scan + RestrictedPython. Vulnerabilidad `__import__` corregida: `_create_safe_builtins()` con restricted import + ALLOWED_MODULES. Doble vector (execute + _verify_compilation) protegido. |
| **CLI (fap)** | `src/cli/main.py` | ✅ | 14 comandos: `init`, `login`, `validate`, `package`, `publish`, `run`, `scaffold`, `dev`, `export-agents`, `validate-tools`, `validate-architect-output`, `test-scenarios`, `phase-close`, **`baseline-check`** (nuevo en Paso 0). |
| **EventStore** | `src/events/store.py` | ✅ | Append síncrono + asíncrono de eventos de dominio. |
| **BundleManager** | `src/services/bundle_manager.py` | ✅ | Carga remota + validación + atomicidad. |
| **BaseCrew** | `src/crews/base_crew.py` | ✅ | Resolución de tools con MCP. |
| **FlowRegistry** | `src/flows/registry.py` | ✅ | Registro de flujos dinámicos. |

### Estructura de Carpetas
```
src/
├── api/          # FastAPI + Middleware + Routes
├── cli/          # Comandos Typer (fap) — baseline-check añadido
├── connectors/   # Conectores externos
├── crews/        # Agent Factory + Base Crews
├── db/           # Supabase + Vault + Memory
├── events/       # Event Store (domain events)
├── flows/        # Architect, Dynamic, Multi-Crew, Registry
├── guardrails/   # Guardrails de seguridad
├── mcp/          # Servidor MCP + Bridge Flow-to-Tool
├── scheduler/    # Jobs programados
├── scripts/      # Scripts utilitarios
├── services/     # Bundle Manager, Security, Warmup
├── state/        # State management
├── tools/        # Registry, MCP Pool, Service Connector
└── utils/        # Utilidades varias
```

### Tests (verificado)
- **Total suite:** 429 tests colectados (`pytest --collect-only`)
- **Unitarios:** 263/263 pass (incluyendo 15 de `test_security_guard.py` con SE5.13-SE5.16 nuevos)
- **Integración:** 84/84 pass, 8 skipped (4 latency con DB presente, 4 excluidos)
- **Lint:** 0 errores (`ruff check src/ tests/`)
- **Coverage:** No medido aún (Paso 7)

---

## 3. Contratos Técnicos Vigentes

### Patrones de Código
- **RLS:** `tenant_isolation` via `org_id::text` contra `app.org_id` (verificado en migraciones: `004_agent_catalog.sql`, `011_bartenders_config.sql`)
- **Registry (Tools):** Singleton `ToolRegistry` en `src/tools/registry.py:272`. Decorador `@tool_registry.register`. API: `list_tools()`, `get()`, `register()`, `get_metadata()`, `clear()`, `invalidate_tenant_cache()`
- **Registry (Flows):** `FlowRegistry` en `src/flows/registry.py`. Decorador `@flow_registry.register`
- **MCP Resolution:** Prefijo `mcp:{server}:{tool}`. Solo paths asíncronos
- **Auth:** Middleware en `src/api/middleware.py`. JWKS + validación membresía. `verify_jwt` + org isolation
- **Seguridad (skills):** AST scan (`security_guard.py:182`) + RestrictedPython + restricted `__import__` con `ALLOWED_MODULES` y `FORBIDDEN_MODULES`
- **Sandbox execution:** `SecurityGuard.execute()` usa `_create_safe_builtins()` con restricted `__import__` (allowlist). System bundles bypass RestrictedPython
- **CLI:** Typer app en `src/cli/main.py`. Comandos registrados via `app.command()` o `app.add_typer()`.

### Esquemas DB Clave (verificado en migraciones)
- `agent_catalog` (004): `id uuid, org_id, name, description, allowed_tools text[], code, soul_json jsonb, version, enabled`
- `org_mcp_servers` (005): `id uuid, org_id, name, command text[], env_secrets jsonb, enabled`
- `workflow_templates` (006): `id uuid, org_id, name, definition jsonb, tags text[], enabled`
- `service_catalog` (024): `id uuid, org_id, name, base_url, auth_type, config jsonb`
- `domain_events` (021-022): `id uuid, aggregate_type, aggregate_id, event_type, payload jsonb, correlation_id, created_at` (con Realtime habilitado)
- `bundle_system` (0026): Soporte para bundles versionados con hash.

### Convenciones de Naming
- Backend: `snake_case` funciones/variables, `PascalCase` clases
- Archivos: `snake_case.py`
- DB: `snake_case` tablas y columnas
- Imports: `absolute` (ej: `from src.tools.registry import tool_registry`)
- Tests: `test_*.py` en `tests/unit/`, `tests/integration/`, `tests/e2e/`

### Dependencias Clave
**Directas:** `fastapi>=0.115.0`, `pydantic>=2.10.0`, `supabase>=2.10.0`, `anthropic>=0.40.0`, `openai>=1.58.0`, `PyJWT>=2.0.0`, `httpx>=0.28.0`, `structlog>=24.4.0`, `mcp>=1.0.0`, `RestrictedPython>=7.0`, `typer>=0.12.0`, `tenacity>=9.0.0` (añadida)

**Dev:** `pytest>=8.3.0`, `pytest-asyncio>=0.24.0`, `pytest-mock>=3.14.0`, `ruff>=0.8.0`

**Opcionales:** `crewai>=0.100.0`, `crewai-tools>=0.20.0`

---

## 4. Decisiones de Arquitectura Tomadas

### De Fase V (details4agents)
1. **Resolución Centralizada:** Todo paso de herramientas por `AgentFactory.resolve_tools()`.
2. **Bifurcación Sync/Async:** MCP restringido a paths asíncronos.
3. **Dogfooding DX:** Herramientas CLI usadas para su propio propósito.
4. **Validación Preventiva:** `fap validate-tools` verifica disponibilidad antes de ejecución.

### De Paso 0 (Auditoría de Línea Base)
5. **Nombre DX:** `baseline-check` sobre `preflight` — más descriptivo.
6. **Vulnerabilidad `__import__`:** Opción A del plan — restricted `__import__` con `ALLOWED_MODULES` allowlist. Crea `_create_safe_builtins()`. Reemplaza inyección directa de `__import__` en builtins. Doble vector protegido: `execute()` y `_verify_compilation()`.
7. **Fix `test_3_5_latency`:** Skip condicional via `skipif` + mover a `tests/integration/`.
8. **`tenacity` dependencia directa:** Añadida explícitamente (era transitiva vía `crewai` opcional).
9. **`clean_registry` fixture:** Postergada a Paso 1. Riesgo documentado.
10. **Bug approval rules:** `>=`/`<=`/`==` se rompen silenciosamente. Fix postergado a Paso 2.3.

### Correcciones al Plan
- `plan.md:21`: `list_all()` corregido a `list_tools()` (P0.4)
- `plan.md:83`: `>=, <=, == "NO están implementados"` corregido a `"se rompen silenciosamente (ver Bug Detallado en §2.3)"`

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Decisiones Tomadas | Notas |
|---|---|---|---|---|---|
| 0 — Auditoría de Línea Base | ✅ COMPLETADO | `DEVS/IMPLEMENTED/testing/00-Auditoria-de-Linea-Base/` | `58e4209` | D1-D6 aplicadas. `baseline-check` creado y funcional. SE5.13-SE5.16 implementados. | Lint 0, Unit 263/263, Integration 84/84, 0 🔴 issues. Validación: ✅ APROBADO. |
| 1–6 | 🔲 PENDIENTE | — | — | — | — |
| 7 — Documentación y Cierre | 🔲 PENDIENTE | — | — | — | Incluye `TESTING.md`, `Makefile`, cobertura, `fap phase-close` |

---

## 6. Criterios Generales de Aceptación MVP

- [x] **Paso 0 completado:** Baseline verificada: importabilidad ✅, suite ≥ 347 pass ✅, lint 0 ✅, tool registry audit ✅, fixtures ✅
- [x] **Herramientas DX:** `fap baseline-check` funcional — reduce 5 comandos manuales a 1
- [x] **Correcciones al plan:** D1-D6 aplicadas (no reintroduce bugs del plan original)
- [x] **Vulnerabilidad corregida:** `__import__` restricted con allowlist. SE5.13-SE5.16 pasan (15/15)
- [x] **Código ejecuta sin errores:** Lint 0, tests pass
- [x] **Sin TODOs ni stubs:** Código limpio
- [ ] Pasos 1–7: pendientes

**Criterios fuera de alcance MVP:** retry con backoff, caching, rate limiting, logging avanzado, optimización performance extrema.
