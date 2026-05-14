# 🧠 Análisis Técnico — Paso 04: Builder Visual — Layout y Formulario de Agente

> **Agente:** glm  
> **Paso:** 04 — Página del builder — layout y formulario de agente  
> **Fecha:** 2026-05-14  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | `reactflow` en `package.json` | NO existe — requiere `npm install reactflow` | ❌ DISCREPANCIA | `dashboard/package.json` — no hay dependencia `reactflow` |
| 2 | Directorio `dashboard/app/(app)/builder/` | NO existe — crear | ⚠️ NO VERIFICABLE | No hay builder directory en `dashboard/app/(app)/` |
| 3 | Directorio `dashboard/components/builder/` | NO existe — crear | ⚠️ NO VERIFICABLE | No hay builder directory en `dashboard/components/` |
| 4 | `agent_catalog` tabla existe | ✅ VERIFICADO | `supabase/migrations/004_agent_catalog.sql:6-17` |
| 5 | Columnas `agent_catalog`: `id, org_id, role, is_active, soul_json, allowed_tools, max_iter, created_at, updated_at` | ✅ VERIFICADO | `004_agent_catalog.sql:6-17` |
| 6 | Columna `model` en `agent_catalog` | ❌ DISCREPANCIA — NO existe en migración, PERO `Agent` type en frontend la tiene como `model?: string` | `dashboard/lib/types.ts:96` tiene `model?: string` pero migración no tiene columna `model` | 
| 7 | RLS `agent_catalog_tenant_isolation` | ✅ VERIFICADO | `025_agent_catalog_rls_update.sql:11-14` — usa `auth.role() = 'service_role' OR org_id::text = current_org_id()` |
| 8 | Endpoint `GET /api/tools/available` | ✅ VERIFICADO | `src/api/routes/tools.py:46-63` |
| 9 | Endpoint `GET /api/templates` | ✅ VERIFICADO | `src/api/routes/templates.py:54-67` |
| 10 | Hook `useCurrentOrg` | ✅ VERIFICADO | `dashboard/hooks/useCurrentOrg.ts:1-7` |
| 11 | Hook `useAuth` | ✅ VERIFICADO | `dashboard/hooks/useAuth.ts:1-44` |
| 12 | `fapFetch` / `api` helper | ✅ VERIFICADO | `dashboard/lib/api.ts:5-77` |
| 13 | `createClient` (Supabase browser) | ✅ VERIFICADO | `dashboard/lib/supabase.ts:5-9` |
| 14 | `react-hook-form` en `package.json` | ✅ VERIFICADO | `dashboard/package.json:40` — `react-hook-form: ^7.72.1` |
| 15 | `@hookform/resolvers` en `package.json` | ✅ VERIFICADO | `dashboard/package.json:13` — `@hookform/resolvers: ^5.2.2` |
| 16 | Zod como dependencia | ❌ DISCREPANCIA — NO existe en `package.json` | Plan dice "Validación con Zod" pero `zod` no está instalado en frontend |
| 17 | Componente UI `Slider` | ❌ NO EXISTE — plan pide "slider 1-10" | `dashboard/components/ui/` no tiene `slider.tsx` |
| 18 | Componente UI `Select` | ✅ VERIFICADO | `dashboard/components/ui/select.tsx` |
| 19 | Componente UI `Switch` | ✅ VERIFICADO | `dashboard/components/ui/switch.tsx` |
| 20 | Componente UI `Input` | ✅ VERIFICADO | `dashboard/components/ui/input.tsx` |
| 21 | Componente UI `Textarea` | ✅ VERIFICADO | `dashboard/components/ui/textarea.tsx` |
| 22 | Componente UI `Label` | ✅ VERIFICADO | `dashboard/components/ui/label.tsx` |
| 23 | Componente UI `Badge` | ✅ VERIFICADO | `dashboard/components/ui/badge.tsx` |
| 24 | Componente UI `Card` | ✅ VERIFICADO | `dashboard/components/ui/card.tsx` |
| 25 | Componente UI `Dialog` | ✅ VERIFICADO | `dashboard/components/ui/dialog.tsx` |
| 26 | Componente UI `Skeleton` | ✅ VERIFICADO | `dashboard/components/ui/skeleton.tsx` |
| 27 | Nav sidebar — `AppSidebar` | ✅ VERIFICADO | `dashboard/components/app-sidebar.tsx:1-72` |
| 28 | Nav items — `defaultNavItems` | ✅ VERIFICADO — NO tiene entrada "Builder" | `dashboard/components/nav-main.tsx:43-63` |
| 29 | `useForm` pattern existente | ✅ VERIFICADO | `dashboard/components/flows/RunFlowDialog.tsx:31` — useForm sin zodResolver |
| 30 | Patrol pattern `RunFlowDialog` como referencia de formularios | ✅ VERIFICADO | `RunFlowDialog.tsx` — usa react-hook-form + shadcn/ui Select/Input |
| 31 | `Agent` type en frontend | ✅ VERIFICADO | `dashboard/lib/types.ts:87-102` |
| 32 | `ToolMetadata` frontend map | ✅ VERIFICADO | `dashboard/lib/tool-registry-metadata.ts:25-103` — es mapa estático, NO usa endpoint real |
| 33 | `(app)` layout con sidebar | ✅ VERIFICADO | `dashboard/app/(app)/layout.tsx:1-31` — AppSidebar + SiteHeader |
| 34 | `next.config.js` vacío — sin transpilePackages/webpack config para reactflow | ⚠️ NO VERIFICABLE | `next.config.js` está vacío, reactflow puede requerir config SSR |
| 35 | `UNIQUE(org_id, role)` constraint en `agent_catalog` | ✅ VERIFICADO | `004_agent_catalog.sql:17` — UNIQUE constraint |
| 36 | `ToolInfo` backend model | ✅ VERIFICADO | `src/api/routes/tools.py:25-36` — name, description, category, source, parameters, requires_approval, timeout_seconds, is_active |
| 37 | `TemplateInfo` backend model | ✅ VERIFICADO | `src/api/routes/templates.py:25-33` — id, name, description, category, suggested_tools, max_iter, is_system |

