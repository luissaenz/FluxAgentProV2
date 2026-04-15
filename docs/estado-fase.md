# 📝 ESTADO DE FASE: EXPANSIÓN (Sprint 5 — EN CURSO)

## 1. Resumen de Fase
- **Objetivo:** Fortalecer el **Ecosistema Agéntico MCP** mediante la resolución de herramientas reales, persistencia de secretos y autenticación robusta.
- **Lista de Pasos (Sprint 5):**
  1. **IntegrationResolver:** Validación y mapeo de tools alucinadas contra el catálogo real (COMPLETADO).
  2. **Auth PIN MCP:** Generación y validación de PIN para emparejamiento Claude-Dashboard.
  3. **Multi-agent Crew Resolution:** Soporte para resolución de dependencias en workflows de múltiples agentes.
- **Dependencias:**
  - Sprint 4 ✅ (SSE + HITL OK).
  - Sprint 5.1 ✅ (Resolver Core OK).

## 2. Estado Actual del Proyecto

- **Qué ya está implementado y funcional:**
  - **IntegrationResolver:** Clase `src/flows/integration_resolver.py` que realiza matching fuzzy de tools y verifica activación de servicios/secretos.
  - **Vault Write Support:** Función `upsert_secret` en `src/db/vault.py` y políticas RLS (Migración 027) para persistencia de credenciales.
  - **Architect Prompt Mejorado:** Inyección dinámica de herramientas reales del catálogo en el prompt del ArchitectFlow para reducir alucinaciones.
  - **Manejo de Resolución en ArchitectFlow:** El flow se detiene y retorna un reporte de faltantes si el resolver detecta servicios inactivos o herramientas no encontradas.

- **Qué está parcialmente implementado:**
  - **Generación de PIN:** Endpoint `/api/v1/mcp/generate-pin` iniciado; falta integración con el flujo de validación de Claude.

- **Qué no existe aún:**
  - **Streaming de Tokens LLM vía SSE:** En el roadmap.
  - **Observabilidad MCP:** Trazas JSON-RPC pendientes.

- **Discrepancias plan vs código:**
  - 📝 **CORRECCIÓN:** El plan original sugería activación por herramienta; el código implementa **activación por servicio** (basado en `service_catalog`) por ser el modelo de datos vigente.
  - 📝 **CORRECCIÓN:** La tabla `secrets` ahora permite `INSERT/UPDATE` vía `service_role` (Migración 027), corrigiendo la restricción de solo lectura previa.

## 3. Contratos Técnicos Vigentes

- **Modelos de Datos (Supabase):**
  - Tabla `secrets`: Ahora accesible para escritura por el sistema (Migración 027).
  - Tabla `service_tools`: Fuente de verdad para el mapping de herramientas reales (Migración 024).

- **Interfaces de Código Nuevas:**
  - `IntegrationResolver.resolve(workflow_def)` -> `ResolutionResult`.
  - `upsert_secret(org_id, name, value)`.

- **Patrones de Código en Uso:**
  - **Pattern Pre-flight Validation:** Uso del Resolver antes de persistir templates en `ArchitectFlow`.
  - **Pattern Fuzzy Matching:** Estrategia de matching de herramientas en 3 niveles (Exacto -> Service-based -> ILIKE general).

## 4. Decisiones de Arquitectura Tomadas
- **Resolución Transitoria:** El `ResolutionResult` no se persiste; se envía como respuesta de la tarea para intervención del usuario.
- **Bloqueo Preventivo:** Se prohíbe la creación de workflows con herramientas en estado `not_found` para garantizar que los workflows sean ejecutables.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| Sprint 4 | ✅ | `middleware.py`, `server_sse.py` | Transporte SSE y HITL | Soporte Claude Web OK |
| Sprint 5.1 | ✅ | `integration_resolver.py`, `vault.py`, `architect_flow.py` | Matching fuzzy y Vault write | Paso 1 del plan completado |

## 6. Criterios Generales de Aceptación MVP
- Happy path de creación de workflows con tools reales verificado.
- Resolución de herramientas alucinadas funcional.
- Secretos almacenables y recuperables para integraciones.
