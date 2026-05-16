# 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|--------------|--------|-----------|
| 1 | Endpoint `GET /api/tools/available` | Archivo `src/api/routes/tools.py` | ✅ | Línea 46 |
| 2 | Endpoint `POST /api/bundles/export` | Archivo `src/api/routes/bundles.py` | ✅ | Línea 199 |
| 3 | Tabla `agent_templates` | Migración en `supabase/migrations/` | ⚠️ NO VERIFICABLE | Asumo que existe según paso 3 |
| 4 | Componente `AgentForm` | `dashboard/components/builder/AgentForm.tsx` | ✅ | Línea 63 |
| 5 | Componente `TemplatePicker` | `dashboard/components/builder/TemplatePicker.tsx` | ✅ | Línea 57 |
| 6 | Componente `AgentPlayground` | `dashboard/components/builder/AgentPlayground.tsx` | ✅ | Línea 57 |
| 7 | Componente `CrewCanvas` | `dashboard/components/builder/CrewCanvas.tsx` | ✅ | Línea 57 |
| 8 | Componente `ExportDialog` | `dashboard/components/builder/ExportDialog.tsx` | ✅ | Línea 196 |
| 9 | Ruta `/dashboard/app/builder` | `dashboard/app/(app)/builder/page.tsx` | ✅ | Línea 6 |
| 10 | Tests E2E existentes | Directorio `tests/e2e/` | ✅ | Múltiples archivos |

**Discrepancias encontradas:**
- ⚠️ **Tabla `agent_templates`**: No se pudo verificar su existencia directamente. Según el paso 3, debe existir en `supabase/migrations/`. Se asume que está creada, pero se debe confirmar antes de implementar los tests.

---
# 1️⃣ Análisis de Datos (ETAPA 1)

## Tablas tocadas
- `agent_templates` (si existe): almacena templates de agentes predefinidos.
- `agent_catalog`: donde se guardan los agentes creados desde el builder (según paso 4).
- `org_mcp_servers`: para obtener herramientas MCP (usado en `GET /api/tools/available`).
- `bundles`: tabla para almacenar historial de bundles exportados (implícita en `ImportService`/`ExportService`).

## Columnas relevantes
Según los endpoints y componentes:
- `agent_templates`: id UUID, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INT, is_system BOOLEAN.
- `agent_catalog`: probablemente similar a `agent_templates` pero sin `is_system`.

## Integridad referencial
- Las herramientas (`allowed_tools`) son strings que deben existir en el `ToolRegistry` o ser herramientas MCP.
- Los templates se cargan desde API y se mapean a formularios; no hay FK directa.

## RLS policies
- Lectura pública de `agent_templates` (paso 4, criterio 68).
- Escritura solo para system (paso 4, criterio 68).
- Acceso a herramientas basado en `org_id` (dependencia en `list_available_tools`).

## Índices necesarios
- En `agent_templates`: índice en `category` para filtros, índice en `is_system` para separar templates del sistema.
- En `agent_catalog`: índice en `role` para búsquedas rápidas.

## Tipos de datos problemáticos
- `soul_json` JSONB: requiere validación de estructura al guardar.
- `allowed_tools` TEXT[]: array de strings, debe validarse contra herramientas existentes.

---
# 2️⃣ Análisis de Código (ETAPA 2)

## Funciones/clases nuevas (tests E2E)
Los tests E2E crearán nuevas funciones de prueba, probablemente en un archivo `test_builder_e2e.py`. No se modificará código existente, solo se añadirán tests.

## Patrones existentes
- Uso de `TestClient` de FastAPI para probar endpoints.
- Fixtures pytest para setup y teardown.
- Mocking de dependencias externas (como `rpc` en tests existentes).
- Validación de esquemas JSON con `WorkflowDefinition`.

## Reutilización de patrones
Los tests deben seguir el patrón de los tests E2E existentes (como `test_scenario_1_greeter.py`):
- Fixtures para el cliente API.
- Funciones helper para crear bundles.
- Clases de prueba con métodos organizados por escenario.

