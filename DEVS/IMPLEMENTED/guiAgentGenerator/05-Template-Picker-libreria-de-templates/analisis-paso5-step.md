# 📋 Análisis Paso 05 — Template Picker (Builder Visual)

**Agente:** step  
**Fase:** guiAgentGenerator  
**Objetivo:** Implementar selector de templates (Template Library) que cargue desde `GET /api/templates`, muestre grid con cards, permita filtrar por categoría y búsqueda, y al seleccionar rellene el `AgentForm`.

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | Migración `030_agent_templates.sql` | ✅ | Línea 10-21: CREATE TABLE |
| 2 | Columna `name` (TEXT NOT NULL) | Migración 030 | ✅ | L12 |
| 3 | Columna `description` (TEXT) | Migración 030 | ✅ | L13 |
| 4 | Columna `category` (TEXT NOT NULL) | Migración 030 | ✅ | L14 |
| 5 | Columna `soul_json` (JSONB NOT NULL) | Migración 030 | ✅ | L15 |
| 6 | Columna `suggested_tools` (TEXT[]) | Migración 030 | ✅ | L16 |
| 7 | Columna `max_iter` (INTEGER) | Migración 030 | ✅ | L17 |
| 8 | Índice parcial `UNIQUE(name) WHERE is_system=TRUE` | Migración 030 | ✅ | L32-33 |
| 9 | RLS: SELECT autenticado, ALL service_role | Migración 030 | ✅ | L25-29 |
| 10 | Endpoint `GET /api/templates` existe | `src/api/routes/templates.py:54-67` | ✅ | @router.get("") |
| 11 | Modelo `TemplateInfo` (id, name, description, category, suggested_tools, max_iter, is_system) | `templates.py:25-33` | ✅ | Campos completos |
| 12 | Modelo `TemplateDetailResponse` incluye `soul_json` | `templates.py:41-52` | ✅ | L46: `soul_json: Dict[str, Any]` |
| 13 | Filtro `?category=` funciona | `templates.py:56-62` | ✅ | `.eq("category", category)` |
| 14 | Endpoint **sin** `require_org_id` (lectura pública) | `templates.py:54-67` | ✅ | Sin Depends auth |
| 15 | Componente `AgentForm` existe y acepta `initialValues` | `AgentForm.tsx:46-50, 74-86` | ✅ | defaultValues inicializados |
| 16 | `AgentForm` expone método `reset()` | `AgentForm.tsx:154-169` | ✅ | reset con valores completos |
| 17 | `AgentForm` usa `useForm` + `zodResolver` | `AgentForm.tsx:65-74` | ✅ | Patrón consistente |
| 18 | `ToolMultiSelect` componente existe | `ToolMultiSelect.tsx:1-156` | ✅ | Multi-select con búsqueda |
| 19 | `BuilderLayout` componente existe | `BuilderLayout.tsx:6-19` | ✅ | Grid 60/40 |
| 20 | Constante `PROVIDER_MODELS` definida | `constants.ts:16-21` | ✅ | 4 providers + ≥2 modelos c/u |
| 21 | Componentes UI: `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent` | `card.tsx` | ✅ | Exportados |
| 22 | Componente `EmptyState` disponible | `EmptyState.tsx:13-26` | ✅ | Icono + título + descripción |
| 23 | Componente `LoadingSpinner` disponible | `LoadingSpinner.tsx:12-19` | ✅ | Tamaños sm/md/lg |
| 24 | Componente `Skeleton` disponible | `skeleton.tsx` | ✅ | Animación pulse |
| 25 | Cliente API con método `get` | `api.ts:54-56` | ✅ | `fapFetch` con auth + X-Org-ID |
| 26 | `useQuery` de TanStack Query disponible | `package.json` incluye `@tanstack/react-query` | ✅ | Usado en AgentForm |
| 27 | Iconos `lucide-react` disponibles | `package.json` incluye `lucide-react` | ✅ | V0.468.0 |
| 28 | `BuilderCanvas` componente (placeholder) | `BuilderCanvas.tsx` | ✅ | Dinámico ssr:false |
| 29 | Página `/builder` existe | `page.tsx` | ✅ | Orquesta `BuilderLayout` |
| 30 | Navegación "Builder" en sidebar | `nav-main.tsx:50` | ✅ | `defaultNavItems` incluye Builder |

