# Análisis Exhaustivo: Conexión FAP ↔ Claude vía MCP

## Fecha: 2026-04-13
## Proyecto: FluxAgentPro-v2

---

## 1. RESUMEN EJECUTIVO

FAP tiene la capacidad de **consumir** herramientas de servidores MCP externos (vía `MCPPool`), pero **no expone** sus propios servicios como servidor MCP. Este análisis identifica los elementos faltantes para que Claude (u otro agente externo) pueda operar FAP como proveedor de herramientas empresariales.

---

## 2. ESTADO ACTUAL DEL PROYECTO

### 2.1 Infraestructura Existente

| Componente | Archivo | Estado | Descripción |
|-----------|---------|--------|-------------|
| FastAPI Gateway | `src/api/main.py` | ✅ Operativo | Rutas REST, auth JWT, middleware |
| FlowRegistry | `src/flows/registry.py` | ✅ Funcional | Registro decorator, validación dependencias |
| ToolRegistry | `src/tools/registry.py` | ✅ Funcional | Metadatos de herramientas |
| BaseFlow | `src/flows/base_flow.py` | ✅ Completo | Lifecycle, HITL, persistencia |
| MCPPool | `src/tools/mcp_pool.py` | ✅ Cliente | **Solo consumidor**, NO expositor |
| Auth/JWT | `src/api/middleware.py` | ✅ ES256+HS256 | verify_org_membership |
| TenantClient | `src/db/session.py` | ✅ RLS | Aislamiento multitenant |
| Config | `src/config.py` | ✅ Multiple LLM | groq, openrouter, openai, **anthropic** |
| AgentCatalog | `src/crews/base_crew.py` | ✅ Estructura | SOUL, roles, allowed_tools |

### 2.2 Dependencias Instaladas

```toml
# pyproject.toml
anthropic>=0.40.0          # ✅ SDK con soporte MCP built-in
crewai>=0.100.0            # ✅ MCPServerAdapter disponible
crewai-tools>=0.20.0       # ✅ StdioServerParameters disponible
openai>=1.58.0             # ✅
litellm>=1.83.0            # ✅
```

### 2.3 Tablas de Base de Datos

| Tabla | Proposito | Relevancia MCP |
|-------|-----------|----------------|
| `org_mcp_servers` | Config de servidores MCP externos | Solo para cliente |
| `agent_catalog` | Definición de agentes | ⚠️ Podría exponer agentes via MCP |
| `workflow_templates` | Templates de workflows | ⚠️ Podría listar como tools |
| `tasks` | Ejecuciones de flows | ✅ Listo para polling |
| `pending_approvals` | HITL approvals | ✅ Necesario para flujos largos |

### 2.4 Endpoints Existentes

```
POST /webhooks/trigger       # Ejecutar flow
GET  /tasks/{task_id}        # Polling estado
POST /flows/{flow_type}/run  # Ejecutar flow específico
GET  /flows/available        # Listar flows
GET  /flows/hierarchy        # Jerarquía de flows
GET  /agents/{id}/detail     # Métricas de agente
POST /approvals/{task_id}    # Procesar HITL
```

---

## 3. ARQUITECTURA MCP: CLIENTE vs SERVIDOR

### 3.1 Lo que existe (Cliente MCP) ✅

```
┌─────────────────────────────────────────────────────────────┐
│                          FAP                                 │
│  ┌─────────────┐                                           │
│  │  MCPPool    │──→ Konsume herramientas de               │
│  │  (CLIENTE)  │   servidores MCP externos                  │
│  └─────────────┘   (ej: Claude Desktop, etc)              │
│                                                              │
│  src/tools/mcp_pool.py                                      │
│  - StdioServerParameters + MCPServerAdapter                 │
│  - Circuit breaker, retry, auto-reconnect                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Lo que falta (Servidor MCP) ❌

```
┌─────────────────────────────────────────────────────────────┐
│  Agente Externo (Claude)                                    │
│  ┌──────────────┐                                            │
│  │ Claude       │                                            │
│  │ Desktop/API  │                                            │
│  └──────┬───────┘                                            │
│         │ stdio/SSE                                          │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              FAP MCP SERVER (NUEVO) ❌                  ││
│  │                                                          ││
│  │  Tools expuestas:                                        ││
│  │  - execute_flow(flow_type, input_data)                  ││
│  │  - list_flows()                                         ││
│  │  - get_task_status(task_id)                             ││
│  │  - list_pending_approvals()                              ││
│  │  - approve_task(task_id, decision)                      ││
│  │  - list_agents()                                        ││
│  │                                                          ││
│  │  Auth: JWT Supabase por request                          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Diferencias Clave

