# 🧠 Análisis Técnico — Paso 5: Template Picker — Librería de Templates

> **Agente:** glm  
> **Paso:** 05 — Template Picker — librería de templates  
> **Fase:** guiAgentGenerator  
> **Fecha:** 2026-05-14  

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | grep en `supabase/migrations/` | ✅ | `030_agent_templates.sql:10-21` — CREATE TABLE |
| 2 | Columna `category` en `agent_templates` | schema check | ✅ | `030_agent_templates.sql:14` — `category TEXT NOT NULL` |
| 3 | Columna `soul_json` en `agent_templates` | schema check | ✅ | `030_agent_templates.sql:15` — `soul_json JSONB NOT NULL` |
| 4 | Columna `suggested_tools` en `agent_templates` | schema check | ✅ | `030_agent_templates.sql:16` — `suggested_tools TEXT[]` |
| 5 | Endpoint `GET /api/templates` existe | grep en `src/api/routes/` | ✅ | `templates.py:54-67` — list con filtro category |
| 6 | Endpoint `GET /api/templates/{id}` existe | grep en `src/api/routes/` | ✅ | `templates.py:70-83` — detalle con soul_json |
| 7 | Modelo `TemplateInfo` Pydantic | grep en `templates.py` | ✅ | `templates.py:25-33` — id, name, description, category, suggested_tools, max_iter, is_system |
| 8 | Modelo `TemplateListResponse` Pydantic | grep en `templates.py` | ✅ | `templates.py:36-37` — templates: List[TemplateInfo], count: int |
| 9 | Modelo `TemplateDetailResponse` Pydantic | grep en `templates.py` | ✅ | `templates.py:41-51` — incluye soul_json completo |
| 10 | Categorías del seed: Research, Development, Support, General | grep en `templates_seed.py` | ✅ | Líneas 36,49,62,75,88,101,114,127 |
| 11 | `AgentForm` existe y acepta `initialValues` | grep en `AgentForm.tsx` | ✅ | `AgentForm.tsx:46-50` — interface `AgentFormProps` con `initialValues?: Partial<AgentFormData>` |
| 12 | `BuilderLayout` renderiza `AgentForm` | grep en `BuilderLayout.tsx` | ✅ | `BuilderLayout.tsx:15` — `<AgentForm />` |
| 13 | `api.get()` disponible en frontend | grep en `api.ts` | ✅ | `api.ts:55-56` — `get: (path) => fapFetch(path, {method: 'GET'})` |
| 14 | `useQuery` de `@tanstack/react-query` instalado | grep en `package.json` | ✅ | `package.json:29` — `"@tanstack/react-query": "^5.62.8"` |
| 15 | Componente `Dialog` shadcn/ui disponible | grep en `dashboard/components/ui/` | ✅ | `dialog.tsx` — Radix Dialog completo |
| 16 | Componente `Card` shadcn/ui disponible | grep en `dashboard/components/ui/` | ✅ | `card.tsx` — Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter |
| 17 | Componente `Badge` shadcn/ui disponible | grep en `dashboard/components/ui/` | ✅ | `badge.tsx` — variantes default, secondary, destructive, outline, success, warning, info |
| 18 | Componente `Skeleton` shadcn/ui disponible | grep en `dashboard/components/ui/` | ✅ | `skeleton.tsx` — ya usado en `AgentForm.tsx:255` |
| 19 | `LoadingSpinner` shared disponible | grep en `dashboard/components/shared/` | ✅ | `LoadingSpinner.tsx` — usado extensivamente en dashboard |
| 20 | `PROVIDER_MODELS` en constants | grep en `constants.ts` | ✅ | `constants.ts:16-21` — 4 providers |
| 21 | Filtro `?category=` implementado en backend | grep en `templates.py` | ✅ | `templates.py:56-62` — `category: Optional[str] = Query(None)` + `.eq("category", category)` |
| 22 | `ToolMultiSelect` componente existe | grep en builder dir | ✅ | `ToolMultiSelect.tsx` — multi-select custom |

**Discrepancias encontradas:**

