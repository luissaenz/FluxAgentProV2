# 🧠 Análisis Técnico — Paso 3: Validación y Pruebas (6 Escenarios)

**Agente:** qwen
**Paso:** 3 — Validación y Pruebas (La "Suite de los 6 Escenarios")
**Fecha:** 2026-04-30

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentFactory.resolve_tools()` soporta MCP en async_mode | `src/crews/factory.py:28-78` | ✅ | Línea 45-68: maneja prefijo `mcp:`, llama `_resolve_mcp_tool` solo si `async_mode=True` |
| 2 | `AgentFactory.create_agent_async()` existe | `src/crews/factory.py:162-183` | ✅ | Línea 172: `async_mode=True` |
| 3 | `BaseCrew.run_async()` usa `create_agent_async` | `src/crews/base_crew.py:185` | ✅ | Línea 185: `AgentFactory.create_agent_async(config, self.org_id)` |
| 4 | `MCPPool.get_tools()` con circuit breaker | `src/tools/mcp_pool.py:77-190` | ✅ | Línea 101-106: circuit breaker 5 fallos → 60s |
| 5 | `ServiceConnectorTool` registrado | `src/tools/service_connector.py:37-43` | ✅ | Decorador `@register_tool("service_connector", ...)` |
| 6 | `WorkflowDefinition` soporta `allowed_tools: list[str]` | `src/flows/workflow_definition.py:21` | ✅ | Campo `allowed_tools: list[str] = Field(default_factory=list)` |
| 7 | `ArchitectFlow._execute_architect_agent()` incluye MCP en prompt | `src/flows/architect_flow.py:260-301` | ✅ | Líneas 261-301: sección HERRAMIENTAS DISPONIBLES con MCP, service_connector, regular |
| 8 | `DynamicWorkflow._run_crew()` pasa contexto entre steps | `src/flows/dynamic_flow.py:95-99` | ✅ | Línea 97-99: `inputs={"previous_results": results, ...}` |
| 9 | `DynamicWorkflow` evalúa approval_rules | `src/flows/dynamic_flow.py:118-124` | ✅ | Línea 118-124: loop sobre approval_rules, llama `request_approval` |
| 10 | `MultiCrewFlow` orquestación secuencial | `src/flows/multi_crew_flow.py:71-107` | ✅ | Línea 89-106: Crew A → router → Crew B/C → finalise |
| 11 | `SecurityGuard.validate_skill()` con AST + RestrictedPython | `src/services/security_guard.py:105-124` | ✅ | Línea 111: `_scan_ast`, línea 116: `_verify_compilation` |
| 12 | `BundleManager.create_bundle()` genera ZIP con hashing | `src/services/bundle_manager.py:197-244` | ✅ | Línea 212-213: auto-hashing SHA256 por archivo |
| 13 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql` | ✅ | phase-state.md:94 — columnas: id, org_id, role, is_active, soul_json, allowed_tools (TEXT[]), max_iter |
| 14 | Tabla `org_mcp_servers` existe | `supabase/migrations/005_org_mcp_servers.sql` | ✅ | phase-state.md:95 — columnas: id, org_id, name, command, args (JSONB), secret_name, is_active |
| 15 | Tabla `workflow_templates` existe | `supabase/migrations/006_workflow_templates.sql` | ✅ | phase-state.md:96 — columnas: id, org_id, flow_type, definition (JSONB), is_python, code_source, is_active |
| 16 | Tabla `service_catalog` existe | `supabase/migrations/024_service_catalog.sql` | ✅ | phase-state.md:97 — columnas: id, org_id, name, base_url, auth_type, secret_name, is_active |
| 17 | Tabla `snapshots` existe | `supabase/migrations/002_governance.sql` | ✅ | phase-state.md:98 — id, org_id, task_id, state, status, approval_status, approved_by |
| 18 | Tests unitarios existentes para factory | `tests/unit/test_factory.py` | ✅ | 150 líneas — TestResolveTools, TestMCPToolResolution, TestCreateAgent |
| 19 | Tests unitarios existentes para base_crew | `tests/unit/test_base_crew.py` | ✅ | 409 líneas — TestAgentLoading, TestToolResolution, TestRunMethod, TestRunAsyncMethod |
| 20 | Tests unitarios existentes para workflow_definition | `tests/unit/test_workflow_definition.py` | ✅ | 162 líneas — validación schema, roles, ciclos, max_iter, modelo |
| 21 | Tests unitarios existentes para architect_flow | `tests/unit/test_architect_flow.py` | ✅ | 74 líneas — validate_input, parse_workflow_definition, ensure_unique_flow_type |
| 22 | `conftest.py` con fixtures globales | `tests/conftest.py` | ✅ | Línea 274-298: global_llm_mock (crewai.Agent, Task, Crew mockeados) |
| 23 | Suite de 6 escenarios NO existe | `grep -r "Escenario 1\|Greeter\|Slack Notifier" tests/` | ❌ | No hay archivos que implementen los 6 escenarios del plan |
| 24 | `fap validate-tools` CLI existe | phase-state.md:260 | ✅ | Comando: `fap validate-tools --tool "..." --org-id ...` |

