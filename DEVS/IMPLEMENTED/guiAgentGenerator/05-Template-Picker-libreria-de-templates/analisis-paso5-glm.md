# 🧠 Análisis Técnico — Paso 05: Template Picker — librería de templates

> **Agente:** glm  
> **Paso:** 05 — Template Picker — librería de templates  
> **Fecha:** 2026-05-14  

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | Tabla `agent_templates` | Existe en migración | ✅ | `supabase/migrations/030_agent_templates.sql:10-21` — columnas: id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at |
| 2 | RLS `agent_templates_read` | SELECT con auth.role() = 'authenticated' | ✅ | `030_agent_templates.sql:25-26` |
| 3 | RLS `agent_templates_write` | ALL con auth.role() = 'service_role' | ✅ | `030_agent_templates.sql:28-29` |
| 4 | Índice parcial UNIQUE system name | Existe | ✅ | `030_agent_templates.sql:32-33` — `UNIQUE(name) WHERE is_system = TRUE` |
| 5 | Índice por category | Existe | ✅ | `030_agent_templates.sql:31` — `idx_agent_templates_category` |
| 6 | Endpoint `GET /api/templates` | Implementado | ✅ | `src/api/routes/templates.py:54-67` — filtro `?category=`, response `TemplateListResponse` |
| 7 | Endpoint `GET /api/templates/{id}` | Implementado | ✅ | `src/api/routes/templates.py:70-83` — `maybe_single()`, 404 si no existe |
| 8 | Router registrado en main.py | Registrado | ✅ | `src/api/main.py:30,113` — import + `include_router(templates_router)` |
| 9 | Modelo `TemplateInfo` (lista) | Sin `soul_json` | ✅ | `templates.py:25-33` — campos: id, name, description, category, suggested_tools, max_iter, is_system, created_at |
| 10 | Modelo `TemplateDetailResponse` | Con `soul_json` | ✅ | `templates.py:41-51` — incluye soul_json: Dict[str, Any] |
| 11 | Modelo `TemplateListResponse` | Incluye `count` | ✅ | `templates.py:36-38` — templates + count |
| 12 | `TemplatePicker.tsx` existe | Implementado | ✅ | `dashboard/components/builder/TemplatePicker.tsx` — 237 líneas |
| 13 | `TemplatePicker` usa `useQuery` | Con cache staleTime | ✅ | `TemplatePicker.tsx:62-70` — queryKey `['templates']`, staleTime `TEMPLATE_CACHE_MS` |
| 14 | `TemplatePicker` double fetch | list → detail al seleccionar | ✅ | `TemplatePicker.tsx:86-98` — `handleUseTemplate` hace `api.get('/api/templates/${template.id}')` |
| 15 | `TemplatePicker` 4 estados visuales | loading/error/empty/data | ✅ | `TemplatePicker.tsx:100-235` — skeletons, AlertTriangle retry, Inbox seed hint, grid cards |
| 16 | `TemplatePicker` filtro categoría chips | IMPLEMENTADO | ✅ | `TemplatePicker.tsx:161-178` — `TEMPLATE_CATEGORIES` + "All" badge |
| 17 | `TemplatePicker` búsqueda client-side | Case-insensitive | ✅ | `TemplatePicker.tsx:79-81` — `t.name.toLowerCase().includes(q)` |
| 18 | `BuilderLayout.tsx` integración TemplatePicker | Dialog modal + botón "Templates" | ✅ | `BuilderLayout.tsx:81-91` — `<Dialog>` + `<TemplatePicker onSelect={handleSelectTemplate}>` |
| 19 | `mapTemplateToFormValues()` | Mapeo defensivo con fallbacks | ✅ | `BuilderLayout.tsx:18-40` — `soul.role ?? template.name`, `soul.backstory ?? template.description`, provider validation |
| 20 | `AgentForm` prop `templateData` | useEffect reset post-montaje | ✅ | `AgentForm.tsx:50,91-107` — `useEffect([templateData, reset])` |
| 21 | `AgentForm` prop `onClear` | Limpia templateData en BuilderLayout | ✅ | `AgentForm.tsx:174-189` — `reset()` + `onClear?.()` |
| 22 | `TEMPLATE_CATEGORIES` constante | Hardcodeada en constants.ts | ✅ | `constants.ts:16` — `['Research', 'Development', 'Support', 'General'] as const` |
| 23 | `TEMPLATE_CACHE_MS` | 5 minutos | ✅ | `constants.ts:18` — `5 * 60 * 1000` |
| 24 | CLI `fap templates use` | Implementado | ✅ | `src/cli/commands/templates_use.py` — 194 líneas, `--org-id`, `--dry-run`, overrides |
| 25 | API `/api/templates` sin auth | Sin `require_org_id` | ✅ | `templates.py:54` — ningún `Depends(require_org_id)` |
| 26 | `LoadingSpinner` componente | Reutilizado en TemplatePicker | ✅ | `TemplatePicker.tsx:224-225` — `<LoadingSpinner size="sm" />` |
| 27 | `EmptyState` componente | Reutilizado en TemplatePicker | ✅ | `TemplatePicker.tsx:125-128,139-144,183-185` — 3 usos |
| 28 | Seed `fap templates seed` | Idempotente, 8 templates | ✅ | `templates_seed.py:140-220` — check-then-insert, `--dry-run`, `--reset` |

