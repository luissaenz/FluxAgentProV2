# Estado de Fase: Generación Avanzada de Agentes (FAP-Context) — v30

> 📅 **Fecha:** 2026-04-30
> 📝 **Estado:** ✅ CERRADA (Fase V - details4agents) — 4/4 pasos completados
> 📦 **Último Archivado:** `DEVS/IMPLEMENTED/details4agents/04-Documentacion-y-Cierre/`

---

## 1. Resumen de Fase

El objetivo de la **Fase V: details4agents** es habilitar la generación de agentes con integraciones (Tipo C), soporte MCP (Stdio/SSE) y workflows multi-agente dinámicos. El flujo Architect ahora reconoce y puede generar workflows que incluyan herramientas MCP (formato `mcp:server:tool`) e integraciones HTTP (`service_connector`).

**Estado Actual:** ✅ **TODOS LOS PASOS COMPLETADOS Y ARCHIVADOS.** Infraestructura de herramientas (MCP bridging en `AgentFactory`), prompt del Architect (convenciones MCP+service_connector), Suite de los 6 Escenarios, y herramienta DX `fap phase-close` implementados y commiteados.

---

## 2. Estado Actual del Proyecto

### ✅ Implementado y Funcional (Verificado en Código)

**Infraestructura de Fase IV (heredado):**
- **Suite de Validación E2E:** `tests/e2e/test_parity_suite.py` cubriendo ciclo `scaffold` -> `package` -> `publish` -> `run`.
- **Auto-Hashing en `BundleManager`:** Cálculo SHA256 durante `create_bundle`.
- **Dogfooding ArchitectFlow:** El Architect genera bundles válidos siendo él mismo un System Bundle.
- **Soporte de Flujos Python (.py):** `BundleManager` y `FlowRegistry` con `RestrictedPython`.
- **CLI Utilities:** `fap scaffold`, `fap run agent/flow/skill`, `fap dev` (watcher).

**Paso 1 — Infraestructura de Herramientas (✅ Commiteado):**
- **`AgentFactory.resolve_tools()` con MCP:** `src/crews/factory.py:28-78` — detecta prefijo `mcp:`, llama `_resolve_mcp_tool` solo en `async_mode`.
- **`AgentFactory._resolve_mcp_tool()`:** `src/crews/factory.py:81-133` — integración con `MCPPool`, circuit breaker, lazy import de crewai-tools.
- **`AgentFactory.create_agent_async()`:** `src/crews/factory.py:162-183` — modo async con soporte MCP completo.
- **`BaseCrew.run_async()`:** `src/crews/base_crew.py:169-205` — usa `create_agent_async` para ejecución no bloqueante.

**Paso 2 — Upgrade del Cerebro (✅ Commiteado):**
- **Prompt Expandido del Architect:** `src/flows/architect_flow.py:259-301` — incluye:
  - Sección HERRAMIENTAS MCP con formato `mcp:server:tool` y 4 ejemplos.
  - Sección INTEGRACIONES HTTP con `service_connector` y ejemplo de uso.
  - Guía de selección MCP vs service_connector.
  - Reglas críticas actualizadas (9 reglas).
- **Schema `WorkflowDefinition`:** `src/flows/workflow_definition.py:57-123` — soporta `allowed_tools: list[str]`, `category`, `approval_threshold`, validación de snake_case, referencias cross-agent, detección de ciclos.
- **`SAFE_BUILTIN_TOOLS`:** `src/flows/workflow_guardrails.py:32-39` — whitelist incluyendo `service_connector`.
- **CLI `fap validate-architect-output`:** `src/cli/commands/validate_architect.py:1-330` — valida contra schema estructural, MCP servers activos, integraciones activas, tools del registry.
- **CLI `fap test-scenarios`:** `src/cli/commands/test_scenarios.py:1-588` — ejecuta 6 escenarios, valida outputs, genera reporte.