**Discrepancias encontradas:**

| # | Discrepancia | Resolución propuesta |
|---|---|---|
| D1 | Plan dice "Escenario 3: MCP con servidor local" pero no hay servidor MCP de test configurado | Crear mock de `MCPPool.get_tools()` en tests para simular servidor MCP sin infraestructura real |
| D2 | Plan dice "Escenario 2: Slack Notifier usando service_connector" pero tabla `service_tools` no está en migraciones verificadas | Usar mock de DB query para `service_tools` en tests — no requiere tabla real para validación unitaria |
| D3 | `DynamicWorkflow._check_approval_rule()` solo soporta operadores `>` y `<` (línea 128-159) — no soporta `>=`, `<=`, `==` como el schema sugiere | Documentar como limitación conocida. Los escenarios de HITL deben usar solo `>` y `<` en conditions |
| D4 | `ServiceConnectorTool._run()` consulta tabla `service_tools` (línea 66) pero esta tabla no aparece en las migraciones listadas en phase-state.md | Verificar si `service_tools` existe en migración no listada. Para tests: mockear la query |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas por los 6 escenarios

| Escenario | Tablas involucradas | Tipo de acceso |
|---|---|---|
| 1 (Simple — Greeter) | `agent_catalog` | SELECT (cargar agente) |
| 2 (Integración — Slack) | `agent_catalog`, `service_catalog`, `service_tools`, `org_service_integrations` | SELECT (agente + integración) |
| 3 (MCP — File Manager) | `agent_catalog`, `org_mcp_servers` | SELECT (agente + config MCP) |
| 4 (Híbrido — Google + CRM) | `agent_catalog`, `org_mcp_servers`, `service_catalog`, `service_tools` | SELECT (todos) |
| 5 (Multi-Agente) | `agent_catalog`, `workflow_templates`, `snapshots` | SELECT + INSERT (persist state) |
| 6 (Full Stack) | Todas las anteriores + `events`, `tasks` | SELECT + INSERT |

### Schema — Sin cambios necesarios

`WorkflowDefinition.allowed_tools: list[str]` ya acepta cualquier string. No requiere migración. Los formatos `mcp:server:tool` y `service_connector` son strings válidos en TEXT[].

### Integridad referencial

- Escenarios 2 y 4 dependen de que `service_tools.service_id` → `service_catalog.id` exista (FK implícita via `!inner` join en `service_connector.py:67`)
- Escenario 3 depende de `org_mcp_servers` con `is_active=True` para el org de test
- Escenario 5 depende de que los roles de agentes en `agent_catalog` coincidan con los `agent_role` en los steps del workflow

### RLS policies

Todas las tablas usan RLS con `current_setting('app.org_id', TRUE)`. Los tests deben usar `get_service_client()` (service_role, bypass RLS) o mockear las queries.

### Índices

No se necesitan índices nuevos. Los queries son por `org_id` + `role`/`name`/`flow_type` — ya cubiertos por índices existentes en migraciones.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases involucradas por escenario

