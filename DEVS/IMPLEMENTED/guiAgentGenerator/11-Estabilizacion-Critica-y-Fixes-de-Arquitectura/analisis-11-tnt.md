# Análisis Técnico — Paso 11: Estabilización Crítica y Fixes de Arquitectura
**Agente:** tnt  
**Fecha:** 2026-05-16  
**Fase:** guiAgentGenerator  
**Prioridad:** Crítica

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `templates_seed.py` idempotencia | SELECT + INSERT sin ON CONFLICT | ⚠️ Riesgo | src/cli/commands/templates_seed.py:183-206 |
| 2 | `BuilderBreadcrumb` sync tabs | Recibe activeTab pero no actualiza | ⚠️ Discrepancia | dashboard/components/builder/BuilderBreadcrumb.tsx:18 |
| 3 | `page.tsx` breadcrumb hardcoded | activeTab="agent-form" fijo | ❌ Confirmado | dashboard/app/(app)/builder/page.tsx:9 |
| 4 | `BuilderLayout` tabs state | activeTab state existe pero no se propaga | ✅ Verificado | dashboard/components/builder/BuilderLayout.tsx:56 |
| 5 | Test mock injection | Tests usan mocks locales vs fixtures globales | ⚠️ Discrepancia | tests/e2e/test_builder_scenarios.py:176-186 |
| 6 | `zodResolver` en `AgentForm.tsx` | Uso correcto pero schema sin min length | ✅ Verificado | dashboard/components/builder/AgentForm.tsx:82,33-45 |
| 7 | `conftest.py` fixtures | No importados en tests de builder | ⚠️ Discrepancia | tests/conftest.py:111-141 |
| 8 | `agent_templates` tabla RLS | Migración 030 con políticas correctas | ✅ Verificado | supabase/migrations/030_agent_templates.sql:25-29 |

**Discrepancias encontradas:**
1. **ID-C02:** `templates_seed.py` no usa `ON CONFLICT` para idempotencia real — actualmente hace SELECT previo + INSERT, pero si falla la inserción parcial se deja en estado inconsistente.
2. **ID-C03:** `BuilderBreadcrumb` recibe `activeTab` como prop, pero `page.tsx` lo hardcodea a `"agent-form"`. El `BuilderLayout` tiene el estado real en `activeTab` pero no lo propaga.
3. **ID-C04:** Tests en `test_builder_scenarios.py` usan mocks locales (`fresh_db()`, `mock_select()`) en lugar de los fixtures globales de `conftest.py`, causando inconsistencia.
4. **ID-023:** El `zodResolver` está bien usado, pero el schema Zod no valida la longitud mínima de `goal`/`backstory` (requerimiento del plan dice ≥10 chars).

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema y Tablas
**Tabla `agent_templates` existe y está migrada (migración 030):**
```sql
CREATE TABLE agent_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    soul_json JSONB NOT NULL DEFAULT '{}',
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter INTEGER DEFAULT 5,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### RLS Policies
- `agent_templates_read`: SELECT para `authenticated`
- `agent_templates_write`: ALL para `service_role`

### Índices
- `idx_agent_templates_category` en columna `category`
- `idx_agent_templates_system_name` UNIQUE partial index para templates system

### Idempotencia DB Seed
**Problema:** El código actual en `templates_seed.py:195-206` hace:
```python
existing = db.table("agent_templates").select("id").eq("name", template["name"]).eq("is_system", True).execute()
if existing.data:
    continue  # skip
db.table("agent_templates").insert({...}).execute()
```
**Solución propuesta:** Usar `ON CONFLICT` con cláusula `WHERE is_system = TRUE`:
```sql
INSERT INTO agent_templates (...) VALUES (...)
ON CONFLICT (name) WHERE is_system = TRUE DO NOTHING
```

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a modificar
| Archivo | Función/Clase | Problema | Solución |
|---|---|---|---|
| `src/cli/commands/templates_seed.py` | `seed_templates()` | No idempotente con ON CONFLICT | Agregar `on_conflict="name"` en insert |
| `dashboard/app/(app)/builder/page.tsx` | `BuilderPage` | Prop `activeTab` hardcodeada | Leer de URL query param o usar contexto |
| `dashboard/components/builder/BuilderLayout.tsx` | `BuilderLayout` | Estado `activeTab` no exportado | Usar callback para sincronizar breadcrumb |
| `tests/e2e/test_builder_scenarios.py` | Múltiples tests | Mocks locales vs fixtures globales | Migrar a fixtures de `conftest.py` |
| `tests/conftest.py` | `mock_service_client` | No importado en tests de builder | Agregar import del fixture necesario |

### Patrones existentes a seguir
1. **Patrón de tablas con RLS global:** Ver `supabase/migrations/024_service_catalog.sql` para el patrón de tablas sin `org_id`.
2. **Patrón de error boundary:** `dashboard/components/builder/BuilderErrorBoundary.tsx` — class component que captura errores de ReactFlow.
3. **Patrón de tests con TestClient:** `tests/e2e/test_scenario_6_full_stack.py` — usa `TestClient(app)` con `dependency_overrides`.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints verificados
| Endpoint | Archivo | Auth Required | Estado |
|---|---|---|---|
| GET /api/tools/available | `src/api/routes/tools.py` | `require_org_id` | ✅ Funcional |
| POST /agents | `src/api/routes/agents.py` | `require_org_id` | ✅ Funcional |
| POST /api/bundles/export | `src/api/routes/bundles.py` | `require_org_id` | ✅ Funcional |
| GET /api/templates | `src/api/routes/templates.py` | None (RLS) | ✅ Funcional |

### Middleware y auth
El fixture `mock_auth` en `test_builder_scenarios.py:176-186` sobrescribe correctamente `verify_org_membership`. Sin embargo, los tests también necesitan mockear `get_service_client` y `get_tenant_client` consistentemente.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo identificado
```
DB (agent_templates)
    ↓
