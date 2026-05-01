# Análisis Técnico — Paso 2: Upgrade del Cerebro (ArchitectFlow)

**Agente:** oc
**Fecha:** 2026-04-30
**Fase:** details4agents
**Paso:** 2 — Upgrade del Cerebro (ArchitectFlow)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `workflow_templates` existe | `006_workflow_templates.sql:6` | ✅ | CREATE TABLE, línea 6 |
| 2 | Tabla `agent_catalog` existe | `004_agent_catalog.sql:6` | ✅ | CREATE TABLE, línea 6 |
| 3 | Tabla `org_mcp_servers` existe | `005_org_mcp_servers.sql:9` | ✅ | CREATE TABLE, línea 9 |
| 4 | Tabla `service_catalog` existe | `024_service_catalog.sql:8` | ✅ | CREATE TABLE, línea 8 |
| 5 | Tabla `service_tools` existe | `024_service_catalog.sql:59` | ✅ | CREATE TABLE, línea 59 |
| 6 | Tabla `org_service_integrations` existe | `024_service_catalog.sql:28` | ✅ | CREATE TABLE, línea 28 |
| 7 | `ArchitectFlow` clase existe | `src/flows/architect_flow.py:51` | ✅ | `class ArchitectFlow(BaseFlow)` |
| 8 | `_execute_architect_agent` método existe | `src/flows/architect_flow.py:190` | ✅ | async def, línea 190 |
| 9 | `WorkflowDefinition` modelo existe | `src/flows/workflow_definition.py:57` | ✅ | Pydantic BaseModel |
| 10 | `AgentDefinition` modelo existe | `src/flows/workflow_definition.py:15` | ✅ | Con campo `allowed_tools: list[str]` |
| 11 | `StepDefinition` modelo existe | `src/flows/workflow_definition.py:38` | ✅ | Con campo `depends_on`, `requires_approval` |
| 12 | `AgentFactory.resolve_tools` existe | `src/crews/factory.py:28` | ✅ | Resolución centralizada sync/async |
| 13 | `MCPPool.get_tools` existe | `src/tools/mcp_pool.py:77` | ✅ | Async, circuit breaker |
| 14 | `ServiceConnectorTool` existe | `src/tools/service_connector.py:44` | ✅ | @register_tool("service_connector") |
| 15 | `ALLOWED_MODELS` set existe | `src/flows/workflow_guardrails.py:16` | ✅ | 5 modelos permitidos |
| 16 | `validate_workflow` función existe | `src/flows/workflow_guardrails.py:39` | ✅ | Valida dangerous tools + quota |
| 17 | `BundleManager` existe | `src/services/bundle_manager.py` | ✅ | Confirmado en phase-state |
| 18 | `_ensure_unique_flow_type` existe | `src/flows/architect_flow.py:310` | ✅ | Verifica colisiones en workflow_templates |
| 19 | `workflow_templates.definition` columna JSONB | `006_workflow_templates.sql:17` | ✅ | JSONB NOT NULL DEFAULT '{}' |
| 20 | `agent_catalog.allowed_tools` columna TEXT[] | `004_agent_catalog.sql:12` | ✅ | TEXT[] DEFAULT '{}' |
| 21 | `org_mcp_servers` columnas: command, args, secret_name | `005_org_mcp_servers.sql:12-15` | ✅ | command TEXT, args JSONB, secret_name TEXT |
| 22 | RLS en `workflow_templates` | `006_workflow_templates.sql:56` | ✅ | tenant_isolation via current_setting |

**Discrepancias encontradas:**

| # | Discrepancia | Resolución propuesta |
|---|---|---|
| D1 | El prompt actual del Architect (líneas 217-265) NO menciona convención `mcp:{server}:{tool}` para herramientas MCP. El plan exige que el Architect reconozca este formato. | Expandir el system_prompt con ejemplos explícitos de herramientas MCP y formato `mcp:server:tool`. |
| D2 | El prompt actual NO menciona `service_connector` como herramienta de integración Tipo C. El plan exige que el Architect pueda generar agentes que usen `service_connector` con `tool_id`. | Agregar sección en el prompt explicando `service_connector` y su uso con `tool_id` del service_catalog. |
| D3 | `WorkflowDefinition` tiene campo `category` (línea 71) pero el prompt del Architect NO lo incluye en el schema JSON que le da al agente. | Agregar `category` al schema JSON del prompt para que el Architect lo genere. |
| D4 | `StepDefinition` tiene campo `approval_threshold` (línea 47) pero el prompt del Architect NO lo incluye en el schema del paso. | Agregar `approval_threshold` al schema JSON del prompt. |
| D5 | El Architect genera bundles ZIP pero el prompt NO instruye al agente sobre cómo estructurar `allowed_tools` para que contengan tanto tools regulares como MCP tools en el mismo array. | Clarificar en el prompt que `allowed_tools` acepta strings de cualquier tipo: registry names y `mcp:server:tool`. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas

| Tabla | Rol en el paso | Impacto |
|---|---|---|
| `workflow_templates` | Almacena la definición generada por el Architect | Sin cambios de schema. El JSONB `definition` ya soporta la estructura necesaria. |
| `agent_catalog` | Los agentes generados se persisten aquí | Sin cambios. `allowed_tools` TEXT[] ya acepta cualquier string incluyendo `mcp:server:tool`. |
| `org_mcp_servers` | Fuente de configuración de servidores MCP | Sin cambios. El Architect solo necesita referencia por nombre. |
| `service_catalog` | Catálogo global de servicios integrables | Sin cambios. El Architect referencia por `tool_id`. |
| `service_tools` | Definiciones de herramientas por servicio | Sin cambios. El Architect referencia por `tool_id`. |

### Integridad referencial

- `workflow_templates.org_id` → `organizations.id` (CASCADE DELETE) ✅
- `agent_catalog.org_id` → `organizations.id` (CASCADE DELETE) ✅
- `org_mcp_servers.org_id` → `organizations.id` (CASCADE DELETE) ✅
- `service_tools.service_id` → `service_catalog.id` ✅
- `org_service_integrations.org_id` → `organizations.id` ✅

### RLS policies aplicables

- `workflow_templates`: `tenant_isolation` via `current_setting('app.org_id', TRUE)` (006:56)
- `agent_catalog`: `agent_catalog_tenant_isolation` via `current_setting` (004:22)
- `org_mcp_servers`: `tenant_isolation_org_mcp_servers` via `current_org_id()` (005:25)
- `org_service_integrations`: `org_integration_access` via service_role OR `current_org_id()` (024:47)

### Índices existentes (relevantes)

- `idx_workflow_templates_flow_type` UNIQUE en `flow_type` (006:47)
- `idx_agent_catalog_org_role` en `(org_id, role)` WHERE is_active (004:26)
- `idx_mcp_servers_org` en `org_id` (005:28)
- `idx_service_tools_service` en `service_id` (024:71)

### Cambios de schema necesarios

**NINGUNO.** El schema actual soporta todas las capacidades del paso 2. Las definiciones JSONB ya son flexibles y `allowed_tools` TEXT[] acepta strings arbitrarios.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivo principal a modificar: `src/flows/architect_flow.py`

#### Método a modificar: `_execute_architect_agent` (líneas 190-287)

**Firma actual:**
```python
async def _execute_architect_agent(self, description: str) -> Any
```

**Responsabilidad actual:** Construir el agente CrewAI "Workflow Architect" con un system_prompt que describe el schema `WorkflowDefinition` y genera JSON.

**Cambios necesarios:**

1. **Expandir el schema JSON en el prompt** (líneas 224-255):
   - Agregar campo `category` al schema de `WorkflowDefinition`
   - Agregar campo `approval_threshold` al schema de `StepDefinition`
   - Agregar explicación de formato `mcp:server:tool` en `allowed_tools`
   - Agregar explicación de `service_connector` como herramienta especial

2. **Agregar ejemplos de herramientas MCP** en las reglas del prompt:
   ```
   Herramientas MCP: usa formato "mcp:nombre_servidor:nombre_herramienta"
   Ejemplo: "mcp:filesystem:read_file", "mcp:github:search_repositories"
   ```

3. **Agregar sección de integraciones Tipo C**:
   ```
   Integraciones HTTP (Service Connector): usa "service_connector" en allowed_tools
   El agente recibirá tool_id e input_data como argumentos
   Ejemplo de uso en steps: el agente llama service_connector con tool_id="stripe.create_customer"
   ```

4. **Actualizar las reglas críticas** (líneas 257-264):
   - Agregar regla sobre validación de formato MCP
   - Agregar regla sobre uso correcto de service_connector

#### Patrones existentes a seguir

**Patrón de prompt del Architect:**
- Usa f-string con variable `allowed_models` interpolada (línea 198)
- Schema JSON como bloque literal dentro del string
- Reglas numeradas al final del prompt
- Espera JSON puro sin markdown

**Patrón de validación:**
- `WorkflowDefinition` Pydantic valida estructuralmente (línea 302)
- `validate_workflow()` valida seguridad (línea 134)
- `_ensure_unique_flow_type()` evita colisiones (línea 139)

#### Cohesión y acoplamiento

- `ArchitectFlow` hereda de `BaseFlow` → cohesión alta
- Usa `BundleManager` para generar ZIP → acoplamiento bajo (inyección directa)
- Usa `workflow_guardrails.validate_workflow` → acoplamiento bajo (función pura)
- El cambio propuesto solo toca el prompt → impacto localizado, sin cambiar flujo

#### Imports existentes (no necesitan cambios)

