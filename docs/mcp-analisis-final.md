# Análisis Final Consolidado: Ecosistema Agéntico FAP ↔ MCP

## 1. Resumen Ejecutivo (Visión 2026)

FluxAgentPro (FAP) ha demostrado ser una plataforma robusta para la orquestación de agentes internos. Este análisis confirma que la infraestructura actual está preparada para evolucionar de un sistema cerrado a un **Ecosistema Agéntico Abierto** mediante el **Model Context Protocol (MCP)**. 

FAP no solo expondrá herramientas de ejecución, sino que actuará como un **Productor de Agentes y Workflows** para entidades externas (como Claude, agML o agentes autónomos en el edge), consolidándose como el "Sistema Operativo" de la automatización empresarial multitenant.

> [!NOTE]
> Este documento unifica los análisis técnicos de **ATG, Claude, Kilo y OC**. Cada sección referencia la fuente original cuando corresponde.

---

## 2. Estado del Arte en el Proyecto

| Componente | Archivo Principal | Rol en MCP | Nivel de Madurez |
| :--- | :--- | :--- | :--- |
| **ArchitectFlow** | `src/flows/architect_flow.py` | Generador de Tools | ✅ **ALTA** (Listo para integrar como System Tool) |
| **FlowRegistry** | `src/flows/registry.py` | Catálogo de Capacidades | ✅ **ALTA** (Requiere interfaz de reflexión) |
| **MCPPool** | `src/tools/mcp_pool.py` | Consumidor de Edge | ✅ **ALTA** (Probado como cliente) |
| **TenantClient** | `src/db/session.py` | Aislamiento RLS | ✅ **PRODUCCIÓN** (Base de la seguridad MCP) |
| **BaseFlow** | `src/flows/base_flow.py` | Orquestador HITL | ✅ **ALTA** (Protocolo de pausa/reinicio listo) |
| **Auth/JWT** | `src/api/middleware.py` | Verificación ES256+HS256 | ✅ **PRODUCCIÓN** (Reutilizable para MCP) |
| **ToolRegistry** | `src/tools/registry.py` | Metadatos de herramientas | ✅ **FUNCIONAL** (Timeout, retry, tags) |
| **Config** | `src/config.py` | LLM Multiple Provider | ✅ **FUNCIONAL** (Anthropic SDK ≥0.40.0 con soporte MCP built-in) |

### 2.1 Elementos Listos para Reutilizar
*(Ref: Claude §10.3, OC §10)*

| # | Componente | Por qué está listo |
|---|----------|-------------------|
| 1 | `flow_registry.list_flows()` | Ya existe, solo exponer como tool |
| 2 | `flow_registry.get_metadata()` | Retorna `depends_on` y `category` (⚠️ no incluye `description` ni `input_schema` — ver §3.4) |
| 3 | `FLOW_INPUT_SCHEMAS` | Diccionario estático en `src/api/routes/flows.py` con JSON Schemas por flow_type |
| 4 | `BaseFlow.execute()` | Listo para ejecutar desde handler |
| 5 | `flow.resume()` | Para HITL approvals |
| 6 | JWT verification | Reutilizar `verify_supabase_jwt()` de `middleware.py` (PyJWT + JWKS) |
| 7 | TenantClient | Para queries multitenant |

### 2.2 Dependencias Ya Instaladas
*(Ref: Claude §2.2)*

```toml
# pyproject.toml — dependencias principales
anthropic>=0.40.0          # SDK con soporte MCP built-in

# pyproject.toml — [project.optional-dependencies] → crew
# ⚠️ NOTA: crewai y crewai-tools son OPCIONALES. Requieren:
#   pip install -e ".[crew]"  o  uv sync --extra crew
crewai>=0.100.0            # MCPServerAdapter disponible
crewai-tools>=0.20.0       # StdioServerParameters + mcp>=1.0.0 transitivo

# ⚠️ PENDIENTE: Agregar como dependencia directa para el MCP Server:
# mcp>=1.0.0                # SDK MCP (actualmente solo transitiva via crewai-tools)
```

### 2.3 Tablas de Base de Datos Relevantes
*(Ref: Claude §2.3)*

| Tabla | Propósito | Relevancia MCP |
|-------|-----------|----------------|
| `org_mcp_servers` | Config de servidores MCP por org | ✅ Registro de integraciones outbound |
| `secrets` | Credenciales cifradas (RLS: solo `service_role`) | ✅ Vault de secretos per-tenant |
| `agent_catalog` | Definición de agentes | ⚠️ Exponer agentes vía MCP |
| `workflow_templates` | Templates de workflows | ⚠️ Listar como tools |
| `tasks` | Ejecuciones de flows | ✅ Listo para polling |
| `pending_approvals` | HITL approvals | ✅ Necesario para flujos largos |
| `service_catalog` | Catálogo global de servicios TIPO C | 🆕 **NUEVO** — Ver §10.5 |
| `org_service_integrations` | Integraciones TIPO C per-org | 🆕 **NUEVO** — Ver §10.5 |
| `service_tools` | Tools individuales por servicio | 🆕 **NUEVO** — Ver §10.5 |

---

## 3. Arquitectura del Servidor MCP (FAP-X)

### 3.1 Entry Point y Transporte
Se implementará un servidor dual en `src/mcp/server.py`:
- **Stdio**: Para integración nativa de ultra-baja latencia con Claude Desktop.
- **SSE (Server-Sent Events)**: Para integración remota y dashboards agénticos.

> [!IMPORTANT]
> Se utilizará el SDK oficial de MCP (`mcp>=1.0.0`) y el `MCPServerAdapter` de `crewai-tools` para garantizar compatibilidad total con el estándar JSON-RPC 2.0.

### 3.2 Estructura del Módulo
*(Ref: OC §9, Claude §6.1)*

```
src/mcp/                      # NUEVO DIRECTORIO
├── __init__.py
├── server.py                 # Main MCP server (StdioServer + SSE)
├── handlers.py               # Tool handlers (execute_flow, approve_task, etc.)
├── tools.py                  # Tool definitions (name, description, inputSchema)
├── flow_to_tool.py           # Traductor dinámico FlowRegistry → MCP Tools
├── auth.py                   # JWT verification + context bridge multitenant
├── config.py                 # MCP-specific settings
└── exceptions.py             # Custom exceptions con códigos JSON-RPC
```

### 3.3 Catálogo Completo de Herramientas MCP
*(Ref: Claude §4.2, ATG §2.2, OC §9.1)*

#### A. Herramientas de Flujos

| Tool | Input Schema | Output | Modo |
|------|-------------|--------|------|
| `list_flows` | `{org_id?: str}` | `FlowInfo[]` | Sync |
| `execute_flow` | `{flow_type: str, input_data: dict}` | `{task_id, correlation_id}` | Async |
| `get_flow_hierarchy` | `{org_id?: str}` | `Hierarchy` | Sync |

#### B. Herramientas de Tareas

| Tool | Input Schema | Output | Modo |
|------|-------------|--------|------|
| `get_task` | `{task_id: str}` | `TaskDetail` | Sync |
| `list_tasks` | `{org_id?: str, status?: str}` | `Task[]` | Sync |
| `poll_task` | `{task_id: str, timeout?: int}` | `TaskDetail` | Long-poll |

#### C. Herramientas de Aprobaciones HITL

