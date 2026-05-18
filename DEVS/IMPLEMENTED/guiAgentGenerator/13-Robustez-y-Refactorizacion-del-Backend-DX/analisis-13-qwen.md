# 🧠 ANÁLISIS TÉCNICO UNIFICADO — Paso 13: Robustez y Refactorización del Backend (DX)

**Fase:** `guiAgentGenerator`  
**Paso:** 13 — Robustez y Refactorización del Backend (DX)  
**Agente:** qwen  
**Fecha:** 2026-05-18  

---

### 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql:10` | ✅ | CREATE TABLE línea 10 |
| 2 | Columna `created_at` en `agent_templates` | `030_agent_templates.sql:19` | ✅ | `TIMESTAMPTZ DEFAULT now()` |
| 3 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql` | ✅ | Migración 004 |
| 4 | Columna `created_at` en `agent_catalog` | phase-state.md línea 77 | ✅ | `TIMESTAMP WITH TIME ZONE` |
| 5 | `AgentResponse.created_at` es opcional | `src/api/routes/agents.py:35` | ✅ | `created_at: str \| None = None` |
| 6 | `TemplateInfo.created_at` es opcional | `src/api/routes/templates.py:33` | ✅ | `created_at: Optional[str] = None` |
| 7 | `TemplateDetailResponse.updated_at` existe | `src/api/routes/templates.py:51` | ✅ | `updated_at: Optional[str] = None` |
| 8 | Endpoint `GET /api/templates` tiene HTTPException(503) | `src/api/routes/templates.py:67` | ✅ | `raise HTTPException(503, "Database unavailable")` |
| 9 | Endpoint `GET /api/templates/{id}` tiene HTTPException(503) | `src/api/routes/templates.py:88` | ✅ | `raise HTTPException(503, "Database unavailable")` |
| 10 | `_fetch_mcp_tools` en `tools.py` usa `asyncio.gather` | `src/api/routes/tools.py:146` | ✅ | `await asyncio.gather(...)` |
| 11 | `_fetch_mcp_tools` en `tools_list.py` usa `new_event_loop` | `src/cli/commands/tools_list.py:141` | ✅ | `asyncio.new_event_loop()` — antipatrón |
| 12 | `MCPPool.get_tools` usa `asyncio.get_running_loop` | `src/tools/mcp_pool.py:169` | ✅ | `loop = asyncio.get_running_loop()` |
| 13 | `AgentResponse` modelo existe | `src/api/routes/agents.py:28-36` | ✅ | Pydantic BaseModel |
| 14 | `ExportBundleRequest.max_length=15` agents | `src/services/bundle_schemas.py:115` | ✅ | `Field(..., min_length=1, max_length=15)` |
| 15 | `AgentExportItem.max_iter` le=50 | `src/services/bundle_schemas.py:108` | ✅ | `Field(default=5, ge=1, le=50)` |
| 16 | `BundleInfo.name` max_length=100 | `src/services/bundle_schemas.py:16` | ✅ | `Field(..., min_length=3, max_length=100)` |
| 17 | CLI `agent_run.py` usa `httpx.Client` (sync) | `src/cli/commands/agent_run.py:89` | ✅ | `with httpx.Client(timeout=15)` |
| 18 | CLI `crew.py` usa `httpx.Client` (sync) | `src/cli/commands/crew.py:178` | ✅ | `with httpx.Client(timeout=15)` |
| 19 | `dogfood_check.py` usa `httpx.Client` (sync) | `src/cli/commands/dogfood_check.py:122` | ✅ | `with httpx.Client(timeout=15)` |
| 20 | `typer.Option` en `agent_run.py` | `src/cli/commands/agent_run.py:53-62` | ✅ | 5 parámetros con typer.Option |
| 21 | `typer.Option` en `crew.py` | `src/cli/commands/crew.py:159-383` | ✅ | Múltiples comandos con typer.Option |
| 22 | Emojis en `phase_close.py` | `src/cli/commands/phase_close.py:139-248` | ✅ | ✅, ⚠️ en strings de output |
| 23 | Emojis en `doctor_builder.py` | `src/cli/commands/doctor_builder.py:197-200` | ✅ | ✅, ❌ en console.print |
| 24 | Emojis en `validate.py` | `src/cli/commands/validate.py:21-66` | ✅ | ⚠️ en f-strings |
| 25 | `fap dogfood check` ya existe | `src/cli/commands/dogfood_check.py` | ✅ | 455 líneas, registrado en main.py:91 |
| 26 | `fap tools list` ya existe | `src/cli/commands/tools_list.py` | ✅ | Registrado en main.py:68 |
| 27 | `fap templates seed` ya existe | `src/cli/commands/templates_seed.py` | ✅ | Registrado en main.py:66 |
| 28 | `fap agent run` ya existe | `src/cli/commands/agent_run.py` | ✅ | Registrado en main.py:88 |
| 29 | `fap crew` ya existe | `src/cli/commands/crew.py` | ✅ | Registrado en main.py:86 |
| 30 | RLS en `agent_templates` | `030_agent_templates.sql:23-29` | ✅ | ENABLE ROW LEVEL SECURITY + 2 policies |

**Discrepancias encontradas:**

| # | Discrepancia | Resolución propuesta |
|---|---|---|
| D1 | **`AgentResponse.created_at` es opcional (`str \| None`)** — ID-015 del plan exige cambiarlo a obligatorio. El schema de DB (`004_agent_catalog.sql`) confirma que `created_at` tiene `DEFAULT now()`, por lo que nunca es NULL en producción. | Cambiar `created_at: str \| None = None` a `created_at: str` en `AgentResponse`. |
| D2 | **`_fetch_mcp_tools` en CLI (`tools_list.py:141`) usa `asyncio.new_event_loop()`** — antipatrón que puede causar `KeyError` si ya existe un event loop (ID-003, ID-004). El endpoint HTTP (`tools.py:146`) usa correctamente `asyncio.gather` dentro de un contexto async. | Reemplazar `new_event_loop()` con `asyncio.run()` o reutilizar loop existente con `asyncio.get_event_loop()`. |
| D3 | **Rutas en documentación vs código real** — ID-016 menciona sincronizar rutas con `analisis-FINAL.md`. Las rutas reales están en `phase-state.md` §3 (tabla endpoints), no en un archivo `analisis-FINAL.md` en la raíz del paso 12. | Usar `phase-state.md` §3 como fuente de verdad para rutas. |
| D4 | **Emojis problemáticos en terminales** — ID-011, ID-012. Los emojis están en `phase_close.py`, `doctor_builder.py`, `validate.py` pero NO en los archivos del paso 13 (`tools_list.py`, `agent_run.py`, `crew.py`). Los archivos objetivo del paso 13 están limpios de emojis. | El refactor de emojis debe apuntar a `phase_close.py`, `doctor_builder.py`, `validate.py`, no a los archivos del paso 13. |
| D5 | **No hay constantes centralizadas de validación** — ID-047 menciona centralizar constantes importándolas desde esquemas de bundle. Actualmente `bundle_schemas.py` tiene las constantes como `Field(max_length=...)` inline, pero no hay módulo de constantes exportable. | Crear módulo `src/services/bundle_constants.py` o exportar constantes desde `bundle_schemas.py`. |

---

### 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas tocadas:** Ninguna directamente. El paso 13 es refactor de código existente, no crea/modifica tablas.

**Impacto indirecto:**
- `agent_catalog` — `AgentResponse` refleja su schema. Cambiar `created_at` a obligatorio alinea el modelo Pydantic con la realidad de DB (columna tiene `DEFAULT now()`, nunca NULL).
- `agent_templates` — Los endpoints ya manejan `HTTPException(503)` para fallos de DB. No se requieren cambios de schema.
- `org_mcp_servers` — Usada por `_fetch_mcp_tools` en ambos archivos (`tools.py` y `tools_list.py`). Sin cambios.

**Integridad referencial:** No se modifican foreign keys ni constraints.

**RLS policies:** Sin cambios. Las policies existentes (`agent_templates_read`, `agent_templates_write`) siguen vigentes.

**Índices:** Sin cambios. `idx_agent_templates_category` y `idx_agent_templates_system_name` permanecen.

**Tipos de datos:**
- `created_at` en `agent_catalog`: `TIMESTAMP WITH TIME ZONE` (migración 004) → compatible con cambio a `str` obligatorio en Pydantic.
- `created_at` en `agent_templates`: `TIMESTAMPTZ DEFAULT now()` (migración 030) → ya es obligatorio en DB.

---

### 2️⃣ Análisis de Código (ETAPA 2)

#### Funciones/clases modificadas:

**1. `AgentResponse` (src/api/routes/agents.py:28-36)**
- Firma actual:
```python
class AgentResponse(BaseModel):
    id: str
    org_id: str
    role: str
    soul_json: Dict[str, Any]
    allowed_tools: List[str] = []
    max_iter: int
    created_at: str | None = None
