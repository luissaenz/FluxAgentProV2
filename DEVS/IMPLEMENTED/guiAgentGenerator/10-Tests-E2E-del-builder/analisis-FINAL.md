# 🏛️ Análisis Técnico Final — Paso 10 — Tests E2E del builder

## 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| step | ✅ | 1 | ✅ (CLI cmd) | ✅ (Archivos listados) | 4.8 |
| lgn | ✅ | 1 | ✅ (Helper script) | ✅ (Rutas reales) | 4.2 |
| ops | ✅ | 1 | ✅ (HTML report) | ✅ (Verification table) | 4.0 |
| tnt | ✅ | 0 | ✅ (Check script) | ✅ (Code view) | 3.8 |
| anonymous | ✅ | 0 | ✅ (Visual report) | ✅ (Detailed tasks) | 4.5 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | Definición de "E2E" | ops, step | ✅ `pyproject.toml` | Se confirma que **NO hay Playwright**. E2E significa tests de escenario usando `TestClient` (API + DB + Logic). |
| 2 | Estado de `agent_templates` | lgn, step | ✅ `supabase/migrations/` | La tabla existe (`030_agent_templates.sql`) pero el test debe verificar que el seed del Paso 03 esté presente para el Happy Path. |
| 3 | Exportación ZIP en tests | step, ops | ✅ `bundles.py` | El test debe validar no solo la descarga, sino que el contenido del ZIP sea procesable por el Importador. |

---

### 1️⃣ Resumen Ejecutivo

El objetivo del Paso 10 es garantizar la integridad del **Builder Visual** mediante una suite de tests de escenarios que cubran el ciclo de vida completo: creación de agentes, uso de templates, pruebas en playground, ensamblaje de crews y exportación/importación de bundles.

**Correcciones críticas al plan:**
- **No se usará navegador:** Los tests se implementarán como escenarios de backend con `TestClient` simulando los payloads que genera el frontend de ReactFlow.
- **Validación Round-Trip:** Se prioriza el test de exportación e importación inmediata para asegurar que el "bundle-schema-v2" sea consistente en ambas direcciones.

**Decisión DX:** Se fusionan las propuestas en una única herramienta integrada: el comando `fap test builder`, que ejecutará la suite de tests y generará un reporte de integridad opcional en HTML.

---

### 2️⃣ Diseño Funcional Consolidado

#### Happy Path
1. **Petición a Tools:** El sistema lista herramientas disponibles (`/api/tools/available`).
2. **Creación de Agente:** Se envía un `POST /agents` con `soul_json` completo.
3. **Uso de Template:** Se recupera un template (`/api/templates/{id}`) y se simula el mapeo al formulario.
4. **Prueba (Playground):** Se ejecuta el agente (`POST /agents/{role}/run`) y se hace polling de resultados.
5. **Ensamblaje Crew:** Se envía un payload de grafo (nodos + edges) a `POST /workflows`.
6. **Exportación:** Se genera un bundle ZIP (`POST /api/bundles/export`).
7. **Importación:** Se re-importa el ZIP (`POST /api/bundles/import`) y se verifica persistencia.

#### Edge Cases MVP
- **Nombre de Agente Inválido:** Caracteres especiales o vacíos.
- **Goal/Backstory cortos:** Menos de 10 caracteres (disparar 422).
- **Template inexistente:** Intentar cargar un ID de template inválido.
- **Grafo de Crew sin agentes:** Intentar guardar una crew vacía.

---

### 3️⃣ Diseño Técnico Definitivo

#### Componentes y Modificaciones

- **Ruta real:** `tests/e2e/test_builder_scenarios.py` (Creación)
- **Tipo de cambio:** Creación
- **Descripción:** Suite principal de escenarios de integración para el Builder.
- **Patrones:** Seguir `tests/e2e/test_scenario_6_full_stack.py`.

- **Ruta real:** `src/cli/commands/test_builder.py` (Creación)
- **Tipo de cambio:** Creación
- **Descripción:** Comando CLI para ejecutar los tests del builder y generar reporte.
- **Firma:** `def run_builder_tests(org_id: str, html_report: bool = False): ...`

#### DX & Tooling — Tarea 0 (OBLIGATORIO)

### Herramienta: `fap test builder`
- **Qué automatiza:** La ejecución selectiva de los tests de integración del builder y la generación de un reporte de integridad HTML.
- **Tipo:** Comando CLI (Typer)
- **Ubicación:** `src/cli/commands/test_builder.py` registrado en `src/cli/main.py`.
- **Cómo se usa:** `fap test builder --org-id test-org --report`
- **Impacto para el usuario final:** Permite validar la integridad de todo el sistema del builder en < 10 segundos sin configurar entornos visuales.

---

### 4️⃣ Decisiones Tecnológicas

1. **Tests sin navegador:** Decidido por la ausencia de Playwright en las dependencias y la convención del proyecto de usar `TestClient` para escenarios E2E.
2. **Uso de Mocks de Supabase:** Se utilizará `mock_tenant_client` (de `conftest.py`) para asegurar que los tests sean idempotentes y no dependan de una base de datos externa, pero simulando transacciones reales.
3. **Mapeo de Grafo:** El test de CrewCanvas inyectará un JSON de tipo `CrewGraph` directamente al backend para validar la lógica de persistencia de workflows.

---

### 5️⃣ Criterios de Aceptación MVP

✅ [DATA] Mocks de `agent_catalog` y `workflow_templates` configurados con datos de prueba consistentes.
✅ [CODE] Archivo `tests/e2e/test_builder_scenarios.py` implementado con todos los casos Happy Path.
✅ [BACKEND] Endpoint `POST /api/bundles/export` validado con payloads complejos del builder.
✅ [FULLSTACK] Test de exportación + importación exitoso (Round-trip exitoso).
✅ [DX] Herramienta `fap test builder` ejecuta sin errores y genera reporte HTML si se solicita.

---

### 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Implementar `fap test builder` y registro en CLI | Media | 1.5h | Ninguna |
| 1 | Implementar fixtures de payloads del builder (Graph, SoulJson, Templates) | Baja | 1.0h | Tarea 0 |
| 2 | Escenario: CRUD Agente y validación de longitud (goal/backstory) | Media | 1.0h | Tarea 1 |
| 3 | Escenario: Playground (POST Run + Polling Task) | Media | 1.0h | Tarea 1 |
| 4 | Escenario: Crew Assembly (POST Workflow con grafo ReactFlow) | Alta | 1.5h | Tarea 1 |
| 5 | Escenario: Round-trip Export -> Import ZIP | Alta | 2.0h | Tareas 2-4 |
| **TOTAL** | | | **8h** | |

---

### 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Inconsistencia de Schema v2 | Alta | Cambios en `ExportService` no reflejados en `ImportService` | Test round-trip obligatorio en la suite. |
| Polling lento en Playground | Media | El mock de tareas no actualiza el estado | Usar un `side_effect` en el mock para cambiar de `pending` a `completed` tras N llamadas. |
| Grafo circular en Crew | Media | El usuario conecta agentes en círculo en el canvas | Incluir validación de ciclos en el test de `POST /workflows`. |

---

### 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Crear Agente desde Builder | Payload `AgentCreate` | 201 Created + Agente en mock DB |
| TP-2 | Exportar Crew Completa | `ExportBundleRequest` con 3 agentes | ZIP binario con `manifest.json` válido |
| TP-3 | Importar Bundle Exportado | ZIP de TP-2 | 201 Created + Componentes activos |

Comando para ejecutar tests: `uv run pytest tests/e2e/test_builder_scenarios.py`
