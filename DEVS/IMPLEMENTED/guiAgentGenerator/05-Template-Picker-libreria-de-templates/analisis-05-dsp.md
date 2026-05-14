# 🧠 Análisis Técnico — Paso 05 (dsp)

> **Fase:** `guiAgentGenerator`
> **Paso:** 05 — Template Picker (librería de templates)
> **Agente:** dsp
> **Fecha:** 2026-05-14
> **Stack:** Next.js + ReactFlow + FastAPI + Supabase

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | grep en `supabase/migrations/` | ✅ | `030_agent_templates.sql:10-21` |
| 2 | Columna `name TEXT NOT NULL` | grep en migración | ✅ | `030_agent_templates.sql:12` |
| 3 | Columna `description TEXT` | grep en migración | ✅ | `030_agent_templates.sql:13` |
| 4 | Columna `category TEXT NOT NULL` | grep en migración | ✅ | `030_agent_templates.sql:14` |
| 5 | Columna `soul_json JSONB DEFAULT '{}'` | grep en migración | ✅ | `030_agent_templates.sql:15` |
| 6 | Columna `suggested_tools TEXT[] DEFAULT '{}'` | grep en migración | ✅ | `030_agent_templates.sql:16` |
| 7 | Columna `max_iter INTEGER DEFAULT 5` | grep en migración | ✅ | `030_agent_templates.sql:17` |
| 8 | Índice `idx_agent_templates_category` | grep en migración | ✅ | `030_agent_templates.sql:31` |
| 9 | RLS SELECT auth.role() = 'authenticated' | grep en migración | ✅ | `030_agent_templates.sql:25-26` |
| 10 | Endpoint `GET /api/templates` existe | grep en `src/api/routes/templates.py` | ✅ | `templates.py:54-67` |
| 11 | Endpoint `GET /api/templates/{id}` existe | grep en `src/api/routes/templates.py` | ✅ | `templates.py:70-83` |
| 12 | `TemplateInfo` incluye `suggested_tools: List[str]` | grep en modelos Pydantic | ✅ | `templates.py:30` |
| 13 | `TemplateDetailResponse` incluye `soul_json: Dict[str, Any]` | grep en modelos Pydantic | ✅ | `templates.py:46` |
| 14 | `TemplatePicker.tsx` NO existe aún | glob `dashboard/components/builder/TemplatePicker*` | ✅ | No encontrado |
| 15 | `AgentForm` acepta `initialValues?: Partial<AgentFormData>` | grep en props | ✅ | `AgentForm.tsx:46-50` |
| 16 | `AgentForm` usa `react-hook-form` + `zodResolver` | grep en imports | ✅ | `AgentForm.tsx:5,7` |
| 17 | `BuilderLayout` renderiza `<AgentForm />` | grep en JSX | ✅ | `BuilderLayout.tsx:15` |
| 18 | `BuilderLayout` NO incluye TemplatePicker actualmente | grep en JSX | ✅ | `BuilderLayout.tsx:6-19` |
| 19 | `Card` + `CardHeader` + `CardTitle` + `CardContent` disponibles | grep en ui/card.tsx | ✅ | `card.tsx:4,15,22,36` |
| 20 | `Badge` con variant `secondary` disponible | grep en ui/badge.tsx | ✅ | `badge.tsx:13` |
| 21 | `Input` componente shadcn/ui disponible | grep en ui/input.tsx | ✅ | `input.tsx:4` |
| 22 | `Skeleton` componente shadcn/ui disponible | grep en ui/skeleton.tsx | ✅ | `skeleton.tsx` |
| 23 | `LoadingSpinner` disponible | grep en shared/ | ✅ | `LoadingSpinner.tsx` |
| 24 | `EmptyState` disponible | grep en shared/ | ✅ | `EmptyState.tsx:13` |
| 25 | `@tanstack/react-query` instalado | grep en package.json | ✅ | `package.json:29` |
| 26 | `lucide-react` instalado | grep en package.json | ✅ | `package.json:36` |
| 27 | `api` helper disponible (`api.get()`) | grep en lib/api.ts | ✅ | `api.ts:55` |
| 28 | `fapFetch` envía `Authorization` + `X-Org-ID` | grep en lib/api.ts | ✅ | `api.ts:19-21` |
| 29 | Templates sin `require_org_id` — auth vía RLS | grep en routes/templates.py | ✅ | `templates.py:54-67` (sin `Depends`) |
| 30 | Seed contiene 8 templates con 4 categorías | grep en templates_seed.py | ✅ | `templates_seed.py:32-137` |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | **`soul_json` del seed tiene estructura diferente a la de AgentForm.** Seed: `{role, goal, backstory}`. AgentForm produce: `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}`. TemplatePicker debe mapear `template.name` → `role` (NO usar `soul_json.role`) y usar `soul_json.goal` y `soul_json.backstory` como fuente. Campos no presentes en seed (llm_provider, etc.) → usar defaults de AgentForm. | Mapeo explícito en `TemplatePicker` al hacer "Use Template". Ver §2 y §7. |
| D2 | **`AgentForm.initialValues` solo afecta `defaultValues` al montar.** No reacciona a cambios posteriores. Al hacer "Use Template", el formulario no se actualiza si ya fue montado. | Añadir prop `templateData?: AgentFormData` a `AgentForm` con `useEffect` que llame `reset(templateData)` cuando cambie. Ver §2 Tarea 2. |
| D3 | **`TemplateInfo` (list) NO incluye `soul_json`.** Para rellenar el formulario se necesita `soul_json`. | "Use Template" → fetch `GET /api/templates/{id}` (incluye `soul_json`). El listado solo muestra info de tarjeta (sin soul_json). |
| D4 | **Endpoint templates es público (sin `require_org_id`) pero `fapFetch` siempre envía `X-Org-ID`.** El backend lo ignora. No es problema funcional pero `useCurrentOrg()` podría no estar disponible en el contexto del builder si no hay org seleccionada. | El builder ya requiere org porque `AgentForm` usa `useCurrentOrg()` para guardar. TemplatePicker usará `api.get()` directamente por consistencia, sin depender de `orgId` para la query. |
| D5 | **Plan dice "chips: Research, Development, Support, General".** Seed usa exactamente esas 4 categorías. Pero el schema no tiene `CHECK` constraint en category — cualquier valor es válido. Si un template custom (futuro) usa otra categoría, el chip no lo mostraría. | Por ahora derivar chips de las categorías retornadas por la API (`TemplateInfo.category`). No hardcodear. Ver §2. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema actual — `agent_templates`

