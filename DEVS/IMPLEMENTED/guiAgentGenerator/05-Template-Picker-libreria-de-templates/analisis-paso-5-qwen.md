# Análisis Técnico — Paso 05: Template Picker

**Agente:** qwen
**Fecha:** 2026-05-14
**Paso:** 05 — Template Picker (librería de templates)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql:10` | ✅ | Mig 030, línea 10-21 |
| 2 | Columna `name TEXT NOT NULL` | `030_agent_templates.sql:12` | ✅ | name TEXT NOT NULL |
| 3 | Columna `description TEXT` | `030_agent_templates.sql:13` | ✅ | description TEXT |
| 4 | Columna `category TEXT NOT NULL` | `030_agent_templates.sql:14` | ✅ | category TEXT NOT NULL |
| 5 | Columna `soul_json JSONB` | `030_agent_templates.sql:15` | ✅ | soul_json JSONB NOT NULL DEFAULT '{}' |
| 6 | Columna `suggested_tools TEXT[]` | `030_agent_templates.sql:16` | ✅ | suggested_tools TEXT[] DEFAULT '{}' |
| 7 | Columna `max_iter INTEGER` | `030_agent_templates.sql:17` | ✅ | max_iter INTEGER DEFAULT 5 |
| 8 | Columna `is_system BOOLEAN` | `030_agent_templates.sql:18` | ✅ | is_system BOOLEAN DEFAULT FALSE |
| 9 | Endpoint `GET /api/templates` | `src/api/routes/templates.py:54-67` | ✅ | list_templates() con filtro ?category= |
| 10 | Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:70-83` | ✅ | get_template() con maybe_single() |
| 11 | Modelo `TemplateInfo` | `src/api/routes/templates.py:25-33` | ✅ | id, name, description, category, suggested_tools, max_iter, is_system, created_at |
| 12 | Modelo `TemplateListResponse` | `src/api/routes/templates.py:36-38` | ✅ | templates: List[TemplateInfo], count: int |
| 13 | Modelo `TemplateDetailResponse` | `src/api/routes/templates.py:41-51` | ✅ | Incluye soul_json: Dict[str, Any] |
| 14 | `AgentForm` existe | `dashboard/components/builder/AgentForm.tsx` | ✅ | 11 campos, react-hook-form + zod, props: onSave, onClear, initialValues |
| 15 | `BuilderLayout` existe | `dashboard/components/builder/BuilderLayout.tsx` | ✅ | Split 60/40, renderiza AgentForm sin initialValues |
| 16 | `BuilderCanvas` placeholder | `dashboard/components/builder/BuilderCanvas.tsx:39` | ✅ | Texto "Placeholder for Step 07" |
| 17 | `api.get()` helper | `dashboard/lib/api.ts:55-56` | ✅ | fapFetch con auth + X-Org-ID |
| 18 | `TemplatePicker.tsx` NO existe | `ls dashboard/components/builder/` | ✅ | No en directorio — crear desde cero |
| 19 | Seed 8 templates | `src/cli/commands/templates_seed.py:32-137` | ✅ | 8 templates: Research, Development(x2), Support, General(x4) |
| 20 | `card.tsx` UI component | `dashboard/components/ui/card.tsx` | ✅ | Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter disponibles |
| 21 | `badge.tsx` UI component | `dashboard/components/ui/badge.tsx` | ✅ | Badge con variant default/secondary/destructive/outline |
| 22 | `scroll-area.tsx` UI component | `dashboard/components/ui/scroll-area.tsx` | ✅ | ScrollArea + ScrollBar disponibles |

**Discrepancias encontradas:**

1. **D1 — `TemplateInfo` no incluye `soul_json` ni campos necesarios para pre-llenado**: El modelo `TemplateInfo` (lista) omite `soul_json`, `goal`, `backstory`. El plan dice "rellena el formulario" pero la lista no tiene datos suficientes. **Resolución:** TemplatePicker usa `GET /api/templates` para cards + `GET /api/templates/{id}` al hacer clic "Use Template" para obtener soul_json completo.

