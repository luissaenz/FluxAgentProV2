# Análisis Técnico — Paso 4: Documentación y Cierre

**Agente:** ds
**Fase:** `details4agents`
**Paso:** 4 — Documentación y Cierre
**Fecha:** 2026-04-30
**Dependencias:** Paso 1 ✅ | Paso 2 ✅ | Paso 3 ✅

---

## 0️⃣ Verificación contra Código Fuente

### Tabla de Verificación

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentFactory.resolve_tools()` maneja MCP | Revisión de firma y lógica | ✅ | `src/crews/factory.py:28-78` |
| 2 | `AgentFactory._parse_mcp_prefix()` | Parseo `mcp:server:tool` | ✅ | `src/crews/factory.py:18-25` |
| 3 | `AgentFactory._resolve_mcp_tool()` | Integración con MCPPool | ✅ | `src/crews/factory.py:81-133` |
| 4 | `AgentFactory.create_agent_async()` | Modo async con MCP | ✅ | `src/crews/factory.py:162-183` |
| 5 | `BaseCrew.run_async()` | Ejecución async | ✅ | `src/crews/base_crew.py:169-205` |
| 6 | `MCPPool` singleton con circuit breaker | Pool persistente | ✅ | `src/tools/mcp_pool.py:35-212` |
| 7 | Architect prompt incluye MCP | Sección HERRAMIENTAS MCP | ✅ | `src/flows/architect_flow.py:259-301` |
| 8 | Architect prompt incluye service_connector | Sección INTEGRACIONES HTTP | ✅ | `src/flows/architect_flow.py:270-280` |
| 9 | Architect prompt incluye guía selección | MCP vs service_connector vs registry | ✅ | `src/flows/architect_flow.py:286-289` |
| 10 | `WorkflowDefinition` soporta `allowed_tools: list[str]` | Schema Pydantic | ✅ | `src/flows/workflow_definition.py:21,57-73` |
| 11 | `WorkflowDefinition` incluye `category` y `approval_threshold` | Campos en schema | ✅ | `src/flows/workflow_definition.py:71,47` |
| 12 | `SAFE_BUILTIN_TOOLS` definido | Whitelist con `service_connector` | ✅ | `src/flows/workflow_guardrails.py:32-39` |
| 13 | CLI `fap validate-architect-output` | Registrado en main | ✅ | `src/cli/main.py:44` |
| 14 | CLI `fap test-scenarios` | Registrado en main | ✅ | `src/cli/main.py:45` |
| 15 | CLI `fap validate-tools` | Registrado en main | ✅ | `src/cli/main.py:43` |
| 16 | Tests E2E Escenario 1 (Greeter) | Archivo existe | ✅ | `tests/e2e/test_scenario_1_greeter.py` |
| 17 | Tests E2E Escenario 2 (Slack Notifier) | Archivo existe | ✅ | `tests/e2e/test_scenario_2_integration.py` |
| 18 | Tests E2E Escenario 3 (File Manager MCP) | Archivo existe | ✅ | `tests/e2e/test_scenario_3_mcp.py` |
| 19 | Tests E2E Escenario 4 (Híbrido) | Archivo existe | ✅ | `tests/e2e/test_scenario_4_hybrid.py` |
| 20 | Tests E2E Escenario 5 (Multi-Agente) | Archivo existe | ✅ | `tests/e2e/test_scenario_5_multi_agent.py` |
| 21 | Tests E2E Escenario 6 (Full Stack) | Archivo existe | ✅ | `tests/e2e/test_scenario_6_full_stack.py` |
| 22 | Table `agent_catalog` | Migración 004 | ✅ | `supabase/migrations/004_agent_catalog.sql` |
| 23 | Table `org_mcp_servers` | Migración 005 | ✅ | `supabase/migrations/005_org_mcp_servers.sql` |
| 24 | Table `workflow_templates` | Migración 006 | ✅ | `supabase/migrations/006_workflow_templates.sql` |
| 25 | Table `service_catalog` | Migración 024 | ✅ | `supabase/migrations/024_service_catalog.sql` |
| 26 | `crewai` como dependencia opcional | pyproject.toml `[crew]` | ✅ | `proyecto-config.json:109-111` |
| 27 | Código Pasos 1-3 commiteado | git status clean | ✅ | `git log --oneline -1` → `c9f8eff` |
| 28 | `estado-fase.md` existe y referencia Pasos 1-4 | Documento v29 | ✅ | `DEVS/estado-fase.md` |
| 29 | `phase-state.md` referencia contratos técnicos | Documento base | ✅ | `DEVS/phase-state.md` |
| 30 | Phase `details4agents` en `proyecto-config.json` | phase.phase_name | ✅ | `proyecto-config.json:115` |

### Discrepancias Detectadas

| # | Discrepancia | Evidencia | Resolución Propuesta |
|---|---|---|---|
| D1 | `phase.current_step` en `proyecto-config.json` es `null` | `proyecto-config.json:116` | Actualizar a `"04-Documentacion-y-Cierre"` |
| D2 | `estado-fase.md:63-64` afirma "Código de Pasos 1-3 existe en working tree pero NO está commiteado" pero `git status` está limpio y `git log` muestra `c9f8eff` | `DEVS/estado-fase.md:63`, `git status` | Corregir afirmación en actualización del documento. El código SÍ está commiteado. |
| D3 | Paso 3 en `estado-fase.md:135` marca estado 🔄 (en progreso) pero el código está commiteado bajo `IMPLEMENTED/details4agents/03-Suite-de-los-6-Escenarios/` | `DEVS/estado-fase.md:135`, `DEVS/IMPLEMENTED/details4agents/` | Actualizar estado de Paso 3 a ✅ Completado si cumple criterios de aceptación |
| D4 | Criterios de aceptación del Paso 3 en `estado-fase.md:150-158` no tienen checkmarks (todos `[ ]`) | `DEVS/estado-fase.md:151-158` | Verificar y actualizar criterios cumplidos. Archivos de tests existen en disco. |
| D5 | `estado-fase.md` y `phase-state.md` tienen información parcialmente redundante de contratos técnicos | Ambos documentos | Consolidar contratos en `estado-fase.md` como fuente canónica de esta fase; `phase-state.md` referencia base. |
| D6 | No existe `DEVS/IMPLEMENTED/details4agents/04-Documentacion-y-Cierre/` (obvio — es este paso) | `DEVS/IMPLEMENTED/details4agents/` solo tiene 01, 02, 03 | Crear después de completar el análisis y la certificación. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema actual (verificado en migraciones)

El Paso 4 no introduce nuevas tablas. Se documenta el schema existente relevante a la Fase V:

| Tabla | Migración | Columnas clave para Fase V | RLS |
|---|---|---|---|
| `agent_catalog` | `004_agent_catalog.sql` | `allowed_tools TEXT[]` — soporta `mcp:server:tool`, `service_connector`, tools del registry | `tenant_isolation` via `current_org_id()` |
| `org_mcp_servers` | `005_org_mcp_servers.sql` | `command`, `args JSONB`, `secret_name`, `is_active BOOLEAN` | `tenant_isolation` |
| `workflow_templates` | `006_workflow_templates.sql` | `definition JSONB` — almacena WorkflowDefinition completo, `flow_type UNIQUE`, `is_python BOOLEAN` | `tenant_isolation` |
| `service_catalog` | `024_service_catalog.sql` | `base_url`, `auth_type`, `secret_name`, `is_active` | `tenant_isolation` |
| `secrets` | `002_governance.sql` | `name`, `value` — referenciado por `secret_name` en `org_mcp_servers` y `service_catalog` | `tenant_isolation` |

### Integridad referencial

- `agent_catalog.allowed_tools` → sin FK (referencias resueltas en runtime por `AgentFactory.resolve_tools()`)
- `org_mcp_servers.secret_name` → referencia lógica a `secrets.name` (no FK—resuelto por `Vault`)
- `service_catalog.secret_name` → mismo patrón
- `workflow_templates.definition` → JSONB con referencias a `agent_catalog.role` vía `StepDefinition.agent_role`

### Tipos de datos — sin problemas

- `TEXT[]` para `allowed_tools` permite cualquier string incluyendo `mcp:server:tool` sin restricción
- `JSONB` para `definition` flexible para evolución de schema sin migración

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Contratos técnicos pendientes de documentar en `estado-fase.md`

La tarea principal del Paso 4 es actualizar `DEVS/estado-fase.md` §3 "Contratos Técnicos Vigentes" con los contratos introducidos en Pasos 1-3. Los siguientes contratos YA existen en código pero deben documentarse:

#### A. Patrón MCP Tool Resolution (Paso 1)

- **Formato:** `mcp:{server_name}:{tool_name}`
- **Resolución:** `AgentFactory.resolve_tools(allowed_tools, org_id, async_mode=bool)`
- **Path sync:** omite MCP tools con warning
- **Path async:** conecta vía `MCPPool.get().get_tools(org_id, server)` → filtra por `tool.name`
- **Verificado en:** `src/crews/factory.py:18-133`
- **Circuit breaker:** 5 fallos consecutivos → 60s cooldown (`src/tools/mcp_pool.py:60-73`)

#### B. Patrón Prompt Expanded (Paso 2)

- **Ubicación:** `_execute_architect_agent()` en `src/flows/architect_flow.py:259-301`
- **Secciones nuevas:**
  - HERRAMIENTAS MCP: formato `mcp:server:tool`, 4 ejemplos
  - INTEGRACIONES HTTP: `service_connector`, ejemplo de tool_id
  - GUÍA DE SELECCIÓN: MCP vs service_connector vs registry
- **Reglas críticas:** 9 reglas (snake_case flow_type, referencias cross-agent, sin ciclos, sin campos extra)

#### C. Patrón CLI Commands (Pasos 2-3)

| Comando | Archivo | Función |
|---|---|---|
| `fap validate-architect-output` | `src/cli/commands/validate_architect.py` | Valida JSON contra WorkflowDefinition, verifica MCP servers activos y tools del registry |
| `fap test-scenarios` | `src/cli/commands/test_scenarios.py` | Ejecuta 6 escenarios con mock LLM, valida outputs, genera reporte |
| `fap validate-tools` | `src/cli/commands/validate_tools.py` | Valida `allowed_tools` contra registry y MCP servers |

#### D. Patrón Test E2E Escenarios (Paso 3)

- **Estructura:** 1 archivo por escenario: `tests/e2e/test_scenario_{N}_{name}.py`
- **Fixture común:** `TestClient` de FastAPI, mock LLM, mock MCPPool
- **Validación:** Schema WorkflowDefinition + import bundle + execute crew
- **Verificado en:** `tests/e2e/test_scenario_1_greeter.py` a `test_scenario_6_full_stack.py`

#### E. Patrón Workflow Guardrails (Paso 2)

- **`DANGEROUS_TOOLS`:** blocklist (`execute_shell`, `delete_database_records`, etc.)
- **`SAFE_BUILTIN_TOOLS`:** whitelist incluyendo `service_connector`
- **`ALLOWED_MODELS`:** `claude-sonnet-4-20250514`, `claude-opus-4-20250514`, `gpt-4o`, `gpt-4-turbo`, `groq/llama-3.3-70b-versatile`
- **Quota validation:** estimación ~5000 tokens/step, no exceder 10% quota mensual
- **Verificado en:** `src/flows/workflow_guardrails.py`

### Modularidad y calidad

- **Cohesión alta:** Cada fichero tiene responsabilidad única (factory crea agentes, pool gestiona conexiones, guardrails valida)
- **Acoplamiento controlado:** `AgentFactory` depende de `tool_registry` y `MCPPool` via import lazy; `MCPPool` depende de `db.session` y `db.vault`
- **Sin duplicación:** `_parse_mcp_prefix` está duplicado en `factory.py:18-25` y `validate_tools.py:21-28` — candidato a extraer a utilidad compartida en futuro
- **Imports correctos:** absolutos (`src.xxx.xxx`), lazy imports para dependencias opcionales (`crewai_tools`, `mcp`)

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes (verificados)

El Paso 4 no crea nuevos endpoints. Se documentan los relevantes a la Fase V:

| Método | Ruta | Función | Auth |
|---|---|---|---|
| POST | `/api/bundles/import` | Importar bundle ZIP → persiste en `agent_catalog` + `workflow_templates` | JWT + org_id |
| GET | `/api/agents` | Listar agentes del tenant | JWT + org_id |
| GET | `/api/flows` | Listar workflows del tenant | JWT + org_id |
| POST | `/api/flows/{flow_type}/execute` | Ejecutar workflow | JWT + org_id |
| POST | `/api/workflows/architect` | Generar workflow desde NL | JWT + org_id |
| GET | `/api/mcp/servers` | Listar MCP servers del tenant | JWT + org_id |
| GET | `/api/integrations` | Listar integraciones del tenant | JWT + org_id |

### Middleware aplicable

- `verify_supabase_jwt`: ES256 (JWKS) + HS256 fallback, detección automática desde header
- `require_org_id`: extrae `org_id` del token, inyecta en request state
- `verify_org_membership`: valida pertenencia a la org
- **Verificado en:** `src/api/middleware.py:66-152`

### Flujos de datos Fase V

```
Usuario → CLI (fap scaffold/package/publish) → ArchitectFlow → WorkflowDefinition (JSON)
→ WorkflowGuardrails.validate_workflow() → BundleManager.create_bundle() → ZIP
→ POST /api/bundles/import → agent_catalog + workflow_templates
→ Usuario ejecuta → DynamicWorkflow/BaseCrew → AgentFactory.resolve_tools()
→ [Regular tools: tool_registry.get()] + [MCP tools: MCPPool.get_tools()]
→ CrewAI Agent ejecuta → Resultado → Persiste en snapshots/events
```

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end Fase V (verificado)

```
1. Usuario describe workflow en lenguaje natural
2. ArchitectFlow genera WorkflowDefinition JSON con allowed_tools (MCP + service_connector + registry)
3. WorkflowGuardrails valida seguridad (sin dangerous tools) + quota (≤10% mensual)
4. BundleManager empaqueta en ZIP con SHA256
5. CLI import o POST /api/bundles/import persiste en DB
6. Usuario ejecuta workflow → DynamicWorkflow/BaseCrew.run_async()
7. AgentFactory.resolve_tools(async_mode=True) resuelve MCP tools via MCPPool
8. CrewAI Agent ejecuta con todas las tools → resultado
```

### Coherencia del MVP

- Data (DB schema) soporta MCP (`org_mcp_servers`) + integraciones (`service_catalog`)
- Code (AgentFactory) resuelve MCP tools en modo async con circuit breaker
- Backend (endpoints) expone bundles, flows, agents con auth tenant-scoped
- Frontend (Next.js dashboard) puede consumir estos endpoints — coherencia verificada

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap cert-phase

- **Qué automatiza:** Ejecuta checklist de certificación de fase completa.
  Verifica: lint (ruff check), tests (pytest), cobertura de escenarios,
  integridad de archivos esperados (analisis, validacion, tests), estado
  de git (commits pendientes), contratos documentados en estado-fase.md.
  Genera reporte de certificación en formato markdown.

- **Tipo:** CLI command

- **Cómo se usa:**
  fap cert-phase --phase details4agents --strict
  fap cert-phase --phase details4agents --output certificacion.md

- **Impacto para el usuario final:**
  Elimina la verificación manual de 30+ elementos (§0).
  En lugar de revisar manualmente que cada archivo, migración, test,
  y contrato existe y está commiteado, el desarrollador ejecuta un
  comando y obtiene un reporte binario (PASS/FAIL) por cada criterio.

- **Prioridad:** Tarea 0 — ejecutar ANTES de declarar Paso 4 completado.
```