| Tool | Input Schema | Output | Modo |
|------|-------------|--------|------|
| `list_pending_approvals` | `{org_id?: str}` | `Approval[]` | Sync |
| `approve_task` | `{task_id: str, notes?: str}` | `Result` | Sync |
| `reject_task` | `{task_id: str, notes?: str}` | `Result` | Sync |

#### D. Herramientas de Agentes

| Tool | Input Schema | Output | Modo |
|------|-------------|--------|------|
| `list_agents` | `{org_id?: str}` | `AgentInfo[]` | Sync |
| `get_agent_detail` | `{agent_id: str}` | `AgentDetail` | Sync |

#### E. Herramientas de Sistema (Integración Arquitectónica)

| Tool | Input Schema | Output | Modo |
|------|-------------|--------|------|
| `create_workflow` | `{description: str}` | `WorkflowDef` | Async |
| `list_capabilities` | `{}` | `Capabilities` | Sync |
| `get_server_time` | `{}` | `timestamp` | Sync |

> [!TIP]
> La tool `create_workflow` llama a **ArchitectFlow** para generar un nuevo flujo desde lenguaje natural. Claude podrá "auto-mejorar" el sistema creando sus propias herramientas — FAP se construye a sí misma vía diálogo con el agente.

### 3.4 Traductor Flow-to-Tool
*(Ref: OC §3.2, ATG §2.2)*

> [!WARNING]
> **Corrección v3.3**: `FlowRegistry.get_metadata()` solo retorna `{depends_on, category}`. No contiene `description` ni `input_schema`. Los input schemas están definidos en `FLOW_INPUT_SCHEMAS` (`src/api/routes/flows.py:70-130`). El traductor debe combinar ambas fuentes.

```python
# src/mcp/flow_to_tool.py
from src.flows.registry import flow_registry
from src.api.routes.flows import FLOW_INPUT_SCHEMAS  # JSON Schemas estáticos

def flow_to_mcp_tool(flow_name: str) -> Tool:
    """Convierte un flow registrado en una tool MCP tipada.
    
    Combina dos fuentes de metadata:
    1. FlowRegistry.get_metadata() → depends_on, category
    2. FLOW_INPUT_SCHEMAS → JSON Schema de input (definido en routes/flows.py)
    """
    metadata = flow_registry.get_metadata(flow_name)
    input_schema = FLOW_INPUT_SCHEMAS.get(flow_name, {
        "type": "object",
        "properties": {},
    })
    
    return Tool(
        name=flow_name,
        description=f"Ejecutar flow: {flow_name.replace('_', ' ').title()}"
                    f" (categoría: {metadata.get('category', 'general')})",
        inputSchema=input_schema,
    )
```

> [!TIP]
> **Mejora futura (pre-Fase 2)**: Enriquecer `FlowRegistry.register()` para aceptar `description` y un schema Pydantic directamente, eliminando la dependencia de `FLOW_INPUT_SCHEMAS`.

### 3.5 Modos de Operación
*(Ref: OC §7.2)*

| Modo | Uso | Timeout | Herramientas Asociadas |
|------|-----|---------|----------------------|
| **Sincrónico** | Flows < 30s | 60s | `list_flows`, `list_agents`, `get_task` |
| **Asincrónico** | Flows largos | N/A (polling) | `execute_flow` → `poll_task` |
| **Streaming** | HITL / Aprobaciones | SSE | `list_pending_approvals` → `approve_task` |

---

## 4. Desafío: El Puente de Identidad (Auth Bridge)
*(Ref: ATG §3.A, Claude §8)*

### 4.1 Problema
Para mantener el aislamiento multitenant, el servidor MCP implementará un decorador de contexto en `src/mcp/auth.py`. A diferencia de un servidor MCP tradicional (diseñado para sesiones de usuario único), FAP es multi-empresa.

### 4.2 Opciones de Identidad

| Opción | Ventajas | Desventajas | Recomendación |
|--------|----------|-------------|---------------|
| **CLI `--org-id`** | Seguro, claro, una sesión = una org | Requiere reiniciar para cambiar org | ✅ **Para Claude Desktop** |
| **Header `X-Org-ID`** | Flexible, dinámico | Header puede ser largo | ✅ **Para Claude API/SSE** |
| **Tool `switch_org`** | Dinámico sin reinicio | Complejo, riesgo de fuga de contexto | ⚠️ Post-MVP |

### 4.3 Implementación del Auth Bridge

> [!WARNING]
> **Corrección v3.3**: El middleware real (`src/api/middleware.py`) usa **PyJWT** con soporte ES256 (JWKS) + HS256, NO `python-jose`. El Auth Bridge MCP debe reutilizar la misma librería y el singleton `_get_jwks_client()` para consistencia y soporte de key rotation.

```python
# src/mcp/auth.py
import jwt as pyjwt  # PyJWT — misma librería que middleware.py
from src.config import get_settings
from src.api.middleware import _get_jwks_client  # Reutiliza JWKS singleton
from src.db.session import get_service_client
from .exceptions import MCPAuthError


async def verify_mcp_request(token: str, org_id: str) -> dict:
    """Verifica JWT Supabase y retorna claims.
    
    Reutiliza la misma lógica de verify_supabase_jwt() de middleware.py:
    - ES256: Verifica vía JWKS endpoint (proyectos Supabase nuevos)
    - HS256: Verifica vía JWT secret (proyectos legacy)
    """
    settings = get_settings()
    issuer = f"{settings.supabase_url}/auth/v1"

    # Detectar algoritmo del header JWT
    header = pyjwt.get_unverified_header(token)
    alg = header.get("alg", "").upper()

    if alg == "ES256":
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        claims = pyjwt.decode(
            token, signing_key, algorithms=["ES256"],
            issuer=issuer, options={"verify_aud": False}
        )
    elif alg == "HS256":
        claims = pyjwt.decode(
            token, settings.supabase_jwt_secret,
            algorithms=["HS256"], issuer=issuer,
            options={"verify_aud": False}
        )
    else:
        raise MCPAuthError(f"Unsupported JWT algorithm: {alg}")

    # Verificar que el user pertenece a la org
    user_id = claims.get("sub")
    if not user_id:
        raise MCPAuthError("Token missing 'sub' claim")
    
    db = get_service_client()
    member = (
        db.table("org_members").select("role")
        .eq("org_id", org_id).eq("user_id", user_id)
        .eq("is_active", True).maybe_single().execute()
    )
    if not member.data:
        raise MCPAuthError(f"User {user_id} is not a member of org {org_id}")

    return {"user_id": user_id, "org_id": org_id, "role": member.data["role"]}


async def mcp_security_context(token: str, org_id: str):
    """Decorador de contexto para cada request MCP."""
    # 1. Valida JWT Supabase (ES256/HS256) + membresía org
    claims = await verify_mcp_request(token, org_id)
    # 2. El org_id viaja al TenantClient en cada handler
    # 3. RLS se configura automáticamente vía get_tenant_client(org_id)
    return claims
```

> [!CAUTION]
> Cada conexión MCP (especialmente vía Stdio) debe recibir explícitamente el `org_id` al inicio para evitar fugas de contexto entre organizaciones en entornos compartidos.

---

## 5. Manejo de Errores
*(Ref: Claude §7)*

### 5.1 Jerarquía de Excepciones

```python
# src/mcp/exceptions.py
class MCPError(Exception):
    """Error base MCP."""
    code: int = -32603  # Internal error

class MCPNotFoundError(MCPError):
    """Recurso no encontrado."""
    code = -32602  # Invalid params

class MCPAuthError(MCPError):
    """Error de autenticación/autorización."""
    code = -32601

class MCPFlowError(MCPError):
    """Error ejecutando flow."""
    code = -32603
```

