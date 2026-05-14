# 🏛️ Análisis Unificado — Paso 04: Builder Visual — Layout y Formulario de Agente

> **Fase:** `guiAgentGenerator`
> **Paso:** 04 — Página del builder — layout y formulario de agente
> **Rol:** Arquitecto de Sistemas Senior / Unificador
> **Fecha:** 2026-05-14
> **Fuente:** 7 análisis de agentes consolidados
> **`proyecto-config.json`:** Leído ✅

---

## 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| dsp | ✅ 29 items | 5 | ✅ `fap agent create` + `fap agent validate` | ✅ Alta — archivos, líneas, firmas Zod, patrones | 4.5 |
| mm | ✅ 12 items | 4 | ✅ `builder_scaffold.py` | ⚠️ Media — verificación base, idioma mixto italiano/español | 3.0 |
| gif | ✅ 20 items | 7 | ✅ `scaffold:builder` npm + `fap builder scaffold` | ✅ Alta — detecta `@xyflow/react` rename, buen análisis de gaps | 4.0 |
| laguna | ✅ 18 items | 6 | ✅ `scaffold-builder` npm | ⚠️ Media — conciso pero menor profundidad en §2 y §4 | 3.5 |
| step | ✅ 20 items | 6 | ✅ `fap agents create` + validate + `useAgentForm` hook | ✅ **MUY ALTA** — **detecta D4 crítica RLS**, propone `POST /api/agents` | 4.5 |
| x | ⚠️ 17 items | 4 | ✅ `scaffold_builder.py` | ❌ Baja — asume `tools/available` no existe (SÍ existe), asume `form.tsx` existe (NO existe), sin verificación real | 1.5 |
| glm | ✅ 37 items | 6 | ✅ `seed_builder_agent.py` | ✅ Alta — más verificaciones del lote, análisis RLS profundo en `025_agent_catalog_rls_update.sql` | 4.0 |

**Leyenda de Score:**
- **4.5**: Excelente — verificación exhaustiva, discrepancias críticas, DX concreta y táctica, evidencia sólida con archivo:línea
- **4.0**: Muy bueno — amplia verificación, buen análisis, DX válida
- **3.0-3.5**: Aceptable — cubre lo básico, verificación suficiente pero menor profundidad o DX genérica
- **1.5**: Deficiente — múltiples suposiciones erróneas, verificación inexacta

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| D1 | `reactflow` NO instalado en `dashboard/package.json` | TODOS | ✅ `dashboard/package.json` — sin `reactflow` | `npm install reactflow`. gif detecta rename a `@xyflow/react` v12 → por consistencia con plan y mayoría de agentes se usa `reactflow` (v11 estable). Paso 07 migrará si es necesario. |
| D2 | `zod` NO instalado en `dashboard/package.json` | dsp, step, gif, laguna, glm | ✅ `dashboard/package.json` — sin `zod` | `npm install zod`. Plan requiere validación Zod. `@hookform/resolvers` ya instalado (v5.2.2). |
| D3 | Slider component NO existe en `dashboard/components/ui/` | TODOS | ✅ `dashboard/components/ui/` — sin `slider.tsx` | **Usar `Input type="number"` con `min=1 max=10 default=3`** para MVP. `@radix-ui/react-slider` + `slider.tsx` post-MVP. Sin bloqueo funcional. |
| D4 | **CRÍTICA: Save Agent directo frontend viola RLS** | step, glm, gif, laguna | ✅ `004_agent_catalog.sql:22-23` — `USING (org_id::text = current_setting('app.org_id', TRUE))`. `app.org_id` seteado por middleware backend (`middleware.py:66`), NO disponible en Supabase browser client. | **Crear `POST /api/agents` endpoint** con `require_org_id` + `TenantClient`. El plan dice "sin nuevo endpoint" → **EL PLAN ESTÁ EQUIVOCADO**. Código real lo desmiente. Sin este endpoint el Save Agent falla con error RLS 42501. |
| D5 | Multi-select component NO existe | TODOS excepto x | ✅ `dashboard/components/` — sin multi-select | Crear `ToolMultiSelect` custom con `Checkbox` + búsqueda/filtro + badges. Agrupar por `source` (local/mcp). |
| D6 | `@xyflow/react` v12 — rename de `reactflow` | gif | ✅ npm registry — `reactflow` package renamed | Usar `reactflow` (v11) por consistencia con plan. Migración a `@xyflow/react` post-MVP si es necesario. |
| D7 | `soul_json` estructura — campos extra no existen como columnas | glm, step, gif | ✅ `004_agent_catalog.sql:12` — `soul_json JSONB DEFAULT '{}'`. Sin columnas `model`, `verbose`, `reasoning`, etc. | Almacenar en `soul_json` plano: `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}`. JSONB flexible. Sin migración. |
| D8 | `UNIQUE(org_id, role)` → `.insert()` falla en duplicado | dsp | ✅ `004_agent_catalog.sql:17` — `UNIQUE(org_id, role)` | Usar `.upsert()` con `onConflict: 'org_id,role'` desde el endpoint `POST /api/agents`. Permite re-guardar/editar sin error 409. |
| D9 | Nav sidebar sin entrada "Builder" | TODOS | ✅ `nav-main.tsx:43-63` — `defaultNavItems` sin "Builder" | Añadir `{ title: 'Builder', url: '/builder', icon: Wand2 }` a `defaultNavItems`. |
| D10 | LLM Provider → Model mapping no existe | gif, step, glm, dsp | ✅ Sin endpoint ni constante | Mapa estático en `constants.ts` con ≥2 modelos por provider (groq, openai, anthropic, openrouter). Post-MVP: endpoint `GET /api/llm/models`. |
| D11 | `agent_catalog` no tiene columna `model` — types.ts:96 sí | glm, gif | ✅ `004_agent_catalog.sql:6-17` sin columna `model`. `types.ts:96` la declara como opcional. | `model` en types.ts es campo enriquecido/derivado. Para formulario: `llm_model` va en `soul_json.llm_model`. No migrar. |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo del paso:** Construir la página `/dashboard/app/builder` con layout split 60/40 (canvas ReactFlow izquierda + formulario de agente derecha). El formulario replica todos los campos del Agent de CrewAI y guarda en `agent_catalog` vía nuevo endpoint `POST /api/agents`.