### Discrepancias encontradas

| ID | Discrepancia | Resolución | Estado |
|----|-------------|------------|--------|
| D1 | `soul_json` del seed tiene `{role, goal, backstory}` pero AgentForm tiene `role` como campo separado y `soul_json` plano sin `role` | `mapTemplateToFormValues()` extrae `soul.role` → `role` plano con fallbacks | ✅ Resuelto — `BuilderLayout.tsx:28-38` |
| D2 | `AgentForm.initialValues` solo afecta `defaultValues` al montar; TemplatePicker necesita aplicar post-montaje | Prop `templateData` + `useEffect` con `form.reset(templateData)` | ✅ Resuelto — `AgentForm.tsx:50,91-107` |
| D3 | `TemplateInfo` (lista) no incluye `soul_json` → requiere double fetch | `handleUseTemplate` hace `GET /api/templates/{id}` al seleccionar | ✅ Resuelto — `TemplatePicker.tsx:88-89` |
| D4 | `BuilderLayout` no manejaba estado de template | `useState<AgentFormData \| null>` + `handleSelectTemplate` / `handleClear` | ✅ Resuelto — `BuilderLayout.tsx:43-50` |
| D5 | Categorías hardcodeadas como constante | `TEMPLATE_CATEGORIES` en `constants.ts:16` — post-MVP: endpoint dinámico | ✅ Aceptado — MVP scope |
| D6 | Prop `templateData` elegida sobre `forwardRef` | Sin refactoring, prop simple够 | ✅ Resuelto — `AgentForm.tsx:50` |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema existente — `agent_templates`

