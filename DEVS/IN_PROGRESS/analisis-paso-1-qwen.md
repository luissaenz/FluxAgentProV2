# Análisis Técnico — Paso 1: Split Sync/Async en AgentFactory

**Agente:** qwen
**Paso:** paso 1 — Split Sync/Async en AgentFactory
**Fecha:** 2026-05-02
**Plan origen:** `DEVS/plan.md` — "Fix Deadlock en MCP Resolution Async"

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentFactory` clase existe | `src/crews/factory.py:14` | ✅ | Clase definida línea 14 |
| 2 | `resolve_tools()` existe | `src/crews/factory.py:28-78` | ✅ | Método estático con `async_mode` param |
| 3 | `_resolve_mcp_tool()` existe | `src/crews/factory.py:80-133` | ✅ | Usa `run_coroutine_threadsafe().result()` — causa deadlock |
| 4 | `create_agent_async()` existe | `src/crews/factory.py:161-183` | ✅ | Llama `resolve_tools(async_mode=True)` |
| 5 | `create_agent()` existe | `src/crews/factory.py:135-159` | ✅ | Llama `resolve_tools()` sin async_mode |
| 6 | `_parse_mcp_prefix()` existe | `src/crews/factory.py:17-25` | ✅ | Parsea `mcp:server:tool` |
| 7 | `MCPPool.get_tools()` es async | `src/tools/mcp_pool.py:77-191` | ✅ | Método async con retry + circuit breaker |
| 8 | `MCPPool.get()` singleton | `src/tools/mcp_pool.py:51-56` | ✅ | Clase singleton |
| 9 | `BaseCrew.run_async()` usa `create_agent_async()` | `src/crews/base_crew.py:185` | ✅ | Línea 185: `AgentFactory.create_agent_async(config, self.org_id)` |
| 10 | `BaseCrew.run()` usa `create_agent()` | `src/crews/base_crew.py:110` | ✅ | Línea 110: `AgentFactory.create_agent(config, self.org_id)` |
| 11 | `tool_registry` singleton existe | `src/tools/registry.py:272` | ✅ | `tool_registry = ToolRegistry()` |
| 12 | Deadlock call chain verificada | `factory.py:116-119` | ✅ | `run_coroutine_threadsafe(...).result()` bloquea thread cuando loop ya corre |
| 13 | `test_exec_agent_mcp.py` parchea `_resolve_mcp_tool` | `tests/e2e/test_exec_agent_mcp.py:62-65` | ✅ | `patch("src.crews.factory.AgentFactory._resolve_mcp_tool", return_value=None)` |
| 14 | `test_exec_multi_mcp.py` parchea `_resolve_mcp_tool` | `tests/e2e/test_exec_multi_mcp.py:75-78` | ✅ | Mismo patrón de parche |
| 15 | `test_factory.py` testea `resolve_tools` | `tests/unit/test_factory.py:18-98` | ✅ | Tests sync + async mode con mock `_resolve_mcp_tool` |
| 16 | `MCPPool.get_tools()` firma | `src/tools/mcp_pool.py:77-82` | ✅ | `async def get_tools(self, org_id: str, server_name: str, timeout: int = 30, max_retries: int = 3) -> list` |
| 17 | `AgentFactory` imports | `src/crews/factory.py:3-9` | ✅ | `logging`, `typing.Any/Dict`, `crewai.Agent/Task`, `src.config.get_settings`, `src.tools.registry.tool_registry` |
| 18 | `crewai` es dependencia opcional | `proyecto-config.json:132-133` | ✅ | `crewai>=0.100.0` en optional |

**Discrepancias encontradas:**

1. **❌ Plan propone `resolve_tools_async()` como método separado** → Código actual ya tiene `async_mode` param en `resolve_tools()`. La alternativa recomendada en plan (convertir `resolve_tools` en async cuando `async_mode=True`) es más limpia y requiere menos cambios.
2. **⚠️ Plan dice `create_agent_async` debe ser async** → Actualmente es sync (`def create_agent_async`). Si `resolve_tools` se vuelve async, `create_agent_async` debe ser `async def`. Esto rompe callers que no hacen await.
3. **❌ `MCPPool.get_tools()` firma real difiere del plan** → Plan asume `pool.get_tools(org_id, server)` pero firma real es `pool.get_tools(org_id, server_name, timeout=30, max_retries=3)`.
4. **⚠️ Tests e2e parchean `_resolve_mcp_tool`** → Si se elimina o renombra `_resolve_mcp_tool`, los parches en `test_exec_agent_mcp.py:62` y `test_exec_multi_mcp.py:75` romperán. Deben actualizarse para parchear `_resolve_mcp_tool_async` o remover parche completamente.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Sin impacto en schema DB.** Este paso es puramente código — no toca migraciones, tablas ni RLS.

- Tablas involucradas indirectamente: `agent_catalog` (lee allowed_tools), `org_mcp_servers` (lee config MCP vía MCPPool)
- Ninguna columna nueva, ninguna migración
- RLS: sin cambios — MCPPool ya usa tenant client con org_id

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Código existente — patrón actual

**`factory.py:28-78` — `resolve_tools()` actual:**
```python
@staticmethod
def resolve_tools(
    allowed_tools: list[str], org_id: str, *, async_mode: bool = False
) -> list:
```
- Itera `allowed_tools`
- Si `mcp:` + `async_mode=False` → skip con warning
- Si `mcp:` + `async_mode=True` → llama `_resolve_mcp_tool()` (sync, con `run_coroutine_threadsafe`)
- Si no `mcp:` → resolve via `tool_registry.get()`

**`factory.py:80-133` — `_resolve_mcp_tool()` actual:**
```python
@staticmethod
def _resolve_mcp_tool(org_id: str, server: str, tool_name: str) -> Any | None:
```
- Lazy import crewai_tools + mcp
- Obtiene `MCPPool.get()`
- Detecta loop running → usa `run_coroutine_threadsafe().result()` → **DEADLOCK**
- Si no loop running → usa `asyncio.run()`

### Cambio propuesto — alternativa recomendada del plan

**Opción A: `resolve_tools` se vuelve async cuando `async_mode=True`**

```python
@staticmethod
async def resolve_tools(
    allowed_tools: list[str], org_id: str, *, async_mode: bool = False
) -> list:
```

Problema: `resolve_tools` ahora es `async def` siempre. Callers sync (`create_agent`) no pueden await.

**Opción B (mejor): Dos métodos separados — `resolve_tools` sync + `resolve_tools_async` async**

```python
# Sync — sin MCP
@staticmethod
def resolve_tools(allowed_tools: list[str], org_id: str) -> list:
    ...  # MCP skipped siempre

