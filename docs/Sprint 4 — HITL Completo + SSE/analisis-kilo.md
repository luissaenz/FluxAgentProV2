# Análisis Técnico: Sprint 4 — HITL Completo + SSE

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|-----------|
| 1 | Tabla `org_mcp_servers` existe | `grep -r "CREATE TABLE.*org_mcp_servers" migrations/` | ✅ | Migration 005, línea 9: `CREATE TABLE IF NOT EXISTS org_mcp_servers` |
| 2 | Tabla `pending_approvals` existe | `grep -r "CREATE TABLE.*pending_approvals" migrations/` | ✅ | Migration 002, línea 50: `CREATE TABLE IF NOT EXISTS pending_approvals` |
| 3 | MCP config soporta transporte SSE | `grep -r "transport.*sse" src/mcp/config.py` | ✅ | config.py L13: `transport: str = "stdio"  # stdio \| sse (SSE → Sprint 4)` |
| 4 | Servidor SSE implementado | `grep -r "EventSource\|text/event-stream\|StreamingResponse" src/` | ❌ | 0 resultados. No existe implementación SSE |
| 5 | Endpoints REST para MCPConfig | `grep -r "mcp.*config\|org_mcp_servers" src/api/routes/` | ❌ | 0 resultados. No existen endpoints para gestionar org_mcp_servers |
| 6 | HITL feedback en Dashboard vía SSE | `grep -r "sse\|EventSource" src/api/routes/approvals.py` | ❌ | 0 resultados. approvals.py no incluye SSE para real-time updates |
| 7 | MCP server puede iniciar con transporte SSE | `grep -r "transport.*==" src/mcp/server.py` | ❌ | server.py no tiene lógica condicional para transporte SSE |
| 8 | Patrón de tool approval_task implementado | `grep -r "approve_task" src/mcp/tools.py` | ✅ | tools.py L82-91: Tool definido con inputSchema correcto |
| 9 | Handler approve_task implementado | `grep -r "handle_approve_task" src/mcp/handlers.py` | ✅ | handlers.py L99-106: Función implementada con llamada a _handle_hitl_decision |
| 10 | Handler resume flow implementado | `grep -r "resume" src/flows/base_flow.py` | ✅ | base_flow.py L326-380: Método resume implementado |
| 11 | Patrón RLS en org_mcp_servers | `grep -r "tenant_isolation_org_mcp_servers" migrations/` | ✅ | Migration 005 L25: Política RLS aplicada |
| 12 | Dependencias para SSE (FastAPI streaming) | `grep -r "fastapi" pyproject.toml` | ✅ | pyproject.toml L10: `fastapi>=0.115.0` incluye streaming capabilities |

**Discrepancias encontradas:**
- ❌ DISCREPANCIA: El plan asume servidor SSE implementado, pero no existe implementación. Evidencia: grep -r "EventSource" src/ → 0 resultados
- ❌ DISCREPANCIA: El plan menciona "MCPConfig panel en Dashboard", pero no existen endpoints REST para gestionar org_mcp_servers. Evidencia: ls src/api/routes/ → no hay mcp_config.py
- ❌ DISCREPANCIA: HITL end-to-end incluye "feedback en Dashboard", pero no hay SSE para real-time updates en approvals. Evidencia: approvals.py no tiene EventSource

## 1. Diseño Funcional

### Happy Path Completo para Sprint 4

1. **Servidor SSE (Transporte Alternativo):**
   - Usuario configura MCP con `transport=sse` en config.json
   - Claude Desktop conecta vía HTTP SSE en lugar de Stdio
   - Servidor MCP responde con EventSource stream para herramientas y resultados
   - Conexión mantiene estado de sesión MCP intacto

2. **HITL End-to-End con Feedback en Dashboard:**
   - Flow ejecuta `request_approval()` → crea registro en pending_approvals
   - Dashboard muestra aprobación pendiente vía GET /approvals
   - SSE push notifica al dashboard de nueva aprobación pendiente
   - Supervisor aprueba desde dashboard → POST /approvals/{task_id}
   - Flow resume automáticamente → dashboard actualiza status vía SSE
   - Claude puede consultar status con get_task tool

3. **MCPConfig Panel en Dashboard:**
   - Admin ve lista de servidores MCP configurados: GET /mcp/servers
   - Admin crea nuevo servidor MCP: POST /mcp/servers con command, args, secret
   - Admin edita configuración existente: PUT /mcp/servers/{id}
   - Admin desactiva servidor: DELETE /mcp/servers/{id}
   - Validación: command debe ser ejecutable, secret debe existir en vault

### Edge Cases
- SSE connection drops: cliente debe reconectar automáticamente
- Aprobación concurrente: solo una decisión por task_id, rechazar duplicados
- MCP server inactivo: panel muestra status "offline", no permite ejecución
- Secret inexistente: creación falla con error claro

### Manejo de Errores
- SSE timeout: devolver error JSON-RPC estándar
- Aprobación no encontrada: 404 con mensaje descriptivo
- MCP config inválida: 422 con campos específicos

## 2. Diseño Técnico

### Componentes Nuevos
- `src/mcp/sse_server.py`: Servidor HTTP con SSE para MCP transport
- `src/api/routes/mcp_config.py`: Endpoints REST para org_mcp_servers
- `src/api/sse/approvals.py`: SSE endpoint para real-time approvals