2. **D2 — `BuilderLayout` no maneja estado de template seleccionado**: `BuilderLayout.tsx:15` renderiza `<AgentForm />` sin props. El plan requiere que TemplatePicker rellene AgentForm. **Resolución:** BuilderLayout debe agregar estado `useState<TemplateDetail | null>` y pasarlo como `initialValues` a AgentForm.

3. **D3 — Categorías del plan vs seed real**: Plan dice chips: "Research, Development, Support, General". Seed real tiene exactamente esas 4 categorías. Coincide. Sin discrepancia.

4. **D4 — `soul_json` del seed incluye `role` pero AgentForm usa campo `role` separado**: En `templates_seed.py:38`, el soul_json contiene `"role": "Research Specialist"`. Pero AgentForm tiene `role` como campo independiente del soul_json (línea 30 del schema). **Resolución:** Al mapear template → initialValues, extraer `soul_json.role` → `role`, `soul_json.goal` → `goal`, `soul_json.backstory` → `backstory`, `soul_json.llm_provider` → `llmProvider`, etc.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas tocadas:** `agent_templates` (solo lectura)

- Schema: ya existe (mig 030). Sin cambios.
- Integridad referencial: tabla global sin FK. Sin impacto.
- RLS: SELECT authenticated — usuario logueado lee. Sin escritura desde frontend.
- Índices: `idx_agent_templates_category` existe — filtro optimizado.
- Tipos: `soul_json JSONB` contiene `{role, goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}` según seed real.

**Flujo datos:**
```
GET /api/templates → TemplateInfo[] (sin soul_json)
  → User clic "Use Template"
    → GET /api/templates/{id} → TemplateDetailResponse (con soul_json)
      → Mapear soul_json → AgentForm initialValues
```

**Impacto:** Ninguno en datos existentes. Solo lectura.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componente nuevo: `TemplatePicker.tsx`

**Firma:**
```tsx
interface TemplatePickerProps {
  onSelect: (template: TemplateDetail) => void
}
export function TemplatePicker({ onSelect }: TemplatePickerProps)
```

**Dependencias:**
- `@tanstack/react-query` — `useQuery`
- `@/lib/api` — `api.get()`
- `@/components/ui/button` — Button
- `@/components/ui/card` — Card, CardHeader, CardTitle, CardDescription, CardContent
- `@/components/ui/input` — Input (búsqueda)
- `@/components/ui/badge` — Badge (categoría)
- `@/components/ui/scroll-area` — ScrollArea
- `@/components/shared/LoadingSpinner` — LoadingSpinner
- `@/components/ui/skeleton` — Skeleton
- `lucide-react` — Search, X, BookOpen (iconos)

**Estado interno:**
- `search: string` — texto búsqueda
- `selectedCategory: string | null` — filtro categoría
- `useQuery` para `GET /api/templates`

**Lógica:**
1. Carga templates vía `useQuery({ queryKey: ['templates'], queryFn: () => api.get('/api/templates') })`
2. Deriva categorías únicas de `templates.map(t => t.category)`
3. Filtra por `search` (match en name, description) y `selectedCategory`
4. Renderiza grid de cards con: name, description, category badge, suggested_tools count
5. Cada card tiene botón "Use Template" → llama `onSelect(template)` con template seleccionado

### Tipo `TemplateDetail` (nuevo, en archivo o inline)

```tsx
interface TemplateDetail {
  id: string
  name: string
  description: string | null
  category: string
  soul_json: Record<string, unknown>
  suggested_tools: string[]
  max_iter: number
  is_system: boolean
}
```

### Modificación: `BuilderLayout.tsx`