| ID | Discrepancia | Resolución propuesta |
|---|---|---|
| D1 | Plan dice "Filtro por categoría (chips: Research, Development, Support, General)" pero las categorías en seed son exactamente esas 4. No hay endpoint para listar categorías únicas. El frontend debe hardcodear las 4 categorías de los seeds o hacer un endpoint nuevo. | Hardcodear las 4 categorías en frontend como constante (igual que `PROVIDER_MODELS`). Post-MVP: endpoint `GET /api/templates/categories`. |
| D2 | Plan dice "Botón 'Use Template' → rellena el formulario AgentForm con los datos del template" pero `AgentForm` no tiene método `setValues()` externo — solo acepta `initialValues` via props, y una vez montado los gestiona `react-hook-form`. Se necesita llamar `reset(values)` desde fuera o exponer una función `ref`/callback. | Agregar `useImperativeHandle` al `AgentForm` para exponer `resetForm(data)` via `forwardRef`, O usar callback `onTemplateSelect` en `BuilderLayout` que pase datos al form. Solución más simple: `AgentForm` expone `formRef` con `reset()`. |
| D3 | `soul_json` en templates tiene claves `role`, `goal`, `backstory` (3 campos), pero `soul_json` en `agent_catalog` tiene estructura extendida: `goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory`. Faltan campos LLM y toggles en templates. | Template `soul_json` → merge partial: campos del template (role/goal/backstory) sobreescriben defaults del form. Campos no presentes en template (llm_provider, llm_model, toggles) conservan defaults del formulario. El mapeo `template.soul_json.role` → `formValues.role` DEBE manejarse explícitamente porque `role` está fuera de `soul_json` en `AgentFormData`. |
| D4 | Plan dice "TemplatePicker visible desde builder (botón 'Templates' o panel superior)" pero `BuilderLayout` es grid 60/40 sin espacio para header/botón. Se necesita modificar `BuilderLayout` para incluir un trigger. | Agregar botón "Templates" o ícono en header del panel derecho del `BuilderLayout` (encima del título "Agent Configuration"). Patrón: trigger de Dialog. |
| D5 | `template.soul_json.role` en seed = `"Research Specialist"` etc., pero `agent_catalog.role` es campo plano (no dentro de `soul_json`). Mapeo `template.soul_json.role` → `form.role` (NO dentro de `soul_json`). | Al usar template: mapear `template.soul_json.role` → `formValues.role`, `template.soul_json.goal` → `formValues.goal`, `template.soul_json.backstory` → `formValues.backstory`. Los 3 campos del template que están dentro de `soul_json` deben "aplanarse" al formulario. |
| D6 | No existe componente `TemplatePicker.tsx` — es completamente nuevo. | Crear archivo nuevo `dashboard/components/builder/TemplatePicker.tsx`. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema — tabla `agent_templates`

```sql
-- Migración 030_agent_templates.sql
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

- ✅ **Tabla existe** — migración 030
- ✅ **Índice** `idx_agent_templates_category` en `category` — soporta filtro `?category=`
- ✅ **Índice parcial** `idx_agent_templates_system_name` en `name WHERE is_system = TRUE` — unicidad de system templates
- ✅ **RLS** — SELECT authenticated, ALL service_role
- ✅ **Sin `org_id`** — tabla global (catálogo público)

### Relaciones

- `agent_templates` → `agent_catalog`: relación lógica (template rellena formulario que POST a `/agents`), NO FK directa
- `agent_templates.suggested_tools` → referencia nombres de tools en `ToolRegistry` (validación laxa, sin FK)

### Datos del seed (8 templates)

| Template | Categoría | suggested_tools | max_iter |
|---|---|---|---|
| Research Agent | Research | sql_analytical, event_store | 5 |
| Code Reviewer | Development | (vacío) | 3 |
| Data Analyst | Development | sql_analytical, excel_reader, excel_writer | 5 |
| Customer Support | Support | (vacío) | 3 |
| Document Writer | General | excel_writer | 4 |
| Translator | General | (vacío) | 2 |
| Summarizer | General | (vacío) | 3 |
| General Assistant | General | excel_reader, excel_writer | 5 |

### Tipos de datos — mapeo

| Campo template | Tipo DB | Tipo Pydantic | Tipo frontend | Notas |
|---|---|---|---|---|
| `id` | UUID | str | string | Pasado como path param |
| `name` | TEXT NOT NULL | str | string | Card title |
| `description` | TEXT | Optional[str] | string \| null | Card subtitle |
| `category` | TEXT NOT NULL | str | string | Filtro chips |
| `soul_json` | JSONB | Dict[str, Any] | Record<string,any> | Contiene role, goal, backstory |
| `suggested_tools` | TEXT[] | List[str] | string[] | Multi-select prefill |
| `max_iter` | INTEGER | int | number | Slider/Input prefill |
| `is_system` | BOOLEAN | bool | boolean | Badge visual |

**⚠️ Incompatibilidad potencial**: `soul_json.role` en templates vs `role` como campo plano en `agent_catalog`. Mapeo necesario (ver D3/D5).

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos

#### `TemplatePicker.tsx` (NUEVO)

**Firma propuesta:**

```tsx
interface Template {
  id: string
  name: string
  description: string | null
  category: string
  soul_json: Record<string, any>
  suggested_tools: string[]
  max_iter: number
  is_system: boolean
}