**Discrepancias encontradas:**

| ID | Discrepancia | Resolución |
|----|-------------|------------|
| D1 | `reactflow` NO instalado → `npm install reactflow` + verificar SSR config | Instalar dependencia + agregar dynamic import `"use client"` / `next/dynamic` con `ssr: false` (plan menciona Paso 09) |
| D2 | `zod` NO instalado en frontend → plan requiere "validación con Zod" | Instalar `zod` + usar `@hookform/resolvers/zod` (ya existe resolvers pkg) |
| D3 | Componente `Slider` NO existe en UI library → plan requiere "slider 1-10" | Crear `dashboard/components/ui/slider.tsx` usando `@radix-ui/react-slider` o usar shadcn/ui add |
| D4 | Columna `model` en `Agent` type frontend pero NO en migración `agent_catalog` | `model` es campo enriquecido del backend o campo agregado posterior, NO está en schema DB. El plan dice "LLM Model (select dinámico según provider)" — guardarlo dentro de `soul_json` o crear migración ad-hoc. **Decisión: guardar como campo dentro de `soul_json`** para evitar migración en paso frontend-puro |
| D5 | Nav sidebar NO tiene "Builder" → agregar entrada al Paso 09, pero Paso 04 necesita ruta accesible | Agregar en Paso 04 temporalmente o documentar como dependencia de Paso 09 |
| D6 | `tool-registry-metadata.ts` es mapa estático, NO consume endpoint real → plan dice "Select de tools carga desde endpoint real" | AgentForm debe usar `GET /api/tools/available` vía `fapFetch`, NO el mapa estático |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema afectado

- **Tabla `agent_catalog`** — escritura directa desde frontend vía Supabase client
  - Columnas relevantes: `id (UUID DEFAULT)`, `org_id (UUID NOT NULL)`, `role (TEXT NOT NULL)`, `is_active (BOOLEAN DEFAULT TRUE)`, `soul_json (JSONB NOT NULL DEFAULT '{}')`, `allowed_tools (TEXT[] DEFAULT '{}')`, `max_iter (INTEGER DEFAULT 5)`, `created_at (TIMESTAMPTZ)`, `updated_at (TIMESTAMPTZ)`
  - Constraint: `UNIQUE(org_id, role)` → no se puede crear agente con mismo `role` en misma org
  - RLS: `agent_catalog_tenant_isolation` → `auth.role() = 'service_role' OR org_id::text = current_org_id()`