**Corrección crítica al plan:** El plan dice "Save Agent → guarda en agent_catalog vía Supabase (directo desde frontend, sin nuevo endpoint)". **ESTO ES INCORRECTO.** La RLS `agent_catalog_tenant_isolation` requiere `app.org_id` en sesión PostgreSQL, variable que solo setea el middleware backend (`middleware.py:66`) al recibir header `X-Org-ID`. El frontend browser client NO puede setear esta variable. **Se requiere `POST /api/agents`** con `require_org_id` + `TenantClient`. Detectado por step y confirmado por glm/gif/laguna.

**Decisión DX:** Herramienta **`fap agent create`** CLI como Tarea 0 — valida el flujo backend antes de construir la UI. Permite crear agentes desde terminal sin dashboard. Consolida las propuestas de dsp (CLI) y step (CLI + validate). Post-MVP: `fap agent validate`.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Usuario navega a `/builder` desde sidebar
2. `BuilderPage` renderiza `BuilderLayout` con split 60/40
3. Panel izquierdo: `BuilderCanvas` — contenedor ReactFlow vacío (placeholder para Paso 07)
4. Panel derecho: `AgentForm` — formulario con react-hook-form + zod
5. `AgentForm` carga tools vía `useQuery(GET /api/tools/available)`
6. Usuario completa: Role, Goal, Backstory, LLM Provider, LLM Model, Tools (multi-select), Max Iterations (1-10, default 3), Toggles (Verbose, Reasoning, Inject Date, Memory)
7. Zod valida en submit: role, goal, backstory requeridos (min 1 char)
8. Zod rechaza → errores inline en cada campo
9. Zod OK → construye soul_json + payload → `api.post('/api/agents', payload)`
10. Backend `POST /api/agents` → valida Pydantic → `TenantClient` inserta en `agent_catalog` con RLS
11. Éxito → toast "Agent saved" + limpiar formulario (`form.reset()`)
12. Error → toast con mensaje (duplicado: "Ya existe un agente con ese rol", RLS: "Sin permisos")
13. Usuario hace clic en "Clear" → formulario se resetea a defaults

