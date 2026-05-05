# analisis-FINAL — Paso 7: Cierre — Remanentes y Pulido para Cobertura Total

**Fuentes:** ds | Y | mm | kilo
**Paso:** 7 (8 sub-pasos: 7.1–7.8)
**Agente unificador:** ds

---

## 0️⃣ Evaluacion de Analisis y Verificaciones

### Tabla de Evaluacion de Agentes

| Agente | Verifico codigo | Discrepancias detectadas | Propuesta DX | Evidencia solida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **ds** | ✅ 18 elementos | 9 (D1-D9) | `seed_bundle.py` | ✅ Archivos+lineas exactos | **4.8** |
| **Y** | ✅ 9 elementos | 8 | `fap seed-import` CLI | ✅ Conciso pero preciso | **3.8** |
| **mm** | ✅ 12 elementos | 4 | `test_seed_import.py` script | ✅ Firmas explicitas | **4.0** |
| **kilo** | ✅ 18 elementos | 4 | `validate_seed_bundle.py` | ✅ Exploracion + API routes | **4.2** |

### Discrepancias Criticas Consolidadas

| # | Discrepancia | Detecto | Verificada contra codigo | Resolucion |
|---|---|---|---|---|
| 1 | Patch `_resolve_mcp_tool_async` en test_exec_agent_mcp.py (lines 62-67) | ds, Y, mm, kilo | ✅ `tests/e2e/test_exec_agent_mcp.py:62-67` | Remover patch + mock `MCPPool.get().get_tools()` fixture |
| 2 | `data/seed/` no existe — plan requiere bundle seed | ds, Y, mm, kilo | ✅ glob `data/seed/**` → vacio | Crear `data/seed/presupuesto-bundle/` con copia + SHA256 recalculado |
| 3 | `test_get_agent_via_api_returns_correct_data` no existe | ds, Y, mm, kilo | ✅ grep `test_register_agent.py` → solo POST tests | Agregar test GET agente con validacion 5+ campos |
| 4 | `test_real_flow_execute.py` no verifica tool calling real | ds, Y, mm, kilo | ✅ grep `get_last_tool_calls` → ausente | Agregar `flow.last_tool_calls.get("excel_reader", 0) >= 1` |
| 5 | `BaseFlow` no expone crew interno para inspeccion | ds, Y, mm, kilo | ✅ grep `src/flows/base_flow.py` → no property | Agregar `BaseFlow.last_tool_calls` property |
| 6 | `test_real_tool_calling.py` duplicado de `test_tool_calling_real.py` | ds, Y, mm, kilo | ✅ diff ambos → mismo patron | Eliminar `test_real_tool_calling.py`, conservar `test_tool_calling_real.py` |
| 7 | `test_real_agent_pipeline.py` similar sin verificacion tool calling | ds, Y, mm, kilo | ✅ grep `get_last_tool_calls` → ausente | Actualizar con asercion tool calling o eliminar |
| 8 | `test_real_agent_presupuesto.py` + `multi_agent` usan pre-fetch data | ds, Y, mm, kilo | ✅ lineas 45-49 usan `ExcelReaderTool._run()` directo | Deprecar con `@pytest.mark.skip` + docstring (Opcion B) |
| 9 | `tests/unit/test_presupuesto_flow.py` no existe | ds, Y, mm, kilo | ✅ glob `tests/unit/` → ausente | Crear test unitario `validate_input()` |
| 10 | Tests validate_input existen en e2e pero no en unit | ds | ✅ `test_presupuesto_flow.py:108-121` | Mover tests de validacion de e2e a unit; mantener en e2e solo integracion |
| 11 | SHA256 en manifest debe verificar post-copia | kilo | ✅ calculado coincide con manifest | `seed_bundle.py` debe recalcular SHA256 automaticamente |
| 12 | GET `/api/agents/{role}` ruta exacta no verificada | ds, kilo | ⚠️ kilo confirmo GET `/api/agents/{id}` en `agents.py` | Usar ruta GET `/api/agents/{role}` si existe, sino mockear consulta directa a `agent_catalog` en el test |

---