interface TemplatePickerProps {
  onSelect: (template: Template) => void
  onClose?: () => void
}
```

**Funcionalidad:**
- Abrir como Dialog modal desde botón en `BuilderLayout`
- Cargar templates via `useQuery` → `api.get('/api/templates')`
- Mostrar grid de cards con: nombre, descripción, categoría, tools sugeridos
- Filtro por categoría (chips interactivos)
- Barra de búsqueda por nombre
- Botón "Use Template" → callback `onSelect(template)`
- Estado loading → `<Skeleton>` del card
- Estado error → mensaje con retry

**Patrones a seguir:**
- Dialog → `dashboard/components/ui/dialog.tsx` (Radix)
- Card → `dashboard/components/ui/card.tsx`
- Loading → `<LoadingSpinner>` + `<Skeleton>`
- Data fetching → `useQuery` de `@tanstack/react-query` (igual que `AgentForm.tsx:97-101`)
- API client → `api.get()` de `@/lib/api` (igual que `AgentForm.tsx:99`)

#### Modificaciones a existentes

**`AgentForm.tsx`** — Agregar `useImperativeHandle` para exponer `reset()`:

```tsx
// Patrón: forwardRef + useImperativeHandle
export interface AgentFormHandle {
  resetForm: (data: Partial<AgentFormData>) => void
}

export const AgentForm = forwardRef<AgentFormHandle, AgentFormProps>(
  ({ onSave, onClear, initialValues }, ref) => {
    // ... useForm setup ...
    
    useImperativeHandle(ref, () => ({
      resetForm: (data) => reset(data)
    }), [reset])
    
    // ... resto sin cambios ...
  }
)
```

**`BuilderLayout.tsx`** — Agregar botón "Templates" y dialog:

```tsx
// Nuevo state para dialog
const [templatePickerOpen, setTemplatePickerOpen] = useState(false)
const formRef = useRef<AgentFormHandle>(null)

