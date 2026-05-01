# Estado Actual de Fase: Certificación Técnica (Fase VI - testing)

> 📅 **Fecha:** 2026-05-01
> 📝 **Estado:** 🔄 EN PROGRESO (Fase VI - testing) — 2/8 pasos completados
> 📦 **Último Archivado:** `DEVS/IMPLEMENTED/testing/01-Cobertura-Unitaria-de-Gaps-Criticos/`
> 📑 **Documento Unificado:** Consolidación de `estado-fase.md` y `phase-state.md`.

---

## 1. Resumen de Fase

**Fase:** `testing`
**Objetivo:** Certificación técnica profunda del código base. Cobertura unitaria de gaps críticos, tests de integración, validación de seguridad, hardening de API, y DX tooling. Suite actual: 455 tests.

**Progreso Actual:**
- ✅ **Paso 0: Auditoría de Línea Base.** Verificación de importabilidad, suite existente, lint, fixtures.
- ✅ **Paso 1: Cobertura Unitaria de Gaps Críticos.** 30 tests unitarios nuevos: MCPPool circuit breaker (5), ServiceConnector error paths (7), Approval operators (4), Sanitizer (14). DX tool `fap test-step`.
- ⬜ **Paso 2: Tests de Integración de Flujos Críticos.**
- ⬜ **Paso 3: Validación de Seguridad Profunda.**
- ⬜ **Paso 4: Hardening de API Pública.**
- ⬜ **Paso 5: Tests de Regresión E2E.**
- ⬜ **Paso 6: Documentación de Arquitectura de Testing.**
- ⬜ **Paso 7: DX Final y Automatización CI.**

---

## 2. Estado Actual del Proyecto

### Rutas Críticas
- `paths.backend:` `src/`
- `paths.migrations:` `supabase/migrations/`
- `paths.devs_implemented:` `DEVS/IMPLEMENTED/`
- `paths.tests_unit:` `tests/unit/`

### Stack Tecnológico
- **Backend:** Python (>=3.12) + FastAPI
- **DB:** Supabase (PostgreSQL) + RLS via `org_id`
- **Auth:** PyJWT (ES256/HS256)
- **Agentes:** CrewAI (opcional) + MCP (Stdio/SSE)
- **Testing:** pytest + pytest-asyncio + pytest-mock + pytest-cov

### Implementado y Funcional (Verificado)

| Componente | Archivo(s) | Estado | Descripción |
|---|---|---|---|
| **AgentFactory** | `src/crews/factory.py` | ✅ | `resolve_tools()` con MCP + `create_agent_async()`. |
| **ArchitectFlow** | `src/flows/architect_flow.py` | ✅ | Generación avanzada con soporte MCP y ServiceConnector. |
| **MCPPool** | `src/tools/mcp_pool.py` | ✅ | Circuit breaker (`_is_circuit_open`, `_record_failure`, `_reset_circuit_breaker`) + tenacity retries. |
| **ServiceConnector** | `src/tools/service_connector.py` | ✅ | Integraciones HTTP via `service_catalog`. 6 ramas error con strings descriptivos. Sanitización de output. |
| **DynamicWorkflow** | `src/flows/dynamic_flow.py` | ✅ | Ejecución multi-paso con `_check_approval_rule`. Bug conocido: `>=`/`<=`/`==` no parseados (diferido a Paso 2). |
| **Sanitizer** | `src/mcp/sanitizer.py` | ✅ | `sanitize_output()` — 7 patrones de secreto + estructuras anidadas + passthrough. |
| **CLI (fap)** | `src/cli/` | ✅ | `test-step`, `scaffold`, `run`, `package`, `validate-architect-output`, `test-scenarios`, `phase-close`, `baseline-check`. |
| **SecurityGuard** | `src/services/security_guard.py` | ✅ | Scan AST + RestrictedPython sandboxing. |
| **Test Suite Paso 1** | `tests/unit/test_mcp_pool_circuit.py` | ✅ | 5 tests circuit breaker. 100% pass. |
| **Test Suite Paso 1** | `tests/unit/test_service_connector.py` | ✅ | 7 tests error paths. 100% pass. |
| **Test Suite Paso 1** | `tests/unit/test_approval_operators.py` | ✅ | 4 tests operador `<` y edge cases. 100% pass. |
| **Test Suite Paso 1** | `tests/unit/test_sanitizer.py` | ✅ | 14 tests sanitizer. 100% pass. |
| **DX Tool** | `src/cli/commands/test_step.py` | ✅ | `fap test-step 1` ejecuta 30 tests del paso con un comando. Soporte `--cov`. |
| **DX Tool** | `src/cli/commands/baseline.py` | ✅ | `fap baseline-check` — auditoría de línea base (Paso 0). |

### Discrepancias Conocidas Plan vs Código
- ⚠️ **Bug `>=`/`<=`/`==`:** `dynamic_flow.py:137` solo parsea `>` y `<`. Los operadores compuestos se tratan como `>` (ej: `>=` hace `split(">")` → `float("= 50000")` → ValueError silencioso → False). Fix diferido a Paso 2.
- ⚠️ **`approval_threshold` no usado:** `workflow_definition.py:47` define el campo pero `_run_crew()` no lo referencia. Deuda técnica documentada.

### Estructura de Carpetas
```
src/
├── api/          # FastAPI + Middleware + Routes
├── cli/          # Comandos Typer (fap) — +test_step, +baseline
├── crews/        # Agent Factory + Base Crews
├── db/           # Supabase + Vault + Memory (session.py + vault.py)
├── flows/        # Architect, Dynamic, Multi-Crew
├── mcp/          # Servidor MCP + Sanitizer + Bridge Flow-to-Tool
├── services/     # Bundle Manager + Security
└── tools/        # Registry, MCP Pool, Service Connector
tests/
├── unit/         # +test_mcp_pool_circuit.py, +test_service_connector.py, +test_approval_operators.py, +test_sanitizer.py
├── integration/
└── e2e/
```