### 5.2 Mapeo de Excepciones FAP → JSON-RPC

| Excepción FAP | Excepción MCP | Código JSON-RPC |
|---------------|---------------|-----------------|
| `ValueError` | `MCPNotFoundError` | -32602 |
| `HTTPException(401)` | `MCPAuthError` | -32601 |
| `HTTPException(404)` | `MCPNotFoundError` | -32602 |
| `FlowError` | `MCPFlowError` | -32603 |
| `TimeoutError` | `MCPError` | -32603 |

---

## 6. Casos de Uso Prácticos
*(Ref: Claude §9)*

### 6.1 Caso 1: Claude Ejecuta un Flow de Cotización

```
Usuario: "Claude, genera una cotización para el evento del sábado"

→ Claude identifica tool: execute_flow

→ Claude llama MCP (tools/call):
  {
    "name": "execute_flow",
    "arguments": {
      "flow_type": "bartenders_preventa",
      "input_data": {
        "fecha_evento": "2026-04-18",
        "provincia": "Tucuman",
        "localidad": "San Miguel de Tucuman",
        "tipo_evento": "corporativo",
        "pax": 150,
        "duracion_horas": 6,
        "tipo_menu": "premium"
      }
    }
  }

→ FAP retorna: { "task_id": "uuid-xxx", "correlation_id": "corr-yyy" }

→ Claude hace poll_task("uuid-xxx") hasta obtener el resultado
```

### 6.2 Caso 2: Claude Consulta Estado de Pedido

```
Usuario: "¿Cuál es el estado del pedido #123?"

→ Claude llama MCP (tools/call):
  { "name": "get_task", "arguments": { "task_id": "uuid-123" } }

→ FAP retorna: { "status": "completed", "result": {...}, "output_data": {...} }
```

### 6.3 Caso 3: Flujo HITL de Aprobación Completo

```
1. Flow ejecutado requiere aprobación (precio > $10,000)
   → FAP pausa el flow, status = AWAITING_APPROVAL

2. Claude llama: list_pending_approvals()
   → FAP retorna: [{ "task_id": "uuid-456", "flow": "cotización_premium", "amount": 15000 }]

3. Claude presenta al usuario:
   "Hay una cotización de $15,000 pendiente de aprobación. ¿Apruebo?"

4. Usuario: "Sí, apruébalo"

5. Claude llama: approve_task("uuid-456", notes="Aprobado por director")
   → FAP resume el flow con la decisión
```

### 6.4 Caso 4: Auto-construcción vía ArchitectFlow

```
Usuario: "Necesito un nuevo flujo para gestionar inventario de bebidas"

→ Claude llama: create_workflow(description="Flujo de gestión de inventario...")
   → ArchitectFlow genera el flujo automáticamente
   → Se registra en FlowRegistry

→ Claude llama: list_flows() → confirma que el nuevo flujo aparece
→ Claude llama: execute_flow("inventario_bebidas", {...}) → lo ejecuta
```

---

## 7. Configuración Claude Desktop (Setup Completo)
*(Ref: Claude §11)*

### 7.1 Ubicación del Archivo de Configuración

```
Windows: %APPDATA%\Claude\claude_desktop_config.json
macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
```

### 7.2 Configuración Recomendada

```json
{
  "mcpServers": {
    "FluxAgentPro-V2": {
      "command": "D:\\Develop\\Personal\\FluxAgentPro-v2\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "src.mcp.server",
        "--org-id",
        "YOUR_ORG_UUID_HERE"
      ],
      "env": {
        "SUPABASE_URL": "https://tmlotwntptmilycvtfoo.supabase.co",
        "SUPABASE_SERVICE_KEY": "YOUR_SERVICE_KEY",
        "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_KEY"
      }
    }
  }
}
```

### 7.3 Verificación Post-Configuración

1. Reiniciar Claude Desktop
2. En el chat, preguntar:
   ```
   "¿Qué flows están disponibles en FAP?"
   ```
3. Claude debería invocar `list_flows()` y retornar los flows registrados.

> [!TIP]
> Si Claude no detecta el servidor, verificar logs en `%APPDATA%\Claude\logs\` y confirmar que el path al Python del `.venv` es correcto.

---

## 8. Configuración MCP (Settings)
*(Ref: OC §8, Claude §4.4)*

```python
# src/mcp/config.py
from pydantic import BaseSettings
from typing import List

class MCPConfig(BaseSettings):
    enabled: bool = True
    transport: str = "stdio"       # stdio | sse
    host: str = "127.0.0.1"       # Solo para SSE
    port: int = 8765              # Solo para SSE
    require_auth: bool = True
    allowed_orgs: List[str] = []  # Vacío = todas las orgs permitidas

    class Config:
        env_prefix = "MCP_"
```

### 8.1 Decisión Arquitectónica: ¿Proceso Independiente o Lifespan?
*(Ref: Kilo §Propuestas)*

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| **Proceso independiente** (`python -m src.mcp.server`) | Aislado, fácil de depurar, compatible con Claude Desktop | Requiere gestión de proceso separada |
| **Lifespan de FastAPI** (`src/api/main.py`) | Integrado, un solo despliegue | Complejidad aumentada, solo para SSE |

> [!IMPORTANT]
> **Recomendación**: Proceso independiente para Fase 1 (Stdio/Claude Desktop). Integrar al lifespan de FastAPI solo para SSE en Fase 3.

---

## 9. Gestión de Secretos en el Ecosistema MCP

### 9.1 Regla Arquitectónica Fundamental

> [!CAUTION]
> **Regla R3: Los secretos NUNCA llegan al LLM.**
>
> Esta regla ya está codificada en `src/tools/base_tool.py`, `src/db/vault.py` y `src/flows/workflow_guardrails.py`. El servidor MCP **debe** respetarla estrictamente.

### 9.2 Infraestructura Existente de Secretos

FAP ya posee un sistema maduro de gestión de secretos en producción:

| Componente | Archivo | Estado | Función |
| :--- | :--- | :--- | :--- |
| **Vault Proxy** | `src/db/vault.py` | ✅ Producción | `get_secret(org_id, name)`, `list_secrets(org_id)` |
| **Tabla `secrets`** | `migrations/002_governance.sql` | ✅ RLS: solo `service_role` SELECT | Almacén cifrado per-org |
| **OrgBaseTool** | `src/tools/base_tool.py` | ✅ Producción | `_get_secret()` encapsulado — Regla R3 |
| **MCPPool** | `src/tools/mcp_pool.py` | ✅ Producción | Resuelve `secret_name` → env var del proceso hijo |
| **Workflow Guardrails** | `src/flows/workflow_guardrails.py` | ✅ Producción | Valida herramientas peligrosas |

### 9.3 Dos Niveles de Secretos

En el contexto MCP, los secretos operan en **dos niveles distintos**:

```
┌────────────────────────────────────────────────────┐
│  NIVEL 1: Secretos de Infraestructura (Server)     │
│  ──────────────────────────────────────────────     │
│  • SUPABASE_URL, SUPABASE_SERVICE_KEY              │
│  • ANTHROPIC_API_KEY (para LLM interno)            │
│  • SUPABASE_JWT_SECRET                             │
│                                                     │
│  Fuente: .env / Variables de entorno del proceso    │
│  Consumidor: src/config.py → Settings()             │
│  Scope: Global al servidor MCP                      │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│  NIVEL 2: Secretos de Negocio (Per-Tenant)         │
│  ──────────────────────────────────────────────     │
│  • messaging_api_token (WhatsApp, Twilio)           │
│  • stripe_key (pagos)                               │
│  • smtp_password (email)                            │
│  • API keys de servicios terceros por org           │
│                                                     │
│  Fuente: Tabla `secrets` (Supabase, RLS)            │
│  Consumidor: vault.get_secret(org_id, name)         │
│  Scope: Aislado por org_id (multitenant)            │
└────────────────────────────────────────────────────┘
```

### 9.4 Matriz de Secretos

| Secreto | Nivel | Storage | Scope | Consumidor |
|:---|:---|:---|:---|:---|
| `SUPABASE_URL` | Infraestructura | `.env` | Global | `config.py` |
| `SUPABASE_SERVICE_KEY` | Infraestructura | `.env` | Global | `session.py` |
| `SUPABASE_JWT_SECRET` | Infraestructura | `.env` | Global | `middleware.py`, `auth.py` |
| `ANTHROPIC_API_KEY` | Infraestructura | `.env` | Global | `config.py` → LLM |
| `messaging_api_token` | Negocio | `secrets` table | Per-org | `OrgBaseTool._get_secret()` |
| `stripe_key` | Negocio | `secrets` table | Per-org | `OrgBaseTool._get_secret()` |
| `smtp_password` | Negocio | `secrets` table | Per-org | `OrgBaseTool._get_secret()` |
| `brave_api_key` | Negocio | `secrets` table | Per-org | `MCPPool` → env var proceso hijo |

### 9.5 Flujo de Secretos en una Request MCP

```
Claude (Agente) ──→ MCP Server ──→ auth.py (JWT + org_id)
                                      │
                                      ▼
                                  handlers.py ──→ BaseFlow.execute()
                                                      │
                                                      ▼
                                                  OrgBaseTool._run()
                                                      │
                                                      ▼
                                                  vault.get_secret("stripe_key")
                                                      │
                                                      ▼
                                              Usa secreto internamente
                                                      │
                                                      ▼
                                              Retorna: "Pago procesado: $150"
                                              (Claude NUNCA ve "sk_live_xxxxx")
