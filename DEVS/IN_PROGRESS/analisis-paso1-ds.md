# Análisis Técnico — Paso 1: Split Sync/Async en AgentFactory

**Agente:** ds
**Paso:** 1 — Split Sync/Async en AgentFactory
**Fecha:** 2026-05-02
**Plan:** plan.md — Paso 1 (único paso)
**Fuente de verdad:** `proyecto-config.json` + código fuente verificado

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentFactory.resolve_tools(..., async_mode)` existe | grep en `src/crews/factory.py:28` | ✅ | Línea 28-78 — ya tiene parámetro `async_mode: bool = False` |
| 2 | `AgentFactory._resolve_mcp_tool()` existe | grep en `src/crews/factory.py:80` | ✅ | Línea 80-133 — implementación actual con `run_coroutine_threadsafe().result()` |
| 3 | `AgentFactory._parse_mcp_prefix()` existe | grep en `src/crews/factory.py:18` | ✅ | Línea 17-25 — parsea `mcp:server:tool` |
| 4 | `AgentFactory.create_agent_async()` existe | grep en `src/crews/factory.py:161` | ✅ | Línea 161-183 — método **sync** que llama `resolve_tools(async_mode=True)` |
| 5 | `create_agent_async()` es `def` no `async def` | src/crews/factory.py:161 | ✅ VERIFICADO | `def create_agent_async(...)` — NO es async. No puede hacer await. |
| 6 | `_resolve_mcp_tool()` usa `run_coroutine_threadsafe().result()` | src/crews/factory.py:117-119 | ✅ | Líneas 117-119 — deadlock cuando loop actual = loop destino |
| 7 | `_resolve_mcp_tool()` fallback `asyncio.run()` existe | src/crews/factory.py:121 | ✅ | Línea 121 — seguro solo si NO hay loop running |
| 8 | `BaseCrew.run_async()` llama `create_agent_async()` | src/crews/base_crew.py:185 | ✅ | Línea 185: `agent = AgentFactory.create_agent_async(config, self.org_id)` — sin await |
| 9 | `BaseCrew.run()` llama `create_agent()` | src/crews/base_crew.py:110 | ✅ | Línea 110: `agent = AgentFactory.create_agent(config, self.org_id)` |
| 10 | `MCPPool.get_tools()` es async | src/tools/mcp_pool.py:77 | ✅ | Línea 77: `async def get_tools(...)` |
| 11 | `MCPPool.get()` singleton existe | src/tools/mcp_pool.py:51 | ✅ | Línea 51-56 |
| 12 | `resolve_tools` sync skipea MCP con warning | src/crews/factory.py:53-58 | ✅ | Líneas 53-58: log warning + continue |
| 13 | `tool_registry.get()` firma | src/tools/registry.py:75 | ✅ | `def get(self, name: str, org_id: str | None = None) -> Type` |
| 14 | Flow `execute()` → `_run_crew()` → `crew.run_async()` chain | base_flow.py:135 → multi_crew_flow.py:118 / dynamic_flow.py:95 | ✅ | Calls `await crew.run_async()` → `create_agent_async()` → `resolve_tools(async_mode=True)` → `_resolve_mcp_tool()` → **deadlock** |
| 15 | `create_agent_async()` retorna `Agent` sincrónicamente | src/crews/factory.py:174-183 | ✅ | Contructor `Agent(...)` es sync |
| 16 | Tests `test_factory.py` usan `patch.object(AgentFactory, "resolve_tools")` | tests/unit/test_factory.py:143-144 | ✅ | Mockean `resolve_tools`, nunca ejercitan `_resolve_mcp_tool` real |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | `create_agent_async()` es `def` no `async def`. Plan asume que ya maneja async pero el deadlock está en que NO PUEDE hacer await. | Hacer `create_agent_async()` → `async def`. Cambiar caller `BaseCrew.run_async()` a `await create_agent_async()`. |
| D2 | `resolve_tools()` ya tiene `async_mode` param. Plan propone crear `resolve_tools_async()` como método separado (solución principal) y luego ofrece "alternativa más simple" de hacer `resolve_tools` async cuando `async_mode=True`. Código actual + tests ya usan `async_mode` param. | Seguir alternativa simple (hacer `resolve_tools` async cuando `async_mode=True`) — menos cambios, compatibilidad con tests existentes. |
| D3 | Plan no menciona que `create_agent_async()` retorna un `Agent` sincrónicamente. Hacerla async requiere solo cambiar tool resolution, no la construcción de Agent. | Tool resolution async, Agent constructor sync. |
| D4 | Plan no registra que `multi_crew_flow.py` y `dynamic_flow.py` son los flujos que activan el deadlock vía `crew.run_async()` → `create_agent_async()`. | Documentar flujos afectados. Sin cambios en estos archivos — el fix en factory/base_crew es suficiente. |
| D5 | Tests existentes de factory mockean `resolve_tools` — nunca detectaron el deadlock porque evitan `_resolve_mcp_tool` real. | Tests nuevos deben probar `_resolve_mcp_tool_async()` real con pool mockeado. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Sin afectación a schema de DB.** Este paso es puramente de código (refactor sync/async en AgentFactory).

- ✅ Ninguna tabla nueva, columna, migración o RLS policy
- ✅ Sin cambios en `supabase/migrations/`
- ✅ Sin impacto en datos existentes
- ✅ Sin índices, constraints, o integridad referencial

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones tocadas (modificar)

#### `AgentFactory.resolve_tools()` → hacer `async def` cuando `async_mode=True`

**Estado actual** (factory.py:28):
```python
@staticmethod
def resolve_tools(
    allowed_tools: list[str], org_id: str, *, async_mode: bool = False
) -> list:
```

**Propuesto:**
```python
@staticmethod
async def resolve_tools(
    allowed_tools: list[str], org_id: str, *, async_mode: bool = False
) -> list:
```
- `async_mode=False` → mismo comportamiento sync actual (MCP skipped)
- `async_mode=True` → `await _resolve_mcp_tool_async()` en vez de `_resolve_mcp_tool()`
- **Regresión:** Tests existentes que llaman `resolve_tools()` sync siguen funcionando — `async def` puede llamarse sync? NO. `async def` siempre retorna coroutine. **Esto es un BREAKING CHANGE.**
- **Corrección:** No hacer `resolve_tools` async. Mejor crear `resolve_tools_async()` como método separado.

✅ **Decisión:** Crear `resolve_tools_async()` como método async separado. Dejar `resolve_tools()` sync intacto. Esto evita romper tests existentes y mantiene compatibilidad.

#### `AgentFactory.create_agent_async()` → hacer `async def`

**Estado actual** (factory.py:161):
```python
@staticmethod
def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent:
    tools = AgentFactory.resolve_tools(allowed_tools, org_id, async_mode=True)
    return Agent(...)
