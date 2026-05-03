# Análisis FINAL — Paso 1: Split Sync/Async en AgentFactory

**Paso:** 1 — Fix Deadlock en MCP Resolution Async
**Fecha:** 2026-05-02
**Fuentes:** `analisis-paso-1-qwen.md`, `analisis-paso1-ds.md`, `analisis-paso1-glm.md`
**Plan origen:** `DEVS/plan.md` — "Fix Deadlock en MCP Resolution Async"

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| qwen | ✅ 18 elementos | 4 | ✅ `fap check-deadlock` | ✅ Archivos + líneas | 4.5 |
| ds | ✅ 16 elementos | 5 | ✅ `fap check-deadlock` | ✅ Archivos + líneas | 4.2 |
| glm | ✅ 18 elementos | 4 | ✅ `fap check-deadlock` | ✅ Archivos + líneas | 4.3 |

### Calidad de aportes por agente

**qwen (Score: 4.5/5):**
- **Fortalezas:** Mejor cobertura de verificación (18 elementos). Identificó discrepancia clave de firma de `MCPPool.get_tools()` (plan dice 2 params, realidad tiene 4). Incluyó sección de testing mínimo con tabla TP-1..TP-N. Estimación más realista (6.25h). Propuesta DX más detallada con flags `--path` y `--check`.
- **Debilidades:** No identificó los 5 archivos de tests que parchean `_resolve_mcp_tool` (solo mencionó 2 e2e). No documentó flujos `multi_crew_flow.py` y `dynamic_flow.py` como activadores del deadlock.

**ds (Score: 4.2/5):**
- **Fortalezas:** Mejor análisis de riesgos — identificó R3 (import guards en versión async) y R4 (circuit breaker abierto). Documentó correctamente que `resolve_tools` NO debe volverse async (breaking change). Estimación más ajustada (2.6h).
- **Debilidades:** No identificó todos los test files afectados por parches (solo 2 e2e + 1 unit). No mencionó flujos externos (`multi_crew_flow.py`, `dynamic_flow.py`, `agents.py` route).

**glm (Score: 4.3/5):**
- **Fortalezas:** Mejor detección de discrepancias del plan — identificó D1 (plan dice base_crew "sin cambios" pero requiere await), D2 (alternativa 1 del plan NO resuelve deadlock), D3 (falta `_resolve_tools_async` en BaseCrew). Encontró 5 archivos de tests con parches (incluyendo `test_production_flows.py` y `test_scenario_3_mcp.py` que otros omitieron).
- **Debilidades:** Estimación de tiempo algo optimista (4.25h). No incluyó tabla de testing mínimo viable. Propuesta DX menos detallada que qwen.

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | Plan dice `base_crew.py` "sin cambios" → FALSO. Línea 185 necesita `await` | glm, qwen, ds | ✅ `base_crew.py:185` | Agregar `await` a llamada `create_agent_async()` |
| 2 | Plan alternativa 1 (snippet principal) NO resuelve deadlock — sigue llamando `_resolve_mcp_tool()` sync | glm, ds | ✅ `factory.py:62-68` | Usar alternativa 2: métodos async separados (`resolve_tools_async`, `_resolve_mcp_tool_async`) |
| 3 | `create_agent_async()` es `def` sync, no `async def` — no puede hacer await | qwen, ds, glm | ✅ `factory.py:161` | Convertir a `async def`, usar `await resolve_tools_async()` |
| 4 | `MCPPool.get_tools()` firma real tiene 4 params, plan asume 2 | qwen | ✅ `mcp_pool.py:77-82` | `_resolve_mcp_tool_async` llama `await pool.get_tools(org_id, server)` — usa defaults para timeout/max_retries |
| 5 | 5 test files parchean `_resolve_mcp_tool` — deben actualizarse | glm | ✅ grep en tests | Actualizar parches a `_resolve_mcp_tool_async` con `AsyncMock` o remover si resolución real funciona |
| 6 | `resolve_tools(async_mode=True)` queda obsoleto con métodos separados | glm, ds | ✅ `factory.py:28-78` | Mantener por backward compat pero agregar warning deprecación. No eliminar en este paso. |
| 7 | Flujos `multi_crew_flow.py`, `dynamic_flow.py`, `agents.py` activan deadlock | ds, glm | ✅ `base_flow.py:135`, `multi_crew_flow.py:118`, `dynamic_flow.py:95` | No requieren cambios — fix en factory/base_crew es suficiente |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo:** Eliminar deadlock en resolución de MCP tools cuando flujos async (`Flow.execute()` → `BaseCrew.run_async()`) intentan resolver tools vía `AgentFactory._resolve_mcp_tool()`. El deadlock ocurre porque `run_coroutine_threadsafe().result()` bloquea el thread mientras el event loop necesita procesar la coroutine scheduleada.

