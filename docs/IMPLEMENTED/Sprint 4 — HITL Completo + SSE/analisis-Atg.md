# 🧠 ANÁLISIS TÉCNICO: Sprint 4 — HITL Completo + SSE

## 0. Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/mcp/server.py` existe | `ls src/mcp/server.py` | ✅ | `src/mcp/server.py` (Stdio funcional) |
| 2 | Handlers HITL implementados | `view_file src/mcp/handlers.py` | ✅ | L99-L115: `handle_approve_task`, `handle_reject_task` |
| 3 | API de Approvals existe | `ls src/api/routes/approvals.py` | ✅ | `src/api/routes/approvals.py` (L66-L87) |
| 4 | Hook de Approvals Dashboard | `ls dashboard/hooks/useApprovals.ts` | ✅ | `dashboard/hooks/useApprovals.ts` (L17-L33) |
| 5 | Página de Approvals Dashboard | `ls dashboard/app/(app)/approvals/page.tsx` | ✅ | `dashboard/app/(app)/approvals/page.tsx` |
| 6 | Dependencia `mcp` instalada | `view_file pyproject.toml` | ✅ | L30: `mcp>=1.0.0,<2.0.0` |
| 7 | Middleware Auth funcional | `view_file src/api/middleware.py` | ✅ | L356: `verify_org_membership` extrae JWT + X-Org-ID |
| 8 | Dashboard API maneja headers | `view_file dashboard/lib/api.ts` | ✅ | L23-L24: Inyecta `Authorization` y `X-Org-ID` |
| 9 | Tabla `pending_approvals` en uso | `grep -r "pending_approvals" src/` | ✅ | `src/api/routes/approvals.py`: L126 |
| 10 | Resumen de Flows (Resume) | `view_file src/mcp/handlers.py` | ✅ | L175: `flow_instance.resume()` invocado |
| 11 | Sanitizador R3 obligatorio | `view_file src/mcp/handlers.py` | ✅ | L54, L93: `sanitize_output()` aplicado |
| 12 | Persistencia Eventos | `view_file src/tools/service_connector.py`| ✅ | L140: Auditoría en `domain_events` |
| 13 | Realtime habilitado | `ls migrations/022_enable_realtime_events.sql` | ✅ | Migración existe y aplicada según estado-fase |
| 14 | Mapeo Errores JSON-RPC | `view_file src/mcp/exceptions.py` | ✅ | Clases mapeadas a códigos estándar |
| 15 | Servidor SSE | `ls src/mcp/server_sse.py` | ❌ | No existe. Req. implementación |
| 16 | UI Configuración MCP | `find dashboard/` | ❌ | No se encontró ruta `/mcp-config` o similar |
| 17 | Librería Auth Inconsistente | `grep -E "jwt|jose" pyproject.toml` | ⚠️ | `pyproject.toml` tiene `python-jose`, `middleware.py` usa `PyJWT` |

**Discrepancias encontradas:**
1. **Librería JWT:** `pyproject.toml` declara `python-jose`, pero `src/api/middleware.py` usa `PyJWT`.
   - *Resolución:* Unificar a `python-jose` en todo el proyecto para consistencia con `src/mcp/auth.py`.
2. **Dashboard MCP Config:** El plan pide panel de configuración, pero no hay rastro en `dashboard/app/`.
   - *Resolución:* Crear `dashboard/app/(app)/settings/mcp/page.tsx`.
3. **SSE Entry Point:** Actualmente solo hay Stdio.
   - *Resolución:* Crear `src/mcp/server_sse.py` usando `FastAPI` + `SseServerTransport`.

---

### 1. Diseño Funcional
- **SSE Transport:** Claude Web/Mobile requiere HTTP (SSE). El servidor expondrá `/sse` y recibirá mensajes vía `/messages`.
- **HITL End-to-End:** 
  1. Claude ejecuta flow. 
  2. Flow dispara pausa en DB. 
  3. Dashboard (via Supabase Realtime) avisa al usuario. 
  4. Usuario decide. 
  5. API Approvals reanuda flow. 
  6. Claude (polling) detecta completion.
- **MCP Config Panel:** Interfaz para copiar URL SSE de la org y gestionar tokens de acceso específicos para MCP.

### 2. Diseño Técnico
- **Nuevo: `src/mcp/server_sse.py`**
  - Integra `mcp.server.fastapi.SseServerTransport`.
  - Monta rutas en `/api/v1/mcp/sse`.
  - Reutiliza `src/mcp/tools.py` y `src/mcp/handlers.py`.
- **Manejo de Estados:** 
  - Usar tabla `tasks` (status `pending_approval`) y `pending_approvals` (payload).
  - Feedback real-time en Dashboard usando `useRealtimeDashboard` hook existente.

### 3. Decisiones
- **Auth SSE:** Usar query param `?token=` para primer handshake SSE (limitación nativa EventSource en browser/algunos clientes).
- **Consistencia Auth:** Migrar `middleware.py` a `python-jose` (HS256 para tokens internos, ES256 para Supabase).

### 4. Criterios de Aceptación
1. Servidor SSE operativo en `/api/v1/mcp/sse` (vía `curl` o cliente MCP).
2. Dashboard muestra alerta inmediata cuando un flow entra en `pending_approval`.
3. Acción en Dashboard reanuda exitosamente el flow persistido.
4. Panel de configuración en Dashboard muestra URL SSE personalizada por `org_id`.

### 5. Riesgos
- **Timeout SSE:** Proxies/Browser terminando conexiones largas. Mitigación: Heartbeats cada 15s.
- **Doble Decisión:** Usuario aprobando en Dashboard y otro en Claude simultáneamente. Mitigación: Check de estado atómico en `process_approval`.

### 6. Plan
| Tarea | Complejidad | Tiempo | Dep |
|---|---|---|---|
| Unificar libs Auth (`python-jose`) | Baja | 1h | - |
| Implementar `src/mcp/server_sse.py` | Media | 3h | Sprint 3 |
| Crear UI MCP Config en Dashboard | Media | 2h | - |
| Integrar Realtime en lista Approvals | Media | 2h | 022 Mig |
| **Total** | | **8h** | |

🔮 **Roadmap:** Soporte para múltiples servidores MCP externos por organización (Inbound + Outbound).
