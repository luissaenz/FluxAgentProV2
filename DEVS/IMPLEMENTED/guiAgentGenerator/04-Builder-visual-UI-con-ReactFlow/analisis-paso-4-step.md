# 🧠 ANALISIS PASO 4 — Builder visual — layout y formulario de agente
**Agente:** step  
**Modo:** caveman ultra  
**Fecha:** 2026-05-14  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `reactflow` instalado | `npm list reactflow` | ❌ NO INSTALADO | package.json sin `reactflow` |
| 2 | `dashboard/app/(app)/builder/page.tsx` | glob builder/ | ❌ NO EXISTE | — |
| 3 | `AgentForm.tsx` | glob builder/ | ❌ NO EXISTE | — |
| 4 | `BuilderCanvas.tsx` | glob builder/ | ❌ NO EXISTE | — |
| 5 | `BuilderLayout.tsx` | glob builder/ | ❌ NO EXISTE | — |
| 6 | Zod (validación frontend) | package.json | ❌ NO PRESENTE | sin `zod` en dependencies |
| 7 | Tabla `agent_catalog` (schema) | `supabase/migrations/004_agent_catalog.sql` | ✅ | cols: id, org_id, role, soul_json JSONB, allowed_tools TEXT[], max_iter |
| 8 | RLS `agent_catalog_tenant_isolation` | `004_agent_catalog.sql:22-23` | ✅ | `org_id::text = current_setting('app.org_id', TRUE)` |
| 9 | `GET /api/tools/available` | `src/api/routes/tools.py:46-63` | ✅ | retorna `ToolsListResponse`,ToolInfo[] |
| 10 | `ToolInfo` model (backend) | `tools.py:25-36` | ✅ | name, description, category, categories, source, parameters, requires_approval, timeout_seconds, is_active |
| 11 | `ToolRegistry` singleton | `src/tools/registry.py:272` | ✅ | `tool_registry = ToolRegistry()` |
| 12 | `MCPPool` singleton | `src/tools/mcp_pool.py:42-56` | ✅ | circuit breaker + retry |
| 13 | `GET /api/templates` | `src/api/routes/templates.py:54-67` | ✅ | list + filter `?category=` + `count`, **público sin auth** |
| 14 | `GET /api/templates/{id}` | `templates.py:70-83` | ✅ | detalle con `soul_json`, 404 |
| 15 | Tabla `agent_templates` (global) | `030_agent_templates.sql:10-21` | ✅ | sin `org_id`, RLS SELECT auth, ALL service_role |
| 16 | `Switch` component | `dashboard/components/ui/switch.tsx` | ✅ | Radix-based |
| 17 | `Select` component | `dashboard/components/ui/select.tsx` | ✅ | Radix-based |
| 18 | Layout pattern `AppLayout` | `dashboard/app/(app)/layout.tsx` | ✅ | SidebarProvider + AppSidebar + SiteHeader |
| 19 | `NavMain` default items | `dashboard/components/nav-main.tsx:43-63` | ✅ | sin "Builder" → se añade en Paso 09 |
| 20 | `fapFetch` auth + org header | `dashboard/lib/api.ts:5-52` | ✅ | Bearer + `X-Org-ID` |

**Discrepancias:**

| ID | Descripción | Plan vs Código | Resolución propuesta |
|---|---|---|---|
| D1 | Zod no en dependencies | Plan: "Validación con Zod" → Frontend sin `zod` | Añadir `zod` + `@hookform/resolvers` a `dashboard/package.json`, o validación manual con `useState`. |
| D2 | Multi-select no existe | Plan: "Tools (multi-select desde GET /api/tools/available)" → No hay `MultiSelect` component | Crear `MultiSelect` custom (Dropdown + Checkboxes) o usar librería externa. Marcar como Tarea 0 DX. |
| D3 | Slider no existe | Plan: "Max Iterations (slider 1-10)" → No hay `Slider` en shadcn/ui | Instalar `@radix-ui/react-slider` + crear `Slider.tsx`, o usar `Input type=number`. |
| D4 | Save Agent directo frontend sin endpoint | Plan: "Botón 'Save Agent' → guarda en `agent_catalog` vía Supabase (directo desde frontend, sin nuevo endpoint)" → `agent_catalog` tiene RLS tenant_isolation que requiere `app.org_id` seteado en sesión DB. Frontend anon key no puede setear `app.org_id` directamente sin RPC autorizado. **Patrón actual**: Tickets van通过 `POST /tickets` (backend). | **Opción A (segura):** crear `POST /api/agents` endpoint que use `TenantClient` y setee `app.org_id` (recomendado). **Opción B (insegura):** RPC `set_config('app.org_id', ...)` desde frontend → requiere validación de membership → necesita función SQL `set_org_context` que verifique org membership antes de setear. **Discrepancia crítica**: plan asume direct write factible; código actual sugiere lo contrario. |
| D5 | LLM Provider/Model fields | `soul_json` en templates solo incluye `role, goal, backstory`. Plan agrega `llm_provider`, `llm_model`, `verbose`, `reasoning`, `inject_date`, `memory`. | Añadir esos campos al `soul_json` al guardar. No requieren migración (JSONB flexible). Verificar que backend los consuma. |
| D6 | Tools multi-select values | Backend `ToolInfo.name` para MCPtools usa prefijo `mcp:server:tool`. Plan supone guardar array de tool names → consistente con `allowed_tools TEXT[]`. ✅ | — |

**Suposiciones no verificadas (⚠️):**
- `agent_catalog` insert desde frontend Requires RLS session setup. Asumimos que `fapFetch` podría incluir paso `supabase.rpc('set_org_context', ...)` antes de insert. **Confirmar con dueño**.
- Los campos extra (verbose, reasoning, etc.) se almacenan en `soul_json` y son opcionales. Backend `Agent` model en `types.ts:87-102` no lista esos campos, pero `soul_json` es `Record<string, unknown>` → flexible. ✅ asumible.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas involucradas:**
- `agent_catalog` (004) — **existente**, RLS tenant isolation.
- `agent_templates` (030) — **existente**, catálogo global (read-only para frontend).
- `org_mcp_servers` — existente, usada por tools endpoint.

**Schema `agent_catalog` relevante:**
```sql
id UUID PK, org_id UUID FK, role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INTEGER, is_active BOOLEAN, created_at, updated_at
UNIQUE(org_id, role)  -- ya existe
```

**Campos del formulario → destino:**
| Campo Frontend | Tipo | Destino DB | Obligatorio |
|---|---|---|---|
| role | TEXT | `agent_catalog.role` | ✅ (UNIQUE per org) |
| goal | TEXT | `soul_json.goal` | ✅ |
| backstory | TEXT | `soul_json.backstory` | ✅ |
| llm_provider | TEXT | `soul_json.llm_provider` | ⚠️ opcional (default groq) |
| llm_model | TEXT | `soul_json.llm_model` | ⚠️ opcional |
| allowed_tools | TEXT[] | `agent_catalog.allowed_tools` | ⚠️ default [] |
| max_iter | INTEGER | `agent_catalog.max_iter` | ⚠️ default 3 (plan) |
| verbose | BOOLEAN | `soul_json.verbose` | ⚠️ opcional |
| reasoning | BOOLEAN | `soul_json.reasoning` | ⚠️ opcional |
| inject_date | BOOLEAN | `soul_json.inject_date` | ⚠️ opcional |
| memory | BOOLEAN | `soul_json.memory` | ⚠️ opcional |