```

### 9.6 Implementación en Handlers MCP

```python
# src/mcp/handlers.py — Los handlers heredan el patrón del Vault

async def handle_execute_flow(flow_type: str, input_data: dict, org_id: str):
    """Ejecuta un flow. Los secretos se resuelven DENTRO del flow."""
    
    # El handler NO toca secretos directamente.
    # Los flows/tools internos usan vault.get_secret() internamente.
    flow = flow_registry.get(flow_type)
    result = await flow.execute(
        input_data=input_data,
        org_id=org_id  # El org_id viaja al TenantClient y al Vault
    )
    
    # NUNCA retornar datos sensibles al agente
    return sanitize_output(result)
```

### 9.7 Herramientas Prohibidas vía MCP

> [!WARNING]
> Estas herramientas son **explícitamente peligrosas** si se exponen vía MCP:

| Tool Prohibida | Riesgo | Alternativa Segura |
|:---|:---|:---|
| `get_secret(name)` | Fuga de credencial al LLM | ❌ Nunca exponer |
| `set_secret(name, value)` | Inyección de credenciales | Solo vía Dashboard UI |
| `list_secrets()` | Enumeración de secretos | Exponer solo conteo, no nombres |
| `raw_sql(query)` | SQL injection | Solo vía ORM/handlers |

---

## 10. Integraciones con Plataformas Externas

### 10.1 Taxonomía de Integraciones

El ecosistema MCP de FAP tiene **tres tipos de integración** con plataformas externas:

```
                    ┌─────────────────────┐
                    │    FAP MCP Server    │
                    │     (FAP-X)         │
                    └──────┬──────────────┘
                           │
              ┌────────────┼───────────────┐
              │            │               │
              ▼            ▼               ▼
       ┌──────────┐ ┌──────────┐   ┌──────────────┐
       │ TIPO A   │ │ TIPO B   │   │ TIPO C       │
       │ Agentes  │ │ MCP Pool │   │ Service      │
       │ Inbound  │ │ Outbound │   │ Connectors   │
       └──────────┘ └──────────┘   └──────────────┘
        Claude       Brave Search    Stripe
        Gemini       GitHub           WhatsApp
        GPTs         Filesystem       SMTP
        Copilot      PostgreSQL       Google Sheets
```

### 10.2 TIPO A: Agentes Externos → FAP (Inbound)

Plataformas de IA que **consumen** FAP como servidor MCP.

| Plataforma | Transporte | Auth | Config |
|:---|:---|:---|:---|
| **Claude Desktop** | Stdio | CLI `--org-id` | `claude_desktop_config.json` |
| **Claude API** | SSE | Bearer JWT + `X-Org-ID` | API call |
| **Gemini / agML** | SSE | Bearer JWT + `X-Org-ID` | Endpoint URL |
| **Custom Agents** | SSE | Bearer JWT + `X-Org-ID` | HTTP client |

**Secretos para Inbound**: Los agentes externos no necesitan secretos almacenados en FAP. Solo requieren:
1. **JWT de Supabase** — obtenido por el agente al autenticarse
2. **org_id** — proporcionado al configurar la conexión

**Configuración del cliente**:
```python
# src/mcp/config.py — Extensión para control de acceso inbound
class MCPConfig(BaseSettings):
    # ... existente ...
    allowed_clients: list[str] = []       # Vacío = todos permitidos
    max_concurrent_sessions: int = 10
    session_timeout_seconds: int = 3600   # 1 hora
    rate_limit_per_minute: int = 60
    rate_limit_per_org: int = 120
```

### 10.3 TIPO B: FAP → Servidores MCP Externos (Outbound)

FAP como **cliente** consumiendo herramientas de servidores MCP terceros. **Ya implementado y en producción.**

#### Infraestructura Existente

| Componente | Descripción |
|:---|:---|
| `org_mcp_servers` | Tabla con config por org: `command`, `args`, `secret_name` + RLS |
| `MCPPool` | Singleton con circuit breaker (5 fallos → 60s pausa) + retry exponencial |
| `Vault` | Resuelve `secret_name` → `API_TOKEN` env var para el proceso MCP hijo |

#### Flujo de Secretos Outbound (Código Existente)

> [!WARNING]
> **Corrección v3.3**: `mcp_pool.py` importa `get_secret_async` desde `db.vault`, pero esta función **no está definida** en `vault.py` (solo existe `get_secret` síncrono). Debe crearse un wrapper async antes de la Fase 1, o verificar si existe un mecanismo implícito no documentado.

```python
# Flujo actual en mcp_pool.py (ya en producción):

# 1. Lee config del servidor MCP desde DB
config = svc.table("org_mcp_servers").select("*")
    .eq("org_id", org_id).eq("name", server_name)...

# 2. Si tiene secret_name, lo resuelve del Vault
# ⚠️ NOTA: get_secret_async no está definida en vault.py — PENDIENTE DE CREAR
if config.data.get("secret_name"):
    env["API_TOKEN"] = await get_secret_async(
        org_id, config.data["secret_name"]
    )

