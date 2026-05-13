# Análisis Técnico — Paso 1: Crear endpoint `GET /api/tools/available`

> **Agente:** glm | **Paso:** 1 | **Fecha:** 2026-05-13

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | `ToolRegistry` existe | `src/tools/registry.py` — clase `ToolRegistry` con singleton `tool_registry` | ✅ VERIFICADO | `registry.py:29-272`, métodos: `register()`, `get()`, `get_metadata()`, `list_tools()`, `list_by_tag()` |
| 2 | `MCPPool` existe | `src/tools/mcp_pool.py` — clase `MCPPool` con singleton `MCPPool.get()` | ✅ VERIFICADO | `mcp_pool.py:35-213`, métodos: `get_tools(org_id, server_name)` async, `close()`, `reset()` |
| 3 | `src/api/routes/tools.py` NO existe | Verificado con `ls` — no está en el directorio de rutas | ✅ VERIFICADO | `src/api/routes/` tiene 14 archivos, `tools.py` ausente. Creación requerida. |
| 4 | Registro de routers en `main.py` | `src/api/main.py:97-110` — `app.include_router(...)` para cada router | ✅ VERIFICADO | Patrones: import → `router = ...` → `app.include_router(router)` |
| 5 | `require_org_id` dependency | `src/api/middleware.py:66-81` — extrae `X-Org-ID` header | ✅ VERIFICADO | Retorna org_id string, lanza 400 si falta |
| 6 | `verify_org_membership` dependency | `src/api/middleware.py:135-152` — verifica JWT + membresía org | ✅ VERIFICADO | Retorna dict con `org_id`, `user_id`, `role` |
| 7 | `ToolMetadata` tiene `tags` pero NO `category` | `src/tools/registry.py:17-27` — `ToolMetadata` dataclass | ❌ DISCREPANCIA | Plan pide campo `category`. `ToolMetadata` solo tiene `tags: List[str]`. Resolución: mapear primer tag como `category`, o duck-type a partir de tags. |
| 8 | `MCPPool.get_tools()` requiere `server_name` | `mcp_pool.py:77-99` — async, params `(org_id, server_name, timeout, max_retries)` | ❌ DISCREPANCIA | Plan asume que se pueden listar todas las tools MCP. No existe `list_all_tools()`. Resolución: consultar `org_mcp_servers` primero, luego iterar. |
| 9 | `org_mcp_servers` tabla existe | `supabase/migrations/005_org_mcp_servers.sql:9-19` | ✅ VERIFICADO | Columnas: id, org_id, name, command, args (JSONB), secret_name, is_active, created_at. UNIQUE(org_id, name). |
| 10 | `service_catalog` / `service_tools` tablas existen | `migration 024` + integrations route | ✅ VERIFICADO | `service_tools` tiene `id, name, tool_profile, service_id`. Solapamiento parcial con tools. |
| 11 | `ToolRegistry.list_tools()` retorna `List[str]` | `registry.py:230-231` | ❌ DISCREPANCIA | Solo retorna nombres, no metadata enriquecida. Endpoint necesita iterar y llamar `get_metadata()` por cada tool. |
| 12 | Herramientas locales registradas | `builtin.py`, `excel_reader.py`, `excel_writer.py`, `service_connector.py`, `analytical.py` + `__init__.py` | ✅ VERIFICADO | Tools registradas: `noop`, `excel_reader`, `excel_writer`, `service_connector`, `sql_analytical`, `event_store`. Demo: `inventario_tool.py`, `escandallo_tool.py`, `clima_tool.py` (no registradas via registry). |
| 13 | `skill_catalog` referenciado en código | `registry.py:130-188` — `_load_from_db()` | ⚠️ NO VERIFICADO | Tabla referenciada pero no hay migración dedicada. Podría estar en `004_agent_catalog.sql` o creada por bundle import. Confirmar existencia en DB antes de implementar. |
| 14 | Endpoint similar `/flows/available` existe | `src/api/routes/flows.py:76-110` | ✅ VERIFICADO | Patrón: `list_flows()` → iterar → `get_metadata()` → filtrar → response. Análogo directo. |
| 15 | Endpoint similar `/api/integrations/available` existe | `src/api/routes/integrations.py:18-23` | ✅ VERIFICADO | Patrón: query a `service_catalog` directo con `get_service_client()`. |
| 16 | Handler de errores MCP: `MCPConnectionError` | `mcp_pool.py:31-32` | ✅ VERIFICADO | Excepción custom. Circuit breaker con 5 fallos → 60s cooldown. |
| 17 | `src/api/routes/__init__.py` solo docstring | `routes/__init__.py:1` — `"""Routes sub-package."""` | ✅ VERIFICADO | No auto-registro. Debe añadirse router a `main.py` manualmente. |

