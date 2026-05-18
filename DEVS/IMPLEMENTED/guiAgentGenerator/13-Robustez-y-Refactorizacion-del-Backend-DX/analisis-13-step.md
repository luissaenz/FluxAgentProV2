# 🏛️ ANÁLISIS TÉCNICO UNIFICADO — Paso 13: Robustez y Refactorización del Backend (DX)

**Fase:** `guiAgentGenerator`
**Paso:** 13 — Robustez y Refactorización del Backend (DX)
**Estado:** ⏳ ANÁLISIS — Previo a implementación
**Fecha:** 2026-05-18
**Agente:** step

---

## 0️⃣ Verificación Contra Código Fuente (OBLIGATORIA)

> Verificación realizada con fuente de verdad: `src/api/routes/`, `src/cli/commands/`,
> `src/flows/`, `src/services/`, `supabase/migrations/`, `src/api/main.py`.

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql:6` | ✅ VERIFICADO | Migración 004, columna `created_at TIMESTAMPTZ DEFAULT now()` línea 14 — **NOT NULL** en DB |
| 2 | `AgentResponse` existe | `src/api/routes/agents.py:28` | ✅ VERIFICADO | Línea 28-35, modelo Pydantic |
| 3 | `AgentResponse.created_at` es Optional | `src/api/routes/agents.py:35` | ✅ VERIFICADO | Línea 35: `created_at: str \| None = None` — opcional con default `None` |
| 4 | `created_at` está en SELECT de `list_agents` | `src/api/routes/agents.py:77` | ❌ DISCREPANCIA | SELECT es `"id, role, soul_json, allowed_tools, max_iter"` — `created_at` **no está seleccionado** |
| 5 | `created_at` está en SELECT de `create_agent` (upsert) | `src/api/routes/agents.py:76,147` | ❌ DISCREPANCIA | No hay `.select("created_at")` tras el INSERT/UPDATE; se usa `result.data[0]` sin asegurar que traiga `created_at` |
| 6 | `created_at` está en response_model | `src/api/routes/agents.py:101` | ✅ VERIFICADO | `@router.post("", response_model=AgentResponse, status_code=201)` |
| 7 | `HttpException(503)` en templates | `src/api/routes/templates.py:67,88` | ✅ VERIFICADO | Ya implementado en ambas rutas — `raise HTTPException(503, "Database unavailable")` |
| 8 | `HttpException(503)` en agents | `src/api/routes/agents.py` (líneas 200, 74) | ❌ DISCREPANCIA | `get_agent_detail` y `list_agents` usan `try/except` de `get_tenant_client` sin captura de excepciones DB → 500 sin control |
| 9 | `_fetch_mcp_tools` en CLI | `src/cli/commands/tools_list.py:103` | ✅ VERIFICADO | Líneas 103-152, anti-patrón `asyncio.new_event_loop()` en 141 |
| 10 | `_fetch_mcp_tools` en API | `src/api/routes/tools.py:109` | ✅ VERIFICADO | Líneas 109-150, patrón correcto `await asyncio.gather()` |
| 11 | Emoji `🩺` en `doctor_builder.py` | `src/cli/commands/doctor_builder.py:170` | ✅ VERIFICADO | Presente: `🩺 FAP Doctor Builder — Diagnostics` |
| 12 | Emoji `✅` en `doctor_builder.py` | `src/cli/commands/doctor_builder.py:197` | ✅ VERIFICADO | Presente: `[OK]` → `✅ All checks passed.` |
| 13 | Emoji `❌` en `doctor_builder.py` | `src/cli/commands/doctor_builder.py:200` | ✅ VERIFICADO | Presente: `[red]❌` → `❌ Some checks failed.` |
| 14 | Emoji `🐶` en `dogfood_check.py` | `src/cli/commands/dogfood_check.py:313,329` | ✅ VERIFICADO | Presente en: `🐶 fap dogfood check` (dry-run y normal) |
| 15 | `httpx.Client` en `agent_run.py` (POST) | `src/cli/commands/agent_run.py:89` | ✅ VERIFICADO | `with httpx.Client(timeout=15) as client:` |
| 16 | `httpx.Client` en `agent_run.py` (poll loop) | `src/cli/commands/agent_run.py:131` | ✅ VERIFICADO | Recrea cliente por cada iteración de polling (hasta 60 iteraciones) |
| 17 | `httpx.Client` en `crew.py` | `src/cli/commands/crew.py:178` | ✅ VERIFICADO | `with httpx.Client(timeout=15) as client:` en `save_crew` |
| 18 | Patrón `httpx.AsyncClient` en `run.py` | `src/cli/commands/run.py:220,248` | ✅ VERIFICADO | Patrón correcto como referencia: `async with httpx.AsyncClient(timeout=timeout) as client:` |
| 19 | `bundle_schemas.py` → constantes exportables | `src/services/bundle_schemas.py:1-116` | ✅ VERIFICADO | No exporta constantes; solo Field constraints inline |
| 20 | `workflow_guardrails.py` → `ALLOWED_MODELS` | `src/flows/workflow_guardrails.py:16` | ✅ VERIFICADO | Definido inline, separado de `bundle_schemas.py` |
| 21 | `bundle_validate_payload.py` → min 10 hardcode | `src/cli/commands/bundle_validate_payload.py:84,88` | ✅ VERIFICADO | Hardcode `len(goal) >= 10` en líneas 84 y 88 — sin import de esquemas |
| 22 | `dogfood_check.py` → `httpx.Client` sync | `src/cli/commands/dogfood_check.py:122` | ⚠️ ADICIONAL | `with httpx.Client(timeout=15) as client:` en `_compare_tools_cli_vs_http` — también sync, **no solo** `agent_run.py` y `crew.py` ID-033/039 |

### Discrepancias encontradas

| # | Discrepancia | Severidad | Resolución propuesta |
|---|---|---|---|
| **D1** | `AgentResponse.created_at` es Optional en el modelo pero `NOT NULL DEFAULT now()` en DB (migraciones 004 y 025). Si el backend no envía el campo en el SELECT, construcción de `AgentResponse(**agent_data)` lanza `TypeError: missing required positional argument`. | **Alta** | 1) Quitar `= None` del campo → `created_at: str` 2) Asegurar que los INSERT devuelvan `created_at` (Supabase lo hace por DEFAULT) 3) Incluir `created_at` en todos los SELECT usados para construir `AgentResponse` |
| **D2** | `list_agents` (línea 77) y `create_agent` (línea 76) usan SELECT sin `created_at`. El upsert POST `/agents` devuelve 201 con `AgentResponse` que requiere `created_at`, pero Supabase puede no devolverlo si no se selecciona. | **Alta** | Agregar `created_at` a cada lista de columnas `.select(...)` |
| **D3** | `get_agent_detail` y `list_agents` no envuelven sus queries DB en `try/except HTTPException(503)`, a diferencia de `templates.py` lo cual ya hace. Si Supabase cae, el cliente recibe 500. | **Media** | Envolver cada bloque `get_tenant_client()` en `try/except Exception` → `raise HTTPException(503)` |
| **D4** | `_fetch_mcp_tools` en `tools_list.py:141-147` usa `asyncio.new_event_loop()` + `loop.run_until_complete()`. Antipatrón documentado en Paso 12. Adicionalmente, `return_exceptions=False` por defecto → un servidor MCP caído hace fallar toda la gather. | **Media** | Reemplazar por `result = asyncio.run(asyncio.gather(*[...], return_exceptions=True))`. O mejor: convertir función a async y consumirla desde un wrapper async. |
| **D5** | Emojis `🩺` (doctor_builder.py:170), `✅` (doctor_builder.py:197), `❌` (doctor_builder.py:200), `🐶` (dogfood_check.py:313,329) causan corrupción de terminal en Windows (cp1252), SSH sin UTF-8, y logs CI/CD. | **Baja** | Reemplazar por alias Rich: `[bold cyan]FAP Doctor Builder[/bold cyan]`, `[green]All checks passed.[/green]`, `[red]Some checks failed.[/red]`, `[bold cyan]fap dogfood check[/bold cyan]` |
| **D6** | `agent_run.py` y `dogfood_check.py` usan `httpx.Client` sincrónico (bloqueante), mientras `run.py` ya tiene el patrón `httpx.AsyncClient` correcto. Inconsistencia con el resto del stack async. `agent_run.py` crea y destruye hasta 60 clientes en el poll loop. | **Media** | Migrar a `asyncio.run(main_async())` + `httpx.AsyncClient` |
| **D7** | `bundle_validate_payload.py:84,88` hardcodea `len(x) >= 10` como constante mágica. Si el schema `ExportBundleRequest` cambia el mínimo, la CLI queda desincronizada. | **Baja** | Extraer constantes desde `bundle_schemas.py` Module-level: `GOAL_MIN_LENGTH = 10`, `BACKSTORY_MIN_LENGTH = 10` |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema de DB — Sin cambios estructurales

Este paso no crea tablas ni migraciones nuevas. Toca únicamente código sobre tablas existentes:

| Tabla | Migración | Columnas relevantes |
|---|---|---|
| `agent_catalog` | 004 + 025 | `id, org_id, role, soul_json, allowed_tools, max_iter, is_active, created_at, updated_at` |
| `agent_templates` | 030 | `id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at` |
| `tasks` | 001 + 002 | `id, org_id, flow_type, status, payload, result, error, tokens_used, created_at, updated_at` |

### Integridad Referencial

- `agent_catalog.org_id → organizations.id` (`ON DELETE CASCADE`) — verificado en migración 004
- `agent_catalog.(org_id, role)` Unique index — confirmado en migración 004:16
- RLS `agent_catalog_tenant_isolation` — versión moderna por `auth.role()` confirmada en migración 025

### RLS Policies

| Tabla | Policy | Estado |
|---|---|---|
| `agent_catalog` | `agent_catalog_tenant_isolation` (mig 025) | ✅ Activa — `auth.role() = 'service_role' OR org_id = current_org_id()` |
| `agent_templates` | Sin política RLS | ⚠️ Verify — Paso 03 mencionó RLS lectura pública/escritura system pero `templates.py` comenta "Sin auth" (línea where: 8) |

### Tipos de datos — Problemas detectados

| Campo | DB | Modelo Python | Problema |
|---|---|---|---|
| `agent_catalog.created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | `str \| None = None` en `AgentResponse:35` | Desalineación: DB no es NULL; modelo dice que sí puede serlo |
| `agent_catalog.created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | No seleccionado en `agents.py:77` | Si Supabase devuelve una tupla sin `created_at`, `AgentResponse(**data)` falla |

---

## 2️⃣ Análisis de Código (ETAPA 2)

### ID-015 — `AgentResponse.created_at` (requerido)

**Archivo:** `src/api/routes/agents.py:28-35`

**Modelo actual (líneas 28-35):**
```python
class AgentResponse(BaseModel):
    id: str
    org_id: str
    soul_json: Dict[str, Any]
    allowed_tools: List[str] = []
    max_iter: int
    created_at: str | None = None          # ← línea 35: Optional DEBE ser requerido
