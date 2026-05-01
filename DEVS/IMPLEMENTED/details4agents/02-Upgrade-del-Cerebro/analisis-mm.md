# Análisis — Paso 2: Upgrade del Cerebro (ArchitectFlow)

**Fecha:** 2026-04-30
**Fase:** `details4agents`
**Plan:** `DEVS/plan.md` — Paso 2
**Agente:** mm
**Dependencias:** Paso 1 ✅ Completado

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `ArchitectFlow` existe | grep en `src/flows/` | ✅ | `architect_flow.py:51` |
| 2 | `WorkflowDefinition` schema | grep en `src/flows/` | ✅ | `workflow_definition.py:57` |
| 3 | `architect_flow._execute_architect_agent()` | read | ✅ | `architect_flow.py:190-287` |
| 4 | Prompt del agente Architect (system_prompt) | read | ✅ | `architect_flow.py:216-265` |
| 5 | `allowed_tools` en `AgentDefinition` | read | ✅ | `workflow_definition.py:21` |
| 6 | `ServiceConnectorTool` existe | grep | ✅ | `service_connector.py:44` |
| 7 | `MCPPool.get_tools()` existe | read | ✅ | `mcp_pool.py:77-191` |
| 8 | `AgentFactory.resolve_tools()` | read | ✅ | `factory.py:28-78` |
| 9 | `workflow_guardrails.ALLOWED_MODELS` | read | ✅ | `workflow_guardrails.py:16-22` |
| 10 | Tabla `org_mcp_servers` | grep en migrations | ✅ | `005_org_mcp_servers.sql` |
| 11 | Tabla `service_catalog` | grep en migrations | ✅ | `024_service_catalog.sql` |
| 12 | Tabla `service_tools` | grep en migrations | ✅ | `024_service_catalog.sql` |
| 13 | `mcp:` prefix detection en factory | read | ✅ | `factory.py:18-25` |
| 14 | `service_connector` tool registration | read | ✅ | `service_connector.py:37-43` |
| 15 | `BaseCrew` usa `AgentFactory` | read | ✅ | `base_crew.py:113` |

**Discrepancias encontradas:**

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | El prompt del Architect NO menciona `mcp:server:tool` ni `service_connector` | Expandir system_prompt en `_execute_architect_agent()` para enseñar convenciones |
| D2 | `WorkflowDefinition` no tiene campo para `mcp:` tools especiales — se asume que van en `allowed_tools` como strings | Confirmar: `allowed_tools` es `list[str]` — ya acepta `"mcp:server:tool"` sin cambios de schema |
| D3 | `workflow_guardrails.DANGEROUS_TOOLS` NO incluye `service_connector` | Agregar `service_connector` a lista de tools válidas (no peligrosa) |
| D4 | El prompt actual (L216-265) no da ejemplos de cómo definir tools MCP o integraciones | Agregar ejemplos concretos en la descripción del task |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Elementos afectados:**

- **Tablas leídas (no modificadas):**
  - `org_mcp_servers` — para verificar servers MCP disponibles en la org
  - `service_catalog` — para verificar integraciones TIPO C disponibles
  - `service_tools` — definición de herramientas de integración

- **No hay cambios de schema** — Paso 2 es exclusivamente prompt/prompt engineering en `_execute_architect_agent()`. No requiere migración.

**Integridad referencial:**
- N/A — sin cambios en DB

**RLS policies:**
- N/A — solo lectura de tablas existentes

**Índices necesarios:**
- N/A

**Tipos de datos:**
- N/A

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a modificar

#### `src/flows/architect_flow.py`

**Método:** `_execute_architect_agent()` (líneas 190-287)

**Cambio requerido:** Expandir el prompt del Task para que el agente Architect entienda y pueda generar bundles con:

1. **Convención `mcp:server:tool`** — Para tools MCP en `allowed_tools`
2. **`service_connector`** — Para integraciones HTTP del Service Catalog
3. **`steps` para orquestación multi-agente** — Ya existe en schema, pero el prompt no lo destaca como feature

