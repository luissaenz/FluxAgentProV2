# Análisis Técnico — Paso 05: Template Picker

**Agente:** lgn
**Fecha:** 2026-05-14
**Paso:** 05 — Template Picker (librería de templates)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql:10` | ✅ | Mig 030, líneas 10-21 |
| 2 | Schema columnas exactas | `030_agent_templates.sql:11-20` | ✅ | id UUID, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INTEGER, is_system BOOLEAN |
| 3 | RLS SELECT authenticated | `030_agent_templates.sql:25-26` | ✅ | `auth.role() = 'authenticated'` |
| 4 | Endpoint `GET /api/templates` | `src/api/routes/templates.py:54-67` | ✅ | `list_templates()` con filtro `?category=` |
| 5 | Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:70-83` | ✅ | `get_template()` retorna `soul_json` completo |
| 6 | Modelo `TemplateInfo` | `templates.py:25-33` | ✅ | id, name, description, category, suggested_tools, max_iter, is_system, created_at |
| 7 | Modelo `TemplateListResponse` | `templates.py:36-38` | ✅ | templates: List[TemplateInfo], count: int |
| 8 | Modelo `TemplateDetailResponse` | `templates.py:41-51` | ✅ | Incluye soul_json: Dict[str, Any] |
| 9 | `AgentForm` con `initialValues` prop | `AgentForm.tsx:49,74-86` | ✅ | Props: onSave, onClear, initialValues — pattern useForm con defaultValues |
| 10 | `BuilderLayout` renderiza `AgentForm` | `BuilderLayout.tsx:15` | ✅ | `<AgentForm />` sin props — puede agregar initialValues |
| 11 | `reactflow` v11 instalado | `package.json` | ✅ | Dependencia en dashboard |
| 12 | `zod` + `@hookform/resolvers` | `package.json` | ✅ | v5.2.2 instalado |
| 13 | `TemplatePicker.tsx` NO existe | `ls dashboard/components/builder/` | ✅ | Archivo no encontrado — crear desde cero |
| 14 | 8 system templates seedeados | `templates_seed.py:32-137` | ✅ | Research, Code Reviewer, Data Analyst, Customer Support, Document Writer, Translator, Summarizer, General Assistant |
| 15 | `card.tsx` component disponible | `dashboard/components/ui/card.tsx` | ✅ | Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter |
| 16 | `badge.tsx` component disponible | `dashboard/components/ui/badge.tsx` | ✅ | Badge con variantes |
| 17 | `scroll-area.tsx` disponible | `dashboard/components/ui/scroll-area.tsx` | ✅ | ScrollArea component |
| 18 | `PROVIDER_MODELS` constante | `dashboard/lib/constants.ts:16-21` | ✅ | Mapa con 4 providers, ≥2 modelos cada uno |
| 19 | `api.get()` helper | `dashboard/lib/api.ts:55-56` | ✅ | `fapFetch` con auth + X-Org-ID headers |
| 20 | `ToolMultiSelect` patrón existente | `ToolMultiSelect.tsx:42-49` | ✅ | `useMemo` para filtrado — referencia para búsqueda |
| 21 | `LoadingSpinner` component | `dashboard/components/shared/LoadingSpinner.tsx` | ✅ | Skeletons disponibles |
| 22 | `Skeleton` component | `dashboard/components/ui/skeleton.tsx` | ✅ | Para loading states |

**Discrepancias encontradas:**

1. **D1 — `TemplateInfo` (lista) omite `soul_json`**: El endpoint GET lista no incluye `soul_json`. Resolución: TemplatePicker usa GET /api/templates para cards → GET /api/templates/{id} al hacer clic "Use Template" para obtener detalle completo.

2. **D2 — `BuilderLayout` sin estado template**: Actualmente renderiza `<AgentForm />` sin props. Resolución: Agregar `useState<TemplateDetail | null>` y pasar `initialValues` mapeados.

3. **D3 — `soul_json` incluye `role` como campo interno**: En `templates_seed.py:38`, `soul_json.role = "Research Specialist"`. Pero `AgentForm` trata `role` como campo separado (schema línea 30). Resolución: Mapeo explícito extrae `soul_json.role` → `role`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas:** `agent_templates` (lectura solamente)

- Schema: existente (mig 030). Sin cambios requeridos.
- Índices: `idx_agent_templates_category` (línea 31) — filtro por categoría optimizado.
- RLS: Lectura pública para autenticados → frontend puede consumir sin `require_org_id`.
- `soul_json` estructura real: `{role, goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}`

**Flujo datos:**
```
GET /api/templates → TemplateInfo[] (sin soul_json)
  → User clic "Use Template"
    → GET /api/templates/{id} → TemplateDetailResponse (con soul_json)
      → Mapear soul_json → AgentForm initialValues
```

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

**Tipo `TemplateDetail`:**
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

