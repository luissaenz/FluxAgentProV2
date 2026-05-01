# 🧠 PROCESO DE ANÁLISIS TÉCNICO (ANALISTA) v5.1 — PASO 3 / KILO

## Perfil del Rol
Senior Software Engineer, Arquitecto de Sistemas, Especialista en Diseño de Producto. Análisis basado en código fuente real. Busca activamente herramientas y funcionalidades que faciliten la vida al usuario final y automaticen procesos repetitivos (DX).

## Contexto del Proyecto
Desarrollamos **FluxAgentPro-v2**. Disponible:
- **proyecto-config.json** (raíz) — fuente de verdad de rutas y convenciones
- **Plan general:** DEVS/plan.md
- **Contexto de fase:** DEVS/phase-state.md
- **Código fuente:** src/ (fuente de verdad)
- **Migraciones:** supabase/migrations/ (schema real de DB)

> [!IMPORTANT]
> **ANTES DE EJECUTAR:** Leer proyecto-config.json. Todas las rutas salen de ahí.

---

## Entradas Obligatorias

**AGENTE:** kilo
**PASO:** paso 3 — E2E — Flujos Completos con Mocks

> [!IMPORTANT]
> Análisis cubre automáticamente:
> - data → schema, integridad, RLS
> - code → patrones, calidad, modularidad
> - backend → APIs, middleware, contratos
> - fullstack → coherencia end-to-end + UX + DX

---

## Prohibiciones Absolutas
- NO escribas código de implementación. Entregable = DOCUMENTO DE ANÁLISIS.
- NO preguntes qué hacer. Lee plan, phase-state y paso asignado. Luego EJECUTA.
- NO analices TODO el sistema. Solo el paso específico — pero SÍ TODO el paso (sub-pasos incluidos).
- NO modifiques ningún archivo que no sea el de salida.
- NO repitas info que ya esté en DEVS/phase-state.md. Referenciala.
- NO asumas que función, tabla, clase o patrón existe solo porque el plan lo menciona. VERIFICAR contra código.

---

## Exploración Inicial del Codebase

**Estructura del proyecto:**
- src/ tiene subdirs: api/, crews/, flows/, mcp/, services/, tools/
- src/api/routes/ tiene 15 archivos .py para endpoints
- supabase/migrations/ tiene 25 archivos .sql
- tests/ tiene unit/, integration/, e2e/
- tests/e2e/ tiene 6 archivos .py existentes (no test_production_flows.py)

**Archivos directamente relacionados al paso:**
- DEVS/plan.md: define E3.1-E3.3
- tests/conftest.py: fixtures globales (mock_service_client, global_llm_mock, mock_mcp_pool)
- tests/e2e/test_scenario_*.py: ejemplos de E2E existentes
- src/crews/factory.py: resolve_tools() para MCP
- src/tools/mcp_pool.py: MCPPool.get_tools()
- src/flows/dynamic_flow.py: DynamicWorkflow con approval rules

**Archivos de referencia (patrones existentes):**
- tests/e2e/test_scenario_3_mcp.py: patrón para MCP tools, usa mock_mcp_pool
- tests/integration/test_handover_real.py: patrón para multi-step handover
- tests/integration/test_hitl_pause_resume.py: patrón para approval HITL

**Dependencias:**
- pyproject.toml: pytest, pytest-asyncio, fastapi, supabase, crewai
- dev dependencies: pytest-mock, pytest-cov

**Resultado:**
Input para §0 y análisis. Paso requiere crear tests/e2e/test_production_flows.py con 3 tests mockeados.

---

## Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | tests/e2e/test_production_flows.py existe | ls tests/e2e/ | ❌ | No existe |
| 2 | AgentFactory.resolve_tools() soporta MCP | grep resolve_tools src/crews/factory.py | ✅ | Líneas 28-74 |
| 3 | MCPPool.get_tools() con circuit breaker | grep get_tools src/tools/mcp_pool.py | ✅ | Líneas 50-90 |
| 4 | DynamicWorkflow._check_approval_rule() soporta >= <= == | grep _check_approval_rule src/flows/dynamic_flow.py | ✅ | Líneas 128-185, operadores >= <= == |
| 5 | request_approval() en DynamicWorkflow | grep request_approval src/flows/dynamic_flow.py | ✅ | Líneas 100-120 |
| 6 | resume() en DynamicWorkflow | grep resume src/flows/dynamic_flow.py | ✅ | Líneas 200-219 |
| 7 | Fixtures conftest.py disponibles | grep mock_service_client tests/conftest.py | ✅ | Líneas 112-200 |
| 8 | global_llm_mock fixture | grep global_llm_mock tests/conftest.py | ✅ | Líneas 275-303 |
| 9 | mock_mcp_pool fixture | grep mock_mcp_pool tests/conftest.py | ✅ | Líneas 304-353 |
| 10 | test_scenario_*.py patrones | read tests/e2e/test_scenario_1_greeter.py líneas 70-100 | ✅ | Hardcoded workflow_json, create_bundle, POST /workflows |
| 11 | Pydantic WorkflowDefinition | grep WorkflowDefinition src/flows/workflow_definition.py | ✅ | Líneas 1-60 |
| 12 | BaseFlow con lifecycle | grep BaseFlow src/flows/base_flow.py | ✅ | Líneas 1-100 |

**Discrepancias encontradas:**
- ❌ DISCREPANCIA: DEVS/plan.md menciona bug en >= <= == pero código actual soporta correctamente (líneas 144-149 dynamic_flow.py). Plan desactualizado.

---

## Análisis de Datos (ETAPA 1)

- ✅ Schema: tablas workflow_templates, snapshots, domain_events soportan flujos E2E
- ✅ Integridad referencial: foreign keys org_id en todas tablas tenant
- ✅ RLS policies: tenant_isolation policy en todas tablas críticas
- ✅ Índices necesarios: índices en org_id, flow_type, status
- ✅ Tipos de datos: JSONB para workflow_definitions, timestamps para eventos

WorkflowDefinition incluye approval_rules con condition strings, steps con agent_role.

---

## Análisis de Código (ETAPA 2)

- ✅ Funciones/clases nuevas: test_production_flows.py con 3 clases test (E3.1-E3.3)
- ✅ Patrones: usar fixtures conftest.py, patch para mocks, assert sobre estados
- ✅ Modularidad: tests independientes, no acoplamiento entre escenarios
- ✅ Calidad: mocking completo, no dependencias externas, timeouts controlados
- ✅ Imports: from tests.conftest import ..., from src.api.main import app

Patrón E2E: TestClient(app), fixtures para mocks, hardcoded workflows, POST /workflows, assert response status + data.

---

## Análisis de Backend (ETAPA 3)

- ✅ APIs/endpoints: POST /workflows para ejecutar flujos
- ✅ Middleware: auth via middleware.py, tenant isolation
- ✅ Flujos: DynamicWorkflow._run_crew() con approval rules, handover entre steps
- ✅ Contratos: WorkflowDefinition Pydantic valida input, output incluye task_id
- ✅ Error handling: SecurityError para bundles, MCPConnectionError para MCP fails

E3.1: resolve_tools falla parcialmente para MCP → workflow usa tools disponibles
E3.2: approval rule triggers → estado PENDING → resume() → COMPLETED
E3.3: 3 steps consumen previous_results correctamente

---

## Análisis de Fullstack + DX (ETAPA 4)

- ✅ Flujo completo: Hardcoded workflow → POST API → DB snapshots → Crew execution → Events emitidos
- ✅ Coherencia: Decisiones data/code/backend apoyan E2E mockeados
- ✅ Alineación: Plan realizable con arquitectura existente (fixtures completas)
- ✅ Gaps: Ninguno — todo mockeado, determinista

### Herramienta Propuesta: fap test-step 3
- **Qué automatiza:** Ejecuta 3 tests E2E Paso 3 con report cobertura
- **Tipo:** CLI command
- **Cómo se usa:** fap test-step 3 [--cov]
- **Impacto para el usuario final:** Corre tests sin recordar comandos pytest
- **Prioridad:** Tarea 0 — implementar antes que tests

---

## Criterios de Aceptación

