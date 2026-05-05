# Análisis — Paso 7: Cierre — Remanentes y Pulido para Cobertura Total

**Agente:** mm
**Paso:** 7 (8 sub-pasos: 7.1–7.8)
**Fecha:** 2026-05-04

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `test_exec_agent_mcp.py` tiene parche `_resolve_mcp_tool_async` | grep líneas 62-67 | ✅ | `tests/e2e/test_exec_agent_mcp.py:63-67` |
| 2 | `_resolve_mcp_tool_async` existe en factory | grep en crews/factory.py | ✅ | Existe, línea ~180 |
| 3 | Directorio `data/seed/` existe | glob | ❌ | No existe |
| 4 | `presupuesto-bundle/` existe | ls | ✅ | `presupuesto-bundle/manifest.json` + `agents/presupuestador.json` |
| 5 | `test_register_agent.py` tiene test GET agente | read | ❌ | Solo POST, no GET |
| 6 | `BaseCrew.get_last_tool_calls()` existe | grep | ✅ | `src/crews/base_crew.py:206` |
| 7 | `BaseFlow` expone `last_tool_calls` | read base_flow.py | ❌ | NO existe |
| 8 | `test_real_flow_execute.py` verifica tool calls | read | ❌ | NO verifica, solo output |
| 9 | `test_tool_calling_real.py` vs `test_real_tool_calling.py` | read ambos | ✅ | Duplicados, mismo propósito |
| 10 | `test_real_agent_presupuesto.py` usa pre-fetch | read líneas 45-49 | ✅ | Llama `tool._run()` directamente |
| 11 | `PresupuestoFlow.validate_input()` | read | ✅ | Verifica 4 campos (línea 38) |
| 12 | Test unitario `validate_input()` | glob tests/unit | ❌ | NO existe |

**Discrepancias encontradas:**

1. **7.3**: Test GET /api/agents/{role} NO existe en test_register_agent.py — solo hay POST bundle import
2. **7.4**: BaseFlow NO expone `last_tool_calls` — el test actual no puede verificar tool calling
3. **7.7**: No hay test que importe bundle desde `data/seed/` — el test actual crea bundle en memoria
4. **7.8**: No existe test unitario para `PresupuestoFlow.validate_input()`

---

## 1️⃣ Análisis de Datos

### Schema

| Sub-paso | Entidad | Cambio |
|----------|---------|--------|
| 7.2 | `data/seed/presupuesto-bundle/` | Crear directorio + copiar bundle existente |
| 7.3 | API `/api/agents/{role}` | GET retorna agente de `agent_catalog` |

### Integridad

- bundle seed: archivos fuente con hashes SHA256 verificados
- El test 7.7 verifica que import desde seed real genera mismo registro en DB

---

## 2️⃣ Análisis de Código

### Funciones/Clases Nuevas

| Sub-paso | Componente | Firma | Archivo |
|----------|------------|-------|---------|
| 7.4 | `BaseFlow.last_tool_calls` property | `@property def last_tool_calls(self) -> Dict[str, int]` | `src/flows/base_flow.py` |

### Patrones Existentes

- **Test E2E**: `tests/e2e/test_tool_calling_real.py` (líneas 121-125) usa `crew.get_last_tool_calls()` — patrón a seguir en test_real_flow_execute.py
- **Bundle seed**: copiar de `presupuesto-bundle/` ya existente

### Importaciones Necesarias

```python
# 7.4 — BaseFlow
from src.crews.base_crew import BaseCrew

# 7.3 — Test GET agente
from fastapi.testclient import TestClient
from src.api.main import app
```

---

## 3️⃣ Análisis de Backend

### Endpoints

| Endpoint | Método | Input | Output |
|----------|--------|-------|--------|
| `/api/bundles/import` | POST | ZIP bundle | 201 + agents_count |
| `/api/agents/{role}` | GET | path param role | 200 + agent config |
| `/api/tasks/{task_id}` | GET | task_id | 200 + status + output |

### Middleware

- `require_org_id` en GET /agents/{role}
- Autenticación JWT via middleware

