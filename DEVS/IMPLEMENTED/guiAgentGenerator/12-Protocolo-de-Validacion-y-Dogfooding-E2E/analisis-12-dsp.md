# 🧠 ANÁLISIS TÉCNICO — Paso 12 · Agente dsp

> **Fase:** `guiAgentGenerator`  
> **Paso:** 12 — Protocolo de Validación y Dogfooding E2E  
> **Agente:** dsp  
> **Fecha:** 2026-05-18  
> **Origen:** Sugerencias 🟡 de validación (ID-001, ID-007, ID-009, ID-013, ID-014, ID-022, ID-028, ID-041, ID-049)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | CLI `fap tools list` existe | `ls src/cli/commands/tools_list.py` | ✅ | `src/cli/commands/tools_list.py:1`, registrado como `tools_list_app` en `main.py:67` |
| 2 | CLI `fap tools list` expone filtro `--source local\|mcp` | grep `source` en `tools_list.py` | ✅ | `tools_list.py:34-35` — `--source` con validación `("local", "mcp")` |
| 3 | CLI `fap templates seed` existe | `ls src/cli/commands/templates_seed.py` | ✅ | `templates_seed.py:140`, registrado en `main.py:65` |
| 4 | CLI `fap templates seed` tiene `--dry-run` y `--reset` | grep `dry_run`/`reset` en `templates_seed.py` | ✅ | `templates_seed.py:141-147` |
| 5 | CLI `fap templates seed` define 8 templates | conteo en `templates_seed.py` | ✅ | `templates_seed.py:32-137` — 8 entradas en `TEMPLATES` |
| 6 | CLI `fap templates seed` usa upsert idempotente | grep `upsert`/`on_conflict` en `templates_seed.py` | ✅ | `templates_seed.py:204-208` — `upsert(row, on_conflict="id", ignore_duplicates=True)` con UUID v5 |
| 7 | CLI `fap templates seed` tiene check preventivo de tabla | grep `table` en `templates_seed.py` | ✅ | `templates_seed.py:154-158` — `select("id").limit(1).execute()` |
| 8 | CLI `fap templates use` existe | `ls src/cli/commands/templates_use.py` | ✅ | `templates_use.py:31`, registrado en `main.py:66` |
| 9 | CLI `fap templates use` tiene `--dry-run` | grep `dry_run` en `templates_use.py` | ✅ | `templates_use.py:51-53` |
| 10 | CLI `fap agent create` existe | `ls src/cli/commands/agent_create.py` | ✅ | `agent_create.py:29-30`, registrado en `main.py:86` |
| 11 | CLI `fap agent create` tiene `--dry-run` | grep `dry_run` en `agent_create.py` | ✅ | `agent_create.py:51-52` |
| 12 | CLI `fap agent create` acepta todos los campos del Agent de CrewAI | `agent_create.py:31-51` | ✅ | role, goal, backstory, tools, max_iter, llm_provider, llm_model, verbose, reasoning, inject_date, memory |
| 13 | CLI `fap agent run` existe | `ls src/cli/commands/agent_run.py` | ✅ | `agent_run.py:52`, registrado en `main.py:87` |
| 14 | CLI `fap agent run` tiene `--watch` y `--timeout` | grep `watch`/`timeout` en `agent_run.py` | ✅ | `agent_run.py:58-63` |
| 15 | CLI `fap bundle validate-payload` existe | `ls src/cli/commands/bundle_validate_payload.py` | ✅ | `bundle_validate_payload.py:24`, registrado en `main.py:84` |
| 16 | CLI `fap bundle validate-payload` usa schema `ExportBundleRequest` | grep `ExportBundleRequest` en `bundle_validate_payload.py` | ✅ | `bundle_validate_payload.py:19,57` |
| 17 | Script `validate_builder_nav.py` existe | `ls scripts/validate_builder_nav.py` | ✅ | `scripts/validate_builder_nav.py:1` |
| 18 | `validate_builder_nav.py` verifica 5 puntos de integración | conteo de funciones check_* | ✅ | `check_sidebar_ssot`, `check_nextjs_files`, `check_error_boundary`, `check_breadcrumb`, `check_ssr_false` |
| 19 | Endpoint `GET /api/tools/available` existe | `ls src/api/routes/tools.py` | ✅ | `tools.py` — `@router.get("/available")` |
| 20 | Endpoint `GET /api/tools/available` soporta filtro `?source=` | grep `source` en `tools.py` | ✅ | `tools.py` — `source: Optional[str] = Query(...)` con regex `^(local\|mcp)$` |
| 21 | Endpoint `GET /api/templates` existe | `ls src/api/routes/templates.py` | ✅ | `templates.py` — `@router.get("")` |
| 22 | Endpoint `GET /api/templates` soporta filtro `?category=` | grep `category` en `templates.py` | ✅ | `templates.py` — `category: Optional[str] = Query(None)` |
| 23 | Endpoint `GET /api/templates/{template_id}` existe | `ls src/api/routes/templates.py` | ✅ | `templates.py` — `@router.get("/{template_id}")` |
| 24 | Endpoint `POST /agents` existe | `ls src/api/routes/agents.py` | ✅ | `agents.py` — `@router.post("")` con status 201 |
| 25 | Endpoint `POST /agents` usa upsert (create or update) | grep `upsert`/`existing` en `agents.py` | ✅ | `agents.py` — busca por `org_id + role`, si existe actualiza, si no inserta |
| 26 | Endpoint `POST /agents/{role}/run` existe | `ls src/api/routes/agents.py` | ✅ | `agents.py` — `@router.post("/{role}/run")` |
| 27 | Endpoint `POST /agents/{role}/run` usa BackgroundTasks | grep `BackgroundTasks\|background_tasks` en `agents.py` | ✅ | `agents.py` — fire-and-forget via `background_tasks.add_task(_execute)` |
| 28 | Endpoint `POST /api/bundles/export` existe | `ls src/api/routes/bundles.py` | ✅ | `bundles.py` — `@router.post("/export")` |
| 29 | Endpoint `POST /api/bundles/export` valida goal y backstory | grep `goal`/`backstory`/`10` en `bundles.py` | ✅ | `bundles.py` — validación `len >= 10` en export endpoint |
| 30 | Tabla `agent_templates` existe | `ls supabase/migrations/030_agent_templates.sql` | ✅ | `030_agent_templates.sql` — `CREATE TABLE agent_templates` |
| 31 | Tabla `agent_catalog` existe | `ls supabase/migrations/004_agent_catalog.sql` | ✅ | `004_agent_catalog.sql` |
| 32 | RLS en `agent_templates`: lectura authenticated, escritura service_role | grep `agent_templates_read`/`agent_templates_write` en migración 030 | ✅ | `030_agent_templates.sql` — 2 políticas diferenciadas |
| 33 | Schema `ExportBundleRequest` existe | grep `class ExportBundleRequest` en `bundle_schemas.py` | ✅ | `bundle_schemas.py:105` — pydantic con `agents: min_items=1, max_items=15` |
| 34 | Tabla `tasks` existe | `ls supabase/migrations/001_*` | ✅ | `001` — tabla `tasks` con status, result, tokens_used, created_at |
| 35 | Comando `fap test-builder run` existe (previo) | `ls src/cli/commands/test_builder.py` | ✅ | `test_builder.py:31`, registrado en `main.py:88` |
| 36 | Comando `fap doctor builder` existe (previo) | `ls src/cli/commands/doctor_builder.py` | ✅ | `doctor_builder.py`, registrado en `main.py:89` |