```

**Campos creados/modificados:**

| Campo | Firma antes | Firma después |
|---|---|---|
| `created_at` | `str \| None = None` | `str` (sin default) |

### ID-003/004 — `_fetch_mcp_tools` anti-patrón event loop

**Archivo:** `src/cli/commands/tools_list.py:103-152`

```python
# Líneas 141-147 — código actual a reemplazar:
loop = asyncio.new_event_loop()                        # ← anti-patrón
try:
    results = loop.run_until_complete(                   # ← crea loop nuevo cada llamada
        asyncio.gather(*[_fetch(s["name"]) for s in servers])
    )
finally:
    loop.close()
```

**Problema adicional:** no usa `return_exceptions=True`. Si un MCP server falla, toda la gather falla.

**Patrón correcto en `src/api/routes/tools.py:146`:**
```python
results = await asyncio.gather(*[_fetch(s["name"]) for s in servers], return_exceptions=False)
```

### ID-010 — `HTTPException(503)` en agents.py

**Archivo:** `src/api/routes/agents.py:74,200` — Sin `try/except` → 500 ante fallo DB
**Referencia patrón correcto:** `src/api/routes/templates.py:59-67` — `try/except Exception` → `HTTPException(503)`

### ID-011/012 — Emojis en salida CLI

**Archivo:** `src/cli/commands/doctor_builder.py:170,197,200` — 3 emojis

```python
# Línea 170 — cambiar:
console.print("\n[bold cyan]🩺 FAP Doctor Builder — Diagnostics[/bold cyan]\n")
# Por:
console.print("\n[bold cyan]FAP Doctor Builder — Diagnostics[/bold cyan]\n")