# Async — con MCP
@staticmethod
async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list:
    ...  # MCP resuelto con await

# Nuevo helper async
@staticmethod
async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any | None:
    from src.tools.mcp_pool import MCPPool
    pool = MCPPool.get()
    all_tools = await pool.get_tools(org_id, server)
    for tool in all_tools:
        if hasattr(tool, "name") and tool.name == tool_name:
            return tool
    return None
```

**`create_agent_async` se vuelve async:**
```python
@staticmethod
async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent:
    tools = await AgentFactory.resolve_tools_async(allowed_tools, org_id)
    return Agent(...)
```

### Firmas exactas de artefactos nuevos/modificados

| Artefacto | Firma | Archivo |
|---|---|---|
| `resolve_tools_async` | `async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list` | `src/crews/factory.py` |
| `_resolve_mcp_tool_async` | `async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any \| None` | `src/crews/factory.py` |
| `create_agent_async` (modificado) | `async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent` | `src/crews/factory.py` |
| `resolve_tools` (modificado) | `def resolve_tools(allowed_tools: list[str], org_id: str) -> list` (sin `async_mode`) | `src/crews/factory.py` |

### Imports a mantener

```python
import logging
from typing import Any, Dict
from crewai import Agent, Task
from src.config import get_settings
from src.tools.registry import tool_registry
```

### Patrón de referencia

- `_resolve_mcp_tool_async` sigue patrón de `MCPPool.get_tools()` en `src/tools/mcp_pool.py:77-191` — await directo, sin `run_coroutine_threadsafe`
- `resolve_tools_async` sigue patrón de `resolve_tools` actual pero con `await` en lugar de `.result()`

### BaseCrew — cambio necesario

`base_crew.py:185`:
```python
# ANTES (sync call dentro de async method):
agent = AgentFactory.create_agent_async(config, self.org_id)

