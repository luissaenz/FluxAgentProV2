# Análisis — Paso 3: Validación y Pruebas (6 Escenarios)

**Fecha:** 2026-04-30
**Fase:** `details4agents`
**Plan:** `DEVS/plan.md` — Paso 3
**Agente:** mm
**Dependencias:** Paso 2 ✅ Completado

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `ArchitectFlow` existe y es funcional | grep en `src/flows/` | ✅ | `architect_flow.py:51` |
| 2 | `validate_architect` CLI command existe | ls `src/cli/commands/` | ✅ | `validate_architect.py` — 262 líneas |
| 3 | `validate_architect` registrado en CLI | read `src/cli/main.py` | ✅ | Línea 39: `from .commands.validate_architect import validate_architect_output` |
| 4 | `WorkflowDefinition` acepta `allowed_tools` arbitrarias | read `workflow_definition.py:21` | ✅ | `allowed_tools: list[str]` sin restricciones |
| 5 | `workflow_guardrails.SAFE_BUILTIN_TOOLS` incluye `service_connector` | read `workflow_guardrails.py:32` | ✅ | `"service_connector"` en SAFE_BUILTIN_TOOLS |
| 6 | Prompt del Architect expandido con MCP y service_connector | read `architect_flow.py:259-301` | ✅ | Sección "HERRAMIENTAS DISPONIBLES" incluye 4 ejemplos MCP + 1 service_connector |
| 7 | `AgentFactory.resolve_tools()` maneja `mcp:` prefix | read `factory.py:18-78` | ✅ | `_parse_mcp_prefix()` + bifurcación sync/async |
| 8 | `MCPPool.get_tools()` existe y es async | read `mcp_pool.py:77` | ✅ | `async def get_tools(...)` |
| 9 | `ServiceConnectorTool` registrada con `@register_tool` | read `service_connector.py:37` | ✅ | `@register_tool("service_connector", ...)` |
| 10 | Test suite existente para ArchitectFlow | ls `tests/integration/` | ✅ | `test_architect_flow_additional.py` — 615 líneas |
| 11 | Test suite unitaria para ArchitectFlow | ls `tests/unit/` | ✅ | `test_architect_flow.py` — 74 líneas |
| 12 | Tabla `org_mcp_servers` existe | grep en migrations | ✅ | `005_org_mcp_servers.sql` |
| 13 | Tabla `service_catalog` existe | grep en migrations | ✅ | `024_service_catalog.sql` |
| 14 | `BundleManager.create_bundle()` existe | read `services/bundle_manager.py` | ✅ | `create_bundle(manifest, agents, flows, skills)` |
| 15 | Tests e2e para certificación MVP | read `tests/e2e/test_mvp_certification.py` | ✅ | 7 criterios de certificación |
| 16 | Tests de validación CLI bundles | read `tests/integration/test_bundle_cli_validate.py` | ✅ | 10 tests para `fap validate` |
| 17 | BaseCrew usa `create_agent_async` para paths async | read `base_crew.py:113` | ✅ | `create_agent_async()` para MCP support |
| 18 | Paso 2 análisis final unificado | read `02-Upgrade-del-Cerebro/analisis-FINAL.md` | ✅ | Consolida D1-D6 |
| 19 | Paso 2 validación aprobada | read `02-Upgrade-del-Cerebro/validacion.md` | ✅ | 10/10 criterios cumplidos |
| 20 | Phase-state actualizado con implementaciones completas | read `DEVS/phase-state.md` | ✅ | Tabla de componentes ✅ funcional |

**Discrepancias encontradas:**

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | El plan original no específica estructura de tests para los 6 escenarios | Implementar suite basada en `test_architect_flow_additional.py` existente + `test_mvp_certification.py` como patrón |
| D2 | No existe test específico para `validate_architect` (ID-002 en validacion.md) | Crear `tests/unit/test_validate_architect.py` como parte del paso |
| D3 | Hay un typo en `validate_architect.py:108` ("service_connectorreferenciado") | Corregir como parte de la implementación del paso |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Elementos afectados:**