# Línea 197 — cambiar:
console.print("\n[bold green]✅ All checks passed.[/bold green]\n")
# Por:
console.print("\n[bold green]All checks passed.[/bold green]\n")

# Línea 200 — cambiar:
console.print("\n[bold red]❌ Some checks failed. Fix issues before proceeding.[/bold red]\n")
# Por:
console.print("\n[bold red]Some checks failed. Fix issues before proceeding.[/bold red]\n")
```

**Archivo:** `src/cli/commands/dogfood_check.py:313,329` — 2 emojis

```python
# Líneas 313 y 329 — cambiar:
console.print("\n[bold cyan]🐶 fap dogfood check --dry-run[/bold cyan]\n")
console.print("\n[bold cyan]🐶 fap dogfood check[/bold cyan]")
# Por:
console.print("\n[bold cyan]fap dogfood check --dry-run[/bold cyan]\n")
console.print("\n[bold cyan]fap dogfood check[/bold cyan]")
```

### ID-033/039 — `httpx.Client` → `httpx.AsyncClient`

**Archivo:** `src/cli/commands/agent_run.py`

**Bloque 1 (POST trigger, línea 89-94):**
```python
# ANTES:
with httpx.Client(timeout=15) as client:
    response = client.post(run_url, json={...}, headers=headers)

