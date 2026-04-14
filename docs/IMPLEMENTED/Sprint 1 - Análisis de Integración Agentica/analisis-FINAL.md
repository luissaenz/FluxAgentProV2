# 🏛️ ANÁLISIS FINAL UNIFICADO — Sprint 1: Prerrequisitos + MCP Server Básico

**Fase:** 5 — Ecosistema Agéntico (MCP)  
**Pasos cubiertos:** 1.0 (Prerrequisitos) + 1.1 (Módulo MCP Base) + 1.2 (Flow-to-Tool) + 1.3 (MCP Server Stdio) + 1.4 (Claude Desktop Config) + 1.5 (Verificación E2E)  
**Fecha:** 2026-04-13  
**Referencia:** `docs/plan.md`, `docs/estado-fase.md` (Fase 5)

---

## 0. Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|
| **ATG** | ✅ (26 elementos, files+lines+greps) | 8 (D1-D8) | ✅ Todas con archivo y línea | **5** |
| **Qwen** | ✅ (22 elementos, files+greps) | 7 (D1-D7) | ✅ Todas con evidencia verificable | **4** |
| **Kilo** | ✅ (18 elementos, greps) | 4 | ✅ Correctas pero menos granulares | **3** |
| **OC** | ✅ (13 elementos, greps+tests) | 5 | ✅ Básicas, conciso pero omite detalles | **3** |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `get_secret_async()` NO existe en `vault.py` pero se importa en `mcp_pool.py:26` | ATG, Kilo, OC, Qwen (4/4) | ✅ `vault.py` solo tiene `get_secret()` síncrono (L23). `mcp_pool.py:26` import roto. | Crear wrapper async con `asyncio.to_thread()` |
| 2 | `mcp>=1.0.0` NO es dependencia directa | ATG, Kilo, OC, Qwen (4/4) | ✅ `pyproject.toml:8-29` — solo transitiva vía `crewai-tools` (L32-34, opcional `[crew]`) | Agregar `"mcp>=1.0.0,<2.0.0"` a `[project.dependencies]` |
| 3 | `FlowRegistry.register()` NO acepta `description` | ATG, Kilo, OC, Qwen (4/4) | ✅ `registry.py:47-53` firma: `register(name, *, depends_on, category)`. `get_metadata()` (L96-99) retorna `{depends_on, category}` sin description. | Agregar parámetro `description: str = ""` |
| 4 | `FLOW_INPUT_SCHEMAS` solo contiene schemas `bartenders_*` | ATG, Qwen (2/4) con análisis profundo | ✅ `flows.py:70-130` — 4 keys: `bartenders_preventa/reserva/alerta/cierre`. Ningún schema para flows registrados (`generic_flow`, `architect_flow`). | Vaciar dict de bartenders; agregar schemas para flows reales si aplicable |
| 5 | `agent_catalog` RLS sin `service_role` bypass | **ATG** (1/4 — hallazgo único) | ✅ `004_agent_catalog.sql:22-23`: `org_id::text = current_setting('app.org_id', TRUE)` — NO tiene `auth.role() = 'service_role'` bypass. Patrón moderno desde mig010: `auth.role() = 'service_role' OR org_id::text = current_org_id()`. mig010 NO actualiza `agent_catalog`. | **CRÍTICA** — Crear migración `025_agent_catalog_rls_update.sql` |
| 6 | `run_full_validation()` no retorna key `"status"` — bug en `main.py:58` | **ATG** (1/4 — hallazgo único) | ✅ `main.py:58` accede `validation["status"]` pero `registry.py:187-199` retorna `{"invalid_dependencies": {...}, "cycles": [...]}`. | Bug heredado, no bloquea Sprint 1 (MCP server standalone no pasa por main.py lifespan). Documentar. |
| 7 | Scheduler bartenders no conectado al lifespan de FastAPI | ATG, Qwen (2/4) | ✅ `main.py:14-18` — no importa `bartenders_jobs`. El scheduler no arranca automáticamente. | Irrelevante para Sprint 1 — posponer refactorización |
| 8 | `python-jose` en deps pero código usa PyJWT | ATG, Qwen (2/4) | ✅ `pyproject.toml:20` vs `middleware.py:54` (`import jwt as pyjwt`). | Deuda técnica — no bloquea Sprint 1 |
| 9 | `SUPABASE_ANON_KEY` requerida por `config.py` pero no mencionada en plan de Claude Desktop config | **ATG** (1/4 — hallazgo único) | ✅ `config.py:13` — `supabase_anon_key: str = Field(...)` es requerido. Plan §1.4.1 solo menciona `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`. | Corrige plan §1.4.1 — agregar `SUPABASE_ANON_KEY` al env de `claude_desktop_config.json` |
| 10 | `health_check.py` usa `get_secret()` síncrono dentro de función async | ATG (detectó), Unificador (verificador) | ✅ `health_check.py:49` — `get_secret(org_id, secret_names[0])` dentro de `async def run_health_checks()`. | Documentado en estado-fase. Cuando `get_secret_async` exista, migrar este call. No bloquea Sprint 1. |
| 11 | `config.py:33` importa `from crewai import LLM` — crash si crewai no instalado | **ATG** (1/4 — hallazgo único, pero para pasos futuros) | ✅ `config.py:33` — import inline en `get_llm()`. El MCP server standalone podría usar `get_settings()` sin llamar `get_llm()`, por lo que no crashea. | No bloquea Sprint 1. Documentar para futuros pasos. |

