# 🗺️ Contexto de Fase — FluxAgentPro-v2

> **Documento fuente de verdad para todos los agentes.** Verificado contra código real.

---

## 1. Resumen de Fase

**Fase activa:** `guiAgentGenerator` — ⏳ **EN PROGRESO** (8/10 pasos completados)
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
| 9 | Navegación, breadcrumbs e integración | ❌ **RECHAZADO** |
| 10 | Tests E2E del builder | ❌ **RECHAZADO** |

### Dependencias entre pasos
- Paso 2 requiere Paso 1 (tools list para export)
- Paso 4 requiere Pasos 1-3 (tools + export + templates para builder)
- Paso 6 requiere Paso 4 (AgentForm creado con `onRoleChange`) + `POST /agents/{role}/run` existente
- Paso 7 requiere Paso 4 (AgentForm + BuilderLayout) + `GET /agents` + `POST /bundles/export` existentes
- Paso 8 requiere Paso 2 (`POST /api/bundles/export` existente) + Paso 7 (CrewCanvas con `canvasToExportPayload()`) + Paso 4 (AgentForm con campos completos)
- Paso 9 requiere Pasos 4, 7 y 8 (integración de componentes navegación en rutas existentes)
- Paso 10 requiere Pasos 4, 6, 7 y 8 (escenarios de integración para todas las piezas del builder)

---

## 2. Estado Actual del Proyecto

> Verificado contra código fuente en `src/` y `supabase/migrations/`.

### ✅ Implementado y funcional

| Componente | Archivo | Línea | Notas |
|---|---|---|---|
| CLI `fap test builder` | `src/cli/commands/test_builder.py:31` | `test_builder_app` registrado en `main.py` | Ejecuta suite E2E + reporte HTML |
| Suite Escenarios E2E | `tests/e2e/test_builder_scenarios.py` | 32 tests (TP-1 a TP-6) | 938 líneas, usa `TestClient` para validar integridad |
| `BuilderBreadcrumb` component | `dashboard/components/builder/BuilderBreadcrumb.tsx` | Breadcrumbs contextuales para el Builder | — |
| `BuilderErrorBoundary` component | `dashboard/components/builder/BuilderErrorBoundary.tsx` | Class component para ReactFlow | — |
| Scripts de validación | `scripts/validate_builder_nav.py` | 11 checks de integridad | — |

*(Para componentes previos 1..8, ver histórico en DEVS/IMPLEMENTED)*

### ⚠️ Parcialmente implementado

| Componente | Archivo | Problema | Notas |
|---|---|---|---|
| Sincronización Breadcrumb | `BuilderBreadcrumb.tsx` | Prop `activeTab` hardcoded en `page.tsx` | No refleja cambios de pestaña en `BuilderLayout` |
| Suite de Tests E2E | `test_builder_scenarios.py` | Fallo masiva de aserciones (21/32) | Problemas de inyección de mocks en rutas API |

---

## 3. Contratos Técnicos Vigentes

### Stack detectado
- **Backend:** Python ≥3.12 + FastAPI (Pydantic v2)
- **Frontend:** TypeScript + Next.js (`dashboard/`)
- **DB:** Supabase (PostgreSQL) vía `supabase` Python client

### Modelos de datos (de migraciones reales)
- `agent_catalog(id UUID, org_id UUID, role TEXT, goal TEXT, backstory TEXT, ...)`
- `workflow_templates(id UUID, org_id UUID, flow_type TEXT, definition JSONB, ...)`
- `agent_templates(id UUID, name TEXT, soul_json JSONB, suggested_tools TEXT[], ...)`

### Endpoints / APIs (rutas reales)
| Ruta | Método | Archivo | Auth |
|---|---|---|---|
| `/api/tools/available` | GET | `src/api/routes/tools.py` | `require_org_id` |
| `/agents` | POST | `src/api/routes/agents.py` | `require_org_id` |
| `/api/bundles/export` | POST | `src/api/routes/bundles.py` | `require_org_id` |
| `/workflows` | POST | `src/api/routes/workflows.py` | `require_org_id` |

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

---

## 4. Decisiones de Arquitectura Tomadas

| Decisión | Detalle | Verificación |
|---|---|---|
| Breadcrumbs Reactivos | Sincronizados con el estado de las pestañas, no con rutas físicas. | `BuilderBreadcrumb.tsx` |
| Testing sin Navegador | Uso de `TestClient` para validar lógica de negocio sin overhead de Playwright. | `test_builder_scenarios.py` |
| Dogfooding Tooling | El implementador debe usar `fap test builder` para verificar integridad. | `src/cli/commands/test_builder.py` |

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Archivados En | Commit | Notas |
|------|--------|----------------------|--------|-------|
| 01..08 | ✅ Completados | (Ver histórico) | (Ver histórico) | — |
| 09-Navegacion-breadcrumbs-integracion | ❌ **RECHAZADO** | `DEVS/IMPLEMENTED/guiAgentGenerator/09-Navegacion-breadcrumbs-e-integracion/` | `57a75de` | Rechazado por fallo en sincronización de tabs. |
| 10-Tests-E2E-del-builder | ❌ **RECHAZADO** | `DEVS/IMPLEMENTED/guiAgentGenerator/10-Tests-E2E-del-builder/` | `037deb9` | Rechazado por fallo en aserciones de mocks (21/32 fallos). |

---

## 6. Criterios Generales de Aceptación MVP

- ✅ Happy path funciona end-to-end (verificado vía CLI manual).
- ✅ Errores manejados sin crash.
- ✅ **Herramienta DX:** `fap test builder` funcional para ejecución de suite E2E.
- ❌ **PENDIENTE:** Sincronización dinámica de Breadcrumbs con el estado de las tabs.
- ❌ **PENDIENTE:** Estabilización de la suite de tests E2E (Paso 10).