### Cambios de schema necesarios

- **NINGUNO en este paso.** El plan dice "guarda en `agent_catalog` vía Supabase (directo desde frontend, sin nuevo endpoint)". Las columnas existentes son suficientes si `model`, `verbose`, `reasoning`, `inject_date`, `memory` se almacenan dentro de `soul_json`.

### Mapeo de campos del formulario → columnas DB

| Campo formulario | Columna DB | Tipo DB | Notas |
|---|---|---|---|
| Role | `role` | `TEXT NOT NULL` | UNIQUE constraint por org |
| Goal | `soul_json.goal` | `JSONB` → campo interno | Dentro de `soul_json` |
| Backstory | `soul_json.backstory` | `JSONB` → campo interno | Dentro de `soul_json` |
| LLM Provider | `soul_json.llm.provider` | `JSONB` → campo interno | Nuevo campo en soul |
| LLM Model | `soul_json.llm.model` | `JSONB` → campo interno | Nuevo campo en soul |
| Tools | `allowed_tools` | `TEXT[]` | Array directo |
| Max Iterations | `max_iter` | `INTEGER DEFAULT 5` | Columna directa |
| Verbose | `soul_json.verbose` | `JSONB` → campo interno | Boolean toggle |
| Reasoning | `soul_json.reasoning` | `JSONB` → campo interno | Boolean toggle |
| Inject Date | `soul_json.inject_date` | `JSONB` → campo interno | Boolean toggle |
| Memory | `soul_json.memory` | `JSONB` → campo interno | Boolean toggle |
| org_id | `org_id` | `UUID NOT NULL` | De `useCurrentOrg()` |

### RLS implications

- Frontend usa `createClient()` con Supabase browser → auto-inyecta auth token
- `org_id` se setea desde `useCurrentOrg().orgId`
- RLS `current_org_id()` necesita que `app.org_id` esté en session — **frontend insert directo puede fallar si RLS no está configurada para browser client**. Verificar si Supabase browser client puede escribir en `agent_catalog` o si necesita service_role

**⚠️ RIESGO:** El plan dice "guarda en `agent_catalog` vía Supabase (directo desde frontend, sin nuevo endpoint)". Pero la RLS usa `current_org_id()` que es una función SQL seteada por middleware backend. Frontend browser client NO tiene `app.org_id` en sesión. **Solución:** Usar Supabase RLS con `auth.uid()` más `org_members` join, O usar el endpoint backend existente para escribir.

**Resolución propuesta:** Verificar la política RLS exacta. Si `current_org_id()` no funciona desde browser client, crear endpoint `POST /api/agents` en paso futuro o usar upsert directo verificando que RLS funcione con auth.uid() + org_members.

### Índices

- Existe: `idx_agent_catalog_org_role ON agent_catalog(org_id, role) WHERE is_active = TRUE`

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos

#### 1. `dashboard/app/(app)/builder/page.tsx`

- **Función:** Page entry del builder. Renderiza `BuilderLayout`.
- **Firma:** `export default function BuilderPage()`
- **Patrón:** Igual que `agents/page.tsx` — `'use client'` + useQuery + `useCurrentOrg`
- **Imports:** `import { BuilderLayout } from '@/components/builder/BuilderLayout'`

#### 2. `dashboard/components/builder/BuilderLayout.tsx`

- **Función:** Layout split — 60% canvas izquierda, 40% formulario derecha
- **Firma:** `export function BuilderLayout()`
- **Patrón:** Componente `'use client'` con `div` flex. Referencia: `RunFlowDialog.tsx` para patrón de layout con formularios
- **Imports:** `import { AgentForm } from './AgentForm'`, `import { BuilderCanvas } from './BuilderCanvas'`

#### 3. `dashboard/components/builder/AgentForm.tsx`

