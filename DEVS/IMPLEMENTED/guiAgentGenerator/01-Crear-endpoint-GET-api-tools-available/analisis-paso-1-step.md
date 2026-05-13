# 📝 Análisis Técnico — Paso 1: Endpoint `GET /api/tools/available`

**Fase:** `guiAgentGenerator`  
**Agente:** `step`  
**Fecha:** 2026-05-13  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `org_mcp_servers` existe | `grep` en migraciones | ✅ | `supabase/migrations/005_org_mcp_servers.sql` línea 9 |
| 2 | Clase `ToolRegistry` existe | `grep` en `src/tools/registry.py` | ✅ | Línea 29 |
| 3 | Método `list_tools()` disponible | `grep` en registry.py | ✅ | Línea 230 |
| 4 | Método `get_metadata(name)` disponible | `grep` en registry.py | ✅ | Línea 220 |
| 5 | Singleton `tool_registry` instanciado | `grep` en registry.py | ✅ | Línea 272 |
| 6 | Clase `MCPPool` existe | `grep` en `src/tools/mcp_pool.py` | ✅ | Línea 35 |
| 7 | Método `get_tools(org_id, server_name)` existe | `grep` en mcp_pool.py | ✅ | Línea 77 |
| 8 | Dependencia `require_org_id` disponible | `grep` en `src/api/middleware.py` | ✅ | Línea 66 |
| 9 | Patrón `APIRouter` confirmado | Lectura de `src/api/routes/agents.py` | ✅ | Línea 15 |
| 10 | Registro de routers en `main.py` | Lectura de `src/api/main.py` | ✅ | Líneas 20-110 |

**Discrepancias encontradas:**

1. **Registro de router**: el plan indica `src/api/__init__.py`, pero la arquitectura actual registra routers en `src/api/main.py`. Se corregirá modificando `main.py`.
2. **Categoría de tools**: `ToolMetadata` no tiene campo `category`. Se derivará de `tags` (primer tag) o default `"general"`. Para MCP tools, categoría = nombre del servidor MCP.
3. **Prefijo MCP**: plan menciona `mcp:server:tool`. Se implementará como `mcp:{server_name}:{tool_name}` para evitar colisiones.
4. **Autenticación**: plan no especifica JWT. Siguiendo otros endpoints (ej. `GET /agents/by-role`), solo se usa `require_org_id`. Se asume suficiente.

---

## 1️⃣ Análisis de Datos

No hay cambios de schema. El endpoint solo lee:
- Tabla `org_mcp_servers` (columnas: `id`, `org_id`, `name`, `command`, `args`, `secret_name`, `is_active`, `created_at`). Ya existe (migración 005). Índice `idx_mcp_servers_org` facilita la consulta.
- RLS policy ya definida: `tenant_isolation_org_mcp_servers` → aislamiento por `org_id` mediante `current_org_id()`.
- ToolRegistry y MCPPool operan en memoria / conexiones persistentes; no触及 datos persistentes nuevos.

---

## 2️⃣ Análisis de Código

**Artefactos nuevos:**
- `src/api/routes/tools.py`:
  - `ToolInfo` (pydantic): `name: str`, `description: Optional[str]`, `category: Optional[str]`, `source: str`.
  - `ToolsListResponse`: `tools: List[ToolInfo]`, `count: int`.
  - `router = APIRouter(prefix="/api/tools", tags=["tools"])`.
  - `@router.get("/available")` → `list_tools(org_id: str = Depends(require_org_id), source: Optional[str] = Query(None, regex="^(local|mcp)$"))`.
- Modificación `src/api/main.py`: import e inclusión del router.
- Opcional: `scripts/list_tools.py` (DX).

**Patrones referencia:**
- Definición de modelos Pydantic: `src/api/routes/flows.py` (líneas 21-53).
- Uso de `require_org_id`: `src/api/routes/agents.py` línea 31.
- Consulta con TenantClient: `src/api/routes/agents.py` líneas 66-75.
- Concurrencia con `asyncio.gather`: patrón usado en `src/tools/mcp_pool.py` (líneas 108-112 y 179-180).