**RLS considerations:**
- `agent_catalog` insert: RLS policy `tenant_isolation` evalúa `org_id::text = current_setting('app.org_id', TRUE)`.
- Si_frontend insert directo → `app.org_id` debe estar seteado en la sesión PostgreSQL.
- `agent_templates` global → solo read.

**Índices existentes (004):**
- `idx_agent_catalog_org_role` en `(org_id, role)` WHERE `is_active = TRUE` → cubre búsquedas por org.

**Integridad referencial:**
- `org_id` referencia `organizations(id)` ON DELETE CASCADE — OK.
- No FK externas adicionales.

**Gaps de datos:**
- None. JSONB flexible permite nuevos campos sin migración.

---

## 2️⃣ Análisis de Código (ETAPA 2)

**Componentes nuevos a crear:**

| Archivo | Propósito | Patrón a seguir | Notas |
|---|---|---|---|
| `dashboard/app/(app)/builder/page.tsx` | Página入口 del builder | Siguen `app/(app)/agents/page.tsx` (page + client component) | Estructura: `export default function BuilderPage() { return <BuilderLayout /> }` |
| `dashboard/components/builder/BuilderLayout.tsx` | Split panel 60/40 | Siguen `dashboard/components/flows/FlowHierarchyView.tsx` o cualquier `Card` layout | Layout: izquierda `<BuilderCanvas />`, derecha `<AgentForm />` + botones. Responsive: flex-col en móvil. |
| `dashboard/components/builder/AgentForm.tsx` | Formulario con todos los campos | Siguen `dashboard/components/tickets/CreateTicketForm.tsx` (useState + validación manual) **o** migrar a `react-hook-form` + `zod` | Plan exige Zod → requiere instalación. Sugerencia: usar `useForm` con `zodResolver`. |
| `dashboard/components/builder/BuilderCanvas.tsx` | Contenedor ReactFlow vacío | Siguen `reactflow`官方 ejemplos + `Dashboard` pattern de Next.js | ReactFlow debe ser dynamic import (`next/dynamic`) para evitar SSR. |

**Interfaces TypeScript sugeridas:**
```ts
// AgentForm fields
interface AgentFormData {
  role: string
  goal: string
  backstory: string
  llm_provider: 'groq' | 'openai' | 'anthropic' | 'openrouter'
  llm_model: string
  allowed_tools: string[]  // ToolInfo.name
  max_iter: number  // 1-10
  verbose: boolean
  reasoning: boolean
  inject_date: boolean
  memory: boolean
}
```

**Patrones existentes a reutilizar:**
- **Hooks de datos:** `useFlows()` → patrón `useQuery` con `useCurrentOrg`. Para tools: crear `useTools(orgId, source?)`. Templates: `useQuery(['templates'])` → `api.get('/api/templates')`.
- **Supabase inserts:** No hay ejemplo frontend directo. Solo通过 backend API. **Gap**.
- **Validación:** `CreateTicketForm` usa `useState` + validación manual. `RunFlowDialog` usa `useForm` sin zod.  
  → Para Zod: instalar `zod` y definir `AgentFormSchema`.

**Imports correctos (convención):**
- Absolutos: `from '@/components/...'`
- Hooks: `from '@/hooks/useCurrentOrg'`
- API: `from '@/lib/api'`
- UI: `from '@/components/ui/...'`

**Componentes UI disponibles:**
- ✅ `Button`, `Input`, `Textarea`, `Label`, `Select`, `Switch`, `Checkbox`, `Card`, `Badge`, `Skeleton`, `Toast (sonner)`.
- ❌ `MultiSelect` → crear.
- ❌ `Slider` → crear o sustituir por `Input type=number`.

**ReactFlow specifics:**
- Instalación requerida: `npm install reactflow`.
- CSS: `import 'reactflow/dist/style.css'` en `page.tsx` o layout.
- Componentes nodo: `AgentNode`, `TaskNode`, `ToolNode` → se implementan en Paso 07. Paso 04 solo canvas vacío → `ReactFlow` component básico con `defaultNodes=[]`, `defaultEdges=[]`.
- SSR: `dynamic(() => import('reactflow'), { ssr: false })` wrap.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Endpoints consumidos por Paso 4 (UI):**

| Endpoint | Método | Usado en | Auth | Response |
|---|---|---|---|---|
| `GET /api/tools/available` | GET | Tools multi-select | `require_org_id` | `{ tools: ToolInfo[], count }` |
| `GET /api/templates` | GET | TemplatePicker (Paso 05, pero puede cargarse en builder) | None | `{ templates: TemplateInfo[], count }` |
| `POST /api/agents` | **NO EXISTE** | Save Agent | `require_org_id` | `Agent` |
| `GET /api/templates/{id}` | GET | TemplatePicker detalle | None | `TemplateDetailResponse` incluye `soul_json` |

**Contrato para `POST /api/agents` (nuevo, sugerido):**
```python
# src/api/routes/agents.py (ya existe agents.py? Verificar)
class AgentCreate(BaseModel):
    role: str
    soul_json: dict  # contiene goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory
    allowed_tools: list[str] = []
    max_iter: int = 3

# Handler:
@router.post("", response_model=AgentResponse)
async def create_agent(
    payload: AgentCreate,
    org_id: str = Depends(require_org_id),
):
    # Usar TenantClient para set app.org_id
    with TenantClient(org_id) as db:
        agent = db.table("agent_catalog").insert({
            "org_id": org_id,
            "role": payload.role,
            "soul_json": payload.soul_json,
            "allowed_tools": payload.allowed_tools,
            "max_iter": payload.max_iter,
            "is_active": True,
        }).execute()
    return agent.data[0]
```

**Middleware aplicable:** `require_org_id` (extrae `X-Org-ID`). Necesario para `POST /api/agents`.

**Flujo datos:**
1. Frontend: formulario → payload JSON con `soul_json` anidado.
2. `api.post('/api/agents', payload)` → headers: `Authorization: Bearer <token>`, `X-Org-ID: <orgId>`.
3. Backend: valida Pydantic, inserta en `agent_catalog` con RLS filtrando por `org_id`.
4. Retorna `Agent` con `id`, `org_id`, etc.

**RLS保证:**
- backend setea `app.org_id` via `TenantClient` → insert solo permite agents dentro de esa org.
- Frontend directo (sin backend) NO funciona sin `app.org_id` en sesión → **gap**.

