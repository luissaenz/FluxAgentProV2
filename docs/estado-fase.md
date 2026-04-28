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
> El proyecto se encuentra al **inicio** de la fase "Sistema de Importación de Bundles". Aún no se ha implementado ningún código de la fase actual.

- **Qué ya está implementado y funcional:**
  - El flujo generador de agentes `ArchitectFlow` está implementado (en `src/flows/architect_flow.py`) pero actualmente hace las inserciones directamente en la base de datos de manera no atómica. Deberá refactorizarse en el paso T5.
  - El registro de herramientas `ToolRegistry` (`src/tools/registry.py`) funciona correctamente en memoria mediante decoradores, pero necesita adaptarse a un enfoque híbrido.
  - Rutas de lectura de agentes como `GET /agents/{agent_id}/detail` (en `src/api/routes/agents.py`) ya existen y devuelven metadata rica y consolidada usando la base de datos (Supabase).
- **Qué no existe aún (Pendiente de implementación):**
  - **No existen** las tablas `bundle_imports` ni `skill_catalog`. La última migración es la `025_agent_catalog_rls_update.sql`. Faltan las migraciones `026_bundle_system.sql` y `027_bundle_rpc.sql`.
  - La dependencia `restrictedpython` **no está instalada** en `pyproject.toml`.
  - El endpoint de subida `/api/bundles/import` **no existe** en `src/api/routes/`.
- **Discrepancias plan vs código:**
  - Ninguna discrepancia fundamental detectada; el plan asume correctamente que las tablas y el entorno restringido deben crearse desde cero.

## 3. Contratos Técnicos Vigentes

- **Modelos de datos / schemas:**
  - Existen y se utilizan `agent_catalog`, `workflow_templates`, `tasks`, y `agent_metadata`.
- **Patrones de código en uso:**
  - **Patrón RLS**: Uso intensivo de `org_id` como identificador de tenant para separación de datos.
  - **Patrón de registro de Tools**: Se usa el decorador `@tool_registry.register` (`src/tools/registry.py`) que instancia un singleton global de herramientas en memoria, guardando metadata operativa (retry, timeout, etc.).
  - **Patrón de registro de Flows**: Se hereda de `BaseFlow` y se usa el decorador `@register_flow` (ej. `src/flows/architect_flow.py`).
  - **Patrón de Auth en Endpoints**: Las rutas requieren `org_id: str = Depends(require_org_id)` y delegan la validación de tokens en `verify_supabase_jwt` (`src/api/middleware.py`), que a su vez llama a funciones centralizadas de validación (`src/mcp/auth.py`). Para base de datos se usa el gestor de contexto `with get_tenant_client(org_id) as db:`.
- **Dependencias instaladas:** `fastapi`, `supabase`, `pydantic`, `PyJWT`, `mcp`, `crewai` (opcional). Falta añadir `restrictedpython`.

## 4. Decisiones de Arquitectura Tomadas

- **Atomicidad Transaccional**: Debido a las limitaciones de PostgREST con los bloques interactivos (`BEGIN/COMMIT`), la inserción de agentes, flujos y skills de un bundle se realizará de forma atómica delegando en una función RPC (`import_bundle_atomic`) de PostgreSQL.
- **Extracción In-Memory**: Los ZIP (hasta 50MB) se procesarán completamente en RAM usando `BytesIO` para evitar vulnerabilidades de path traversal y uso innecesario de I/O temporal.
- **Seguridad Sandbox**: El código Python de las skills pasará por un filtro de AST estricto (prohibiendo `os`, `sys`, `importlib`, etc.) y luego se compilará con `RestrictedPython` para asegurar aislamiento durante runtime.
- **Clave única de Agentes**: La unicidad de agentes se garantizará por la dupla `(org_id, role)`. El campo `name` o `display_name` no será la clave principal en la BD.
- **`ArchitectFlow` Conservado**: El sistema actual de creación por NL no se elimina, se *refactoriza* para producir la salida estructurada de un bundle válido sin modificar la base de datos directamente.

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| Análisis Inicial | Completado | N/A | Generación del documento base `estado-fase.md` verificando que estamos en fase inicial de la T1. | |

## 6. Criterios Generales de Aceptación MVP
- El happy path (empaquetar bundle válido → importar → confirmar en DB) funciona end-to-end.
- Los fallos (hashes incorrectos, skills maliciosas) se bloquean sin crashear el servidor y devolviendo HTTP 400.
- Si falla alguna parte del parseo/inserción, la transacción atómica RPC garantiza que **ningún** dato es insertado en el catálogo.
- La CLI es capaz de empaquetar un manifest correctamente validado.
- El código ejecuta limpio, sin requerir reintentos sofisticados o sistemas de cache complejos para el MVP.