### Correcciones al Plan General

| Sección del Plan | Corrección | Evidencia |
|---|---|---|
| §1.0.0.1 T2 (renombrar keys a `demo_*`) | Los flows bartenders NO están registrados en FlowRegistry — renombrar a `demo_*` crearía schemas huérfanos. **Vaciar o reemplazar** con schemas para flows reales. | `main.py:15-17` solo importa `generic_flow`, `architect_flow`, `test_flows`. `grep -rn "@register_flow.*bartenders" src/` → 0 resultados. |
| §1.0.0.1 T1 (renombrar `bartenders_jobs.py → jobs.py`) | El scheduler NO está conectado al lifespan ni importado en main.py. Renombrarlo es innecesario para Sprint 1. **Posponer.** | `grep "bartenders" src/api/main.py` → 0 resultados. |
| §1.4.1 (Claude Desktop config env) | Falta `SUPABASE_ANON_KEY` en la lista de env vars requeridas. | `config.py:13` — campo requerido sin default. |
| §1.2.1 (flow_to_tool.py usa FLOW_INPUT_SCHEMAS) | Post-desacople, el dict queda vacío o con keys de flows registrados. El edge case "schema vacío" será la norma, no la excepción. | Verificado: los 4 flows registrados (`generic_flow`, `architect_flow`, `success_test_flow`, `fail_test_flow`) NO tienen entrada en `FLOW_INPUT_SCHEMAS`. |
| Sin mención (RLS agent_catalog) | El plan NO menciona la necesidad de actualizar RLS de `agent_catalog`. Las tools `list_agents` y `get_agent_detail` fallarán silenciosamente (retornan 0 rows). | `004_agent_catalog.sql:22-23` — sin `service_role` bypass. Todas las tablas desde mig010+ lo tienen excepto `agent_catalog`. |

---

## 1. Resumen Ejecutivo

Este Sprint construye los cimientos del ecosistema agéntico MCP de FluxAgentPro-v2. El objetivo es que **Claude Desktop conecte al servidor MCP de FAP y pueda listar flows y agentes disponibles** sin ejecutar nada todavía.

El sprint incluye: (a) prerrequisitos técnicos (`get_secret_async`, dependencia `mcp` directa, enriquecimiento de FlowRegistry), (b) desacople de dominio "Bartenders NOA" del core, (c) creación del módulo `src/mcp/` con config, tools estáticas, flow-to-tool translator, y servidor Stdio, y (d) configuración y verificación E2E con Claude Desktop.

**Correcciones necesarias al plan: 5.** El plan original omitía la migración RLS de `agent_catalog` (crítica — sin ella, `list_agents` retorna vacío), no mencionaba `SUPABASE_ANON_KEY` como requerida, y asumía que renombrar schemas de bartenders a `demo_*` tendría sentido (no lo tiene — los flows no están registrados).

---

## 2. Diseño Funcional Consolidado

### Happy Path (Sprint 1 Completo)

```
1. [Pre-req] Crear migración 025 para RLS de agent_catalog (service_role bypass)
   → list_agents y get_agent_detail pueden consultar datos

2. [1.0.0.1] Desacoplar bartenders del core
   → Vaciar FLOW_INPUT_SCHEMAS de keys bartenders_*
   → Mover tools bartenders a src/tools/demo/
   → Verificar limpieza de refs en código core

3. [1.0.1] Crear get_secret_async() en vault.py
   → Import roto en mcp_pool.py:26 se resuelve
   → Base async lista para MCP server

4. [1.0.2] Agregar mcp>=1.0.0,<2.0.0 como dependencia directa
   → from mcp.server import Server funciona sin extras opcionales

5. [1.0.3] Enriquecer FlowRegistry.register() con description
   → Metadata más rica para flow-to-tool translator m

6. [1.0.4] Verificar accesibilidad de FLOW_INPUT_SCHEMAS
   → Ya verificado: NO hay dependencia circular
   → Mantener en src/api/routes/flows.py

7. [1.1] Crear estructura src/mcp/ (config.py, tools.py)
   → MCPConfig con Pydantic BaseSettings + env_prefix MCP_
   → 5 tool definitions estáticas

8. [1.2] Crear flow_to_tool.py
   → Combina FlowRegistry metadata + FLOW_INPUT_SCHEMAS
   → Genera Tool MCP por cada flow registrado

9. [1.3] Crear server.py (MCP Server Stdio)
   → Entry point: python -m src.mcp.server --org-id <UUID>
   → Registra tools estáticas + dinámicas (flow-to-tool)
   → Handlers para tools/list y tools/call

10. [1.4] Crear template claude_desktop_config.json
    → Path al venv Python + env vars completas

11. [1.5] Verificación E2E
    → Server arranca sin errors → Claude conecta → tools listadas → queries OK
```