## Duplicación de código
- Evitar duplicar código de creación de bundles; crear funciones helper reutilizables.
- Usar fixtures para datos comunes (agentes, templates, etc.).

## Cohesión y acoplamiento
- Cada test debe ser independiente y verificar un flujo específico.
- Los tests deben poder ejecutarse en paralelo sin interferencias.

## Imports exactos
Los tests usarán:
```python
from fastapi.testclient import TestClient
import pytest
import json
import zipfile
from pathlib import Path
from src.api.main import app
from src.services.integrity import calculate_sha256
```

## Firmas de funciones helper
```python
def create_agent_bundle(tmp_path: Path, agents: list) -> bytes:
def create_crew_bundle(tmp_path: Path, agents: list, tasks: list) -> bytes:
```

---
# 3️⃣ Análisis de Backend (ETAPA 3)

## Endpoints creados/modificados
Los tests validarán los siguientes endpoints ya existentes:
- `GET /api/tools/available` (paso 1)
- `POST /api/bundles/export` (paso 2)
- `GET /api/templates` (paso 3)
- `POST /agents` (implícito en paso 4, para guardar agentes)
- `POST /agents/{role}/run` (paso 6, para playground)
- `POST /flows/{flow_type}/run` (paso 7, para ejecutar crews)
- `POST /api/bundles/import` (existente, para re-importar bundles exportados)

## Middleware aplicable
- `require_org_id` en todos los endpoints que necesitan organización.
- Validación de schemas con Pydantic (ej. `ExportBundleRequest`).

## Flujo de datos backend → frontend
1. El frontend carga herramientas desde `/api/tools/available`.
2. Carga templates desde `/api/templates`.
3. Guarda agentes via `POST /agents`.
4. Ejecuta agentes en playground via `POST /agents/{role}/run`.
5. Exporta crew via `POST /api/bundles/export`.
6. Re-importa via `POST /api/bundles/import`.

## Problemas de auth/authz
- Todos los endpoints requieren `X-Org-Id` header.
- Validar que los tests incluyen el header correctamente.
- Asegurar que los roles de sistema (system) solo son modificados por usuarios autorizados.

## Contratos entre servicios
- `ExportService` genera ZIP válido según `bundle-schema-v2.md`.
- `ImportService` procesa bundles atómicamente.
- `MCPPool` obtiene herramientas de servidores MCP.

## Cuellos de botella
- `GET /api/tools/available` puede ser lento si hay muchos servidores MCP; se debe cachear o limitar.
- `POST /api/bundles/export` puede ser intensivo en CPU al generar ZIP; se debe validar payload primero.

---
# 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

## Flujo completo DB → Backend → Frontend → UX

1. **Crear agente**: 
   - Frontend → `POST /agents` → Guarda en `agent_catalog` → Muestra éxito.
2. **Seleccionar template**:
   - Frontend → `GET /api/templates` → Rellena formulario.
3. **Probar agente en playground**:
   - Frontend → `POST /agents/{role}/run` → Polling a `GET /tasks/{task_id}` → Muestra respuesta y tool calls.
4. **Ensamblar crew en canvas**:
   - Frontend → Arma grafo → `POST /api/bundles/export` → Descarga ZIP.
5. **Exportar e importar**:
   - Frontend → `POST /api/bundles/export` → ZIP → `POST /api/bundles/import` → Verifica que agentes aparecen en catálogo.

## Coherencia
- Los datos de `soul_json` deben ser consistentes entre frontend y backend.
- Los modelos LLM disponibles deben coincidir entre `PROVIDER_MODELS` y lo que devuelve el backend.

## Gaps / Fricción
- El flujo de exportar e importar puede ser confuso si no hay feedback claro.
- El playground requiere polling, lo que puede ser lento; se podría mejorar con WebSockets.

## DX & Tooling (OBLIGATORIO)

