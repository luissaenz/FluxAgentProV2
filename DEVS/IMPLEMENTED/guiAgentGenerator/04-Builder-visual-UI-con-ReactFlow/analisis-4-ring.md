# 🧠 ANÁLISIS TÉCNICO — Paso 04: Builder Visual de Agentes (UI)

> **Agente:** ring  
> **Paso:** 4  
> **Fecha:** 2026-05-14  
> **Archivo de referencia:** `DEVS/plan.md` → Paso 04  
> **Estado de la fase:** `guiAgentGenerator` — Paso 4 de 10 (Pendiente)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql:6` | ✅ VERIFICADO | Columnas: `id UUID`, `org_id UUID`, `role TEXT`, `is_active BOOLEAN`, `soul_json JSONB`, `allowed_tools TEXT[]`, `max_iter INTEGER`, timestamps. RLS tenant_isolation. |
| 2 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql:10` | ✅ VERIFICADO | Sin `org_id` (global). RLS: SELECT authenticated, ALL service_role. Índice parcial `UNIQUE(name) WHERE is_system=TRUE`. |
| 3 | Endpoint `GET /api/tools/available` | `src/api/routes/tools.py:46` | ✅ VERIFICADO | Retorna `ToolsListResponse` con `ToolInfo[]`. Parámetros `?source=` y `?category=`. Auth: `require_org_id`. |
| 4 | Endpoint `GET /api/templates` | `src/api/routes/templates.py:54` | ✅ VERIFICADO | Lista templates con `?category=`. Sin auth. `TemplateListResponse` con `count`. |
| 5 | Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:70` | ✅ VERIFICADO | Retorna `TemplateDetailResponse` con `soul_json`. 404 si no existe. |
| 6 | Tipo `Agent` en frontend | `dashboard/lib/types.ts:87` | ✅ VERIFICADO | Interface con `id`, `org_id`, `role`, `is_active`, `soul_json`, `allowed_tools`, `max_iter`, `model?`. Campos extendidos: `display_name?`, `soul_narrative?`, `avatar_url?`. |
| 7 | API fetch helper | `dashboard/lib/api.ts:54` | ✅ VERIFICADO | Objeto `api` con `get`, `post`, `put`, `patch`, `delete`. Inyecta `Authorization` + `X-Org-ID`. |
| 8 | Hook `useCurrentOrg` | `dashboard/hooks/useCurrentOrg.ts:5` | ✅ VERIFICADO | Retorna `useOrganization()` → provee `orgId`. |
| 9 | Componente Sidebar | `dashboard/components/app-sidebar.tsx:28` | ✅ VERIFICADO | Array `navMain` con items de navegación. Listo para agregar "Builder". |
| 10 | Componente NavMain | `dashboard/components/nav-main.tsx:43` | ✅ VERIFICADO | Array `defaultNavItems`. Listo para agregar item Builder. |
| 11 | Componentes UI disponibles | `dashboard/components/ui/` | ✅ VERIFICADO | `input.tsx`, `textarea.tsx`, `select.tsx`, `card.tsx`, `badge.tsx`, `button.tsx`, `loading-spinner.tsx`, `empty-state.tsx`, `tabs.tsx`, `sheet.tsx`, `dialog.tsx`. |
| 12 | `reactflow` en package.json | `dashboard/package.json` | ❌ NO EXISTE | No está en `dependencies`. Se requiere `npm install reactflow`. |
| 13 | `zod` en package.json | `dashboard/package.json` | ❌ NO EXISTE | No está en `dependencies`. Se requiere para validación Zod del plan. |
| 14 | Directorio `components/builder/` | Glob: `dashboard/components/builder/**/*` | ❌ NO EXISTE | No hay ningún archivo. Debe crearse. |
| 15 | Ruta `app/(app)/builder/` | Glob: `dashboard/app/**/builder*` | ❌ NO EXISTE | No hay page.tsx ni layout. Debe crearse. |
| 16 | Endpoint para listar LLM models | `src/api/routes/` | ⚠️ NO ENCONTRADO | El plan menciona "select dinámico según provider" pero no hay endpoint de modelos LLM. |
| 17 | Archivo `src/api/routes/agents.py` | Verificado | ✅ VERIFICADO | `GET /agents/by-role/{role}`, `GET /agents/{agent_id}/detail`, `POST /agents/{role}/run`. |
| 18 | `Supabase client` directo en frontend | `dashboard/app\(app\)\agents\page.tsx:21` | ✅ VERIFICADO | Usa `createClient()` y `.from('agent_catalog')` directamente. Confirma que el plan puede guardar sin endpoint nuevo. |
| 19 | `ExportService` para bundles | `src/services/export_service.py:21` | ✅ VERIFICADO | `export(payload)` → `(bytes, filename)`. Consumido por `POST /api/bundles/export`. |
| 20 | `BundleManager.create_bundle()` | `src/services/bundle_manager.py:197` | ✅ VERIFICADO | Genera ZIP en memoria. Usa `manifest`, `agents`, `flows`, `skills`. |

### Discrepancias encontradas:

**D1: `reactflow` y `zod` no están instalados**  
- El plan menciona instalar `reactflow` y usar Zod para validación, pero ninguno está en `package.json`.  
- **Resolución:** Agregar `reactflow` y `zod` a las dependencias del dashboard en `package.json` antes de implementar.

**D2: No existe endpoint para listar modelos LLM por provider**  
- El plan describe un `<select>` dinámico de modelos según el proveedor (Groq/OpenAI/Anthropic/OpenRouter), pero no hay endpoint `GET /api/models` ni similar.  
- **Resolución:** Opción A — crear endpoint backend que consulte modelos disponibles por provider. Opción B — definir un mapa estático en frontend (`src/lib/llm-models.ts`) con modelos por provider. La Opción B es más rápida para MVP y consistente con el patrón de `tool-registry-metadata.ts` (metadata estática en frontend).

**D3: `AgentForm` guarda en Supabase directo sin endpoint nuevo**  
- El plan dice "sin nuevo endpoint", usando Supabase client directamente.  
- **Riesgo:** La tabla `agent_catalog` tiene RLS con `tenant_isolation`. El insert necesita `org_id` y usa el cliente anónimo. Debe verificarse que el insert funcione con la política RLS actual desde el cliente browser.  
- **Resolución:** Usar `supabase.from('agent_catalog').insert(...)` que ya respeta el header `X-Org-ID` para el `require_org_id` del backend, pero para INSERT directo desde el cliente, se necesita verificar que la RLS permita INSERT al tenant autenticado. La política actual es `FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE))` — esto aplica para todas las operaciones si el cliente setea la variable de sesión. El cliente Supabase JS envía el JWT que contiene el `org_id` en el claim, por lo que debería funcionar. ⚠️ Confirmar en testing.

**D4: La interfaz `Agent` en types.ts no incluye `goal` y `backstory` como campos directos**  
- Estos están dentro de `soul_json: Record<string, unknown>`. El formulario trabajará con `soul_json.goal` y `soul_json.backstory`.  
- **Resolución:** El `AgentForm` debe construir el payload combinando `role`, `soul_json: { role, goal, backstory }`, `allowed_tools`, `max_iter`, `model`, y las flags booleanas.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### 1.1 Tablas involucradas

| Tabla | Operación | Migración | Notas |
|---|---|---|---|
| `agent_catalog` | INSERT (Save Agent) | `004_agent_catalog.sql` | RLS tenant_isolation. Columnas: `id`, `org_id`, `role`, `is_active`, `soul_json`, `allowed_tools`, `max_iter`, timestamps. |
| `agent_templates` | SELECT (Template Picker) | `030_agent_templates.sql` | Tabla global. RLS: SELECT para authenticated, ALL para service_role. 8 templates pre-cargados por seed. |
| `org_mcp_servers` | SELECT indirecto (tool listing) | `005_org_mcp_servers.sql` | Se consulta vía `tools.py` para llenar el multi-select de tools. |

### 1.2 Integridad referencial

- `agent_catalog.org_id` → `organizations.id` (FK, ON DELETE CASCADE)
- `agent_catalog.allowed_tools` → array de nombres de `tool_registry` (NO es FK, se valida en runtime)
- `agent_templates` no tiene FK (tabla global sin `org_id`)

### 1.3 RLS policies

| Tabla | Política | Efecto para el Builder |
|---|---|---|
| `agent_catalog` | `tenant_isolation` — `org_id::text = current_setting('app.org_id', TRUE)` | El usuario debe estar autenticado con un JWT que contenga el `org_id`. El INSERT desde el frontend debe setear `app.org_id` vía Supabase Auth. |
| `agent_templates` | `SELECT: auth.role() = 'authenticated'`, `ALL: service_role` | Lectura pública para usuarios autenticados. Sin acceso de escritura desde el frontend. |

### 1.4 Índices relevantes

- `idx_agent_catalog_org_role` (004) — `org_id, role WHERE is_active = TRUE` → búsqueda rápida de agentes por rol.
- `idx_agent_templates_category` (030) — filtrado por categoría en el Template Picker.
- `idx_agent_templates_system_name` (030) — `UNIQUE(name) WHERE is_system = TRUE` → garantiza nombres únicos de templates del sistema.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 2.1 Componentes nuevos a crear

| Archivo | Tipo | Descripción |
|---|---|---|
| `dashboard/app/(app)/builder/page.tsx` | Página Next.js | Entrada del builder. Layout con `<BuilderLayout>`. Debe ser `use client`. |
| `dashboard/components/builder/BuilderLayout.tsx` | Componente | Split panel: 60% canvas (izquierda) / 40% formulario (derecha). Responsive. |
| `dashboard/components/builder/AgentForm.tsx` | Componente | Formulario con campos del Agent CrewAI. Validación Zod. |
| `dashboard/components/builder/BuilderCanvas.tsx` | Componente | Contenedor ReactFlow. Inicialmente vacío (se puebla en Paso 07). |

### 2.2 Firmas y APIs de componentes

**BuilderLayout**
```tsx
// Props: none
// Interno: usa useMediaQuery o CSS grid para split 60/40
// Hijos: <BuilderCanvas /> (izquierda), <AgentForm /> (derecha)
```

**AgentForm** — campos basados en el plan y el tipo `Agent` existente:
```tsx
// Form schema (Zod):
//   role: string, min 1
//   goal: string, min 10
//   backstory: string, min 10
//   llmProvider: "groq" | "openai" | "anthropic" | "openrouter"
//   llmModel: string (dinámico según provider)
//   tools: string[] (multi-select desde GET /api/tools/available)
//   maxIter: number, min 1, max 10, default 3
//   verbose: boolean
//   reasoning: boolean
//   injectDate: boolean
//   memory: boolean

