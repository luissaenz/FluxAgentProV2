# Análisis Técnico — Paso 4: Página del builder — layout y formulario de agente

**Agente:** gif  
**Fecha:** 2026-05-14  
**Rol:** Ingeniero de Software Senior — Análisis basado en código fuente real

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `reactflow` en package.json | grep en `dashboard/package.json` | ❌ DISCREPANCIA | NO existe. Plan dice `npm install reactflow` pero package renombrado a `@xyflow/react` v12. Usar `@xyflow/react` |
| 2 | `dashboard/app/(app)/builder/` | ls en `dashboard/app/(app)/` | ✅ NO existe | Directorio no creado — tarea de creación |
| 3 | `dashboard/components/builder/` | ls en `dashboard/components/` | ✅ NO existe | Directorio no creado — tarea de creación |
| 4 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql` | ✅ VERIFICADO | Línea 6-17, migración 004 |
| 5 | Columnas `agent_catalog` | grep en migración 004 | ✅ VERIFICADO | `id`, `org_id`, `role`, `is_active`, `soul_json`, `allowed_tools`, `max_iter`, `created_at`, `updated_at` |
| 6 | Columna `model` en `agent_catalog` | grep en migración 004 | ❌ NO EXISTE | Plan usa `model` en AgentDetail, pero DB no tiene columna. Solo en TypeScript type como campo enriquecido |
| 7 | Patrón save directo a Supabase desde frontend | `dashboard/app/(app)/agents/page.tsx:21-26` | ✅ VERIFICADO | `createClient()` + `supabase.from('agent_catalog').select('*')` |
| 8 | Componente `Switch` existe | `dashboard/components/ui/switch.tsx` | ✅ VERIFICADO | shadcn/ui Switch |
| 9 | Componente `Select` existe | `dashboard/components/ui/select.tsx` | ✅ VERIFICADO | shadcn/ui Select con @radix-ui/react-select |
| 10 | Componente `Slider` existe | `dashboard/components/ui/slider.tsx` | ❌ NO EXISTE | Plan requiere slider para Max Iterations (1-10). No hay componente shadcn/ui slider instalado |
| 11 | Componente multi-select para tools | grep en `dashboard/components/` | ❌ NO EXISTE | No hay multi-select component. Plan requiere tools multi-select desde endpoint real |
| 12 | Zod instalado | grep en `dashboard/package.json` | ❌ NO DIRECTO | `@hookform/resolvers` presente (v5.2.2) que requiere zod/validator. `zod` debe ser peer dep |
| 13 | `react-hook-form` instalado | `dashboard/package.json:40` | ✅ VERIFICADO | `react-hook-form: ^7.72.1` |
| 14 | `GET /api/tools/available` endpoint | `src/api/routes/tools.py:46-63` | ✅ VERIFICADO | Endpoint real que retorna `ToolInfo[]` con `name`, `description`, `category`, `source` |
| 15 | `fapFetch` / `api` helper existe | `dashboard/lib/api.ts:54-77` | ✅ VERIFICADO | `api.get()`, `api.post()`, etc con auth + org headers |
| 16 | Patrón form existente en dashboard | Revisión de componentes | ⚠️ NO VERIFICABLE | No hay forms complejos con react-hook-form en dashboard aún. Architect page usa useState manual |
| 17 | `useCurrentOrg` hook existe | `dashboard/hooks/useCurrentOrg.ts` | ✅ VERIFICADO | Retorna `{ orgId, currentOrg }` |
| 18 | Nav sidebar builder link existe | `dashboard/components/nav-main.tsx:43-63` | ❌ NO EXISTE | No hay entrada "Builder" en `defaultNavItems` |
| 19 | `@hookform/resolvers` en package.json | `dashboard/package.json:13` | ✅ VERIFICADO | `@hookform/resolvers: ^5.2.2` |
| 20 | Patrón de página (`(app)`) existente | `dashboard/app/(app)/agents/page.tsx` | ✅ VERIFICADO | `'use client'` + `useCurrentOrg` + `createClient` + `useQuery` |

### Discrepancias Detectadas

| ID | Discrepancia | Resolución |
|---|---|---|
| D1 | `reactflow` no existe como package. Renombrado a `@xyflow/react` desde v12 | Usar `npm install @xyflow/react` en vez de `reactflow`. API de ReactFlow v12 cambió — revisar `@xyflow/react` docs |
| D2 | `agent_catalog` NO tiene columna `model`, `llm_provider`, `verbose`, `reasoning`, `memory`, `inject_date` | Campos adicionales deben ir dentro de `soul_json` JSONB. Formulario debe serializar config completa (provider, model, toggles) dentro de soul_json |
| D3 | No existe componente `Slider` para Max Iterations | Crear `slider.tsx` basado en shadcn/ui Slider o usar Input type="range" con estilos. Patrón: `dashboard/components/ui/slider.tsx` siguiendo demás componentes shadcn |
| D4 | No existe multi-select para Tools | Usar shadcn/ui `Select` con múltiple selección simulada, o crear multi-select. Carga desde `api.get('/api/tools/available')` con `useQuery` |
| D5 | No existe entrada "Builder" en sidebar nav | Agregar a `defaultNavItems` en `nav-main.tsx` con icono `Wand2` (ya importado) |
| D6 | LLM Provider → Model mapping no definido en ningún lado | Crear mapa estático `PROVIDER_MODELS` en `constants.ts` o dentro del componente. Sin endpoint API para esto |
| D7 | `agent_catalog` guarda `role` como columna separada, `goal`/`backstory` dentro de `soul_json` | Form debe mapear: `role` → columna role, `goal` → `soul_json.goal`, `backstory` → `soul_json.backstory`, config adicional → resto de soul_json |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema afectado

**Tabla existente:** `agent_catalog` (migración 004)

| Columna | Tipo | Uso en formulario |
|---|---|---|
| `id` | UUID PK | Autogenerado |
| `org_id` | UUID FK → organizations | De `useCurrentOrg()` |
| `role` | TEXT | Input "Role" del formulario |
| `is_active` | BOOLEAN DEFAULT TRUE | No expuesto en UI. Dejar TRUE por defecto |
| `soul_json` | JSONB | Almacena: `goal`, `backstory`, `llm_provider`, `llm_model`, `verbose`, `reasoning`, `inject_date`, `memory` |
| `allowed_tools` | TEXT[] | Multi-select "Tools" |
| `max_iter` | INTEGER DEFAULT 5 | Slider (1-10, default 3) |
| `created_at` | TIMESTAMPTZ | Autogenerado |
| `updated_at` | TIMESTAMPTZ | Autogenerado |

### No se requieren migraciones nuevas
Paso 4 no crea/modifica tablas. Usa `agent_catalog` existente.

### Estructura de `soul_json`
```json
{
  "goal": "string (textarea)",
  "backstory": "string (textarea)",
  "llm_provider": "groq | openai | anthropic | openrouter",
  "llm_model": "string (depende del provider)",
  "config": {
    "verbose": true | false,
    "reasoning": true | false,
    "inject_date": true | false,
    "memory": true | false
  }
}
```

### RLS aplicable
`agent_catalog` tiene `agent_catalog_tenant_isolation` (FOR ALL USING org_id). Guardado directo desde frontend requiere RLS policy que permita INSERT a usuarios autenticados. Verificar con `show_rls_policies`.

⚠️ **RIESGO:** Si Supabase RLS no permite INSERT directo desde frontend (solo permite SELECT via policy auth), guardado fallará. Confirmar política actual de `agent_catalog`.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a crear

#### A. `dashboard/app/(app)/builder/page.tsx`
- **Patrón:** `dashboard/app/(app)/agents/page.tsx`
- **Tipo:** `'use client'`
- **Estructura:**
  - Renderiza `BuilderLayout`
  - No necesita queries propias (layout maneja estado)
  - Responsive container

#### B. `dashboard/components/builder/BuilderLayout.tsx`
- **Firma:** `export function BuilderLayout()`
- **Patrón:** Split panel (60% canvas / 40% form)
- **Estructura:**
  - Flex container con dos hijos
  - Izquierda: `BuilderCanvas`
  - Derecha: `AgentForm`
  - Estado compartido vía props (selected agent data, dirty state)
  - Responsive: stack en mobile

#### C. `dashboard/components/builder/AgentForm.tsx`
- **Firma:** `export function AgentForm({ onSave }: { onSave?: (data: AgentFormData) => void })`
- **Campos:**

| Campo | Tipo | Componente | Validación |
|---|---|---|---|
| `role` | string | Input | Zod: `z.string().min(1, "Role requerido")` |
| `goal` | string | Textarea | Zod: `z.string().min(1, "Goal requerido")` |
| `backstory` | string | Textarea | Zod: `z.string().min(1, "Backstory requerido")` |
| `llm_provider` | enum | Select | Zod: `z.enum(["groq","openai","anthropic","openrouter"])` |
| `llm_model` | string | Select (dinámico) | Zod: `z.string().min(1)` |
| `allowed_tools` | string[] | Multi-select | Zod: `z.array(z.string())` |
| `max_iter` | number | Slider (1-10, default 3) | Zod: `z.number().int().min(1).max(10)` |
| `verbose` | boolean | Switch | Zod: `z.boolean()` |
| `reasoning` | boolean | Switch | Zod: `z.boolean()` |
| `inject_date` | boolean | Switch | Zod: `z.boolean()` |
| `memory` | boolean | Switch | Zod: `z.boolean()` |

- **Form library:** `react-hook-form` + `@hookform/resolvers/zod`
- **Provider → Model mapping:** Estático en `constants.ts`
- **Carga tools:** `useQuery(['available-tools'], () => api.get('/api/tools/available'))`
- **Botón "Save Agent":** Inserta en `agent_catalog` vía `createClient().from('agent_catalog').insert({...})`
- **Botón "Clear":** `form.reset()` con valores default

#### D. `dashboard/components/builder/BuilderCanvas.tsx`
- **Firma:** `export function BuilderCanvas()`
- **Patrón:** Contenedor ReactFlow vacío (placeholder hasta Paso 07)
- **Estructura:**
  - Estado vacío: EmptyState "Arma tu crew visualmente"
  - No usa ReactFlow aún (sin nodes/edges)
  - Se poblará en Paso 07

#### E. `dashboard/components/ui/slider.tsx` (NUEVO)
- **Patrón:** Seguir estructura de `dashboard/components/ui/switch.tsx`
- **Firma:** `React.forwardRef<HTMLInputElement, SliderProps>` usando @radix-ui/react-slider

#### F. `dashboard/components/builder/MultiSelect.tsx` (NUEVO, opcional)
- **Alternativa:** Usar shadcn/ui Select con `multiple` + checkboxes
- **Firma:** `export function MultiSelect({ options, values, onChange, placeholder })`

### Patrón a seguir
- **Página:** `dashboard/app/(app)/agents/page.tsx` — `'use client'`, `useCurrentOrg()`, `createClient()` desde supabase
- **Form:** No existe form complejo previo → crear nuevo patrón usando react-hook-form + zod
- **Componentes UI:** `switch.tsx`, `select.tsx`, `card.tsx` como referencia de estilo shadcn/ui

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints consumidos

| Endpoint | Método | Uso en formulario |
|---|---|---|
| `/api/tools/available` | GET | Cargar tools en multi-select |
| `supabase.from('agent_catalog').insert()` | Supabase directo | Guardar agente |

### No se crean nuevos endpoints
Paso 4 es frontend-only. Backend ya implementado en pasos 1-3.

### Auth implícita
- Tools endpoint: requiere `X-Org-ID` header vía `api.ts` (usa `localStorage.getItem('organization_id')`)
- Supabase directo: usa sesión del browser (RLS de `agent_catalog`)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
[Builder Page] → [AgentForm] → role, goal, backstory, config
       ↓                                              ↓
[BuilderCanvas] (placeholder)           [supabase insert agent_catalog]
       ↓                                              ↓
[Paso 07: ReactFlow canvas]          [Tabla agent_catalog persistida]
```