### Edge Cases MVP

| Edge Case | Manejo |
|---|---|
| FlowRegistry vacío al arranque standalone | `server.py` importa eager los mismos módulos que `main.py:15-17` para triggear `@register_flow` |
| Flow registrado sin schema en `FLOW_INPUT_SCHEMAS` | Tool se genera con schema vacío `{"type": "object", "properties": {}}` + warning en log. **Es la norma post-desacople.** |
| `agent_catalog` vacía para la org | `list_agents` retorna `[]` — no es error. Claude informa "No hay agentes configurados" |
| `--org-id` inválido o inexistente | Server arranca pero queries retornan datos vacíos. No hay crash. |
| `SUPABASE_SERVICE_KEY` no disponible en env | Server no puede conectar a DB — tools retornan error JSON `{"error": "No se pudo conectar a la base de datos"}` como `TextContent` |
| Tool no encontrada en `tools/call` | `CallToolResult` con `isError=True` y mensaje descriptivo |

### Manejo de Errores

| Escenario | Qué ve el usuario (Claude/agente) | Tipo de error |
|---|---|---|
| Tool no encontrada | `{"error": "Tool 'xyz' not found"}` | `CallToolResult(isError=True)` |
| Supabase inaccesible | `{"error": "No se pudo conectar a la base de datos"}` | `CallToolResult(isError=True)` |
| `org_id` no proporcionado (CLI) | Proceso no arranca, error en stderr | argparse SystemExit |
| `SUPABASE_ANON_KEY` faltante | Proceso no arranca — `ValidationError` de Pydantic Settings | Crash al importar `get_settings()` |
| Flow no registrado | No se genera tool MCP para él | Silencioso — es correcto |

---

## 3. Diseño Técnico Definitivo

### 3.1 `src/db/vault.py` — Modificar (Paso 1.0.1)

**Archivo fuente:** `src/db/vault.py`  
**Función existente:** `get_secret(org_id: str, secret_name: str) -> str` (L23-61)  
**Firma verificada:** ✅

Agregar función async:

```python
async def get_secret_async(org_id: str, secret_name: str) -> str:
    """Wrapper async de get_secret() para uso en event loops MCP.

    Usa asyncio.to_thread() para no bloquear el event loop.
    Disponible desde Python 3.9 (proyecto requiere >=3.12).
    """
    import asyncio
    return await asyncio.to_thread(get_secret, org_id, secret_name)
```

- **No modifica** la función síncrona existente.
- Propaga `VaultError` tal cual.
- Resuelve el import roto en `mcp_pool.py:26`.

---

### 3.2 `pyproject.toml` — Modificar (Paso 1.0.2)

**Archivo fuente:** `pyproject.toml`  
**Sección:** `[project.dependencies]` (L8-29)

Agregar después del bloque `# LLM` (después de L25):

```toml
    # MCP Server (Phase 5)
    "mcp>=1.0.0,<2.0.0",
```

Ejecutar `uv sync` después de agregar.

> **Decisión:** Version pin con upper bound `<2.0.0` para evitar breaking changes del SDK MCP (consenso ATG, Kilo, OC, Qwen — 4/4).

---

### 3.3 `src/flows/registry.py` — Modificar (Paso 1.0.3)

**Archivo fuente:** `src/flows/registry.py`  
**Clase:** `FlowRegistry`  
**Método:** `register()` (L47-88) — Firma verificada: `register(name, *, depends_on, category)`  

Modificar firma de `register()`:

```python
def register(
    self,
    name: str | None = None,
    *,
    depends_on: Optional[List[str]] = None,
    category: Optional[str] = None,
    description: str = "",       # ← NUEVO
) -> Callable[[Type], Type]:
```

Almacenar en metadata (L75-78):

```python
self._metadata[flow_name] = {
    "depends_on": depends_on or [],
    "category": category,
    "description": description,   # ← NUEVO
}
```

Actualizar `register_flow()` (L241-248) con el mismo parámetro:

```python
def register_flow(
    name: str | None = None,
    *,
    depends_on: Optional[List[str]] = None,
    category: Optional[str] = None,
    description: str = "",       # ← NUEVO
) -> Callable[[Type], Type]:
    return flow_registry.register(
        name, depends_on=depends_on, category=category, description=description
    )
```

**No rompe código existente** — keyword-only con default vacío.

---

### 3.4 `src/api/routes/flows.py` — Modificar (Paso 1.0.0.1 T2)

**Archivo fuente:** `src/api/routes/flows.py`  
**Dict:** `FLOW_INPUT_SCHEMAS` (L70-130)

**Decisión: Vaciar el dict de schemas bartenders y dejarlo preparado para schemas futuros.**