### Flujos

- **7.1**: Flow con MCP tools → `_resolve_mcp_tool_async` real (sin mock)
- **7.2**: ZIP seed → import → agente en `agent_catalog`
- **7.3**: GET /agents/presupuestador → verificar campos

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo End-to-End

```
7.1: MCP Flow → resolve_tools_async() → MCPPool.get_tools() → COMPLETED
7.2: ZIP seed → POST /api/bundles/import → agent_catalog
7.3: GET /api/agents/presupuestador → validar campos JSON
7.4: Flow.execute() → crew.get_last_tool_calls() → verificar excel_reader ≥ 1
7.5: Eliminar test_real_tool_calling.py y test_real_agent_pipeline.py
7.6: @pytest.mark.skip + docstring en tests legacy
7.7: Import seed real → validar agente en DB
7.8: validate_input() → unit test
```

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: test_seed_import.py (script helper)
- **Qué automatiza**: Verifica que el bundle seed en data/seed/ es importable y genera agentes válidos
- **Tipo**: Test E2E automático
- **Cómo se usa**: `uv run pytest tests/e2e/test_seed_import.py -v`
- **Impacto para el usuario final**: Garantiza que el seed funciona sin intervención manual
- **Prioridad**: Tarea 0 para sub-pasos 7.2 y 7.7
```

---

## 5️⃣ Criterios de Aceptación

| ID | Sub-paso | Criterio | Verificable |
|----|----------|----------|-------------|
| ✅ [DATA] | 7.1 | `test_exec_agent_mcp.py::test_mcp_flow_completes` sin parche | SÍ |
| ✅ [DATA] | 7.2 | `data/seed/presupuesto-bundle/` existe con manifest + agents | SÍ |
| ✅ [CODE] | 7.3 | Test GET /api/agents/presupuestador pasa | SÍ |
| ✅ [BACKEND] | 7.4 | test_real_flow_execute.py verifica `get_last_tool_calls()` ≥ 1 | SÍ |
| ✅ [CODE] | 7.5 | test_real_tool_calling.py eliminado | SÍ |
| ✅ [CODE] | 7.6 | test_real_agent_presupuesto.py tiene @pytest.mark.skip | SÍ |
| ✅ [DATA] | 7.7 | Import seed real → agente en DB | SÍ |
| ✅ [CODE] | 7.8 | validate_input() rechaza input incompleto | SÍ |
| ✅ [DX] | 7.2,7.7 | Script helper verifica seed importable | SÍ |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| 7.1: MCPPool mock no provee tools | Media | Test usa `AsyncMock(return_value=None)` | Crear fixture con MCPPool mock que retorne tools |
| 7.4: BaseFlow no expone crew | Alta | BaseFlow no tiene referencia al crew interno | Agregar `last_tool_calls` property |
| 7.5: Eliminar test_real_tool_calling.py | Baja | Duplicado — perder cobertura si test_tool_calling_real.py falla | Verificar que test_tool_calling_real.py pasa primero |
| 7.6: Tests legacy dan falso positivo | Media | Parecen probar tool calling pero pre-fetchean datos | Deprecar con skip + docstring claro |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|----|-------|-----------|-----------------|-----------------|-------|-------------|--------------|--------------|---------------|
| 0 | **DX**: Fixture MCPPool mock | `tests/conftest.py` | `@pytest.fixture async def mock_mcp_pool()` | — | DX | Media | 0.5h | Ninguna | → verificar: `python -c "from tests.conftest import mock_mcp_pool"` |
| 1 | 7.1: Remover parche MCP | `tests/e2e/test_exec_agent_mcp.py` | Eliminar líneas 63-67 (patch context manager) | `tests/e2e/test_tool_calling_real.py::test_presupuestador_calls_excel_reader` | CODE | Baja | 0.25h | Tarea 0 | → verificar: grep "patch.*_resolve_mcp_tool_async" test_exec_agent_mcp.py retorna vacío |
| 2 | 7.2: Crear bundle seed | `data/seed/presupuesto-bundle/` | Copiar manifest.json + agents/presupuestador.json | `presupuesto-bundle/` existente | DATA | Baja | 0.25h | Ninguna | → verificar: `ls data/seed/presupuesto-bundle/` muestra archivos |
| 3 | 7.3: Test GET agente via API | `tests/e2e/test_register_agent.py` | `def test_get_agent_via_api_returns_correct_data(self)` | `test_register_agent.py::test_bundle_import_returns_201` | CODE | Media | 0.5h | Ninguna | → verificar: `uv run pytest tests/e2e/test_register_agent.py::TestRegisterAgent::test_get_agent_via_api_returns_correct_data -v` |
| 4 | 7.4: Exponer last_tool_calls | `src/flows/base_flow.py` | `@property def last_tool_calls(self) -> Dict[str, int]: return self._crew.get_last_tool_calls() if hasattr(self, '_crew') else {}` | `src/crews/base_crew.py::get_last_tool_calls` | CODE | Media | 0.5h | Ninguna | → verificar: `python -c "from src.flows.base_flow import BaseFlow; print(hasattr(BaseFlow, 'last_tool_calls'))"` |
| 5 | 7.4: Agregar verificación tool calls | `tests/e2e/test_real_flow_execute.py` | Agregar `tool_calls = flow.last_tool_calls; assert tool_calls.get("excel_reader", 0) >= 1` | `test_tool_calling_real.py:121-125` | CODE | Media | 0.25h | Tarea 4 | → verificar: `uv run pytest tests/e2e/test_real_flow_execute.py -k test_flow_execute_with_tool -v` |
| 6 | 7.5: Eliminar duplicados | `tests/e2e/test_real_tool_calling.py`, `test_real_agent_pipeline.py` | Eliminar ambos archivos | — | CODE | Baja | 0.25h | Ninguna | → verificar: `ls tests/e2e/test_*tool*.py` muestra solo test_tool_calling_real.py |
| 7 | 7.6: Deprecar legacy tests | `tests/e2e/test_real_agent_presupuesto.py`, `test_real_multi_agent_presupuesto.py` | Agregar `@pytest.mark.skip(reason="Legacy: migrado a test_tool_calling_real.py")` en cada test | — | CODE | Baja | 0.5h | Ninguna | → verificar: `uv run pytest tests/e2e/test_real_agent_presupuesto.py -v` muestra skipped |
| 8 | 7.7: Test import seed real | `tests/e2e/test_register_agent.py` | `async def test_import_seed_bundle_via_api(self)` | `test_register_agent.py::test_bundle_import_returns_201` | CODE | Media | 0.5h | Tarea 2 | → verificar: `uv run pytest tests/e2e/test_register_agent.py::TestRegisterAgent::test_import_seed_bundle_via_api -v` |
| 9 | 7.8: Test unitario validate_input | `tests/unit/test_presupuesto_flow.py` | `def test_validate_input_rejects_missing_fields()`, `test_validate_input_accepts_complete()` | — | CODE | Baja | 0.25h | Ninguna | → verificar: `uv run pytest tests/unit/test_presupuesto_flow.py -v` |

**Tiempo total estimado:** 3.25 horas

---

## 🔮 Roadmap

- **7.1 post-implementación**: Verificar que test con LLM real no deadlock
- **7.4 post-implementación**: Si BaseFlow no tiene `_crew`, exponer `get_last_tool_calls()` desde `BaseCrew` directamente
- **Fase futura**: Integrar Google Sheets API (reemplazar ExcelWriter)

---

## 🚫 Reglas de Oro Cumplidas

- ✅ Análisis accionable y específico
- ✅ TODO verificado contra código real
- ✅ Discrepancias documentadas (4 encontradas)
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta (test_seed_import.py)
- ✅ Tareas atómicas (1 artefacto por tarea)
- ✅ Interfaz exacta por tarea
- ✅ Patrón de referencia explícito
- ✅ Verificación inline por tarea
- ✅ Estimación de tiempo por tarea y total