**Paso 3 — Suite de los 6 Escenarios (✅ Commiteado):**
- **Análisis de Paso 3:** Archivado en `DEVS/IMPLEMENTED/details4agents/03-Suite-de-los-6-Escenarios/` — 4 agentes analizaron (kilo, mm, qwen, atg) + análisis final + validación.
- **Tests E2E de Escenarios (Verificados en código):**
  - `tests/e2e/test_scenario_1_greeter.py` — Agente Simple "Greeter".
  - `tests/e2e/test_scenario_2_integration.py` — Agente "Slack Notifier" con `service_connector`.
  - `tests/e2e/test_scenario_3_mcp.py` — Agente "File Manager" con servidor MCP local.
  - `tests/e2e/test_scenario_4_hybrid.py` — Agente Híbrido (MCP + Integración).
  - `tests/e2e/test_scenario_5_multi_agent.py` — Flujo Investigador → Escritor → Corrector.
  - `tests/e2e/test_scenario_6_full_stack.py` — Flujo Full Stack con todas las capacidades.
- **CLI `fap validate-tools`:** `src/cli/commands/validate_tools.py:97` — verifica disponibilidad de tools en registry.
- **Test E2E CLI Scenarios:** `tests/e2e/test_cli_test_scenarios.py` — validación completa de CLI.
- **Test Unitario Validate Architect:** `tests/unit/test_validate_architect.py` — tests para validador.
- **Test Unitario Factory:** `tests/unit/test_factory.py` — tests para AgentFactory.

**Paso 4 — Documentación y Cierre (✅ Commiteado):**
- **CLI `fap phase-close`:** `src/cli/commands/phase_close.py:1-462` — registrado en `src/cli/main.py:47`. Cierre de fase completo: ejecuta lint + tests + certificación, resuelve discrepancias automáticamente, actualiza `estado-fase.md` y `proyecto-config.json`, genera reporte PASS/FAIL.
- **Certificación Fase V:** Commit `5ca8dfc` — `fap phase-close --certify` resolvió D1-D6, cerró Fase V.
- **Archivado de documentación:** Commit `30fc6ef` — archivos de análisis archivados en `IMPLEMENTED/details4agents/04-Documentacion-y-Cierre/`.
- **`phase-state.md`:** Documento de referencia técnica generado por CONTEXTO. `estado-fase.md` es la fuente canónica (confirmado en `phase-state.md:5`).

### ⚠️ Deuda Técnica Documentada

- **ID-001:** `SAFE_BUILTIN_TOOLS` definido pero no se usa activamente en la lógica de `validate_workflow()` — es referencial.
- **ID-002:** La herramienta `fap validate-architect-output` no tiene tests unitarios propios (sugerido para futuro).
- **ID-003:** Typo en mensaje de error: `"service_connectorreferenciado"` sin espacio — no bloquea funcionalidad.
- **ID-005 (D6):** `_check_approval_rule` en `src/flows/dynamic_flow.py:128-159` solo soporta operadores `>` y `<`, no `>=` ni `<=`. **Limitación conocida.** Los 6 escenarios usan solo `>` y `<`. No bloquea funcionalidad actual.

### 📝 Discrepancias Plan vs Código — Resueltas

- ✅ **D1:** `phase.current_step` actualizado a `"04-Documentacion-y-Cierre"` en `proyecto-config.json:116`.
- ✅ **D2:** Código Pasos 1-3 commiteado — verificado con `git log` (commits `c9f8eff`, `4f61392`).
- ✅ **D3:** Paso 3 correctamente marcado como ✅ Completado.
- ✅ **D4:** Criterios de aceptación Paso 3 verificados y marcados `[x]`.
- ✅ **D5:** `phase-state.md` declarado como documento de referencia. `estado-fase.md` = fuente canónica.
- ✅ **D6:** `_check_approval_rule` limitación documentada como ID-005.

---

## 3. Contratos Técnicos Vigentes

### 🌐 Endpoints y Firmas de CLI (Verificados en Código)
| Comando | Firma / Argumentos | Estado |
| :--- | :--- | :--- |
| `fap run skill` | `file_path, --input, --file, --danger-no-sandbox` | ✅ Funcional |
| `fap run agent` | `role, --bundle, --input, --timeout` | ✅ Funcional |
| `fap run flow` | `flow_type, --bundle, --input, --timeout` | ✅ Funcional |
| `fap scaffold` | `name, --dir` | ✅ Funcional |
| `fap package` | `bundle_path, --output` | ✅ Funcional |
| `fap validate-architect-output` | `json_path, --org-id <uuid>` | ✅ Nuevo (Paso 2) |
| `fap test-scenarios` | `--org-id <uuid>` | ✅ Nuevo (Paso 3) |
| `fap validate-tools` | `--org-id <uuid>` | ✅ Nuevo (Paso 3) |
| `fap phase-close` | `--phase, --certify, --org-id, --dry-run, --output` | ✅ Nuevo (Paso 4) |