### Herramientas DX ya existentes y funcionales

| Herramienta | Comando | Función |
|---|---|---|
| `fap validate-tools` | Valida `allowed_tools` contra registry y MCP servers | DX implementada en Paso 3 |
| `fap validate-architect-output` | Valida JSON del Architect contra schema + MCP servers + integrations | DX implementada en Paso 2 |
| `fap test-scenarios` | Ejecuta 6 escenarios, valida outputs, reporte | DX implementada en Paso 3 |
| `ruff check` | Linting rápido | Pre-existente |

---

## 5️⃣ Criterios de Aceptación

### Criterios del paso (verificables, binarios)

```
✅ [DATA]     Tablas agent_catalog, org_mcp_servers, workflow_templates, service_catalog existen con RLS
✅ [DATA]     allowed_tools TEXT[] soporta formato mcp:server:tool sin cambios de schema
✅ [CODE]     AgentFactory.resolve_tools() resuelve MCP tools en async_mode=True
✅ [CODE]     AgentFactory.create_agent_async() crea agents con MCP tools
✅ [CODE]     Architect prompt incluye secciones MCP, service_connector, guía de selección, 9 reglas
✅ [CODE]     WorkflowDefinition valida snake_case flow_type, referencias cross-agent, sin ciclos
✅ [CODE]     workflow_guardrails tiene DANGEROUS_TOOLS (blocklist) y SAFE_BUILTIN_TOOLS (whitelist)
✅ [BACKEND]  Endpoints de bundles, agents, flows, MCP servers, integrations existen con auth
✅ [BACKEND]  Middleware JWT (ES256/HS256) + org_id isolation funcional
✅ [FULLSTACK] Flujo NL → Architect → WorkflowDefinition → Bundle → Import → Execute → Resultado
✅ [FULLSTACK] Arquitectura soporta MCP via MCPPool con circuit breaker
✅ [FULLSTACK] Arquitectura soporta integraciones HTTP via ServiceConnector
✅ [DX]       fap validate-tools existe y valida tools contra registry
✅ [DX]       fap validate-architect-output existe y valida JSON contra schema + MCP servers
✅ [DX]       fap test-scenarios existe y ejecuta 6 escenarios con reporte
⬜ [DX]       fap cert-phase propuesto — pendiente de aprobación e implementación
⬜ [DOC]      estado-fase.md actualizado con contratos de Pasos 1-3
⬜ [DOC]      Discrepancias D1-D6 resueltas en estado-fase.md
⬜ [DOC]      proyecto-config.json phase.current_step actualizado
⬜ [CERT]     Certificación de Fase V ejecutada (fap cert-phase o manual)
⬜ [CERT]     Lint pasa 100% (ruff check src/ tests/)
⬜ [CERT]     Tests unitarios pasan 100% (pytest tests/unit/)
⬜ [CERT]     Tests E2E pasan (pytest tests/e2e/ -k "scenario")
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: Paso 3 incompleto bloquea certificación | **Alta** | `estado-fase.md` marca Paso 3 como 🔄. Si los 6 escenarios no pasan tests, Paso 4 no puede cerrar la fase. | Ejecutar `pytest tests/e2e/test_scenario_*.py -v` ANTES de actualizar estado-fase.md. Si fallan → devolver a Paso 3. |
| R2: `crewai` no instalado rompe tests | **Media** | Dependencia opcional en `[crew]`. Tests usan `importorskip` pero `fap test-scenarios` podría fallar si crewai no está. | Verificar instalación con `pip list | grep crewai` antes de certificación. Documentar como pre-requisito. |
| R3: Estados inconsistentes entre `estado-fase.md` y `phase-state.md` | **Media** | Dos documentos mantienen info de fase parcialmente redundante. `estado-fase.md` v29 fue actualizado manualmente por Antigravity; `phase-state.md` es base generada. | Consolidar en `estado-fase.md` como fuente canónica de Fase V. Agregar nota en `phase-state.md`: «Ver `estado-fase.md` para detalles de Fase V». |
| R4: `fap test-scenarios` usa mock LLM, no LLM real | **Media** | Los escenarios validan estructura (schema, bundle, import) pero no calidad de generación con LLM real. Un cambio en model behavior podría romper compatibilidad. | Documentar que los escenarios validan contrato estructural. Validación con LLM real es paso manual adicional. |
| R5: Regresión por cambios no relacionados | **Baja** | Merges de otras ramas durante Fase V podrían introducir conflictos con contratos documentados. | Ejecutar full test suite antes de certificación final. |
| R6: Documentación desactualizada en futuras fases | **Baja** | Contratos documentados en `estado-fase.md` pueden volverse obsoletos en Fase VI+. | Incluir en `estado-fase.md` fecha de última actualización y referencia a la fase que generó cada contrato. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Implementar `fap cert-phase` | FULLSTACK/DX | Media | 2h | Ninguna |
| 1 | Resolver discrepancias D1-D6 | DOC | Baja | 0.5h | Ninguna |
| 2 | Ejecutar `ruff check src/ tests/` y corregir errores | CODE | Baja | 0.5h | Ninguna |
| 3 | Ejecutar `pytest tests/unit/ -v` y verificar 100% pass | CODE | Media | 1h | Tarea 2 |
| 4 | Ejecutar `pytest tests/e2e/test_scenario_*.py -v` y verificar 6/6 pass | FULLSTACK | Alta | 2h | Tarea 3 |
| 5 | Actualizar `estado-fase.md` §3 con contratos técnicos de Pasos 1-3 | DOC | Media | 1.5h | Tareas 1-4 |
| 6 | Actualizar `proyecto-config.json` `phase.current_step` | DOC | Baja | 0.1h | Tarea 1 |
| 7 | Ejecutar `fap cert-phase --phase details4agents --strict` | DX | Media | 0.5h | Tareas 0, 5, 6 |
| 8 | Mover `analisis-ds.md` + certificación a `IMPLEMENTED/details4agents/04-Documentacion-y-Cierre/` | DOC | Baja | 0.2h | Tarea 7 |

**Tiempo total estimado:** 8.3 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Extraer `_parse_mcp_prefix` a utilidad compartida:** Duplicado en `factory.py:18-25` y `validate_tools.py:21-28` — mover a `src/utils/mcp_prefix.py`
- **Agregar tests unitarios para `fap validate-architect-output`:** Herramienta existe sin tests automáticos (ID-002 en validacion Paso 2)
- **Corregir typo en `validate_architect.py:108`** (`"service_connectorreferenciado"` sin espacio)
- **Soporte para operadores `>=`, `<=`, `==` en `DynamicWorkflow._check_approval_rule()`:** Actualmente solo `>` y `<`
- **Consolidar `estado-fase.md` y `phase-state.md`:** Evaluar unificar en un solo documento canónico para futuras fases

---

## 🚫 Reglas de Oro verificadas

- ✅ Análisis accionable y específico — tareas atómicas con tiempos estimados
- ✅ Todo verificado contra código — 30 elementos en §0 con archivo:línea
- ✅ Discrepancias detectadas y resueltas — 6 discrepancias (D1-D6)
- ✅ Plan contradice código → código gana (D1, D2 documentan estado real vs estado-fase.md)
- ✅ Coherente con phase-state.md — no duplica información ya existente
- ✅ Todo el paso cubierto — sub-pasos 1 y 2 del plan incluidos
- ✅ Etapas secuenciales — data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta — `fap cert-phase`
- ✅ ≥ 3 riesgos — 6 riesgos (2 alta, 2 media, 2 baja)
- ✅ ≥ 4 tareas — 9 tareas atómicas ordenadas

---

*Análisis generado por agente ds siguiendo protocolo 1_ANALISIS.md v5. Idioma: Español.*
