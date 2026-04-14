# 🧠 Análisis Técnico — Sprint 1: Prerrequisitos + MCP Server Básico
## Agente: ATG | Paso: 1 (completo: 1.0 → 1.5)

**Fecha:** 2026-04-13
**Alcance:** 8-10 archivos afectados → Umbral mínimo §0: ≥18 elementos
**Referencia de fase:** `docs/estado-fase.md` (Fase 5 — Ecosistema Agéntico MCP)

---

## §0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `get_secret()` existe como función síncrona en `vault.py` | `view_file src/db/vault.py` | ✅ | L23: `def get_secret(org_id: str, secret_name: str) -> str` |
| 2 | `get_secret_async` NO existe en `vault.py` | `grep get_secret_async src/db/vault.py` → 0 resultados | ✅ | Solo existe `get_secret` síncrono. Confirmado que falta. |
| 3 | `get_secret_async` se importa en `mcp_pool.py` | `mcp_pool.py:26` | ✅ | `from ..db.vault import get_secret_async` — import ROTO (ImportError en runtime) |
| 4 | `mcp>=1.0.0` NO es dependencia directa | `pyproject.toml:8-29` | ✅ | Solo disponible transitiva vía `crewai-tools` (L32-34, opcional `[crew]`) |
| 5 | `FlowRegistry.register()` NO acepta `description` | `registry.py:47-53` | ✅ | Firma: `register(self, name, *, depends_on, category)` — sin parámetro `description` |
| 6 | `FlowRegistry.get_metadata()` retorna `{depends_on, category}` | `registry.py:96-99` | ✅ | Default: `{"depends_on": [], "category": None}` — sin `description` |
| 7 | `FLOW_INPUT_SCHEMAS` está en `src/api/routes/flows.py:70-130` | Lectura directa | ✅ | Dict con 4 keys: `bartenders_preventa`, `bartenders_reserva`, `bartenders_alerta`, `bartenders_cierre` |
| 8 | `FLOW_INPUT_SCHEMAS` sólo se referencia dentro de `flows.py` | `grep FLOW_INPUT_SCHEMAS src/` | ✅ | 2 refs, ambas en `flows.py:70` y `flows.py:149`. No exportado a otros módulos. |
| 9 | `src/mcp/` existe con `__init__.py` y `sanitizer.py` | `list_dir src/mcp/` | ✅ | 2 archivos. **No existen** `server.py`, `config.py`, `tools.py`, `flow_to_tool.py` |
| 10 | `agent_catalog` tabla existe | `004_agent_catalog.sql` | ✅ | Columnas: `id UUID PK, org_id UUID FK, role TEXT, is_active BOOL, soul_json JSONB, allowed_tools TEXT[], max_iter INT` |
| 11 | `agent_catalog` RLS NO tiene `service_role` bypass | `004_agent_catalog.sql:22-23` | ❌ | Policy: `org_id::text = current_setting('app.org_id', TRUE)` — usa `current_setting` directo (NO `current_org_id()`), y **NO** tiene `auth.role() = 'service_role'` bypass. El MCP server usa `service_role` → NO podrá leer `agent_catalog` sin setear `app.org_id`. |
| 12 | Patrón RLS moderno con `service_role` bypass | `010_service_role_rls_bypass.sql` + `024_service_catalog.sql` | ✅ | Patrón estándar desde mig010: `auth.role() = 'service_role' OR org_id::text = current_org_id()`. **`agent_catalog` (mig004) NO fue actualizada a este patrón.** |
| 13 | `scheduler` global en `bartenders_jobs.py` | `bartenders_jobs.py:31` | ✅ | `scheduler = AsyncIOScheduler(timezone="America/Argentina/Tucuman")` — instancia global domain-specific |
| 14 | `scheduler` NO importado en `main.py` | `grep scheduler src/api/main.py` → 0 resultados | ✅ | El scheduler de `bartenders_jobs.py` no está conectado al lifespan de FastAPI |
| 15 | `main.py` NO importa `bartenders_jobs` | `grep bartenders src/api/main.py` → 0 resultados | ✅ | No hay referencia alguna al scheduler de bartenders en el entrypoint |
| 16 | Flows registrados al arranque: `generic_flow`, `architect_flow`, `test_flows` | `main.py:15-17` | ✅ | 3 imports eager. Ningún flow de bartenders registrado — los flows bartenders se registrarían desde `src/crews/bartenders/` si se importaran, pero no se importan. |
| 17 | `FLOW_INPUT_SCHEMAS` tiene SOLO schemas de bartenders | `flows.py:70-130` | ❌ | Las 4 keys son `bartenders_*`. Ningún schema genérico. Tras desacople (T2), el dict quedaría vacío — `flow_to_tool.py` no tendrá schemas para los flows realmente registrados (`generic_flow`, `architect_flow`, etc.). |
| 18 | `bartenders_jobs.py` importa de `src.crews.bartenders` y `src.connectors` | `bartenders_jobs.py:114-115` | ✅ | `from src.crews.bartenders.cierre_crews import _actualizar_precios` + `from src.connectors.supabase_connector import SupabaseMockConnector` |
| 19 | Tools de bartenders en `src/tools/bartenders/` | `list_dir` | ✅ | 3 tools: `clima_tool.py`, `escandallo_tool.py`, `inventario_tool.py` + `__init__.py` |
| 20 | `pydantic-settings>=2.6.0` disponible | `pyproject.toml:13` | ✅ | Necesario para `MCPConfig(BaseSettings)` |
| 21 | `httpx>=0.28.0` disponible como dependencia directa | `pyproject.toml:23` | ✅ | Disponible para health checks y service connector |
| 22 | `agents` endpoint existente en `src/api/routes/agents.py` | `main.py:30` + router registrado L95 | ✅ | Existe ruta para consultar agentes (patrón de referencia para tool `list_agents`) |
| 23 | `structlog` disponible como dep directa | `pyproject.toml:24` | ✅ | `structlog>=24.4.0` — usar para logging del MCP server |
| 24 | Python `>=3.12` requerido | `pyproject.toml:6` | ✅ | `asyncio.to_thread()` disponible desde 3.9 — OK |
| 25 | `flow_registry.run_full_validation()` retorna dict con key `status` | `main.py:58` | ❌ | `main.py:58` accede `validation["status"]` pero `run_full_validation()` (registry.py:187-199) retorna `{"invalid_dependencies": {...}, "cycles": [...]}` — **no tiene key "status"**. Bug heredado, no bloquea Sprint 1 pero causa `KeyError` al arrancar. |
| 26 | `python-jose` en deps pero código usa `PyJWT` | `pyproject.toml:20` vs `middleware.py:54` | ⚠️ | Discrepancia documentada en estado-fase. No bloquea Sprint 1. |