// Submit handler → Supabase insert en agent_catalog
// Botones: "Save Agent", "Clear"
```

**BuilderCanvas**
```tsx
// Contenedor ReactFlow
// Props: none
// Estado: nodes [], edges [] (vacío inicialmente, se puebla en Paso 07)
// Incluye: <ReactFlow> con tipos de nodo custom
```

### 2.3 Patrones existentes a seguir

| Patrón | Archivo de referencia | Aplicación |
|---|---|---|
| Componente con shadcn/ui | `dashboard/components/agents/AgentPersonalityCard.tsx` | Uso de `<Card>`, `<Badge>`, `<Button>` |
| Data fetching con React Query | `dashboard/hooks/useAgentDetail.ts` | `useQuery` con TanStack Query |
| Formulario con react-hook-form | `dashboard/components/tickets/CreateTicketForm.tsx` | Patrón de form handling |
| API calls con api.ts | `dashboard/lib/api.ts` | `api.get()`, `api.post()` |
| Supabase directo | `dashboard/app\(app\)\agents\page.tsx` | `createClient().from('agent_catalog')` |
| Loading skeletons | `dashboard/components/shared/LoadingSpinner.tsx` | Estado de carga |
| Empty states | `dashboard/components/shared/EmptyState.tsx` | Sin resultados |

### 2.4 Dependencias del dashboard (package.json)

```
Notable:
- ✅ @tanstack/react-query — data fetching
- ✅ react-hook-form + @hookform/resolvers — forms
- ✅ @radix-ui/react-select — select component
- ✅ @radix-ui/react-dialog — dialog/sheet
- ✅ jszip — soporte ZIP (ya instalado, útil para export)
- ❌ reactflow — NO INSTALADO (requiere npm install)
- ❌ zod — NO INSTALADO (requiere npm install)
- ❌ @reactflow/... packages — NO INSTALADOS
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### 3.1 Endpoints que el frontend del Builder consume

