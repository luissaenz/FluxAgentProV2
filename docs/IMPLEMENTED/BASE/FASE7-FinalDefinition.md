# FAP — Fase 7: Plan de Implementación

**Capa de Presentación Declarativa**
Versión 1.0 — Abril 2026

| Campo | Valor |
|-------|-------|
| Documento base | `docs/FAP-Phase7-Presentation.md` |
| Plan técnico | `.claude/plans/cuddly-doodling-aurora.md` |
| Estado | Pendiente de implementación |

---

## 1. Decisión de Diseño

### Problema

El doc de Fase 7 propone agregar `presentation_config` a `agent_catalog`. Sin embargo, no hay join directo entre `tasks.flow_type` y `agent_catalog.role`. El Dashboard ya tiene `task.flow_type` disponible, pero necesitaría un mapping intermedio para llegar a `agent_catalog`.

### Solución adoptada

Nueva tabla **`flow_presentations`** con lookup directo por `flow_type`:

```
flow_presentations(org_id, flow_type, presentation_config)
```

- Lookup directo: `WHERE org_id = X AND flow_type = Y`
- Multi-tenant con RLS (mismo patrón que tablas existentes)
- No requiere modificar `agent_catalog`

### flow_types reales en BD (verificados)

| flow_type | Sistema | HITL |
|-----------|---------|------|
| `PreventaFlow` | Bartenders NOA | No |
| `ReservaFlow` | Bartenders NOA | Condicional (faltante stock) |
| `AlertaClimaFlow` | Bartenders NOA | Obligatorio (compra emergencia) |
| `CierreFlow` | Bartenders NOA | Condicional (margen < 10%) |
| `CotizacionFlow` | CoctelPro | Sí |
| `architect_flow` | Plataforma | No |
| `multi_crew` | Plataforma | No |

---

## 2. Esquemas de Output por Flow

Datos reales que produce cada flow en `tasks.result` (base para presentation_config):

### PreventaFlow
```json
{
  "evento_id": "evt-xxx",
  "cotizacion_id": "cot-xxx",
  "escandallo_total": 3584505,
  "opcion_basica": 4301406,
  "opcion_recomendada": 5376757,
  "opcion_premium": 7167676,
  "factor_climatico": 15,
  "bartenders_necesarios": 3
}
```

### ReservaFlow
```json
{
  "evento_id": "evt-xxx",
  "status": "confirmado",
  "bartenders": ["Nombre1", "Nombre2"],
  "necesita_head": true,
  "stock_ok": true,
  "hoja_de_ruta": "texto markdown con instrucciones"
}
```

### AlertaClimaFlow (sin alerta)
```json
{
  "evento_id": "evt-xxx",
  "alerta_roja": false,
  "accion": "sin_accion",
  "mensaje": "Temperatura dentro del rango normal..."
}
```

### AlertaClimaFlow (con alerta)
```json
{
  "evento_id": "evt-xxx",
  "alerta_roja": true,
  "accion": "compra_aprobada",
  "orden_id": "ord-xxx",
  "total_ars": 45000,
  "mensaje": "Compra de emergencia aprobada..."
}
```

### CierreFlow
```json
{
  "evento_id": "evt-xxx",
  "status": "cerrado",
  "auditoria_id": "aud-xxx",
  "margen_pct": 33.47,
  "ganancia_neta": 1792252,
  "proxima_contacto": "2027-03-15"
}
```

---

## 3. Arquitectura de Archivos

### Archivos nuevos (18)