```python
from crewai import Agent, Crew, Process, Task
from src.config import get_settings
from src.flows.workflow_guardrails import ALLOWED_MODELS
from src.utils.llm_parsing import extract_json_from_text, extract_token_usage
from src.services.bundle_manager import BundleManager, BundleManifest
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints afectados

**Ninguno directamente.** El paso 2 modifica solo el flujo interno del Architect. Los endpoints que invocan ArchitectFlow siguen funcionando sin cambios:

- `POST /api/flows/architect` (si existe) → invoca `ArchitectFlow` con descripción NL
- El output del Architect (bundle_b64 + definition) se consume por `POST /api/bundles/import`

### Flujo de datos actualizado

```
Usuario (NL description)
  → POST /api/flows/architect
    → ArchitectFlow._run_crew()
      → _execute_architect_agent()  ← MODIFICADO: prompt expandido
        → CrewAI Agent "Workflow Architect"
          → JSON con soporte MCP + service_connector
      → _parse_workflow_definition()
        → WorkflowDefinition (Pydantic valida)
      → validate_workflow()
        → Seguridad + quota check
      → BundleManager.create_bundle()
        → ZIP con agents + flows
      → Retorna {flow_type, definition, bundle_b64}
```

### Contratos entre servicios

| Contrato | Input | Output |
|---|---|---|
| Architect → WorkflowDefinition | JSON del agente | Pydantic model validado |
| WorkflowDefinition → BundleManager | model_dump() de agents + flows | ZIP bytes |
| BundleManager → Import endpoint | ZIP base64 | Agentes + templates en DB |

### Error handling

- `WorkflowValidationError` → se convierte en `ValueError` con mensaje descriptivo (línea 136)
- JSON parsing fallido → `ValueError` con snippet del raw text (línea 297)
- Pydantic validation fallido → `ValueError` con JSON recibido (línea 305)
- Colisión de flow_type → sufijo con org_id + random (líneas 329-338)

### Cuellos de botella potenciales

1. **`_ensure_unique_flow_type`** hace consultas sincrónicas a DB en loop (hasta 5 intentos). En alta concurrencia podría haber race conditions. Mitigación: el índice UNIQUE en `flow_type` previene duplicados a nivel DB.
2. **Bundle generation** es sincrónico y bloqueante. Para workflows grandes (>10 agentes) podría tardar varios segundos.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: DB → Backend → Frontend → UX

```
[Frontend] Usuario escribe: "Quiero un agente que busque en Google y envíe emails"
    ↓
[Backend] ArchitectFlow recibe description
    ↓
[Architect] Prompt expandido reconoce:
  - mcp:google:search → herramienta MCP
  - service_connector → para email (sendgrid, etc.)
    ↓
[JSON] Genera:
  {
    "agents": [{
      "role": "investigador",
      "allowed_tools": ["mcp:google:search", "service_connector"]
    }],
    "steps": [...]
  }
    ↓
[Pydantic] WorkflowDefinition valida estructura
    ↓
[Guardrails] validate_workflow checkea dangerous tools + quota
    ↓
[Bundle] ZIP generado con agents + flows
    ↓
[Frontend] Recibe bundle_b64 + definition → usuario confirma import
    ↓