```python
# Mapeo de flows a sus schemas de input
# Los schemas de bartenders fueron removidos en Sprint 1 (desacople).
# Para MCP, flow_to_tool.py genera tools con schema vacío si no hay entrada aquí.
FLOW_INPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {}
```

> **Justificación (ATG, score 5, evidencia de código):** Los 4 schemas de bartenders no tienen flows registrados correspondientes en FlowRegistry. Renombrarlos a `demo_*` (opción del plan) crearía schemas huérfanos. Los flows realmente registrados (`generic_flow`, `architect_flow`, `success_test_flow`, `fail_test_flow`) no tienen schemas definidos — `flow_to_tool.py` generará tools con schema vacío para ellos, lo cual es aceptable para Sprint 1 (solo consulta, no ejecución).

---

### 3.5 Desacople de Bartenders Tools (Paso 1.0.0.1 T3)

Mover `src/tools/bartenders/` → `src/tools/demo/`:

```
src/tools/demo/
├── __init__.py
├── clima_tool.py
├── escandallo_tool.py
└── inventario_tool.py
```

**Tareas:**
1. Crear directorio `src/tools/demo/`
2. Mover los 3 archivos + `__init__.py`
3. Eliminar `src/tools/bartenders/`
4. Verificar que ningún archivo core importa desde `src.tools.bartenders` (solo `bartenders_jobs.py` lo hace, y ese archivo ya no es importado por `main.py`)

**Paso 1.0.0.1 T1 (renombrar `bartenders_jobs.py`):** **POSPUESTO.** El scheduler no está conectado al lifespan ni importado en `main.py`. No afecta al MCP server. Refactorizar cuando se conecte el scheduler.

**Paso 1.0.0.1 T4 (verificar limpieza):** `grep -rn "bartenders" src/ --exclude-dir=demo --exclude-dir=crews --exclude-dir=connectors` debe retornar ≤2 resultados (solo comentarios residuales en `health_check.py:6`).

---

### 3.6 `src/mcp/config.py` — Crear (Paso 1.1.2)

```python
"""MCPConfig — Configuración del servidor MCP con Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class MCPConfig(BaseSettings):
    """Configuración del servidor MCP de FAP.

    Variables de entorno con prefijo MCP_ (ej: MCP_TRANSPORT=sse).
    CLI args (--org-id) sobreescriben los env vars.
    """
    enabled: bool = True
    transport: str = "stdio"       # stdio | sse (SSE → Sprint 4)
    host: str = "127.0.0.1"       # Solo SSE
    port: int = 8765              # Solo SSE
    require_auth: bool = False    # Sprint 3
    allowed_orgs: list[str] = []  # Vacío = todas
    org_id: str = ""              # Recibido vía --org-id CLI

    model_config = {"env_prefix": "MCP_"}
```

**Patrón:** Sigue `src/config.py` (usa `pydantic-settings>=2.6.0`, ya disponible como dependencia directa en `pyproject.toml:13`).

---

### 3.7 `src/mcp/tools.py` — Crear (Paso 1.1.3)

Define 5 tools estáticas MCP + sus handlers. Cada handler retorna `CallToolResult` con `TextContent` (JSON serializado como string).

| Tool MCP | inputSchema | Handler | Integración |
|---|---|---|---|
| `list_flows` | `{}` | `flow_registry.list_flows()` + `get_metadata()` por cada flow | `src/flows/registry.py:flow_registry` |
| `list_agents` | `{}` | Query `agent_catalog` WHERE `org_id = ? AND is_active = true` | `src/db/session.py:get_service_client()` (requiere migración 025) |
| `get_agent_detail` | `{agent_id: str}` | Query `agent_catalog` WHERE `id = ? AND org_id = ?` | `src/db/session.py:get_service_client()` |
| `get_server_time` | `{}` | `datetime.utcnow().isoformat()` | Ninguna |
| `list_capabilities` | `{}` | Dict con versión FAP, `org_id`, `transport`, `tools_count` | `MCPConfig` |

**Queries DB verificadas:**

```sql
-- list_agents
SELECT id, role, is_active, soul_json, allowed_tools, max_iter
FROM agent_catalog
WHERE org_id = :org_id AND is_active = true;

-- get_agent_detail (incluye agent_metadata si existe)
SELECT id, role, is_active, soul_json, allowed_tools, max_iter, created_at, updated_at
FROM agent_catalog
WHERE id = :agent_id AND org_id = :org_id;
```

**Columnas verificadas** contra `004_agent_catalog.sql:6-17`: `id UUID PK, org_id UUID FK, role TEXT, is_active BOOL, soul_json JSONB, allowed_tools TEXT[], max_iter INT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ`.

**Regla R3:** El output de ALL tools pasa por `sanitize_output()` (de `src/mcp/sanitizer.py`, ya existente y validado) antes de retornar al agente.

---

### 3.8 `src/mcp/flow_to_tool.py` — Crear (Paso 1.2.1)

