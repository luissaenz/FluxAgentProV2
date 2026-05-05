# analisis-paso7-y (ultra)

## 0️⃣ Verificación Código

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `test_exec_agent_mcp.py` patch `_resolve_mcp_tool_async` | grep line 63-67 | ✅ | file:62-67 |
| 2 | `data/seed/` existe | glob `data/seed/**/*` | ❌ | no files |
| 3 | `test_register_agent.py` GET agent test | grep file | ❌ | no test |
| 4 | `test_real_flow_execute.py` tool_calls check | grep file | ❌ | no assert |
| 5 | `test_real_tool_calling.py` duplicado | existencia | ✅ | 129 lines |
| 6 | `test_real_agent_presupuesto.py` existe | read | ✅ | 183 lines |
| 7 | `test_presupuesto_flow.py` unit test | glob | ❌ | file not found |
| 8 | `PresupuestoFlow.validate_input()` existe | read `presupuesto_flow.py:37` | ✅ | file:37-39 |
| 9 | `resolve_tools_async()` existe | read `factory.py:190` | ✅ | file:190-230 |

**Discrepancias:**
1. Patch `_resolve_mcp_tool_async` presente (plan exige remover) → remover + mock `MCPPool.get()`
2. `data/seed/` no existe → crear + copiar bundle
3. Test GET agente no existe → crear en `test_register_agent.py`
4. Test tool_calls no existe en `test_real_flow_execute.py` → agregar
5. `test_real_tool_calling.py` duplicado → eliminar
6. Legacy tests no deprecados → marcar skip + docstring
7. Test seed import no existe → crear en `test_register_agent.py`
8. Unit test `validate_input` no existe → crear `tests/unit/test_presupuesto_flow.py`

---

## 1️⃣ Análisis Datos
- 0 DB changes. Paso 7 no toca schema/migrations. ✅

---

## 2️⃣ Análisis Código

### 7.1 Remover parche MCP
- Archivo: `tests/e2e/test_exec_agent_mcp.py`
- Acción: eliminar líneas 62-67 (patch `_resolve_mcp_tool_async`)
- Agregar: fixture mock `MCPPool.get().get_tools()` → retorna tools controlados
- Patrón: `test_tool_calling_real.py` mock `get_service_client` (líneas 101-103)
- Firma: `MCPPool.get_tools(org_id, server) → list[Tool]`

### 7.2 Crear seed bundle
- Ruta: `data/seed/presupuesto-bundle/`
- Acción: crear dir, copiar `presupuesto-bundle/manifest.json` + `agents/presupuestador.json`
- Verificar hashes SHA256 en manifest.json
- Script opcional: `scripts/seed_bundle.py` → llama `POST /api/bundles/import`

### 7.3 Test GET agente API
- Archivo: `tests/e2e/test_register_agent.py`
- Nuevo test: `test_get_agent_via_api_returns_correct_data`
- Pasos: import bundle → GET `/api/agents/presupuestador` → validar 5+ campos
- Patrón: `test_bundle_import_returns_201` (líneas 68-89)

### 7.4 Tool calling check en Flow.execute
- Archivo: `tests/e2e/test_real_flow_execute.py`
- Agregar: `flow.get_last_tool_calls()["excel_reader"] >= 1`
- Referencia: `test_tool_calling_real.py:122-125` (`crew.get_last_tool_calls()`)
- Si `BaseFlow` no expone → agregar propiedad `last_tool_calls` que delegue a `BaseCrew`

### 7.5 Consolidar tests duplicados
- Mantener: `test_tool_calling_real.py` (136 lines, más completo)
- Eliminar: `test_real_tool_calling.py` (129 lines, duplicado)
- `test_real_agent_pipeline.py` → actualizar con `get_last_tool_calls()` o eliminar

### 7.6 Deprecar legacy tests
- Archivos: `test_real_agent_presupuesto.py`, `test_real_multi_agent_presupuesto.py`
- Acción: agregar `@pytest.mark.skip(reason="Legacy: reemplazado por test_tool_calling_real.py")` + docstring
- Opción B (recomendada, 0.5h) → phase-state.md línea 309

### 7.7 Verificación seed import
- Archivo: `tests/e2e/test_register_agent.py`
- Nuevo test: `test_import_seed_bundle_via_api`
- Pasos: cargar seed manifest → armar ZIP → POST `/api/bundles/import` → validar agente
- Patrón: `test_bundle_import_returns_201`

### 7.8 Unit test validate_input
- Archivo nuevo: `tests/unit/test_presupuesto_flow.py`
- Tests: `test_validate_input_rejects_missing_fields`, `test_validate_input_accepts_complete`
- Validar: `PresupuestoFlow.validate_input(input) → bool`

---

## 3️⃣ Análisis Backend

- Endpoint GET `/api/agents/{role}` → verificar existe en `src/api/routes/` (glob `src/api/routes/*agent*` → check)
- `BaseFlow.last_tool_calls` → si no existe, agregar en `src/flows/base_flow.py`:
  ```python
  @property
  def last_tool_calls(self) -> dict:
      return self.state.crew.get_last_tool_calls() if self.state.crew else {}
  ```
- `FlowRegistry` → `PresupuestoFlow` ya registrado `@register_flow("presupuesto")` ✅

---

## 4️⃣ Fullstack + DX

### Flujo End-to-End
`data/seed/` → `POST /api/bundles/import` → `agent_catalog` → `GET /api/agents/presupuestador` → `Flow.execute()` → `excel_reader` tool → output JSON ✅