### Edge Cases MVP

- **Role duplicado:** `UNIQUE(org_id, role)` → endpoint detecta error 23505 → 409 "Role already exists in this organization"
- **Tools endpoint caído:** `GET /api/tools/available` falla → mostrar skeleton + botón "Retry". Permite guardar agente sin tools.
- **Org no seleccionada:** `useCurrentOrg().orgId` es null → deshabilitar formulario + mensaje "Select an organization first"
- **Save sin conexión:** Supabase/API inaccesible → toast "Failed to save agent. Check your connection."
- **Formulario sucio + navegación:** `window.confirm` antes de abandonar página con cambios sin guardar
- **max_iter fuera de rango:** Zod `z.number().int().min(1).max(10)` rechaza valores <1 o >10

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. `D:\Develop\Personal\FluxAgentPro-v2\dashboard\package.json`
- **Tipo:** Modificación
- **Descripción:** Añadir dependencias: `reactflow`, `zod`
- **Instalación:** `npm install reactflow zod`

---

#### 2. `D:\Develop\Personal\FluxAgentPro-v2\dashboard\app\(app)\builder\page.tsx` (NUEVO)
- **Tipo:** Creación
- **Descripción:** Página entry del builder. `'use client'`. Orquesta `BuilderLayout`.
- **Interfaz:** `export default function BuilderPage()`
- **Patrón:** `dashboard/app/(app)/agents/page.tsx:14-29`

---

#### 3. `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\BuilderLayout.tsx` (NUEVO)
- **Tipo:** Creación
- **Descripción:** Layout split panel flex. Izquierda `BuilderCanvas` (60%), derecha `AgentForm` (40%). Responsive: stack vertical en mobile.
- **Interfaz:** `export function BuilderLayout()`
- **Patrón:** Grid/flex con Tailwind `lg:grid-cols-[60%_40%]`

---

#### 4. `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\AgentForm.tsx` (NUEVO)
- **Tipo:** Creación
- **Descripción:** Formulario completo de agente con react-hook-form + zodResolver. 11 campos. Carga tools desde API. Guarda vía `api.post('/api/agents', ...)`.
- **Interfaces clave:**

```typescript
// Zod schema
const agentFormSchema = z.object({
  role: z.string().min(1, "Role is required"),
  goal: z.string().min(1, "Goal is required"),
  backstory: z.string().min(1, "Backstory is required"),
  llmProvider: z.enum(["groq", "openai", "anthropic", "openrouter"]).default("groq"),
  llmModel: z.string().default("llama-3.1-70b-versatile"),
  alllowedTools: z.array(z.string()).default([]),
  maxIter: z.number().int().min(1).max(10).default(3),
  verbose: z.boolean().default(false),
  reasoning: z.boolean().default(false),
  injectDate: z.boolean().default(false),
  memory: z.boolean().default(false),
})

type AgentFormData = z.infer<typeof agentFormSchema>

// Component
export function AgentForm({
  onSave,
  onClear,
  initialValues,
}: {
  onSave?: (data: AgentFormData) => Promise<void>
  onClear?: () => void
  initialValues?: Partial<AgentFormData>
})
```

- **Campos UI:**
  | Campo | Componente | Validación |
  |---|---|---|
  | Role | `<Input />` | `z.string().min(1)` |
  | Goal | `<Textarea />` | `z.string().min(1)` |
  | Backstory | `<Textarea />` | `z.string().min(1)` |
  | LLM Provider | `<Select />` | `z.enum([...])` |
  | LLM Model | `<Select />` dinámico | `z.string()` |
  | Tools | `<ToolMultiSelect />` | `z.array(z.string())` |
  | Max Iterations | `<Input type="number" min=1 max=10 />` | `z.number().int().min(1).max(10)` |
  | Verbose | `<Switch />` | `z.boolean()` |
  | Reasoning | `<Switch />` | `z.boolean()` |
  | Inject Date | `<Switch />` | `z.boolean()` |
  | Memory | `<Switch />` | `z.boolean()` |

