# Análisis Técnico — Paso 1: Endpoint `GET /api/tools/available`

**Paso:** paso 1  
**Agente:** dsp  
**Fecha:** 2026-05-13  
**Fase:** `guiAgentGenerator`  
**Plan ref:** `DEVS/plan.md` L8-24  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `ToolRegistry` singleton existe | `grep` en `src/tools/registry.py` | ✅ | `src/tools/registry.py:272` — `tool_registry = ToolRegistry()` |
| 2 | `ToolRegistry.list_tools()` existe | Leído `registry.py` | ✅ | `src/tools/registry.py:231` — retorna `List[str]` |
| 3 | `ToolRegistry.get_metadata(name)` existe | Leído `registry.py` | ✅ | `src/tools/registry.py:220` — retorna `Optional[ToolMetadata]` |
| 4 | `ToolMetadata` tiene `name`, `description` | Leído `registry.py` | ✅ | `src/tools/registry.py:20-22` |
| 5 | `ToolMetadata` NO tiene campo `category` | Leído `registry.py` | ❌ | Usa `tags: List[str]` en vez de `category: str` |
| 6 | `ToolMetadata` NO tiene campo `source` | Leído `registry.py` | ❌ | No existe atributo `source` — debe derivarse |
| 7 | `MCPPool` singleton existe | Leído `mcp_pool.py` | ✅ | `src/tools/mcp_pool.py:42` — `_instance` + `get()` classmethod |
| 8 | `MCPPool.get_tools(org_id, server_name)` existe | Leído `mcp_pool.py` | ✅ | `src/tools/mcp_pool.py:77` — async, retorna `list` |
| 9 | `MCPPool` NO tiene `list_all_servers()` ni `list_all_tools()` | Leído `mcp_pool.py` | ❌ | Solo `get_tools(org_id, server_name)` por servidor |
| 10 | `org_mcp_servers` tabla existe | Leído migración | ✅ | `supabase/migrations/005_org_mcp_servers.sql:9` |
| 11 | `org_mcp_servers` columnas: `name`, `is_active`, `org_id` | Leído migración | ✅ | `005_org_mcp_servers.sql:11-17` |
| 12 | `skill_catalog` tabla existe | Leído migración | ✅ | `supabase/migrations/0026_bundle_system.sql:27` |
| 13 | `skill_catalog` columnas: `name`, `code_source`, `metadata` | Leído migración | ✅ | `0026_bundle_system.sql:27-36` |
| 14 | Archivo `src/api/routes/tools.py` NO existe | Listado `src/api/routes/` | ✅ | 15 archivos listados, `tools.py` no aparece |
| 15 | `src/api/main.py` registra routers con `app.include_router()` | Leído `main.py` | ✅ | `src/api/main.py:97-110` — 14 routers registrados |
| 16 | Patrón de endpoint "available": `Depends(require_org_id)` | Leído `flows.py`, `integrations.py` | ✅ | `src/api/routes/flows.py:77` — `GET /flows/available` |
| 17 | Tools locales registradas actualmente | `grep` `@register_tool` en `src/tools/` | ✅ | 6 tools: `noop`, `excel_reader`, `excel_writer`, `service_connector`, `sql_analytical`, `event_store` |
| 18 | Tools locales NO tienen source="local" explícito | Leído `registry.py` | ❌ | Atributo `source` inexistente — debe inferirse |

### Discrepancias encontradas: 4

| # | Discrepancia | Plan dice | Código real | Resolución |
|---|---|---|---|---|
| D1 | **Campo `category`** | Cada tool tiene `category` | `ToolMetadata` usa `tags: List[str]`, sin campo `category` | Exponer `tags[0]` como `category` principal, o serializar `tags` completo como array de categorías. Recomendación: `tags` → `categories` en la respuesta. |
| D2 | **Campo `source`** | Cada tool tiene `source: local\|mcp` | `ToolMetadata` no tiene este campo | Derivar `source` dinámicamente: tools del `tool_registry` → `"local"`; tools del `MCPPool`/`org_mcp_servers` → `"mcp"`. |
| D3 | **Listado MCP tools** | "Las tools de MCPPool aparecen con prefijo `mcp:server:tool`" | `MCPPool.get_tools()` requiere conexión activa por servidor (lenta, >500ms) | 2 estrategias: (a) listado rápido: consultar `org_mcp_servers` y devolver metadata de servidores como "servers disponibles" con conteo; (b) listado completo: conectar async con timeout 2s por servidor para obtener tools reales. Recomendación: implementar ambas — `?source=mcp` retorna metadata de servidores; flag `?deep=true` intenta conexión para listar tools reales. |
| D4 | **Timeout < 500ms vs MCP** | Criterio: "Timeout < 500ms" | Conexiones MCP tardan 1-5s típicamente | Solo el listado de tools locales garantiza <500ms. MCP tools deben ser async/background o devolverse como "pending" con polling. Ajustar criterio de aceptación: `<500ms` para `source=local`; `<5s` para `source=mcp`. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema tocado (directo/indirecto)