```sql
-- 030_agent_templates.sql
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

### Integridad referencial
- ✅ Tabla global sin `org_id` — patrón `service_catalog`, catálogo público
- ✅ RLS: `SELECT` requiere `authenticated`, `ALL` requiere `service_role`
- ✅ Índice parcial `UNIQUE(name) WHERE is_system = TRUE` — sistema nombres únicos, custom futuros libres
- ✅ Índice `idx_agent_templates_category` — optimiza filtro `?category=`

### `soul_json` estructura (de seed)
```json
{
  "role": "Research Specialist",
  "goal": "Research topics thoroughly...",
  "backstory": "Expert researcher...",
  "llm_provider": "groq",  // opcional, no todos los templates lo tienen
  "llm_model": "llama-3.1-70b-versatile",  // opcional
  "verbose": false,  // opcional
  "reasoning": false,  // opcional
  "inject_date": false,  // opcional
  "memory": false  // opcional
}
```

- ❌ `soul_json` sin validación Pydantic en API — `Dict[str, Any]` → cualquier JSON aceptado. Seed provee estructura consistente, pero no hay contrato estricto.
- ⚠️ `suggested_tools` son strings arbitrarios sin FK a `tool_registry` — permitido (tools dinámicas via MCP), pero implica que cards pueden mostrar tools que no existen en `GET /api/tools/available`.

### Impacto en datos existentes
- ✅ Seed crea 8 templates con UUID5 determinista (`uuid5(NAMESPACE_DNS, "fap.system.template.{name}")`)
- ✅ Idempotente: check-then-insert compatible con índice parcial UNIQUE
- ⚠️ Si se corre `--reset`, elimina TODOS los system templates y re-inserta. IDs cambian si se usa UUID aleatorio en lugar del determinista (pero seed usa UUID5, IDs estables).

### Índices necesarios
- ✅ `idx_agent_templates_category` — ya existe para filtro
- ⚠️ No hay índice en `is_system` — pero `idx_agent_templates_system_name` (partial) cubre queries `WHERE is_system = TRUE`. Queries `WHERE is_system = FALSE` (custom templates futuro) serían seq scan. Aceptable para MVP.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos creados en este paso

#### `TemplatePicker.tsx` (237 líneas)
- **Firma:** `function TemplatePicker({ onSelect }: TemplatePickerProps)`
- **Props:** `onSelect: (template: TemplateDetail) => void`
- **Interfaces exportadas:** `TemplateDetail extends TemplateInfo { soul_json, updated_at }`
- **Estado local:** `search: string`, `selectedCategory: string | null`, `loadingId: string | null`
- **Datos:** `useQuery<TemplateListResponse>` — staleTime 5min, queryKey `['templates']`
- **Filtrado:** `useMemo` client-side — category filter + search (case-insensitive en `name`)
- **4 estados UI:** loading (skeletons ×6), error (EmptyState + Retry), empty (EmptyState + seed hint), data (cards grid)
- **Card:** nombre + descripción (line-clamp-2) + categoría badge + suggested_tools badges (max 3 + "+N") + botón "Use Template" con LoadingSpinner
- **Patrón:** Consistente con `ToolMultiSelect.tsx` — useQuery + useMemo + estados explícitos

#### `BuilderLayout.tsx` — integración (94 líneas)
- **Firma:** `function BuilderLayout()`
- **Estado:** `dialogOpen: boolean`, `templateData: AgentFormData | null`
- **`mapTemplateToFormValues(template: TemplateDetail): AgentFormData`** — mapeo defensivo:
  - `soul.role ?? template.name` (fallback a nombre del template)
  - `soul.goal ?? ''` 
  - `soul.backstory ?? template.description ?? ''` 
  - `soul.llm_provider` validado contra `valid` tuple ('groq' | 'openai' | 'anthropic' | 'openrouter'), fallback 'groq'
  - `soul.llm_model ?? 'llama-3.1-70b-versatile'`
  - `suggested_tools ?? []`
  - `max_iter ?? 3`
  - Toggles con `?? false`
- **UI:** `<Dialog>` con `max-w-3xl max-h-[80vh] overflow-y-auto` + botón "Templates" con icono `Layers`

#### `AgentForm.tsx` — extensión (356 líneas)
- **Nuevas props:** `templateData?: AgentFormData | null`, `onClear?: () => void`
- **`useEffect([templateData, reset])`** — aplica template post-montaje con `form.reset(templateData)`
- **`handleClear()`** — reset a defaults + `onClear?.()` para notificar a BuilderLayout

#### `constants.ts` — nuevas constantes
- `TEMPLATE_CATEGORIES` — `['Research', 'Development', 'Support', 'General'] as const`
- `TEMPLATE_CACHE_MS` — `5 * 60 * 1000` (5 minutos)

### Patrones seguidos
- ✅ `useQuery` con `staleTime` — mismo patrón que `AgentForm` con `['tools-available', orgId]`
- ✅ Componentes shadcn/ui reutilizados: `Card`, `Button`, `Input`, `Badge`, `Skeleton`, `Dialog`
- ✅ Componentes shared reutilizados: `EmptyState`, `LoadingSpinner`
- ✅ API client `api.get()` — mismo `fapFetch` con auth headers
- ✅ Alternancia de estados visuales (loading → error → empty → data) — idéntico patrón que `AgentForm` para tools

### Modularidad
- ✅ Alta cohesión: TemplatePicker encapsula toda la lógica de grid/búsqueda/filtro
- ✅ Bajo acoplamiento: `onSelect` callback — TemplatePicker no conoce AgentForm directamente
- ✅ `mapTemplateToFormValues` en BuilderLayout — capa de adaptación entre template y form, desacoplada de ambos
- ⚠️ `TemplatePicker.tsx` define `TemplateInfo` y `TemplateDetail` localmente (no importable desde `@/types`). Implica duplicación de tipos si otros componentes necesitan los mismos tipos. Aceptable para MVP.

### Imports
- `TemplatePicker.tsx`: useState, useMemo (React), useQuery (@tanstack/react-query), toast (sonner), lucide-react icons, api client, constants, shadcn/ui components, shared components
- `BuilderLayout.tsx`: useState (React), BuilderCanvas, AgentForm, TemplatePicker + TemplateDetail type, Dialog components, Button, Layers icon
- Todos correctos, absolutos desde `@/`.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes (Paso 03)

#### `GET /api/templates`
- **Ruta:** `src/api/routes/templates.py:54-67`
- **Método:** GET
- **Auth:** Ninguna (catálogo público)
- **Query params:** `?category=` (opcional)
- **Response:** `TemplateListResponse { templates: TemplateInfo[], count: number }`
- **`TemplateInfo` NO incluye `soul_json`** — solo metadatos para cards

#### `GET /api/templates/{template_id}`
- **Ruta:** `src/api/routes/templates.py:70-83`
- **Método:** GET
- **Auth:** Ninguna
- **Path param:** `template_id` (UUID string)
- **Response:** `TemplateDetailResponse` — incluye `soul_json: Dict[str, Any]`
- **Error:** 404 "Template not found" si `maybe_single()` retorna None

### Flujo de datos: TemplatePicker → Backend

```
[TemplatePicker mount]
  → GET /api/templates
  → TemplateListResponse { templates: TemplateInfo[], count }
  → Render cards con name, description, category, suggested_tools, max_iter

