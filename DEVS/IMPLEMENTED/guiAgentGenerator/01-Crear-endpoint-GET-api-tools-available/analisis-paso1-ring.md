# 🧠 Análisis Técnico — Paso 01: Endpoint `GET /api/tools/available`

> **Agente:** ring  
> **Fecha:** 2026-05-13  
> **Fuente de verdad:** `DEVS/plan.md` → Paso 01  

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---------|-------------|--------|-----------|
| 1 | Archivo `src/api/routes/tools.py` | No existe — debe crearse | ❌ NUEVO | `ls src/api/routes/` no lo muestra |
| 2 | `src/api/__init__.py` | Existe, solo tiene docstring, no importa router de tools | ✅ VERIFICADO | `src/api/__init__.py:1` → `"API package — FastAPI application, middleware, routes."` |
| 3 | `src/api/main.py` | Existe, registra todos los routers vía `app.include_router()` | ✅ VERIFICADO | `src/api/main.py:97-110` — 13 routers incluidos, NO incluye tools |
| 4 | `src/tools/registry.py` — `ToolRegistry` | Existe con `list_tools()` (retorna nombres) y `get_metadata()` (retorna un solo tool) | ✅ VERIFICADO | `src/tools/registry.py:230-234` `list_tools()` → `List[str]`; `src/tools/registry.py:220-221` `get_metadata()` → single |
| 5 | `src/tools/mcp_pool.py` — `MCPPool` | Existe, `get_tools(org_id, server_name)` retorna lista de tools de un servidor MCP específico | ✅ VERIFICADO | `src/tools/mcp_pool.py:77-91` |
| 6 | `src/mcp/tools.py` — `STATIC_TOOLS` + `get_static_tools()` | Existe, define 7 MCP tools estáticas con name, description, inputSchema | ✅ VERIFICADO | `src/mcp/tools.py:29-106` |
| 7 | `src/mcp/server.py` — `handle_list_tools()` | Combina `get_static_tools()` + `build_flow_tools()` para el servidor MCP Stdio | ✅ VERIFICADO | `src/mcp/server.py:33-37` |
| 8 | Herramientas locales auto-registradas | 5 herramientas locales usan `@register_tool`: noop, service_connector, sql_analytical, event_store, excel_reader, excel_writer | ✅ VERIFICADO | `src/tools/builtin.py`, `service_connector.py`, `analytical.py`, `excel_reader.py`, `excel_writer.py` |
| 9 | `ToolMetadata` — no tiene campo `category` | Solo tiene: name, description, parameters, requires_approval, timeout_seconds, retry_count, tags | ⚠️ DISCREPANCIA | `src/tools/registry.py:17-26` — `ToolMetadata` dataclass no incluye `category` |
| 10 | `src/api/routes/mcp.py` | Patrón de referencia para nuevos routers: `APIRouter(prefix=..., tags=[...])` + Dependencies | ✅ VERIFICADO | `src/mcp/routes/mcp.py:26` |
| 11 | `src/api/routes/integrations.py` | Endpoint `GET /available` como referencia de listado simple | ✅ VERIFICADO | `src/api/routes/integrations.py:18-23` |
| 12 | MCPPool.get_tools() requiere `server_name` | No existe método para listar TODOS los MCP servers/tools disponibles sin especificar servidor | ⚠️ GAP | `src/tools/mcp_pool.py:77` — necesita `org_id` + `server_name` |

**Discrepancias encontradas (2):**

1. **`ToolMetadata` no tiene campo `category`** — El plan dice "Devolver lista de tools con: name, description, category, source", pero `ToolMetadata` (registry.py:17-26) solo tiene `name, description, parameters, requires_approval, timeout_seconds, retry_count, tags`. Se necesita agregar `category` a `ToolMetadata` O definir cómo se obtiene la categoría (podría inferirse de `tags` o del módulo de origen).

2. **No existe forma de listar todas las MCP tools sin especificar servidor** — `MCPPool.get_tools()` requiere un `server_name` específico. Para exponer `GET /api/tools/available` con filtro `?source=mcp`, se necesita primero listar los servidores MCP configurados (tabla `org_mcp_servers`) y luego obtener las tools de cada uno, o bien mantener un caché/registro de tools MCP disponibles.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas involucradas

