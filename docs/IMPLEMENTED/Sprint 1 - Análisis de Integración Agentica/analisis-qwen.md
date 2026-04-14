# 🧠 ANÁLISIS TÉCNICO — Sprint 1: Prerrequisitos + MCP Server Básico

**Agente:** qwen (Analista)
**Fecha:** 2026-04-13
**Paso:** Sprint 1 completo (Paso 1.0 + 1.1 + 1.2 + 1.3 + 1.4 + 1.5)
**Referencia:** `docs/plan.md` (Sprint 1 definition), `docs/estado-fase.md` (Fase 5 estado)

---

## 0. Verificación contra Código Fuente (OBLIGATORIA)

### Tabla de Verificación (22 elementos — alcance 10+ archivos)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `FlowRegistry` con `list_flows()`, `get_metadata()`, `register()` | `src/flows/registry.py` completo | ✅ VERIFICADO | `registry.py:52-82` — `register()` acepta `depends_on`, `category`; **NO acepta `description`** |
| 2 | `get_secret_async()` importado en `mcp_pool.py` | `src/tools/mcp_pool.py:22` — `from ..db.vault import get_secret_async` | ❌ DISCREPANCIA | **Función NO existe** en `vault.py`. Solo `get_secret()` síncrono (`vault.py:33-68`) |
| 3 | `FLOW_INPUT_SCHEMAS` definido en `flows.py` | `src/api/routes/flows.py:70-130` | ✅ VERIFICADO | 4 schemas: `bartenders_preventa`, `bartenders_reserva`, `bartenders_alerta`, `bartenders_cierre` |
| 4 | `mcp` como dependencia transitiva vía `crewai-tools` | `pyproject.toml` — `[project.optional-dependencies]` crew | ✅ VERIFICADO | `mcp` NO está en `[project.dependencies]` directo |
| 5 | `agent_catalog` tabla existe | `supabase/migrations/004_agent_catalog.sql` | ✅ VERIFICADO | Columnas: `id, org_id, role, is_active, soul_json, allowed_tools, max_iter, created_at, updated_at` |
| 6 | RLS pattern con `current_org_id()` y cast `::text` | `001_set_config_rpc.sql:37-44` | ✅ VERIFICADO | `current_org_id()` retorna `TEXT`; policies usan `org_id::text = current_org_id()` |
| 7 | `require_org_id` middleware existe | `src/api/middleware.py:103` | ✅ VERIFICADO | `async def require_org_id(x_org_id: str = Header(..., alias="X-Org-ID"))` |
| 8 | `verify_org_membership` middleware existe | `src/api/middleware.py:356` | ✅ VERIFICADO | `async def verify_org_membership(request, org_id, user)` — verifica `org_members` table |
| 9 | `httpx` como dependencia directa | `pyproject.toml:22` — `"httpx>=0.28.0"` | ✅ VERIFICADO | Confirmado en dependencies |
| 10 | `src/mcp/__init__.py` existe | `src/mcp/__init__.py` | ✅ VERIFICADO | Una sola línea: docstring del módulo |
| 11 | `src/mcp/sanitizer.py` existe | `src/mcp/sanitizer.py` | ✅ VERIFICADO | `sanitize_output()` con 7 patrones regex |
| 12 | `pyproject.toml` usa `hatchling` build system | `pyproject.toml:45-48` | ✅ VERIFICADO | `build-backend = "hatchling.build"` |
| 13 | `requires-python = ">=3.12,<3.14"` | `pyproject.toml:6` | ✅ VERIFICADO | `asyncio.to_thread()` disponible (Python 3.9+) |
| 14 | `TenantClient` con `get_service_client()` | `src/db/session.py` | ✅ VERIFICADO | `get_service_client()` singleton con service_role key |
| 15 | `register_flow` decorator convenience | `src/flows/registry.py:210-215` | ✅ VERIFICADO | Wrapper de `flow_registry.register()` |
| 16 | Flows registrados actualmente | `generic_flow.py`, `test_flows.py`, `architect_flow.py` | ✅ VERIFICADO | 4 flows: `generic_flow`, `success_test_flow`, `fail_test_flow`, `architect_flow` |
| 17 | `bartenders_*` NO están registrados en FlowRegistry | `src/api/routes/flows.py` tiene schemas pero no registro | ⚠️ DISCREPANCIA | Los schemas existen en `flows.py:70-130` pero **no hay código que registre** `bartenders_preventa` etc. en FlowRegistry |
| 18 | `src/tools/bartenders/` existe con tools | `clima_tool.py`, `escandallo_tool.py`, `inventario_tool.py` | ✅ VERIFICADO | 3 files en `src/tools/bartenders/` |
| 19 | `src/scheduler/bartenders_jobs.py` existe | `src/scheduler/bartenders_jobs.py` | ✅ VERIFICADO | Jobs: `check_upcoming_events_climate`, `update_prices_all_orgs` — importan de `src.crews.bartenders` |
| 20 | `src/api/main.py` lifespan | `src/api/main.py:50-68` | ✅ VERIFICADO | Importa `generic_flow`, `architect_flow`, `test_flows`, `tools.builtin` — **NO importa `bartenders_jobs`** |
| 21 | `domain_events` tabla schema | `001_set_config_rpc.sql:68-79` | ✅ VERIFICADO | `(id, org_id, aggregate_type, aggregate_id, event_type, payload, actor, sequence, created_at)` |
| 22 | `src/flows/demo/` NO existe | `glob` retornó 0 resultados | ❌ DISCREPANCIA | **El plan dice mover bartenders tools a `src/tools/demo/`** — directorio no existe |

