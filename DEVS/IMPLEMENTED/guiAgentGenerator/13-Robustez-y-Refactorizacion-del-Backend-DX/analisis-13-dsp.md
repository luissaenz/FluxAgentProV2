# 🧠 ANÁLISIS TÉCNICO — Paso 13: Robustez y Refactorización del Backend (DX)

**Fase:** `guiAgentGenerator`  
**Paso:** 13 — Robustez y Refactorización del Backend (DX)  
**Agente:** dsp  
**Fecha:** 2026-05-18  
**Estado:** Análisis completado  

---

### 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentResponse.created_at` tipado como `Optional` | grep en `src/api/routes/agents.py` | ❌ | Línea 35: `created_at: str \| None = None` — debe ser obligatorio |
| 2 | `phase-state.md` dice templates usan `require_org_id` | grep en `src/api/routes/templates.py` | ❌ | Líneas 6-7: código real NO usa auth — discrepancia con phase-state |
| 3 | `_fetch_mcp_tools` versión async en API | `src/api/routes/tools.py:109` | ✅ | Usa `asyncio.gather` — patrón correcto |
| 4 | `_fetch_mcp_tools` versión sync en CLI | `src/cli/commands/tools_list.py:141` | ❌ | Usa `asyncio.new_event_loop()` — antipatrón documentado en paso 12 |
| 5 | `HTTPException(503)` en templates ya implementado | `src/api/routes/templates.py:67,88` | ✅ | Ya existe: `raise HTTPException(503, "Database unavailable") from exc` |
| 6 | Emojis en CLI commands | grep en `src/cli/commands/` | ❌ | 🐶 en dogfood_check.py:313,329; 🩺 en doctor_builder.py:170; ✅/❌ en doctor_builder.py:197,200 |
| 7 | `typer.Option` sin keyword names (old-style) | `src/cli/commands/templates_seed.py:142-147` | ❌ | `typer.Option(False, help="...")` — parámetros posicionales sin nombre |
| 8 | CLI usa `httpx.Client` (sync) en vez de `AsyncClient` | grep en `src/cli/commands/` | ❌ | 10 ocurrencias en 8 archivos: agent_run.py, crew.py, agent_create.py, templates_use.py, dogfood_check.py, login.py, validate.py, publish.py |
| 9 | Constantes de validación centralizadas | grep `MIN_GOAL`/`MIN_BACKSTORY` en `src/` | ❌ | No existen — hardcodeados como `>= 10` en bundle_validate_payload.py:84,88 |
| 10 | `bundle_manager.py` límites hardcodeados | `src/services/bundle_manager.py:192,194` | ❌ | `20` (max flows), `30` (max skills) — sin importar desde config/schemas |
| 11 | Tabla `agent_catalog` tiene columna `created_at` | `supabase/migrations/` | ✅ | schema en phase-state.md:77 — `created_at TIMESTAMP WITH TIME ZONE` |
| 12 | Tabla `agent_templates` existe | `supabase/migrations/` | ✅ | schema en phase-state.md:79 |
| 13 | `src/services/bundle_schemas.py` no exporta constantes de validación | lectura completa | ✅ | Solo define modelos Pydantic, sin constantes `MIN_*` |
| 14 | `ExportService` comentario sobre `MIN_GOAL_LENGTH` | `src/services/export_service.py:55` | ⚠️ | Comentario NOTA menciona analisis-FINAL — las constantes nunca se definieron |
| 15 | Backend usa `asyncio` consistentemente | `src/api/routes/tools.py`, `mcp_pool.py` | ✅ | Uso de `asyncio.gather`, `asyncio.get_running_loop()` |
| 16 | CLI `agent_run.py` polling loop síncrono | `src/cli/commands/agent_run.py:89,131` | ❌ | `httpx.Client` creado dos veces por iteración — ineficiente |
| 17 | `crew.py` usa `httpx.Client` | `src/cli/commands/crew.py:178` | ✅ | Solo en `save` — otros comandos usan DB directa |
| 18 | `dogfood_check.py` usa `httpx.Client` | `src/cli/commands/dogfood_check.py:122,209` | ❌ | Dos instancias en funciones auxiliares |

