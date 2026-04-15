# 🧠 PASO 1: IntegrationResolver — Definición (ANÁLISIS ATG)

## 0. Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `service_catalog` existe | `024_service_catalog.sql` L8 | ✅ | `CREATE TABLE service_catalog` |
| 2 | Tabla `service_tools` existe | `024_service_catalog.sql` L59 | ✅ | `CREATE TABLE service_tools` |
| 3 | Tabla `org_service_integrations` existe | `024_service_catalog.sql` L28 | ✅ | `CREATE TABLE org_service_integrations` |
| 4 | Tabla `agent_catalog` existe | `004_agent_catalog.sql` L6 | ✅ | `allowed_tools TEXT[]` exists |
| 5 | Tabla `workflow_templates` existe | `006_workflow_templates.sql` L6 | ✅ | `definition JSONB` exists |
| 6 | Tabla `secrets` (Vault) existe | `002_governance.sql` L79 | ✅ | `org_id`, `name`, `secret_value` |
| 7 | Función `get_service_client` existe | `src/db/session.py` L48 | ✅ | Usar bypass de RLS para catálogos globales |
| 8 | Manejo de secretos en `vault.py` | `src/db/vault.py` | ❌ | Falta función `upsert_secret` (solo lectura) |
| 9 | Estructura de `ArchitectFlow` | `src/flows/architect_flow.py` | ✅ | `_run_crew` L112-163 coincide con lógica |
| 10 | `allowed_tools` en `WorkflowDefinition` | `src/flows/workflow_definition.py` | ✅ | `AgentDefinition.allowed_tools` (list[str]) |
| 11 | `DynamicWorkflow.register` | `src/flows/dynamic_flow.py` L39 | ✅ | Permite registro dinámico en `FLOW_REGISTRY` |
| 12 | Dependencia `httpx` | `pyproject.toml` L23 | ✅ | Disponible para health checks y llamadas MCP |

### Discrepancias encontradas:

1. **Vault solo lectura:** `db/vault.py` no tiene métodos para escribir secretos. El plan requiere `store_credential`.
   - **Resolución:** Añadir `upsert_secret(org_id, name, value)` a `src/db/vault.py` usando `service_role`.
2. **Políticas RLS en `secrets`:** La migración 002 solo define política para `SELECT`. `upsert` fallará.
   - **Resolución:** Nueva migración para añadir política `ALL` (o INSERT/UPDATE) para `service_role` en tabla `secrets`.
3. **Pausa en flows dinámicos:** `DynamicWorkflow` ya tiene lógica de pausa con `request_approval` (L120), pero `ArchitectFlow` no la está usando para el proceso de resolución.
   - **Resolución:** `ArchitectFlow` debe ser capaz de pausarse si el `resolver` retorna `is_ready == False`, similar a un flow operativo.

---

## 1. Diseño Funcional

- **Happy Path:**
  1. El usuario pide: "Analiza mis ventas de Google Sheets".
  2. `ArchitectFlow` genera un JSON con la tool `google_sheets_read`.
  3. `IntegrationResolver` matchea `google_sheets_read` → `google_sheets.read_spreadsheet` (Real).
  4. Verifica que `google_sheets` esté activo para la org y tenga el secreto `SPREADSHEET_TOKEN` en Vault.
  5. Si todo OK, se persiste el template con el ID real de la tool.
- **Edge Cases MVP:**
  - **Match Ambiguo:** Si un nombre alucinado matchea con 2+ tools (ej: `sheets_get` → `read` o `list`), se elige el que tenga mayor ratio de coincidencia o se pide aclaración en el estado `not_ready`.
  - **Servicio Inactivo:** El resolver detecta que la `org` no tiene activado el servicio. Marca `needs_activation`.
- **Manejo de Errores:**
  - Si no hay ningún match razonable (threshold < 0.6), la tool va a `not_found`. El flow se detiene y muestra la lista al usuario.

---

## 2. Diseño Técnico

- **IntegrationResolver (`src/flows/integration_resolver.py`):**
  - Implementará `async resolve(workflow_def)` que orquesta las consultas a `service_tools`, `org_service_integrations` y `Vault`.
  - Usará `SequenceMatcher` (difflib) o `ILIKE` para el fuzzy matching inicial.
- **WorkflowDefinition Update:**
  - El prompt de `ArchitectFlow` (L232+) se modificará para inyectar una lista de tools "sugeridas" desde el catálogo para minimizar alucinaciones.
- **Persistence Layer:**
  - `_persist_agents` usará el `tool_mapping` generado por el resolver para guardar IDs reales de tools en la columna `allowed_tools` de `agent_catalog`.

---

## 3. Decisiones

1. **Bypass de RLS para Matching:** El matching se hace contra `service_tools` (global, sin RLS) usando `get_service_client()`.
2. **Resolución en Memoria:** El `ResolutionResult` no se persiste en DB si falla; se retorna como `output_data` de la tarea `pending` para que el cliente lo gestione.
3. **Mapping Determinista:** Ante la duda, no mapear. Es mejor que el usuario confirme a que un agente ejecute una tool incorrecta por un falso positivo de fuzzy match.

---

## 4. Criterios de Aceptación

1. **¿Matching funciona?** Una descripción con "google sheets" resulta en el ID real `google_sheets.read_spreadsheet`. (Sí/No)
2. **¿Bloquea persistencia?** Si falta una credencial requisitada por el servicio, el workflow NO se guarda en `workflow_templates`. (Sí/No)
3. **¿Efecto en Vault?** `upsert_secret` guarda el valor correctamente y es recuperable por `get_secret`. (Sí/No)
4. **¿Prompt mejorado?** El log de CrewAI muestra que el catálogo de tools fue pasado como contexto al agente Architect. (Sí/No)

---

## 5. Riesgos

- **Alucinaciones de Parámetros:** El resolver valida el nombre de la tool, pero no todavía si el LLM respeta el `input_schema` de la tool real.
  - *Mitigación:* Futuro paso de validación profunda de schema (Paso 2).
- **Conflictos de RLS:** Si la política de `secrets` no se actualiza, el sistema fallará silenciosamente al intentar guardar credenciales.
  - *Mitigación:* Incluir la migración SQL como primera tarea del plan.

---

## 6. Plan

1. **Infra DB (30m):** Migración para RLS en `secrets` (INSERT/UPDATE para `service_role`). [Baja]
2. **Vault Update (30m):** Implementar `upsert_secret` en `src/db/vault.py`. [Baja]
3. **Resolver Core (2h):** Clase `IntegrationResolver` con lógica de matching, activación y validación de secrets. [Media]
4. **Integration (1.5h):** Modificar `ArchitectFlow._run_crew` para intercalar el resolver y manejar el estado `is_ready`. [Media]
5. **Prompt Refine (30m):** Inyectar herramientas reales en el prompt del Architect. [Baja]
6. **Tests (1h):** Test unitario del Resolver con mocks. [Baja]

**Tiempo total estimado:** 6 horas.