### Discrepancias Encontradas

**D1 — `get_secret_async()` NO existe en `vault.py`**
- **Evidencia:** `grep -rn "get_secret_async" src/db/vault.py` → 0 resultados. `mcp_pool.py:22` la importa pero falla al ejecutar.
- **Impacto:** Bloqueante para MCP server async y para MCPPool existente.
- **Resolución:** Crear wrapper async en `vault.py` usando `asyncio.to_thread(get_secret, org_id, secret_name)`. Es exactamente lo que pide el Paso 1.0.1.

**D2 — `FlowRegistry.register()` NO acepta `description`**
- **Evidencia:** `registry.py:52-82` — firma es `register(name, depends_on, category)`. No hay parámetro `description`.
- **Impacto:** Sin descriptions, los tools MCP generados por `flow_to_tool.py` tendrán descriptions genéricas ("Flow: generic_flow").
- **Resolución:** Agregar parámetro `description: str = ""` a `register()` y almacenarlo en `self._metadata[name]["description"]`. Es el Paso 1.0.3.

**D3 — `bartenders_*` flows NO están registrados en FlowRegistry**
- **Evidencia:** `flows.py:70-130` define `FLOW_INPUT_SCHEMAS` con 4 schemas, pero no hay `@register_flow("bartenders_preventa")` ni equivalente. Los únicos flows registrados son: `generic_flow`, `success_test_flow`, `fail_test_flow`, `architect_flow`.
- **Impacto:** `list_flows` retornará solo 4 flows, no los de Bartenders. `flow_to_tool.py` generará tools solo para los registrados.
- **Resolución:** Esto es intencional — los bartenders flows son dominio-específicos y deben moverse a `src/tools/demo/` (Paso 1.0.0.1 T3). Los schemas en `flows.py` deben renombrarse o eliminarse (T2). Para Sprint 1, los 4 flows existentes son suficientes para validar conectividad.