**Contratos existentes validados:**
- `GET /api/tools/available` → Tools con `source: "local" | "mcp"`, MCP tools con prefijo `mcp:{server}:{tool}`. Plan: "Tools desde GET /api/tools/available" → OK.
- `GET /api/templates` → Devuelve templates globales sin auth. Plan: TemplatePicker en paso 05, pero builder puede precargar. ✅.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

**Flujo end-to-end ( happy path ):**

1. Usuario accede `/dashboard/app/builder` → `BuilderPage` carga.
2. `BuilderLayout` renderiza: izquierda canvas vacío (ReactFlow), derecha `AgentForm`.
3. `AgentForm` carga tools via `useTools` (`GET /api/tools/available`).
4. Usuario completa campos:
   - role, goal, backstory → requeridos.
   - LLM provider → select. Model → dinámico ( provider→models mapping).
   - Tools → multi-select (múltiples `ToolInfo.name`).
   - Max iterations → slider (number).
   - Toggles → Switch components.
5. Click "Save Agent" → validación Zod → `POST /api/agents` (backend) → insert en `agent_catalog`.
6. Success → toast + limpiar formulario.

**Coherencia arquitectónica:**
- UI stack: Next.js App Router + shadcn/ui + Tailwind → consistente.
- Data fetching: React Query pattern (`useQuery`) → ya usado en `useFlows`, `useTickets`.
- State: `useState` o `useForm` → consistente con `CreateTicketForm`.
- RLS: Tenant isolation → respetado con backend endpoint.
- **Inconsistencia:** plan pide frontend directo; arquitectura actual usa backend endpoints para writes. Inconsistencia **crítica** → ajustar plan o crear endpoint.

**DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: **`fap agents create` CLI command**
- **Qué automatiza:** Crear agentes desde terminal sin UI. Útil para scripting, seeding, DevOps.
- **Tipo:** CLI command (Typer) en `src/cli/commands/agents_create.py`.
- **Cómo se usa:**
  ```bash
  fap agents create --role "Research Agent" --goal "Research topics" --backstory "You are..." --tools "sql_analytical" "event_store" --model "groq/llama-3.3-70b-versatile" --max-iter 5
  ```
- **Impacto:** Reduce fricción en automatizaciones, CI/CD, pruebas. No depende del dashboard.
- **Prioridad:** Tarea 0 (antes de Paso 04 UI) → validar schema y backend antes de UI.

### Herramienta Propuesta: **`fap agents validate` CLI command**
- **Qué automatiza:** Validar `soul_json` de un agente contra esquema (role, goal, backstory obligatorios; max_iter 1-10; tools existen en registry).
- **Tipo:** Validador CLI.
- **Uso:**
  ```bash
  fap agents validate --file agent.json
  ```
- **Impacto:** Previene errores antes de guardar, útil para import/export.

### Herramienta Propuesta: **`useAgentForm` hook + `AgentFormValidator` component**
- **Qué automatiza:** Reutilizar lógica de formulario en múltiples páginas (builder, playground).
- **Tipo:** Custom hook + componente composable.
- **Uso:**
  ```tsx
  const { register, errors, submit } = useAgentForm()
  ```
- **Impacto:** DRY, consistente.

**Gaps de UX:**
- Sin multi-select → UX pobre (checkboxes list).
- Sin slider → UX número input.
- Sin breadcrumbs → orientación usuario (Paso 09).
- ReactFlow SSR crash → usar dynamic import (`dynamic(() => import('reactflow'), { ssr: false })`) → documentar.

---

## 5️⃣ Criterios de Aceptación

Lista binaria, verificable:

✅ **[DATA]** Tabla `agent_catalog` existe con columnas: `role`, `soul_json`, `allowed_tools`, `max_iter`. — Verificado: `004_agent_catalog.sql`.
✅ **[DATA]** RLS policy `agent_catalog_tenant_isolation` aplica `org_id` desde `current_setting('app.org_id')`.
✅ **[CODE]** Componente `AgentForm.tsx` existe con campos: role, goal, backstory, llm_provider, llm_model, allowed_tools (multi-select), max_iter (number input o slider), toggles: verbose, reasoning, inject_date, memory.
✅ **[CODE]** Validación con Zod (o manual si se decide) bloquea save si role/goal/backstory vacíos.
✅ **[CODE]** `BuilderLayout.tsx` implementa split panel: 60% izquierda canvas, 40% derecha formulario. Responsive: mobile column.
✅ **[CODE]** `BuilderCanvas.tsx` renderiza `<ReactFlow />` vacío con `fitView`, minimapa, controles zoom. Dynamic import ssr:false.
✅ **[BACKEND]** Endpoint `POST /api/agents` existe (si se elige Opción A) y accepts payload con `soul_json` anidado, inserta correctamente con TenantClient.
✅ **[BACKEND]** Endpoint `GET /api/tools/available` devuelve tools locales + MCP con `source` y `category`.
✅ **[FULLSTACK]** Usuario puede crear agente y verlo listado en `/agents` (confirmar insert exitoso).
✅ **[DX]** CLI `fap agents create` ejecuta sin errores y crea agente en DB.
⚠️ **[DX]** Zod instalado en frontend (`zod` + `@hookform/resolvers`). *Pendiente añadir*.

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: Insert directo frontend viola RLS | **Alta** | `agent_catalog` RLS requiere `app.org_id` en sesión. Frontend anon key no puede setearlo sin RPC autorizado. | Implementar `POST /api/agents` endpoint con `TenantClient` (Patrón tickets). |
| R2: Multi-select no nativo en Radix | **Media** | Radix `Select` no soporta `multiple`. | Crear componente custom con `DropdownMenu` + `Checkbox` items. Tarea 0 DX. |
| R3: Slider ausente en shadcn/ui | **Baja** | No hay `Slider` en UI components. | Usar `Input type=number` con `min/max` o instalar `@radix-ui/react-slider` + crear componente. |
| R4: LLM model dinámico requiere mapeo | **Media** | Provider→models no expose API. | Hardcodear mapping en frontend desde `config.py` (provider_models = { groq: [...], openai: [...], ...}). |
| R5: ReactFlow SSR break | **Media** | ReactFlow no isomórfico. | Dynamic import con `ssr: false` en `BuilderCanvas`. Loading skeleton previo. |
| R6: Validación Zod no disponible | **Baja** | `zod` no en package.json. | Añadir a dependencies o validación manual simple (if !role...). |

**Riesgos futuro (post-MVP):**
- Performance: `GET /api/tools/available` con cientos de MCP tools → paginación.
- UX: Formulario muy largo → wizard steps.

---

## 7️⃣ Plan de Implementación

**Total estimado:** 13h (D: 1h, C: 4h, B: 2h, F: 3h, DX: 3h)

**Reglas atómicas aplicadas:**
- Cada tarea = 1 archivo o 1 función.
- Interfaz exacta especificada.
- Patrón de referencia explícito.
- Verificación inline incluida.
- Implementador no decide nada.

