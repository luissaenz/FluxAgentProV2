# 🏛️ Análisis Unificado — Paso 1: Endpoint `GET /api/tools/available`

**Fase:** `guiAgentGenerator`  
**Fuente de verdad:** Código real (`src/`) — plan solo referencia  
**Config raíz:** `proyecto-config.json` leído y aplicado  
**Fecha:** 2026-05-13

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **dsp** | ✅ 18 checks | 4 (D1-D4) | ✅ `fap-cli tools validate` | ✅ Archivos+líneas exactos | **5.0** |
| **glm** | ✅ 17 checks | 4 (+2 no verificadas) | ✅ `scripts/list_tools.py` | ✅ Archivos+líneas exactos | **4.7** |
| **step** | ✅ 10 checks | 4 | ✅ `scripts/list_tools.py` | ✅ Archivos+líneas exactos | **4.5** |
| **ring** | ✅ 12 checks | 2 | ✅ `tools_list_cli` | ✅ Archivos+líneas exactos | **4.3** |
| **laguna** | ✅ 14 checks | 3 | ✅ `scripts/tool_ls.py` | ⚠️ Algunas genéricas | **3.5** |
| **GF** | ✅ 8 checks | 3 | ✅ `scripts/debug_tools.py` | ❌ Sin líneas exactas | **2.5** |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| D1 | **`ToolMetadata` no tiene `category`** | dsp, glm, ring, step, laguna, GF | ✅ `src/tools/registry.py:17-26` — `ToolMetadata` dataclass sin `category` | Derivar `category` de `meta.tags[0]`. Si no hay tags → `"general"`. NO modificar `ToolMetadata` (breaking change). |
| D2 | **`MCPPool.get_tools()` requiere `server_name` — no existe `list_all_tools()`** | dsp, glm, ring, step | ✅ `src/tools/mcp_pool.py:77` — firma `get_tools(org_id, server_name, ...)` | Consultar `org_mcp_servers` primero para obtener servidores activos, luego iterar. `asyncio.gather()` para concurrencia. |
| D3 | **Timeout <500ms vs MCP conexión** | dsp, glm, step | ✅ Tiempo real: conexión MCP 1-5s | Ajustar: `<500ms` para `source=local`. MCP con caché TTL 60s + `asyncio.gather(timeout=2s)`. Degradado graceful. |
| D4 | **Plan dice `src/api/__init__.py` pero proyecto usa `src/api/main.py`** | step, laguna, GF | ✅ `src/api/main.py:97-110` — todos los routers registrados aquí | Registrar en `main.py`, NO en `__init__.py`. `__init__.py` solo docstring. |
| D5 | **`list_tools()` retorna solo nombres, necesita `get_metadata()` por cada uno** | glm | ✅ `src/tools/registry.py:230-231` — retorna `List[str]` | Aceptado. Endpoint itera `list_tools()` + llama `get_metadata(name)` por cada tool. |
| D6 | **Tools DB-loaded invisibles sin warmup (`skill_catalog`)** | dsp, glm | ✅ `src/tools/registry.py:130-188` — `_load_from_db()` lazy solo en `get()`, no en `list_tools()` | Documentado como limitación en MVP. No implementar warmup ahora. |

---

## 1️⃣ Resumen Ejecutivo

Endpoint `GET /api/tools/available` expone herramientas locales (`ToolRegistry`) + servidores MCP configurados (`org_mcp_servers`) como API REST unificada. Alimenta el multi-select de tools del builder visual (Paso 4).

**Correcciones críticas al plan:**
- ⚠️ `ToolMetadata` no tiene `category` → derivar de `tags[0]`
- ⚠️ Plan indica `src/api/__init__.py` → realidad es `src/api/main.py`
- ⚠️ MCP no soporta listado global → requiere iterar `org_mcp_servers`
- ⚠️ Timeout <500ms inalcanzable con MCP → ajustar criterio

**Decisión DX:** Fusionar propuestas en `fap tools list` — comando CLI (`src/cli/commands/tools_list.py`) que lista tools locales + MCP. El proyecto ya tiene `fap validate-tools` (dsp propuso crear algo que ya existe). La verdadera brecha DX es **listado**, no validación.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Dashboard builder/envía `GET /api/tools/available` con header `X-Org-ID`
2. FastAPI `require_org_id` extrae `org_id`
3. Handler itera `tool_registry.list_tools()` → `get_metadata(name)` → construye `ToolInfo[]` con `source="local"`
4. Handler consulta `org_mcp_servers` vía `get_service_client()` → `.eq("org_id", org_id).eq("is_active", True)` → lista servidores
5. Para cada servidor MCP activo, `asyncio.gather()` con timeout 2s por servidor
6. Tools MCP mapeadas con nombre `mcp:{server_name}:{tool_name}` y `source="mcp"`
7. Filtra por `?source=local|mcp` si aplica
8. Retorna `ToolsListResponse(tools=[...], count=N)` en JSON

