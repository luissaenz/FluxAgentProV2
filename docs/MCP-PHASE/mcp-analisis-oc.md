# Análisis Exhaustivo: Integración FAP ↔ Agente Externo vía MCP

## 1. Estado Actual del Proyecto

### 1.1 Infraestructura Existente

| Componente | Archivo | Estado | Notas |
|-----------|--------|--------|-------|
| FastAPI Gateway | `src/api/main.py` | ✅ Operativo | Rutas: webhooks, tasks, flows, chat, agents |
| FlowRegistry | `src/flows/registry.py` | ✅ Funcional | Registro decorator, validación dependencias |
| ToolRegistry | `src/tools/registry.py` | ✅ Funcional | Metadatos (timeout, retry, tags) |
| BaseFlow | `src/flows/base_flow.py` | ✅ Completo | Lifecycle, HITL, persistencia |
| MCPPool | `src/tools/mcp_pool.py` | ✅ Implementado | Cliente MCP (consume herramientas externas) |
| Auth/JWT | `src/api/middleware.py` | ✅ ES256+HS256 | verify_org_membership |
| TenantClient | `src/db/session.py` | ✅ RLS | set_config via RPC |
| Config | `src/config.py` | ✅ Multiple LLM | groq, openrouter, openai, anthropic |

### 1.2 Endpoints Disponibles

```python
# Rutas principales
POST /webhooks/trigger       # Ejecutar flow (202 Accepted)
GET  /tasks/{task_id}       # Polling de estado
GET  /flows/available      # Listar flows registrados
POST /flows/{flow_type}/run # Ejecutar flow específico
POST /chat/architect       # Flow conversacional (ArchitectFlow)
GET  /agents/{id}/detail   # Métricas de agente
```

### 1.3 Código Protegido (NO modificar)

- `src/crews/` - Implementaciones CrewAI
- `src/flows/multi_crew_flow.py` - Flujos multi-agente
- Tests en `tests/unit/test_base_crew.py`, `tests/integration/test_multi_crew_flow.py`

---

## 2. Elementos Existentes para MCP

### 2.1 MCPPool (Cliente)

```python
# src/tools/mcp_pool.py
class MCPPool:
    async def get_tools(org_id, server_name) -> list:
        # Conecta a servidor MCP externo
        # Usa StdioServerParameters + MCPServerAdapter
```

**Estado:** Cliente consumidor, NO servidor expositor.

### 2.2 Dependencias en pyproject.toml

```toml
[dependencies]
# Ya instaladas
fastapi>=0.115.0
pydantic>=2.10.0

# NO instaladas (requieren extra "crew")
# crewai>=0.100.0
# crewai-tools>=0.20.0  # ← Contiene MCPServerAdapter
```

### 2.3 Tabla org_mcp_servers

Existe en DB para configurar servidores MCP por organización.

---

## 3. Elementos Faltantes para Integración Agéntica

### 3.1 Servidor MCP (Expositor) — CRÍTICO

| Prioridad | Componente | Descripción |
|----------|-----------|-------------|
| 🔴 Alta | `src/mcp/server.py` | Servidor MCP que expone herramientas FAP |

**Requisitos:**
- Usar `@modelcontextprotocol/sdk` o implementación manual stdio
- Exponer tools derivadas de FlowRegistry
- Manejar auth (JWT Supabase)

### 3.2 Traductor Flow → Tool MCP

| Prioridad | Componente | Descripción |
|----------|-----------|-------------|
| 🔴 Alta | `src/mcp/flow_to_tool.py` | Convierte flows registrados en tools MCP |

**Funcionalidad:**
```python
def flow_to_mcp_tool(flow_name: str) -> Tool:
    """Convierte flow a tool con:
    - name: nombre del flow
    - description: del metadata
    - input_schema: del FlowInputSchema
    """
```

### 3.3 Esquemas de Input por Flow

| Prioridad | Componente | Descripción |
|----------|-----------|-------------|
| 🟡 Media | `src/flows/schemas.py` | Definir input schemas Pydantic por flow |

**Estado actual:** schemas definidos manualmente en `src/api/routes/flows.py`

### 3.4 Endpoint SSE / Streaming

| Prioridad | Componente | Descripción |
|----------|-----------|-------------|
| 🟡 Media | `src/api/routes/events.py` | Server-Sent Events para streaming |

