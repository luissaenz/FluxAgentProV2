# Análisis Técnico — Paso 12: Protocolo de Validación y Dogfooding E2E

**Agente:** ds4f
**Fecha:** 2026-05-18
**Fase:** guiAgentGenerator
**Paso:** 12 — Protocolo de Validación y Dogfooding E2E

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | CLI `fap tools list` existe | `src/cli/commands/tools_list.py:29` | ✅ | `list_tools()` function registrada en `main.py:67` como `tools list` |
| 2 | CLI `fap templates seed` existe | `src/cli/commands/templates_seed.py:140` | ✅ | `seed_templates()` function, registrada en `main.py:65` como `templates seed` |
| 3 | CLI `fap agent create` con `--dry-run` | `src/cli/commands/agent_create.py:29` | ✅ | `create_agent()` acepta `dry_run: bool`, registrada en `main.py:86` como `agent create` |
| 4 | CLI `fap templates use` con `--dry-run` | `src/cli/commands/templates_use.py:31` | ✅ | `use_template()` acepta `dry_run: bool`, registrada en `main.py:66` como `templates use` |
| 5 | CLI `fap agent run` existe | `src/cli/commands/agent_run.py:52` | ✅ | `run_agent()` function, registrada en `main.py:87` como `agent run` |
| 6 | CLI `fap bundle validate-payload` existe | `src/cli/commands/bundle_validate_payload.py:24` | ✅ | `validate_payload()` function, registrada en `main.py:84` como `bundle validate-payload` |
| 7 | Script `validate_builder_nav.py` existe | `scripts/validate_builder_nav.py` | ✅ | 227 líneas, 5 checks de integridad del Builder |
| 8 | Endpoint `GET /api/tools/available` existe | `src/api/routes/tools.py:46` | ✅ | `list_available_tools()` con `source` y `category` querys |
| 9 | Endpoint `GET /api/templates` existe | `src/api/routes/templates.py:54` | ✅ | `list_templates()` con `?category=` filter |
| 10 | Endpoint `GET /api/templates/{id}` existe | `src/api/routes/templates.py:74` | ✅ | `get_template()` retorna `TemplateDetailResponse` con `soul_json` |
| 11 | Endpoint `POST /agents` existe | `src/api/routes/agents.py:101` | ✅ | `create_agent()` con upsert por `org_id,role` |
| 12 | Endpoint `POST /agents/{role}/run` existe | `src/api/routes/agents.py:312` | ✅ | `run_agent()` retorna `task_id`, ejecución en background |
| 13 | Endpoint `POST /api/bundles/export` existe | `src/api/routes/bundles.py:199` | ✅ | `export_bundle()` con validación de goal/backstory ≥ 10 chars |
| 14 | Schema `ExportBundleRequest` existe | `src/services/bundle_schemas.py:111` | ✅ | Pydantic model con `bundle_name`, `agents` (1-15), `skills` |
| 15 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql:10` | ✅ | Columnas: id UUID PK, name, description, category, soul_json JSONB, suggested_tools TEXT[], max_iter INT, is_system BOOL |
| 16 | CLI `fap tools list` usa HTTP endpoint? | `tools_list.py:69-71` | ❌ DISCREPANCIA | Lee `ToolRegistry` y `MCPPool` directo vía DB, NO llama `GET /api/tools/available`. No valida el contrato HTTP del endpoint. |
| 17 | CLI `fap templates use --dry-run` valida endpoint? | `templates_use.py:72-95` | ❌ DISCREPANCIA | Lee `agent_templates` directo vía `get_service_client()`, NO llama `GET /api/templates/{id}`. No valida el contrato REST. |
| 18 | `validate_builder_nav.py:65` regex falso positivo | `validate_builder_nav.py:65` | ❌ DISCREPANCIA | `"items={\\s*defaultNavItems}"` — doble backslash literaliza `\s` en vez de ser regex whitespace. Además en TSX real sería `items={defaultNavItems}` sin whitespace, el regex `\\s*` jamás matchearía. |
| 19 | `fap agent create --dry-run` valida endpoint? | `agent_create.py:83-87` | ⚠️ | Solo print del payload. No envía request. Correcto para dry-run pero NO valida que `POST /agents` acepte el payload. |
| 20 | Schema `agent_templates` RLS policies | `030_agent_templates.sql:25-29` | ✅ | SELECT para authenticated, ALL para service_role |
| 21 | E2E tests en `test_builder_scenarios.py` | `tests/e2e/test_builder_scenarios.py` | ✅ | 948 líneas, 6 escenarios (TP-1 a TP-6), 32 tests |

### Discrepancias encontradas

1. **ID-001 (Tools Validation bypass HTTP)**: `fap tools list` no llama `GET /api/tools/available`. Lee ToolRegistry + MCPPool directo. Para dogfooding real del contrato HTTP, debe usarse `httpx` contra el endpoint o integrarse en un test con `TestClient`.

2. **ID-007/009 (Templates Validation bypass HTTP)**: `fap templates use --dry-run` consulta DB directa, no pasa por `GET /api/templates/{id}`. El contrato REST no se valida.

3. **ID-049 (validate_builder_nav.py regex rotto)**: Línea 65: `"items={\\s*defaultNavItems}"` en Python interpreta `\\s` como regex literal backslash+s, no como `\s` (whitespace). La detección siempre falla → falso positivo cuando en realidad el check debería pasar.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema existente**: `agent_templates` (migración 030) y `agent_catalog` (migración 004) ya creadas. No se requieren cambios de schema para este paso.
- ✅ **Tablas involucradas**:
  - `agent_templates` — solo lectura para validación de templates
  - `agent_catalog` — lectura/escritura para validación de agentes
  - `org_mcp_servers` — lectura para MCP tools
  - `tasks` — lectura para polling de ejecución
- ✅ **RLS existente**: `agent_templates` tiene RLS con SELECT público. `agent_catalog` usa tenant isolation vía `org_id`.
- ✅ **Integridad referencial**: No hay FK entre `agent_templates` y `agent_catalog`. El mapping template→agente es puramente lógico (copia de `soul_json`).
- ⚠️ **Índices**: `idx_agent_templates_category` existe en `category`. `idx_agent_templates_system_name` (UNIQUE WHERE is_system) existe. OK.
- ✅ **Datos existentes**: El paso no agrega ni modifica datos. Es puramente de validación.

### Cambios necesarios en schema
Ninguno.

### Impacto en datos existentes
Ninguno.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases verificadas

| Función | Archivo | Línea | Firma real |
|---|---|---|---|
| `list_tools()` | `src/cli/commands/tools_list.py` | 29 | `(org_id: Optional[str], source: Optional[str], json_output: bool) -> None` |
| `seed_templates()` | `src/cli/commands/templates_seed.py` | 140 | `(dry_run: bool, reset: bool) -> None` |
| `create_agent()` | `src/cli/commands/agent_create.py` | 29 | `(role: str, goal: str, backstory: str, org_id: Optional[str], tools: Optional[list[str]], max_iter: int, llm_provider: str, llm_model: str, verbose: bool, reasoning: bool, inject_date: bool, memory: bool, dry_run: bool) -> None` |
| `use_template()` | `src/cli/commands/templates_use.py` | 31 | `(template_name: str, org_id: str, role: Optional[str], goal: Optional[str], backstory: Optional[str], tools: Optional[list[str]], max_iter: Optional[int], dry_run: bool) -> None` |
| `run_agent()` | `src/cli/commands/agent_run.py` | 52 | `(role: str, message: str, org_id: Optional[str], watch: bool, timeout: int) -> None` |
| `validate_payload()` | `src/cli/commands/bundle_validate_payload.py` | 24 | `(file: Optional[Path], stdin: bool, json_output: bool) -> None` |
| `main()` | `scripts/validate_builder_nav.py` | 179 | `() -> int` |

### Patrones
- Todos los CLI commands siguen el patrón `typer.Option` + `rich.console` + `CLIConfig.load()`.
- Los commands que escriben DB usan `get_service_client()` (service role).
- Los commands que interactúan con API usan `httpx.Client` (síncrono).
- `tool_registry.list_tools()` se usa tanto en el CLI como en el endpoint HTTP — duplicación de lógica de colección de tools.

### Modularidad
- `tools_list.py` y `tools.py` (API route) comparten lógica de colección de tools duplicada (`_collect_tools`, `_fetch_mcp_tools`). Potencial refactorización.
- `bundle_validate_payload.py` usa `ExportBundleRequest` desde `bundle_schemas.py` — reutilización correcta.

### Problemas detectados
- `tools_list.py:_collect_tools()` es sync pero llama `asyncio.new_event_loop()` para ejecutar `_fetch_mcp_tools()`. El endpoint API (`tools.py`) usa `await` directo. Inconsistencia de patrón async/sync.
- `validate_builder_nav.py:65` tiene bug de regex (ver §0 discrepancia 3).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints involucrados en validación

| Endpoint | Método | Archivo | Auth | Input | Output |
|---|---|---|---|---|---|
| `/api/tools/available` | GET | `src/api/routes/tools.py:46` | `require_org_id` | `?source=local\|mcp&category=...` | `ToolsListResponse {tools: ToolInfo[], count: int}` |
| `/api/templates` | GET | `src/api/routes/templates.py:54` | Sin auth | `?category=` | `TemplateListResponse {templates, count}` |
| `/api/templates/{id}` | GET | `src/api/routes/templates.py:74` | Sin auth | `template_id: str` | `TemplateDetailResponse {soul_json, ...}` |
| `POST /agents` | POST | `src/api/routes/agents.py:101` | `require_org_id` | `AgentCreate {role, soul_json, allowed_tools, max_iter}` | `AgentResponse {id, org_id, role, ...}` (201) |
| `POST /agents/{role}/run` | POST | `src/api/routes/agents.py:312` | `verify_org_membership` | `RunAgentRequest {input_data}` | `RunAgentResponse {task_id, status}` |
| `POST /api/bundles/export` | POST | `src/api/routes/bundles.py:199` | `require_org_id` | `ExportBundleRequest {agents, skills?, bundle_name?}` | ZIP `StreamingResponse` (200) |

### Flujos de validación

**Tools Validation (ID-001):**
```
fap tools list (--source local) 
  → tool_registry.list_tools() + tool_registry.get_metadata()
  → NO pasa por GET /api/tools/available