**Total verificado:** 36 elementos. **Umbral superado** (mínimo 18 para 6-10 archivos).

### Discrepancias encontradas

| # | Discrepancia | Severidad | Resolución propuesta |
|---|---|---|---|
| **D1** | `validate_builder_nav.py:65` — La variable `uses_navmain` se calcula (`<NavMain` in content or `"items={\\s*defaultNavItems}"` in content) pero **nunca se usa** en la decisión. El check `NavMain en app-sidebar.tsx recibe items={defaultNavItems}` pasa incondicionalmente cuando `not has_navmain`, sin validar realmente que la prop `items` se esté pasando. | Media | ID-049: reescribir la detección para que extraiga y valide la prop `items` del JSX `<NavMain items={defaultNavItems}>` usando regex o AST. |
| **D2** | `validate_builder_nav.py:65` — La cadena `"items={\\s*defaultNavItems}"` contiene `\\s*` como literal (no es regex). Nunca hará match con `in`, produciendo **falso negativo** si la prop existe con espacios. | Alta | ID-049: cambiar detección por `re.search(r'items\s*=\s*\{defaultNavItems\}', content)` o similar. |
| **D3** | `tools_list.py:141` — `_fetch_mcp_tools` crea un `asyncio.new_event_loop()` por cada invocación. Este patrón es frágil en entornos con event loop ya corriendo. Asignado a Paso 13 (ID-003/ID-004) pero **NO bloquea** la validación de Paso 12. | Baja | No resolver en Paso 12 — documentar como riesgo conocido para Paso 13. |
| **D4** | `templates_use.py:31` — La función `use_template` no está decorada con `@templates_app.command("use")`. La registración ocurre externamente en `main.py:66` (`templates_app.command("use")(use_template)`). Esto es funcionalmente correcto pero inconsistente con otros comandos (ej: `tools_list`, `templates_seed`). | Baja | Documentar como patrón atípico. No requiere cambio para Paso 12. Podría unificarse en Paso 13 o 14. |
| **D5** | `agent_create.py` y `agent_run.py` usan `httpx.Client` sincrónico, pero `templates_use.py` también. El Paso 13 (ID-033/039) planea migrar a `httpx.AsyncClient`. Sin embargo, los comandos `tools_list`, `templates_seed`, `templates_use` usan `get_service_client()` directo (Supabase client sync). Esta mezcla de patrones (sync httpx + sync supabase) es válida para dogfooding. | Baja | No resolver en Paso 12. Documentar como deuda técnica para Paso 13. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema involucrado

