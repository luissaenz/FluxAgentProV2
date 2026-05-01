# 🏛️ Análisis Unificado — Paso 3: Validación y Pruebas (6 Escenarios)

**Fase:** `details4agents`
**Paso:** 3 — Validación y Pruebas (La "Suite de los 6 Escenarios")
**Fecha:** 2026-04-30
**Dependencias:** Paso 1 ✅ | Paso 2 ✅

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| qwen | ✅ 24 elementos con archivo:línea | 4 | ✅ fap run-scenario + validate-scenario-output | ✅ Referencias concretas a líneas de código | 4.5 |
| mm | ✅ 20 elementos con archivo:línea | 3 | ✅ fap test-scenarios | ✅ Referencias a archivos y líneas | 4.0 |
| kilo | ✅ 18 elementos | 6 (archivos faltantes) | ✅ Scenario Runner (script) | ⚠️ Menos granularidad en referencias | 3.5 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | Plan dice "Escenario 3: MCP con servidor local" pero no hay servidor MCP de test configurado | qwen, kilo | ✅ `src/tools/mcp_pool.py:77-190` — requiere conexión real | Mockear `MCPPool.get_tools()` en tests. Fixture `mock_mcp_pool` retorna tools simuladas sin infraestructura real. |
| 2 | Tabla `service_tools` referenciada en `service_connector.py:66` pero no aparece en migraciones listadas en phase-state.md | qwen | ✅ `src/tools/service_connector.py:66` — query a `service_tools` | Verificar si existe en migración no listada. Para tests unitarios: mockear query. Para integración: crear datos con `mock_service_client`. |
| 3 | `DynamicWorkflow._check_approval_rule()` solo soporta operadores `>` y `<` (línea 128-159) — no soporta `>=`, `<=`, `==` | qwen | ✅ `src/flows/dynamic_flow.py:128-159` | Documentar como limitación conocida. Escenarios HITL usan solo `>` y `<`. No corregir en este paso. |
| 4 | Typo en `validate_architect.py:108` ("service_connectorreferenciado") | mm | ✅ `src/cli/commands/validate_architect.py:108` | Corregir string como parte de implementación. No bloqueante pero degrada UX. |
| 5 | No hay tests para `fap validate-architect-output` (ID-002 en validacion.md Paso 2) | mm | ✅ Herramienta existe, sin tests automáticos | Crear `tests/unit/test_validate_architect.py` con cobertura de validación estructural, MCP y service_connector. |
| 6 | Los 6 archivos de test para escenarios no existen — requieren creación desde cero | qwen, mm, kilo | ✅ `grep -r "Escenario\|Greeter\|Slack" tests/` → sin resultados | Crear suite de tests siguiendo patrones de `test_parity_suite.py` y `test_mvp_certification.py`. |
| 7 | Plan dice "Modificar BaseCrew._resolve_tools para MCP" pero es dead code | phase-state (D1) | ✅ `src/crews/base_crew.py` — `run()` usa `AgentFactory.create_agent()` directamente | Ya resuelto en Paso 1. Resolución centralizada en `AgentFactory.resolve_tools()`. Confirmado funcional. |
| 8 | `crewai` es dependencia opcional (`[crew]`) — puede no estar en entorno de test | qwen | ✅ `pyproject.toml` — `crewai>=0.100.0` en `[crew]` | Tests usan `pytest.importorskip("crewai")` para saltar si no disponible. |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo:** Crear la suite de validación de los 6 escenarios definidos en el plan (Paso 3), verificando que ArchitectFlow genera bundles válidos con soporte MCP, service_connector y multi-agente, y que estos bundles se importan y ejecutan correctamente end-to-end.

**Correcciones críticas al plan:**
- El plan asume infraestructura MCP real para Escenario 3 → se mockea para tests unitarios.
- El plan no menciona la tabla `service_tools` fuera de `service_connector.py` → se verifica y mockea.
- El plan no contempla tests para `validate-architect-output` → se agregan.
- Typo en `validate_architect.py:108` se corrige como parte del paso.