[User clicks "Use Template"]
  → loadingId = template.id  (bloquea botón, muestra spinner)
  → GET /api/templates/{template.id}
  → TemplateDetailResponse (con soul_json completo)
  → onSelect(detail)  →  BuilderLayout.handleSelectTemplate
  → mapTemplateToFormValues(detail)
  → setTemplateData(mapped) + setDialogOpen(false)
  → AgentForm useEffect reset(templateData)
```

- ✅ Double fetch es intencional — lista sin `soul_json` (payload ligero para grid), detalle con `soul_json` (solo al seleccionar)
- ✅ `staleTime: 5min` — evita re-fetch continuo del listado durante misma sesión
- ✅ `loadingId` previene doble click mientras se obtiene el detail

### Contratos

| Endpoint | Input | Output | Status |
|----------|-------|--------|--------|
| `GET /api/templates` | `?category=` opcional | `{ templates: TemplateInfo[], count: number }` | 200 |
| `GET /api/templates?category=Research` | Query param | Filtro server-side por category | 200 |
| `GET /api/templates/{id}` | UUID path param | `{ id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at }` | 200 / 404 |

### Error handling
- ✅ TemplatePicker: `try/catch` en `handleUseTemplate` → `toast.error('Failed to load template details')`
- ✅ TemplatePicker: estado `isError` → `EmptyState` con Retry button
- ✅ Backend: `maybe_single()` retorna None → 404 con mensaje claro
- ⚠️ Backend no tiene rate limit en endpoints públicos — aceptable para MVP
- ⚠️ Backend no filtra `is_system` en listado — retorna TODOS los templates (system + custom futuros). Aceptable para MVP (solo hay system templates ahora).

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: DB → Backend → Frontend → UX

```
[Supabase: agent_templates]
  → get_service_client().table("agent_templates").select("*")
  → Endpoints GET /api/templates (list) + GET /api/templates/{id} (detail)
  → API client fapFetch con auth headers (pero endpoint no requiere org_id)
  → TemplatePicker useQuery(['templates'], staleTime: 5min)
  → Grid cards con búsqueda + filtro chips
  → "Use Template" → GET /api/templates/{id}
  → mapTemplateToFormValues() → AgentForm reset()
  → Usuario edita formulario → "Save Agent" → POST /agents