### 📊 Esquemas de Base de Datos
- **`workflow_templates`**: `definition` JSONB, `flow_type` UNIQUE, RLS via `tenant_isolation`.
- **`agent_catalog`**: `allowed_tools` TEXT[], soporta cualquier string incluyendo `mcp:server:tool`.
- **`org_mcp_servers`**: `command`, `args` JSONB, `secret_name`, `is_active` boolean.
- **`service_catalog`**: Catálogo global de integraciones HTTP.
- **`service_tools`**: Definiciones de herramientas por servicio, vinculadas a `service_catalog`.
- **`org_service_integrations`**: Integraciones activas por org (`status: active`).

### 🛠️ Patrones de Código en Uso
- **Prompt Engineering Pattern:** El `Task.description` en `_execute_architect_agent` usa f-string con variables (`{allowed_models}`) interpoladas.
- **Blocklist de Herramientas Peligrosas:** `DANGEROUS_TOOLS` en `workflow_guardrails.py` — blocklist para `validate_workflow()`.
- **Whitelist de Tools Seguras:** `SAFE_BUILTIN_TOOLS` — referencia para tools que no requieren validación activa.
- **CLI Command Pattern:** Estructura de `validate.py` replicada en `validate_architect.py` y `phase_close.py` — mismo patrón de imports relativos.
- **Service Connector Pattern:** `ServiceConnectorTool` ejecuta HTTP con `httpx`, resuelve secretos del Vault, audita en `domain_events`.
- **MCP Pool Pattern:** `MCPPool.get_tools()` usa circuit breaker y retry con `tenacity`.

### 📄 Documentos de Referencia
- **`DEVS/phase-state.md`**: Documento técnico detallado generado por protocolo CONTEXTO. Contiene stack, componentes, migraciones, endpoints, y tablas de estado funcional. **Nota:** `estado-fase.md` es la fuente canónica de estado para Fase V (`phase-state.md:5`).

---

## 4. Decisiones de Arquitectura Tomadas

**Heredadas de Fase IV:**
- **Modo Estricto Global:** Registry en modo estricto, sin fallbacks accidentales.
- **System Bundle Trust:** Bundles con `author: FAP-CORE` activan `is_system=True` en `SecurityGuard`.
- **Aislamiento Multi-Tenant:** `OrgBaseTool` con proxy `self._get_secret()` para secretos.

**Nuevas en Paso 2:**
- **Schema sin cambios:** `WorkflowDefinition.allowed_tools: list[str]` ya soporta `mcp:server:tool` y `service_connector` sin modificación — el plan decía lo contrario pero el código real lo permite.
- **Prompt expansion en lugar de refactor:** Solo se modifica el string del prompt, sin cambios en firmas o flujo de ejecución.
- **Validación post-generación (opcional):** La herramienta DX valida contra `org_mcp_servers` antes de bundle — warning no blocking.

**Nuevas en Paso 3:**
- **Arquitectura de Tests E2E:** Cada escenario tiene su propio archivo de test (`test_scenario_N_name.py`) + un CLI runner unificado (`test_scenarios.py`).
- **Validación de Tools:** Nuevo comando `fap validate-tools` para verificar disponibilidad de tools en registry antes de ejecutar escenarios.
- **Pipeline de Análisis Multi-Agente:** 4 agentes (kilo, mm, qwen, atg) analizan cada paso + síntesis final + validación — replicable para futuros pasos.