- **Tablas leídas:**
  - `agent_catalog` — verificar agents generados por Architect en escenarios
  - `workflow_templates` — verificar workflows generados
  - `org_mcp_servers` — verificar servers MCP configurados (para escenarios 3, 4)
  - `service_catalog`, `service_tools` — verificar integraciones disponibles (para escenarios 2, 4)
  - `snapshots` — verificar que HITL funciona (para escenarios 5, 6 con approval_threshold)

- **No hay cambios de schema** — Paso 3 es validación y pruebas, no modifica estructura de datos.

**Integridad referencial:**
- N/A — sin cambios en DB

**RLS policies:**
- N/A — solo lectura

**Índices necesarios:**
- N/A

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos directamente relacionados al paso

#### `tests/integration/test_architect_flow_additional.py` (615 líneas)

**Funciones/test classes:**
- `TestArchitectFlowExecution` — tests lifecycle completo
- `TestWorkflowDefinitionParsing` — tests de parsing y validación
- `TestFlowTypeUniqueness` — tests de uniqueness flow_type
- `TestTemplatePersistence` — tests de persistencia (SKIPPED — bundle-driven)
- `TestAgentPersistence` — tests de persistencia agentes (SKIPPED)
- `TestDynamicFlowRegistration` — tests de registro dinámico (SKIPPED)
- `TestValidationIntegration` — tests de validación integración

#### `tests/unit/test_architect_flow.py` (74 líneas)

**Tests existentes:**
- `test_validate_input_rejects_empty`
- `test_parse_workflow_definition_extracts_json`
- `test_parse_workflow_definition_strips_markdown`
- `test_ensure_unique_flow_type_adds_suffix`
- `test_ensure_unique_flow_type_returns_same_if_new`

#### `src/cli/commands/validate_architect.py` (262 líneas)

**Funciones:**
- `_load_json(path)` — cargar JSON desde archivo
- `_validate_structural(data)` — validar contra WorkflowDefinition
- `_validate_mcp_tools(data, org_id)` — validar servers MCP en org
- `_validate_service_connectors(data, org_id)` — validar service_tools activos
- `_validate_tools_registry(data)` — validar tools contra TOOL_REGISTRY
- `validate_architect_output(json_path, org_id)` — CLI entry point

**Imports usados:**
- `typer`, `rich.console`, `rich.table`
- `WorkflowDefinition` desde `src.flows.workflow_definition`
- `get_service_client` desde `src.db.session`
- `tool_registry` desde `src.tools.registry`

#### `src/flows/workflow_guardrails.py` (104 líneas)

**Constantes:**
- `ALLOWED_MODELS` — modelos válidos
- `DANGEROUS_TOOLS` — tools bloqueadas (blocklist)
- `SAFE_BUILTIN_TOOLS` — tools seguras (incluye `service_connector`)

**Funciones:**
- `validate_workflow(workflow_def, org_id)` — validación principal
- `_validate_org_quota(org_id, workflow_def)` — validación quota

### Archivos de referencia (patrones existentes)

**Patrón tests e2e:** `tests/e2e/test_mvp_certification.py`
- 7 criterios de certificación
- Usa `TestClient` de FastAPI, `CliRunner` de Typer
- Tests: validate zip, import API, hash mismatch, malicious skill blocked, atomicity, warmup, RestrictedPython version

**Patrón tests integración:** `tests/integration/test_bundle_cli_validate.py`
- Tests para `fap validate` command
- Valida estructura, integridad, seguridad
- 10 tests covering success, failure, edge cases

### Dependencias

- `pytest>=8.3.0`, `pytest-asyncio>=0.24.0`, `pytest-mock>=3.14.0`
- `typer`, `rich` para CLI
- `fastapi.testclient` para tests de API

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints y flujos relevantes