```python
def build_flow_tools() -> list[Tool]:
    """Genera un Tool MCP por cada flow registrado en FlowRegistry.

    Combina dos fuentes:
    1. FlowRegistry.get_metadata(flow_name) → nombre, category, description, depends_on
    2. FLOW_INPUT_SCHEMAS.get(flow_name) → JSON Schema de input (vacío si no existe)
    """
    from src.flows.registry import flow_registry
    from src.api.routes.flows import FLOW_INPUT_SCHEMAS
    from mcp.types import Tool

    tools = []
    for flow_name in flow_registry.list_flows():
        meta = flow_registry.get_metadata(flow_name)
        schema = FLOW_INPUT_SCHEMAS.get(
            flow_name, {"type": "object", "properties": {}}
        )
        description = (
            meta.get("description")
            or f"Ejecutar flow de trabajo: {flow_name}"
        )

        tools.append(Tool(
            name=flow_name,
            description=description,
            inputSchema=schema,
        ))
    return tools
```

**Import de FLOW_INPUT_SCHEMAS — verificación de circular dependency:**
- Cadena: `src/mcp/flow_to_tool.py` → `src/api/routes/flows.py` → `src/flows/registry.py`
- No hay camino de vuelta (`flows/registry.py` no importa de `mcp/` ni `api/routes/`)
- **Verificado por OC (test directo) y ATG (análisis de cadena): NO hay circular dependency.**
- Si en el futuro se genera, mover `FLOW_INPUT_SCHEMAS` a `src/flows/input_schemas.py`.

---

### 3.9 `src/mcp/server.py` — Crear (Paso 1.3.1)

Entry point principal del servidor MCP. Estructura:

```python
"""MCP Server Stdio — Entry point para Claude Desktop.

Uso:
    python -m src.mcp.server --org-id "uuid-de-la-org"
"""
import argparse
import asyncio
import json
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, CallToolResult

# Eager flow registration (mismos que main.py:15-17)
import src.flows.generic_flow   # noqa: F401
import src.flows.architect_flow # noqa: F401
import src.flows.test_flows     # noqa: F401

from .config import MCPConfig
from .tools import get_static_tools, handle_tool_call
from .flow_to_tool import build_flow_tools
from ..mcp.sanitizer import sanitize_output

logger = logging.getLogger(__name__)

server = Server("FluxAgentPro-v2")
config: MCPConfig  # se asigna en main()

@server.list_tools()
async def handle_list_tools():
    """Retorna tools estáticas + dinámicas (flow-to-tool)."""
    static = get_static_tools()
    dynamic = build_flow_tools()
    return static + dynamic

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Route a handler apropiado."""
    return await handle_tool_call(name, arguments, config)

async def main():
    global config
    parser = argparse.ArgumentParser(description="FAP MCP Server")
    parser.add_argument("--org-id", required=True, help="UUID de la organización")
    args = parser.parse_args()

    config = MCPConfig(org_id=args.org_id)
    logger.info("MCP Server starting (org_id=%s, transport=%s)", config.org_id, config.transport)

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

**CLI:** `python -m src.mcp.server --org-id "uuid-de-la-org"`

> **Decisión D.3 (ATG, evidencia de código):** Los imports eager de flows (`generic_flow`, `architect_flow`, `test_flows`) son obligatorios en `server.py`. Sin ellos, el MCP server standalone tiene FlowRegistry vacío y `list_flows` retorna `[]`. Verificado: `main.py:15-17` sigue el mismo patrón.

---

### 3.10 `claude_desktop_config.json` — Crear template (Paso 1.4.1)

Template para Windows (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "FluxAgentPro-V2": {
      "command": "D:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["-m", "src.mcp.server", "--org-id", "<ORG_UUID>"],
      "env": {
        "SUPABASE_URL": "https://xxx.supabase.co",
        "SUPABASE_ANON_KEY": "<anon_key>",
        "SUPABASE_SERVICE_KEY": "<service_key>"
      }
    }
  }
}
```

> **Corrige plan §1.4.1 (hallazgo ATG):** `SUPABASE_ANON_KEY` es campo requerido sin default en `src/config.py:13`. Sin ella, `get_settings()` lanza `ValidationError` y el server no arranca.

---

### 3.11 `supabase/migrations/025_agent_catalog_rls_update.sql` — Crear (Corrección D1)

```sql
-- ============================================================
-- Migration 025: Update agent_catalog RLS to modern pattern
--   Adds service_role bypass (consistent with mig010+)
--   Required for MCP server tools (list_agents, get_agent_detail)
-- ============================================================

-- Drop old policy (mig004 pattern: current_setting without service_role bypass)
DROP POLICY IF EXISTS "agent_catalog_tenant_isolation" ON agent_catalog;

-- Recreate with modern pattern (mig010+)
CREATE POLICY "agent_catalog_tenant_isolation" ON agent_catalog
    FOR ALL USING (
        auth.role() = 'service_role'
        OR org_id::text = current_org_id()
    );
```