| Aspecto | Cliente MCP | Servidor MCP |
|---------|------------|--------------|
| Dirección | Consumo | Exposición |
| Transporte | Stdio (solo) | Stdio + SSE |
| Auth | Por org (config) | JWT por request |
| Herramientas | Externas | Internas (Flows, Tasks, Agents) |
| Ubicación | `src/tools/mcp_pool.py` | `src/mcp/server.py` (NUEVO) |

---

## 4. ELEMENTOS FALTANTES

### 4.1 Servidor MCP Principal (CRÍTICO)

| Prioridad | Componente | Archivo |
|-----------|-----------|---------|
| 🔴 CRÍTICO | `src/mcp/server.py` | Servidor MCP que expone herramientas FAP |

**Responsabilidades:**
- Inicializar sesión MCP con Claude Desktop
- Manejar protocolo JSON-RPC 2.0
- Autenticar cada request con JWT Supabase
-Delegar ejecución a handlers internos
- Retornar resultados en formato MCP

### 4.2 Módulo de Herramientas MCP

| Prioridad | Componente | Archivo |
|-----------|-----------|---------|
| 🔴 CRÍTICO | `src/mcp/handlers.py` | Handlers para cada tool MCP |
| 🔴 CRÍTICO | `src/mcp/tools.py` | Definiciones de tools (name, description, inputSchema) |

**Tools a exponer inicialmente:**

```python
# 1. Flujos
execute_flow(flow_type: str, input_data: dict, org_id?: str)
list_flows(org_id?: str) -> list[FlowInfo]
get_flow_hierarchy(org_id?: str) -> Hierarchy

# 2. Tareas
get_task(task_id: str) -> TaskDetail
list_tasks(org_id?: str, status?: str) -> list[Task]
poll_task(task_id: str, timeout?: int) -> TaskDetail  # Para flujos largos

# 3. Aprobaciones HITL
list_pending_approvals(org_id?: str) -> list[Approval]
approve_task(task_id: str, notes?: str) -> Result
reject_task(task_id: str, notes?: str) -> Result

# 4. Agentes
list_agents(org_id?: str) -> list[AgentInfo]
get_agent_detail(agent_id: str) -> AgentDetail

# 5. Sistema
get_server_time() -> timestamp
list_capabilities() -> capabilities
```

### 4.3 Capa de Auth para MCP

| Prioridad | Componente | Archivo |
|-----------|-----------|---------|
| 🔴 CRÍTICO | `src/mcp/auth.py` | Verificación JWT para requests MCP |

**Desafío multitenant:**
- Cada request MCP debe incluir `org_id`
- Posibilidades:
  1. **Header dedicado**: `MCP-Org-ID: <org_id>` (simple)
  2. **Sesión por conexión**: Iniciar con `--org-id <id>` en CLI
  3. **Tool de切换**: `switch_organization(org_id)` tool

### 4.4 Configuración MCP

| Prioridad | Componente | Archivo |
|-----------|-----------|---------|
| 🟡 Media | Extender `src/config.py` | Agregar campos MCP |

```python
# Extensión src/config.py
class Settings(BaseSettings):
    # ... existentes ...

    # MCP Server (nuevos)
    mcp_enabled: bool = True
    mcp_transport: str = "stdio"  # stdio | sse
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765
    mcp_require_auth: bool = True
```

### 4.5 Integración SSE para Claude Web/API

| Prioridad | Componente | Archivo |
|-----------|-----------|---------|
| 🟡 Media | `src/api/routes/mcp_sse.py` | Endpoint SSE para Claude API |

Para conectar Claude via API (no Desktop):
- `GET /mcp/stream` - SSE endpoint
- Autenticación via `Authorization: Bearer <jwt>`

