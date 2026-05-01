# 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

## Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| kilo | ✅ | 1 | ✅ | ✅ | 4.5 |
| oc | ✅ | 5 | ✅ | ✅ | 5.0 |
| mm | ✅ | 4 | ✅ | ✅ | 4.5 |

## Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | Prompt no menciona convención `mcp:server:tool` en allowed_tools | kilo, oc, mm | ✅ `architect_flow.py:216-265` | Expandir prompt con ejemplos de formato MCP |
| 2 | Prompt no menciona `service_connector` como herramienta de integración | kilo, oc, mm | ✅ `architect_flow.py:216-265` | Agregar sección dedicada a integraciones Tipo C |
| 3 | `WorkflowDefinition` tiene campo `category` (línea 71) pero prompt no lo incluye en schema JSON | oc | ✅ `workflow_definition.py:71` | Agregar `category` al schema JSON del prompt |
| 4 | `StepDefinition` tiene campo `approval_threshold` (línea 47) pero prompt no lo incluye | oc | ✅ `workflow_definition.py:47` | Agregar `approval_threshold` al schema del paso |
| 5 | Prompt no instruye cómo estructurar `allowed_tools` mezclando tools regulares y MCP | oc | ✅ `architect_flow.py:224-255` | Clarificar que allowed_tools acepta cualquier string |
| 6 | `workflow_guardrails.DANGEROUS_TOOLS` no tiene explicititud sobre `service_connector` como tool válida | mm | ✅ `workflow_guardrails.py:16-22` | Agregar `service_connector` a whitelist o confirmar que no está en dangerous list |

---

### 1️⃣ Resumen Ejecutivo

- **Objetivo:** Expandir el system_prompt del agente Architect en `_execute_architect_agent()` para que genere workflows JSON que incluyan herramientas MCP (formato `mcp:server:tool`) e integraciones HTTP (`service_connector`).
- **Correcciones críticas al plan:** El plan indica modificar `WorkflowDefinition` para permitir nuevos formatos, pero el schema YA soporta `allowed_tools: list[str]` sin cambios. Solo el prompt requiere actualización.
- **Decisión DX:** Se selecciona la herramienta `fap validate-architect-output` de oc por ser la más completa — valida contra registry real de tools y MCP servers de la org antes de importar bundle.

---

### 2️⃣ Diseño Funcional Consolidado

#### Happy Path

1. Usuario describe workflow NL: "Crear un agente que busque archivos en MCP y notifique por Slack"
2. `ArchitectFlow._run_crew()` invoca `_execute_architect_agent(description)`
3. Prompt expandido instruye al agente sobre convenciones `mcp:` y `service_connector`
4. CrewAI Agent genera JSON con `allowed_tools: ["mcp:mi_server:list_files", "service_connector"]`
5. `_parse_workflow_definition()` valida JSON contra `WorkflowDefinition` (Pydantic)
6. `validate_workflow()` checkea seguridad + quota
7. `BundleManager.create_bundle()` genera ZIP
8. Usuario importa bundle via `POST /api/bundles/import`

#### Edge Cases MVP

- Agente genera `mcp:server:tool` con servidor no configurado → runtime error en MCPPool (aceptable por ahora)
- Agente usa `service_connector` sin configurar `tool_id` → runtime error en ServiceConnectorTool (aceptable por ahora)
- JSON generado no pasa validación estructural → `WorkflowValidationError` → retry con mensaje descriptivo
- Flow type colisiona con existente → `_ensure_unique_flow_type()` agrega sufijo

---

### 3️⃣ Diseño Técnico Definitivo

#### Componentes y Modificaciones

**Archivo:** `src/flows/architect_flow.py`
- **Tipo de cambio:** Modificación
- **Descripción:** Expandir el task description en `_execute_architect_agent()` (líneas 190-287) para incluir:
  1. Schema JSON completo de `WorkflowDefinition` con campos `category` y `approval_threshold`
  2. Sección de herramientas MCP con formato `mcp:server:tool` y ≥2 ejemplos
  3. Sección de integraciones Tipo C con `service_connector` y ≥1 ejemplo
  4. Guía de selección MCP vs service_connector
  5. Reglas de validación de formato en critical rules
- **Interfaces clave:** `async def _execute_architect_agent(self, description: str) -> Any`
- **Patrones a seguir:** El prompt actual usa f-string con `{allowed_models}` interpolada — continuar ese patrón

**Archivo:** `src/flows/workflow_guardrails.py`
- **Tipo de cambio:** Modificación
- **Descripción:** Agregar `service_connector` a `SAFE_BUILTIN_TOOLS` o confirmar que no está en `DANGEROUS_TOOLS` (explícito vs implícito)
- **Interfaces clave:** `DANGEROUS_TOOLS: set[str]` línea 16
- **Patrones a seguir:** Patrón existente de blocklist/whitelist

**Archivo:** `src/cli/commands/validate_architect.py` (NUEVO)
- **Tipo de cambio:** Creación
- **Descripción:** CLI command que valida JSON del Architect contra registry de tools y MCP servers de la org
- **Interfaces clave:** `fap validate-architect-output <json_path> --org-id <uuid>`
- **Patrones a seguir:** Patrones de CLI en `src/cli/main.py`

#### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap validate-architect-output
- **Qué automatiza:** Valida el JSON generado por el Architect contra el registry de tools y MCP servers antes de crear el bundle. Detecta tools inexistentes, MCP servers no configurados, y service_tools IDs inválidos.
- **Tipo:** CLI command
- **Ubicación:** src/cli/commands/validate_architect.py (registrado en src/cli/main.py)
- **Cómo se usa:** fap validate-architect-output <architect_json_path> --org-id <org_uuid>
- **Impacto para el usuario final:** Evita importar bundles con referencias rotas. El usuario ve errores claros como "MCP server 'filesystem' no configurado para esta org" en vez de fallos crípticos en runtime.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso.
```

---

### 4️⃣ Decisiones Tecnológicas

1. **Schema WorkflowDefinition sin cambios:** `allowed_tools: list[str]` ya acepta `"mcp:server:tool"` y `"service_connector"` sin modificación. El plan decía lo contrario pero el código real lo permite.
2. **Prompt expansion en lugar de refactor:** Solo se modifica el string del prompt, sin cambios en firmas o flujo de ejecución.
3. **Validación post-generación (opcional):** La herramienta DX valida contra `org_mcp_servers` antes de bundle — warning no blocking.
4. **⚠️ El plan dice** modificar `WorkflowDefinition` para nuevos formatos pero **el código real** ya los soporta via `list[str]`. Se implementa lo que dice el código.

---

### 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] WorkflowDefinition permite allowed_tools con strings arbitrarias (mcp: y service_connector)
✅ [DATA] Schema JSON en prompt incluye campos category y approval_threshold
✅ [CODE] Prompt del Architect explica formato mcp:server:tool con ≥ 2 ejemplos
✅ [CODE] Prompt del Architect explica service_connector con ≥ 1 ejemplo de uso
✅ [CODE] Prompt incluye guía para elegir entre MCP y service_connector
✅ [CODE] workflow_guardrails tiene explícito que service_connector es tool válida
✅ [BACKEND] JSON generado por Architect valida contra WorkflowDefinition sin errores
✅ [FULLSTACK] Usuario puede describir workflow con herramientas MCP y Architect genera JSON válido
✅ [FULLSTACK] Usuario puede describir workflow con integraciones HTTP y Architect genera JSON válido
✅ [DX] Herramienta fap validate-architect-output existe y valida referencias contra registry
```

**Funcionales:**
- [ ] El Architect genera JSON con `category` y `approval_threshold` incluidos
- [ ] El JSON generado pasa validación estructural de WorkflowDefinition
- [ ] Bundle importado se persiste en `workflow_templates` y `agent_catalog`

**Técnicos:**
- [ ] `_execute_architect_agent()` no modifica su firma ni comportamiento de retorno
- [ ] `workflow_guardrails` no tiene warnings de importación
- [ ] CLI command `fap validate-architect-output` retorna exit code 0 para JSON válido

---

### 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `fap validate-architect-output` CLI | Media | 3h | Ninguna |
| 1 | Expandir schema JSON en prompt: agregar `category` y `approval_threshold` | Baja | 0.5h | Ninguna |
| 2 | Agregar sección de herramientas MCP al prompt con formato y ≥2 ejemplos | Baja | 1h | Tarea 1 |
| 3 | Agregar sección de service_connector al prompt con ≥1 ejemplo | Baja | 1h | Tarea 1 |
| 4 | Agregar guía de selección MCP vs service_connector en reglas | Baja | 0.5h | Tareas 2-3 |
| 5 | Actualizar reglas críticas del prompt para validación de formatos | Baja | 0.5h | Tareas 2-4 |
| 6 | Agregar explicititud de service_connector en workflow_guardrails | Baja | 0.5h | Ninguna |
| 7 | Test end-to-end: generar workflow con MCP tools + service_connector | Alta | 2h | Tareas 1-6 |
| **TOTAL** | | | **8.5h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar la herramienta resultante para el resto del paso (dogfooding obligatorio).

---

### 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Prompt demasiado largo causa truncamiento por LLM | Media | Agregar muchos ejemplos | Mantener ejemplos concisos, validar con pruebas |
| El Architect genera mcp: con servidor inexistente | Alta | Prompt no tiene contexto de qué MCP servers están configurados | Validación post-generación con fap validate-architect-output (warning) |
| El Architect inventa tool_id para service_connector | Media | service_tools es global pero el agente no tiene acceso al catálogo | Agregar en prompt: "Si no conoces el ID exacto, usa placeholder" |
| service_connector sin configuración de org | Media | El prompt no advierte sobre configuración previa | fap validate-architect-output detecta esta falta |
| Race condition en _ensure_unique_flow_type | Baja | Dos ArchitectFlows simultáneos | Índice UNIQUE en DB + retry con sufijo |

---

### 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Validar JSON con MCP tools | `{"allowed_tools": ["mcp:fs:read_file"]}` | Exit code 0 si server existe, error claro si no |
| TP-2 | Validar JSON con service_connector | `{"allowed_tools": ["service_connector"]}` | Error si tool_id no referenciado o no existe |
| TP-3 | Generar workflow simple (sin MCP/integraciones) | "Crear agente que salude" | JSON válido que pasa WorkflowDefinition |
| TP-4 | Generar workflow con MCP | "Agente que busque archivos" | JSON incluye `mcp:server:tool` en allowed_tools |
| TP-5 | Generar workflow con integración | "Notificador por Slack" | JSON incluye `service_connector` en allowed_tools |

Comando para ejecutar tests: `pytest tests/unit/`

---

**Archivo generado por UNIFICADOR siguiendo protocolo 2_UNIFICACION.md**
**Agentes consolidados:** kilo, oc, mm
**Fecha:** 2026-04-30