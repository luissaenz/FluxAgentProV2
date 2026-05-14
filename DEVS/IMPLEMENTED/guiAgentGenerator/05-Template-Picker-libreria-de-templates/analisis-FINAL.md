# 🏛️ ANÁLISIS FINAL UNIFICADO — Paso 05: Template Picker — librería de templates

> **Fase:** `guiAgentGenerator`
> **Estado real:** ✅ Completado (commit `0779eb1`, archivado en `DEVS/IMPLEMENTED/guiAgentGenerator/05-Template-Picker-libreria-de-templates/`)
> **Unificación:** 7 análisis de agentes consolidados
> **Fecha:** 2026-05-14

---

## 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| dsp | ✅ (24 elementos) | 5 (D1-D5) | ✅ `fap templates use` + `fap templates seed` | ✅ Firmas completas, imports, 6 riesgos, roadmap | **5.0** |
| ring | ✅ (22 elementos) | 4 (D1-D4) | ✅ `fap templates use` + `fap templates seed` | ✅ Firmas clave, 7 riesgos, roadmap | **4.5** |
| step | ✅ (30 elementos) | 3 (D1-D3) | ✅ Documenta existentes (`seed` + `use`), no propone nuevo | ✅ Gaps identificados (404 error, tool validation), 5 riesgos | **4.5** |
| glm | ✅ (28 elementos) | 6 (D1-D6) | ✅ `fap templates use` | ✅ Firmas completas, 6 riesgos, gap analysis detallado | **4.5** |
| lgn | ✅ (26 elementos) | ❌ 0 (afirma "NINGUNA") | ✅ `fap templates use` | ❌ Sin firmas de código, "matchean" typo | **2.5** |
| mm2.7 | ✅ (15 elementos) | ❌ 0 (afirma "ninguna") | ⚠️ Propone `fap templates validate` (innecesario) | ❌ Mínimo, sin firmas, sin plan de tareas | **2.0** |
| hy3 | ✅ (15 elementos) | ⚠️ 2 (D1 es falso positivo) | ⚠️ Propone `scripts/seed_templates.py` (path incorrecto) | ❌ Confunde plan pre-implementación con post-completado | **1.5** |

> **Nota sobre lgn/mm2.7:** Afirman "0 discrepancias" pero `phase-state.md` documenta 6 correcciones (D1-D6) aplicadas al plan durante implementación. Fallan en detectar que `soul_json` del seed no incluye `llm_provider`/`llm_model`/toggles (corrección D1), que `AgentForm.initialValues` no sirve post-montaje (corrección D2), y que `TemplateInfo` no incluye `soul_json` (corrección D3). Análisis incompletos.
>
> **Nota sobre hy3:** Su D1 ("TemplatePicker.tsx no debería existir — plan task 1 dice 'Crear'") es un falso positivo: el plan es un documento pre-implementación y el paso YA está completado. El archivo debe existir. Su D2 sobre seed es erróneo — el seed sí existe en `src/cli/commands/templates_seed.py:140-220`.

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `soul_json` del seed solo tiene `{role, goal, backstory}` — NO incluye `llm_provider`, `llm_model`, `verbose`, `reasoning`, `inject_date`, `memory` | dsp, ring, step, glm | ✅ `templates_seed.py:32-137` — seed define esos campos | `mapTemplateToFormValues()` en `BuilderLayout.tsx:18-40` usa fallbacks explícitos: provider→groq, model→llama-3.1-70b, booleans→false |
| 2 | `GET /api/templates` (lista) NO incluye `soul_json` → requiere double fetch para "Use Template" | dsp, ring, step, glm | ✅ `templates.py:25-33` — `TemplateInfo` sin `soul_json` vs `templates.py:41-51` — `TemplateDetailResponse` con `soul_json` | `handleUseTemplate()` en `TemplatePicker.tsx:86-98` hace `GET /api/templates/{id}` al seleccionar. Aceptado como trade-off MVP. Post-MVP: `?include=soul_json` param |
| 3 | `AgentForm.initialValues` solo afecta `defaultValues` al montar; TemplatePicker necesita aplicar post-montaje | ring, glm | ✅ `AgentForm.tsx:91-107` — `useEffect` + `form.reset(templateData)` | Prop `templateData` + `useEffect` con `reset()` implementado en `AgentForm.tsx:50,91-107`. Corrección D6 del phase-state |
| 4 | Plan decía "Botón 'Use Template' → rellena el formulario" pero no define qué pasa si el formulario ya tiene datos | dsp | ✅ Código: `reset()` sobrescribe sin confirmación — `AgentForm.tsx:91-107` | Aceptado para MVP. Post-MVP: diálogo de confirmación "¿Sobrescribir formulario actual?" |
| 5 | Categorías hardcodeadas como constante (`TEMPLATE_CATEGORIES`) — no endpoint dinámico | dsp, ring, glm | ✅ `constants.ts:16` — `['Research','Development','Support','General'] as const` | Aceptado para MVP (solo 4 categorías, seed las usa consistentemente). Post-MVP: `GET /api/templates/categories` endpoint |
| 6 | Búsqueda solo por `name` — no busca en `description` | dsp, glm | ✅ `TemplatePicker.tsx:79-81` — `t.name.toLowerCase().includes(q)` | Aceptado para MVP (8 templates). Post-MVP: búsqueda en name+description |
| 7 | Seed `suggested_tools` puede referenciar tools no registradas en `ToolRegistry` | step, glm | ✅ Seed tools como `sql_analytical`, `excel_reader` son builtin; `search`, `code_analyzer` pueden no existir | Badge se muestra igual. Sin validación en `POST /agents`. Post-MVP: cross-check contra `GET /api/tools/available` |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo del paso:** Añadir el selector de templates al builder visual (equivalente al Template Library de Crew Studio). El usuario elige un template y el formulario AgentForm se auto-completa con los datos del template seleccionado.