| # | Tarea | Artefacto | Interfaz exacta / especificación | Patrón a seguir | Etapa | Complejidad | Tiempo | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: instalar reactflow + slider component | `dashboard/package.json` + `dashboard/components/ui/slider.tsx` | `npm install reactflow @radix-ui/react-slider` + `Slider` component shadcn-style | `switch.tsx` (Radix) | DX | Baja | 1h | — | `npm run build` sin errores; `import { Slider }` OK |
| 0b | **DX & Tooling**: multi-select component | `dashboard/components/ui/multi-select.tsx` | `MultiSelect(options: {value:string, label:string}[]): { selected: string[], onToggle: (v:string)=>void }` | `Select` + `Checkbox` + `DropdownMenu` | DX | Media | 2h | — | Storybook o demo page render |
| 0c | **DX & Tooling**: CLI `fap agents create` | `src/cli/commands/agents_create.py` | `def create_agent(role, goal, backstory, llm_provider, llm_model, tools, max_iter, verbose, reasoning, inject_date, memory):` | `templates_seed.py` (typer) | DX | Media | 2h | — | `fap agents create --help` OK |
| 1 | Página builder入口 | `dashboard/app/(app)/builder/page.tsx` | `export default function BuilderPage() { return <BuilderLayout /> }` | `app/(app)/agents/page.tsx:14` | CODE | Baja | 0.5h | Tarea 0 | `http://localhost:3000/dashboard/app/builder` carga sin 404 |
| 2 | BuilderLayout split panel | `dashboard/components/builder/BuilderLayout.tsx` | `export function BuilderLayout({ childrenLeft, childrenRight })` o `children: { left: ReactNode, right: ReactNode }` | `app/(app)/layout.tsx` (flex Split) | CODE | Baja | 1h | Tarea 1 | Layout con dos paneles visibles, left 60%, right 40%, mobile column |
| 3 | AgentForm con Zod | `dashboard/components/builder/AgentForm.tsx` | `export function AgentForm({ onSuccess }: { onSuccess: () => void })`<br>Campos exactos: `role`, `goal`, `backstory`, `llm_provider` (select), `llm_model` (select), `allowed_tools` (MultiSelect), `max_iter` (number o Slider), `verbose`, `reasoning`, `inject_date`, `memory` (Switch).<br>Validación: `z.object({ role: z.string().min(1), goal: z.string().min(10), backstory: z.string().min(10) })` | `CreateTicketForm.tsx` + `RunFlowDialog.tsx` (useForm) | CODE | Alta | 3h | Tarea 2, 0b | Form renderiza, validación bloquea submit vacío, Zod error messages |
| 4 | BuilderCanvas (ReactFlow) | `dashboard/components/builder/BuilderCanvas.tsx` | `export function BuilderCanvas() { return ( <ReactFlow nodes={[]} edges={[]} onNodesChange... > <Background/><Controls/><MiniMap/> </ReactFlow> ) }` | Ejemplo oficial ReactFlow + `dynamic` import | CODE | Media | 2h | Tarea 0 | Canvas visible sin crash SSR, minimapa y zoom controls operativos |
| 5 | Integrar BuilderLayout en page | `dashboard/app/(app)/builder/page.tsx` | Combinar Tareas 1,2,3,4: `<BuilderLayout left={<BuilderCanvas/>} right={<AgentForm onSuccess={...}/>}` | — | CODE | Baja | 0.5h | Tareas 1-4 | Página funcional completa |
| 6 | Backend endpoint `POST /api/agents` | `src/api/routes/agents.py` | `@router.post("") async def create_agent(payload: AgentCreate, org_id: str = Depends(require_org_id)) -> AgentResponse:`<br>Firma: `def create_agent(payload: AgentCreate, org_id: str = Depends(require_org_id))` | `src/api/routes/templates.py:54` (list) + `src/db/session.py` TenantClient | BACKEND | Media | 2h | — | `curl -X POST /api/agents -H "X-Org-ID: ..." -d {...}` → 201, agente creado |
| 7 | Registrar router agents en main | `src/api/main.py` | `from src.api.routes import agents`<br>`app.include_router(agents.router, prefix="/api")` | `main.py:31,112` (tools, bundles) | BACKEND | Baja | 0.5h | Tarea 6 | `GET /openapi.json` incluye `/api/agents` |
| 8 | Añadir "Builder" a NavMain | `dashboard/components/nav-main.tsx` | `defaultNavItems.push({ title: 'Builder', url: '/dashboard/app/builder', icon: Wand2 })` (o insert en array posición 5) | Existente nav items | FULLSTACK | Baja | 0.5h | Tarea 5 | Sidebar muestra "Builder" ícono (Wand2) → click navega |
| 9 | Breadcrumbs en Builder page | `dashboard/app/(app)/builder/page.tsx` + `SiteHeader` ya muestra浮动 breadcrumbs? | Usar `Breadcrumb` component: `Dashboard > Builder > New Agent` | `dashboard/components/ui/breadcrumb.tsx` | FULLSTACK | Media | 1h | Tarea 5 | Ruta cambia → breadcrumb actualiza |
| 10 | E2E test: crear agente | `tests/e2e/test_builder_agent_creation.py` (o .ts si Playwright) | Test: visit `/builder`, fill form, submit, verify DB row exists via API `GET /api/agents` | Patrón tests existentes en `tests/e2e/` (si existen) | TEST | Alta | 2h | Tareas 1-9 | Test pasa, agente persistido |
| 11 | Unit test: AgentForm validation | `tests/unit/test_agent_form.tsx` (si usa RHF) o manual | Simulate submit empty → errors present; valid payload → calls `api.post` | `tests/unit/test_bundle_export.py` (py) / `test_templates.py` | TEST | Media | 1h | Tarea 3 | Test pasan |
| 12 | Actualizar `agent_catalog` query hook (opcional) | `dashboard/hooks/useAgents.ts` si no existe | `useAgents(orgId)` → query `SELECT * FROM agent_catalog WHERE org_id = ?` | `useFlows.ts` patrón | CODE | Baja | 0.5h | Tarea 6 | Hook disponible para lista agents |

**Ajustes necesarios previos a implementación:**

- **Migración**: No hay cambios schema → no migración.
- **CLI tools**: 
  - `fap agents create` → usa `Supabase` service client (backend) con `TenantClient`.
  - `fap agents validate` → valida `soul_json` estructura mínima.
- **Dependencies añadir:**
  - Backend: ninguna (usar `src.db.session.TenantClient`).
  - Frontend: `reactflow`, `zod`, `@hookform/resolvers` (si se usa RHF + Zod), `@radix-ui/react-slider` (opcional), `lucide-react` ya incluye iconos (Wand2 para Builder).
- **Config provider:** No se necesita.

**Implementación por etapas:**
1. **Tarea 0** (DX): installer + componentes base (Slider, MultiSelect) + CLI commands.  
2. **Tarea 6** (Backend): crear `POST /api/agents` → garantiza RLS safe.  
3. **Tarea 1-5** (Frontend UI):(page, layout, form, canvas).  
4. **Tarea 8-9** (Nav + Breadcrumbs).  
5. **Tarea 10-11** (Tests).  