**Dependencias:**
- `@tanstack/react-query` — useQuery
- `@/lib/api` — api.get()
- `@/components/ui/card` — Card components
- `@/components/ui/badge` — Badge
- `@/components/ui/input` — Input búsqueda
- `@/components/shared/LoadingSpinner` — Loading states
- `lucide-react` — BookOpen, Search, X iconos

**Patrones de referencia:**
| Artefacto | Referencia | Archivo |
|---|---|---|
| Cards grid | Card + CardContent + CardFooter | `card.tsx` |
| Loading/Error states | LoadingSpinner + Skeleton | `ToolMultiSelect.tsx:254-262` |
| Búsqueda + filtro | useMemo filtrado | `ToolMultiSelect.tsx:42-49` |

### Función de mapeo template → form

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

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Sin cambios backend.** Solo consumo de endpoints existentes.

| Endpoint | Uso |
|---|---|
| `GET /api/templates` | Lista para cards |
| `GET /api/templates/{id}` | Detalle con soul_json |

**Contratos:**
- Response lista: `{ templates: TemplateInfo[], count: number }`
- Response detalle: `{ id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at }`

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
[builder/page.tsx]
  └── BuilderLayout
       ├── [Templates] button → abre TemplatePicker
       └── AgentForm(initialValues={...}) ← rellenado desde template
```

### Herramienta Propuesta: `fap templates preview`

- **Qué automatiza:** Listar templates disponibles con soul_json desde CLI.
- **Tipo:** CLI command
- **Cómo se usa:** `uv run python -m src.cli.main templates preview`
- **Impacto:** Validar templates sin abrir dashboard.
- **Prioridad:** Tarea 0

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] GET /api/templates devuelve ≥8 templates con categorías válidas
✅ [DATA] GET /api/templates/{id} devuelve soul_json con role, goal, backstory
✅ [CODE] TemplatePicker.tsx existe y renderiza grid de cards
✅ [CODE] Templates cargan desde API real (no mock)
✅ [CODE] Búsqueda filtra cards en tiempo real
✅ [CODE] Filtro por categoría funciona (chips Research/Development/Support/General)
✅ [CODE] Botón "Use Template" llama onSelect con template
✅ [CODE] BuilderLayout maneja estado template y pasa initialValues a AgentForm
✅ [FULLSTACK] Flujo: Templates → buscar/filtrar → Use → formulario relleno → Save
✅ [FULLSTACK] Loading/error states manejados con retry
✅ [DX] CLI `fap templates preview` funciona sin errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| soul_json fields no coinciden con AgentForm | Media | `soul_json.role` vs campo `role` separado | Mapeo explícito con fallback |
| Templates no seedeados en Supabase | Alta | Seed existe pero DB no actualizada | Ejecutar `fap templates seed` |
| Suggested_tools inexistentes | Media | Template refiere tools no instaladas | ToolMultiSelect ignora tools no disponibles |
| Layout overflow mobile | Baja | Modal puede romper responsive | Usar Sheet component para mobile |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo | Verificación |
|---|---|---|---|---|---|---|---|---|
| 0 | DX: CLI `fap templates preview` | `src/cli/commands/templates_preview.py` | `def preview_templates() -> None` | `templates_seed.py` pattern | DX | Baja | 0.5h | `uv run -m src.cli.main templates preview` muestra tabla |
| 1 | Registrar subcomando templates preview | `src/cli/main.py` | `templates_app.command("preview")` | línea 33, 58 existentes | DX | Baja | 0.1h | `--help` muestra preview |
| 2 | Crear TemplatePicker.tsx | `dashboard/components/builder/TemplatePicker.tsx` | `function TemplatePicker({ onSelect })` | `ToolMultiSelect.tsx` pattern | CODE | Media | 2h | Import sin error TS |
| 3 | Definir TemplateDetail interface | Inline en TemplatePicker.tsx | interface TemplateDetail | `AgentForm.tsx:52-56` | CODE | Baja | 0.2h | TS compila |
| 4 | Función mapeo template → form | TemplatePicker.tsx | `mapTemplateToFormValues(template)` | `AgentForm.tsx:117-131` | CODE | Baja | 0.3h | Retorna objeto con 11 keys |
| 5 | Modificar BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Agregar useState + handleSelectTemplate | `AgentForm.tsx:62-87` | CODE | Media | 1h | Form rellenado al clic "Use" |
| 6 | Integrar TemplatePicker | BuilderLayout.tsx | Render condicional Sheet/Dialog | `ui/sheet.tsx` pattern | CODE | Baja | 0.5h | Botón abre/cierra sin romper |
| 7 | Validar flujo E2E | — | — | — | FULLSTACK | Baja | 0.5h | Criterios §5 pasan |

**Tiempo total estimado:** 5.1 horas

---

## 🔮 Roadmap

- Template custom creation (POST /api/templates)
- Template versioning
- Sharing entre organizaciones
- Preview detallado antes de aplicar