**Total verificados: 26/18 mínimo** ✅

### Discrepancias encontradas:

**D1 — `agent_catalog` RLS sin `service_role` bypass (CRÍTICA)**
- **Plan:** Sprint 1 tools `list_agents` y `get_agent_detail` hacen queries a `agent_catalog`.
- **Código:** La política RLS de `agent_catalog` (mig004) usa `current_setting('app.org_id', TRUE)` SIN bypass de `service_role`. El MCP server usará `get_service_client()` (service_role key) → las queries retornarán **0 rows** a menos que se setee `app.org_id` vía `set_config` RPC.
- **Resolución:** Dos opciones:
  1. **(Recomendada)** Crear migración `025_agent_catalog_rls_update.sql` que actualice la policy al patrón moderno: `auth.role() = 'service_role' OR org_id::text = current_org_id()`. Consistente con mig010, mig020, mig024.
  2. **(Alternativa)** Usar `TenantClient` con `set_config(org_id)` antes de consultar. Pero esto agrega complejidad al handler MCP y es inconsistente con otros componentes que ya tienen `service_role` bypass.

**D2 — `FLOW_INPUT_SCHEMAS` solo contiene schemas de bartenders**
- **Plan:** El paso 1.0.0.1 desacopla bartenders renombrando o vaciando `FLOW_INPUT_SCHEMAS`. El paso 1.2 usa `FLOW_INPUT_SCHEMAS` como fuente para `flow_to_tool.py`.
- **Código:** Las 4 keys son `bartenders_*`. Los flows realmente registrados al arranque (`generic_flow`, `architect_flow`, `success_test_flow`, `fail_test_flow`, `multi_crew`) NO tienen entrada en este dict.
- **Resolución:** Tras el desacople de T2, agregar al menos un schema genérico para los flows registrados, o aceptar que `flow_to_tool.py` genere tools con schema vacío `{"type": "object", "properties": {}}` para flows sin schema definido (ya contemplado como edge case en plan §1.2.1).