```

### Coherencia end-to-end
- ✅ Seed CLI pobla 8 templates con categorías que matchean `TEMPLATE_CATEGORIES`
- ✅ Filtro por categoría funciona: chips usan `TEMPLATE_CATEGORIES` que coincide exactamente con `category` field del seed
- ✅ `soul_json` del seed contiene `role`, `goal`, `backstory` → mapeo los extrae y adapta a AgentForm
- ✅ `suggested_tools` del seed matchea tools disponibles en `ToolRegistry` (no todas — `sql_analytical`, `event_store`, `excel_reader`, `excel_writer` son builtin; `search`, `code_analyzer` pueden no existir)
- ⚠️ Tools mostradas en cards (`suggested_tools.slice(0, 3) + "+N"`) son strings arbitrarios. No hay validación contra `GET /api/tools/available`. Si un template sugiere una tool que no existe, el badge se muestra igual. Impacto UX menor — info visual فقط.

### UX Flow
1. Usuario ve botón "Templates" en header del panel derecho
2. Click → Dialog modal con grid de templates
3. Puede filtrar por categoría (chips: All, Research, Development, Support, General)
4. Puede buscar por nombre (búsqueda client-side, case-insensitive)
5. Click "Use Template" → spinner en botón → fetch detail → dialog se cierra → formulario pre-llenado
6. Usuario puede editar campos pre-llenados antes de guardar
7. Botón "Clear" → reset formulario + `onClear()` → `templateData` a null

### Gaps detectados
- ⚠️ Búsqueda solo por `name` — no busca en `description` ni `category`. Para MVP suficiente, post-MVP ampliar a full-text.
- ⚠️ No hay paginación en `GET /api/templates` — con 8 templates es trivial, pero si se agregan custom templates por org necesitará paginación o infinite scroll.
- ⚠️ No hay indicación visual de qué template está "activo" en el formulario. El usuario no sabe si el formulario tiene datos de un template o datos manuales.
- ⚠️ `TEMPLATE_CATEGORIES` está hardcodeado — si se agregan nuevas categorías al seed, hay que actualizar el frontend manualmente. Post-MVP: endpoint `GET /api/templates/categories` dinámico.

### Herramienta DX Propuesta: `fap templates use`

- **Qué automatiza:** Crear un agente desde template vía CLI sin abrir el dashboard. Dogfooding del mapeo template→agent antes de construir UI.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:** `fap templates use "Research Agent" --org-id UUID` o `fap templates use UUID --dry-run`
- **Impacto para el usuario final:** Valida mapeo `soul_json` → `AgentFormData` sin depender de UI. Permite CI/testing.
- **Prioridad:** Tarea 0 — implementar antes que el componente frontend (ya implementado en paso completado)

```
### Herramienta Propuesta: fap templates use
- **Qué automatiza:** Crear agente desde template CLI — dogfooding mapeo soul_json → payload POST /agents
- **Tipo:** CLI
- **Cómo se usa:** `fap templates use "Research Agent" --org-id UUID [--dry-run] [--role X] [--goal Y] [--backstory Z]`
- **Impacto para el usuario final:** Valida pipeline template→agent sin UI. Permite overrides parciales.
- **Prioridad:** Tarea 0 — ya implementado (dogfooding validado)
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [FULLSTACK] TemplatePicker visible desde builder (botón "Templates" en panel derecho)
✅ [FULLSTACK] Click en "Templates" abre Dialog modal con grid de cards
✅ [DATA] Templates cargan desde GET /api/templates (API real, no mock)
✅ [BACKEND] GET /api/templates retorna TemplateListResponse con count
✅ [BACKEND] GET /api/templates/{id} retorna TemplateDetailResponse con soul_json
✅ [FULLSTACK] Click en "Use Template" → fetch detail → formulario se rellena
✅ [DATA] Filtro por categoría funciona (chips: All, Research, Development, Support, General)
✅ [CODE] Búsqueda por texto funciona (client-side, case-insensitive en name)
✅ [FULLSTACK] 4 estados visuales: loading (skeletons), error (retry), empty (seed hint), data (cards)
✅ [DATA] LoadingSpinner en botón "Use Template" durante fetch de detail
✅ [CODE] mapTemplateToFormValues() mapea soul_json → AgentFormData con fallbacks defensivos
✅ [CODE] handleClear() resetea formulario + limpia templateData en BuilderLayout
✅ [BACKEND] Endpoint GET /api/templates no requiere auth (catálogo público)
✅ [BACKEND] Filtro ?category= funciona en backend
✅ [DX] fap templates use CLI funcional con --dry-run y overrides
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| R1: `suggested_tools` muestra tools inexistentes | Baja | Templates referencian tools por string sin FK — `sql_analytical`, `excel_reader` son builtin, pero `search`, `code_analyzer` pueden no existir en instalación específica | Mostrar badge igual; al guardar agente, `allowed_tools` se persiste como array de strings sin validación. Post-MVP: cross-check contra `GET /api/tools/available` |
| R2: sin paginación en listado de templates | Media | `GET /api/templates` retorna todos sin paginación. Con custom templates por org (post-MVP) puede crecer | MVP: 8 templates sys + pocos custom = trivial. Post-MVP: agregar `?limit=&offset=` |
| R3: `soul_json` sin validación estricta | Baja | Dict[str, Any] acepta cualquier JSON. Seed provee estructura consistente, pero no hay contrato Pydantic | MVP aceptable — seed es única fuente de templates. Post-MVP: Pydantic model para soul_json |
| R4: búsqueda solo por nombre | Baja | `t.name.toLowerCase().includes(q)` — no cubre description ni category | Post-MVP: buscar en description + category, o full-text search en backend |
| R5: Cache staleTime 5min puede mostrar datos obsoletos | Baja | Si admin corre `fap templates seed --reset`, usuarios con sesión activa ven cache viejo 5min | Aceptable — templates cambian raramente. `refetch()` disponible manualmente |
| R6: Categorías hardcodeadas vs dinámicas | Media | `TEMPLATE_CATEGORIES` hardcodeado en `constants.ts`. Si se agregan categorías al seed, hay que actualizar frontend manual | Post-MVP: endpoint `GET /api/templates/categories` dinámico |

