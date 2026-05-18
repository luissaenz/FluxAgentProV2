# Análisis Técnico — Paso 12: Protocolo de Validación y Dogfooding E2E

**Agente:** qwen3.6
**Fecha:** 2026-05-18
**Fase:** guiAgentGenerator

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `GET /api/tools/available` | `src/api/routes/tools.py:46` — `@router.get("/available")` | ✅ | tools.py línea 46, response_model `ToolsListResponse` |
| 2 | Endpoint `GET /api/templates` | `src/api/routes/templates.py:54` — `@router.get("")` | ✅ | templates.py línea 54, response_model `TemplateListResponse` |
| 3 | Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:74` — `@router.get("/{template_id}")` | ✅ | templates.py línea 74, response_model `TemplateDetailResponse` |
| 4 | Endpoint `POST /agents` | `src/api/routes/agents.py:101` — `@router.post("")` | ✅ | agents.py línea 101, response_model `AgentResponse`, status_code 201 |
| 5 | Endpoint `POST /agents/{role}/run` | `src/api/routes/agents.py:312` — `@router.post("/{role}/run")` | ✅ | agents.py línea 312, response_model `RunAgentResponse` |
| 6 | Endpoint `GET /tasks/{task_id}` | `src/api/routes/tasks.py:69` — `@router.get("/{task_id}")` | ✅ | tasks.py línea 69, response_model `TaskResponse` |
| 7 | Endpoint `POST /api/bundles/export` | `src/api/routes/bundles.py:199` — `@router.post("/export")` | ✅ | bundles.py línea 199, valida goal/backstory >= 10 chars |
| 8 | CLI `fap tools list` | `src/cli/commands/tools_list.py:29` — `@tools_list_app.command("list")` | ✅ | tools_list.py línea 29, registrado en main.py:67 |
| 9 | CLI `fap templates seed` | `src/cli/commands/templates_seed.py:140` — `@templates_app.command("seed")` | ✅ | templates_seed.py línea 140, 8 templates hardcodeados |
| 10 | CLI `fap templates use` | `src/cli/commands/templates_use.py:31` — `def use_template()` | ✅ | templates_use.py línea 31, soporta `--dry-run` |
| 11 | CLI `fap agent create` | `src/cli/commands/agent_create.py:29` — `@agent_app.command("create")` | ✅ | agent_create.py línea 29, soporta `--dry-run` |
| 12 | CLI `fap agent run` | `src/cli/commands/agent_run.py:52` — `def run_agent()` | ✅ | agent_run.py línea 52, polling con `--watch` y `--timeout` |
| 13 | CLI `fap bundle validate-payload` | `src/cli/commands/bundle_validate_payload.py:24` — `def validate_payload()` | ✅ | bundle_validate_payload.py línea 24, usa `ExportBundleRequest` |
| 14 | CLI `fap test-builder run` | `src/cli/commands/test_builder.py:30` — `@test_builder_app.command("run")` | ✅ | test_builder.py línea 30, ejecuta pytest subprocess |
| 15 | Script `validate_builder_nav.py` | `scripts/validate_builder_nav.py:179` — `def main()` | ✅ | validate_builder_nav.py línea 179, 5 categorías de checks |
| 16 | Tabla `agent_templates` | `supabase/migrations/030_agent_templates.sql` | ✅ | Migración 030 existe |
| 17 | Tabla `agent_catalog` | `supabase/migrations/004_agent_catalog.sql` | ✅ | Migración 004 existe |
| 18 | Tabla `org_mcp_servers` | `supabase/migrations/005_org_mcp_servers.sql` | ✅ | Migración 005 existe |
| 19 | Tabla `tasks` | Schema verificado en `tasks.py:26` — `TaskResponse` | ✅ | tasks.py línea 26, columnas: id, org_id, flow_type, status, result, error, tokens_used, created_at, updated_at |
| 20 | Schema `ExportBundleRequest` | `src/services/bundle_schemas.py:111` | ✅ | bundle_schemas.py línea 111, agents: List[AgentExportItem] min 1 max 15 |
| 21 | Routers registrados en `main.py` | `src/api/main.py:100-114` | ✅ | tools_router:114, templates_router:113, agents_router:107, bundles_router:111, tasks_router:100 |
| 22 | Suite E2E existente | `tests/e2e/test_builder_scenarios.py` — 32 tests (TP-1 a TP-6) | ✅ | 948 líneas, clases: TestBuilderAgentCRUD, TestBuilderToolsEndpoint, TestBuilderTemplates, TestBuilderPlayground, TestBuilderCrewAssembly, TestBuilderRoundTrip |

**Discrepancias encontradas:**

1. **❌ DISCREPANCIA (ID-001):** El plan dice "Validar `GET /api/tools/available` usando `fap tools list`". El CLI `fap tools list` NO llama al endpoint REST — implementa su propia lógica `_collect_tools()` directa desde `tool_registry` y `MCPPool` (tools_list.py:67-100). No hay dogfooding real del endpoint HTTP. **Resolución:** El script de validación debe llamar al endpoint HTTP directamente y comparar con la salida del CLI.

2. **❌ DISCREPANCIA (ID-014):** El plan dice "CLI create -> UI save -> verificación directa en DB". No existe CLI command que verifique directamente en DB que un agente fue creado. `fap agent create` solo hace POST al API. **Resolución:** Crear sub-comando `fap agent verify --role <role> --org-id <org>` que consulte `agent_catalog` directamente.

3. **⚠️ NO VERIFICABLE (ID-049):** "Eliminar falsos positivos en `validate_builder_nav.py` mejorando la detección de props". El script actual usa regex simple (`"Builder" in nav_content`) para detectar entrada Builder. No verifica props reales de React components. **Resolución:** Mejorar checks para parsear AST o al menos buscar patrones más específicos como `title: "Builder"` o `href: "/builder"`.

4. **❌ DISCREPANCIA (ID-007/ID-009):** El plan dice "Validar flujo completo de templates (seed -> list -> detail -> filter)". No existe un CLI command que encadene estas operaciones. `fap templates seed` y `fap templates use` son independientes. **Resolución:** Crear script de validación que ejecute la secuencia completa.

5. **⚠️ NO VERIFICABLE:** El plan menciona `fap agent create --dry-run` (ID-013). Este comando SÍ existe y funciona (agent_create.py:51). Pero no hay validación de que el payload generado sea compatible con el schema `AgentCreate` del backend. **Resolución:** El dry-run debe validar contra el schema Pydantic antes de imprimir.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas

| Tabla | Operación | Columnas relevantes |
|---|---|---|
| `agent_templates` | READ (list, detail, filter) | `id`, `name`, `description`, `category`, `soul_json`, `suggested_tools`, `max_iter`, `is_system`, `created_at` |
| `agent_catalog` | CREATE, READ | `id`, `org_id`, `role`, `soul_json`, `allowed_tools`, `max_iter`, `is_active`, `created_at` |
| `tasks` | CREATE, READ (polling) | `id`, `org_id`, `flow_type`, `status`, `result`, `error`, `tokens_used`, `created_at`, `updated_at` |
| `org_mcp_servers` | READ (tools lookup) | `name`, `org_id`, `is_active`, `command`, `args`, `secret_name` |

### Integridad referencial

- `agent_templates.id` → UUID determinista vía `uuid5(NAMESPACE_DNS, f"fap.system.template.{name}")` (templates_seed.py:192). No hay FK explícita pero el patrón garantiza unicidad.
- `agent_catalog.org_id` → referencia implícita a `organizations.id`. RLS aplica tenant isolation.
- `tasks.org_id` → referencia implícita a `organizations.id`. RLS aplica tenant isolation.
- `tasks.flow_type` → formato `agent:{role}` cuando se crea desde `POST /agents/{role}/run` (agents.py:336).

### RLS policies

- `agent_templates`: lectura pública (endpoints sin auth en templates.py:58). Escritura solo system (`is_system = true`).
- `agent_catalog`: RLS tenant isolation via `org_id::text = app.org_id()`. Solo org puede ver sus agentes.
- `tasks`: RLS tenant isolation via `org_id`.

### Índices necesarios

- `agent_templates`: índice en `category` para filtro `?category=` (ya cubierto por migración 030).
- `agent_catalog`: índice compuesto `(org_id, role)` para upsert check (agents.py:115-117).
- `tasks`: índice en `id` (PK), índice en `(org_id, status)` para polling.

### Tipos de datos — problemas detectados

- `TaskResponse.created_at` y `updated_at` son `str` (tasks.py:37-38). El backend convierte con `str(t["created_at"])`. Si el valor es NULL, `str(None)` = `"None"` string — potencial bug en frontend.
- `AgentResponse.created_at` es `str | None = None` (agents.py:35). Inconsistencia con Paso 13 que planea hacerlo obligatorio.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases nuevas requeridas para este paso

No se crean funciones nuevas de backend. Este paso es **validación/dogfooding** — se crean scripts de validación y se ejecutan herramientas CLI existentes.

### Funciones CLI existentes a validar

| CLI Command | Archivo | Firma | Patrón a seguir |
|---|---|---|---|
| `fap tools list` | `src/cli/commands/tools_list.py` | `def list_tools(org_id, source, json_output)` | Typer command con Rich table output |
| `fap templates seed` | `src/cli/commands/templates_seed.py` | `def seed_templates(dry_run, reset)` | Typer command, upsert con UUID v5 |
| `fap templates use` | `src/cli/commands/templates_use.py` | `def use_template(template_name, org_id, role, goal, backstory, tools, max_iter, dry_run)` | Typer command, httpx.Client POST |
| `fap agent create` | `src/cli/commands/agent_create.py` | `def create_agent(role, goal, backstory, org_id, tools, max_iter, llm_provider, llm_model, verbose, reasoning, inject_date, memory, dry_run)` | Typer command, httpx.Client POST |
| `fap agent run` | `src/cli/commands/agent_run.py` | `def run_agent(role, message, org_id, watch, timeout)` | Typer command, polling loop |
| `fap bundle validate-payload` | `src/cli/commands/bundle_validate_payload.py` | `def validate_payload(file, stdin, json_output)` | Typer command, Pydantic validation |
| `fap test-builder run` | `src/cli/commands/test_builder.py` | `def run_builder_tests(org_id, report, scenario)` | Typer command, subprocess pytest |

### Imports correctos (patrón existente)

```python
# CLI commands usan:
from src.cli.config import CLIConfig
from src.db.session import get_service_client
from src.tools.registry import tool_registry
import httpx
import typer
from rich.console import Console
from rich.table import Table
```

### Discrepancias de código

1. **`fap tools list` NO valida el endpoint HTTP** — recolecta tools directamente desde `tool_registry` y `MCPPool` (tools_list.py:67-100). Para dogfooding real, debería llamar `GET /api/tools/available` y comparar.

2. **`fap templates use` usa `httpx.Client` síncrono** (templates_use.py:162). El backend es async. No hay problema funcional pero inconsistencia con Paso 13 que planea migrar a `httpx.AsyncClient`.

3. **`validate_builder_nav.py` detección de props superficial** — usa `"Builder" in nav_content` (validate_builder_nav.py:83). Debería buscar `href: "/builder"` o `title: "Builder"` para evitar falsos positivos.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints involucrados en dogfooding

| Endpoint | Método | Input | Output | Auth |
|---|---|---|---|---|
| `/api/tools/available` | GET | `?source=local|mcp`, `?category=` | `ToolsListResponse {tools: ToolInfo[], count: int}` | `require_org_id` |
| `/api/templates` | GET | `?category=` | `TemplateListResponse {templates: TemplateInfo[], count: int}` | Sin auth |
| `/api/templates/{id}` | GET | path param `template_id` | `TemplateDetailResponse` con `soul_json` | Sin auth |
| `/agents` | POST | `AgentCreate {role, soul_json, allowed_tools, max_iter}` | `AgentResponse {id, org_id, role, soul_json, allowed_tools, max_iter, created_at}` | `require_org_id` |
| `/agents/{role}/run` | POST | `RunAgentRequest {input_data}` | `RunAgentResponse {task_id, status}` | `verify_org_membership` |
| `/tasks/{task_id}` | GET | path param `task_id` | `TaskResponse {task_id, org_id, flow_type, status, result, error, tokens_used, created_at, updated_at}` | `verify_org_membership` |
| `/api/bundles/export` | POST | `ExportBundleRequest {bundle_name?, agents[], skills?}` | ZIP file (StreamingResponse) | `require_org_id` |

### Contratos verificados

- **Tools endpoint:** `ToolInfo` tiene campos: `name`, `description`, `category`, `categories`, `source`, `parameters`, `requires_approval`, `timeout_seconds`, `is_active`. CLI `fap tools list` solo usa `name`, `description`, `category`, `source`. **Parcialmente cubierto.**

- **Templates endpoint:** `TemplateInfo` (lista) NO incluye `soul_json`. `TemplateDetailResponse` SÍ incluye `soul_json`. El TemplatePicker del frontend necesita `soul_json` — debe llamar al endpoint de detalle, no al de lista. **Correcto.**

- **Agent create:** `AgentCreate` requiere `role`, `soul_json`, `allowed_tools` (default []), `max_iter` (default 3). El CLI `fap agent create` construye `soul_json` con: `goal`, `backstory`, `llm_provider`, `llm_model`, `verbose`, `reasoning`, `inject_date`, `memory`. **Compatible.**

- **Agent run:** Retorna `task_id` + `status: "accepted"`. El CLI hace polling a `/tasks/{task_id}` cada 2s. Timeout configurable (default 120s). **Correcto.**

- **Bundle export:** Valida `goal` y `backstory` >= 10 chars (bundles.py:229-237). `ExportBundleRequest` valida `agents` min 1, max 15. **Correcto.**

### Middleware

- `require_org_id`: extrae `org_id` del header `X-Org-ID`. Usado en tools, bundles, agents (create).
- `verify_org_membership`: verifica JWT + org membership. Usado en agents (run), tasks.
- Templates endpoints **NO tienen auth** — patrón de lectura pública (templates.py:7-8).

### Error handling

| Escenario | Status | Detalle |
|---|---|---|
| Template no encontrado | 404 | `"Template not found"` |
| DB unavailable (templates) | 503 | `"Database unavailable"` |
| Agent role duplicado | 409 | `"Role already exists"` (manejado como update en realidad) |
| Goal/backstory < 10 chars | 422 | Mensaje específico por agente |
| Task no encontrada | 404 | `"Task not found"` |
| Task ID inválido (no UUID) | 400 | `"Invalid task ID"` |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end validado por este paso

```
[CLI] fap templates seed
   → INSERT 8 templates en agent_templates (DB)