**Decisión DX:** Se fusionan las 3 propuestas (qwen: `fap run-scenario` + `validate-scenario-output`, mm: `fap test-scenarios`, kilo: `Scenario Runner`) en un único **CLI command `fap test-scenarios`** que ejecuta los 6 escenarios, valida outputs, y genera reporte consolidado. El implementador DEBE crearlo primero y usarlo para validar cada escenario (dogfooding obligatorio).

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Implementador ejecuta `fap test-scenarios --scenario all --org-id <uuid>`
2. Para cada escenario (1-6):
   a. Genera input NL (descripción del agente/flujo)
   b. Ejecuta ArchitectFlow con LLM mockeado → JSON WorkflowDefinition
   c. Valida JSON con `validate_architect_output` → verifica tools MCP, service_connector, schema
   d. Genera bundle ZIP con `BundleManager.create_bundle()`
   e. Importa bundle vía `POST /api/bundles/import` → persiste en `agent_catalog` + `workflow_templates`
   f. Ejecuta workflow con `BaseCrew.run_async()` / `DynamicWorkflow.execute()` → tools mockeadas
   g. Valida output contra criterios específicos del escenario
3. Reporte consolidado: ✅/❌ por escenario + detalle de fallos

### Edge Cases MVP

- **CrewAI no instalado:** Tests saltan con `pytest.importorskip("crewai")`
- **MCP server no configurado:** `MCPPool.get_tools()` mockeado retorna tools simuladas
- **service_tools sin config activa:** `validate_architect` emite warning (no blocking) — tests mockean query
- **JSON malformado de Architect:** `_parse_workflow_definition()` lanza `ValueError` — tests validan manejo
- **Approval rules limitadas:** Solo `>` y `<` soportados — escenarios HITL usan estos operadores
- **Colisión de flow_type:** `_ensure_unique_flow_type()` agrega sufijo — tests usan `uuid4()` para unicidad
- **Async event loop conflicts:** `MCPPool.get_tools()` usa `asyncio.run()` — tests usan `pytest-asyncio` con `asyncio_mode = "auto"`

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. `src/cli/commands/test_scenarios.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\test_scenarios.py`
- **Tipo de cambio:** Creación
- **Descripción:** CLI command `fap test-scenarios` que ejecuta los 6 escenarios de validación. Orquesta ArchitectFlow mockeado, validación de output, import de bundle, ejecución de workflow, y reporte.
- **Interfaces clave:** `test_scenarios(scenario: str, org_id: str, mock_mcp: bool)` — entry point Typer
- **Patrones a seguir:** `src/cli/commands/validate_architect.py` (estructura Typer + Rich), `src/cli/commands/validate.py` (reporte con tablas)

#### 2. `tests/unit/test_validate_architect.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\unit\test_validate_architect.py`
- **Tipo de cambio:** Creación
- **Descripción:** Tests unitarios para `validate_architect_output` — validación estructural, MCP tools, service connectors, registry tools.
- **Interfaces clave:** Tests parametrizados con fixtures de `conftest.py`
- **Patrones a seguir:** `tests/unit/test_factory.py` (mock en punto de import), `tests/unit/test_workflow_definition.py` (validación schema)

#### 3. `tests/conftest.py` (MODIFICACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\conftest.py`
- **Tipo de cambio:** Modificación — agregar fixtures
- **Descripción:** Nuevos fixtures: `mock_mcp_pool`, `mock_service_connector`, `sample_agent_config`, `mock_llm_response`
- **Interfaces clave:** `@pytest.fixture def mock_mcp_pool(mocker)` — mockea `MCPPool.get_tools()`
- **Patrones a seguir:** Fixtures existentes en `conftest.py:274-298` (`global_llm_mock`)

#### 4. `tests/e2e/test_scenario_1_greeter.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\e2e\test_scenario_1_greeter.py`
- **Tipo de cambio:** Creación
- **Descripción:** Escenario 1 — agente simple sin tools. Verifica ArchitectFlow genera JSON válido, bundle importa, BaseCrew ejecuta.
- **Patrones a seguir:** `tests/e2e/test_mvp_certification.py`, `tests/e2e/test_parity_suite.py`

#### 5. `tests/e2e/test_scenario_2_integration.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\e2e\test_scenario_2_integration.py`
- **Tipo de cambio:** Creación
- **Descripción:** Escenario 2 — agente con `service_connector`. Verifica resolución de tools, mock de HTTP call, validación de output.
- **Patrones a seguir:** Mismo patrón + mock de `httpx` para HTTP calls

#### 6. `tests/e2e/test_scenario_3_mcp.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\e2e\test_scenario_3_mcp.py`
- **Tipo de cambio:** Creación
- **Descripción:** Escenario 3 — agente con MCP tools. Verifica `create_agent_async`, `MCPPool.get_tools()` mockeado, ejecución async.
- **Patrones a seguir:** `tests/unit/test_factory.py::TestMCPToolResolution`