**Discrepancias encontradas:**

1. **`ToolMetadata` no tiene campo `category`** — Plan pide `category` en respuesta. `ToolMetadata.tags` es `List[str]`. Resolución: usar primer tag como categoría. Si no hay tags, categoría = `"general"`.

2. **`MCPPool` no tiene método para listar todas las tools** — Solo `get_tools(org_id, server_name)`. Resolución: consultar tabla `org_mcp_servers` para obtener nombres de servidores activos, luego llamar `get_tools()` por cada uno. Esto requerirá manejar errores por servidor (circuit breaker abierto = skip con warning).

3. **`skill_catalog` tabla no verificada en migraciones** — Código la referencia pero no hay migración dedicada. Si no existe, `_load_from_db()` falla gracefulmente. El endpoint de listado solo debe mostrar tools en memoria (locale + MCP), no intentar cargar desde DB en el listado.

4. **Timeout < 500ms puede ser imposible con MCP** — Si org tiene múltiples servidores MCP, cada `get_tools()` puede tardar >500ms (network, start server). Resolución: cachear resultados de MCP tools por org_id con TTL, y timeout individual por server. Si circuit breaker está abierto, retornar resultado parcial.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema: No se crean tablas nuevas

Este paso NO requiere migraciones. El endpoint lee de:
- **Memoria (ToolRegistry)**: tools registradas via `@register_tool`
- **`org_mcp_servers`**: tabla existente (migración 005) para obtener servidores MCP de una org

### Tablas tocadas (lectura):
- `org_mcp_servers`: SELECT por `org_id`, `is_active=True` → obtener nombres de servidores MCP

### Integridad referencial:
- `org_mcp_servers.org_id` → `organizations(id)` (FK existente con ON DELETE CASCADE)

### RLS:
- `org_mcp_servers` tiene RLS con policy `tenant_isolation_org_mcp_servers` usando `current_org_id()`
- El endpoint usa `get_service_client()` (bypass RLS) para leer MCP servers, o `get_tenant_client()` con org_id
- **Decisión**: usar `get_service_client()` con filtro manual `.eq("org_id", org_id)` para consistencia con `integrations.py`

### Índices:
- `idx_mcp_servers_org` ya existe en `org_mcp_servers(org_id)` → suficiente

### Tipos de datos:
- SIN problemas de tipos. Todo es lectura.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases nuevas:

**Archivo: `src/api/routes/tools.py`** (NUEVO)

1. `ToolInfo(BaseModel)` — Response model
   ```python
   class ToolInfo(BaseModel):
       name: str
       description: str
       category: str
       source: Literal["local", "mcp"]
       tags: List[str] = []
       requires_approval: bool = False
       timeout_seconds: int = 30
   ```

2. `ToolsAvailableResponse(BaseModel)` — Wrapper
   ```python
   class ToolsAvailableResponse(BaseModel):
       tools: List[ToolInfo]
   ```

3. `list_available_tools(org_id, source)` — Endpoint handler
   ```python
   @router.get("/available", response_model=ToolsAvailableResponse)
   async def list_available_tools(
       org_id: str = Depends(require_org_id),
       source: Optional[Literal["local", "mcp"]] = None,
   ) -> ToolsAvailableResponse:
   ```

### Patrones existentes a seguir:

- **Patrón de listing endpoint**: `src/api/routes/flows.py::list_available_flows()` (L76-110). Patrón: iterar registry → construir response model → filtrar por query param → retornar. **Este es el patrón de referencia principal.**

- **Patrón de router con prefix `/api/`**: `src/api/routes/integrations.py` — `router = APIRouter(prefix="/api/integrations", tags=["integrations"])`. Para tools: `prefix="/api/tools"`.

- **Patrón de auth mínimo listing**: `integrations.py::list_available_services()` usa `Depends(require_org_id)` para endpoints de solo lectura.