**Firmas involucradas:**
- `async def _execute_architect_agent(self, description: str) -> Any` — sin cambios en firma
- `Task(description=...)` — el string del description se expande

**Patrones existentes a seguir:**
- El prompt actual ya usa variables como `{allowed_models}` — continuar ese patrón
- Agregar `{mcp_examples}` y `{integration_examples}` como variables inyectadas

**Decisión de diseño:** No hardcodear ejemplos en el string del prompt — pasarlos como variables para facilitar mantenimiento futuro.

#### `src/flows/workflow_definition.py`

**Verificado:** `allowed_tools: list[str]` en `AgentDefinition` (línea 21) — El schema ya acepta strings arbitrary, incluyendo `"mcp:file_server:read_file"` o `"service_connector"`. **No requiere cambios de schema.**

**Validator existente:** `model_validator` en `WorkflowDefinition` valida que `agent_role` exista en `agents[].role` — No hay validación para formato de `allowed_tools` (asumo intencional: flexibility).

#### `src/flows/workflow_guardrails.py`

**Cambio requerido:** Agregar `service_connector` a `DANGEROUS_TOOLS` exclusion list (o mejor: crear `SAFE_BUILTIN_TOOLS` y whitelist). Current `DANGEROUS_TOOLS` es blocklist — `service_connector` no está ahí, pero conviene hacerlo explícito.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints impactados

Ninguno directamente — `architect_flow` es un Flow (ejecutado via `flow_registry` o `BaseFlow.run()`), no un endpoint HTTP. El flujo es:

```
POST /api/flows/architect (o CLI fap run architect)
  → ArchitectFlow.validate_input()
  → ArchitectFlow.create_task_record()
  → ArchitectFlow._run_crew()
    → _execute_architect_agent() ← ACA ESTÁ EL CAMBIO
      → CrewAI Agent genera JSON
  → _parse_workflow_definition()
  → validate_workflow()
  → BundleManager.create_bundle()
```

### Middleware aplicable

- Auth via `require_org_id` en el caller (no dentro de ArchitectFlow)
- `verify_jwt` — igual que antes

### Flujo de datos

```
Input NL → Architect agent prompt (EXPANDIDO) → JSON con allowed_tools=["mcp:server:tool", "service_connector"]
  → WorkflowDefinition.validate()
  → bundle ZIP
```

### Contratos

- Output: `{"flow_type": "...", "definition": {...}, "bundle_b64": "..."}`
- El campo `definition.agents[].allowed_tools` ahora puede contener:
  - Tools regulares: `"db_read"`, `"http_request"`, etc.
  - Tools MCP: `"mcp:mi_server:list_files"`
  - Integraciones: `"service_connector"` (con tool_id en `input_data` en runtime)

### Error handling

- Si el agente no entiende la convención `mcp:` — retornará JSON inválido → `WorkflowDefinition` validation fail → `ValueError`
- Si `service_connector` no está configurado para la org → runtime error en `ServiceConnectorTool._run()` — ya manejado

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
Usuario escribe descripción NL:
"Crear un agente que busque archivos en mi servidor MCP
y notifique al equipo por Slack"

