# Análisis Técnico — Paso 4: Builder Layout + Agent Form

**Agente:** laguna | **Fecha:** 2026-05-14

---

## 0️⃣ Verificación (18 elementos)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `reactflow` en package.json | grep `dashboard/package.json` | ❌ DISCREPANCIA | NO existe. Renombrado a `@xyflow/react` v12 |
| 2 | `dashboard/app/(app)/builder/` existe | ls | ✅ NO existe | Crear directorio |
| 3 | `dashboard/components/builder/` existe | ls | ✅ NO existe | Crear directorio |
| 4 | Tabla `agent_catalog` | `supabase/migrations/004_agent_catalog.sql:6-17` | ✅ VERIFICADO | id, org_id, role, soul_json, allowed_tools, max_iter |
| 5 | Columna `model` en DB | grep migración 004 | ❌ NO EXISTE | En types.ts solo |
| 6 | Endpoint `/api/tools/available` | `src/api/routes/tools.py:46-63` | ✅ VERIFICADO | GET con filtro source/category |
| 7 | Componente Switch | `dashboard/components/ui/switch.tsx` | ✅ VERIFICADO | shadcn/ui |
| 8 | Componente Select | `dashboard/components/ui/select.tsx` | ✅ VERIFICADO | radix-ui |
| 9 | Slider component | grep `dashboard/components/ui/` | ❌ NO EXISTE | Requerido para max_iter |
| 10 | Multi-select component | grep `dashboard/components/` | ❌ NO EXISTE | Requerido para tools |
| 11 | react-hook-form instalado | `dashboard/package.json:40` | ✅ VERIFICADO | v7.72.1 |
| 12 | @hookform/resolvers | `dashboard/package.json:13` | ✅ VERIFICADO | v5.2.2 |
| 13 | zod disponible | peer dep de @hookform/resolvers | ⚠️ NO DIRECTO | Instalar zod |
| 14 | useCurrentOrg hook | `dashboard/hooks/useCurrentOrg.ts` | ✅ VERIFICADO | retorna { orgId, currentOrg } |
| 15 | Patrón save Supabase directo | `dashboard/app/(app)/agents/page.tsx:21-26` | ✅ VERIFICADO | createClient().from('agent_catalog') |
| 16 | Builder en nav-main.tsx | grep `Wand2` | ❌ NO EXISTE | NavItem "Builder" pendiente |
| 17 | useQuery de tanstack | `dashboard/app/(app)/agents/page.tsx:17` | ✅ VERIFICADO | @tanstack/react-query v5.62.8 |
| 18 | Soul_json estructura DB | migración 004 | ✅ VERIFICADO | JSONB para goal/backstory/config |

### Discrepancias

| ID | Problema | Fix |
|---|---|---|
| D1 | `reactflow` → `@xyflow/react` v12 | npm install @xyflow/react (API cambió) |
| D2 | `agent_catalog` no tiene `model`, `llm_provider`, toggles | Guardar en `soul_json` JSONB |
| D3 | No Slider component | Crear `dashboard/components/ui/slider.tsx` |
| D4 | No multi-select para tools | Usar Command con checkboxes |
| D5 | zod no en dependencies | npm install zod |
| D6 | NavItem Builder no existe | Agregar a `defaultNavItems` en nav-main.tsx |

---

## 1️⃣ Análisis de Datos

### Tabla afectada: `agent_catalog`

| Columna | Tipo | Formulario |
|---|---|---|
| id | UUID PK | auto |
| org_id | UUID FK | useCurrentOrg() |
| role | TEXT | Input requerido |
| soul_json | JSONB | goal, backstory, llm_provider, model, config |
| allowed_tools | TEXT[] | Multi-select |
| max_iter | INTEGER | Slider 1-10 default 3 |

### Schema soul_json

```json
{
  "goal": "string",
  "backstory": "string", 
  "llm_provider": "groq|openai|anthropic|openrouter",
  "llm_model": "string",
  "config": {
    "verbose": true,
    "reasoning": false,
    "inject_date": true,
    "memory": true
  }
}
```

---

## 2️⃣ Análisis de Código

### Archivos a crear