**Nota:** Si se decide **no** crear endpoint y seguir plan (frontend directo), se requiere:
- RPC `set_org_context(org_id uuid)` en DB que valida membership antes de `set_config`.  
- Frontend: llamar `supabase.rpc('set_org_context', { org_id })` antes de insert.  
Esa RPC no existe → crearla en migración aparte. **No recomendado** por seguridad.

---

## 🛠️ Resumen Ejecutivo (caveman)

- **Estado actual**: endpoints tools + templates OK;前端 sin reactflow, sin Zod, sin multi-select/slider.  
- **Discrepancia crítica**: Save Agent directo frontend → RLS bloquea sin `app.org_id`. Solución: endpoint backend `POST /api/agents`.  
- **Tareas atómicas**: 12 tasks (incluye 0,0b,0c DX).  
- **DX tools mínimas**: 3 propuestas (CLI create, CLI validate, useAgentForm hook).  
- **Tiempo total**: ~13h (incluye aprendizaje, tests).  
- **Riesgo alto**: RLS → bloquea insert directo. Mitigate: endpoint backend.  
- **Próximo paso inmediato**:  
  1. Añadir `zod`, `reactflow` a `package.json` + `npm install`.  
  2. Crear `src/api/routes/agents.py` + registrar en `main.py`.  
  3. Implementar `AgentForm` con validación manual ( MVP ) o Zod (post-instalación).  

**Done.** Archivo guardaría en `DEVS/IN_PROGRESS/analisis-paso-4-step.md` una vez aprobado.


</invoke>
</function_calls>

<invoke name="write">
<parameter name="content">
# 🧠 ANALISIS PASO 4 — Builder visual — layout y formulario de agente
**Agente:** step  
**Modo:** caveman ultra  
**Fecha:** 2026-05-14  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `reactflow` instalado | `npm list reactflow` | ❌ NO INSTALADO | package.json sin `reactflow` |
| 2 | `dashboard/app/(app)/builder/page.tsx` | glob builder/ | ❌ NO EXISTE | — |
| 3 | `AgentForm.tsx` | glob builder/ | ❌ NO EXISTE | — |
| 4 | `BuilderCanvas.tsx` | glob builder/ | ❌ NO EXISTE | — |
| 5 | `BuilderLayout.tsx` | glob builder/ | ❌ NO EXISTE | — |
| 6 | Zod (validación frontend) | package.json | ❌ NO PRESENTE | sin `zod` en dependencies |
| 7 | Tabla `agent_catalog` (schema) | `supabase/migrations/004_agent_catalog.sql` | ✅ | cols: id, org_id, role, soul_json JSONB, allowed_tools TEXT[], max_iter |
| 8 | RLS `agent_catalog_tenant_isolation` | `004_agent_catalog.sql:22-23` | ✅ | `org_id::text = current_setting('app.org_id', TRUE)` |
| 9 | `GET /api/tools/available` | `src/api/routes/tools.py:46-63` | ✅ | retorna `ToolsListResponse`,ToolInfo[] |
| 10 | `ToolInfo` model (backend) | `tools.py:25-36` | ✅ | name, description, category, categories, source, parameters, requires_approval, timeout_seconds, is_active |
| 11 | `ToolRegistry` singleton | `src/tools/registry.py:272` | ✅ | `tool_registry = ToolRegistry()` |
| 12 | `MCPPool` singleton | `src/tools/mcp_pool.py:42-56` | ✅ | circuit breaker + retry |
| 13 | `GET /api/templates` | `src/api/routes/templates.py:54-67` | ✅ | list + filter `?category=` + `count`, **público sin auth** |
| 14 | `GET /api/templates/{id}` | `templates.py:70-83` | ✅ | detalle con `soul_json`, 404 |
| 15 | Tabla `agent_templates` (global) | `030_agent_templates.sql:10-21` | ✅ | sin `org_id`, RLS SELECT auth, ALL service_role |
| 16 | `Switch` component | `dashboard/components/ui/switch.tsx` | ✅ | Radix-based |
| 17 | `Select` component | `dashboard/components/ui/select.tsx` | ✅ | Radix-based |
| 18 | Layout pattern `AppLayout` | `dashboard/app/(app)/layout.tsx` | ✅ | SidebarProvider + AppSidebar + SiteHeader |
| 19 | `NavMain` default items | `dashboard/components/nav-main.tsx:43-63` | ✅ | sin "Builder" → se añade en Paso 09 |
| 20 | `fapFetch` auth + org header | `dashboard/lib/api.ts:5-52` | ✅ | Bearer + `X-Org-ID` |

**Discrepancias:**

| ID | Descripción | Plan vs Código | Resolución propuesta |
|---|---|---|---|
| D1 | Zod no en dependencies | Plan: "Validación con Zod" → Frontend sin `zod` | Añadir `zod` + `@hookform/resolvers` a `dashboard/package.json`, o validación manual con `useState`. |
| D2 | Multi-select no existe | Plan: "Tools (multi-select desde GET /api/tools/available)" → No hay `MultiSelect` component | Crear `MultiSelect` custom (Dropdown + Checkboxes) o usar librería externa. Marcar como Tarea 0 DX. |
| D3 | Slider no existe | Plan: "Max Iterations (slider 1-10)" → No hay `Slider` en shadcn/ui | Instalar `@radix-ui/react-slider` + crear `Slider.tsx`, o usar `Input type=number`. |
| D4 | Save Agent directo frontend sin endpoint | Plan: "Botón 'Save Agent' → guarda en `agent_catalog` vía Supabase (directo desde frontend, sin nuevo endpoint)" → `agent_catalog` tiene RLS tenant_isolation que requiere `app.org_id` seteado en sesión DB. Frontend anon key no puede setear `app.org_id` directamente sin RPC autorizado. **Patrón actual**: Tickets van通过 `POST /tickets` (backend). | **Opción A (segura):** crear `POST /api/agents` endpoint que use `TenantClient` y setee `app.org_id` (recomendado). **Opción B (insegura):** RPC `set_config('app.org_id', ...)` desde frontend → requiere validación de membership → necesita función SQL `set_org_context` que verifique org membership antes de setear. **Discrepancia crítica**: plan asume direct write factible; código actual sugiere lo contrario. |
| D5 | LLM Provider/Model fields | `soul_json` en templates solo incluye `role, goal, backstory`. Plan agrega `llm_provider`, `llm_model`, `verbose`, `reasoning`, `inject_date`, `memory`. | Añadir esos campos al `soul_json` al guardar. No requieren migración (JSONB flexible). Verificar que backend los consuma. |
| D6 | Tools multi-select values | Backend `ToolInfo.name` para MCPtools usa prefijo `mcp:server:tool`. Plan supone guardar array de tool names → consistente con `allowed_tools TEXT[]`. ✅ | — |