**Correcciones críticas al plan original detectadas durante el análisis:**
- ⚠️ El plan asumía que `AgentForm` tenía `initialValues` para aplicar templates, pero `initialValues` solo afecta `defaultValues` al montar. Se implementó prop `templateData` + `useEffect` + `reset()` (corrección D2/D6).
- ⚠️ El plan no consideraba que `GET /api/templates` (lista) no incluye `soul_json`. Se implementó double fetch: lista para cards + detalle al seleccionar (corrección D3).
- ⚠️ El plan no especificaba qué campos del `soul_json` mapear al formulario. Se implementó `mapTemplateToFormValues()` con whitelist de providers y fallbacks defensivos (corrección D1).

**Decisión sobre herramienta DX:** `fap templates use` es la herramienta DX principal de este paso (Tarea 0). Permite crear agentes desde template vía CLI, validando el mapeo `soul_json → payload POST /agents` antes de construir la UI. `fap templates seed` es infraestructura preexistente del Paso 03 reutilizada aquí para poblar los 8 templates del sistema.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Usuario navega a `/builder` desde el sidebar del dashboard.
2. En el panel derecho (AgentForm), hace clic en botón "Templates" (icono `Layers`).
3. Se abre un Dialog modal (`max-w-3xl max-h-[80vh] overflow-y-auto`) con TemplatePicker.
4. TemplatePicker carga templates desde `GET /api/templates` (React Query, `staleTime: 5min`).
5. Usuario puede filtrar por categoría (chips Badge: All, Research, Development, Support, General).
6. Usuario puede buscar por nombre (Input con filtro client-side case-insensitive).
7. Usuario ve cards con: nombre, descripción (line-clamp-2), categoría badge, suggested_tools badges (max 3 + "+N"), botón "Use Template".
8. Usuario hace clic en "Use Template" → spinner en botón → `handleUseTemplate()` llama `GET /api/templates/{id}` para obtener `soul_json` completo.
9. `BuilderLayout.mapTemplateToFormValues()` mapea `TemplateDetail → AgentFormData` con fallbacks defensivos.
10. Dialog se cierra. `AgentForm.useEffect` detecta `templateData` → `form.reset(templateData)` → formulario pre-llenado.
11. Usuario puede editar cualquier campo antes de "Save Agent" (POST /agents con TenantClient, RLS).
12. Botón "Clear" resetea formulario a defaults y limpia `templateData`.

### Edge Cases MVP