**Discrepancias encontradas:** 10

| # | Discrepancia | Resolución propuesta |
|---|---|---|
| D1 | `AgentResponse.created_at` es `Optional` pero DB siempre lo retorna | Cambiar a `created_at: str` y asegurar que todas las queries devuelvan la columna |
| D2 | `phase-state.md` linea 83-87 declara `require_org_id` en templates pero el código real no lo usa | Corregir `phase-state.md` §3 tabla de endpoints para reflejar que templates son públicos |
| D3 | `tools_list.py:141` usa `asyncio.new_event_loop()` — antipatrón identificado en paso 12 (D5) | Usar `asyncio.run()` o migrar completamente a `httpx.AsyncClient` |
| D4 | Emojis Unicode (🐶🩺) en dogfood_check.py y doctor_builder.py causan problemas en terminales sin soporte UTF-8 | Reemplazar por alternativas ASCII o Rich markup (`:dog:`, `:stethoscope:`) con fallback |
| D5 | `templates_seed.py:142-147` usa old-style `typer.Option(pos, help)` sin keyword names | Refactorizar a `typer.Option(False, "--dry-run", help="...")` con nombre de flag explícito |
| D6 | 10 instancias de `httpx.Client` en CLI vs backend async — inconsistencia arquitectónica | Migrar a `httpx.AsyncClient` con `asyncio.run()` wrapper en entry points sync |
| D7 | `bundle_validate_payload.py:84,88` hardcodea `>= 10` para goal/backstory | Definir `MIN_GOAL_LENGTH = 10`, `MIN_BACKSTORY_LENGTH = 10` en `bundle_schemas.py` e importar |
| D8 | `bundle_manager.py:192,194` hardcodea límites `20`/`30` | Mover a `get_settings()` o constantes en `bundle_schemas.py` |
| D9 | `agent_run.py` crea nuevo `httpx.Client` por cada iteración del polling loop (linea 131) | Reutilizar un solo cliente con `async with` o mantener instancia única |
| D10 | `export_service.py` referencia `MIN_GOAL_LENGTH` inexistente en comentario | Definir la constante en `bundle_schemas.py` y eliminar el comentario NOTA |

---

### 1️⃣ Análisis de Datos (ETAPA 1)

#### Schema afectado

El paso 13 es puramente de refactorización y no introduce nuevas tablas ni migraciones. Sin embargo, las siguientes tablas son relevantes para verificar la integridad de los cambios:

- ✅ **`agent_catalog`** — columna `created_at` (TIMESTAMP WITH TIME ZONE, NOT NULL por defecto de Supabase). El cambio ID-015 afecta al modelo Pydantic, no al schema.
- ✅ **`agent_templates`** — sin cambios. ID-010 (503 handling) ya implementado.
- ✅ **`org_mcp_servers`** — consultada por `_fetch_mcp_tools` en ambas versiones (API + CLI). Sin cambios.

#### Impacto en datos existentes

- **ID-015:** Cambiar `created_at` de `Optional` a requerido en `AgentResponse` NO rompe datos existentes. Supabase siempre retorna `created_at` en inserciones con `default now()`. El riesgo está en el path de `update` (línea 129 de agents.py) donde `result.data` podría no incluir `created_at` si no se hace `.select()` explícito después del update.
- **ID-003/004:** Optimización de `_fetch_mcp_tools` es solo de rendimiento. Sin impacto en datos.

#### RLS Policies

Sin cambios. Los endpoints afectados (tools, templates) ya tienen su configuración RLS establecida.

---

### 2️⃣ Análisis de Código (ETAPA 2)

#### 2.1 ID-015: Strict Typing en `AgentResponse`

**Archivo:** `src/api/routes/agents.py:28-35`

