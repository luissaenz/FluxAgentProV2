# Estado de Fase: Sistema de Importación de Bundles (ZIP) - v2

## 1. Resumen de Fase
El objetivo de esta fase es eliminar la creación manual de agentes e implementar un sistema seguro y atómico de importación a través de "Bundles" (archivos ZIP), el cual será el único camino de entrada para agentes, flujos y skills en FluxAgentPro-v2.

**Pasos de la fase:**
1. **T1. Setup y Migraciones**: Añadir `restrictedpython` y crear migraciones SQL para `bundle_imports`, `skill_catalog`, y la función RPC atómica. *(Completado)* ✅
2. **T2. BundleManager**: Parseo en memoria, extracción y validación de hashes (SHA256). *(Completado)* ✅
3. **T3. Security (Sandboxing)**: Escaneo AST y sandboxing con `RestrictedPython`. *(Completado)* ✅
4. **T4. Persistencia Atómica**: Refactor de RLS, validación de RPC `import_bundle_atomic` y modelos de datos. *(Completado)* ✅
5. **T5. Pipeline de Importación (API)**: Endpoint `/bundles/import` e invocación de la transacción RPC. *(Depende de T2, T3 y T4)*
6. **T6. Refactor Existente**: Modificar `ArchitectFlow` para no insertar directamente y habilitar un `ToolRegistry` híbrido. *(Depende de T5)*
7. **T7. FAP-CLI**: Utilidad de línea de comandos para empaquetado y validación. *(Depende de T5)*

## 2. Estado Actual del Proyecto

> [!IMPORTANT]
> Se han completado los pasos **T0 a T4**. El sistema ya cuenta con la capacidad de persistir bundles de forma atómica y multi-tenant en la base de datos, con integridad y seguridad verificadas.

- **Qué ya está implementado y funcional:**
  - **Persistencia Atómica**: Función RPC `import_bundle_atomic` validada con suite de pruebas unitarias y de integración.
  - **RLS Refactores**: Migración `0026` actualizada para usar `current_org_id()` y bypass de `service_role` (estándar del proyecto).
  - **Suite de Pruebas**: 100% de éxito en tests de estabilización, seguridad y ahora persistencia atómica (`tests/test_bundle_rpc.py`).
  - **Security Sandbox**: Sandboxing híbrido con `RestrictedPython` y escaneo AST funcional.
  - **Bundle Foundation**: `BundleManager`, `SecurityGuard` e `IntegrityGuard` en `src/services/`.
  - **Modelos RPC**: Schemas Pydantic `BundleRPCPayload` y `BundleRPCResult` en `src/services/bundle_schemas.py`.
- **Qué no existe aún (Pendiente de implementación):**
  - El endpoint de subida `/api/bundles/import` **no existe** (Tarea T5).
  - El servicio de orquestación `ImportService` (Tarea T5).
  - Refactorización de `ArchitectFlow` (Tarea T6).
- **Discrepancias plan vs código:**
  - 📝 CORRECCIÓN: El plan original sugería persistencia vía API directa, pero se ha consolidado el uso de **RPC Atómico** como único camino de persistencia.

## 3. Contratos Técnicos Vigentes

- **Modelos de datos / schemas:**
  - `bundle_imports`, `skill_catalog`, `agent_catalog` (extendido), `workflow_templates` (extendido).
  - Schemas Pydantic: `BundleManifest`, `BundleContent`, `BundleRPCPayload`, `BundleRPCResult`.
- **Patrones de código en uso:**
  - **Patrón RLS**: Uso de `(auth.role() = 'service_role' OR org_id::text = current_org_id())` (Verificado en `024` y `026`).
  - **Validación de Bundles**: Verificación de hashes SHA256 obligatoria previo a cualquier procesamiento.
  - **Sandboxing**: Prohibición de imports de sistema y timeout de 30s para skills.
  - **RPC Signature**: `import_bundle_atomic(p_org_id UUID, p_payload JSONB)`.
- **Dependencias instaladas:** `fastapi`, `supabase`, `pydantic`, `RestrictedPython>=7.0`, `crewai`, `litellm`, `ruff`.

## 4. Decisiones de Arquitectura Tomadas

- **Transacciones Atómicas vía RPC**: Confirmado el uso de `import_bundle_atomic` para garantizar integridad (All-or-Nothing).
- **Tenant Isolation**: Delegación total al parámetro `p_org_id` y validación vía RLS.
- **Upsert Strategy**: Los bundles actualizan registros existentes basados en claves únicas de negocio (`org_id + role` / `org_id + flow_type`).
- **In-Memory ZIP Processing**: Procesamiento en RAM para evitar ataques de Path Traversal y optimizar velocidad.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| T0. Estabilización | ✅ Completado | `architect_flow.py`, `conftest.py` | Relajación de umbrales de latencia. | 100% tests en verde. |
| T2. Foundation | ✅ Completado | `src/services/*`, `026_bundle_system.sql` | Índice único por org en flujos. | Integrity y Memory-Only parsing. |
| T3. Security | ✅ Completado | `security_guard.py`, `027_bundle_rpc.sql` | Timeout y Blacklist real. | 16 tests de seguridad al 100%. |
| T4. Persistencia | ✅ Completado | `026_bundle_system.sql`, `bundle_schemas.py` | Refactor RLS a `current_org_id()`. | Suite de tests `test_bundle_rpc.py` exitosa. |

## 6. Criterios Generales de Aceptación MVP
- El happy path (empaquetar bundle válido → importar → confirmar en DB) funciona end-to-end.
- Los fallos (hashes incorrectos, skills maliciosas, errores SQL) se bloquean o revierten (Rollback).
- El sistema es 100% multi-tenant y respeta las políticas RLS.
- El código ejecuta sin errores ni warnings nuevos.