#### 7. `tests/e2e/test_scenario_4_hybrid.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\e2e\test_scenario_4_hybrid.py`
- **Tipo de cambio:** Creación
- **Descripción:** Escenario 4 — agente con MCP + service_connector. Verifica resolución mixta en `resolve_tools(async_mode=True)`.
- **Patrones a seguir:** Combinación de escenarios 2 y 3

#### 8. `tests/e2e/test_scenario_5_multi_agent.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\e2e\test_scenario_5_multi_agent.py`
- **Tipo de cambio:** Creación
- **Descripción:** Escenario 5 — flujo multi-agente secuencial. Verifica `DynamicWorkflow._run_crew()`, context passing via `previous_results`, `depends_on`.
- **Patrones a seguir:** `tests/integration/test_architect_flow_additional.py::TestDynamicFlowRegistration`

#### 9. `tests/e2e/test_scenario_6_full_stack.py` (CREACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\e2e\test_scenario_6_full_stack.py`
- **Tipo de cambio:** Creación
- **Descripción:** Escenario 6 — full stack: Architect → Bundle → Import → Execution con MCP + service_connector + multi-agent + approval.
- **Patrones a seguir:** `tests/e2e/test_mvp_certification.py` (end-to-end completo)

#### 10. `src/cli/commands/validate_architect.py` (MODIFICACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\validate_architect.py`
- **Tipo de cambio:** Modificación — corregir typo línea 108
- **Descripción:** Corregir string "service_connectorreferenciado" → "service_connector referenciado"
- **Evidencia:** `validate_architect.py:108`

#### 11. `src/cli/main.py` (MODIFICACIÓN)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\main.py`
- **Tipo de cambio:** Modificación — registrar nuevo command
- **Descripción:** Agregar import y registro de `test_scenarios` command
- **Patrones a seguir:** `src/cli/main.py:39` — patrón existente de registro

### DX & Tooling — Tarea 0 (OBLIGATORIO)

### Herramienta: `fap test-scenarios`
- **Qué automatiza:** Ejecución de los 6 escenarios de validación contra ArchitectFlow, con validación automática de outputs, detección de regresiones, y reporte consolidado. Elimina la necesidad de configurar manualmente agentes, tools y workflows en DB para cada prueba.
- **Tipo:** CLI command (Typer) + script de validación integrado
- **Ubicación:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\test_scenarios.py` (registrado en `src/cli/main.py`)
- **Cómo se usa:**
  ```
  fap test-scenarios --scenario 1 --org-id <uuid>          # Solo escenario 1
  fap test-scenarios --scenario all --org-id <uuid>         # Los 6 escenarios
  fap test-scenarios --scenario 3 --mock-mcp --org-id ...   # Escenario 3 con MCP mockeado
  fap test-scenarios --scenario all --report-json output.json  # Con reporte
  ```
- **Impacto para el usuario final:** Reduce tiempo de validación de ~30 min por escenario a ~2 min totales. Detecta regresiones antes de commit. Valida que `validate-architect-output` funciona correctamente en contexto de cada escenario.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso (dogfooding obligatorio).

---

## 4️⃣ Decisiones Tecnológicas

1. **Mocks sobre infraestructura real:** Tests unitarios mockean `MCPPool.get_tools()`, `ServiceConnectorTool._run()`, y LLM calls. Justificación: `crewai` es dependencia opcional, MCP servers requieren infraestructura externa, LLM real consume tokens. Tests de integración pueden usar infra real opcionalmente.

2. **`pytest.importorskip("crewai")`** para tests que requieren CrewAI. Justificación: `crewai>=0.100.0` está en `[crew]` optional dependencies. El proyecto debe funcionar sin CrewAI para uso solo con Flows nativos.

3. **E2E tests en `tests/e2e/`** (no `tests/unit/`) para los 6 escenarios. Justificación: Los escenarios validan flujo end-to-end (Architect → Bundle → Import → Execution), no unidades aisladas. Patrón coherente con `test_mvp_certification.py` y `test_parity_suite.py`.

4. **Fixtures en `conftest.py`** para mocks compartidos. Justificación: Los 6 escenarios comparten necesidad de mockear MCPPool, ServiceConnector, y LLM. Centralizar en fixtures evita duplicación.

5. **Correcciones al plan:**
   - ⚠️ El plan dice "Escenario 3: MCP con servidor local" pero el código real requiere `MCPPool.get_tools()` async con conexión Stdio/SSE. Se implementa con mock.
   - ⚠️ El plan dice "Modificar BaseCrew._resolve_tools" pero el código real usa `AgentFactory.resolve_tools()` como fuente única. Ya corregido en Paso 1.
   - ⚠️ El plan no menciona tests para `validate-architect-output`. Se agregan como parte del paso.
   - ⚠️ El plan asume `service_tools` disponible en DB pero no está en migraciones listadas. Se mockea para tests unitarios.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] allowed_tools acepta formatos "mcp:server:tool" y "service_connector" sin validación de schema
✅ [DATA] Cada escenario usa tablas existentes sin requerir migraciones nuevas
✅ [DATA] Escenario 1 genera JSON simple que pasa WorkflowDefinition
✅ [DATA] Escenario 2 genera JSON con service_connector que pasa validación
✅ [DATA] Escenario 3 genera JSON con mcp:server:tool que pasa validación
✅ [DATA] Escenario 4 genera JSON híbrido (MCP + service_connector)
✅ [DATA] Escenario 5 genera JSON multi-agent con depends_on válido (sin ciclos)
✅ [DATA] Escenario 6 genera JSON full stack con approval_threshold
✅ [CODE] AgentFactory.resolve_tools() resuelve correctamente tools regulares, MCP (async), y service_connector
✅ [CODE] BaseCrew.run_async() usa create_agent_async para habilitar MCP tools
✅ [CODE] DynamicWorkflow pasa contexto entre steps via previous_results
✅ [CODE] 6 archivos de test E2E implementados siguiendo patrones existentes
✅ [CODE] Tests unitarios para validate_architect_output existen y pasan
✅ [BACKEND] ArchitectFlow genera JSON válido contra WorkflowDefinition para cada escenario aplicable
✅ [BACKEND] BundleManager.create_bundle() genera ZIP válido con hashing SHA256
✅ [BACKEND] Todos los bundles generados se pueden importar vía POST /api/bundles/import
✅ [FULLSTACK] Escenario 1: Agente simple con 0 tools ejecuta y retorna resultado
✅ [FULLSTACK] Escenario 2: Agente con service_connector ejecuta integración HTTP mockeada
✅ [FULLSTACK] Escenario 3: Agente con MCP tool resuelve conexión via MCPPool mockeado
✅ [FULLSTACK] Escenario 4: Agente híbrido usa MCP + service_connector en mismo allowed_tools
✅ [FULLSTACK] Escenario 5: Multi-agente ejecuta steps secuenciales pasando contexto
✅ [FULLSTACK] Escenario 6: Architect genera bundle → import → ejecución end-to-end
✅ [FULLSTACK] validate_architect output.json para cada escenario no genera errores
✅ [DX] fap test-scenarios CLI ejecuta sin errores y reduce validación manual de ~30min a ~2min
✅ [DX] Typo en validate_architect.py:108 corregido
✅ [DX] Dogfooding: fap test-scenarios usa validate-architect-output internamente
```