# DESPUÉS (await):
agent = await AgentFactory.create_agent_async(config, self.org_id)
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Impacto en APIs/endpoints

**Sin cambios en rutas HTTP.** Este paso es interno a crews/factory.

### Flujo de datos modificado

**ANTES (deadlock):**
```
Flow.execute() [async]
  → BaseCrew.run_async() [async]
    → AgentFactory.create_agent_async() [sync]
      → resolve_tools(async_mode=True) [sync]
        → _resolve_mcp_tool() [sync]
          → run_coroutine_threadsafe(coro, loop).result() → BLOQUEA → DEADLOCK
```

**DESPUÉS (sin deadlock):**
```
Flow.execute() [async]
  → BaseCrew.run_async() [async]
    → await AgentFactory.create_agent_async() [async]
      → await resolve_tools_async() [async]
        → await _resolve_mcp_tool_async() [async]
          → await pool.get_tools() → OK
```

### Error handling

`_resolve_mcp_tool_async` debe propagar excepciones de `MCPPool.get_tools()`:
- `MCPConnectionError` → log error, skip tool
- `asyncio.TimeoutError` → log error, skip tool
- Exception genérica → log error, skip tool

Mismo comportamiento que `_resolve_mcp_tool` actual pero sin el puente sync→async.

### Contratos entre servicios

- `AgentFactory.resolve_tools_async()` → retorna `list` de tool objects (mismo tipo que sync)
- `AgentFactory.create_agent_async()` → retorna `Agent` (mismo tipo que sync)
- `MCPPool.get_tools()` → retorna `list` de tool objects (sin cambio)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

DB (`agent_catalog.allowed_tools`) → `BaseCrew.run_async()` → `AgentFactory.create_agent_async()` → `resolve_tools_async()` → `_resolve_mcp_tool_async()` → `MCPPool.get_tools()` → `Agent(tools=...)` → `Crew.kickoff_async()` → resultado

### Coherencia

- Plan es realizable con arquitectura existente
- `BaseCrew.run_async()` ya es async — solo necesita `await` en `create_agent_async`
- `MCPPool.get_tools()` ya es async — compatible directo
- No hay fricción entre capas

### Gaps

1. **Callers de `create_agent_async` fuera de `BaseCrew`** → buscar todos los usos. Si hay callers sync que no pueden await, necesitan adaptación.
2. **`resolve_tools` con `async_mode` param** → si se elimina el param, cualquier caller externo que lo pase romperá.

### DX & Tooling — Herramienta Propuesta