## 1️⃣ Resumen Ejecutivo

Paso 7 cierra 8 remanentes de pasos 1-6: remover parche MCP en test (7.1), crear bundle seed (7.2), test GET agente API (7.3), verificar tool calling en Flow.execute (7.4), consolidar tests tool calling duplicados (7.5), deprecar tests legacy pre-fetch (7.6), test import seed real (7.7), test unitario validate_input (7.8).

**Correcciones criticas al plan:**
- Plan no menciona que `BaseFlow` necesita exponer `last_tool_calls` para 7.4. Agregar property.
- Plan asume `GET /api/agents/{name}` sin verificar. Ruta real puede diferir.
- Tests de validate_input ya existen en e2e (`test_presupuesto_flow.py:108-121`) pero no en unit. Mover a unit.

**Herramienta DX seleccionada (fusionada):** `scripts/seed_bundle.py` — copia bundle a `data/seed/`, recalcula SHA256, importa via API. Fusiona `seed_bundle.py` (ds) + validacion de `validate_seed_bundle.py` (kilo). Rechazada propuesta `fap seed-import` (Y) por ser CLI command que requiere registro en `cli/main.py` = mas overhead del necesario.

---

## 2️⃣ Diseno Funcional Consolidado

### Happy Path

```
1. seed_bundle.py → lee presupuesto-bundle/ → copia a data/seed/presupuesto-bundle/ → recalcula SHA256 → imprime estructura
2. POST /api/bundles/import con ZIP de data/seed/presupuesto-bundle/ → HTTP 201 + agents_count:1
3. GET /api/agents/presupuestador → 200 + {role, soul_json, allowed_tools, is_active, ...}
4. Flow.execute() con LLM real → BaseCrew.run_async() → excel_reader tool llamada ≥1 vez → COMPLETED
5. test_exec_agent_mcp.py sin parche → MCPPool.get_tools() real → flow COMPLETED
```

### Edge Cases MVP

| ID | Caso | Descripcion |
|---|---|---|
| EC1 | MCPPool devuelve tools vacio | Mock retorna lista vacia → flow no deadlock, warning log |
| EC2 | Bundle seed SHA256 mismatch | `seed_bundle.py` falla con error claro antes de copiar |
| EC3 | POST bundle import con ZIP corrupto | API retorna 400, no 500 |
| EC4 | GET agente que no existe | API retorna 404, no crash |
| EC5 | Flow.execute() sin GROQ_API_KEY | Test skip con `@pytest.mark.skipif` |
| EC6 | validate_input con campos extra | `duracion_horas` y `menu` presentes → `_run_crew()` los usa con defaults robustos |

---

## 3️⃣ Diseno Tecnico Definitivo

### Componentes y Modificaciones

#### 7.1 — Remover parche MCP en test E2E

| Atributo | Valor |
|---|---|
| **Ruta real** | `tests/e2e/test_exec_agent_mcp.py` |
| **Tipo de cambio** | Modificacion |
| **Descripcion** | Remover `patch("src.crews.factory.AgentFactory._resolve_mcp_tool_async")` (lines 62-67). Agregar fixture async mock `MCPPool.get().get_tools()` que retorne tools controlados (o lista vacia) |
| **Interfaz** | `MCPPool.get_tools(org_id: str, server: str) → list[Tool]` |
| **Patron** | `tests/conftest.py:307-319` — `mock_mcp_pool` fixture existente |

#### 7.2 — Bundle seed en `data/seed/`

| Atributo | Valor |
|---|---|
| **Ruta real** | `data/seed/presupuesto-bundle/` |
| **Tipo de cambio** | Creacion |
| **Descripcion** | Copiar `presupuesto-bundle/manifest.json` + `presupuesto-bundle/agents/presupuestador.json`. Recalcular SHA256. Verificar hashes |
| **Hashes** | `agents/presupuestador.json` SHA256 = `8bdc4257879bd9c362819bcafff163a0d54ded2d1f6f9b20d4598d188ec5524a` (verificado ✅) |
| **Patron** | `presupuesto-bundle/` existente |

#### 7.3 — Test GET agente via API

