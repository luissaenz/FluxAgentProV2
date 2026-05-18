# Analisis Unificado — Paso 13: Robustez y Refactorizacion del Backend (DX)

**Fase:** guiAgentGenerator
**Paso:** 13 — Robustez y Refactorizacion del Backend (DX)
**Fecha:** 2026-05-18
**Estado:** Analisis UNIFICADO — listo para implementacion
**Fuente:** 6 analisis de agentes (dsp, g3f, lgn, mm, qwen, step)

---

### 0 Evaluacion de Analisis y Verificaciones

#### Tabla de Evaluacion de Agentes

| Agente | Verifico codigo | Discrepancias detectadas | Propuesta DX | Evidencia solida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| dsp | 18 | 10 | `fap doctor backend` (7 checks) | 18 elementos, lineas exactas | 4.7 |
| g3f | 20 | 3 | `fap doctor api` | 20 elementos, rutas correctas | 3.2 |
| lgn | 10 | 4 | `fap backend diagnose` | 10 elementos, basico | 3.0 |
| mm | 8 | 4 | `fap lint-emojis` | 8 elementos, superficial | 2.5 |
| qwen | 30 | 5 | `fap backend-health` | 30 elementos, exhaustivo en cantidad | 3.8 |
| step | 22 | 7 | `fap db-sync check` | 22 elementos, detecta D2 critica | 4.5 |

**Agente destacado:** step — unico en detectar D1+D2 combinados (SELECT sin `created_at`). dsp — mayor profundidad y cobertura de discrepancias (10). qwen — mayor cantidad de verificaciones (30).

#### Discrepancias Criticas Consolidadas

| # | Discrepancia | Detecto | Verificada contra codigo | Resolucion |
|---|---|---|---|---|
| 1 | `AgentResponse.created_at` opcional (`str \| None = None`) mientras DB tiene `NOT NULL DEFAULT now()` | dsp, g3f, lgn, mm, qwen, step | `src/api/routes/agents.py:35` | Cambiar a `created_at: str` (obligatorio) |
| 2 | `list_agents` SELECT excluye `created_at` (linea 77). `create_agent` update path sin `.select("*")` post-update | step UNICAMENTE | `src/api/routes/agents.py:77,128-143` | Agregar `created_at` a SELECT + `.select("*")` tras update **CRITICO: sin esto AgentResponse falla** |
| 3 | `phase-state.md:86-87` documenta templates con `require_org_id` pero codigo real es publico (templates.py:6-7) | dsp, g3f, qwen | `src/api/routes/templates.py:6-7` vs `DEVS/phase-state.md:86-87` | Actualizar phase-state.md: templates son publicos |
| 4 | `_fetch_mcp_tools` en CLI (`tools_list.py:141`) usa `asyncio.new_event_loop()` antipatron | dsp, g3f, lgn, qwen, step | `src/cli/commands/tools_list.py:141-147` | Usar `asyncio.run()` + `return_exceptions=True` |
| 5 | Emojis Unicode en CLI output problemáticos en terminales sin UTF-8 | dsp, lgn, mm, qwen, step | `doctor_builder.py:170,197,200`, `dogfood_check.py:313,329`, `phase_close.py:138-248`, `validate.py:21-66` | Reemplazar por Rich markup (`[green]PASS[/green]`) |
| 6 | `httpx.Client` sync en CLI vs backend async — 10+ instancias en agent_run.py, crew.py, dogfood_check.py, agent_create.py, templates_use.py, login.py, validate.py, publish.py | dsp, g3f, lgn, mm, qwen, step | `agent_run.py:89,131`, `crew.py:178`, `dogfood_check.py:122` + 7 mas | Migrar a `httpx.AsyncClient` con `asyncio.run()` wrapper |
| 7 | Constantes de validacion hardcodeadas: `>= 10` en `bundle_validate_payload.py:84,88`, `bundles.py:229,234` | dsp, g3f, qwen, step | `bundle_validate_payload.py:84,88`, `bundles.py:229,234` | Centralizar en `bundle_schemas.py` |
| 8 | `HTTPException(503)` ausente en endpoints `GET /agents`, `POST /agents`, `GET /agents/{id}/detail` | step UNICAMENTE | `src/api/routes/agents.py:64-98`, `188-309` | Agregar `try/except Exception -> HTTPException(503)` |
| 9 | `typer.Option` old-style sin keyword names en `templates_seed.py:142-147` | dsp UNICAMENTE | `src/cli/commands/templates_seed.py:142-147` | Agregar `--dry-run`, `--reset` flags explicitos |
| 10 | `export_service.py:55` comentario referencia constante `MIN_GOAL_LENGTH` que jamas se definio | dsp UNICAMENTE | `src/services/export_service.py:55` | Definir constante en `bundle_schemas.py` o eliminar comentario |
| 11 | `bundle_manager.py:192,194` hardcodea limites `> 20` (max flows) y `> 30` (max skills) | dsp UNICAMENTE | `src/services/bundle_manager.py:192,194` | Mover a constantes en `bundle_schemas.py` |