**Estado actual:**
```python
class AgentResponse(BaseModel):
    id: str
    org_id: str
    role: str
    soul_json: Dict[str, Any]
    allowed_tools: List[str] = []
    max_iter: int
    created_at: str | None = None  # ← DEBE ser obligatorio
```

**Firma corregida:**
```python
class AgentResponse(BaseModel):
    id: str
    org_id: str
    role: str
    soul_json: Dict[str, Any]
    allowed_tools: List[str] = []
    max_iter: int
    created_at: str  # ← Obligatorio. DB siempre lo retorna.
```

**Riesgo identificado:** En `create_agent` (línea 128-143), el update path hace:
```python
result = db.table("agent_catalog").update({...}).eq("id", existing_id).execute()
```
La respuesta de `.update()` sin `.select()` explícito podría no incluir `created_at`. Esto debe verificarse y corregirse antes de hacer el campo obligatorio.

**Patrón de referencia:** `src/api/routes/templates.py:32-33` — `TemplateInfo` ya tiene `created_at: Optional[str] = None`. El cambio alinea `AgentResponse` con la realidad de la DB.

#### 2.2 ID-003, ID-004: Optimización `_fetch_mcp_tools`

**Dos versiones del mismo código — problema de duplicación:**

| Aspecto | API (`tools.py:109`) | CLI (`tools_list.py:103`) |
|---|---|---|
| Tipo | `async def` | `def` (sync) |
| Event loop | Usa el running loop | Crea `asyncio.new_event_loop()` |
| Patrón | `asyncio.gather` con `return_exceptions=False` | `loop.run_until_complete(asyncio.gather(...))` |
| Error handling | `except MCPConnectionError` + `except Exception` | `except MCPConnectionError` + `except Exception` |
| KeyError riesgo | Ninguno (usa `.get()` y `getattr()`) | Ninguno (usa `.get()` y `getattr()`) |

**Problema raíz:** La versión CLI crea un nuevo event loop cada vez que se llama. En entornos donde ya hay un loop corriendo (pytest-asyncio, Jupyter), `new_event_loop()` puede causar warnings de "There is already an event loop running".

**Solución propuesta:** Migrar CLI a `httpx.AsyncClient` (parte de ID-033/039), eliminando la necesidad de `_fetch_mcp_tools` sync completamente. El CLI llamaría al endpoint HTTP en vez de consultar DB directamente.

**Respecto a KeyError:** Tras revisión exhaustiva del código, NO se encontró riesgo real de `KeyError`. Ambas versiones acceden a diccionarios con `.get()` y a atributos con `getattr()`. La mención de `KeyError` en el plan podría referirse a un escenario ya resuelto o a una falsa alarma.

#### 2.3 ID-047: Centralización de Constantes de Validación

**Constantes hardcodeadas encontradas:**

| Ubicación | Valor | Significado |
|---|---|---|
| `bundle_validate_payload.py:84` | `>= 10` | MIN_GOAL_LENGTH |
| `bundle_validate_payload.py:88` | `>= 10` | MIN_BACKSTORY_LENGTH |
| `bundle_validate_payload.py:99` | `> 10` | MAX_AGENTS_WARNING_THRESHOLD |
| `bundle_manager.py:192` | `> 20` | MAX_FLOWS_PER_BUNDLE |
| `bundle_manager.py:194` | `> 30` | MAX_SKILLS_PER_BUNDLE |

**Archivo destino propuesto:** `src/services/bundle_schemas.py` (ya es el punto de importación natural para `ExportBundleRequest`)

**Constantes a definir:**
```python
# src/services/bundle_schemas.py — añadir al inicio del archivo
MIN_GOAL_LENGTH: int = 10
MIN_BACKSTORY_LENGTH: int = 10
MAX_AGENTS_PER_BUNDLE: int = 15      # ya existe en ExportBundleRequest Field
MAX_FLOWS_PER_BUNDLE: int = 20
MAX_SKILLS_PER_BUNDLE: int = 30
AGENT_COUNT_WARNING_THRESHOLD: int = 10
```