| Método | Ruta | Archivo | Auth | Uso en el Builder |
|---|---|---|---|---|
| `GET` | `/api/tools/available?source=&category=` | `src/api/routes/tools.py:46` | `require_org_id` | Llenar multi-select de tools en `AgentForm` |
| `GET` | `/api/templates` | `src/api/routes/templates.py:54` | None (público) | Cargar templates en `TemplatePicker` |
| `GET` | `/api/templates/{id}` | `src/api/routes/templates.py:70` | None (público) | Obtener template para auto-rellenar formulario |
| `POST` | `/api/bundles/export` | `src/api/routes/bundles.py:199` | `require_org_id` | Exportar agente/crew como ZIP (Paso 08) |
| `POST` | `/flows/{flow_type}/run` | `src/api/routes/flows.py:142` | `require_org_id` | Ejecutar crew (Paso 07) |
| *(sin endpoint)* | `POST /api/agents` | *No existe* | — | **El plan indica que no se crea endpoint nuevo** — se inserta directo en Supabase |

### 3.2 Contratos de datos

**Request para `GET /api/tools/available`:**
```
Query params:
  source?: "local" | "mcp"
  category?: string
Headers:
  X-Org-ID: <org_uuid>
Response 200:
  { tools: ToolInfo[], count: number }
  ToolInfo = {
    name: string,
    description: string,
    category: string,
    categories: string[],
    source: "local" | "mcp",
    parameters: {},
    requires_approval: boolean,
    timeout_seconds: number,
    is_active: boolean
  }
```