- **Patrón:** `RunFlowDialog.tsx:31` (useForm) + `agents/page.tsx:17` (useQuery para tools)

---

#### 5. `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\ToolMultiSelect.tsx` (NUEVO)
- **Tipo:** Creación
- **Descripción:** Componente multi-select con checkboxes, búsqueda/filtro, badges removibles, agrupación por source (local/mcp).
- **Interfaz:** `export function ToolMultiSelect({ options, values, onChange }: { options: {value: string, label: string, source: string}[]; values: string[]; onChange: (v: string[]) => void })`
- **Patrón:** `Command` + `Popover` + `Checkbox` de shadcn/ui

---

#### 6. `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\BuilderCanvas.tsx` (NUEVO)
- **Tipo:** Creación
- **Descripción:** Contenedor ReactFlow vacío. Placeholder para Paso 07. `dynamic import` con `ssr: false`.
- **Interfaz:** `export function BuilderCanvas()`
- **Patrón:** `next/dynamic(() => import('reactflow'), { ssr: false })` + `EmptyState`
- **Contenido:** `<ReactFlow nodes={[]} edges={[]} fitView><Background /><Controls /><MiniMap /></ReactFlow>`

---

#### 7. `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\nav-main.tsx` (MODIFICAR)
- **Tipo:** Modificación
- **Descripción:** Añadir entrada "Builder" a `defaultNavItems`.
- **Cambio exacto:** Añadir `{ title: 'Builder', url: '/builder', icon: Wand2 }` al array `defaultNavItems` (línea ~63).

---

#### 8. `D:\Develop\Personal\FluxAgentPro-v2\dashboard\lib\constants.ts` (MODIFICAR)
- **Tipo:** Modificación
- **Descripción:** Añadir mapa estático `PROVIDER_MODELS` con ≥2 modelos por provider.
```typescript
export const PROVIDER_MODELS: Record<string, string[]> = {
  groq: ["llama-3.1-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
  openai: ["gpt-4o", "gpt-4o-mini"],
  anthropic: ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
  openrouter: ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"],
}
```

---

#### 9. `D:\Develop\Personal\FluxAgentPro-v2\src\api\routes\agents.py` (NUEVO — backend)
- **Tipo:** Creación
- **Descripción:** Endpoint `POST /api/agents` para crear agentes. Usa `require_org_id` + `TenantClient` para garantizar RLS.
- **Interfaces clave:**
```python
from pydantic import BaseModel

class AgentCreate(BaseModel):
    role: str
    soul_json: dict  # {goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}
    allowed_tools: list[str] = []
    max_iter: int = 3

class AgentResponse(BaseModel):
    id: str
    org_id: str
    role: str
    soul_json: dict
    allowed_tools: list[str]
    max_iter: int
    created_at: str

@router.post("", response_model=AgentResponse)
async def create_agent(
    payload: AgentCreate,
    org_id: str = Depends(require_org_id),
):
    # Usar TenantClient para set app.org_id en sesión
    with TenantClient(org_id) as db:
        agent = db.table("agent_catalog").upsert({
            "org_id": org_id,
            "role": payload.role,
            "soul_json": payload.soul_json,
            "allowed_tools": payload.allowed_tools,
            "max_iter": payload.max_iter,
            "is_active": True,
        }, on_conflict="org_id,role").execute()
    return agent.data[0]
```
- **Patrón:** `src/api/routes/templates.py:54` (list) + `src/db/session.py` TenantClient

---

#### 10. `D:\Develop\Personal\FluxAgentPro-v2\src\api\main.py` (MODIFICAR)
- **Tipo:** Modificación
- **Descripción:** Registrar router `agents`.
- **Cambio exacto:** `from src.api.routes import agents` (línea ~31) + `app.include_router(agents.router, prefix="/api")` (línea ~112)
- **Patrón:** `main.py:31,112` — igual que `tools`, `templates`

---

#### 11. `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\agent_create.py` (NUEVO — Tarea 0 DX)
- **Tipo:** Creación
- **Descripción:** CLI `fap agent create` para crear agentes desde terminal. Ver §DX & Tooling abajo.
- **Patrón:** `src/cli/commands/templates_seed.py`