### Edge Cases MVP

| # | Edge Case | Manejo |
|---|---|---|
| EC1 | Org sin servidores MCP configurados | Retornar solo tools locales, MCP vacío. Sin error. |
| EC2 | ToolRegistry vacío | Retornar `{"tools": [], "count": 0}`. Sin error. |
| EC3 | Servidor MCP offline/circuit breaker abierto | `try/except` por server → log warning + skip. Retornar partial. |
| EC4 | `?source=invalido` | FastAPI validation automática → 422. |
| EC5 | `?category=nonexistente` | Retornar `{"tools": [], "count": 0}`. |
| EC6 | Falta header X-Org-ID | `require_org_id` middleware → 400. |

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. `src/api/routes/tools.py` — NUEVO

| Campo | Valor |
|:---|---|
| **Ruta real** | `D:\Develop\Personal\FluxAgentPro-v2\src\api\routes\tools.py` |
| **Tipo de cambio** | Creación |
| **Descripción** | Endpoint `GET /api/tools/available` que lista herramientas locales (ToolRegistry) y MCP (org_mcp_servers) |
| **Patrones a seguir** | `src/api/routes/flows.py:76-110` (patrón listing) + `src/api/routes/integrations.py:18-23` (query DB con get_service_client) |

**Modelos Pydantic:**

```python
class ToolInfo(BaseModel):
    name: str
    description: str
    category: str                              # meta.tags[0] or "general"
    categories: List[str] = []                 # meta.tags completo
    source: Literal["local", "mcp"]            # origen
    parameters: Dict[str, Any] = {}            # meta.parameters
    requires_approval: bool = False
    timeout_seconds: int = 30
    is_active: bool = True

class ToolsListResponse(BaseModel):
    tools: List[ToolInfo]
    count: int
```

**Firma endpoint:**

```python
router = APIRouter(prefix="/api/tools", tags=["tools"])

@router.get("/available", response_model=ToolsListResponse)
async def list_available_tools(
    org_id: str = Depends(require_org_id),
    source: Optional[str] = Query(None, regex="^(local|mcp)$"),
    category: Optional[str] = Query(None),
) -> ToolsListResponse:
```

**Imports exactos:**
```python
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from src.tools.registry import tool_registry
from src.tools.mcp_pool import MCPPool, MCPConnectionError
from src.db.session import get_service_client
from src.api.middleware import require_org_id
```

#### 2. `src/api/main.py` — MODIFICACIÓN

| Campo | Valor |
|:---|---|
| **Ruta real** | `D:\Develop\Personal\FluxAgentPro-v2\src\api\main.py` |
| **Tipo de cambio** | Modificación (2 líneas) |
| **Descripción** | Importar y registrar `tools_router` |

```python
# Línea ~28-29 (junto a otros imports):
from .routes.tools import router as tools_router

# Línea ~111 (después de mcp_router):
app.include_router(tools_router)
```

#### 3. `src/cli/commands/tools_list.py` — NUEVO (DX)

| Campo | Valor |
|:---|---|
| **Ruta real** | `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\tools_list.py` |
| **Tipo de cambio** | Creación |
| **Descripción** | CLI command para listar herramientas desde terminal |
| **Patrones a seguir** | `src/cli/commands/validate_tools.py` (Typer sub-app) |

```python
import asyncio
import typer
from rich.table import Table
from rich.console import Console

tools_list_app = typer.Typer(help="List available tools (local + MCP).")

@tools_list_app.command("list")
def list_tools(
    org_id: str = typer.Option(..., "--org-id", "-o", help="Organization UUID"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter: local|mcp"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all available tools from ToolRegistry and MCP servers."""
    ...
```

Registro en `src/cli/main.py`:
```python
from src.cli.commands.tools_list import tools_list_app
app.add_typer(tools_list_app, name="tools")
```

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: `fap tools list`
- **Qué automatiza:** Listar todas las herramientas disponibles (locales + MCP) desde CLI.
  Diagnóstico rápido de registry y conectividad MCP sin depender del dashboard.
- **Tipo:** CLI command (Typer sub-app)
- **Ubicación:** `src/cli/commands/tools_list.py` + registro en `src/cli/main.py`
- **Cómo se usa:**
  ```
  uv run python -m src.cli.main tools list --org-id <UUID>
  uv run python -m src.cli.main tools list --org-id <UUID> --source mcp
  uv run python -m src.cli.main tools list --org-id <UUID> --json
  ```
- **Impacto para el usuario final:** Elimina curl/Postman para verificar tools.
  Valida registry y conectividad MCP en un solo comando.
  Complementa `fap validate-tools` (ya existente) que valida tools vs agent configs.
