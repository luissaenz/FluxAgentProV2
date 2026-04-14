# 🏛️ ANÁLISIS TÉCNICO UNIFICADO: Sprint 4 — HITL Completo + SSE

## 0. Evaluación de Análisis y Verificaciones (OBLIGATORIO)

### Tabla de Evaluación por Agente

| Agente | Verificó código | Discrepancias detectadas | Evidencia sólida | Score (1-5) | Notas |
|:---|:---|:---|:---|:---|:---|
| **Atg** | ✅ | 3 encontradas | ✅ | 5 | Detectó inconsistencia Crítica en librerías Auth (`middleware` vs `auth`). |
| **oc** | ✅ | 4 encontradas | ✅ | 5 | Excelente detalle técnico en el diseño del servidor SSE y componentes Dashboard. |
| **kilo** | ✅ (Sprint 3) | 1 encontrada | ✅ | 3 | Útil para verificar el estado de Sprint 3, pero no cubre el alcance de Sprint 4. |
| **qwen** | ✅ (Sprint 3) | 2 encontradas | ✅ | 3 | Documentación robusta de lo existente. |

### Discrepancias Críticas y Resoluciones

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | **Guerra de Librerías JWT:** `middleware.py` usa `PyJWT` (no en deps), `auth.py` usa `python-jose`. | Atg | ✅ `middleware.py:54` vs `auth.py:6` | **Unificar a `python-jose`** en `middleware.py` para consistencia y seguridad (ya en `pyproject.toml`). |
| 2 | **Parámetros SSE Huérfanos:** `config.py` tiene `host/port` pero no hay servidor SSE. | oc | ✅ `config.py:14` vs `server.py:70` (Solo Stdio) | Implementar `src/mcp/server_sse.py` integrando con FastAPI. |
| 3 | **Dashboard Inexistente:** Se referencian rutas de Approvals pero no hay UI. | oc / Atg | ✅ `ls dashboard/` | Crear componentes en `dashboard/app/(app)/approvals` y `dashboard/app/(app)/settings/mcp`. |
| 4 | **Health Check Desconectado:** `health_check.py` existe pero no monitorea nada real. | oc | ✅ `src/api/main.py` | Conectar al lifespan de la app FastAPI. |

### Correcciones al Plan General
- **Sprint 4 Auth:** El plan menciona `PyJWT`, pero se usará `python-jose` por consistencia con la implementación existente en el bridge de identidad.
- **Rutas de Archivos:** Corregir referencias a rutas Windows (`D:\...`) a rutas relativas al workspace Linux.

---

## 1. Resumen Ejecutivo
Se implementará el soporte para **Server-Sent Events (SSE)** como transporte alternativo a Stdio, permitiendo conexiones desde Claude Web/Mobile. Además, se completará el ciclo de **Human-In-The-Loop (HITL)** mediante una interfaz en el Dashboard que permita gestionar aprobaciones en tiempo real, conectando el estado de los flows en la base de datos con la intervención del usuario. Finalmente, se unificará la arquitectura de autenticación eliminando dependencias fantasma.

---

## 2. Diseño Funcional Consolidado

### 2.1 Flujo SSE (Transporte HTTP)
1. **Handshake:** El cliente (Claude Web) inicia conexión `GET /api/v1/mcp/sse`.
2. **Mensajería:** Los mensajes JSON-RPC se envían vía `POST /api/v1/mcp/messages`.
3. **Streaming:** Las respuestas y eventos se reciben en el stream SSE abierto.
4. **Auth:** El cliente debe incluir un JWT generado en el Dashboard (o login).

### 2.2 Flujo HITL End-to-End
1. **Pausa:** Un Flow alcanza un estado `pending_approval`. Se crea el registro en `pending_approvals`.
2. **Notificación:** El MCP retorna un mensaje indicando que se requiere aprobación y el `task_id`.
3. **Intervención:** El usuario ve la notificación en el Dashboard (Realtime).
4. **Decisión:** El usuario aprueba/rechaza. La API `POST /approvals/{task_id}` actualiza el estado.
5. **Reanudación:** El handler de la API invoca `flow.resume()`. El flow continúa su ejecución.
6. **Result:** Claude consulta `get_task` y obtiene el resultado final.

---

## 3. Diseño Técnico Definitivo