| Tabla | Relevancia | Operación |
|-------|-----------|-----------|
| `agent_catalog` | No directamente — referencia `allowed_tools` que apunta a tools del registry | Solo lectura |
| `org_mcp_servers` | **Sí** — para listar MCP servers y sus herramientas disponibles | Solo lectura |
| `skill_catalog` | Potencialmente — skills cargadas desde DB en `ToolRegistry._load_from_db()` | Solo lectura (via registry) |

### Integridad referencial
- No se crean nuevas tablas ni columnas → sin cambios de schema.
- El endpoint lee datos existentes de `org_mcp_servers` (migración `005_org_mcp_servers.sql` verificada).

### RLS
- `org_mcp_servers` tiene RLS `tenant_isolation` (migración 005) → usar `TenantClient` con `org_id`.
- No se requiere escritura → riesgo de RLS bajo.

### Nuevas dependencias de datos
- Ninguna migración necesaria.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a crear

| Archivo | Tipo | Ubicación |
|---------|------|-----------|
| `src/api/routes/tools.py` | Nuevo — módulo FastAPI APIRouter | `src/api/routes/tools.py` |

### Archivos a modificar

| Archivo | Cambio | Motivo |
|---------|--------|--------|
| `src/api/__init__.py` | Añadir import del nuevo router | Necesario para exponer el router |
| `src/api/main.py` | Añadir `app.include_router(tools_router)` | Registrar endpoint en la app |
| `src/tools/registry.py` (opcional) | Agregar método `list_all_with_metadata()` o extender `ToolMetadata` con `category` | Para exponer metadata completa de tools locales |

### Patrones existentes a seguir

**Patrón de router** (referencia: `src/api/routes/integrations.py`):
```python
router = APIRouter(prefix="/api/integrations", tags=["integrations"])

@router.get("/available")
async def list_available_services(org_id: str = Depends(require_org_id)):
    ...
```

**Patrón de dependencias**:
- Endpoints ligeros (solo lectura) → `Depends(require_org_id)`
- Endpoints con autenticación completa → `Depends(verify_org_membership)`

**Patrón de respuesta Pydantic** (referencia: `src/api/routes/workflows.py`):
```python
class WorkflowSummary(BaseModel):
    id: str
    name: str
    ...
```

### Código existente reutilizable

- `tool_registry.list_tools()` → retorna `List[str]` con los nombres de tools locales
- `tool_registry.get_metadata(name)` → retorna `ToolMetadata` para un tool específico
- `MCPPool.get_tools(org_id, server_name)` → retorna tools de un servidor MCP
- `src/mcp/tools.py` → `get_static_tools()` retorna `List[Tool]` con name, description, inputSchema

### Firmas esperadas

**Nueva función endpoint:**
```python
# src/api/routes/tools.py
@router.get("/available")
async def get_available_tools(
    org_id: str = Depends(require_org_id),
    source: Optional[str] = Query(None, alias="source")
) -> ToolsListResponse:
```

**Modelos de respuesta (nuevos):**
```python
class ToolInfo(BaseModel):
    name: str
    description: str
    category: str  # derivado de tags[0] o campo nuevo en ToolMetadata
    source: str    # "local" | "mcp:<server_name>"

class ToolsListResponse(BaseModel):
    tools: List[ToolInfo]
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoint a implementar

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/tools/available` | Lista todas las herramientas disponibles (locales + MCP) |

### Query parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `source` | `local` \| `mcp` | Filtro por origen de la herramienta |

### Respuesta esperada (200 OK)

```json
{
  "tools": [
    {
      "name": "excel_reader",
      "description": "Lee archivos Excel del proyecto Aybar...",
      "category": "business",
      "source": "local"
    },
    {
      "name": "mcp:server:tool_name",
      "description": "...",
      "category": "external",
      "source": "mcp:server_name"
    }
  ]
}
```

### Contratos y flujo

```
Frontend → GET /api/tools/available?source=local
    ↓
FastAPI Router (src/api/routes/tools.py)
    ↓
require_org_id (middleware) → extrae org_id del header X-Org-ID
    ↓
ToolRegistry.list_tools() → nombres de tools locales
    +
ToolRegistry.get_metadata(name) → description, tags por tool local
    +
MCPPool.get_tools(org_id, server) → herramientas de servidores MCP
    +
org_mcp_servers table → lista de servidores MCP configurados
    ↓
Response JSON
```

### Error handling