**Request para `GET /api/templates`:**
```
Query params:
  category?: string
Response 200:
  { templates: TemplateInfo[], count: number }
  TemplateInfo = {
    id: string,
    name: string,
    description?: string,
    category: string,
    suggested_tools: string[],
    max_iter: number,
    is_system: boolean
  }
```

**Insert en `agent_catalog` (Supabase directo):**
```typescript
// Payload que genera AgentForm
{
  org_id: "<org_uuid>",           // del useCurrentOrg()
  role: "my_agent",               // del form
  is_active: true,
  soul_json: {
    role: "my_agent",
    goal: "...",
    backstory: "..."
  },
  allowed_tools: ["tool1", "tool2"],
  max_iter: 3,
  model: "groq/llama-3-70b",     // campo opcional, NO existe en la tabla actual
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
}
```

### 3.3 ⚠️ Discrepancia: El campo `model` no existe en `agent_catalog`

La tabla `agent_catalog` (migración 004) **NO tiene columna `model`**. El tipo `Agent` en el frontend (`types.ts:95`) incluye `model?: string`, pero la tabla DB no lo soporta.

- **Impacto:** Si el formulario permite seleccionar un modelo LLM y se intenta guardar en `agent_catalog`, el campo `model` será ignorado por Supabase (o causará error si se envía explícitamente).
- **Resolución:** Agregar migración `031_agent_catalog_add_model.sql` con `ALTER TABLE agent_catalog ADD COLUMN model TEXT;`, o bien omitir `model` del insert y dejarlo como campo display-only del frontend.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### 4.1 Flujo completo end-to-end

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER → Dashboard Sidebar → clicks "Builder"                       │
│                                                                     │
│  1. /dashboard/app/(app)/builder/page.tsx                          │
│     ├─ useCurrentOrg() → obtiene orgId                             │
│     ├─ BuilderLayout (split 60/40)                                  │
│     │  ├─ BuilderCanvas (ReactFlow, vacío, paso 07 lo llena)      │
│     │  └─ AgentForm                                                │
│     │     ├─ Fetches: GET /api/tools/available (llena tools select)│
│     │     ├─ Fetches: GET /api/templates (TemplatePicker, paso 05) │
│     │     └─ Validación Zod → Submit                                │
│     │        └─ Supabase .from('agent_catalog').insert(...)        │
│     └─ TemplatePicker (paso 05, botón "Templates")                 │
│           └─ GET /api/templates → cards → "Use Template"           │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Coherencia de decisiones

| Decisión | Consistente | Nota |
|---|---|---|
| Supabase client directo para guardar agente | ✅ Sí | Misma patrón que `agents/page.tsx` |
| Sin endpoint nuevo para crear agente | ✅ Sí | Plan dice "sin nuevo endpoint" |
| Filtro `?category=` en templates | ✅ Sí | Ya funciona en GET /api/templates |
| Tools desde endpoint real | ✅ Sí | GET /api/tools/available ya existe |
| ReactFlow para canvas | ✅ Sí | Elegido en el plan |