**Firma exacta del endpoint:**
```python
@router.get("/available", response_model=ToolsListResponse)
async def list_tools(
    org_id: str = Depends(require_org_id),
    source: Optional[str] = Query(None, regex="^(local|mcp)$")
) -> ToolsListResponse: ...
```

---

## 3️⃣ Análisis de Backend

** endpoint details:**
- Método: `GET`
- Ruta: `/api/tools/available`
- Query param: `source` (opcional, valores `local` o `mcp`)
- Headers requeridos: `X-Org-ID`
- Respuesta exitosa (200):
```json
{
  "tools": [
    {
      "name": "noop",
      "description": "No-op tool used for testing",
      "category": "builtin",
      "source": "local"
    },
    {
      "name": "mcp:github:list_issues",
      "description": "Listar issues de un repo",
      "category": "github",
      "source": "mcp"
    }
  ],
  "count": 2
}
```
- Error handling:
  - 400 si `source` no coincide con regex.
  - 500 si ocurre error inesperado al conectar a MCP; se captura excepción y se registra, se retorna 500 con detalle.

**Flujo interno:**
1. Extraer `org_id` desde header.
2. Obtener tools locales:
   ```python
   local_tools = []
   for name in tool_registry.list_tools():
       meta = tool_registry.get_metadata(name)
       category = (meta.tags[0] if meta.tags else "general")
       local_tools.append(ToolInfo(name=name, description=meta.description, category=category, source="local"))
   ```
3. Obtener servidores MCP activos:
   ```python
   with get_tenant_client(org_id) as db:
       res = db.table("org_mcp_servers").select("name").eq("is_active", True).execute()
       servers = res.data or []
   ```
4. Para cada servidor, obtener tools concurrentemente:
   ```python
   async def _fetch(server_name):
       try:
           tools = await MCPPool.get_tools(org_id, server_name)
           return [(f"mcp:{server_name}:{t.name}", t.description, server_name) for t in tools]
       except Exception as e:
           logger.error("MCP fetch failed %s: %s", server_name, e)
           return []
   results = await asyncio.gather(*[_fetch(s["name"]) for s in servers], return_exceptions=True)
   ```
5. Aplanar resultados MCP, crear `ToolInfo` con `source="mcp"`.
6. Filtrar por `source` si se proporcionó.
7. Devolver `ToolsListResponse(tools=combined, count=len(combined))`.

**Performance:** Se asume pool MCP precalentado vía `warmup_all_active_tenants()` (lifespan). En frío, primera llamada puede superar 500ms. Se sugiere documentar consideración.

---

## 4️⃣ Análisis Fullstack + DX

**Flujo end-to-end:**
1. Frontend (builder) llama a `GET /api/tools/available?source=local` para poblar selector de herramientas locales.
2. Frontend también puede llamar sin filtro o con `source=mcp` para tools MCP.
3. El builder muestra listado con nombre, descripción, categoría; permite seleccionar múltiples tools.

**Coherencia arquitectónica:**
- Ruta bajo prefijo `/api` consistente con bundles, mcp.
- Autenticación mediante `X-Org-ID` como en otros endpoints.
- Uso de TenantClient asegura aislamiento de datos.
- Respuesta paginada no necesaria (tools por org típicamente < 100).

**DX & Tooling — Obligatorio:**

### Herramienta Propuesta: `scripts/list_tools.py`

- **Qué automatiza:** Permite a desarrolladores y Ops verificar qué herramientas están disponibles en una organización sin necesidad de abrir el dashboard o usar curl. Útil para depurar registros de tools y conexiones MCP.
- **Tipo:** Script Python (CLI) con argumentos `--org-id` y opcional `--source`.
- **Cómo se usa:**
  ```bash
  python scripts/list_tools.py --org-id <ORG_UUID> [--source local|mcp|all]
  ```
  Imprime tabla formateada (o JSON con `--json`).
- **Impacto para el usuario final:** Reduce fricción en diagnóstico de herramientas; valida rápidamente que el endpoint responde y que los servidores MCP están conectados.
- **Prioridad:** **Tarea 0** — implementar antes que el endpoint para poder probarlo una vez desplegado.

---

## 5️⃣ Criterios de Aceptación