**D3 — `FlowRegistry.run_full_validation()` no retorna key `status`**
- **Plan/Código:** `main.py:58` accede `validation["status"]` pero el método retorna `{"invalid_dependencies": {...}, "cycles": [...]}`.
- **Resolución:** Bug heredado — no bloquea Sprint 1. Documentar para corrección posterior. Mencionado porque al arrancar el server MCP standalone, este bug no se manifiesta (el server MCP no pasa por `main.py` lifespan). Pero SÍ afecta al arranque normal de FastAPI.

**D4 — `agent_catalog` RLS usa `current_setting()` directamente en vez de `current_org_id()`**
- **Plan:** El patrón estándar desde mig010+ es `current_org_id()` (wrapper helper).
- **Código:** `agent_catalog` (mig004, pre-010) usa `current_setting('app.org_id', TRUE)` directamente.
- **Resolución:** La migración 025 propuesta en D1 debe usar `current_org_id()` por consistencia.

**D5 — No existe ningún flow de bartenders registrado en FlowRegistry al arranque**
- **Plan:** El paso 1.0.0.1 asume que hay flows bartenders registrados que deben desacoplarse.
- **Código:** Ningún flow de bartenders se registra vía `@register_flow`. Los imports de `main.py` solo importan `generic_flow`, `architect_flow`, `test_flows`. Los bartenders existen como crews, no como flows registrados.
- **Resolución:** El desacople T2 del paso 1.0.0.1 (renombrar keys en `FLOW_INPUT_SCHEMAS`) es conceptualmente correcto — esos schemas existen aunque no haya flows registrados con esos nombres. Simplificar: vaciar `FLOW_INPUT_SCHEMAS` o reemplazar con schemas para los flows que SÍ están registrados.

**D6 — Scheduler de bartenders no está conectado al lifespan de FastAPI**
- **Plan:** El paso 1.0.0.1 dice renombrar `bartenders_jobs.py → jobs.py`.
- **Código:** El scheduler NO está importado en `main.py` ni conectado al lifespan. Renombrarlo es trivial pero innecesario si el scheduler no se usa. El `health_check.py` tampoco está conectado.
- **Resolución:** Para Sprint 1, el scheduler de bartenders es irrelevante. El MCP server no necesita scheduler. Posponer la refactorización del scheduler al momento en que se conecte al lifespan.

**D7 — `mcp_pool.py` importa `StdioServerParameters` de `mcp` pero el plan crea un MCP SERVER, no cliente**
- **Plan:** Sprint 1 crea un MCP Server Stdio.
- **Código:** `mcp_pool.py:150` importa `from mcp import StdioServerParameters` — esto es para MCPPool como CLIENTE de servidores MCP externos. El MCP Server que crearemos usará `from mcp.server import Server` (API del SDK para crear servidores).
- **Resolución:** No genera conflicto. Solo es importante notar que hay dos usos del paquete `mcp`: como cliente (MCPPool, existente) y como servidor (Sprint 1, nuevo). Ambos coexisten sin problemas.

**D8 — `health_check.py` usa `get_secret()` síncrono dentro de función async**
- **Código:** `health_check.py` define `run_health_checks()` como `async` pero usa operaciones que podrían necesitar `get_secret()` síncrono.
- **Resolución:** Documentado en `estado-fase.md`. No bloquea Sprint 1, pero es relevante como antecedente de por qué `get_secret_async` es necesario.

---

## §1. Diseño Funcional

### Happy Path Completo (Pasos 1.0 → 1.5)