### 4.3 Gaps y fricciones

| # | Gap | Severidad | Mitigación |
|---|---|---|---|
| G1 | `reactflow` y `zod` no instalados | Media | Instalar antes de comenzar desarrollo |
| G2 | Columna `model` no existe en tabla | Media | Migración adicional o omitir del insert |
| G3 | No hay endpoint de modelos LLM | Media | Mapa estático en frontend o crear endpoint |
| G4 | TemplatePicker no existe aún (paso 05) | Baja | Dependencia temporal, Builder funciona sin él |
| G5 | BuilderCanvas vacío hasta paso 07 | Baja | Diseñado así intencionalmente |
| G6 | RLS en agent_catalog requiere `app.org_id` seteada | Alta | Verificar que Supabase JS envía la variable de sesión correctamente en INSERT. Si no, usar RPC en lugar de direct insert. |

### 4.4 DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap builder scaffold`

```
### Herramienta Propuesta: fap builder scaffold
- **Qué automatiza:** Genera automáticamente la estructura de componentes del builder
  (AgentForm, BuilderCanvas, BuilderLayout, TemplatePicker) con boilerplate
  consistente al patrón shadcn/ui + react-hook-form + TanStack Query.
- **Tipo:** CLI command (script Python)
- **Cómo se usa:**
  fap builder scaffold --component AgentForm --fields role,goal,backstory,llm-provider,tools
  fap builder scaffold --component BuilderCanvas
  fap builder scaffold --component BuilderLayout
- **Impacto para el usuario final:** Elimina ~45 min de scaffolding manual,
  garantiza consistencia de imports, tipos y patrón de estado.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

**Alternativa DX (ya existente):** La CLI `fap templates seed` (`src/cli/commands/templates_seed.py`) ya automatiza la carga de templates que alimentan el TemplatePicker del builder. Ejecutar `fap templates seed` como setup previo al desarrollo.

---

## 5️⃣ Criterios de Aceptación

Lista binaria, verificable al completar cada tarea:

```
✅ [DATA] Tabla agent_catalog tiene columnas: id, org_id, role, soul_json, allowed_tools, max_iter, is_active
✅ [DATA] Tabla agent_templates existe con RLS pública de lectura
✅ [DATA] Columna model en agent_catalog (verificar si se agrega migración 031)
✅ [CODE] AgentForm.tsx renderiza campos: role, goal, backstory, llmProvider, llmModel, tools, maxIter, toggles
✅ [CODE] AgentForm valida con Zod: role (min 1), goal (min 10), backstory (min 10)
✅ [CODE] BuilderCanvas.tsx inicializa ReactFlow con nodes=[], edges=[]
✅ [CODE] BuilderLayout.tsx renderiza split 60/40 responsive
✅ [CODE] page.tsx monta BuilderLayout con BuilderCanvas + AgentForm + TemplatePicker
✅ [BACKEND] GET /api/tools/available responde con ToolInfo[] en <500ms
✅ [BACKEND] GET /api/templates responde con templates de seed
✅ [BACKEND] GET /api/templates/{id} responde con soul_json
✅ [BACKEND] GET /api/templates NO requiere auth (catálogo público)
✅ [FULLSTACK] Ruta /builder accesible desde sidebar del dashboard
✅ [FULLSTACK] Formulario carga tools desde endpoint real (no mock)
✅ [FULLSTACK] Botón "Save Agent" persiste en agent_catalog vía Supabase
✅ [FULLSTACK] Botón "Clear" resetea formulario
✅ [FULLSTACK] Select de LLM Provider muestra opciones: Groq/OpenAI/Anthropic/OpenRouter
✅ [FULLSTACK] Select de Model se actualiza dinámicamente según Provider
✅ [DX] npm install reactflow zod ejecutado sin errores
✅ [DX] fap builder scaffold disponible como CLI (opcional)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| RLS bloquea INSERT directo desde frontend | **Alta** | `agent_catalog` usa `tenant_isolation` vía `current_setting('app.org_id')`. Si Supabase JS no setea la variable de sesión correctamente, el INSERT falla silenciosamente. | Verificar en entorno de prueba que `supabase.from('agent_catalog').insert({org_id, role, soul_json, ...})` funciona con el JWT del usuario. Si falla, migrar a RPC o usar `set_config` call. |
| Modelo LLM no persiste en DB | Media | La tabla `agent_catalog` no tiene columna `model`. Seleccionar modelo en formulario se pierde al guardar. | Agregar migración `031` con `ALTER TABLE ADD COLUMN model TEXT;` o mostrar modelo como display-only derivado de provider. |
| reactflow SSR issues | Media | ReactFlow puede fallar en SSR (window/document undefined). | Cargar canvas con `dynamic import` + `ssr: false` (misma estrategia que indica el plan para canvas). |
| Conflictos de versiones reactflow | Media | reactflow tiene peer dependencies estrictas con React. | Usar versión exacta compatible con React 18 (`reactflow` v11.x). |
| Dependencia circular: Pasos 04-05-07 | Media | Paso 04 crea formulario, Paso 05 TemplatePicker, Paso 07 Canvas interactivo. Si Paso 05 se retrasa, el formulario funciona sin TemplatePicker. | Diseñar AgentForm como standalone (TemplatePicker es complementario, no requerido para submit). |
| Missing `model` migration | Media | `model` column no existe en `agent_catalog` | Agregar migración separada `031_agent_catalog_add_model.sql` |