| # | Caso | Comportamiento |
|---|---|---|
| EC1 | No hay templates en DB (seed no ejecutado) | TemplatePicker muestra EmptyState con icono `Inbox` + mensaje "Run: `fap templates seed`" |
| EC2 | Error de red al cargar templates | EmptyState con icono `AlertTriangle` + botón "Retry" (llama `refetch()`) |
| EC3 | Error al obtener detail (404 template borrado) | `toast.error('Failed to load template details')` — no distingue 404 vs network (gap documentado) |
| EC4 | Búsqueda sin resultados | EmptyState con icono `Search` + mensaje "No templates match your search" |
| EC5 | `soul_json` del template no tiene `role` | `mapTemplateToFormValues` usa `template.name` como fallback |
| EC6 | `soul_json.llm_provider` no está en whitelist | `valid.includes(provider)` → fallback a `'groq'` |
| EC7 | Formulario tiene datos previos al aplicar template | `reset()` sobrescribe sin confirmación (MVP acepta; post-MVP: diálogo de confirmación) |
| EC8 | Template tiene `suggested_tools` con tools no registradas | Badges se muestran igual; `POST /agents` persiste strings sin validación |

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. TemplatePicker.tsx — CREACIÓN
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\TemplatePicker.tsx`
- **Tipo de cambio:** Creación
- **Descripción:** Grid de templates con búsqueda, filtro por categoría, selección. 237 líneas. 4 estados visuales (loading/error/empty/data). Double fetch al seleccionar.
- **Interfaces clave:**
  ```ts
  interface TemplatePickerProps { onSelect: (template: TemplateDetail) => void }
  export function TemplatePicker({ onSelect }: TemplatePickerProps): JSX.Element
  ```
- **Patrones a seguir:** `AgentForm.tsx` (useQuery + skeleton + EmptyState), `ToolMultiSelect.tsx` (useMemo filtrado client-side)

#### 2. BuilderLayout.tsx — MODIFICACIÓN
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\BuilderLayout.tsx`
- **Tipo de cambio:** Modificación (añadido Dialog modal + integración TemplatePicker)
- **Descripción:** Layout split 60/40. Añade botón "Templates", estado `dialogOpen`/`templateData`, función `mapTemplateToFormValues()`, orquestación template → AgentForm.
- **Interfaces clave:**
  ```ts
  function mapTemplateToFormValues(template: TemplateDetail): AgentFormData
  function handleSelectTemplate(template: TemplateDetail): void
  function handleClear(): void
  ```
  Mapeo defensivo: `soul.role ?? template.name`, `soul.goal ?? ''`, `soul.backstory ?? template.description ?? ''`, `soul.llm_provider` validado contra `['groq','openai','anthropic','openrouter']`, fallback `'groq'`, `soul.llm_model ?? 'llama-3.1-70b-versatile'`.
- **Patrones a seguir:** Dialog modal shadcn/ui, patrón de orquestación existente en BuilderLayout

#### 3. AgentForm.tsx — MODIFICACIÓN
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\AgentForm.tsx`
- **Tipo de cambio:** Modificación (añadidas props `templateData` + `onClear`)
- **Descripción:** Acepta datos externos de template vía prop y aplica `form.reset()` vía `useEffect` post-montaje. 356 líneas total.
- **Interfaces clave:**
  ```ts
  interface AgentFormProps {
    onSave?: (data: AgentFormData) => Promise<void>
    onClear?: () => void
    initialValues?: Partial<AgentFormData>
    templateData?: AgentFormData | null  // ← Añadido Paso 05
  }
  ```
  `useEffect(() => { if (templateData) reset(templateData) }, [templateData, reset])`
- **Patrones a seguir:** react-hook-form `reset()`, patrón de props drilling existente

#### 4. constants.ts — MODIFICACIÓN
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\dashboard\lib\constants.ts`
- **Tipo de cambio:** Modificación (añadidas constantes)
- **Descripción:** `TEMPLATE_CATEGORIES = ['Research','Development','Support','General'] as const` + `TEMPLATE_CACHE_MS = 5 * 60 * 1000`
- **Patrones a seguir:** `PROVIDER_MODELS` existente en mismo archivo

