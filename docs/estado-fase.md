# 📝 ESTADO DE FASE: MANTENIMIENTO (Sprint 4 — COMPLETADO)

## 1. Resumen de Fase
- **Objetivo:** Implementación de soporte **Server-Sent Events (SSE)** para acceso remoto (Claude Web/Mobile) y ciclo completo de **Human-In-The-Loop (HITL)** vía Dashboard.
- **Lista de Pasos (Sprint 4):**
  1. Refactor de Auth en middleware a `python-jose` (Unificación).
  2. Implementación de `src/mcp/server_sse.py` (Transporte HTTP).
  3. Creación de UI en Dashboard para gestión de aprobaciones (`/approvals`).
  4. Creación de panel de configuración MCP (`/settings/mcp`).
  5. Conexión de Health Checks al lifespan de FastAPI.
  6. Endpoint POST `/api/mcp/generate-pin` (Iniciando Sprint 5).
- **Dependencias:**
  - Sprint 1, 2, 3 ✅ (Core Handlers OK).
  - Sprint 4 ✅ (SSE + HITL OK).
  - Sprint 5 🔄 (Auth PIN MCP en curso).

## 2. Estado Actual del Proyecto

- **Qué ya está implementado y funcional:**
  - **Servidor MCP Dual Transport:** Soporta Stdio (`server.py`) y SSE (`server_sse.py`).
  - **Multi-tenant Seguro:** Uso de `contextvars` para manejar aisladamente el `org_id` en el servidor MCP compartido.
  - **Health Checks Activos:** Ejecución en background iniciada desde el lifespan de FastAPI.
  - **Dashboard HITL:** Interfaz operativa para aprobaciones pendientes con actualizaciones Realtime (Supabase).
  - **Configuración MCP:** Panel en el Dashboard con instrucciones de conexión para Stdio y URL de SSE.
  - **Trazabilidad Mejorada:** Columna `requires_approval` en tabla `tasks` para identificar flows intervenidos.

- **Qué está parcialmente implementado:**
  - **Manejo de Secretos:** Los tokens JWT para SSE son internos; falta integración con un secret manager para rotación automática (Phase 5).

- **Qué no existe aún:**
  - **Endpoint de Autenticación MCP:** POST `/api/mcp/generate-pin` (Planeado en Sprint 5).
  - **Streaming de Tokens LLM vía SSE:** Actualmente la respuesta se envía completa al finalizar.
  - **Observabilidad MCP:** Trazas detalladas de mensajes JSON-RPC en el Dashboard.

- **Discrepancias plan vs código:**
  - 📝 **CORRECCIÓN:** El plan original indicaba `PyJWT`; el código ha sido **unificado a `python-jose`** en todo el proyecto (Auth & Middleware).
  - 📝 **CORRECCIÓN:** El plan mencionaba rutas Windows; el proyecto está estandarizado en Linux/Unix paths.
  - ⚠️ **VERIFICAR:** El `plan.md` asume la existencia de `secure-pin.ts`, pero no fue hallado en `src/` ni en `dashboard/`.

## 3. Contratos Técnicos Vigentes

- **Modelos de Datos (Supabase):**
  - Tabla `tasks`: Incluye `requires_approval` (Migración 026).
  - Tabla `pending_approvals`: Tabla central para HITL (Migración 002).
  - RLS: Utiliza `auth.jwt() -> 'app_metadata' -> 'org_id'` (verificado).

- **Endpoints API:**
  - `/api/v1/mcp/sse`: Canal de eventos MCP.
  - `/api/v1/mcp/messages`: Receptor de mensajes MCP (JSON-RPC POST).
  - `/api/v1/approvals/`: Gestión de tareas pendientes de intervención humana.

- **Patrones de Código en Uso:**
  - **Pattern ContextAware:** Uso de `mcp_config_var` para inyectar configuración de tenant en handlers asíncronos.
  - **Pattern Realtime:** El Dashboard se suscribe a `pending_approvals` para notificaciones push.
  - **Auth en API:** Middleware unificado en `src/api/middleware.py` usando `python-jose` con validación de JWKS.

- **Estructura de Carpetas:** Core logic en `src/mcp`, Routes en `src/api/routes`, Dashboard en `dashboard/app/(app)`.

- **Dependencias (pyproject.toml):**
  - `mcp>=1.0.0`
  - `python-jose[cryptography]>=3.3.0`
  - `httpx>=0.28.0` (Usado para fetch de JWKS y health checks).

## 4. Decisiones de Arquitectura Tomadas
- **Single Process / Multi-tenant MCP:** Uso de un único servidor MCP que cambia su contexto dinámicamente según la petición HTTP/SSE entrante.
- **SseServerTransport:** Elección del transporte oficial del SDK de MCP para compatibilidad máxima.
- **Unificación Criptográfica:** Eliminación de `PyJWT` para evitar conflictos de firmas y dependencias fantasma.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| Sprint 1 | ✅ | `server.py`, `tools.py` | Stdio como transporte principal | Base funcional lista |
| Sprint 2 | ✅ | `sanitizer.py`, `migr/024` | Herramientas dinámicas via DB | Service Catalog validado |
| Sprint 3 | ✅ | `handlers.py`, `auth.py` | Ejecución real con timeouts | Handlers productivos listos |
| Sprint 4 | ✅ | `middleware.py`, `server_sse.py`, `main.py` | Transporte SSE y HITL Realtime | Soporte Claude Web y UI Aprobaciones |

## 6. Criterios Generales de Aceptación MVP
- Happy path operativo (Claude ejecuta flows de prueba vía SSE).
- Intervención humana funcional desde el Dashboard.
- Aislamiento total entre organizaciones verificado.
- Salud del sistema monitoreada en tiempo real.
