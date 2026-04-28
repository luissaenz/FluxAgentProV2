# Estado de Fase: Sistema de Importación de Bundles (ZIP) - v2

## 1. Resumen de Fase
El objetivo de esta fase es eliminar la creación manual de agentes e implementar un sistema seguro y atómico de importación a través de "Bundles" (archivos ZIP), el cual será el único camino de entrada para agentes, flujos y skills en FluxAgentPro-v2.

**Pasos de la fase:**
1. **T1. Setup y Migraciones**: Añadir `restrictedpython` y crear migraciones SQL para `bundle_imports`, `skill_catalog`, y la función RPC atómica. *(Completado)* ✅
2. **T2. BundleManager**: Parseo en memoria, extracción y validación de hashes (SHA256). *(Completado)* ✅
3. **T3. Security (Sandboxing)**: Escaneo AST y sandboxing con `RestrictedPython`. *(Completado)* ✅
4. **T4. Persistencia Atómica**: Refactor de RLS, validación de RPC `import_bundle_atomic` y modelos de datos. *(Completado)* ✅
5. **T5. Pipeline de Importación (API)**: Endpoint `/api/bundles/import` e orquestador `ImportService`. *(Completado)* ✅
6. **T6. Refactor Existente**: Modificar `ArchitectFlow` para no insertar directamente y habilitar un `ToolRegistry` híbrido y scoped. *(Completado)* ✅
7. **T7. FAP-CLI**: Utilidad de línea de comandos para empaquetado y validación. *(Depende de T5)*

## 2. Estado Actual del Proyecto

> [!IMPORTANT]
> Se han completado los pasos **T0 a T6**. El sistema ya cuenta con el pipeline completo de importación operativo, validado técnica y funcionalmente bajo aislamiento multi-tenant.

- **Qué ya está implementado y funcional:**
  - **API de Bundles**: Endpoint `POST /api/bundles/import` operativo con soporte para multipart/form-data.
  - **Orquestador de Importación**: `ImportService` integra validación de integridad, seguridad (RestrictedPython), persistencia atómica (Supabase RPC) y registro in-memory dinámico.
  - **Aislamiento Tenant (ToolRegistry)**: Búsqueda de herramientas scoped por `org_id`. Las herramientas importadas vía bundle solo son visibles para la organización propietaria.
  - **Refactor de ArchitectFlow**: Desacoplado de la persistencia directa; ahora produce definiciones JSON listas para ser empaquetadas como bundles.
  - **Suite de Pruebas Unificada**: 100% de éxito en 226 tests unitarios y 75 tests de integración (Incluyendo resolución de regresiones de arquitectura).
- **Qué no existe aún (Pendiente de implementación):**
  - **FAP-CLI**: Utilidad para desarrolladores para validar y empaquetar bundles localmente (Tarea T7).
- **Discrepancias plan vs código:**
  - 📝 CORRECCIÓN: El `ToolRegistry` se ha implementado como un sistema híbrido (Memoria > Disco) con aislamiento estricto por prefijos (`org_id:name`) para cumplir con los requisitos de seguridad multi-tenant.

## 3. Contratos Técnicos Vigentes

- **Modelos de datos / schemas:**
  - `bundle_imports`, `skill_catalog`, `agent_catalog`, `workflow_templates`.
  - Schemas Pydantic: `BundleManifest`, `BundleContent`, `BundleRPCPayload`.
- **Patrones de código en uso:**
  - **Patrón RLS**: Uso de `(auth.role() = 'service_role' OR org_id::text = current_org_id())`.
  - **Tool Scoping**: Registro de herramientas en memoria usando prefijo `{org_id}:{tool_name}`.
  - **Modern Datetime**: Uso obligatorio de `datetime.now(UTC)` (verificado en `src/db/memory.py`).
  - **Bundle-Driven Architect**: El flujo de arquitecto es el generador de esquemas, pero no el persistidor.
- **Dependencias instaladas:** `fastapi`, `supabase`, `pydantic`, `RestrictedPython>=7.0`, `crewai`, `litellm`, `ruff`, `pytest`.

## 4. Decisiones de Arquitectura Tomadas

- **Namespace Isolation en ToolRegistry**: Decisión crítica para evitar colisiones entre organizaciones compartiendo el mismo proceso de servidor.
- **Desacoplamiento de Persistencia en Flujos**: Toda mutación de estado de "definición" (agentes/workflows) debe pasar ahora por el pipeline de bundles para garantizar seguridad.
- **Validación E2E en Ciclo de Desarrollo**: La suite de pruebas debe pasar obligatoriamente al 100% antes de aprobar cualquier cambio de arquitectura (Verificado en Iteración 4 de validación).

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| T0. Estabilización | ✅ Completado | `architect_flow.py`, `conftest.py` | Relajación de umbrales de latencia. | 100% tests en verde. |
| T2-T4. Foundation | ✅ Completado | `src/services/*`, `026_bundle_system.sql` | RPC Atómico como único camino. | Integridad y Seguridad verificadas. |
| T5. Pipeline API | ✅ Completado | `src/api/routes/bundles.py`, `import_service.py` | Orquestación centralizada en `ImportService`. | Endpoint `/api/bundles/import` funcional. |
| T6. Refactor & Scoping| ✅ Completado | `registry.py`, `base_crew.py`, `architect_flow.py` | Aislamiento por prefijo en ToolRegistry. | Regresiones de tests resueltas. |

## 6. Criterios Generales de Aceptación MVP
- El happy path (empaquetar ZIP → POST API → persistencia en DB → ejecución por agente) funciona end-to-end.
- Las regresiones técnicas han sido eliminadas (Mocks actualizados, tests de integración sincronizados).
- El sistema es 100% multi-tenant y seguro contra inyección de código malicioso en bundles.
- El código ejecuta sin errores ni warnings (Linter Ruff & ESLint al 100%).
