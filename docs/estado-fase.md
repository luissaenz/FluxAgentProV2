# 📝 ESTADO DE FASE: MANTENIMIENTO (Sprint 4)

## 1. Resumen de Fase
- **Objetivo:** Implementación de handlers productivos para que Claude pueda ejecutar flows reales, consultar tareas y gestionar workflows vía ArchitectFlow.
- **Lista de Pasos (Sprint 3):**
  1. Implementación de `src/mcp/handlers.py` (Lógica real de ejecución).
  2. Implementación de `src/mcp/auth.py` (Auth Bridge con python-jose).
  3. Implementación de `src/mcp/exceptions.py` (Mapeo de errores JSON-RPC).
  4. Registro de tools productivas: `execute_flow`, `get_task`, `approve_task`, `reject_task`, `create_workflow`.
- **Dependencias:**
  - Requiere Sprint 1 ✅ (Servidor Stdio OK).
  - Requiere Sprint 2 ✅ (ServiceCatalog + Sanitizer OK).
  - Sprint 3 ✅ (Handlers Productivos OK).
  - Sprint 4 ⏳ (HITL Completo + SSE).

## 2. Estado Actual del Proyecto

- **Qué ya está implementado y funcional:**
  - **Servidor MCP Básico:** `src/mcp/server.py` y `src/mcp/config.py` operativos vía Stdio (Sprint 1).
  - **Traductor de Flows a Tools:** `src/mcp/flow_to_tool.py` genera herramientas dinámicamente desde el registry.
  - **Herramientas Estáticas:** 10 tools en `src/mcp/tools.py` (5 básicas + 5 productivas del Sprint 3).
  - **Handlers de Ejecución:** `src/mcp/handlers.py` implementado con lógica real de ejecución y timeouts (Sprint 3).
  - **Auth Bridge:** `src/mcp/auth.py` genera internal tokens usando `python-jose` (Sprint 3).
  - **Mapeo de Errores:** `src/mcp/exceptions.py` mapea excepciones internas a códigos JSON-RPC (Sprint 3).
  - **Service Catalog (Tipo C):** Tablas `service_catalog`, `org_service_integrations` y `service_tools` en DB (Migración 024).
  - **Sanitizador de Salida:** `src/mcp/sanitizer.py` con 7 patrones regex (Regla R3).
  - **Integración SUPABASE:** Migración 025 aplicada con RLS moderno y bypass para `service_role`.
  - **Endpoints REST de Integración:** `src/api/routes/integrations.py` implementado.

- **Qué está parcialmente implementado:**
  - **Health Check:** `src/scheduler/health_check.py` existe pero no está conectado al lifespan del servidor.

- **Qué no existe aún:**
  - **Servidor SSE:** Transporte alternativo para Claude Web/Mobile (Sprint 4).
  - **HITL Dashboard UI:** Panel para gestionar aprobaciones pendientes (Sprint 4).
  - **MCP Config UI:** Panel para gestionar conexiones MCP (Sprint 4).

- **Discrepancias plan vs código:**
  - 📝 **CORRECCIÓN:** El plan menciona `PyJWT` para Auth, el código usa `python-jose` (verificado en `pyproject.toml`).
  - 📝 **CORRECCIÓN:** El plan asume rutas de Windows, el entorno de ejecución real es Linux (`/home/daniel/develop/...`).

## 3. Contratos Técnicos Vigentes

- **Modelos de Datos (Supabase):**
  - Schema `public` verificado. Tablas críticas: `agent_catalog`, `service_catalog`, `service_tools`.
  - RLS: Utiliza `auth.jwt() -> 'app_metadata' -> 'org_id'` para aislamiento (verificado en migración 013/025).

- **Endpoints API:**
  - `/api/v1/integrations/`: Gestión de Service Catalog.

- **Patrones de Código en Uso:**
  - **Pattern RLS:** Uso de `tenant_id` o `organization_id` con chequeo de `service_role` bypass.
  - **Tool Registry:** Los flows se registran en `src/flows/registry.py` usando `FLOW_INPUT_SCHEMAS`.
  - **Sanitización:** Llamada obligatoria a `sanitize_output()` en cada handler de tool MCP.
  - **Auth en API:** Middleware en `src/api/middleware.py` usa `python-jose` para validar tokens.

- **Estructura de Carpetas:** Standard Python Package en `src/` con `dashboard/` para el frontend Next.js.
- **Dependencias (pyproject.toml):**
  - `mcp>=1.0.0,<2.0.0`
  - `fastapi>=0.115.0`
  - `python-jose[cryptography]>=3.3.0`
  - `httpx>=0.28.0`

## 4. Decisiones de Arquitectura Tomadas
- **Transporte Stdio:** Elegido para la fase inicial de conexión con Claude Desktop.
- **Service Catalog Tipo C:** Implementación dinámica vía DB para evitar hardcode de ~226 tools.
- **Sanitización R3:** Obligatoria para prevenir leaks de keys o URLs internas en el output del LLM.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| Sprint 1 | ✅ | `src/mcp/server.py`, `src/mcp/tools.py` | Stdio como transporte principal | Base funcional MCP lista |
| Sprint 2 | ✅ | `src/mcp/sanitizer.py`, `migrations/024` | Herramientas dinámicas via DB | Service Catalog validado 18/18 |
| Sprint 3 | ✅ | `src/mcp/handlers.py`, `src/mcp/auth.py` | Ejecución real con timeouts | Handlers productivos listos |

## 6. Criterios Generales de Aceptación MVP
- Happy path operativo (Claude ejecuta flows de prueba).
- Manejo de excepciones sin crash del servidor (JSON-RPC Error mapping).
- Validación de esquemas de input para cada tool dinámico.
- Persistencia de eventos de ejecución en `domain_events`.