```

**Propuesto:**
```python
@staticmethod
async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent:
    # Tool resolution async (nuevo método async)
    from .factory import AgentFactory
    tools = await AgentFactory.resolve_tools_async(allowed_tools, org_id)
    # Agent constructor sigue siendo sync
    return Agent(...)
```

#### `AgentFactory._resolve_mcp_tool()` → método actual se mantiene para compatibilidad sync

#### `AgentFactory._resolve_mcp_tool_async()` → NUEVO método async

```python
@staticmethod
async def _resolve_mcp_tool_async(
    org_id: str, server: str, tool_name: str
) -> Any | None:
    pool = MCPPool.get()
    all_tools = await pool.get_tools(org_id, server)
    for tool in all_tools:
        if hasattr(tool, "name") and tool.name == tool_name:
            return tool
    return None
```

Sin `run_coroutine_threadsafe().result()` → sin deadlock.

#### `BaseCrew.run_async()` → añadir `await` en `create_agent_async()`

**Estado actual** (base_crew.py:185):
```python
agent = AgentFactory.create_agent_async(config, self.org_id)
```

**Propuesto:**
```python
agent = await AgentFactory.create_agent_async(config, self.org_id)
```

### Importaciones exactas

| Archivo | Import actual | Cambio |
|---|---|---|
| `factory.py` | `from src.tools.mcp_pool import MCPPool` (dentro de `_resolve_mcp_tool`) | Se mantiene — también usado en `_resolve_mcp_tool_async` |
| `factory.py` | `import asyncio` (implicit, usado en `_resolve_mcp_tool`) | Se mantiene — `_resolve_mcp_tool` sync sigue usándolo |
| `factory.py` | `from src.tools.registry import tool_registry` (top-level) | Sin cambios |
| `base_crew.py` | `from .factory import AgentFactory` (dentro de métodos) | Sin cambios |

### Patrones existentes a seguir

- **Patrón async en MCPPool:** `MCPPool.get_tools()` es async (mcp_pool.py:77). `_resolve_mcp_tool_async` debe usar `await pool.get_tools()`, no `run_coroutine_threadsafe()`.
- **Patrón de registro:** `tool_registry.get()` es sync (registry.py:75). Tools regulares no necesitan async.

### Modularidad

- ✅ Cohesión alta: toda la lógica de resolución de tools está en `AgentFactory`
- ✅ Bajo acoplamiento: `AgentFactory` depende de `MCPPool` y `tool_registry` — ya existente
- ✅ Reutilización: `resolve_tools_async()` llama a `_resolve_mcp_tool_async()` y `tool_registry.get()` — reusa lógica parseo y registro

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Sin endpoints nuevos.** Este paso no toca APIs HTTP ni middleware.

| Elemento | Estado |
|---|---|
| Endpoints nuevos | 0 |
| Rutas modificadas | 0 |
| Middleware afectado | 0 |
| Contratos HTTP | Sin cambios |
| Error handling HTTP | Sin cambios |

**Impacto en flujos backend:**

| Flow | Archivo | Llamada actual | Después del fix |
|---|---|---|---|
| `multi_crew_flow.py` | L117-118 | `await crew.run_async()` → `create_agent_async()` (sync + deadlock) | `await crew.run_async()` → `await create_agent_async()` (async, sin deadlock) |
| `dynamic_flow.py` | L94-95 | `await crew.run_async()` → `create_agent_async()` (sync + deadlock) | Idem — sin cambios en flow, fix en factory/base_crew |
| `agents.py` (API route) | L198 | `await crew.run_async()` → `create_agent_async()` | Idem |

---

## 4️⃣ Análisis Fullstack + DX (ETAPA 4)

### Flujo end-to-end del bug

```
Flow.execute() [async, event loop L]
  → BaseCrew.run_async() [async]
    → AgentFactory.create_agent_async() [sync — BUG: debería ser async]
      → resolve_tools(async_mode=True) [sync]
        → _resolve_mcp_tool() [sync]
          → asyncio.run_coroutine_threadsafe(pool.get_tools(), loop=L).result()
            → .result() BLOQUEA thread → loop L no procesa coro → DEADLOCK ↑
