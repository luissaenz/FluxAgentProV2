# Plan: Agentes Reales Productivos

> **Objetivo:** Llevar agentes de presupuesto desde tests offline hasta producción (registrados, ejecutables via API/CLI, con tool calling real y flows formales).
> **Origen:** Sesión de pruebas con datos reales Aybar (11 sheets, Groq LLM, tests multi-agente).
> **Estado:** ⏳ PENDIENTE

---

## Dependencias Entre Pasos

```
Paso 1 (fix deadlock MCP) ──┐
                             ├──→ Paso 4 (Flow.execute real) ──→ Paso 5 (flow registrado)
Paso 2 (registrar agente) ──┘
           │
Paso 3 (tool calling) ──────┘

Paso 6 (ExcelWriter) ──→ standalone, paralelo a todo
```

---

## Paso 1: Fix Deadlock en MCP Resolution Async

**Archivo:** `src/crews/factory.py`
**Estimación:** 1h
**Bloqueante para:** Paso 4, 5

### Problema
`_resolve_mcp_tool()` usa `asyncio.run_coroutine_threadsafe(coro, loop).result()` que deadlockea cuando se ejecuta desde el mismo event loop (contexto async).

### Solución
Agregar `resolve_tools_async()` y `_resolve_mcp_tool_async()` que usen `await` en vez de `run_coroutine_threadsafe`. `create_agent_async()` pasa a ser async y usa la variante async.

### Cambios
| Archivo | Cambio |
|---------|--------|
| `src/crews/factory.py` | Agregar `resolve_tools_async()` y `_resolve_mcp_tool_async()`. `create_agent_async()` → `async def` y llama `await resolve_tools_async()` |
| `src/crews/base_crew.py` | `run_async()` ya tiene `await AgentFactory.create_agent_async()` — sin cambios |

### Tests
- `tests/unit/test_factory.py`: agregar test para `resolve_tools_async` con MCP mock
- `tests/e2e/test_exec_agent_mcp.py`: remover parche `_resolve_mcp_tool` → test usa resolución async real

### Criterios
- [ ] Flow async con MCP tools completa sin deadlock
- [ ] Flow sync con MCP tools skipea (comportamiento actual)
- [ ] Tests existentes de factory pasan sin modificación

---

## Paso 2: Registrar Agente Presupuestador en el Sistema

**Archivos:** `data/seed/` (nuevo bundle), API
**Estimación:** 2h
**Bloqueante para:** Paso 4, 5

### Qué hacer
1. Crear bundle ZIP con agente `presupuestador` + `excel_reader` tool
2. Crear definición de agente en `agents/presupuestador.json` con `soul_json`, `allowed_tools: ["excel_reader"]`
3. Importar bundle via API `POST /api/bundles/import`
4. Verificar agente visible en `agent_catalog`

### Bundle structure
```
presupuesto-bundle/
├── manifest.json
├── agents/
│   └── presupuestador.json   # role, goal, backstory, allowed_tools
└── skills/
    └── excel_reader.py        # opcional — el tool ya está registrado en sistema
```

### Tests
- Test E2E: bundle import → HTTP 201 → agente en agent_catalog
- Test E2E: consultar agente via API → datos correctos

---

## Paso 3: Tool Calling Real (Agente usa herramienta durante ejecución)

**Archivo:** `src/crews/factory.py` (opcional), tests
**Estimación:** 3h
**Bloqueante para:** Paso 4, 5

### Qué hacer
Hoy los tests pasan datos precargados al prompt. El agente no llama `excel_reader` activamente — recibe los datos como contexto.

Para tool calling real:
1. El agente tiene `allowed_tools: ["excel_reader"]` en su config
2. `AgentFactory.create_agent_async()` resuelve el tool → `ExcelReaderTool(org_id=xxx)`
3. CrewAI Agent recibe el tool en su lista
4. Durante `crew.kickoff_async()`, el LLM decide llamar `excel_reader` según necesidad
5. El resultado del tool se inyecta en el contexto del LLM

### Desafío
CrewAI tool calling requiere que el LLM soporte function calling. Groq con llama-3.3-70b lo soporta. Pero el formato de tool description debe ser claro para que el LLM decida usarlo.