#### 5. templates_use.py — CREACIÓN (DX)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\templates_use.py`
- **Tipo de cambio:** Creación
- **Descripción:** CLI para crear agente desde template sin UI. 194 líneas. `--org-id`, `--role`, `--goal`, `--backstory`, `--tools`, `--max-iter`, `--dry-run`. Dogfooding del mapeo template→agent.
- **Interfaces clave:**
  ```python
  def use_template(
      template_name: str = Argument(help="Template name or UUID"),
      org_id: str = Option(..., "--org-id"),
      role: Optional[str] = None,
      goal: Optional[str] = None,
      backstory: Optional[str] = None,
      tools: Optional[List[str]] = None,
      max_iter: Optional[int] = None,
      dry_run: bool = False,
  ) -> None
  ```
- **Patrones a seguir:** `templates_seed.py` (Typer + Rich + get_service_client), `agent_create.py` (POST /agents payload)

#### 6. cli/main.py — MODIFICACIÓN
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\main.py`
- **Tipo de cambio:** Modificación (registro `templates use` sub-comando)
- **Descripción:** `templates_app.command("use")(use_template)` en línea 61
- **Patrones a seguir:** Registro existente de `templates_app` sub-comandos

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap templates use
- **Qué automatiza:** Crear un agente desde un template del sistema vía CLI sin abrir el dashboard. Reemplaza el flujo manual: abrir dashboard → navegar a Builder → abrir Template Picker → buscar template → "Use Template" → editar → "Save Agent"
- **Tipo:** CLI (comando Typer)
- **Ubicación:** D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\templates_use.py
- **Cómo se usa:**
  fap templates use "Research Agent" --org-id <UUID>
  fap templates use "Research Agent" --org-id <UUID> --dry-run
  fap templates use "<template_uuid>" --org-id <UUID> --role "Custom Role" --max-iter 7
- **Impacto para el usuario final:** Reduce creación de agente desde template de ~30s (UI) a ~2s (CLI). Permite scripting/batch creation. Dogfooding: valida mapeo template→agent antes de implementar UI.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso.
```

**Herramienta complementaria (infraestructura preexistente):** `fap templates seed` (`src/cli/commands/templates_seed.py`) — pobla 8 system templates en Supabase. Setup inicial de 15min (SQL manual) → 1s. Idempotente (check-then-insert). No es Tarea 0 de este paso (pertenece al Paso 03) pero es prerequisito para que TemplatePicker tenga datos.

**NOTA sobre propuesta de mm2.7 (`fap templates validate`):** Rechazada para MVP. Los 8 system templates son seedados por sistema y confiables. Un validador de `soul_json` sería post-MVP. La propuesta de hy3 (`scripts/seed_templates.py`) es incorrecta — el seed ya existe en `src/cli/commands/templates_seed.py`, path correcto según `proyecto-config.json`.

---

## 4️⃣ Decisiones Tecnológicas

1. **Double fetch (lista sin `soul_json` + detalle con `soul_json`):** `TemplateInfo` no incluye `soul_json` para evitar payloads JSONB grandes en listado. Solo al hacer "Use Template" se obtiene el detalle completo. Trade-off consciente: ~100-300ms de latencia extra vs payloads de grid más ligeros. Post-MVP: `?include=soul_json` en endpoint lista.

2. **Prop `templateData` sobre `forwardRef`:** Elegido prop simple en `AgentForm` con `useEffect` + `reset()` en lugar de exponer `ref.reset()` vía `forwardRef`. Menos refactoring, mismo resultado. Consistente con patrón de props drilling del proyecto.

3. **Categorías hardcodeadas como constante `TEMPLATE_CATEGORIES`:** 4 categorías fijas (`Research`, `Development`, `Support`, `General`) en `constants.ts`. Evita endpoint extra para MVP. Seed usa las mismas categorías → consistencia garantizada. Post-MVP: endpoint dinámico `GET /api/templates/categories`.

4. **Búsqueda client-side solo por `name`:** `t.name.toLowerCase().includes(q)`. Con 8 templates es instantáneo. Post-MVP: ampliar a `description` + `category`, o full-text search en backend si >50 templates.

5. **Sin validación de `suggested_tools` contra `ToolRegistry`:** Los badges muestran strings arbitrarios del seed. `POST /agents` persiste `allowed_tools` sin validar existencia. Aceptable MVP — las tools del seed son mayoritariamente builtin. Post-MVP: cross-check contra `GET /api/tools/available`.

6. **Sin confirmación al sobrescribir formulario:** `reset()` pisa datos del usuario sin warning. MVP acepta el riesgo (el usuario acaba de abrir el picker, es poco probable que tenga datos valiosos sin guardar). Post-MVP: diálogo "You have unsaved changes. Overwrite?".