**Cambios:**
- Agregar `useState<TemplateDetail | null>` para template seleccionado
- Agregar función `handleSelectTemplate` que mapea `TemplateDetail.soul_json` → `AgentFormData` parcial
- Pasar `initialValues={mappedValues}` a `<AgentForm>`
- Agregar botón "Templates" que muestra/oculta TemplatePicker (panel superior o modal)

**Mapeo soul_json → AgentFormData:**
```tsx
function mapTemplateToFormValues(template: TemplateDetail): Partial<AgentFormData> {
  const soul = template.soul_json as Record<string, unknown>
  return {
    role: (soul.role as string) ?? '',
    goal: (soul.goal as string) ?? '',
    backstory: (soul.backstory as string) ?? '',
    llmProvider: (soul.llm_provider as AgentFormData['llmProvider']) ?? 'groq',
    llmModel: (soul.llm_model as string) ?? 'llama-3.1-70b-versatile',
    allowedTools: template.suggested_tools ?? [],
    maxIter: template.max_iter ?? 3,
    verbose: (soul.verbose as boolean) ?? false,
    reasoning: (soul.reasoning as boolean) ?? false,
    injectDate: (soul.inject_date as boolean) ?? false,
    memory: (soul.memory as boolean) ?? false,
  }
}
```

### Patrones de referencia:

| Artefacto | Patrón a seguir | Archivo referencia |
|---|---|---|
| TemplatePicker grid | Cards con loading/error states | `ToolMultiSelect.tsx` — patrón loading + error + retry |
| Búsqueda + filtro | useMemo para filtrado | `ToolMultiSelect.tsx:42-49` — filtered useMemo |
| BuilderLayout con estado | useState + callback a hijo | `AgentForm.tsx:62-87` — useForm + initialValues pattern |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Sin cambios backend.** Paso 05 es puramente frontend.

**Endpoints consumidos (ya existentes):**
| Endpoint | Archivo | Uso en paso 05 |
|---|---|---|
| `GET /api/templates` | `src/api/routes/templates.py:54-67` | Lista templates para cards |
| `GET /api/templates/{id}` | `src/api/routes/templates.py:70-83` | Detalle con soul_json al seleccionar |

**Contratos:**
- `TemplateListResponse`: `{ templates: TemplateInfo[], count: number }`
- `TemplateDetailResponse`: `{ id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at }`

**Error handling:**
- 404 si template no existe (manejado por backend)
- Network error → mostrar estado error en UI (patrón ToolMultiSelect)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
┌─────────────────────────────────────────────────────────────┐
│  Builder (/builder)                                         │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │  BuilderCanvas      │  │  BuilderLayout               │  │
│  │  (ReactFlow empty)  │  │  ┌────────────────────────┐  │  │
│  │                     │  │  │ [📚 Templates] button  │  │  │
│  │                     │  │  ├────────────────────────┤  │  │
│  │                     │  │  │ AgentForm              │  │  │
│  │                     │  │  │ - role                 │  │  │
│  │                     │  │  │ - goal                 │  │  │
│  │                     │  │  │ - backstory            │  │  │
│  │                     │  │  │ - llm provider/model   │  │  │
│  │                     │  │  │ - tools                │  │  │
│  │                     │  │  │ - toggles              │  │  │
│  │                     │  │  │ - Save / Clear         │  │  │
│  │                     │  │  └────────────────────────┘  │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ TemplatePicker (modal/panel al clic Templates)         │ │
│  │ [🔍 Buscar...]  [Research] [Development] [Support]... │ │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐                │ │
│  │ │Research  │ │Code      │ │Data      │                │ │
│  │ │Agent     │ │Reviewer  │ │Analyst   │                │ │
│  │ │desc...   │ │desc...   │ │desc...   │                │ │
│  │ │[Research]│ │[Develop] │ │[Develop] │                │ │
│  │ │[Use]     │ │[Use]     │ │[Use]     │                │ │
│  │ └──────────┘ └──────────┘ └──────────┘                │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