// En panel derecho, agregar botón arriba del form
// En Dialog, TemplatePicker con onSelect que llama formRef.current.resetForm(data)
```

### Imports exactos necesarios

```tsx
// TemplatePicker.tsx
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Search } from 'lucide-react'
```

### Función de mapeo template → formValues

```tsx
function templateToFormValues(template: Template): Partial<AgentFormData> {
  const soul = template.soul_json || {}
  return {
    role: soul.role || '',
    goal: soul.goal || '',
    backstory: soul.backstory || '',
    llmProvider: 'groq',  // default
    llmModel: 'llama-3.1-70b-versatile',  // default
    allowedTools: template.suggested_tools || [],
    maxIter: template.max_iter || 3,
    verbose: soul.verbose ?? false,
    reasoning: soul.reasoning ?? false,
    injectDate: soul.inject_date ?? false,
    memory: soul.memory ?? false,
  }
}
```

### Modularidad

- `TemplatePicker` es componente puro presentacional + data fetching. No muta estado del form directamente → callback `onSelect`
- `AgentForm` expone `resetForm` via `useImperativeHandle` → inversión de control: `BuilderLayout` orquesta
- Sin duplicación: `api.get('/api/templates')` es la única fuente de datos templates
- Categorías hardcodeadas como constante en `TemplatePicker` (no endpoint nuevo)

### Calidad

- Complejidad ciclomática baja: `TemplatePicker` es lista + filtro + búsqueda
- Sin efecto cascada: TemplatePicker notifica al padre → padre resetea form
- `useQuery` con staleTime para evitar re-fetches innecesarios

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes (NO hay endpoints nuevos en este paso)

Paso 5 es **100% frontend**. Los endpoints ya existen:

| Endpoint | Método | Auth | Archivo | Notas |
|---|---|---|---|---|
| `/api/templates` | GET | Ninguno (público) | `templates.py:54-67` | Lista con `?category=` |
| `/api/templates/{id}` | GET | Ninguno (público) | `templates.py:70-83` | Detalle con `soul_json` |

### Contrato `GET /api/templates`

**Response:**
```json
{
  "templates": [
    {
      "id": "uuid",
      "name": "Research Agent",
      "description": "Conducts in-depth research...",
      "category": "Research",
      "suggested_tools": ["sql_analytical", "event_store"],
      "max_iter": 5,
      "is_system": true,
      "created_at": "2026-..."
    }
  ],
  "count": 8
}
```

**Filtro `?category=Research`:**
```json
{
  "templates": [...solo Research...],
  "count": 1
}
```

### Contrato `GET /api/templates/{id}`

**Response:**
```json
{
  "id": "uuid",
  "name": "Research Agent",
  "description": "...",
  "category": "Research",
  "soul_json": {
    "role": "Research Specialist",
    "goal": "Research topics thoroughly...",
    "backstory": "You are a research agent..."
  },
  "suggested_tools": ["sql_analytical", "event_store"],
  "max_iter": 5,
  "is_system": true,
  "created_at": "...",
  "updated_at": "..."
}
```

### Flujo de datos — Template Picker

```
[TemplatePicker Dialog]
  → useQuery('templates', api.get('/api/templates'))
  → filtrar por categoría (client-side)
  → buscar por nombre (client-side)
  → usuario clickea "Use Template"
  → onSelect(template) callback
  → BuilderLayout recibe template
  → mapea template → form values (templateToFormValues)
  → formRef.current.resetForm(mappedValues)
  → AgentForm se rellena
  → Dialog se cierra
```

### Error handling

- **Templates API 401/403**: No aplica — endpoint es público sin auth
- **Templates vacío**: Mostrar EmptyState "No templates available"
- **Error de red**: `useQuery` con `isError` → mensaje + botón Retry
- **Timeout**: No aplica — es GET simple sin dependencia MCP

### Cuello de botella

- Sin cuellos: `GET /api/templates` es query simple a tabla indexada por `category`. ~10-50ms para 8 rows.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: DB → Backend → Frontend → UX

```
[Supabase: agent_templates table]
  ↓ (get_service_client — bypass RLS)
[FastAPI: GET /api/templates?category=]
  ↓ (JSON response)
[useQuery: fetch + cache]
  ↓
[TemplatePicker: grid de cards con filtro + búsqueda]
  ↓ ("Use Template" click)
[BuilderLayout: mapea template → AgentFormData]
  ↓ (ref.resetForm)
[AgentForm: formulario relleno con datos del template]
  ↓ ("Save Agent" click)
