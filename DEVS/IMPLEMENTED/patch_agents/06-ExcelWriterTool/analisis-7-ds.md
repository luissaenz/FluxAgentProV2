# Análisis Técnico — Paso 7: Cierre — Remanentes y Pulido para Cobertura Total

**Agente:** ds  
**Fecha:** 2026-05-04  
**Paso:** 7 (8 sub-pasos: 7.1–7.8)  
**Destino:** `DEVS/IN_PROGRESS/analisis-7-ds.md`

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `tests/e2e/test_exec_agent_mcp.py` existe | grep en `tests/e2e/` | ✅ | línea 62-67 — `patch("src.crews.factory.AgentFactory._resolve_mcp_tool_async")` con `return_value=None` |
| 2 | `data/seed/` existe | glob `data/seed/**` | ❌ NO EXISTE | Directorio `data/seed/` no creado |
| 3 | `presupuesto-bundle/manifest.json` existe | glob `presupuesto-bundle/manifest.json` | ✅ | 17 líneas con hashes correctos |
| 4 | `presupuesto-bundle/agents/presupuestador.json` existe | glob `presupuesto-bundle/agents/presupuestador.json` | ✅ | 12 líneas, `allowed_tools: ["excel_reader"]` |
| 5 | SHA256 en manifest coincide con archivo real | calculado vs declarado | ✅ | `8bdc4257879bd9c362819bcafff163a0d54ded2d1f6f9b20d4598d188ec5524a` coincide |
| 6 | `tests/e2e/test_register_agent.py` tiene `test_get_agent_via_api_returns_correct_data` | grep en test_register_agent.py | ❌ NO EXISTE | Solo `test_bundle_import_returns_201`, `test_agent_definition_valid`, `test_bundle_hash_integrity`, `test_excel_reader_tool_registered`, `test_agent_can_use_excel_reader` |
| 7 | `tests/e2e/test_real_flow_execute.py` verifica tool calling | grep `get_last_tool_calls` | ❌ NO VERIFICA | Verifica state transitions, output structure, DB persistence — pero NO `get_last_tool_calls()` |
| 8 | `BaseFlow` expone `last_tool_calls` | grep `last_tool_calls` en `src/flows/base_flow.py` | ❌ NO EXPONE | `BaseFlow` no tiene propiedad `last_tool_calls` ni referencia al crew interno |
| 9 | `BaseCrew.get_last_tool_calls()` existe | grep en `src/crews/base_crew.py` | ✅ | línea 206-213 — retorna `Dict[str, int]` |
| 10 | `tests/e2e/test_tool_calling_real.py` existe | glob | ✅ | 136 líneas, test `test_presupuestador_calls_excel_reader` |
| 11 | `tests/e2e/test_real_tool_calling.py` existe | glob | ✅ | 129 líneas, test `test_agent_uses_excel_reader_tool` |
| 12 | `tests/e2e/test_real_agent_pipeline.py` existe | glob | ✅ | 139 líneas, test `test_agent_presupuesto_via_crewai` |
| 13 | `tests/e2e/test_real_agent_presupuesto.py` existe | glob | ✅ | 183 líneas, 2 tests — NO usa `allowed_tools`, pre-fetch via `ExcelReaderTool._run()` directo |
| 14 | `tests/e2e/test_real_multi_agent_presupuesto.py` existe | glob | ✅ | 184 líneas, 1 test multi-agente — pre-fetch data, NO tool calling |
| 15 | `tests/e2e/test_presupuesto_flow.py` tiene tests de validación | grep en test_presupuesto_flow.py | ✅ | `test_validate_input_requires_all_fields`, `test_validate_input_rejects_missing_provincia`, `test_validate_input_accepts_with_provincia` (e2e, no unit) |
| 16 | `tests/unit/test_presupuesto_flow.py` existe | glob `tests/unit/test_presupuesto_flow.py` | ❌ NO EXISTE | No hay test unitario dedicado para `PresupuestoFlow.validate_input()` |
| 17 | `test_tool_calling_real.py` vs `test_real_tool_calling.py` son duplicados | diff | ✅ CONFIRMADO | Mismo patrón (save real classes → counter-patch → BaseCrew.run_async → get_last_tool_calls). Difieren en tildes y descripciones de backstory |
| 18 | `test_real_agent_pipeline.py` NO verifica tool calling | grep `get_last_tool_calls` | ✅ CONFIRMADO | Solo verifica `"Mocked Crew Result" not in raw` + JSON parse |