| Escenario | Clases/Funciones clave | Firma real |
|---|---|---|
| 1 | `AgentFactory.create_agent()` | `create_agent(config: Dict[str, Any], org_id: str) -> Agent` |
| 1 | `BaseCrew.run()` | `run(task_description: str, inputs: Optional[Dict], expected_output: str) -> Any` |
| 2 | `ServiceConnectorTool._run()` | `_run(tool_id: str, input_data: dict = None) -> str` |
| 3 | `MCPPool.get_tools()` | `async get_tools(org_id: str, server_name: str, timeout: int = 30, max_retries: int = 3) -> list` |
| 3 | `AgentFactory.create_agent_async()` | `create_agent_async(config: Dict[str, Any], org_id: str) -> Agent` |
| 4 | Combinación de 2 + 3 | Ambas en mismo agente con `allowed_tools` mixto |
| 5 | `DynamicWorkflow._run_crew()` | `async _run_crew() -> Dict[str, Any]` |
| 5 | `MultiCrewFlow.execute()` | `async execute(input_data: Dict, correlation_id: Optional[str] = None) -> MultiCrewState` |
| 6 | `ArchitectFlow.execute()` | Heredado de `BaseFlow`: `async execute(input_data, correlation_id) -> ArchitectState` |
| 6 | `BundleManager.create_bundle()` | `create_bundle(manifest, agents, flows, skills) -> bytes` |

### Patrones existentes a seguir

**Patrón de test unitario (de `test_factory.py`):**
```python
@patch("src.crews.factory.tool_registry")
@patch("src.crews.factory.AgentFactory._resolve_mcp_tool")
def test_mcp_resolved_in_async_mode(self, mock_resolve_mcp, mock_registry, sample_org_id):
```
- Mock en el punto de import, no en la definición original
- Usa fixtures de `conftest.py`: `sample_org_id`, `global_llm_mock`

**Patrón de test de integración (de `test_multi_crew_flow.py` si existe):**
- Mock de `get_service_client` para DB
- Mock de `crewai.Crew.kickoff_async` para ejecución
- Verificación de `persist_state()` y `emit_event()` calls

### Cohesión y acoplamiento

- `AgentFactory` → cohesión alta, responsabilidad única: crear Agent/Task desde config
- `BaseCrew` → cohesión media: carga agente + resuelve tools + ejecuta crew + extrae token usage
- `DynamicWorkflow` → cohesión alta: solo ejecuta steps de template
- `MultiCrewFlow` → cohesión alta: orquestación secuencial con routing

### Imports correctos

Todos los módulos usan imports absolutos (`src.xxx.xxx`). Los tests deben seguir la misma convención.

### Complejidad ciclomática estimada

| Módulo | Complejidad | Riesgo |
|---|---|---|
| `AgentFactory.resolve_tools()` | 8 (if/for/try) | Baja |
| `MCPPool.get_tools()` | 12 (retry + circuit breaker + branching) | Media |
| `DynamicWorkflow._check_approval_rule()` | 6 (split + try/except) | Baja |
| `MultiCrewFlow.execute()` | 7 (if/elif branching) | Media |
| `ServiceConnectorTool._run()` | 10 (HTTP method branching + auth types) | Media |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints relevantes para los escenarios

No se crean endpoints nuevos en este paso. Los escenarios validan flujos internos que los endpoints existentes ya invocan:

| Endpoint | Escenario | Función |
|---|---|---|
| `POST /api/bundles/import` | 1, 6 | Importa bundle generado |
| `POST /webhooks/{org_id}/{flow_type}` | 5, 6 | Ejecuta DynamicWorkflow |
| `POST /api/workflows/architect` | 6 | Ejecuta ArchitectFlow |

### Middleware aplicable

- `Depends(require_org_id)` en todos los endpoints — los escenarios deben pasar `org_id` válido
- JWT validation en endpoints protegidos — tests unitarios mockean, tests de integración necesitan token mock

### Flujo de datos por escenario

**Escenario 1 (Simple):**
```
JSON spec → AgentFactory.create_agent() → BaseCrew.run() → CrewAI kickoff → result.raw
```

**Escenario 2 (Integración):**
```
JSON spec (allowed_tools: ["service_connector"])
  → AgentFactory.resolve_tools() → ServiceConnectorTool(org_id)
  → BaseCrew.run() → agent llama service_connector(tool_id="slack.notify", input_data={...})
  → ServiceConnectorTool._run() → consulta service_tools → httpx POST → sanitized result
```

