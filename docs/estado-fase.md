# Estado de Fase: Sistema de Importación de Bundles (ZIP) — v3

> 📅 Documento generado: 2026-04-28
> 📝 Modo: ACTUALIZACIÓN (el documento anterior solo cubría T0-T8 Bundle System)

---

## 1. Resumen de Fase

El objetivo de esta fase es eliminar la creación manual de agentes e implementar un sistema seguro y atómico de importación a través de "Bundles" (archivos ZIP), el cual es el único camino de entrada para agentes, flujos y skills en FluxAgentPro-v2.

**Pasos completados:**

| Paso | Descripción | Estado |
|:---|:---|:---|
| T0 | Estabilización de Tests | ✅ Completado |
| T1 | Limpieza Legacy (ArchitectFlow) | ✅ Completado |
| T2 | Setup y Migraciones (026+027) | ✅ Completado |
| T3 | BundleManager (hash, extracción) | ✅ Completado |
| T4 | SecurityGuard (AST + RestrictedPython) | ✅ Completado |
| T5 | ImportService + API `/bundles/import` | ✅ Completado |
| T6 | Refactor ToolRegistry + FlowRegistry híbridos | ✅ Completado |
| T7 | FAP-CLI (init, validate, package, export-agents) | ✅ Completado |
| T8 | Lazy Loading Persistente + Migración Legacy | ✅ Completado |

**Dependencias entre pasos:** T0 → T1 → T2 → T3/T4 (paralelo) → T5 → T6 → T7 → T8

---

## 2. Estado Actual del Proyecto

> [!IMPORTANT]
> **Fase de Bundles FINALIZADA.** Todos los pasos T0-T8 completados. El sistema se encuentra en estado operativo y estable.

### Qué ya está implementado y funcional (verificado contra código):

**Lazy Loading Persistente:**
- `ToolRegistry.get()` (`src/tools/registry.py:75-108`) — búsqueda en 4 niveles: tenant-scoped memory → global memory → DB (`skill_catalog`) → filesystem fallback
- `FlowRegistry.get()` (`src/flows/registry.py:211-236`) — búsqueda en 2 niveles: memory → DB (`workflow_templates`)
- Ambos registros realizan introspección de `org_id` en cada lookup, garantizando aislamiento multi-tenant

**Sistema de Importación Atómica:**
- Tablas `bundle_imports` y `skill_catalog` creadas en migración `0026_bundle_system.sql`
- Función RPC `import_bundle_atomic` definida en `0027_bundle_rpc.sql`
- Endpoint `POST /api/bundles/import` en `src/api/routes/bundles.py`
- `ImportService` orchestrando el pipeline completo (BundleManager → SecurityGuard → RPC)

**Seguridad Runtime:**
- `SecurityGuard.scan_source()` en `src/services/security_guard.py` — AST scanning
- `RestrictedPython.compile_restricted()` integrado en `_load_from_db()` de ambos registries
- Módulos bloqueados: `os`, `subprocess`, `shutil`, `socket`, `eval`, `exec`, `open`, `importlib`

**CLI FAP:**
- `src/cli/main.py` — commands: `init`, `validate`, `package`, `export-agents`
- Comportamiento verificado contra plan: paridad total con validación de seguridad local

**ArchitectFlow Saneado:**
- `src/flows/architect_flow.py` — refactorizado, ya no inserta directamente
- Retorna estructura JSON/Bundle en lugar de ejecutar `db.insert()`
- Conversational endpoint en `src/api/routes/chat.py` — `POST /chat/architect` y `GET /chat/{conversation_id}`

**Patrones de Código Verificados:**
- RLS en migraciones usa `auth.uid()` (NO `app.current_org_id`) — verificado en `008_org_members.sql`, `009_fix_organizations_rls.sql`, `010_service_role_rls_bypass.sql`
- Auth en endpoints: `verify_supabase_jwt` en `src/api/middleware.py` soporta ES256 (JWKS) y HS256 (legacy)
- Scheduler jobs definidos en `src/scheduler/health_check.py` y `src/scheduler/bartenders_jobs.py`

### Qué no existe aún:
- Ningún paso pendiente en el plan MVP. El sistema Bundle está completo.

### Discrepancias Plan vs Código detectadas:
- ⚠️ **Ninguna crítica.** El plan y el código están alineados. Las migraciones `026` y `027` existen exactamente como se planificaron.

---

## 3. Contratos Técnicos Vigentes

### Modelos de datos / schemas (de migraciones reales):

| Tabla | Columnas principales | Archivo de verificación |
|:---|:---|:---|
| `bundle_imports` | `id`, `org_id`, `bundle_name`, `bundle_hash`, `status`, `imported_at`, `error_detail` | `0026_bundle_system.sql:13` |
| `skill_catalog` | `id`, `org_id`, `bundle_id`, `name`, `code_source`, `metadata`, `created_at` | `0026_bundle_system.sql:25` |
| `agent_catalog` | `id`, `org_id`, `role`, `name`, `bundle_id` (FK nullable) | `0026_bundle_system.sql:48` |
| `workflow_templates` | `id`, `org_id`, `flow_type`, `definition`, `is_active` | `006_workflow_templates.sql` |
| `organizations` | `id`, `name`, `slug` | `002_governance.sql` |
| `org_members` | `user_id`, `org_id`, `role` | `008_org_members.sql` |