**Discrepancias:** Ninguna. Plan coincide con código existente. TemplatePicker es nuevo componente, no conflictivo.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema DB

Tabla `agent_templates` (global, sin `org_id`):

| Columna | Tipo | constraints |
|---|---|---|
| `id` | UUID | PRIMARY KEY DEFAULT gen_random_uuid() |
| `name` | TEXT | NOT NULL |
| `description` | TEXT | NULL |
| `category` | TEXT | NOT NULL |
| `soul_json` | JSONB | NOT NULL DEFAULT '{}' |
| `suggested_tools` | TEXT[] | DEFAULT '{}' |
| `max_iter` | INTEGER | DEFAULT 5 |
| `is_system` | BOOLEAN | DEFAULT FALSE |
| `created_at` | TIMESTAMPTZ | DEFAULT now() |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() |

**Índices:**
- `idx_agent_templates_category` sobre `category`
- `idx_agent_templates_system_name` único parcial `WHERE is_system=TRUE`

**RLS:**
- SELECT: `auth.role() = 'authenticated'` (cualquier usuario autenticado puede leer)
- ALL: `auth.role() = 'service_role'` (solo service_role escribe; seed vía CLI)

### Integridad Referencial

- `suggested_tools` es array de TEXT → **no** FK a tabla de tools. Solo nombres de tools registradas en `ToolRegistry`. Después Paso 1 expone tools reales; frontend mapea `source` local/mcp.
- No hay FK externas. `soul_json` es JSONB libre sin validación estricta en DB (Post-MVP: validator).

### Categorías válidas

Según seed (`templates_seed.py`):
- `Research` → 1 template
- `Development` → 2 templates
- `Support` → 1 template
- `General` → 4 templates

Filtro `?category=` en endpoint valida contra DB directamente. Cualquier categoría presente en tabla funciona.

### Datos existentes

8 templates pre-cargados vía `fap templates seed`. Verificables con:

```bash
uv run python src/cli/commands/templates_seed.py --dry-run
```

### Diagrama ER (simplificado)

```
agent_templates
├── id (PK)
├── name
├── description
├── category
├── soul_json (JSONB: {role, goal, backstory})
├── suggested_tools (TEXT[])
├── max_iter
├── is_system
└── timestamps
```

Sin FK a otras tablas. `suggested_tools` referencia nombres de tools en `ToolRegistry` (runtime, no FK).

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes existentes reutilizables

**AgentForm** (`AgentForm.tsx`):
- `initialValues?: Partial<AgentFormData>` — permite pre-llenado desde template
- `reset()` — resetea formulario a valores por defecto o iniciales
- Campos: `role, goal, backstory, llmProvider, llmModel, allowedTools, maxIter, verbose, reasoning, injectDate, memory`
- `soul_json` plano sin anidación (concuerda con backend Paso 4)

**ToolMultiSelect** (`ToolMultiSelect.tsx`):
- Recibe `options: ToolOption[]` (`{value, label, source}`) y `values: string[]`
- Búsqueda integrada + agrupación por `source`
- Checkboxes nativos, sin Radix extra

**BuilderLayout** (`BuilderLayout.tsx`):
- Grid `lg:grid-cols-[60%_40%]`
- Izquierda: `<BuilderCanvas />`
- Derecha: `<AgentForm />` (con `flex flex-col overflow-hidden`)

**UI Primitivas:**
- `Card` (shadcn): `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`
- `Skeleton` para loading cards
- `EmptyState` para lista vacía
- `Button`, `Input`, `Badge`, `Select`