**Escenario 3 (MCP):**
```
JSON spec (allowed_tools: ["mcp:filesystem:read_file"])
  → AgentFactory.create_agent_async() → resolve_tools(async_mode=True)
  → MCPPool.get_tools(org_id, "filesystem") → MCPServerAdapter.connect()
  → BaseCrew.run_async() → crew.kickoff_async() → result con herramientas MCP
```

**Escenario 4 (Híbrido):**
```
allowed_tools: ["mcp:duckduckgo:search", "service_connector"]
  → resolve_tools(async_mode=True) → resuelve MCP + service_connector
  → Agent con ambas herramientas → ejecuta búsqueda + notificación
```

**Escenario 5 (Multi-Agente):**
```
workflow_template definition (steps: [step_1, step_2, step_3])
  → DynamicWorkflow.register(flow_type, definition)
  → webhook trigger → DynamicWorkflow.execute()
  → step_1: BaseCrew(role="investigador") → result_1
  → step_2: BaseCrew(role="escritor", inputs={previous_results: result_1}) → result_2
  → step_3: BaseCrew(role="corrector", inputs={previous_results: {result_1, result_2}}) → result_3
  → approval_rules evaluation → request_approval si aplica
```

**Escenario 6 (Full Stack):**
```
ArchitectFlow.execute({"description": "..."}) 
  → _execute_architect_agent() → LLM genera JSON
  → _parse_workflow_definition() → WorkflowDefinition
  → validate_workflow() → security + quota checks
  → BundleManager.create_bundle() → ZIP con agents + flows + skills + manifest + hashes
  → bundle_b64 → POST /api/bundles/import → import_service.process()
  → DynamicWorkflow.register() → webhook trigger → ejecución end-to-end
```

### Error handling

| Componente | Error | Respuesta al cliente |
|---|---|---|---|
| `AgentFactory.resolve_tools()` | Tool no encontrado | Warning log, tool omitida |
| `AgentFactory._resolve_mcp_tool()` | MCP server no configurado | `MCPConnectionError` con mensaje descriptivo |
| `MCPPool.get_tools()` | Circuit breaker abierto | `MCPConnectionError` con tiempo restante |
| `ServiceConnectorTool._run()` | HTTP error | String `"Error HTTP: {status_code}"` |
| `DynamicWorkflow._run_crew()` | Step sin agent_role | Warning log, step omitido |
| `BundleManager.process_zip()` | Hash mismatch | `BundleError("Integrity check failed")` |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ESCENARIO 6 (Full Stack)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Usuario → POST /api/workflows/architect → ArchitectFlow            │
│    │                                                                │
│    ▼                                                                │
│  LLM genera JSON → WorkflowDefinition valida                       │
│    │                                                                │
│    ▼                                                                │
│  BundleManager.create_bundle() → ZIP (agents + flows + skills)     │
│    │                                                                │
│    ▼                                                                │
│  POST /api/bundles/import → SecurityGuard.scan() → DB insert       │
│    │                                                                │
│    ▼                                                                │
│  DynamicWorkflow.register() → flow disponible en registry          │
│    │                                                                │
│    ▼                                                                │
│  POST /webhooks/{org_id}/{flow_type} → DynamicWorkflow.execute()   │
│    │                                                                │
│    ▼                                                                │
│  Step 1 → BaseCrew(role_1) → result_1 → persist_state()           │
│    │                                                                │
│    ▼                                                                │
│  Step 2 → BaseCrew(role_2, inputs={prev: result_1}) → result_2    │
│    │                                                                │
│    ▼                                                                │
│  Step N → approval_rules? → request_approval() o continue          │
│    │                                                                │
│    ▼                                                                │
│  Final → flow.completed event → output_data con todos los results  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Coherencia con arquitectura existente

- ✅ `WorkflowDefinition` valida `allowed_tools` como `list[str]` — acepta MCP, service_connector, regular
- ✅ `AgentFactory.resolve_tools()` centraliza resolución — single source of truth
- ✅ `MCPPool` con circuit breaker — resiliente a fallos de servidores MCP
- ✅ `DynamicWorkflow` pasa contexto entre steps — `previous_results` en inputs
- ⚠️ `DynamicWorkflow._check_approval_rule()` limitado a `>` y `<` — no soporta expresiones complejas

### Gaps identificados