✅ [DATA] WorkflowDefinition soporta approval_rules y multi-step
✅ [CODE] Tests usan patrones existentes de test_scenario_*.py
✅ [BACKEND] POST /workflows maneja approval HITL y MCP degraded
✅ [FULLSTACK] Flujos completan sin real LLM/DB/MCP
✅ [DX] fap test-step 3 ejecuta todos con --cov opcional

---

## Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|---|
| MCP mock no simula fallos parciales | Media | mock_mcp_pool siempre success | Configurar side_effect para 1 success, 1 fail |
| Approval HITL requiere estado PENDING | Alta | DynamicWorkflow debe persistir estado | Verificar snapshots table actualizada |
| Multi-step handover pierde contexto | Alta | previous_results no pasan entre steps | Testear con 3 steps reales |
| Timeout en tests E2E | Baja | Mocking completo debería ser rápido | <5s por test |

- Riesgos técnicos: Estado approval no persiste correctamente
- Riesgos integración: MCP degraded no maneja warning logs
- Riesgos futuro: Tests no cubren edge cases como 0 steps

---

## Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Implementar fap test-step 3 | FULLSTACK/DX | Media | 1h | Ninguna | → verificar: fap test-step 3 corre 3 tests sin errores |
| 1 | Crear tests/e2e/test_production_flows.py con E3.1 | CODE/BACKEND | Alta | 2h | Tarea 0 | → verificar: E3.1 pasa con mock MCP fallando parcialmente |
| 2 | Agregar E3.2 approval HITL | BACKEND/FULLSTACK | Alta | 2h | Tarea 1 | → verificar: Estado PENDING → resume() → COMPLETED |
| 3 | Agregar E3.3 multi-step handover | FULLSTACK | Media | 1h | Tarea 2 | → verificar: 3 steps consumen previous_results |
| 4 | Validar cobertura >80% Paso 3 | FULLSTACK | Baja | 30m | Tareas 1-3 | → verificar: pytest --cov=src tests/e2e/test_production_flows.py |

**Tiempo total estimado:** 6.5 horas

---

## Roadmap (NO implementar ahora)

- Optimizaciones: Parallel tests para reducir tiempo CI
- Mejoras UX: Mejor error messages en approval failures
- Pre-requisitos futuros: Real LLM integration tests

---

## Reglas de Oro

- ✅ Análisis accionable y específico, no genérico
- ✅ TODO verificado contra código, no supuestos
- ✅ Si algo no está definido → señalar ambigüedad + resolución concreta
- ✅ Si el plan contradice el código → el código gana + documentar discrepancia
- ✅ Nivel CTO exigente en rigor y profundidad
- ✅ Coherente con phase-state.md — no perder decisiones ya tomadas
- ✅ TODO el paso, incluyendo sub-pasos
- ✅ Etapas secuenciales — data → code → backend → fullstack+DX, sin saltar
- ✅ ≥ 1 herramienta DX propuesta — siempre, sin excepción
- ✅ Cada tarea con verificación inline — el implementador no debe inferir cómo saber que terminó

---

## Métrica de Calidad

| Métrica | Mínimo |
|:---|:---|
| proyecto-config.json leído antes de explorar | 100% |
| Elementos verificados (§0) | ≥ 12 |
| Discrepancias detectadas | ≥ 1 |
| Secciones completadas | 8 secciones (0-7) |
| Etapas cubiertas | 4 etapas (data, code, backend, fullstack+DX) |
| Criterios de aceptación | ≥ 5, verificables |
| Riesgos identificados | ≥ 3 (técnico, integración, futuro) |
| Tareas en el plan | ≥ 4, atómicas, ordenadas |
| Verificación inline por tarea (§7) | 100% — toda tarea tiene su `→ verificar:` |
| Suposiciones no verificadas | ≤ 2, cada una marcada ⚠️ |
| Propuesta DX / Tooling | ≥ 1 herramienta concreta con descripción de impacto para usuario final |
| Estimación de tiempo | Sí, por tarea y total |

---

**Idioma de respuesta:** Español 🇪🇸</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\DEVS\IN_PROGRESS\analisis-3-kilo.md