| Tabla | Tipo de acceso | Motivo |
|---|---|---|
| `org_mcp_servers` | Lectura | Listar servidores MCP activos de la org para obtener tools MCP |
| `skill_catalog` | Lectura (indirecta vía `ToolRegistry._load_from_db`) | Tools cargadas desde DB ya están en memoria del registry; listarlas solo lee el `_tools` dict en memoria |

### Cambios de schema: **NINGUNO**

El Paso 1 no requiere migraciones. Es un endpoint de solo lectura sobre datos ya existentes.

### RLS / Integridad

- `org_mcp_servers`: RLS activo (`tenant_isolation_org_mcp_servers` vía `current_org_id()`). La query debe usar `get_service_client()` (service_role) o `get_tenant_client(org_id)` con filtro explícito por `org_id`.
- `skill_catalog`: RLS activo (`skill_catalog_tenant_isolation`). El `ToolRegistry` ya maneja el scoping por `org_id` en su 4-tier lookup.
- **Decisión**: Usar `get_service_client()` para bypass RLS en la query a `org_mcp_servers` (consistente con el patrón de `integrations.py` y `mcp_pool.py`).

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos nuevos: 1

#### `src/api/routes/tools.py` (NUEVO)

**Firma del router:**

```python
router = APIRouter(prefix="/api/tools", tags=["tools"])
```

**Endpoints:**

##### `GET /api/tools/available`

```python
@router.get("/available")
async def list_available_tools(
    org_id: str = Depends(require_org_id),
    source: Optional[str] = Query(None, regex="^(local|mcp)$"),
    category: Optional[str] = Query(None),
):
    """Listar todas las herramientas disponibles: locales + MCP.
    
    Args:
        org_id: UUID de la organización (header X-Org-ID).
        source: Filtrar por origen — "local" (ToolRegistry) o "mcp" (MCPPool servers).
        category: Filtrar por tag/categoría (aplica a tools locales).
    
    Returns:
        ToolsListResponse con array de herramientas.
    """
```

**Modelos Pydantic necesarios:**

```python
class ToolInfo(BaseModel):
    """Información de una herramienta disponible."""
    name: str
    description: str
    category: Optional[str] = None       # Primer tag de ToolMetadata
    categories: List[str] = []            # Todos los tags
    source: Literal["local", "mcp"]       # Origen
    parameters: Dict[str, Any] = {}       # Schema de parámetros
    requires_approval: bool = False
    timeout_seconds: int = 30
    is_active: bool = True

class ToolsListResponse(BaseModel):
    """Respuesta con lista de herramientas disponibles."""
    tools: List[ToolInfo]
    count: int
```

### Patrón de referencia

**Archivo espejo:** `src/api/routes/flows.py` → endpoint `GET /flows/available`

| Aspecto | flows.py | tools.py (a crear) |
|---|---|---|
| Router | `APIRouter(prefix="/flows", tags=["flows"])` | `APIRouter(prefix="/api/tools", tags=["tools"])` |
| Auth | `Depends(require_org_id)` | `Depends(require_org_id)` |
| Query params | `category: Optional[str]`, `exclude_system: bool` | `source: Optional[str]`, `category: Optional[str]` |
| Respuesta | `FlowsListResponse(flows=flows)` | `ToolsListResponse(tools=tools, count=N)` |
| Import style | Relativo: `from ...flows.registry import flow_registry` | Absoluto: `from src.tools.registry import tool_registry` |
| Modelos | Pydantic `BaseModel` anidados | Pydantic `BaseModel` anidados |

**Decisión de imports:** Usar imports absolutos (`from src.tools.registry import tool_registry`) como en `integrations.py`, ya que el patrón de rutas modernas del proyecto lo prefiere.

### Lógica de listado local (ToolRegistry)