- **Patrón de import de registry**: `src/api/routes/flows.py:13` → `from ...flows.registry import flow_registry`. Para tools: `from ...tools.registry import tool_registry`.

### Modularidad:
- Archivo nuevo auto-contenido: `tools.py` en `routes/`. Sin modificar archivos existentes excepto `main.py` (añadir import + include_router).
- Mismo patrón que `integrations.py` y `flows.py`.

### Imports exactos:
```python
from __future__ import annotations
import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...tools.registry import tool_registry
from ...tools.mcp_pool import MCPPool, MCPConnectionError
from ...db.session import get_service_client
from ..middleware import require_org_id
```

### Complejidad:
- Baja. Endpoint de solo lectura. 2 fuentes de datos (memoria + DB). Lógica de merge simple.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints:

**`GET /api/tools/available`**

| Aspecto | Detalle |
|---------|---------|
| Método | GET |
| Ruta | `/api/tools/available` |
| Auth | `Depends(require_org_id)` — Header `X-Org-ID` |
| Query params | `?source=local` \| `?source=mcp` (opcional) |
| Response 200 | `{"tools": [...]}` |
| Response 400 | Org-ID faltante (middleware) |

### Contrato del endpoint:

**Request:**
```
GET /api/tools/available
Header: X-Org-ID: <uuid>
Query: ?source=local (opcional)
```

**Response 200 (sin filtro):**
```json
{
  "tools": [
    {
      "name": "excel_reader",
      "description": "Lee archivos Excel del proyecto Aybar y retorna datos estructurados en JSON.",
      "category": "business",
      "source": "local",
      "tags": ["business", "excel", "aybar"],
      "requires_approval": false,
      "timeout_seconds": 30
    },
    {
      "name": "mcp:filesystem:list_files",
      "description": "List files in a directory",
      "category": "filesystem",
      "source": "mcp",
      "tags": ["mcp", "filesystem"],
      "requires_approval": false,
      "timeout_seconds": 30
    }
  ]
}
```

**Response 200 (filtro ?source=local):**
```json
{
  "tools": [
    {
      "name": "excel_reader",
      "description": "...",
      "category": "business",
      "source": "local",
      ...
    }
  ]
}
```

### Flujo de datos:

```
1. Request → middleware (require_org_id) → extrae org_id
2. Si source != "mcp":
   a. tool_registry.list_tools() → lista de nombres
   b. Por cada nombre → tool_registry.get_metadata(nombre) → ToolMetadata
   c. Mapear a ToolInfo(source="local", category=tags[0] o "general")
3. Si source != "local":
   a. get_service_client() → query org_mcp_servers donde org_id=X, is_active=True
   b. Por cada server → MCPPool.get().get_tools(org_id, server.name) (async)
   c. Por cada tool del server → mapear tool.name → "mcp:{server_name}:{tool.name}"
   d. Construir ToolInfo(source="mcp", ...)
   e. Si MCPConnectionError → log.warning + skip ese server (no fallar todo)
4. Filtrar por source si corresponde
5. Retornar ToolsAvailableResponse
```

### Error handling:
- `MCPConnectionError` por server individual → `logger.warning()` + skip. Retornar tools disponibles.
- Si TODOS los MCP servers fallan → retornar solo local tools. No 500.
- Si `require_org_id` falla → 400 automático (middleware)
- Si ToolRegistry vacío → retornar lista vacía (no error)

### Cuellos de botella:
- **MCP get_tools() es async con timeout/network**. Si org tiene N servidores MCP, latencia = sum de latencias individuales. Mitigar con `asyncio.gather()` + timeout individual.
- **Caché**: Para cumplir <500ms, implementar caché en memoria con TTL (ej: 60s). MCPPool ya cachea adapters, pero `get_tools()` re-valida conectividad.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo:

```
Dashboard (Next.js)
  → GET /api/tools/available?source=local
  → Response: lista de tools con nombre + descripción + categoría
  → Renderizar multi-select en AgentForm (Paso 04)
  → Filtro por source para tabs: Locales | MCP
```

### Coherencia:
- Endpointalimenta directamente el formulario del builder (Paso 04). Campo `allowed_tools` en `agent_catalog` usa `TEXT[]` → el endpoint devuelve nombres que matchean 1:1 con lo que se persiste.
- Categoría permite agrupar visualmente en el multi-select del builder.