ArchitectFlow valida input
↓
Ejecuta agente Architect con prompt EXPANDIDO (knows MCP + service_connector)
↓
Arquitecto genera:
{
  "name": "File Search and Notify",
  "flow_type": "file_search_notify",
  "steps": [...],
  "agents": [{
    "role": "file_searcher",
    "goal": "Buscar archivos...",
    "allowed_tools": ["mcp:mi_server:list_files"],
    ...
  }, {
    "role": "notifier",
    "goal": "Notificar por Slack",
    "allowed_tools": ["service_connector"],
    ...
  }]
}
↓
WorkflowDefinition valida
↓
Crea bundle ZIP
↓
Retorna bundle_b64 al cliente
```

### Coherencia

- ✅ `WorkflowDefinition` soporta `allowed_tools` con strings arbitrary — no hay gap entre prompt y schema
- ✅ `AgentFactory.resolve_tools()` maneja `mcp:` prefix (Paso 1) y `service_connector` (ya existe)
- ✅ `ServiceConnectorTool` existe y está registrada

### Gaps

| Gap | Descripción | Impacto |
|---|---|---|
| G1 | El prompt no explica que `service_connector` es una tool especial que requiere configuración de `tool_id` en runtime | El usuario podría pensar que basta agregar `"service_connector"` a `allowed_tools` sin configurar la integración en `service_catalog` |
| G2 | No hay validación de que `mcp:server:tool` referencie un server configurado en `org_mcp_servers` | Validación ocurre en runtime (en `MCPPool.get_tools()`) — podría fallar tarde |
| G3 | El prompt no menciona que `service_connector` acepta parámetros via `input_data` | Posible confusión sobre cómo pasar credenciales/configuración |

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap validate-workflow
- **Qué automatiza:** Validación de un JSON de WorkflowDefinition contra:
  1. Schema estructural (Pydantic)
  2. Tools referenciadas en allowed_tools (registry + MCP servers + service_connector)
  3. Modelos en ALLOWED_MODELS
  4. Ciclo de dependencias en steps
- **Tipo:** CLI / Validador
- **Cómo se usa:** 
  ```
  fap validate-workflow --definition '{"name": "...", ...}'
  fap validate-workflow --file workflow.json
  fap validate-workflow --bundle bundle.zip --extract-first
  ```
- **Impacto para el usuario final:** 
  - Detecta errors en el JSON generado por Architect ANTES de importarlo
  - Evita runtime failures por tools MCP no configuradas o integraciones faltantes
  - El usuario puede iterar en la descripción NL si la validación falla
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] `_execute_architect_agent()` expandido con convenciones mcp: y service_connector
✅ [CODE] `workflow_guardrails` tiene explícito que service_connector es tool válida
✅ [DX] `fap validate-workflow` existe y valida schema + tools + models + cycles
✅ [CODE] Prompt注入 ejemplos de mcp:server:tool en allowed_tools
✅ [CODE] Prompt注入 ejemplos de service_connector en allowed_tools  
✅ [CODE] Prompt inyecta ejemplos de steps para multi-agente
✅ [BACKEND] ArchitectFlow genera JSON que pasa validación de WorkflowDefinition con nuevas convenciones
✅ [FULLSTACK] Bundle generado incluye tools MCP y service_connector resolubles
✅ [DX] fap validate-workflow ejecuta sin errores y detecta JSON inválido
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1 | Media | Ejemplos en prompt pueden quedar desactualizados si cambian los servers MCP disponibles | Mantener ejemplos genéricos (describir formato, no hardcodear servers específicos) |
| R2 | Baja | LLM puede ignorar las instrucciones y no seguir convención `mcp:` | Validación fuerte en `WorkflowDefinition` + `validate_workflow()` rechaza formatos inválidos |
| R3 | Media | `service_connector` requiere configuración previa en `service_catalog` que el usuario quizás no hizo | `fap validate-workflow` detecta service_connector sin config válida |
| R4 | Baja | El prompt expandido puede afectar la calidad del output para casos simples | Testing con escenarios 1-6 del plan |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear `fap validate-workflow` CLI | FULLSTACK/DX | Media | 2h | Ninguna |
| 1 | Expandir `_execute_architect_agent()` prompt con ejemplos MCP y service_connector | CODE | Media | 1h | Tarea 0 |
| 2 | Agregar `service_connector` a whitelist safe tools en `workflow_guardrails` | CODE | Baja | 0.5h | Ninguna |
| 3 | Validar con escenarios 1-6 del plan (verificar que JSON generado pasa validate) | FULLSTACK | Alta | 3h | Tareas 1-2 |

**Tiempo total estimado:** 6.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Agregar a `WorkflowDefinition` un campo `mcp_tools: list[McpToolDefinition]` explícito (en vez de embeber en `allowed_tools` como strings) — requiere breaking change
- `fap scaffold workflow` — wizard que guía al usuario paso a paso para definir un workflow con MCP tools
- Validación de `mcp:` tools contra `org_mcp_servers` en `validate_workflow()` (no solo en runtime)