7. **Correcciones al plan:**
   - ⚠️ El plan dice "Botón 'Use Template' → rellena el formulario" pero no especifica cómo. El código real usa `mapTemplateToFormValues()` + `AgentForm.reset(templateData)` vía `useEffect`. Se implementa con prop `templateData`.
   - ⚠️ El plan asume que `GET /api/templates` retorna `soul_json` para cards. El código real separa `TemplateInfo` (lista, sin `soul_json`) de `TemplateDetailResponse` (detalle, con `soul_json`). Se implementa double fetch.
   - ⚠️ El plan no menciona `soul_json` del seed incompleto. El código real tiene fallbacks en `mapTemplateToFormValues()` para `llm_provider`, `llm_model`, `verbose`, `reasoning`, `inject_date`, `memory`.

---

## 5️⃣ Criterios de Aceptación MVP

### Por capa
```
✅ [DATA]    Tabla agent_templates existe con columnas: id, name, description, category, soul_json, suggested_tools, max_iter, is_system, created_at, updated_at
✅ [DATA]    RLS: SELECT para authenticated, ALL solo para service_role
✅ [DATA]    Índice parcial UNIQUE(name) WHERE is_system=TRUE previene duplicados de system templates
✅ [DATA]    Índice idx_agent_templates_category para filtro eficiente
✅ [CODE]    TemplatePicker.tsx renderiza grid de cards con name, description, category, suggested_tools
✅ [CODE]    TemplatePicker tiene 4 estados visuales: loading (skeletons ×6), error (EmptyState+Retry), empty (EmptyState+seed hint), data (cards)
✅ [CODE]    AgentForm acepta prop templateData y aplica reset() vía useEffect post-montaje
✅ [CODE]    mapTemplateToFormValues() extrae soul_json.role → role plano con fallbacks defensivos
✅ [CODE]    Double fetch: GET /api/templates (lista) + GET /api/templates/{id} (detalle) al hacer "Use Template"
✅ [CODE]    Búsqueda client-side case-insensitive por nombre
✅ [CODE]    Filtro chips (All + 4 categorías) reactivo sin recarga
✅ [CODE]    LoadingSpinner en botón "Use Template" durante fetch de detalle
✅ [CODE]    Botón "Clear" resetea formulario + limpia templateData
✅ [BACKEND] GET /api/templates devuelve {templates: TemplateInfo[], count: int} con filtro ?category= opcional
✅ [BACKEND] GET /api/templates/{id} devuelve TemplateDetailResponse con soul_json completo o 404
✅ [BACKEND] Endpoints sin require_org_id — catálogo público (RLS autenticado vía auth.role())
✅ [FULLSTACK] Usuario abre Template Picker desde Builder (botón "Templates") → explora templates → filtra/busca → clic "Use Template" → formulario autocompletado
✅ [FULLSTACK] Template Picker se cierra al seleccionar template y formulario muestra datos del template
✅ [FULLSTACK] Usuario puede editar cualquier campo después de aplicar template y guardar agente
✅ [FULLSTACK] TemplatePicker Dialog responsive: max-w-3xl max-h-[80vh] overflow-y-auto
✅ [DX]      fap templates seed ejecuta sin errores y siembra 8 templates (check-then-insert idempotente)
✅ [DX]      fap templates use "Research Agent" --org-id <UUID> crea agente desde template vía CLI
✅ [DX]      fap templates use "Research Agent" --org-id <UUID> --dry-run imprime payload sin insertar
```

### Funcionales
- [x] TemplatePicker visible desde builder (botón "Templates" en panel derecho)
- [x] Templates cargan desde API real (`GET /api/templates`)
- [x] Cards muestran: nombre, descripción (line-clamp-2), categoría badge, suggested_tools badges
- [x] Botón "Use Template" rellena AgentForm con datos del template
- [x] Filtro por categoría funciona (chips Badge: All, Research, Development, Support, General)
- [x] Barra de búsqueda por nombre funciona (client-side, case-insensitive)
- [x] Estados de carga (skeletons), error (EmptyState+Retry) y vacío (EmptyState+seed hint) manejados