Para flujos largos con HITL.

---

## 4. Análisis de Gap: Cliente vs Servidor MCP

### 4.1 Lo que existe (Cliente)

```
FAP (MCPPool) → Servidor MCP Externo → Herramientas
```

### 4.2 Lo que falta (Servidor)

```
Agente Externo (Claude) → Servidor MCP FAP → Flows
                     → Tasks
                     → Agents
```

### 4.3 Diferencias Clave

| Aspecto | Cliente MCP | Servidor MCP |
|---------|------------|------------|
| Dirección | Consumo | Exposición |
| Transporte | Stdio | Stdio + SSE |
| Auth | Por org | JWT por request |
| Herramientas | Externas | Internas (Flows) |

---

## 5. Roadmap de Implementación

### Fase 1: Servidor MCP Básico ⏱️ 2h

```
1.1 Crear src/mcp/__init__.py
1.2 Crear src/mcp/server.py (Stdio)
1.3 Agregar mcp-model a pyproject.toml
1.4 Test: python -m src.mcp.server
```

### Fase 2: Exposición de Flows ⏱️ 3h

```
2.1 Crear src/mcp/flow_to_tool.py
2.2 Mapear FlowRegistry → tools
2.3 Agregar input schemas
2.4 Test: listar tools disponibles
```

### Fase 3: Auth y Contexto ⏱️ 2h

```
3.1 Integrar JWT verification
3.2 Manejo de org_id por sesión
3.3 Rate limiting
3.4 Logging/Monitoring
```

### Fase 4: Integración Agente Externo ⏱️ 1h

```
4.1 Configurar Claude Desktop
4.2 Test end-to-end
4.3 Documentación
```

---

## 6. Dependencias a Instalar

```toml
[project.optional-dependencies]
mcp = [
    "mcp>=1.0.0",  # SDK oficial
]
```

O usar implementación manual stdio sin dependencia adicional.

---

## 7. Consideraciones de Arquitectura

### 7.1 Patrón de Ejecución

```
Claude → MCP Server (stdio)
           ↓
    FlowRegistry.get(flow_name)
           ↓
    BaseFlow.execute(input_data)
           ↓
    Task/Polling o Callback
```

### 7.2 Modos de Operación

| Modo | Uso | Timeout |
|------|-----|--------|
| Sincrónico | Flows < 30s | 60s |
| Asincrónico | Flows largos | No aplica |
| Streaming | HITL | SSE |

### 7.3 Aislamiento

- Cada request incluye `X-Org-ID` header
- TenantClient inyecta org_id antes de queries
- RLS filtra datos

---

## 8. Archivo de Configuración suggested

`src/mcp/config.py`:

```python
class MCPConfig(BaseSettings):
    enabled: bool = True
    transport: str = "stdio"  # stdio | sse
    require_auth: bool = True
    allowed_orgs: List[str] = []  # vacio = todas
```

---

## 9. Test de Concepto

### 9.1 Herramientas a Exponer Inicialmente

```python
# tools = [
#     "execute_flow",      # ejecutar flow por nombre
#     "list_flows",      # listar flows disponibles
#     "get_task",       # obtener estado de task
#     "list_tasks",     # listar tasks
# ]
```

### 9.2 Ejemplo de Sesión

```bash
$ python -m src.mcp.server --org-id org_123

# Claude envía:
# {"jsonrpc": "2.0", "method": "tools/list", ...}

# FAP responde:
# {"jsonrpc": "2.0", "result": [{"name": "execute_flow", ...}]}
```

---

## 10. Conclusión

### Elementos Críticos Faltantes

1. **Servidor MCP** (`src/mcp/server.py`)
2. **Traductor Flow→Tool** (`src/mcp/flow_to_tool.py`)
3. **Input Schemas** definidos consistentemente
4. **Dependencia MCP SDK** en pyproject.toml

### Elementos de Soporte

5. Endpoint SSE para streaming
6. MCPConfig en src/config.py
7. Tests de integración

### Elementoslistos para Reutilizar

- FlowRegistry ✅
- ToolRegistry ✅
- Auth/JWT ✅
- TenantClient ✅
- Endpoints existentes ✅

---

*Análisis generado para OpenCode - FluxAgentPro-v2*