GET /api/templates → templates_seed.py → BuilderLayout
    ↓
Tabs cambian → activeTab state → BuilderBreadcrumb (debe actualizarse)
    ↓
Tests E2E validan con TestClient → conftest.py fixtures
```

### Gaps identificados
1. **Gap de estado:** El `activeTab` en `BuilderLayout` no se comunica con `BuilderBreadcrumb` en `page.tsx`.
2. **Gap de tests:** Los tests de builder no usan los fixtures globales, causando inyección inconsistente de mocks.

### Herramienta DX Propuesta: `fap validate-builder-fixes`
- **Qué automatiza:** Ejecuta verificación de los 6 fixes críticos del paso 11 (seed idempotente, breadcrumb sync, test suite estable, ts-check, mocks, regression).
- **Tipo:** CLI command
- **Cómo se usa:** `uv run fap validate-builder-fixes --all`
- **Impacto para el usuario final:** Verifica que los fixes aplicados no rompan otras suites de tests existentes.
- **Prioridad:** Tarea 0 — implementar primero

---

## 5️⃣ Criterios de Aceptación
```
✅ [DATA] fap templates seed ejecutable N veces sin error
✅ [CODE] BuilderBreadcrumb refleja cambios de pestaña en tiempo real
✅ [BACKEND] fap test-builder run pasa al 100% (32/32 escenarios)
✅ [FULLSTACK] tsc --noEmit sin errores en componentes del builder
✅ [DX] Herramienta fap validate-builder-fixes ejecuta sin errores
```

---

## 6️⃣ Riesgos
| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tests regresivos | Alta | `conftest.py` fixtures globales pueden afectar suites preexistentes | Auditar con `grep -r "mock_service_client" tests/` antes de aplicar |
| Race condition en seed | Media | Si `SELECT` y `INSERT` no son atómicos | Usar `ON CONFLICT` o `upsert` atómico |
| Loss of URL sync | Baja | Deep linking con `?tab=` no implementado | Agregar soporte de query params en BuilderLayout |

---

## 7️⃣ Plan de Implementación
| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap validate-builder-fixes` | `src/cli/commands/validate_builder_fixes.py` | `def run(check: str) -> bool` | `src/cli/commands/test_builder.py` | DX | Media | 0.5h | Ninguna | → verificar: `uv run fap validate-builder-fixes --help` ejecuta sin errores |
| 1 | Fix DB Seed | `src/cli/commands/templates_seed.py` | `def seed_templates(...):` | `src/cli/commands/templates_seed.py:195-206` | DATA | Baja | 0.5h | Tarea 0 | → verificar: `uv run fap templates seed` 3 veces sin error |
| 2 | Sync Breadcrumbs | `dashboard/components/builder/BuilderLayout.tsx` + `BuilderBreadcrumb.tsx` | `setActiveTab: (tab: string) => void` | `dashboard/components/builder/BuilderLayout.tsx` | FULLSTACK | Media | 1h | Tarea 0,1 | → verificar: cambiar tab y breadcrumb actualiza en vivo |
| 3 | Fix Test Suite | `tests/e2e/test_builder_scenarios.py` | Usar `mock_service_client` fixture | `tests/conftest.py:111-141` | CODE | Alta | 2h | Tarea 0 | → verificar: `uv run pytest tests/e2e/test_builder_scenarios.py -v` pasa 32/32 |
| 4 | TypeScript Integrity | `dashboard/components/builder/AgentForm.tsx` | Schema Zod con min(10) | `dashboard/components/builder/AgentForm.tsx:33-45` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `cd dashboard && tsc --noEmit` sin errores |
| 5 | Mocking Refactor | `tests/conftest.py` | Asegurar patches correctos | `tests/conftest.py:116-126` | CODE | Media | 1h | Tarea 0,3 | → verificar: `uv run pytest tests/unit/ -v` pasa sin regresiones |
| 6 | Regression Audit | `tests/conftest.py` | Scope de fixtures limitado | `tests/conftest.py` | CODE | Media | 1h | Tarea 4,5 | → verificar: suite completa `uv run pytest tests/` pasa |

**Tiempo total estimado:** 6 horas

---

## 🔮 Roadmap (NO implementar ahora)
- Agregar query params `?tab=` para deep linking en URLs del builder
- Implementar optimistic UI para el seed de templates
- Añadir test de regresión visual para verificar que los fixes no afectan componentes existentes