| Atributo | Valor |
|---|---|
| **Ruta real** | `tests/e2e/test_register_agent.py` |
| **Tipo de cambio** | Modificacion (nuevo test) |
| **Descripcion** | Agregar `test_get_agent_via_api_returns_correct_data`. Import bundle → GET `/api/agents/presupuestador` → validar ≥5 campos |
| **Interfaz** | `def test_get_agent_via_api_returns_correct_data(api_client, mock_tenant_client)` |
| **Campos a validar** | `role == "presupuestador"`, `soul_json.role == "Cotizador de Eventos"`, `soul_json.goal` incluye "excel_reader", `allowed_tools == ["excel_reader"]`, `is_active == True` |
| **Patron** | `test_register_agent.py::test_bundle_import_returns_201` |

#### 7.4 — Tool calling check en Flow.execute + BaseFlow.last_tool_calls

| Atributo | Valor |
|---|---|
| **Ruta real** | `src/flows/base_flow.py` + `tests/e2e/test_real_flow_execute.py` |
| **Tipo de cambio** | Modificacion (property + assertion) |
| **Descripcion** | Agregar `BaseFlow.last_tool_calls` property que delegue al BaseCrew interno. Agregar assertion en test |
| **Interfaz** | `@property def last_tool_calls(self) -> Dict[str, int]` |
| **Implementacion** | `return getattr(self, '_last_crew', None).get_last_tool_calls() if hasattr(self, '_last_crew') else {}` |
| **Assertion en test** | `tool_calls = flow.last_tool_calls; assert tool_calls.get("excel_reader", 0) >= 1` |
| **Patron** | `BaseCrew.get_last_tool_calls()` en `src/crews/base_crew.py:206-213` |

#### 7.5 — Consolidar tests tool calling duplicados

| Accion | Archivo | Razon |
|---|---|---|
| **CONSERVAR** | `tests/e2e/test_tool_calling_real.py` | Mejor nombre, mas completo, sin patches CrewAI |
| **ELIMINAR** | `tests/e2e/test_real_tool_calling.py` | Duplicado exacto (variaciones minimas de tildes) |
| **ACTUALIZAR** | `tests/e2e/test_real_agent_pipeline.py` | Agregar `get_last_tool_calls()["excel_reader"] >= 1` + docstring diferenciador (test de pipeline completo, no solo tool calling) |

#### 7.6 — Deprecar tests legacy pre-fetch

| Archivo | Accion |
|---|---|
| `tests/e2e/test_real_agent_presupuesto.py` | Agregar `@pytest.mark.skip(reason="Legacy: reemplazado por test_tool_calling_real.py::test_presupuestador_calls_excel_reader")` + docstring |
| `tests/e2e/test_real_multi_agent_presupuesto.py` | Agregar `@pytest.mark.skip(reason="Legacy: reemplazado por test_tool_calling_real.py::test_presupuestador_calls_excel_reader")` + docstring |

#### 7.7 — Test import seed bundle via API

| Atributo | Valor |
|---|---|
| **Ruta real** | `tests/e2e/test_register_agent.py` |
| **Tipo de cambio** | Modificacion (nuevo test) |
| **Descripcion** | `test_import_seed_bundle_via_api`. Cargar `data/seed/presupuesto-bundle/`, armar ZIP en memoria, POST `/api/bundles/import`, verificar agente en `agent_catalog` |
| **Patron** | `test_register_agent.py::test_bundle_import_returns_201` |

#### 7.8 — Test unitario validate_input

| Atributo | Valor |
|---|---|
| **Ruta real** | `tests/unit/test_presupuesto_flow.py` (NUEVO) |
| **Tipo de cambio** | Creacion |
| **Descripcion** | Test unitario puro de `PresupuestoFlow.validate_input()`. Sin mocks DB. |
| **Interfaz** | `def test_validate_input_rejects_missing_fields():` + `def test_validate_input_accepts_complete():` |
| **Cobertura** | Inputs incompletos (`{}`, `{"tipo_evento": "boda"}`, `{"tipo_evento": "boda", "pax": 100}`) → `False`. Input completo (4 campos) → `True` |
| **Patron** | `tests/unit/test_factory.py` |