```
1. [1.0.0.1] Desacoplar bartenders del core
   → FLOW_INPUT_SCHEMAS limpio de refs bartenders
   → tools bartenders movidos a src/tools/demo/
   → scheduler bartenders renombrado o aislado
   
2. [1.0.1] Crear get_secret_async() en vault.py
   → MCPPool ya no tiene import roto
   → Base async lista para MCP server

3. [1.0.2] Agregar mcp>=1.0.0 como dependencia directa
   → `from mcp.server import Server` funciona sin extras opcionales

4. [1.0.3] Enriquecer FlowRegistry.register() con description
   → Metadata más rica para flow-to-tool translator

5. [1.0.4] Verificar accesibilidad de FLOW_INPUT_SCHEMAS
   → Confirmar que se puede importar sin circular dependency
   → Si hay circular: mover a src/flows/input_schemas.py

6. [1.1] Crear estructura src/mcp/ (config.py, tools.py)
   → Config con Pydantic BaseSettings + env_prefix MCP_
   → Tool definitions estáticas (list_flows, list_agents, etc.)

7. [1.2] Crear flow_to_tool.py
   → Combina FlowRegistry metadata + FLOW_INPUT_SCHEMAS
   → Genera Tool MCP por cada flow registrado

8. [1.3] Crear server.py (MCP Server Stdio)
   → Entry point: python -m src.mcp.server --org-id <UUID>
   → Registra tools estáticas + dinámicas
   → Handlers para tools/list y tools/call

9. [1.4] Configurar Claude Desktop
   → claude_desktop_config.json con path al venv Python

10. [1.5] Verificación E2E
    → Claude Desktop conecta → lista tools → ejecuta queries
```

### Edge Cases MVP

1. **FlowRegistry vacío al arranque standalone:** El MCP server arranca con `python -m src.mcp.server`, NO pasa por `main.py` lifespan. Los eager imports de flows (`generic_flow`, etc.) no se ejecutan → FlowRegistry vacío.
   - **Resolución:** En `server.py`, importar los mismos módulos que `main.py:15-17` antes de iniciar el servidor. O importar `flow_registry` después de triggear los registros.

2. **`agent_catalog` vacía para la org:** `list_agents` retorna lista vacía → El LLM recibe `[]`. OK para MVP, Claude puede informar "No hay agentes configurados".

3. **`FLOW_INPUT_SCHEMAS` vacío post-desacople:** `flow_to_tool.py` genera tools con schema vacío → Claude puede invocar el flow pero sin guía de parámetros. Aceptable para MVP.

4. **`--org-id` inválido o inexistente:** El servidor arranca normalmente pero queries retornan datos vacíos. No hay crash.

### Manejo de Errores

| Escenario | Comportamiento | Código HTTP/MCP |
|---|---|---|
| Tool no encontrada en `tools/call` | `CallToolResult` con `isError=True`, mensaje descriptivo | Error JSON-RPC estándar |
| Supabase inaccesible | Catch exception, retornar TextContent con error sanitizado | `CallToolResult(isError=True)` |
| `org_id` no proporcionado | Argparse error al iniciar, stderr | Proceso no arranca |
| Flow no registrado en FlowRegistry | `flow_to_tool.py` simplemente no genera tool para él | N/A (silencioso) |

---

## §2. Diseño Técnico

### 2.1 Componentes Nuevos

#### `src/db/vault.py` — Modificar (Paso 1.0.1)
Agregar función:
```python
async def get_secret_async(org_id: str, secret_name: str) -> str:
    """Async wrapper around get_secret() using asyncio.to_thread()."""
    import asyncio
    return await asyncio.to_thread(get_secret, org_id, secret_name)
```
- Firma idéntica a `get_secret` pero async.
- `asyncio.to_thread()` disponible desde Python 3.9 (proyecto requiere ≥3.12).
- No modifica la función síncrona existente.

#### `pyproject.toml` — Modificar (Paso 1.0.2)
Agregar en `[project.dependencies]`:
```toml
"mcp>=1.0.0",
```
Posición recomendada: después del bloque `# LLM`, antes de `# Auth`.

#### `src/flows/registry.py` — Modificar (Paso 1.0.3)
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
Almacenar en metadata:
```python
self._metadata[flow_name] = {
    "depends_on": depends_on or [],
    "category": category,
    "description": description,   # ← NUEVO
}
```
Actualizar `register_flow()` convenience decorator con el mismo parámetro.
**No rompe código existente** — parámetro keyword-only con default vacío.