**Flujo end-to-end de los 6 escenarios:**

```
Escenario 1-6
    ↓
POST /api/flows/architect (o CLI fap run architect)
    ↓
ArchitectFlow._run_crew()
    ↓
_evaluate_architect_agent(description) ← Prompt expandido (Paso 2)
    ↓
CrewAI Agent genera JSON
    ↓
_parse_workflow_definition()
    ↓
validate_workflow() ← Security + quota check
    ↓
BundleManager.create_bundle() → ZIP
    ↓
POST /api/bundles/import → agent_catalog + workflow_templates
    ↓
BaseCrew.run_async() ← usa create_agent_async para MCP
    ↓
MCPPool.get_tools() / ServiceConnectorTool._run()
```

**Endpoints usados:**
- `POST /api/bundles/import` — importar bundle generado
- `GET /api/flows/{flow_type}` — obtener workflow generado
- `GET /api/agents/{role}` — obtener agent config

**Middleware:**
- `require_org_id` — tenant isolation
- `verify_jwt` — autenticación
- `verify_org_membership` — autorización

### Contratos de los 6 escenarios

| Escenario | Input | Output esperado | Integración |
|-----------|-------|----------------|-------------|
| 1 (Greeter) | NL: "Crear agente que salude" | JSON válido simple | Ninguna |
| 2 (Slack Notifier) | NL: "Agente notificador por Slack" | JSON con `service_connector` | service_catalog |
| 3 (File Manager MCP) | NL: "Agente gestor de archivos" | JSON con `mcp:server:tool` | org_mcp_servers |
| 4 (Híbrido) | NL: "Agente busca Google y notifica CRM" | JSON con ambos | MCP + service_connector |
| 5 (Multi-Agente) | NL: "Flujo Investigador->Escritor->Corrector" | JSON con ≥2 agents, steps con depends_on | Ninguna |
| 6 (Full Stack) | NL: "Flujo complejo con todo" | JSON con MCP + service_connector + multi-agent + approval | Todas |

### Error handling

- JSON malformado → `ValueError` en `_parse_workflow_definition`
- Schema inválido → `WorkflowValidationError` en `validate_workflow`
- MCP server no configurado → Warning en `validate_architect` (no blocking)
- service_connector sin config activa → Warning en `validate_architect` (no blocking)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo para cada escenario

**Escenario 1 (Simple — Greeter):**
```
Usuario: "Crear un agente que salude cordialmente"
    ↓
ArchitectFlow genera JSON simple (1 agent, 1 step)
    ↓
fap validate-architect-output output.json --org-id {org}
    ↓
bundle ZIP generado
    ↓
POST /api/bundles/import
    ↓
Agent "greeter" persiste en agent_catalog
    ↓
BaseCrew.run_async() ejecuta agent
```

**Escenario 2 (Integración — Slack Notifier):**
```
Usuario: "Crear agente que notifique al equipo por Slack"
    ↓
ArchitectFlow genera JSON con ["service_connector"] en allowed_tools
    ↓
fap validate-architect-output output.json --org-id {org}
    ↓ (valida service_tools activas en org)
    ↓
bundle ZIP → POST /api/bundles/import
    ↓
ServiceConnectorTool._run(tool_id="slack.send_message", input_data={...})
    ↓
httpx POST a webhook de Slack
```

**Escenario 3 (MCP — File Manager):**
```
Usuario: "Crear agente que gestione archivos locales"
    ↓
ArchitectFlow genera JSON con ["mcp:filesystem:read_file", "mcp:filesystem:write_file"]
    ↓
fap validate-architect-output output.json --org-id {org}
    ↓ (valida org_mcp_servers tiene "filesystem" activo)
    ↓
bundle ZIP → POST /api/bundles/import
    ↓
BaseCrew.run_async() usa create_agent_async (async_mode=True)
    ↓
MCPPool.get_tools(org_id, "filesystem") → herramientas MCP
```