# DESPUÉS:
async def run_agent_async(...):
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(...)
# Envolver llamada completa en asyncio.run()
```

**Bloque 2 (poll loop, línea 131):**
```python
# ANTES: crea 60+ clientes sincrónicos durante una sesión
with httpx.Client(timeout=10) as client:
    poll_response = client.get(poll_url, headers=headers)

# DESPUÉS: reutilizar AsyncClient durante todo el poll loop
async with httpx.AsyncClient(timeout=10) as client:
    poll_response = await client.get(poll_url, headers=headers)
```

**Patrón de referencia:** `src/cli/commands/run.py:220-238`

```python
async def _run_remote_agent(role, inputs, timeout):
    config = CLIConfig.load()
    ...
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=inputs, headers=headers)
        response.raise_for_status()
        ...
        await _poll_task(client, ...)
```

**Archivo:** `src/cli/commands/crew.py:178`

```python
# ANTES:
with httpx.Client(timeout=15) as client:
    response = client.get(url, headers=headers)

# DESPUÉS: envolver save_crew en asyncio.run()
```

### ID-047 — Constantes de validación desde bundle schemas

**Archivo:** `src/services/bundle_schemas.py`
- `AgentExportItem.max_iter: int = Field(default=5, ge=1, le=50)` (línea 108)
- `SkillExportItem.name: str = Field(..., min_length=1, max_length=100)` (línea 98)
- `SkillExportItem.code: str = Field(..., min_length=1, max_length=50000)` (línea 99)
- `ExportBundleRequest.bundle_name: str = Field(default=None, min_length=3, max_length=200)` (línea 114)

**Archivo:** `src/cli/commands/bundle_validate_payload.py:84,88` — hardcode sin importación:
```python
if isinstance(goal, str) and len(goal) >= 10:        # línea 84
    agent_goals_ok += 1
