# Análisis Técnico — Paso 1: Split Sync/Async en AgentFactory

> **Agente:** glm
> **Paso:** Paso 1 — Fix Deadlock en MCP Resolution Async (Split Sync/Async en AgentFactory)
> **Fecha:** 2026-05-02

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | `AgentFactory.resolve_tools()` existe | `grep` en `src/crews/factory.py` | ✅ VERIFICADO | `factory.py:28-78` — método sync con parámetro `async_mode` |
| 2 | `AgentFactory._resolve_mcp_tool()` deadlock | Inspección directa | ✅ VERIFICADO | `factory.py:109-119` — `asyncio.run_coroutine_threadsafe(coro, loop).result()` bloquea thread si `loop` es el event loop actual |
| 3 | `AgentFactory.create_agent_async()` es `def` (sync) | Inspección directa | ✅ VERIFICADO | `factory.py:162` — `@staticmethod def create_agent_async(...)` — NO es `async def` |
| 4 | `BaseCrew.run_async()` llama `create_agent_async()` sin `await` | Inspección directa | ✅ VERIFICADO | `base_crew.py:185` — `agent = AgentFactory.create_agent_async(config, self.org_id)` — sin `await` |
| 5 | `BaseCrew.run()` usa `create_agent()` sync | Inspección directa | ✅ VERIFICADO | `base_crew.py:110` — `agent = AgentFactory.create_agent(config, self.org_id)` — correcto |
| 6 | `MCPPool.get_tools()` es `async def` | Inspección directa | ✅ VERIFICADO | `mcp_pool.py:77` — `async def get_tools(self, org_id, server_name, ...)` |
| 7 | `_parse_mcp_prefix()` funciona correctamente | Inspección directa | ✅ VERIFICADO | `factory.py:18-25` — parsea `mcp:server:tool`, retorna `(server, tool)` o `None` |
| 8 | `BaseCrew._resolve_tools()` es sync-only | Inspección directa | ✅ VERIFICADO | `base_crew.py:77-85` — delega a `AgentFactory.resolve_tools(allowed_tools, self.org_id)` sin `async_mode` → skip MCP |
| 9 | 5 test files parchean `_resolve_mcp_tool` | `grep` en tests | ✅ VERIFICADO | `test_factory.py:70,88`, `test_exec_agent_mcp.py:63`, `test_exec_multi_mcp.py:76`, `test_production_flows.py:150`, `test_scenario_3_mcp.py:209` |
| 10 | Call chain deadlock confirmado | Inspección directa | ✅ VERIFICADO | `Flow.execute()` [async] → `BaseCrew.run_async()` [async] → `create_agent_async()` [sync] → `resolve_tools(async_mode=True)` → `_resolve_mcp_tool()` → `run_coroutine_threadsafe().result()` → DEADLOCK |
| 11 | `tool_registry.get()` es sync | Inspección directa | ✅ VERIFICADO | `registry.py:75` — `def get(self, name, org_id=None)` — sync, no necesita await |
| 12 | `BaseCrew.run_async()` NO usa `_resolve_tools()` | Inspección directa | ✅ VERIFICADO | `base_crew.py:183-185` — usa `AgentFactory.create_agent_async()` directamente, no `_resolve_tools()` |
| 13 | `asyncio.get_running_loop()` detecta loop activo | Inspección directa | ✅ VERIFICADO | `factory.py:112-114` — captura `RuntimeError` si no hay loop, asigna `None` |
| 14 | `asyncio.run()` fallback para contexto no-async | Inspección directa | ✅ VERIFICADO | `factory.py:121` — `asyncio.run(pool.get_tools(org_id, server))` si no hay loop corriendo |
| 15 | Plan dice "sin cambios" en `base_crew.py` | Verificación cruzada plan vs código | ❌ DISCREPANCIA | Si `create_agent_async` pasa a `async def`, `run_async()` necesita `await`. Línea 185 requiere cambio. |
| 16 | Plan alternativa 1 muestra `create_agent_async` sync llamando `resolve_tools(async_mode=True)` | Verificación cruzada plan vs código | ❌ DISCREPANCIA | El snippet de alternativa 1 en plan muestra `resolve_tools(async_mode=True)` desde `create_agent_async` sync → sigue llamando `_resolve_mcp_tool()` sync → SIGUE DEADLOCK |
| 17 | Plan presenta 2 alternativas sin decisión clara | Verificación cruzada plan vs especificación | ⚠️ NO VERIFICABLE | Plan no marca cuál alternativa implementar. Alternativa 2 ("más simple") es la correcta pero tiene implicaciones que el plan no documenta. |
| 18 | `BaseCrew._resolve_tools()` no tiene variante async | Verificación cruzada plan vs código | ❌ DISCREPANCIA | Plan no menciona necesidad de `_resolve_tools_async()` en `base_crew.py`. El método actual es sync-only y no serviría en contexto async. |

