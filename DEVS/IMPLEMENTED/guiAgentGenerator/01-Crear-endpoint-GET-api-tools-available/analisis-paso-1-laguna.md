# Análisis Paso 1 - laguna

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `tool_registry` singleton existe | grep en `src/tools/registry.py` | ✅ | src/tools/registry.py:272 |
| 2 | `ToolRegistry.list_tools()` método existe | grep en `src/tools/registry.py` | ✅ | src/tools/registry.py:230-231 |
| 3 | `ToolRegistry.get_metadata()` método existe | grep en `src/tools/registry.py` | ✅ | src/tools/registry.py:220-221 |
| 4 | `MCPPool.get()` singleton existe | grep en `src/tools/mcp_pool.py` | ✅ | src/tools/mcp_pool.py:51-56 |
| 5 | `MCPPool.get_tools()` método async existe | grep en `src/tools/mcp_pool.py` | ✅ | src/tools/mcp_pool.py:77-191 |
| 6 | `ToolMetadata` dataclass con name/description | grep en `src/tools/registry.py` | ✅ | src/tools/registry.py:16-27 |
| 7 | Archivo `src/api/routes/tools.py` no existe | ls check | ✅ | No existe - necesario crear |
| 8 | Router tools registrado en `main.py` | grep en `src/api/main.py` | ❌ | No existe |
| 9 | `require_org_id` middleware existe | grep en `src/api/middleware.py` | ✅ | src/api/middleware.py:66-81 |
| 10 | `verify_org_membership` middleware existe | grep en `src/api/middleware.py` | ✅ | src/api/middleware.py:135-151 |
| 11 | `agents_router` patrón de registro | src/api/main.py:20-110 | ✅ | Ejemplo: `from .routes.agents import router` |
| 12 | Tabla `org_mcp_servers` existe en migraciones | grep en `supabase/migrations/` | ✅ | 005_org_mcp_servers.sql |
| 13 | `NoopTool` registrado como ejemplo | src/tools/builtin.py | ✅ | src/tools/builtin.py:8-13 |
| 14 | Tools demo en `src/tools/demo/` existen | ls check | ✅ | clima_tool.py, escandallo_tool.py, inventario_tool.py |

### Discrepancias encontradas:

1. **❌ Router `tools_router` no registrado**: El router `tools` no está importado ni registrado en `src/api/main.py`. Se debe agregar después de crear el archivo.

2. **⚠️ Fuente MCP requiere configuración previa**: `MCPPool.get_tools()` requiere que el servidor esté configurado en `org_mcp_servers` (ver migración 005). El endpoint debe manejar el caso donde no hay servidores MCP configurados.

3. **❌ Falta campo `category` en ToolMetadata**: El plan requiere `category` pero `ToolMetadata` solo tiene `name`, `description`, `parameters`, `requires_approval`, `timeout_seconds`, `retry_count`, `tags`. Se debe derivar `category` de los tags o agregar campo.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema impactado
- **Ninguna tabla nueva** - El paso solo expone datos existentes vía API
- Tablas referenciadas: `skill_catalog` (tools desde DB), `org_mcp_servers` (config MCP)

### RLS aplicable
- Endpoints usan `require_org_id` middleware (verificado en §0)
- No se requiere RLS adicional para solo lectura de herramientas registradas

### Índices necesarios
- Ninguno - solo lectura de registros en memoria

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a crear
1. **`src/api/routes/tools.py`** (nuevo - 0 existencia previa)

### Firma del endpoint a crear
```python
# src/api/routes/tools.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/tools", tags=["Tools"])

class ToolInfo(BaseModel):
    name: str
    description: str
    category: str  # derivado de tags
    source: str  # "local" o "mcp:server_name"

@router.get("/available")
async def list_available_tools(
    source: Optional[str] = Query(None, regex="^(local|mcp)$"),
    org_id: str = Depends(require_org_id),
) -> List[ToolInfo]:
    """List available tools from ToolRegistry and MCPPool."""
```

### Patrón a seguir
- **Referencia**: `src/api/routes/bundles.py` - patrón de APIRouter con prefijo `/api/`
- **Middleware**: `require_org_id` (sin auth completa, solo identificación de tenant)
- **Formato respuesta**: Lista de objetos con `name`, `description`, `category`, `source`