---

### 1 Resumen Ejecutivo

Paso 13 aborda ~11 issues tecnicas en backend y CLI de `guiAgentGenerator`. No crea funcionalidad nueva — mejora calidad, manejo de errores, rendimiento y coherencia de contratos.

**Correcciones criticas al plan original:**
- **D1+D2:** Hacer `created_at` requerido SIN asegurar SELECTS en agents.py rompe `AgentResponse`. step descubrio que `list_agents` (linea 77) NO incluye `created_at` en su SELECT. Correccion obligatoria: incluir campo en todos los SELECT y agregar `.select("*")` tras updates.
- **D8:** `HTTPException(503)` falta en 3 endpoints de agents.py (step). El plan solo mencionaba templates. Agents tambien necesita 503 handling.
- **D3:** `phase-state.md` dice templates usan `require_org_id`. Realidad: son publicos. Documentacion desactualizada.

**Herramienta DX seleccionada (fusion):** `fap doctor backend` (base dsp) + `db-sync check` (step). Fusion en `fap doctor backend` con 8 checks totales.

---

### 2 Diseno Funcional Consolidado

#### Happy Path

1. CLI ejecuta `fap doctor backend --org-id <uuid>` — 8 checks pasan
2. `POST /agents` recibe `AgentCreate`, consulta DB, retorna `AgentResponse` con `created_at` obligatorio
3. `GET /agents` lista agentes incluyendo `created_at` en cada item
4. `GET /api/templates` y `GET /api/templates/{id}` retornan datos publicos sin auth, con 503 si DB falla
5. `uv run fap tools list` consulta endpoint HTTP async (no crea event loop nuevo)
6. `uv run fap agent run` usa `httpx.AsyncClient` con polling loop eficiente
7. `bundle_validate_payload.py` importa constantes centralizadas

#### Edge Cases MVP

- **D2 edge:** Update path en `create_agent` (linea 128-143) retorna `AgentResponse` sin `created_at` si falta `.select("*")`
- **D4 edge:** `asyncio.new_event_loop()` en tools_list.py rompe si ya hay loop (pytest-asyncio, Jupyter)
- **D6 edge:** `httpx.Client` recreado cada iteracion de polling (~60 veces) degrada performance
- **D8 edge:** DB caida en `GET /agents` retorna 500 en vez de 503
- **D3 edge:** Documentacion erronea lleva a futuros agentes a agregar auth a templates

---

### 3 Diseno Tecnico Definitivo

#### Componentes y Modificaciones

