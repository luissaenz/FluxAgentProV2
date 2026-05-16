# Análisis Técnico — Paso 10: Tests E2E del Builder

> **Agente:** [AGENTE]
> **Paso:** 10
> **Fecha:** 2026-05-16
> **Fase:** guiAgentGenerator

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `GET /api/tools/available` | `src/api/routes/tools.py:46-63` | ✅ | Handler `list_available_tools`, retorna `ToolsListResponse` |
| 2 | Endpoint `POST /api/bundles/export` | `src/api/routes/bundles.py:199-248` | ✅ | Handler `export_bundle`, valida goal/backstory, retorna ZIP |
| 3 | Endpoint `GET /api/templates` | `src/api/routes/templates.py:54-67` | ✅ | Handler `list_templates`, filtro `?category=` |
| 4 | Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:70-83` | ✅ | Handler `get_template`, 404 si no existe |
| 5 | Endpoint `POST /agents` | `src/api/routes/agents.py:101-151` | ✅ | Handler `create_agent`, upsert logic, 201 |
| 6 | Endpoint `POST /agents/{role}/run` | `src/api/routes/agents.py:301-369` | ✅ | Handler `run_agent`, background task, retorna task_id |
| 7 | Endpoint `GET /tasks/{task_id}` | `src/api/routes/tasks.py:69-91` | ✅ | Handler `get_task`, polling, retorna `TaskResponse` |
| 8 | Tabla `agent_catalog` | `supabase/migrations/004_agent_catalog.sql` | ✅ | phase-state.md §2 línea 179 |
| 9 | Tabla `agent_templates` | `supabase/migrations/030_agent_templates.sql:10-21` | ✅ | phase-state.md §2 línea 62 |
| 10 | Tabla `tasks` | `src/api/routes/tasks.py:76-91` (queries) | ✅ | Columnas: id, org_id, flow_type, status, result, error, tokens_used, created_at, updated_at |
| 11 | `TestClient` de FastAPI | `tests/e2e/test_mvp_certification.py:27-28` | ✅ | Fixture `api_client` ya existe |
| 12 | Mocks Supabase (`mock_tenant_client`, `mock_service_client`) | `tests/conftest.py:111-213` | ✅ | Fixtures globales con chain mocking completo |
| 13 | Mock LLM global (`global_llm_mock`) | `tests/conftest.py:274-303` | ✅ | Autouse fixture, patchea crewai.Agent/Task/Crew |
| 14 | `ExportService` | `src/services/export_service.py:21-66` | ✅ | `export(payload) -> tuple[bytes, str]` |
| 15 | `ImportService` | `src/services/import_service.py` | ✅ | `process_bundle(zip_bytes) -> BundleRPCResult` |
| 16 | `tests/e2e/` directorio existe | `ls tests/e2e/` | ✅ | 20 archivos de tests E2E existentes |
| 17 | `tests/e2e/__init__.py` | `tests/e2e/__init__.py` | ✅ | Archivo existe, módulo Python válido |
| 18 | `ExportBundleRequest` modelo | `src/services/bundle_schemas.py:102-116` | ✅ | Pydantic BaseModel con agents + skills |
| 19 | `AgentForm.tsx` componente | `dashboard/components/builder/AgentForm.tsx` | ✅ | 11 campos, react-hook-form + zodResolver, POST /agents |
| 20 | `TemplatePicker.tsx` componente | `dashboard/components/builder/TemplatePicker.tsx` | ✅ | Grid cards, GET /api/templates, "Use Template" |
| 21 | `AgentPlayground.tsx` componente | `dashboard/components/builder/AgentPlayground.tsx` | ✅ | Chat panel, POST /agents/{role}/run + polling tasks |
| 22 | `CrewCanvas.tsx` componente | `dashboard/components/builder/CrewCanvas.tsx:74` | ✅ | ReactFlow v11, DnD nativo, autosave localStorage |
| 23 | `ExportDialog.tsx` componente | `dashboard/components/builder/ExportDialog.tsx:1-322` | ✅ | 5 estados, POST /api/bundles/export |
| 24 | `canvasToExportPayload()` | `dashboard/lib/canvasUtils.ts:36-44` | ✅ | Convierte agentNodes → ExportBundleRequest |
| 25 | `fapDownload()` helper | `dashboard/lib/api.ts:54-94` | ✅ | Descarga binaria autenticada con JWT |
| 26 | Router tools registrado | `src/api/main.py:114` | ✅ | `app.include_router(tools_router)` |
| 27 | Router bundles registrado | `src/api/main.py:111` | ✅ | `app.include_router(bundles_router)` |
| 28 | Router templates registrado | `src/api/main.py:113` | ✅ | `app.include_router(templates_router)` |
| 29 | Router agents registrado | `src/api/main.py:107` | ✅ | `app.include_router(agents_router)` |
| 30 | Router tasks registrado | `src/api/main.py:100` | ✅ | `app.include_router(tasks_router)` |
| 31 | No existe `tests/e2e/test_builder_*.py` | `ls tests/e2e/` | ✅ | No hay tests E2E del builder aún |
| 32 | No existe Playwright en dashboard | `dashboard/package.json` | ❌ DISCREPANCIA | No hay playwright ni @playwright/test en devDependencies |

**Discrepancias encontradas:**

1. **❌ DISCREPANCIA D1:** El plan dice "Tests usan Supabase real (no mock)" pero el proyecto NO tiene infraestructura de test con Supabase real. Todos los tests existentes usan `mock_service_client` y `mock_tenant_client`. No hay `.env.test` ni fixture de Supabase local. **Resolución:** Los tests E2E del builder deben usar mocks (patrón existente), no Supabase real. Documentar como desviación del plan.

2. **❌ DISCREPANCIA D2:** El plan menciona tests de UI frontend (formulario, template picker, playground, canvas) pero el dashboard NO tiene Playwright ni Cypress instalado. Los tests existentes son 100% Python (FastAPI + services). **Resolución:** Crear tests E2E a nivel API Python que simulen el flujo completo del builder. Los tests de UI del frontend quedan como mejora futura (requiere instalar Playwright).

3. **⚠️ NO VERIFICABLE:** El plan dice "Todos los tests pasan en `uv run pytest tests/e2e/ -k builder`" — el filtro `-k builder` funcionará si los archivos se nombran `test_builder_*.py`. Confirmar convención de naming.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas

| Tabla | Uso en tests | Migración |
|---|---|---|
| `agent_catalog` | Crear agente, leer agente creado | `004_agent_catalog.sql` |
| `agent_templates` | Listar templates, obtener detalle | `030_agent_templates.sql` |
| `tasks` | Crear task (via run agent), polling task status | Schema implícito (queries en `tasks.py`) |
| `org_mcp_servers` | Query para MCP tools en endpoint tools | Schema en `mcp_pool.py:122-131` |

### Integridad referencial

- `agent_catalog.org_id` → referencia `organizations.id` (tenant isolation via RLS)
- `tasks.org_id` → referencia `organizations.id` (tenant isolation via RLS)
- `agent_templates` — tabla global, sin `org_id`, RLS SELECT public

### RLS policies aplicables

- `agent_catalog`: POLICY tenant_isolation via `org_id::text = app.org_id()` (migración 004)
- `tasks`: POLICY tenant_isolation via `org_id` (patrón consistente)
- `agent_templates`: Sin RLS de escritura (solo system), lectura pública

### Datos de seed necesarios para tests

Los tests necesitan datos mock que simulen:
- Templates seed (8 templates system) — ya existe `templates_seed.py`
- Agentes en `agent_catalog` — insertados via `POST /agents` en tests
- Tasks creadas via `POST /agents/{role}/run` — generadas dinámicamente

### Impacto en datos existentes

- Tests NO modifican datos reales (usan mocks)
- Tests de round-trip export→import validan estructura ZIP sin tocar DB real
- Sin riesgo de corrupción de datos

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Tests a crear — firmas y estructura

Se creará **un solo archivo** de tests E2E: `tests/e2e/test_builder_e2e.py`

#### Clases de test (una por sub-paso del plan):

**Clase `TestBuilderCreateAgent`**
- `test_create_agent_via_api_success(self, api_client, mock_tenant_client, sample_org_id)`
  - POST /agents con payload válido → 201
  - Verificar response contiene id, role, soul_json

**Clase `TestBuilderTemplatePicker`**
- `test_template_list_returns_templates(self, api_client, mock_service_client)`
  - GET /api/templates → 200, array no vacío
- `test_template_use_fills_form_data(self, api_client, mock_service_client)`
  - GET /api/templates/{id} → 200, incluye soul_json completo
  - Simular flujo: obtener template → crear agente con esos datos

**Clase `TestBuilderPlayground`**
- `test_agent_run_returns_task_id(self, api_client, mock_tenant_client, sample_org_id)`
  - POST /agents/{role}/run → 200, retorna task_id + status "accepted"
- `test_task_polling_returns_result(self, api_client, mock_tenant_client, sample_org_id)`
  - GET /tasks/{task_id} → 200, retorna TaskResponse con status, tokens_used

**Clase `TestBuilderCrewCanvas`**
- `test_canvas_export_payload_valid(self)`
  - Validar estructura de `canvasToExportPayload()` (lógica TypeScript, test unitario Python mirror)
- `test_crew_graph_serialize_deserialize(self)`
  - `nodesToSnapshot()` / `snapshotToNodes()` round-trip

**Clase `TestBuilderExportImport`**
- `test_export_creates_valid_zip(self, api_client, mock_tenant_client, sample_org_id)`
  - POST /api/bundles/export → 200, ZIP válido
- `test_export_import_roundtrip(self, api_client, mock_tenant_client, sample_org_id)`
  - Export → validar ZIP → Import → 201

**Clase `TestBuilderEndpointsIntegration`**
- `test_tools_available_returns_tools(self, api_client, mock_tenant_client, sample_org_id)`
  - GET /api/tools/available → 200, ToolsListResponse
- `test_templates_endpoint_returns_templates(self, api_client, mock_service_client)`
  - GET /api/templates → 200, TemplateListResponse
- `test_export_validation_goal_backstory_required(self, api_client, mock_tenant_client)`
  - POST /api/bundles/export sin goal → 422

### Patrones existentes a seguir

| Patrón | Archivo de referencia |
|---|---|
| TestClient fixture | `tests/e2e/test_mvp_certification.py:26-28` |
| Mock Supabase chain | `tests/conftest.py:42-105` |
| Crear ZIP en memoria | `tests/e2e/test_mvp_certification.py:36-61` |
| Test class con métodos | `tests/unit/test_templates.py:78-139` |
| Async test con pytest.mark.asyncio | `tests/e2e/test_exec_simple_agent.py:56-80` |

### Imports exactos necesarios

```python
from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.services.bundle_schemas import AgentExportItem, ExportBundleRequest
from src.services.export_service import ExportService
from src.services.import_service import ImportService
```

### Modularidad

- Un solo archivo `test_builder_e2e.py` — cohesión alta (todos tests del builder)
- Cada clase = un sub-flujo del builder
- Sin duplicación: reutiliza fixtures globales de `conftest.py`
- Acoplamiento bajo: cada test es independiente, no comparte estado

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints bajo test

| Endpoint | Método | Input | Output | Auth |
|---|---|---|---|---|
| `/api/tools/available` | GET | `?source=`, `?category=` | `ToolsListResponse` | `require_org_id` |
| `/api/templates` | GET | `?category=` | `TemplateListResponse` | None |
| `/api/templates/{id}` | GET | path param | `TemplateDetailResponse` | None |
| `/agents` | POST | `AgentCreate` | `AgentResponse` (201) | `require_org_id` |
| `/agents/{role}/run` | POST | `RunAgentRequest` | `RunAgentResponse` | `verify_org_membership` |
| `/tasks/{task_id}` | GET | path param | `TaskResponse` | `verify_org_membership` |
| `/api/bundles/export` | POST | `ExportBundleRequest` | ZIP (200) | `require_org_id` |
| `/api/bundles/import` | POST | multipart ZIP | `BundleRPCResult` (201) | `require_org_id` |

### Flujo de datos end-to-end del builder

```
1. User → GET /api/tools/available → lista tools (local + MCP)
2. User → GET /api/templates → selecciona template
3. User → GET /api/templates/{id} → obtiene soul_json
4. User → POST /agents → crea agente en agent_catalog
5. User → POST /agents/{role}/run → inicia ejecución → task_id
6. User → GET /tasks/{task_id} → polling → resultado + tokens_used
7. User → POST /api/bundles/export → genera ZIP
8. User → POST /api/bundles/import → re-importa ZIP → verifica
```

### Error handling a validar

| Endpoint | Error esperado | Status code |
|---|---|---|
| `POST /agents` | role duplicado en org | 409 |
| `POST /agents/{role}/run` | role no existe | 404 |
| `GET /tasks/{task_id}` | task no existe | 404 |
| `GET /tasks/{task_id}` | UUID inválido | 400 |
| `POST /api/bundles/export` | goal/backstory vacío | 422 |
| `POST /api/bundles/export` | goal/backstory < 10 chars | 422 |
| `POST /api/bundles/import` | ZIP inválido | 400 |
| `GET /api/templates/{id}` | template no existe | 404 |

### Contratos entre servicios

- `ExportService.export()` → genera ZIP compatible con `ImportService.process_bundle()`
- `POST /agents/{role}/run` → crea task en DB → `GET /tasks/{task_id}` lee misma task
- `ToolRegistry` + `MCPPool` → `GET /api/tools/available` combina ambas fuentes

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

El builder tiene 4 componentes frontend que interactúan con 7 endpoints backend:

```
┌─────────────────────────────────────────────────────────────┐
│                    Builder UI (Frontend)                     │
├──────────────┬──────────────┬───────────────┬───────────────┤
│ AgentForm    │ TemplatePick │ AgentPlaygrnd │ CrewCanvas    │
│ POST /agents │ GET /tpls    │ POST /run     │ export payload│
│ GET /tools   │ GET /tpl/id  │ GET /tasks    │ POST /export  │
└──────┬───────┴──────┬───────┴───────┬───────┴───────┬───────┘
       │              │               │               │
       ▼              ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