#### `src/mcp/config.py` — Crear (Paso 1.1.2)
```python
from pydantic_settings import BaseSettings

class MCPConfig(BaseSettings):
    enabled: bool = True
    transport: str = "stdio"
    host: str = "127.0.0.1"       # SSE only (Sprint 4)
    port: int = 8765              # SSE only (Sprint 4)
    require_auth: bool = False    # Sprint 3
    allowed_orgs: list[str] = []
    org_id: str = ""              # Recibido vía --org-id CLI

    model_config = {"env_prefix": "MCP_"}
```
Patrón: sigue `src/config.py` (usa `pydantic-settings`).

#### `src/mcp/tools.py` — Crear (Paso 1.1.3)
Define 5 tools estáticas MCP. Cada una como instancia de `mcp.types.Tool`:
- `list_flows` — Llama `flow_registry.list_flows()` + `get_metadata()`
- `list_agents` — Query `agent_catalog` filtrado por `org_id` (requiere D1 resuelto)
- `get_agent_detail` — Query `agent_catalog` por `agent_id`
- `get_server_time` — `datetime.utcnow().isoformat()`
- `list_capabilities` — Metadata del servidor (versión, org_id, transport, tool count)

Cada handler retorna `CallToolResult` con `TextContent` (JSON serializado como string).
Pasar output por `sanitize_output()` antes de retornar (Regla R3).

#### `src/mcp/flow_to_tool.py` — Crear (Paso 1.2.1)
```python
def flows_to_mcp_tools() -> list[Tool]:
    """Genera Tool MCP por cada flow registrado en FlowRegistry."""
```
Combina dos fuentes:
1. `flow_registry.list_flows()` + `flow_registry.get_metadata(flow_name)` → nombre, categoría, descripción, dependencias.
2. `FLOW_INPUT_SCHEMAS.get(flow_name, {"type": "object", "properties": {}})` → JSON Schema de input.

**Import de FLOW_INPUT_SCHEMAS:** Importar desde `src.api.routes.flows`. **Riesgo de circular dependency** evaluado: `flow_to_tool.py` (en `src/mcp/`) importa de `src/api/routes/flows.py` que importa de `src/flows/registry.py`. La cadena es `mcp → api.routes → flows`. No hay camino de vuelta `flows → mcp`, por lo que NO hay circular dependency.

Si por alguna razón futura se genera una, mover `FLOW_INPUT_SCHEMAS` a `src/flows/input_schemas.py`.

#### `src/mcp/server.py` — Crear (Paso 1.3.1)
Entry point principal. Estructura:
```python
import argparse
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Eager flow registration (mismos que main.py)
import src.flows.generic_flow
import src.flows.architect_flow
import src.flows.test_flows

server = Server("FluxAgentPro-v2")

@server.list_tools()
async def handle_list_tools():
    # Combinar tools estáticas + dinámicas (flow_to_tool)
    ...

@server.call_tool()
async def handle_call_tool(name, arguments):
    # Route a handler apropiado
    ...

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--org-id", required=True)
    args = parser.parse_args()
    # Guardar org_id en MCPConfig
    async with stdio_server() as (read, write):
        await server.run(read, write, ...)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**CLI:** `python -m src.mcp.server --org-id "uuid-de-la-org"`

#### `claude_desktop_config.json` — Crear/Documentar (Paso 1.4.1)
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
**Nota:** `SUPABASE_ANON_KEY` también necesaria — `get_settings()` en `config.py:13` lo requiere como campo obligatorio. No documentado en el plan original.

#### `supabase/migrations/025_agent_catalog_rls_update.sql` — Crear (Corrección D1)
```sql
-- Actualizar RLS de agent_catalog al patrón moderno (service_role bypass)
DROP POLICY IF EXISTS "agent_catalog_tenant_isolation" ON agent_catalog;
CREATE POLICY "agent_catalog_tenant_isolation" ON agent_catalog
    FOR ALL USING (
        auth.role() = 'service_role'
        OR org_id::text = current_org_id()
    );
