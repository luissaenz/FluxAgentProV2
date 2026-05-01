# Análisis — Paso 4: Documentación y Cierre

**Agente:** qwen
**Paso:** 4 — Documentación y Cierre
**Fase:** details4agents
**Fecha:** 2026-04-30
**Dependencias:** Paso 1 ✅ | Paso 2 ✅ | Paso 3 ✅

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` | grep en migrations | ✅ | `004_agent_catalog.sql:6` — columnas id, org_id, role, is_active, soul_json, allowed_tools (TEXT[]), max_iter |
| 2 | Tabla `workflow_templates` | grep en migrations | ✅ | `006_workflow_templates.sql:6` — columnas id, org_id, name, description, flow_type, definition (JSONB), is_active |
| 3 | Tabla `org_mcp_servers` | grep en migrations | ✅ | `005_org_mcp_servers.sql` — nombre, command, args (JSONB), secret_name, is_active |
| 4 | `ArchitectFlow` existe | grep en src/flows | ✅ | `architect_flow.py:51` — clase con decorator `@register_flow` |
| 5 | `BundleManager.create_bundle()` | grep en services | ✅ | `bundle_manager.py:197-244` — método genera ZIP con SHA256 hash |
| 6 | `DynamicWorkflow` existe | grep en src/flows | ✅ | `dynamic_flow.py:27` — clase hereda de BaseFlow |
| 7 | `workflow_templates` tiene índice UNIQUE en flow_type | grep en migrations | ✅ | `006_workflow_templates.sql:47-48` — `CREATE UNIQUE INDEX idx_workflow_templates_flow_type ON workflow_templates(flow_type)` |
| 8 | RLS policies en workflow_templates | grep en migrations | ✅ | `006_workflow_templates.sql:54-57` — POLICY tenant_isolation |
| 9 | `WorkflowDefinition` tiene campo `category` | grep en workflow_definition.py | ✅ | `workflow_definition.py:71` — `category: str Field(default="business")` |
| 10 | `WorkflowDefinition` tiene campo `approval_threshold` en StepDefinition | grep en workflow_definition.py | ✅ | `workflow_definition.py:47` — `approval_threshold: Optional[str] = None` |
| 11 | `BaseFlow` tiene métodos `persist_state` y `emit_event` | grep en base_flow.py | ✅ | `base_flow.py:89-103` (persist_state), `base_flow.py:105-113` (emit_event) |
| 12 | `_check_approval_rule` solo soporta `>` y `<` | grep en dynamic_flow.py | ✅ | `dynamic_flow.py:128-159` — solo parsea `>` y `<`, no `>=`, `<=`, `==` |
| 13 | `fap validate-architect-output` existe | grep en CLI commands | ✅ | `validate_architect.py:235` — función `validate_architect_output()` |
| 14 | `fap test-scenarios` existe | grep en CLI commands | ✅ | `test_scenarios.py:588` — comando Typer con 6 escenarios |
| 15 | `fap validate-tools` existe | grep en CLI commands | ✅ | `validate_tools.py` — comando CLI |
| 16 | Tool registry tiene `get()` con org_id scope | grep en registry.py | ✅ | `registry.py:75-89` — lookup con org_id fallback a global |
| 17 | MCPPool tiene `get_tools()` async | grep en mcp_pool.py | ✅ | `mcp_pool.py:77-190` — método async con circuit breaker |
| 18 | `service_connector` como tool referenciada | grep en architect_flow.py | ✅ | `architect_flow.py:270-281` — ejemplos de uso en prompt |

**Discrepancias encontradas:**

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | `_check_approval_rule` docstring dice `>, <, >=, <=` pero implementación solo maneja `>` y `<` | Documentado como limitación conocida en validacion.md Paso 3. No блокирует — escenarios HITL usan `>` y `<`. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema y tablas

- **`workflow_templates`**: Almacena workflows generados por Architect. Columnas: `id, org_id, name, description, flow_type, definition (JSONB), is_active, status, execution_count`. Índice UNIQUE en `flow_type` garantiza unicidad global.
- **`agent_catalog`**: Agentes generados. Columna `allowed_tools TEXT[]` acepta tanto tools regulares como `mcp:server:tool` y `service_connector` sin cambios de schema.
- **`org_mcp_servers`**: Servidores MCP configurados por org. Necesario para validar referencias `mcp:` en bundles.

### Integridad referencial

- `workflow_templates.org_id` → `organizations(id)` ON DELETE CASCADE
- `agent_catalog.org_id` → `organizations(id)` ON DELETE CASCADE
- RLS policies con `current_setting('app.org_id', TRUE)` garantizan tenant isolation.

### Índices necesarios

- `idx_workflow_templates_flow_type` (UNIQUE) — ya existe en `006_workflow_templates.sql:47`
- `idx_agent_catalog_org_role` — ya existe en `004_agent_catalog.sql:26`

### Tipos de datos problemáticos

- Ninguno. `TEXT[]` para `allowed_tools` acepta cualquier formato de string.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases nuevas o modificadas

| Componente | Archivo | Responsabilidad |
|---|---|---|
| `ArchitectFlow` | `src/flows/architect_flow.py` | Genera workflows desde NL. Output: `WorkflowDefinition` + ZIP bundle en base64. Usa `_execute_architect_agent()` con prompt expandido (MCP + service_connector). |
| `BundleManager.create_bundle()` | `src/services/bundle_manager.py` | Crea ZIP con SHA256 hashes. Genera manifest con autor `SYSTEM-GENERATED` para bundles del Architect. |
| `DynamicWorkflow._check_approval_rule()` | `src/flows/dynamic_flow.py` | Evalúa condiciones de approval. Limitación: solo soporta `>` y `<`. |
| `validate_architect_data()` | `src/cli/commands/validate_architect.py` | Valida JSON contra schema + MCP servers + service_tools. Retorna `valid, errors, warnings`. |

### Patrones seguidos

- Decorador `@register_flow("architect_flow", category="system")` — confirmado en `architect_flow.py:50`
- `WorkflowDefinition` como Pydantic model con validators — confirmado en `workflow_definition.py`
- RLS con `org_id::text = current_setting('app.org_id', TRUE)` — confirmado en `006_workflow_templates.sql:57`
- Bundle ZIP con SHA256 hash — confirmado en `bundle_manager.py:98,212`

### Modularidad y calidad

- `ArchitectFlow` delega validación a `validate_workflow()` (workflow_guardrails)
- `_execute_architect_agent()` genera prompt con ejemplos MCP y service_connector
- `_parse_workflow_definition()` usa helper `extract_json_from_text()` para manejo robusto de CrewOutput

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints creados

| Endpoint | Método | Payload | Descripción |
|---|---|---|---|
| `POST /api/bundles/import` | POST | `{bundle_b64, org_id}` | Importa bundle ZIP generado por Architect. Persiste agents en `agent_catalog` y flows en `workflow_templates`. |

### Middleware aplicable

- `require_org_id` — para extraer `org_id` del JWT
- `verify_supabase_jwt` — autenticación
- RLS policies en `agent_catalog`, `workflow_templates` — aislamiento tenant

### Flujos de datos

1. Usuario ejecuta `ArchitectFlow` con descripción NL
2. `_execute_architect_agent()` genera JSON → `_parse_workflow_definition()` valida
3. `BundleManager.create_bundle()` genera ZIP → base64 encode
4. `POST /api/bundles/import` persiste en DB
5. `DynamicWorkflow` carga workflow desde `workflow_templates` y ejecuta steps

### Error handling

- JSON inválido: `ValueError` con mensaje descriptivo (`architect_flow.py:333-335`)
- Workflow inválido: `WorkflowValidationError` → retry con feedback (`architect_flow.py:135-136`)
- Flow type duplicado: `_ensure_unique_flow_type()` agrega sufijo (`architect_flow.py:346-377`)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

```
Usuario (NL description)
    → ArchitectFlow._execute_architect_agent()
    → LLM genera JSON con MCP/service_connector
    → WorkflowDefinition(**data) valida
    → BundleManager.create_bundle() → ZIP
    → POST /api/bundles/import → agent_catalog + workflow_templates
    → DynamicWorkflow.load_dynamic_flows_from_db()
    → Webhook POST /webhooks/{org_id}/{flow_type}
    → DynamicWorkflow._run_crew() → steps secuenciales
    → BaseCrew.run_async() → Agent con tools resueltas