**Suposiciones no verificadas (⚠️):**
- `agent_catalog` insert desde frontend Requires RLS session setup. Asumimos que `fapFetch` podría incluir paso `supabase.rpc('set_org_context', ...)` antes de insert. **Confirmar con dueño**.
- Los campos extra (verbose, reasoning, etc.) se almacenan en `soul_json` y son opcionales. Backend `Agent` model en `types.ts:87-102` no lista esos campos, pero `soul_json` es `Record<string, unknown>` → flexible. ✅ asumible.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas involucradas:**
- `agent_catalog` (004) — **existente**, RLS tenant isolation.
- `agent_templates` (030) — **existente**, catálogo global (read-only para frontend).
- `org_mcp_servers` — existente, usada por tools endpoint.

**Schema `agent_catalog` relevante:**
```sql
id UUID PK, org_id UUID FK, role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INTEGER, is_active BOOLEAN, created_at, updated_at
UNIQUE(org_id, role)  -- ya existe
```

**Campos del formulario → destino:**
| Campo Frontend | Tipo | Destino DB | Obligatorio |
|---|---|---|---|
| role | TEXT | `agent_catalog.role` | ✅ (UNIQUE per org) |
| goal | TEXT | `soul_json.goal` | ✅ |
| backstory | TEXT | `soul_json.backstory` | ✅ |
| llm_provider | TEXT | `soul_json.llm_provider` | ⚠️ opcional (default groq) |
| llm_model | TEXT | `soul_json.llm_model` | ⚠️ opcional |
| allowed_tools | TEXT[] | `agent_catalog.allowed_tools` | ⚠️ default [] |
| max_iter | INTEGER | `agent_catalog.max_iter` | ⚠️ default 3 (plan) |
| verbose | BOOLEAN | `soul_json.verbose` | ⚠️ opcional |
| reasoning | BOOLEAN | `soul_json.reasoning` | ⚠️ opcional |
| inject_date | BOOLEAN | `soul_json.inject_date` | ⚠️ opcional |
| memory | BOOLEAN | `soul_json.memory` | ⚠️ opcional |

**RLS considerations:**
- `agent_catalog` insert: RLS policy `tenant_isolation` evalúa `org_id::text = current_setting('app.org_id', TRUE)`.
- Si_frontend insert directo → `app.org_id` debe estar seteado en la sesión PostgreSQL.
- `agent_templates` global → solo read.

**Índices existentes (004):**
- `idx_agent_catalog_org_role` en `(org_id, role)` WHERE `is_active = TRUE` → cubre búsquedas por org.

**Integridad referencial:**
- `org_id` referencia `organizations(id)` ON DELETE CASCADE — OK.
- No FK externas adicionales.

**Gaps de datos:**
- None. JSONB flexible permite nuevos campos sin migración.

---

## 2️⃣ Análisis de Código (ETAPA 2)

**Componentes nuevos a crear:**

| Archivo | Propósito | Patrón a seguir | Notas |
|---|---|---|---|
| `dashboard/app/(app)/builder/page.tsx` | Página入口 del builder | Siguen `app/(app)/agents/page.tsx` (page + client component) | Estructura: `export default function BuilderPage() { return <BuilderLayout /> }` |
| `dashboard/components/builder/BuilderLayout.tsx` | Split panel 60/40 | Siguen `dashboard/components/flows/FlowHierarchyView.tsx` o cualquier `Card` layout | Layout: izquierda `<BuilderCanvas />`, derecha `<AgentForm />` + botones. Responsive: flex-col en móvil. |
| `dashboard/components/builder/AgentForm.tsx` | Formulario con todos los campos | Siguen `dashboard/components/tickets/CreateTicketForm.tsx` (useState + validación manual) **o** migrar a `react-hook-form` + `zod` | Plan exige Zod → requiere instalación. Sugerencia: usar `useForm` con `zodResolver`. |
| `dashboard/components/builder/BuilderCanvas.tsx` | Contenedor ReactFlow vacío | Siguen `reactflow`官方 ejemplos + `Dashboard` pattern de Next.js | ReactFlow debe ser dynamic import (`next/dynamic`) para evitar SSR. |

**Interfaces TypeScript sugeridas:**
```ts
interface AgentFormData {
  role: string
  goal: string
  backstory: string
  llm_provider: 'groq' | 'openai' | 'anthropic' | 'openrouter'
  llm_model: string
  allowed_tools: string[]
  max_iter: number
  verbose: boolean
  reasoning: boolean
  inject_date: boolean
  memory: boolean
}
```

**Patrones existentes a reutilizar:**
- **Hooks de datos:** `useFlows()` → patrón `useQuery` con `useCurrentOrg`. Para tools: crear `useTools(orgId, source?)`. Templates: `useQuery(['templates'])` → `api.get('/api/templates')`.
- **Supabase inserts:** No hay ejemplo frontend directo. Solo通过 backend API. **Gap**.
- **Validación:** `CreateTicketForm` usa `useState` + validación manual. `RunFlowDialog` usa `useForm` sin zod.  
  → Para Zod: instalar `zod` y definir `AgentFormSchema`.

**Imports correctos (convención):**
- Absolutos: `from '@/components/...'`
- Hooks: `from '@/hooks/useCurrentOrg'`
- API: `from '@/lib/api'`
- UI: `from '@/components/ui/...'`

**Componentes UI disponibles:**
- ✅ `Button`, `Input`, `Textarea`, `Label`, `Select`, `Switch`, `Checkbox`, `Card`, `Badge`, `Skeleton`, `Toast (sonner)`.
- ❌ `MultiSelect` → crear.
- ❌ `Slider` → crear o sustituir por `Input type=number`.

**ReactFlow specifics:**
- Instalación requerida: `npm install reactflow`.
- CSS: `import 'reactflow/dist/style.css'` en `page.tsx` o layout.
- Componentes nodo: `AgentNode`, `TaskNode`, `ToolNode` → se implementan en Paso 07. Paso 04 solo canvas vacío → `ReactFlow` component básico con `defaultNodes=[]`, `defaultEdges=[]`.
- SSR: `dynamic(() => import('reactflow'), { ssr: false })` wrap.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Endpoints consumidos por Paso 4 (UI):**

| Endpoint | Método | Usado en | Auth | Response |
|---|---|---|---|---|
| `GET /api/tools/available` | GET | Tools multi-select | `require_org_id` | `{ tools: ToolInfo[], count }` |
| `GET /api/templates` | GET | TemplatePicker (Paso 05, pero puede cargarse en builder) | None | `{ templates: TemplateInfo[], count }` |
| `POST /api/agents` | **NO EXISTE** | Save Agent | `require_org_id` | `Agent` |
| `GET /api/templates/{id}` | GET | TemplatePicker detalle | None | `TemplateDetailResponse` incluye `soul_json` |