**D4 — `src/tools/demo/` NO existe**
- **Evidencia:** `glob **/demo/**` → 0 resultados.
- **Impacto:** El Paso 1.0.0.1 T3 pide mover bartenders tools a `src/tools/demo/`. El directorio debe crearse.
- **Resolución:** Crear directorio `src/tools/demo/` con `__init__.py` y mover los 3 archivos existentes (`clima_tool.py`, `escandallo_tool.py`, `inventario_tool.py`).

**D5 — `FLOW_INPUT_SCHEMAS` contiene keys `bartenders_*` que no corresponden a flows registrados**
- **Evidencia:** `flows.py:71-130` — schemas para `bartenders_preventa`, `bartenders_reserva`, `bartenders_alerta`, `bartenders_cierre`. Ninguno tiene flow registrado.
- **Impacto:** `flow_to_tool.py` intentará generar tools para flows que no existen en FlowRegistry. El plan propone renombrar a `demo_*` o eliminar.
- **Resolución:** Renombrar keys a `demo_preventa`, `demo_reserva`, `demo_alerta`, `demo_cierre` (Paso 1.0.0.1 T2). O eliminar y dejar un schema de ejemplo genérico. **Recomendación:** Eliminar los 4 schemas y dejar un solo schema de ejemplo (`generic_flow`) que sí tiene flow registrado. Esto evita confusión y el `flow_to_tool.py` no generará tools huérfanos.

**D6 — `src/api/main.py` NO importa `bartenders_jobs` en lifespan**
- **Evidencia:** `main.py:50-68` — lifespan importa `generic_flow`, `architect_flow`, `test_flows`, `tools.builtin`. No importa scheduler ni bartenders_jobs.
- **Impacto:** Los jobs scheduler de bartenders no arrancan automáticamente. El plan pide desacoplar bartenders del core.
- **Resolución:** El Paso 1.0.0.1 T1 pide renombrar `bartenders_jobs.py` → `jobs.py` o mover scheduler a `src/scheduler/__init__.py`. **Verifiqué que `scheduler/__init__.py` ya existe** (vacío o con contenido mínimo). Recomendación: Mover el scheduler setup a `__init__.py` y dejar que `main.py` lo importe condicionalmente.

**D7 — `python-jose` en deps pero código usa PyJWT**
- **Evidencia:** `pyproject.toml:19` — `"python-jose[cryptography]>=3.3.0"`. `middleware.py:54` — `import jwt as pyjwt`.
- **Impacto:** Dependencia innecesaria. No bloquea Sprint 1 pero es deuda técnica.
- **Resolución:** No es parte del Sprint 1. Documentar como deuda técnica para limpieza posterior.

---

## 1. Diseño Funcional

### Happy Path (Sprint 1 Completo)

1. **Paso 1.0 — Prerrequisitos:**
   - Se crea `get_secret_async()` en `vault.py` como wrapper de `get_secret()` vía `asyncio.to_thread()`.
   - Se agrega `mcp>=1.0.0,<2.0.0` como dependencia directa en `pyproject.toml`.
   - Se enriquece `FlowRegistry.register()` con parámetro `description`.
   - Se verifica que `FLOW_INPUT_SCHEMAS` es importable desde `src.api.routes.flows`. Se decide **no extraer** (no hay dependencia circular verificada).
   - Se limpian las referencias a `bartenders_*`: renombrar schemas a `demo_*` o eliminar. Se renombra `bartenders_jobs.py` → `jobs.py`. Se mueven bartenders tools a `src/tools/demo/`.

2. **Paso 1.1 — Módulo MCP Base:**
   - Se crea `src/mcp/config.py` con `MCPConfig(BaseSettings)`: `enabled`, `transport`, `host`, `port`, `require_auth`, `allowed_orgs`, `org_id`, `env_prefix="MCP_"`.
   - Se crea `src/mcp/tools.py` con 5 tools estáticas: `list_flows`, `list_agents`, `get_agent_detail`, `get_server_time`, `list_capabilities`. Cada una con su `Tool` definition (name, description, inputSchema).

