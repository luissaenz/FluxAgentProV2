# 🧠 Análisis Técnico — Paso 10 — Agente: ops

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Carpeta `tests/e2e` existe | `ls -d tests/e2e` | ✅ | `tests/e2e` existe |
| 2 | `TestClient` importable | `grep -r "TestClient" tests/` | ✅ | Usado en `tests/conftest.py` |
| 3 | `mock_tenant_client` disponible | `grep "mock_tenant_client" tests/conftest.py` | ✅ | `tests/conftest.py:175` |
| 4 | Endpoint `GET /api/tools/available` | `src/api/routes/tools.py` | ✅ | Implementado en Paso 01 |
| 5 | Endpoint `POST /api/bundles/export` | `src/api/routes/bundles.py` | ✅ | Implementado en Paso 02 |
| 6 | Endpoint `GET /api/templates` | `src/api/routes/templates.py` | ✅ | Implementado en Paso 03 |
| 7 | Endpoint `POST /agents` | `src/api/routes/agents.py` | ✅ | Implementado en Paso 04 |
| 8 | Endpoint `POST /workflows` | `src/api/routes/workflows.py` | ✅ | Implementado en Paso 07 |
| 9 | Tabla `agent_catalog` RLS | `004_agent_catalog.sql` | ✅ | Policy `agent_catalog_tenant_isolation` |

**Discrepancias encontradas:**
1. **Falta de tests unitarios de builder:** Aunque hay lógica de serialización en `dashboard/lib/canvasUtils.ts`, no hay tests unitarios equivalentes en el backend para validar que los payloads generados por el canvas sean procesados correctamente. Se deben incluir tests de escenarios en `tests/e2e/test_builder_scenarios.py`.
2. **E2E sin navegador:** El plan menciona tests E2E pero el stack no incluye Playwright/Cypress. Seguiremos el patrón de "Escenarios de Integración" usando `TestClient` y simulando los payloads que enviaría el frontend.
3. **Criterio de "drag & drop":** Al no haber navegador, el test de "ensamblar crew en canvas" se validará mediante la inyección de payloads de `CrewGraph` (nodos + edges) al endpoint `/workflows` y verificando la persistencia y coherencia del grafo.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

El análisis desde Ops se centra en la integridad y consistencia de los datos inyectados para los tests, asegurando que los mocks de Supabase repliquen el comportamiento de RLS.

- **✅ Schema Mocking:** Los tests deben configurar el `mock_tenant_client` para devolver respuestas consistentes en `agent_catalog` y `workflow_templates`.
- **✅ Integridad Referencial:** Verificar que al crear un workflow desde el canvas, los IDs de los agentes referenciados existan en el `agent_catalog` (simulado en el mock).
- **✅ RLS Verification:** Cada llamada al `api_client` debe incluir el header `X-Org-ID`. El test debe validar que si se cambia el header, el `mock_tenant_client` recibe el nuevo ID.

---

## 2️⃣ Análisis de Código (ETAPA 2)

- **✅ Patrón de Escenario:** Usaremos el patrón definido en `tests/e2e/test_scenario_6_full_stack.py`.
- **✅ Fixtures:** Se creará una fixture `builder_payloads` en `tests/e2e/conftest.py` (o local al archivo) para centralizar los JSONs de prueba (templates, agents, canvas graphs).
- **✅ Firmas de Test:**
  - `test_create_agent_from_form_scenario`: Simula `POST /agents`.
  - `test_select_template_mapping_scenario`: Simula `GET /api/templates/{id}` y valida estructura.
  - `test_crew_assembly_and_export_scenario`: Simula `POST /workflows` seguido de `POST /api/bundles/export`.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- **✅ Contrato Export/Import:** El punto más crítico es asegurar que lo que sale de `POST /api/bundles/export` (Paso 10.8) pueda entrar en `POST /api/bundles/import` sin errores.