```
supabase/
  migrations/
    016_flow_presentations.sql          # Tabla + RLS + índice
    017_seed_flow_presentations.sql     # INSERTs para 7 flows

scripts/
  seed_flow_presentations.py            # Seed programático por org_id
  verify_rls_016.sql                    # Verificación RLS manual

dashboard/
  lib/presentation/
    types.ts                            # Interfaces TS (PresentationConfig, FieldRef, etc.)
    resolve.ts                          # JSONPath resolver (~20 líneas, sin deps)
    format.ts                           # Formateadores (currency_ars, pct, date, etc.)
    fallback.ts                         # Helpers fallback (formatFlowType, snakeCaseToTitle)
    index.ts                            # Re-exports

  hooks/
    usePresentationConfig.ts            # React Query hook → flow_presentations

  components/presentation/
    ResultKeyValueTable.tsx             # Tabla key/value genérica (reemplaza JSON crudo)
    PresentedTaskCard.tsx               # Card configurable para Kanban
    PresentedTaskDetail.tsx             # Orquestador de vista detalle
    SectionRenderer.tsx                 # Dispatcher por section.type

    sections/
      FieldsSection.tsx                 # Lista label-valor en <dl>
      TableSection.tsx                  # Tabla con columnas + highlight_where
      AccordionSection.tsx              # Colapsable con chevron animado
      KeyValueListSection.tsx           # Lista key-value sin header
```

### Archivos a modificar (6)

```
dashboard/
  components/kanban/
    TaskCard.tsx                         # formatFlowType + línea de resumen
    KanbanBoard.tsx                      # Prop configs para PresentedTaskCard
    KanbanColumn.tsx                     # Prop configs pasado a cards

  app/(app)/
    kanban/page.tsx                      # usePresentationConfigs + reemplazar JSON
    tasks/[id]/page.tsx                  # PresentedTaskDetail en vez de <pre>

  package.json                           # vitest + testing-library (devDeps)
```

---

## 4. Iteraciones de Implementación

### Iteración 1 — Fallback Inteligente (Quick Win)

**Objetivo:** Eliminar JSON crudo de toda la UI sin necesitar configuración por flow.

**Scope:**

| Archivo | Cambio |
|---------|--------|
| `dashboard/lib/presentation/fallback.ts` | **NUEVO** — `formatFlowType()`, `snakeCaseToTitle()`, `extractCardSummary()` |
| `dashboard/components/presentation/ResultKeyValueTable.tsx` | **NUEVO** — Tabla key/value con manejo de tipos (bool→Sí/No, null→—, arrays→comma-sep, nested→sub-filas) |
| `dashboard/components/kanban/TaskCard.tsx` | **MOD** línea 32: `{task.flow_type}` → `{formatFlowType(task.flow_type)}` + línea resumen |
| `dashboard/app/(app)/tasks/[id]/page.tsx` | **MOD** líneas 88-96: `<pre>JSON.stringify</pre>` → `<ResultKeyValueTable>` |
| `dashboard/app/(app)/kanban/page.tsx` | **MOD** líneas 56-62: idem en slide-over panel |

**Resultado esperado:** Supervisor ve tablas legibles en vez de JSON en todas las vistas.

---

### Iteración 2 — Card Configurable + Infraestructura

**Objetivo:** Tabla `flow_presentations` en Supabase + Cards del Kanban configurables por flow.

**Scope DB:**

```sql
CREATE TABLE IF NOT EXISTS flow_presentations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    flow_type           TEXT NOT NULL,
    presentation_config JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, flow_type)
);

ALTER TABLE flow_presentations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "flow_presentations_access" ON flow_presentations
    FOR ALL USING (
        auth.role() = 'service_role'
        OR org_id::text = current_setting('app.org_id', TRUE)
    );
```

**Scope Dashboard:**

| Archivo | Cambio |
|---------|--------|
| `dashboard/lib/presentation/types.ts` | **NUEVO** — `PresentationConfig`, `CardConfig`, `DetailConfig`, `FieldRef`, `FormatType`, section types |
| `dashboard/lib/presentation/resolve.ts` | **NUEVO** — `resolvePath("$.campo.subcampo", data)` → valor o undefined |
| `dashboard/lib/presentation/format.ts` | **NUEVO** — `formatValue(val, "currency_ars")` → `"$5.376.757"` |
| `dashboard/hooks/usePresentationConfig.ts` | **NUEVO** — React Query hook con `staleTime: 5min` |
| `dashboard/components/presentation/PresentedTaskCard.tsx` | **NUEVO** — Card con fallback si config es null |
| `dashboard/components/kanban/KanbanBoard.tsx` | **MOD** — Acepta prop `configs` |
| `dashboard/components/kanban/KanbanColumn.tsx` | **MOD** — Pasa `configs` a cards |
| `dashboard/app/(app)/kanban/page.tsx` | **MOD** — Llama `usePresentationConfigs()` |