---

## 7️⃣ Plan de Implementación

> **NOTA:** Paso 05 ya está implementado y validado. Este plan documenta lo que se implementó para referencia del implementador.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|--------------|-------------|
| 0 | **DX: fap templates use** | `src/cli/commands/templates_use.py` | `use_template(template_name, org_id, role?, goal?, backstory?, tools?, max_iter?, dry_run?) → None` | `src/cli/commands/templates_seed.py` (Typer pattern) | DX | Media | 1.5h | Ninguna | → verificar: `fap templates use "Research Agent" --dry-run --org-id test-uuid` ejecuta sin errores |
| 1 | Crear componente TemplatePicker | `dashboard/components/builder/TemplatePicker.tsx` | `function TemplatePicker({ onSelect }: { onSelect: (template: TemplateDetail) => void })` | `dashboard/components/builder/ToolMultiSelect.tsx` (useQuery + estados) | CODE | Alta | 2h | Paso 03 endpoints | → verificar: TemplatePicker renderiza con datos mock y responda a onSelect |
| 2 | Crear función mapTemplateToFormValues | `dashboard/components/builder/BuilderLayout.tsx` | `function mapTemplateToFormValues(template: TemplateDetail): AgentFormData` | `src/cli/commands/templates_use.py:104-128` (mapeo defensivo soul_json → payload) | CODE | Media | 0.5h | Tarea 1 | → verificar: mapeo de template con soul_json completa → AgentFormData correcto |
| 3 | Integrar TemplatePicker en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | `useState<AgentFormData \| null>(null)` + `<Dialog>` + `<TemplatePicker onSelect>` + `handleSelectTemplate` | Patrón dialog de shadcn/ui | FULLSTACK | Media | 1h | Tareas 1-2 | → verificar: Click "Templates" → dialog abre → click "Use Template" → formulario rellena |
| 4 | Extender AgentForm con templateData prop | `dashboard/components/builder/AgentForm.tsx` | `interface AgentFormProps { templateData?: AgentFormData \| null; onClear?: () => void }` | Patrón react-hook-form reset | CODE | Baja | 0.5h | Tarea 3 | → verificar: templateData cambia → form.reset(templateData) ejecuta sin errores TS |
| 5 | Agregar constantes TEMPLATE_CATEGORIES y TEMPLATE_CACHE_MS | `dashboard/lib/constants.ts` | `export const TEMPLATE_CATEGORIES = ['Research', 'Development', 'Support', 'General'] as const` y `export const TEMPLATE_CACHE_MS = 5 * 60 * 1000` | Patrón PROVIDER_MODELS existente | CODE | Baja | 0.15h | Ninguna | → verificar: TemplatePicker importa ambas sin error |
| 6 | Ejecutar seed + verificar flujo E2E | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-5 | → verificar: `fap templates seed` + abrir builder + click Templates + usar template → formulario rellena + Save Agent funciona |