### Tests
- Test con LLM real: agente con `excel_reader` tool que DEBE llamarlo para responder
- Verificar que la respuesta incluye datos de la sheet (no precargados)

---

## Paso 4: Flow.execute() con LLM Real

**Archivo:** Tests E2E
**Estimación:** 2h
**Depende de:** Paso 1 + Paso 2 + Paso 3

### Qué hacer
Ejecutar pipeline completo: `Flow.execute()` → `BaseFlow._run_crew()` → `BaseCrew.run_async()` → LLM real → output.

Similar a `test_real_agent_pipeline.py` pero pasando por `BaseFlow.execute()` que agrega:
- `create_task_record()` → persistencia en DB
- State transitions → PENDING → RUNNING → COMPLETED
- Event emission → flow.created, flow.completed
- `persist_state()` → snapshots + tasks update

### Tests
- Flow.execute() con LLM real + tool excel_reader
- Verificar state transitions + event emission + output

---

## Paso 5: Flow de Presupuesto Registrado Formalmente

**Archivo:** `src/flows/presupuesto_flow.py`
**Estimación:** 2h
**Depende de:** Paso 4

### Qué hacer
1. Crear `PresupuestoFlow(BaseFlow)` con `@register_flow("presupuesto")`
2. `validate_input()` verifica: tipo_evento, pax, fecha, provincia
3. `_run_crew()` ejecuta agente `presupuestador` con datos del input
4. Output: quote estructurada en JSON

### Tests
- Flow registrado en `flow_registry`
- POST `/api/webhooks/trigger` con flow_type="presupuesto"
- GET `/api/tasks/{task_id}` → status COMPLETED + output
- Test multi-turn: ejecutar flow, verificar output en DB

---

## Paso 6: ExcelWriterTool (Escribir Presupuesto a .xlsx)

**Archivo:** `src/tools/excel_writer.py`
**Estimación:** 2h
**Paralelo a:** todo lo demás

### Qué hacer
1. Crear `ExcelWriterTool(OrgBaseTool)` con `@register_tool("excel_writer")`
2. Input: filename, sheet_name, data (JSON array)
3. Output: escribe .xlsx en PROJECT-Aybar/
4. Integración futura: reemplazar por Google Sheets API

### Tests
- Unit: escribir + leer roundtrip
- Unit: append vs overwrite
- Unit: validación de datos (estructura JSON consistente)

## Paso 7: Cierre — Remanentes y Pulido para Cobertura Total

**Estimación:** 4h
**Depende de:** Todos los pasos anteriores (1-6)

### 7.1 P1 — Remover parche MCP en test E2E

**Archivo:** `tests/e2e/test_exec_agent_mcp.py`

**Contexto:** `_resolve_mcp_tool_async` está parcheado con `return_value=None` en el test (lines 63-67). El plan original exige resolución async real.

#### Cambios
| Detalle | Descripción |
|---------|-------------|
| Remover `patch("src.crews.factory.AgentFactory._resolve_mcp_tool_async")` | Eliminar las 4 líneas del context manager con `AsyncMock` y `return_value=None` |
| Agregar fixture o mock de `MCPPool.get().get_tools()` | Para que la resolución async tenga un server MCP mock que devuelva tools reales (o vacío controlado) |
| Validar que `MCPAgentFlow` ejecuta con resolución async real | Sin parche, el flow debe obtener tools via `resolve_tools_async()` → `_resolve_mcp_tool_async()` → `pool.get_tools()` |
| Test de caja negra | Ejecutar flow con MCP tool configurado y verificar que no hay deadlock |

#### Condiciones de aceptación
- [ ] Test `test_exec_agent_mcp.py::test_execute_with_mcp_tools` **no usa ningún parche** sobre `AgentFactory._resolve_mcp_tool_async`
- [ ] El mock de `MCPPool.get()` provee tools sin bloquear el event loop
- [ ] El flow completa con estado `COMPLETED`
- [ ] Todos los tests de `test_factory.py` pasan sin modificación

---

### 7.2 P2 — Crear bundle seed en `data/seed/`