Clic "Use Template" → GET /api/templates/{id} → soul_json → AgentForm relleno
```

### Coherencia

- ✅ Templates API existe y funciona (paso 03)
- ✅ AgentForm acepta `initialValues` (ya implementado)
- ✅ BuilderLayout necesita modificación mínima (agregar estado + botón)
- ✅ soul_json del seed tiene estructura compatible con AgentForm campos

### DX & Tooling

### Herramienta Propuesta: `fap templates preview`
- **Qué automatiza:** Ver templates disponibles + su soul_json completo desde terminal sin abrir dashboard. Permite validar que templates están bien configurados antes de usarlos en builder.
- **Tipo:** CLI command
- **Cómo se usa:** `fap templates preview` (lista compacta) | `fap templates preview --detail <name>` (soul_json completo)
- **Impacto para usuario final:** Desarrolladores/admins verifican templates sin consumir UI. Setup rápido de validación.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Endpoint GET /api/templates devuelve ≥8 templates con categorías válidas
✅ [DATA] Endpoint GET /api/templates/{id} devuelve soul_json completo con role, goal, backstory
✅ [CODE] Componente TemplatePicker.tsx existe y renderiza grid de cards
✅ [CODE] TemplatePicker carga templates desde API real (no mock)
✅ [CODE] Búsqueda por nombre filtra cards en tiempo real
✅ [CODE] Filtro por categoría (chips) funciona — muestra solo templates de categoría seleccionada
✅ [CODE] Botón "Use Template" dispara callback onSelect con template completo
✅ [CODE] BuilderLayout maneja estado de template seleccionado
✅ [CODE] AgentForm se rellena con valores del template al seleccionar
✅ [FULLSTACK] Flujo completo: clic Templates → ver cards → buscar/filtrar → Use Template → formulario relleno → Save Agent
✅ [FULLSTACK] Estado de carga visible mientras templates cargan
✅ [FULLSTACK] Estado de error manejado con opción retry
✅ [DX] CLI `fap templates preview` ejecuta sin errores y muestra templates
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| soul_json del template no coincide con campos AgentForm | Media | Seed tiene `role` dentro de soul_json pero AgentForm lo trata como campo separado | Mapeo explícito en `mapTemplateToFormValues()` — extraer cada campo con fallback |
| Templates no seedeados en Supabase | Alta | Paso 03 completado pero seed no ejecutado en DB real | Verificar con `fap templates seed --dry-run` antes de probar UI |
| Suggested_tools del template no existen en ToolRegistry | Media | Template referencia tools que no están instaladas | ToolMultiSelect ya maneja tools inexistentes (simplemente no las muestra como seleccionables) |
| Layout overflow en mobile | Baja | TemplatePicker modal puede no ser responsive en pantallas pequeñas | Usar Sheet component (ya disponible en ui/sheet.tsx) para mobile, grid para desktop |
| Doble llamada API al seleccionar template | Baja | TemplatePicker ya tiene lista pero necesita detalle para soul_json | Aceptar: lista ligera + detalle on-demand es patrón correcto. Cache con react-query staleTime |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: CLI `fap templates preview` | `src/cli/commands/templates_preview.py` | `def preview_templates(detail: bool = False, name: str | None = None) -> None` | `src/cli/commands/templates_seed.py :: seed_templates()` — usar Rich table + get_service_client | DX | Baja | 0.5h | Ninguna | → verificar: `uv run python -m src.cli.main templates preview` muestra 8 templates en tabla |
| 1 | Registrar CLI `templates preview` | `src/cli/main.py` | `templates_app.command("preview")(preview_templates)` ya registrado en templates_app | `src/cli/main.py:33,58` — `add_typer(templates_app, name="templates")` ya existe | DX | Baja | 0.1h | Tarea 0 | → verificar: `uv run python -m src.cli.main templates --help` muestra subcomando `preview` |
| 2 | Crear componente TemplatePicker | `dashboard/components/builder/TemplatePicker.tsx` | `interface TemplatePickerProps { onSelect: (template: TemplateDetail) => void }` + `export function TemplatePicker({ onSelect }: TemplatePickerProps)` | `dashboard/components/builder/ToolMultiSelect.tsx` — patrón useQuery + loading/error states + búsqueda con useMemo | CODE | Media | 2h | Ninguna | → verificar: `import { TemplatePicker } from '@/components/builder/TemplatePicker'` sin error de compilación |
| 3 | Definir tipo TemplateDetail | `dashboard/components/builder/TemplatePicker.tsx` (inline) | `interface TemplateDetail { id: string; name: string; description: string \| null; category: string; soul_json: Record<string, unknown>; suggested_tools: string[]; max_iter: number; is_system: boolean }` | `dashboard/components/builder/AgentForm.tsx:52-56` — interface ToolInfo pattern | CODE | Baja | 0.2h | Tarea 2 | → verificar: TypeScript compila sin errores de tipo |
| 4 | Agregar función mapeo template → form values | `dashboard/components/builder/TemplatePicker.tsx` (o archivo util) | `function mapTemplateToFormValues(template: TemplateDetail): Partial<AgentFormData>` — extrae role, goal, backstory, llmProvider, llmModel, allowedTools, maxIter, verbose, reasoning, injectDate, memory de soul_json | `dashboard/components/builder/AgentForm.tsx:117-131` — estructura soul_json plano | CODE | Baja | 0.3h | Tarea 2 | → verificar: función retorna objeto con las 11 keys de AgentFormData |
| 5 | Modificar BuilderLayout para manejar estado template | `dashboard/components/builder/BuilderLayout.tsx` | Agregar: `useState<TemplateDetail \| null>(null)`, `handleSelectTemplate(template: TemplateDetail)`, `initialValues` computed, botón "Templates" toggle | `dashboard/app/(app)/builder/page.tsx` — patrón 'use client' + state | CODE | Media | 1h | Tarea 2, Tarea 4 | → verificar: clic en "Use Template" rellena campos del AgentForm visible |
| 6 | Integrar TemplatePicker en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Render condicional: `{showPicker && <TemplatePicker onSelect={handleSelectTemplate} />}` — como panel superior o Sheet | `dashboard/components/ui/sheet.tsx` — patrón Sheet para mobile, div para desktop | CODE | Baja | 0.5h | Tarea 2, Tarea 5 | → verificar: botón "Templates" abre/cierra picker sin romper layout |
| 7 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 2-6 | → verificar: criterios §5 [FULLSTACK] pasan todos — crear agente desde template → guardar en Supabase |

**Tiempo total estimado:** 5.1 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Template custom creation: permitir guardar agente actual como template personalizado (POST /api/templates con service_role)
- Template versioning: trackear cambios en soul_json de templates system
- Template sharing entre organizaciones: agregar org_id a agent_templates + RLS modificado
- Preview de template: modal con detalle completo del soul_json antes de aplicar
- Template categories dinámicas: permitir admin crear nuevas categorías
- Template rating/usage stats: trackear qué templates se usan más

---

## 🚫 Reglas de Oro Aplicadas

- ✅ Análisis accionable y específico — cada tarea con interfaz exacta y patrón de referencia
- ✅ TODO verificado contra código — 22 elementos verificados en §0
- ✅ Discrepancias señaladas con resolución concreta — D1, D2, D4
- ✅ Código gana sobre plan — BuilderLayout modificado, no nuevo archivo
- ✅ 4 etapas cubiertas — data, code, backend, fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta — `fap templates preview`
- ✅ Tareas atómicas — una tarea = un artefacto
- ✅ Interfaz exacta por tarea — firmas completas
- ✅ Patrón de referencia explícito — archivo concreto por tarea
- ✅ Verificación inline por tarea — comando o check concreto
- ✅ Estimación de tiempo — por tarea y total