> **Hallazgo exclusivo de ATG (score 5).** Sin esta migración, las queries `list_agents` y `get_agent_detail` retornan 0 rows cuando se usan con `get_service_client()` (service_role). Todas las tablas desde mig010+ tienen este patrón EXCEPTO `agent_catalog` (mig004, pre-010). **Probabilidad de fallo: 100% sin fix.**

---

### 3.12 Componentes Existentes que NO se Modifican

- `src/api/middleware.py` — Auth no se toca (Sprint 3)
- `src/tools/mcp_pool.py` — Cliente MCP, no se modifica (pero su import roto de `get_secret_async` se resuelve con paso 1.0.1)
- `src/mcp/sanitizer.py` — Ya implementado (Paso 5.2.5), se reutiliza en handlers
- `src/mcp/__init__.py` — Ya existe, actualizar imports de conveniencia si necesario
- `src/api/main.py` — El MCP server es standalone, no pasa por FastAPI lifespan

---

## 4. Decisiones Tecnológicas

| # | Decisión | Justificación | Fuente |
|---|---|---|---|
| D1 | **Migración 025 para RLS de `agent_catalog`** | Es la ÚNICA tabla core sin `service_role` bypass (mig004, pre-010). Queries MCP retornarían vacío sin fix. | ATG (hallazgo exclusivo, verificado L22-23 de 004_agent_catalog.sql). **Corrige plan — no mencionado.** |
| D2 | **Vaciar `FLOW_INPUT_SCHEMAS`** (no renombrar a `demo_*`) | Los flows bartenders NO están registrados en FlowRegistry. Renombrar crearía schemas huérfanos. Los 4 flows registrados no tienen schemas definidos. | ATG (evidencia: grep `@register_flow.*bartenders` → 0 resultados, `main.py:15-17`). **Corrige plan §1.0.0.1 T2.** |
| D3 | **Importar flows eager en `server.py`** | El MCP server es standalone — sin los imports eager, FlowRegistry está vacío. | ATG + Qwen (evidencia: main.py:15-17 como patrón idéntico). |
| D4 | **`get_secret_async` con `asyncio.to_thread()`** | Consenso 4/4 agentes. Simple, no bloquea event loop. Python 3.12+ garantizado. | ATG, Kilo, OC, Qwen (consenso unánime). |
| D5 | **`mcp>=1.0.0,<2.0.0`** (version pinning) | Consenso 3/4 agentes (ATG dice `>=1.0.0` sin upper bound). SDK nuevo — upper bound previene breaking changes. | ATG, Kilo, OC, Qwen. Adoptamos upper bound por precaución. |
| D6 | **Posponer refactorización del scheduler bartenders** | No está conectado al lifespan. No afecta MCP server. | ATG D.6 (evidencia: grep scheduler main.py → 0 resultados). |
| D7 | **`SUPABASE_ANON_KEY` requerida en Claude Desktop config** | `config.py:13` campo requerido sin default. | ATG D.5 (hallazgo exclusivo). **Corrige plan §1.4.1.** |
| D8 | **`get_service_client()` para queries de tools MCP** | Coherente con patrón existente. Service role bypasea RLS (tras D1). El `org_id` se filtra explícitamente en query `.eq("org_id", config.org_id)`. | ATG D.4, Qwen D6. |
| D9 | **No hay decisiones nuevas sobre stack** | Todo coherente con `docs/estado-fase.md`. Mismas dependencias (pydantic-settings, httpx, structlog), mismos patrones (RLS, decoradores, client). | Verificado contra estado-fase.md §3 y §4. |

---

## 5. Criterios de Aceptación MVP ✅

> [!IMPORTANT]
> El Validador usará EXACTAMENTE esta lista para aprobar o rechazar la implementación.

### Funcionales

| # | Criterio | Paso | Verificación |
|---|---|---|---|
| CA1 | Claude Desktop muestra ≥5 tools de FAP tras reinicio | 1.5.2 | Visual: ícono MCP tools en chat |
| CA2 | `list_flows` retorna ≥3 flows registrados como JSON válido | 1.5.3 | Pregunta a Claude: "¿Qué flows están disponibles?" |
| CA3 | `list_agents` retorna datos de `agent_catalog` para la org (o `[]` si vacía) | 1.5.4 | Pregunta a Claude: "¿Qué agentes tiene esta org?" |
| CA4 | `get_agent_detail` acepta `agent_id` y retorna `soul_json`, `allowed_tools` | 1.5.5 | Pregunta a Claude sobre un agente específico |
| CA5 | `get_server_time` retorna timestamp UTC válido | 1.5 | Pregunta a Claude: "¿Qué hora tiene el servidor?" |
| CA6 | `list_capabilities` retorna metadata (version, org_id, transport, tools_count) | 1.5 | Pregunta a Claude: "¿Cuáles son las capacidades del servidor?" |

### Técnicos