3. **Paso 1.2 — Flow-to-Tool Translator:**
   - `src/mcp/flow_to_tool.py` importa `flow_registry` y `FLOW_INPUT_SCHEMAS`.
   - Para cada flow en `flow_registry.list_flows()`, genera un `Tool` MCP combinando metadata del registry + input schema.
   - Si un flow no tiene schema en `FLOW_INPUT_SCHEMAS`, usa schema vacío.
   - Retorna lista de `Tool` objects.

4. **Paso 1.3 — MCP Server Stdio:**
   - `src/mcp/server.py` es entry point con CLI `--org-id`.
   - Inicializa `MCPConfig`, registra tools (estáticas + dinámicas de flow_to_tool).
   - Handlers: `tools/list` (retorna todas), `tools/call` (dispatch por nombre).
   - Todos los handlers retornan `CallToolResult` con `TextContent` (JSON serializado).

5. **Paso 1.4 — Claude Desktop Config:**
   - Config JSON en `%APPDATA%\Claude\claude_desktop_config.json` apuntando al venv Python con `--org-id`.

6. **Paso 1.5 — Verificación E2E:**
   - Server arranca sin errores → `python -m src.mcp.server --org-id test --help`.
   - Claude Desktop conecta y muestra tools.
   - `list_flows` retorna datos reales.
   - `list_agents` retorna agentes de la org.
   - `get_agent_detail` acepta agent_id.

### Edge Cases

| Edge Case | Manejo |
|---|---|
| Flow registrado sin schema en `FLOW_INPUT_SCHEMAS` | Tool se genera con schema vacío `{}` + warning en log |
| `agent_catalog` vacío para la org | `list_agents` retorna `[]` (lista vacía) — no es error |
| `--org-id` no proporcionado al CLI | Server arranca con `org_id=""` — `list_agents` y `list_flows` filtran por org_id vacío (retornan todo o nada, según query) |
| `SUPABASE_SERVICE_KEY` no disponible | Server no puede conectar a DB — tools que requieren DB retornan error JSON |
| Import circular al importar `FLOW_INPUT_SCHEMAS` | Verificar en Paso 1.0.4; si hay, extraer a `src/flows/input_schemas.py` |

### Manejo de Errores (qué ve el usuario)

- **Error de import:** Server no arranca — traceback en stdout (Claude Desktop lo muestra como error de conexión).
- **Error de DB (Supabase down):** Tool retorna `{"error": "No se pudo conectar a la base de datos"}` como `TextContent`.
- **Flow no encontrado en `tools/call`:** `{"error": "Tool '{name}' not found"}`.
- **Query sin resultados:** `[]` o `{}` — no es error, es resultado legítimo.

---

## 2. Diseño Técnico

### Componentes Nuevos

#### 2.1 `src/db/vault.py` — agregar `get_secret_async()`

```python
async def get_secret_async(org_id: str, secret_name: str) -> str:
    """Wrapper async de get_secret() para uso en event loops MCP."""
    import asyncio
    return await asyncio.to_thread(get_secret, org_id, secret_name)
```

- **No modifica** `get_secret()` existente.
- Usa `asyncio.to_thread()` (disponible Python 3.9+).

#### 2.2 `src/mcp/config.py`

```python
from pydantic_settings import BaseSettings
from typing import List

class MCPConfig(BaseSettings):
    enabled: bool = True
    transport: str = "stdio"  # sse en Sprint 4
    host: str = "127.0.0.1"
    port: int = 8765
    require_auth: bool = False  # Sprint 3
    allowed_orgs: List[str] = []
    org_id: str = ""

    model_config = {"env_prefix": "MCP_"}
```

- CLI args (`--org-id`) override el env var.

#### 2.3 `src/mcp/tools.py` — Tools estáticas

5 tools con formato MCP SDK:

| Tool | inputSchema | Implementación |
|---|---|---|
| `list_flows` | `{}` | `flow_registry.get_hierarchy()` + metadata |
| `list_agents` | `{}` | Query `agent_catalog` WHERE `org_id = ?` AND `is_active = true` |
| `get_agent_detail` | `{agent_id: str}` | Query `agent_catalog` WHERE `id = ?` |
| `get_server_time` | `{}` | `datetime.utcnow().isoformat()` |
| `list_capabilities` | `{}` | Dict con versión FAP, `org_id`, `transport`, `tools_count` |

#### 2.4 `src/mcp/flow_to_tool.py`

```python
def build_flow_tools() -> list[Tool]:
    """Genera un Tool MCP por cada flow registrado."""
    from src.flows.registry import flow_registry
    from src.api.routes.flows import FLOW_INPUT_SCHEMAS

    tools = []
    for flow_name in flow_registry.list_flows():
        meta = flow_registry.get_metadata(flow_name)
        schema = FLOW_INPUT_SCHEMAS.get(flow_name, {"type": "object", "properties": {}})
        description = meta.get("description") or f"Ejecutar flow de trabajo: {flow_name}"

        tools.append(Tool(
            name=flow_name,
            description=description,
            inputSchema=schema,
        ))
    return tools
```

#### 2.5 `src/mcp/server.py` — Entry point

- CLI: `argparse` con `--org-id`.
- Inicializa `MCPConfig`.
- Crea servidor MCP Stdio con SDK `mcp`.
- Registra tools estáticas + flow-to-tool.
- Registra handlers `tools/list` y `tools/call`.
- Arranca con `mcp.run()`.

### Modelo de Datos (queries DB)

**`list_agents`:**
```sql
SELECT id, role, is_active, soul_json, allowed_tools, max_iter
FROM agent_catalog
WHERE org_id = :org_id AND is_active = true
```

**`get_agent_detail`:**
```sql
SELECT id, role, is_active, soul_json, allowed_tools, max_iter, created_at, updated_at
FROM agent_catalog
WHERE id = :agent_id AND org_id = :org_id
```

### APIs/Endpoints MCP (JSON-RPC 2.0 sobre Stdio)

| Método | Params | Respuesta |
|---|---|---|
| `tools/list` | `{}` | `{tools: [Tool, ...]}` |
| `tools/call` | `{name: "list_flows", arguments: {}}` | `{content: [TextContent(text=JSON)]}` |
| `tools/call` | `{name: "list_agents", arguments: {}}` | `{content: [TextContent(text=JSON)]}` |
| `tools/call` | `{name: "get_agent_detail", arguments: {agent_id: "..."}}` | `{content: [TextContent(text=JSON)]}` |
| `tools/call` | `{name: "get_server_time", arguments: {}}` | `{content: [TextContent(text=JSON)]}` |
| `tools/call` | `{name: "list_capabilities", arguments: {}}` | `{content: [TextContent(text=JSON)]}` |

### Integración con Código Existente

| Componente | Cómo se integra |
|---|---|
| `FlowRegistry` | `flow_to_tool.py` importa `flow_registry` directamente — no hay circularidad |
| `FLOW_INPUT_SCHEMAS` | Importado desde `src.api.routes.flows` — verificar dependencia circular (Paso 1.0.4) |
| `get_service_client()` | Usado por `list_agents` y `get_agent_detail` para queries directos |
| `TenantClient` | No se usa en Sprint 1 — las queries son de solo lectura con service_role |

---

## 3. Decisiones

