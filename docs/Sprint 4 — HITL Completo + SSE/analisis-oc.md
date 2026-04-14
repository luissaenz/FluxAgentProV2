# 🧠 ANÁLISIS TÉCNICO — Sprint 4: HITL Completo + SSE

**Paso:** String 4 (Sprint 4)
**Agente:** oc

---

## ⛔ Instrucciones Recibidas

El archivo `1_ANALISIS.md` indica que debo:
- Explor AR el código fuente ANTES de leer el plan en detalle
- VERIFICAR contra código fuente (no suposiciones)
- Producir análisis accionable del paso COMPLETO

---

## 0. Verificación contra Código Fuente

### Exploración Inicial

**Estructura del Proyecto verificada:**
```
src/mcp/
├── __init__.py
├── config.py          ✅ MCPConfig con transport='stdio' prep for SSE
├── server.py         ✅ Entry point Stdio
├── tools.py          ✅ 10 tools estáticas + handler dispatch
├── flow_to_tool.py  ✅ Generador dinámico de tools
├── handlers.py       ✅ Implementación Sprint 3
├── auth.py           ✅ Auth Bridge con python-jose
├── exceptions.py     ✅ Mapeo JSON-RPC
└── sanitizer.py      ✅ Output sanitizer (R3)

src/api/routes/
├── workflows.py
├── approvals.py      ⚠️ Approvals endpoint existe
├── main.py          ✅ FastAPI app
└── ...

supabase/migrations/
├── 002_governance.sql  ✅ Tabla pending_approvals
├── 010_service_role_rls_bypass.sql  ✅ RLS on pending_approvals
└── ...
```

### A. Tablas y Schema de DB

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `pending_approvals` existe | `grep "CREATE TABLE.*pending_approvals" migrations/002_governance.sql` | ✅ | Línea 50, migración 002 |
| 2 | Columnas `pending_approvals` | `id UUID, task_id UUID, org_id UUID, status, resolved_at, notes, created_at` | ✅ | Líneas 52-63, migración 002 |
| 3 | RLS en `pending_approvals` | `tenant_isolation_pending_approvals` policy | ✅ | Línea 72, migración 002 |
| 4 | Tabla `service_catalog` | Existe con RLS | ✅ | Migración 024 |
| 5 | RLS usa `auth.jwt() -> 'app_metadata' -> 'org_id'` | Verificación en migración 013/025 | ✅ | Migración 025 |

### B. Herramientas MCP Existentes

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 6 | Tool `execute_flow` existe | `src/mcp/tools.py` línea 59 | ✅ | Definida + handler en handlers.py |
| 7 | Tool `get_task` existe | `src/mcp/tools.py` línea 71 | ✅ | Handler implementado |
| 8 | Tool `approve_task` existe | `src/mcp/tools.py` línea 82 | ✅ | Handler implementado |
| 9 | Tool `reject_task` existe | `src/mcp/tools.py` línea 94 | ✅ | Handler implementado |
| 10 | Tool `create_workflow` existe | `src/mcp/tools.py` línea 106 | ✅ | Wrapper de architect_flow |
| 11 | Handlers productivos | `src/mcp/handlers.py` líneas 22-186 | ✅ | Implementación Sprint 3 |
| 12 | Auth Bridge con python-jose | `src/mcp/auth.py` línea 6 | ✅ | USA python-jose (NO PyJWT) |
| 13 | Error mapping JSON-RPC | `src/mcp/exceptions.py` | ✅ | MCPError con códigos |

### C. Componentes Preparados para SSE

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 14 | MCPConfig soporta transport | `transport: str = "stdio" # stdio \| sse` | ✅ | config.py línea 13 |
| 15 | MCPConfig host/port | `host/port` params | ✅ | config.py líneas 14-15 |
| 16 | FastAPI app existe | `src/api/main.py` | ✅ | FastAPI entry point |
| 17 | Aprobaciones endpoint | `src/api/routes/approvals.py` | ⚠️ | Existe pero parcial |