# 3. Conecta al MCP server externo con el token como env var
params = StdioServerParameters(
    command=config.data["command"],
    args=config.data["args"],
    env=env  # ← El secreto va como env var del proceso hijo
)
```

**Acción requerida pre-Fase 1**: Agregar a `src/db/vault.py`:
```python
async def get_secret_async(org_id: str, secret_name: str) -> str:
    """Versión async de get_secret (wrapper sobre la versión sync)."""
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_secret, org_id, secret_name)
```

#### Agregar Nueva Integración Outbound

```sql
-- 1. Registrar el servidor MCP externo
INSERT INTO org_mcp_servers (org_id, name, command, args, secret_name)
VALUES (
    'org_uuid_aquí',
    'brave-search',
    'npx',
    '["@anthropic/mcp-brave-search"]'::jsonb,
    'brave_api_key'           -- Ref indirecta al Vault
);

-- 2. Insertar el secreto correspondiente
INSERT INTO secrets (org_id, name, secret_value)
VALUES (
    'org_uuid_aquí',
    'brave_api_key',
    'BSA-xxxxxxxxxxxxxxxx'    -- El API key real
);
```

> [!TIP]
> **Patrón clave**: `org_mcp_servers.secret_name` es una **referencia indirecta** al Vault. El MCPPool nunca conoce el secreto directamente — lo resuelve en runtime mediante `get_secret_async()`.

### 10.4 TIPO C: Conectores de Servicio (vía OrgBaseTool)

Integraciones con APIs REST/HTTP convencionales (no MCP) a través de tools de CrewAI. **Patrón existente, catálogo formal nuevo (ver §10.5).**

#### Patrón Existente

```python
# src/tools/base_tool.py — Ejemplo real
class SendMessageTool(OrgBaseTool):
    name: str = "send_message"
    description: str = "Envía un mensaje de texto al número especificado."
    args_schema: Type[BaseModel] = SendMessageInput

    def _run(self, to: str, message: str) -> str:
        # 1. Obtener secreto internamente (REGLA R3)
        token = self._get_secret("messaging_api_token")
        # 2. Llamar a la API externa con el token
        # 3. Retornar solo el RESULTADO (no el token)
        return f"Mensaje enviado a {to}"
```

#### Agregar Nueva Integración de Servicio

| Paso | Acción | Dónde |
|:---|:---|:---|
| 1 | Crear tool heredando `OrgBaseTool` | `src/tools/my_tool.py` |
| 2 | Insertar secreto en Vault | `INSERT INTO secrets (...)` |
| 3 | Registrar tool en `ToolRegistry` | `@tool_registry.register(...)` |
| 4 | La tool queda disponible para flows | Automático via FlowRegistry |
| 5 | Si el flow se expone vía MCP → la tool se ejecuta internamente | Transparente |

### 10.5 Catálogo Formal de Integraciones TIPO C (Service Catalog)

> [!IMPORTANT]
> **Sección nueva — v3.2.** Resuelve el gap identificado: FAP tiene estructura formal para TIPO B (`org_mcp_servers`) pero no tenía equivalente para TIPO C. Las tools que integran APIs REST externas estaban dispersas en código sin catalogar, sin metadatos de proveedor, sin referencia estandarizada al Vault, y sin health check.

#### 10.5.1 Problema

El `ToolRegistry` existente cataloga **tools** (lo que un agente puede hacer), pero no cataloga **servicios** (la conexión con un proveedor externo). Esta distinción es clave: una integración con Stripe es una sola (una API key, un `base_url`, un health check), pero expone múltiples tools (`create_payment_intent`, `create_customer`, `list_charges`). Además, una organización puede tener Stripe habilitado y otra no — y cada una usa sus propias credenciales.

Sin un catálogo formal, un agente no puede saber qué servicios externos tiene disponibles su organización, el onboarding de un nuevo cliente requiere configuración manual dispersa, y no hay health checks ni monitoreo de conectividad.

#### 10.5.2 Solución: Tres Tablas Nuevas

La integración TIPO C se modela en tres niveles: el **servicio** (catálogo global), la **habilitación per-org**, y las **tools** individuales de cada servicio.

##### Tabla `service_catalog` (global, compartida)

Define los servicios disponibles en la plataforma. No es per-org — es el catálogo que FAP ofrece a todos los tenants.

```sql
CREATE TABLE service_catalog (
  id TEXT PRIMARY KEY,                              -- 'stripe', 'whatsapp', 'hubspot'
  name TEXT NOT NULL,                               -- 'Stripe Payments'
  category TEXT NOT NULL,                           -- 'payments', 'crm', 'messaging', 'email',
                                                    -- 'storage', 'calendar', 'analytics',
                                                    -- 'social', 'ecommerce', 'project_management',
                                                    -- 'ai', 'other'
  auth_type TEXT NOT NULL,                          -- 'oauth2', 'api_key', 'none'
  auth_scopes JSONB DEFAULT '[]'::JSONB,            -- scopes OAuth2 necesarios
  base_url TEXT NOT NULL,                           -- 'https://api.stripe.com'
  api_version TEXT,                                 -- 'v1', '2023-10', etc.
  health_check_url TEXT,                            -- endpoint para verificar conectividad
  docs_url TEXT,                                    -- link a docs oficiales del proveedor
  logo_url TEXT,                                    -- para Dashboard UI
  required_secrets TEXT[] NOT NULL DEFAULT '{}',     -- ['stripe_secret_key'] — nombres esperados
  config_schema JSONB DEFAULT '{}'::JSONB,          -- JSON Schema de config adicional per-org
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Índice para búsquedas por categoría (Dashboard UI, ArchitectFlow)
CREATE INDEX idx_service_catalog_category ON service_catalog(category);
```

##### Tabla `org_service_integrations` (per-org, con RLS)

Registra qué servicios tiene habilitados cada organización y su estado operacional.

```sql
-- ⚠️ NOTA v3.3: Verificar que la tabla `organizations` existe en el schema
-- actual antes de aplicar esta migración. No aparece en las migraciones
-- locales (001-023) pero puede existir como tabla gestionada por Supabase Auth
-- o creada externamente. Ajustar la FK si el nombre real difiere.
CREATE TABLE org_service_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  service_id TEXT NOT NULL REFERENCES service_catalog(id),
  status TEXT NOT NULL DEFAULT 'pending_setup',     -- 'pending_setup', 'active', 'error', 'disabled'
  secret_names JSONB NOT NULL DEFAULT '[]'::JSONB,  -- ['stripe_key'] — refs indirectas al Vault
  config JSONB DEFAULT '{}'::JSONB,                 -- config per-org (webhook URLs, subdomain, etc.)
  last_health_check TIMESTAMPTZ,
  last_health_status TEXT,                          -- 'ok', 'error', 'timeout'
  error_message TEXT,                               -- último error si status = 'error'
  enabled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  
  UNIQUE(org_id, service_id)                        -- una org no puede tener el mismo servicio dos veces
);

-- RLS: cada org solo ve sus propias integraciones
ALTER TABLE org_service_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation ON org_service_integrations
  USING (org_id = current_setting('app.current_org_id')::UUID);