# Debería ser: len(goal) >= BUNDLE_GOAL_MIN_LENGTH
```

**Solución propuesta** — Añadir al final de `bundle_schemas.py`:
```python
# ── Constants for CLI/reference use ───────────────────────────────────────
GOAL_MIN_LENGTH = 10
BACKSTORY_MIN_LENGTH = 10
MAX_AGENTS_PER_BUNDLE = 15
```

Y en `bundle_validate_payload.py`:
```python
from src.services.bundle_schemas import ExportBundleRequest, GOAL_MIN_LENGTH, BACKSTORY_MIN_LENGTH
# ...
if isinstance(goal, str) and len(goal) >= GOAL_MIN_LENGTH:
```

### Modularidad — Evaluación

| Archivo | Cohesión | Acoplamiento | Observación |
|---|---|---|---|
| `agents.py` | Alta | Baja | Cada handler es independiente; SELECT duplicado sin abstraer |
| `tools_list.py` | Media | Baja | `_fetch_mcp_tools` sincrónico envuelve async — mezcla de paradigmas |
| `agent_run.py` | Alta | Media | Polling loop mezclado con sync HttpClient → acoplamiento innecesario |
| `crew.py` | Alta | Baja | `save_crew` parseo manual vs. usar servicio existente |
| `bundle_validate_payload.py` | Alta | Baja (tras fix ID-047) | Lógica de validación duplicada con `bundles.py` |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints tocados

| Ruta | Método | Archivo | Auth |
|---|---|---|---|
| `POST /agents` | POST | `src/api/routes/agents.py:101` | `require_org_id` |
| `GET /agents` | GET | `src/api/routes/agents.py:64` | `require_org_id` |
| `GET /agents/by-role/{role}` | GET | `src/api/routes/agents.py:165` | `require_org_id` |
| `GET /agents/{agent_id}/detail` | GET | `src/api/routes/agents.py:188` | `require_org_id` |
| `POST /agents/{role}/run` | POST | `src/api/routes/agents.py:312` | `verify_org_membership` |
| `GET /api/templates` | GET | `src/api/routes/templates.py:54` | público (sin auth) |
| `GET /api/templates/{id}` | GET | `src/api/routes/templates.py:74` | público (sin auth) |
| `GET /api/tools/available` | GET | `src/api/routes/tools.py` | `require_org_id` |

### Middleware aplicable

| Ruta | Middleware actual | Falta |
|---|---|---|
| `POST /agents` | `require_org_id` | None |
| `GET /agents` | `require_org_id` | None |
| `GET /agents/{role}/run` | `verify_org_membership` | None |
| ` agents/{id}/detail` | `require_org_id` implícito | FALTA: `try/except(DB) → HTTPException(503)` |
| `/api/templates` | Ninguno | Ya tiene 503 (líneas 65-67) |
| `/api/tools/available` | `require_org_id` | None |

### Flujos de datos backend → frontend

```
Frontend (Builder AgentForm)
  └─ POST /agents → AgentResponse {id, org_id, role, soul_json, allowed_tools, max_iter, created_at}
       └─ INSERT/UPDATE agent_catalog → Supabase RETURNING *

Frontend (Agent Playground)
  └─ POST /agents/{role}/run → RunAgentResponse {task_id, status}
       └─ BackgroundTask executa BaseCrew.run_async()
  └─ GET /tasks/{task_id} → TaskResponse (polling)

CLI (fap agent run)
  └─ httpx.Client → POST /agents/{role}/run → task_id
  └─ httpx.Client polling → GET /tasks/{task_id} → resultado
```

### Contratos

| Endpoint | Input | Output | Status |
|---|---|---|---|
| `POST /agents` | `AgentCreate {role, soul_json, allowed_tools, max_iter}` | `AgentResponse {id, org_id, role, soul_json, allowed_tools, max_iter, created_at}` | 201 / 409 (dup) |
| `GET /agents` | query `active_only: bool = true` | `ListAgentsResponse {agents: AgentListItem[]}` | 200 |
| `GET /agents/{id}/detail` | path `agent_id` | `dict {agent, metrics, credentials}` | 200 / 404 |
| `POST /agents/{role}/run` | `RunAgentRequest {input_data}` | `RunAgentResponse {task_id, status}` | 200 |
| `GET /tasks/{task_id}` | path `task_id` | `TaskResponse` | 200 / 404 |

### Error handling

| Escenario | Endpoint | Comportamiento actual | Deseado |
|---|---|---|---|
| Supabase cae en `list_agents` | `GET /agents` | Excepción Python sin capturar → 500 | `HTTPException(503, "Database unavailable")` |
| Supabase cae en `create_agent` | `POST /agents` | Excepción Python sin capturar → 500 | `HTTPException(503, "Database unavailable")` |
| Supabase cae en `get_agent_detail` | `GET /agents/{id}/detail` | Excepción Python sin capturar → 500 | `HTTPException(503, "Database unavailable")` |
| MCP server cae | `GET /api/tools/available` | `MCPConnectionError` capturado → log warning + degradación graceful | ✅ Ya correcto |
| DB cae en `templates` | `GET /api/templates` | `HTTPException(503)` | ✅ Ya correcto |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

```
DB (Supabase): agent_catalog.created_at = TIMESTAMPTZ DEFAULT now() [NOT NULL]
  ↓