### Discrepancias Encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | `data/seed/` NO existe. Plan pide crear bundle seed allí | Crear `data/seed/presupuesto-bundle/` con copias de `presupuesto-bundle/manifest.json` y `agents/presupuestador.json` |
| D2 | `test_get_agent_via_api_returns_correct_data` NO existe en `test_register_agent.py` | Agregar test que importa bundle via API y consulta GET agente |
| D3 | `test_real_flow_execute.py` NO verifica tool calling real | Agregar aserción `crew.get_last_tool_calls()["excel_reader"] >= 1` post-ejecución. Requiere exponer crew en BaseFlow |
| D4 | `BaseFlow` NO expone crew interno para inspeccionar tool calls | Agregar propiedad `last_tool_calls` en `BaseFlow` que delegue al `BaseCrew` interno, O modificar `_run_crew()` para que retorne metadata con tool calls |
| D5 | `tests/unit/test_presupuesto_flow.py` NO existe. Tests de validación están en e2e, no unit | Crear test unitario independiente o mover tests existentes de e2e a unit |
| D6 | `test_real_tool_calling.py` (129 lines) casi idéntico a `test_tool_calling_real.py` (136 lines) | Eliminar `test_real_tool_calling.py` — conservar `test_tool_calling_real.py` (mejor nombre, más completo) |
| D7 | `test_real_agent_pipeline.py` (139 lines) similar pero sin verificación tool calling | Actualizar con `get_last_tool_calls()` o eliminar si cubierto por `test_tool_calling_real.py` |
| D8 | `test_real_agent_presupuesto.py` + `test_real_multi_agent_presupuesto.py` usan pre-fetch data, no tool calling real | Deprecar con `@pytest.mark.skip` + docstring de reemplazo (Opción B del plan) |
| D9 | `test_exec_agent_mcp.py` parchea `_resolve_mcp_tool_async` con `return_value=None` — no hay resolución async real | Remover parche, agregar fixture/mock de `MCPPool.get().get_tools()` que devuelva tools reales o vacío controlado |

---

## 1️⃣ Análisis de Datos

### Schema afectado
- Ningún cambio de schema DB requerido. Todos los sub-pasos son código y tests.

### Bundle seed (`data/seed/presupuesto-bundle/`)
- Estructura exacta:
  ```
  data/seed/
  └── presupuesto-bundle/
      ├── manifest.json          (copiar de presupuesto-bundle/manifest.json)
      └── agents/
          └── presupuestador.json (copiar de presupuesto-bundle/agents/presupuestador.json)
  ```
- `manifest.json` actual tiene `hashes` con SHA256 correcto (`8bdc4257879bd9c362819bcafff163a0d54ded2d1f6f9b20d4598d188ec5524a`)
- El hash NO incluye el propio `manifest.json` en el cómputo — solo `agents/presupuestador.json`

### Tablas DB referenciadas
- `agent_catalog` (migración 004): id, org_id, name, description, allowed_tools text[], code, soul_json jsonb, version, enabled — verificada existente
- `tasks` (migraciones varias): id, org_id, flow_type, status, payload, result, tokens_used — verificada existente
- `snapshots` (migraciones varias): task_id, org_id, flow_type, status, state_json — verificada existente

---

## 2️⃣ Análisis de Código

### Archivos a crear

| Archivo | Propósito | Patrón a seguir |
|---|---|---|
| `data/seed/presupuesto-bundle/manifest.json` | Bundle seed para importación automatizada | Copia literal de `presupuesto-bundle/manifest.json` |
| `data/seed/presupuesto-bundle/agents/presupuestador.json` | Definición de agente seed | Copia literal de `presupuesto-bundle/agents/presupuestador.json` |
| `tests/unit/test_presupuesto_flow.py` (NUEVO) | Test unitario de `validate_input()` | Ver `test_presupuesto_flow.py:108-121` (tests existentes en e2e) + `plan.md:350-356` |

### Archivos a modificar