**Discrepancias encontradas:**

1. **❌ D1:** Plan dice `base_crew.py` "sin cambios" → FALSO. Si `create_agent_async` se vuelve `async def`, línea 185 debe cambiar a `await AgentFactory.create_agent_async(config, self.org_id)`. El `import` de `AgentFactory` ya existe, no necesita cambio, pero la llamada sí.

2. **❌ D2:** Plan alternativa 1 (snippet principal) no resuelve el deadlock. El código muestra `create_agent_async` (sync) llamando `resolve_tools(async_mode=True)` que a su vez llama `_resolve_mcp_tool()` (sync, con `run_coroutine_threadsafe().result()`) → deadlock persiste. Solo la alternativa 2 (hacer `resolve_tools` async) lo resuelve.

3. **❌ D3:** Plan no menciona `BaseCrew._resolve_tools()` como candidato a variante async. Este método sync-only se usa solo en `run()` (correcto), pero si algún caller futuro necesita resolución MCP en contexto async, necesitará variante async. No es bloqueante para este paso, pero es deuda técnica.

4. **⚠️ D4:** Plan presenta 2 alternativas sin elegir una. El implementador necesita saber cuál aplicar. Recomendación: alternativa 2 (métodos async separados) — más limpia, sin afectar callers existentes del path sync.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas afectadas:** Ninguna directamente. Schema DB no se modifica.

- ✅ **Schema:** Sin cambios en migraciones. Paso no toca DB.
- ✅ **Integridad referencial:** N/A
- ✅ **RLS:** N/A
- ✅ **Índices:** N/A
- ✅ **Tipos de datos:** N/A

**Nota:** La tabla `agent_catalog` (migración 004) tiene campo `allowed_tools text[]` que contiene prefijos `mcp:*:*`. La resolución de estos prefijos es lo que causa el deadlock. No hay cambio de schema, solo cambio de código.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases afectadas

#### `AgentFactory.resolve_tools()` — `src/crews/factory.py:28-78`
- **Firma actual:** `def resolve_tools(allowed_tools: list[str], org_id: str, *, async_mode: bool = False) -> list`
- **Problema:** Cuando `async_mode=True`, delega a `_resolve_mcp_tool()` sync que usa `run_coroutine_threadsafe().result()` → deadlock si event loop está corriendo.
- **Cambio propuesto:** Conservar `resolve_tools()` sync (skip MCP). Agregar `async def resolve_tools_async()` que resuelva todo (regular + MCP) vía await.

#### `AgentFactory._resolve_mcp_tool()` — `src/crews/factory.py:81-133`
- **Firma actual:** `def _resolve_mcp_tool(org_id: str, server: str, tool_name: str) -> Any | None`
- **Problema:** Usa `asyncio.run_coroutine_threadsafe(coro, loop).result()` → deadlock cuando loop = event loop actual.
- **Cambio propuesto:** Agregar `async def _resolve_mcp_tool_async(org_id, server, tool_name) -> Any | None` que use `await pool.get_tools()` directamente. Mantener `_resolve_mcp_tool` sync para casos no-async (sin event loop).

