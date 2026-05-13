# 🧠 ANÁLISIS TÉCNICO - PASO 01 - GF

## 0️⃣ Verificación Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `ToolRegistry` | `src/tools/registry.py` | ✅ | Clase `ToolRegistry` (L29) |
| 2 | `tool_registry` | `src/tools/registry.py` | ✅ | Singleton (L272) |
| 3 | `MCPPool` | `src/tools/mcp_pool.py` | ✅ | Clase `MCPPool` (L35) |
| 4 | `api_routes` dir | `ls src/api/routes` | ✅ | Carpeta existe |
| 5 | `app.include_router` | `src/api/main.py` | ✅ | Router inclusion (L97-111) |
| 6 | `require_org_id` | `src/api/middleware.py` | ✅ | Middleware de org (L22 en mcp.py) |
| 7 | `org_mcp_servers` | `src/tools/mcp_pool.py` | ✅ | Tabla DB (L125) |
| 8 | `ToolMetadata` | `src/tools/registry.py` | ✅ | Clase (L17) |

**Discrepancias:**
- Plan pide `src/api/__init__.py`. Proyecto usa `src/api/main.py`. -> *Fijar en main.py.*
- `ToolMetadata` no tiene `category`. -> *Usar primera tag o "general".*
- `MCPPool` requiere iterar `org_mcp_servers`. -> *Fetch servers, luego tools.*

---

## 1️⃣ Análisis de Datos
- **Tablas:** `org_mcp_servers` (read-only para listar).
- **Schema:** Sin cambios.
- **RLS:** Filtrado por `org_id`.

---

## 2️⃣ Análisis de Código
- **Nuevo:** `src/api/routes/tools.py`.
- **Patrón:** `APIRouter` + `Depends(require_org_id)`.
- **Logic:**
  - Local: `tool_registry._metadata.values()`.
  - MCP: Iterar servers activos -> `mcp_pool.get_tools()`.

---

## 3️⃣ Análisis de Backend
- **Endpoint:** `GET /api/tools/available`.
- **Query Params:** `source` (optional).
- **Response:**
```json
[
  {
    "name": "mcp:github:search_code",
    "description": "Search code...",
    "category": "mcp",
    "source": "mcp"
  }
]
```

---

## 4️⃣ Análisis Fullstack + DX
- **Flujo:** Client -> API -> Registry/MCP -> JSON.
- **DX Tooling:**
  ### Herramienta: `list-tools-cli`
  - **Qué:** Script CLI para ver tools sin Postman.
  - **Tipo:** Script `uv run`.
  - **Uso:** `python scripts/debug_tools.py --org <id>`.
  - **Prioridad:** Tarea 0.

---

## 5️⃣ Criterios de Aceptación
- ✅ `GET /api/tools/available` devuelve 200.
- ✅ Prefijo `mcp:[server]:[tool]` en MCP tools.
- ✅ Filtro `?source=local` funciona.
- ✅ Filtro `?source=mcp` funciona.
- ✅ Timeout < 500ms (cache pool).

---

## 6️⃣ Riesgos
| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Latencia MCP | Alta | Servers lentos | `asyncio.gather` con timeouts. |
| Cache stale | Media | Tools nuevas no aparecen | Endpoint `?refresh=true` (opcional). |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón | Etapa | T |
|---|---|---|---|---|---|---|
| 0 | **DX**: Script list | `scripts/debug_tools.py` | `def main(org_id: str)` | `src/cli/main.py` | DX | 0.5h |
| 1 | Crear router tools | `src/api/routes/tools.py` | `@router.get("/tools/available")` | `src/api/routes/mcp.py` | BACKEND | 1.5h |
| 2 | Registro Router | `src/api/main.py` | `app.include_router(tools_router)` | L111 | BACKEND | 0.1h |
| 3 | Validar E2E | — | — | — | FULLSTACK | 0.4h |

**Total:** 2.5h