| # | Decisión | Justificación Técnica |
|---|---|---|
| D1 | `require_auth = False` en Sprint 1 | Sprint 1 es conectividad básica. Auth Bridge (JWT, org membership) es Sprint 3. El `--org-id` CLI es suficiente para identificar la sesión en modo local. |
| D2 | `mcp>=1.0.0,<2.0.0` (version pinning) | El SDK MCP es nuevo y puede tener breaking changes. Fijar el upper bound evita sorpresas. |
| D3 | No extraer `FLOW_INPUT_SCHEMAS` a módulo separado **a menos que** se detecte dependencia circular | Verificación en Paso 1.0.4 determinará si es necesario. Si `flows.py` no importa de `mcp/`, no hay circularidad. |
| D4 | Eliminar schemas `bartenders_*` de `FLOW_INPUT_SCHEMAS` y dejar solo los de flows registrados | Los 4 schemas de bartenders no tienen flows registrados correspondientes. Mantenerlos generaría tools MCP huérfanos. Los flows registrados actualmente son: `generic_flow`, `success_test_flow`, `fail_test_flow`, `architect_flow`. |
| D5 | Mover bartenders tools a `src/tools/demo/` como dice el plan | Desacopla dominio específico del core. Los tools siguen existiendo pero no se importan por defecto. |
| D6 | Queries de `list_agents`/`get_agent_detail` usan `get_service_client()` (service_role) | Sprint 1 no tiene auth bridge. Las queries son de solo lectura y el `org_id` viene del CLI. service_role es apropiado para queries internas del servidor MCP. |
| D7 | `get_secret_async` usa `asyncio.to_thread()` (no `run_in_executor`) | `to_thread()` es más simple y es el padrão Python 3.9+. Equivalente funcional con menos boilerplate. |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificación |
|---|---|---|
| CA1 | `from mcp.types import Tool` funciona sin instalar `[crew]` | `python -c "from mcp.types import Tool; print('OK')"` → OK |
| CA2 | `get_secret_async()` definida en `vault.py` | `grep -n "async def get_secret_async" src/db/vault.py` → ≥ 1 resultado |
| CA3 | `get_secret_async` retorna mismo valor que `get_secret` | Test unitario: ambos retornan igual para mismo org_id + secret_name |
| CA4 | `FlowRegistry.register()` acepta `description` | `@register_flow("test", description="Test flow")` → `get_metadata("test")["description"] == "Test flow"` |
| CA5 | `FLOW_INPUT_SCHEMAS` no contiene keys `bartenders_*` | `grep "bartenders_" src/api/routes/flows.py` → 0 resultados en keys del dict |
| CA6 | Bartenders tools movidos a `src/tools/demo/` | `ls src/tools/demo/` → `clima_tool.py`, `escandallo_tool.py`, `inventario_tool.py` |
| CA7 | `bartenders_jobs.py` renombrado o desacoplado | `ls src/scheduler/` → `jobs.py` o scheduler en `__init__.py`; `grep -rn "bartenders_jobs" src/` → 0 resultados en core |
| CA8 | `python -m src.mcp.server --org-id test` arranca sin error de import | CLI ejecuta y muestra help o inicia server sin traceback |
| CA9 | `src/mcp/config.py` existe con `MCPConfig` | `python -c "from src.mcp.config import MCPConfig; print(MCPConfig().transport)"` → `stdio` |
| CA10 | `src/mcp/tools.py` define ≥5 tools | `python -c "from src.mcp.tools import get_static_tools; print(len(get_static_tools()))"` → ≥ 5 |
| CA11 | `src/mcp/flow_to_tool.py` genera tools por flow registrado | `python -c "from src.mcp.flow_to_tool import build_flow_tools; print(len(build_flow_tools()))"` → ≥ 4 (flows existentes) |
| CA12 | `src/mcp/server.py` registra handlers `tools/list` y `tools/call` | `grep -n "tools/list\|tools/call" src/mcp/server.py` → ≥ 2 resultados |
| CA13 | `tools/list` retorna ≥5 herramientas combinadas (estáticas + flows) | Verificación vía Claude Desktop o test script |
| CA14 | `list_flows` retorna flows reales con categoría y dependencias | Pregunta a Claude → datos de `flow_registry.get_hierarchy()` |
| CA15 | `list_agents` retorna lista (puede ser vacía) de `agent_catalog` | Pregunta a Claude → datos de query DB |
| CA16 | Todas las respuestas son `TextContent` con JSON válido | Parsear cada response como JSON sin error |
| CA17 | Claude Desktop config generado con path al venv Python correcto | `claude_desktop_config.json` con `"command": "<path-al-python-del-venv>"` válido |