### 3.1 Arquitectura de Componentes
- **Backend (Python/FastAPI):**
  - `src/mcp/server_sse.py`: Servidor de transporte SSE integrado con el router de FastAPI.
  - `src/api/routes/approvals.py`: Extensión para soportar la lógica de negocio del Dashboard.
  - `src/mcp/auth.py`: Centralización de validación de tokens internos.
- **Frontend (Next.js/React):**
  - `dashboard/app/(app)/approvals`: Vista de lista y detalle de aprobaciones.
  - `dashboard/app/(app)/settings/mcp`: Panel de configuración para conexión remota.

### 3.2 Contratos de API (Nuevos/Modificados)
- **POST `/api/v1/mcp/sse`**: Endpoint de transporte.
- **GET `/api/v1/approvals`**: Lista de aprobaciones pendientes (auth: org-level).
- **POST `/api/v1/approvals/{task_id}`**: Resolución de aprobación (`{ action: 'approve' | 'reject', notes: string }`).

### 3.3 Modelos de Datos (Verificados)
- Tabla `pending_approvals`: `002_governance.sql`.
- Tabla `tasks`: `001_set_config_rpc.sql`.
- **Modificación:** Se agregará `requires_approval` a `tasks` para trazabilidad rápida.

---

## 4. Decisiones Tecnológicas
- **Librería Auth:** `python-jose` (HS256 para internal, ES256 para Supabase). Corrige plan §3.
- **Transporte SSE:** `mcp.server.fastapi.SseServerTransport` para compatibilidad nativa con el SDK.
- **UI State:** `useRealtimeDashboard` (Supabase Realtime) para actualizaciones instantáneas de aprobaciones.

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El usuario puede conectar Claude a FAP vía una URL SSE personalizada.
- [ ] Al requerirse una aprobación, el Dashboard muestra una alerta visual sin refrescar la página.
- [ ] Aprobar una tarea desde el Dashboard desbloquea inmediatamente la ejecución del flow.

### Técnicos
- [ ] `middleware.py` ya no importa `jwt` (PyJWT) sino `jose`.
- [ ] El endpoint de SSE responde con el header `Content-Type: text/event-stream`.
- [ ] Se registran auditorías en `domain_events` para cada decisión HITL.

### Robustez
- [ ] El servidor maneja reconexiones SSE sin duplicar procesos de ejecución en background.
- [ ] El sistema ataja decisiones sobre tareas que ya no están pendientes (Race condition handling).

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Tiempo | Dep |
|---|---|---|---|---|
| 1 | **Refactor Auth:** Migrar `middleware.py` a `python-jose`. | Baja | 1h | - |
| 2 | **SSE Server:** Implementar `src/mcp/server_sse.py` y montarlo en FastAPI. | Alta | 3h | Sprint 3 |
| 3 | **Dashboard Approvals:** Implementar página de lista y detalle. | Media | 3h | Route Approvals |
| 4 | **Config UI:** Crear panel de configuración MCP en Settings. | Media | 2h | - |
| 5 | **Realtime Integr.:** Vincular notificaciones de aprobaciones en UI. | Media | 2h | 022 Mig |
| 6 | **Integración Final:** Test E2E Claude -> SSE -> Flow -> Dashboard -> Finish. | Alta | 3h | 1-5 |

**Total estimado: 14h**

---

## 7. Riesgos y Mitigaciones
- **Riesgo:** Implementador usa `PyJWT` por inercia o siguiendo el plan original equivocado.
  - *Mitigación:* Se ha explicitado el cambio en la Sección 0 y la Tarea 1.
- **Riesgo:** Pérdida de conexión en SSE durante ejecuciones críticas.
  - *Mitigación:* Implementar persistencia de estado atómica en cada step del flow (ya presente en `BaseFlow`).

---

## 8. Testing Mínimo Viable
1. **Prueba SSE:** `curl -N -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/mcp/sse`.
2. **Prueba HITL:** Ejecutar `test_approval_flow`, verificar aparición en Dashboard, aprobar, verificar completion en log.

---

## 9. 🔮 Roadmap (NO implementar ahora)
- Streaming de tokens LLM directo sobre el canal SSE.
- Autenticación multifactor para aprobaciones críticas de servidor.
- Panel de observabilidad para trazas de MCP en tiempo real.