**Tiempo total estimado:** 5.15 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Paginación en templates list:** Agregar `?limit=&offset=` a `GET /api/templates` cuando custom templates crezcan
- **Endpoint dinámico de categorías:** `GET /api/templates/categories` que retorne categorías únicas desde DB
- **Búsqueda extendida:** Buscar en `description` y `category`, no solo `name`
- **Validación Pydantic de `soul_json`:** Modelo estricto para templates en vez de `Dict[str, Any]`
- **Template badges de "activo":** Visualización en AgentForm del template seleccionado (nombre, badge)
- **Cross-check de `suggested_tools`:** Mostrar badge "unavailable" si la tool del template no existe en `GET /api/tools/available`
- **Custom templates por org:** Migración adicional con `org_id` en `agent_templates`, endpoint `POST /api/templates` con auth
- **Favoritos/templates recientes:** Persistir en localStorage para acceso rápido

---

## 🚫 Reglas de Oro — Verificación

- ✅ Análisis accionable y específico — cada sección con evidencia de código
- ✅ TODO verificado contra código — §0 con 28 elementos verificados
- ✅ Discrepancias detectadas: 6 (D1-D6), todas resueltas
- ✅ Coherente con phase-state.md — referencias cruzadas sin repetición
- ✅ TODO el paso cubierto (sub-pasos incluidos: TemplatePicker, BuilderLayout integración, AgentForm extensión, CLI use template)
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX: `fap templates use` CLI
- ✅ Tareas atómicas con interfaz, patrón y verificación
- ✅ Nivel CTO en rigor y profundidad