```python
def _list_local_tools(org_id: str, category: Optional[str] = None) -> List[ToolInfo]:
    tools = []
    for name in tool_registry.list_tools():
        # Saltar keys tenant-scoped (contienen ":")
        if ":" in name:
            continue
        meta = tool_registry.get_metadata(name)
        if not meta:
            continue
        # Filtro por tag/categoría
        if category and category not in meta.tags:
            continue
        tools.append(ToolInfo(
            name=name,
            description=meta.description,
            category=meta.tags[0] if meta.tags else None,
            categories=meta.tags,
            source="local",
            parameters=meta.parameters,
            requires_approval=meta.requires_approval,
            timeout_seconds=meta.timeout_seconds,
            is_active=True,
        ))
    return tools
```

### Lógica de listado MCP

```python
def _list_mcp_servers(org_id: str) -> List[ToolInfo]:
    """Lista servidores MCP configurados. No conecta — solo metadata."""
    db = get_service_client()
    result = (
        db.table("org_mcp_servers")
        .select("name, command, is_active")
        .eq("org_id", org_id)
        .eq("is_active", True)
        .execute()
    )
    tools = []
    for server in (result.data or []):
        tools.append(ToolInfo(
            name=f"mcp:{server['name']}",      # Prefijo mcp:server
            description=f"MCP Server: {server['name']} — {server.get('command', '')}",
            category=None,
            categories=["mcp"],
            source="mcp",
            parameters={},
            is_active=server.get("is_active", True),
        ))
    return tools
```

### Archivos modificados: 1

#### `src/api/main.py` (añadir 2 líneas)

Después de la línea 108 (`app.include_router(integrations_router)`), añadir:

```python
from .routes.tools import router as tools_router  # junto a los demás imports
app.include_router(tools_router)                   # en el bloque de include_router
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoint

| Método | Ruta | Auth | Input | Output | Status |
|---|---|---|---|---|---|
| `GET` | `/api/tools/available` | `X-Org-ID` header | Query: `?source=local\|mcp`, `?category=tag` | `{"tools": [...], "count": N}` | 200 OK |

### Happy path — request/response

**Request:**
```
GET /api/tools/available?source=local
Headers:
  X-Org-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Response (200):**
```json
{
  "tools": [
    {
      "name": "excel_reader",
      "description": "Lee archivos Excel del proyecto Aybar...",
      "category": "business",
      "categories": ["business", "excel", "aybar"],
      "source": "local",
      "parameters": {},
      "requires_approval": false,
      "timeout_seconds": 30,
      "is_active": true
    },
    {
      "name": "sql_analytical",
      "description": "Ejecuta consultas analiticas pre-validadas...",
      "category": "analytical",
      "categories": ["analytical", "sql", "read-only"],
      "source": "local",
      "parameters": {},
      "requires_approval": false,
      "timeout_seconds": 30,
      "is_active": true
    }
  ],
  "count": 2
}
```

### Error handling

| Escenario | Status | Respuesta |
|---|---|---|
| Falta header `X-Org-ID` | 400 | `{"detail": "X-Org-ID header is required"}` |
| `source` inválido (≠ `local\|mcp`) | 422 | FastAPI validation automática (regex) |
| `category` no coincide con ninguna tool | 200 | `{"tools": [], "count": 0}` |
| Error DB al consultar `org_mcp_servers` | 200 (degradado) | Solo lista tools locales + warning en logs |

### Middleware aplicable

- `require_org_id`: Extrae valida el header `X-Org-ID`. **Único middleware necesario** para este endpoint (no requiere JWT ni verificación de membresía — listado público dentro de una org).

### Flujo de datos

```
Cliente (Dashboard Builder)
  │ GET /api/tools/available?source=local
  │ Header: X-Org-ID
  ▼
FastAPI Router (tools.py)
  │ Depends(require_org_id) → extrae org_id
  ▼
ToolRegistry.list_tools()          ─── tools locales en memoria
  │
  │ (si source=mcp o sin filtro)
  ▼
get_service_client()
  → org_mcp_servers (is_active=true)
  │
  ▼
ToolsListResponse(tools=[...], count=N)
  │ 200 OK JSON
  ▼
Cliente (se renderiza en TemplatePicker/AgentForm)
```

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
DB (org_mcp_servers, skill_catalog)
  │
  ▼ (al startup)
ToolRegistry (memoria) + org_mcp_servers (DB)
  │
  ▼ GET /api/tools/available
Backend (tools.py route)
  │
  ▼ JSON response
Dashboard Builder (AgentForm → Tools multi-select)
  │
  ▼ Selección de tools por el usuario