**Archivos:** `data/seed/presupuesto-bundle/`

**Contexto:** El bundle ZIP existe en `presupuesto-bundle/` pero no hay directorio `data/seed/`. El plan original pide crear un bundle seed para importación automatizada.

#### Bundle seed structure
```
data/seed/
└── presupuesto-bundle/
    ├── manifest.json
    └── agents/
        └── presupuestador.json
```

#### Cambios
| Detalle | Descripción |
|---------|-------------|
| Copiar `presupuesto-bundle/manifest.json` a `data/seed/presupuesto-bundle/manifest.json` | Idéntico al existente |
| Copiar `presupuesto-bundle/agents/presupuestador.json` a `data/seed/presupuesto-bundle/agents/presupuestador.json` | Idéntico al existente |
| Verificar hashes en manifest.json coinciden con archivos | SHA256 real de cada archivo |
| Script helper (opcional) | `scripts/seed_bundle.py` que lee `data/seed/presupuesto-bundle/` y llama `POST /api/bundles/import` |

#### Condiciones de aceptación
- [ ] `data/seed/presupuesto-bundle/manifest.json` existe con hashes correctos
- [ ] `data/seed/presupuesto-bundle/agents/presupuestador.json` existe
- [ ] Correr `POST /api/bundles/import` con data del seed → HTTP 201

---

### 7.3 P2 — Test de consulta GET agente via API

**Archivos:** `tests/e2e/test_register_agent.py` (nuevo test)

**Contexto:** No hay test que consulte un agente via API luego de importarlo.

#### Test nuevo
```python
async def test_get_agent_via_api_returns_correct_data(mock_...)
```
1. Importar bundle via `POST /api/bundles/import`
2. Consultar vía `GET /api/agents/presupuestador` (o equivalente)
3. Verificar que el JSON devuelto contiene:
   - `role == "presupuestador"`
   - `soul_json.role == "Cotizador de Eventos"`
   - `soul_json.goal` incluye "excel_reader"
   - `allowed_tools == ["excel_reader"]`
   - `is_active == True`

#### Condiciones de aceptación
- [ ] Test `test_get_agent_via_api_returns_correct_data` implementado y pasando
- [ ] El test valida al menos 5 campos del agente

---

### 7.4 P4 — Agregar verificación de tool calling real en Flow.execute

**Archivo:** `tests/e2e/test_real_flow_execute.py`

**Contexto:** `test_flow_execute_with_tool` verifica estructura de output y state transitions pero **no** confirma que el LLM realmente llamó `excel_reader` vía tool calling. Solo valida que el output contiene ciertos campos (costos, precios).

#### Cambios
| Detalle | Descripción |
|---------|-------------|
| Agregar aserción `crew.get_last_tool_calls().get("excel_reader", 0) >= 1` | Después de `Flow.execute()`, inspeccionar `self.crew._last_tool_calls` |
| Acceder al crew interno | `flow.state.crew` o exponer `flow.get_last_crew_tool_calls()` desde `BaseFlow` |
| Si `BaseFlow` no expone el crew | Agregar propiedad `last_tool_calls` en `BaseFlow` que delegue al `BaseCrew` interno |
| Alternativa | Modificar `BaseFlow._run_crew()` para que retorne tool calls como metadata |

#### Condiciones de aceptación
- [ ] `test_real_flow_execute.py` verifica que `excel_reader` fue invocada ≥ 1 vez
- [ ] `BaseFlow` expone `last_tool_calls` o equivalente (si no existía)
- [ ] Output sigue siendo válido (no romper aserciones existentes)

---

### 7.5 — Consolidar tests duplicados de tool calling

**Archivos:**
- `tests/e2e/test_tool_calling_real.py` (136 lines)
- `tests/e2e/test_real_tool_calling.py` (129 lines)
- `tests/e2e/test_real_agent_pipeline.py` (139 lines)

**Contexto:** Tres archivos con propósito casi idéntico (verificar tool calling con LLM real). Los dos primeros son duplicados. El tercero usa LLM real pero no verifica tool calling.