---

#### 12. `D:\Develop\Personal\FluxAgentPro-v2\src\cli\main.py` (MODIFICAR)
- **Tipo:** Modificación
- **Descripción:** Registrar sub-app `agent` en CLI.
- **Cambio exacto:** `from src.cli.commands import agent_create` + `app.add_typer(agent_app, name="agent")`
- **Patrón:** `main.py:33,58` — igual que `templates_app`

---

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap agent create
- **Qué automatiza:** Crear un agente desde CLI sin abrir el dashboard. El usuario define role/goal/backstory vía flags y el comando inserta en agent_catalog vía POST /api/agents. Útil para CI/CD, scripts de setup, power users.
- **Tipo:** CLI command (Typer sub-app de `fap`)
- **Ubicación:** D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\agent_create.py
- **Cómo se usa:**
  uv run python -m src.cli.main agent create \
    --role "Code Reviewer" \
    --goal "Review pull requests for security issues" \
    --backstory "Senior security engineer with 10 years experience" \
    --tools "code_analysis" "security_scan" \
    --max-iter 5 \
    --org-id "550e8400-e29b-41d4-a716-446655440000" \
    --llm-provider groq \
    --llm-model "llama-3.1-70b-versatile" \
    --verbose --inject-date
- **Impacto para el usuario final:** Deja de abrir dashboard + formulario para crear agentes. Un comando los crea. Validación del flujo backend antes de construir la UI (dogfooding).
- **El implementador DEBE usarla** para validar el endpoint POST /api/agents antes de construir el formulario. `fap agent create --dry-run` para ver payload sin insertar.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **`POST /api/agents` (NUEVO) — corrección al plan:** El plan dice "guardar directo desde frontend vía Supabase sin nuevo endpoint". **ESTO ES TÉCNICAMENTE INCORRECTO.** La RLS `agent_catalog_tenant_isolation` usa `current_setting('app.org_id', TRUE)` que solo setea el middleware backend. El frontend browser client no puede setear variables de sesión PostgreSQL. Se requiere endpoint backend con `TenantClient`. Sin este endpoint, el Save Agent falla con error 42501.

2. **`reactflow` (v11), no `@xyflow/react` (v12):** El plan especifica `reactflow`. `@xyflow/react` v12 cambió API drásticamente. Usar v11 estable por consistencia. Migración a v12 en Paso 07 si es necesario.

3. **`Input type="number"` para max_iter, no Slider:** El componente `Slider` no existe en shadcn/ui actual. `Input type="number"` con `min=1 max=10` provee la misma funcionalidad sin dependencia extra (`@radix-ui/react-slider`). Slider visual post-MVP.

4. **`soul_json` plano, no anidado con `config` sub-objeto:** Estructura plana `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}`. Consistente con cómo `agents/page.tsx:62` ya accede a `soul_json` como `Record<string, string>`. Sin anidación innecesaria.

5. **Upsert, no insert:** `UNIQUE(org_id, role)` hace que `.insert()` falle en duplicado. `.upsert()` con `onConflict: 'org_id,role'` permite crear y re-guardar sin error 409.

6. **Multi-select custom, no librería externa:** `ToolMultiSelect` custom con `Checkbox` + `Command` (cmdk) + badges. Mismo stack shadcn/ui. Sin dependencia extra.

7. **LLM models estáticos en `constants.ts`:** Sin endpoint para listar modelos por provider en MVP. Mapa estático con ≥2 modelos/provider. Post-MVP: `GET /api/llm/models?provider=`.

8. **Nav sidebar "Builder" en Paso 04, no en Paso 09:** La ruta `/builder` debe ser accesible desde el momento en que existe. Añadir entrada en sidebar ahora.

---

## 5️⃣ Criterios de Aceptación MVP

### DATA
- [ ] `agent_catalog` recibe row con `org_id`, `role`, `soul_json {goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}`, `allowed_tools`, `max_iter`
- [ ] `UNIQUE(org_id, role)` se respeta vía upsert — no error 409 en re-guardado
- [ ] RLS `agent_catalog_tenant_isolation` se cumple vía `TenantClient` en endpoint