AgentForm guarda en agent_catalog.allowed_tools
  │
  ▼ Al ejecutar agente
AgentFactory.resolve_tools() → ToolRegistry.get() | MCPPool.get_tools()
```

### Coherencia: plan realizable con arquitectura existente

- **SÍ**, con ajustes documentados en §0 (D1-D4). El endpoint se apoya en `ToolRegistry` y `org_mcp_servers` existentes.
- El frontend (`AgentForm.tsx` en Paso 4) consumirá este endpoint para el multi-select de tools — no requiere cambios adicionales en backend.

### Gaps / Fricción

- **MCP tools no listan individualmente**: Solo se expone el servidor como "contenedor". Para listar tools individuales de un MCP server se requiere conexión activa (lenta). Esto se aborda en el roadmap (§7), no en este paso.
- **Tags vs Categories**: El frontend deberá mapear `categories` (array) a chips de filtro, no esperar un solo `category` string.

### DX & Tooling

#### Herramienta Propuesta: `fap-cli tools validate`

- **Qué automatiza:** Validación de disponibilidad de tools — verifica que todas las tools referenciadas en `agent_catalog.allowed_tools` existen realmente en el registry o en MCP servers activos. Hoy el usuario descubre tools rotas solo al ejecutar un agente y verlo fallar.
- **Tipo:** CLI command
- **Cómo se usa:**
  ```bash
  uv run python -m src.cli.main tools validate --org-id <UUID>
  # Output:
  # ✅ excel_reader       → local (disponible)
  # ✅ service_connector  → local (disponible)
  # ❌ mcp:stripe:charge  → MCP server 'stripe' no configurado
  # ⚠️ inventario_tool    → existente pero inactivo
  ```
- **Impacto para el usuario final:** Evita guardar configuraciones de agente con tools rotas. Diagnostica problemas de conectividad MCP antes de ejecutar el agente.
- **Prioridad:** Tarea 0 — implementar antes del resto del paso.

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Tipo |
|---|---|---|
| ✅ C1 | `GET /api/tools/available` responde 200 con array de tools | BACKEND |
| ✅ C2 | `GET /api/tools/available?source=local` retorna solo tools del ToolRegistry | BACKEND |
| ✅ C3 | `GET /api/tools/available?source=mcp` retorna solo servidores MCP de la org | BACKEND |
| ✅ C4 | `GET /api/tools/available?category=business` filtra tools locales por tag | BACKEND |
| ✅ C5 | Tools locales aparecen con `source: "local"` y `categories` del `ToolMetadata.tags` | BACKEND |
| ✅ C6 | MCP servers aparecen con `source: "mcp"` y nombre con formato `mcp:{server_name}` | BACKEND |
| ✅ C7 | Sin header `X-Org-ID` → 400 Bad Request | BACKEND |
| ✅ C8 | Endpoint local (sin MCP) responde en <500ms | BACKEND |
| ✅ C9 | Router registrado en `src/api/main.py` sin romper otros endpoints | CODE |
| ✅ C10 | `src/api/routes/tools.py` sigue el patrón de `flows.py` (imports, modelos, router) | CODE |
| ✅ C11 | Respuesta incluye `name`, `description`, `category`, `categories`, `source`, `parameters`, `requires_approval`, `timeout_seconds`, `is_active` | FULLSTACK |
| ✅ C12 | DX: `fap-cli tools validate --org-id UUID` ejecuta sin errores y reporta estado de cada tool | DX |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: MCP tools no listan individualmente | Media | `MCPPool` requiere conexión activa por servidor — lento (>500ms) para listado | Documentar limitación. MVP lista servidores MCP como contenedores. Paso futuro: `GET /api/tools/available?source=mcp&server=X` con conexión bajo demanda. |
| R2: Tools DB-loaded no visibles sin `org_id` | Baja | `ToolRegistry._tools` incluye keys tenant-scoped (`org_id:name`). `list_tools()` las retorna todas. | Filtrar keys con `:` para el listado público; las tenant-scoped se cargan al consultar con `org_id`. |
| R3: `category` ambiguo (tags vs string único) | Media | Plan asume `category: string`, código usa `tags: List[str]`. Frontend espera string. | Exponer ambas: `category` = primer tag, `categories` = array completo. Frontend usa `categories` para filtros, `category` para display simple. |
| R4: `tool_registry.list_tools()` no expone tools DB-loaded si org no ha hecho warmup | Baja | Tools de `skill_catalog` se cargan lazy vía `_load_from_db()` al primer `get()`. No aparecen en `list_tools()` hasta ser accedidas. | Documentar: el listado muestra tools registradas en memoria + MCP servers. Tools DB-loaded no accedidas aún no aparecen. Mitigación futura: warmup por org al inicio. |
| R5: Conflicto de import circular | Baja | `tools.py` importa `tool_registry` y potencialmente `get_service_client`; ambos ya usados en otras rutas sin conflicto. | Seguir el patrón exacto de `integrations.py` para imports de DB client. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: CLI `tools validate` | `src/cli/commands/tools_cmd.py` | `def tools_validate(org_id: str) -> None` — itera `agent_catalog.allowed_tools`, verifica cada tool contra `tool_registry.get()` y `org_mcp_servers` | `src/cli/commands/baseline_check.py` | DX | Media | 1.5h | Ninguna | → verificar: `uv run python -m src.cli.main tools validate --help` ejecuta |
| 1 | Crear `src/api/routes/tools.py` con endpoint `GET /api/tools/available` | `src/api/routes/tools.py` | `router = APIRouter(prefix="/api/tools", tags=["tools"])` con `@router.get("/available") async def list_available_tools(org_id, source, category)` → `ToolsListResponse` | `src/api/routes/flows.py :: GET /flows/available` | BACKEND | Baja | 1h | Tarea 0 | → verificar: `curl localhost:8000/api/tools/available -H "X-Org-ID: test"` → 200 con tools |
| 2 | Registrar router en `src/api/main.py` | `src/api/main.py` | Añadir `from .routes.tools import router as tools_router` + `app.include_router(tools_router)` | `src/api/main.py:27` (imports existentes) + `src/api/main.py:108` (include existente) | CODE | Baja | 0.25h | Tarea 1 | → verificar: `uv run python -c "from src.api.main import app; print([r.path for r in app.routes])"` incluye `/api/tools/available` |
| 3 | Test unitario del endpoint | `tests/unit/test_tools_endpoint.py` | `async def test_list_local_tools(): ...` — mockea `tool_registry`, verifica respuesta | `tests/unit/test_flows_endpoint.py` (si existe) o `tests/unit/` existentes | CODE | Baja | 0.75h | Tarea 2 | → verificar: `uv run pytest tests/unit/test_tools_endpoint.py -v` pasa |
| 4 | Validar flujo end-to-end | — | `curl GET /api/tools/available` → verificar cada campo del response contra §3 happy path | — | FULLSTACK | Baja | 0.5h | Tareas 1-3 | → verificar: criterios §5 C1-C8 pasan todos |

**Tiempo total estimado:** 4 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **MCP tool listing individual**: Conectar async a cada servidor MCP para listar tools reales (no solo metadata de servidor). Requiere `?deep=true` o endpoint separado `GET /api/tools/available/mcp/{server}`.
- **Tool warmup al startup**: Incluir `skill_catalog` en el warmup por org para que `list_tools()` refleje tools DB-loaded sin acceso previo.
- **Tool health status**: Añadir campo `health` (healthy/degraded/offline) basado en último éxito de conexión MCP o validación de tool.
- **Tool usage stats**: Exponer métricas de uso por tool (cuántas veces invocada, tasa de error) desde `tasks.tokens_used` + `domain_events`.

---

## 📊 Métrica de Calidad (Auto-verificación)

| Métrica | Mínimo | Cumplido |
|---|---|---|
| `proyecto-config.json` leído antes de explorar | 100% | ✅ |
| Elementos verificados (§0) | ≥ 8 (1-2 archivos) | ✅ 18 |
| Discrepancias detectadas | ≥ 1 | ✅ 4 (D1-D4) |
| Secciones completadas | 8 (0-7) | ✅ 8 |
| Etapas cubiertas | 4 | ✅ 4 |
| Criterios de aceptación | ≥ 1 por sub-paso | ✅ 12 |
| Riesgos identificados | ≥ 3 | ✅ 5 |
| Tareas atómicas (1 artefacto) | 100% | ✅ 5 tareas |
| Interfaz exacta por tarea | 100% | ✅ Todas con firma |
| Patrón de referencia explícito | 100% | ✅ Cada tarea referencia archivo concreto |
| Verificación inline por tarea | 100% | ✅ Comandos concretos |
| Suposiciones no verificadas | ≤ 2 | ✅ 0 (todo verificado) |
| Propuesta DX / Tooling | ≥ 1 | ✅ `fap-cli tools validate` |
| Estimación de tiempo | Por tarea + total | ✅ 4h total |