### Interfaces (Inputs/Outputs)
- **SSE Transport:** Input: HTTP GET /mcp/sse con headers auth. Output: EventSource stream con eventos MCP
- **MCPConfig API:**
  - GET /mcp/servers → List[MCPServer]
  - POST /mcp/servers → MCPServerCreate → MCPServer
  - PUT /mcp/servers/{id} → MCPServerUpdate → MCPServer
  - DELETE /mcp/servers/{id} → 204

### Modelos de Datos Nuevos
- MCPServer (Pydantic BaseModel para org_mcp_servers)
- SSEEvent (para approvals: {"type": "approval_pending", "data": approval_record})

### Modelos de Datos Extendidos
- pending_approvals: agregar campo `sse_notified` boolean para tracking

### Integraciones
- SSE server integra con MCP server existente (compartir config, tools)
- MCPConfig endpoints usan get_tenant_client() con RLS
- Approvals SSE integra con existing POST /approvals/{task_id}

**Coherente con estado-fase.md:** Usa patrones RLS existentes, middleware auth, tenant isolation.

## 3. Decisiones

- **Transporte SSE como Feature Flag:** Implementar SSE junto a Stdio, permitir switch vía config sin breaking changes. Justificación: permite gradual rollout y backward compatibility.
- **SSE Scope Limitado a Approvals:** Solo push para pending_approvals, no para todos los eventos. Justificación: MVP focus, evita complejidad innecesaria.
- **MCPConfig UI-Driven:** Endpoints backend sin UI específica, asumir dashboard consume REST. Justificación: separación de concerns, dashboard ya existe.

## 4. Criterios de Aceptación

- Servidor MCP inicia correctamente con `transport=sse` en config.json
- Claude Desktop conecta vía SSE y lista tools sin errores
- Tool execute_flow funciona vía SSE transport
- Nueva aprobación aparece en dashboard sin refresh manual (SSE push)
- POST /approvals/{task_id} actualiza dashboard en real-time vía SSE
- GET /mcp/servers retorna lista de servidores configurados para la org
- POST /mcp/servers crea registro válido en org_mcp_servers con validación
- PUT /mcp/servers/{id} actualiza configuración existente
- DELETE /mcp/servers/{id} marca como inactivo (soft delete)
- MCPConfig endpoints rechazan requests de otras orgs (RLS verificado)
- SSE connection sobrevive network interruptions con auto-reconnect
- Errores SSE mapean correctamente a JSON-RPC error codes

## 5. Riesgos

- **Riesgo SSE Complexity:** Implementación SSE añade complejidad de state management vs Stdio. Mitigación: limitar scope a approvals, usar librerías probadas.
- **Riesgo Breaking MCP Protocol:** SSE transport debe cumplir spec MCP exactamente. Mitigación: revisar MCP docs, test contra Claude Desktop.
- **Riesgo RLS en MCPConfig:** Endpoints nuevos deben aplicar RLS correctamente. Mitigación: usar patrones existentes de tenant_client, test cross-org.
- **Riesgo Performance SSE:** Conexiones abiertas pueden escalar mal. Mitigación: limitar conexiones por org, implementar cleanup de conexiones idle.
- **Riesgo de discrepancias HITL:** Feedback en dashboard asume UI consume SSE. Mitigación: documentar contract SSE claramente para frontend.

## 6. Plan

| Tarea | Complejidad | Tiempo Estimado | Dependencias |
|-------|-------------|-----------------|--------------|
| Implementar servidor SSE básico en src/mcp/sse_server.py | Media | 4h | Ninguna |
| Integrar SSE con MCP server existente (compartir config/tools) | Baja | 2h | Servidor SSE básico |
| Crear endpoints REST MCPConfig en src/api/routes/mcp_config.py | Baja | 2h | Ninguna |
| Agregar SSE endpoint para approvals en src/api/sse/approvals.py | Media | 3h | Endpoints REST MCPConfig |
| Extender approvals.py con SSE push en decisiones | Baja | 1h | SSE endpoint approvals |
| Agregar validación y RLS a MCPConfig endpoints | Baja | 1h | Endpoints REST MCPConfig |
| Testing end-to-end: SSE transport con Claude Desktop | Alta | 3h | Servidor SSE integrado |
| Testing HITL con feedback SSE en dashboard mock | Media | 2h | SSE endpoint approvals extendido |
| Testing MCPConfig CRUD con validaciones | Baja | 1h | Validación y RLS agregados |
| Refactor y cleanup código | Baja | 1h | Todos tests pasan |

**Tiempo Total Estimado:** 20h

## 🔮 Roadmap

- **Optimizaciones SSE:** Connection pooling, heartbeat para detectar desconexiones
- **Expansión SSE:** Push para más eventos (flow completion, task updates)
- **MCPConfig Avanzado:** Health checks automáticos, métricas de uso por servidor
- **Multi-Transport:** Soporte concurrente Stdio + SSE para diferentes clientes
- **Offline Mode:** Queue de approvals cuando dashboard offline, replay al reconectar

**Pre-requisitos para Sprints Futuros:** SSE transport funcional desbloquea Sprint 5 (expansión tools), MCPConfig UI desbloquea gestión avanzada.</content>
<parameter name="filePath">/home/daniel/develop/Personal/FluxAgentProV2/LAST/analisis-kilo.md