### CODE
- [ ] `AgentForm.tsx` renderiza 11 campos con react-hook-form + zodResolver
- [ ] Zod rechaza submit sin role, goal, o backstory con error inline
- [ ] Zod rechaza max_iter <1 o >10
- [ ] `AgentForm` carga tools desde `GET /api/tools/available` vía `useQuery`
- [ ] LLM Provider select cambia dinámicamente opciones de LLM Model
- [ ] `ToolMultiSelect` muestra tools agrupadas por source (local/mcp) con búsqueda
- [ ] `BuilderCanvas` renderiza ReactFlow vacío con `dynamic import` + `ssr: false`
- [ ] `BuilderLayout` muestra split 60/40; responsive: stack vertical en mobile
- [ ] Todos los componentes tienen `'use client'` directive
- [ ] Imports usan `@/*` path alias

### BACKEND
- [ ] `POST /api/agents` acepta `{role, soul_json, allowed_tools, max_iter}` con `require_org_id`
- [ ] `POST /api/agents` inserta/upsert en `agent_catalog` vía `TenantClient`
- [ ] `POST /api/agents` retorna 409 en `UNIQUE(org_id, role)` conflict con mensaje claro
- [ ] Router `agents` registrado en `main.py` con prefijo `/api`
- [ ] `GET /openapi.json` incluye `/api/agents`

### FULLSTACK
- [ ] Ruta `/builder` accesible y renderiza layout + formulario
- [ ] "Save Agent" → `api.post('/api/agents', ...)` → agente persiste en `agent_catalog`
- [ ] Agente creado aparece en lista de `/agents` (confirmar SELECT)
- [ ] "Clear" resetea formulario a valores default
- [ ] Errores de red/validación se muestran como toast (sonner)
- [ ] Sidebar muestra "Builder" con ícono `Wand2` → navega a `/builder`