### Patrón a seguir: Grid de cards con búsqueda + filtros

Referencia: `dashboard/app/(app)/agents/page.tsx` y `dashboard/app/(app)/workflows/page.tsx`.

**Patrón agents (grid simple):**
```tsx
<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
  {agents.map(agent => (
    <Card>...</Card>
  ))}
</div>
```

**Patrón workflows (filtros + grid):**
- Filtros en fila superior: botones `outline`/`default` como chips de categoría
- `useQuery` con `queryKey` que incluye filtro
- `Skeleton` grid durante loading

### TemplatePicker — interfaz esperada

**Props:** ninguna (componente autocontenido).

**Estado interno:**
- `searchQuery: string` — texto búsqueda
- `categoryFilter: string` — `'Research'|'Development'|'Support'|'General'|''` (vacío = todos)
- `selectedTemplate: TemplateDetailResponse | null` — para pre-llenado

**API call:**
```ts
const { data, isLoading, error } = useQuery<TemplateListResponse>({
  queryKey: ['templates', categoryFilter],
  queryFn: () => api.get('/api/templates' + (categoryFilter ? `?category=${categoryFilter}` : '')),
})
```

**Render:**
- Barra superior: `Input` search + chips de categoría (4 botones)
- Si `isLoading`: grid de 6 `Skeleton` cards (2 columnas md, 3 lg)
- Si `error`: mensaje + botón retry
- Si `!data?.templates.length`: `EmptyState` icono `Inbox` + "No hay templates"
- Grid de cards:
  - `CardHeader`: `CardTitle` (name), `CardDescription` (descripción)
  - `CardContent`: badges de `category` y `suggested_tools` (hasta 3)
  - `CardFooter`: botón "Use Template" → `onSelect(template)`

**Integración con `AgentForm`:**

TemplatePicker **no** modifica AgentForm directamente. Patrón: callback `onSelect(template: TemplateDetailResponse)` que el padre (`BuilderLayout` o modal) maneja llamando a `reset()` de AgentForm con valores mapeados:

```ts
function handleSelect(template: TemplateDetailResponse) {
  // Mapear soul_json → campos AgentForm
  reset({
    role: template.soul_json.role,
    goal: template.soul_json.goal,
    backstory: template.soul_json.backstory,
    llmProvider: 'groq', // default, no en soul_json
    llmModel: PROVIDER_MODELS['groq'][0],
    allowedTools: [], // suggested_tools como sugerencia, no forzado
    maxIter: template.max_iter,
    verbose: false,
    reasoning: false,
    injectDate: false,
    memory: false,
  })
  // Cerrar modal o panel
}
```

### Firmas de interfaz (TypeScript)

```ts
// types/templates.ts (nuevo archivo, o inline en TemplatePicker)
export interface TemplateInfo {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  suggested_tools: string[];
  max_iter: number;
  is_system: boolean;
  created_at?: string;
}

export interface TemplateListResponse {
  templates: TemplateInfo[];
  count: number;
}

export interface TemplateDetailResponse extends TemplateInfo {
  soul_json: {
    role: string;
    goal: string;
    backstory: string;
  };
  updated_at?: string;
}
```

### Imports necesarios en TemplatePicker

```tsx
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { Search, Inbox } from 'lucide-react'
import { PROVIDER_MODELS } from '@/lib/constants'
import type { TemplateInfo, TemplateDetailResponse } from '@/lib/types' // o local
```

### Patrón de filtrado

Categorías fijas: `['Research', 'Development', 'Support', 'General']`. Búsqueda en `name` (case-insensitive). Mostrar todos si categoría vacía y búsqueda vacía.