#### 2.4 ID-011, ID-012: CLI Polish

**Emojis problemáticos:**
| Archivo | Línea | Emoji | Propuesto |
|---|---|---|---|
| `dogfood_check.py` | 313, 329 | 🐶 | `[bold cyan]fap dogfood check[/bold cyan]` (ya tiene Rich markup) |
| `doctor_builder.py` | 170 | 🩺 | `[bold cyan]FAP Doctor Builder[/bold cyan]` |
| `doctor_builder.py` | 197, 200 | ✅ / ❌ | `[green]PASS[/green]` / `[red]FAIL[/red]` (ya tiene Rich markup) |

**typer.Option old-style (posicionales sin keyword):**
```python
# MAL — templates_seed.py:142-147
dry_run: bool = typer.Option(False, help="Preview without inserting")
reset: bool = typer.Option(False, help="Delete all existing system templates and re-insert")

# BIEN — con keyword arguments explícitos
dry_run: bool = typer.Option(False, "--dry-run", help="Preview without inserting")
reset: bool = typer.Option(False, "--reset", help="Delete all existing system templates and re-insert")
```

**Archivos con old-style:** `templates_seed.py:142-147` es el caso más claro. La mayoría de los otros comandos ya usan el estilo correcto con `--flag` explícito.

#### 2.5 Modularidad y Duplicación

- **Duplicación crítica:** `_fetch_mcp_tools` existe en dos archivos con firmas diferentes (async vs sync). La versión sync debería desaparecer al migrar CLI a HTTP (ID-033/039).
- **Duplicación de constantes:** `>= 10` aparece en 3 lugares (bundle_validate_payload.py, export_service.py comentario, y potencialmente dogfood_check.py).
- **Patrones inconsistentes:** `typer.Option` sin keyword names vs con keyword names vs `Annotated` pattern.

---

### 3️⃣ Análisis de Backend (ETAPA 3)

#### 3.1 Endpoints afectados

| Endpoint | Cambio | Impacto |
|---|---|---|
| `GET /api/tools/available` | Ninguno directo. `_fetch_mcp_tools` async ya optimizado. | Solo se beneficia si se reduce overhead de MCP pool |
| `POST /agents` | `AgentResponse.created_at` pasa a obligatorio | ⚠️ Requiere asegurar que `.update()` retorne `created_at` |
| `GET /api/templates` | ID-010 ya implementado (503 handling) | Sin cambios |
| `GET /api/templates/{id}` | ID-010 ya implementado (503 handling) | Sin cambios |

#### 3.2 Contratos y Middleware

**Discrepancia de documentación vs código (ID-016):**

`phase-state.md:83-87` documenta:
```
| `/api/templates` | GET | `src/api/routes/templates.py` | `require_org_id` |
| `/api/templates/{id}` | GET | `src/api/routes/templates.py` | `require_org_id` |
```

Pero el código real en `src/api/routes/templates.py:6-7`:
```python
Correcciones vs plan:
  - Endpoints SIN require_org_id (lectura publica, patron integrations.py)
```

Y las firmas de las funciones (`list_templates`, `get_template`) NO incluyen `Depends(require_org_id)`.

**Resolución:** `phase-state.md` debe actualizarse para reflejar que templates son endpoints públicos. El código es la fuente de verdad.

#### 3.3 Flujo de datos Backend → Frontend

Sin cambios en este paso. El flujo actual:
```
AgentForm (frontend) → POST /agents → AgentResponse → Supabase
                      ← GET /api/tools/available ← ToolRegistry + MCPPool
                      ← GET /api/templates ← agent_templates table
```

#### 3.4 Error Handling