### DX & Tooling — Tarea 0

```
### Herramienta: seed_bundle.py
- **Que automatiza:** Copia `presupuesto-bundle/` a `data/seed/presupuesto-bundle/`, recalcula SHA256 en manifest.json, verifica integridad, imprime estructura lista para import. Fusion de seed_bundle.py (ds) + validate_seed_bundle.py (kilo).
- **Tipo:** Script Python standalone
- **Ubicacion:** `scripts/seed_bundle.py`
- **Como se usa:** `python scripts/seed_bundle.py`
- **Impacto para el usuario final:** Elimina 3 pasos manuales: (1) copiar archivos, (2) calcular SHA256, (3) verificar integridad. Previene errores de hash desincronizado.
- **El implementador DEBE usarla** para completar las tareas 7.2 y 7.7 del paso.
```

---

## 4️⃣ Decisiones Tecnologicas

1. **`BaseFlow.last_tool_calls` como property:** Se agrega property simple en `BaseFlow` que retorna `{}` por defecto. No modifica metodo abstracto `_run_crew()`. Minimo impacto en flujos existentes. Decision unanime entre ds, mm, Y.
2. **`seed_bundle.py` sobre `fap seed-import`:** Script standalone > CLI command. Menos overhead de registro en `cli/main.py`. Suficiente para una operacion unica. DS propuso, kilo complemento con validacion.
3. **Opcion B para tests legacy (deprecar):** Unanime entre los 4 agentes. Tests legacy dan falso positivo de tool calling. `test_tool_calling_real.py` ya cubre el escenario con mejor calidad.
4. **Eliminar `test_real_tool_calling.py`, NO eliminar `test_real_agent_pipeline.py`:** `test_real_agent_pipeline.py` prueba pipeline completo con LLM real (no solo tool calling). Agregar verificacion tool calling + docstring diferenciador. DS y Y recomiendan actualizar; mm recomienda eliminar. Se adopta actualizar (mayor cobertura).
5. **Ruta GET `/api/agents/{role}`:** Kilo confirmo ruta existe en `src/api/routes/agents.py`. Si la ruta exacta difiere (`{id}` vs `{role}`), el test debe ajustarse. Gap documentado en D12.
6. **Mover tests validate_input de e2e a unit:** Tests de validacion pura (`validate_input` sin DB) pertenecen a `tests/unit/`. E2e debe conservar solo tests de integracion (webhook, tasks endpoint, persistencia).

### Correcciones al plan

- ⚠️ Plan dice agregar test a `tests/e2e/test_real_flow_execute.py` pero no menciona que `BaseFlow` necesita exponer crew para tool calls. Correccion: agregar `BaseFlow.last_tool_calls` property.
- ⚠️ Plan asume `GET /api/agents/{name}` existe sin verificacion. Codigo real puede tener ruta `GET /api/agents/{id}`. Test debe ajustarse.
- ⚠️ Plan propone crear `tests/unit/test_presupuesto_flow.py` pero `tests/e2e/test_presupuesto_flow.py` ya tiene tests de validate_input. Corregir: mover a unit, no duplicar.
- ⚠️ Plan no menciona `seed_bundle.py` como tooling. Agregado como Tarea 0.

---

## 5️⃣ Criterios de Aceptacion MVP

### Funcionales