---

## 5. SDK ANTHROPIC MCP - CAPACIDADES EXISTENTES

El SDK `anthropic>=0.40.0` ya tiene soporte MCP integrado:

### 5.1 Módulo: `anthropic.lib.tools.mcp`

```python
# Herramientas disponibles:
from anthropic.lib.tools.mcp import (
    mcp_tool,           # Conversión sync tool → BetaFunctionTool
    async_mcp_tool,     # Conversión async tool → BetaAsyncFunctionTool
    mcp_content,        # Convertir ContentBlock MCP → Anthropic
    mcp_message,        # Convertir PromptMessage → BetaMessageParam
    mcp_resource_to_content,
    mcp_resource_to_file,
)

# Tipos MCP soportados:
from mcp.types import (
    Tool,               # Definición de tool MCP
    TextContent,        # Texto
    ImageContent,       # Imagen (jpeg, png, gif, webp)
    CallToolResult,     # Resultado de llamar tool
    ClientSession,      # Sesión MCP client
)
```

### 5.2 Uso con Claude API

```python
# Para Claude API con MCP tools:
from anthropic import Anthropic

client = Anthropic()

# Obtener tools de servidor MCP
# ( Claude se conectaría como CLIENTE a FAP como SERVIDOR )

# Pero aquí FAP es el SERVIDOR, entonces Claude Desktop
# actuaría como cliente MCP conectándose a FAP
```

### 5.3 Claude Desktop Configuration

Claude Desktop se configura para conectar a servidores MCP:

```json
// Windows: %APPDATA%\Claude\claude_desktop_config.json
{
  "mcpServers": {
    "fap": {
      "command": "python",
      "args": ["-m", "src.mcp.server", "--org-id", "<org_id>"],
      "env": {
        "ANTHROPIC_API_KEY": "..."
      }
    }
  }
}
```

---

## 6. IMPLEMENTACIÓN RECOMENDADA

### 6.1 Estructura de Archivos

```
src/
├── mcp/                      # NUEVO DIRECTORIO
│   ├── __init__.py
│   ├── server.py             # Main MCP server (StdioServer)
│   ├── handlers.py           # Tool handlers (execute_flow, etc)
│   ├── tools.py              # Tool definitions (name, schema)
│   ├── auth.py               # JWT verification
│   ├── config.py             # MCP settings
│   └── exceptions.py         # Custom exceptions
```

### 6.2 Dependencias Requeridas

```toml
# pyproject.toml - agregar:
[project.optional-dependencies]
mcp = [
    "mcp>=1.0.0",  # SDK oficial MCP (ya en crewai-tools)
]
```

El paquete `mcp` ya está disponible como dependencia transitiva de `crewai-tools>=0.20.0`.

### 6.3 Plan de Implementación por Fases

#### Fase 1: Servidor MCP Básico ⏱️ 2h
```
src/mcp/__init__.py
src/mcp/server.py           # StdioServer básico
src/mcp/exceptions.py
Test: python -m src.mcp.server --help
```

#### Fase 2: Tools Fundamentales ⏱️ 3h
```
src/mcp/tools.py            # Definiciones de tools
src/mcp/handlers.py         # Handlers concretos
Test: list_flows via MCP
```

#### Fase 3: Auth y Multi-Tenant ⏱️ 2h
```
src/mcp/auth.py             # JWT verification
src/mcp/config.py           # Settings
Integrar con middleware.py existente
```

#### Fase 4: Ejecución de Flows ⏱️ 2h
```
Handler de execute_flow
Integración con FlowRegistry
Polling de tasks
```

#### Fase 5: HITL Approvals ⏱️ 1h
```
Handlers de approval
list_pending_approvals
approve/reject_task
```

#### Fase 6: Configuración Claude Desktop ⏱️ 1h
```
Documentación de configuración
Scripts de setup
```

---

## 7. MANEJO DE ERRORES

### 7.1 Errores MCP

```python
# src/mcp/exceptions.py
class MCPError(Exception):
    """Error base MCP."""
    code: int = -32603  # Internal error

class MCPNotFoundError(MCPError):
    code = -32602  # Invalid params

class MCPAuthError(MCPError):
    code = -32601  # Method not found (o nuevo código)

class MCPFlowError(MCPError):
    """Error ejecutando flow."""
    code = -32603
```