### Gaps:
1. **MCP tools pueden no estar disponibles** si el servidor está offline. El frontend necesita saber cuáles fallaron. Considerar campo `status` en ToolInfo para MCP tools: `"available"` | `"unreachable"`.
2. **No hay paginación**. Si org tiene 100+ MCP tools, la respuesta será grande. Por ahora aceptable (tools son pocas), pero considerar `?limit=` en futuro.

### DX & Tooling — OBLIGATORIO:

```
### Herramienta Propuesta: scripts/list_tools.py
- **Qué automatiza:** Verificar qué tools están disponibles sin levantar el servidor completo. Permite al developer confirmar que el registry está bien configurado y las MCP connections funcionan.
- **Tipo:** script CLI
- **Cómo se usa:** `uv run python scripts/list_tools.py --org_id=<UUID> [--source=local|mcp]`
- **Impacto para el usuario final:** El implementador puede verificar el endpoint SIN curl. Debug rápido de tools faltantes. DX en desarrollo.
- **Prioridad:** Tarea 0 — implementar antes que el endpoint
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla org_mcp_servers consultable sin errores (lectura con RLS)
✅ [CODE] Archivo src/api/routes/tools.py creado con endpoint GET /available
✅ [CODE] Router registrado en src/api/main.py
✅ [CODE] Response model ToolInfo con campos: name, description, category, source, tags, requires_approval, timeout_seconds
✅ [CODE] Filtro ?source=local|mcp funciona correctamente
✅ [BACKEND] GET /api/tools/available responde 200 con array de tools
✅ [BACKEND] Tools locales aparecen con source="local" y nombre registrado
✅ [BACKEND] Tools MCP aparecen con source="mcp" y prefijo "mcp:{server_name}:{tool_name}"
✅ [BACKEND] Endpoint funciona correctamente cuando MCP servers están offline (skip + warning, no 500)
✅ [BACKEND] Auth middleware (X-Org-ID) aplicado correctamente
✅ [FULLSTACK] Frontend puede consumir endpoint para poblar multi-select de tools
✅ [DX] Script list_tools.py ejecuta sin errores y lista tools disponibles
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| Timeout > 500ms con múltiples MCP servers | Alta | `get_tools()` es async con network I/O. N servers = N llamadas secuenciales. | Usar `asyncio.gather()` con timeout individual. Caché en memoria con TTL 60s. Retornar partial results si algún server falla. |
| `skill_catalog` tabla referenciada pero sin migración verificada | Media | `_load_from_db()` en registry.py la usa. Si no existe, DB query falla. | El endpoint SOLO lista tools en memoria (registry) + MCP. No intenta cargar desde DB dinámicamente. `_load_from_db()` solo se invoca en `get()`, no en `list_tools()`. |
| `category` no existe en ToolMetadata — decisión de mapping | Baja | Plan pide category pero ToolMetadata solo tiene tags. | Mapear `tags[0]` como category. Si no hay tags, default `"general"`. Documentar decisión. |
| MCP circuit breaker abierto → tools MCP invisibles | Media | Si server falló 5 veces, circuit breaker lo bloquea 60s. | Log warning. Retornar tools locales parcialmente. Considerar campo `unavailable_mcp_servers` en response para transparencia. |
| `service_connector` aparece duplicado en listing | Baja | Está en ToolRegistry Y en `service_tools` de integraciones. | Son scopes distintos: registry tools vs service catalog tools. Endpoint lista solo registry + MCP. No confundir con `/api/integrations/tools`. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|------------------|-------|-------------|-------------|--------------|--------------|
| 0 | **DX: Script list_tools.py** | `scripts/list_tools.py` | `def main(org_id: str, source: Optional[str]): ...` → imprime lista de tools | `scripts/seed_system_bundles.py` | DX | Baja | 0.5h | Ninguna | → verificar: `uv run python scripts/list_tools.py --help` ejecuta sin errores |
| 1 | Crear response models ToolInfo y ToolsAvailableResponse | `src/api/routes/tools.py` (_inicio) | `class ToolInfo(BaseModel): name: str, description: str, category: str, source: Literal["local","mcp"], tags: List[str]=[], requires_approval: bool=False, timeout_seconds: int=30` y `class ToolsAvailableResponse(BaseModel): tools: List[ToolInfo]` | `src/api/routes/flows.py::FlowInfo, FlowsListResponse` | CODE | Baja | 0.25h | Ninguna | → verificar: importable sin error desde `src.api.routes.tools` |
| 2 | Implementar handler list_available_tools (local tools) | `src/api/routes/tools.py` | `async def list_available_tools(org_id: str = Depends(require_org_id), source: Optional[Literal["local","mcp"]] = None) -> ToolsAvailableResponse` —itar `tool_registry.list_tools()` → `tool_registry.get_metadata(name)` → construir `ToolInfo(source="local", category=tags[0] or "general")` | `src/api/routes/flows.py::list_available_flows()` L76-110 | BACKEND | Media | 0.5h | Tarea 1 | → verificar: `uv run python -c "from src.api.routes.tools import list_available_tools; print('OK')"` |
| 3 | Añadir lógica MCP tools al handler | `src/api/routes/tools.py` | (extender tarea 2) — query `org_mcp_servers` con `get_service_client()` → `MCPPool.get().get_tools(org_id, server_name)` por cada server → mapear nombre como `f"mcp:{server_name}:{tool.name}"` → `asyncio.gather()` con timeout → skip en `MCPConnectionError` | `src/api/routes/integrations.py::list_available_services()` L18-23 + `src/tools/mcp_pool.py` | BACKEND | Media | 0.75h | Tarea 2 | → verificar: endpoint retorna tools MCP con prefijo `mcp:` cuando org tiene servidores configurados |
| 4 | Registrar router en main.py | `src/api/main.py` | Añadir `from .routes.tools import router as tools_router` + `app.include_router(tools_router)` | `src/api/main.py:28,109` patrón existente | CODE | Baja | 0.1h | Tarea 2 | → verificar: `uv run python -c "from src.api.main import app; routes = [r.path for r in app.routes]; assert '/api/tools/available' in str(routes)"` |
| 5 | Test unitario del endpoint | `tests/unit/test_tools_available.py` | `def test_list_local_tools()`, `def test_filter_by_source()`, `def test_mcp_tools_format()`, `def test_mcp_failure_graceful()` | `tests/unit/test_bartenders_routes.py` o `tests/unit/test_base_crew.py` | BACKEND | Media | 1h | Tareas 1-4 | → verificar: `uv run pytest tests/unit/test_tools_available.py -v` pasa |
| 6 | Script DX: list_tools.py | `scripts/list_tools.py` | `def main(org_id, source)`: importa tool_registry + MCPPool, imprime lista formateada | `scripts/seed_system_bundles.py` | DX | Baja | 0.5h | Tarea 2 | → verificar: `uv run python scripts/list_tools.py --help` sin errores |

**Tiempo total estimado:** 3.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Caché de MCP tools**: `MCPPool` ya cachea adapters, pero listing completo debería tener caché con TTL en el endpoint para cumplir <500ms con múltiples servers.
- **Campo `status` en ToolInfo para MCP**: `"available"` | `"unreachable"` | `"circuit_open"`. Útil para el frontend del builder.
- **Paginación**: `?limit=50&offset=0` para orgs con muchas tools.
- **Endpoint granular por server**: `GET /api/tools/available?mcp_server=filesystem` para consultar un solo server MCP.
- **`skill_catalog` tools dinámicas**: Cuando se implementen completamente las skills importadas via bundle, añadir source `"dynamic"` para tools cargadas desde DB.
- **Campo `category` formal en ToolMetadata**: Añadir campo `category: Optional[str]` a `ToolMetadata` y actualizar decoradores `@register_tool` existentes.

---

## 📊 Métrica de Calidad

| Métrica | Valor |
|---------|-------|
| `proyecto-config.json` leído antes de explorar | ✅ 100% |
| Elementos verificados (§0) | 17 (≥ 12 requerido para 3-5 archivos) |
| Discrepancias detectadas | 4 (+ 2 no verificadas) |
| Secciones completadas | 8 (0-7) |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 12, verificables |
| Riesgos identificados | 5 (1 alta, 2 media, 2 baja) |
| Tareas atómicas | 7 (1 artefacto c/u) |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia por tarea | 100% |
| Verificación inline por tarea | 100% |
| Suposiciones no verificadas | 1 (`skill_catalog` tabla — marcada ⚠️) |
| Propuesta DX/Tooling | 1 (scripts/list_tools.py) |
| Estimación de tiempo | 3.5h total |