| # | Criterio | Paso | Verificación |
|---|---|---|---|
| CA7 | `python -c "from mcp.types import Tool; print('OK')"` ejecuta sin error (sin extras `[crew]`) | 1.0.2 | Comando CLI |
| CA8 | `get_secret_async` está definida en `vault.py` y es callable async | 1.0.1 | `grep -n "async def get_secret_async" src/db/vault.py` → ≥1 resultado |
| CA9 | `from src.db.vault import get_secret_async` no lanza `ImportError` | 1.0.1 | Comando Python |
| CA10 | `flow_registry.register("x", description="test")` no lanza error | 1.0.3 | Script de test |
| CA11 | `flow_registry.get_metadata("x")` retorna dict con key `description` | 1.0.3 | Script de test |
| CA12 | `from src.api.routes.flows import FLOW_INPUT_SCHEMAS` funciona sin import circular | 1.0.4 | Comando Python |
| CA13 | `FLOW_INPUT_SCHEMAS` no contiene keys con prefijo `bartenders_` | 1.0.0.1 | `grep "bartenders_" src/api/routes/flows.py` →  0 resultados en keys del dict |
| CA14 | `src/mcp/config.py` existe y `MCPConfig(org_id="test")` instancia correctamente | 1.1.2 | Comando Python |
| CA15 | `python -m src.mcp.server --org-id test --help` muestra opciones sin error de import | 1.3.1 | Comando CLI |
| CA16 | Migración `025_agent_catalog_rls_update.sql` aplicada | Pre-req | Verificar en DB |
| CA17 | Output de todas las tools pasa por `sanitize_output()` antes de retornar | 1.1.3 | Revisión de código |
| CA18 | `SUPABASE_ANON_KEY` documentada como requerida en `claude_desktop_config.json` template | 1.4.1 | Lectura del template |

### Robustez

| # | Criterio | Paso | Verificación |
|---|---|---|---|
| CA19 | Si Supabase es inaccesible, tools retornan error JSON sin crash del server | 1.1.3 | Prueba con env vars incorrectas |
| CA20 | Si se invoca tool inexistente en `tools/call`, retorna `CallToolResult(isError=True)` sin crash | 1.3.1 | Prueba con tool ficticia |
| CA21 | Todas las respuestas son `TextContent` con JSON parseable | 1.1.3 | Parsear cada response |

---

## 6. Plan de Implementación

| # | Tarea | Paso | Complejidad | Tiempo Est. | Dependencia | ⚠️ Corrige plan |
|---|---|---|---|---|---|---|
| T1 | Crear migración `025_agent_catalog_rls_update.sql` | Pre-req (D1) | Baja | 15 min | Ninguna | ✅ Plan no mencionaba |
| T2 | Vaciar `FLOW_INPUT_SCHEMAS` (quitar schemas bartenders) | 1.0.0.1 T2 | Baja | 15 min | Ninguna | ✅ Vaciar en vez de renombrar |
| T3 | Mover tools bartenders a `src/tools/demo/` | 1.0.0.1 T3 | Baja | 15 min | Ninguna | — |
| T4 | Verificar limpieza: grep bartenders en src core | 1.0.0.1 T4 | Baja | 10 min | T2, T3 | — |
| T5 | Crear `get_secret_async()` en `vault.py` | 1.0.1 | Baja | 20 min | Ninguna | — |
| T6 | Agregar `mcp>=1.0.0,<2.0.0` en `pyproject.toml` + `uv sync` | 1.0.2 | Baja | 15 min | Ninguna | — |
| T7 | Agregar `description` a `FlowRegistry.register()` + `register_flow()` | 1.0.3 | Baja | 30 min | Ninguna | — |
| T8 | Verificar importabilidad de `FLOW_INPUT_SCHEMAS` sin circular deps | 1.0.4 | Baja | 10 min | T2 | — |
| T9 | Crear `src/mcp/config.py` con MCPConfig | 1.1.2 | Baja | 20 min | T6 | — |
| T10 | Crear `src/mcp/tools.py` con 5 tool definitions + handlers | 1.1.3 | Media | 1.5h | T1, T5, T9 | — |
| T11 | Crear `src/mcp/flow_to_tool.py` | 1.2.1 | Media | 45 min | T7, T8 | — |
| T12 | Crear `src/mcp/server.py` (entry point stdio) | 1.3.1 | Alta | 2h | T9, T10, T11 | — |
| T13 | Crear template `claude_desktop_config.json` en repo root | 1.4.1 | Baja | 15 min | T12 | ✅ Agregar SUPABASE_ANON_KEY |
| T14 | Verificación E2E: servidor arranca, Claude conecta, tools funcionan | 1.5 | Media | 45 min | T12, T13, T1 (mig aplicada) | — |

### Orden de Ejecución Recomendado

```
[Paralelo] T1, T2, T3, T5, T6, T7
     ↓
[Verificar] T4 (limpieza bartenders), T8 (import circular)
     ↓
[Secuencial] T9 → T10 → T11 → T12
     ↓
[Secuencial] T13 → T14
```

**Tiempo total estimado: 7-8 horas**

---