### D. Dependencias

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 18 | mcp>=1.0.0,<2.0.0 | En pyproject.toml | ✅ | Dependencia directa |
| 19 | python-jose[cryptography] | En pyproject.toml | ✅ | Dependencia directa |
| 20 | fastapi>=0.115.0 | En pyproject.toml | ✅ | Dependencia directa |
| 21 | httpx>=0.28.0 | En pyproject.toml | ✅ | Dependencia directa |

---

### Discrepancias Encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| 1 | **Plan usa PyJWT pero código usa python-jose** | ✅ Confirmado: `src/mcp/auth.py` usa `jose.jwt` (línea 6). El plan dice PyJWT, código dice python-jose. **El código gana.** |
| 2 | **MCPConfig tiene `transport='stdio'` pero no hay servidor SSE** | ⚠️ El código tiene los parámetros prepuestos (host, port) pero el servidor SSE NO existe aún. El servidor en `server.py` solo hace Stdio (línea 70). |
| 3 | **Dashboard UI para HITL NO existe** | ⚠️ El `src/api/routes/approvals.py` existe pero no hay UI en `dashboard/` para approvals. |
| 4 | **MCPConfig UI NO existe** | ⚠️ No hay componente React para gestionar conexiones MCP. |

---

## 1. Diseño Funcional

### 1.1 Descripción del Paso (Sprint 4)

El **Sprint 4** tiene 3 componentes principales:

1. **HITL Completo** — Panel de aprobaciones para gestionar tareas que requieren intervención humana:
   - Dashboard UI para listar, approve/reject pending tasks
   - Feedback visual al usuario cuando el flow se pausa
   - Persistencia en `pending_approvals`

2. **Servidor SSE** — Transporte alternativo para Claude Web/Mobile:
   - HTTP server con Server-Sent Events
   - Mantiene conexión viva para ejecuciones largas
   - Auth por token JWT

3. **MCPConfig Panel** — UI para gestionar conexiones MCP:
   - Ver estado del servidor
   - Configurar transport (stdio/SSE)
   - Ver tools disponibles

### 1.2 Happy Path

**HITL Flow:**
```
1. Claude llama execute_flow(...)
2. Flow crea task en DB con status="pending_approval"
3. Flow inserta registro en pending_approvals
4. MCP retorna {task_id, status: "pending_approval"}
5. Usuario desde Dashboard ve pending task
6. Usuario hace approve o reject
7. Dashboard llama approvals API
8. Flow resumes con decision
9. MCP retorna result 最终
```

**SSE Flow:**
```
1. Cliente conecta a SSE endpoint con JWT
2. Servidor acepta conexión
3. Cliente llama tool via HTTP POST
4. Servidor procesa y envía eventos SSE
5. Cliente recebe streaming de更新
6. Conexión se cierra cuando 完成
```

### 1.3 Edge Cases

| Edge Case | Manejo |
|---|---|
| Flow toma >5s | Retorna `status: "pending"` con task_id para polling |
| Approval después de timeout | Flow debe poder reanudar hasta X horas |
| Conexión SSE se corta | Cliente debe poder reconectar y resume |
| Multiple approvals simultáneas | DB con optimistic locking |
| Reject con理由 vacía | Usar razón por defecto |

### 1.4 Manejo de Errores

| Error | Respuesta |
|---|---|
| Task no encontrada | ` LookupError` → JSON-RPC -32602 |
| Status no es pending_approval | ValueError → -32602 |
| Token JWT inválido | -32001 Unauthorized |
| Flow execution falla | MCPError → -32603 |

---

## 2. Diseño Técnico

### 2.1 Componentes a Crear

#### A. Servidor SSE (`src/mcp/server_sse.py` — NUEVO)

```python
# Pseudo-code basado en verificación
class SSEServer:
    def __init__(self, config: MCPConfig, server: Server):
        self.server = server
        self.config = config
    
    async def handle_connection(self, request, org_id: str):
        # Accept SSE connection
        # Route tool calls via MCP protocol
        # Stream responses via SSE
```

**Dependencias verificadas:**
- FastAPI: `src/api/main.py` ya tiene FastAPI app
- SSE: No hay implementación existente
- JWT: `src/mcp/auth.py` tiene `create_internal_token()`