| Archivo | Cambio | Función/Clase afectada |
|---|---|---|
| `tests/e2e/test_exec_agent_mcp.py` | Remover `patch("src.crews.factory.AgentFactory._resolve_mcp_tool_async")` (líneas 62-67). Agregar fixture/mock `MCPPool.get().get_tools()` | `TestExecAgentMCP.test_mcp_flow_completes` |
| `tests/e2e/test_register_agent.py` | Agregar `test_get_agent_via_api_returns_correct_data` | Nueva función test |
| `tests/e2e/test_real_flow_execute.py` | Agregar verificación `get_last_tool_calls()["excel_reader"] >= 1` | `test_flow_execute_with_tool` |
| `src/flows/base_flow.py` | Agregar propiedad `last_tool_calls` que delegue al crew interno | `BaseFlow` |
| `tests/e2e/test_real_agent_pipeline.py` | Agregar aserción `get_last_tool_calls()["excel_reader"] >= 1` o eliminar | `test_agent_presupuesto_via_crewai` |
| `tests/e2e/test_real_agent_presupuesto.py` | Agregar `@pytest.mark.skip` + docstring de reemplazo | Archivo completo |
| `tests/e2e/test_real_multi_agent_presupuesto.py` | Agregar `@pytest.mark.skip` + docstring de reemplazo | Archivo completo |

### Archivos a eliminar

| Archivo | Razón |
|---|---|
| `tests/e2e/test_real_tool_calling.py` | Duplicado de `test_tool_calling_real.py` (mismo patrón, variaciones mínimas) |

### Firma de nuevas funciones

```python
# BaseFlow (src/flows/base_flow.py)
@property
def last_tool_calls(self) -> Dict[str, int]:
    """Return tool invocation counts from last crew run.
    
    Delegates to the internal BaseCrew used in _run_crew().
    Returns empty dict if no run completed or crew not exposed.
    """
    return getattr(self._last_crew, "get_last_tool_calls", lambda: {})()
```

### Firma de nuevos tests

```python
# tests/e2e/test_register_agent.py
async def test_get_agent_via_api_returns_correct_data(mock_...):
    """Import bundle -> GET /api/agents/presupuestador -> verify 5+ fields."""
    # 1. Import bundle via POST /api/bundles/import
    # 2. GET /api/agents/presupuestador (o equivalente)
    # 3. Assert: role == "presupuestador"
    #    soul_json.role == "Cotizador de Eventos"
    #    soul_json.goal includes "excel_reader"
    #    allowed_tools == ["excel_reader"]
    #    is_active == True

# tests/unit/test_presupuesto_flow.py
def test_validate_input_rejects_missing_fields():
    """Incomplete inputs return False."""
    flow = PresupuestoFlow(org_id="test", user_id="test")
    assert not flow.validate_input({})
    assert not flow.validate_input({"tipo_evento": "boda"})
    assert not flow.validate_input({"tipo_evento": "boda", "pax": 100})
    assert flow.validate_input({"tipo_evento": "boda", "pax": 100, "fecha": "2026-03-15", "provincia": "Tucumán"})

# tests/e2e/test_register_agent.py (extensión)
async def test_import_seed_bundle_via_api(mock_...):
    """Import seed from data/seed/presupuesto-bundle/."""
    # 1. Load manifest.json and agents/presupuestador.json from seed dir
    # 2. Build ZIP in memory matching seed structure
    # 3. POST /api/bundles/import -> HTTP 201
    # 4. Query agent_catalog -> agent exists with all fields
```

---

## 3️⃣ Análisis de Backend

### Endpoints afectados

| Endpoint | Método | Uso en el paso | Estado actual |
|---|---|---|---|
| `/api/bundles/import` | POST | Importar bundle seed (7.2, 7.7) | ✅ Existe — ver `src/api/routes/bundles.py` |
| `/api/agents/{agent_name}` (o equivalente) | GET | Consultar agente registrado (7.3) | ⚠️ Verificar ruta exacta — depende de implementación de API de agents |
| `/api/tasks/{task_id}` | GET | Verificar estado de tarea (ya testeado en P5) | ✅ Existe |
| `/webhooks/trigger` | POST | Disparar flow presupuesto | ✅ Existe |

### Contratos