CREATE INDEX idx_org_integrations_org ON org_service_integrations(org_id);
CREATE INDEX idx_org_integrations_status ON org_service_integrations(org_id, status);
```

##### Tabla `service_tools` (catálogo de tools por servicio)

Las tools individuales que cada servicio expone. Vincula con el `ToolRegistry` existente y almacena los metadatos necesarios para ejecución HTTP.

```sql
CREATE TABLE service_tools (
  id TEXT PRIMARY KEY,                              -- 'stripe.create_payment_intent'
  service_id TEXT NOT NULL REFERENCES service_catalog(id),
  name TEXT NOT NULL,                               -- 'Crear Intención de Pago'
  version TEXT NOT NULL DEFAULT '1.0.0',
  input_schema JSONB NOT NULL,                      -- JSON Schema de parámetros de entrada
  output_schema JSONB NOT NULL,                     -- JSON Schema de respuesta esperada
  execution JSONB NOT NULL,                         -- { "type": "http", "method": "POST",
                                                    --   "url": "https://...", "headers": {} }
  tool_profile JSONB NOT NULL,                      -- { "description": "...",
                                                    --   "example_prompt": "...",
                                                    --   "risk_level": "low|medium|high",
                                                    --   "requires_approval": true|false }
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_service_tools_service ON service_tools(service_id);
```

#### 10.5.3 Relación entre Tablas

```
service_catalog (global)          org_service_integrations (per-org)
┌──────────────────┐              ┌─────────────────────────┐
│ id: "stripe"     │──────────────│ service_id: "stripe"    │
│ name: "Stripe"   │    1:N       │ org_id: "bartenders"    │
│ category: "pay"  │              │ status: "active"        │
│ base_url: ...    │              │ secret_names: [...]     │
│ required_secrets │              └─────────────────────────┘
└──────┬───────────┘
       │ 1:N
       ▼
service_tools (global)            secrets (per-org, existente)
┌──────────────────────────┐      ┌──────────────────────┐
│ id: "stripe.create_pi"   │      │ org_id: "bartenders" │
│ service_id: "stripe"     │      │ name: "stripe_key"   │
│ execution: {POST, url..} │      │ ciphertext: "xxx"    │
│ tool_profile: {...}      │      └──────────────────────┘
└──────────────────────────┘
```

#### 10.5.4 Flujo de Ejecución en Runtime

```python
# Cuando un agente necesita ejecutar stripe.create_payment_intent:

# 1. ¿La org tiene Stripe activo?
integration = db.table("org_service_integrations") \
    .select("*").eq("org_id", org_id).eq("service_id", "stripe") \
    .eq("status", "active").single()

# 2. Obtener la definición de la tool
tool_def = db.table("service_tools") \
    .select("*").eq("id", "stripe.create_payment_intent").single()

# 3. Resolver secreto del Vault (Regla R3 — el secreto NUNCA sale de este bloque)
secret = vault.get_secret(org_id, integration["secret_names"][0])

# 4. Ejecutar la llamada HTTP
response = requests.post(
    tool_def["execution"]["url"],
    headers={
        **tool_def["execution"]["headers"],
        "Authorization": f"Bearer {secret}"
    },
    json=input_data
)

# 5. Retornar resultado sanitizado (nunca el secreto)
return sanitize(response.json())
```

#### 10.5.5 Flujo de Onboarding de un Nuevo Cliente

Cuando se onboardea una nueva organización, el catálogo formaliza el proceso:

```
1. Admin selecciona servicios en Dashboard UI
   → Consulta service_catalog para mostrar opciones disponibles

2. Por cada servicio seleccionado:
   → INSERT INTO org_service_integrations (org_id, service_id, status='pending_setup')
   → Dashboard muestra formulario dinámico basado en service_catalog.required_secrets

3. Admin ingresa las API keys del cliente
   → INSERT INTO secrets (org_id, name, ciphertext) — vía Dashboard UI (Regla R3)
   → UPDATE org_service_integrations SET status='active', secret_names=[...]

4. FAP ejecuta health check automático
   → GET service_catalog.health_check_url con el secreto
   → UPDATE org_service_integrations SET last_health_check=now(), last_health_status='ok'

5. Las tools del servicio quedan disponibles para los agentes de esa org
   → El ContextBuilder puede filtrar tools por servicios activos de la org
```

#### 10.5.6 Población Inicial del Catálogo

El catálogo se puebla desde dos fuentes:

| Fuente | Qué aporta | Formato |
|:---|:---|:---|
| **JSON canónico (NotebookLM)** | 50 tools HTTP REST verificadas | Cada `provider` → `service_catalog`, cada tool → `service_tools` |
| **MCP Registry API** | MCP servers nativos publicados | Estos van a `org_mcp_servers` (TIPO B), no a TIPO C |

Script de import para las 50 tools:
```python
# scripts/import_service_catalog.py
import json

def import_catalog(tools_json: list[dict]):
    """Importa el JSON canónico al Service Catalog."""
    
    # 1. Extraer proveedores únicos → service_catalog
    providers = {}
    for tool in tools_json:
        pid = tool["provider"].lower().replace(" ", "_")
        if pid not in providers:
            providers[pid] = {
                "id": pid,
                "name": tool["provider"],
                "category": tool["category"],
                "auth_type": tool["auth"]["type"],
                "auth_scopes": tool["auth"].get("scopes", []),
                "base_url": extract_base_url(tool["execution"]["url"]),
                "api_version": tool["version"],
                "required_secrets": [f"{pid}_api_key"],
            }
    
    # 2. Cada tool → service_tools
    for tool in tools_json:
        service_tool = {
            "id": tool["tool_id"],
            "service_id": tool["provider"].lower().replace(" ", "_"),
            "name": tool["name"],
            "version": tool["version"],
            "input_schema": tool["input_schema"],
            "output_schema": tool["output_schema"],
            "execution": tool["execution"],
            "tool_profile": tool["tool_profile"],
        }
    
    # 3. INSERT en Supabase
    # ...
```

#### 10.5.7 Simetría con TIPO B

| Aspecto | TIPO B (MCP Outbound) | TIPO C (Service Connectors) |
|:---|:---|:---|
| Catálogo global | *(no tiene, es per-org)* | `service_catalog` + `service_tools` |
| Habilitación per-org | `org_mcp_servers` | `org_service_integrations` |
| Referencia a secretos | `secret_name` → Vault | `secret_names` → Vault |
| Ejecución | MCPPool (stdio/SSE) | OrgBaseTool (HTTP) |
| Health check | Circuit breaker (reactivo) | `health_check_url` (proactivo) |
| Protocolo | JSON-RPC 2.0 (MCP) | HTTP REST |
| Registro de tools | Dinámico (MCP `tools/list`) | `service_tools` table |

#### 10.5.8 Integración con ArchitectFlow

El `service_catalog` habilita un caso de uso poderoso: cuando ArchitectFlow diseña un nuevo flujo, puede consultar qué servicios están disponibles para la org y sugerir tools concretas:

```python
# En ArchitectFlow, al diseñar un flujo:
available_services = db.table("org_service_integrations") \
    .select("service_id, status") \
    .eq("org_id", org_id).eq("status", "active").execute()

available_tools = db.table("service_tools") \
    .select("id, tool_profile") \
    .in_("service_id", [s["service_id"] for s in available_services]).execute()

# ArchitectFlow puede incluir en el prompt del LLM:
# "Las siguientes tools están disponibles para esta org: ..."
```

#### 10.5.9 Integraciones Custom (Partners/Desarrolladores)

Para servicios que no están en el catálogo pre-cargado, un desarrollador o partner sigue este proceso:

| Paso | Acción | Herramienta |
|:---|:---|:---|
| 1 | Verificar si existe MCP server nativo | Consultar MCP Registry API |
| 2a | Si existe MCP server → registrar como TIPO B | `INSERT INTO org_mcp_servers` |
| 2b | Si no existe → crear OrgBaseTool custom | Heredar `OrgBaseTool`, implementar `_run()` |
| 3 | Registrar servicio en catálogo | `INSERT INTO service_catalog` + `service_tools` |
| 4 | Cargar secretos | Dashboard UI → `INSERT INTO secrets` |
| 5 | Activar para la org | `INSERT INTO org_service_integrations` |

> [!TIP]
> El SDK para Partners (Fase 5, ya implementado) debería incluir un CLI helper: `fap-sdk register-service --openapi spec.yaml` que genere automáticamente los registros en `service_catalog` y `service_tools` a partir de una especificación OpenAPI.

### 10.6 Diagrama de Arquitectura de Integraciones

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTES EXTERNOS (TIPO A - Inbound)          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────────┐  │
│  │ Claude  │  │ Gemini  │  │ GPTs    │  │ Custom / agML    │  │
│  │ Desktop │  │ API     │  │ API     │  │ Edge Agents      │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬─────────┘  │
│       │ stdio      │ SSE       │ SSE             │ SSE        │
└───────┼────────────┼───────────┼─────────────────┼────────────┘
        │            │           │                 │
        ▼            ▼           ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  FAP-X MCP SERVER (src/mcp/)                                    │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ server.py│→ │ auth.py  │→ │handlers  │→ │ exceptions.py  │  │
│  │ Stdio+SSE│  │ JWT+RLS  │  │ .py      │  │ JSON-RPC codes │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
│       │                           │                              │
│       │     ┌─────────────────────┤                              │
│       ▼     ▼                     ▼                              │
│  ┌────────────────┐    ┌──────────────────┐                     │
│  │  .env / env    │    │  Vault           │                     │
│  │  NIVEL 1       │    │  NIVEL 2         │                     │
│  │  (infra keys)  │    │  (per-org keys)  │                     │
│  └────────────────┘    └───────┬──────────┘                     │
│                                │                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FAP Core                                                │   │
│  │                                                          │   │
│  │  FlowRegistry → BaseFlow → CrewAI Crews                 │   │
│  │       │              │          │                         │   │
│  │       │              │    ┌─────┴──────┐                 │   │
│  │       │              │    │ OrgBaseTool │──→ APIs        │   │
│  │       │              │    │ (TIPO C)    │   externas     │   │
│  │       │              │    └──────┬──────┘   Stripe       │   │
│  │       │              │           │          Twilio       │   │
│  │       │              │           ▼          SMTP         │   │
│  │       │              │    ┌──────────────────────────┐   │   │
│  │       │              │    │  SERVICE CATALOG (§10.5) │   │   │
│  │       │              │    │  service_catalog (global) │   │   │
│  │       │              │    │  service_tools (global)   │   │   │
│  │       │              │    │  org_service_integrations │   │   │
│  │       │              │    │  (per-org + RLS)          │   │   │
│  │       │              │    └──────────────────────────┘   │   │
│  │       │              ▼                                   │   │
│  │       │         ┌─────────┐                              │   │
│  │       │         │ MCPPool │──→ MCP Servers (TIPO B)     │   │
│  │       │         │(cliente)│    Brave, GitHub, FS         │   │
│  │       │         └─────────┘                              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 10.7 Pendientes de Implementación para Integraciones

| # | Item | Prioridad | Esfuerzo | Descripción |
|:---|:---|:---|:---|:---|
| 1 | Output sanitizer | 🔴 Alta | 1h | Función que garantice R3 en responses MCP |
| 2 | **Migración SQL: Service Catalog** | 🔴 **Alta** | **2h** | **Crear tablas `service_catalog`, `org_service_integrations`, `service_tools` con RLS** |
| 3 | **Import script: 50 tools** | 🔴 **Alta** | **2h** | **Script Python que cargue el JSON canónico en las 3 tablas** |
| 4 | **ServiceConnectorTool (base class)** | 🟠 **Media-Alta** | **3h** | **OrgBaseTool genérico que lee `execution` de `service_tools` en vez de hardcodear URL/method** |
| 5 | Rate limiter por org | 🟡 Media | 2h | Evitar abuso de tools vía agentes externos |
| 6 | Audit log de accesos MCP | 🟡 Media | 1h | Registrar qué agente llamó qué tool |
| 7 | Health check scheduler | 🟡 Media | 2h | APScheduler job que valide `health_check_url` periódicamente |
| 8 | Dashboard UI para secrets | 🟢 Baja | 4h | CRUD de secretos por org (ahora solo SQL) |
| 9 | Dashboard UI para integraciones | 🟢 Baja | 4h | Activar/desactivar servicios por org |
| 10 | Rotación de secretos | 🟢 Baja | 2h | Mecanismo para rotar keys sin downtime |
| 11 | CLI: `fap-sdk register-service` | 🟢 Baja | 3h | Generar registros desde OpenAPI spec |

---

## 11. Roadmap de Implementación Consolidado

### Fase 0: Prerrequisitos (⏱️ 2-3h) 🆕

| Tarea | Archivo | Entregable |
|-------|---------|------------|
| Crear `get_secret_async()` | `src/db/vault.py` | Wrapper async sobre `get_secret()` |
| Agregar `mcp>=1.0.0` a deps | `pyproject.toml` | Dependencia directa del SDK MCP |
| Enriquecer FlowRegistry (opcional) | `src/flows/registry.py` | Aceptar `description` en `register()` |

**Definition of Done**: `import mcp` funciona y `get_secret_async()` resuelve secretos.

---

### Fase 1: Conectividad y Reflexión (⏱️ 5-6h)

| Tarea | Archivo | Entregable |
|-------|---------|------------|
| Inicializar módulo | `src/mcp/__init__.py` | Módulo importable |
| Servidor Stdio básico | `src/mcp/server.py` | Responde a `tools/list` |
| Flow-to-Tool adapter | `src/mcp/flow_to_tool.py` | Combina `FlowRegistry` + `FLOW_INPUT_SCHEMAS` → Tools |
| Definiciones de tools | `src/mcp/tools.py` | 3+ tools con inputSchema |

**Definition of Done**: `tools/list` retorna ≥3 herramientas al conectar desde Claude Desktop.

**Verificación**:
```bash
python -m src.mcp.server --org-id test_org --help
# Debe mostrar opciones de configuración
```

---

### Fase 2: Agencia Productiva (⏱️ 8-10h)

| Tarea | Archivo | Entregable |
|-------|---------|------------|
| Handler `execute_flow` | `src/mcp/handlers.py` | Ejecuta flows vía FlowRegistry |
| Handler `create_workflow` | `src/mcp/handlers.py` | Integración con ArchitectFlow |
| Auth Bridge (PyJWT) | `src/mcp/auth.py` | Validación JWT ES256/HS256 + org membership (reutiliza `_get_jwks_client`) |
| Excepciones MCP | `src/mcp/exceptions.py` | Mapeo FAP → JSON-RPC |

**Definition of Done**: Claude construye y ejecuta un flujo simple en FAP desde el chat.

**Verificación**:
```
Claude > "Ejecuta el flow de prueba con estos datos: {...}"
→ FAP retorna task_id
→ Claude hace poll_task() y obtiene resultado
```

---

### Fase 2.5: Service Catalog TIPO C (⏱️ 9-12h) 🆕

| Tarea | Archivo | Entregable |
|-------|---------|------------|
| Migración SQL | `migrations/024_service_catalog.sql` | 3 tablas + RLS + índices (⚠️ verificar FK `organizations`) |
| Import script | `scripts/import_service_catalog.py` | 50 tools cargadas desde JSON canónico |
| ServiceConnectorTool | `src/tools/service_connector.py` | OrgBaseTool genérico que lee execution de DB |
| Health check job | `src/jobs/health_check.py` | APScheduler valida servicios activos |

**Definition of Done**: Un agente puede ejecutar `stripe.create_payment_intent` leyendo la definición de `service_tools` y resolviendo el secreto del Vault, sin código hardcodeado para Stripe.

**Verificación**:
```python
# 1. Verificar que Stripe está activo para la org
GET /api/integrations?org_id=bartenders&status=active
→ [{"service_id": "stripe", "status": "active"}]

# 2. Ejecutar una tool del catálogo
POST /api/tools/execute
{
  "tool_id": "stripe.create_customer",
  "input": {"email": "test@test.com", "name": "Test"}
}
→ {"id": "cus_xxx", "email": "test@test.com"}
```

---

### Fase 3: Ecosistema Full-Stack (⏱️ 8-10h)

| Tarea | Archivo | Entregable |
|-------|---------|------------|
| Endpoint SSE | `src/api/routes/mcp_sse.py` | Streaming para Claude API |
| HITL completo | `src/mcp/handlers.py` | `list_pending_approvals` + `approve/reject` |
| Inputs complejos | `src/mcp/tools.py` | Soporte imágenes/archivos vía MCP |
| MCPConfig integrada | `src/mcp/config.py` | Settings con validación |

**Definition of Done**: Integración completa con el Dashboard de Approvals. Flujo HITL end-to-end funcional.

**Verificación**: Escenario §6.3 (aprobación HITL) ejecutado exitosamente desde Claude.

---

## 12. Endpoints Existentes Reutilizables
*(Ref: Claude §2.4, OC §1.2)*

Los siguientes endpoints REST ya existen y serán encapsulados por los handlers MCP:

```
POST /webhooks/trigger       → execute_flow handler
GET  /tasks/{task_id}        → get_task / poll_task handler
POST /flows/{flow_type}/run  → execute_flow handler (alternativo)
GET  /flows/available        → list_flows handler
GET  /flows/hierarchy        → get_flow_hierarchy handler
GET  /agents/{id}/detail     → get_agent_detail handler
POST /approvals/{task_id}    → approve_task / reject_task handler
POST /chat/architect         → create_workflow handler (vía ArchitectFlow)
```

---

## 13. Conclusión

La actualización de este análisis confirma que la pieza más potente para el sistema agéntico es el **ArchitectFlow**. Al exponerlo vía MCP, FAP deja de ser un ejecutor estático y se convierte en una plataforma de software que se construye a sí misma a través del diálogo con el agente.

La infraestructura está **~90% lista** para ser agéntica. Las piezas fundamentales (`FlowRegistry`, `BaseFlow`, `TenantClient`, JWT auth via PyJWT/JWKS) ya existen y funcionan en producción. El esfuerzo restante reside en la **capa de exposición (MCP Server)** y el **catálogo formal de integraciones TIPO C**, estimados en **32-41 horas de desarrollo** divididas en 5 fases incrementales:

| Fase | Esfuerzo | Foco |
|:---|:---|:---|
| **Fase 0: Prerrequisitos** | **2-3h** | **`get_secret_async`, dep `mcp>=1.0.0`, enriquecer FlowRegistry** |
| Fase 1: Conectividad | 5-6h | MCP Server básico + `tools/list` (usando `FLOW_INPUT_SCHEMAS`) |
| Fase 2: Agencia | 8-10h | Handlers + Auth Bridge (PyJWT ES256/HS256 + org membership) |
| **Fase 2.5: Service Catalog** | **9-12h** | **Tablas TIPO C + Import + ServiceConnectorTool** |
| Fase 3: Ecosistema | 8-10h | SSE + HITL + Inputs complejos |

> [!NOTE]
> **Ajuste v3.3**: Las estimaciones originales (23h) fueron corregidas tras verificación contra código. Los deltas principales son: (a) `flow_to_tool.py` requiere combinar dos fuentes de datos, (b) Auth Bridge debe soportar ES256+HS256 con JWKS, no solo HS256, (c) Service Catalog import de 50 tools incluye parsing y validación multi-auth-type.

**Próximo Paso Recomendado**: Ejecutar **Fase 0** (prerrequisitos) para crear `get_secret_async()` y agregar `mcp>=1.0.0`. Luego iniciar `src/mcp/server.py` y exponer `list_flows` como primera herramienta para validar la conectividad con Claude Desktop. En paralelo, ejecutar la migración SQL del Service Catalog (§10.5) verificando primero la FK a `organizations`.

---

## Apéndice A: SDK Anthropic MCP — Referencia Rápida
*(Ref: Claude §5)*

```python
# Herramientas del SDK anthropic>=0.40.0:
from anthropic.lib.tools.mcp import (
    mcp_tool,                    # Conversión sync tool → BetaFunctionTool
    async_mcp_tool,              # Conversión async tool → BetaAsyncFunctionTool
    mcp_content,                 # ContentBlock MCP → Anthropic
    mcp_message,                 # PromptMessage → BetaMessageParam
    mcp_resource_to_content,
    mcp_resource_to_file,
)

# Tipos MCP soportados:
from mcp.types import (
    Tool,                        # Definición de tool MCP
    TextContent,                 # Texto
    ImageContent,                # Imagen (jpeg, png, gif, webp)
    CallToolResult,              # Resultado de llamar tool
    ClientSession,               # Sesión MCP client
)
```

## Apéndice B: Diagrama de Flujo de Ejecución

```
Claude (Agente Externo)
    │
    │ stdio / SSE (JSON-RPC 2.0)
    ▼
┌─────────────────────────────────────────────┐
│  FAP MCP SERVER (src/mcp/server.py)         │
│                                              │
│  1. Recibe request JSON-RPC                  │
│  2. auth.py → Valida JWT + org_id            │
│  3. Routing → handlers.py                    │
│  4. Handler invoca FlowRegistry / BaseFlow   │
│  5. Formatea resultado → TextContent/Image   │
│  6. Retorna response JSON-RPC                │
│                                              │
│  Tools: 15 herramientas en 5 categorías      │
│  Auth: JWT Supabase + RLS por org_id         │
│  Errores: Mapeo FAP → JSON-RPC codes         │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  FAP Core (existente, sin modificar)         │
│                                              │
│  FlowRegistry → BaseFlow → CrewAI           │
│  TenantClient → Supabase (RLS)              │
│  ToolRegistry → MCPPool (cliente externo)    │
│  ServiceCatalog → OrgBaseTool (HTTP REST)    │
└─────────────────────────────────────────────┘
```

---
*Reporte Final v3.3 — Actualizado 2026-04-13 — **Verificado contra código fuente***
*Basado en la unificación de criterios de ATG, Claude, Kilo y OC.*
*Incorpora: Gestión de Secretos (§9), Integraciones con Plataformas (§10), y Catálogo Formal TIPO C (§10.5).*
*v3.3: Correcciones post-verificación: PyJWT (no jose), FLOW_INPUT_SCHEMAS, get_secret_async, estimaciones ajustadas.*
*Fuentes: [mcp-analisis-atg.md], [mcp-analisis-claude.md], [mcp-analisis-kilo.md], [mcp-analisis-oc.md]*