**Funcionales:**
- [ ] Escenario 1 (Greeter): Test E2E pasa — agente simple sin tools
- [ ] Escenario 2 (Slack Notifier): Test E2E pasa — service_connector mockeado
- [ ] Escenario 3 (File Manager): Test E2E pasa — MCP tools mockeadas
- [ ] Escenario 4 (Híbrido): Test E2E pasa — MCP + service_connector combinados
- [ ] Escenario 5 (Multi-Agente): Test E2E pasa — steps secuenciales con context passing
- [ ] Escenario 6 (Full Stack): Test E2E pasa — Architect → Bundle → Import → Execution
- [ ] `fap validate-architect-output` tiene tests unitarios con ≥80% coverage

**Técnicos:**
- [ ] Todos los tests existentes siguen pasando (≥248 tests actuales)
- [ ] `ruff check src/ tests/` → 0 errores
- [ ] `pytest tests/unit/` → 0 fallos
- [ ] `pytest tests/e2e/` → 0 fallos (con mocks)
- [ ] Typo en `validate_architect.py:108` corregido

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `fap test-scenarios` CLI command + registro en `main.py` | Media | 3h | Ninguna |
| 1 | Corregir typo en `validate_architect.py:108` | Baja | 0.25h | Ninguna |
| 2 | Agregar fixtures a `conftest.py`: `mock_mcp_pool`, `mock_service_connector`, `sample_agent_config`, `mock_llm_response` | Baja | 1h | Ninguna |
| 3 | Crear `tests/unit/test_validate_architect.py` — tests para validate_architect_output | Media | 2h | Tarea 2 |
| 4 | Crear `tests/e2e/test_scenario_1_greeter.py` — agente simple | Baja | 1h | Tarea 0, 2 |
| 5 | Crear `tests/e2e/test_scenario_2_integration.py` — service_connector | Media | 2h | Tarea 0, 2 |
| 6 | Crear `tests/e2e/test_scenario_3_mcp.py` — MCP tools | Media | 2h | Tarea 0, 2 |
| 7 | Crear `tests/e2e/test_scenario_4_hybrid.py` — MCP + service_connector | Alta | 3h | Tareas 5, 6 |
| 8 | Crear `tests/e2e/test_scenario_5_multi_agent.py` — multi-agente secuencial | Alta | 3h | Tarea 2 |
| 9 | Crear `tests/e2e/test_scenario_6_full_stack.py` — full stack end-to-end | Alta | 4h | Tareas 4-8 |
| 10 | Ejecutar `fap test-scenarios --scenario all` para validar dogfooding | Baja | 1h | Tareas 0-9 |
| 11 | Ejecutar `ruff check src/ tests/` + `pytest tests/` — verificar suite completa | Baja | 0.5h | Tareas 1-10 |
| **TOTAL** | | | **22.75h** | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap test-scenarios` para validar cada escenario subsecuente (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| CrewAI no instalado en entorno de test | Alta | `crewai` es dependencia opcional (`[crew]`) | `pytest.importorskip("crewai")` salta tests si no disponible |
| MCPPool requiere conexión real a servidor MCP | Alta | `MCPPool.get_tools()` conecta via StdioServerParameters | Mockear `MCPPool.get_tools()` en todos los tests con fixture `mock_mcp_pool` |
| LLM real consume tokens en tests | Media | ArchitectFlow ejecuta LLM para generar JSON | Mockear `crewai.Crew.kickoff_async` para retornar JSON predefinido |
| ServiceConnector requiere service_tools en DB | Media | Tabla `service_tools` no verificada en migraciones listadas | Mockear query de `service_tools` en tests unitarios |
| Approval rules limitadas a `>` y `<` | Baja | `_check_approval_rule()` solo parsea 2 operadores | Documentar limitación. Escenarios HITL usan solo estos operadores |
| Tests asíncronos con event loop conflicts | Media | `MCPPool.get_tools()` usa `asyncio.run()` internamente | `pytest-asyncio` con `asyncio_mode = "auto"` (ya configurado en pyproject.toml) |
| Colisión de flow_type en tests | Baja | `_ensure_unique_flow_type()` agrega sufijo aleatorio | Usar `uuid4()` en flow_type de test para garantizar unicidad |
| Flaky tests por race conditions en async | Media | Ejecución concurrente de steps en DynamicWorkflow | Fixtures controladas con `pytest-asyncio`, evitar tests paralelos |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Escenario 1: Agente simple | NL: "Crear agente que salude" | JSON válido con 1 agent, 1 step. Bundle importa. BaseCrew.run() retorna resultado. |
| TP-2 | Escenario 2: Service Connector | NL: "Agente notificador por Slack" | JSON con `["service_connector"]`. Mock HTTP POST retorna 200. Output contiene confirmación. |
| TP-3 | Escenario 3: MCP Tools | NL: "Agente gestor de archivos" | JSON con `["mcp:filesystem:read_file"]`. MCPPool mockeado retorna tool. BaseCrew.run_async() ejecuta. |
| TP-4 | Escenario 4: Híbrido | NL: "Agente busca Google y notifica CRM" | JSON con `["mcp:google:search", "service_connector"]`. Ambas tools resueltas. Output combinado. |
| TP-5 | Escenario 5: Multi-Agente | NL: "Flujo Investigador→Escritor→Corrector" | JSON con 3 agents, 3 steps con depends_on. DynamicWorkflow ejecuta secuencial. Context passed entre steps. |
| TP-6 | Escenario 6: Full Stack | NL: "Flujo complejo con todo" | JSON con MCP + service_connector + multi-agent + approval_threshold. End-to-end: Architect → Bundle → Import → Execution. |
| TP-7 | validate_architect: JSON válido | JSON bien formado con tools válidas | Exit code 0, tabla verde con todos los checks pass |
| TP-8 | validate_architect: MCP no configurado | JSON con `mcp:server:tool` sin server en DB | Warning (no error), tabla amarilla |
| TP-9 | validate_architect: Schema inválido | JSON con campo faltante | Error exit code 1, mensaje descriptivo |
| TP-10 | fap test-scenarios: Todos | `fap test-scenarios --scenario all` | 6/6 escenarios pass, reporte consolidado |

**Comandos para ejecutar tests:**
- Unitarios: `pytest tests/unit/`
- E2E: `pytest tests/e2e/`
- Todos: `pytest tests/`
- Lint: `ruff check src/ tests/`