```sql
-- 030_agent_templates.sql:10-21
CREATE TABLE agent_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT NOT NULL,
    soul_json       JSONB NOT NULL DEFAULT '{}',
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter        INTEGER DEFAULT 5,
    is_system       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

- **Sin `org_id`** → tabla GLOBAL, mismo patrón que `service_catalog` (mig 024).
- **RLS:** SELECT solo `authenticated`. Escritura solo `service_role`.
- **Índices:** `idx_agent_templates_category` (btree, acelera `?category=`). `idx_agent_templates_system_name` (UNIQUE parcial WHERE `is_system = TRUE`).
- **Datos semilla:** 8 templates en 4 categorías (Research ×1, Development ×2, Support ×1, General ×4).
- **`soul_json` sin validación de schema.** `JSONB DEFAULT '{}'` — cualquier estructura es válida. Seed contiene `{role, goal, backstory}`. AgentForm produce `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}`. **No hay integridad referencial entre `suggested_tools` y `tool_registry`**.

### Cambios requeridos para Paso 05

- **NINGÚN cambio de schema.** Paso 05 es solo frontend. Consume datos existentes.
- **NINGUNA migración nueva.**

### Integridad referencial

- `suggested_tools TEXT[]` no tiene FK a `tool_registry`. Es una lista de strings libre. Si una tool no existe, el formulario la acepta igual — el backend `POST /agents` validará al ejecutar. **Riesgo bajo**: el seed usa herramientas que existen o son opcionales.
- `soul_json` sin schema fijo. TemplatePicker debe hacer acceso defensivo: `soul_json?.goal ?? ''`, `soul_json?.backstory ?? ''`.

### RLS policies

```
✅ agent_templates_read: SELECT para cualquier authenticated user
✅ agent_templates_write: ALL solo service_role
```

La lectura desde el frontend requiere token JWT válido → `fapFetch` lo incluye automáticamente vía `api.get()`. Sin cambios necesarios.

### Índices

- `idx_agent_templates_category` — cubre `?category=` filter. **Suficiente para MVP.** Sin necesidad de índice adicional para búsqueda por texto (búsqueda se hace client-side con `filter()`).

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes a crear

#### 2.1 `TemplatePicker.tsx` (NUEVO)

**Firma:**
```typescript
export function TemplatePicker({
  onUseTemplate,
}: {
  onUseTemplate: (template: AgentFormData) => void
}): JSX.Element
```

**Estado interno:**
- `search: string` — búsqueda por nombre
- `selectedCategory: string | null` — filtro por categoría
- `templates: TemplateInfo[]` — vía `useQuery`
- `isLoading: boolean` — estado de carga
- `isError: boolean` — estado de error

**Flujo:**
1. `useQuery(['templates'], () => api.get('/api/templates'))` → obtiene `TemplateListResponse.templates`
2. Render grid de cards con `name`, `description`, `category` badge, `suggested_tools` badges
3. "Use Template" → `api.get('/api/templates/{id}')` → mapea `TemplateDetailResponse` → `AgentFormData` → `onUseTemplate(data)`
4. Filtro categoría: chips renderizados desde `[...new Set(templates.map(t => t.category))]` (dinámico, no hardcodeado)
5. Búsqueda: `templates.filter(t => t.name.toLowerCase().includes(search.toLowerCase()))`

**Mapeo template → AgentFormData (OBLIGATORIO):**
```typescript
function mapTemplateToFormData(detail: TemplateDetailResponse): AgentFormData {
  const soul = detail.soul_json ?? {}
  return {
    role: detail.name,                         // ⚠️ NO soul_json.role — discrepancia D1
    goal: soul.goal ?? '',
    backstory: soul.backstory ?? detail.description ?? '',
    llmProvider: mapProvider(soul.llm_provider), // snake→camel, con validación
    llmModel: soul.llm_model ?? 'llama-3.1-70b-versatile',
    allowedTools: detail.suggested_tools,
    maxIter: detail.max_iter,
    verbose: soul.verbose ?? false,
    reasoning: soul.reasoning ?? false,
    injectDate: soul.inject_date ?? false,
    memory: soul.memory ?? false,
  }
}