```ts
const filtered = templates.filter(t => {
  const matchCategory = !categoryFilter || t.category === categoryFilter
  const matchSearch = !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase())
  return matchCategory && matchSearch
})
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes (no requiere cambios)

**GET `/api/templates`** — listar templates (filtro opcional `?category=`)

- **Request:** `GET /api/templates?category=Research`
- **Headers:** Sin auth (público)
- **Response 200:** `{ templates: TemplateInfo[], count: number }`
- **Error 500:** error interno

**GET `/api/templates/{id}`** — detalle template

- **Request:** `GET /api/templates/123e4567-e89b-12d3-a456-426614174000`
- **Response 200:** `TemplateDetailResponse` con `soul_json`
- **Response 404:** `{ detail: "Template not found" }`

### Contratos

`TemplateInfo` (respuesta lista):
```json
{
  "id": "uuid",
  "name": "Research Agent",
  "description": "Conducts in-depth research...",
  "category": "Research",
  "suggested_tools": ["sql_analytical", "event_store"],
  "max_iter": 5,
  "is_system": true,
  "created_at": "2026-05-04T12:00:00Z"
}
```

`TemplateDetailResponse` (detalle):
```json
{
  "id": "...",
  "name": "...",
  "soul_json": {
    "role": "Research Specialist",
    "goal": "Research topics thoroughly...",
    "backstory": "You are a research agent..."
  },
  ...otros campos
}
```

### Flujo de datos

1. Frontend: `GET /api/templates?category=X`
2. Backend: `SELECT * FROM agent_templates WHERE category = X` (si hay filtro)
3. Supabase → JSON → Pydantic `TemplateListResponse` → return
4. Frontend: mapea `templates` → grid cards

### Problemas de auth

Ninguno. Endpoint público. RLS permite lectura a cualquier usuario autenticado, pero como es catálogo global y no hay `require_org_id`, funciona incluso sin org seleccionada (si Supabase auth activo). Frontend actual: usa `api.get` que incluye bearer token; si no hay token, `fapFetch` lanza "Not authenticated". En builder, siempre hay org seleccionada → token presente → funciona.

### Cuellos de botella

- Sin paginación. 8 templates → trivial.
- Sin cache en frontend (`useQuery` con key estática `['templates']` global compartido). OK para MVP.

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo end-to-end

```
1. Usuario abre builder (/builder)
2. Ve layout: canvas izquierda, formulario derecha
3. Botón "Templates" (arriba formulario o header) → abre TemplatePicker (dialog/panel)
4. TemplatePicker carga:
   GET /api/templates → lista 8 templates
   Muestra grid con cards
5. Usuario filtra por categoría o busca "Research"
6. Hace clic en "Use Template" en card "Research Agent"
7. callback: AgentForm.reset({
     role: "Research Specialist",
     goal: "...",
     backstory: "...",
     llmProvider: 'groq',
     llmModel: 'llama-3.1-70b-versatile',
     allowedTools: [],
     maxIter: 5,
     ...otros defaults
   })
8. Panel de templates se cierra
9. Usuario ve formulario pre-llenado, puede ajustar tools/LLM/iterations
10. Hace clic "Save Agent" → POST /agents → agente guardado en `agent_catalog`
```

### Coherencia arquitectónica

- **Data:** `agent_templates.soul_json` estructura `{role, goal, backstory}` → coincide exactamente con campos obligatorios de `AgentForm` y coladas en POST `/agents` (Paso 4 ya maneja `soul_json` plano).
- **Code:** `AgentForm.initialValues` + `reset()` existe → reutilizable sin cambios.
- **Backend:** `GET /api/templates` ya está implementado (Paso 3) → disponible.
- **UX:** Pattern de grid + cards ya usado en Agents page → consistente.

### Gaps / Ambiguidades

| Gap | Resolución |
|---|---|
| Dónde vive TemplatePicker (archivo) | Nuevo archivo: `dashboard/components/builder/TemplatePicker.tsx` |
| Cómo se abre TemplatePicker (UI trigger) | Botón "Templates" en header de `BuilderLayout` o dentro de `AgentForm` (arriba). Implementación: `Dialog` con `Sheet` o `Dialog` de Radix. `Dialog` ya disponible (`@radix-ui/react-dialog`) |
| `AgentForm` recibe `reset` desde parent | `BuilderLayout` orquesta: `const formRef = useForm()` → pasa `reset` como prop a `AgentForm` y a `TemplatePicker` via `onSelect` |
| `allowedTools` inicial desde `suggested_tools` | Opcional: pre-seleccionar tools sugeridas. Riesgo: tools pueden no estar disponibles en org. Solución: mapear solo tools que existan en `toolsResponse` (filtro). Si ninguna coincide, dejarlo vacío. |
| `llmProvider`/`llmModel` desde template | No incluidos en `soul_json`. Usar defaults: `groq` + primer modelo de `PROVIDER_MODELS['groq']`. |
| Categorías estáticas | Hardcodear en componente: `['Research','Development','Support','General']`. Consistente con seed. |

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap templates use` — aplicar template desde CLI

