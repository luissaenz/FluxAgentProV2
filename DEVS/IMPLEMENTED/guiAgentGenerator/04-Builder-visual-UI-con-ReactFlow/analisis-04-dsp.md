# 🧠 Análisis Técnico — Paso 04 / Agente dsp

> **Fase:** `guiAgentGenerator`
> **Paso:** Página del builder — layout y formulario de agente
> **Agente:** dsp
> **Fecha:** 2026-05-14
> **`proyecto-config.json`:** Leído ✅

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` existe | grep migrations | ✅ | `supabase/migrations/004_agent_catalog.sql:6-17` |
| 2 | `agent_catalog` columnas: `id uuid`, `org_id uuid`, `role text`, `soul_json jsonb`, `allowed_tools text[]`, `max_iter int` | verificar schema | ✅ | `004_agent_catalog.sql:7-14` |
| 3 | `agent_catalog.UNIQUE(org_id, role)` | verificar constraint | ✅ | `004_agent_catalog.sql:16` |
| 4 | `agent_catalog` ADD COLUMN `bundle_id` | verificar migración posterior | ✅ | `0026_bundle_system.sql:42` |
| 5 | Endpoint `GET /api/tools/available` existe | verificar routes | ✅ | `src/api/routes/tools.py:46-63` |
| 6 | Endpoint `GET /api/tools/available` retorna `ToolInfo` con name, description, category, source | verificar modelo | ✅ | `src/api/routes/tools.py:25-32` |
| 7 | `@supabase/ssr` instalado | package.json | ✅ | `dashboard/package.json:27` — `"@supabase/ssr": "^0.5.2"` |
| 8 | `@supabase/supabase-js` instalado | package.json | ✅ | `dashboard/package.json:28` — `"@supabase/supabase-js": "^2.47.12"` |
| 9 | `react-hook-form` instalado | package.json | ✅ | `dashboard/package.json:40` — `"react-hook-form": "^7.72.1"` |
| 10 | `@hookform/resolvers` instalado | package.json | ✅ | `dashboard/package.json:13` — `"@hookform/resolvers": "^5.2.2"` |
| 11 | Carpeta `dashboard/app/(app)/` existe | ls | ✅ | `dashboard/app/(app)/` — 11 sub-rutas |
| 12 | `dashboard/app/(app)/layout.tsx` — patrón layout con SidebarProvider | verificar | ✅ | `dashboard/app/(app)/layout.tsx:1-31` |
| 13 | Componente `AppSidebar` con `navMain` | verificar | ✅ | `dashboard/components/app-sidebar.tsx:1-72` |
| 14 | Componente `NavMain` con `defaultNavItems` | verificar | ✅ | `dashboard/components/nav-main.tsx:43-63` |
| 15 | `useCurrentOrg()` hook — retorna `{ orgId }` | verificar | ✅ | `dashboard/hooks/useCurrentOrg.ts:5-7` |
| 16 | `createClient()` browser supabase | verificar | ✅ | `dashboard/lib/supabase.ts:5-10` |
| 17 | Componentes UI existentes: Input, Textarea, Select, Switch, Button, Label, Card, Badge, Skeleton, Dialog | verificar | ✅ | `dashboard/components/ui/` — 26 archivos |
| 18 | `LoadingSpinner` componente | verificar | ✅ | `dashboard/components/shared/LoadingSpinner.tsx:12-19` |
| 19 | `EmptyState` componente | verificar | ✅ | `dashboard/components/shared/EmptyState.tsx:13-25` |
| 20 | Path alias `@/*` → `./*` | tsconfig.json | ✅ | `dashboard/tsconfig.json:17` |
| 21 | `soul_json` estructura — contiene `role`, `goal`, `backstory` | verificar uso existente | ✅ | `dashboard/app/(app)/agents/page.tsx:62` — acceso como `Record<string, string>` |
| 22 | `allowed_tools` usado como `string[]` en frontend | verificar tipos | ✅ | `dashboard/lib/types.ts:93` |
| 23 | `max_iter` como `number` en frontend | verificar tipos | ✅ | `dashboard/lib/types.ts:94` |
| 24 | `reactflow` instalado | package.json | ❌ | NO en dependencias |
| 25 | `zod` instalado | package.json | ❌ | NO instalado — `npm list zod` → empty |
| 26 | Slider (`@radix-ui/react-slider`) instalado | package.json | ❌ | NO instalado. Plan dice "Max Iterations (slider 1-10, default 3)" |
| 27 | Carpeta `dashboard/components/builder/` existe | ls | ❌ | No existe |
| 28 | Ruta `/dashboard/app/(app)/builder/` existe | ls | ❌ | No existe |
| 29 | `react-hook-form` usa `zodResolver` en código existente | grep | ❌ | `RunFlowDialog.tsx` usa `useForm()` sin resolver, sin zod |

**Discrepancias encontradas:** 5

| ID | Discrepancia | Resolución |
|---|---|---|
| D1 | `reactflow` NO instalado. Plan: `npm install reactflow` | Tarea previa: `npm install reactflow` |
| D2 | `zod` NO instalado. Plan requiere validación Zod | Tarea previa: `npm install zod` |
| D3 | Sin componente Slider. Plan dice slider para max_iter (1-10, default 3) | Alternativa: usar `Input type="number"` con min=1 max=10. Mejor: `npm install @radix-ui/react-slider` + crear `components/ui/slider.tsx`. Decisión: **usar Input type="number"** por MVP, Slider post-MVP. |
| D4 | Carpeta `builder/` no existe | Crear en Tarea 1 |
| D5 | `agent_catalog` tiene `UNIQUE(org_id, role)`. Plan: "Save Agent" guarda directo vía Supabase. Si mismo role ya existe → error 409 (duplicate key) | El formulario debe manejar `onConflict`: upsert o mostrar error "Role already exists". Mejor: **upsert vía `.upsert()`** con `onConflict: 'org_id,role'` para permitir re-guardar/editar. |

---

## 1️⃣ Análisis de Datos

### Tablas afectadas

| Tabla | Acción | Columnas relevantes |
|---|---|---|
| `agent_catalog` | INSERT (Save Agent) | `id`, `org_id`, `role`, `is_active`, `soul_json`, `allowed_tools`, `max_iter` |

### Schema existente — `agent_catalog`

```
agent_catalog
├── id             UUID PK DEFAULT gen_random_uuid()
├── org_id         UUID NOT NULL FK → organizations(id) ON DELETE CASCADE
├── role           TEXT NOT NULL
├── is_active      BOOLEAN DEFAULT TRUE
├── soul_json      JSONB NOT NULL DEFAULT '{}'
├── allowed_tools  TEXT[] DEFAULT '{}'
├── max_iter       INTEGER DEFAULT 5
├── bundle_id      UUID FK → bundle_imports(id) ON DELETE SET NULL  (mig 0026)
├── created_at     TIMESTAMPTZ DEFAULT now()
├── updated_at     TIMESTAMPTZ DEFAULT now()
└── UNIQUE(org_id, role)
```

### Integridad referencial

- `org_id` → `organizations(id)` ON DELETE CASCADE ✅
- `bundle_id` → `bundle_imports(id)` ON DELETE SET NULL ✅
- `soul_json` no tiene FK contra `agent_templates` (relación lógica, no estructural) — OK para MVP

### RLS

```
POLICY "agent_catalog_tenant_isolation" ON agent_catalog
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE))
```
- Desde frontend (Supabase client directo): la sesión del usuario autenticado + RLS se encargan automáticamente. El `org_id` debe coincidir con el del usuario logueado.
- No se requiere `require_org_id` en esta ruta porque es llamada directa de Supabase, no vía backend.

### Mapeo campos formulario → DB

| Campo Formulario | Tipo UI | Columna DB | Transformación |
|---|---|---|---|
| Role | Input text | `role` | Directo |
| Goal | Textarea | `soul_json.goal` | Empaquetar en `soul_json` |
| Backstory | Textarea | `soul_json.backstory` | Empaquetar en `soul_json` |
| LLM Provider | Select | `soul_json.llm_provider` | Empaquetar en `soul_json` |
| LLM Model | Select | `soul_json.llm_model` | Empaquetar en `soul_json` |
| Tools | Multi-select | `allowed_tools` | Array directo |
| Max Iterations | Input number | `max_iter` | Number directo |
| Verbose | Toggle | `soul_json.verbose` | Boolean en `soul_json` |
| Reasoning | Toggle | `soul_json.reasoning` | Boolean en `soul_json` |
| Inject Date | Toggle | `soul_json.inject_date` | Boolean en `soul_json` |
| Memory | Toggle | `soul_json.memory` | Boolean en `soul_json` |

### Estructura `soul_json` esperada

```json
{
  "role": "Research Agent",
  "goal": "Find and analyze...",
  "backstory": "Expert researcher with...",
  "llm_provider": "groq",
  "llm_model": "llama-3.1-70b-versatile",
  "verbose": true,
  "reasoning": false,
  "inject_date": true,
  "memory": false
}
```

> ⚠️ AVISO: El frontend actualmente accede a `soul_json` como `Record<string, string>` (`agents/page.tsx:62`). Los booleans en `soul_json` son `boolean`, no `string`. Esto ya funcionaba porque TS usa `Record<string, string>` como type assertion. Para el formulario nuevo, definir interfaz explícita.

### Tipos de datos problemáticos

- `soul_json` es JSONB → almacena cualquier estructura. No hay validación en DB. La validación ocurre en frontend (Zod) + Supabase acepta el JSON.
- `max_iter` debe ser 1-10. Validar en frontend (Zod `z.number().min(1).max(10)`).
- `allowed_tools` es `TEXT[]` → debe ser array de strings. Validar en frontend.

---

## 2️⃣ Análisis de Código

### Archivos a crear

| # | Archivo | Tipo | Función |
|---|---|---|---|
| 1 | `dashboard/app/(app)/builder/page.tsx` | Page | Entrada del builder, compone layout |
| 2 | `dashboard/components/builder/AgentForm.tsx` | Component | Formulario de agente con react-hook-form + zod |
| 3 | `dashboard/components/builder/BuilderCanvas.tsx` | Component | Contenedor ReactFlow vacío (placeholder Paso 07) |
| 4 | `dashboard/components/builder/BuilderLayout.tsx` | Component | Layout split panel 60/40 |

### Firmas de componentes

#### `AgentForm.tsx`

```typescript
interface AgentFormValues {
  role: string
  goal: string
  backstory: string
  llmProvider: string
  llmModel: string
  tools: string[]
  maxIter: number
  verbose: boolean
  reasoning: boolean
  injectDate: boolean
  memory: boolean
}

// Zod schema
const agentFormSchema = z.object({
  role: z.string().min(1, "Role is required"),
  goal: z.string().min(1, "Goal is required"),
  backstory: z.string().min(1, "Backstory is required"),
  llmProvider: z.string().default("groq"),
  llmModel: z.string().default("llama-3.1-70b-versatile"),
  tools: z.array(z.string()).default([]),
  maxIter: z.number().int().min(1).max(10).default(3),
  verbose: z.boolean().default(false),
  reasoning: z.boolean().default(false),
  injectDate: z.boolean().default(false),
  memory: z.boolean().default(false),
})

interface AgentFormProps {
  onSave?: (values: AgentFormValues) => void
  initialValues?: Partial<AgentFormValues>
}

export function AgentForm({ onSave, initialValues }: AgentFormProps)
```

**Patrón de referencia:** `dashboard/components/flows/RunFlowDialog.tsx` — uso de `react-hook-form` con `useForm()`, `handleSubmit`, componentes shadcn/ui. Extender con `zodResolver` para validación.

#### `BuilderCanvas.tsx`

```typescript
interface BuilderCanvasProps {
  className?: string
}

export function BuilderCanvas({ className }: BuilderCanvasProps)
// Renderiza div vacío con placeholder para ReactFlow.
// ReactFlow se importa dinámicamente en Paso 07.
```

**Patrón de referencia:** Componentes `EmptyState` + card con skeleton/placeholder.

#### `BuilderLayout.tsx`

```typescript
interface BuilderLayoutProps {
  canvas: React.ReactNode
  form: React.ReactNode
}

export function BuilderLayout({ canvas, form }: BuilderLayoutProps)
// Renderiza grid 60% izquierda / 40% derecha.
// Responsive: colapsa a stack vertical en mobile.
```

#### `builder/page.tsx`

```typescript
export default function BuilderPage()
// 'use client'
// Compone: BuilderLayout > { canvas: BuilderCanvas, form: AgentForm }
// Maneja save vía Supabase upsert en agent_catalog
```

**Patrón de referencia:** `dashboard/app/(app)/agents/page.tsx` — `'use client'` + `useQuery` + `useCurrentOrg` + `createClient`.

### Patrones a seguir

1. **`'use client'`** — todos los componentes del builder (ReactFlow + formulario necesitan cliente)
2. **`@/*` imports** — absolutos desde raíz dashboard
3. **shadcn/ui components** — Input, Textarea, Select, Switch, Button, Label, Card, Skeleton (sin inventar nuevos estilos)
4. **`useCurrentOrg()`** — obtener `orgId`
5. **`createClient()`** — Supabase browser client para guardar en `agent_catalog`
6. **`@tanstack/react-query`** — `useQuery` para cargar tools desde API
7. **`api.get()`** — patrón `lib/api.ts` para llamadas al backend
8. **`LoadingSpinner`** / **`Skeleton`** — estados de carga
9. **Tailwind `space-y-4`**, `grid`, `gap-4` — espaciado consistente

### Imports exactos necesarios

```typescript
// AgentForm.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'

// page.tsx
import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { createClient } from '@/lib/supabase'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'

// BuilderCanvas.tsx
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

// BuilderLayout.tsx
import { cn } from '@/lib/utils'
```

### Modularidad

- `AgentForm` encapsula toda la lógica de formulario → reusable en Paso 05 (Template Picker auto-relleno)
- `BuilderCanvas` es placeholder → se reemplaza con versión real en Paso 07 sin romper layout
- `BuilderLayout` es composición pura (render props) → permite cambiar paneles sin tocar page.tsx
- `page.tsx` es orchestrator liviano → delega a componentes

### Calidad

- Complejidad ciclomática baja: formulario = 1 schema + 1 handler submit + JSX
- Sin duplicación: reutiliza shadcn/ui + hooks existentes
- Validación centralizada en Zod schema (single source of truth)
- Tipos TypeScript estrictos (`strict: true` en tsconfig)

---

## 3️⃣ Análisis de Backend

### Endpoints consumidos

| Endpoint | Método | Uso en Paso 04 | Estado |
|---|---|---|---|
| `GET /api/tools/available` | GET | Cargar lista de tools para multi-select | ✅ Existe (tools.py:46) |

### Endpoints NO requeridos en Paso 04

- El plan dice "Botón Save Agent → guarda en agent_catalog vía Supabase (directo desde frontend, sin nuevo endpoint)".
- **CORRECTO:** No se crea endpoint nuevo. Frontend usa Supabase client directo.
- RLS maneja autorización automáticamente (POLICY `agent_catalog_tenant_isolation`).

### Flujo de datos

```
[AgentForm]
  │
  ├─ carga tools: GET /api/tools/available ──► FastAPI ──► ToolRegistry + MCPPool
  │
  └─ guardar agente: supabase.from('agent_catalog').upsert({
       org_id, role, soul_json, allowed_tools, max_iter
     })
       │
       └─► Supabase ──► RLS check ──► INSERT/UPDATE agent_catalog
```

### Auth / AuthZ

- Frontend autenticado vía `@supabase/ssr` (cookie-based session).
- RLS en `agent_catalog` garantiza que el usuario solo escribe en su `org_id`.
- No se requiere header `X-Org-ID` aquí porque el Supabase client ya tiene la sesión JWT.

### Contratos

- `GET /api/tools/available` → `ToolsListResponse { tools: ToolInfo[], count: number }`
  - `ToolInfo { name, description, category, source: "local"|"mcp" }`
  - Frontend necesita mapear `ToolInfo[]` a opciones de multi-select (name como value, description como label).

### Error handling

| Escenario | Respuesta esperada |
|---|---|
| `GET /api/tools/available` falla (backend down) | Mostrar error toast + tools vacío. El usuario puede guardar sin tools. |
| Supabase upsert falla (red) | Mostrar error toast "Failed to save agent" |
| Duplicate `(org_id, role)` | `.upsert()` maneja automáticamente → actualiza existente |
| `soul_json` malformado | Zod validation rechaza en frontend antes de enviar |

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo completo end-to-end

```
1. User navega a /builder
2. BuilderLayout renderiza: canvas izquierdo (vacío) + formulario derecho
3. AgentForm carga tools vía useQuery(GET /api/tools/available)
4. User completa: role, goal, backstory, provider, model, tools, max_iter, toggles
5. Zod valida al submit: role/goal/backstory requeridos
6. Zod rechaza → muestra errores inline
7. Zod ok → construye soul_json + payload
8. Supabase client → upsert en agent_catalog(org_id, role, soul_json, allowed_tools, max_iter)
9. Éxito → toast "Agent saved" + limpiar formulario
10. Error → toast con mensaje de error
```

### Decisiones end-to-end

- **Guardado directo a Supabase:** Evita crear endpoint innecesario. RLS protege datos. Consistente con patrón de `agents/page.tsx`.
- **soul_json como bolsa flexible:** Campos de CrewAI que no son columnas explícitas (verbose, reasoning, llm_provider, etc.) van en `soul_json`. Esto replica exactamente cómo CrewAI define un Agent.
- **Upsert no insert:** Permite re-guardar/editar sin preocuparse por duplicados de role. El `UNIQUE(org_id, role)` funciona como clave natural para upsert.

### Coherencia con arquitectura existente

- ✅ Mismo patrón de página: `'use client'` + `useQuery` + `useCurrentOrg` (como `agents/page.tsx`)
- ✅ Mismos componentes UI: shadcn/ui (como `integrations/page.tsx`)
- ✅ Mismo cliente API: `api.get()` (como `useFlows.ts`)
- ✅ Mismo cliente Supabase: `createClient()` (como `agents/page.tsx`)
- ✅ Mismo patrón de hooks: custom hook reutilizable (como `useAgentDetail.ts`)

### Gaps detectados

| Gap | Severidad | Impacto |
|---|---|---|
| Sin Slider component → usar Input type="number" | Baja | Estético. Funcionalidad no afectada. |
| Sin multi-select component → implementar con checkboxes + badges | Media | Requiere componente custom. Tools pueden ser 20+. |
| Modelo LLM dinámico por provider → mapeo estático vs endpoint | Baja | Definir mapa estático en frontend para MVP. Post-MVP: endpoint `GET /api/llm/models`. |
| Sin endpoint para listar agentes existentes → builder no sabe si el role ya existe | Media | upsert mitiga. Para edición futura: reusar `GET /agents/by-role/{role}`. |
| `agent_catalog` no tiene columna `model` → va en soul_json | Baja | Documentado en estructura soul_json. |

### DX & Tooling

#### Herramienta Propuesta: `fap agent scaffold`

- **Qué automatiza:** Crear un agente desde CLI sin usar el builder visual. El usuario define role/goal/backstory vía flags y el comando inserta directo en `agent_catalog`. Útil para CI/CD, scripts de setup, o power users que prefieren terminal.
- **Tipo:** CLI command (Typer sub-app de `fap`)
- **Cómo se usa:**
  ```
  fap agent create --role "Code Reviewer" \
    --goal "Review pull requests for security issues" \
    --backstory "Senior security engineer with 10 years experience" \
    --tools "code_analysis,security_scan" \
    --max-iter 5 \
    --org-id "550e8400-e29b-41d4-a716-446655440000"
  ```
- **Impacto para el usuario final:** Deja de abrir dashboard + formulario para crear agentes simples. Un comando los crea.
- **Prioridad:** Tarea 0 — implementar antes que el resto del Paso 04. El builder visual usa el mismo flujo (Supabase upsert), así que validar el comando = validar que el flujo de guardado funciona.

#### Herramienta Propuesta: `fap agent validate`

- **Qué automatiza:** Validar que un agente (definido en `agent_catalog`) tiene todos los campos requeridos, tools existentes en el registry, y estructura `soul_json` correcta. Ejecutable en pre-commit hooks o CI.
- **Tipo:** CLI validator
- **Cómo se usa:**
  ```
  fap agent validate --role "Code Reviewer" --org-id "<uuid>"
  fap agent validate --all --org-id "<uuid>"
  ```
- **Impacto para el usuario final:** Detecta agentes inválidos ANTES de ejecutarlos, evitando errores en runtime.
- **Prioridad:** Post-MVP (se implementa en Paso 06 o 10).

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla agent_catalog recibe INSERT con org_id, role, soul_json, allowed_tools, max_iter
✅ [DATA] soul_json contiene goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory
✅ [DATA] allowed_tools es TEXT[] con nombres de tools del registry
✅ [DATA] max_iter es INTEGER 1-10 con default 3
✅ [CODE] AgentForm usa react-hook-form + zodResolver + zod schema
✅ [CODE] Zod rechaza submit sin role, goal, o backstory con mensaje de error inline
✅ [CODE] AgentForm carga tools desde GET /api/tools/available vía useQuery
✅ [CODE] Todos los componentes tienen 'use client' directive
✅ [CODE] Imports usan path alias @/* (consistente con tsconfig)
✅ [CODE] BuilderCanvas es placeholder vacío (sin ReactFlow aún)
✅ [CODE] BuilderLayout usa grid 60/40 responsive
✅ [BACKEND] GET /api/tools/available responde con ToolInfo[] (ya existe)
✅ [BACKEND] Supabase RLS permite INSERT en agent_catalog para usuario autenticado con org_id correcto
✅ [FULLSTACK] Usuario navega a /builder, ve formulario con todos los campos
✅ [FULLSTACK] Usuario completa role/goal/backstory, selecciona tools, ajusta max_iter
✅ [FULLSTACK] Usuario hace clic en "Save Agent" → agente persiste en agent_catalog
✅ [FULLSTACK] Usuario hace clic en "Clear" → formulario se resetea
✅ [FULLSTACK] Errores de red o validación se muestran como toast (sonner)
✅ [DX] Herramienta fap agent create ejecuta sin errores y guarda agente en Supabase
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `reactflow` incompatible con Next.js SSR | Alta | ReactFlow usa `window`/`document`. Next.js App Router ejecuta componentes en servidor por defecto. | `'use client'` + dynamic import con `ssr: false` en `BuilderCanvas` cuando se use ReactFlow real (Paso 07). En Paso 04 es solo placeholder → sin riesgo. |
| `zod` no instalado → build rompe | Alta | `npm install zod` no ejecutado | Tarea 0 verifica instalación. Si falta, el import falla en compile time. |
| `UNIQUE(org_id, role)` causa error 409 si se usa `.insert()` | Media | `.insert()` lanza error en duplicado | Usar `.upsert()` con `onConflict: 'org_id,role'`. Documentado en Tarea 3. |
| Tools multi-select UX pobre con 20+ tools | Media | Sin componente multi-select, usar checkboxes en scroll puede ser incómodo | Implementar búsqueda + filtro por categoría en el multi-select. Agrupar por source (local/mcp). |
| Mapa de LLM models desactualizado | Baja | Hardcodeado en frontend. Providers cambian modelos frecuentemente | Definir mapa estático inicial con ≥3 modelos por provider. Post-MVP: endpoint en backend. |
| `soul_json` sin validación de estructura en DB | Media | JSONB acepta cualquier JSON válido. Si el frontend manda estructura incorrecta, DB la acepta. | Zod schema valida estructura en frontend. `fap agent validate` post-MVP para CI. |
| Builder sin indicador visual de agente creado | Baja | "Save Agent" guarda pero no hay feedback en canvas (vacío) | Toast de éxito es suficiente para MVP. Paso 07 añade nodo visual. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap agent create` | `src/cli/commands/agent_create.py` | `def agent_create(role: str, goal: str, backstory: str, tools: list[str], max_iter: int, org_id: str, verbose: bool, reasoning: bool, inject_date: bool, memory: bool, llm_provider: str, llm_model: str) -> None` | `src/cli/commands/templates_seed.py` | DX | Media | 1h | Ninguna | → verificar: `uv run python -m src.cli.main agent create --help` ejecuta sin errores + `--dry-run` muestra SQL sin insertar |
| 1 | Instalar dependencias | `dashboard/package.json` | `npm install reactflow zod @radix-ui/react-slider` | — | SETUP | Baja | 0.2h | Ninguna | → verificar: `npm list reactflow zod` muestra versiones instaladas |
| 2 | Crear `dashboard/components/builder/BuilderLayout.tsx` | `components/builder/BuilderLayout.tsx` | `function BuilderLayout({ canvas, form }: { canvas: React.ReactNode; form: React.ReactNode }): JSX.Element` | `dashboard/app/(app)/layout.tsx` — grid layout + responsive | CODE | Baja | 0.5h | Tarea 1 | → verificar: importable desde `@/components/builder/BuilderLayout` sin error TS |
| 3 | Crear `dashboard/components/builder/BuilderCanvas.tsx` | `components/builder/BuilderCanvas.tsx` | `function BuilderCanvas({ className }: { className?: string }): JSX.Element` | `dashboard/components/shared/EmptyState.tsx` | CODE | Baja | 0.3h | Tarea 1 | → verificar: renderiza div con placeholder y texto "Canvas — drag agents here (Paso 07)" |
| 4 | Crear `dashboard/components/builder/AgentForm.tsx` | `components/builder/AgentForm.tsx` | `function AgentForm({ onSave, initialValues }: AgentFormProps): JSX.Element` — ver §2 firma completa | `dashboard/components/flows/RunFlowDialog.tsx` (form pattern) + `dashboard/app/(app)/agents/page.tsx` (useQuery pattern) | CODE | Alta | 2h | Tarea 1, Tarea 0 | → verificar: todos los campos renderizan, Zod rechaza submit sin role/goal/backstory, tools cargan desde API |
| 5 | Crear `dashboard/app/(app)/builder/page.tsx` | `app/(app)/builder/page.tsx` | `export default function BuilderPage(): JSX.Element` | `dashboard/app/(app)/agents/page.tsx` | FULLSTACK | Media | 1h | Tareas 2-4 | → verificar: ruta `/builder` accesible, layout 60/40 visible, Save Agent persiste en Supabase |
| 6 | Añadir enlace "Builder" en sidebar | `dashboard/components/nav-main.tsx` | Añadir `{ title: 'Builder', url: '/builder', icon: Wand2 }` a `defaultNavItems` | `nav-main.tsx:43-63` — array `defaultNavItems` | FULLSTACK | Baja | 0.2h | Tarea 5 | → verificar: sidebar muestra "Builder" con ícono, navega a `/builder` |
| 7 | Registrar `fap agent` en CLI | `src/cli/main.py` | `app.add_typer(agent_app, name="agent")` | `src/cli/main.py:33,58` — `templates_app` registro | DX | Baja | 0.2h | Tarea 0 | → verificar: `uv run python -m src.cli.main agent --help` muestra subcomandos |
| 8 | Validar flujo end-to-end | — | Crear agente vía CLI → ver en DB → abrir builder → editar → guardar → ver update en DB | — | FULLSTACK | Media | 0.5h | Tareas 0-7 | → verificar: criterios §5 [FULLSTACK] pasan todos. Agente creado por CLI se lista en /agents. Agente creado en builder se ve en /agents. |

**Tiempo total estimado:** 5.9 horas

---

## 🔮 Roadmap

- **Slider real para max_iter:** Reemplazar `Input type="number"` con `@radix-ui/react-slider` + `components/ui/slider.tsx`. Post-MVP, 0.3h.
- **Endpoint `GET /api/llm/models`:** Listar modelos disponibles por provider. Reemplaza mapa estático. Requiere integración con APIs de Groq/OpenAI/Anthropic/OpenRouter. Post-MVP, 2h.
- **Multi-select component reutilizable:** `components/shared/MultiSelect.tsx` con búsqueda, filtro, badges removibles. Usable en AgentForm + futuros filtros. Post-MVP, 1h.
- **Edición de agentes desde builder:** Cargar agente existente en formulario. Requiere endpoint `GET /agents/by-role/{role}` (ya existe en agents.py:31-51). Solo falta UI para buscarlo. Post Paso 05, 0.5h.
- **Auto-guardado:** Guardar borrador en localStorage mientras el usuario completa el formulario. Evita pérdida de datos. Post-MVP, 0.5h.
- **Validación pre-save de tools:** Verificar que las tools seleccionadas existen en registry antes de guardar. `fap agent validate` (Tarea 0 extendida). Post-MVP, 0.5h.

---

> **Métrica de calidad:** 29 elementos verificados (§0) ✅ | 5 discrepancias detectadas ✅ | 8 secciones completadas ✅ | 4 etapas cubiertas ✅ | 19 criterios de aceptación ✅ | 7 riesgos identificados ✅ | 8 tareas atómicas (1 artefacto/tarea) ✅ | Interfaz exacta + patrón referencia + verificación inline por tarea ✅ | ≥1 herramienta DX propuesta ✅ | Estimación por tarea + total ✅