[CLI] fap tools list --org-id X
   → Lee tool_registry + MCPPool → lista tools (NO pasa por endpoint HTTP)

[CLI] fap templates use "Research Agent" --org-id X --dry-run
   → Lee template de DB → construye payload → imprime JSON (no envía)

[CLI] fap agent create --role X --goal Y --backstory Z --org-id W --dry-run
   → Construye payload AgentCreate → imprime JSON (no envía)

[CLI] fap agent create --role X --goal Y --backstory Z --org-id W
   → POST /agents → AgentResponse con id

[CLI] fap agent run --role X --message "Hola" --org-id Y --watch
   → POST /agents/{role}/run → task_id → polling GET /tasks/{id} → resultado

[CLI] fap bundle validate-payload --file payload.json
   → Valida contra ExportBundleRequest → muestra summary

[Script] validate_builder_nav.py
   → Checks estáticos de archivos frontend (sidebar, loading, error, boundary, breadcrumb)
```

### Gaps identificados

1. **No hay validación de contrato CLI ↔ API:** `fap tools list` no llama al endpoint HTTP. No hay forma de verificar que el endpoint y el CLI devuelven los mismos datos.

2. **No hay validación de template mapping completo:** `fap templates use --dry-run` imprime el payload pero no verifica que el payload sea válido contra `AgentCreate` del backend.

3. **No hay validación de ciclo completo:** seed → list → use → create → run → verify en DB como un solo flujo automatizado.

4. **`validate_builder_nav.py` no verifica runtime:** Solo checks estáticos de archivos. No verifica que el builder cargue correctamente en el navegador.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: `fap dogfood run`
- **Qué automatiza:** Ejecuta el ciclo completo de dogfooding del Paso 12 en un solo comando: seed templates → list tools → list templates → create agent (dry-run) → create agent (real) → run agent → verify in DB → validate bundle payload → run validate_builder_nav.py. Elimina la necesidad de ejecutar 8+ comandos manualmente.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:** `fap dogfood run --org-id <uuid> --scenario all` o `--scenario tools|templates|agents|bundles|nav`
- **Impacto para el usuario final:** Reduce validación de ~15 minutos manualmente a ~30 segundos automatizados. Genera reporte de integridad con todos los contratos verificados.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

```
### Herramienta Propuesta: `scripts/dogfood_validator.py`
- **Qué automatiza:** Script standalone que valida contratos API vs CLI comparando salidas. Ejecuta `GET /api/tools/available` y `fap tools list --json` y compara los resultados. Hace lo mismo para templates. Detecta discrepancias entre lo que devuelve la API y lo que devuelve el CLI.
- **Tipo:** Script Python ejecutable
- **Cómo se usa:** `uv run python scripts/dogfood_validator.py --base-url http://localhost:8000 --org-id <uuid>`
- **Impacto para el usuario final:** Detecta bugs de contrato antes de que lleguen a producción. Ejemplo: si la API agrega un campo nuevo que el CLI no consume, o viceversa.
- **Prioridad:** Tarea 1
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `agent_templates` existe con 8 templates seed (verificado con `SELECT count(*) WHERE is_system = true`)
✅ [DATA] Tabla `agent_catalog` acepta INSERT con payload completo (role, soul_json, allowed_tools, max_iter)
✅ [DATA] Tabla `tasks` registra tarea al ejecutar `POST /agents/{role}/run`
✅ [CODE] CLI `fap tools list` ejecuta sin errores y muestra tools locales
✅ [CODE] CLI `fap templates seed` ejecuta N veces sin error (idempotente)
✅ [CODE] CLI `fap templates use --dry-run` imprime payload JSON válido
✅ [CODE] CLI `fap agent create --dry-run` imprime payload JSON válido contra schema AgentCreate
✅ [CODE] CLI `fap agent run` completa ciclo: POST → polling → resultado
✅ [CODE] CLI `fap bundle validate-payload` valida payload contra ExportBundleRequest
✅ [BACKEND] Endpoint `GET /api/tools/available` responde 200 con array de tools
✅ [BACKEND] Endpoint `GET /api/templates` responde 200 con templates
✅ [BACKEND] Endpoint `GET /api/templates/{id}` responde 200 con soul_json
✅ [BACKEND] Endpoint `POST /agents` responde 201 con AgentResponse
✅ [BACKEND] Endpoint `POST /agents/{role}/run` responde 200 con task_id
✅ [BACKEND] Endpoint `GET /tasks/{task_id}` responde 200 con TaskResponse
✅ [BACKEND] Endpoint `POST /api/bundles/export` valida goal/backstory >= 10 chars
✅ [FULLSTACK] Ciclo completo: CLI create → API save → DB verify funciona end-to-end
✅ [FULLSTACK] Template mapping: template soul_json → agent soul_json preserva goal/backstory
✅ [DX] Herramienta `fap dogfood run` ejecuta sin errores y genera reporte de integridad
✅ [DX] Script `dogfood_validator.py` detecta discrepancias API vs CLI
✅ [DX] `validate_builder_nav.py` mejora detección de props (sin falsos positivos)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| DB Supabase no disponible durante dogfooding | Alta | El dogfooding requiere DB real para seed, create, run | Verificar conectividad DB antes de iniciar (`fap check-env`) |
| Falsos positivos en `validate_builder_nav.py` | Media | Regex superficial detecta "Builder" en comentarios o strings no relacionados | Mejorar checks para buscar patrones específicos (`href: "/builder"`, `title: "Builder"`) |
| CLI `fap tools list` no valida endpoint HTTP | Media | Implementación directa vs endpoint REST pueden divergir | Crear `dogfood_validator.py` que compare salidas |
| Agent run timeout por LLM provider | Media | Groq/OpenAI pueden tardar > 120s en responder | Aumentar timeout default a 300s para dogfooding, o usar mock LLM |
| Templates seed falla si migración 030 no aplicada | Alta | Script valida tabla existe pero no verifica schema completo | Agregar check de columnas requeridas antes de insertar |
| `fap bundle validate-payload` solo valida schema, no contenido real | Baja | No verifica que los agentes referenciados existan en DB | Documentar limitación; validación completa requiere API running |
| Org ID no configurado en .env | Baja | CLI commands fallan si `FAP_ORG_ID` no está set | Todos los commands ya requieren `--org-id` explícito o fallan con mensaje claro |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear `fap dogfood run` | `src/cli/commands/dogfood_run.py` | `def dogfood_run(org_id, scenario, report)` → ejecuta secuencia de validación y genera reporte | `src/cli/commands/test_builder.py :: run_builder_tests()` | DX | Alta | 3h | Ninguna | → verificar: `uv run fap dogfood run --org-id test --scenario all` ejecuta sin errores y genera reporte |
| 1 | Crear script `dogfood_validator.py` | `scripts/dogfood_validator.py` | `def main(base_url, org_id)` → compara API vs CLI outputs | `scripts/validate_builder_nav.py :: main()` | DX | Media | 2h | Tarea 0 | → verificar: `uv run python scripts/dogfood_validator.py --base-url http://localhost:8000 --org-id test` muestra discrepancias |
| 2 | Mejorar `validate_builder_nav.py` detección de props | `scripts/validate_builder_nav.py` | Modificar `check_sidebar_ssot()` para buscar `href: "/builder"` y `title: "Builder"` | Regex patterns existentes en mismo archivo | CODE | Baja | 0.5h | Ninguna | → verificar: `uv run python scripts/validate_builder_nav.py` pasa todos los checks sin falsos positivos |
| 3 | Validar `GET /api/tools/available` con `fap tools list` | `scripts/dogfood_validator.py` (parte de Tarea 1) | `def validate_tools_endpoint(base_url, org_id)` → GET /api/tools/available vs `fap tools list --json` | `src/cli/commands/tools_list.py :: _collect_tools()` | BACKEND | Media | 1h | Tarea 1 | → verificar: script reporta 0 discrepancias entre API y CLI para tools locales |
| 4 | Validar flujo templates (seed → list → detail → filter) | `scripts/dogfood_validator.py` (parte de Tarea 1) | `def validate_templates_flow(base_url, org_id)` → seed, list, detail, filter | `src/cli/commands/templates_seed.py :: seed_templates()` | FULLSTACK | Media | 1.5h | Tarea 1 | → verificar: script completa ciclo seed → list (count >= 8) → detail (soul_json presente) → filter (category=Research funciona) |
| 5 | Validar `fap agent create --dry-run` payload | `src/cli/commands/agent_create.py` | Modificar `create_agent()` para validar payload contra `AgentCreate` antes de dry-run print | `src/cli/commands/bundle_validate_payload.py :: validate_payload()` | CODE | Baja | 0.5h | Ninguna | → verificar: `uv run fap agent create --dry-run --role test --goal "1234567890" --backstory "1234567890"` valida sin errores |
| 6 | Validar ciclo CLI create → API save → DB verify | `src/cli/commands/dogfood_run.py` (parte de Tarea 0) | `def validate_agent_cycle(org_id)` → create agent → query DB → verify | `src/cli/commands/templates_use.py :: use_template()` | FULLSTACK | Alta | 2h | Tarea 0, Tarea 5 | → verificar: agente creado via CLI existe en `agent_catalog` con mismos valores |
| 7 | Validar `fap templates use --dry-run` para 8 templates | `src/cli/commands/dogfood_run.py` (parte de Tarea 0) | `def validate_all_templates(org_id)` → loop 8 templates, use --dry-run, verificar payload | `src/cli/commands/templates_use.py :: use_template()` | FULLSTACK | Media | 1.5h | Tarea 0 | → verificar: los 8 templates generan payload válido con goal/backstory >= 10 chars |
| 8 | Validar ciclo de vida de tarea con `fap agent run` | `src/cli/commands/dogfood_run.py` (parte de Tarea 0) | `def validate_agent_run(org_id)` → create agent → run agent → poll task → verify result | `src/cli/commands/agent_run.py :: run_agent()` | BACKEND | Alta | 2h | Tarea 6 | → verificar: task completa con status "completed" o "failed" (no timeout) |
| 9 | Validar contratos de payload con `fap bundle validate-payload` | `src/cli/commands/dogfood_run.py` (parte de Tarea 0) | `def validate_bundle_contracts(org_id)` → generar payload export → validate-payload → verificar | `src/cli/commands/bundle_validate_payload.py :: validate_payload()` | BACKEND | Media | 1h | Tarea 6 | → verificar: payload de 3 agentes pasa validación sin warnings |
| 10 | Ejecutar validación completa y documentar evidencia | `DEVS/IN_PROGRESS/` | Generar reporte HTML con resultados de todas las validaciones | `src/cli/commands/test_builder.py :: _generate_html_report()` | FULLSTACK | Baja | 1h | Tareas 0-9 | → verificar: reporte HTML existe con todos los checks en verde |