**Escenario 4 (Híbrido):**
```
Usuario: "Agente que busca en Google y notifica por CRM"
    ↓
ArchitectFlow genera JSON con ["mcp:google:search", "service_connector"]
    ↓
fap validate-architect-output output.json --org-id {org}
    ↓
bundle ZIP → import
    ↓
BaseCrew.run_async() resuelve ambas tools
```

**Escenario 5 (Multi-Agente):**
```
Usuario: "Crear flujo investigador que busque, escriba y corrija"
    ↓
ArchitectFlow genera JSON con:
  - 3 agents: researcher, writer, editor
  - 3 steps con depends_on: step_1→step_2→step_3
    ↓
fap validate-architect-output output.json --org-id {org}
    ↓
bundle ZIP → import
    ↓
DynamicWorkflow._run_crew() ejecuta steps secuenciales
    ↓
Cada step crea BaseCrew, pasa previous_results al siguiente
```

**Escenario 6 (Full Stack):**
```
Usuario: "Flujo complejo: búsqueda MCP + integración HTTP + multi-agent + approval"
    ↓
ArchitectFlow genera JSON con:
  - agents con MCP tools + service_connector
  - steps con depends_on
  - approval_threshold en algún step
    ↓
fap validate-architect-output output.json --org-id {org}
    ↓
bundle ZIP → import
    ↓
DynamicWorkflow._run_crew() con approval check
    ↓
Si approval_threshold se cumple → HITL pause → snapshots table
```

### Coherencia

- ✅ `_execute_architect_agent()` ya tiene prompt expandido con MCP y service_connector (Paso 2)
- ✅ `validate_architect` valida MCP servers y service_tools antes de importar
- ✅ `workflow_guardrails.SAFE_BUILTIN_TOOLS` incluye `service_connector`
- ✅ `AgentFactory.resolve_tools()` bifurca sync/async para MCP
- ✅ `DynamicWorkflow` ejecuta steps secuenciales con context passing

### Gaps

| Gap | Descripción | Impacto |
|---|---|---|
| G1 | No hay test específico para `validate_architect` (ID-002 en validacion.md) | Gap de cobertura — herramienta validada manualmente pero no con tests automáticos |
| G2 | Escenarios 5-6 requieren approval_threshold working — no verificado end-to-end | Podría fallar en runtime sin tests |
| G3 | El typo en `validate_architect.py:108` ("service_connectorreferenciado") causa mensaje feo | No bloqueante pero degrada UX |

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap test-scenarios
- **Qué automatiza:** Ejecuta los 6 escenarios de prueba contra el endpoint /api/flows/architect, comparando output con	expected. Detecta prompt injection, cycle dependencies, y invalid tool references.
- **Tipo:** CLI command
- **Ubicación:** src/cli/commands/test_scenarios.py (registrado en src/cli/main.py)
- **Cómo se usa:**
  ```
  fap test-scenarios --scenario 1           # Solo escenario 1
  fap test-scenarios --scenario all         # Todos los escenarios
  fap test-scenarios --org-id {uuid}        # Con org para validar MCP/svc
  ```