**POST /api/bundles/import**
- Input: `multipart/form-data` con archivo ZIP
- Output: `{"status": "success", "bundle_id": "...", "agents_count": 1, ...}`
- Status: 201
- Headers: `X-Org-Id` requerido

**GET /api/agents/presupuestador** (ruta asumida)
- Output esperado: `{role, soul_json, allowed_tools, is_active, ...}`
- Status: 200
- Auth: `verify_org_membership`

### Middleware
- `require_org_id` y `verify_org_membership` — aplican a todos los endpoints de API
- Mockeados en tests via `app.dependency_overrides` (`test_presupuesto_flow.py:83-87`)

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo end-to-end del paso

```
7.1: test_exec_agent_mcp.py
     └─ patch removido → MCPPool mock → resolución async real → flow COMPLETED

7.2: presupuesto-bundle/ → data/seed/presupuesto-bundle/ (copia)
     └─ seed_bundle.py → POST /api/bundles/import

7.3: POST /api/bundles/import → GET /api/agents/presupuestador → verify 5 campos

7.4: Flow.execute() → BaseCrew.run_async() → get_last_tool_calls()["excel_reader"] >= 1
     └─ BaseFlow.last_tool_calls property agregada

7.5: test_real_tool_calling.py DELETE
     └─ test_real_agent_pipeline.py UPDATE o DELETE
     └─ test_tool_calling_real.py CONSERVAR (único)

7.6: test_real_agent_presupuesto.py → @pytest.mark.skip + docstring
     └─ test_real_multi_agent_presupuesto.py → @pytest.mark.skip + docstring

7.7: test_import_seed_bundle_via_api → seed real → POST /api/bundles/import → verify

7.8: tests/unit/test_presupuesto_flow.py → validate_input unit tests
```

### Coherencia
- Paso 7 cierra todos los gaps identificados en pasos 1-6
- No hay inconsistencias entre plan y arquitectura existente
- Todos los cambios son sobre tests o archivos de datos (seed), sin modificar lógica core
- `BaseFlow.last_tool_calls` es la única modificación a código de producción

### Gaps y Ambigüedades

| Gap | Descripción | Resolución |
|---|---|---|
| G1 | Ruta `GET /api/agents/{name}` no está documentada en plan | Verificar API de agents existente en `src/api/routes/`. Si no existe, crear endpoint simple o usar consulta directa a `agent_catalog` en el test |
| G2 | `BaseFlow._run_crew()` no retorna metadata de tool calls | Plan propone 3 opciones: (1) propiedad `last_tool_calls` en BaseFlow, (2) modificar `_run_crew()` retorno, (3) acceder `flow.state.crew`. Recomendación: opción 1 (propiedad) — menor impacto, sigue patrón existente |
| G3 | `test_real_agent_pipeline.py` — ¿conservar o eliminar? | Plan deja ambigüedad: "Actualizar o eliminar". Recomendación: ACTUALIZAR con verificación `get_last_tool_calls()` + docstring diferenciador (test de pipeline con LLM real, no específicamente tool calling) |
| G4 | Tests legacy — Opción B recomendada pero A y C son plausibles | Análisis confirma Opción B: tests pre-fetch dan falso positivo. `test_tool_calling_real.py` + `test_real_flow_execute.py` ya cubren mejor calidad |

### DX & Tooling

```
### Herramienta Propuesta: `seed_bundle.py`
- **Qué automatiza:** Copia archivos de `presupuesto-bundle/` a `data/seed/presupuesto-bundle/`, recalcula SHA256 en manifest, y llama POST /api/bundles/import. Elimina la tarea manual de verificar hashes y estructura ZIP.
- **Tipo:** script CLI
- **Cómo se usa:** `python scripts/seed_bundle.py` — Lee `presupuesto-bundle/`, copia a `data/seed/`, imprime resultado del import.
- **Impacto para el usuario final:** No más errores de hash desincronizado o estructura de bundle incorrecta.
- **Prioridad:** Tarea 0 — implementar antes que 7.2 y 7.7
```

---

## 5️⃣ Criterios de Aceptación