├──────────────┬──────────────┬───────────────┬───────────────┤
│ /agents      │ /templates   │ /tasks        │ /bundles      │
│ /tools       │              │               │               │
└──────┬───────┴──────┬───────┴───────┬───────┴───────┬───────┘
       │              │               │               │
       ▼              ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Supabase (PostgreSQL)                      │
├──────────────┬──────────────┬───────────────┬───────────────┤
│ agent_catalog│ agent_tmplts │ tasks         │ (ZIP en mem)  │
└──────────────┴──────────────┴───────────────┴───────────────┘
```

### Coherencia con arquitectura existente

- ✅ Todos los endpoints existen y están registrados en `main.py`
- ✅ Modelos Pydantic definidos para request/response
- ✅ Mocks globales en `conftest.py` cubren todos los puntos de patch
- ✅ Patrones de test existentes (TestClient + mock chain) aplicables directamente

### Gaps identificados

1. **No hay tests E2E del builder** — el paso 10 es el primero en cubrir este flujo
2. **No hay Playwright** — tests de UI del frontend no son posibles sin infraestructura adicional
3. **`POST /agents/{role}/run` usa background_tasks** — el test de polling necesita simular que la task cambia de estado (pending → running → completed)

### DX & Tooling (OBLIGATORIO)

### Herramienta Propuesta: `test_builder_runner.py`
- **Qué automatiza:** Ejecutar solo los tests del builder con output detallado, sin correr toda la suite E2E. El usuario actual debe recordar el comando exacto `uv run pytest tests/e2e/ -k builder -v`.
- **Tipo:** Script CLI
- **Cómo se usa:** `uv run python scripts/test_builder_runner.py [--verbose] [--coverage]`
- **Impacto para el usuario final:** Un comando simple para validar el builder completo. Con `--verbose` muestra qué sub-flujo está testeando. Con `--coverage` genera reporte de cobertura específico del builder.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `agent_catalog` accesible via mock_tenant_client en tests
✅ [DATA] Tabla `agent_templates` accesible via mock_service_client en tests
✅ [DATA] Tabla `tasks` con columnas status, result, tokens_used verificadas en mock
✅ [CODE] Archivo `tests/e2e/test_builder_e2e.py` existe y es importable sin errores
✅ [CODE] Clase TestBuilderCreateAgent con test que valida POST /agents → 201
✅ [CODE] Clase TestBuilderTemplatePicker con tests que validan GET /api/templates
✅ [CODE] Clase TestBuilderPlayground con tests que validan POST /agents/{role}/run + GET /tasks/{task_id}
✅ [CODE] Clase TestBuilderCrewCanvas con tests que validan serialización de grafo
✅ [CODE] Clase TestBuilderExportImport con test round-trip export→import
✅ [BACKEND] Endpoint GET /api/tools/available retorna ToolsListResponse con count > 0
✅ [BACKEND] Endpoint POST /api/bundles/export genera ZIP válido con manifest.json
✅ [BACKEND] Endpoint POST /api/bundles/export rechaza sin goal/backstory → 422
✅ [BACKEND] Endpoint POST /api/bundles/import acepta ZIP exportado → 201
✅ [FULLSTACK] Flujo completo: crear agente → ejecutar → obtener resultado → exportar → importar
✅ [DX] Script `scripts/test_builder_runner.py` ejecuta sin errores con `--help`
✅ [FULLSTACK] Todos los tests pasan con `uv run pytest tests/e2e/test_builder_e2e.py -v`
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Background tasks no ejecutan en TestClient | Alta | FastAPI TestClient no procesa `background_tasks` automáticamente | Mockear `_execute` directamente en el test de playground, simular task completion |
| ZIP export/import round-trip falla por hash mismatch | Media | `ExportService` genera hashes SHA256 que `ImportService` valida | Usar `ExportService` real en test, no mock — los hashes serán consistentes |
| Tests dependen de orden de ejecución | Media | Tests comparten estado si no se aíslan correctamente | Cada test crea su propio org_id (uuid4), mocks independientes |
| No se puede testear UI real del builder | Media | Sin Playwright/Cypress en dashboard | Documentar como limitación, tests cubren API que el UI consume |
| MCP tools endpoint falla sin infraestructura real | Baja | `_fetch_mcp_tools` query `org_mcp_servers` | Mockear `get_service_client` para retornar lista vacía de servers |
| Polling de tasks requiere simular transición de estado | Media | Task se crea en "pending" pero nunca cambia sin background task | Mockear `db.table("tasks").update()` para simular completion en el test |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `test_builder_runner.py` | `scripts/test_builder_runner.py` | `def main(): subprocess.run(["uv", "run", "pytest", "tests/e2e/test_builder_e2e.py", "-v"])` | `scripts/validate_builder_nav.py` | DX | Baja | 0.5h | Ninguna | → verificar: `uv run python scripts/test_builder_runner.py --help` ejecuta sin errores |
| 1 | Crear archivo test_builder_e2e.py | `tests/e2e/test_builder_e2e.py` | Módulo Python con imports: `pytest`, `TestClient`, `io`, `json`, `zipfile`, `patch`, `uuid4` | `tests/e2e/test_mvp_certification.py` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `python -c "import tests.e2e.test_builder_e2e"` sin error |
| 2 | Implementar TestBuilderCreateAgent | `tests/e2e/test_builder_e2e.py :: class TestBuilderCreateAgent` | `test_create_agent_via_api_success(self, api_client, mock_tenant_client, sample_org_id)`: POST `/agents` con `{"role":"test","soul_json":{"goal":"test goal value here","backstory":"test backstory value"},"allowed_tools":[],"max_iter":3}` → assert 201, assert response.json()["role"]=="test" | `tests/unit/test_templates.py :: TestListTemplates` | CODE | Baja | 0.5h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_builder_e2e.py::TestBuilderCreateAgent -v` pasa |
| 3 | Implementar TestBuilderCreateAgent error cases | `tests/e2e/test_builder_e2e.py :: class TestBuilderCreateAgent` | `test_create_agent_missing_role_raises_422(self, api_client)`: POST `/agents` sin role → assert 422 | `tests/unit/test_templates.py :: TestGetTemplate.test_get_by_id_not_found` | CODE | Baja | 0.5h | Tarea 2 | → verificar: `uv run pytest tests/e2e/test_builder_e2e.py::TestBuilderCreateAgent -v` pasa todos |
| 4 | Implementar TestBuilderTemplatePicker | `tests/e2e/test_builder_e2e.py :: class TestBuilderTemplatePicker` | `test_template_list_returns_templates(self, api_client, mock_service_client)`: mock `agent_templates` con 2 items → GET `/api/templates` → assert 200, count==2; `test_template_detail_includes_soul_json(self, api_client, mock_service_client)`: mock single template → GET `/api/templates/{id}` → assert 200, "soul_json" in body | `tests/unit/test_templates.py :: TestListTemplates + TestGetTemplate` | CODE | Baja | 0.5h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_builder_e2e.py::TestBuilderTemplatePicker -v` pasa |
| 5 | Implementar TestBuilderPlayground | `tests/e2e/test_builder_e2e.py :: class TestBuilderPlayground` | `test_agent_run_returns_task_id(self, api_client, mock_tenant_client, sample_org_id)`: POST `/agents/{role}/run` con `{"input_data":{"message":"hello"}}` → assert 200, "task_id" in response; `test_task_polling_returns_result(self, api_client, mock_tenant_client, sample_org_id)`: mock task con status="completed", tokens_used=150 → GET `/tasks/{task_id}` → assert 200, status=="completed" | `tests/e2e/test_exec_simple_agent.py :: TestExecSimpleAgent` | BACKEND | Media | 1h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_builder_e2e.py::TestBuilderPlayground -v` pasa |
| 6 | Implementar TestBuilderCrewCanvas | `tests/e2e/test_builder_e2e.py :: class TestBuilderCrewCanvas` | `test_canvas_export_payload_structure(self)`: crear dict con `agents: [{role, soul_json, allowed_tools, max_iter}]` → validar contra `ExportBundleRequest.model_validate()` → assert sin error; `test_crew_graph_roundtrip(self)`: crear grafo nodes+edges → serializar a JSON → deserializar → assert nodes iguales | `tests/unit/test_canvas_serialize.py` | CODE | Media | 1h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_builder_e2e.py::TestBuilderCrewCanvas -v` pasa |
| 7 | Implementar TestBuilderExportImport | `tests/e2e/test_builder_e2e.py :: class TestBuilderExportImport` | `test_export_creates_valid_zip(self, api_client, mock_tenant_client, sample_org_id)`: POST `/api/bundles/export` con payload válido → assert 200, validar ZIP con `zipfile.ZipFile`, assert "manifest.json" in names; `test_export_import_roundtrip(self, api_client, mock_tenant_client, sample_org_id)`: export → mock import → assert 201, status=="committed" | `tests/integration/test_bundle_export_roundtrip.py :: TestExportImportRoundtrip` | BACKEND | Media | 1.5h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_builder_e2e.py::TestBuilderExportImport -v` pasa |
| 8 | Implementar TestBuilderEndpointsIntegration | `tests/e2e/test_builder_e2e.py :: class TestBuilderEndpointsIntegration` | `test_tools_available_returns_tools(self, api_client, mock_tenant_client, sample_org_id)`: mock tool_registry con 1 tool → GET `/api/tools/available` → assert 200, count>=1; `test_export_validation_goal_required(self, api_client, mock_tenant_client)`: POST `/api/bundles/export` con soul_json sin goal → assert 422 | `tests/unit/test_templates.py :: TestListTemplates.test_list_no_auth_required` | BACKEND | Baja | 0.5h | Tarea 1 | → verificar: `uv run pytest tests/e2e/test_builder_e2e.py::TestBuilderEndpointsIntegration -v` pasa |
| 9 | Validar flujo end-to-end completo | — | Ejecutar `uv run pytest tests/e2e/test_builder_e2e.py -v` → todos pasan | `tests/e2e/test_mvp_certification.py` | FULLSTACK | Baja | 0.5h | Tareas 2-8 | → verificar: `uv run pytest tests/e2e/test_builder_e2e.py -v --tb=short` → 0 fallos |