```

### 2.2 Componentes Existentes que NO se Modifican (Sprint 1)

- `src/api/middleware.py` — Auth no se toca (Sprint 3)
- `src/tools/mcp_pool.py` — Cliente MCP, no se modifica (pero su import roto de `get_secret_async` se resuelve con paso 1.0.1)
- `src/mcp/sanitizer.py` — Ya implementado, se reutiliza en handlers
- `src/api/main.py` — El MCP server es standalone, no pasa por FastAPI

### 2.3 Modelo de Datos

No se crean tablas nuevas excepto la migración de corrección RLS (025). Se consultan:
- `agent_catalog` — Para `list_agents` y `get_agent_detail` (queries con `service_role` client tras D1)
- `agent_metadata` — Opcionalmente para enriquecer `get_agent_detail` con `display_name` y `soul_narrative`

---

## §3. Decisiones

| # | Decisión | Justificación |
|---|---|---|
| D.1 | **Migración 025 para RLS de `agent_catalog`** — actualizar al patrón `service_role` bypass | `agent_catalog` (mig004) es la ÚNICA tabla core sin `service_role` bypass. Todas las tablas desde mig010+ lo tienen. El MCP server usa `get_service_client()` → sin bypass, las queries retornan vacío. Corrige plan implícito. |
| D.2 | **Simplificar paso 1.0.0.1** — vaciar `FLOW_INPUT_SCHEMAS` en lugar de renombrar keys | Los flows bartenders NO están registrados en FlowRegistry. Renombrar keys a `demo_*` no tiene sentido si no hay flows `demo_*` registrados. Mejor: vaciar el dict o agregar schemas para flows realmente registrados (`generic_flow`). |
| D.3 | **Importar flows eagerly en `server.py`** — mismos que `main.py:15-17` | El MCP server arranca como proceso standalone (`python -m`). Sin los imports eager, el FlowRegistry estará vacío. Replicar el patrón de `main.py`. |
| D.4 | **Usar `get_service_client()` para queries del MCP server** | Coherente con el patrón existente. Service role bypasea RLS (tras D1). El `org_id` se usa como filtro explícito en las queries (`.eq("org_id", config.org_id)`), no como RLS automático. |
| D.5 | **`SUPABASE_ANON_KEY` requerida en env del MCP server** | `src/config.py:13` define `supabase_anon_key` como campo obligatorio sin default. El plan solo menciona `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` en la config de Claude Desktop. Corrige plan §1.4.1. |
| D.6 | **Posponer refactorización del scheduler bartenders** | El scheduler no está conectado al lifespan y no afecta al MCP server. La refactorización (T1 del 1.0.0.1) es ruido que no aporta valor a Sprint 1. Dejar para cleanup posterior. |

---

## §4. Criterios de Aceptación

| # | Criterio | Sub-paso | Verificable |
|---|---|---|---|
| CA1 | `python -c "from mcp.types import Tool; print('OK')"` ejecuta sin error (sin extras `[crew]`) | 1.0.2 | Sí/No |
| CA2 | `get_secret_async` está definida en `src/db/vault.py` y es callable async | 1.0.1 | Sí/No |
| CA3 | `from src.db.vault import get_secret_async` no lanza ImportError | 1.0.1 | Sí/No |
| CA4 | `flow_registry.register("x", description="test")` no lanza error | 1.0.3 | Sí/No |
| CA5 | `flow_registry.get_metadata("x")` retorna dict con key `description` | 1.0.3 | Sí/No |
| CA6 | `from src.api.routes.flows import FLOW_INPUT_SCHEMAS` funciona sin import circular | 1.0.4 | Sí/No |
| CA7 | `FLOW_INPUT_SCHEMAS` no contiene keys con prefijo `bartenders_` | 1.0.0.1 | Sí/No |
| CA8 | `grep -rn "bartenders" src/ --exclude-dir=demo --exclude-dir=bartenders` retorna ≤5 resultados (solo refs residuales en comentarios) | 1.0.0.1 | Sí/No |
| CA9 | `src/mcp/config.py` existe y `MCPConfig(org_id="test")` instancia correctamente | 1.1.2 | Sí/No |
| CA10 | `src/mcp/tools.py` define ≥5 tool definitions MCP | 1.1.3 | Sí/No |
| CA11 | `src/mcp/flow_to_tool.py` genera ≥1 tool MCP a partir de FlowRegistry | 1.2.1 | Sí/No |
| CA12 | `python -m src.mcp.server --org-id test --help` muestra opciones sin error de import | 1.3.1 | Sí/No |
| CA13 | Claude Desktop muestra tools de FAP tras reinicio | 1.5.2 | Sí/No |
| CA14 | `list_flows` retorna flows registrados como JSON válido vía Claude | 1.5.3 | Sí/No |
| CA15 | `list_agents` retorna datos de `agent_catalog` para la org | 1.5.4 | Sí/No |
| CA16 | `get_agent_detail` acepta agent_id y retorna `soul_json`, `allowed_tools` | 1.5.5 | Sí/No |
| CA17 | Migración 025 aplicada: `agent_catalog` RLS incluye `service_role` bypass | Pre-req | Sí/No |
| CA18 | Output de todas las tools pasa por `sanitize_output()` antes de retornar | 1.1.3 | Sí/No |
| CA19 | Env `SUPABASE_ANON_KEY` documentada como requerida en claude_desktop_config | 1.4.1 | Sí/No |

---

## §5. Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | **`agent_catalog` RLS bloquea queries** — Sin migración 025, `list_agents` retorna vacío | Alta (100% sin fix) | Alto (tool broken) | Migración 025 como primer paso de implementación |
| R2 | **SDK `mcp` API surface diferente a la esperada** — El plan asume `mcp.server.Server`, `mcp.server.stdio.stdio_server` sin verificar la API exacta | Media | Alto | Verificar `pip show mcp` y leer API docs/source al inicio de implementación |
| R3 | **FlowRegistry vacío en server standalone** — Si olvidamos los imports eager, `list_flows` retorna vacío | Alta (100% sin fix) | Medio | Incluir imports eager en server.py (mismos que main.py) |
| R4 | **`SUPABASE_ANON_KEY` faltante** — Settings lanza error al instanciar sin esta var | Media | Alto | Documentar en config de Claude Desktop. Alternativa: hacer el campo opcional con default vacío en MCPConfig propio |
| R5 | **`main.py:58` KeyError "status"** — Bug heredado que causa crash al arrancar FastAPI normal, pero NO afecta MCP server standalone | Baja (no bloquea Sprint 1) | Bajo | Documentar para fix posterior |
| R6 | **Circular dependency al importar FLOW_INPUT_SCHEMAS** — Si `flows.py` crece o importa desde `mcp/` | Baja | Medio | La cadena actual `mcp → api.routes → flows → registry` no tiene ciclo. Monitorear. |
| R7 | **Claude Desktop no detecta el server** — Path al Python incorrecto, config JSON malformada | Media | Alto | Template de config con paths verificados. Documentar troubleshooting vía `%APPDATA%\Claude\logs\` |
| R8 | **Desacople de bartenders rompe tests existentes** — Si hay tests que importan flows/tools de bartenders | Media | Medio | Verificar `tests/` antes del desacople. Mover tests junto con el código. |

### Riesgos para pasos FUTUROS descubiertos:

| Paso | Riesgo | Detalle |
|---|---|---|
| 5.2 (Auth Bridge) | `_verify_es256_manual()` usa `requests` (no `httpx`) | `middleware.py:195` importa `import requests as req_lib`. Función de referencia — no se usa en producción, pero si Auth Bridge la reutiliza, debe migrar a `httpx`. |
| 5.2 (Handlers de ejecución) | `execute_flow` necesita `org_id` y `user_id` — el MCP server no tiene `user_id` en Sprint 1 | La ejecución de flows usa `BaseFlow(org_id, user_id)`. Para Sprint 3 se necesitará mapear la identidad del agente externo a un `user_id` de FAP. |
| 5.1+ | `config.py:31-44` `get_llm()` importa `from crewai import LLM` — crash si crewai no instalado | El MCP server standalone puede no tener `crewai` instalado si solo se instaló sin extras. Proteger con try/except o no llamar `get_llm()` desde el server. |

---

## §6. Plan de Implementación

| # | Tarea | Paso | Complejidad | Tiempo Est. | Dependencia |
|---|---|---|---|---|---|
| T1 | Crear migración `025_agent_catalog_rls_update.sql` | Pre-req (D1) | Baja | 15 min | Ninguna |
| T2 | Vaciar/refactorizar `FLOW_INPUT_SCHEMAS` (quitar refs bartenders) | 1.0.0.1 (T2) | Baja | 20 min | Ninguna |
| T3 | Mover tools bartenders a `src/tools/demo/` | 1.0.0.1 (T3) | Baja | 15 min | Ninguna |
| T4 | Verificar limpieza: grep bartenders en src/ (excluir demo/) | 1.0.0.1 (T4) | Baja | 10 min | T2, T3 |
| T5 | Crear `get_secret_async()` en `vault.py` | 1.0.1 | Baja | 20 min | Ninguna |
| T6 | Agregar `mcp>=1.0.0` en `pyproject.toml` + `uv sync` | 1.0.2 | Baja | 15 min | Ninguna |
| T7 | Agregar `description` a `FlowRegistry.register()` + `register_flow()` | 1.0.3 | Baja | 30 min | Ninguna |
| T8 | Verificar importabilidad de `FLOW_INPUT_SCHEMAS` sin circular deps | 1.0.4 | Baja | 15 min | T2 |
| T9 | Crear `src/mcp/config.py` con MCPConfig | 1.1.2 | Baja | 20 min | T6 |
| T10 | Crear `src/mcp/tools.py` con 5 tool definitions + handlers | 1.1.3 | Media | 1.5h | T1, T5, T6, T9 |
| T11 | Crear `src/mcp/flow_to_tool.py` | 1.2.1 | Media | 45 min | T7, T8 |
| T12 | Crear `src/mcp/server.py` (entry point stdio) | 1.3.1 | Alta | 2h | T9, T10, T11 |
| T13 | Crear template `claude_desktop_config.json` en repo root | 1.4.1 | Baja | 15 min | T12 |
| T14 | Verificación E2E: servidor arranca, Claude conecta, tools funcionan | 1.5 | Media | 45 min | T12, T13 |

**Orden recomendado:**
```
[Paralelo] T1, T2, T3, T5, T6, T7
     ↓