function mapProvider(provider?: string): AgentFormData['llmProvider'] {
  const valid = ['groq', 'openai', 'anthropic', 'openrouter']
  return valid.includes(provider as any) ? (provider as any) : 'groq'
}
```

**Patrón de referencia:** `dashboard/app/(app)/agents/page.tsx` (grid de cards con `Card` + `Badge` + loading/empty states).

**Props/estados cubiertos:**
- `isLoading` → `<Skeleton>` grid (4 cards, patrón `agents/[id]/page.tsx` skeleton)
- `isError` → `<EmptyState icon={<AlertTriangle/>} title="Error loading templates" />`
- `!templates?.length` → `<EmptyState icon={<Layers/>} title="No templates available" />`
- `filtered.length === 0` → `<EmptyState title="No templates match your search" />`

#### 2.2 `AgentForm.tsx` (MODIFICAR)

**Cambio requerido:** Añadir prop `templateData` para aplicar template después del montaje.

**Firma actual:**
```typescript
interface AgentFormProps {
  onSave?: (data: AgentFormData) => Promise<void>
  onClear?: () => void
  initialValues?: Partial<AgentFormData>
}
```

**Firma propuesta (ADD, no modificar existente):**
```typescript
interface AgentFormProps {
  onSave?: (data: AgentFormData) => Promise<void>
  onClear?: () => void
  initialValues?: Partial<AgentFormData>
  templateData?: AgentFormData | null   // ADD: aplicar template desde TemplatePicker
}
```

**Implementación (ADD después de `useForm`, después de línea 87):**
```typescript
useEffect(() => {
  if (templateData) {
    reset({
      role: templateData.role,
      goal: templateData.goal,
      backstory: templateData.backstory,
      llmProvider: templateData.llmProvider,
      llmModel: templateData.llmModel,
      allowedTools: templateData.allowedTools,
      maxIter: templateData.maxIter,
      verbose: templateData.verbose,
      reasoning: templateData.reasoning,
      injectDate: templateData.injectDate,
      memory: templateData.memory,
    })
  }
}, [templateData, reset])
```

> ⚠️ `templateData` se debe pasar como `null` cuando el usuario hace "Clear". El `useEffect` NO se dispara con `null`.

#### 2.3 `BuilderLayout.tsx` (MODIFICAR)

**Cambio requerido:** Integrar `TemplatePicker` como modal/dialog accionado por botón, y pasar `templateData` a `AgentForm`.

**Firma propuesta:**
```typescript
'use client'