| # | Ruta real | Tipo de cambio | Descripcion | Interfaz clave | Patron a seguir |
|---|---|---|---|---|---|
| M1 | `src/api/routes/agents.py:35` | Modificacion | `created_at: str` (obligatorio) | `class AgentResponse(BaseModel): ... created_at: str` | `templates.py:33` |
| M2 | `src/api/routes/agents.py:77` | Modificacion | Agregar `"created_at"` al SELECT de list_agents | `.select("id, role, soul_json, allowed_tools, max_iter, created_at")` | `templates.py:61` `.select("*")` |
| M3 | `src/api/routes/agents.py:128-143` | Modificacion | Agregar `.select("*")` tras `.update()` | `db.table("agent_catalog").update({...}).eq("id", existing_id).select("*").execute()` | Misma linea, agregar `.select("*")` |
| M4 | `src/api/routes/agents.py:64-98, 101-163, 188-309` | Modificacion | Envolver queries DB en `try/except -> HTTPException(503)` | 3 bloques try/except en list_agents, create_agent, get_agent_detail | `templates.py:59-67` |
| M5 | `DEVS/phase-state.md:86-87` | Modificacion | Corregir auth de templates a "publico" | Tabla endpoints: templates auth = "ninguno (publico)" | `templates.py:6-7` |
| M6 | `src/cli/commands/tools_list.py:141-147` | Modificacion | Reemplazar `new_event_loop()` por `asyncio.run()` | `results = asyncio.run(asyncio.gather(*[...], return_exceptions=True))` | `tools.py:146` |
| M7 | `src/cli/commands/doctor_builder.py:170,197,200` | Modificacion | Remover emojis, usar Rich markup | `console.print("[bold cyan]FAP Doctor Builder[/bold cyan]")` | `run.py` sin emoji |
| M8 | `src/cli/commands/dogfood_check.py:313,329` | Modificacion | Remover emojis, usar Rich markup | `console.print("[bold cyan]fap dogfood check[/bold cyan]")` | `run.py` sin emoji |
| M9 | `src/cli/commands/agent_run.py:86-174` | Refactor | Migrar a `httpx.AsyncClient` + `asyncio.run()` wrapper | `async def run_agent_async(...) -> None` | `run.py:213-238` |
| M10 | `src/cli/commands/crew.py:157-217` | Refactor | Migrar save_crew a async | `async def _save_crew_async(...) -> None` | `run.py:220` |
| M11 | `src/cli/commands/templates_seed.py:142-147` | Modificacion | Agregar keyword names a typer.Option | `typer.Option(False, "--dry-run", help="...")` | `agent_create.py:51` |
| C1 | `src/services/bundle_schemas.py` (final) | Creacion (constantes) | Agregar constantes de validacion | `MIN_GOAL_LENGTH: int = 10`, `MIN_BACKSTORY_LENGTH: int = 10`, `MAX_FLOWS_PER_BUNDLE: int = 20`, `MAX_SKILLS_PER_BUNDLE: int = 30` | `config.py :: get_settings()` |
| C2 | `src/cli/commands/doctor_backend.py` | Creacion (DX) | Herramienta de diagnostico con 8 checks | `def doctor_backend(org_id: str, json_output: bool = False) -> None` | `doctor_builder.py :: doctor_builder()` |

#### DX & Tooling — Tarea 0

```
### Herramienta: fap doctor backend (fusionado: dsp + step)
- **Que automatiza:** 8 checks de salud del backend: Strict Typing Audit, Doc-Code Sync,
  Event Loop Health, Constant Provenance, AsyncClient Coverage, Emoji-Free CLI,
  typer.Option Style, DB-Sync Check (schema DB vs modelos Pydantic).
- **Tipo:** Comando CLI (Typer) — subcomando de `fap doctor`
- **Ubicacion:** src/cli/commands/doctor_backend.py
- **Como se usa:** `uv run fap doctor backend --org-id <uuid>`
- **Impacto para el usuario final:** Elimina verificacion manual de 11 tareas de refactorizacion
  en un solo comando de ~5 segundos. Detecta regresiones de tipado, divergencia de contratos,
  constantes huerfanas, y desalineacion DB/backend antes de produccion.
- **El implementador DEBE usarla** para completar las tareas 1..14 del paso.
```

---

### 4 Decisiones Tecnologicas