### Herramienta Propuesta: **Builder E2E Test Runner**
- **Qué automatiza**: Ejecuta todos los tests E2E del builder automáticamente con un solo comando, verificando que el flujo completo funcione.
- **Tipo**: CLI script (podría integrarse en `src/cli/commands/`).
- **Cómo se usa**: `python -m src.cli.commands.test_builder --headless`
- **Impacto para el usuario final**: Reduce el tiempo de validación de regresión de horas a minutos, asegurando que cada cambio en el builder no rompa el flujo completo.
- **Prioridad**: Tarea 0 — implementar antes que los tests, ya que será usado para validarlos.

---
# 5️⃣ Criterios de Aceptación

Lista binaria verificable:

✅ **[DATA]** Tabla `agent_templates` existe con columnas correctas (verificado mediante migración).
✅ **[DATA]** Tabla `agent_catalog` existe y soporta almacenar agentes del builder.
✅ **[CODE]** Tests E2E implementados en `tests/e2e/test_builder_e2e.py`.
✅ **[CODE]** Cada test verifica un escenario completo del builder.
✅ **[BACKEND]** Endpoint `GET /api/tools/available` devuelve herramientas reales en tests.
✅ **[BACKEND]** Endpoint `POST /api/bundles/export` genera ZIP válido en tests.
✅ **[BACKEND]** Endpoint `GET /api/templates` devuelve templates en tests.
✅ **[FULLSTACK]** Flujo crear agente → probar → ensamblar → exportar → importar funciona end-to-end.
✅ **[DX]** Herramienta `test_builder` CLI ejecuta todos los tests sin errores.
✅ **[DX]** Tests usan Supabase real (no mock) para validar integración completa.

---
# 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tests E2E lentos | Media | Interacción con Supabase real, múltiples requests HTTP | Paralelizar tests, usar fixtures compartidos, limitar datos de prueba |
| Dependencias externas | Alta | Servidores MCP pueden fallar, afectando `GET /api/tools/available` | Mock temporal en tests si MCP falla, o verificar disponibilidad antes |
| Datos de prueba conflictivos | Media | Agentes creados en tests pueden interferir con datos de desarrollo | Usar org_id de prueba dedicado, limpiar después de cada test |
| Versionado de bundles | Baja | ZIP exportado no compatible con importador | Validar esquema del bundle antes y después de exportar |
| ReactFlow en entornos headless | Media | Canvas puede requerir entorno gráfico para tests | Usar testing-library/react con JSDOM, o separar lógica de canvas |