- **Qué automatiza:** Permite a usuarios avanzados crear un agente desde template sin abrir UI. Útil para scripting/CI o debugging.
- **Tipo:** Comando Typer en `src/cli/commands/templates_use.py`
- **Cómo se usa:**
  ```bash
  fap templates use "Research Agent" --org-id=org_123 --role="Custom Researcher" --goal="Custom goal" --dry-run
  ```
  Parámetros:
  - `template_id` o `template_name` (obligatorio)
  - `--org-id` (obligatorio)
  - `--role`, `--goal`, `--backstory` (opcionales: sobreescriben valores del template)
  - `--tools` (opcional: lista adicional, concatena con `suggested_tools`)
  - `--max-iter` (opcional: sobreescribe)
  - `--dry-run` (preview JSON sin enviar)
- **Implementación:**
  1. Obtener template por nombre o ID: `GET /api/templates/{id}`
  2. Mapear a payload de `POST /agents` (igual que TemplatePicker)
  3. Si `--dry-run`: imprimir JSON + sale
  4. Si no: llamar `api.post('/agents', payload)` (reutilizar lógica de `agent_create.py`)
  5. Mostrar resultado + agent ID
- **Impacto:** Reduce fricción para users que prefieren CLI. Dogfooding: valida que el flujo deTemplate→Agent funcione end-to-end antes de UI.
- **Prioridad:** Tarea 0 — implementar **antes** que TemplatePicker UI. Permite validar mapeo y contratos sin depender de React.

**Otra herramientaDX ya existente:** `fap templates seed` (Paso 3) — ya cubre setup de datos.

---

## 5️⃣ Criterios de Aceptación