### Técnicos
- [x] `mapTemplateToFormValues()` maneja `soul_json` incompleto con fallbacks `??`
- [x] Provider validation: solo `groq`, `openai`, `anthropic`, `openrouter` aceptados; fallback a `groq`
- [x] `TEMPLATE_CATEGORIES` constante exportada desde `constants.ts`
- [x] `TEMPLATE_CACHE_MS = 5 * 60 * 1000` — staleTime para React Query
- [x] Router `templates` registrado en `main.py:30,113` (NO en `__init__.py`)
- [x] CLI `templates use` registrado en `main.py:35,61`
- [x] 7 tests unitarios templates: `tests/unit/test_templates.py` — list, filter, detail, 404, auth, soul_json

---

## 6️⃣ Plan de Implementación

> **NOTA:** Paso 05 ya implementado y archivado. Este plan documenta la estructura real para trazabilidad.

| # | Tarea | Artefacto | Interfaz exacta | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling: `fap templates use`** | `src/cli/commands/templates_use.py` | `def use_template(template_name: str, org_id: str, role?: str, goal?: str, backstory?: str, tools?: List[str], max_iter?: int, dry_run?: bool) -> None` | Media | 1.5h | Ninguna (dogfooding pre-UI) |
| 1 | Constantes frontend | `dashboard/lib/constants.ts` | `TEMPLATE_CATEGORIES = ['Research','Development','Support','General'] as const`, `TEMPLATE_CACHE_MS = 5*60*1000` | Baja | 0.15h | Ninguna |
| 2 | Componente TemplatePicker | `dashboard/components/builder/TemplatePicker.tsx` | `function TemplatePicker({ onSelect }: TemplatePickerProps)` — 4 estados, búsqueda, filtro chips, "Use Template" con double fetch | Alta | 2.5h | Tarea 1 |
| 3 | Prop `templateData` en AgentForm | `dashboard/components/builder/AgentForm.tsx` | `templateData?: AgentFormData \| null` + `useEffect(() => { if (templateData) reset(templateData) }, [templateData])` | Baja | 0.5h | Tarea 2 |
| 4 | `mapTemplateToFormValues` en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | `function mapTemplateToFormValues(template: TemplateDetail): AgentFormData` — whitelist providers, fallbacks | Media | 0.5h | Tarea 3 |
| 5 | Integrar TemplatePicker en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | `handleSelectTemplate(template)`, `handleClear()`, Dialog modal, estado `dialogOpen`/`templateData` | Media | 1h | Tareas 2-4 |
| 6 | Registro CLI `templates use` | `src/cli/main.py` | `templates_app.command("use")(use_template)` | Baja | 0.1h | Ninguna |
| 7 | Validación E2E | — | Abrir Builder → Templates → seleccionar "Research Agent" → formulario relleno → editar → Save → verificar en `agent_catalog` | Baja | 0.5h | Tareas 1-6 |
| **TOTAL** | | | | | **6.75h** | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap templates use` para validar el mapeo template→agent antes de construir la UI. Dogfooding obligatorio.

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Pérdida de datos del formulario sin confirmación | Media | `reset()` sobrescribe `AgentForm` sin warning si el usuario ya tenía datos | MVP acepta riesgo. Post-MVP: diálogo "¿Sobrescribir formulario actual?" antes de aplicar template |
| Seed `soul_json` incompleto causa defaults silenciosos | Baja | Templates seed no incluyen `llm_provider`, `llm_model`, `verbose`, etc. → todos caen a groq/llama-3.1/false | Fallbacks explícitos en `mapTemplateToFormValues()`. Post-MVP: enriquecer seed con esos campos |
| Double fetch latencia en redes lentas | Baja | 2 HTTP calls secuenciales al hacer "Use Template" (lista cacheada, detalle fresh) | `staleTime: 5min` en lista. Detalle ~1KB JSON → latencia ~100-300ms. Post-MVP: `?include=soul_json` param |
| `suggested_tools` muestra tools inexistentes | Baja | Templates referencian tools por string sin FK; `search`, `code_analyzer` pueden no existir | Badge se muestra igual. Post-MVP: cross-check contra `GET /api/tools/available` |
| Filtro client-side no escala con >100 templates | Baja | `useMemo` filtra array completo en cada re-render. Con 8 templates instantáneo | Post-MVP (>50 templates): server-side filtering con `?search=` param |
| Error 404 en detail no diferenciado de error de red | Media | `handleUseTemplate` captura error genérico → `toast.error('Failed to load template details')` | Post-MVP: distinguir status 404 ("Template not found — was deleted?") vs 5xx/network ("Server error — retry?") |
| Categorías nuevas no aparecen en chips de filtro | Baja | `TEMPLATE_CATEGORIES` hardcodeado. Si admin añade categoría "AI" vía seed, no se puede filtrar por chip | "All" muestra todas. Post-MVP: endpoint `GET /api/templates/categories` dinámico |
| RLS `service_role` comprometido → templates modificables | Alta | Cualquiera con service_role key puede INSERT/UPDATE/DELETE templates. Clave en `.env` del backend | Rotación periódica de service_role key. Auditoría de cambios en `agent_templates`. Post-MVP: firma criptográfica de system templates |

---

## 8️⃣ Testing Mínimo Viable

### Casos de prueba concretos

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | TemplatePicker carga templates | GET /api/templates | 200, `{ templates: [...8 items], count: 8 }` |
| TP-2 | Filtro por categoría | GET /api/templates?category=Research | 200, `count: 1`, template "Research Agent" |
| TP-3 | Template inexistente | GET /api/templates/00000000-0000-0000-0000-000000000000 | 404, `{ "detail": "Template not found" }` |
| TP-4 | "Use Template" llena formulario | Seleccionar "Research Agent" → click "Use Template" | AgentForm muestra role="Research Specialist", goal, backstory, tools, max_iter=5 |
| TP-5 | Template sin `role` en soul_json | Template con `soul_json: { goal: "test", backstory: "test" }` | AgentForm muestra role = template.name (fallback) |
| TP-6 | Template con provider inválido | `soul_json.llm_provider = "invalid_provider"` | AgentForm muestra `llmProvider = "groq"` (fallback) |
| TP-7 | Búsqueda filtra correctamente | Escribir "Code" en barra de búsqueda | Solo "Code Reviewer" visible en grid |
| TP-8 | CLI `fap templates use` --dry-run | `fap templates use "Research Agent" --org-id test-uuid --dry-run` | Imprime payload sin insertar en DB |
| TP-9 | CLI `fap templates use` sin template | `fap templates use "NonExistent" --org-id test-uuid --dry-run` | Error: template not found |
| TP-10 | Seed idempotente | Ejecutar `fap templates seed` 2 veces | Segunda ejecución: 8 skipped (ya existen) |

### Comandos para ejecutar tests

```
{commands.test_unit}:   uv run pytest tests/unit/ -v --timeout=60
{commands.test_integration}: uv run pytest tests/integration/ -v --timeout=60
```

Tests unitarios existentes: `tests/unit/test_templates.py` — 7 tests (list, filter, detail, 404, auth, soul_json). 7/7 pasan.
Tests E2E planificados en Paso 10: validar flujo TemplatePicker → fill → save → agent creado.

---

## 📊 Métrica de Calidad del FINAL

| Métrica | Mínimo | Real | Estado |
|---|---|---|---|
| `proyecto-config.json` leído antes de generar | 100% | ✅ | Cumple |
| Discrepancias consolidadas con resolución | 100% detectadas | 7/7 | ✅ Cumple |
| Correcciones al plan documentadas | Todas encontradas | 3 correcciones | ✅ Cumple |
| Propuesta DX incluida en §3 y Tarea 0 en §6 | Obligatorio | `fap templates use` | ✅ Cumple |
| Criterio DX en §5 | Obligatorio | 3 criterios DX | ✅ Cumple |
| Secciones completadas | 9 (0-8) | 9/9 | ✅ Cumple |
| Casos de testing | ≥ 3 casos concretos | 10 casos | ✅ Cumple |
| Tiempo estimado por tarea | 100% | 7 tareas con estimación | ✅ Cumple |
| Evaluación de calidad de agentes | Obligatorio | 7 agentes evaluados | ✅ Cumple |
| Fusión/resolución de propuestas DX conflictivas | Obligatorio | Propuestas mm2.7 y hy3 rechazadas con justificación | ✅ Cumple |

---

> **Unificación completada.** Paso 05 implementado, validado y archivado. 7 análisis consolidados. DX tooling (`fap templates use`) verificado funcional. Ready para Paso 06 (Agent Playground).