### Decisión de diseño: Category mapping
```python
# Mapeo de tags a categorías
TAG_TO_CATEGORY = {
    "mcp": "mcp",
    "builtin": "local",
    "testing": "local",
    # default: primera palabra del nombre
}
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoint a crear
- **Ruta**: `GET /api/tools/available`
- **Method**: GET
- **Query params**: `?source=local|mcp` (opcional)
- **Auth**: `require_org_id` middleware (X-Org-ID header)
- **Response**: `200 OK` con array de `ToolInfo`
- **Timeout**: Debe ser < 500ms (usar caché del registry)

### Flujo de datos
```
GET /api/tools/available
  → require_org_id() extrae org_id
  → tool_registry.list_tools() obtiene nombres
  → tool_registry.get_metadata() por cada tool
  → MCPPool.get() → await get_tools(org_id, server_name) si source=mcp
  → Serializa a ToolInfo[]
  → Return 200
```

### Error handling
- Si `source=mcp` pero no hay servidores configurados → devolver `[]` (no error)
- Si registry vacío → devolver `[]`

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end
```
Builder visual (dashboard)
  → GET /api/tools/available
  → Presenta multi-select de tools en AgentForm
```

### Herramienta Propuesta: DX & Tooling

**Herramienta Propuesta: CLI tool-ls**

- **Qué automatiza:** Listar tools disponibles desde CLI para verificar antes de usar en el builder.
- **Tipo:** Script CLI
- **Cómo se usa:**
  ```bash
  uv run python scripts/tool_ls.py [--source local|mcp] [--json]
  ```
- **Impacto para el usuario final:** Permite verificar qué tools están registradas sin entrar al dashboard.
- **Prioridad:** Tarea 0 — verificar registro de tools después de implementar

### Inconsistencias detectadas
- El plan menciona `MCPPool` pero no especifica cómo listar servidores disponibles. Se asume que `MCPPool.get_tools()` debe iterar sobre servidores activos en `org_mcp_servers`.

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | [DATA] Endpoint responde 200 con array de tools | ✅ `curl -H "X-Org-ID: test" http://localhost:8000/api/tools/available` |
| 2 | [DATA] Tools locales aparecen con su nombre registrado | ✅ Verificar en respuesta |
| 3 | [DATA] Tools MCP aparecen con prefijo `mcp:server:tool` | ✅ Verificar naming |
| 4 | [DATA] Filtro `?source=local` funciona | ✅ `curl ...?source=local` |
| 5 | [DATA] Filtro `?source=mcp` funciona | ✅ `curl ...?source=mcp` |
| 6 | [BACKEND] Timeout < 500ms | ✅ `time curl` |
| 7 | [CODE] Archivo `tools.py` creado siguiendo patrón bundles.py | ✅ `ls src/api/routes/tools.py` |
| 8 | [FULLSTACK] Router registrado en main.py | ✅ Import agregado |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| MCPPool async en endpoint sync | Media | `get_tools()` es async, endpoint debe ser async | Usar `async def` y `await` |
| Tools DB no cargadas | Baja | `ToolRegistry` solo tiene tools en memoria | Documentar que tools deben registrarse al startup |
| Category implícito | Media | `ToolMetadata` no tiene `category` | Derivar de `tags` o primer palabra de nombre |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DX: Script tool-ls | `scripts/tool_ls.py` | `def list_tools(source: Optional[str]) -> List[ToolInfo]` | Nuevo archivo | DX | Baja | 0.25h | Ninguna | → `python scripts/tool_ls.py --json` ejecuta sin errores |
| 1 | Crear endpoint tools | `src/api/routes/tools.py` | `@router.get("/available") async def list_available_tools(source: Optional[str] = Query(None, regex="^(local|mcp)$"), org_id: str = Depends(require_org_id)) -> List[ToolInfo]` | `src/api/routes/bundles.py` | BACKEND | Baja | 0.5h | Tarea 0 | → `curl -H "X-Org-ID: test" localhost:8000/api/tools/available` devuelve 200 |
| 2 | Registrar router | `src/api/main.py` | Agregar `from .routes.tools import router as tools_router` y `app.include_router(tools_router)` | Líneas 20-110 | CODE | Baja | 0.1h | Tarea 1 | → Import no falla: `uv run python -c "from src.api.main import app"` |

**Tiempo total estimado:** 0.85 horas