El Paso 12 no crea ni modifica tablas. **Valida** que las tablas existentes y su schema soporten los contratos de API esperados por las herramientas CLI.

| Tabla | Uso en Paso 12 | CLI que la toca |
|---|---|---|
| `agent_templates` | Lectura por `templates use`, `templates seed` (escritura upsert), endpoint `GET /api/templates` | `fap templates seed`, `fap templates use` |
| `agent_catalog` | Lectura/escritura por `agent create`, `agent run`, endpoint `POST /agents`, `POST /agents/{role}/run` | `fap agent create`, `fap agent run` |
| `tasks` | Lectura por polling vía `GET /tasks/{task_id}` en `agent run` | `fap agent run` |
| `org_mcp_servers` | Lectura por `tools list` para listar herramientas MCP | `fap tools list` |
| `bundle_imports` | Validación indirecta vía `ExportBundleRequest` schema | `fap bundle validate-payload` |

### Integridad referencial

- `agent_templates` es tabla global (sin `org_id`). RLS permite lectura a cualquier `authenticated`, escritura solo a `service_role`. Esto es correcto para el flujo de dogfooding: el CLI usa `get_service_client()` (service_role) para el seed.
- `agent_catalog` tiene FK a `organizations(id)` y `bundle_imports(id)`. El CLI usa `get_service_client()` o `httpx` con header `X-Org-ID`. Ambas vías son válidas.
- `tasks` se inserta vía `POST /agents/{role}/run` usando `get_tenant_client(org_id)`. El CLI de `agent run` hace polling vía `GET /tasks/{task_id}` con header `X-Org-ID`.

### RLS policies

| Tabla | Política | Impacto en dogfooding |
|---|---|---|
| `agent_templates` | SELECT: `authenticated`, ALL: `service_role` | Seed usa service_role → OK. List/detail vía API son públicos (sin dependencia org) → OK |
| `agent_catalog` | `service_role` OR `current_org_id()` | CLI usa header `X-Org-ID` → el tenant client setea `app.org_id` → OK |
| `tasks` | Tenant isolation por `current_org_id()` | Polling vía API con `X-Org-ID` → OK |

### Tipos de datos

- `soul_json` es `JSONB` en `agent_catalog` y `agent_templates`. Los CLI serializan campos flat (goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory) en el dict. Coincidencia exacta entre CLI y API.
- `allowed_tools` es `TEXT[]` en ambas tablas. CLI acepta lista de strings (`--tools` repetible). Coincidencia exacta.
- `max_iter` es `INTEGER` en ambas. CLI usa `int` con validación `min=1, max=10` en `agent_create`. El schema `AgentExportItem` permite 1-50. **Gap menor**: el CLI restringe a 10 mientras el bundle permite 50. No bloquea la validación.

### Índices necesarios

- `idx_agent_templates_system_name` (unique sobre `name` WHERE `is_system = TRUE`) ya existe. El seed usa upsert por `id` (UUID v5 determinista), no por `name`, evitando colisiones con este índice parcial.
- `idx_agent_catalog_org_role` (sobre `org_id, role` WHERE `is_active = TRUE`) soporta el upsert del endpoint `POST /agents`.

### Impacto en datos existentes

Ninguno. El Paso 12 es solo lectura/validación. `fap templates seed` es idempotente (upsert) y no destruye datos existentes. `fap agent create --dry-run` y `fap bundle validate-payload` no persisten.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos afectados

| Archivo | Acción | Líneas |
|---|---|---|
| `scripts/validate_builder_nav.py` | **MODIFICAR** — Fix detección de props NavMain (ID-049) | 65, 67-70 |
| `src/cli/commands/tools_list.py` | **VALIDAR** — Ejecutar `fap tools list` y verificar output | — |
| `src/cli/commands/templates_seed.py` | **VALIDAR** — Ejecutar `fap templates seed` y verificar idempotencia | — |
| `src/cli/commands/templates_use.py` | **VALIDAR** — Ejecutar `fap templates use --dry-run` para 8 templates | — |
| `src/cli/commands/agent_create.py` | **VALIDAR** — Ejecutar `fap agent create --dry-run` | — |
| `src/cli/commands/agent_run.py` | **VALIDAR** — Ejecutar `fap agent run` con un agente real | — |
| `src/cli/commands/bundle_validate_payload.py` | **VALIDAR** — Ejecutar `fap bundle validate-payload` con payload real | — |
| `src/api/routes/tools.py` | **VALIDAR** — Verificar que el contrato coincide con el CLI | — |
| `src/api/routes/templates.py` | **VALIDAR** — Verificar que el contrato coincide con el CLI | — |
| `src/api/routes/agents.py` | **VALIDAR** — Verificar contratos create/run | — |
| `src/api/routes/bundles.py` | **VALIDAR** — Verificar contrato de export | — |