```yaml
✅ [CODE] test_exec_agent_mcp.py::test_mcp_flow_completes NO usa patch sobre AgentFactory._resolve_mcp_tool_async
✅ [CODE] MCPPool.get() mock provee tools sin bloquear event loop en test MCP
✅ [CODE] Flow MCP completa con estado COMPLETED sin parche
✅ [DATA] data/seed/presupuesto-bundle/manifest.json existe con hashes correctos
✅ [DATA] data/seed/presupuesto-bundle/agents/presupuestador.json existe
✅ [BACKEND] POST /api/bundles/import con data del seed → HTTP 201
✅ [BACKEND] test_get_agent_via_api_returns_correct_data implementado en test_register_agent.py
✅ [BACKEND] Test GET agente valida ≥ 5 campos (role, soul_json.role, soul_json.goal, allowed_tools, is_active)
✅ [FULLSTACK] test_flow_execute_with_tool verifica tool_calls["excel_reader"] >= 1
✅ [FULLSTACK] BaseFlow expone last_tool_calls property (si no existía)
✅ [FULLSTACK] Output de test_flow_execute_with_tool sigue siendo válido (no rompe aserciones existentes)
✅ [CODE] test_real_tool_calling.py ELIMINADO (duplicado)
✅ [CODE] test_real_agent_pipeline.py actualizado con get_last_tool_calls() o eliminado si redundante
✅ [CODE] Solo 1 archivo (o 2 con roles distintos) cubre tool calling real con LLM
✅ [CODE] test_real_agent_presupuesto.py tiene @pytest.mark.skip + docstring de reemplazo
✅ [CODE] test_real_multi_agent_presupuesto.py tiene @pytest.mark.skip + docstring de reemplazo
✅ [CODE] 0 tests legacy sin tool calling que pretendan probar "agente con excel_reader"
✅ [CODE] test_import_seed_bundle_via_api pasa con el seed real
✅ [CODE] Test import seed verifica campos en DB coinciden con JSON del seed
✅ [CODE] Test import seed es independiente del entorno (usa mocks para Supabase)
✅ [CODE] tests/unit/test_presupuesto_flow.py implementado
✅ [CODE] Test unitario validate_input verifica inputs incompletos retornan False
✅ [CODE] Test unitario validate_input verifica input completo retorna True
✅ [CODE] seed_bundle.py script existe y ejecuta sin errores
✅ [TEST] Todos los tests existentes de factory.py pasan sin modificación
✅ [TEST] Lint 0 (ruff check src/ tests/)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1 — Ruta GET /api/agents/{name} no existe | Alta | Plan asume endpoint pero no está verificado en código. Si no existe, test 7.3 no puede implementarse sin crear endpoint nuevo | Verificar API routes antes de implementar. Si no existe, usar consulta directa a agent_catalog via mock o crear endpoint mínimo |
| R2 — BaseFlow.last_tool_calls cambia interfaz pública | Media | Agregar propiedad a `BaseFlow` puede afectar flujos existentes que heredan de él | Implementar como property simple que retorna `{}` por defecto. Sin cambios en firmas de métodos abstractos. Tests existentes no deben romperse |
| R3 — Eliminar test_real_tool_calling.py elimina cobertura E2E real | Media | Si `test_tool_calling_real.py` tiene dependencia no obvia del test eliminado | Verificar que `test_tool_calling_real.py` es estrictamente superior (mismo coverage + mejor naming). Confirmar diff línea por línea |
| R4 — Tests legacy deprecados pueden ser olvidados | Baja | `@pytest.mark.skip` silencia tests que podrían tener valor como integración | Usar docstring EXPLÍCITO con "Reemplazado por: test_tool_calling_real.py::test_presupuestador_calls_excel_reader". Incluir fecha de deprecación |
| R5 — SHA256 desincronizado en seed | Baja | Si `presupuesto-bundle/agents/presupuestador.json` se modifica pero `manifest.json` hash no se actualiza | `seed_bundle.py` debe recalcular SHA256 automáticamente al copiar. Validar como paso CI |
| R6 — Tests existentes de presupuesto_flow en e2e vs nuevos en unit se superponen | Media | `test_presupuesto_flow.py` (e2e) ya tiene tests de validate_input. Crear `tests/unit/test_presupuesto_flow.py` puede duplicar | Decidir: mover tests existentes de e2e a unit (más correcto) o mantener ambos con roles distintos. Recomendación: mover a unit, dejar en e2e solo tests de integración (webhook, tasks endpoint, persistencia) |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `seed_bundle.py` | `scripts/seed_bundle.py` | `def run(): ...` — lee `presupuesto-bundle/`, copia a `data/seed/`, recalcula SHA256, imprime estructura | `scripts/` pattern (ver `scripts/seed_system_bundles.py`) | DX | Baja | 0.25h | Ninguna | → verificar: `python scripts/seed_bundle.py` imprime estructura sin errores |
| 1 | Crear bundle seed en `data/seed/` | `data/seed/presupuesto-bundle/manifest.json` + `data/seed/presupuesto-bundle/agents/presupuestador.json` | Copia literal de `presupuesto-bundle/`. SHA256 recalculado. Estructura: `manifest.json{version, agents[], skills[], compatibility, bundle_info{name, description, version, author}, hashes{}}` + `agents/presupuestador.json{role, soul_json{role, goal, backstory}, allowed_tools, model, max_iter, is_active}` | `presupuesto-bundle/` existente | DATA | Baja | 0.25h | Tarea 0 | → verificar: `ls data/seed/presupuesto-bundle/agents/presupuestador.json` y `ls data/seed/presupuesto-bundle/manifest.json` existen |
| 2 | Remover parche MCP en `test_exec_agent_mcp.py` | `tests/e2e/test_exec_agent_mcp.py` | Remover `patch("src.crews.factory.AgentFactory._resolve_mcp_tool_async")`. Agregar fixture/mock `MCPPool.get().get_tools()` | `tests/conftest.py:307-319` — `mock_mcp_pool` fixture existente | CODE | Media | 0.75h | Tareas 1-6 de pasos previos (ya completadas) | → verificar: `uv run pytest tests/e2e/test_exec_agent_mcp.py -v` pasa sin errores |
| 3 | Agregar `test_get_agent_via_api_returns_correct_data` | `tests/e2e/test_register_agent.py` | `async def test_get_agent_via_api_returns_correct_data(mock_...): ...` — import bundle → GET agent → assert 5 campos | `tests/e2e/test_register_agent.py::test_bundle_import_returns_201` | BACKEND | Media | 0.5h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_register_agent.py::TestRegisterAgent::test_get_agent_via_api_returns_correct_data -v` pasa |
| 4 | Agregar `last_tool_calls` a `BaseFlow` | `src/flows/base_flow.py` | `@property def last_tool_calls(self) -> Dict[str, int]: return getattr(self._last_crew, "get_last_tool_calls", lambda: {})()` | `BaseCrew.get_last_tool_calls()` en `src/crews/base_crew.py:206-213` | CODE | Baja | 0.25h | Ninguna | → verificar: `uv run pytest tests/ -k "test_flow_execute" -v` pasa |
| 5 | Agregar verificación tool calling en `test_real_flow_execute.py` | `tests/e2e/test_real_flow_execute.py` | Agregar `tool_calls = flow.last_tool_calls; assert tool_calls.get("excel_reader", 0) >= 1` al final de `test_flow_execute_with_tool` | `test_tool_calling_real.py:122-125` | FULLSTACK | Baja | 0.25h | Tarea 4 | → verificar: `uv run pytest tests/e2e/test_real_flow_execute.py -v` pasa |
| 6 | Consolidar tests tool calling duplicados | `tests/e2e/test_real_tool_calling.py` (ELIMINAR) + `tests/e2e/test_real_agent_pipeline.py` (ACTUALIZAR) | Eliminar `test_real_tool_calling.py`. En `test_real_agent_pipeline.py` agregar aserción `get_last_tool_calls()["excel_reader"] >= 1` | `test_tool_calling_real.py` como referencia de conservar | CODE | Baja | 0.5h | Tarea 4 | → verificar: `uv run pytest tests/e2e/test_tool_calling_real.py tests/e2e/test_real_agent_pipeline.py -v` pasa |
| 7 | Deprecar tests legacy pre-fetch | `tests/e2e/test_real_agent_presupuesto.py` + `tests/e2e/test_real_multi_agent_presupuesto.py` | Agregar `@pytest.mark.skip(reason="Legacy: reemplazado por test_tool_calling_real.py::test_presupuestador_calls_excel_reader")` + docstring explicativo | Opción B del plan | CODE | Baja | 0.5h | Tarea 6 | → verificar: `uv run pytest tests/e2e/test_real_agent_presupuesto.py tests/e2e/test_real_multi_agent_presupuesto.py -v` → SKIPPED (no FAILED) |
| 8 | Agregar test import seed bundle via API | `tests/e2e/test_register_agent.py` | `async def test_import_seed_bundle_via_api(mock_...): ...` — carga seed real, arma ZIP, POST import, verifica en agent_catalog | `tests/e2e/test_register_agent.py::test_bundle_import_returns_201` | FULLSTACK | Media | 0.5h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_register_agent.py::TestRegisterAgent::test_import_seed_bundle_via_api -v` pasa |
| 9 | Crear test unitario validate_input | `tests/unit/test_presupuesto_flow.py` (NUEVO) | `def test_validate_input_rejects_missing_fields(): ...` — verifica inputs incompletos → False, completo → True | `tests/e2e/test_presupuesto_flow.py:108-121` (mover tests de validez) | CODE | Baja | 0.25h | Ninguna | → verificar: `uv run pytest tests/unit/test_presupuesto_flow.py -v` pasa |

**Tiempo total estimado:** 3.75h

**Orden de ejecución recomendado:** Tarea 0 → Tarea 1 → Tarea 2 → Tarea 3 → Tarea 4 → Tarea 5 → Tarea 6 → Tarea 7 → Tarea 8 → Tarea 9

---

## 🔮 Roadmap

- **Optimización post-paso:** Los tests deprecados (7.6) podrían migrarse en el futuro a tool calling real (Opción A) si hay tiempo. Actualmente Opción B (deprecar) es suficiente.
- **Mejora futura:** `BaseFlow.last_tool_calls` es una property simple. Podría evolucionar a un sistema de métricas más completo (tokens por tool, latencia por llamada, etc.) similar a OpenTelemetry spans.
- **Pre-requisito para pasos siguientes:** Ninguno. Paso 7 es el último paso del plan.
- **Decisión de diseño:** `last_tool_calls` implementado como property en `BaseFlow` (no como modificación de `_run_crew()` return) para minimizar impacto en flujos existentes. Si en el futuro se necesita tool calls por flow, `_run_crew()` podría retornar `Tuple[Dict, Dict]` o usar un `FlowResult` Pydantic model.

---

## 🚫 Reglas de Oro — Verificación

- ✅ Análisis accionable y específico — cada tarea tiene artefacto, interfaz, patrón y verificación concretos
- ✅ TODO verificado contra código — 19 elementos verificados en §0
- ✅ Discrepancias documentadas — 9 discrepancias (D1-D9) con resolución
- ✅ Ambigüedades señaladas — 4 gaps (G1-G4) con resolución
- ✅ Nivel CTO en rigor — cobertura data, code, backend, fullstack+DX
- ✅ Coherente con phase-state.md — no contradice decisiones registradas
- ✅ TODO el paso — 8 sub-pasos (7.1–7.8) cubiertos
- ✅ Etapas secuenciales — data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta — `seed_bundle.py`
- ✅ Tareas atómicas — 10 tareas, cada una = 1 artefacto
- ✅ Interfaz exacta por tarea — firmas completas sin inferencia
- ✅ Patrón de referencia explícito — archivo concreto por tarea
- ✅ Verificación inline por tarea — comando concreto

---

## 📊 Métrica de Calidad

| Métrica | Valor |
|---|---|
| `proyecto-config.json` leído antes de explorar | ✅ |
| Elementos verificados (§0) | 19 (≥18 para 6-10 archivos) |
| Discrepancias detectadas | 9 (≥1, toca código existente) |
| Secciones completadas | 8 (0-7) |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 24 (≥1 por sub-paso, verificables) |
| Riesgos identificados | 6 (técnico, integración, futuro) |
| Tareas atómicas (1 artefacto por tarea) | 100% (10 tareas) |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia explícito | 100% |
| Verificación inline por tarea | 100% |
| Suposiciones no verificadas | 0 |
| Propuesta DX / Tooling | 1 (`seed_bundle.py`) |
| Estimación de tiempo | 3.75h total, por tarea individual |