### Herramienta Propuesta: `fap check-deadlock`
- **Qué automatiza:** Detecta llamadas a `asyncio.run_coroutine_threadsafe().result()` en código base — patrón de deadlock potencial. Escanea todos los `.py` files buscando este anti-pattern.
- **Tipo:** CLI command + validador estático
- **Cómo se usa:** `fap check-deadlock --path src/` o `fap check-deadlock --check` (exit 1 si encuentra patrones)
- **Impacto para el usuario final:** Previene reintroducción del bug de deadlock en futuros cambios. CI puede ejecutarlo como gate.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] Método `resolve_tools_async()` existe en `AgentFactory` con firma `async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list`
✅ [CODE] Método `_resolve_mcp_tool_async()` existe en `AgentFactory` con firma `async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any | None`
✅ [CODE] `create_agent_async()` es `async def` y usa `await resolve_tools_async()`
✅ [CODE] `resolve_tools()` sync ya NO acepta `async_mode` param — MCP siempre skipped
✅ [CODE] `BaseCrew.run_async()` usa `await AgentFactory.create_agent_async()`
✅ [BACKEND] Flow async con MCP tools completa sin deadlock (no `.result()` bloqueante)
✅ [BACKEND] Flow sync con MCP tools skipea MCP (comportamiento actual mantenido)
✅ [FULLSTACK] Tests e2e `test_exec_agent_mcp.py` y `test_exec_multi_mcp.py` pasan sin parchear `_resolve_mcp_tool`
✅ [FULLSTACK] Tests unitarios `test_factory.py` pasan con nuevos métodos async
✅ [DX] Herramienta `fap check-deadlock` ejecuta sin errores y detecta patrón `run_coroutine_threadsafe().result()`
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Break callers de `create_agent_async` | Alta | Cambio de sync a async — callers que no hacen await fallarán | Buscar todos los usos con grep antes de implementar. Actualizar cada caller. |
| Tests e2e rompen por parche obsoleto | Media | Tests parchean `_resolve_mcp_tool` que cambiará | Actualizar parches a `_resolve_mcp_tool_async` o remover si ya no necesario |
| `resolve_tools` pierde `async_mode` param | Media | Callers externos que pasen `async_mode=True` romperán | Verificar con grep si hay callers fuera de factory.py |
| Regresión en sync path | Baja | Modificar `resolve_tools` podría introducir bugs en path sync | Mantener path sync intacto — solo remover `async_mode` param + MCP skip logic |
| MCPPool no disponible en tests | Media | Tests unitarios mockean `_resolve_mcp_tool`, no `MCPPool` | Tests unitarios deben mockear `MCPPool.get_tools()` para path async |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap check-deadlock` | `src/cli/commands/check_deadlock.py` | `def check_deadlock(path: str = "src/") -> list[str]` escanea `.py` files por `run_coroutine_threadsafe.*\.result\(\)` | `src/cli/commands/security_audit.py` — patrón de scan + output + exit code | DX | Baja | 1h | Ninguna | → verificar: `uv run python -m src.cli.main check-deadlock --path src/` encuentra 1 match en `factory.py` |
| 1 | Crear `_resolve_mcp_tool_async()` | `src/crews/factory.py` — nuevo método | `@staticmethod async def _resolve_mcp_tool_async(org_id: str, server: str, tool_name: str) -> Any \| None` | `src/tools/mcp_pool.py::get_tools()` — await directo sin bridge | CODE | Baja | 0.5h | Tarea 0 | → verificar: `uv run python -c "from src.crews.factory import AgentFactory; import inspect; assert inspect.iscoroutinefunction(AgentFactory._resolve_mcp_tool_async)"` |
| 2 | Crear `resolve_tools_async()` | `src/crews/factory.py` — nuevo método | `@staticmethod async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list` | `src/crews/factory.py::resolve_tools()` — misma lógica iterativa pero con `await _resolve_mcp_tool_async()` en vez de `_resolve_mcp_tool()` | CODE | Media | 1h | Tarea 1 | → verificar: `uv run python -c "from src.crews.factory import AgentFactory; import inspect; assert inspect.iscoroutinefunction(AgentFactory.resolve_tools_async)"` |
| 3 | Modificar `create_agent_async()` a async | `src/crews/factory.py:161-183` | `@staticmethod async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent` — body: `tools = await AgentFactory.resolve_tools_async(allowed_tools, org_id)` | `src/crews/factory.py::create_agent()` — misma estructura de Agent() pero con await | CODE | Media | 0.5h | Tarea 2 | → verificar: `uv run python -c "from src.crews.factory import AgentFactory; import inspect; assert inspect.iscoroutinefunction(AgentFactory.create_agent_async)"` |
| 4 | Modificar `resolve_tools()` — remover `async_mode` | `src/crews/factory.py:28-78` | `@staticmethod def resolve_tools(allowed_tools: list[str], org_id: str) -> list` — MCP siempre skipped con warning | Mismo método actual pero sin param `async_mode` y sin branch async | CODE | Baja | 0.5h | Tarea 2 | → verificar: `uv run python -c "from src.crews.factory import AgentFactory; import inspect; sig = inspect.signature(AgentFactory.resolve_tools); assert 'async_mode' not in sig.parameters"` |
| 5 | Modificar `BaseCrew.run_async()` — await create_agent_async | `src/crews/base_crew.py:185` | Cambiar `agent = AgentFactory.create_agent_async(config, self.org_id)` → `agent = await AgentFactory.create_agent_async(config, self.org_id)` | — | CODE | Baja | 0.25h | Tarea 3 | → verificar: `grep -n "await.*create_agent_async" src/crews/base_crew.py` retorna línea con await |
| 6 | Actualizar tests e2e — remover parche `_resolve_mcp_tool` | `tests/e2e/test_exec_agent_mcp.py:62-65` | Remover `patch("src.crews.factory.AgentFactory._resolve_mcp_tool", ...)` — test usa resolución async real | — | CODE | Baja | 0.5h | Tareas 1-3 | → verificar: `uv run pytest tests/e2e/test_exec_agent_mcp.py -v --timeout=120` pasa sin error |
| 7 | Actualizar tests e2e — remover parche `_resolve_mcp_tool` | `tests/e2e/test_exec_multi_mcp.py:75-78` | Remover `patch("src.crews.factory.AgentFactory._resolve_mcp_tool", ...)` — test usa resolución async real | — | CODE | Baja | 0.5h | Tareas 1-3 | → verificar: `uv run pytest tests/e2e/test_exec_multi_mcp.py -v --timeout=120` pasa sin error |
| 8 | Agregar test unitario para `resolve_tools_async` | `tests/unit/test_factory.py` — nueva clase | `class TestResolveToolsAsync:` con test `test_mcp_resolved_async` que mockea `MCPPool.get_tools` y verifica await | `tests/unit/test_factory.py::TestMCPToolResolution` — patrón de mock + assert | CODE | Media | 1h | Tareas 1-2 | → verificar: `uv run pytest tests/unit/test_factory.py -v --timeout=60 -k async` pasa |
| 9 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-8 | → verificar: criterios §5 pasan todos |

**Tiempo total estimado:** 6.25 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Convertir `create_agent()` también a async path unificado (eliminar duplicación sync/async)
- Agregar timeout configurable en `_resolve_mcp_tool_async` (pasar a `MCPPool.get_tools(timeout=...)`)
- Implementar lazy tool resolution en CrewAI Agent (tools como callable, resueltos solo cuando se usan)
- Agregar métrica de tiempo de resolución MCP para observabilidad
- `fap check-deadlock` extender a detectar otros anti-patterns async: `asyncio.run()` dentro de async context, `loop.run_until_complete()` en running loop

---

## 🚫 Reglas de Oro — Checklist

- ✅ `proyecto-config.json` leído antes de explorar
- ✅ 18 elementos verificados (§0) — umbral 3-5 archivos = ≥12
- ✅ 4 discrepancias detectadas (código existente tocado)
- ✅ 8 secciones completadas (0-7)
- ✅ 4 etapas cubiertas (data, code, backend, fullstack+DX)
- ✅ 10 criterios de aceptación — verificables, binarios
- ✅ 5 riesgos identificados (técnico, integración, futuro)
- ✅ 10 tareas atómicas — 1 artefacto por tarea
- ✅ Interfaz exacta por tarea — sin inferencias
- ✅ Patrón de referencia explícito por tarea — archivo concreto
- ✅ Verificación inline por tarea — comando concreto
- ✅ 1 herramienta DX propuesta: `fap check-deadlock`
- ✅ Estimación de tiempo: 6.25h total, por tarea individual