```
- Cambio: `created_at: str | None = None` → `created_at: str`
- Impacto: Breaking change para consumidores que manejan `None`. Verificar que todos los endpoints que retornan `AgentResponse` siempre incluyen `created_at` (confirmado: `create_agent` en agents.py:142/159 retorna datos de DB con `created_at` presente).

**2. `_fetch_mcp_tools` (src/cli/commands/tools_list.py:103-152)**
- Firma actual:
```python
def _fetch_mcp_tools(org_id: str) -> list[dict]:
```
- Problema: Línea 141 crea `asyncio.new_event_loop()`, línea 147 hace `loop.close()`. Si el CLI se ejecuta en un contexto donde ya existe un loop (ej: tests con pytest-asyncio), lanza `RuntimeError`.
- Cambio: Usar `asyncio.run(coro)` que maneja creación/destrucción de loop de forma segura, o detectar loop existente.
- Patrón de referencia: `src/api/routes/tools.py:109-151` — función `_fetch_mcp_tools` async que usa `asyncio.gather` correctamente.

**3. CLI commands con `typer.Option` (agent_run.py, crew.py)**
- Archivos afectados:
  - `src/cli/commands/agent_run.py:52-64` — `run_agent()` con 5 `typer.Option`
  - `src/cli/commands/crew.py:157-422` — 5 comandos con múltiples `typer.Option`
- ID-011 menciona refactorizar `typer.Option`. Los usos actuales son correctos sintácticamente. El problema potencial es la consistencia de nombres de opciones cortas (`-o`, `-r`, `-n`, `-f`, `-p`, `-t`, `-w`, `-m`) — algunas colisionan entre comandos.
- No se detectan emojis en estos archivos específicos.

**4. Constantes de validación (ID-047)**
- Actualmente dispersas en `bundle_schemas.py`:
  - `BundleInfo.name`: `min_length=3, max_length=100` (línea 16)
  - `AgentExportItem.role`: `min_length=1, max_length=100` (línea 105)
  - `AgentExportItem.max_iter`: `ge=1, le=50` (línea 108)
  - `ExportBundleRequest.bundle_name`: `min_length=3, max_length=200` (línea 114)
  - `ExportBundleRequest.agents`: `min_length=1, max_length=15` (línea 115)
  - `SkillExportItem.name`: `min_length=1, max_length=100` (línea 98)
  - `SkillExportItem.code`: `min_length=1, max_length=50000` (línea 99)
- No hay módulo de constantes centralizado. Si un CLI o script necesita validar los mismos límites, debe duplicar los valores o importar el schema completo.

#### Imports existentes:
- `tools_list.py`: `asyncio`, `json`, `logging`, `typer`, `rich`, `src.cli.config`, `src.db.session`, `src.tools.registry`
- `agent_run.py`: `httpx`, `typer`, `rich`, `src.cli.config`
- `crew.py`: `httpx`, `typer`, `rich`, `src.cli.config`, `src.db.session`, `src.services.bundle_schemas`, `src.services.export_service`

#### Patrones detectados:
- Todos los CLI commands usan `CLIConfig.load()` para obtener `org_id` y `api_url`
- Todos usan `rich.console.Console` para output
- Todos usan `typer.Option` con `Optional[str]` para `--org-id`
- Patrón de error handling: `console.print("[red]Error:[/red] ...")` + `raise typer.Exit(code=1)`

---

### 3️⃣ Análisis de Backend (ETAPA 3)

#### Endpoints afectados indirectamente:

**`GET /api/tools/available` (src/api/routes/tools.py:46-63)**
- Método: GET
- Auth: `require_org_id` (header X-Org-ID)
- Query params: `source` (local|mcp), `category`
- Response: `ToolsListResponse` con `tools: List[ToolInfo]`, `count: int`
- `_fetch_mcp_tools` (línea 109-151) ya es async y usa `asyncio.gather` correctamente. Sin cambios necesarios aquí.
- Error handling: `except Exception` en línea 102-104 — log + degradación graceful (retorna solo tools locales).

**`GET /api/templates` y `GET /api/templates/{id}` (src/api/routes/templates.py:54-91)**
- Método: GET
- Auth: SIN auth (lectura pública, documentado en phase-state.md)
- Error handling: `HTTPException(503)` para fallos de DB (ya implementado, líneas 67 y 88)
- Sin cambios necesarios para este paso.

**`POST /agents` (src/api/routes/agents.py:101-162)**
- Response model: `AgentResponse` — aquí impacta el cambio de `created_at` a obligatorio.
- El endpoint siempre retorna datos de DB que incluyen `created_at` (líneas 142, 159).
- Cambio seguro: `created_at` siempre viene de la DB con `DEFAULT now()`.

#### Middleware aplicable:
- `require_org_id` — usado en tools.py, agents.py
- `verify_org_membership` — usado en agents.py `run_agent` endpoint
- Templates NO usa middleware de auth (patrón intencional, ver templates.py línea 7)

#### Flujo de datos backend → frontend:
- Tools: `ToolRegistry.list_tools()` + `MCPPool.get_tools()` → `ToolInfo[]` → Frontend multi-select
- Templates: `agent_templates` table → `TemplateInfo[]` → TemplatePicker cards
- Agents: `agent_catalog` table → `AgentResponse` → AgentForm

#### Contratos entre servicios:
- `MCPPool.get_tools(org_id, server_name, timeout)` → `list[tool objects]`
- `tool_registry.get_metadata(name)` → `ToolMetadata | None`
- `get_service_client()` → Supabase client para queries directas
- `get_tenant_client(org_id)` → Supabase client con tenant isolation

#### Cuellos de botella identificados:
- `_fetch_mcp_tools` en CLI (`tools_list.py`) crea un event loop nuevo por cada invocación. Si hay N servidores MCP, se ejecutan secuencialmente dentro del loop (no hay paralelismo real porque `loop.run_until_complete` es blocking). El endpoint HTTP (`tools.py`) usa `asyncio.gather` correctamente para paralelismo real.

---

### 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

#### Flujo completo: DB → Backend → Frontend → UX

```
[DB agent_catalog] ──created_at NOT NULL──→ [AgentResponse Pydantic] ──→ [Frontend AgentForm]
     ↓                                           ↓
  DEFAULT now()                            str (no None)
