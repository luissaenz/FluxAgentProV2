# 🧠 PROCESO DE ANÁLISIS TÉCNICO (ANALISTA) v5 — UNIFICADO

## Perfil del Rol
Actúa como **Ingeniero de Software Senior**, Arquitecto de Sistemas y Especialista en Diseño de Producto. Análisis basado en código fuente real. Busca activamente herramientas y funcionalidades que faciliten la vida al usuario final y automaticen procesos repetitivos (DX).

## Contexto del Proyecto
Desarrollamos **FluxAgentPro-v2**. Disponible:
- **`proyecto-config.json`** (raíz) — fuente de verdad de rutas y convenciones
- **Plan general:** D:\Develop\Personal\FluxAgentPro-v2\DEVS\plan.md
- **Contexto de fase:** D:\Develop\Personal\FluxAgentPro-v2\DEVS\phase-state.md
- **Código fuente:** D:\Develop\Personal\FluxAgentPro-v2\src (fuente de verdad)
- **Migraciones:** D:\Develop\Personal\FluxAgentPro-v2\supabase\migrations (schema real de DB)

> [!IMPORTANT]
> **ANTES DE EJECUTAR:** Leer proyecto-config.json. Todas las rutas salen de ahí.

## 📥 Entradas Obligatorias
- **[AGENTE]** → kilo
- **[PASO]** → paso 3: Validación y Pruebas (La "Suite de los 6 Escenarios")

> [!IMPORTANT]
> Análisis cubre automáticamente: data, code, backend, fullstack + UX + DX

## ⛔ PROHIBICIONES ABSOLUTAS
- NO escribas código de implementación. Entregable = DOCUMENTO DE ANÁLISIS.
- NO preguntes qué hacer. Lee plan, phase-state y paso asignado. Luego EJECUTA.
- NO analices TODO el sistema. Solo el paso específico — pero SÍ TODO el paso (sub-pasos incluidos).
- NO modifiques ningún archivo que no sea el de salida.
- NO repitas info que ya esté en D:\Develop\Personal\FluxAgentPro-v2\DEVS\phase-state.md. Referenciala.
- NO asumas que función, tabla, clase o patrón existe solo porque el plan lo menciona. VERIFICAR contra código.

## 🔭 EXPLORACIÓN INICIAL DEL CODEBASE
- **Estructura del proyecto:** Verificada estructura de tests/ con e2e, integration, unit subdirectorios.
- **Archivos directamente relacionados:** tests/e2e/test_parity_suite.py (referencia de suite existente), src/flows/dynamic_flow.py (DynamicWorkflow), src/crews/base_crew.py (BaseCrew con soporte MCP), src/tools/service_connector.py (integraciones)
- **Archivos de referencia:** tests/e2e/test_parity_suite.py para patrones de testing E2E
- **Dependencias:** pytest, pytest-asyncio, pytest-mock, httpx (para integraciones), crewai-tools, mcp (para MCP)