- **Función:** Formulario completo de agente con validación Zod + react-hook-form
- **Firma:** `export function AgentForm({ onSave, onClear }: AgentFormProps)`
- **Props:** `onSave?: (agent: AgentFormData) => void`, `onClear?: () => void`
- **Estado:** `useForm<AgentFormData>` con zodResolver
- **Patrón de referencia:** `RunFlowDialog.tsx` — useForm + shadcn/ui Select/Input
- **Campos:**
  - Role: `Input` — requerido
  - Goal: `Textarea` — requerido
  - Backstory: `Textarea` — requerido
  - LLM Provider: `Select` con opciones ["groq", "openai", "anthropic", "openrouter"]
  - LLM Model: `Select` dinámico según provider (arrays estáticos por provider)
  - Tools: Multi-select desde `GET /api/tools/available` — usar `api.get('/api/tools/available')`
  - Max Iterations: Slider nativo o Input type="number" 1-10
  - Toggles: Switch — Verbose, Reasoning, Inject Date, Memory
- **Validación Zod:**
  ```typescript
  const agentFormSchema = z.object({
    role: z.string().min(1, 'Role es requerido'),
    goal: z.string().min(1, 'Goal es requerido'),
    backstory: z.string().min(1, 'Backstory es requerido'),
    llmProvider: z.enum(['groq', 'openai', 'anthropic', 'openrouter']).default('groq'),
    llmModel: z.string().default(''),
    allowedTools: z.array(z.string()).default([]),
    maxIter: z.number().min(1).max(10).default(3),
    verbose: z.boolean().default(false),
    reasoning: z.boolean().default(false),
    injectDate: z.boolean().default(false),
    memory: z.boolean().default(false),
  })
  ```
- **Guardado:** `supabase.from('agent_catalog').insert({...})` directo

#### 4. `dashboard/components/builder/BuilderCanvas.tsx`

- **Función:** Contenedor ReactFlow vacío inicialmente — se poblará en Paso 07
- **Firma:** `export function BuilderCanvas()`
- **Contenido:** ReactFlow con nodo placeholder o texto "Arrastra agentes aquí"
- **Importante:** ReactFlow requiere `ssr: false` — usar `next/dynamic`
- **Imports:** `import ReactFlow from 'reactflow'` + `import 'reactflow/dist/style.css'`

### Patrones existentes a seguir

| Patrón | Archivo referencia | Uso en Paso 4 |
|--------|-------------------|---------------|
| Page con useQuery + useCurrentOrg | `agents/page.tsx:14-29` | BuilderPage |
| useForm sin zodResolver | `RunFlowDialog.tsx:31` | AgentForm CON zodResolver |
| fapFetch para API calls | `lib/api.ts:54-77` | Cargar tools desde endpoint |
| Supabase browser client | `lib/supabase.ts:5-9` | Guardar agente directamente |
| OrganizationProvider/useCurrentOrg | `providers/organization-provider.tsx` | Obtener orgId |
| UI Components (Card, Input, etc.) | `components/ui/*` | Formulario agente |

### Dependencias nuevas (npm)

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `reactflow` | latest | Canvas visual de nodos |
| `zod` | latest | Validación formulario |
| `@radix-ui/react-slider` | latest | Slider para Max Iterations (alternativa: shadcn add) |

### Modularidad

- `AgentForm` independiente — recibe `onSave` callback → testable
- `BuilderCanvas` independiente — placeholder, se reemplaza en Paso 07
- `BuilderLayout` compone ambos → split responsivo
- `page.tsx` solo orquesta layout → limpio

### Imports exactos

