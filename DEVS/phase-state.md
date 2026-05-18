# 🗺️ Contexto de Fase — FluxAgentPro-v2

> **Documento fuente de verdad para todos los agentes.** Verificado contra código real.

---

## 1. Resumen de Fase

**Fase activa:** `guiAgentGenerator` — ⏳ **EN PROGRESO** (12/15 pasos completados)
**Objetivo:** Replicar experiencia de creación visual de agentes (Crew Studio) dentro del dashboard FAP, sobre stack propio (Next.js + ReactFlow + FastAPI + Supabase).

### Pasos en orden

| # | Paso | Estado |
|---|------|--------|
| 1 | Crear endpoint `GET /api/tools/available` | ✅ Completado |
| 2 | Crear endpoint `POST /api/bundles/export` | ✅ Completado |
| 3 | Endpoints CRUD para templates de agentes | ✅ Completado |
| 4 | Builder visual — UI con ReactFlow | ✅ Completado |
| 5 | Template Picker — librería de templates | ✅ Completado |
| 6 | Agent Playground — prueba en tiempo real | ✅ Completado |
| 7 | Canvas visual — ensamblaje de crews | ✅ Completado |
| 8 | ExportDialog + flujo completo de exportación | ✅ Completado |
| 9 | Navegación, breadcrumbs e integración | ✅ Completado |
| 10 | Tests E2E del builder | ✅ Completado |
| 11 | Estabilización Crítica y Fixes de Arquitectura | ✅ Completado |
| 12 | Protocolo de Validación y Dogfooding E2E | ✅ Completado |
| 13 | Robustez y Refactorización del Backend (DX) | ⏳ En Progreso |
| 14 | Optimización de UX y Rendimiento Frontend | ⏳ En Progreso |
| 15 | Expansión de Cobertura y DX de Tests | ⏳ En Progreso |

### Dependencias entre pasos
- Paso 2 requiere Paso 1 (tools list para export)
- Paso 4 requiere Pasos 1-3 (tools + export + templates para builder)
- Paso 6 requiere Paso 4 (AgentForm creado con `onRoleChange`) + `POST /agents/{role}/run` existente
- Paso 7 requiere Paso 4 (AgentForm + BuilderLayout) + `GET /agents` + `POST /bundles/export` existentes
- Paso 8 requiere Paso 2 (`POST /api/bundles/export` existente) + Paso 7 (CrewCanvas con `canvasToExportPayload()`) + Paso 4 (AgentForm con campos completos)
- Paso 9 requiere Pasos 4, 7 y 8 (integración de componentes navegación en rutas existentes)
- Paso 10 requiere Pasos 4, 6, 7 y 8 (escenarios de integración para todas las piezas del builder)
- Paso 11 requiere los Pasos 9 y 10 para corregir bugs de inyección de mocks, tipado en frontend, e idempotencia del seed de templates.
- Paso 12 requiere Pasos 1-11 (usa endpoints, CLI commands, y scripts existentes para validación E2E cruzada).

---

## 2. Estado Actual del Proyecto

> Verificado contra código fuente en `src/` y `supabase/migrations/`.

### ✅ Implementado y funcional