| Endpoint | Error actual | ¿Cumple ID-010? |
|---|---|---|
| `GET /api/templates` | `HTTPException(503, "Database unavailable")` | ✅ Ya implementado |
| `GET /api/templates/{id}` | `HTTPException(503, "Database unavailable")` + `HTTPException(404, "Template not found")` | ✅ Ya implementado |
| `POST /agents` | Sin 503 explícito — DB errors capturados por el `with get_tenant_client` | ⚠️ Podría beneficiarse de 503 explícito si el connection pool falla |

---

### 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

#### 4.1 Flujo End-to-End

```
┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────┐
│  CLI     │───▶│  httpx.Client │───▶│  FastAPI  │───▶│ Supabase │
│ (sync)   │    │  (sync HTTP)  │    │  (async)  │    │          │
└──────────┘    └──────────────┘    └──────────┘    └──────────┘
     │                                       │
     │  Direct DB access (crew.py,           │
     │  bundle_export.py, export.py,         │
     │  templates_seed.py, tools_list.py)    │
     └───────────────────────────────────────┘
                 BYPASS — sin API
```

**Problema estructural:** 5 de 8 comandos CLI van directo a DB sin pasar por la API. Esto:
- Invalida el dogfooding (no se prueban los endpoints reales)
- Permite que CLI y API diverjan en serialización
- Obliga a duplicar lógica (ej: `_fetch_mcp_tools`)

#### 4.2 Coherencia MVP

- **ID-015:** Hace que el tipo sea honesto con la realidad. Mejora la confiabilidad del contrato.
- **ID-016:** Alinea documentación con código. Previene confusiones en futuros desarrolladores.
- **ID-003/004:** Elimina warnings de event loop. Mejora DX en testing.
- **ID-010:** Ya cubierto. No requiere acción.
- **ID-011/012:** Elimina problemas de renderizado en terminales legacy. Mejora accesibilidad CLI.
- **ID-033/039:** Unifica el stack de comunicación (todo async). Reduce duplicación de código.
- **ID-047:** Centraliza reglas de negocio. Un solo lugar para cambiar límites.

#### 4.3 DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap doctor backend
- **Qué automatiza:** Diagnostica la salud del backend: verifica que todos los endpoints respondan, 
  detecta discrepancias entre documentación (phase-state.md) y código real (firmas de rutas, 
  modelos Pydantic, constantes de validación), y reporta warnings de event loop en CLI.
- **Tipo:** Comando CLI (Typer) — subcomando de `fap doctor`
- **Cómo se usa:** `uv run fap doctor backend --org-id <uuid>`
- **Impacto para el usuario final:** Elimina la verificación manual de 7 tareas de refactorización 
  en un solo comando de ~5 segundos. Detecta regresiones de tipado, divergencia de contratos, 
  y constantes huérfanas antes de que lleguen a producción.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

```
### Herramienta Propuesta: fap doctor backend (checks específicos)
- **Check 1: Strict Typing Audit** — Verifica que `AgentResponse.created_at` no sea Optional
  y que todas las queries de update/insert incluyan `.select()` para garantizar la columna.
- **Check 2: Doc-Code Sync** — Compara `phase-state.md` tabla de endpoints contra código real
  (extrae decoradores de ruta y dependencias de auth) y reporta discrepancias.
- **Check 3: Event Loop Health** — Detecta `asyncio.new_event_loop()` en código CLI y sugiere migración.
- **Check 4: Constant Provenance** — Rastrea números mágicos hardcodeados (`>= 10`, `> 20`, `> 30`)
  y verifica que exista una constante centralizada equivalente en `bundle_schemas.py`.
- **Check 5: httpx.AsyncClient Coverage** — Reporta archivos CLI que aún usan `httpx.Client` (sync).
- **Check 6: Emoji-Free CLI** — Detecta caracteres Unicode no-ASCII en output strings de CLI.
- **Check 7: typer.Option Style** — Reporta usos de `typer.Option(val, help)` sin keyword argument names.
```

---

### 5️⃣ Criterios de Aceptación