| Escenario | Código | Detalle |
|-----------|--------|---------|
| `source` inválido (no `local` ni `mcp`) | 422 | Validación automática de FastAPI con enum |
| Error en conexión a MCP | 503 | MCPPool lanza `MCPConnectionError` |
| Sin herramientas encontradas | 200 | Array vacío `{"tools": []}` |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
[Dashboard UI] → fetch('/api/tools/available?source=local')
       ↓
[FastAPI Router: /api/tools/available]
       ↓
[ToolRegistry] → lista tools locales con metadata
       ↓
[Response JSON] → UI muestra lista de tools en selector multi-select
```

### Coherencia con el plan
- El endpoint alimenta directamente el componente `AgentForm.tsx` (Paso 04) que necesita un multi-select de tools.
- El formato de respuesta (`name, description, category, source`) es suficiente para el selector.
- No se requieren cambios en BD ni migraciones nuevas.

### Gaps detectados
1. **Categorización de tools locales**: `ToolMetadata` no tiene campo `category`. Opciones:
   - (A) Agregar `category` a `ToolMetadata` y pedirlo en el decorator `@register_tool`
   - (B) Derivar categoría del primer tag (ej: tag `"business"` → category `"business"`)
   - (C) Hardcodear un mapping por nombre de tool
   - **Recomendación:** Opción B — derivar de `tags[0]` si existe, sino `"general"`. No requiere cambios en todos los `@register_tool` existentes.

2. **Listar tools MCP sin servidor específico**: `MCPPool.get_tools()` requiere un `server_name`. Para listar TODAS las tools MCP disponibles, se necesita iterar sobre las filas de `org_mcp_servers` y llamar `get_tools()` por cada servidor. **Esto puede ser lento (>500ms si hay muchos servidores)**.
   - **Mitigación:** Cachear el resultado con TTL corto (ej: 60s), o mantener un registro de tools MCP disponibles en una tabla separada/refrescar en background.

### DX & Tooling — Propuesta

```
### Herramienta Propuesta: tools_list_cli
- **Qué automatiza:** Lista todas las tools disponibles (locales + MCP) desde CLI, 
  útil para debugging y validación sin depender del frontend.
- **Tipo:** script CLI
- **Cómo se usa:** `python -m src.cli tools list --org-id <org_uuid> [--source local|mcp]`
- **Impacto para el usuario final:** Elimina la necesidad de probar el endpoint manualmente 
  con curl/Postman. Permite a desarrolladores verificar que las tools están correctamente 
  registradas antes de probar en el builder UI.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No se requieren migraciones nuevas — solo lectura de tablas existentes