[POST /agents → agent_catalog → persiste en DB]
```

### Coherencia end-to-end

- ✅ Templates backend crea datos, TemplatePicker los consume, AgentForm los presenta
- ✅ Categorías del seed (Research, Development, Support, General) coinciden con filtro chips
- ✅ `suggested_tools` del template → `allowedTools` del form → `allowed_tools` del POST → `agent_catalog.allowed_tools`
- ✅ `max_iter` del template → `maxIter` del form → `max_iter` del POST
- ⚠️ `soul_json.role` del template → `role` del form (campo plano, fuera de `soul_json`). Mapeo explícito necesario.

### Gaps y fricción

1. **Sin endpoint para categorías únicas** — Se hardcodean las 4 categorías. Correcto para MVP.
2. **Template preview** — Plan pide ver "tools sugeridos" en card pero `suggested_tools` son strings sin labels. Necesario mapear nombre → label usando `GET /api/tools/available`.
3. **No hay paginación** — 8 templates es trivial, sin paginación. Correcto.
4. **Búsqueda client-side** — Suficiente para 8 templates. Post-MVP: server-side search.

### Herramienta DX propuesta

```
### Herramienta Propuesta: template-preview
- **Qué automatiza:** Previsualizar cómo se verá un template al completar el formulario, sin necesidad de abrir el builder UI. Reduce ciclo de feedback al seeded templates.
- **Tipo:** CLI command
- **Cómo se usa:** `fap templates preview "Research Agent"` → imprime mapeo completo de campos del template al formulario AgentForm
- **Impacto para el usuario final:** Verifica que los 8 templates se mapean correctamente antes de implementar TemplatePicker. Reduce errores de mapeo soul_json → form fields.
- **Prioridad:** Tarea 0 — implementar antes para validar mapeo
```

Alternativa DX más simple: extender `fap templates list` con flag `--format=map` que muestre el mapeo template→form.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `agent_templates` accesible desde frontend (GET /api/templates retorna 8 templates seeded)
✅ [DATA] Filtro `?category=` funciona para las 4 categorías (Research, Development, Support, General)
✅ [CODE] Componente `TemplatePicker.tsx` existe en `dashboard/components/builder/`
✅ [CODE] `TemplatePicker` carga templates via `useQuery` + `api.get('/api/templates')`
✅ [CODE] `TemplatePicker` muestra grid de cards con nombre, descripción, categoría, tools sugeridos
✅ [CODE] `TemplatePicker` filtra por categoría via chips interactivos
✅ [CODE] `TemplatePicker` busca por nombre via barra de búsqueda
✅ [CODE] TemplatePicker integrado en BuilderLayout via Dialog trigger
✅ [CODE] Al seleccionar template, AgentForm se rellena con los datos del template
✅ [CODE] Mapeo `soul_json.role` → `role` (campo plano), `soul_json.goal` → `goal`, `soul_json.backstory` → `backstory`
✅ [CODE] `suggested_tools` del template → `allowedTools` del formulario
✅ [CODE] `max_iter` del template → `maxIter` del formulario
✅ [CODE] `AgentForm` expone `resetForm()` via `useImperativeHandle`
✅ [BACKEND] Endpoint `GET /api/templates` retorna array con `count` + templates completos
✅ [BACKEND] Endpoint `GET /api/templates/{id}` retorna `TemplateDetailResponse` con `soul_json`
✅ [FULLSTACK] Flujo completo: click "Templates" → seleccionar template → formulario relleno → guardar agente funciona
✅ [FULLSTACK] Estado de carga (Skeleton) visible mientras cargan templates
✅ [FULLSTACK] Estado de error manejado con mensaje + botón Retry
✅ [DX] Herramienta `fap templates preview` ejecuta sin errores y muestra mapeo template→form
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: Mapeo `soul_json.role` → `role` plano | Alta | `soul_json` en templates contiene `role`, pero `AgentFormData` tiene `role` como campo plano fuera de `soul_json`. Si se anida incorrectamente, el POST falla silenciosamente o guarda mal. | Función explícita `templateToFormValues()` que haga el mapeo campo a campo. Tests unitarios. |
| R2: Categorías hardcodeadas vs dinámicas | Media | Si se agregan categorías via seed futuro, chips hardcodeados no las muestran. | MVP: hardcodear. Post-MVP: endpoint `GET /api/templates/categories`. Agregar comentario TODO en código. |
| R3: `suggested_tools` como strings sin labels | Media | Template tiene `["sql_analytical", "event_store"]` que son nombres internos. En la card se muestran sin label legible. | Mostrar tools como `Badge` con nombre técnico. Alternativa: cross-referenciar con `GET /api/tools/available` pero añade complejidad. MVP: mostrar nombre técnico. |
| R4: Template Dialog no cierra al seleccionar | Baja | Si `onSelect` no llama a `setTemplatePickerOpen(false)`, Dialog permanece abierto. | `onSelect` debe: llamar callback → reset form → cerrar dialog. Secuencia explícita. |
| R5: `useQuery` stale data | Baja | Si se seedean nuevos templates, useQuery puede servir cache viejo. | `staleTime: 5 * 60 * 1000` (5 min). Refetch on window focus. Correcto para datos raramente cambiantes. |
| R6: Accesibilidad Dialog (a11y) | Baja | Radix Dialog maneja focus trap y escape. shadcn/ui Dialog ya accessible. | Usar `DialogDescription` para screen readers. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: Extender `fap templates list` con mapeo** | `src/cli/commands/templates_seed.py` + nuevo flag `--format=map` | `def templates_list(format: str = "table") -> None` | `templates_seed.py:140-175` — Typer command con Rich table | DX | Baja | 0.5h | Ninguna | → verificar: `fap templates list --format=map` ejecuta sin errores y muestra mapeo template→form |
| 1 | Exportar `AgentFormHandle` con `useImperativeHandle` | `dashboard/components/builder/AgentForm.tsx` | `export interface AgentFormHandle { resetForm: (data: Partial<AgentFormData>) => void }` + `forwardRef<AgentFormHandle, AgentFormProps>` | React pattern `useImperativeHandle` | CODE | Baja | 0.5h | Ninguna | → verificar: `formRef.current.resetForm({role: "test"})` actualiza formulario |
| 2 | Agregar constante `TEMPLATE_CATEGORIES` | `dashboard/lib/constants.ts` | `export const TEMPLATE_CATEGORIES = ['Research', 'Development', 'Support', 'General'] as const` | `PROVIDER_MODELS` en `constants.ts:16-21` | CODE | Baja | 0.1h | Ninguna | → verificar: importable desde TemplatePicker |
| 3 | Crear tipo `Template` y función `templateToFormValues` | `dashboard/components/builder/TemplatePicker.tsx` (archivo nuevo) | `interface Template { id: string; name: string; description: string \| null; category: string; soul_json: Record<string, any>; suggested_tools: string[]; max_iter: number; is_system: boolean }` + `function templateToFormValues(t: Template): Partial<AgentFormData>` | Mapeo explícito, no `any` spread | CODE | Media | 0.5h | Tarea 2 | → verificar: TypeScript compila sin errores |
| 4 | Crear componente `TemplatePicker` con Dialog | `dashboard/components/builder/TemplatePicker.tsx` | `interface TemplatePickerProps { onSelect: (template: Template) => void }` → Grid de Cards + filtro chips + búsqueda + botón "Use Template" | `dashboard/components/ui/dialog.tsx` + `card.tsx` + `badge.tsx` + `AgentForm.tsx:97-101` (useQuery pattern) | CODE | Media | 1.5h | Tarea 3 | → verificar: abrir `/builder`, clic "Templates" → Dialog muestra 8 cards con categorías |
| 5 | Integrar TemplatePicker en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Agregar `templatePickerOpen` state + `formRef` + botón "Templates" en header + `<Dialog>` con `<TemplatePicker onSelect={...}/>` | `AgentForm.tsx` ref pattern + state management en `BuilderLayout.tsx` | FULLSTACK | Media | 1h | Tarea 1, 4 | → verificar: clic "Templates" → seleccionar "Research Agent" → formulario se rellena con role="Research Specialist", goal, backstory, allowedTools=["sql_analytical","event_store"], maxIter=5 |
| 6 | Manejar estados de carga y error en TemplatePicker | `dashboard/components/builder/TemplatePicker.tsx` | `<Skeleton>` cards durante loading + `<EmptyState>` si 0 resultados + error message con Retry button | `AgentForm.tsx:255-268` (patrón toolsLoading/toolsError) | FULLSTACK | Baja | 0.5h | Tarea 4 | → verificar: desconectar backend → ver mensaje error con Retry |
| 7 | Validar flujo end-to-end operativo | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-6 | → verificar: criterios §5 [FULLSTACK] y [CODE] pasan todos |

**Tiempo total estimado:** 4.6 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Endpoint `GET /api/templates/categories`** — listar categorías únicas dinámicamente en vez de hardcodear
- **Worker de búsqueda server-side** — cuando templates crezcan > 50, buscar en backend en vez de client-side
- **Preview de template con ToolMultiSelect** — cross-referenciar `suggested_tools` con `GET /api/tools/available` para mostrar labels legibles en vez de nombres técnicos
- **Favoritos/recientes** — localStorage para marcar templates favoritos o usados recientemente
- **Custom templates** — `POST /api/templates` para que orgs creen sus propios templates (requiere `org_id` → migración adicional)
- **Drag & drop de template al canvas** — cuando ReactFlow canvas esté implementado (Paso 07), drag template al canvas creando node de agente