```

### Flujo end-to-end post-fix

```
Flow.execute() [async, event loop L]
  → BaseCrew.run_async() [async]
    → await AgentFactory.create_agent_async() [async — FIXED]
      → await resolve_tools_async() [async — NUEVO]
        → await _resolve_mcp_tool_async() [async — NUEVO, sin .result()]
          → await pool.get_tools() [await directo, loop L avanza]
            → tools list → sin deadlock ✅
```

### Coherencia

- ✅ Plan realizable con arquitectura existente — solo refactor sync→async en factory
- ✅ Decisiones de data/code/backend alineadas con MVP
- ✅ Sin cambios en DB, APIs o frontend

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap check-deadlock
- **Qué automatiza:** Verifica que no haya llamadas `run_coroutine_threadsafe().result()` desde contexto async. Busca patrones de deadlock sync→async en todo el codebase.
- **Tipo:** script CLI (Typer command)
- **Cómo se usa:** `fap check-deadlock` — escanea src/ en busca de `run_coroutine_threadsafe().` + `.result()` y reporta archivo/línea/contexto (sync o async). Exit 0 si no hay deadlocks potenciales.
- **Impacto para usuario final:** Previene reintroducción del mismo tipo de deadlock en futuros desarrollos. Categoriza como Tarea 0.
- **Prioridad:** Tarea 0 — implementar antes del resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] `AgentFactory.resolve_tools_async()` existe como método async con firma:
       `async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list`
✅ [CODE] `AgentFactory._resolve_mcp_tool_async()` existe como método async:
       `async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any | None`
       Usa `await pool.get_tools()` — SIN `run_coroutine_threadsafe().result()`
✅ [CODE] `AgentFactory.create_agent_async()` es `async def` y usa `await resolve_tools_async()`
✅ [CODE] `BaseCrew.run_async()` llama `await AgentFactory.create_agent_async()`
✅ [CODE] `resolve_tools()` sync NO cambia — MCP skipped con warning, tools regulares funcionan igual
✅ [TEST] Flow async con MCP tools completa sin deadlock
✅ [TEST] Flow sync con MCP tools skipea MCP (comportamiento actual preservado)
✅ [TEST] `resolve_tools` sync sin MCP tools retorna tools regulares — no cambia
✅ [TEST] Tests existentes de factory pasan sin modificación
✅ [TEST] Tests MCP execution pasan sin parche `_resolve_mcp_tool` (test_exec_agent_mcp.py, test_exec_multi_mcp.py)
✅ [DX] `fap check-deadlock` existe y escanea `run_coroutine_threadsafe().result()` en codebase
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1 — Break tests existentes que llaman `resolve_tools()` sync | Alta | `async def` cambia tipo de retorno. Tests que esperan lista obtienen coroutine. | **NO** cambiar `resolve_tools` a async. Crear `resolve_tools_async()` separado. Tests existentes intactos. |
| R2 — `create_agent_async()` llamado sin await en algún flow no cubierto | Alta | Flujo no analizado que usa `create_agent_async()` directamente sin await | Buscar grep `create_agent_async` en todo src/. Verificar que todos los callers usen `await` después del cambio. |
| R3 — `_resolve_mcp_tool_async()` no cubre errores de import (crewai-tools opcional) | Media | `_resolve_mcp_tool` actual verifica dependencias opcionales. Nueva versión async debe replicar ese guard. | Incluir mismo bloque `importlib.util.find_spec` en `_resolve_mcp_tool_async()` |
| R4 — MCPPool.get_tools() falla por circuit breaker abierto | Media | Circuit breaker en mcp_pool.py puede lanzar MCPConnectionError. Async path debe manejarlo igual que sync path. | `_resolve_mcp_tool_async()` debe capturar MCPConnectionError y loguear + retornar None, igual que sync version. |
| R5 — Regresión: algún flujo sync llama accidentalmente `resolve_tools_async` | Baja | Nombre similar puede confundir | Tests de tipo verifican que `resolve_tools` sync no puede resolver MCP tools (solo async) |

---

## 7️⃣ Plan de Implementación

> **REGLA:** Una tarea = un artefacto = interfaz exacta = patrón explícito = verificación inline.
> **REGLA:** Tarea 0 siempre = DX & Tooling. Implementar primero.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: fap check-deadlock** | `src/cli/commands/check_deadlock.py` | `def check_deadlock() -> int:` — escanea `run_coroutine_threadsafe.*\.result\(\)` en `src/` | `src/cli/commands/check_env.py` — patrón comando simple con `app.command()` | DX | Baja | 0.5h | Ninguna | `fap check-deadlock` exit 0 (sin deadlocks nuevos). Exit >0 si encuentra patrón. |
| 1 | **Crear `_resolve_mcp_tool_async()`** | `src/crews/factory.py` | `async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any \| None:` — usa `await MCPPool.get().get_tools(org_id, server)`, replica guards de import opcional | `_resolve_mcp_tool()` actual (factory.py:80-133) — misma lógica pero con await en vez de `run_coroutine_threadsafe().result()` | CODE | Baja | 0.3h | Ninguna | Importable desde factory.py sin error. Invocable con await. |
| 2 | **Crear `resolve_tools_async()`** | `src/crews/factory.py` | `async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list:` — Itera tools, MCP usa `await _resolve_mcp_tool_async()`, regulares usan `tool_registry.get()` (sync, sin cambio) | `resolve_tools()` actual (factory.py:28-78) — misma lógica pero MCP path usa await | CODE | Baja | 0.3h | Tarea 1 | `await resolve_tools_async(["db_read"], org_id)` retorna tools sin MCP tocado. `await resolve_tools_async(["mcp:s:t"], org_id)` resuelve MCP sin deadlock. |
| 3 | **Hacer `create_agent_async()` async** | `src/crews/factory.py` | `async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent:` — usa `await resolve_tools_async()` para tools | `create_agent()` (factory.py:136-159) — mismo constructor de Agent, tool resolution cambia | CODE | Baja | 0.2h | Tarea 2 | `await create_agent_async(config, org_id)` retorna Agent sin deadlock con MCP tools. |
| 4 | **Actualizar `BaseCrew.run_async()`** | `src/crews/base_crew.py` | Cambiar `agent = AgentFactory.create_agent_async(...)` → `agent = await AgentFactory.create_agent_async(...)` | Llamada existente (base_crew.py:185) — solo añadir await | CODE | Baja | 0.1h | Tarea 3 | `test_base_crew.py` tests pasan. |
| 5 | **Actualizar tests existentes** | `tests/unit/test_factory.py` | `test_create_agent_async_enables_mcp` → marcar `async def` + `await create_agent_async()`. NO eliminar tests sync existentes. | Patrón `@pytest.mark.asyncio` en tests/fixtures existentes | CODE | Baja | 0.3h | Tarea 3 | `uv run pytest tests/unit/test_factory.py -v` → tests existentes pasan + test async nuevo pasa. |
| 6 | **Remover parche `_resolve_mcp_tool` en E2E** | `tests/e2e/test_exec_agent_mcp.py`, `tests/e2e/test_exec_multi_mcp.py` | Remover parches que mockean `_resolve_mcp_tool`. Tests usan resolución async real. | Revisar parches actuales en esos archivos | TEST | Media | 0.5h | Tareas 0-4 | `uv run pytest tests/e2e/test_exec_agent_mcp.py tests/e2e/test_exec_multi_mcp.py -v` pasan. |
| 7 | **Agregar test unitario `resolve_tools_async`** | `tests/unit/test_factory.py` | Nueva clase `TestResolveToolsAsync` — testea MCP resolution async con pool mockeado, verifica sin deadlock | `test_mcp_resolved_in_async_mode` (test_factory.py:69-86) — mismo patrón pero con async mock de MCPPool | TEST | Media | 0.4h | Tareas 1-2 | `uv run pytest tests/unit/test_factory.py::TestResolveToolsAsync -v` → 2-3 tests pasan. |
| 8 | **Validar flujo end-to-end sin deadlock** | — | Ejecutar flow async con MCP tools configuradas. Verificar que completa sin colgarse. | Prueba manual o test E2E existente | FULLSTACK | Baja | 0.3h | Tareas 1-4 | Criterios §5 [FULLSTACK] y [DX] pasan todos. |

**Tiempo total estimado:** 2.6 horas

---

## 🔮 Roadmap (NO implementar ahora)

- `_resolve_mcp_tool()` actual (sync version) podría refactorizarse para reusar `_resolve_mcp_tool_async()` con `asyncio.run()` cuando no hay loop running — reduciría duplicación de lógica
- Eventualmente, `resolve_tools()` sync podría eliminarse si todos los callers migran a async — pero requiere cambios en `create_agent()` y `BaseCrew.run()`
- `fap check-deadlock` podría integrarse en CI como hook pre-commit

---

## 📊 Métrica de Calidad

| Métrica | Resultado |
|---|---|
| `proyecto-config.json` leído antes de explorar | ✅ |
| Elementos verificados (§0) | 16 (≥8 para 1-2 archivos) |
| Discrepancias detectadas | 5 (≥1 — toca código existente) |
| Secciones completadas | 8 secciones (0-7) |
| Etapas cubiertas | 4 etapas (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 11 (≥1 por sub-paso) |
| Riesgos identificados | 5 (≥3) |
| Tareas atómicas (1 artefacto por tarea) | 9 tareas — 100% atómicas |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia explícito por tarea | 100% |
| Verificación inline por tarea | 100% |
| Propuesta DX / Tooling | 1 herramienta (`fap check-deadlock`) |
| Estimación de tiempo | 2.6h total |