### Patrones en uso

1. **CLI → API via httpx sync**: `agent_create.py:101` y `agent_run.py:89` usan `httpx.Client` con timeout 15. `templates_use.py:162` mismo patrón. Patrón consistente entre comandos.
2. **CLI → DB via service_client**: `tools_list.py:105`, `templates_seed.py:150`, `templates_use.py:57` usan `get_service_client()` directo. El patrón es `db.table().select()...execute()` con Supabase Python client.
3. **Validación con Pydantic**: `bundle_validate_payload.py:57` usa `ExportBundleRequest(**data)` y captura `ValidationError`. Patrón correcto y reutilizable.
4. **Salida Rich**: todos los CLI usan `rich.console.Console` y `rich.table.Table` para output formateado. Consistente.

### Calidad del código

| Archivo | Observaciones |
|---|---|
| `tools_list.py` | `asyncio.new_event_loop()` en línea 141 es un anti-patrón conocido (ID-003/004). Funciona pero es frágil. **No se modifica en Paso 12.** |
| `templates_seed.py` | Ya refactorizado con idempotencia correcta (Paso 11). Código limpio. |
| `templates_use.py` | `use_template` no decorada como comando Typer. Registrada externamente en `main.py:66`. Funciona pero es inconsistente con el resto. **No se modifica.** |
| `agent_create.py` | Simple y directo. `--dry-run` bien implementado (print + exit sin enviar). |
| `agent_run.py` | Polling sincrónico con `time.sleep(2)`. Timeout configurable. Correcto para dogfooding. |
| `bundle_validate_payload.py` | Excelente: valida contra Pydantic, muestra tabla con goal/backstory OK, estima tamaño ZIP. Modelo de CLI a seguir. |
| `validate_builder_nav.py` | **Requiere fix (ID-049):** la detección de `items={defaultNavItems}` en `check_sidebar_ssot()` tiene un bug (D1, D2 arriba). La variable `uses_navmain` se calcula pero nunca se usa para decidir. |

### Firmas de funciones relevantes