---

## 7️⃣ Plan de Implementación

> **Regla:** Una tarea = un artefacto. Interfaz exacta + patrón + verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: Instalar dependencias** | `package.json` | `npm install reactflow zod @reactflow/node-toolbar @reactflow/node-resizer` | — | DX | Baja | 0.5h | Ninguna | → verificar: `npm ls reactflow zod` sin errores |
| 1 | **Crear BuilderLayout** | `dashboard/components/builder/BuilderLayout.tsx` | `export default function BuilderLayout({ children }: { children: React.ReactNode })` — split 60/40, responsive | `dashboard/components/app-sidebar.tsx` (Layout pattern) | CODE | Baja | 0.5h | Tarea 0 | → verificar: componente renderiza sin errores en Storybook/dev |
| 2 | **Crear BuilderCanvas** | `dashboard/components/builder/BuilderCanvas.tsx` | `export default function BuilderCanvas()` — `<ReactFlow nodes={[]} edges={[]}>` con `fitView` | ReactFlow docs + `dashboard/components/flows/FlowHierarchyView.tsx` (concepto de grafo) | CODE | Media | 1h | Tarea 0,1 | → verificar: canvas renderiza vacío sin errores SSR (dynamic import) |
| 3 | **Crear AgentForm** | `dashboard/components/builder/AgentForm.tsx` | `export default function AgentForm({ onSave }: { onSave: (data: AgentFormData) => Promise<void> })` — campos: role, goal, backstory, llmProvider, llmModel, tools, maxIter, toggles. Zod schema: `role` min 1, `goal` min 10, `backstory` min 10. | `dashboard/components/tickets/CreateTicketForm.tsx` (form pattern) + `dashboard/components/agents/AgentToolsCard.tsx` (tools display) | CODE | Alta | 2h | Tarea 0,1 + endpoints existentes | → verificar: submit con datos válidos pasa validación Zod; submit sin role falla |
| 4 | **Crear TemplatePicker** | `dashboard/components/builder/TemplatePicker.tsx` | `export default function TemplatePicker({ onSelect }: { onSelect: (template: TemplateInfo) => void })` — grid de cards, filtro categoría, búsqueda | `dashboard/components/flows/RunFlowDialog.tsx` (modal pattern) | CODE | Media | 1.5h | Ninguna (endpoints ya existen) | → verificar: GET /api/templates carga cards; filtro categoría funciona; búsqueda filtra |
| 5 | **Crear ruta builder** | `dashboard/app/(app)/builder/page.tsx` | `export default function BuilderPage()` — monta `<BuilderLayout>` con `<BuilderCanvas>` + `<AgentForm>` + `<TemplatePicker>` | `dashboard/app\(app\)\agents\page.tsx` (data fetching pattern) | CODE | Media | 1h | Tareas 1-4 | → verificar: ruta /builder accesible, layout renderiza completo |
| 6 | **Agregar Builder a navegación** | `dashboard/components/nav-main.tsx` + `dashboard/components/app-sidebar.tsx` | Agregar item `{ title: 'Builder', url: '/builder', icon: Wand2 }` a `defaultNavItems` y `navMain` | Misma estructura que items existentes (ej: Agents, Workflows) | CODE | Baja | 0.25h | Tarea 5 | → verificar: enlace "Builder" visible en sidebar, navega a /builder |
| 7 | **Validar flujo Save Agent** | — | Script de prueba manual o test: llenar form → submit → verificar registro en Supabase `agent_catalog` | `src/cli/commands/templates_seed.py` (patrón seed/check) | FULLSTACK | Media | 0.5h | Tareas 3-6 + Supabase accesible | → verificar: `SELECT * FROM agent_catalog WHERE role = 'test_from_builder'` retorna fila nueva |