**Correcciones críticas al plan:**
1. Plan dice `base_crew.py` "sin cambios" → requiere `await` en línea 185.
2. Alternativa 1 del plan NO resuelve deadlock → usar métodos async separados.
3. `create_agent_async()` debe convertirse a `async def`.

**Decisión DX:** `fap check-deadlock` — CLI que escanea `run_coroutine_threadsafe().result()` en codebase. Unifica propuesta de los 3 agentes. Previene reintroducción del anti-patrón.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. `Flow.execute()` (async) llama `BaseCrew.run_async()`
2. `run_async()` llama `await AgentFactory.create_agent_async(config, org_id)`
3. `create_agent_async()` llama `await resolve_tools_async(allowed_tools, org_id)`
4. `resolve_tools_async()` itera `allowed_tools`:
   - Si `mcp:server:tool` → `await _resolve_mcp_tool_async(org_id, server, tool_name)`
   - `_resolve_mcp_tool_async()` → `await MCPPool.get().get_tools(org_id, server)` → busca tool por nombre
   - Si tool regular → `tool_registry.get(tool_name, org_id=org_id)` (sync, sin cambio)
5. Tools resueltos → `Agent(tools=...)` → `Crew.kickoff_async()` → resultado

### Edge Cases MVP

- **MCP tool no encontrado en servidor:** `_resolve_mcp_tool_async` retorna `None`, log warning, continúa
- **Circuit breaker abierto en MCPPool:** `MCPConnectionError` capturado, log error, tool skipped
- **Prefijo MCP malformado (`mcp:`):** Parseo falla, log warning, tool skipped
- **Dependencias opcionales no instaladas (crewai-tools, mcp):** `ImportError` con mensaje instalador
- **Flow sync con MCP tools:** `resolve_tools()` sync skipea MCP con warning — comportamiento actual preservado
- **`async_mode=True` legacy:** Warning deprecación sugiere usar `resolve_tools_async()`

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. `src/crews/factory.py` — Crear `_resolve_mcp_tool_async()`

- **Tipo:** Creación
- **Descripción:** Método async que resuelve un MCP tool individual usando `await` directo sobre `MCPPool.get_tools()`. Sin `run_coroutine_threadsafe().result()`.
- **Interfaz:**
  ```python
  @staticmethod
  async def _resolve_mcp_tool_async(
      org_id: str, server: str, tool_name: str
  ) -> Any | None:
  ```
- **Patrones a seguir:** `src/tools/mcp_pool.py:77-191` — await directo. Mismo import guard lazy que `_resolve_mcp_tool` actual (factory.py:88-104).
- **Error handling:** Captura `MCPConnectionError`, `Exception` → log + retorna `None`.

#### 2. `src/crews/factory.py` — Crear `resolve_tools_async()`

- **Tipo:** Creación
- **Descripción:** Método async que resuelve lista completa de tools. MCP vía `await _resolve_mcp_tool_async()`, regulares vía `tool_registry.get()` (sync).
- **Interfaz:**
  ```python
  @staticmethod
  async def resolve_tools_async(
      allowed_tools: list[str], org_id: str
  ) -> list:
  ```
- **Patrones a seguir:** `src/crews/factory.py:28-78` (`resolve_tools`) — misma lógica iterativa, branch MCP usa await.

#### 3. `src/crews/factory.py` — Modificar `create_agent_async()`

- **Tipo:** Modificación (sync → async)
- **Descripción:** Convertir de `def` a `async def`. Tool resolution cambia de `resolve_tools(async_mode=True)` a `await resolve_tools_async()`.
- **Interfaz:**
  ```python
  @staticmethod
  async def create_agent_async(
      config: Dict[str, Any], org_id: str
  ) -> Agent:
  ```
- **Patrones a seguir:** `src/crews/factory.py:135-159` (`create_agent`) — mismo constructor `Agent(...)`.

#### 4. `src/crews/factory.py` — Modificar `resolve_tools()` (sin cambios funcionales)

- **Tipo:** Modificación menor
- **Descripción:** Agregar warning deprecación en branch `async_mode=True`. Path sync intacto.
- **Interfaz:** Sin cambio de firma.

#### 5. `src/crews/base_crew.py:185` — Agregar `await`

- **Tipo:** Modificación (1 línea)
- **Descripción:** `agent = AgentFactory.create_agent_async(config, self.org_id)` → `agent = await AgentFactory.create_agent_async(config, self.org_id)`
- **Patrones a seguir:** `base_crew.py:200` — ya usa `await crew.kickoff_async()`.

