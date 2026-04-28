# Estado de Fase: Sistema de Importación de Bundles (ZIP) - v2

## 1. Resumen de Fase
El objetivo de esta fase es eliminar la creación manual de agentes e implementar un sistema seguro y atómico de importación a través de "Bundles" (archivos ZIP), el cual será el único camino de entrada para agentes, flujos y skills en FluxAgentPro-v2.

**Pasos de la fase:**
1. **T1. Setup y Migraciones**: Añadir `restrictedpython` y crear migraciones SQL para `bundle_imports`, `skill_catalog`, y la función RPC atómica.
2. **T2. BundleManager**: Parseo en memoria, extracción y validación de hashes (SHA256). *(Depende de T1)*
3. **T3. SecurityGuard**: Escaneo AST y sandboxing con `RestrictedPython`. *(Completado)* ✅
4. **T4. ImportService + API**: Endpoint `/bundles/import` e invocación de la transacción RPC. *(Depende de T2 y T3)*
5. **T5. Refactor Existente**: Modificar `ArchitectFlow` para no insertar directamente y habilitar un `ToolRegistry` híbrido. *(Depende de T4)*
6. **T6. FAP-CLI**: Utilidad de línea de comandos para empaquetado y validación. *(Depende de T4)*
7. **T7. Migration Tool**: Herramienta para exportar agentes legacy al formato de bundle.

## 2. Estado Actual del Proyecto

> [!IMPORTANT]
> Se han completado los pasos **T0 (Estabilización)** y **T2 (Estándar y Foundation)**. El sistema cuenta con la infraestructura base para procesar bundles (ZIP) de forma segura, con integridad verificada y sandboxing funcional.

- **Qué ya está implementado y funcional:**
  - **Suite de Pruebas**: 100% de éxito en tests de estabilización (307) e integración de bundles (16).
  - **Security Sandbox**: Sandboxing híbrido con `RestrictedPython` (timeout de 30s) y escaneo AST (blacklist/allowlist) funcional.
  - **Bundle Foundation**: Implementación de `BundleManager`, `SecurityGuard` y `IntegrityGuard` en `src/services/`.
  - **Esquema DB**: Tablas `bundle_imports`, `skill_catalog` y RPC `import_bundle_atomic` (Migraciones 026 y 027).
  - **Pipeline de Calidad**: Orquestación de linting (Ruff/ESLint) unificada en la raíz vía `npm run lint`.
  - **Corrección de Schema**: Índice único de flujos corregido a `(org_id, flow_type)` para soportar tenancy.
- **Qué no existe aún (Pendiente de implementación):**
  - El endpoint de subida `/api/bundles/import` **no existe** (Tarea T4).
  - El servicio de persistencia atómica `ImportService` (Tarea T4).
  - Refactorización de `ArchitectFlow` (Tarea T1/T5).
- **Discrepancias plan vs código:**
  - Se resolvió la discrepancia del índice único en `workflow_templates` detectada en el análisis (ahora es por org_id).

## 3. Contratos Técnicos Vigentes

- **Modelos de datos / schemas:**
  - `agent_catalog`, `workflow_templates`, `tasks`, `agent_metadata`, `bundle_imports`, `skill_catalog`.
- **Patrones de código en uso:**
  - **Patrón RLS**: Uso de `org_id::text = current_setting('app.org_id', TRUE)`.
  - **Validación de Bundles**: Verificación de hashes SHA256 obligatoria previo a cualquier procesamiento.
  - **Sandboxing**: Prohibición de imports de sistema (os, subprocess) y funciones peligrosas (eval, exec).
  - **Linting Pipeline**: Ejecución secuencial obligatoria de `lint:front` y `lint:back` antes de validar pasos.
- **Dependencias instaladas:** `fastapi`, `supabase`, `pydantic`, `RestrictedPython>=7.0`, `crewai`, `litellm`, `ruff`, `npm-run-all`.

## 4. Decisiones de Arquitectura Tomadas

- **Transacciones Atómicas vía RPC**: Confirmado el uso de `import_bundle_atomic` para evitar inconsistencias por fallos parciales.
- **In-Memory ZIP Processing**: Procesamiento en RAM para seguridad y velocidad.
- **Restricted Sandbox**: Combinación de AST Scan y RestrictedPython.
- **Identidad Tenancy**: El `current_org_id()` de PostgreSQL es el ancla de seguridad para RLS.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| T0. Estabilización | ✅ Completado | `architect_flow.py`, `conftest.py` | Relajación de umbrales de latencia. | 100% tests en verde. |
| T2. Estándar y Foundation | ✅ Completado | `src/services/*`, `026_bundle_system.sql` | Cambio a índice único por org en flujos. | Integrity y Memory-Only parsing. |
| T3. Security (Sandboxing) | ✅ Completado | `security_guard.py`, `027_bundle_rpc.sql` | Implementación de Timeout y Blacklist real. | 16 tests de seguridad al 100%. |
| Análisis Unificado | ✅ Completado | `analisis-FINAL.md` | Consolidación de atg y kilo. | |

## 6. Criterios Generales de Aceptación MVP
- El happy path (empaquetar bundle válido → importar → confirmar en DB) funciona end-to-end.
- Los fallos (hashes incorrectos, skills maliciosas) se bloquean con HTTP 400.
- Si falla la inserción, el rollback es total (atomicidad RPC).
- El código ejecuta sin errores ni warnings nuevos.