---

## 3. Contratos Técnicos y Patrones

### Patrones de Código
- **RLS:** `tenant_isolation` via `org_id::text` contra `app.org_id`.
- **Registry:** Lookup tenant-scoped → global → DB. Decoradores `@tool_registry.register` / `@register_tool`.
- **MCP Resolution:** Prefijo `mcp:{server}:{tool}`. Solo en `async_mode`.
- **Auth:** Middleware con soporte JWKS y validación de membresía.
- **Testing:** `mock_service_client` fixture — parchea `get_service_client` en 8 puntos de import. `time.time` mockeado por test (no fixture global). `MCPPool.reset()` obligatorio entre tests circuit breaker.

### Patrón de Mocking (Paso 1)
- **MCPPool:** `unittest.mock.patch("time.time")` por test. `MCPPool.reset()` en fixture `autouse=True`.
- **ServiceConnector:** `patch("httpx.Client")` para HTTP. `mock_service_client` para DB. `patch("src.tools.service_connector.get_secret")` para Vault.
- **Approval:** `DynamicWorkflow(org_id=...)` instancia directa. Método síncrono puro — sin mocking.
- **Sanitizer:** `sanitize_output()` import directo. Función pura sin IO. Solo edge case parchea `SECRET_PATTERNS`.

### Esquemas DB Clave
- `agent_catalog`: Soporta `allowed_tools` con strings MCP.
- `org_mcp_servers`: Configuración de comandos y secretos para servidores externos.
- `workflow_templates`: Definiciones JSONB para `DynamicWorkflow`.
- `service_tools`: Definiciones de tools TIPO C para ServiceConnector.
- `org_service_integrations`: Activación de servicios por organización.
- `domain_events`: Auditoría de ejecuciones.

### Dependencias (de pyproject.toml)
- **Directas:** fastapi, uvicorn, pydantic, supabase, anthropic, openai, PyJWT, httpx, structlog, apscheduler, mcp, typer, RestrictedPython, watchdog
- **Dev:** pytest, pytest-asyncio, pytest-mock, pytest-cov, ruff
- **Opcionales:** crewai, crewai-tools

---

## 4. Decisiones de Arquitectura

1. **Resolución Centralizada:** Todo paso de herramientas por `AgentFactory.resolve_tools()`.
2. **Bifurcación Sync/Async:** MCP restringido a paths asíncronos para evitar bloqueos.
3. **Dogfooding DX:** Cada paso usa su propia herramienta DX. Paso 0: `fap baseline-check`. Paso 1: `fap test-step 1`.
4. **Validación Preventiva:** `fap validate-tools` verifica disponibilidad antes de ejecución.
5. **Circuit Breaker en MCPPool:** 5 fallos en <60s → circuito abierto. Half-open tras 60s. Reset tras éxito.
6. **Sanitización Obligatoria:** `sanitize_output()` como última línea de defensa (Regla R3). 7 patrones de secreto + recursión en dict/list.
7. **Corrección conftest.py:** `mock_service_client` incluye `src.tools.service_connector.get_service_client` en patch_points. Necesario por patrón de import `from src.db.session import get_service_client` que crea referencia local.

---

## 5. Registro de Pasos (Historial)

### Fase VI — testing

| Paso | Commit | Carpeta Archivado | Nota |
|---|---|---|---|
| 0 | `17349a5` | `DEVS/IMPLEMENTED/testing/00-Auditoria-de-Linea-Base/` | Lint clean, suite base OK, fixtures verificados |
| 1 | `61887e1` | `DEVS/IMPLEMENTED/testing/01-Cobertura-Unitaria-de-Gaps-Criticos/` | 30 tests unitarios + `fap test-step` |

### Fase V — details4agents

| Paso | Commit | Carpeta Archivado | Nota |
|---|---|---|---|
| 1 | `c9f8eff` | `01-mejora-infraestructura-herramientas/` | MCP Bridging |
| 2 | `c9f8eff` | `02-Upgrade-del-Cerebro/` | Prompt Architect |
| 3 | `4f61392` | `03-Suite-de-los-6-Escenarios/` | 6 Escenarios E2E |
| 4 | `c83fef5` | `04-Documentacion-y-Cierre/` | Certificación Final |

---

## 6. Criterios de Aceptación (Fase VI — testing)

### Paso 1 (COMPLETADO)
- [x] 30/30 tests unitarios pasan (5 MCPPool + 7 ServiceConnector + 4 Approval + 14 Sanitizer)
- [x] Lint: `ruff check src/ tests/` → 0 errores
- [x] `fap test-step 1` funcional y verificado (dogfooding)
- [x] mock_service_client parchea todos los puntos de import necesarios (8 puntos)
- [x] MCPPool.reset() entre tests circuit breaker
- [x] time.time mockeado por test (no fixture global)
- [x] Bug `>=`/`<=`/`==` documentado y diferido a Paso 2

### Paso 0 (COMPLETADO)
- [x] Importabilidad de todos los módulos `src/`
- [x] Suite existente completa: 100% pass
- [x] Lint estricto: 0 errores
- [x] Fixtures conftest.py disponibles y funcionales

### Pendiente
- [ ] `pytest-cov` instalado para verificar thresholds de cobertura

---

**Progreso Fase VI: 25% (2/8 pasos). Próximo: Paso 2 — Tests de Integración de Flujos Críticos.**