#### Acciones
| Archivo | Acción |
|---------|--------|
| `tests/e2e/test_tool_calling_real.py` | **Conservar** (mejor nombre, más completo) |
| `tests/e2e/test_real_tool_calling.py` | **Eliminar** (duplicado) |
| `tests/e2e/test_real_agent_pipeline.py` | **Actualizar**: agregar verificación `get_last_tool_calls()` o **eliminar** si está cubierto por `test_tool_calling_real.py` |

#### Si se conserva `test_real_agent_pipeline.py`
- Agregar aserción `get_last_tool_calls()["excel_reader"] >= 1` después de `crew.run_async()`
- Asegurar que el task description incita al LLM a usar la tool (similar al wording en `presupuesto_flow.py`)

#### Condiciones de aceptación
- [ ] Solo 1 archivo (o 2 con roles distintos) cubre tool calling real con LLM
- [ ] Ningún test duplicado idéntico
- [ ] Test consolidado nombrado `test_tool_calling_real.py` (o nombre representativo)

---

### 7.6 — Tests legacy con pre-fetch data: migrar a tool calling real o deprecar

**Archivos:**
- `tests/e2e/test_real_agent_presupuesto.py` (183 lines)
- `tests/e2e/test_real_multi_agent_presupuesto.py` (184 lines)

**Contexto:** Estos tests NO usan `allowed_tools`. Pre-fetchen datos vía `ExcelReaderTool._run()` directo y los inyectan como texto en el prompt del LLM. No hay tool calling. El plan original (Paso 3) exige tool calling real donde el LLM decida llamar `excel_reader`.

#### Opciones
| Opción | Descripción | Esfuerzo |
|--------|-------------|----------|
| **A — Migrar** | Refactorizar para que el agente tenga `allowed_tools: ["excel_reader"]` y el LLM decida llamarlo. El test verifica `get_last_tool_calls()` | ~4h (multi-agente más complejo) |
| **B — Deprecar + docstring** | Marcar como `@pytest.mark.skip(reason="Legacy: reemplazado por test_tool_calling_real.py")`, agregar docstring explicando por qué existe y qué lo reemplaza | ~0.5h |
| **C — Mantener como integración** | Renombrar a `test_legacy_preloaded_presupuesto.py`, dejar como test complementario que prueba el pipeline sin tool calling (caso degrade) | ~0.5h |

#### Recomendación
Opción **B** (deprecar) — los tests de tool calling real (P3) y Flow.execute (P4) ya cubren el escenario con mejor calidad. Los tests legacy aportan falso positivo: parecen probar tool calling pero en realidad solo mandan contexto precargado.

#### Condiciones de aceptación
- [ ] `test_real_agent_presupuesto.py` tiene `@pytest.mark.skip` + docstring de reemplazo
- [ ] `test_real_multi_agent_presupuesto.py` tiene `@pytest.mark.skip` + docstring de reemplazo
- [ ] 0 tests legacy sin tool calling que pretendan probar "agente con excel_reader"

---

### 7.7 — Verificación cruzada: importación de bundle seed en test E2E

**Archivo:** `tests/e2e/test_register_agent.py` (nuevo test o extensión)

**Contexto:** Actualmente `test_register_agent.py` tests crean el bundle manualmente en memoria. No se prueba la importación desde el seed real (`data/seed/presupuesto-bundle/`).

#### Test nuevo
```python
async def test_import_seed_bundle_via_api(mock_...)
```
1. Cargar `data/seed/presupuesto-bundle/manifest.json` y leer agentes
2. Leer `data/seed/presupuesto-bundle/agents/presupuestador.json`
3. Armar ZIP en memoria con la estructura exacta del seed
4. `POST /api/bundles/import` con el ZIP
5. `assert response.status_code == 201`
6. Consultar `agent_catalog` y verificar agente existe con todos los campos

#### Condiciones de aceptación
- [ ] Test `test_import_seed_bundle_via_api` pasa con el seed real
- [ ] El test verifica que los campos en DB coinciden con el JSON del seed
- [ ] El test es independiente del entorno (usa mocks para Supabase)

---

### 7.8 — Verificar que `PresupuestoFlow.validate_input()` rechaza input inválido