### Tiempo total estimado: ~8.25 horas

### Notas de implementación:

**Tarea 0:** Agregar `reactflow` y `zod` a `package.json` del dashboard. Ejecutar `npm install`. Considerar `@reactflow/node-toolbar` y `@reactflow/node-resizer` como extras opcionales para el canvas (útil en Paso 07).

**Tarea 3 (AgentForm):**  
- El formulario debe construir `soul_json: { role, goal, backstory }` antes del submit.  
- `allowed_tools` se toma del multi-select que consume `GET /api/tools/available?source=local`.  
- Si el modelo LLM no está en la DB aún, guardarlo solo en el formulario (campo display-only derivado del provider).  
- Usar `createClient()` de `@/lib/supabase` para INSERT directo:  
  ```typescript
  const supabase = createClient()
  await supabase.from('agent_catalog').insert({
    org_id, role, is_active: true,
    soul_json: { role, goal, backstory },
    allowed_tools, max_iter,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  })
  ```

**Tarea 5 (Página builder):**  
- Debe ser `use client` obligatoriamente (ReactFlow no soporta SSR).  
- Alternativamente, cargar `<BuilderCanvas>` con `dynamic(() => import('./BuilderCanvas'), { ssr: false })`.

**Tarea 7 (Validación):**  
- Si RLS bloquea el INSERT, considerar crear un endpoint `POST /api/agents` o usar RPC para setear `app.org_id` antes del insert.

---

## 🔮 Roadmap (NO implementar ahora)

- **Paso 05 (Template Picker):** La Tarea 4 prepara el componente. Puede implementarse en paralelo o secuencialmente.
- **Paso 07 (Canvas interactivo):** BuilderCanvas se crea vacío. Arrastrar agentes, tareas y conexiones será la evolución del canvas. La estructura ReactFlow con tipos de nodo custom debe diseñarse en la Tarea 2 pensando en extensibilidad.
- **Paso 08 (ExportDialog):** Consume `POST /api/bundles/export`. No es bloqueante para este paso.
- **Migración 031 (model column):** Agregar `model TEXT` a `agent_catalog` cuando se confirme si el campo es funcional o solo display.

---

## 🚫 Reglas de Oro verificadas

- ✅ **Análisis accionable y específico:** Cada tarea tiene artefacto, firma y verificación concreta.
- ✅ **TODO verificado contra código:** 20 items verificados, 2 faltantes identificados (reactflow, zod), 4 discrepancias documentadas.
- ✅ **Ambigüedades señaladas:** D2 (modelos LLM), D3 (RLS INSERT), D4 (campo model vs DB).
- ✅ **Si contradicción plan vs código → código gana:** No hay contradicción directa, pero se identifica que `model` en types.ts no tiene columna en DB.
- ✅ **Nivel CTO exigente:** 20 verificaciones, 4 discrepancias, ≥ 3 riesgos.
- ✅ **Coherente con phase-state.md:** No contradice decisiones previas.
- ✅ **TODO el paso:** 4 sub-pasos cubiertos (formulario, canvas, layout, navegación + scaffold DX).
- ✅ **Etapas secuenciales:** data → code → backend → fullstack+DX completadas en orden.
- ✅ **≥ 1 herramienta DX:** `fap builder scaffold` propuesto.
- ✅ **Tareas atómicas:** 7 tareas = 7 artefactos.
- ✅ **Interfaz exacta por tarea:** Firmas completas documentadas.
- ✅ **Patrón de referencia explícito:** Archivo concreto referenciado para cada patrón.
- ✅ **Verificación inline:** Comando de verificación por tarea.
- ✅ **Estimación de tiempo:** ~8.25h total, por tarea.

---

*Análisis generado por ring — Kilo Engineer Agent*