```
✅ [DATA] AgentResponse.created_at es obligatorio (str, no Optional)
✅ [DATA] Las queries update/insert en agents.py retornan created_at (verificado con .select())
✅ [CODE] _fetch_mcp_tools versión sync (CLI) eliminada — CLI usa endpoint HTTP
✅ [CODE] Constantes MIN_GOAL_LENGTH, MIN_BACKSTORY_LENGTH, MAX_FLOWS_PER_BUNDLE, 
         MAX_SKILLS_PER_BUNDLE definidas en bundle_schemas.py e importadas donde se usan
✅ [CODE] templates_seed.py usa typer.Option con keyword arguments explícitos
✅ [CODE] No existen llamadas a asyncio.new_event_loop() en código nuevo/modificado
✅ [BACKEND] Endpoints de templates documentados correctamente en phase-state.md como públicos (sin auth)
✅ [BACKEND] Todos los comandos CLI que consumen API usan httpx.AsyncClient (consistencia con backend)
✅ [FULLSTACK] Flujo CLI → API → DB es consistente: serialización idéntica en ambos lados
✅ [DX] fap doctor backend ejecuta 7 checks y retorna exit code 0 en código saludable
✅ [DX] No hay emojis Unicode en output de CLI — solo Rich markup
```

---

### 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1:** `created_at` obligatorio rompe `create_agent` update path | Alta | `.update().execute()` sin `.select()` puede no retornar `created_at` | Agregar `.select("*")` después del update o hacer query adicional para obtener el registro completo antes de retornar |
| **R2:** Migración a `httpx.AsyncClient` introduce bugs de concurrencia en CLI | Media | Comandos CLI actualmente síncronos; migrar requiere wrapping con `asyncio.run()` y manejar correctamente el event loop | Migrar comando por comando con tests de regresión. Usar `anyio.run()` o `asyncio.run()` como wrapper estándar |
| **R3:** Eliminar `_fetch_mcp_tools` sync podría degradar `fap tools list` si el backend no está corriendo | Baja | CLI actualmente funciona offline (DB directa); al depender de HTTP requiere backend activo | Implementar fallback: si HTTP falla, usar DB directa con advertencia. Documentar como breaking change |
| **R4:** Cambio de `typer.Option` old-style a keyword podría romper CLI si los flags implícitos cambian | Baja | typer infiere `--dry-run` del nombre del parámetro; old-style omite el nombre explícito | Verificar que el nombre inferido coincide con el explícito antes de cambiar. Tests de integración CLI |
| **R5:** Centralizar constantes cambia valores si hay discrepancia entre archivos | Media | `bundle_validate_payload.py` usa `>= 10`; `bundle_manager.py` usa `> 20` y `> 30` — ¿son los valores correctos? | Auditar cada valor contra `get_settings()` y documentar la fuente de verdad para cada límite |
| **R6:** `phase-state.md` desactualizado causa confusión en agentes futuros | Media | Documentación dice `require_org_id` pero código es público | Actualizar phase-state.md inmediatamente después de verificar con código (ID-016). Agregar check D2 a `fap doctor backend` |

---