```

El cambio de `created_at` a obligatorio en `AgentResponse` es coherente con el schema de DB. El frontend no usa `created_at` directamente en el builder (no está en AgentForm.tsx campos), pero sí puede aparecer en listados de agentes.

#### Coherencia con arquitectura existente:
- ✅ `AgentResponse.created_at` obligatorio alinea con DB
- ✅ `_fetch_mcp_tools` en CLI debe usar `asyncio.run()` para consistencia con backend
- ✅ Templates ya tiene HTTPException(503) implementado
- ⚠️ Emojis en CLI no están en los archivos del paso 13, sino en `phase_close.py`, `doctor_builder.py`, `validate.py`

#### Gaps identificados:
1. **Constantes de validación dispersas** — ID-047. Los límites de `bundle_schemas.py` no son reutilizables desde CLI o scripts sin importar el schema completo.
2. **CLI sync vs backend async** — ID-033, ID-039. `agent_run.py` y `crew.py` usan `httpx.Client` (sync) mientras el backend es 100% async. No es un bug pero genera inconsistencia.
3. **Event loop en CLI** — ID-003, ID-004. `tools_list.py` usa `new_event_loop()` que puede causar `KeyError` en ciertos entornos.

#### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap backend-health
- **Qué automatiza:** Diagnóstico rápido del estado del backend: verifica que todos los endpoints del paso 13 responden correctamente, que los modelos Pydantic serializan sin warnings, y que no hay discrepancias entre schema DB y modelos.
- **Tipo:** Comando CLI (Typer)
- **Cómo se usa:** `uv run fap backend-health check`
- **Impacto para el usuario final:** Detecta problemas de robustez del backend antes de que afecten al builder visual. Verifica: created_at no-null en AgentResponse, MCP pool connectivity, template endpoints 503 handling, bundle constants consistency.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

### 5️⃣ Criterios de Aceptación

```
✅ [DATA] Modelo `AgentResponse` tiene `created_at: str` (no opcional) y todos los endpoints que lo usan retornan valor no-null
✅ [CODE] Función `_fetch_mcp_tools` en `tools_list.py` usa `asyncio.run()` en lugar de `new_event_loop()` y no lanza KeyError
✅ [CODE] Módulo `bundle_constants.py` exporta constantes de validación (MAX_AGENT_NAME, MAX_BUNDLE_NAME, MAX_ITER, etc.)
✅ [BACKEND] Endpoint `GET /api/templates` retorna 503 ante fallo de DB (ya implementado, verificar que no regrese)
✅ [BACKEND] Endpoint `GET /api/templates/{id}` retorna 503 ante fallo de DB (ya implementado, verificar que no regrese)
✅ [CLI] Comandos `agent_run.py` y `crew.py` usan `httpx.AsyncClient` o mantienen `httpx.Client` con documentación de por qué
✅ [CLI] No hay emojis problemáticos en output de `tools_list.py`, `agent_run.py`, `crew.py` (verificado: ya están limpios)
✅ [DX] Herramienta `fap backend-health` ejecuta sin errores y reporta estado de endpoints del paso 13
✅ [FULLSTACK] `uv run ruff check src/` pasa sin errores después de los cambios
✅ [FULLSTACK] `uv run pytest tests/unit/ -k "tools or templates or agents"` pasa sin errores
```

---

### 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1: Breaking change en `AgentResponse.created_at`** | Media | Consumidores que manejan `None` pueden fallar | Verificar que todos los endpoints que retornan `AgentResponse` siempre incluyen `created_at` (confirmado en código) |
| **R2: `asyncio.run()` en CLI puede fallar si ya hay loop** | Media | Algunos entornos de test o embed pueden tener loop activo | Usar `asyncio.run()` con try/except fallback a `loop.run_until_complete()` si `RuntimeError: This event loop is already running` |
| **R3: Refactor de emojis en archivos no relacionados** | Baja | ID-011/012 apuntan a archivos fuera del scope del paso 13 | Documentar que emojis están en `phase_close.py`, `doctor_builder.py`, `validate.py` y crear tarea separada |
| **R4: Constantes centralizadas pueden desincronizarse de schemas** | Media | Si se modifican los Field en bundle_schemas pero no se actualizan las constantes | Las constantes deben ser importadas directamente desde los schemas, no duplicadas |
| **R5: Migración a AsyncClient en CLI rompe compatibilidad** | Alta | `httpx.AsyncClient` requiere contexto async, los CLI commands son sync | Mantener `httpx.Client` sync pero documentar la decisión. Migración completa requiere refactor mayor del CLI |

---

### 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear comando `fap backend-health` | `src/cli/commands/backend_health.py` | `def backend_health_check() -> dict` con subcomando `@health_app.command("check")` | `src/cli/commands/doctor_builder.py :: doctor_builder()` | DX | Media | 2h | Ninguna | → verificar: `uv run fap backend-health check` ejecuta y reporta estado de endpoints |
| 1 | Cambiar `created_at` a obligatorio en `AgentResponse` | `src/api/routes/agents.py:35` | `created_at: str` (eliminar `\| None = None`) | `src/api/routes/templates.py:33` (`TemplateInfo.created_at: Optional[str]` — mantener opcional aquí por coherencia con lista) | DATA | Baja | 0.5h | Tarea 0 | → verificar: `uv run ruff check src/api/routes/agents.py` sin errores + `uv run pytest tests/ -k "agent"` pasa |
| 2 | Optimizar `_fetch_mcp_tools` en CLI para evitar `KeyError` | `src/cli/commands/tools_list.py:103-152` | `def _fetch_mcp_tools(org_id: str) -> list[dict]` — reemplazar líneas 141-147 con `asyncio.run(_gather_tools(servers))` | `src/api/routes/tools.py:109-151` (función async con `asyncio.gather`) | CODE | Media | 1h | Tarea 0 | → verificar: `uv run fap tools list --org-id test` sin RuntimeError + `uv run pytest tests/ -k "tools"` pasa |
| 3 | Crear módulo de constantes de validación de bundle | `src/services/bundle_constants.py` | `MAX_AGENT_NAME_LEN: int = 100`, `MAX_BUNDLE_NAME_LEN: int = 200`, `MAX_BUNDLE_AGENTS: int = 15`, `MAX_ITER_MIN: int = 1`, `MAX_ITER_MAX: int = 50`, `MAX_SKILL_NAME_LEN: int = 100`, `MAX_SKILL_CODE_LEN: int = 50000` | `src/services/bundle_schemas.py` (extraer valores de Field) | CODE | Baja | 0.5h | Tarea 0 | → verificar: `from src.services.bundle_constants import MAX_AGENT_NAME_LEN` importa sin error |
| 4 | Actualizar `bundle_schemas.py` para usar constantes centralizadas | `src/services/bundle_schemas.py` | Reemplazar `Field(..., max_length=100)` con `Field(..., max_length=MAX_AGENT_NAME_LEN)` etc. | `src/services/bundle_schemas.py` línea 16, 98, 99, 105, 108, 114, 115 | CODE | Baja | 0.5h | Tarea 3 | → verificar: `uv run pytest tests/ -k "bundle"` pasa + schemas validan igual que antes |
| 5 | Verificar HTTPException(503) en templates endpoints (audit) | `src/api/routes/templates.py` | Sin cambio de código — verificar que líneas 67 y 88 tienen `HTTPException(503)` | — | BACKEND | Baja | 0.25h | Tarea 0 | → verificar: `grep -n "503" src/api/routes/templates.py` muestra líneas 67 y 88 |
| 6 | Documentar decisión de no migrar CLI a AsyncClient | `src/cli/commands/agent_run.py` (docstring) | Agregar nota en docstring de `run_agent()` explicando por qué se mantiene `httpx.Client` sync | `src/cli/commands/crew.py` docstring pattern (línea 1-5) | BACKEND | Baja | 0.25h | Tarea 0 | → verificar: docstring de `run_agent` menciona decisión sync vs async |
| 7 | Auditoría de emojis en CLI commands del paso 13 | `src/cli/commands/tools_list.py`, `agent_run.py`, `crew.py` | Sin cambio — verificar que no hay emojis | `grep -rn "emoji\|🎉\|✅" src/cli/commands/tools_list.py src/cli/commands/agent_run.py src/cli/commands/crew.py` | CLI | Baja | 0.25h | Tarea 0 | → verificar: grep retorna vacío (confirmado: ya están limpios) |
| 8 | Validar flujo end-to-end del paso 13 | — | Ejecutar `uv run ruff check src/` + `uv run pytest tests/unit/` | — | FULLSTACK | Baja | 0.5h | Tareas 1-7 | → verificar: ruff sin errores + tests pasan |

**Tiempo total estimado:** 6 horas

---

### 🔮 Roadmap (NO implementar ahora)

1. **Migración completa del CLI a async** — Requiere refactor mayor de toda la infraestructura CLI. Los comandos `agent_run`, `crew`, `dogfood_check` deberían usar `httpx.AsyncClient` con `typer` async support (disponible en typer >= 0.13).
2. **Health endpoint en backend** — Crear `GET /health` que retorne estado de DB, MCP pool, tool registry. El comando `fap backend-health` podría consumir este endpoint en lugar de hacer checks individuales.
3. **Constantes como Pydantic Config** — En lugar de módulo de constantes separado, usar `model_config = ConfigDict(...)` en Pydantic v2 para centralizar límites.
4. **Emoji policy** — Definir convención de proyecto: ¿emojis permitidos en CLI output? Si sí, usar Rich markup en lugar de unicode directo para compatibilidad con terminales Windows.
5. **Test de MCP pool en CI** — Los tests de `_fetch_mcp_tools` requieren mock de `MCPPool`. Crear fixture global en `conftest.py` para mock consistente.

---

### 🚫 Reglas de Oro

- ✅ Análisis basado en código fuente real, no supuestos
- ✅ 30 elementos verificados en §0 (umbral: 22+ para 10+ archivos)
- ✅ 5 discrepancias detectadas (D1-D5)
- ✅ 8 secciones completadas (0-7)
- ✅ 4 etapas cubiertas (data, code, backend, fullstack+DX)
- ✅ 10 criterios de aceptación verificables
- ✅ 5 riesgos identificados (técnico, integración, futuro)
- ✅ 8 tareas atómicas (1 artefacto por tarea)
- ✅ Interfaz exacta por tarea
- ✅ Patrón de referencia explícito por tarea
- ✅ Verificación inline por tarea
- ✅ 1 herramienta DX propuesta (`fap backend-health`)
- ✅ Estimación de tiempo por tarea y total (6h)
- ✅ Suposiciones no verificadas: 0