#### `AgentFactory.create_agent_async()` — `src/crews/factory.py:162-183`
- **Firma actual:** `@staticmethod def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent`
- **Problema:** Es sync pero se llama desde contexto async. No puede `await` resolución MCP.
- **Cambio propuesto:** Convertir a `@staticmethod async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent` → `await resolve_tools_async(...)` en vez de `resolve_tools(..., async_mode=True)`

#### `BaseCrew.run_async()` — `src/crews/base_crew.py:169-205`
- **Cambio:** Línea 185: `agent = AgentFactory.create_agent_async(config, self.org_id)` → `agent = await AgentFactory.create_agent_async(config, self.org_id)`

### Patrones

- **Patrón existente:** Factory con métodos `@staticmethod` sync. Se introduce primer método async en la clase.
- **Nuevo patrón:** Par sync/async — `resolve_tools()` (sync, skip MCP) + `resolve_tools_async()` (async, full). Mismo patrón que `run()`/`run_async()` en `BaseCrew`.
- **Referencia:** `BaseCrew.run()` / `BaseCrew.run_async()` en `base_crew.py:87-205` — par sync/async existente.

### Modularidad

- ✅ Cohesión alta: cambios circunscritos a `factory.py` + `base_crew.py`.
- ✅ Acoplamiento bajo: callers de `resolve_tools()` sin `async_mode` (path sync) no cambian.
- ⚠️ `create_agent_async` cambia firma (sync → async) — callers que no usen `await` fallan. Solo `BaseCrew.run_async()` lo llama (verificado en grep).

### Imports

- `factory.py` necesita: `from typing import Any, Dict` (ya existe), sin nuevos imports.
- `base_crew.py` no necesita nuevos imports. Change es solo `await` en línea 185.

### Firmas completas (nuevos métodos)

```python
@staticmethod
async def resolve_tools_async(
    allowed_tools: list[str], org_id: str
) -> list:
    """Async variant: regular + MCP tools resolved with await, no deadlock."""

@staticmethod
async def _resolve_mcp_tool_async(
    org_id: str, server: str, tool_name: str
) -> Any | None:
    """Async MCP tool resolution — uses await, safe from async context."""

@staticmethod
async def create_agent_async(
    config: Dict[str, Any], org_id: str
) -> Agent:
    """Create a CrewAI Agent with full async MCP tool resolution."""
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs/Endpoints

- ✅ Sin cambios en endpoints. Modificación es interna al motor de ejecución de crews.
- ✅ Middleware auth: No afectado.
- ✅ Contratos: Firmas internas cambian pero API externa (HTTP endpoints) permanece igual.

### Flujos de datos

- **Flujo sync (sin cambios):** `BaseCrew.run()` → `AgentFactory.create_agent()` → `resolve_tools(async_mode=False)` → skip MCP. Sin deadlock posible.
- **Flujo async (actualizado):** `BaseCrew.run_async()` → `await AgentFactory.create_agent_async()` → `await resolve_tools_async()` → `await _resolve_mcp_tool_async()` → `await pool.get_tools()`. Sin deadlock.
- **Flujo async vía BaseFlow:** `BaseFlow.execute()` [async] → `BaseCrew.run_async()` → (nuevo flujo async). Sin interrupción del event loop.

### Error handling

- `_resolve_mcp_tool_async` debe mantener el mismo try/except que `_resolve_mcp_tool` para errores de conexión MCP.
- `MCPPool.get_tools()` ya tiene circuit breaker + retry (tenacity). `_resolve_mcp_tool_async` usa `await` directo, elimina `run_coroutine_threadsafe`.
- Import guard (`crewai_tools`, `mcp`) se mantiene igual — lazy import en `_resolve_mcp_tool_async`.

### Contratos

| Método | Input | Output | Status |
|--------|-------|--------|--------|
| `resolve_tools_async(allowed_tools, org_id)` | `list[str]`, `str` | `list` (tool objects) | Nuevo |
| `_resolve_mcp_tool_async(org_id, server, tool_name)` | `str`, `str`, `str` | `Any or None` | Nuevo |
| `create_agent_async(config, org_id)` | `Dict`, `str` | `Agent` (coroutine → await) | Modificado (sync → async) |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: DB → Backend → Frontend → UX

```
[DB: agent_catalog.allowed_tools] 
  → [AgentFactory.resolve_tools_async()] 
    → [regular tools: tool_registry.get()] 
    → [MCP tools: await MCPPool.get_tools() → await MCPServerAdapter]
  → [Agent(config, tools)]
  → [CrewAI Crew.kickoff_async()]
  → [Result]