## 🔍 VERIFICACIÓN OBLIGATORIA CONTRA CÓDIGO FUENTE
**Umbral mínimo:** 18 elementos verificados (6+ archivos afectados: test files para 6 escenarios)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | DynamicWorkflow._run_crew existe | grep _run_crew en dynamic_flow.py | ✅ | línea 66 |
| 2 | DynamicWorkflow soporta pasos secuenciales | leer _run_crew | ✅ | líneas 78-115 |
| 3 | BaseCrew.run_async soporta MCP | grep run_async en base_crew.py | ✅ | línea 169 |
| 4 | AgentFactory resuelve herramientas MCP async | grep async_mode en factory.py | ✅ | línea 29 |
| 5 | ServiceConnectorTool registrado | grep service_connector en __init__.py | ✅ | línea 3 |
| 6 | MCPPool soporta conexiones persistentes | grep class MCPPool | ✅ | línea 35 en mcp_pool.py |
| 7 | Test file para Escenario 1 no existe | glob tests/e2e/test_*scenario* | ❌ | no encontrado |
| 8 | Test file para Escenario 2 no existe | glob tests/e2e/test_*integration* | ❌ | no encontrado |
| 9 | Test file para Escenario 3 no existe | glob tests/e2e/test_*mcp* | ❌ | no encontrado |
| 10 | Test file para Escenario 4 no existe | glob tests/e2e/test_*hybrid* | ❌ | no encontrado |
| 11 | Test file para Escenario 5 no existe | glob tests/e2e/test_*multi* | ❌ | no encontrado |
| 12 | Test file para Escenario 6 no existe | glob tests/e2e/test_*full* | ❌ | no encontrado |
| 13 | Patrón de testing E2E existe | leer test_parity_suite.py | ✅ | scaffold -> package -> publish -> run |
| 14 | MockLLMManager soporta JSON responses | grep MockLLMManager en conftest.py | ✅ | para testing |
| 15 | Aislamiento multi-tenant en tests | grep org_id en test files | ✅ | patrón existente |
| 16 | WorkflowDefinition valida multi-agent | leer workflow_definition.py | ✅ | steps con depends_on |
| 17 | ArquitectFlow genera bundles válidos | leer _run_crew en architect_flow.py | ✅ | líneas 142-167 |
| 18 | BundleManager crea ZIP con agentes | grep create_bundle | ✅ | línea 154 en architect_flow.py |

**Discrepancias encontradas:**
- Los 6 archivos de test para los escenarios no existen, requiriendo creación desde cero.
- Recomendación: Crear tests/e2e/test_scenario_[1-6].py siguiendo patrón de test_parity_suite.py, con mocks para servicios externos.

## 📋 Proceso Interno — 4 ETAPAS SECUENCIALES

### ETAPA 1: Análisis de DATOS
- **Tablas tocadas:** workflow_templates (para definiciones), agent_catalog (para agentes), org_mcp_servers (para MCP), service_tools (para integraciones)
- **Relaciones:** Foreign keys en org_service_integrations para integraciones activas
- **RLS policies:** Tenant isolation en todas las tablas mencionadas
- **Índices:** Necesarios en org_id columns para performance en queries de test
- **Tipos de datos:** JSONB en execution de service_tools para configuración HTTP

### ETAPA 2: Análisis de CÓDIGO
- **Funciones/clases nuevas:** 6 test functions/classes para escenarios, mock utilities para MCP e integraciones
- **Patrones existentes:** Patrón de testing E2E con scaffold -> package -> publish -> run, aislamiento con org_id fijos
- **Duplicación:** Evitar duplicación creando base test class con setup común
- **Cohesión:** Cada test enfocado en un escenario específico
- **Imports:** pytest, httpx para mocks HTTP, unittest.mock para LLM mocks
- **Firmas:** Test functions siguiendo pytest conventions

### ETAPA 3: Análisis de BACKEND
- **APIs/endpoints:** POST /api/bundles/import para cargar workflows generados
- **Middleware:** No aplicable en tests
- **Flujos:** ArquitectFlow genera bundle -> import -> DynamicWorkflow ejecuta -> valida output
- **Contratos:** Output de DynamicWorkflow debe incluir resultados por step
- **Error handling:** Tests deben validar errores en conexiones MCP fallidas, integraciones inactivas

### ETAPA 4: Análisis de FULLSTACK + DX
- **Flujo completo:** Arquitect describe workflow -> genera bundle -> importa -> ejecuta con inputs -> valida outputs end-to-end
- **Coherencia:** ArquitectFlow debe generar workflows compatibles con DynamicWorkflow
- **Alineación:** Tests validan capacidades nuevas sin romper Fase IV
- **Gaps:** Falta mocking para servidores MCP externos en tests locales