| Componente | Archivo | Línea | Notas |
|---|---|---|---|
| CLI `fap templates seed` | `src/cli/commands/templates_seed.py` | `seed_templates` | Semilla idempotente por UUID v5 y con check preventivo de tabla |
| CLI `fap doctor builder` | `src/cli/commands/doctor_builder.py` | `doctor_builder` | Suite de 6 diagnósticos críticos automatizados con formato visual *Rich* |
| CLI `fap test builder` | `src/cli/commands/test_builder.py:31` | `test_builder_app` registrado en `main.py` | Ejecuta suite E2E + reporte HTML |
| Suite Escenarios E2E | `tests/e2e/test_builder_scenarios.py` | 32 tests (TP-1 a TP-6) | 938 líneas, usa `TestClient` para validar integridad |
| `BuilderTabContext` / Provider | `dashboard/components/builder/BuilderTabContext.tsx` | Context API | Mantiene el estado global de la pestaña seleccionada en el Builder |
| `BuilderBreadcrumb` component | `dashboard/components/builder/BuilderBreadcrumb.tsx` | Breadcrumbs contextuales para el Builder | Sincronizado dinámicamente mediante Context API |
| `BuilderErrorBoundary` component | `dashboard/components/builder/BuilderErrorBoundary.tsx` | Class component para ReactFlow | Captura fallos SSR y de ReactFlow |
| Mocks Globales Estabilizados | `tests/e2e/conftest.py` | Fixture `global_llm_mock` | Aislado a la suite E2E para evitar regresiones de tests unitarios |
| Validación de Mocks en Tests | `scripts/validate_builder_mocks.py` | Checks de patching | Asegura que los parches de base de datos apunten a los namespaces correctos |
| CLI `fap dogfood check` | `src/cli/commands/dogfood_check.py` | `dogfood_check` registrado en `main.py` | Orquestador unificado de 7 validaciones E2E con reporte Rich + JSON para CI/CD. Flags: `--org-id`, `--json`, `--dry-run`. |
| Script `validate_builder_nav.py` (corregido) | `scripts/validate_builder_nav.py` | 11 checks críticos de UI | Correcciones aplicadas: regex reparado (D2), variable `uses_navmain` usada en decision (D1), check SSR mejorado para verificar `BuilderCanvas.tsx` con `dynamic()` + `ssr: false` (D3 mejorada). Exit code 0. |

*(Para componentes previos 1..8, ver histórico en DEVS/IMPLEMENTED)*

---

## 3. Contratos Técnicos Vigentes

### Stack detectado
- **Backend:** Python ≥3.12 + FastAPI (Pydantic v2)
- **Frontend:** TypeScript + Next.js (`dashboard/`)
- **DB:** Supabase (PostgreSQL) vía `supabase` Python client

### Modelos de datos (de migraciones reales)
- `agent_catalog(id UUID, org_id UUID, role TEXT, goal TEXT, backstory TEXT, llm_provider TEXT, llm_model TEXT, max_iter INTEGER, allowed_tools TEXT[], verbose BOOLEAN, reasoning BOOLEAN, inject_date BOOLEAN, memory BOOLEAN, is_active BOOLEAN, created_at TIMESTAMP WITH TIME ZONE)`
- `workflow_templates(id UUID, org_id UUID, flow_type TEXT, definition JSONB, created_at TIMESTAMP WITH TIME ZONE)`
- `agent_templates(id UUID, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INTEGER, is_system BOOLEAN, created_at TIMESTAMP WITH TIME ZONE)`

### Endpoints / APIs (rutas reales)
| Ruta | Método | Archivo | Auth |
|---|---|---|---|
| `/api/tools/available` | GET | `src/api/routes/tools.py` | `require_org_id` |
| `/api/bundles/export` | POST | `src/api/routes/bundles.py` | `require_org_id` |
| `/api/templates` | GET | `src/api/routes/templates.py` | `require_org_id` (maneja 503 ante fallos de DB) |
| `/api/templates/{id}` | GET | `src/api/routes/templates.py` | `require_org_id` (maneja 503 ante fallos de DB) |
| `/agents` | POST | `src/api/routes/agents.py` | `require_org_id` |
| `/agents/{role}/run` | POST | `src/api/routes/agents.py` | `require_org_id` |

### Patrones de código en uso

**1. Patrón E2E Integration (Backend)**
```python
# tests/e2e/test_builder_scenarios.py
with TestClient(app) as client:
    response = client.post("/agents", json=payload, headers=headers)
```

**2. Patrón Error Boundary (Frontend)**
```tsx
// dashboard/components/builder/BuilderErrorBoundary.tsx
export class BuilderErrorBoundary extends Component<Props, State> { ... }
```

**3. Idempotencia en Semillas (Sembrado Seguro):**
```python
# src/cli/commands/templates_seed.py
row = {
    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fap.system.template.{template['name']}")),
    ...
}
result = db.table("agent_templates").upsert(row, on_conflict="id", ignore_duplicates=True).execute()
```

---

## 4. Decisiones de Arquitectura Tomadas