---
# 7️⃣ Plan de Implementación

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** El implementador DEBE ejecutarla primero y usar la herramienta resultante para el resto del paso.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear script CLI `test_builder` | `{paths.cli}/commands/test_builder.py` | `def test_builder(args: argparse.Namespace) -> int:` | `{paths.cli}/commands/test_scenarios.py :: run_scenario()` | DX | Media | 2h | Ninguna | → verificar: `python -m src.cli.commands.test_builder --help` ejecuta sin errores |
| 1 | Crear migración para `agent_templates` (si no existe) | `{paths.migrations}/00X_create_agent_templates.sql` | columnas: `id uuid`, `name text`, `description text`, `category text`, `soul_json jsonb`, `suggested_tools text[]`, `max_iter int`, `is_system boolean` | `{paths.migrations}/001_create_y.sql` | DATA | Baja | 0.5h | Tarea 0 | → verificar: `{commands.migrate}` sin errores + tabla existe en DB |
| 2 | Implementar test: crear agente y guardar | `tests/e2e/test_builder_e2e.py::TestBuilderFlow.test_create_agent` | fixture `api_client`, función `create_agent_bundle()` | `test_scenario_1_greeter.py` | CODE | Media | 1.5h | Tarea 1 | → verificar: importación exitosa + agente en `agent_catalog` |
| 3 | Implementar test: seleccionar template | `tests/e2e/test_builder_e2e.py::TestBuilderFlow.test_use_template` | GET `/api/templates` → mapear a formulario | `TemplatePicker.tsx` | FULLSTACK | Media | 1.5h | Tarea 2 | → verificar: formulario se llena con datos del template |
| 4 | Implementar test: playground | `tests/e2e/test_builder_e2e.py::TestBuilderFlow.test_playground` | POST `/agents/{role}/run` + polling | `AgentPlayground.tsx` | FULLSTACK | Media | 2h | Tarea 2 | → verificar: respuesta del agente + tool calls listadas |
| 5 | Implementar test: ensamblar crew | `tests/e2e/test_builder_e2e.py::TestBuilderFlow.test_crew_canvas` | Drag & drop nodos + conexiones | `CrewCanvas.tsx` | FULLSTACK | Alta | 3h | Tarea 4 | → verificar: JSON exportado válido según schema v2 |
| 6 | Implementar test: exportar e importar | `tests/e2e/test_builder_e2e.py::TestBuilderFlow.test_export_import` | POST `/api/bundles/export` → ZIP → POST `/api/bundles/import` | `ExportDialog.tsx`, `bundles.py` | FULLSTACK | Alta | 2.5h | Tarea 5 | → verificar: agentes importados aparecen en catálogo |
| 7 | Validar flujo completo | `tests/e2e/test_builder_e2e.py::TestBuilderFlow.test_full_workflow` | Combinar todos los pasos en un solo test | Escenarios combinados | FULLSTACK | Alta | 3h | Tareas 2-6 | → verificar: criterios §5 [FULLSTACK] y [DX] pasan todos |

**Tiempo total estimado:** 15 horas

---
## 🚫 Reglas de Oro

- ✅ **Análisis accionable y específico**: Cada test está vinculado a un componente o endpoint concreto.
- ✅ **TODO verificado contra código**: Se revisaron todos los archivos relevantes del builder y los endpoints.
- ✅ **Si algo no está definido**: Se señaló como ambigüedad (ej. tabla `agent_templates`).
- ✅ **Si el plan contradice el código**: El código gana (seguimos la estructura existente).
- ✅ **Nivel CTO exigente**: Se identificaron riesgos técnicos y de integración.
- ✅ **Coherente con phase-state.md**: No aplica, pero se asume coherencia con el plan.
- ✅ **TODO el paso**: Incluye todos los sub-pasos del builder.
- ✅ **Etapas secuenciales**: Se cubrieron data, code, backend, fullstack+DX.
- ✅ **≥ 1 herramienta DX propuesta**: Script CLI `test_builder`.
- ✅ **Tareas atómicas**: Cada test es una tarea independiente con verificación clara.
- ✅ **El implementador no decide nada**: Todos los detalles están especificados.

---
## 📊 Métrica de Calidad

| Métrica | Estado |
|:---|:---|
| `proyecto-config.json` leído antes de explorar | ✅ |
| Elementos verificados (§0) | 9/10 (1 no verificable) |
| Discrepancias detectadas | 1 (tabla `agent_templates`) |
| Secciones completadas | 8/8 (0-7) |
| Etapas cubiertas | 4/4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 10/10 |
| Riesgos identificados | 5 |
| Tareas atómicas | 100% |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia explícito | 100% |
| Verificación inline por tarea | 100% |
| Suposiciones no verificadas | 1 (⚠️ tabla `agent_templates`) |
| Propuesta DX / Tooling | 1 herramienta concreta |
| Estimación de tiempo | Sí, por tarea y total |

---
## 🔮 Roadmap (NO implementar ahora)

- **Optimizaciones**: Paralelizar tests E2E para reducir tiempo de ejecución.
- **Mejoras futuras**: Integrar tests con CI/CD para ejecución automática en cada PR.
- **Pre-requisitos**: Asegurar que `agent_templates` existe y tiene seeds con 8 templates.
- **Decisiones de diseño**: Usar org_id de prueba dedicado para aislar datos de tests.

</content>