## 7. Riesgos y Mitigaciones

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | **`agent_catalog` RLS bloquea queries** — Sin migración 025, `list_agents` retorna vacío | Alta (100% sin fix) | Alto | Migración 025 como **primer paso** de implementación |
| R2 | **SDK `mcp` API surface diferente a la esperada** | Media | Alto | Verificar `pip show mcp` y leer API docs/source **antes** de escribir server.py |
| R3 | **FlowRegistry vacío en server standalone** | Alta (100% sin eagr imports) | Medio | Incluir imports eager en server.py (mismos que main.py:15-17) |
| R4 | **`SUPABASE_ANON_KEY` faltante** — `get_settings()` lanza `ValidationError` | Media | Alto | Documentar en template de Claude Desktop config. Alternativa: crear MCPSettings separado que no requiera ANON_KEY |
| R5 | **Claude Desktop no detecta el server** — Path al Python incorrecto | Media | Alto | Template de config con paths verificados. Documentar troubleshooting vía `%APPDATA%\Claude\logs\` |
| R6 | **Desacople de bartenders rompe tests existentes** | Media | Medio | Verificar `tests/` antes del desacople. Mover tests junto con el código si existen |
| R7 | **`main.py:58` KeyError "status"** — Bug heredado | Baja (no bloquea Sprint 1) | Bajo | Documentar. El MCP server no pasa por lifespan de FastAPI |
| R8 | **Implementador copia plan sin aplicar correcciones** | Media | Alto | **5 correcciones al plan documentadas arriba con ⚠️.** El implementador DEBE leer este documento, no el plan original, para: RLS agent_catalog, SUPABASE_ANON_KEY, vaciado de FLOW_INPUT_SCHEMAS |

---

## 8. Testing Mínimo Viable

Alineado 1:1 con criterios de aceptación:

| Test | Corresponde a | Método |
|---|---|---|
| `python -c "from mcp.types import Tool; print('OK')"` → OK sin extras | CA7 | CLI |
| `python -c "from src.db.vault import get_secret_async; print('OK')"` → OK | CA8, CA9 | CLI |
| Script que registra un flow con description y verifica metadata | CA10, CA11 | Script Python |
| `python -c "from src.api.routes.flows import FLOW_INPUT_SCHEMAS; print(len(FLOW_INPUT_SCHEMAS))"` → 0 | CA12, CA13 | CLI |
| `python -c "from src.mcp.config import MCPConfig; print(MCPConfig(org_id='test').transport)"` → `stdio` | CA14 | CLI |
| `python -m src.mcp.server --help` → sin error de import | CA15 | CLI |
| Migración 025 aplicada en Supabase | CA16 | Verificar en dashboard Supabase |
| Reiniciar Claude Desktop → ícono MCP tools visible | CA1 | Visual |
| Preguntar a Claude "¿Qué flows están disponibles?" → JSON con ≥3 flows | CA2 | Claude Chat |
| Preguntar a Claude "¿Qué agentes hay?" → JSON (lista o vacía) | CA3 | Claude Chat |
| Preguntar a Claude sobre un agente → detalles con soul_json | CA4 | Claude Chat |
| Verificar que output contiene solo texto sanitizado (sin tokens/secrets) | CA17 | Revisión de respuestas |

---

## 🔮 9. Roadmap (NO implementar ahora)

### Post-Sprint 1 (limpieza)
- **Refactorización del scheduler:** Renombrar `bartenders_jobs.py → jobs.py`, conectar al lifespan de FastAPI, integrar `health_check.py` como job.
- **Fix `run_full_validation()` retorno:** Agregar key `"status"` al retorno de `FlowRegistry.run_full_validation()` para resolver el bug heredado en `main.py:58`.
- **Eliminar `python-jose` de dependencias:** El código usa `PyJWT` exclusivamente. `python-jose` es peso muerto.
- **Schemas para flows genéricos:** Definir `FLOW_INPUT_SCHEMAS` entries para `generic_flow` (schema: `{text: string}`) y `architect_flow` (schema: `{prompt: string}`).
- **Migrar `health_check.py` a `get_secret_async`:** L49 usa síncrono dentro de async.

### Sprint 3 (Auth Bridge + Ejecución)
- `require_auth = true` en MCPConfig.
- Auth Bridge con PyJWT: verificar JWT del agente, mapear identidad → `user_id` de FAP (necesita "service account" o "agent user" en `org_members`).
- `execute_flow` handler — requiere `BaseFlow(org_id, user_id)`. El MCP server no tiene `user_id` en Sprint 1.
- Excepciones MCP → JSON-RPC error codes estándar.
- `config.py:33` (`from crewai import LLM`): proteger contra `ImportError` en entornos sin extras `[crew]`.

### Sprint 4 (SSE + HITL)
- Transport SSE (MCPConfig ya incluye `host` y `port`).
- `approve_task` / `reject_task` handlers.
- Inputs complejos (imágenes, archivos).

---

*Documento generado por el proceso de UNIFICACIÓN — 4 análisis consolidados (ATG score 5, Qwen 4, Kilo 3, OC 3). 11 discrepancias documentadas. 5 correcciones al plan general. 21 criterios de aceptación binarios.*