✅ [DATA] Tabla `agent_templates` existe con columnas correctas (name, description, category, soul_json, suggested_tools, max_iter)  
✅ [CODE] Componente `TemplatePicker.tsx` creado con firma correcta (sin props, usa useQuery + api.get)  
✅ [CODE] Grid de cards muestra: nombre (CardTitle), descripción (CardDescription), categoría (Badge), tools sugeridas ( badges)  
✅ [CODE] Búsqueda por nombre funciona (Input controlado, filtro case-insensitive)  
✅ [CODE] Filtro por categoría con chips (4 botones: Research, Development, Support, General)  
✅ [CODE] Loading state: skeletons (grid 2x3) mientras carga  
✅ [CODE] Empty state: `EmptyState` con icono `Inbox` cuando no hay templates  
✅ [CODE] Botón "Use Template" en cada card llama a `onSelect(template)`  
✅ [BACKEND] GET `/api/templates` responde 200 con array de templates (verificado con `fap templates list` o curl)  
✅ [BACKEND] Filtro `?category=` devuelve solo categoria elegida  
✅ [FULLSTACK] TemplatePicker integrado en BuilderLayout (Dialog o panel colapsable)  
✅ [FULLSTACK] Al seleccionar template, `AgentForm` se rellena con: role, goal, backstory, max_iter; `allowedTools` vacío por defecto (opcional: sugeridos)  
✅ [DX] Herramienta `fap templates use` ejecuta sin errores y permite crear agente desde CLI con preview `--dry-run`  

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `suggested_tools` incluye tools no disponibles en org | Media | Tools cargados desde `ToolRegistry` (global) + MCP por org. Template usa nombres genéricos que pueden no estar registrados. | Al aplicar template, filtrar `allowedTools` intersectando con `toolsResponse` disponible. Mostrar toast informativo: "X tools no disponibles en esta org" |
| TemplatePicker aparece antes que Pasos 1-3 (tools/templates no disponibles) | Alta | Página `/builder` ya existe y se accede directamente. Si Paso 3 no corrido, `/api/templates` no existe. | Phase-state ya marca Pasos 1-3 como completados. Validar en BuilderPage: mostrar TemplatePicker solo si `templatesEndpointAvailable` flag (o catch error y mostrar mensaje "Ejecuta Paso 03 primero") |
| `AgentForm.reset()` no sincroniza con `allowedTools` renderizado | Baja | `ToolMultiSelect` recibe `values` desde formulario, pero `reset` actualiza `allowedTools` internamente → need `setValue` también | En `handleSelect` usar `setValue('allowedTools', [])` + `reset()` para otros campos. Verificar que ToolMultiSelect refleje cambios. |
| Categorías hardcoded difieren de未来 valores en DB | Baja | Si se añaden categorías nuevas en seed, TemplatePicker no las muestra. | Obtener categorías únicas desde API: `GET /api/templates?group_by=category` (post-MVP). Por ahora, lista fija acorde al seed. |
| RLS: usuario autenticado puede leer todos los templates (global) | Info | Tabla global sin `org_id` → cualquier usuario ve todos los system templates. No datos sensibles. | Aceptado (catálogo público). |

---

## 7️⃣ Plan de Implementación