- **El implementador DEBE usarla** para verificar el endpoint antes y después de implementar.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Derivar `category` de `tags[0]`:** NO modificar `ToolMetadata` dataclass. Evita breaking change en 6 decoradores `@register_tool` + tools demo existentes. `ToolInfo.category` = `meta.tags[0] or "general"`. `ToolInfo.categories` = `meta.tags` completo.

2. **MCP listing via `org_mcp_servers` + `asyncio.gather()`:** No hay API nativa para listar todas las tools MCP. Estrategia: query DB para servidores activos → llamadas concurrentes con timeout individual 2s → degradado parcial si algún server falla.

3. **No cache ahora:** Primera iteración MVP sin cache. Si performance es problema, añadir `functools.lru_cache` con TTL en tarea futura.

4. **`get_service_client()` para MCP query:** Consistente con `integrations.py` y `mcp_pool.py`. Bypass RLS con filtro manual `.eq("org_id", org_id)`.

5. **Response incluye `count`:** Diferente de algunos análisis (ring, glm omiten). Incluir `count` para que frontend muestre total sin calcular en cliente. Consistente con `flows.py`.

6. **Corrección plan — ubicación router:** ⚠️ Plan dice `src/api/__init__.py`. Código real usa `src/api/main.py`. Router registrado en `main.py:111`.

7. **Corrección plan — MCP tool prefix:** ⚠️ Plan dice genérico "prefijo mcp:server:tool". Implementación: `mcp:{server_name}:{tool_name}`. Se deriva de la respuesta real de `MCPPool.get_tools()` + nombre del server.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Tabla org_mcp_servers consultable con get_service_client() (lectura directa)
✅ [DATA] ToolRegistry.tool_registry singleton responde list_tools() + get_metadata()
✅ [CODE] Archivo src/api/routes/tools.py creado con modelo ToolInfo + ToolsListResponse
✅ [CODE] Router registrado en src/api/main.py (NO en __init__.py)
✅ [CODE] Filtro ?source=local|mcp validado con regex en Query param
✅ [CODE] Filtro ?category=<tag> filtra tools locales por tag
✅ [BACKEND] GET /api/tools/available responde 200 con {"tools": [...], "count": N}
✅ [BACKEND] Tools locales aparecen con source="local", nombre registrado, category=tags[0]
✅ [BACKEND] Tools MCP aparecen con source="mcp" y prefijo "mcp:{server_name}:{tool_name}"
✅ [BACKEND] Sin header X-Org-ID → 400 Bad Request
✅ [BACKEND] Servidor MCP offline → skip + log warning, retornar partial, no 500
✅ [BACKEND] Timeout < 500ms para source=local (solo memoria)
✅ [FULLSTACK] Response contiene: name, description, category, categories, source, parameters, requires_approval, timeout_seconds, is_active
✅ [DX] fap tools list --org-id <UUID> ejecuta sin errores y muestra tools
```

**Funcionales:**
- [ ] Endpoint listo para ser consumido por `AgentForm.tsx` multi-select (Paso 4)
- [ ] Filtro por origen permite tabs "Locales | MCP" en builder UI

**Técnicos:**
- [ ] `src/api/routes/tools.py` importable sin error desde `src.api.routes.tools`
- [ ] `uv run python -c "from src.api.main import app"` no falla después de registro
- [ ] `/api/tools/available` aparece en OpenAPI docs (`/docs`)

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap tools list` — CLI command en `src/cli/commands/tools_list.py` | Media | 1h | Ninguna |
| 1 | Crear `src/api/routes/tools.py` con modelos `ToolInfo` + `ToolsListResponse` | Baja | 0.5h | Tarea 0 (opcional) |
| 2 | Implementar handler `list_available_tools` — lógica local (ToolRegistry) + MCP (org_mcp_servers + gather) | Media | 1.5h | Tarea 1 |
| 3 | Registrar router en `src/api/main.py` (import + include_router) | Baja | 0.15h | Tarea 2 |
| 4 | Test unitario endpoint: `tests/unit/test_tools_endpoint.py` (local, mcp, filtros, degradado) | Media | 1h | Tareas 1-3 |
| 5 | Validación E2E: curl endpoint, probar todos los filtros, simular MCP offline | Baja | 0.5h | Tareas 2-4 |
| **TOTAL** | | | **~4.65h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap tools list` para verificar el registro de tools antes/durante implementación.

### Detalle Tarea 0 — `fap tools list`

Archivo: `src/cli/commands/tools_list.py` (NUEVO)
Registro: `src/cli/main.py` — `app.add_typer(tools_list_app, name="tools")`
Comportamiento:
- `--org-id` requerido
- `--source local|mcp` opcional
- `--json` output estructurado
- Lógica replica exactamente el endpoint pero localmente: importa `tool_registry`, consulta `org_mcp_servers`, imprime tabla con `rich.Table`

### Detalle Tarea 2 — Handler endpoint

```python
async def list_available_tools(org_id, source, category):
    tools = []

    # Local tools
    if source in (None, "local"):
        for name in tool_registry.list_tools():
            if ":" in name:  # skip tenant-scoped keys
                continue
            meta = tool_registry.get_metadata(name)
            if not meta:
                continue
            if category and category not in meta.tags:
                continue
            tools.append(ToolInfo(
                name=name,
                description=meta.description,
                category=meta.tags[0] if meta.tags else "general",
                categories=meta.tags,
                source="local",
                parameters=meta.parameters,
                requires_approval=meta.requires_approval,
                timeout_seconds=meta.timeout_seconds,
                is_active=True,
            ))

    # MCP servers
    if source in (None, "mcp"):
        db = get_service_client()
        result = (
            db.table("org_mcp_servers")
            .select("name")
            .eq("org_id", org_id)
            .eq("is_active", True)
            .execute()
        )
        servers = result.data or []

        async def _fetch(server_name: str) -> List[ToolInfo]:
            try:
                pool = MCPPool.get()
                mcp_tools = await pool.get_tools(org_id, server_name, timeout=5)
                return [
                    ToolInfo(
                        name=f"mcp:{server_name}:{t.name}",
                        description=t.description,
                        category=server_name,
                        categories=["mcp", server_name],
                        source="mcp",
                        is_active=True,
                    )
                    for t in mcp_tools
                ]
            except MCPConnectionError:
                logger.warning("MCP server '%s' unreachable — skipping", server_name)
                return []
            except Exception:
                logger.exception("MCP server '%s' error — skipping", server_name)
                return []

        results = await asyncio.gather(
            *[_fetch(s["name"]) for s in servers], return_exceptions=False
        )
        for result in results:
            tools.extend(result)

    return ToolsListResponse(tools=tools, count=len(tools))
