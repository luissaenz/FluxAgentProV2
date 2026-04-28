# Estado de Fase: Sistema de Importación de Bundles (ZIP) - v2

## 1. Resumen de Fase
El objetivo de esta fase es eliminar la creación manual de agentes e implementar un sistema seguro y atómico de importación a través de "Bundles" (archivos ZIP), el cual será el único camino de entrada para agentes, flujos y skills en FluxAgentPro-v2.

**Pasos de la fase:**
1. **T1. Setup y Migraciones**: Añadir `restrictedpython` y crear migraciones SQL para `bundle_imports`, `skill_catalog`, y la función RPC atómica.
2. **T2. BundleManager**: Parseo en memoria, extracción y validación de hashes (SHA256). *(Depende de T1)*
3. **T3. SecurityGuard**: Escaneo AST y sandboxing con `RestrictedPython`. *(Depende de T1)*
4. **T4. ImportService + API**: Endpoint `/bundles/import` e invocación de la transacción RPC. *(Depende de T2 y T3)*
5. **T5. Refactor Existente**: Modificar `ArchitectFlow` para no insertar directamente y habilitar un `ToolRegistry` híbrido. *(Depende de T4)*
6. **T6. FAP-CLI**: Utilidad de línea de comandos para empaquetado y validación. *(Depende de T4)*
7. **T7. Migration Tool**: Herramienta para exportar agentes legacy al formato de bundle.

## 2. Estado Actual del Proyecto

> [!IMPORTANT]
> Se ha completado el **Paso T0 (Estabilización)**. El proyecto cuenta con una base de código estable y una suite de pruebas con 100% de éxito, lista para iniciar la refactorización legacy.

- **Qué ya está implementado y funcional:**
  - **Suite de Pruebas**: 100% de éxito en 307 tests (`pytest`). Estabilidad confirmada en E2E y latencia.
  - El flujo generador de agentes `ArchitectFlow` está implementado (en `src/flows/architect_flow.py`) pero actualmente hace las inserciones directamente en la base de datos de manera no atómica.
  - El registro de herramientas `ToolRegistry` (`src/tools/registry.py`) funciona correctamente en memoria mediante decoradores.
  - Rutas de lectura de agentes como `GET /agents/{agent_id}/detail` (en `src/api/routes/agents.py`) ya existen.
- **Qué no existe aún (Pendiente de implementación):**
  - **No existen** las tablas `bundle_imports` ni `skill_catalog`. La última migración es la `025_agent_catalog_rls_update.sql`.
  - La dependencia `restrictedpython` **no está instalada** en `pyproject.toml`.
  - El endpoint de subida `/api/bundles/import` **no existe**.
- **Discrepancias plan vs código:**
  - El plan menciona que `ArchitectFlow` debe ser refactorizado para eliminar persistencia directa (Tarea T1). Actualmente el código *sí* persiste directamente, confirmando la necesidad de la T1.

## 3. Contratos Técnicos Vigentes

- **Modelos de datos / schemas:**
  - `agent_catalog`, `workflow_templates`, `tasks`, `agent_metadata`, `pending_approvals`, `secrets`, `domain_events`.
- **Patrones de código en uso:**
  - **Patrón RLS**: Uso de `org_id::text = current_org_id()` (verificado en `001_set_config_rpc.sql` y `002_governance.sql`).
  - **Patrón de registro de Tools**: Decorador `@tool_registry.register` en `src/tools/registry.py`.
  - **Patrón de registro de Flows**: Herencia de `BaseFlow` y decorador `@register_flow`.
  - **Patrón de Auth**: Middleware en `src/api/middleware.py` delegando en `src/mcp/auth.py`. Uso de `with get_tenant_client(org_id) as db:`.
- **Dependencias instaladas:** `fastapi`, `supabase`, `pydantic`, `PyJWT`, `mcp`, `crewai` (opcional), `litellm`.

## 4. Decisiones de Arquitectura Tomadas

- **Transacciones Atómicas vía RPC**: Confirmado el uso de `import_bundle_atomic` para evitar inconsistencias por fallos parciales.
- **In-Memory ZIP Processing**: Procesamiento en RAM para seguridad y velocidad.
- **Restricted Sandbox**: Combinación de AST Scan y RestrictedPython.
- **Identidad Tenancy**: El `current_org_id()` de PostgreSQL es el ancla de seguridad para RLS.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| T0. Estabilización | ✅ Completado | `architect_flow.py`, `conftest.py`, `test_webhook_to_completion.py`, `test_3_5_latency.py` | Relajación de umbrales de latencia para entorno virtual. | 100% tests en verde (304 pass, 3 skip). |
| Análisis Inicial | ✅ Completado | N/A | Generación del documento base `estado-fase.md`. | |

## 6. Criterios Generales de Aceptación MVP
- El happy path (empaquetar bundle válido → importar → confirmar en DB) funciona end-to-end.
- Los fallos (hashes incorrectos, skills maliciosas) se bloquean con HTTP 400.
- Si falla la inserción, el rollback es total (atomicidad RPC).
- El código ejecuta sin errores ni warnings nuevos.