```

**Templates Validation (ID-007, ID-009):**
```
fap templates seed → DB direct (service role)
GET /api/templates (existe, sin auth) ✅
GET /api/templates/{id} (existe, sin auth) ✅
```

**Agent CRUD Validation (ID-013):**
```
fap agent create --dry-run → solo print payload
fap agent create (real) → httpx POST /agents → API upsert en agent_catalog ✅
```

**Mapping Template→Agent (ID-022):**
```
fap templates use --dry-run 
  → DB direct (SELECT agent_templates) 
  → build payload local
  → NO llama GET /api/templates/{id}
  → NO llama POST /agents
```

**Execution Validation (ID-028):**
```
fap agent run → httpx POST /agents/{role}/run → poll GET /tasks/{task_id} ✅
```

**Export Validation (ID-041):**
```
fap bundle validate-payload --file payload.json 
  → ExportBundleRequest validation (Pydantic) ✅
  → Sin IO, sin HTTP
```

### Problemas de contratos
- **Discrepancia crítica**: Varios CLIs bypassan los endpoints HTTP. El plan dice "validar contratos de API" pero las herramientas CLI existentes no validan esos contratos — validan las implementaciones subyacentes directamente. Para dogfooding real, se necesita una suite que llame los endpoints HTTP reales.
- `fap tools list` no expone el filtro `?category=` que sí tiene el endpoint API (`tools.py:49`).

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end del paso

```
CLI fap tools list ─→ ToolRegistry/MCPPool (bypass HTTP)
CLI fap templates seed ─→ DB direct (bypass HTTP)
CLI fap agent create ─→ httpx POST /agents ─→ agent_catalog
CLI fap templates use ─→ DB direct + httpx POST /agents (si no dry-run)
CLI fap agent run ─→ httpx POST /agents/{role}/run ─→ polling GET /tasks/{task_id}
CLI fap bundle validate-payload ─→ Pydantic schema validation
Script validate_builder_nav.py ─→ Filesystem checks
```

### Gaps identificados

1. **Sin validación de `GET /api/tools/available`**: No existe ningún comando/script que valide que el endpoint HTTP retorne lo mismo que `fap tools list`.

2. **Sin validación de `GET /api/templates` via HTTP**: No existe comando que llame el endpoint real y verifique que retorna templates seeded.

3. **Sin validación `GET /api/templates?category=`**: El filtro de categoría del endpoint no está cubierto por ningún test/CLI.

4. **Sin ciclo Fullstack Live completo (ID-014)**: El plan pide "CLI create -> UI save -> DB verification" pero no existe herramienta que haga la verificación en DB después de un save de UI. Depende de operación manual.

5. **validate_builder_nav.py con falso positivo**: El regex roto en línea 65 hace que el check B de nav-main siempre pase incorrectamente (porque cae en el else que retorna `True`).

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap validate api-contracts
- **Qué automatiza:** Valida que los CLIs que bypassan HTTP (tools list, templates use) retornen exactamente los mismos datos que los endpoints HTTP reales.
- **Tipo:** CLI command
- **Cómo se usa:** `fap validate api-contracts --org-id <org_id>` — ejecuta:
  1. `GET /api/tools/available` (HTTP) vs `fap tools list --json`
  2. `GET /api/templates` (HTTP) vs `fap templates seed --dry-run` (estructura)
  3. `GET /api/templates/{id}` (HTTP) vs lectura directa DB
- **Impacto para el usuario final:** Elimina la brecha de confianza entre CLIs y endpoints. Detecta desincronización de contratos antes de que llegue a frontend.
- **Prioridad:** Tarea 0
```