**Contrato para `POST /api/agents` (nuevo, sugerido):**
```python
# src/api/routes/agents.py (ya existe agents.py? Verificar)
class AgentCreate(BaseModel):
    role: str
    soul_json: dict  # contiene goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory
    allowed_tools: list[str] = []
    max_iter: int = 3

@router.post("", response_model=AgentResponse)
async def create_agent(
    payload: AgentCreate,
    org_id: str = Depends(require_org_id),
):
    with TenantClient(org_id) as db:
        agent = db.table("agent_catalog").insert({
            "org_id": org_id,
            "role": payload.role,
            "soul_json": payload.soul_json,
            "allowed_tools": payload.allowed_tools,
            "max_iter": payload.max_iter,
            "is_active": True,
        }).execute()
    return agent.data[0]
```

**Middleware aplicable:** `require_org_id` (extrae `X-Org-ID`). Necesario para `POST /api/agents`.

**Flujo datos:**
1. Frontend: formulario → payload JSON con `soul_json` anidado.
2. `api.post('/api/agents', payload)` → headers: `Authorization: Bearer <token>`, `X-Org-ID: <orgId>`.
3. Backend: valida Pydantic, inserta en `agent_catalog` con RLS filtrando por `org_id`.
4. Retorna `Agent` con `id`, `org_id`, etc.

**RLS保证:**
- backend setea `app.org_id` via `TenantClient` → insert solo permite agents dentro de esa org.
- Frontend directo (sin backend) NO funciona sin `app.org_id` en sesión → **gap**.

**Contratos existentes validados:**
- `GET /api/tools/available` → Tools con `source: "local" | "mcp"`, MCP tools con prefijo `mcp:{server}:{tool}`. Plan: "Tools desde GET /api/tools/available" → OK.
- `GET /api/templates` → Devuelve templates globales sin auth. Plan: TemplatePicker en paso 05, pero builder puede precargar. ✅.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

**Flujo end-to-end ( happy path ):**

1. Usuario accede `/dashboard/app/builder` → `BuilderPage` carga.
2. `BuilderLayout` renderiza: izquierda canvas vacío (ReactFlow), derecha `AgentForm`.
3. `AgentForm` carga tools via `useTools` (`GET /api/tools/available`).
4. Usuario completa campos:
   - role, goal, backstory → requeridos.
   - LLM provider → select. Model → dinámico ( provider→models mapping).
   - Tools → multi-select (múltiples `ToolInfo.name`).
   - Max iterations → slider (number).
   - Toggles → Switch components.
5. Click "Save Agent" → validación Zod → `POST /api/agents` (backend) → insert en `agent_catalog`.
6. Success → toast + limpiar formulario.

**Coherencia arquitectónica:**
- UI stack: Next.js App Router + shadcn/ui + Tailwind → consistente.
- Data fetching: React Query pattern (`useQuery`) → ya usado en `useFlows`, `useTickets`.
- State: `useState` o `useForm` → consistente con `CreateTicketForm`.
- RLS: Tenant isolation → respetado con backend endpoint.
- **Inconsistencia:** plan pide frontend directo; arquitectura actual usa backend endpoints para writes. Inconsistencia **crítica** → ajustar plan o crear endpoint.

**DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: **`fap agents create` CLI command**
- **Qué automatiza:** Crear agentes desde terminal sin UI. Útil para scripting, seeding, DevOps.
- **Tipo:** CLI command (Typer) en `src/cli/commands/agents_create.py`.
- **Cómo se usa:**
  ```bash
  fap agents create --role "Research Agent" --goal "Research topics" --backstory "You are..." --tools "sql_analytical" "event_store" --model "groq/llama-3.3-70b-versatile" --max-iter 5
  ```
- **Impacto:** Reduce fricción en automatizaciones, CI/CD, pruebas. No depende del dashboard.
- **Prioridad:** Tarea 0 (antes de Paso 04 UI) → validar schema y backend antes de UI.

### Herramienta Propuesta: **`fap agents validate` CLI command**
- **Qué automatiza:** Validar `soul_json` de un agente contra esquema (role, goal, backstory obligatorios; max_iter 1-10; tools existen en registry).
- **Tipo:** Validador CLI.
- **Uso:**
  ```bash
  fap agents validate --file agent.json
  ```
- **Impacto:** Previene errores antes de guardar, útil para import/export.

### Herramienta Propuesta: **`useAgentForm` hook + `AgentFormValidator` component**
- **Qué automatiza:** Reutilizar lógica de formulario en múltiples páginas (builder, playground).
- **Tipo:** Custom hook + componente composable.
- **Uso:**
  ```tsx
  const { register, errors, submit } = useAgentForm()
  ```
- **Impacto:** DRY, consistente.

**Gaps de UX:**
- Sin multi-select → UX pobre (checkboxes list).
- Sin slider → UX número input.
- Sin breadcrumbs → orientación usuario (Paso 09).
- ReactFlow SSR crash → usar dynamic import (`dynamic(() => import('reactflow'), { ssr: false })`) → documentar.

---

## 5️⃣ Criterios de Aceptación

✅ **[DATA]** Tabla `agent_catalog` existe con columnas: `role`, `soul_json`, `allowed_tools`, `max_iter`.
✅ **[DATA]** RLS policy `agent_catalog_tenant_isolation` aplica `org_id` desde `current_setting('app.org_id')`.
✅ **[CODE]** `AgentForm.tsx` existe con campos: role, goal, backstory, llm_provider, llm_model, allowed_tools (multi-select), max_iter (number o slider), toggles: verbose, reasoning, inject_date, memory.
✅ **[CODE]** Validación (Zod o manual) bloquea save si role/goal/backstory vacíos.
✅ **[CODE]** `BuilderLayout.tsx` implementa split panel 60/40, responsive mobile column.
✅ **[CODE]** `BuilderCanvas.tsx` renderiza `<ReactFlow />` vacío, minimapa, zoom controls, dynamic import ssr:false.
✅ **[BACKEND]** Endpoint `POST /api/agents` existe (si se elige Opción A) y accepts payload con `soul_json` anidado, inserta correctamente con TenantClient.
✅ **[BACKEND]** `GET /api/tools/available` devuelve tools locales + MCP con `source` y `category`.
✅ **[FULLSTACK]** Usuario puede crear agente y verlo listado en `/agents` (confirmar insert exitoso).
✅ **[DX]** CLI `fap agents create` ejecuta sin errores y crea agente en DB.
⚠️ **[DX]** Zod instalado en frontend (`zod` + `@hookform/resolvers`). *Pendiente añadir*.

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: Insert directo frontend viola RLS | **Alta** | `agent_catalog` RLS requiere `app.org_id` en sesión. Frontend anon key no puede setearlo sin RPC autorizado. | Implementar `POST /api/agents` endpoint con `TenantClient` (Patrón tickets). |
| R2: Multi-select no nativo en Radix | **Media** | Radix `Select` no soporta `multiple`. | Crear componente custom con `DropdownMenu` + `Checkbox` items. Tarea 0 DX. |
| R3: Slider ausente en shadcn/ui | **Baja** | No hay `Slider` en UI components. | Usar `Input type=number` con `min/max` o instalar `@radix-ui/react-slider` + crear componente. |
| R4: LLM model dinámico requiere mapeo | **Media** | Provider→models no expose API. | Hardcodear mapping en frontend desde `config.py` (provider_models = { groq: [...], openai: [...], ...}). |
| R5: ReactFlow SSR break | **Media** | ReactFlow no isomórfico. | Dynamic import con `ssr: false` en `BuilderCanvas`. Loading skeleton previo. |
| R6: Validación Zod no disponible | **Baja** | `zod` no en package.json. | Añadir a dependencies o validación manual simple (if !role...). |