---

## 5. Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | Dependencia circular al importar `FLOW_INPUT_SCHEMAS` desde `flow_to_tool.py` | Media | Medio | Paso 1.0.4 verifica. Si hay circular: extraer schemas a `src/flows/input_schemas.py`. **Mi análisis:** `flows.py` importa `webhooks.execute_flow` y `middleware.require_org_id` — ninguno importa de `mcp/`. Probablemente NO hay circular, pero confirmar. |
| R2 | SDK `mcp` tiene breaking changes entre 1.x | Baja | Alto | Version pin `mcp>=1.0.0,<2.0.0`. Verificar versión exacta instalada con `uv pip show mcp`. |
| R3 | Claude Desktop no detecta el servidor | Media | Alto | Verificar: (a) path al Python del `.venv` es correcto, (b) formato JSON es válido, (c) `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` están en `env`. Revisar logs en `%APPDATA%\Claude\logs\`. |
| R4 | `FlowRegistry` tiene pocos flows registrados (solo 4) | Alta | Bajo | Para Sprint 1 es suficiente — validar conectividad no requiere muchos flows. Los bartenders flows se pueden re-registrar después del desacople. |
| R5 | `agent_catalog` vacío para la org de test | Media | Medio | No bloquea — `list_agents` retorna `[]`. Crear seed data si se quiere validar con datos reales. |
| R6 | `SUPABASE_SERVICE_KEY` no disponible en env del proceso hijo | Media | Alto | Configurar explícitamente en `claude_desktop_config.json` → `env`. El proceso Claude Desktop hereda un environment diferente al shell. |
| R7 | `get_secret_async` con `asyncio.to_thread()` bloquea el event loop si `get_secret()` es lenta (DB timeout) | Baja | Bajo | `to_thread()` corre en thread pool separado — no bloquea el loop principal. Pero el timeout de la query puede ser largo. Mitigación: agregar timeout wrapper si se detecta lentitud. |
| R8 | `bartenders_jobs.py` renombrado rompe imports en otros archivos | Media | Medio | Verificar todos los imports existentes: `grep -rn "bartenders_jobs" src/`. Actualizar cada referencia. |
| R9 | `FLOW_INPUT_SCHEMAS` eliminado completamente deja `flows.py` sin schemas para los flows que SÍ existen (`generic_flow`, etc.) | Media | Medio | **Resolución:** No eliminar todos los schemas. Agregar al menos un schema para `generic_flow` (`{"text": "..."}`) para que `flow_to_tool.py` tenga algo útil. Los bartenders schemas se eliminan o renombran. |

---

## 6. Plan de Implementación

### Tareas Atómicas

| # | Tarea | Paso | Complejidad | Tiempo | Dependencias |
|---|---|---|---|---|---|
| T1 | Verificar import circular de `FLOW_INPUT_SCHEMAS` | 1.0.4 | Baja | 15min | Ninguna |
| T2 | Crear `get_secret_async()` en `vault.py` | 1.0.1 | Baja | 20min | T1 (no bloqueante) |
| T3 | Agregar `mcp>=1.0.0,<2.0.0` a `pyproject.toml` + `uv sync` | 1.0.2 | Baja | 15min | Ninguna |
| T4 | Enriquecer `FlowRegistry.register()` con `description` | 1.0.3 | Media | 45min | Ninguna |
| T5 | Desacoplar Bartenders NOA: renombrar `bartenders_jobs.py` → `jobs.py`, actualizar imports | 1.0.0.1 T1 | Media | 30min | Ninguna |
| T6 | Renombrar/eliminar schemas `bartenders_*` en `FLOW_INPUT_SCHEMAS` + agregar schema para `generic_flow` | 1.0.0.1 T2 | Baja | 20min | T1 |
| T7 | Mover bartenders tools a `src/tools/demo/` | 1.0.0.1 T3 | Baja | 20min | Ninguna |
| T8 | Verificar 0 referencias a "bartenders" en core | 1.0.0.1 T4 | Baja | 10min | T5, T6, T7 |
| T9 | Crear `src/mcp/__init__.py` (ya existe, verificar) | 1.1.1 | Baja | 5min | Ninguna |
| T10 | Crear `src/mcp/config.py` con `MCPConfig` | 1.1.2 | Baja | 30min | T3 (mcp dependency) |
| T11 | Crear `src/mcp/tools.py` con 5 tools estáticas | 1.1.3 | Media | 1h | T10 |
| T12 | Crear `src/mcp/flow_to_tool.py` translator | 1.2.1 | Media | 1h | T4, T6 |
| T13 | Crear `src/mcp/server.py` con CLI + handlers | 1.3.1 | Alta | 2h | T10, T11, T12 |
| T14 | Generar `claude_desktop_config.json` template | 1.4.1 | Baja | 15min | T13 |
| T15 | Test: server arranca sin errores | 1.5.1 | Baja | 10min | T1-T14 |
| T16 | Test E2E: Claude Desktop conecta + tools listadas | 1.5.2-1.5.5 | Media | 30min | T15 |

**Total estimado:** ~7h 15min (rango: 6-9h dependiendo de complejidad del SDK MCP)

### Orden Recomendado de Ejecución

```
T1 → T2, T3 (paralelo)
T3 → T10
T4 → T12
T5 → T8
T6 → T12
T7 → T8
T8 → (verificación)
T10 → T11
T11, T12 → T13
T13 → T14
T14 → T15 → T16
```

---

## 🔮 Roadmap (NO implementar ahora)

### Para Sprint 2 (Service Catalog TIPO C + Sanitizer)
- Conectar `sanitizer.py` al output del MCP server (ya existe pero no se usa en Sprint 1 porque no hay ejecución de tools externas).
- Service Catalog TIPO C como fuente de tools dinámicas — ya implementado en 5.2.5 pero no integrado al MCP server.

### Para Sprint 3 (Auth Bridge + Ejecución)
- `require_auth = true` en `MCPConfig`.
- Auth Bridge: verificar JWT del agente externo vía `_get_jwks_client()` existente.
- `execute_flow` handler — requiere `get_secret_async` para resolver credenciales de servicios.
- Excepciones MCP → JSON-RPC error codes estándar.

### Para Sprint 4 (SSE + HITL)
- Transport SSE (`mcp.server.SSEServer` o equivalente).
- `approve_task` / `reject_task` handlers.
- Inputs complejos (imágenes, archivos).

### Pre-requisitos descubiertos durante exploración
- **`python-jose` es dependencia fantasma:** está en `pyproject.toml` pero el código usa PyJWT. Debería eliminarse como dep directa (no bloquea nada, pero es confusión).
- **Health Check Scheduler no conectado al lifespan:** `health_check.py` existe pero no se invoca automáticamente. Debería registrarse en el lifespan de `main.py`.
- **FlowRegistry podría beneficiarse de `register(description=...)` para todos los flows existentes:** Los 4 flows registrados actualmente no tienen description — se generará automáticamente en Sprint 1 pero es mejorable.
- **`src/scheduler/__init__.py` existe pero no contiene el scheduler principal:** El plan de Fase 6 mencionaba mover scheduler aquí. Sería buena práctica para el desacople de bartenders.

---

*Análisis completado — Sprint 1 verificado contra código fuente real. 7 discrepancias detectadas y documentadas con resolución. 17 criterios de aceptación binarios. Estimación: 6-9h.*