---

## 5️⃣ Criterios de Aceptación

``` 
✅ [DATA] Tabla `agent_templates` existe con columnas correctas (migración 030)
✅ [CODE] CLI `fap tools list` ejecuta sin errores y retorna lista de tools
✅ [CODE] CLI `fap templates seed` ejecuta N veces sin error (idempotencia)
✅ [CODE] CLI `fap agent create --dry-run` genera payload JSON válido
✅ [CODE] CLI `fap templates use --dry-run` genera payload para los 8 templates
✅ [CODE] CLI `fap agent run` ejecuta ciclo POST + polling GET tasks
✅ [CODE] CLI `fap bundle validate-payload --stdin` valida schema ExportBundleRequest
✅ [CODE] `validate_builder_nav.py` pasa con 0 falsos positivos
✅ [BACKEND] GET /api/tools/available responde 200 con array de ToolInfo
✅ [BACKEND] GET /api/templates responde 200 con array de templates
✅ [BACKEND] GET /api/templates/{id} responde 200 con soul_json completo
✅ [BACKEND] POST /agents responde 201 con AgentResponse
✅ [BACKEND] POST /agents/{role}/run responde 200 con task_id
✅ [BACKEND] POST /api/bundles/export responde 200 con ZIP
✅ [FULLSTACK] Flujo CLI create → POST /agents → DB verification funciona
✅ [FULLSTACK] 8 templates mapean correctamente a agentes (soul_json completo)
✅ [DX] Herramienta `fap validate api-contracts` (propuesta) valida consistencia CLI↔HTTP
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| CLIs bypassan HTTP → falsa validación | Alta | `fap tools list` y `fap templates use` no llaman endpoints REST. Dogfooding valida implementación interna, no contrato API. | Implementar `fap validate api-contracts` que compare CLI output vs HTTP endpoint response. |
| validate_builder_nav.py falso positivo permanente | Media | Regex roto en línea 65 (`\\s*` en vez de `\s*`). Check de `items={defaultNavItems}` siempre falla en detección. | Corregir regex a `r"items=\{\s*defaultNavItems\}"`. |
| `fap agent run` usa httpx sync en CLI pero endpoint es async | Baja | CLI sync (`httpx.Client`), endpoint async (`async def`). No hay bug funcional pero inconsistencia de patrón. | Migrar CLI a `httpx.AsyncClient` cuando se refactorice (Paso 13 lo menciona). |
| Sin validación de `GET /api/templates?category=` | Media | Paso 03 implementó filtro, paso 05 lo usa en UI, pero ningún test/CLI valida que el filtro funcione. | Agregar validación en `fap templates seed --dry-run` o en test E2E existente (TP-5). |
| Dependencia de LLM real en `fap agent run` | Alta | Si no hay mock, `fap agent run` intenta llamar LLM real. Puede timeout, costar tokens, o fallar. | El test E2E (TP-2) usa `global_llm_mock`. Para dogfooding CLI, considerar flag `--mock-llm`. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: `fap validate api-contracts`** | `src/cli/commands/validate_api_contracts.py` | `def validate_api_contracts(org_id: str) -> None` | `src/cli/commands/tools_list.py :: list_tools()` para estructura | DX | Media | 1.5h | Ninguna | → verificar: `fap validate api-contracts --org-id test-org --dry-run` ejecuta sin errores |
| 1 | Fix regex `validate_builder_nav.py:65` | `scripts/validate_builder_nav.py` | L65: cambiar `"items={\\s*defaultNavItems}"` a `r"items=\{\s*defaultNavItems\}"` | — | CODE | Baja | 0.25h | Ninguna | → verificar: `uv run python scripts/validate_builder_nav.py` pasa check B correctamente |
| 2 | Dogfooding: validar `fap tools list` vs `GET /api/tools/available` | Manual — documentar resultado | `fap tools list --json --source local \| jq length` vs `curl /api/tools/available?source=local` | — | FULLSTACK | Baja | 0.5h | Tarea 0 | → verificar: ambos retornan mismo `count` y mismos `name` |
| 3 | Dogfooding: seed + list + detail + filter templates | Manual — documentar resultado | `fap templates seed` → `curl GET /api/templates` → `curl GET /api/templates/{id}` → `curl GET /api/templates?category=Research` | — | FULLSTACK | Baja | 0.5h | Paso 03 (seed existente) | → verificar: 8 templates retornados, soul_json presente en detail, filtro retorna solo Research |
| 4 | Dogfooding: `fap agent create --dry-run` + real | Manual — documentar resultado | `fap agent create --role test-agent --goal "..." --backstory "..." --dry-run` → `fap agent create --role test-agent --goal "..." --backstory "..."` | `tests/e2e/test_builder_scenarios.py :: TP-1` | FULLSTACK | Baja | 0.5h | Tarea 0 | → verificar: dry-run print payload válido POST /agents retorna 201 |
| 5 | Dogfooding: `fap templates use --dry-run` x8 | Manual — documentar resultado | `fap templates use "Research Agent" --org-id <id> --dry-run` para cada uno de los 8 templates | `src/cli/commands/templates_use.py :: use_template()` | FULLSTACK | Baja | 0.5h | Tarea 2 (seed ejecutado) | → verificar: cada dry-run produce payload con `soul_json.goal` y `soul_json.backstory` ≥ 10 chars |
| 6 | Dogfooding: `fap bundle validate-payload` con payload real | Manual — documentar resultado | Ejemplo: `echo '{"agents":[{"role":"x","soul_json":{"goal":"...","backstory":"..."}}]}' \| fap bundle validate-payload --stdin` | `src/cli/commands/bundle_validate_payload.py :: validate_payload()` | FULLSTACK | Baja | 0.5h | Tarea 5 (templates export payload) | → verificar: schema valid retorna 0 errores, warnings si goal < 10 chars |
| 7 | Dogfooding: fullstack live cycle | Manual — documentar resultado | `fap agent create ...` → login dashboard → UI edit → DB query confirm | — | FULLSTACK | Media | 1h | Tareas 2, 4 | → verificar: agente creado via CLI visible en dashboard y persistente en DB |

**Tiempo total estimado:** 4.75h

---

## 🔮 Roadmap

- Centralizar colección de tools (tool_registry + MCPPool) en un service compartido para eliminar duplicación entre `tools_list.py` y `tools.py`.
- Migrar CLIs `agent_create.py`, `templates_use.py`, `agent_run.py` a `httpx.AsyncClient` para consistencia con backend async.
- Agregar `fap validate api-contracts` como comando permanente en la suite de CI.
- Considerar flag `--mock-llm` en `fap agent run` para dogfooding sin LLM real.