[DB] agent_catalog + workflow_templates persistidos
```

### Coherencia con arquitectura existente

- ✅ `AgentFactory.resolve_tools()` ya soporta `mcp:server:tool` (factory.py:44-68)
- ✅ `MCPPool` ya resuelve conexiones persistentes (mcp_pool.py:77-190)
- ✅ `ServiceConnectorTool` ya está registrado (service_connector.py:37-44)
- ✅ `allowed_tools` TEXT[] acepta cualquier string (004:12)
- ✅ `workflow_templates.definition` JSONB es flexible (006:17)

### Gaps identificados

| Gap | Impacto | Mitigación |
|---|---|---|
| El prompt no enseña al Architect cuándo usar MCP vs service_connector | El agente podría elegir mal el tipo de herramienta | Agregar guía en el prompt: "Usa MCP para herramientas locales/externas estandarizadas. Usa service_connector para APIs HTTP del service_catalog." |
| No hay validación de que el MCP server referido existe antes de generar el bundle | Bundle importado podría fallar en runtime | Agregar validación opcional contra `org_mcp_servers` durante `_run_crew` (post-prompt, pre-bundle) |
| `service_connector` requiere `tool_id` específico pero el Architect no sabe qué tools existen | El agente podría inventar tool_ids inexistentes | Agregar al prompt: "Para service_connector, el tool_id debe existir en service_tools. Si no conoces el ID exacto, usa un placeholder y el usuario lo configurará." |

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap validate-architect-output
- **Qué automatiza:** Valida el JSON generado por el Architect contra el registry de tools y MCP servers antes de crear el bundle. Detecta tools inexistentes, MCP servers no configurados, y service_tools IDs inválidos.
- **Tipo:** Comando CLI
- **Cómo se usa:** `fap validate-architect-output <architect_json_path> --org-id <org_uuid>`
- **Impacto para el usuario final:** Evita importar bundles con referencias rotas. El usuario ve errores claros como "MCP server 'filesystem' no configurado para esta org" en vez de fallos crípticos en runtime.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

**Implementación sugerida:**
- Archivo nuevo: `src/cli/commands/validate_architect.py`
- Registra comando en `src/cli/main.py`
- Valida:
  1. Cada `mcp:server:tool` contra `org_mcp_servers` para el org_id
  2. Cada `service_connector` referencia contra `service_tools`
  3. Cada tool regular contra `tool_registry`
  4. Retorna exit code 0 si todo válido, 1 con errores detallados

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] El schema JSON en el prompt del Architect incluye todos los campos de WorkflowDefinition (name, description, flow_type, steps, agents, approval_rules, category)
✅ [DATA] El prompt incluye campo approval_threshold en StepDefinition
✅ [CODE] El prompt del Architect explica formato mcp:server:tool con ≥ 2 ejemplos
✅ [CODE] El prompt del Architect explica service_connector con ≥ 1 ejemplo de uso
✅ [CODE] El prompt incluye guía para elegir entre MCP y service_connector
✅ [BACKEND] El JSON generado por el Architect valida contra WorkflowDefinition sin errores
✅ [BACKEND] allowed_tools en el JSON generado acepta tanto tools regulares como mcp:server:tool
✅ [FULLSTACK] Un usuario puede describir un workflow con herramientas MCP y el Architect genera JSON válido
✅ [FULLSTACK] Un usuario puede describir un workflow con integraciones HTTP y el Architect genera JSON válido
✅ [DX] Herramienta fap validate-architect-output existe y valida referencias contra registry
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| El Architect genera `mcp:server:tool` con servidor inexistente | Alta | El prompt no tiene contexto de qué MCP servers están configurados para la org | Validación post-generación contra `org_mcp_servers` (warning, no bloqueo) |
| El Architect inventa `tool_id` para service_connector | Media | service_tools es global pero el agente no tiene acceso al catálogo | Agregar lista de tool_ids comunes en el prompt o usar placeholders |
| Prompt demasiado largo excede contexto del LLM | Media | Agregar mucha información puede reducir calidad de generación | Medir tokens del prompt actual (~1200) vs límite del modelo. Priorizar ejemplos concisos. |
| Cambios en el prompt rompen generación de workflows simples | Baja | El modelo podría confundirse con nuevas instrucciones | Mantener compatibilidad: los ejemplos nuevos son aditivos, no reemplazan el schema base |
| Race condition en `_ensure_unique_flow_type` | Baja | Dos ArchitectFlows simultáneos podrían generar el mismo flow_type | El índice UNIQUE en DB previene duplicados. El error se maneja con retry. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear `fap validate-architect-output` CLI command | FULLSTACK/DX | Media | 3h | Ninguna |
| 1 | Expandir schema JSON en prompt: agregar `category` y `approval_threshold` | CODE | Baja | 0.5h | Ninguna |
| 2 | Agregar sección de herramientas MCP al prompt con formato y ejemplos | CODE | Baja | 1h | Tarea 1 |
| 3 | Agregar sección de service_connector al prompt con ejemplos de uso | CODE | Baja | 1h | Tarea 1 |
| 4 | Agregar guía de selección MCP vs service_connector en reglas del prompt | CODE | Baja | 0.5h | Tareas 2-3 |
| 5 | Actualizar reglas críticas del prompt para incluir validación de formatos | CODE | Baja | 0.5h | Tareas 2-4 |
| 6 | Validación post-generación: checkear MCP servers referidos existen | BACKEND | Media | 2h | Tarea 2 |
| 7 | Test end-to-end: generar workflow con MCP tools + service_connector | FULLSTACK | Media | 2h | Tareas 1-6 |

**Tiempo total estimado:** 10.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Validación de MCP servers en tiempo real:** Integrar `fap validate-architect-output` como paso automático dentro de `ArchitectFlow._run_crew()` antes de generar el bundle.
- **Catálogo de tools disponible:** Pasar al Architect una lista de tools registradas + MCP servers configurados para la org como contexto adicional en el prompt.
- **Generación iterativa:** Permitir que el usuario refine el workflow generado mediante conversación ("agrega un paso de revisión", "cambia el modelo del agente X").
- **Preview visual:** Generar un diagrama ASCII o Mermaid del workflow antes de importar para que el usuario verifique el grafo de dependencias.
- **Templates predefinidos:** Ofrecer plantillas de workflows comunes (investigador→redactor→corrector) como punto de partida para el Architect.