### 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Implementar `fap doctor backend` | `src/cli/commands/doctor_backend.py` | `def doctor_backend(org_id: str, json_output: bool = False) -> None` | `src/cli/commands/doctor_builder.py :: doctor_builder()` | DX | Media | 2.0h | Ninguna | → verificar: `uv run fap doctor backend --org-id test` ejecuta 7 checks sin errores |
| 1 | Fix `AgentResponse.created_at` a obligatorio | `src/api/routes/agents.py:35` | `created_at: str` (sin Optional) | `src/api/routes/templates.py:28-33 :: TemplateInfo` — campos requeridos | DATA | Baja | 0.5h | Tarea 0 | → verificar: `uv run python -c "from src.api.routes.agents import AgentResponse; print(AgentResponse.model_fields['created_at'].is_required())"` devuelve True |
| 2 | Asegurar `created_at` en respuesta de update | `src/api/routes/agents.py:128-143` | Agregar `.select("*")` después de `.update()` o query adicional | `src/api/routes/agents.py:145-156` — insert path que ya incluye columnas completas | DATA | Media | 0.5h | Tarea 1 | → verificar: test de integración `POST /agents` (update) retorna `created_at` no-nulo |
| 3 | Sincronizar `phase-state.md` con rutas reales | `DEVS/phase-state.md:83-87` | Templates: `auth` columna cambia a "ninguno (público)" | `src/api/routes/templates.py:6-8` — docstring que declara pública | DOC | Baja | 0.25h | Ninguna | → verificar: `grep "require_org_id" DEVS/phase-state.md` no muestra templates |
| 4 | Optimizar `_fetch_mcp_tools` CLI: migrar a HTTP | `src/cli/commands/tools_list.py:103-152` | Eliminar función sync `_fetch_mcp_tools`. Usar `httpx.AsyncClient.get(f"{base_url}/api/tools/available?source=mcp")` | `src/cli/commands/agent_create.py:98-103` — patrón de llamada HTTP con `httpx` | CODE | Media | 1.0h | Tarea 0 | → verificar: `grep "_fetch_mcp_tools" src/cli/` no retorna resultados |
| 5 | Centralizar constantes de validación en bundle_schemas | `src/services/bundle_schemas.py` | `MIN_GOAL_LENGTH: int = 10`, `MIN_BACKSTORY_LENGTH: int = 10`, `MAX_FLOWS_PER_BUNDLE: int = 20`, `MAX_SKILLS_PER_BUNDLE: int = 30` | `src/config.py :: get_settings()` — constantes a nivel módulo | CODE | Baja | 0.5h | Ninguna | → verificar: `uv run python -c "from src.services.bundle_schemas import MIN_GOAL_LENGTH; assert MIN_GOAL_LENGTH == 10"` |
| 6 | Refactorizar `bundle_validate_payload.py` para usar constantes | `src/cli/commands/bundle_validate_payload.py:84,88,99` | `from src.services.bundle_schemas import MIN_GOAL_LENGTH, MIN_BACKSTORY_LENGTH, AGENT_COUNT_WARNING_THRESHOLD` | `src/services/bundle_schemas.py` — constantes ya definidas en Tarea 5 | CODE | Baja | 0.25h | Tarea 5 | → verificar: `grep ">= 10" src/cli/commands/bundle_validate_payload.py` no retorna resultados |
| 7 | Refactorizar `bundle_manager.py` para usar constantes | `src/services/bundle_manager.py:192,194` | Usar `MAX_FLOWS_PER_BUNDLE`, `MAX_SKILLS_PER_BUNDLE` de `bundle_schemas` | `src/services/bundle_manager.py:186` — ya usa `settings.max_agents_per_bundle` | CODE | Baja | 0.25h | Tarea 5 | → verificar: `grep "> 20\|> 30" src/services/bundle_manager.py` no retorna resultados |
| 8 | Migrar `agent_run.py` a `httpx.AsyncClient` | `src/cli/commands/agent_run.py:52-175` | `async def run_agent(...)` con `async with httpx.AsyncClient() as client`. Entry point wrapper: `run_agent_sync = lambda **kw: asyncio.run(run_agent(**kw))` | `src/api/routes/tools.py:100` — `await _fetch_mcp_tools(org_id)` | BACKEND | Media | 1.5h | Tarea 4 | → verificar: `uv run fap agent run --role test --message "hi" --org-id $FAP_ORG_ID --timeout 10` funciona sin errores |
| 9 | Migrar `crew.py` save a `httpx.AsyncClient` | `src/cli/commands/crew.py:157-217` | `async def save_crew(...)` + wrapper sync | Tarea 8 — mismo patrón | BACKEND | Media | 0.75h | Tarea 8 | → verificar: `uv run fap crew save --name test --org-id $FAP_ORG_ID` funciona |
| 10 | Migrar `agent_create.py` a `httpx.AsyncClient` | `src/cli/commands/agent_create.py:29-124` | `async def create_agent(...)` + wrapper sync | Tarea 8 — mismo patrón | BACKEND | Media | 0.5h | Tarea 8 | → verificar: `uv run fap agent create --role test --goal "test goal" --backstory "test backstory" --org-id $FAP_ORG_ID --dry-run` funciona |
| 11 | Migrar `templates_use.py` a `httpx.AsyncClient` | `src/cli/commands/templates_use.py:31-194` | `async def use_template(...)` + wrapper sync | Tarea 8 — mismo patrón | BACKEND | Media | 0.5h | Tarea 8 | → verificar: `uv run fap templates use "Research Agent" --org-id $FAP_ORG_ID --dry-run` funciona |
| 12 | Migrar `dogfood_check.py` a `httpx.AsyncClient` | `src/cli/commands/dogfood_check.py:298-455` | `async def dogfood_check(...)` + wrapper sync. Funciones auxiliares `_compare_tools`, `_create_dogfood_agent` async | Tarea 8 — mismo patrón | BACKEND | Alta | 2.0h | Tareas 8-11 | → verificar: `uv run fap dogfood check --org-id $FAP_ORG_ID` ejecuta 7 pasos sin errores |
| 13 | Eliminar emojis Unicode de CLI output | `dogfood_check.py:313,329`, `doctor_builder.py:170,197,200` | Reemplazar 🐶 → `[bold cyan]fap dogfood check[/bold cyan]`, 🩺 → `[bold cyan]FAP Doctor Builder[/bold cyan]` | `src/cli/commands/tools_list.py:62-63` — Rich markup sin emojis | DX | Baja | 0.25h | Ninguna | → verificar: `grep -P '[^\x00-\x7F]' src/cli/commands/dogfood_check.py src/cli/commands/doctor_builder.py` no retorna resultados |
| 14 | Refactorizar `typer.Option` old-style en templates_seed | `src/cli/commands/templates_seed.py:142-147` | `typer.Option(False, "--dry-run", help="Preview without inserting")` | `src/cli/commands/agent_create.py:51` — `typer.Option(False, "--dry-run", ...)` | DX | Baja | 0.25h | Ninguna | → verificar: `uv run fap templates seed --help` muestra `--dry-run` en ayuda |
| 15 | Validación final end-to-end | — | Ejecutar `fap doctor backend` + tests de regresión | — | FULLSTACK | Media | 1.0h | Tareas 1-14 | → verificar: todos los criterios §5 pasan + `uv run pytest tests/ -k "agent or bundle or tools or template"` verde |