**Nuevas en Paso 4:**
- **DX Unification:** Tres propuestas de herramientas (`fap cert-phase`, `fap phase-close`, `fap generate-contratos`) fusionadas en `fap phase-close --certify` para evitar duplicación.
- **Resolución automática de discrepancias:** D1-D6 son editables por script — la herramienta `fap phase-close --certify` las resuelve automáticamente.
- **Dogfooding integral:** La herramienta `fap phase-close` fue usada para cerrar su propia fase (commit `5ca8dfc`).
- **Estructura de documentación canónica:** `estado-fase.md` = fuente de verdad para estado de pasos. `phase-state.md` = documento técnico de referencia para analistas/implementadores.

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Decisiones Tomadas | Notas |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fase IV (S1-S9)** | ✅ | `IMPLEMENTED/parity/` | — | Paridad local-producción | Completada |
| **Paso 1** | ✅ | `IMPLEMENTED/details4agents/01-mejora-infraestructura-herramientas/` | `c9f8eff` | MCP bridging en `AgentFactory`, `create_agent_async`, `run_async` | Código commiteado |
| **Paso 2** | ✅ | `IMPLEMENTED/details4agents/02-Upgrade-del-Cerebro/` | `c9f8eff` | Prompt expandido MCP+service_connector, `fap validate-architect-output`, `SAFE_BUILTIN_TOOLS` | Código commiteado |
| **Paso 3** | ✅ | `IMPLEMENTED/details4agents/03-Suite-de-los-6-Escenarios/` | `4f61392` | 6 escenarios E2E, `fap test-scenarios`, `fap validate-tools`, pipeline multi-agente | Análisis y código commiteados |
| **Paso 4** | ✅ | `IMPLEMENTED/details4agents/04-Documentacion-y-Cierre/` | `30fc6ef` | `fap phase-close --certify`, resolución D1-D6, certificación Fase V | Fase V cerrada. `estado-fase.md` = canónico |

---

## 6. Criterios Generales de Aceptación MVP (Fase V)

**Del Paso 2:**
- [x] El prompt del Architect incluye `category` y `approval_threshold` en el schema JSON.
- [x] El prompt explica formato `mcp:server:tool` con ≥2 ejemplos.
- [x] El prompt explica `service_connector` con ≥1 ejemplo.
- [x] El prompt incluye guía de selección MCP vs service_connector.
- [x] `workflow_guardrails` tiene explicititud de `service_connector` como tool válida (`SAFE_BUILTIN_TOOLS`).
- [x] `fap validate-architect-output` existe y valida referencias contra registry.
- [x] Lint pasa al 100% (`ruff check src/ tests/`).
- [x] Tests unitarios pasan — `pytest tests/unit/` (test_factory.py 12/12).

**Para Paso 3:**
- [x] `fap test-scenarios` ejecuta los 6 escenarios sin errores.
- [x] Escenario 1: Agente "Greeter" genera y ejecuta workflow simple.
- [x] Escenario 2: Agente "Slack Notifier" usa `service_connector` correctamente.
- [x] Escenario 3: Agente "File Manager" usa servidor MCP local correctamente.
- [x] Escenario 4: Agente Híbrido combina MCP + Integración.
- [x] Escenario 5: Flujo Multi-Agente (Investigador → Escritor → Corrector) con paso de contexto.
- [x] Escenario 6: Flujo Full Stack con todas las capacidades.
- [x] Código de Paso 3 commiteado a git.

**Para Paso 4:**
- [x] `fap phase-close --phase details4agents --certify` implementado y ejecuta sin errores.
- [x] `estado-fase.md` actualizado con contratos de Fase V (§2, §3, §4, §5).
- [x] `proyecto-config.json phase.current_step` actualizado a `"04-Documentacion-y-Cierre"`.
- [x] Discrepancias D1-D6 resueltas en documentación.
- [x] `phase-state.md` marcado como documento de referencia técnica.
- [x] Fase V oficialmente cerrada.

---

## 📦 Ultimo Archivado

- **Origen:** `DEVS/IN_PROGRESS/`
- **Destino:** `DEVS/IMPLEMENTED/details4agents/04-Documentacion-y-Cierre/`
- **Archivos movidos:**
  - `analisis-ds.md`
  - `analisis-FINAL.md`
  - `analisis-kilo.md`
  - `analisis-qwen.md`
  - `validacion.md`
- **Commit:** `30fc6ef` — "04-Documentacion-y-Cierre"

---

*Documento actualizado por el Arquitecto de Contexto (Antigravity) siguiendo el protocolo 6_CONTEXTO.md v4.1.*
*Fase V - details4agents — CERRADA. 4/4 pasos completados, archivados y commiteados.*