1. **`AgentResponse.created_at` obligatorio:** Alinea Pydantic con DB (NOT NULL). Backward-compatible porque Supabase siempre retorna `created_at` via `DEFAULT now()`.
2. **`httpx.AsyncClient` en CLI:** Consistencia con backend async. Usar `asyncio.run()` como wrapper sync para compatibilidad con entrypoints Typer.
3. **Constantes en `bundle_schemas.py`:** Unico lugar de verdad. Schemas Pydantic ya definen limites via Field; agregar constantes modulares reutilizables desde CLI.
4. **Correcciones al plan:**
   - El plan no detecto que `list_agents` SELECT excluye `created_at` (step D2). Se implementa: agregar campo a SELECT + `.select("*")` tras update.
   - El plan no menciono `HTTPException(503)` en agents endpoints (step D8). Se implementa: 3 bloques try/except en agents.py.
   - `phase-state.md` documenta templates con `require_org_id` incorrectamente. Se corrige a publico.

---

### 5 Criterios de Aceptacion MVP

```
[DATA] AgentResponse.created_at es obligatorio (str, no Optional)
[DATA] Las queries SELECT en agents.py incluyen created_at
[DATA] Las queries UPDATE en agents.py usan `.select("*")` para garantizar created_at
[CODE] _fetch_mcp_tools sync (CLI) eliminada o migrada a asyncio.run()
[CODE] Constantes MIN_GOAL_LENGTH, MIN_BACKSTORY_LENGTH, MAX_FLOWS_PER_BUNDLE,
       MAX_SKILLS_PER_BUNDLE definidas en bundle_schemas.py e importadas donde se usan
[CODE] bundle_validate_payload.py y bundles.py importan constantes (no hardcode)
[CODE] templates_seed.py usa typer.Option con keyword arguments explicitos
[CODE] No existen llamadas a asyncio.new_event_loop() en codigo nuevo/modificado
[BACKEND] Endpoints de templates documentados en phase-state.md como publicos (sin auth)
[BACKEND] GET /agents, POST /agents, GET /agents/{id}/detail retornan 503 si DB falla
[BACKEND] Todos los comandos CLI que consumen API usan httpx.AsyncClient
[FULLSTACK] Flujo CLI -> API -> DB es consistente: serializacion identica
[DX] fap doctor backend ejecuta 8 checks y retorna exit code 0 en codigo saludable
[DX] No hay emojis Unicode en output de CLI — solo Rich markup
```

**Funcionales:**
- [ ] `POST /agents` retorna 201 con `created_at` no-nulo
- [ ] `GET /agents` lista agentes con `created_at` en cada item
- [ ] `GET /api/templates` funciona sin auth header
- [ ] `fap doctor backend` ejecuta y reporta estado
- [ ] `fap tools list` funciona sin warning de event loop
- [ ] `fap agent run --role test --message "hi"` funciona sin errores

**Tecnicos:**
- [ ] `ruff check src/` pasa sin errores
- [ ] `pytest tests/unit/ -k "agent or tools or template"` pasa
- [ ] `grep "new_event_loop" src/cli/` no retorna resultados
- [ ] `grep -P '[^\x00-\x7F]' src/cli/commands/doctor_builder.py src/cli/commands/dogfood_check.py` no retorna emojis

---