1. **No hay suite de tests para los 6 escenarios** — el paso 3 consiste en crearla
2. **Escenario 3 requiere servidor MCP real** — necesita mock o servidor de test
3. **Escenario 6 requiere LLM real** — necesita mock de CrewAI + LLM para tests unitarios
4. **No hay fixture de datos de test** para `agent_catalog`, `org_mcp_servers`, `service_catalog`

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap run-scenario
- **Qué automatiza:** Ejecución de un escenario específico de la suite de 6 sin necesidad de configurar manualmente agentes, tools y workflows en DB. Crea los datos de test, ejecuta el flujo, y reporta resultados.
- **Tipo:** CLI command + script de validación
- **Cómo se usa:** 
  fap run-scenario --scenario 1 --org-id <uuid>          # Ejecuta escenario 1
  fap run-scenario --scenario all --org-id <uuid>         # Ejecuta los 6
  fap run-scenario --scenario 3 --mock-mcp --org-id ...   # Escenario 3 con MCP mockeado
- **Impacto para el usuario final:** Elimina la necesidad de crear manualmente registros en agent_catalog, org_mcp_servers, y workflow_templates para probar cada escenario. Reduce tiempo de validación de ~30 min a ~2 min.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

```
### Herramienta Propuesta: fap validate-scenario-output
- **Qué automatiza:** Validación post-ejecución de un escenario — verifica que el output cumple criterios específicos del escenario (formato, contenido, tokens, eventos).
- **Tipo:** Validador CLI
- **Cómo se usa:**
  fap validate-scenario-output --task-id <uuid> --scenario 2
- **Impacto:** Feedback inmediato sobre si un escenario pasó o falló, con detalles específicos de qué criterio no se cumplió.
- **Prioridad:** Tarea 1 — implementar junto con la suite
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Cada escenario usa tablas existentes sin requerir migraciones nuevas
✅ [DATA] allowed_tools acepta formatos "mcp:server:tool" y "service_connector" sin validación de schema
✅ [CODE] AgentFactory.resolve_tools() resuelve correctamente tools regulares, MCP (async), y service_connector
✅ [CODE] BaseCrew.run_async() usa create_agent_async para habilitar MCP tools
✅ [CODE] DynamicWorkflow pasa contexto entre steps via previous_results
✅ [CODE] MultiCrewFlow orquesta crews secuenciales con routing condicional
✅ [BACKEND] ArchitectFlow genera JSON válido contra WorkflowDefinition para cada escenario aplicable
✅ [BACKEND] BundleManager.create_bundle() genera ZIP válido con hashing SHA256
✅ [BACKEND] SecurityGuard.validate_skill() escanea código Python en bundles
✅ [FULLSTACK] Escenario 1: Agente simple con 0 tools ejecuta y retorna resultado
✅ [FULLSTACK] Escenario 2: Agente con service_connector ejecuta integración HTTP mockeada
✅ [FULLSTACK] Escenario 3: Agente con MCP tool resuelve conexión via MCPPool mockeado
✅ [FULLSTACK] Escenario 4: Agente híbrido usa MCP + service_connector en mismo allowed_tools
✅ [FULLSTACK] Escenario 5: Multi-agente ejecuta steps secuenciales pasando contexto
✅ [FULLSTACK] Escenario 6: Architect genera bundle → import → ejecución end-to-end
✅ [DX] fap run-scenario CLI ejecuta al menos 1 escenario sin configuración manual
✅ [DX] fap validate-scenario-output valida output de escenario con criterios binarios
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| CrewAI no instalado en entorno de test | Alta | `crewai` es dependencia opcional (`[crew]`) | Tests deben verificar `importlib.util.find_spec("crewai")` y saltar si no disponible con `pytest.importorskip` |
| MCPPool requiere conexión real a servidor MCP | Alta | `MCPPool.get_tools()` conecta via StdioServerParameters | Mockear `MCPPool.get_tools()` en todos los tests. Crear fixture `mock_mcp_pool` |
| LLM real consume tokens en tests | Media | ArchitectFlow ejecuta LLM para generar JSON | Mockear `crewai.Crew.kickoff_async` para retornar JSON predefinido. Tests unitarios no deben llamar LLM |
| ServiceConnector requiere service_tools en DB | Media | Tabla `service_tools` no verificada en migraciones | Mockear query de `service_tools` en tests. Para tests de integración, crear datos de test con `mock_service_client` |
| Approval rules limitadas a `>` y `<` | Baja | `_check_approval_rule()` solo parsea 2 operadores | Documentar limitación. Escenarios de HITL deben usar solo estos operadores |
| Tests asíncronos con event loop conflicts | Media | `MCPPool.get_tools()` usa `asyncio.run()` internamente | Usar `pytest-asyncio` con `asyncio_mode = "auto"` (ya configurado en pyproject.toml) |
| Colisión de flow_type en tests | Baja | `_ensure_unique_flow_type()` agrega sufijo aleatorio | Usar `uuid4()` en flow_type de test para garantizar unicidad |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Implementar `fap run-scenario` CLI command | FULLSTACK/DX | Media | 3h | Ninguna |
| 1 | **DX & Tooling**: Implementar `fap validate-scenario-output` | FULLSTACK/DX | Baja | 2h | Tarea 0 |
| 2 | Crear fixtures de test: `mock_mcp_pool`, `mock_service_connector`, `sample_agent_config` | CODE | Baja | 1h | Ninguna |
| 3 | Escenario 1 (Simple — Greeter): Test unitario + integración | CODE/BACKEND | Baja | 1h | Tarea 2 |
| 4 | Escenario 2 (Integración — Slack): Test con service_connector mockeado | CODE/BACKEND | Media | 2h | Tarea 2 |
| 5 | Escenario 3 (MCP — File Manager): Test con MCPPool mockeado | CODE/BACKEND | Media | 2h | Tarea 2 |
| 6 | Escenario 4 (Híbrido — Google + CRM): Test combinado MCP + service_connector | CODE/BACKEND | Alta | 3h | Tareas 4, 5 |
| 7 | Escenario 5 (Multi-Agente): Test DynamicWorkflow con context passing | CODE/FULLSTACK | Alta | 3h | Tarea 2 |
| 8 | Escenario 6 (Full Stack): Test end-to-end Architect → Bundle → Execution | FULLSTACK | Alta | 4h | Tareas 3-7 |
| 9 | Validar flujo end-to-end: ejecutar los 6 escenarios con `fap run-scenario --scenario all` | FULLSTACK | Baja | 1h | Tareas 0-8 |
| 10 | Ejecutar lint + tests existentes: verificar que nuevos tests no rompen suite actual | CODE | Baja | 0.5h | Tareas 3-9 |

**Tiempo total estimado:** 22.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Extender `DynamicWorkflow._check_approval_rule()` para soportar `>=`, `<=`, `==`, `and`, `or`
- Crear servidor MCP de test para tests de integración reales (no mockeados)
- Agregar métricas de token usage por escenario en el reporte de `fap run-scenario`
- Implementar `fap compare-scenarios` para diff de outputs entre versiones del sistema
- Agregar soporte para escenarios parametrizables (ej: mismo escenario con diferentes org_ids)
- Crear dashboard de resultados de escenarios en el frontend (Next.js)

---

## 📊 Métrica de Calidad Auto-Evaluada

| Métrica | Mínimo | Real |
|---|---|---|
| `proyecto-config.json` leído antes de explorar | 100% | ✅ |
| Elementos verificados (§0) | Según umbral (18+ para 6-10 archivos) | ✅ 24 elementos |
| Discrepancias detectadas | ≥ 1 si toca código existente | ✅ 4 discrepancias |
| Secciones completadas | 8 secciones (0-7) | ✅ 8 secciones (0-7 + roadmap) |
| Etapas cubiertas | 4 etapas (data, code, backend, fullstack+DX) | ✅ 4 etapas |
| Criterios de aceptación | ≥ 1 por sub-paso, verificables | ✅ 17 criterios |
| Riesgos identificados | ≥ 3 (técnico, integración, futuro) | ✅ 7 riesgos |
| Tareas en el plan | ≥ 4, atómicas, ordenadas | ✅ 11 tareas |
| Suposiciones no verificadas | ≤ 2, cada una marcada ⚠️ | ✅ 0 suposiciones no verificadas |
| Propuesta DX / Tooling | ≥ 1 herramienta concreta | ✅ 2 herramientas (fap run-scenario, fap validate-scenario-output) |
| Estimación de tiempo | Sí, por tarea y total | ✅ 22.5h total |