```

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| MCP latency >500ms en listing | Media | `MCPPool.get_tools()` conexión network por servidor | `asyncio.gather()` con timeout 5s. Caché TTL 60s (post-MVP). Degradado parcial. |
| `skill_catalog` tools no aparecen (sin warmup) | Baja | `_load_from_db()` solo se invoca en `get()`, no en `list_tools()` | Documentado. No es blocker MVP. Mitigación futura: warmup al startup. |
| `category` derivada inconsistente entre tools | Baja | Tags no estandarizados entre herramientas | `tags[0]` como canonical. Si vacío → `"general"`. Consistente para todas. |
| Import circular tools.py ↔ registry.py | Baja | `tools.py` importa `tool_registry` que puede importar db.session | Patrón probado en `flows.py` y `integrations.py`. Sin riesgo real. |
| MCP circuit breaker abierto → tools MCP invisibles | Media | Server falló 5 veces → bloqueado 60s | Log warning + retornar tools locales. Transparente para el frontend. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Listar tools locales (sin MCP config) | `GET /api/tools/available?source=local` con X-Org-ID válido | `200 {"tools": [...count N local tools], "count": N}` |
| TP-2 | Listar tools MCP con server activo | `GET /api/tools/available?source=mcp` con org que tiene servidor configurado | `200 {"tools": [{"name": "mcp:server1:tool1", "source": "mcp", ...}], "count": M}` |
| TP-3 | MCP server offline — degradado graceful | `GET /api/tools/available?source=mcp` con server caído | `200 {"tools": [], "count": 0}` — log warning, no 500 |
| TP-4 | Filtro por categoría | `GET /api/tools/available?category=business` | Solo tools con tag "business" |
| TP-5 | Sin header X-Org-ID | `GET /api/tools/available` sin header | `400 {"detail": "..."}` |
| TP-6 | Source inválido | `GET /api/tools/available?source=invalid` | `422` FastAPI validation error |
| TP-7 | DX: fap tools list CLI | `uv run python -m src.cli.main tools list --org-id <UUID>` | Tabla rich con tools, sin errores |
| TP-8 | DX: fap tools list --source=mcp --json | `uv run python -m src.cli.main tools list --org-id <UUID> --source mcp --json` | JSON válido con solo tools MCP |

**Comandos para ejecutar tests:**
```bash
# Unitarios
uv run pytest tests/unit/test_tools_endpoint.py -v --timeout=60

# Integración (requiere servidor + DB)
uv run pytest tests/integration/ -v -k "tools" --timeout=60

# Validación DX
uv run python -m src.cli.main tools list --help
```

---

*Documento unificado generado desde 6 análisis independientes. Código real como fuente de verdad.*