[Secuencial] T4 (verificar limpieza), T8 (verificar imports)
     ↓
[Secuencial] T9 → T10 → T11 → T12
     ↓
[Secuencial] T13 → T14
```

**Tiempo total estimado: 7-8 horas**

---

## 🔮 Roadmap (NO implementar ahora)

### Optimizaciones pospuestas
- **Refactorización del scheduler:** Renombrar `bartenders_jobs.py → jobs.py`, conectar al lifespan de FastAPI, integrar `health_check.py` como job registrado.
- **Fix `run_full_validation()` retorno:** Agregar key `"status"` al retorno de `FlowRegistry.run_full_validation()` para resolver el bug en `main.py:58`.
- **Eliminar `python-jose` de dependencias:** El código usa `PyJWT` exclusivamente. `python-jose` es peso muerto.
- **Schemas para flows genéricos:** Definir `FLOW_INPUT_SCHEMAS` entries para `generic_flow` (schema: `{text: string}`) y `architect_flow` (schema: `{prompt: string}`).

### Pre-requisitos para pasos futuros
- **Sprint 3 (Auth Bridge):** Necesitará mapear identidad del agente externo → `user_id` de FAP. El MCP server actual solo tiene `org_id`. Diseñar un "service account" o "agent user" en `org_members`.
- **Sprint 3 (Handler execute_flow):** Los handlers de ejecución necesitan `BackgroundTasks` de FastAPI para ejecutar flows async. El MCP server standalone NO tiene FastAPI → usar `asyncio.create_task()` o similar.
- **Sprint 4 (SSE transport):** El `MCPConfig` ya incluye `host` y `port` como preparación. No se implementan hasta Sprint 4.
- **`config.py:get_llm()` crash prevention:** Proteger contra `ImportError` de `crewai` en entornos donde el MCP server se instala sin extras `[crew]`.