**Formatos disponibles:**

| Formato | Input | Output |
|---------|-------|--------|
| `currency_ars` | `5376757` | `$5.376.757` |
| `currency_usd` | `3720` | `USD 3.720` |
| `pct` | `0.45` o `45` | `45%` |
| `date` | `"2026-01-15"` | `15/01/2026` |
| `datetime_short` | `"2026-01-15T14:30:00"` | `15/01 14:30` |
| `boolean_yn` | `true` | `Sí` |

---

### Iteración 3 — Detalle Configurable

**Objetivo:** Vista detalle con secciones configurables (fields, table, accordion, key_value_list).

**Scope:**

| Archivo | Cambio |
|---------|--------|
| `sections/FieldsSection.tsx` | **NUEVO** — `<dl>` con pares label-valor |
| `sections/TableSection.tsx` | **NUEVO** — Tabla con columnas configurables + `highlight_where` |
| `sections/AccordionSection.tsx` | **NUEVO** — Toggle con `useState`, sin dependencia Radix |
| `sections/KeyValueListSection.tsx` | **NUEVO** — Lista sin header chrome |
| `SectionRenderer.tsx` | **NUEVO** — Switch dispatcher por `section.type` |
| `PresentedTaskDetail.tsx` | **NUEVO** — Si config null → `<ResultKeyValueTable>`, si config existe → secciones |
| `tasks/[id]/page.tsx` | **MOD** — `<ResultKeyValueTable>` → `<PresentedTaskDetail>` |
| `kanban/page.tsx` | **MOD** — Slide-over usa `<PresentedTaskDetail>` |

**Tipos de sección:**

| Tipo | Uso | Ejemplo |
|------|-----|---------|
| `fields` | Ficha de datos | Datos del evento, resumen cliente |
| `table` | Tabla comparativa | 3 opciones de precio |
| `accordion` | Detalle colapsable | Escandallo de costos |
| `key_value_list` | Lista simple | Ajustes aplicados |

---

### Iteración 4 — Seed Data para Todos los Flows

**Objetivo:** Insertar `presentation_config` para los 7 flow_types conocidos.

**Configs por flow:**

| flow_type | Card | Detalle |
|-----------|------|---------|
| `PreventaFlow` | title=evento_id, amount=opcion_recomendada (currency_ars) | fields (cotización) + key_value_list (3 opciones) + fields (escandallo) |
| `ReservaFlow` | title=evento_id | fields (reserva) + key_value_list (bartenders) + accordion (hoja de ruta) |
| `AlertaClimaFlow` | title=evento_id + icon alerta, amount=total_ars (currency_ars) | fields (alerta) + fields (mensaje) |
| `CierreFlow` | title=evento_id, amount=ganancia_neta (currency_ars) | fields (cierre: margen, auditoría, próximo contacto) |
| `CotizacionFlow` | title="Cotización", amount=total (currency_ars) | fields (total, descuento) |
| `architect_flow` | fallback | fallback |
| `multi_crew` | fallback | fallback |

**Archivos:**
- `supabase/migrations/017_seed_flow_presentations.sql` — INSERTs SQL
- `scripts/seed_flow_presentations.py` — Script Python para seed por org_id

---

## 5. Plan de Testeo

### 5.1 Tests Unitarios Frontend (Vitest)

**Setup:** `vitest` + `@testing-library/react` + `@testing-library/jest-dom` como devDependencies.