### 7.2 Mapeo de Excepciones FAP → MCP

| Excepción FAP | Excepción MCP | Código |
|---------------|---------------|--------|
| `ValueError` | `MCPNotFoundError` | -32602 |
| `HTTPException(401)` | `MCPAuthError` | -32601 |
| `HTTPException(404)` | `MCPNotFoundError` | -32602 |
| `FlowError` | `MCPFlowError` | -32603 |

---

## 8. AUTENTICACIÓN Y SEGURIDAD

### 8.1 Opciones de Auth para Servidor MCP

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| **JWT por header** | Simple, flexible | Header puede ser largo |
| **Sesión por CLI** | Seguro, claro | Una conexión = una org |
| **Tool de switch** | Dinámico | Complejo de implementar |

### 8.2 Implementación Recomendada

Para Claude Desktop (local):
- Usar `--org-id` como argumento CLI
- El servidor valida el JWT al iniciar (opcional)

```bash
python -m src.mcp.server \
    --org-id <org_uuid> \
    --jwt-secret <supabase_jwt_secret>
```

Para Claude API (remoto):
- Header `Authorization: Bearer <supabase_jwt>`
- Header `X-Org-ID: <org_uuid>`

### 8.3 Verificación de JWT

```python
# src/mcp/auth.py
async def verify_mcp_request(token: str, org_id: str) -> dict:
    """Verifica JWT y retorna claims."""
    from jose import jwt
    from src.config import get_settings

    settings = get_settings()
    claims = jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"]
    )

    # Verificar org_id pertenece al usuario
    if claims.get("org_id") != org_id:
        raise MCPAuthError("Org ID mismatch")

    return claims
```

---

## 9. CASOS DE USO PRÁCTICOS

### 9.1 Caso: Claude Ejecuta un Flow

```
Usuario: "Claude, genera una cotización para el evento del sábado"
↓
Claude identifica tool: execute_flow(flow_type="bartenders_preventa")
↓
Claude llama MCP: tools/call
  {
    name: "execute_flow",
    arguments: {
      flow_type: "bartenders_preventa",
      input_data: {
        fecha_evento: "2026-04-18",
        provincia: "Tucuman",
        localidad: "San Miguel de Tucuman",
        tipo_evento: "corporativo",
        pax: 150,
        duracion_horas: 6,
        tipo_menu: "premium"
      }
    }
  }
↓
 FAP retorna task_id y correlation_id
↓
 Claude puede hacer poll_task() para obtener resultado
```

### 9.2 Caso: Claude Consulta Estados

```
Usuario: "Cuál es el estado del pedido #123?"
↓
Claude llama MCP: tools/call
  { name: "get_task", arguments: { task_id: "uuid-123" } }
↓
 FAP retorna: { status, result, output_data, etc }
```

### 9.3 Caso: Aprobación HITL

```
Flow requiere aprobación (precio > $10,000)
↓
 FAP pausa, retorna task con status AWAITING_APPROVAL
↓
 Claude list_pending_approvals()
↓
 Claude presenta al usuario
↓
 Usuario: "Apruébalo"
↓
 Claude approve_task(task_id, notes="Aprobado por director")
```

---

## 10. GAPS CRÍTICOS IDENTIFICADOS

### 10.1 Elementos Completamente Faltantes

| # | Elemento | Prioridad | Impacto |
|---|----------|-----------|---------|
| 1 | Servidor MCP (`src/mcp/server.py`) | 🔴 CRÍTICO | No hay forma de conectar Claude |
| 2 | Handlers de tools | 🔴 CRÍTICO | No hay implementación de operaciones |
| 3 | Auth para MCP | 🔴 CRÍTICO | No hay seguridad en requests |
| 4 | Tool definitions | 🔴 CRÍTICO | Claude no sabe qué operaciones existen |

### 10.2 Elementos Parcialmente Existentes