Backend (agents.py): AgentResponse(**agent_data) ← requiere created_at como str
  ↓ FRAGILIDAD: Si SELECT no incluye created_at → TypeError/Pydantic ValidationError
  ↓
Frontend (AgentForm.tsx): guarda en Supabase aguardando respuesta 201 con created_at
  ↓ RISCO: Frontend espera el campo, backend puede no enviarlo
```

### Gaps de coherencia

| Gap | Descripción |
|---|---|
| **G1** | `AgentResponse.created_at` Optional pero DB NOT NULL → riesgo de TypeError silencioso |
| **G2** | `list_agents` y `create_agent` SELECT excluyen `created_at` → dato nunca llega al frontend |
| **G3** | `agent_run.py` sync bloqueante en stack async → overhead innecesario, difícil escalar a polling concurrente |
| **G4** | No existe `analisis-FINAL.md` para documentar rutas de BD → alineación paso 13(ID-016) sin punto de partida |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta Propuesta: fap db-sync check
- **Qué automatiza:** Detecta desalineaciones entre schema DB (migraciones) y modelos Pydantic backend. Para cada tabla compara: columnas en DB vs campos en ResponseModel, tipos (TIMESTAMPTZ vs str), y si el SELECT de cada endpoint incluye las columnas requeridas por el response_model.
- **Tipo:** CLI (Typer)
- **Ubicación:** src/cli/commands/db_sync_check.py
- **Cómo se usa:** uv run fap db-sync check
- **Impacto para el usuario final:** Previene errores 500 en runtime por desalineación DB/backend. Reduce verificación de consistencia de 30min de comparación manual a <2segundos.
- **Prioridad:** Tarea 0 — implementar antes del resto del paso 13
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `agent_catalog` migración 004 define `created_at TIMESTAMPTZ DEFAULT now()` (NOT NULL)
✅ [DATA] Tabla `agent_templates` migración 030 define `created_at` + `updated_at` correctamente
✅ [DATA] `agent_templates` con RLS confirmada sin política activa (confirmar si es intencional)
✅ [CODE] `AgentResponse.created_at` es `str` (sin `= None`) en `src/api/routes/agents.py:35`
✅ [CODE] `.select(...)` en `list_agents`, `create_agent`, `get_agent_detail` incluye `created_at`
✅ [CODE] `_fetch_mcp_tools` en `tools_list.py` usa `asyncio.run()` o patrón async correcto, no `new_event_loop()`
✅ [CODE] Emojis `🩺`, `✅`, `❌`, `🐶` removidos de `doctor_builder.py` y `dogfood_check.py`
✅ [BACKEND] `GET /agents/{id}/detail` y `GET /agents` envuelven queries DB en `try/except → HTTPException(503)`
✅ [BACKEND] `fap agent run` funciona end-to-end sin errores tras migración a `httpx.AsyncClient`
✅ [BACKEND] `fap crew save` funciona sin errores tras migración a `asyncio.run()`
✅ [FULLSTACK] `POST /agents` devuelve 201 con `AgentResponse` completo incluyendo `created_at`
✅ [DX] Herramienta `fap db-sync check` ejecuta sin errores y detecta desalineaciones DB/backend
```

---

## 6️⃣ Plan de Implementación