| Decisión | Detalle | Verificación |
|---|---|---|
| **Idempotencia por PK (`id`) en Semillas** | Se reemplazó el upsert por `name` por un upsert directo hacia el PK `id` (UUID v5 determinista). Esto resolvió el error de base de datos `42P10` generado por la indexación parcial `WHERE is_system = TRUE`. | `templates_seed.py` |
| **Control Preventivo en CLI** | El comando de seed valida proactivamente que la tabla exista mediante una consulta ultra-rápida (`select.limit(1)`) antes de proceder, optimizando el DX operativa. | `templates_seed.py` |
| Breadcrumbs Reactivos | Sincronizados con el estado de las pestañas mediante Context API (`BuilderTabContext`), no con rutas físicas. | `BuilderBreadcrumb.tsx` |
| Testing sin Navegador | Uso de `TestClient` para validar lógica de negocio sin overhead de Playwright. | `test_builder_scenarios.py` |
| Dogfooding Tooling | El implementador debe usar `fap test builder` para verificar integridad. | `src/cli/commands/test_builder.py` |
| **Aislamiento en Mocks E2E** | La fixture `global_llm_mock` se encapsuló en `tests/e2e/conftest.py` en lugar de la raíz global de tests, previniendo falsos positivos en las suites unitarias del núcleo de la aplicación. | `tests/e2e/conftest.py` |
| **Validación Orquestada Unificada** | Un solo comando `fap dogfood check` centraliza 7 flujos de validación (doctor, seed, HTTP-vs-CLI, dry-run, agent create, bundle validate, UI integrity). Descarta scripts dispersos como `dogfood_validator.py`. | `dogfood_check.py` |
| **Validación Cruzada HTTP vs CLI** | `fap dogfood check` consume endpoints REST reales (`GET /api/tools/available`, `POST /agents`) vía `httpx` y compara estructuralmente contra respuestas locales para detectar desincronización de contratos. | `dogfood_check.py:111-150` |
| **SSR Check mejorado sobre FINAL (D3)** | La corrección D3 del análisis recomendaba buscar `CrewCanvas` en `BuilderLayout.tsx`, pero el componente real es `BuilderCanvas`. El implementador corrigió la premisa: verifica `BuilderCanvas.tsx` para confirmar `dynamic(CrewCanvas, { ssr: false })`. | `validate_builder_nav.py:163-200` |

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Notas |
|------|--------|----------------------|--------|-------|
| 01..08 | ✅ Completados | (Ver histórico) | (Ver histórico) | — |
| 09-Navegacion-breadcrumbs-integracion | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/09-Navegacion-breadcrumbs-e-integracion/` | `57a75de` | Integración del sidebar, skeletons y error boundaries para ReactFlow. |
| 10-Tests-E2E-del-builder | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/10-Tests-E2E-del-builder/` | `037deb9` | Suite de 32 escenarios pasando al 100% de éxito. |
| 11-Estabilizacion-Critica-y-Fixes-de-Arquitectura | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/11-Estabilizacion-Critica-y-Fixes-de-Arquitectura/` | `f56d9d7` | Resolución definitiva de error 42P10, sync dinámico de tabs y checks de mocks robustos. |
| 12-Protocolo-de-Validacion-y-Dogfooding-E2E | ✅ Completado | `DEVS/IMPLEMENTED/guiAgentGenerator/12-Protocolo-de-Validacion-y-Dogfooding-E2E/` | `e414bf1` | Comando `fap dogfood check` unificado. Script `validate_builder_nav.py` corregido (D1-D2-D3). Validación cruzada HTTP vs CLI. 9/9 criterios MVP. Validación APROBADA. |

---

## 6. Criterios Generales de Aceptación MVP

- ✅ Happy path funciona end-to-end (verificado vía CLI manual).
- ✅ Errores manejados sin crash.
- ✅ **Herramienta DX:** `fap test builder` funcional para ejecución de suite E2E.
- ✅ **Estabilidad de Semilla:** El comando `uv run fap templates seed` es 100% reutilizable de forma concurrente y segura.
- ✅ **Compilación Limpia:** `tsc --noEmit` y `ruff` pasan sin una sola falla.
- ✅ **DX Diagnóstico visual:** `fap doctor builder` provee visualización premium de 6 puntos de salud críticos.
- ✅ **Suite de tests verde:** 382 tests unitarios y 32 tests de integración/E2E ejecutándose con total éxito en entornos locales y pipelines.
- ✅ **Dogfooding Automatizado:** `fap dogfood check` ejecuta 7 validaciones E2E en ~10 segundos con reporte Rich + salida JSON para CI/CD. Reduce verificación manual de 15 min a comando único.