#### B. HITL Dashboard UI (`dashboard/components/hitl/PendingApprovals.tsx` — NUEVO)

```
dashboard/components/hitl/
├── PendingApprovals.tsx    # Lista de tareas pendientes
├── ApprovalCard.tsx        # Card individual con approve/reject
└── ApprovalDetail.tsx     # Vista detallada
```

**Dependencias:**
- approvals API endpoint: `src/api/routes/approvals.py` existe
- PendingApprovals table: Existe (migración 002)

#### C. MCPConfig Panel (`dashboard/components/mcp/MCPConfigPanel.tsx` — NUEVO)

```
dashboard/components/mcp/
├── MCPConfigPanel.tsx      # Configuración de conexión
└── MCPStatusCard.tsx       # Estado del servidor
```

### 2.2 Modificaciones a Existentes

| Archivo | Modificación |
|---|---|
| `src/mcp/server.py` | Agregar entry point para SSE transport |
| `src/mcp/config.py` | Agregar `require_auth: bool = False` para SSE |
| `src/api/main.py` | Agregar lifespan事件 para SSE server |
| `src/scheduler/health_check.py` | Conectar al lifespan (ya existe, no conectado)**

### 2.3 APIs y Endpoints

#### SSE Endpoints

| Endpoint | Método | Descripción |
|---|---|---|
| `/mcp/sse` | GET | Server-Sent Events stream |
| `/mcp/tools` | POST | Tool execution |
| `/mcp/tools/list` | GET | List tools |
| `/mcp/auth` | POST | Token refresh |