### Endpoints API existentes (de `src/api/routes/`):

| Ruta | Método | Descripción | Archivo |
|:---|:---|:---|:---|
| `/chat/architect` | POST | Chat conversacional con ArchitectFlow | `chat.py` |
| `/chat/{conversation_id}` | GET | Estado de conversación | `chat.py` |
| `/bundles/import` | POST | Importación atómica de bundles ZIP | `bundles.py` |
| `/flows` | GET/POST | CRUD de workflows | `flows.py` |
| `/flows/{flow_id}/run` | POST | Ejecutar workflow | `flows.py` |
| `/agents` | GET | Listar agentes (solo lectura) | `agents.py` |
| `/approvals` | GET/POST/PATCH | Aprobaciones de tareas | `approvals.py` |
| `/tasks` | GET | Lista de tareas | `tasks.py` |
| `/tickets` | GET/POST | Sistema de tickets | `tickets.py` |

### Patrones de código en uso:

**RLS Pattern:**
```sql
-- Verificado en 008_org_members.sql, 009_fix_organizations_rls.sql
org_id = auth.jwt() -> 'org_id'
user_id = auth.uid()
-- NO usa app.current_org_id (el plan mencionaba este patrón pero no existe en código)
```

**Tool Registry Pattern:**
- Decorator: `@tool_registry.register(name="...", description="...")`
- Lookup: `tool_registry.get(name, org_id=org_id)`
- Lazy DB load: `_load_from_db()` → AST scan → `compile_restricted()` → `exec()`

**Flow Registry Pattern:**
- Decorator: `@flow_registry.register("name", category="...", depends_on=[...])`
- Lookup: `flow_registry.get(name, org_id=org_id)`
- Lazy DB load: `_load_from_db()` → `DynamicWorkflow` wrapper

**Auth Pattern:**
- ES256: JWKS público desde Supabase (`/auth/v1/.well-known/jwks.json`)
- HS256: `SUPABASE_JWT_SECRET` del entorno
- Header: `Authorization: Bearer <token>` + `X-Org-ID: <uuid>`

**Scheduler Pattern:**
- Jobs definidos en `src/scheduler/health_check.py` y `bartenders_jobs.py`
- Registro vía `APScheduler` en `src/scheduler/__init__.py`

### Convenciones de naming:
- Flujos: `PascalCase` → `cotizacion_flow`, `facturacion_flow`
- Herramientas: `snake_case` → `fetch_url_tool`
- Tablas: `snake_case` → `bundle_imports`, `skill_catalog`
- APIs: `kebab-case` en rutas → `/chat/architect`, `/bundles/import`

### Estructura de carpetas del proyecto:
```
src/
├── api/routes/          # Endpoints FastAPI
├── cli/                 # FAP-CLI (Typer)
├── crews/               # CrewAI crews
├── db/                  # Session, vault, conversation_store
├── events/              # Sistema de eventos
├── flows/               # FlowRegistry, DynamicFlow, ArchitectFlow
├── guardrails/          # Guardrails base
├── mcp/                 # MCP server + auth
├── scheduler/           # APScheduler jobs
├── scripts/             # Scripts utilitarios
├── services/            # ImportService, SecurityGuard, BundleManager
├── state/               # State management
└── tools/               # ToolRegistry, demo tools
```

### Dependencias instaladas (de `pyproject.toml`):

**Directas:**
- `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`
- `pydantic>=2.10.0`, `pydantic-settings>=2.6.0`
- `supabase>=2.10.0`
- `anthropic>=0.40.0`, `openai>=1.58.0`
- `PyJWT>=2.0.0` (NO `python-jose` — corrección vs. lo que el plan asumía)
- `python-dotenv>=1.0.0`, `httpx>=0.28.0`, `structlog>=24.4.0`, `litellm>=1.83.0`
- `apscheduler>=3.10.0`, `python-dateutil>=2.9.0`
- `mcp>=1.0.0,<2.0.0`, `sse-starlette>=0.21.0`
- `RestrictedPython>=7.0` ✅ (añadido en T2)
- `typer>=0.12.0`

**Opcionales:**
- `crewai>=0.100.0`, `crewai-tools>=0.20.0` (crew)
- `pytest>=8.3.0`, `pytest-asyncio>=0.24.0`, `pytest-mock>=3.14.0`, `pytest-cov>=6.0.0`, `ruff>=0.8.0` (dev)

---

## 4. Decisiones de Arquitectura Tomadas