**Riesgos futuro (post-MVP):**
- Performance: `GET /api/tools/available` con cientos de MCP tools → paginación.
- UX: Formulario muy largo → wizard steps.

---

## 7️⃣ Plan de Implementación

**Total estimado:** 13h (D: 1h, C: 4h, B: 2h, F: 3h, DX: 3h)

| # | Tarea | Artefacto | Interfaz exacta / especificación | Patrón a seguir | Etapa | Complejidad | Tiempo | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: instalar reactflow + slider component | `dashboard/package.json` + `dashboard/components/ui/slider.tsx` | `npm install reactflow @radix-ui/react-slider` + `Slider` component shadcn-style | `switch.tsx` (Radix) | DX | Baja | 1h | — | `npm run build` sin errores; `import { Slider }` OK |
| 0b | **DX & Tooling**: multi-select component | `dashboard/components/ui/multi-select.tsx` | `MultiSelect(options: {value:string, label:string}[]): { selected: string[], onToggle: (v:string)=>void }` | `Select` + `Checkbox` + `DropdownMenu` | DX | Media | 2h | — | Demo page render OK |
| 0c | **DX & Tooling**: CLI `fap agents create` | `src/cli/commands/agents_create.py` | `def create_agent(role, goal, backstory, llm_provider, llm_model, tools, max_iter, verbose, reasoning, inject_date, memory):` | `templates_seed.py` (typer) | DX | Media | 2h | — | `fap agents create --help` OK |
| 1 | Página builder入口 | `dashboard/app/(app)/builder/page.tsx` | `export default function BuilderPage() { return <BuilderLayout /> }` | `app/(app)/agents/page.tsx:14` | CODE | Baja | 0.5h | Tarea 0 | `/dashboard/app/builder` carga sin 404 |
| 2 | BuilderLayout split panel | `dashboard/components/builder/BuilderLayout.tsx` | `export function BuilderLayout({ childrenLeft, childrenRight })` o `{ left, right }` | `app/(app)/layout.tsx` flex Split | CODE | Baja | 1h | Tarea 1 | Layout con paneles 60/40, mobile column |
| 3 | AgentForm con Zod | `dashboard/components/builder/AgentForm.tsx` | Campos exactos + `z.object({ role: z.string().min(1), goal: z.string().min(10), backstory: z.string().min(10) })` | `CreateTicketForm.tsx` + `RunFlowDialog.tsx` | CODE | Alta | 3h | Tarea 2, 0b | Form renderiza, validación bloquea submit vacío |
| 4 | BuilderCanvas (ReactFlow) | `dashboard/components/builder/BuilderCanvas.tsx` | `export function BuilderCanvas() { return ( <ReactFlow nodes={[]} edges={[]} onNodesChange... > <Background/><Controls/><MiniMap/> </ReactFlow> ) }` | Ejemplo oficial + dynamic import | CODE | Media | 2h | Tarea 0 | Canvas visible sin crash SSR, controls operativos |
| 5 | Integrar BuilderLayout en page | `dashboard/app/(app)/builder/page.tsx` | Combinar Tareas 1-4: `<BuilderLayout left={<BuilderCanvas/>} right={<AgentForm onSuccess={...}/>}` | — | CODE | Baja | 0.5h | Tareas 1-4 | Página funcional completa |
| 6 | Backend endpoint `POST /api/agents` | `src/api/routes/agents.py` | `@router.post("") async def create_agent(payload:AgentCreate, org_id: str=Depends(require_org_id)) -> AgentResponse:` | `templates.py` + `TenantClient` | BACKEND | Media | 2h | — | `curl -X POST /api/agents` → 201, agente creado |
| 7 | Registrar router agents en main | `src/api/main.py` | `from src.api.routes import agents; app.include_router(agents.router, prefix="/api")` | `main.py:31,112` | BACKEND | Baja | 0.5h | Tarea 6 | `/openapi.json` incluye `/api/agents` |
| 8 | Añadir "Builder" a NavMain | `dashboard/components/nav-main.tsx` | Insert item en `defaultNavItems`: `{ title: 'Builder', url: '/dashboard/app/builder', icon: Wand2 }` | existente nav items | FULLSTACK | Baja | 0.5h | Tarea 5 | Sidebar muestra "Builder" |
| 9 | Breadcrumbs en Builder page | `dashboard/app/(app)/builder/page.tsx` | Usar `Breadcrumb` component: `Dashboard > Builder > New Agent` | `components/ui/breadcrumb.tsx` | FULLSTACK | Media | 1h | Tarea 5 | Ruta cambia → breadcrumb actualiza |
| 10 | E2E test: crear agente | `tests/e2e/test_builder_agent_creation.py` | Test: visit `/builder`, fill form, submit, verify DB row exists via API `GET /api/agents` | Patrón tests existentes | TEST | Alta | 2h | Tareas 1-9 | Test pasa, agente persistido |
| 11 | Unit test: AgentForm validation | `tests/unit/test_agent_form.tsx` | Simulate submit empty → errors; valid payload → calls `api.post` | `test_bundle_export.py` patrón | TEST | Media | 1h | Tarea 3 | Tests pasan |
| 12 | Hook `useAgents` (opcional) | `dashboard/hooks/useAgents.ts` | `export function useAgents(orgId: string) { return useQuery(['agents', orgId], ...) }` | `useFlows.ts` | CODE | Baja | 0.5h | Tarea 6 | Hook disponible |

**Tiempo total: ≈ 13h**

**Ajustes previos:**
1. Instalar dependencias: `npm install reactflow zod @hookform/resolvers @radix-ui/react-slider` (en dashboard).
2. Crear componentes base: `Slider.tsx` (si no se usa input number), `MultiSelect.tsx`.
3. Crear `POST /api/agents` (Tarea 6) **antes** de UI para no bloquear integración.
4. CLI tools (0c) pueden postergarse a paso pos-MVP, pero plan las incluye como DX obligatoria → implementar al menos `fap agents create`.

**Nota sobre plan original:**
Plan omite endpoint backend para save. Discrepancia D4 resuelta con Tarea 6 (crear `POST /api/agents`). Si se insiste en frontend directo, se requiere RPC `set_org_context` + validation middle — no recomendado.

---

## 📌 ENTREGABLE

**Archivo:** `DEVS/IN_PROGRESS/analisis-paso-4-step.md`  
**Contenido:** Este documento (versión final sin markdown extra).  
**Estado:** Listo para revisión.  
**Siguiente:** Implementador ejecuta tareas atómicas en orden, comenzando por Tarea 0 (DX tools + deps) y Tarea 6 (backend endpoint).  

Fin.