#### 6. Tests — Actualizar parches y agregar tests async

- `tests/unit/test_factory.py` — Agregar `TestResolveToolsAsync`, `TestResolveMCPToolAsync`. Actualizar `test_create_agent_async_enables_mcp`.
- `tests/e2e/test_exec_agent_mcp.py` — Remover/actualizar parche `_resolve_mcp_tool`.
- `tests/e2e/test_exec_multi_mcp.py` — Idem.
- `tests/e2e/test_production_flows.py` — Actualizar parche si existe.
- `tests/e2e/test_scenario_3_mcp.py` — Actualizar parche si existe.

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap check-deadlock
- **Qué automatiza:** Detecta llamadas a `asyncio.run_coroutine_threadsafe().result()` en código fuente — patrón de deadlock sync→async. Escanea todos los `.py` files buscando este anti-pattern y reporta archivo/línea/contexto.
- **Tipo:** CLI command (Typer)
- **Ubicación:** `src/cli/commands/check_deadlock.py`
- **Cómo se usa:** `fap check-deadlock --path src/` o `fap check-deadlock --check` (exit 1 si encuentra patrones)
- **Impacto para el usuario final:** Previene reintroducción del bug de deadlock en futuros cambios. CI puede ejecutarlo como gate pre-merge.
- **El implementador DEBE usarla** para verificar que tras implementar las tareas 1-5, el patrón deadlock ya no existe en el path async.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Métodos async separados en vez de hacer `resolve_tools` async:** `resolve_tools()` sync se mantiene intacto. Se crean `resolve_tools_async()` y `_resolve_mcp_tool_async()` como métodos nuevos. Evita breaking change en tests existentes y callers sync.

2. **`create_agent_async()` se vuelve `async def`:** Único caller es `BaseCrew.run_async()` (verificado). Cambio seguro. Requiere agregar `await` en línea 185 de `base_crew.py`.

3. **`async_mode` param se mantiene por backward compat:** No se elimina en este paso. Se agrega warning deprecación si `async_mode=True` para guiar migración a `resolve_tools_async()`.

4. **`_resolve_mcp_tool()` sync se mantiene:** No se elimina. Puede ser útil para contextos no-async (sin event loop running). Se mantiene como fallback.

5. **Plan dice base_crew "sin cambios" → código gana:** Línea 185 de `base_crew.py` requiere `await`. El plan es incorrecto en este punto.