- [ ] ✅ [CODE] `test_exec_agent_mcp.py::test_mcp_flow_completes` no usa patch sobre `AgentFactory._resolve_mcp_tool_async`
- [ ] ✅ [CODE] Mock `MCPPool.get()` provee tools sin bloquear event loop
- [ ] ✅ [CODE] Flow MCP completa con estado COMPLETED sin parche
- [ ] ✅ [DATA] `data/seed/presupuesto-bundle/manifest.json` existe con hashes correctos
- [ ] ✅ [DATA] `data/seed/presupuesto-bundle/agents/presupuestador.json` existe
- [ ] ✅ [BACKEND] POST `/api/bundles/import` con data del seed → HTTP 201
- [ ] ✅ [BACKEND] `test_get_agent_via_api_returns_correct_data` implementado en `test_register_agent.py`
- [ ] ✅ [BACKEND] Test GET agente valida ≥5 campos (`role`, `soul_json.role`, `soul_json.goal` incluye "excel_reader", `allowed_tools == ["excel_reader"]`, `is_active == True`)
- [ ] ✅ [FULLSTACK] `test_flow_execute_with_tool` verifica `tool_calls["excel_reader"] >= 1`
- [ ] ✅ [FULLSTACK] `BaseFlow` expone `last_tool_calls` property
- [ ] ✅ [FULLSTACK] Output de `test_flow_execute_with_tool` sigue siendo valido (no rompe aserciones existentes)
- [ ] ✅ [CODE] `test_real_tool_calling.py` ELIMINADO (duplicado)
- [ ] ✅ [CODE] `test_real_agent_pipeline.py` actualizado con `get_last_tool_calls()` + docstring diferenciador
- [ ] ✅ [CODE] Solo 1 archivo (`test_tool_calling_real.py`) cubre tool calling real con LLM
- [ ] ✅ [CODE] `test_real_agent_presupuesto.py` tiene `@pytest.mark.skip` + docstring de reemplazo
- [ ] ✅ [CODE] `test_real_multi_agent_presupuesto.py` tiene `@pytest.mark.skip` + docstring de reemplazo
- [ ] ✅ [CODE] 0 tests legacy sin tool calling que pretendan probar "agente con excel_reader"
- [ ] ✅ [CODE] `test_import_seed_bundle_via_api` pasa con el seed real
- [ ] ✅ [CODE] Test import seed verifica campos en DB coinciden con JSON del seed
- [ ] ✅ [CODE] Test import seed independiente del entorno (usa mocks para Supabase)
- [ ] ✅ [CODE] `tests/unit/test_presupuesto_flow.py` implementado
- [ ] ✅ [CODE] Test unitario validate_input verifica inputs incompletos retornan `False`
- [ ] ✅ [CODE] Test unitario validate_input verifica input completo retorna `True`

### Tecnicos

- [ ] ✅ [DX] `seed_bundle.py` ejecuta sin errores y reduce paso manual de copia + hash + import
- [ ] ✅ [TEST] Todos los tests existentes de `test_factory.py` pasan sin modificacion
- [ ] ✅ [TEST] Todos los tests existentes de `test_presupuesto_flow.py` pasan (sin romper aserciones existentes)
- [ ] ✅ [LINT] `ruff check src/ tests/` → 0 errores
- [ ] ✅ [COVERAGE] Tests unitarios nuevos no reducen coverage actual

---

## 6️⃣ Plan de Implementacion

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `seed_bundle.py` | Baja | 0.25h | Ninguna |
| 1 | 7.2: Crear `data/seed/presupuesto-bundle/` + copiar archivos + SHA256 | Baja | 0.25h | Tarea 0 |
| 2 | 7.1: Remover parche MCP + fixture mock MCPPool | Media | 0.75h | Pasos previos |
| 3 | 7.3: `test_get_agent_via_api_returns_correct_data` en test_register_agent.py | Media | 0.5h | Tarea 1 |
| 4 | 7.4: `BaseFlow.last_tool_calls` property en base_flow.py | Baja | 0.25h | Ninguna |
| 5 | 7.4: Verificacion tool calling en test_real_flow_execute.py | Baja | 0.25h | Tarea 4 |
| 6 | 7.5: Eliminar `test_real_tool_calling.py` + actualizar `test_real_agent_pipeline.py` | Baja | 0.5h | Ninguna |
| 7 | 7.6: Deprecar tests legacy (`@pytest.mark.skip` + docstring) | Baja | 0.5h | Tarea 6 |
| 8 | 7.7: `test_import_seed_bundle_via_api` en test_register_agent.py | Media | 0.5h | Tarea 1 |
| 9 | 7.8: `tests/unit/test_presupuesto_flow.py` (test unitario validate_input) | Baja | 0.25h | Ninguna |
| **TOTAL** | | | **3.75h** | |