```
dashboard/app/(app)/builder/page.tsx:
  → import { BuilderLayout } from '@/components/builder/BuilderLayout'

dashboard/components/builder/BuilderLayout.tsx:
  → import { AgentForm } from './AgentForm'
  → import { BuilderCanvas } from './BuilderCanvas'

dashboard/components/builder/AgentForm.tsx:
  → import { useForm } from 'react-hook-form'
  → import { zodResolver } from '@hookform/resolvers/zod'
  → import { z } from 'zod'
  → import { useQuery } from '@tanstack/react-query'
  → import { createClient } from '@/lib/supabase'
  → import { api } from '@/lib/api'
  → import { useCurrentOrg } from '@/hooks/useCurrentOrg'
  → import { Button } from '@/components/ui/button'
  → import { Input } from '@/components/ui/input'
  → import { Textarea } from '@/components/ui/textarea'
  → import { Label } from '@/components/ui/label'
  → import { Switch } from '@/components/ui/switch'
  → import { Select, ... } from '@/components/ui/select'
  → import { Card, ... } from '@/components/ui/card'

dashboard/components/builder/BuilderCanvas.tsx:
  → import dynamic from 'next/dynamic' (para ssr: false)
  → import ReactFlow from 'reactflow'
  → import 'reactflow/dist/style.css'
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes consumidos

| Endpoint | Método | Auth | Uso en Paso 4 |
|----------|--------|------|---------------|
| `/api/tools/available` | GET | `require_org_id` (header X-Org-ID) | Cargar lista de tools para multi-select |
| `/api/templates` | GET | None (público) | Opcional — cargar templates para auto-fill del formulario |
| Agentes backend `GET /agents/{role}` | GET | `require_org_id` | Ya existe pero no se usa en este paso |

### Flujo de datos: Guardar agente

```
Frontend (AgentForm)
  → useForm.handleSubmit()
  → mapear AgentFormData → Supabase insert format
  → const supabase = createClient()
  → supabase.from('agent_catalog').insert({
      org_id: orgId,
      role: data.role,
      soul_json: {
        goal: data.goal,
        backstory: data.backstory,
        llm: { provider: data.llmProvider, model: data.llmModel },
        verbose: data.verbose,
        reasoning: data.reasoning,
        inject_date: data.injectDate,
        memory: data.memory,
      },
      allowed_tools: data.allowedTools,
      max_iter: data.maxIter,
    })
  → success: reset form + notify user
  → error: mostrar error (conflicto UNIQUE = role duplicado)
```

### Middleware / Auth

- Frontend → Supabase directo: usa `createBrowserClient()` con `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- RLS `agent_catalog_tenant_isolation` requiere `current_org_id()` → **investigar si esta función funciona con browser client**
- Alternativa: Frontend → `fapFetch('/api/agents')` → backend endpoint → Supabase service_role (SI existiera endpoint POST)
- **Decisión CRÍTICA:** Verificar si `current_org_id()` está definida como SQL function en Postgres o si es seteada solo por middleware backend

**⚠️ PROBLEMA IDENTIFICADO:** La función `current_org_id()` usada en RLS (`025_agent_catalog_rls_update.sql:14`) es probablemente `current_setting('app.org_id', TRUE)` adaptado. Si el frontend browser client no puede setear esta variable de sesión, los inserts directos fallarán con error RLS. La solución original del plan dice "directo desde frontend" → verificar o crear endpoint intermedio.

### Error handling

| Error | Código | Tratamiento |
|-------|--------|-------------|
| UNIQUE violation (role duplicado) | 409 / 23505 | Toast "Ya existe un agente con ese rol" |
| RLS policy violation | 403 / 42501 | Toast "Sin permisos para crear agentes en esta org" |
| Tools endpoint timeout | 500 / timeout | Degradado: mostrar lista vacía + botón "Reintentar" |
| Campo requerido vacío | Validación Zod | Inline error en campo |
| Org no seleccionada | — | Deshabilitar formulario hasta orgId disponible |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: DB → Backend → Frontend → UX

```
[Railway/Supabase DB] agent_catalog
        ↕ RLS
[Frontend Browser] Supabase JS Client
        ↓ Insert directo
[AgentForm] → [BuilderLayout] → [BuilderPage]
        ↑ Read tools
[GET /api/tools/available] → [FastAPI Backend]
```

### Coherencia end-to-end

1. **Alta coherencia:** Los campos del formulario mapean 1:1 a columnas de `agent_catalog` (role, allowed_tools, max_iter) o dentro de `soul_json` (goal, backstory, llm, toggles). Sin campos huérfanos.
2. **Gap:** Los toggles (verbose, reasoning, inject_date, memory) NO existen como columnas en DB → almacenados en `soul_json` que es JSONB. Es consistente con cómo `goal` y `backstory` ya se almacenan.
3. **Gap:** `model` como select → NO existe columna `model` en tabla → almacenar en `soul_json.llm.model`. Consistente con patrón existente.
4. **Gap:** LLM provider/model selection → datos estáticos en frontend (arrays por provider). Post-MVP: podría venir de config endpoint.

### Alineación con plan

- Plan dice "sin nuevo endpoint" → puede ser problemático por RLS (ver §3)
- Plan dice "Select de tools carga desde endpoint real" → correcto, usar `GET /api/tools/available`
- Plan dice "Guardar en agent_catalog vía Supabase directo" → verificar RLS

### Gaps y fricción