### Patrones en uso:
- **Lazy Registry Pattern**: Registro actúa como caché L1, DB como L2
- **Scoping por Prefijo**: `{org_id}:{name}` en memoria para aislamiento tenant
- **Bundle-Driven Lifecycle**: Architect (fábrica) separado de ImportService (persistencia)
- **Security Guard**: Validación AST + RestrictedPython obligatorio para código dinámico

### Decisiones formalizadas:
| Decisión | Justificación | Origen |
|:---|:---|:---|
| Transacciones vía función RPC | PostgREST no soporta `BEGIN...COMMIT` | Análisis Unificado |
| Clave única en agentes: `(org_id, role)` | Upsert consistente con diseño previo | Análisis Unificado |
| Memoria 100% (BytesIO) | Evita path traversal, sin I/O a disco | Análisis Unificado |
| `bundle_id` opcional en `agent_catalog` | `ON DELETE SET NULL` para compatibilidad legacy | Análisis Unificado |

### Correcciones al plan detectadas durante verificación:
- ⚠️ **PyJWT (NO python-jose)**: El plan mencionaba `python-jose` pero el código real usa `PyJWT` (`src/api/middleware.py` importa `decode_jwt` de `src/mcp/auth.py`). Verificado en `pyproject.toml:20`.
- ⚠️ **RLS no usa `app.current_org_id`**: El plan mencionaba este patrón pero las migraciones reales usan `auth.uid()` y `auth.jwt() -> 'org_id'`. El valor `app.current_org_id` NO existe en las migraciones.

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|:---|:---|:---|:---|:---|
| T0 | ✅ | `tests/*.py` | Tests reparados, suite estabilizada | 100% verde |
| T1 | ✅ | `src/flows/architect_flow.py` | Eliminación de `_persist_*`, retorna JSON | Arquitecto = fábrica de bundles |
| T2 | ✅ | `pyproject.toml`, `supabase/migrations/026+027` | RestrictedPython añadido, RPC atómica | Deps verificadas contra código |
| T3 | ✅ | `src/services/bundle_manager.py` | Hash SHA256, extracción in-memory | 4-level lookup |
| T4 | ✅ | `src/services/security_guard.py` | AST + RestrictedPython sandbox | 30s timeout |
| T5 | ✅ | `src/api/routes/bundles.py`, `src/services/import_service.py` | Pipeline completo | RPC `import_bundle_atomic` |
| T6 | ✅ | `src/tools/registry.py`, `src/flows/registry.py` | Híbrido memory+DB+FS | Lazy loading |
| T7 | ✅ | `src/cli/main.py` | `init`, `validate`, `package`, `export-agents` | CLI paritativo |
| T8 | ✅ | `src/tools/registry.py`, `src/flows/registry.py` | Persistencia tras restart | Migración legacy certificada |

---

## 6. Criterios Generales de Aceptación MVP

> ✅ **TODOS LOS CRITERIOS CUMPLIDOS** — Verificado contra código y plan.

| # | Criterio | Verificación |
|:---|:---|:---|
| 1 | `fap-cli validate <archivo.zip>` retorna exit code 0 si hashes y seguridad correctos | ✅ Implementado en `src/cli/main.py` |
| 2 | `POST /api/bundles/import` con ZIP válido retorna HTTP 201 y status 'committed' | ✅ Endpoint en `bundles.py:27` |
| 3 | Bundle alterado post-packaging es rechazado con HTTP 400 "Hash mismatch" | ✅ `BundleManager.verify_hashes()` |
| 4 | Skill con `import os` es bloqueada con HTTP 400 | ✅ `SecurityGuard.scan_source()` |
| 5 | Bundle donde un item falla SQL = 0 cambios en DB | ✅ RPC atómica con `ROLLBACK` |
| 6 | Agente existente se actualiza sin error de clave duplicada | ✅ Upsert por `(org_id, role)` |
| 7 | `restrictedpython>=7.0` instalado | ✅ `pyproject.toml:32` |
| 8 | Lazy loading persiste tras restart | ✅ DB lookup en `get()` |
| 9 | Aislamiento multi-tenant en todos los lookups | ✅ `org_id` propagado en todos los registries |
| 10 | Código ejecuta sin errores ni warnings (Ruff) | ✅ Lint passing |

---

## 7. Estado del Repositorio

**Branch actual:** `main`
**Commits recientes:**
- `40fad2c` — PASO 7. Migración de Agentes y Skills (Legacy)
- `78b2bc9` — PASO 6. Developer Experience (FAP-CLI)
- `426212f` — PASO 5. Pipeline de Importación (Lado Backend)
- `2f931aa` — PASO 4. Persistencia Atómica (Vía PostgreSQL RPC)
- `da6beb3` — PASO 3. Seguridad (Sandboxing Real)

**Cambios sin commitear:**
- `LAST/log_latencia.json` — modificado
- `LAST/validacion.md` — modificado
- `src/api/routes/chat.py` — modificado
- Archivos de análisis en `LAST/` (no rastreados)