6. **Plan alternativa 1 NO resuelve deadlock → alternativa 2 gana:** El snippet principal del plan muestra `create_agent_async` sync llamando `resolve_tools(async_mode=True)` que sigue usando `_resolve_mcp_tool()` sync → deadlock persiste. Solo métodos async separados lo resuelven.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] `AgentFactory._resolve_mcp_tool_async()` existe con firma `async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any | None`
✅ [CODE] `AgentFactory.resolve_tools_async()` existe con firma `async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list`
✅ [CODE] `AgentFactory.create_agent_async()` es `async def` y usa `await resolve_tools_async()`
✅ [CODE] `BaseCrew.run_async()` usa `await AgentFactory.create_agent_async(config, self.org_id)` en línea 185
✅ [CODE] `resolve_tools()` sync mantiene comportamiento actual — MCP skipped con warning
✅ [CODE] `_resolve_mcp_tool_async()` usa `await pool.get_tools()` directo — SIN `run_coroutine_threadsafe().result()`
✅ [BACKEND] Flow async con MCP tools completa sin deadlock
✅ [BACKEND] Flow sync con MCP tools skipea MCP (comportamiento actual preservado)
✅ [FULLSTACK] Tests e2e pasan sin parchear `_resolve_mcp_tool` (o con parche actualizado a `_resolve_mcp_tool_async`)
✅ [FULLSTACK] Tests unitarios de factory pasan (existentes + nuevos async)
✅ [DX] `fap check-deadlock` ejecuta sin errores y detecta patrón `run_coroutine_threadsafe().result()` en código actual
```

**Funcionales:**
- [ ] Flow async con agente que tiene `allowed_tools` conteniendo `mcp:*:*` completa sin colgarse
- [ ] Flow sync con mismo agente skipea MCP tools con warning en log
- [ ] Tools regulares (no-MCP) se resuelven igual en ambos paths

**Técnicos:**
- [ ] 0 llamadas a `run_coroutine_threadsafe().result()` en path async
- [ ] `inspect.iscoroutinefunction(AgentFactory.create_agent_async)` retorna `True`
- [ ] `inspect.iscoroutinefunction(AgentFactory.resolve_tools_async)` retorna `True`
- [ ] `inspect.iscoroutinefunction(AgentFactory._resolve_mcp_tool_async)` retorna `True`

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap check-deadlock` — CLI que escanea anti-pattern `run_coroutine_threadsafe().result()` | Media | 1h | Ninguna |
| 1 | Crear `_resolve_mcp_tool_async()` en `factory.py` — async, await directo sobre `MCPPool.get_tools()` | Baja | 0.5h | Tarea 0 |
| 2 | Crear `resolve_tools_async()` en `factory.py` — async, itera tools, MCP usa `await _resolve_mcp_tool_async()` | Baja | 0.5h | Tarea 1 |
| 3 | Convertir `create_agent_async()` a `async def` — usa `await resolve_tools_async()` | Media | 0.5h | Tarea 2 |
| 4 | Agregar `await` en `BaseCrew.run_async()` línea 185 | Baja | 0.25h | Tarea 3 |
| 5 | Agregar warning deprecación en `resolve_tools(async_mode=True)` | Baja | 0.25h | Tarea 2 |
| 6 | Agregar tests unitarios `TestResolveToolsAsync` + `TestResolveMCPToolAsync` | Media | 0.5h | Tareas 1-2 |
| 7 | Actualizar test `test_create_agent_async_enables_mcp` a async | Baja | 0.25h | Tarea 3 |
| 8 | Actualizar parches E2E (`test_exec_agent_mcp.py`, `test_exec_multi_mcp.py`, `test_production_flows.py`, `test_scenario_3_mcp.py`) | Media | 0.5h | Tareas 1-4 |
| 9 | Validación end-to-end — ejecutar suite completa de tests afectados | Baja | 0.5h | Tareas 1-8 |
| **TOTAL** | | | **4.75h** | |

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Callers de `create_agent_async` sin await fallan silenciosamente | Alta | Cambio sync→async — retorna coroutine si no se hace await | Grep exhaustivo de `create_agent_async` en `src/`. Solo 1 caller confirmado (`base_crew.py:185`). |
| Tests E2E rompen por parches obsoletos | Media | 5 archivos parchean `_resolve_mcp_tool` sync | Actualizar parches a `_resolve_mcp_tool_async` con `AsyncMock`. Ejecutar tests tras cada cambio. |
| `_resolve_mcp_tool_async` no replica import guards de versión sync | Media | `crewai-tools` y `mcp` son opcionales | Incluir mismo bloque `importlib.util.find_spec` en `_resolve_mcp_tool_async`. |
| Circuit breaker abierto en MCPPool durante resolución async | Media | `get_tools()` lanza `MCPConnectionError` | Capturar excepción, log error, retornar `None` — mismo comportamiento que sync. |
| `async_mode=True` legacy usado por caller externo | Baja | Param obsoleto pero no eliminado | Warning deprecación guía migración. No eliminar en este paso. |
| Regresión en path sync | Baja | Modificar `resolve_tools` podría romper path sync | Path sync intacto — solo agregar warning en branch `async_mode=True`. Tests existentes verifican. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | `resolve_tools_async` resuelve tools regulares | `["db_read"]`, org_id | Lista con 1 tool object |
| TP-2 | `resolve_tools_async` resuelve MCP tools async | `["mcp:fs:list_files"]`, org_id, MCPPool mockeado | Lista con 1 MCP tool object, sin deadlock |
| TP-3 | `_resolve_mcp_tool_async` retorna tool matching | org_id, server, tool_name, pool mockeado con tool | Tool object con `name == tool_name` |
| TP-4 | `_resolve_mcp_tool_async` retorna None si no encuentra | org_id, server, tool_name inexistente | `None` + warning log |
| TP-5 | `create_agent_async` retorna Agent con tools | config con `allowed_tools`, org_id | `Agent` instance con tools resueltos |
| TP-6 | `resolve_tools` sync skipea MCP | `["mcp:fs:list"]`, org_id, async_mode=False | Lista vacía + warning log |
| TP-7 | Flow async completo sin deadlock | Flow con MCP tools, mocks | `FlowStatus.COMPLETED` |
| TP-8 | `fap check-deadlock` detecta patrón actual | `--path src/crews/` | Exit 1, reporta `factory.py:117-119` |
| TP-9 | `fap check-deadlock` pasa tras fix | `--path src/crews/` tras implementar | Exit 0, 0 patrones encontrados |

**Comandos para ejecutar tests:**
- Unitarios: `uv run pytest tests/unit/test_factory.py -v --timeout=60`
- E2E: `uv run pytest tests/e2e/test_exec_agent_mcp.py tests/e2e/test_exec_multi_mcp.py -v --timeout=120`
- DX tool: `uv run python -m src.cli.main check-deadlock --path src/crews/`