### DX & Tooling
**Herramienta Propuesta: `fap seed-import`**
- **Qué automatiza:** Importación de seed bundles sin crear ZIP manual
- **Tipo:** CLI command (Typer)
- **Cómo se usa:** `fap seed-import --bundle data/seed/presupuesto-bundle/`
- **Impacto:** Elimina paso manual de empaquetado ZIP para tests E2E
- **Prioridad:** Tarea 0

---

## 5️⃣ Criterios Aceptación

- [ ] 7.1: Test `test_exec_agent_mcp.py` sin parche `_resolve_mcp_tool_async`
- [ ] 7.1: Mock `MCPPool.get()` provee tools sin bloquear event loop
- [ ] 7.1: Flow completa con estado `COMPLETED`
- [ ] 7.2: `data/seed/presupuesto-bundle/manifest.json` existe con hashes correctos
- [ ] 7.2: `data/seed/presupuesto-bundle/agents/presupuestador.json` existe
- [ ] 7.3: Test `test_get_agent_via_api` valida 5+ campos
- [ ] 7.4: `test_real_flow_execute.py` verifica `excel_reader` ≥ 1 llamada
- [ ] 7.5: Solo 1 test tool calling real (`test_tool_calling_real.py`)
- [ ] 7.6: Legacy tests tienen `@pytest.mark.skip` + docstring
- [ ] 7.7: Test `test_import_seed_bundle_via_api` pasa con seed real
- [ ] 7.8: Unit test `validate_input` rechaza inputs incompletos

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| 7.1: Remover parche sin mock MCPPool → test falla | Alta | MCPPool real no disponible en test | Agregar fixture mock `MCPPool.get().get_tools()` |
| 7.2: Hashes incorrectos en manifest → import falla | Media | Copia de archivos altera hash | Calcular SHA256 real post-copia |
| 7.5: Eliminar `test_real_tool_calling.py` rompe refs | Baja | CI referencia archivo | Buscar imports/refs antes de eliminar |
| 7.6: Legacy tests deprecados ocultan regresiones | Media | No hay cobertura tool calling pre-load | `test_tool_calling_real.py` cubre escenario |

---

## 7️⃣ Plan Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX:** `fap seed-import` | `src/cli/commands/seed_import.py` | `def run(bundle_dir: Path)` | `src/cli/commands/check_env.py` | DX | Media | 0.5h | Ninguna | → `fap seed-import --help` ejecuta sin errores |
| 1 | 7.1: Remover parche MCP + mock | `tests/e2e/test_exec_agent_mcp.py` | Eliminar líneas 62-67, agregar mock `MCPPool.get()` | `test_tool_calling_real.py` mock `get_service_client` | CODE | Media | 0.75h | Tarea 0 | → `pytest tests/e2e/test_exec_agent_mcp.py -v` pasa |
| 2 | 7.2: Crear seed bundle | `data/seed/presupuesto-bundle/` | `manifest.json` + `agents/presupuestador.json` copiados, hashes SHA256 correctos | `presupuesto-bundle/` (existente) | DATA | Baja | 0.25h | Tarea 0 | → `cat data/seed/presupuesto-bundle/manifest.json` existe |
| 3 | 7.3: Test GET agente API | `tests/e2e/test_register_agent.py` | `async def test_get_agent_via_api_returns_correct_data(mock_...)` | `test_bundle_import_returns_201` | BACKEND | Media | 0.5h | Tarea 2 | → `pytest tests/e2e/test_register_agent.py::test_get_agent_via_api -v` pasa |
| 4 | 7.4: Tool calling check Flow.execute | `tests/e2e/test_real_flow_execute.py` | Agregar `assert flow.get_last_tool_calls()["excel_reader"] >= 1` | `test_tool_calling_real.py:122-125` | BACKEND | Media | 0.5h | Tarea 4 | → `pytest tests/e2e/test_real_flow_execute.py -v` pasa |
| 5 | 7.5: Consolidar tests tool calling | `tests/e2e/test_real_tool_calling.py` | Eliminar archivo | `test_tool_calling_real.py` (conservar) | CODE | Baja | 0.5h | Ninguna | → `ls tests/e2e/` no contiene `test_real_tool_calling.py` |
| 6 | 7.6: Deprecar legacy tests | `tests/e2e/test_real_agent_presupuesto.py`, `test_real_multi_agent_presupuesto.py` | Agregar `@pytest.mark.skip` + docstring | `test_exec_agent_mcp.py` pytestmark | CODE | Baja | 0.5h | Ninguna | → `pytest tests/e2e/test_real_agent_presupuesto.py -v` SKIPPED |
| 7 | 7.7: Test seed import | `tests/e2e/test_register_agent.py` | `async def test_import_seed_bundle_via_api(mock_...)` | `test_bundle_import_returns_201` | BACKEND | Media | 0.5h | Tarea 2 | → `pytest tests/e2e/test_register_agent.py::test_import_seed_bundle -v` pasa |
| 8 | 7.8: Unit test validate_input | `tests/unit/test_presupuesto_flow.py` | `async def test_validate_input_rejects_missing_fields()` | `tests/unit/test_factory.py` | CODE | Baja | 0.25h | Ninguna | → `pytest tests/unit/test_presupuesto_flow.py -v` pasa |

**Tiempo total estimado:** 3.75h (align with plan.md línea 389)

---

## 🔮 Roadmap
- Optimizar `fap seed-import` para aceptar múltiples bundles
- Agregar CI check para hashes de seed bundles
- Migrar legacy tests a tool calling real (opción A) si se requiere cobertura