```

### Coherencia MVP

- El MVP permite generar agentes con MCP tools e integraciones HTTP sin cambios de schema.
- Bundles se importan y ejecutan correctamente.
- Aprobaciones HITL funcionan con `_check_approval_rule` (limitado a `>` y `<`).

### Gaps

| Gap | Descripción | Impacto |
|---|---|---|
| G1 | `_check_approval_rule` no soporta `>=`, `<=`, `==` | Escenarios HITL con этих operadores no funcionan. Documentado como limitación. |
| G2 | No hay comando `fap` para actualizar phase-state.md | Cierre de fase requiere edición manual. |

### DX & Tooling (OBLIGATORIO)

```
### Herramienta: fap phase-close
- **Qué automatiza:** Cierre de fase automático — actualiza phase-state.md y phase-state.md con summary de la fase, marca pasos como completados, y genera reporte de certificación.
- **Tipo:** CLI command (Typer)
- **Ubicación:** `src/cli/commands/phase_close.py` (registrado en `src/cli/main.py`)
- **Cómo se usa:**
  - `fap phase-close --phase details4agents --org-id <uuid>`
  - Genera: resumen de fase, pasos completados, estadísticas de tests, artifacts generados
- **Impacto para el usuario final:** Cierre de fase documentado correctamente sin edición manual de markdown. Garantiza trazabilidad.
- **Prioridad:** Alta — debe ejecutarse como último paso del cierre de fase.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] workflow_templates tiene definición de workflow con category, steps, agents
✅ [DATA] agent_catalog tiene allowed_tools como TEXT[] (soporta mcp: y service_connector)
✅ [CODE] ArchitectFlow genera JSON válido contra WorkflowDefinition
✅ [CODE] BundleManager.create_bundle() genera ZIP con SHA256 y autor SYSTEM-GENERATED
✅ [CODE] DynamicWorkflow._check_approval_rule() evalúa condiciones (solo > y <)
✅ [BACKEND] POST /api/bundles/import persiste bundle del Architect
✅ [BACKEND] DynamicWorkflow.load_dynamic_flows_from_db() carga templates activos
✅ [FULLSTACK] Architect genera → bundle importado → DynamicWorkflow ejecuta → approval rules evaluadas
✅ [FULLSTACK] validate_architect_output verifica JSON contra MCP servers y service_tools de la org
✅ [DX] fap phase-close ejecuta cierre de fase y actualiza documentos de estado
✅ [DX] Documentación de contratos técnicos actualizada en phase-state.md
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Approval rules con operadores no soportados crashean | Media | `_check_approval_rule` solo parsea `>` y `<` | Documentar limitación. Escenarios usan solo `>` y `<`. No corregir en este paso. |
| workflow_templates con flow_type duplicado | Baja | Índice UNIQUE pero múltiples orgs pueden tener mismo nombre | `_ensure_unique_flow_type()` ya implementado con sufijo |
| Bundle import con references MCP inválidas | Media | `validate_architect` valida antes de import pero no es blocking | Warning no blocking, servidor MCP puede no estar activo aún |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `fap phase-close` CLI | FULLSTACK/DX | Baja | 2h | Ninguna |
| 1 | Actualizar `DEVS/phase-state.md` con nuevos contratos técnicos | DATA | Baja | 0.5h | Ninguna |
| 2 | Actualizar `DEVS/phase-state.md` con resumen de fase | FULLSTACK | Baja | 0.5h | Tarea 1 |
| 3 | Documentar limitaciones descubiertas (_check_approval_rule) | CODE | Baja | 0.25h | Ninguna |
| 4 | Ejecutar `fap phase-close --phase details4agents` | DX | Baja | 0.25h | Tareas 0-3 |
| **TOTAL** | | | | **3.5h** | |

---

## 🔮 Roadmap (NO implementar ahora)

- Implementar soporte completo de operadores en `_check_approval_rule` (`>=`, `<=`, `==`)
- Agregar comando `fap bundle-execute` para ejecutar workflow importado directamente
- Soporte de versionado de bundles (upgrade/downgrade)
- Métricas de ejecución de workflows en DB para dashboard