**Tiempo total estimado:** 15 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Integrar `fap dogfood run` en CI/CD:** Ejecutar automáticamente en cada PR para detectar regresiones de contrato API ↔ CLI.
- **Mock LLM para dogfooding:** Permitir modo `--mock-llm` que simula respuestas de LLM para validar flujo sin consumir tokens reales.
- **Dashboard de integridad:** Página `/dashboard/integrity` que muestre resultados de dogfooding en tiempo real con históricos.
- **Validación de contratos con OpenAPI:** Generar spec OpenAPI del backend y validar que todos los CLI commands cumplen el spec.
- **Dogfooding de frontend:** Integrar Playwright para validar que el builder UI funciona con los datos creados via CLI.

---

## 🚫 Reglas de Oro — Checklist

- ✅ Análisis accionable y específico — cada tarea tiene interfaz exacta, patrón de referencia, verificación inline
- ✅ TODO verificado contra código — 22 elementos verificados en §0, 5 discrepancias documentadas
- ✅ Ambigüedades señaladas — CLI vs API divergence, template mapping validation, props detection
- ✅ Código gana sobre plan — templates endpoints sin auth documentado, tools list implementación directa
- ✅ Nivel CTO — riesgos técnicos concretos, mitigaciones específicas
- ✅ Coherente con phase-state.md — pasos 1-11 completados, paso 12 en progreso
- ✅ TODO el paso cubierto — 8 sub-tareas del plan analizadas
- ✅ Etapas secuenciales — data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta — `fap dogfood run` + `dogfood_validator.py`
- ✅ Tareas atómicas — una tarea = un artefacto = interfaz completa = patrón explícito = verificación inline
- ✅ Estimación de tiempo — por tarea y total (15h)