- **✅ Polling Playground:** El test de playground debe simular múltiples llamadas a `GET /tasks/{task_id}` hasta alcanzar el estado `completed`.
- **✅ Error Handling:** Validar que `POST /api/bundles/export` devuelva 422 si el `soul_json` (goal/backstory) no cumple con la longitud mínima de 10 chars (mitigación implementada en Paso 02/08).

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- **✅ Coherencia:** El flujo "Crear → Probar → Exportar" debe ser testeado como una secuencia lógica en un único test de escenario para validar que los estados intermedios en DB son correctos.
- **✅ DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: `validate_builder_e2e.py`
- **Qué automatiza:** Ejecuta específicamente la suite de tests del builder y genera un reporte HTML visual con el estado de salud de cada feature (Templates, Agents, Canvas, Export).
- **Tipo:** script / validador
- **Cómo se usa:** `uv run python scripts/validate_builder_e2e.py`
- **Impacto para el usuario final:** Proporciona confianza inmediata en la integridad de la fase `guiAgentGenerator` antes de pasar a producción o la siguiente fase.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

---

## 5️⃣ Criterios de Aceptación

✅ [DATA] Mocks de Supabase configurados con datos de prueba para 3 agentes y 2 templates.
✅ [CODE] Archivo `tests/e2e/test_builder_scenarios.py` creado con 6 escenarios base.
✅ [BACKEND] Endpoint `POST /api/bundles/export` validado contra payload real generado por `CrewCanvas`.
✅ [FULLSTACK] Test de round-trip (Export -> Import) pasa exitosamente usando el bundle generado.
✅ [DX] Script `scripts/validate_builder_e2e.py` genera reporte sin errores.

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Falsos positivos en mocks | Alta | Los mocks no replican exactamente las constraints de DB | Usar `WorkflowDefinition` (Pydantic) para validar los datos antes de inyectarlos al mock. |
| Incompatibilidad de ZIP | Media | El ZIP generado por Export no es leído correctamente por Import | El test de round-trip debe usar `zipfile` para inspeccionar el contenido del ZIP. |
| Timeouts en Playground | Baja | El polling en el test puede tardar demasiado | Configurar un timeout agresivo (5s) en el `TestClient` para el polling mockeado. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `validate_builder_e2e.py` | `scripts/validate_builder_e2e.py` | `def main(): ...` | `scripts/validate_builder_nav.py` | DX | Media | 1h | Ninguna | → verificar: `python scripts/validate_builder_e2e.py` |
| 1 | Crear fixtures de payloads | `tests/e2e/test_builder_scenarios.py` | `BUILDER_CANVAS_PAYLOAD = {...}` | `tests/e2e/test_scenario_6_full_stack.py` | CODE | Baja | 1h | Tarea 0 | → verificar: Payloads cargan correctamente |
| 2 | Test: Escenario CRUD Agente | `tests/e2e/test_builder_scenarios.py` | `test_agent_builder_crud_scenario(api_client, mock_tenant_client)` | `tests/unit/test_crew_endpoints.py` | BACKEND | Media | 1h | Tarea 1 | → verificar: `pytest tests/e2e/test_builder_scenarios.py -k crud` |
| 3 | Test: Escenario Canvas y Export | `tests/e2e/test_builder_scenarios.py` | `test_canvas_to_export_scenario(api_client, mock_tenant_client)` | `tests/integration/test_bundle_export_roundtrip.py` | FULLSTACK | Alta | 2h | Tarea 2 | → verificar: `pytest tests/e2e/test_builder_scenarios.py -k export` |
| 4 | Test: Escenario Playground | `tests/e2e/test_builder_scenarios.py` | `test_playground_polling_scenario(api_client, mock_tenant_client)` | `tests/unit/test_agent_run.py` | BACKEND | Media | 1h | Tarea 1 | → verificar: `pytest tests/e2e/test_builder_scenarios.py -k playground` |

**Tiempo total estimado:** 6 horas