### 6 Plan de Implementacion

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap doctor backend` (8 checks) | Media | 2.0h | Ninguna |
| 1 | `AgentResponse.created_at` obligatorio (agents.py:35) | Baja | 0.25h | Tarea 0 |
| 2 | Agregar `created_at` a SELECT de list_agents (agents.py:77) | Baja | 0.25h | Tarea 1 |
| 3 | Agregar `.select("*")` tras update en create_agent (agents.py:128-143) | Baja | 0.25h | Tarea 2 |
| 4 | Agregar `try/except -> 503` en list_agents (agents.py:64-98) | Baja | 0.25h | Tarea 3 |
| 5 | Agregar `try/except -> 503` en create_agent (agents.py:101-163) | Baja | 0.25h | Tarea 4 |
| 6 | Agregar `try/except -> 503` en get_agent_detail (agents.py:188-309) | Baja | 0.50h | Tareas 4,5 |
| 7 | Sincronizar `phase-state.md:86-87` templates como publicos | Baja | 0.25h | Ninguna |
| 8 | Refactor `_fetch_mcp_tools` en tools_list.py:141-147 | Media | 0.75h | Tarea 0 |
| 9 | Remover emojis de doctor_builder.py y dogfood_check.py | Baja | 0.50h | Tarea 8 |
| 10 | Migrar `agent_run.py` a `httpx.AsyncClient` | Alta | 2.0h | Tareas 0, 9 |
| 11 | Migrar `crew.py save_crew` a `httpx.AsyncClient` | Media | 1.0h | Tarea 10 |
| 12 | Centralizar constantes en `bundle_schemas.py` | Baja | 0.50h | Ninguna |
| 13 | Refactor `bundle_validate_payload.py` y `bundles.py` a constantes | Baja | 0.50h | Tarea 12 |
| 14 | Refactor `templates_seed.py` typer.Option keyword names | Baja | 0.25h | Ninguna |
| 15 | Validacion final: `fap doctor backend` + tests | Media | 1.0h | Tareas 1-14 |
| | **TOTAL** | | **10.0h** | |

---

### 7 Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigacion |
|---|---|---|---|
| D2: `created_at` obligatorio rompe serializacion si SELECT no lo incluye | Alta | `list_agents` (linea 77) NO selecciona `created_at`. `update().execute()` sin `.select("*")` no lo retorna | Agregar `created_at` a SELECT + `.select("*")` tras update. Verificar con tests de integracion |
| R1: `asyncio.run()` anidado desde event loop activo | Alta | Si CLI se ejecuta desde contexto async (pytest, Jupyter), `asyncio.run()` lanza RuntimeError | Usar patron `if loop.is_running(): loop.create_task(coro)` o `nest_asyncio.apply()` |
| R2: Migracion async en CLI rompe entrypoints Typer | Media | Typer espera funciones sync. Funcion async necesita wrapper sync | Usar patron existente: funcion async interna + `asyncio.run()` wrapper sync |
| R3: Emojis no detectados en archivos fuera del scope | Baja | qwen detecto emojis en `phase_close.py`, `validate.py` — fuera del paso 13 | Incluir en fap doctor backend check 5 (Emoji-Free CLI) que scanea todo `src/cli/` |
| R4: Constantes desincronizadas entre Field y constantes | Media | Si Field cambia en bundle_schemas pero constante no se actualiza | Las constantes DEBEN ser la fuente de verdad. Fields deben importar desde constantes, no al reves |
| R5: `return_exceptions=True` enmascara errores MCP | Media | Si se activa sin filtrar, excepciones se convierten en entradas de lista | Filtrar: `if isinstance(r, Exception): logger.warning(...) else: tools.extend(r)` |
| R6: `phase-state.md` desactualizado causa confusion en agentes futuros | Media | Sin actualizar, proximos pasos agregaran auth incorrecta a templates | Actualizar inmediatamente (Tarea 7). Agregar check a fap doctor backend |

---

### 8 Testing Minimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | `AgentResponse.created_at` requerido | `AgentResponse(id="x", org_id="y", role="z", soul_json={}, max_iter=5)` | Error: field required (created_at faltante) |
| TP-2 | `GET /agents` con DB caida | Mock `get_tenant_client` lanza excepcion | `HTTPException(503, "Database unavailable")` |
| TP-3 | `list_agents` SELECT incluye created_at | Inspeccionar query string de agents.py:77 | `"created_at"` presente en `.select()` |
| TP-4 | `fap tools list` sin warning event loop | Ejecutar comando en entorno con loop activo (pytest-asyncio) | No `RuntimeError: This event loop is already running` |
| TP-5 | Emojis en CLI output | `grep -rn '[^\x00-\x7F]' src/cli/commands/doctor_builder.py src/cli/commands/dogfood_check.py` | 0 resultados |
| TP-6 | Constantes centralizadas importables | `from src.services.bundle_schemas import MIN_GOAL_LENGTH, MIN_BACKSTORY_LENGTH` | Importacion exitosa, valores 10 |

Comando para ejecutar tests: `uv run pytest tests/unit/ -v --timeout=60`
Comando lint: `uv run ruff check src/ tests/`