**Orden de ejecucion:** 0 → 1 → 8 → 3 → 2 → 4 → 5 → 6 → 7 → 9

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigacion |
|---|---|---|---|
| R1 — GET `/api/agents/{role}` no existe como endpoint publico | Alta | Plan asume ruta sin verificar. Kilo confirmo `agents.py` existe pero ruta exacta puede diferir (`{id}` vs `{role}`) | Verificar ruta exacta en `src/api/routes/agents.py`. Si no existe endpoint publico, testear mockeando `agent_catalog` directamente |
| R2 — `BaseFlow.last_tool_calls` property rompe flujos existentes | Media | Flujos que heredan de `BaseFlow` podrian tener colisiones de nombre `_last_crew` | Usar nombre interno `_flow_last_crew` o `getattr(self, '_last_crew', None)` para evitar colisiones. Tests existentes validan no regression |
| R3 — Eliminar `test_real_tool_calling.py` sin verificar referencias externas | Baja | CI o scripts de test podrian referenciar el archivo | `grep -r "test_real_tool_calling" tests/` antes de eliminar. Solo debe existir en pytest discovery implicito |
| R4 — Tests legacy deprecados pueden esconder regresiones reales | Media | `@pytest.mark.skip` silencia tests que prueban flujo con datos reales | Docstring debe incluir archivo de reemplazo exacto + fecha de deprecacion. Considerar Opcion C (renombrar a `test_legacy_*`) como alternativa si se requiere cobertura de regression |
| R5 — SHA256 desincronizado en seed | Baja | Copia manual sin recalcular hash → `POST /api/bundles/import` falla con 400 | `seed_bundle.py` debe recalcular SHA256 automaticamente. Validacion CI opcional |
| R6 — Tests validate_input duplicados entre e2e y unit | Baja | `test_presupuesto_flow.py` (e2e) ya tiene validate_input tests. Crear `tests/unit/test_presupuesto_flow.py` duplica | Mover tests de validacion de e2e a unit. E2e conserva solo tests de integracion (webhook, tasks, persistencia) |

---

## 8️⃣ Testing Minimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | seed_bundle.py ejecuta sin errores | `python scripts/seed_bundle.py` | Exit 0 + "Bundle seed creado en data/seed/presupuesto-bundle/" |
| TP-2 | POST bundle import con seed real | ZIP from `data/seed/presupuesto-bundle/` | HTTP 201 + `agents_count: 1` |
| TP-3 | GET agente presupuestador despues de import | `GET /api/agents/presupuestador` con `X-Org-Id` | HTTP 200 + `role == "presupuestador"`, `allowed_tools == ["excel_reader"]`, `is_active == true` |
| TP-4 | Flow.execute con MCP sin parche | `MCPAgentFlow.execute({"path": "/tmp"})` | `state.status == "completed"`, sin deadlock |
| TP-5 | Flow.execute con tool calling verificado | `RealFlow.execute({"evento": "Boda", "pax": 100})` | `flow.last_tool_calls["excel_reader"] >= 1` |
| TP-6 | validate_input con campos incompletos | `{"tipo_evento": "boda"}` | `False` |
| TP-7 | validate_input con campos completos | `{"tipo_evento": "boda", "pax": 100, "fecha": "2026-03-15", "provincia": "Tucuman"}` | `True` |
| TP-8 | Tests legacy deprecados (no fallan, solo skip) | `pytest tests/e2e/test_real_agent_presupuesto.py -v` | `SKIPPED` (no `FAILED`) |
| TP-9 | Lint 0 post-cambios | `ruff check src/ tests/` | 0 errores |

**Comandos para ejecutar tests:**
- Unitarios: `uv run pytest tests/unit/ -v --timeout=60`
- E2E: `uv run pytest tests/e2e/ -v --timeout=60`
- Lint: `uv run ruff check src/ tests/`
- Suite completa P7: `uv run pytest tests/e2e/test_exec_agent_mcp.py tests/e2e/test_register_agent.py tests/e2e/test_real_flow_execute.py tests/unit/test_presupuesto_flow.py -v`