✅ [DATA] Tabla `org_mcp_servers` existe con columnas necesarias.  
✅ [CODE] Endpoint `GET /api/tools/available` creado en `src/api/routes/tools.py`.  
✅ [CODE] Modelos `ToolInfo` y `ToolsListResponse` definidos con campos correctos.  
✅ [BACKEND] Endpoint responde 200 con JSON `{tools: [...], count: N}`.  
✅ [BACKEND] Cada tool incluye `name`, `description`, `category`, `source`.  
✅ [BACKEND] Filtro `?source=local|mcp` funciona y es validated por regex.  
✅ [BACKEND] Tools MCP incluyen prefijo `mcp:{server_name}:{tool_name}`.  
✅ [FULLSTACK] Tiempo de respuesta < 500ms en escenario con pool MCP activo.  
✅ [DX] Script `scripts/list_tools.py` ejecuta sin errores y muestra herramientas en formato tabla/JSON.

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Conexión MCP fría > 500ms | Alta | Primera conexión incluye arranque de proceso externo | Pre-warm en lifespan; documentar que timeout asume pool activo |
| Muchos servidores MCP (>10) ralentizan agregación | Media | Llamadas concurrentes consumen recursos | Limitar concurrencia con semáforo (asyncio.Semaphore), cachear resultados 60s |
| Política RLS deniega acceso a `org_mcp_servers` | Media | Config RLS mal aplicada o variable `app.org_id` no seteada | Usar `TenantClient` que ejecuta `set_config` antes de query; verificar policy en migración |
| Filtro `source` con valores inválidos no retorna error claro | Baja | Validación omitida | Usar `Query(..., regex=...)` para autovalidar |
| Categoría derivada de tags inconsistente entre tools locales | Baja | Tags no estandarizados | Establecer default "general"; considerar future: agregar campo `category` en ToolMetadata |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DX & Tooling: script list_tools | `scripts/list_tools.py` | `def main():` (argparse: `--org-id`, `--source` optional) | Estructura similar a `scripts/seed_bundle.py` | DX | Baja | 1h | Ninguna | `python scripts/list_tools.py --org <uuid>` imprime JSON/table sin error |
| 1 | Crear endpoint tools | `src/api/routes/tools.py` | `router = APIRouter(prefix="/api/tools", tags=["tools"])`<br>`class ToolInfo(BaseModel): ...`<br>`class ToolsListResponse(BaseModel): ...`<br>`@router.get("/available") async def list_tools(...) -> ToolsListResponse` | Seguir `src/api/routes/flows.py` (modelos, Depends, Query) | BACKEND | Media | 2h | — | → verificar: import de módulo sin errores; `/docs` muestra endpoint; `pytest` unitario importable |
| 2 | Registrar router en main.py | `src/api/main.py` | Añadir: `from .routes.tools import router as tools_router`<br>`app.include_router(tools_router)` | Igual que líneas 20-32 en main.py | BACKEND | Baja | 0.5h | Tarea 1 | → verificar: servidor inicia sin error; `GET /api/tools/available` responde 200 |

**Tiempo total estimado:** 3.5h

---

## 🔮 Roadmap (NO implementar ahora)

- **Cache por org de tools MCP**: almacenar listado 60s en memoria para reducir latencia.
- **Categorización automática**: etiquetar tools local usando LLM o metadatos extendidos.
- **Paginación**: si número de tools crece mucho, añadir `?limit`/`?offset`.
- **Tool testing endpoint**: `POST /api/tools/{name}/test` para invocar herramienta directamente.

---

## 🚫 Reglas de Oro — Cumplimiento

- ✅ Análisis accionable y específico.
- ✅ Todo verificado contra código fuente.
- ✅ Discrepancias identificadas y resueltas.
- ✅ Código como fuente de verdad.
- ✅ 8+ elementos verificados.
- ✅ 4 etapas cubiertas (Data, Code, Backend, Fullstack+DX).
- ✅ ≥1 herramienta DX propuesta.
- ✅ Tareas atómicas: 1 archivo/tarea, interfaz exacta, patrón explícito, verificación inline.
- ✅ Implementador no decide detalles de interfaz.

---

*Fin del documento.*