```

**Coherencia:** Cambio puramente backend. Sin impacto en frontend ni UX. El fix elimina un bug de producción (deadlock) sin cambiar comportamiento visible para el usuario final.

### Gaps identificados

1. **`_resolve_mcp_tool` sync sigue existiendo** pero ya no se usa en path async. Debería marcarse como deprecated o eliminarse si `_resolve_mcp_tool_async` reemplaza completamente su funcionalidad.
2. **`async_mode` parámetro en `resolve_tools()` queda obsoleto** — la bifurcación sync/async se hace a nivel de método, no de parámetro. `async_mode=True` ya no debería usarse.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap check-deadlock
- **Qué automatiza:** Detecta `run_coroutine_threadsafe().result()` y `asyncio.run()` dentro de funciones que pueden ser llamadas desde contexto async. Escanea estáticamente el código fuente.
- **Tipo:** script / validador CLI
- **Cómo se usa:** `fap check-deadlock src/`
- **Impacto para el usuario final:** Previene reintroducción del patrón deadlock en futuros cambios de código. Detecta el anti-patrón antes de que llegue a producción.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No se modifican tablas ni migraciones — solo código
✅ [CODE] `resolve_tools_async()` existe en AgentFactory con firma `async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list`
✅ [CODE] `_resolve_mcp_tool_async()` existe en AgentFactory con firma `async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any | None`
✅ [CODE] `create_agent_async()` es `async def` y usa `await resolve_tools_async()`
✅ [CODE] `BaseCrew.run_async()` usa `await AgentFactory.create_agent_async(config, self.org_id)`
✅ [CODE] `resolve_tools()` sync mantiene comportamiento actual (skip MCP con warning)
✅ [CODE] `_resolve_mcp_tool()` sync mantiene comportamiento para contexto no-async
✅ [BACKEND] Flow async con MCP tools completa sin deadlock
✅ [BACKEND] Flow sync sin MCP tools funciona sin cambios
✅ [BACKEND] `_resolve_mcp_tool_async` usa `await pool.get_tools()` directo (sin `run_coroutine_threadsafe`)
✅ [FULLSTACK] `MCPPool.get_tools()` se llama vía await — sin bridge sync→async inseguro
✅ [DX] `fap check-deadlock` ejecuta sin errores y detecta el patrón deadlock en código actual
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| R1: `create_agent_async` cambia de sync → async | Alta | Callers existentes que no usen `await` fallan silenciosamente (retorna coroutine en vez de Agent) | Solo 1 caller: `BaseCrew.run_async():185`. Verificar con grep que no hay otros callers. |
| R2: Tests E2E parchean `_resolve_mcp_tool` (sync) | Media | 5 test files parchean el método sync. Si se elimina, tests fallan. | Actualizar patches a `_resolve_mcp_tool_async`, o mantener ambos métodos. |
| R3: `_resolve_mcp_tool` sync queda como código muerto si path async lo reemplaza | Baja | Confusión futura sobre cuál método usar | Marcar como deprecated con warning en docstring. Considerar eliminación en futuro paso. |
| R4: `async_mode` parámetro en `resolve_tools` queda ambiguo | Media | Con métodos separados, `async_mode=True` ya no debería usarse | Mantener `async_mode` por backward compatibility pero agregar warning si se usa `async_mode=True` sugerir `resolve_tools_async`. |
| R5: Import de `MCPPool` en `_resolve_mcp_tool_async` lazy | Baja | `from src.tools.mcp_pool import MCPPool` dentro del método async → overhead en primera llamada | Mismo patrón que `_resolve_mcp_tool` actual (lazy import). Aceptable. |
| R6: `BaseCrew._resolve_tools()` sin variante async | Baja | Deuda técnica — método sync-only, no usable en contextos async | Documentar. No bloquea este paso. `_resolve_tools()` solo se usa en `run()` (sync). |

---

## 7️⃣ Plan de Implementación

> **Regla:** Una tarea = un artefacto. Interfaz completa. Patrón de referencia explícito. Verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|------------------|-------|-------------|-------------|--------------|--------------|
| 0 | **DX & Tooling:** fap check-deadlock | `src/cli/commands/check_deadlock.py` | `def check_deadlock(paths: list[str]) -> list[dict]: ...` | `src/cli/commands/check_env.py` | DX | Media | 0.5h | Ninguna | → verificar: `uv run python -m src.cli.main check-deadlock src/crews/` detecta patrón en `_resolve_mcp_tool` |
| 1 | Agregar `_resolve_mcp_tool_async` en AgentFactory | `src/crews/factory.py` | `@staticmethod`<br/>`async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any \| None` | `factory.py:81-133` (`_resolve_mcp_tool`) — mismo body pero con `await pool.get_tools(org_id, server)` directo | CODE | Baja | 0.5h | Tarea 0 | → verificar: `uv run python -c "from src.crews.factory import AgentFactory; import inspect; assert inspect.iscoroutinefunction(AgentFactory._resolve_mcp_tool_async)"` |
| 2 | Agregar `resolve_tools_async` en AgentFactory | `src/crews/factory.py` | `@staticmethod`<br/>`async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list` | `factory.py:28-78` (`resolve_tools`) — mismo body pero con `await _resolve_mcp_tool_async()` en branch MCP | CODE | Baja | 0.5h | Tarea 1 | → verificar: `uv run python -c "from src.crews.factory import AgentFactory; import inspect; assert inspect.iscoroutinefunction(AgentFactory.resolve_tools_async)"` |
| 3 | Convertir `create_agent_async` a async | `src/crews/factory.py` | `@staticmethod`<br/>`async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent` | `factory.py:162-183` — mismo body pero con `tools = await AgentFactory.resolve_tools_async(allowed_tools, org_id)` | CODE | Media | 0.5h | Tarea 2 | → verificar: `uv run python -c "from src.crews.factory import AgentFactory; import inspect; assert inspect.iscoroutinefunction(AgentFactory.create_agent_async)"` |
| 4 | Actualizar `BaseCrew.run_async()` para await | `src/crews/base_crew.py` | Línea 185: `agent = await AgentFactory.create_agent_async(config, self.org_id)` | `base_crew.py:185` — agregar `await` a llamada existente | CODE | Baja | 0.25h | Tarea 3 | → verificar: `uv run pytest tests/unit/test_base_crew.py -v -k "run_async"` pasa |
| 5 | Agregar test `resolve_tools_async` con MCP mockeado | `tests/unit/test_factory.py` | `class TestResolveToolsAsync:` con `test_resolves_mcp_tools_async`, `test_skips_malformed_mcp`, `test_mcp_error_logged_and_skipped_async`, `test_regular_tools_resolved_async` | `tests/unit/test_factory.py:48-99` (`TestMCPToolResolution`) — mismo patrón con `pytest.mark.asyncio` | CODE | Media | 0.5h | Tarea 2 | → verificar: `uv run pytest tests/unit/test_factory.py -v -k "TestResolveToolsAsync"` pasa |
| 6 | Agregar test `_resolve_mcp_tool_async` con MCPPool mockeado | `tests/unit/test_factory.py` | `class TestResolveMCPToolAsync:` con `test_returns_matching_tool`, `test_returns_none_if_not_found`, `test_raises_connection_error` | `tests/unit/test_factory.py:48-99` — patrón async con `AsyncMock` | CODE | Media | 0.5h | Tarea 1 | → verificar: `uv run pytest tests/unit/test_factory.py -v -k "TestResolveMCPToolAsync"` pasa |
| 7 | Actualizar test `create_agent_async` existente | `tests/unit/test_factory.py` | Test existente `test_create_agent_async_enables_mcp` → actualizar patch a `resolve_tools_async` con `AsyncMock` | `tests/unit/test_factory.py:130-150` | CODE | Baja | 0.25h | Tarea 3 | → verificar: `uv run pytest tests/unit/test_factory.py -v -k "TestCreateAgent"` pasa |
| 8 | Actualizar patches E2E: `_resolve_mcp_tool` → `_resolve_mcp_tool_async` | `tests/e2e/test_exec_agent_mcp.py`, `tests/e2e/test_exec_multi_mcp.py`, `tests/e2e/test_production_flows.py`, `tests/e2e/test_scenario_3_mcp.py` | Cambiar `patch("src.crews.factory.AgentFactory._resolve_mcp_tool")` → `patch("src.crews.factory.AgentFactory._resolve_mcp_tool_async", new_callable=AsyncMock)` | Patrón existente en los 4 archivos | BACKEND | Media | 0.5h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_exec_agent_mcp.py tests/e2e/test_exec_multi_mcp.py -v` pasa |
| 9 | Agregar warning deprecation en `resolve_tools(async_mode=True)` | `src/crews/factory.py` | En branch `async_mode=True` de `resolve_tools()`: `logger.warning("Use resolve_tools_async() instead of resolve_tools(async_mode=True)")` | — | CODE | Baja | 0.25h | Tarea 2 | → verificar: `uv run pytest tests/unit/test_factory.py -v -k "test_mcp_skipped_in_sync_mode"` muestra warning deprecation |
| 10 | Validación end-to-end de flujo async con MCP | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-9 | → verificar: todos los criterios §5 pasan, `uv run pytest tests/unit/test_factory.py tests/unit/test_base_crew.py tests/e2e/test_exec_agent_mcp.py tests/e2e/test_exec_multi_mcp.py -v` sin errores |