| Archivo | Firma | Patrón |
|---|---|---|
| `dashboard/app/(app)/builder/page.tsx` | `export default function BuilderPage()` | `dashboard/app/(app)/agents/page.tsx` |
| `dashboard/components/builder/BuilderLayout.tsx` | `export function BuilderLayout()` | Split panel 60/40 flex |
| `dashboard/components/builder/AgentForm.tsx` | `export function AgentForm({ onSave, onClear })` | react-hook-form + zod |
| `dashboard/components/builder/BuilderCanvas.tsx` | `export function BuilderCanvas()` | EmptyState placeholder |
| `dashboard/components/ui/slider.tsx` | Radix Slider | `dashboard/components/ui/switch.tsx` |
| `dashboard/components/builder/ToolMultiSelect.tsx` | `export function ToolMultiSelect({ options, values, onChange })` | Command + checkboxes |
| `dashboard/lib/builder-schema.ts` | `export const agentFormSchema = z.object(...)` | Zod schema |

---

## 3️⃣ Análisis de Backend

| Endpoint | Uso |
|---|---|
| GET `/api/tools/available` | Cargar tools en multi-select |
| Supabase directo `agent_catalog.insert()` | Save agent desde frontend |

No nuevos endpoints. Backend completo en pasos 1-3.

---

## 4️⃣ Fullstack + DX

### Flujo
Builder Page → AgentForm (role, goal, backstory, llm, tools, toggles) → Supabase INSERT

### Herramienta DX

```
### Herramienta: scaffold-builder
- Qué: Script que genera estructura completa builder
- Tipo: npm script
- Uso: npm run scaffold:builder
- Archivos: page.tsx, AgentForm.tsx, BuilderCanvas.tsx, BuilderLayout.tsx, schema.ts
- Impacto: 15min → 1seg setup
- Prioridad: Tarea 0
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] agent_catalog tiene columnas correctas
✅ [DATA] soul_json almacena goal, backstory, config completo
✅ [CODE] BuilderLayout renderiza split 60/40 responsive
✅ [CODE] AgentForm usa react-hook-form + zod
✅ [CODE] Tools cargan desde GET /api/tools/available
✅ [CODE] Validación: role/goal/backstory requeridos, max_iter 1-10
✅ [CODE] Provider→Model Select dinámico
✅ [CODE] Slider max_iter funcional
✅ [CODE] 4 toggles (verbose, reasoning, inject_date, memory)
✅ [FULLSTACK] Save inserta en agent_catalog con org_id
✅ [FULLSTACK] Clear resetea formulario
✅ [FULLSTACK] Nav sidebar incluye "Builder"
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Fix |
|---|---|---|
| RLS bloquea INSERT desde frontend | Alta | Verificar policy `agent_catalog_tenant_isolation` permite INSERT |
| @xyflow/react API cambió | Media | No usar ReactFlow aún (canvas placeholder hasta Paso 07) |
| Sin form complejo previo | Baja | Establecer patrón react-hook-form + zod |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Verificación |
|---|---|---|---|
| 0 | DX: Script scaffold-builder | `dashboard/package.json` scripts | → `npm run scaffold:builder` crea archivos |
| 1 | Instalar deps | `dashboard/package.json` | → grep "@xyflow/react" ✓, "zod" ✓ |
| 2 | Slider component | `dashboard/components/ui/slider.tsx` | → import sin error |
| 3 | Zod schema | `dashboard/lib/builder-schema.ts` | → schema compila |
| 4 | ToolMultiSelect | `dashboard/components/builder/ToolMultiSelect.tsx` | → carga options desde API |
| 5 | AgentForm | `dashboard/components/builder/AgentForm.tsx` | → 11 campos + Save/Clear |
| 6 | BuilderCanvas | `dashboard/components/builder/BuilderCanvas.tsx` | → EmptyState visible |
| 7 | BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | → Split 60/40 |
| 8 | Builder page | `dashboard/app/(app)/builder/page.tsx` | → `/builder` carga layout |
| 9 | Save to Supabase | AgentForm onSubmit | → SELECT agent en dashboard |
| 10 | Nav sidebar Builder | `dashboard/components/nav-main.tsx` | → Link visible navega `/builder` |

**Tiempo estimado:** 5 horas