> **Reglas de segmentación atómica:**
> 1. **Una tarea = un artefacto:** archivo o función.
> 2. **Interfaz completa en la tarea:** firma exacta del artefacto.
> 3. **Patrón de referencia explícito:** archivo concreto.
> 4. **Verificación inline:** comando concreto que confirma completitud.
> 5. **Atomicidad test:** implementador no debe tomar decisiones de diseño.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Implementar `fap db-sync check` | `src/cli/commands/db_sync_check.py` | `def check_db_sync(org_id: str) -> None: ...` comandos: `check`, `--json` | `src/cli/commands/doctor_builder.py :: doctor_builder()` | DX | Media | 1.5h | Ninguna | `uv run fap db-sync check` ejecuta sin errores |
| 1 | Hacer `created_at` requerido en `AgentResponse` | `src/api/routes/agents.py:35` |Cambiar `created_at: str \| None = None` → `created_at: str` (sin default) | `src/api/routes/templates.py:33` (`TemplateInfo`) | CODE | Baja | 0.25h | Tarea 0 | `uv run ruff check src/api/routes/agents.py` sin errores |
| 2 | Incluir `created_at` en SELECT de `list_agents` | `src/api/routes/agents.py:77` | Agregar `"created_at"` al `.select(...)` | `src/api/routes/templates.py:61` (`.select("*")`) | CODE | Baja | 0.25h | Tarea 1 | `grep "select.*created_at" src/api/routes/agents.py` devuelve 4 coincidencias |
| 3 | Incluir `created_at` en tracking de `create_agent` | `src/api/routes/agents.py:76,147` | Asegurar que el SELECT tras UPDATE/INSERT incluya `created_at` | `src/api/routes/templates.py:61` | CODE | Baja | 0.25h | Tarea 2 | `uv run pytest tests/ -k test_create_agent` pasa |
| 4 | Agregar `try/except DB → 503` en `list_agents` | `src/api/routes/agents.py:64-98` | Envolver bloque `get_tenant_client` línea 74 en `try/except Exception` | `src/api/routes/templates.py:59-67` | BACKEND | Baja | 0.25h | Tarea 3 | `uv run pytest tests/ -k test_list_agents_db_fail` (crear si no existe) |
| 5 | Agregar `try/except DB → 503` en `create_agent` | `src/api/routes/agents.py:101-163` | Envolver bloque `get_tenant_client` línea 112 en `try/except Exception` | `src/api/routes/templates.py:59-67` | BACKEND | Baja | 0.25h | Tarea 4 | `uv run pytest tests/ -k test_create_agent_db_fail` |
| 6 | Agregar `try/except DB → 503` en `get_agent_detail` | `src/api/routes/agents.py:188-309` | Envolver bloques `get_tenant_client` líneas 200 y 254 | `src/api/routes/templates.py:59-67` | BACKEND | Baja | 0.5h | Tareas 4, 5 | `uv run pytest tests/ -k test_agent_detail_db_fail` |
| 7 | Refactor `_fetch_mcp_tools` en `tools_list.py` | `src/cli/commands/tools_list.py:141-147` | Reemplazar `new_event_loop()` + `run_until_complete()` por `asyncio.run()` | `src/cli/commands/run.py:_run_remote_agent()` (línea 220) | CODE | Media | 0.75h | Tareas 0-6 | `uv run fap tools list --source mcp` ejecuta sin warnings de event loop |
| 8 | Remover emojis de `doctor_builder.py` | `src/cli/commands/doctor_builder.py:170,197,200` | Reemplazar `🩺` → texto plano, `✅` → `[green]...[/green]`, `❌` → `[red]...[/red]` | `src/cli/commands/run.py` (sin emoji) | DX | Baja | 0.25h | Tarea 7 | `uv run fap doctor builder` output sin emojis |
| 9 | Remover emojis de `dogfood_check.py` | `src/cli/commands/dogfood_check.py:313,329` | Reemplazar `🐶` → `fap dogfood check` | `src/cli/commands/run.py` (sin emoji) | DX | Baja | 0.25h | Tarea 8 | `uv run fap dogfood check --dry-run` output sin emojis |
| 10 | Migrar `agent_run.py` a `httpx.AsyncClient` | `src/cli/commands/agent_run.py:86-174` | Refactor a `async def run_agent_async(...)` envuelto en `asyncio.run(run_agent_async())` | `src/cli/commands/run.py:213-238` | BACKEND | Alta | 2h | Tareas 0, 8, 9 | `uv run fap agent run --role test --message "hola"` funciona correctamente |
| 11 | Migrar `crew.py save_crew` a `asyncio.run` + `AsyncClient` | `src/cli/commands/crew.py:157-217` | Convertir `save_crew` a `async def _save_crew_async()` + `asyncio.run()` | `src/cli/commands/run.py:220` | BACKEND | Media | 1h | Tarea 10 | `uv run fap crew save --name test --org-id <id>` funciona |
| 12 | Centralizar constantes en `bundle_schemas.py` (ID-047) | `src/services/bundle_schemas.py` (añadir al final) | Añadir: `GOAL_MIN_LENGTH = 10`, `BACKSTORY_MIN_LENGTH = 10`, `MAX_AGENTS_PER_BUNDLE = 15` | Mismo `bundle_schemas.py` líneas 1-116 | CODE | Baja | 0.25h | Tarea 11 | `grep "GOAL_MIN_LENGTH" src/services/bundle_schemas.py` existe |
| 13 | Importar constantes en `bundle_validate_payload.py` | `src/cli/commands/bundle_validate_payload.py:19,84,88` | Importar `GOAL_MIN_LENGTH, BACKSTORY_MIN_LENGTH` y reemplazar hardcodes | `src/services/bundle_schemas.py` (después de Tarea 12) | CODE | Baja | 0.25h | Tarea 12 | `grep "GOAL_MIN_LENGTH" src/cli/commands/bundle_validate_payload.py` existe |