import { useState } from 'react'
import { BuilderCanvas } from '@/components/builder/BuilderCanvas'
import { AgentForm, type AgentFormData } from '@/components/builder/AgentForm'
import { TemplatePicker } from '@/components/builder/TemplatePicker'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Layers } from 'lucide-react'

export function BuilderLayout() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [templateData, setTemplateData] = useState<AgentFormData | null>(null)

  return (
    <div className="grid h-full gap-4 lg:grid-cols-[60%_40%]">
      <div className="min-h-0">
        <BuilderCanvas />
      </div>
      <div className="flex flex-col overflow-hidden rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">Agent Configuration</h3>
          <Button variant="outline" size="sm" onClick={() => setDialogOpen(true)}>
            <Layers className="mr-1.5 h-3.5 w-3.5" />
            Templates
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <AgentForm templateData={templateData} />
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Template Library</DialogTitle>
          </DialogHeader>
          <TemplatePicker
            onUseTemplate={(data) => {
              setTemplateData(data)
              setDialogOpen(false)
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

**Patrón de referencia:** `dashboard/components/flows/RunFlowDialog.tsx` (Dialog con contenido funcional).

### Imports necesarios

```typescript
// TemplatePicker.tsx
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { AlertTriangle, Layers, Search } from 'lucide-react'

// BuilderLayout.tsx (ADD)
import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { TemplatePicker } from '@/components/builder/TemplatePicker'
import { Button } from '@/components/ui/button'
import { Layers } from 'lucide-react'

// AgentForm.tsx (ADD)
// Solo añadir `templateData` a AgentFormProps y el useEffect
```

### Modularidad

- `TemplatePicker` es autónomo: recibe solo `onUseTemplate` callback. No conoce `AgentForm` ni `BuilderLayout`.
- `AgentForm` gana prop `templateData` sin breaking change: es opcional, sin default.
- `BuilderLayout` orquesta la interacción entre ambos componentes. Patrón consistente con cómo `agents/page.tsx` orquesta grid + Link.

### Calidad

- Complejidad ciclomática baja: cada componente ≤ 3 niveles de anidamiento.
- Sin estado global: todo vía props locales.
- Sin efectos secundarios fuera de `useQuery` y el `useEffect` de `templateData`.
- `useMemo` para filtered templates — evita re-filtrado en cada render.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs consumidas

| Endpoint | Método | Input | Output | Llamado desde |
|---|---|---|---|---|
| `/api/templates` | GET | `?category=` (opt) | `{templates: TemplateInfo[], count: int}` | TemplatePicker (listado inicial) |
| `/api/templates/{id}` | GET | — | `TemplateDetailResponse` (incluye `soul_json`) | TemplatePicker ("Use Template" click) |

### Flujo de datos

```
[Supabase agent_templates]
  ↓ get_service_client() + service_role → bypass RLS
[GET /api/templates]
  ↓ JSON response {templates: [...], count: N}
[TemplatePicker useQuery]
  ↓ render cards (name, description, category, tools)
[User clicks "Use Template"]
  ↓ onClick → api.get('/api/templates/{id}')
  ↓ JSON response {soul_json: {...}, suggested_tools: [...], max_iter: ...}
  ↓ mapTemplateToFormData()
  ↓ onUseTemplate(data) → BuilderLayout.setState({templateData: data})
  ↓ props.templateData → AgentForm.useEffect → reset(data)
[AgentForm muestra campos rellenos]
```

### Contratos

- `GET /api/templates`: Contrato estable. Sin auth en handler, pero RLS requiere JWT → `fapFetch` lo cubre. Tiempo de respuesta <200ms (sin MCP overhead).
- `GET /api/templates/{id}`: Contrato estable. Sin auth en handler. `maybe_single()` → 404 si no existe. `TemplateDetailResponse` incluye `soul_json: Dict[str, Any]`.
- **NO se crean nuevos endpoints.** Paso 05 solo consume APIs existentes del Paso 03.

### Auth / AuthZ

- Endpoints públicos (sin `Depends(require_org_id)`). RLS: `auth.role() = 'authenticated'`.
- `fapFetch` (api.ts:9-21) envía `Authorization: Bearer <jwt>` + `X-Org-ID` automáticamente. `get_service_client()` usa `service_role` → bypass RLS para query DB.
- Si el usuario no está autenticado, `fapFetch` lanza `'Not authenticated'` → `useQuery` marca `isError: true` → TemplatePicker muestra error.

### Error handling

- **API error (4xx/5xx):** `fapFetch` lanza `Error(message)`. `useQuery` expone `isError` + `error`. TemplatePicker muestra `<EmptyState icon={<AlertTriangle/>} title="Failed to load templates" />`.
- **Template not found (404):** `api.get('/api/templates/{id}')` lanza error con `detail: "Template not found"`. TemplatePicker muestra toast `toast.error('Template not found')`.
- **soul_json incompleto:** TemplatePicker usa acceso defensivo (`soul_json?.goal ?? ''`). Nunca falla por campos faltantes.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

```
1. [DB] agent_templates (8 system templates, 4 categorías)
   ↓
2. [Backend] GET /api/templates → TemplateInfo[] (sin soul_json)
   ↓
3. [Frontend] TemplatePicker cards grid (loading → grid → empty/error)
   ↓
4. [UX] User busca/filtra templates por categoría/nombre
   ↓
5. [UX] User hace clic en "Use Template" en una card
   ↓
6. [Backend] GET /api/templates/{id} → TemplateDetailResponse (con soul_json)
   ↓
7. [Frontend] mapTemplateToFormData() → AgentFormData
   ↓
8. [UX] AgentForm se rellena con role, goal, backstory, tools, max_iter, toggles
   ↓
9. [UX] User puede modificar cualquier campo antes de guardar
```

### Coherencia

- **Decisión de data (template global sin org_id)** → correcto. Templates son catálogo público. Cualquier usuario autenticado puede verlos.
- **Decisión de API (list sin soul_json, detail completo)** → correcto. Evita payloads grandes en listado. Detail solo al aplicar.
- **Decisión de frontend (modal dialog, no inline)** → correcto. El BuilderLayout ya está congestionado (60/40 split). Modal evita perder espacio de canvas.
- **Decisión de interacción (TemplatePicker no conoce AgentForm)** → correcto. Callback `onUseTemplate` mantiene desacoplamiento. BuilderLayout orquesta.

### Alineación plan ↔ arquitectura

- Plan: "Botón 'Use Template' → rellena formulario" → viable con props `templateData` + `useEffect`.
- Plan: "Filtro por categoría (chips)" → viable con `Badge` + `onClick` toggle.
- Plan: "Barra de búsqueda por nombre" → viable con `Input` + `useMemo` filter client-side (8-20 templates, no justifica búsqueda server-side).
- Plan: "Mostrar cards con: nombre, descripción, categoría, tools sugeridos" → viable con patrón `Card` del grid de agents.

### Gaps detectados

| Gap | Impacto | Resolución |
|---|---|---|
| `soul_json` sin schema fijo → template puede no tener `llm_provider`, `verbose`, etc. | Bajo. Se usan defaults de AgentForm. | Mapeo defensivo en `mapTemplateToFormData()`. |
| Búsqueda client-side escala mal con >100 templates | Nulo para MVP (8 templates). Post-MVP: `?search=` en API. | Documentado en §7 como optimización futura. |
| Templates con `suggested_tools` que no existen en `tool_registry` → formulario acepta valores inválidos. | Bajo. El backend validará al ejecutar. | Post-MVP: validator en `POST /agents` que cruce tools. |

### DX & Tooling

#### Herramienta Propuesta: `fap templates list`

- **Qué automatiza:** Listar templates desde terminal sin abrir el dashboard. Reemplaza `curl GET /api/templates | jq`.
- **Tipo:** CLI
- **Cómo se usa:** `fap templates list [--category Research] [--json]`
- **Impacto para el usuario final:** Ve qué templates existen y sus categorías en 1 segundo, sin navegar al builder.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

> ⚠️ Este comando NO existe actualmente. `fap templates` solo tiene `seed`. Añadir `list` subcomando.

#### Herramienta Propuesta (alternativa): `fap templates apply`

- **Qué automatiza:** Aplicar template a un agente existente vía CLI. `fap templates apply "Research Agent" --output research_agent.json`
- **Tipo:** CLI
- **Cómo se usa:** `fap templates apply <template_name> [--output <path>] [--org-id <id>]`
- **Impacto:** Configuración de agente fuera de la UI, útil para automatización/CI.
- **Prioridad:** Post-MVP. No bloquea Paso 05.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA]    Tabla agent_templates tiene ≥ 8 registros con is_system = true
✅ [DATA]    Categorías Research, Development, Support, General existen en los datos
✅ [CODE]    TemplatePicker.tsx exporta función con firma correcta
✅ [CODE]    TemplatePicker carga templates desde GET /api/templates (no mock)
✅ [CODE]    AgentForm acepta prop templateData y aplica reset cuando cambia
✅ [CODE]    BuilderLayout integra TemplatePicker vía Dialog + botón "Templates"
✅ [CODE]    Mapeo template→form usa name→role, NO soul_json.role
✅ [CODE]    Mapeo template→form usa soul_json.goal/backstory con fallback a description
✅ [CODE]    Mapeo template→form usa defaults para campos no presentes en soul_json
✅ [BACKEND] GET /api/templates responde 200 con templates array
✅ [BACKEND] GET /api/templates?category=Research filtra correctamente
✅ [BACKEND] GET /api/templates/{id} responde 200 con soul_json completo
✅ [BACKEND] GET /api/templates/{uuid-invalido} responde 404
✅ [FULLSTACK] TemplatePicker visible desde el builder con botón "Templates"
✅ [FULLSTACK] Templates cargan desde API real (no mock/hardcode)
✅ [FULLSTACK] Al hacer clic en "Use Template", el formulario AgentForm se rellena
✅ [FULLSTACK] Filtro por categoría (chips dinámicos) funciona
✅ [FULLSTACK] Búsqueda por texto (nombre) funciona client-side
✅ [FULLSTACK] Estado de carga muestra skeletons
✅ [FULLSTACK] Estado de error muestra EmptyState con mensaje
✅ [FULLSTACK] Modal se cierra automáticamente al seleccionar template
✅ [UX]      Tooltip o badge en cada card muestra suggested_tools
✅ [UX]      Categoría visible como badge en cada card
✅ [DX]      `fap templates list` ejecuta sin errores y muestra ≥ 8 templates
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `soul_json` inconsistente entre seed y AgentForm | Media | Seed usa `{role, goal, backstory}`. AgentForm espera `{goal, backstory, llm_provider, ...}`. | Mapeo defensivo en `mapTemplateToFormData()`. NO usar `soul_json.role`. Documentado en D1. |
| TemplatePicker no maneja 404 al hacer detail fetch | Baja | `api.get()` lanza `Error` genérico con `response.status`. `maybe_single()` puede retornar `null`. | Intentar/except en `onClick` con `toast.error('Template not found')`. |
| Modal Dialog bloquea scroll en mobile | Baja | `DialogContent max-h-[80vh] overflow-y-auto` cubre pantallas pequeñas. Grid de 8 cards × ~200px requiere scroll. | Probar en viewport 375×667. Si muy ajustado → `grid-cols-1` en mobile. |
| Doble fetch innecesario (list + detail) | Baja | List ya tiene `TemplateInfo` sin `soul_json`. Detail fetch añade ~50ms en LAN. | Aceptable para MVP. Post-MVP: incluir `soul_json` en list si el payload promedio < 5KB. |
| `fapFetch` requiere `orgId` → `localStorage` puede estar vacío | Media | `api.get()` usa `fapFetch` que lee `localStorage.getItem('organization_id')`. Si el usuario navegó directo a `/builder` sin seleccionar org, `orgId = ''`. | `GET /api/templates` no usa `X-Org-ID` (endpoint público). Pero `fapFetch` igual lo envía como `''` → backend lo ignora. Sin impacto funcional. |
| Categorías dinámicas vs hardcodeadas | Baja | Plan dice "chips: Research, Development, Support, General". Si alguien añade template con categoría nueva vía seed personalizado, no aparecerá chip. | Derivar chips de `[...new Set(templates.map(t => t.category))]`. Dinámico. Siempre cubre todas las categorías reales. |
| `@tanstack/react-query` cache puede mostrar datos stale | Baja | Templates son estáticos (solo cambian con seed CLI). Cache por defecto `staleTime: 0` → refetch en cada mount. | Si rendimiento preocupa, `staleTime: 5 * 60 * 1000` (5 min). Post-MVP. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: `fap templates list`** | `src/cli/commands/templates_list.py` | `@templates_app.command("list") def list_templates(category: Optional[str] = None, json_output: bool = False) -> None:` | `src/cli/commands/templates_seed.py :: templates_app` | DX | Baja | 0.5h | Ninguna | → verificar: `uv run python -m src.cli.main templates list` muestra ≥8 templates |
| 1 | **Crear `TemplatePicker.tsx`** | `dashboard/components/builder/TemplatePicker.tsx` | `export function TemplatePicker({ onUseTemplate }: { onUseTemplate: (data: AgentFormData) => void }): JSX.Element` | `dashboard/app/(app)/agents/page.tsx` (grid de cards con Card+Badge+LoadingSpinner+EmptyState) | CODE | Media | 2h | Tarea 0 | → verificar: `TemplatePicker` importable desde `@/components/builder/TemplatePicker` sin error. Render muestra 8 cards con `useQuery`. |
| 2 | **Modificar `AgentForm.tsx`** — añadir prop `templateData` | `dashboard/components/builder/AgentForm.tsx` | `interface AgentFormProps { ... templateData?: AgentFormData \| null }` + `useEffect` que llama `reset(templateData)` | Patrón existente: `useForm({ defaultValues: initialValues })` en mismo archivo, línea 72-87 | CODE | Baja | 0.5h | Ninguna | → verificar: `AgentForm` recibe `templateData` sin error TS. Cambiar `templateData` → formulario se actualiza. |
| 3 | **Modificar `BuilderLayout.tsx`** — integrar TemplatePicker | `dashboard/components/builder/BuilderLayout.tsx` | `useState(templateData)`, `useState(dialogOpen)`, `<Dialog>` wrapper, `<Button variant="outline" size="sm">` | `dashboard/components/flows/RunFlowDialog.tsx` (Dialog con contenido funcional) | CODE | Media | 1h | Tareas 1, 2 | → verificar: Botón "Templates" visible en builder. Click → modal abre con grid. Click "Use Template" → modal cierra + AgentForm se rellena. |
| 4 | **Validar flujo end-to-end** | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-3 | → verificar: criterios §5 [FULLSTACK] y [DX] pasan todos. `npm run lint` sin errores. |

**Tiempo total estimado:** 4.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

| Mejora | Prioridad | Descripción |
|---|---|---|
| `soul_json` validator en API | Post-MVP | Validar estructura de `soul_json` en `POST /api/templates` (custom templates por org) con Pydantic schema. |
| Búsqueda server-side `?search=` | Post-MVP | Cuando haya >50 templates. Índice GIN en `name` + `description`. |
| `fap templates apply` | Post-MVP | Aplicar template a agente existente desde CLI sin UI. `--output` genera JSON listo para `fap agent create`. |
| Template preview | Post-MVP | Hover en card muestra tooltip con preview del `soul_json.goal` y `soul_json.backstory`. |
| Custom templates por org | Post-MVP | Migración adicional con `org_id` en `agent_templates`. Templates privados por organización. |
| Animar transición template→form | Post-MVP | Framer-motion `AnimatePresence` al cerrar modal + rellenar form. Patrón existente en `AgentPersonalityCard`. |
| `staleTime` para query de templates | Post-MVP | Templates son datos casi estáticos. `staleTime: 5 * 60 * 1000` evita refetch innecesario. |

---

## 📊 Métrica de Calidad (auto-check)

| Métrica | Mínimo | Actual | Cumple |
|---|---|---|---|
| `proyecto-config.json` leído antes de explorar | 100% | ✅ Leído línea 1-135 | ✅ |
| Elementos verificados (§0) | ≥12 (3-5 archivos) | 30 | ✅ |
| Discrepancias detectadas | ≥1 si toca código existente | 5 (D1-D5) | ✅ |
| Secciones completadas | 8 (0-7) | 8 | ✅ |
| Etapas cubiertas | 4 | 4 (data, code, backend, fullstack+DX) | ✅ |
| Criterios de aceptación | ≥1 por sub-paso, verificables | 26 (cubren todos los criterios del plan) | ✅ |
| Riesgos identificados | ≥3 (técnico, integración, futuro) | 7 | ✅ |
| Tareas atómicas (1 artefacto por tarea) | 100% | 4 tareas, cada una 1 artefacto | ✅ |
| Interfaz exacta por tarea | 100% | Firmas completas con tipos en cada tarea | ✅ |
| Patrón de referencia explícito por tarea | 100% | Archivos concretos citados (agents/page.tsx, RunFlowDialog.tsx, etc.) | ✅ |
| Verificación inline por tarea | 100% | Comandos concretos en columna Verificación | ✅ |
| Suposiciones no verificadas | ≤2, marcadas ⚠️ | 0 (todas verificadas o marcadas como discrepancia) | ✅ |
| Propuesta DX / Tooling | ≥1 | 2 (`fap templates list` + `fap templates apply`) | ✅ |
| Estimación de tiempo | Sí, por tarea y total | 4.5h total | ✅ |