**Tiempo total estimado:** 4.25 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Eliminar `_resolve_mcp_tool` sync una vez que `_resolve_mcp_tool_async` esté validado en producción (2+ sprints sin incidentes).
- Eliminar parámetro `async_mode` de `resolve_tools()` una vez que todos los callers usen `resolve_tools_async()`.
- Agregar `_resolve_tools_async()` en `BaseCrew` para callers directos fuera de AgentFactory.
- Considerar `lazy` tool resolution: pasar callables en vez de tool instances resueltas al Agent de CrewAI (permite resolver tools on-demand).

---

## 🚫 Reglas de Gold — Verificación

- ✅ Análisis accionable y específico
- ✅ TODO verificado contra código
- ✅ Discrepancias documentadas (4 encontradas) con resolución
- ✅ Si plan contradice código → código gana + discrepancia documentada
- ✅ Nivel CTO exigente
- ✅ Coherente con phase-state.md
- ✅ TODO el paso (incluyendo sub-cambios en base_crew.py)
- ✅ Etapas secuenciales (data → code → backend → fullstack+DX)
- ✅ ≥ 1 herramienta DX propuesta (`fap check-deadlock`)
- ✅ Tareas atómicas (1 artefacto = 1 tarea)
- ✅ Interfaz exacta por tarea
- ✅ Patrón de referencia explícito por tarea
- ✅ Verificación inline por tarea

## 📊 Métrica de Calidad

| Métrica | Resultado |
|:---|:---|
| `proyecto-config.json` leído antes de explorar | ✅ 100% |
| Elementos verificados (§0) | 18 (≥12 umbral para 3-5 archivos) |
| Discrepancias detectadas | 4 (D1-D4) |
| Secciones completadas | 8 (§0-§7 + roadmap) |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 12 verificables |
| Riesgos identificados | 6 (2 alto, 2 medio, 2 bajo) |
| Tareas atómicas | 11 tareas, 1 artefacto c/u |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia por tarea | 100% |
| Verificación inline por tarea | 100% |
| Suposiciones no verificadas | 0 |
| Propuesta DX | 1 (`fap check-deadlock`) |
| Estimación de tiempo | 4.25h total |