| Test | Qué valida |
|------|-----------|
| `resolve.test.ts` | `$.field`, `$.nested.field`, missing paths → undefined, null data |
| `format.test.ts` | `currency_ars(5376757)` → `"$5.376.757"`, `pct(0.45)` → `"45%"`, `date("2026-01-15")` → `"15/01/2026"`, `boolean_yn(true)` → `"Sí"`, undefined → `"—"` |
| `fallback.test.ts` | `formatFlowType("PreventaFlow")` → `"Preventa"`, `snakeCaseToTitle("opcion_recomendada")` → `"Opcion Recomendada"` |
| `ResultKeyValueTable.test.tsx` | Renderiza keys de objeto plano, nested objects, arrays, handles null/empty |
| `SectionRenderer.test.tsx` | Despacha al componente correcto por type, maneja type desconocido |

### 5.2 Tests de Integración Backend

**`tests/integration/test_flow_presentations.py`**:
- CRUD en `flow_presentations` con service_role
- Lectura con org_id context correcto
- Aislamiento: insertar con org_a, leer con org_b → vacío

### 5.3 Verificación RLS

**`scripts/verify_rls_016.sql`** — Script manual para Supabase SQL Editor:

```sql
-- 1. Service role puede insertar en cualquier org
INSERT INTO flow_presentations (org_id, flow_type, presentation_config)
VALUES ('<org_a>', 'TestFlow', '{"card": {"title": {"from": "$.test"}}}');

-- 2. Con contexto org_a: ve solo sus filas
SELECT set_config('app.org_id', '<org_a>', true);
SELECT count(*) FROM flow_presentations;

-- 3. Con contexto org_b: no ve filas de org_a
SELECT set_config('app.org_id', '<org_b>', true);
SELECT count(*) FROM flow_presentations;  -- debe ser 0

-- 4. Cleanup
DELETE FROM flow_presentations WHERE flow_type = 'TestFlow';
```

### 5.4 Test E2E Manual

1. Ejecutar `POST /bartenders/preventa` con `org_id` del Dashboard (`6877612f-3768-44bf-b6e3-b2d1453c3de9`)
2. Esperar completion (~10s)
3. Kanban: Card muestra "Preventa — $X.XXX.XXX" en vez de "PreventaFlow"
4. Click en card → panel lateral muestra tabla key/value o secciones configuradas
5. `/tasks/{id}` → Detalle con labels y formateo, no JSON crudo

---

## 6. Premisas Inmutables

- CrewAI no se toca (`src/crews/`, `src/flows/multi_crew_flow.py`)
- `tasks.result` sigue siendo JSONB sin cambios
- La presentación se aplica **client-side** en el Dashboard
- Botones Aprobar/Rechazar quedan fuera de `presentation_config`
- Los agentes nunca saben cómo se muestra su output

---

## 7. Criterios de Aceptación

| # | Criterio |
|---|----------|
| 1 | Supervisor entiende output de cualquier agente sin JSON visible |
| 2 | Card del Kanban muestra info de negocio, no IDs ni JSON |
| 3 | Detalle con `presentation_config` no contiene JSON crudo |
| 4 | Fallback genérico muestra ficha key/value, no `<pre>` |
| 5 | Botones Aprobar/Rechazar NO son parte de `presentation_config` |
| 6 | CrewAI no fue modificado |
| 7 | `tasks.result` sigue siendo JSONB sin restricciones |
| 8 | `presentation_config` NULL funciona correctamente (fallback) |

---

## 8. Archivos de Referencia

| Archivo | Relevancia |
|---------|-----------|
| `dashboard/components/kanban/TaskCard.tsx` | Card actual a modificar |
| `dashboard/app/(app)/tasks/[id]/page.tsx` | Vista detalle actual (JSON crudo) |
| `dashboard/app/(app)/kanban/page.tsx` | Kanban + slide-over |
| `dashboard/hooks/useTasks.ts` | Patrón React Query a replicar |
| `dashboard/lib/supabase.ts` | Client Supabase |
| `dashboard/lib/types.ts` | Tipo `Task` existente |
| `dashboard/lib/constants.ts` | `STATUS_BADGES`, `KANBAN_COLUMNS` |
| `supabase/migrations/004_agent_catalog.sql` | Patrón RLS |
| `supabase/migrations/010_service_role_rls_bypass.sql` | Patrón service_role bypass |
| `src/flows/bartenders/*_flow.py` | Output schemas reales |

---

*Generado: 2026-04-04*