**Tiempo total estimado:** 11.5 horas

---

### 🔮 Roadmap (NO implementar ahora)

- **Unificación completa CLI→HTTP:** Los comandos `crew.py export` y `bundle_export.py` aún usan DB directa (porque necesitan datos que el HTTP no expone). Futuro: exponer endpoint `GET /api/agents/export` para que CLI no necesite acceso directo a DB.
- **Estandarización de `typer.Option`:** Adoptar `Annotated` pattern (como en `bundle_validate_payload.py`) en todos los comandos CLI para consistencia con estándares modernos de Typer.
- **`fap doctor backend` → CI/CD:** Integrar el comando en el pipeline de CI para detectar regresiones de tipado y divergencia de contratos automáticamente.
- **Eliminación total de `asyncio.new_event_loop()`:** Tras migración completa a `httpx.AsyncClient`, agregar lint rule (ruff) que prohíba `new_event_loop()` en código de producción.
- **Internacionalización de CLI:** Los emojis son solo la punta del iceberg. Preparar el CLI para i18n usando gettext o similar, eliminando strings hardcodeados en español/inglés mezclados.

---

*Análisis completado. 18 elementos verificados contra código fuente. 10 discrepancias detectadas. 7 tareas de refactorización + 1 herramienta DX propuesta. Listo para implementación.*