✅ [CODE] Endpoint GET /api/tools/available implementado en src/api/routes/tools.py
✅ [CODE] Router registrado en src/api/__init__.py y src/api/main.py
✅ [CODE] Respuesta usa modelo Pydantic con campos: name, description, category, source
✅ [BACKEND] Filtro ?source=local|mcp funciona correctamente
✅ [BACKEND] Tools locales aparecen con su nombre registrado y metadata real
✅ [BACKEND] Tools MCP aparecen con prefijo mcp:server:tool
✅ [BACKEND] Timeout < 500ms (requiere cache o estrategia optimizada para MCP)
✅ [FULLSTACK] Endpoint consumible desde AgentForm.tsx multi-select de tools
✅ [DX] Herramienta tools_list_cli ejecutable y funcional
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| **Performance: listado MCP lento** | Media | MCPPool.get_tools() abre conexión a cada servidor MCP; N servidores = N conexiones secuenciales | Implementar caché en memoria con TTL de 60s para el listado completo |
| **ToolMetadata sin category** | Baja | El plan asume campo `category` pero `ToolMetadata` no lo tiene | Derivar de `tags[0]`, o agregar campo opcional a `ToolMetadata` con default `"general"` |
| **MCP tools con error bloquean la respuesta** | Media | Si un servidor MCP está caído, get_tools() lanza excepción y el endpoint falla | Wrap cada llamada MCP en try/except, retornar herramientas disponibles y loggear errores |
| **Migraciones inesperadas** | Baja | Si `ToolMetadata` necesita `category`, requiere actualizar el decorator `@register_tool` | Hacer el campo opcional con default; no requiere migración de BD |
| **Cambios en herramientas existentes** | Baja | El paso toca `src/api/__init__.py` y `src/api/main.py` que ya tienen muchos imports | Seguir el patrón exacto de los otros routers existentes |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica aplicadas** — cada tarea = un artefacto con interfaz exacta y verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|----------------|-----------------|-------|-------------|-------------|--------------|-------------|
| 0 | **DX: tools_list_cli** | `scripts/tools_list.py` | `def run(org_id: str, source: Optional[str] = None) -> list[dict]` | `scripts/seed_system_bundles.py` | DX | Media | 1h | Ninguna | → verificar: `python scripts/tools_list.py --help` ejecuta sin errores |
| 1 | Crear modelo de respuesta | Dentro de `src/api/routes/tools.py` | `class ToolInfo(BaseModel): name: str; description: str; category: str; source: str` <br> `class ToolsListResponse(BaseModel): tools: list[ToolInfo]` | `src/api/routes/workflows.py :: WorkflowSummary` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `from src.api.routes.tools import ToolsListResponse` importable |
| 2 | Crear endpoint GET /api/tools/available | `src/api/routes/tools.py` | `def get_available_tools(org_id: str = Depends(require_org_id), source: Optional[str] = Query(None, alias="source")) -> ToolsListResponse` | `src/api/routes/integrations.py :: list_available_services` | BACKEND | Media | 1h | Tarea 1 | → verificar: `curl localhost:8000/api/tools/available?org_id=test` responde 200 |
| 3 | Extender ToolMetadata con category (opcional) | `src/tools/registry.py` línea ~26 | Agregar `category: str = "general"` a `ToolMetadata` dataclass | `src/tools/registry.py :: ToolMetadata` (existente) | CODE | Baja | 0.5h | Ninguna | → verificar: `ToolMetadata(name="test", description="", category="test")` funciona |
| 4 | Agregar método list_all con metadata a ToolRegistry | `src/tools/registry.py` | `def list_all_with_metadata(self, org_id: str | None = None) -> list[dict]` — combina `_tools` locales + MCP pool (opcional) | `src/tools/registry.py :: list_tools` + `src/mcp/tools.py :: get_static_tools` | CODE | Media | 1h | Tarea 3 | → verificar: retorna lista con name, description, category, source |
| 5 | Registrar router en `src/api/__init__.py` | `src/api/__init__.py` | Añadir `from .routes.tools import router as tools_router` | `src/api/__init__.py :: agents_router` (línea 20 de main.py) | CODE | Baja | 0.25h | Tarea 2 | → verificar: archivo modificado, import correcto |
| 6 | Registrar router en `src/api/main.py` | `src/api/main.py` | Añadir `app.include_router(tools_router)` | `src/api/main.py:109` (`app.include_router(mcp_router)`) | CODE | Baja | 0.25h | Tarea 5 | → verificar: `python -c "from src.api.main import app"` sin errores |
| 7 | Validar flujo end-to-end | — | Ejecutar endpoint contra servidor local con datos reales | — | FULLSTACK | Baja | 0.5h | Tareas 2-6 | → verificar: retorna tools locales + MCP con todos los campos correctos |

**Tiempo total estimado:** ~5.5 horas

### Detalle de implementación — Tarea 2 (endpoint principal)

La lógica del endpoint debe:

1. **Para source="local" o sin filtro:**
   - Obtener nombres via `tool_registry.list_tools()`
   - Para cada nombre, obtener metadata via `tool_registry.get_metadata(name)`
   - Mapear a `ToolInfo(name=..., description=..., category=metadata.tags[0] o "general", source="local")`

2. **Para source="mcp" o sin filtro:**
   - Leer `org_mcp_servers` con `TenantClient(org_id)` — obtener lista de servidores activos
   - Para cada servidor, llamar `MCPPool.get_tools(org_id, server_name)` con try/except
   - Mapear cada tool MCP a `ToolInfo(name=f"mcp:{server_name}:{tool.name}", description=tool.description, category="external", source=f"mcp:{server_name}")`

3. **Combinar resultados y devolver** `ToolsListResponse`

**Timeout:** El paso indica <500ms. Con MCP pool esto depende del número de servidores. Implementar caché en la Tarea 4 o usar timeout agresivo en las llamadas MCP.

---

## 🔮 Roadmap (NO implementar ahora)

- Cache distribuida para el listado de tools MCP (Redis o similar)
- Categorización automática de tools MCP basada en sus capacidades
- Endpoint `GET /api/tools/{name}/detail` para inspeccionar una herramienta específica
- WebSocket para notificar al frontend cuando cambien las tools disponibles

---

*Análisis generado desde código real. Toda afirmación está respaldada por evidencia del codebase verificado.*