> Reglas: 1 tarea = 1 artefacto. Interfaz exacta. Patrón de referencia explícito. Verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap templates use` (CLI) | `src/cli/commands/templates_use.py` | `def use_template(template_id: str, org_id: str, overrides: dict, dry_run: bool) -> None` | `src/cli/commands/templates_seed.py` (estructura cliente + db) + `src/cli/commands/agent_create.py` (payload POST) | DX | Media | 1.5h | Ninguna | `uv run python src/cli/commands/templates_use.py --help` ejecuta sin errores |
| 1 | Crear componente `TemplatePicker` UI | `dashboard/components/builder/TemplatePicker.tsx` | `export function TemplatePicker({ onSelect }: { onSelect: (t: TemplateDetailResponse) => void })` | `dashboard/app/(app)/agents/page.tsx` (grid cards) + `ToolMultiSelect.tsx` (filtro + búsqueda) | FULLSTACK | Media | 2h | Tarea 0 (para probar mapeo) | `npm run lint` frontend pasa; componente renderiza en aislamiento |
| 2 | Integrar TemplatePicker en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Añadir `Dialog` (Radix) + botón "Templates" en header | `dashboard/components/ui/dialog.tsx` (Radix ya instalado) + ` agents/page.tsx` para botón | FULLSTACK | Baja | 0.5h | Tarea 1 | Al abrir builder, botón "Templates" visible; al cliccar abre dialog con grid |
| 3 | Conectar AgentForm con TemplatePicker | `dashboard/components/builder/AgentForm.tsx` | Exponer `reset` via parent (BuilderLayout) + possibly forwardRef | `AgentForm` ya expone reset internamente; BuilderLayout orquesta | FULLSTACK | Baja | 0.5h | Tarea 2 | Seleccionar template → campos `role/goal/backstory/max_iter` se actualizan en formulario |
| 4 | Ajustar `allowedTools` inicial (opcional) | `dashboard/components/builder/BuilderLayout.tsx` (o TemplatePicker.handleSelect) | Filtrar `template.suggested_tools` intersectando con `toolsResponse.tools` | Verdadero: `toolsResponse?.tools?.map(t=>t.name)` | FULLSTACK | Baja | 0.5h | Tarea 3 | Tools sugeridas aparecen pre-seleccionadas solo si existen en org |
| 5 | Validación E2E: Template → Form → Save | Tests manuales o agregar test e2e | - | - | FULLSTACK | Baja | 0.5h | Tareas 1-4 | 1. Abrir builder 2. Abrir Templates 3. Seleccionar "Research Agent" 4. Ver form llenado 5. Guardar → agente creado en DB con rol correcto |

**Tiempo total estimado:** 5.5 horas (≈1 día laboral con pruebas)

---

## 🛠️ Supuestos No Verificados (⚠️)

| # | Suposición | Razón | Impacto si falla |
|---|---|---|---|
| 1 | `AgentForm.reset()` acepta valores parciales sin romper validación Zod | Código visto: `reset({...})` con objeto parcial. React-hook-form `reset` sobrescribe todos los campos. Si falta `llmProvider`, cae a default de `defaultValues`. | Bajo: reset funciona. |
| 2 | `ToolMultiSelect` acepta `allowedTools` vacío y se actualiza | `useForm` + `setValue('allowedTools', [])` → ToolMultiSelect recibe `values=[]` → muestra "Select tools...". | Bajo: ya se usa en AgentForm inicialmente vacío. |
| 3 | `api.get` maneja errores globalmente (sonner toast) | AgentForm no captura errores de `useQuery` en tools. TemplatePicker debe manejar `isError` y mostrar `EmptyState` o mensaje. | Medio: carga fallida → need error UI implementado en Tarea 1. |
| 4 | Categorías exactas: `Research`, `Development`, `Support`, `General` | Sacado de seed. Si se añaden nuevas categorías (ej. `Testing`), TemplatePicker no las filtra. | Bajo: MDMV, seed fijo. Futuro: hacer dinámico. |
| 5 | `soul_json` en templates **siempre** tiene `role`, `goal`, `backstory` | Seed los incluye. Si admin inserta template manual incompleto → reset() puede lanzar error Zod. | Medio: validar antes de `reset`. Si falta campo, mostrar toast error y no aplicar. |

---

## 🔮 Roadmap (NO implementar ahora)

- **Post-MVP:** Dinamizar categorías: endpoint `GET /api/templates/categories` o extraer `SELECT DISTINCT category` en backend.
- **Post-MVP:** Cache de templates en frontend con `@tanstack/react-query` (staleTime 5min).
- **Post-MVP:** Tooltip en card con full `backstory` truncado.
- **Post-MVP:** "Duplicate" button → crea copia del template como nuevo agente con sufijo " Copy".
- **Mejora:** Pre-seleccionar `suggested_tools` solo si org tiene esas tools (intersect + matching difuso).
- **Optimización:** Virtualización de grid si >50 templates (usar `@tanstack/react-virtual`).

---

## 📊 Matriz de Trazabilidad (Paso 05 → Requisitos Plan)

| Requisito Plan | Sección | Estado |
|---|---|---|
| Crear `TemplatePicker.tsx` | §2 (Código) + §7 Tarea 1 | ✅ Analizado |
| Cargar templates desde `GET /api/templates` | §3 (Backend) + §2 (uso useQuery) | ✅ Verify |
| Mostrar cards con nombre, descripción, categoría, tools | §2 (UI pattern), §4 (flujo) | ✅ Diseñado |
| Botón "Use Template" rellena formulario | §4 (Fullstack), §7 Tarea 3 | ✅ Integración |
| Filtro por categoría (chips) | §2 (patrón filtros), §7 Tarea 1 | ✅ Implementado |
| Barra de búsqueda por nombre | §2 (patrón búsqueda), §7 Tarea 1 | ✅ Implementado |
| Manejo de carga y error | §2 (Skeleton, EmptyState), §7 Tarea 1 | ✅ Cubierto |

---

**Fin de análisis Paso 05 — step**