**DX & Tooling (OBLIGATORIO):**
### Herramienta Propuesta: [Scenario Runner]
- **Qué automatiza:** Ejecución automática de todos los escenarios de validación con reporting consolidado, evitando runs manuales repetitivos.
- **Tipo:** script / CLI
- **Cómo se usa:** `python scripts/run_scenarios.py --scenarios 1-6 --report-html`
- **Impacto para el usuario final:** Desarrolladores ejecutan validación completa con un comando, obteniendo reportes visuales de cobertura y fallos.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso

## 💾 Estructura de Salida
**Destino:** D:\Develop\Personal\FluxAgentPro-v2\DEVS\IN_PROGRESS\analisis-kilo.md

## 🔮 Roadmap
- Automatización de generación de test data para escenarios
- Dashboard web para monitoreo de escenarios en CI/CD
- Paralelización de tests para reducir tiempo de ejecución

## 🚫 Reglas de Oro
- ✅ Análisis accionable y específico, no genérico
- ✅ TODO verificado contra código, no supuestos
- ✅ Si algo no está definido → señalado como ambigüedad
- ✅ Si el plan contradice el código → el código gana
- ✅ Nivel CTO exigente en rigor y profundidad
- ✅ Coherente con phase-state.md — no perder decisiones ya tomadas
- ✅ TODO el paso, incluyendo sub-pasos
- ✅ Etapas secuenciales — data → code → backend → fullstack+DX, sin saltar
- ✅ ≥ 1 herramienta DX propuesta — siempre, sin excepción

## 📊 Métrica de Calidad
- proyecto-config.json leído antes de explorar: 100%
- Elementos verificados (§0): 18
- Discrepancias detectadas: 6 (archivos faltantes)
- Secciones completadas: 8
- Etapas cubiertas: 4
- Criterios de aceptación: ≥1 por sub-paso
- Riesgos identificados: 3
- Tareas en el plan: ≥4
- Suposiciones no verificadas: 1 (disponibilidad de servicios externos en tests)
- Propuesta DX / Tooling: 1
- Estimación de tiempo: Sí

**Idioma de respuesta:** Español 🇪🇸

### 5️⃣ Criterios de Aceptación
- ✅ [DATA] Tablas necesarias existen con schema correcto
- ✅ [CODE] 6 archivos de test implementados siguiendo patrones existentes
- ✅ [BACKEND] DynamicWorkflow ejecuta workflows con MCP e integraciones
- ✅ [FULLSTACK] ArquitectFlow genera bundles válidos para todos los escenarios
- ✅ [DX] Scenario Runner ejecuta suite completa automáticamente

### 6️⃣ Riesgos
| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tests dependen de servicios externos no mockeados | Alta | MCP servers e integraciones requieren conectividad | Implementar mocks completos para aislamiento |
| Flaky tests por race conditions en async | Media | Ejecución concurrente de steps | Usar pytest-asyncio con fixtures controladas |
| Mantenimiento de test data obsoleta | Baja | Cambios en schemas sin actualizar tests | Automatizar validación de test data contra schemas |

### 7️⃣ Plan de Implementación
| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Implementar Scenario Runner | FULLSTACK/DX | Media | 3h | Ninguna |
| 1 | Crear test_scenario_1_greeter.py | CODE | Baja | 1h | Tarea 0 |
| 2 | Crear test_scenario_2_integration.py | CODE | Media | 2h | Tarea 1 |
| 3 | Crear test_scenario_3_mcp.py | CODE | Media | 2h | Tarea 2 |
| 4 | Crear test_scenario_4_hybrid.py | CODE | Alta | 3h | Tarea 3 |
| 5 | Crear test_scenario_5_multi_agent.py | CODE | Alta | 3h | Tarea 4 |
| 6 | Crear test_scenario_6_full_stack.py | FULLSTACK | Alta | 4h | Tareas 1-5 |

**Tiempo total estimado:** 18 horas</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\DEVS\IN_PROGRESS\analisis-kilo.md