### Coherencia
- ✅ Tools endpoint real disponible
- ✅ Supabase insert directo viable (mismo patrón que agents page)
- ✅ Zod validación integrable con react-hook-form via `@hookform/resolvers`
- ⚠️ Slider y multi-select requieren componentes nuevos
- ⚠️ Provider→Model mapping debe definirse static (sin endpoint)

### DX & Tooling

```
### Herramienta Propuesta: npm run scaffold:builder
- **Qué automatiza:** Creación de toda la estructura de archivos del builder (page, components, types) con boilerplate de react-hook-form + zod schema + react-query hooks
- **Tipo:** Script npm / CLI
- **Cómo se usa:** `npm run scaffold:builder` en `dashboard/` — genera:
  - `dashboard/app/(app)/builder/page.tsx`
  - `dashboard/components/builder/AgentForm.tsx`
  - `dashboard/components/builder/BuilderCanvas.tsx`
  - `dashboard/components/builder/BuilderLayout.tsx`
  - `dashboard/lib/builder-types.ts`
  - `dashboard/lib/builder-schema.ts`
- **Impacto:** Setup manual actual requiere crear 5+ archivos con imports cross-referencia. Script reduce setup de 15min → 1seg
- **Prioridad:** Tarea 0 — implementar antes del resto

### Herramienta Propuesta: fap builder scaffold (CLI)
- **Qué automatiza:** Lo mismo que el script npm pero desde backend CLI
- **Tipo:** Comando CLI
- **Cómo se usa:** `fap builder scaffold --output dashboard/`
- **Impacto:** Misma reducción. Útil si el equipo prefiere CLI
- **Prioridad:** Tarea 0 alternativa
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] `agent_catalog` tabla existe con columnas correctas (004 migration)
✅ [DATA] `soul_json` almacena goal, backstory y config completa del agente
✅ [CODE] `BuilderLayout.tsx` renderiza split panel 60/40
✅ [CODE] `AgentForm.tsx` usa react-hook-form + zod resolver
✅ [CODE] `AgentForm.tsx` carga tools desde GET /api/tools/available via react-query
✅ [CODE] Validación Zod: role, goal, backstory requeridos; max_iter 1-10
✅ [CODE] Select de LLM Provider cambia opciones de LLM Model dinámicamente
✅ [CODE] Slider para Max Iterations (1-10, default 3) funcional
✅ [CODE] Switch toggles para verbose, reasoning, inject_date, memory
✅ [BACKEND] No requiere nuevos endpoints (usa tools endpoint + supabase directo)
✅ [FULLSTACK] "Save Agent" inserta en agent_catalog con org_id + soul_json correcto
✅ [FULLSTACK] "Clear" resetea formulario a valores default
✅ [FULLSTACK] `@xyflow/react` instalado correctamente (D1 resuelta)
✅ [DX] Slider y multi-select componentes creados (D3, D4 resueltas)
✅ [DX] Nav sidebar incluye entrada "Builder" con icono Wand2 (D5 resuelta)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| RLS bloquea INSERT directo desde frontend | Alta | `agent_catalog` policy solo permite SELECT auth. INSERT requiere service_role o policy más permisiva | Verificar policy actual. Si no permite INSERT → crear policy `agent_catalog_insert` FOR INSERT WITH CHECK (org_id::text = current_setting('app.org_id', TRUE)) |
| `@xyflow/react` API incompatible con plan | Media | Plan escrito para `reactflow` (v11). v12 (`@xyflow/react`) cambió API drásticamente | BuilderCanvas es placeholder vacío. No requiere ReactFlow hasta Paso 07. Instalar pero no implementar lógica reactflow ahora |
| Provider→Model mapping desactualizado | Media | Mapping estático en frontend. Nuevos modelos requieren deploy | Documentar en constants.ts con comentario de actualización. Post-MVP: endpoint `/api/models/available` |
| Sin experiencia previa con react-hook-form en codebase | Baja | No hay forms complejos existentes. Implementador debe establecer patrón nuevo | Usar ejemplo mínimo: `useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) })` con `handleSubmit` |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: Scaffold builder structure** | Script npm `scaffold:builder` | — | — | DX | Baja | 0.5h | Ninguna | → verificar: `ls dashboard/app/(app)/builder/` + `ls dashboard/components/builder/` muestra archivos esperados |
| 1 | Instalar dependencias | `dashboard/package.json` | `npm install @xyflow/react @radix-ui/react-slider zod` | — | CODE | Baja | 0.2h | Ninguna | → verificar: `grep "@xyflow/react" dashboard/package.json` existe |
| 2 | Crear Slider component | `dashboard/components/ui/slider.tsx` | `export const Slider = React.forwardRef<HTMLInputElement, { min: number; max: number; step?: number; value: number[]; onValueChange: (v: number[]) => void }>` | `dashboard/components/ui/switch.tsx` — patrón shadcn/ui con Radix | CODE | Baja | 0.3h | Tarea 1 | → verificar: importable sin error |
| 3 | Crear tipos y schema Zod | `dashboard/lib/builder-types.ts` | `export interface AgentFormData { role, goal, backstory, llm_provider, llm_model, allowed_tools, max_iter, verbose, reasoning, inject_date, memory }` + Zod schema | `dashboard/lib/types.ts` — patrón interfaces existentes | CODE | Baja | 0.3h | Ninguna | → verificar: schema compila con `z.infer` |
| 4 | Crear Provider→Model mapping | `dashboard/lib/constants.ts` (extender) | `export const PROVIDER_MODELS = { groq: [...], openai: [...], anthropic: [...], openrouter: [...] }` | `dashboard/lib/constants.ts` — extender constante existente | CODE | Baja | 0.2h | Ninguna | → verificar: mapping completo con ≥2 modelos por provider |
| 5 | Crear AgentForm | `dashboard/components/builder/AgentForm.tsx` | `export function AgentForm({ onSave, onClear }: { onSave?: (data: AgentFormData) => Promise<void>; onClear?: () => void })` | Sin patrón exacto (primer form complejo). Usar `react-hook-form` + `zodResolver` + tanstack `useQuery` para tools | CODE | Alta | 2h | Tareas 2, 3, 4 | → verificar: form renderiza 11 campos + carga tools desde API + botones Save/Clear funcionan |
| 6 | Crear BuilderCanvas | `dashboard/components/builder/BuilderCanvas.tsx` | `export function BuilderCanvas()` | `dashboard/components/shared/EmptyState.tsx` — estado vacío con placeholder | CODE | Baja | 0.3h | Tarea 1 | → verificar: renderiza EmptyState |
| 7 | Crear BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | `export function BuilderLayout()` | — | CODE | Media | 0.5h | Tareas 5, 6 | → verificar: split panel 60/40 visible |
| 8 | Crear builder page | `dashboard/app/(app)/builder/page.tsx` | `export default function BuilderPage()` | `dashboard/app/(app)/agents/page.tsx` — patrón page `'use client'` | CODE | Baja | 0.2h | Tarea 7 | → verificar: navegación a `/builder` carga layout |
| 9 | Guardar agente en Supabase | Lógica en AgentForm | `supabase.from('agent_catalog').insert({ org_id, role, soul_json, allowed_tools, max_iter })` | `dashboard/app/(app)/agents/page.tsx:21-26` — patrón supabase insert | FULLSTACK | Media | 0.5h | Tarea 5 | → verificar: agente se crea en tabla `agent_catalog` (SELECT desde dashboard) |
| 10 | Agregar Builder a nav sidebar | `dashboard/components/nav-main.tsx` | Agregar `{ title: 'Builder', url: '/builder', icon: Wand2 }` en `defaultNavItems` | `nav-main.tsx:51-55` — patrón nav item | FULLSTACK | Baja | 0.2h | Tarea 8 | → verificar: link "Builder" visible en sidebar + navega a `/builder` |

**Tiempo total estimado:** 4.7 horas

---

## 🔮 Roadmap

- **Post-MVP:** Endpoint `/api/models/available` para evitar mapping estático de modelos
- **Post-MVP:** Agregar columna `model` a `agent_catalog` via migración, en vez de almacenar en soul_json
- **Post-MVP:** Endpoint `POST /api/agents` como alternativa a Supabase directo (abstrae RLS + validación server-side)
- **Pre-requisito para Paso 07:** BuilderCanvas debe migrarse de placeholder a ReactFlow real con nodos/edges