| # | Elemento | Estado | Gap |
|---|----------|--------|-----|
| 1 | FlowRegistry | ✅ | No tiene interfaz MCP |
| 2 | Tasks API | ✅ | No hay endpoint de polling eficiente |
| 3 | HITL approvals | ✅ | No hay forma de consultarlos via MCP |
| 4 | Auth JWT | ✅ | No está adaptado para MCP |

### 10.3 Elementos Listos para Reutilizar

| # | Elemento | Por qué está listo |
|---|----------|-------------------|
| 1 | `flow_registry.list_flows()` | Ya existe, solo exponer |
| 2 | `flow_registry.get_metadata()` | Input schemas ya definidos |
| 3 | `BaseFlow.execute()` | Listo para ejecutar |
| 4 | `flow.resume()` | Para HITL approvals |
| 5 | JWT verification | Reutilizar lógica de `middleware.py` |
| 6 | TenantClient | Para queries multitenant |

---

## 11. CONFIGURACIÓN CLAUDE DESKTOP (Windows)

### 11.1 Ubicación del Config

```
%APPDATA%\Claude\claude_desktop_config.json
```

### 11.2 Configuración Sugerida

```json
{
  "mcpServers": {
    "FluxAgentPro": {
      "command": "D:\\Develop\\Personal\\FluxAgentPro-v2\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "src.mcp.server",
        "--org-id",
        "YOUR_ORG_ID_HERE"
      ],
      "env": {
        "SUPABASE_URL": "https://tmlotwntptmilycvtfoo.supabase.co",
        "SUPABASE_SERVICE_KEY": "YOUR_SERVICE_KEY"
      }
    }
  }
}
```

### 11.3 Verificación

Después de configurar, reiniciar Claude Desktop y decir:

```
"Qué flows están disponibles en FAP?"
```

Debería retornar la lista de flows registrados.

---

## 12. COMPARACIÓN CON ANÁLISIS PREVIOS

Este análisis difiere de análisis anteriores en:

| Aspecto | Análisis Previos | Este Análisis |
|---------|-----------------|--------------|
| Enfoque | Genérico MCP | Específico Claude Desktop |
| SDK | Sugerían instalar | Ya instalado (`anthropic>=0.40.0`) |
| Auth | Conceptual | Detallado (JWT, headers, CLI) |
| Tools | Parcial | Completo con casos de uso |
| Implementación | Roadmap | Estructura de archivos exacta |

---

## 13. RECOMENDACIONES

### 13.1 Prioridad Alta

1. **Crear `src/mcp/`** con estructura básica
2. **Implementar `server.py`** con StdioServer del MCP SDK
3. **Exponer `list_flows`** como primera tool
4. **Crear auth simple** con `--org-id` CLI arg

### 13.2 Prioridad Media

1. **Implementar `execute_flow`**
2. **Agregar polling para tasks largas**
3. **Soportar HITL approvals**

### 13.3 Prioridad Baja (Post-MVP)

1. **SSE para Claude API**
2. **Dashboard de configuración MCP**
3. **Rate limiting avanzado**

---

## 14. CONCLUSIÓN

FAP tiene una base sólida para convertirse en un proveedor MCP para Claude. El código existente (`FlowRegistry`, `BaseFlow`, auth JWT, multitenant) puede reutilizarse directamente. Lo único faltante es la capa de servidor MCP que conecte estas piezas.

El SDK de Anthropic ya incluye soporte MCP, por lo que no hay dependencias adicionales que instalar.

La implementación sugerida es incremental: comenzar con un servidor básico que exponga `list_flows`, luego agregar `execute_flow`, y finalmente completar con auth y HITL.

---

## 15. PRÓXIMOS PASOS INMEDIATOS

1. Crear directorio `src/mcp/`
2. Crear `src/mcp/__init__.py`
3. Crear `src/mcp/server.py` con StdioServer básico
4. Crear `src/mcp/tools.py` con definiciones iniciales
5. Crear `src/mcp/handlers.py` con `list_flows` implementado
6. Probar manualmente: `python -m src.mcp.server`
7. Configurar Claude Desktop
8. Probar "qué flows hay disponibles?"

---

*Análisis generado: 2026-04-13*
*Proyecto: FluxAgentPro-v2*
*Autor: Claude Code (análisis exhaustivo)*