**Archivo:** `tests/unit/test_presupuesto_flow.py` (nuevo test)

**Contexto:** `validate_input()` chequea solo 4 campos (`tipo_evento`, `pax`, `fecha`, `provincia`). `_run_crew()` usa también `duracion_horas` y `menu` (sin default robusto). No hay test unitario de validación.

#### Tests
```python
async def test_validate_input_rejects_missing_fields():
    flow = PresupuestoFlow(org_id="test", user_id="test")
    assert not flow.validate_input({})
    assert not flow.validate_input({"tipo_evento": "boda"})
    assert not flow.validate_input({"tipo_evento": "boda", "pax": 100})
    assert flow.validate_input({"tipo_evento": "boda", "pax": 100, "fecha": "2026-03-15", "provincia": "Tucumán"})
```

#### Condiciones de aceptación
- [ ] Test unitario de validación de input para `PresupuestoFlow`
- [ ] Test verifica que inputs incompletos retornan `False`
- [ ] Test verifica que input completo retorna `True`

---

## Resumen de Estimación

| Paso | Tiempo | Depende de |
|------|--------|------------|
| 1 — Fix deadlock MCP | 1h | — |
| 2 — Registrar agente | 2h | — |
| 3 — Tool calling real | 3h | 1, 2 |
| 4 — Flow.execute real | 2h | 1, 2, 3 |
| 5 — Flow registrado | 2h | 4 |
| 6 — ExcelWriter | 2h | — |
| **7 — Cierre** | **~4h** | **1-6** |
| **Total** | **~16h** | |

### Desglose Paso 7

| Sub-paso | Descripción | Tiempo |
|----------|-------------|--------|
| 7.1 | Remover parche MCP en test E2E | 0.75h |
| 7.2 | Crear bundle seed en `data/seed/` | 0.25h |
| 7.3 | Test de consulta GET agente via API | 0.5h |
| 7.4 | Agregar tool calling check en Flow.execute test | 0.5h |
| 7.5 | Consolidar tests tool calling duplicados | 0.5h |
| 7.6 | Migrar/deprecar tests legacy pre-fetch | 0.5h |
| 7.7 | Verificación cruzada bundle seed | 0.5h |
| 7.8 | Test unitario validate_input() | 0.25h |
| **Total** | | **~3.75h** |

---

## 📥 Pasos incorporados desde sugerencias de validación
> Incorporados el 2026-05-05 — Fase activa: patch_agents

## Paso 8: 08-sincronizar-proyecto-config-con-fase-activa

**Origen:** Sugerencia 🟡 de validación — Paso 3: Tool Calling Real
**Prioridad:** Alta
**Fase:** patch_agents

### Objetivo
Actualizar `proyecto-config.json` para reflejar la fase activa `patch_agents`, sincronizando `phase_name`, `current_step` y `pipeline` con el estado real del proyecto registrado en `phase-state.md`.

### Tareas
- [ ] Cambiar `phase.phase_name` de `"testing"` a `"patch_agents"` en `proyecto-config.json`
- [ ] Actualizar `phase.current_step` al último paso completado (06-ExcelWriterTool, commit `7827d78`)
- [ ] Actualizar `pipeline.*` flags para reflejar estado actual (phase_state_exists ✅, pasos implementados)
- [ ] Verificar que discrepancias documentadas en phase-state.md §2 y §4 se reducen post-actualización
- [ ] Confirmar lint 0 post-cambio

### Criterios de Aceptación
- [ ] `proyecto-config.json` muestra `phase_name: "patch_agents"` (no `"testing"`)
- [ ] `phase.current_step` coincide con el último paso completado en `phase-state.md §5`
- [ ] Todas las discrepancias sobre `phase_name` incorrecto en phase-state.md están resueltas
- [ ] Pipeline downstream (analistas, implementadores, validadores) reciben `phase_name` correcto

### Notas
Dependencia con ID-001 de sugest.md. Este paso es crítico porque `proyecto-config.json` es la fuente de verdad que todos los agentes downstream consumen. Error aquí = error en todo el pipeline. La desincronización persiste desde commit `64cf7c5`.