### DX
- [ ] `fap agent create` ejecuta sin errores y crea agente en Supabase
- [ ] `fap agent create --help` muestra todos los flags
- [ ] `fap agent create --dry-run` muestra payload sin insertar

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| **0** | **DX & Tooling:** `fap agent create` CLI + registrar sub-app `agent` en `main.py` | Media | 1.5h | Ninguna |
| 1 | Instalar dependencias frontend: `reactflow`, `zod` | Baja | 0.2h | Ninguna |
| 2 | Crear `POST /api/agents` endpoint + modelo Pydantic | Alta | 1.5h | Ninguna |
| 3 | Registrar router `agents` en `src/api/main.py` | Baja | 0.2h | Tarea 2 |
| 4 | Crear `ToolMultiSelect` component | Media | 1h | Tarea 1 |
| 5 | Añadir `PROVIDER_MODELS` constante a `constants.ts` | Baja | 0.2h | Ninguna |
| 6 | Crear `AgentForm.tsx` con react-hook-form + zod + useQuery tools + save vía `api.post` | Alta | 2.5h | Tareas 1, 4, 5 |
| 7 | Crear `BuilderCanvas.tsx` (ReactFlow placeholder, dynamic import ssr:false) | Media | 1h | Tarea 1 |
| 8 | Crear `BuilderLayout.tsx` (split 60/40 responsive) | Baja | 0.5h | Tareas 6, 7 |
| 9 | Crear `builder/page.tsx` (orquesta BuilderLayout) | Baja | 0.3h | Tarea 8 |
| 10 | Añadir "Builder" a `nav-main.tsx` sidebar | Baja | 0.2h | Tarea 9 |
| 11 | Validar flujo end-to-end: CLI → DB → UI → save → verify | Media | 0.5h | Tareas 0-10 |
| **TOTAL** | | | **9.1h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap agent create` para validar el endpoint `POST /api/agents` antes de construir la UI (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1:** Insert directo frontend viola RLS | **Alta** | `app.org_id` no disponible en browser client. RLS rechaza INSERT sin `current_setting('app.org_id')`. | Implementar `POST /api/agents` con `TenantClient` (Tarea 2). **SI NO SE IMPLEMENTA, EL SAVE AGENT NO FUNCIONA.** |
| **R2:** ReactFlow SSR crash en Next.js App Router | **Alta** | ReactFlow usa `window`/`document`/`ResizeObserver`. App Router ejecuta componente en servidor por defecto. | `next/dynamic(() => import(...), { ssr: false })` en `BuilderCanvas`. Loading skeleton mientras carga. |
| **R3:** `showdown` `@hookform/resolvers` v5 + `zod` incompatibilidad | **Media** | `@hookform/resolvers` v5.2.2 requiere `zod` como peer dependency. Versión exacta no especificada. | `npm install zod@latest`. Si falla: usar `zod@3.23`. |
| **R4:** ToolMultiSelect UX pobre con 20+ tools | **Media** | Sin componente multi-select nativo en Radix. Checkboxes en scroll largo es incómodo. | Implementar búsqueda/filtro + agrupación por source (local/mcp). Post-MVP: `Command` combobox. |
| **R5:** LLM model mapping desactualizado | **Baja** | Providers cambian modelos frecuentemente. Mapa estático en frontend se desfasa. | Documentar en `constants.ts` con comentario de actualización. Post-MVP: endpoint `GET /api/llm/models?provider=`. |
| **R6:** `UNIQUE(org_id, role)` error poco claro | **Baja** | Supabase retorna error genérico. Usuario no entiende "duplicate key". | Catch error code 23505 en endpoint → 409 con mensaje "Agent with role '{role}' already exists". Frontend muestra toast amigable. |
| **R7:** `fap agent create` CLI se usa sin org_id | **Baja** | Flag `--org-id` es opcional pero requerido para insert. | Validar en CLI: si `--org-id` no se provee, mostrar error "org_id is required" + help text. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | `POST /api/agents` con payload válido | `{"role":"Test","soul_json":{"goal":"T","backstory":"T"},"allowed_tools":[],"max_iter":3}` + `X-Org-ID` | 200, agente creado con `id` UUID |
| TP-2 | `POST /api/agents` sin role | `{"soul_json":{"goal":"T","backstory":"T"}}` | 422 Validation Error |
| TP-3 | `POST /api/agents` sin X-Org-ID | payload válido sin header | 400 "X-Org-ID header required" |
| TP-4 | `POST /api/agents` role duplicado (upsert) | mismo role dos veces, misma org | 200 en ambas (upsert actualiza), segunda llamada actualiza registro existente |
| TP-5 | `GET /api/tools/available` responde | `?source=local` | 200, `{tools: [...], count: N}`, tools con `source: "local"` |
| TP-6 | `AgentForm` submit sin role/goal/backstory | campos vacíos, clic Save | Zod errors inline: "Role is required", "Goal is required", "Backstory is required" |
| TP-7 | `AgentForm` submit con max_iter=15 | max_iter > 10, clic Save | Zod error: "max_iter must be ≤ 10" |
| TP-8 | `BuilderCanvas` render sin crash SSR | visitar `/builder` | Canvas visible, ReactFlow montado, minimapa y controles de zoom operativos |
| TP-9 | `fap agent create` CLI con flags mínimos | `--role Test --goal T --backstory T --org-id <uuid>` | Agente creado en DB, verificable con `SELECT * FROM agent_catalog WHERE role='Test'` |
| TP-10 | Sidebar navega a `/builder` | clic en "Builder" en sidebar | Navegación correcta, layout 60/40 visible |

**Comando para ejecutar tests:**
```
uv run pytest tests/ -v --timeout=60
```

---

> **Métrica de Calidad del FINAL:**
> | Métrica | Estado |
> |---|---|
> | `proyecto-config.json` leído | ✅ |
> | Discrepancias consolidadas con resolución | ✅ 11/11 |
> | Correcciones al plan documentadas | ✅ D4 (RLS → endpoint) + D1-D11 |
> | Propuesta DX incluida en §3 y Tarea 0 en §6 | ✅ `fap agent create` |
> | Criterio DX en §5 | ✅ |
> | Secciones completadas | ✅ 9 secciones (0-8) |
> | Casos de testing | ✅ 10 casos |
> | Tiempo estimado por tarea | ✅ 100% |