**Tiempo total estimado:** ~5.25h (sin contar retardos por impedimentos)

---

## 7️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1:** `AgentResponse` required rompe serialización si `created_at` viene `null` | Alta | DB DEFAULT `now()` previene NULLs, pero un INSERT sin RETURNING podría no traer el campo | Verificar que Supabase Python client devuelve `created_at` en `result.data[0]` tras INSERT. Si no, usar `db.table(...).select("*")` explícitamente para INSERT. |
| **R2:** `asyncio.run()` no se puede anidar (no puede llamarse desde event loop activo) | Alta | Si `agent_run.py` ya está en un loop, `asyncio.run()` lanza `RuntimeError` | Usar `nest_asyncio.apply()` antes de `asyncio.run()` o usar patrón `asyncio.get_running_loop().run_until_complete()` como fallback |
| **R3:** Migración CLI a async cambia firma de entrypoints Typer | Media | Typer espera funciones síncronas; `async def` necesita wrapper | Usar patrón existente: función async interna + `asyncio.run()` en el comando Typer sync wrapper (igual que `run.py` hace) |
| **R4:** Emojis en otros archivos CLI no detectados | Baja | Análisis cubrió 2 archivos; pueden existir más con emoji | Ejecutar `rg "[\x{1F300}-\x{1F9FF}]" src/cli/` después del paso para scan completo |
| **R5:** `return_exceptions=True` en `_fetch_mcp_tools` enmascara errores | Media | Si se activa `return_exceptions=True` sin filtrar, errores se convierten en excepciones en la lista | Filtrar: `if isinstance(r, Exception): logger.warning(...) else: tools.extend(r)` |
| **R6:** JSON `created_at` desde Supabase es `str` pero tipo DB es `datetime` | Baja | Supabase devuelve timestamps como ISO strings, Pydantic `str` lo acepta directamente | No hay problema — verificar en pruebas que el string sea parseable por `datetime.fromisoformat()` |

---

## 8️⃣ Implementación del Paso — Estado

El paso se segmenta en **13 tareas** (0-12) en el §6 Plan de Implementación.

La **Tarea 0 (DX: `fap db-sync check`)** está como primer paso siguiendo la regla de oro del proyecto:
> *"Tarea 0 siempre = DX & Tooling. El implementador DEBE ejecutarla primero"*

La herramienta propuesta (`fap db-sync check`) automatiza la detección de desalineaciones entre el schema de DB y los modelos Pydantic, preveniendo el tipo de error que causa las discrepancias D1 y D2 detectadas en este análisis.

---

## 9️⃣ Resumen Ejecutivo

**Paso 13** aborda **7 Issues técnicas identificadas** (IDs 003, 004, 010, 011, 012, 015, 016, 033, 039, 047) en el backend y CLI de `guiAgentGenerator`. No crea funcionalidades nuevas — mejora la calidad técnica, el manejo de errores, el rendimiento y la coherencia de contratos.

**Cambio más crítico:** Hacer `AgentResponse.created_at` requerido (ID-015) + asegurar que todos los SELECT de `agents.py` incluyan el campo (D1, D2) — combinación que evita `TypeError` en runtime al construir respuestas.

**Cambio de mayor impacto DX:** La herramienta `fap db-sync check` (Tarea 0), que evita que discrepancias DB↔backend lleguen a producción.

**Compatibilidad con estado actual:** Los pasos 4-12 ya usan `AgentResponse` como response_model. Hacer `created_at` requerido no rompe contratos públicos porque Supabase (`TIMESTAMPTZ DEFAULT now()`) garantiza que el campo existe en todo registro. Los cambios son backward-compatible con el stack FastAPI/Pydantic.