```python
# tools_list.py
def list_tools(org_id: Optional[str], source: Optional[str], json_output: bool) -> None

# templates_seed.py
def seed_templates(dry_run: bool, reset: bool) -> None

# templates_use.py
def use_template(template_name: str, org_id: str, role: Optional[str], goal: Optional[str],
                 backstory: Optional[str], tools: Optional[list[str]], max_iter: Optional[int],
                 dry_run: bool) -> None

# agent_create.py
def create_agent(role: str, goal: str, backstory: str, org_id: Optional[str],
                 tools: Optional[list[str]], max_iter: int, llm_provider: str,
                 llm_model: str, verbose: bool, reasoning: bool, inject_date: bool,
                 memory: bool, dry_run: bool) -> None

# agent_run.py
def run_agent(role: str, message: str, org_id: Optional[str], watch: bool, timeout: int) -> None

# bundle_validate_payload.py
def validate_payload(file: Optional[Path], stdin: bool, json_output: bool) -> None

# validate_builder_nav.py
def check_sidebar_ssot() -> None      # ← contiene el bug de ID-049
def check_nextjs_files() -> None
def check_error_boundary() -> None
def check_breadcrumb() -> None
def check_ssr_false() -> None
def main() -> int
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints involucrados en la validación

| Endpoint | Método | CLI que lo consume | Contrato validado |
|---|---|---|---|
| `/api/tools/available` | GET | `fap tools list` | Response: `ToolsListResponse` con `tools: List[ToolInfo]`, `count` |
| `/api/templates` | GET | (validación vía seed → list) | Response: `TemplateListResponse` con `templates: List[TemplateInfo]`, filtro `?category=` |
| `/api/templates/{id}` | GET | (validación vía seed → detail) | Response: `TemplateDetailResponse` con `soul_json` expandido |
| `/agents` | POST | `fap agent create`, `fap templates use` | Input: `AgentCreate`, Output: `AgentResponse` (201), upsert si existe |
| `/agents/{role}/run` | POST | `fap agent run` | Input: `RunAgentRequest`, Output: `RunAgentResponse(task_id)`, 202-style (retorna 200/201) |
| `/tasks/{task_id}` | GET | `fap agent run` (polling) | Output: task con `status`, `result`, `tokens_used`, `error` |
| `/api/bundles/export` | POST | `fap bundle validate-payload` (schema, no ejecuta) | Input: `ExportBundleRequest`, Output: `StreamingResponse` ZIP |

### Middleware y Auth

- `GET /api/tools/available`: usa `Depends(require_org_id)` → `X-Org-ID` header requerido. CLI lo envía correctamente.
- `GET /api/templates`: **sin auth** (público). Correcto para catálogo global de templates.
- `POST /agents`: usa `Depends(require_org_id)`. CLI envía `X-Org-ID`.
- `POST /agents/{role}/run`: usa `Depends(verify_org_membership)` (más estricto). Requiere JWT además de `X-Org-ID`. CLI envía ambos si `config.access_token` existe.
- `POST /api/bundles/export`: usa `Depends(require_org_id)`. CLI de `validate-payload` no ejecuta este endpoint (solo valida schema).

### Flujo de datos CLI ↔ Backend

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DOGFOODING FLOWS                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [ID-001] fap tools list                                            │
│    CLI → ToolRegistry.list_tools() (local, in-process)              │
│    CLI → get_service_client() → org_mcp_servers → MCPPool (remote) │
│    ⚠️ NO toca el endpoint /api/tools/available directamente       │
│                                                                     │
│  [ID-007] fap templates seed                                        │
│    CLI → get_service_client() → agent_templates (upsert)            │
│    ⚠️ NO toca el endpoint /api/templates directamente              │
│                                                                     │
│  [ID-009] Validación templates (seed → list → detail → filter)     │
│    CLI seed → service_client → agent_templates                      │
│    CLI list → httpx → GET /api/templates?category=                  │
│    CLI detail → httpx → GET /api/templates/{id}                     │
│                                                                     │
│  [ID-013] fap agent create --dry-run                                │
│    CLI → construye payload → imprime → NO envía a API               │
│    ⚠️ Dry-run no valida contrato de API, solo schema local         │
│                                                                     │
│  [ID-014] Fullstack Live: CLI create → UI save → DB verify          │
│    CLI → httpx → POST /agents → insert/upsert en agent_catalog      │
│    UI → Supabase direct → agent_catalog                             │
│    DB → SQL → SELECT FROM agent_catalog                             │
│                                                                     │
│  [ID-022] fap templates use --dry-run (8 templates)                 │
│    CLI → get_service_client() → agent_templates (lectura)           │
│    CLI → construye payload con soul_json                            │
│    ⚠️ Dry-run no toca POST /agents, solo valida mapeo local        │
│                                                                     │
│  [ID-028] fap agent run                                             │
│    CLI → httpx → POST /agents/{role}/run → task_id                  │
│    CLI → httpx → GET /tasks/{task_id} (polling cada 2s)             │
│    Backend → BackgroundTasks → crew.run_async()                     │
│                                                                     │
│  [ID-041] fap bundle validate-payload                               │
│    CLI → parse JSON → Pydantic ExportBundleRequest(**data)           │
│    ⚠️ NO toca el endpoint /api/bundles/export directamente         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### ⚠️ Hallazgo crítico de backend

**5 de 7 herramientas de dogfooding validan contratos de API solo parcialmente o usan bypass de DB:**

| Herramienta | Valida API HTTP? | Usa DB directa? | Riesgo |
|---|---|---|---|
| `fap tools list` | ❌ No — lee `ToolRegistry` y `org_mcp_servers` directo | ✅ Sí | Alto: **No prueba el endpoint `/api/tools/available`** — solo valida el backend interno. Si el endpoint falla (ej: middleware, serialización Pydantic), el CLI no lo detecta. |
| `fap templates seed` | ❌ No — escribe directo con `service_client` | ✅ Sí | Medio: Valida escritura DB pero no el endpoint GET. La validación ID-009 (list/detail) si prueba endpoints HTTP. |
| `fap templates use --dry-run` | ❌ No — lee DB directo, imprime payload | ✅ Sí | Medio: Dry-run no valida el POST. Se necesita modo no-dry-run para validar contrato completo. |
| `fap agent create --dry-run` | ❌ No — construye payload y sale | ❌ No | Alto: **Dry-run no valida absolutamente nada del backend.** Solo valida que el payload se construye. |
| `fap agent run` | ✅ Sí — POST + polling GET | ❌ No | Bajo: Única herramienta que valida el flujo HTTP completo. |
| `fap bundle validate-payload` | ❌ No — valida schema Pydantic local | ❌ No | Medio: Valida schema del payload, no la respuesta del endpoint de export. |

**Conclusión:** El "dogfooding" actual es principalmente **validación de lógica de negocio interna y schema**, no validación end-to-end de contratos HTTP. Esto es un gap significativo respecto al objetivo declarado del paso: _"validar los contratos de API antes de darlos por finalizados"_.

### Manejo de errores en los endpoints

- `GET /api/tools/available`: MCP errors degradan graceful (warning log, empty list). No propaga 500.
- `GET /api/templates`: `HTTPException(503)` para fallos de DB. Ya implementado (Paso 11 fix).
- `POST /agents`: 409 si el role ya existe (upsert, no error real). 422 si falta goal/backstory (validación en endpoint de bundles, no en POST /agents directamente).
- `POST /agents/{role}/run`: Fire-and-forget — siempre retorna 200/201/202 con task_id. Errores van al registro `tasks.status = 'failed'`.
- `POST /api/bundles/export`: 422 si goal/backstory < 10 chars.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo end-to-end de dogfooding

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    FLUJO END-TO-END: DOGFOODING PASO 12                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  [1] fap templates seed                     → DB: agent_templates (8 rows)           │
│  [2] curl GET /api/templates                → JSON: 8 templates                     │
│  [3] curl GET /api/templates?category=Dev   → JSON: 2 templates                     │
│  [4] curl GET /api/templates/{id}           → JSON: soul_json + suggested_tools     │
│  [5] fap templates use "Research Agent" --dry-run → payload preview                │
│  [6] fap agent create --dry-run             → payload preview                       │
│  [7] fap agent create (real)                → POST /agents → DB: agent_catalog      │
│  [8] curl GET /agents                       → JSON: agents list                     │
│  [9] fap agent run --role "X" --message "Y" → POST run → task_id → poll → result   │
│ [10] fap bundle validate-payload --file p.json → schema validation                  │
│ [11] uv run python scripts/validate_builder_nav.py → integridad UI                  │
│ [12] fap tools list                         → tools from registry + MCP             │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Coherencia DB → Backend → CLI → UX

- **DB ↔ Backend:** Tablas correctamente definidas con migraciones versionadas. RLS consistente.
- **Backend ↔ CLI:** 5/7 herramientas usan DB directa en vez de HTTP. Solo `agent run` y parcialmente `agent create`/`templates use` (modo no-dry-run) validan HTTP. **Gap de cobertura de contratos HTTP.**
- **CLI ↔ UX:** El output Rich (tablas, colores, states) es consistente entre todos los comandos. La experiencia de desarrollador es homogénea.
- **Backend ↔ Frontend:** El script `validate_builder_nav.py` valida que el frontend esté correctamente cableado (sidebar, breadcrumb, error boundary, SSR).

### Alineación plan ↔ arquitectura

- El plan pide "Validar `GET /api/tools/available` usando `fap tools list`" — pero `fap tools list` **no llama** a ese endpoint. Solo comparte la lógica interna (`_collect_tools`). Esto es una ambigüedad en el plan: ¿se espera validar el endpoint HTTP o la lógica de negocio subyacente?
- El plan pide "Validar contratos de payload con `fap bundle validate-payload`" — esto valida el schema de entrada, no la respuesta del endpoint. Correcto para validación de contrato de entrada, pero incompleto para contrato de salida.

### DX & Tooling

#### Herramienta Propuesta: `fap validate-dogfood`
- **Qué automatiza:** Ejecuta secuencialmente los 8 protocolos de validación del Paso 12 (seed templates → listar → detalle → filtrar → crear agente → ejecutar → validar payload → validar nav) y genera un reporte unificado en formato Rich con checks pass/fail por cada tarea.
- **Tipo:** CLI command (subcomando de `fap validate` o comando standalone)
- **Cómo se usa:**
  ```bash
  uv run fap validate-dogfood --org-id $ORG_ID --json > report.json
  uv run fap validate-dogfood --org-id $ORG_ID  # output Rich
  ```
- **Impacto para el usuario final:** Elimina la ejecución manual de 8 comandos distintos + verificación visual de resultados. El desarrollador obtiene un reporte consolidado con evidencia documentada en segundos.
- **Prioridad:** Tarea 0 — implementar antes de ejecutar el resto del paso. La herramienta misma ejecuta y documenta todas las validaciones.

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Tipo | Verificable |
|---|---|---|---|
| ✅ 1 | `fap templates seed` ejecutado N veces sin error (idempotencia confirmada) | DATA | `fap templates seed && fap templates seed` → exit 0 ambas veces |
| ✅ 2 | `GET /api/templates` devuelve 8 templates | DATA | `curl /api/templates \| jq '.count'` → 8 |
| ✅ 3 | `GET /api/templates?category=Research` filtra correctamente | DATA | `curl /api/templates?category=Research \| jq '.count'` → 1 |
| ✅ 4 | `GET /api/templates/{id}` devuelve `soul_json` completo | DATA | `curl /api/templates/{id} \| jq '.soul_json.goal'` → no nulo |
| ✅ 5 | `fap agent create --dry-run` genera payload Pydantic-válido | CODE | output JSON compatible con `AgentCreate` schema |
| ✅ 6 | `fap agent create` real persiste en `agent_catalog` | BACKEND | `curl POST /agents` → 201, `SELECT` en DB → 1 row |
| ✅ 7 | `fap agent run` completa ciclo: POST run → poll → result | BACKEND | exit 0 con `[OK] Completed in Xs` |
| ✅ 8 | `fap bundle validate-payload --file payload.json` valida schema | CODE | `ExportBundleRequest(**data)` sin `ValidationError` |
| ✅ 9 | `fap bundle validate-payload` con JSON inválido → exit 1 con errores | CODE | exit code 1, tabla de errores en output |
| ✅ 10 | `fap tools list` lista herramientas locales + MCP | BACKEND | output muestra tools con source `local` y `mcp` |
| ✅ 11 | `fap tools list --source local` solo muestra tools locales | BACKEND | output no contiene entries con source `mcp` |
| ✅ 12 | `fap templates use "Research Agent" --dry-run` mapea soul_json correctamente para los 8 templates | FULLSTACK | 8 ejecuciones dry-run sin errores, payloads con goal/backstory ≥ 10 chars |
| ✅ 13 | `uv run python scripts/validate_builder_nav.py` → exit 0, todos los checks OK | FULLSTACK | Tabla de resultados todos ✔ OK |
| ✅ 14 | `validate_builder_nav.py` detecta correctamente `items={defaultNavItems}` en NavMain (ID-049) | CODE | Regex/AST detecta la prop con/sin espacios |
| ✅ 15 | `validate_builder_nav.py` NO produce falsos positivos cuando NavMain NO tiene la prop | CODE | Test con sidebar sin items → FAIL legítimo, no PASS incondicional |
| ✅ 16 | [DX] `fap validate-dogfood` ejecuta todos los checks y genera reporte | DX | exit 0, reporte JSON o Rich con 8 secciones |
| ✅ 17 | [DX] `fap validate-dogfood --json` genera JSON válido con structured results | DX | `jq .` parsea sin error |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1:** Dogfooding no valida contratos HTTP reales | **Alta** | 5/7 herramientas usan DB directa en vez de HTTP (ver §3 hallazgo crítico). Si el middleware de auth, serialización Pydantic o CORS fallan, el dogfooding no lo detecta. | Incluir en el plan de implementación llamadas `curl` explícitas a cada endpoint como pasos de verificación. La herramienta DX propuesta (`fap validate-dogfood`) debe incluir validación HTTP. |
| **R2:** `fap tools list` no valida endpoint `/api/tools/available` | **Alta** | El CLI lee `ToolRegistry` en-process y `org_mcp_servers` directo, nunca llama al endpoint HTTP. Si el endpoint tiene bugs de serialización Pydantic (`ToolInfo`), el dogfooding no los detecta. | Añadir validación HTTP explícita: `curl GET /api/tools/available` y comparar output con `fap tools list --json`. |
| **R3:** `agent_create --dry-run` no valida validación del backend | **Media** | El CLI construye el payload localmente pero no lo envía. Si el backend rechaza campos que el CLI acepta (ej: `llm_provider` inválido), no se detecta. | Añadir validación con envío real (non-dry-run) + verificación de response 201/200. |
| **R4:** `validate_builder_nav.py` puede romper con cambios futuros en la estructura de archivos del dashboard | **Media** | El script usa paths hardcodeados. Si se mueve `BuilderLayout.tsx` o `page.tsx`, el script falla con falsos negativos. | Documentar los paths como constantes al inicio del script. Añadir test que verifique que los paths existen antes de correr checks. |
| **R5:** `fap agent run` depende de backend corriendo + agente creado previamente | **Media** | Si el backend no está corriendo o el agente no existe, la validación falla con error de conexión, no con error de contrato. | El orden de ejecución importa: seed → create → run. Documentar precondiciones. La herramienta DX debe validar precondiciones antes de ejecutar. |
| **R6:** MCP servers pueden no estar disponibles durante la validación | **Baja** | `fap tools list` depende de `org_mcp_servers` para listar tools MCP. Si no hay servers configurados, la sección MCP queda vacía pero no falla. | Documentar que la validación MCP es opcional y depende de infraestructura externa. El CLI ya maneja graceful degradation. |
| **R7:** Falsos positivos residuales en `validate_builder_nav.py` después del fix | **Baja** | La detección por string matching (incluso con regex) puede fallar si el código se formatea con Prettier de manera inesperada. | Considerar migración futura a AST parsing (como `validate_builder_mocks.py`) en Paso 15. Para Paso 12, regex es suficiente. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| **0** | **DX & Tooling**: Crear `fap validate-dogfood` | `src/cli/commands/validate_dogfood.py` | `def validate_dogfood(org_id: str, api_url: str, json_output: bool) -> None` | `src/cli/commands/doctor_builder.py::doctor_builder()` — ejecución secuencial de checks con tabla Rich | DX | Media | 2h | Ninguna | → verificar: `uv run fap validate-dogfood --help` ejecuta sin errores |
| **1** | Fix detección de props NavMain en `validate_builder_nav.py` (ID-049) | `scripts/validate_builder_nav.py` | `check_sidebar_ssot()` — reescribir `uses_navmain` con `re.search(r'items\s*=\s*\{defaultNavItems\}', content)` y usarlo en decisión real | `scripts/validate_builder_mocks.py` — usa AST parsing para detección | CODE | Baja | 0.5h | Tarea 0 | → verificar: `uv run python scripts/validate_builder_nav.py` exit 0, todos checks OK |
| **2** | Ejecutar y documentar validación de tools (ID-001) | `fap tools list` + `curl GET /api/tools/available` | Ejecución CLI + HTTP, output > `DEVS/IN_PROGRESS/evidencia-12-tools.md` | — | BACKEND | Baja | 0.5h | Tarea 0 | → verificar: `fap tools list --json` contiene tools locales, `curl` devuelve 200 con mismo count |
| **3** | Ejecutar y documentar validación de templates seed → list → detail → filter (ID-007, ID-009) | `fap templates seed` + `curl GET /api/templates` + `GET /api/templates/{id}` + `?category=` | Ejecución secuencial, evidencia > `DEVS/IN_PROGRESS/evidencia-12-templates.md` | — | DATA | Baja | 0.5h | Tarea 0 | → verificar: seed idempotente (2 ejecuciones = 0 errores), list devuelve 8, detail tiene soul_json, filter funciona |
| **4** | Ejecutar y documentar validación de agent create --dry-run + real (ID-013, ID-014) | `fap agent create --dry-run` + `fap agent create` real + `curl POST /agents` | Payload dry-run, luego POST real, verificar persistencia en DB | — | BACKEND | Media | 1h | Tarea 3 | → verificar: dry-run imprime payload válido, POST real → 201, `SELECT` en DB devuelve 1 row |
| **5** | Ejecutar y documentar validación de mapping templates → agentes (ID-022) | `fap templates use "X" --dry-run` para 8 templates | 8 ejecuciones, payloads > `DEVS/IN_PROGRESS/evidencia-12-mapping.md` | — | CODE | Media | 1h | Tarea 3 | → verificar: 8/8 dry-runs generan payloads con goal ≥ 10 chars, backstory ≥ 10 chars, role no vacío |
| **6** | Ejecutar y documentar validación de agent run (ID-028) | `fap agent run --role "X" --message "test" --watch` | Ejecución con agente creado en tarea 4, capturar output | — | BACKEND | Media | 1h | Tarea 4 | → verificar: exit 0, output muestra `[OK] Completed in Xs`, tokens usados > 0 |
| **7** | Ejecutar y documentar validación de bundle validate-payload (ID-041) | `fap bundle validate-payload --file test_payload.json` | Payload con 3 agentes, validar schema + warnings | — | CODE | Baja | 0.5h | Tarea 0 | → verificar: exit 0 con "Schema valid", exit 1 con JSON inválido, tabla de warnings muestra goal/backstory checks |
| **8** | Ejecutar validación completa integrada con `fap validate-dogfood` | `fap validate-dogfood --org-id $ORG_ID` | Ejecuta tareas 2-7 automáticamente, genera reporte unificado | — | FULLSTACK | Baja | 0.5h | Tareas 1-7 | → verificar: `fap validate-dogfood` exit 0, reporte muestra 8/8 secciones OK, `--json` genera JSON parseable |

**Tiempo total estimado:** 7.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

1. **Paso 13 (ID-003/004):** Reemplazar `asyncio.new_event_loop()` en `tools_list.py:_fetch_mcp_tools` por reutilización de event loop.
2. **Paso 13 (ID-033/039):** Migrar `agent_create.py`, `agent_run.py`, `templates_use.py` a `httpx.AsyncClient` para consistencia con backend async.
3. **Paso 15 (ID-053/054):** Añadir tests unitarios para `fap validate-dogfood` que mockeen los comandos subyacentes y validen el reporte.
4. **Cobertura HTTP real en dogfooding:** Las herramientas actuales (excepto `agent run`) no validan contratos HTTP. Futuro: añadir flag `--via-api` a `fap tools list` y `fap templates seed` para forzar validación HTTP.
5. **Migrar `validate_builder_nav.py` a AST parsing** (como `validate_builder_mocks.py`) para eliminar falsos positivos por formateo de código.

---

## 🚫 Reglas de Oro — Cumplimiento

| Regla | Cumplimiento |
|---|---|
| Análisis accionable y específico | ✅ Cada tarea tiene artefacto, interfaz, patrón y verificación |
| TODO verificado contra código | ✅ 36 elementos verificados (§0) |
| Señalar ambigüedades + resolución | ✅ 5 discrepancias documentadas con resolución propuesta |
| Código gana sobre plan | ✅ D1/D2: bug real en `validate_builder_nav.py` priorizado sobre descripción del plan |
| Nivel CTO exigente | ✅ Hallazgo crítico: 5/7 herramientas no validan HTTP real |
| Coherente con phase-state.md | ✅ Pasos 1-11 completados, contratos y decisiones respetados |
| TODO el paso (sub-pasos incluidos) | ✅ 8 tareas del plan cubiertas en plan de implementación |
| Etapas secuenciales | ✅ Data → Code → Backend → Fullstack+DX |
| ≥ 1 herramienta DX | ✅ `fap validate-dogfood` propuesta como Tarea 0 |
| Tareas atómicas | ✅ 1 artefacto por tarea, interfaz completa, patrón explícito |
| El implementador no decide nada | ✅ Firmas exactas, nombres de archivo, comandos de verificación inline |