**Tiempo total estimado:** 7 horas

---

## 🔮 Roadmap (NO implementar ahora)

1. **Instalar Playwright en dashboard** — para tests E2E reales de UI (formulario, drag-and-drop, canvas). Requiere: `npm install -D @playwright/test`, configurar `playwright.config.ts`, crear tests en `dashboard/tests/`.
2. **Supabase local (Docker)** — para tests con DB real en vez de mocks. Requiere: `docker-compose.yml` con Supabase, fixture de seed data, cleanup entre tests.
3. **Test de CrewCanvas drag-and-drop** — validar que nodos se pueden arrastrar y conectar visualmente. Solo posible con Playwright.
4. **Test de ExportDialog UI** — validar que el diálogo muestra resumen pre-export y descarga ZIP. Solo posible con Playwright.
5. **Performance tests del builder** — medir tiempo de carga de templates, tools, y generación de ZIP con 10+ agentes.
6. **Test de concurrencia** — múltiples usuarios creando agentes simultáneamente en la misma org, validar aislamiento.

---

## 📊 Métrica de Calidad (auto-evaluación)

| Métrica | Mínimo | Resultado |
|---|---|---|
| `proyecto-config.json` leído antes de explorar | 100% | ✅ |
| Elementos verificados (§0) | ≥ 22 (10+ archivos) | ✅ 32 elementos |
| Discrepancias detectadas | ≥ 1 si toca código existente | ✅ 2 discrepancias + 1 no verificable |
| Secciones completadas | 8 secciones (0-7) | ✅ 8 secciones |
| Etapas cubiertas | 4 etapas | ✅ data, code, backend, fullstack+DX |
| Criterios de aceptación | ≥ 1 por sub-paso | ✅ 16 criterios, todos verificables |
| Riesgos identificados | ≥ 3 | ✅ 6 riesgos |
| Tareas atómicas (1 artefacto por tarea) | 100% | ✅ 10 tareas, cada una = 1 artefacto |
| Interfaz exacta por tarea | 100% | ✅ Cada tarea tiene firma/detalle completo |
| Patrón de referencia explícito por tarea | 100% | ✅ Cada tarea referencia archivo concreto |
| Verificación inline por tarea | 100% | ✅ Cada tarea tiene comando `→ verificar` |
| Suposiciones no verificadas | ≤ 2 | ✅ 1 (convención naming) |
| Propuesta DX / Tooling | ≥ 1 | ✅ `test_builder_runner.py` |
| Estimación de tiempo | Sí, por tarea y total | ✅ 7 horas total |