- **Impacto para el usuario final:**
  - El implementador puede verificar que los 6 escenarios funcionan sin hacer requests manuales
  - Detecta regresiones antes de commit
  - Valida que validate_architect funciona correctamente en contexto de los 6 escenarios
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] Test suite para `fap validate-architect-output` existe en tests/unit/
✅ [CODE] Todos los tests unitarios pasan (≥248 tests)
✅ [DX] fap test-scenarios existe y ejecuta sin errores
✅ [CODE] 6 escenarios pueden ejecutarse con mock de LLM (sin costo real)
✅ [DATA] Escenario 1 genera JSON simple que pasa WorkflowDefinition
✅ [DATA] Escenario 2 genera JSON con service_connector que pasa validación
✅ [DATA] Escenario 3 genera JSON con mcp:server:tool que pasa validación
✅ [DATA] Escenario 4 genera JSON híbrido (MCP + service_connector)
✅ [DATA] Escenario 5 genera JSON multi-agent con depends_on válido (sin ciclos)
✅ [DATA] Escenario 6 genera JSON full stack con approval_threshold
✅ [BACKEND] Todos los bundles generados se pueden importar vía POST /api/bundles/import
✅ [FULLSTACK] validate_architect output.json para cada escenario no genera errores
✅ [DX] Typo en validate_architect.py:108 corregido
✅ [DX] Dogfooding: fap test-scenarios usa fap validate-architect-output internamente
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1 | Media | Los 6 escenarios requieren LLM real o mock costoso | Usar mocks de Agent que retornen JSON predefinido — sin llamado real a LLM |
| R2 | Baja | Escenarios 5-6 con approval_threshold pueden fallar en runtime | Testear con mock de snapshots table |
| R3 | Baja | validate_architect.py tiene typo que degrada mensaje de error | Corregir en Tarea 1 |
| R4 | Media | No hay tests para validate_architect tool — ID-002 | Crear tests/unit/test_validate_architect.py |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `fap test-scenarios` CLI | FULLSTACK/DX | Media | 2h | Ninguna |
| 1 | Corregir typo en `validate_architect.py:108` | CODE | Baja | 0.25h | Ninguna |
| 2 | Crear `tests/unit/test_validate_architect.py` | CODE | Media | 2h | Ninguna |
| 3 | Implementar test mock para LLM en `test_architect_flow` | CODE | Media | 1h | Ninguna |
| 4 | Implementar escenario 1 (Greeter) — test simple | FULLSTACK | Baja | 0.5h | Tarea 0 |
| 5 | Implementar escenario 2 (Slack Notifier) — test service_connector | FULLSTACK | Baja | 0.5h | Tarea 0 |
| 6 | Implementar escenario 3 (File Manager) — test MCP | FULLSTACK | Baja | 0.5h | Tarea 0 |
| 7 | Implementar escenario 4 (Híbrido) — test ambos | FULLSTACK | Media | 0.75h | Tareas 5-6 |
| 8 | Implementar escenario 5 (Multi-Agent) — test depends_on | FULLSTACK | Media | 1h | Tarea 3 |
| 9 | Implementar escenario 6 (Full Stack) — test approval | FULLSTACK | Alta | 1.5h | Tareas 3, 5, 6, 8 |
| 10 | Ejecutar suite completa con `pytest tests/` | FULLSTACK | Baja | 0.5h | Tareas 1-9 |

**Tiempo total estimado:** 10 horas (por la necesidad de mocks y validación e2e)

---

## 🔮 Roadmap (NO implementar ahora)

- Agregar test de rendimiento para los 6 escenarios (tokens consumidos, latency)
- Test de carga: 100 bundles generados simultáneamente
- Integración con Supabase Realtime para verificar events en escenarios con approval
- Coverage report para validate_architect con `pytest --cov`
- Agregar `fap scaffold scenario` — wizard que guía creación de scenario tests

---

## Notas de Implementación Previas (Paso 2)

El análisis-mm.md del Paso 2 identificó:
- D1: Prompt NO menciona convenciones MCP y service_connector → **RESUELTO en Paso 2** (prompt expandido)
- D2: WorkflowDefinition ya soporta `allowed_tools` arbitrarias → **CONFIRMADO** (no necesita cambios)
- D3: workflow_guardrails no tiene explicititud sobre service_connector → **RESUELTO** (SAFE_BUILTIN_TOOLS incluye `"service_connector"`)
- D4: Prompt no da ejemplos de MCP o integraciones → **RESUELTO** (4 ejemplos MCP + 1 service_connector)

El analisis-FINAL.md del Paso 2 resume las discrepancias críticas consolidadas (D1-D6) y las resoluciones aplicadas. El implementador del Paso 3 debe construir sobre lo implementado en Pasos 1 y 2.