| Gap | Severidad | Resolución |
|-----|-----------|------------|
| RLS puede bloquear insert directo desde frontend | Alta | Probar insert directo con Supabase browser client. Si falla, crear endpoint POST |
| `reactflow` no en package.json | Alta | `npm install reactflow` obligatorio |
| `zod` no en package.json | Media | `npm install zod` obligatorio |
| Slider UI component no existe | Baja | Crear con @radix-ui/react-slider o usar Input number |
| Nav sidebar sin "Builder" | Baja | Agregar en Paso 04 temporalmente o documentar como Paso 09 |
| LLM models lista hardcodeada | Baja | Aceptable para MVP |

### Herramienta DX Propuesta:

```
### Herramienta Propuesta: Builder Seed Script
- **Qué automatiza:** Crear agente de prueba desde CLI sin abrir dashboard. Permite validar formulario + guardado Supabase sin UI manual.
- **Tipo:** script
- **Cómo se usa:** `uv run python scripts/seed_builder_agent.py --org-id <UUID> --role "Test Agent" --goal "Test" --backstory "Test agent for builder validation"`
- **Impacto para el usuario final:** Elimina prueba manual de "crear agente → verificar en DB → borrar → repetir". Un comando crea agente de prueba, otro lo limpia.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Columnas de agent_catalog cubren todos los campos del formulario (role, soul_json, allowed_tools, max_iter)
✅ [DATA] RLS permite insert desde browser client authenticated (verificar manualmente)
✅ [DATA] UNIQUE constraint en (org_id, role) produce error manejable en UI
✅ [CODE] reactflow instalado y BuilderCanvas renderiza sin errores SSR
✅ [CODE] zod instalado y AgentForm valida role/goal/backstory como requeridos
✅ [CODE] AgentForm usa useForm + zodResolver pattern consistente con RunFlowDialog
✅ [CODE] BuilderLayout muestra split 60/40 responsivo
✅ [CODE] Multi-select de tools carga desde GET /api/tools/available (endpoint real)
✅ [CODE] LLM Provider select cambia dinámicamente modelos disponibles
✅ [BACKEND] No se crean nuevos endpoints en este paso
✅ [BACKEND] GET /api/tools/available responde con X-Org-ID header desde fapFetch
✅ [FULLSTACK] Ruta / builder accesible y renderiza layout + formulario
✅ [FULLSTACK] Botón "Save Agent" persiste en Supabase agent_catalog
✅ [FULLSTACK] Botón "Clear" resetea formulario a valores default
✅ [FULLSTACK] Validación Zod bloquea envío sin role/goal/backstory
✅ [FULLSTACK] Toggles (Verbose, Reasoning, Inject Date, Memory) se guardan en soul_json
✅ [DX] Builder Seed Script ejecuta sin errores e inserta agente de prueba
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| RLS bloquea insert directo desde frontend | Alta | `current_org_id()` requiere `app.org_id` seteada por backend, no disponible en browser client | Probar insert directo. Si falla: crear endpoint POST /api/agents temporal o usar service_role client |
| ReactFlow SSR crash en Next.js | Alta | ReactFlow usa APIs del browser (ResizeObserver, etc.) — no SSR compatible | Usar `next/dynamic` con `ssr: false` para BuilderCanvas |
| UNIQUE constraint (org_id, role) error poco claro | Media | Error genérico de Supabase sin mensaje amigable | Catch error code 23505 y mostrar toast "Ya existe agente con ese rol" |
| zod + react-hook-form versión incompatibles | Media | @hookform/resolvers v5 con zod resolution puede fallar | Verificar compatibilidad; usar `zodResolver` import desde `@hookform/resolvers/zod` |
| Multi-select tools sin componente UI adecuado | Baja | No hay componente `MultiSelect` en shadcn/ui actual | Implementar con checkboxes o instalar `cmdk` para combobox multi-select |
| LLM models hardcodeados quedan obsoletos | Baja | Providers agregan/retiran modelos | Post-MVP: endpoint de configuración o archivo estático versionado |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|-------------|--------------|
| 0 | **DX: Builder Seed Script** | `scripts/seed_builder_agent.py` | `def main(org_id: str, role: str, goal: str, backstory: str): ...` | `scripts/seed_system_bundles.py` | DX | Media | 0.5h | Ninguna | → verificar: `uv run python scripts/seed_builder_agent.py --help` ejecuta sin errores |
| 1 | Instalar dependencias frontend | `dashboard/package.json` | Agregar: `reactflow`, `zod`, `@radix-ui/react-slider` | — | CODE | Baja | 0.25h | Ninguna | → verificar: `cd dashboard && npm ls reactflow zod` sin errores |
| 2 | Crear componente Slider UI | `dashboard/components/ui/slider.tsx` | `export const Slider: React.ForwardRefExoticComponent<SliderProps>` | shadcn/ui pattern (radix wrapper) | CODE | Baja | 0.25h | Tarea 1 | → verificar: import funciona sin error de tipos |
| 3 | Crear Zod schema para AgentForm | `dashboard/components/builder/schemas.ts` | `agentFormSchema: z.ZodObject<{role: z.string, goal: z.string, backstory: z.string, llmProvider: z.enum, llmModel: z.string, allowedTools: z.array, maxIter: z.number, verbose: z.boolean, reasoning: z.boolean, injectDate: z.boolean, memory: z.boolean}>` | Zod schema pattern | CODE | Baja | 0.5h | Tarea 1 | → verificar: `zod.parse(agentFormSchema, {role:'', goal:'', backstory:''})` retorna errores |
| 4 | Crear AgentForm con validación y guardado | `dashboard/components/builder/AgentForm.tsx` | `export function AgentForm({ onSave, className }: { onSave?: (data: AgentFormData) => void; className?: string })` | `RunFlowDialog.tsx` — useForm + Select/Input | CODE | Alta | 2h | Tareas 1,2,3 | → verificar: formulario renderiza, validación Zod bloquea submit vacío, `onSave` callback recibe datos |
| 5 | Crear BuilderCanvas placeholder | `dashboard/components/builder/BuilderCanvas.tsx` | `export function BuilderCanvas()` — renderiza ReactFlow vacío con placeholder | ReactFlow quickstart docs | CODE | Media | 1h | Tarea 1 | → verificar: componente renderiza sin SSR crash, canvas visible |
| 6 | Crear BuilderLayout split panel | `dashboard/components/builder/BuilderLayout.tsx` | `export function BuilderLayout()` — div flex con 60% canvas + 40% form | — | CODE | Baja | 0.5h | Tareas 4,5 | → verificar: layout responsivo renderiza ambos paneles |
| 7 | Crear página builder | `dashboard/app/(app)/builder/page.tsx` | `export default function BuilderPage()` — renderiza BuilderLayout | `agents/page.tsx` | BACKEND | Baja | 0.25h | Tarea 6 | → verificar: `/builder` accesible, renderiza sin errores |
| 8 | Lógica de guardado Supabase en AgentForm | Dentro de `AgentForm.tsx` | `async function saveAgent(data: AgentFormData, orgId: string): Promise<void>` — `supabase.from('agent_catalog').insert({...})` | `agents/page.tsx:19-28` — supabase insert pattern | FULLSTACK | Media | 1h | Tarea 4 | → verificar: submit formulario crea registro en `agent_catalog` con orgId correcto |
| 9 | Multi-select de tools desde endpoint | Dentro de `AgentForm.tsx` | `useQuery<ToolsListResponse>` → `api.get('/api/tools/available')` | `agents/page.tsx:17-28` — useQuery pattern | FULLSTACK | Media | 1h | Tarea 4 | → verificar: select muestra tools reales del endpoint |
| 10 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 7-9 | → verificar: criterios §5 [FULLSTACK] y [DX] pasan |

**Tiempo total estimado:** 7.25 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Paso 05:** TemplatePicker → formulario pre-llenado desde `GET /api/templates`
- **Paso 06:** AgentPlayground → chat real-time con agente
- **Paso 07:** ReactFlow canvas poblado con nodos drag-and-drop
- **Paso 09:** Navegación sidebar + breadcrumbs + error boundaries
- **Optimización:** LLM models por provider debería venir de config, no hardcodeado
- **Optimización:** Multi-select de tools debería usar Command+Popover (combobox) cuando >>10 tools
- **Endpoint POST Agent:** Si RLS no permite insert directo, crear `POST /api/agents` para abstracción
- **Migración `model` column:** Si se quiere `model` como columna separada (no en soul_json), agregar migración post-MVP