#### HITL / Approvals API (ya existe parcial)

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/approvals/` | GET | List pending approvals |
| `/api/v1/approvals/{task_id}` | GET | Get approval detail |
| `/api/v1/approvals/{task_id}/approve` | POST | Approve task |
| `/api/v1/approvals/{task_id}/reject` | POST | Reject task |

**Verificación:** `src/api/routes/approvals.py` existe pero verificar estado real.

### 2.4 Modelos de Datos

**pending_approvals (ya existe):**
```sql
CREATE TABLE pending_approvals (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL,
    org_id UUID NOT NULL,
    status TEXT CHECK (status IN ('pending', 'approved', 'rejected')),
    notes TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**tasks (ya existe):**
```sql
-- Agregar columna para HITL
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN DEFAULT FALSE;
```

### 2.5 Interfaces Verificadas

**Handler signatures (verificadas en handlers.py):**
```python
async def handle_execute_flow(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]
async def handle_get_task(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]
async def handle_approve_task(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]
async def handle_reject_task(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]
```

**Auth signatures (verificadas en auth.py):**
```python
def create_internal_token(org_id: str, user_id: str = "mcp-system", expires_delta: timedelta = timedelta(minutes=60)) -> str
```

**Config (verificada en config.py):**
```python
class MCPConfig(BaseSettings):
    transport: str = "stdio"       # stdio | sse
    host: str = "127.0.0.1"      # Solo SSE
    port: int = 8765               # Solo SSE
    require_auth: bool = False      # NEW for SSE
    org_id: UUID
```

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|---|---|
| 1 | **Usar FastAPI + uvicorn para SSE** | El proyecto ya tiene FastAPI en src/api/main.py. Reutilizar para evitar nueva dependencia. |
| 2 | **python-jose para auth (ya implementado)** | Código existente en src/mcp/auth.py. NO cambiar a PyJWT. |
| 3 | **JWT conrol expires en 60 min** | Balance entre seguridad y实用性. 60 min es estándar. |
| 4 | **Dashboard para HITL requiere React** | Frontend existente es Next.js/React. Componentes nuevos deben seguir patrón existente. |
| 5 | **SSE usa chunked transfer encoding** | Estándar para Server-Sent Events en HTTP. |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | Servidor SSE inicia correctamente con `transport='sse'` | `python -m src.mcp.server --transport sse` retorna 200 OK |
| 2 | Conexión SSE desde cliente establece stream de eventos | curl a endpoint retorna event stream |
| 3 | Tool execution via SSE retorna respuesta completa |POST /mcp/tools con JSON body retorna result |
| 4 | Dashboard muestra pending approvals correctamente | GET /api/v1/approvals/ retorna lista |
| 5 | Approve desde Dashboard reanuda flow | POST approvals/approve actualiza DB y flow completa |
| 6 | Reject desde Dashboard finaliza task | POST approvals/reject actualiza DB y limpia estado |
| 7 | Timeout de auth (-32001) funciona en SSE | Token inválido retorna error code -32001 |
| 8 | MCPConfig panel muestra tools disponibles | stats de tools coincidircon GET /mcp/tools/list count |
| 9 | Health check desconectado SE conecta | POST /api/v1/health retorna 200 |
| 10 | Fallback a Stdio si SSE falla | config transport="stdio" conecta sin SSE |

---

## 5. Riesgos

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| 1 | **SSE no está implementado** | Alto — No hay fallback en código | Implementar servidor SSE desde cero |
| 2 | **Health check no conectado** | Medio — No hay way verificar estado | Conectar al lifespan en main.py |
| 3 | **Dashboard approvals UI no existe** | Alto — No hay UI to approve tasks | Crear componentes React |
| 4 | **MCPConfig UI no existe** | Medio — No hay way change config | Crear componentes React |
| 5 | **Auth en SSE necesita validación por request** | Alto — Stdio no usa auth, SSE sí | Usar create_internal_token + validation |
| 6 | **Flows existentes supportan HITL?** | Medio — Verificar BaseFlow resume | Verificar base_flow.py tiene resume() |
| 7 | **PendingApprovals RLS permite acceso correcto** | Alto — Security | Verificar policy usa service_role bypass |

---

## 6. Plan de Implementación

### Tareas Atómicas

| # | Tarea | Complejidad | Tiempo | Dependencias |
|---|---|---|---|---|
| 1 | Implementar server_sse.py (entry point SSE) | Alta | 2h | 2, 3 |
| 2 | Agregar require_auth a MCPConfig | Baja | 30min | - |
| 3 | Modificar server.py para dual transport | Media | 1h | 1 |
| 4 | Conectar health_check.py al lifespan | Baja | 30min | - |
| 5 | Implementar SSE endpoints en FastAPI | Media | 2h | 1, 3 |
| 6 | Implementar PendingApprovals.tsx UI | Media | 2h | 7 |
| 7 | Implementar ApprovalCard.tsx | Baja | 1h | 6 |
| 8 | Crear approvals API REST enhancements | Baja | 1h | - |
| 9 | Implementar MCPConfigPanel.tsx | Media | 2h | - |
| 10 | Test E2E HITL + SSE | Alta | 2h | 1-9 |

**Total estimado:** 14 horas

### Orden Recomendado

1. Primero: Tareas 1-3 (Server SSE core)
2. Segundo: Tareas 4-5 (Integración FastAPI)
3. Tercero: Tareas 6-7 (Dashboard HITL)
4. Cuarto: Tarea 8 (API enhancements)
5. Quinto: Tarea 9 (MCPConfig panel)
6. Sexto: Tarea 10 (Test E2E)

---

## 🔮 Roadmap (NO implementar ahora)

| # | Item | Descripción | Pre-requisito |
|---|---|---|---|
| 1 | Streaming de salida LLM via SSE | Enviar tokens uno por uno | SSE server implementado |
| 2 | Multiple org support en SSE | Organizaciones múltiples | Auth por org_id en JWT |
| 3 | MCP Registry Protocol | Descubrimiento dinámico de servers | Mismo proyecto |
| 4 | WebSocket fallback | Para browsers sin SSE | SSE working |
| 5 | MCPConfig storage en DB | Persistir config between restarts | Tabla nueva + migrations |

---

## Métricas de Calidad

| Métrica | Estado |
|---|---|
| Elementos verificados contra código | 21 ✅ |
| Discrepancias detectadas | 4 (1 код, 3 missing) |
| Resoluciones con evidencia | 4/4 |
| Criterios de aceptación binarios | 10 ✅ |
| Estimación de tiempo | 14h total |

---

**Idioma:** Español 🇪🇸

**Documento generado:** `/home/daniel/develop/Personal/FluxAgentProV2/LAST/analisis-oc.md`