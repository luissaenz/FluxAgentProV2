# Análisis Técnico — Paso 14: Optimización de UX y Rendimiento Frontend

**Agente:** dsp
**Fecha:** 2026-05-18
**Fase:** guiAgentGenerator
**Origen:** Sugerencias 🔵 de validación (ID-017, ID-018, ID-019, ID-021, ID-026, ID-034, ID-035, ID-038, ID-044, ID-045, ID-046, ID-048, ID-050, ID-042, ID-043)

> **Contexto de fase:** `DEVS/phase-state.md` — Pasos 1-13 completados. Paso 14 en progreso. No hay sugerencias pendientes en `sugest.md`.

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `useClickOutside` hook | grep en `dashboard/hooks/` | ❌ DISCREPANCIA | No existe. Lógica inline en `ToolMultiSelect.tsx:32-40` con `useEffect` + `mousedown` listener |
| 2 | `useDebounce` hook | grep en `dashboard/hooks/` | ❌ DISCREPANCIA | No existe. Sin debounce en ningún componente builder |
| 3 | ReactFlow CSS import | `CrewCanvas.tsx:48` | ✅ VERIFICADO | `import 'reactflow/dist/style.css'` — carga estática, bloquea bundle principal |
| 4 | `useMemo` en `canvasToExportPayload` | `CrewCanvas.tsx:207` | ✅ VERIFICADO | `const exportPayload = useMemo(() => canvasToExportPayload(nodes), [nodes])` |
| 5 | `useMemo` en `nodesToSnapshot` | `CrewCanvas.tsx:209` | ✅ VERIFICADO | `const fullGraphJson = useMemo(() => nodesToSnapshot(nodes, edges), [nodes, edges])` |
| 6 | `useMemo` en `exportAgents` | `CrewCanvas.tsx:211-218` | ✅ VERIFICADO | Mapeo memoizado de exportPayload.agents a AgentExportItem[] |
| 7 | `useMemo` en `buildSingleAgentPayload` | `AgentForm.tsx:203-222` | ❌ DISCREPANCIA | Es función plana — se recrea en cada render, llamada 2× en línea 399 y 401 |
| 8 | `cmdk` dependency | `dashboard/package.json` | ❌ DISCREPANCIA | No instalado — no existe en dependencies ni devDependencies |
| 9 | Debounce en campos de texto | `AgentForm.tsx:248-263` | ❌ DISCREPANCIA | `goal` y `backstory` son Textarea controlados por react-hook-form sin delay |
| 10 | `lib/template-mapper.ts` | `dashboard/lib/` | ❌ DISCREPANCIA | No existe. `mapTemplateToFormValues` inline en `BuilderLayout.tsx:28-50` |
| 11 | Query params `?tab=` | `BuilderTabContext.tsx:29` | ❌ DISCREPANCIA | Solo `useState(defaultTab)` — sin sincronización con `useSearchParams` ni `useRouter` |
| 12 | `page.tsx` del builder | `builder/page.tsx:7-19` | ✅ VERIFICADO | `BuilderTabProvider` envuelve toda la página, `defaultTab="agent-form"` hardcodeado |
| 13 | `navigator.clipboard` fallback | `ExportDialog.tsx:91-98` | ✅ VERIFICADO | try/catch con toast de error mostrando primeras 500 chars |
| 14 | Scroll ref en `AgentPlayground` | `AgentPlayground.tsx:56,182` | ⚠️ AMBIGUO | `scrollRef` apunta a `<div>` dentro de `<ScrollArea>`. ScrollArea maneja su propio scroll interno — posible conflicto de referencias |
| 15 | `eslint-disable` active | `AgentForm.tsx:228`, `CrewCanvas.tsx:113` | ✅ VERIFICADO | 2 instancias: una en `useEffect` de llmModel, otra en snapshot restore |
| 16 | `api.ts` soporta métodos HTTP | `api.ts:96-118` | ✅ VERIFICADO | `api.get`, `api.post`, `api.put`, `api.patch`, `api.delete` — cobertura completa |
| 17 | `fapDownload` hardcodea POST | `api.ts:73` | ⚠️ NO VERIFICABLE | `method: 'POST'` fijo. Solo un endpoint de descarga binaria hoy (`POST /bundles/export`) |
| 18 | Constantes de export hardcodeadas | `ExportDialog.tsx:72,112` | ⚠️ NO VERIFICABLE | `15` agents limit duplicado en frontend y backend (`max_length=15` en Pydantic). Sin constante compartida |
| 19 | `duplicatedRoles` computed | `CrewCanvas.tsx:339-349` | ⚠️ NO VERIFICABLE | IIFE inline — calculado en cada render, sin `useMemo` |
| 20 | `nodesWithWarnings` computed | `CrewCanvas.tsx:354-357` | ⚠️ NO VERIFICABLE | Calculado en cada render — sin `useMemo` |
| 21 | `hasAgentNodes` / `exportDisabled` | `CrewCanvas.tsx:351-352` | ⚠️ NO VERIFICABLE | Derivados inline en cada render — sin `useMemo` |
| 22 | `sidebarAgents` | `CrewCanvas.tsx:337` | ⚠️ NO VERIFICABLE | `agentsData?.agents ?? []` — recalculado cada render |
| 23 | `toolOptions` en AgentForm | `AgentForm.tsx:135-139` | ⚠️ NO VERIFICABLE | `.map()` ejecutado en cada render — sin `useMemo` |
| 24 | `availableModels` en AgentForm | `AgentForm.tsx:141` | ⚠️ NO VERIFICABLE | Lookup directo `PROVIDER_MODELS[llmProvider] ?? []` en cada render |
| 25 | `filtered`/`grouped` en ToolMultiSelect | `ToolMultiSelect.tsx:42-59` | ✅ VERIFICADO | Ambos con `useMemo` correcto |
| 26 | `filtered` en TemplatePicker | `TemplatePicker.tsx:74-84` | ✅ VERIFICADO | `useMemo` con dependencias `[templates, selectedCategory, search]` |
| 27 | `BuilderErrorBoundary` class component | `BuilderErrorBoundary.tsx:13-55` | ✅ VERIFICADO | Class component con `getDerivedStateFromError` + retry |
| 28 | `BuilderCanvas` dynamic import SSR | `BuilderCanvas.tsx:6-8` | ✅ VERIFICADO | `dynamic(() => import('@/components/builder/CrewCanvas').then(...), { ssr: false })` |
| 29 | Hook `useCurrentOrg` patrón de referencia | `hooks/useCurrentOrg.ts` | ✅ VERIFICADO | Patrón: export function hookName() retorna objeto con estado |
| 30 | Patrón de hooks existentes | `hooks/use-theme.tsx`, `hooks/useFlows.ts` | ✅ VERIFICADO | Cada hook en archivo separado, export function, usa React hooks internos |

**Discrepancias encontradas (12):**

1. **ID-017:** `useClickOutside` no existe como hook reutilizable. `ToolMultiSelect.tsx:32-40` tiene lógica inline duplicable.
2. **ID-019:** `CrewCanvas.tsx:48` importa CSS de ReactFlow estáticamente (`import 'reactflow/dist/style.css'`). No usa carga diferida, bloquea bundle principal.
3. **ID-021:** `cmdk` no instalado en `package.json`. El plan sugiere "evaluar migración a cmdk" pero no hay base instalada para evaluación.
4. **ID-034:** Sin debounce en campos `goal`/`backstory` de `AgentForm`. Cada keystroke dispara re-render completo del formulario.
5. **ID-026:** `mapTemplateToFormValues` inline en `BuilderLayout.tsx:28-50`. Debe extraerse a `lib/template-mapper.ts`.
6. **ID-050:** `BuilderTabContext` usa solo `useState` — sin sincronización con URL `?tab=`. No hay deep linking entre pestañas.
7. **ID-046/ID-048:** `AgentForm.tsx:401` llama `buildSingleAgentPayload()` 2 veces en mismo render (línea 399 para `agents`, línea 401 para `fullGraphJson`). Sin `useMemo`.
8. **ID-035:** `AgentPlayground.tsx:56-62` `scrollRef` apunta a `<div>` dentro de `<ScrollArea>`. ScrollArea tiene su propia viewport con scroll interno — posible conflicto de referencias.
9. **ID-038:** `AgentForm.tsx:228` y `CrewCanvas.tsx:113` tienen `eslint-disable` sin justificación documentada clara del porqué es seguro omitir dependencias.
10. **ID-045:** `ExportDialog.tsx:94-99` fallback de clipboard solo muestra 500 chars en toast. No ofrece área de texto para copia manual completa.
11. **ID-042:** `fapDownload` en `api.ts:73` hardcodea `method: 'POST'`. Si se necesita GET para descarga binaria futura, requiere refactor.
12. **ID-043:** Límite `15` agents duplicado en `ExportDialog.tsx:72,112` y backend (Pydantic `max_length=15`). Sin constante centralizada ni en `constants.ts` ni compartida con backend.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

> Paso 14 es puramente frontend. No hay cambios en schema de DB, migraciones ni datos persistentes.

- **Sin nuevas tablas ni columnas.** El paso no modifica `agent_catalog`, `agent_templates`, `workflow_templates` ni ninguna tabla existente.
- **Sin impacto en integridad referencial.** Sin cambios en foreign keys ni constraints.
- **Sin RLS policies nuevas.** Las policies existentes (`tenant_isolation` en `agent_catalog`) no se alteran.
- **Sin índices necesarios.** No se crean ni modifican consultas a DB.

**Única consideración de datos:** El `BuilderTabContext` persistirá estado de tabs vía query params (`?tab=`), no en DB ni localStorage. Es estado de UI efímero. La elección de query params sobre localStorage es correcta: permite compartir URLs, bookmarks, y evita el problema de estado compartido entre pestañas del navegador que localStorage introduce.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 2.1 Hook `dashboard/hooks/useClickOutside.ts` (Nuevo — ID-017)

**Patrón de referencia:** `dashboard/hooks/useCurrentOrg.ts` y `dashboard/hooks/use-theme.tsx` — hooks exportados como función nombrada, sin default export, usando React hooks nativos.

**Firma exacta:**
```typescript
import { type RefObject, useEffect } from 'react'

export function useClickOutside(
  ref: RefObject<HTMLElement | null>,
  handler: () => void,
  enabled?: boolean
): void
```

**Comportamiento:** Registra listener `mousedown` en `document`. Si el clic es fuera de `ref.current`, ejecuta `handler`. Cleanup en return de `useEffect`. Parámetro `enabled` (default `true`) permite deshabilitar condicionalmente (ej: cuando el dropdown está cerrado).

**Ejemplo de uso en ToolMultiSelect:**
```typescript
// Reemplaza líneas 32-40 actuales
useClickOutside(containerRef, () => setOpen(false))
```

**Extracción desde código existente:** La lógica ya existe inline en `ToolMultiSelect.tsx:32-40`:
```typescript
useEffect(() => {
  function handleClickOutside(e: MouseEvent) {
    if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
      setOpen(false)
    }
  }
  document.addEventListener('mousedown', handleClickOutside)
  return () => document.removeEventListener('mousedown', handleClickOutside)
}, [])
```

### 2.2 Hook `dashboard/hooks/useDebounce.ts` (Nuevo — ID-034)

**Firma exacta:**
```typescript
export function useDebounce<T>(value: T, delay: number): T
```

**Comportamiento:** Retorna `value` tras `delay` ms de inactividad. Implementación estándar con `useState` + `useEffect` + `setTimeout`/`clearTimeout`.

**Ejemplo de uso (no inmediato en este paso, pero propuesto como DX):**
```typescript
const debouncedGoal = useDebounce(goalValue, 300)
```

> ⚠️ **Nota:** Aplicar debounce a campos de `react-hook-form` no es trivial porque `register()` vincula directamente al DOM. El debounce aplicaría a búsquedas (TemplatePicker, ToolMultiSelect) o validaciones asíncronas, no a campos de formulario controlados por RHF. Para formularios se recomienda usar `useMemo` en derivados o lazy validation de Zod con `mode: 'onBlur'`.

### 2.3 Archivo `dashboard/lib/template-mapper.ts` (Nuevo — ID-026)

**Patrón de referencia:** `dashboard/lib/canvasUtils.ts` — funciones puras exportadas como named exports, sin dependencias de React, con tipos locales o importados de `types.ts`.

**Firma exacta:**
```typescript
import type { AgentFormData } from '@/components/builder/AgentForm'
import type { TemplateDetail } from '@/components/builder/TemplatePicker'

export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData
```

**Extracción desde código existente:** Mover `BuilderLayout.tsx:28-50` íntegro, con sus tipos locales (`Provider`, `mapProvider`) internalizados en el módulo. La lógica de mapeo es pura (sin efectos secundarios, sin estado), ideal para `lib/`.

**Código a extraer (BuilderLayout.tsx:28-50):**
```typescript
function mapTemplateToFormValues(template: TemplateDetail): AgentFormData {
  const soul = template.soul_json ?? {}
  const valid = ['groq', 'openai', 'anthropic', 'openrouter'] as const
  type Provider = AgentFormData['llmProvider']

  function mapProvider(provider?: string): Provider {
    return (valid as readonly string[]).includes(provider ?? '') ? (provider as Provider) : 'groq'
  }

  return {
    role: (soul.role as string) ?? template.name ?? '',
    goal: (soul.goal as string) ?? '',
    backstory: (soul.backstory as string) ?? template.description ?? '',
    llmProvider: mapProvider(soul.llm_provider as string),
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

### 2.4 Mejoras de `useMemo` en AgentForm (ID-046, ID-048)

**Problema detectado:** `AgentForm.tsx:399-403` — `buildSingleAgentPayload()` es función plana llamada 2 veces en render (línea 399 y 401):

```tsx
// Línea 398-403 actual
<ExportDialog
  open={exportDialogOpen}
  onOpenChange={setExportDialogOpen}
  agents={buildSingleAgentPayload().agents}       // llamada 1
  source="agent-form"
  fullGraphJson={JSON.stringify(buildSingleAgentPayload(), null, 2)}  // llamada 2
  onExportComplete={() => setExportDialogOpen(false)}
/>
```

**Solución:** Envolver en `useMemo` + dependencias derivadas de `watch()`:

```typescript
const buildSingleAgentPayload = useMemo(() => {
  const values = getValues()
  return { agents: [{ role: values.role, soul_json: { goal: values.goal, ... }, allowed_tools: values.allowedTools, max_iter: values.maxIter }] }
}, [getValues])  // o usar dependencias específicas de cada campo
```

> ⚠️ **Cuidado:** `getValues()` no es reactivo — no dispara re-memoización al cambiar campos. Alternativa: calcular desde `watch()` de cada campo individual.

### 2.5 Mejoras de `useMemo` en CrewCanvas

**Derivados no memoizados que se recalculan en cada render:**
- `duplicatedRoles` (línea 339-349) — IIFE que itera `nodes` filtrando agentNodes
- `nodesWithWarnings` (línea 354-357) — filtra `nodes` buscando agentes sin edges
- `hasAgentNodes` (línea 351) — `nodes.some()`
- `exportDisabled` (línea 352) — booleano derivado de `hasAgentNodes` y `duplicatedRoles`
- `sidebarAgents` (línea 337) — `agentsData?.agents ?? []`

**Recomendación:** Envolver en `useMemo` para evitar recálculos en renders no relacionados con `nodes` o `edges`:

```typescript
const duplicatedRoles = useMemo(() => { ... }, [nodes])
const nodesWithWarnings = useMemo(() => { ... }, [nodes, edges])
const sidebarAgents = useMemo(() => agentsData?.agents ?? [], [agentsData])
```

### 2.6 Mejoras de `useMemo` en AgentForm

**Derivados no memoizados:**
- `toolOptions` (línea 135-139) — `.map()` ejecutado en cada render
- `availableModels` (línea 141) — lookup de objeto en cada render

**Solución:**
```typescript
const toolOptions = useMemo(() =>
  (toolsResponse?.tools ?? []).map((t) => ({
    value: t.name,
    label: t.label || t.name,
    source: t.source || 'local',
  })), [toolsResponse])

const availableModels = useMemo(() =>
  PROVIDER_MODELS[llmProvider] ?? [], [llmProvider])
```

### 2.7 Fix de dependencias `useEffect` (ID-018, ID-038)

**Problema 1 — `AgentForm.tsx:224-229`:**
```typescript
useEffect(() => {
  if (availableModels.length > 0 && !availableModels.includes(watch('llmModel'))) {
    setValue('llmModel', availableModels[0])
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [llmProvider])
```

`watch('llmModel')` se llama dentro del efecto pero no está en el array de dependencias. `eslint-disable` suprime la advertencia sin justificación documentada.

**Solución:** Usar `getValues('llmModel')` y agregarlo como dependencia, o reestructurar usando el valor ya disponible vía `watch` fuera del efecto:

```typescript
const llmModel = watch('llmModel')
useEffect(() => {
  if (availableModels.length > 0 && !availableModels.includes(llmModel)) {
    setValue('llmModel', availableModels[0])
  }
}, [llmProvider, availableModels, llmModel, setValue])
```

**Problema 2 — `CrewCanvas.tsx:113`:**
```typescript
// eslint-disable-next-line react-hooks/exhaustive-deps -- snapshot restore only on mount
}, [])
```

Este caso es legítimo (restauración única al montar), pero falta documentación explícita de por qué es seguro.

### 2.8 Modularidad General

**Estado actual:** Buena modularidad en componentes (cada componente en su archivo). Puntos débiles:
- `mapTemplateToFormValues` inline en `BuilderLayout` rompe separación de concerns (UI + lógica de negocio)
- `useClickOutside` inline en `ToolMultiSelect` — duplicación futura si otro componente necesita mismo comportamiento
- `fapDownload` en `api.ts` con método hardcodeado — inflexible para futuros endpoints de descarga

---

## 3️⃣ Análisis de Backend (ETAPA 3)

> Paso 14 es puramente frontend. No hay cambios en APIs, middleware ni servicios backend.

**Sin endpoints nuevos ni modificados.** Los endpoints consumidos (`GET /api/tools/available`, `GET /api/templates`, `POST /agents`, `POST /bundles/export`, etc.) permanecen sin cambios.

**Consideración de contratos:**
- `POST /bundles/export` acepta `max_length=15` en Pydantic. El frontend duplica este límite en `ExportDialog.tsx:72` (`exceedsLimit = agents.length > 15`). Si el límite cambia en backend, el frontend queda desincronizado.
- `fapDownload` en `api.ts` asume `Content-Type: application/json` para todas las descargas. Correcto para `POST /bundles/export` hoy. Si en futuro se necesita `GET` con `Accept: application/zip`, la función no lo soporta.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end actual

```
┌──────────────┐    ┌───────────────┐    ┌────────────┐    ┌───────────┐
│ Builder Page │───▶│ BuilderLayout │───▶│ AgentForm  │───▶│ Supabase  │
│ (page.tsx)   │    │ (Tabs UI)     │    │ (RHF+Zod)  │    │ agent_    │
│              │    │               │    │            │    │ catalog   │
│ ?tab=        │    │ activeTab ◀──│    │ watch()    │    │           │
│ query param  │    │ useState      │    │ re-renders │    │           │
└──────────────┘    └───────────────┘    └────────────┘    └───────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────┐    ┌───────────────┐    ┌───────────────┐
│ BuilderBread │    │ AgentPlaygrnd │    │ ExportDialog  │
│ crumb        │    │ (Sheet)       │    │ (Dialog)      │
│ reactivo a   │    │ polling GET   │    │ POST /bundles │
│ activeTab    │    │ /tasks/{id}   │    │ /export → ZIP │
└──────────────┘    └───────────────┘    └───────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────┐    ┌───────────────┐    ┌───────────────┐
│ CrewCanvas   │    │ TemplatePickr │    │ fapDownload() │
│ ReactFlow    │    │ (Dialog)      │    │ api.ts        │
│ dynamic SSR  │    │ GET /template │    │ hardcoded POST│
└──────────────┘    └───────────────┘    └───────────────┘
```

### Puntos de fricción detectados

1. **Tabs sin deep linking:** Usuario no puede compartir URL `.../builder?tab=crew-canvas`. Siempre llega a `agent-form`.
2. **CSS bloqueante:** `reactflow/dist/style.css` (~15KB) se incluye en bundle principal aunque el canvas es `dynamic(ssr: false)`.
3. **Re-renders innecesarios:** `AgentForm` re-renderea en cada keystroke de `goal`/`backstory`. `CrewCanvas` recalcula 5 derivados en cada render sin `useMemo`.
4. **Clipboard UX pobre:** Si `navigator.clipboard` falla (HTTP, iframe, permisos), el usuario solo ve 500 caracteres en un toast — inservible para JSON de 10KB+.
5. **Lógica de negocio acoplada a UI:** `mapTemplateToFormValues` vive en `BuilderLayout` — no testeable de forma aislada, no reutilizable.

### Coherencia con el MVP

El paso 14 no introduce funcionalidad nueva — optimiza lo existente. El MVP (pasos 1-10) ya funciona end-to-end. Este paso aplica "polish" que:
- Reduce tiempo de carga percibido (CSS lazy)
- Permite compartir estado vía URL (deep linking)
- Mejora mantenibilidad (hooks reutilizables, lógica extraída)
- Reduce bugs futuros (dependencias de useEffect correctas)

**Conclusión:** El plan es realizable con la arquitectura existente. Todos los cambios son incrementales sobre código ya desplegado.

---

### Herramienta DX Propuesta 1: `useClickOutside` + `useDebounce` hooks bundle

- **Qué automatiza:** Extracción de lógica repetitiva de manejadores de eventos `mousedown` y debounce de valores. Evita que cada componente nuevo re-implemente click-outside o debounce manualmente.
- **Tipo:** Hooks reutilizables (librería interna)
- **Cómo se usa:**
```typescript
// En cualquier componente
import { useClickOutside } from '@/hooks/useClickOutside'
import { useDebounce } from '@/hooks/useDebounce'

function MyDropdown() {
  const ref = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  useClickOutside(ref, () => setOpen(false))
  // ...
}
```
- **Impacto para el usuario final:** Menos bugs de UI (dropdowns que no cierran, búsquedas que disparan requests en cada keystroke). Desarrollo más rápido de nuevos selectores/dropdowns.
- **Prioridad:** Tarea 0 — implementar antes de refactorizar ToolMultiSelect.

### Herramienta DX Propuesta 2: `lib/template-mapper.ts` con tests unitarios

- **Qué automatiza:** Centraliza la lógica de mapeo template→formulario. Permite testear la transformación de datos aislada de React. Si el schema de `agent_templates` cambia, solo se modifica este archivo.
- **Tipo:** Módulo de utilidades (funciones puras)
- **Cómo se usa:**
```typescript
import { mapTemplateToFormValues } from '@/lib/template-mapper'
const formData = mapTemplateToFormValues(templateDetail)
```
- **Impacto para el usuario final:** Templates se aplican consistentemente sin importar desde dónde se invoquen. Si se añade un "Quick Apply" en otro punto de la UI, no hay código duplicado.
- **Prioridad:** Tarea de modularización — puede hacerse después de hooks DX.

---

## 5️⃣ Criterios de Aceptación

### Hook extraction (ID-017, ID-018)
- ✅ [CODE] Hook `useClickOutside` exportado desde `dashboard/hooks/useClickOutside.ts` con firma `(ref: RefObject<HTMLElement | null>, handler: () => void, enabled?: boolean): void`
- ✅ [CODE] Hook `useDebounce` exportado desde `dashboard/hooks/useDebounce.ts` con firma `<T>(value: T, delay: number): T`
- ✅ [CODE] `ToolMultiSelect.tsx` importa y usa `useClickOutside` — sin `useEffect` + `mousedown` inline
- ✅ [CODE] `AgentForm.tsx:224-229` useEffect tiene array de dependencias completo — sin `eslint-disable`

### Performance (ID-019, ID-046, ID-048)
- ✅ [CODE] `CrewCanvas.tsx` importa CSS de ReactFlow vía `dynamic` o `next/dynamic` con `ssr: false` — sin `import 'reactflow/dist/style.css'` estático
- ✅ [CODE] `AgentForm.tsx` `buildSingleAgentPayload` usa `useMemo` en lugar de función plana llamada 2×
- ✅ [CODE] `CrewCanvas.tsx` tiene `useMemo` en `duplicatedRoles`, `nodesWithWarnings`, `hasAgentNodes`, `exportDisabled`, `sidebarAgents`
- ✅ [CODE] `AgentForm.tsx` tiene `useMemo` en `toolOptions` y `availableModels`

### UX Components (ID-021, ID-034)
- ✅ [ANALYSIS] Decisión documentada sobre `cmdk`: adoptar, posponer o alternativa. Si se adopta → `npm install cmdk` + integración en ToolMultiSelect
- ✅ [DX] `useDebounce` implementado (ver Hook extraction) — usado al menos en búsqueda de TemplatePicker o ToolMultiSelect

### Modularization (ID-026)
- ✅ [STRUCTURE] `lib/template-mapper.ts` existe con `export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData`
- ✅ [CODE] `BuilderLayout.tsx` importa desde `@/lib/template-mapper` — no contiene la función inline

### UI Robustness (ID-035, ID-038, ID-045)
- ✅ [CODE] `AgentPlayground.tsx` scrollRef corregido: apunta al viewport de ScrollArea o usa `scrollAreaRef` nativo
- ✅ [CODE] Ambas instancias de `eslint-disable` tienen comentario justificando por qué es seguro omitir dependencias
- ✅ [UX] `ExportDialog.tsx` clipboard fallback incluye `<Textarea>` con JSON completo + botón "Copy" además del toast

### Navigation (ID-050)
- ✅ [FULLSTACK] `BuilderTabContext` sincroniza `activeTab` con `useSearchParams` (`?tab=agent-form|crew-canvas`)
- ✅ [FULLSTACK] URL `.../builder?tab=crew-canvas` abre directamente el canvas
- ✅ [FULLSTACK] Cambiar pestaña actualiza la URL sin recargar página (`router.replace`)

### Helper flexibility (ID-042, ID-043)
- ✅ [CODE] `fapDownload` acepta parámetro `method?: string` con default `'POST'`
- ✅ [CODE] `constants.ts` exporta `MAX_EXPORT_AGENTS = 15` y `ExportDialog.tsx` lo importa
- ✅ [CODE] `constants.ts` exporta `HTTP_METHODS` (opcional — si se considera útil) o al menos `DEFAULT_DOWNLOAD_METHOD = 'POST'`

### Verificaciones cruzadas
- ✅ [FULLSTACK] `tsc --noEmit` pasa sin errores en `dashboard/`
- ✅ [FULLSTACK] `npm run lint` pasa sin nuevos warnings en componentes builder
- ✅ [FULLSTACK] Flujo completo builder (crear agente → templates → playground → canvas → export) funciona sin regresiones
- ✅ [DX] `grep -rn "useClickOutside" dashboard/hooks/` devuelve al menos 1 archivo
- ✅ [DX] `grep -rn "useDebounce" dashboard/hooks/` devuelve al menos 1 archivo
- ✅ [DX] `grep -rn "mapTemplateToFormValues" dashboard/lib/template-mapper.ts` devuelve 1 match

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `cmdk` introduce dependencia pesada innecesaria | Media | `cmdk` añade ~15KB al bundle. ToolMultiSelect actual ya funciona bien con implementación custom de ~60 líneas. Costo/beneficio dudoso. | Evaluar primero: ¿el selector actual tiene problemas de UX reales? Si no → posponer `cmdk`. Si sí → implementar detrás de feature flag. |
| `useSearchParams` rompe SSR en page.tsx | Alta | `page.tsx:1` tiene `'use client'` pero `BuilderTabProvider` se renderiza del lado servidor inicialmente. `useSearchParams` necesita `Suspense` boundary en Next.js 14. | Envolver `BuilderTabProvider` en `<Suspense fallback={...}>` dentro de `page.tsx`. Verificar que no hay errores de hidratación. |
| Cambios en `useEffect` dependencias rompen comportamiento | Media | `AgentForm.tsx:224` actualiza `llmModel` automáticamente al cambiar provider. Añadir dependencias podría causar loops (setValue → watch → useEffect → setValue). | Usar `getValues('llmModel')` dentro del efecto y comparar antes de `setValue`. O usar `ref` para tracking de "ya actualizado". |
| CSS dynamic de ReactFlow causa FOUC (flash of unstyled content) | Media | Si se carga CSS dinámicamente, el canvas puede renderizar nodos sin estilo durante ~100-200ms. | Usar `next/dynamic` con `loading` skeleton. El CSS se inyecta via `import('reactflow/dist/style.css')` dentro del dynamic import, no desde `next/dynamic` directamente. Alternativa: usar `<link rel="preload">` en `head.tsx`. |
| `useMemo` excesivo en CrewCanvas reduce legibilidad | Baja | Memoizar 5+ valores simples puede hacer el código más difícil de leer sin ganancia medible de performance (ReactFlow ya es el cuello de botella real). | Solo memoizar `duplicatedRoles` y `nodesWithWarnings` (los que iteran arrays). `hasAgentNodes` y `exportDisabled` son O(1) — no justifican `useMemo`. |
| Sincronización tabs↔URL causa ciclo de actualización | Media | `useState` → `useSearchParams` → `setActiveTab` → `router.replace` → `useSearchParams` podría ciclar si no se maneja con cuidado. | Usar patrón: leer `searchParams` solo en inicialización (o con `useEffect` + flag `initialized`). Escribir con `router.replace` sin disparar re-lectura. Next.js 14 `useSearchParams` retorna objeto inmutable — seguro si se evita dependencia circular. |
| Regresión en flujo de exportación | Media | Cambiar `fapDownload` signature (añadir `method`) podría romper calls existentes si no se hace backward-compatible. | Parámetro `method` opcional con default `'POST'`. Todos los call sites existentes siguen funcionando sin cambios. |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica aplicadas:** Una tarea = un artefacto. Interfaz completa. Patrón de referencia explícito. Verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear hooks `useClickOutside` y `useDebounce` | `dashboard/hooks/useClickOutside.ts`, `dashboard/hooks/useDebounce.ts` | `export function useClickOutside(ref: RefObject<HTMLElement \| null>, handler: () => void, enabled?: boolean): void` / `export function useDebounce<T>(value: T, delay: number): T` | `dashboard/hooks/useCurrentOrg.ts` — hook simple, export nombrado, sin default | DX | Baja | 0.5h | Ninguna | → verificar: `grep -n "export function useClickOutside" dashboard/hooks/useClickOutside.ts` devuelve 1 match; `grep -n "export function useDebounce" dashboard/hooks/useDebounce.ts` devuelve 1 match |
| 1 | Refactorizar `ToolMultiSelect` — usar `useClickOutside` hook | `dashboard/components/builder/ToolMultiSelect.tsx` | Reemplazar `useEffect` inline (líneas 32-40) por `useClickOutside(containerRef, () => setOpen(false))`. Importar desde `@/hooks/useClickOutside`. | Tarea 0 (hook creado) | CODE | Baja | 0.25h | Tarea 0 | → verificar: `grep -n "useEffect.*mousedown" ToolMultiSelect.tsx` NO devuelve matches |
| 2 | Extraer `mapTemplateToFormValues` a `lib/template-mapper.ts` | `dashboard/lib/template-mapper.ts` | `export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData` — extraer líneas 28-50 de `BuilderLayout.tsx` | `dashboard/lib/canvasUtils.ts` — funciones puras, named exports, sin React | CODE | Baja | 0.5h | Ninguna | → verificar: `import { mapTemplateToFormValues } from '@/lib/template-mapper'` sin errores en BuilderLayout |
| 3 | Actualizar `BuilderLayout.tsx` — importar desde `lib/template-mapper.ts` | `dashboard/components/builder/BuilderLayout.tsx` | Eliminar función inline `mapTemplateToFormValues` (líneas 28-50). Agregar `import { mapTemplateToFormValues } from '@/lib/template-mapper'` en imports. | — (mismo componente, swap de import) | CODE | Baja | 0.25h | Tarea 2 | → verificar: `grep -n "function mapTemplateToFormValues" BuilderLayout.tsx` NO devuelve matches; template picker sigue funcionando |
| 4 | Implementar sincronización tabs↔query params (`?tab=`) | `dashboard/components/builder/BuilderTabContext.tsx`, `dashboard/app/(app)/builder/page.tsx` | `BuilderTabProvider` lee `useSearchParams().get('tab')` como valor inicial. `setActiveTab` actualiza URL vía `useRouter().replace()`. Envolver en `<Suspense>` en `page.tsx`. | Next.js 14 `useSearchParams` + `useRouter` pattern. Referencia: documentación oficial Next.js sobre `useSearchParams` en client components | FULLSTACK | Media | 1h | Ninguna | → verificar: URL `.../builder?tab=crew-canvas` abre Crew Canvas. Cambiar pestaña en UI actualiza URL a `?tab=crew-canvas` sin recargar. |
| 5 | Corregir `useEffect` dependencias en `AgentForm.tsx` (ID-018) | `dashboard/components/builder/AgentForm.tsx` | Líneas 224-229: extraer `watch('llmModel')` a variable `llmModel` fuera del efecto. Agregar `llmModel` y `setValue` al array de dependencias. Remover `eslint-disable`. Agregar comentario justificando seguridad. | — (mismo componente, mejora de hook) | CODE | Baja | 0.5h | Tarea 0 | → verificar: `npm run lint` sin warning `react-hooks/exhaustive-deps` en AgentForm |
| 6 | Agregar `useMemo` en derivados de `AgentForm.tsx` (ID-046, ID-048) | `dashboard/components/builder/AgentForm.tsx` | Envolver `buildSingleAgentPayload` en `useMemo` con dependencias de `watch()` individuales. Envolver `toolOptions` y `availableModels` en `useMemo`. | `CrewCanvas.tsx:207-218` — patrón de `useMemo` para payloads derivados | CODE | Media | 0.75h | Ninguna | → verificar: `grep -n "useMemo(() =>" AgentForm.tsx` devuelve al menos 3 matches |
| 7 | Agregar `useMemo` en derivados de `CrewCanvas.tsx` | `dashboard/components/builder/CrewCanvas.tsx` | Envolver en `useMemo`: `duplicatedRoles` (línea 339), `nodesWithWarnings` (línea 354), `sidebarAgents` (línea 337). No memoizar `hasAgentNodes` (O(1), no justifica overhead). | `CrewCanvas.tsx:207-218` — mismo archivo, mismo patrón | CODE | Baja | 0.5h | Ninguna | → verificar: `grep -n "useMemo(() =>" CrewCanvas.tsx` devuelve al menos 6 matches |
| 8 | Carga diferida de CSS de ReactFlow (ID-019) | `dashboard/components/builder/CrewCanvas.tsx` | Eliminar `import 'reactflow/dist/style.css'` (línea 48). Mover import a `BuilderCanvas.tsx` dentro del `dynamic()`: `dynamic(() => import('@/components/builder/CrewCanvas').then(mod => { import('reactflow/dist/style.css'); return { default: mod.CrewCanvas }; }), { ssr: false })`. | `BuilderCanvas.tsx:6-8` — patrón existente de `dynamic()` con `ssr: false` | CODE | Media | 0.5h | Ninguna | → verificar: `grep -n "reactflow/dist/style.css" CrewCanvas.tsx` NO devuelve matches; canvas renderiza con estilos correctos |
| 9 | Mejorar fallback de clipboard en `ExportDialog.tsx` (ID-045) | `dashboard/components/builder/ExportDialog.tsx` | Línea 94-98: Reemplazar toast truncado por estado `clipboardFallback: string \| null`. Si falla `navigator.clipboard`, mostrar `<Textarea readOnly value={fullGraphJson} />` + `<Button onClick={() => navigator.clipboard?.writeText(fullGraphJson)}>Copy</Button>` dentro del diálogo. | `ExportDialog.tsx` existente — extender estado de error existente | UX | Baja | 0.5h | Ninguna | → verificar: Simular fallo de `navigator.clipboard` → diálogo muestra Textarea con JSON completo |
| 10 | Agregar `method` param a `fapDownload` (ID-042) | `dashboard/lib/api.ts` | `fapDownload(path: string, body: unknown, method?: string): Promise<Response>` con default `method = 'POST'`. Línea 73: usar `method` en lugar de `'POST'` hardcodeado. | `api.ts:96-118` — `api.get/post/put/patch/delete` wrappers existentes. Mismo patrón de default params. | CODE | Baja | 0.25h | Ninguna | → verificar: `fapDownload('/path', body, 'GET')` no lanza error de tipo; calls existentes sin `method` siguen funcionando |
| 11 | Centralizar `MAX_EXPORT_AGENTS` en `constants.ts` (ID-043) | `dashboard/lib/constants.ts`, `dashboard/components/builder/ExportDialog.tsx` | Agregar `export const MAX_EXPORT_AGENTS = 15` en constants.ts. Importar en ExportDialog.tsx. Reemplazar hardcodeos `15` (línea 72: `exceedsLimit`, línea 112: `agents.slice(0, 15)`, línea 192: `agents.slice(0, 15)`, línea 212: `agents.length > 15`, línea 215: `agents.length - 15`). | `constants.ts` existente — `PROVIDER_MODELS`, `TEMPLATE_CATEGORIES` son constantes exportadas del mismo estilo | CODE | Baja | 0.25h | Ninguna | → verificar: `grep -rn "MAX_EXPORT_AGENTS" dashboard/lib/constants.ts` devuelve 1 match; `grep -rn "15" ExportDialog.tsx` solo muestra ocurrencias no relacionadas con límite |
| 12 | Corregir `scrollRef` en `AgentPlayground.tsx` (ID-035) | `dashboard/components/builder/AgentPlayground.tsx` | ScrollArea de Radix expone viewport via `ref`. Cambiar `scrollRef` para apuntar al viewport interno de ScrollArea en lugar de un `<div>` hijo. Alternativa: usar `scrollAreaRef` con `useEffect` que llama a `scrollToBottom` en el elemento viewport. | Documentación de `@radix-ui/react-scroll-area` — viewport ref pattern | CODE | Media | 0.5h | Ninguna | → verificar: Auto-scroll funciona al recibir nuevos mensajes; sin warning de consola sobre refs |
| 13 | Documentar `eslint-disable` en `CrewCanvas.tsx:113` (ID-038) | `dashboard/components/builder/CrewCanvas.tsx` | Línea 113: Cambiar comentario a `// eslint-disable-next-line react-hooks/exhaustive-deps — snapshot restore runs once on mount by design (snapshotRestored ref guard)` | — (mismo archivo, solo comentario) | CODE | Baja | 0.1h | Ninguna | → verificar: `npm run lint` sin nuevos warnings |
| 14 | Evaluar y decidir sobre `cmdk` (ID-021) | `DEVS/IN_PROGRESS/analisis-14-dsp.md` (este documento) | **Decisión registrada en §6 (Riesgos):** POSPONER. `cmdk` añade ~15KB. ToolMultiSelect actual (60 líneas) funciona bien, soporta agrupación por source, búsqueda con `useMemo`. No hay evidencia de problemas de UX con el selector actual. Si en futuro se necesita command palette global → reconsiderar. | — | ANALYSIS | Baja | 0h (decisión ya tomada) | Ninguna | → verificar: Análisis documenta decisión de posponer. No se instala `cmdk`. |
| 15 | Validar flujo end-to-end sin regresiones | — | Test manual: crear agente → seleccionar template → playground → canvas drag-drop → export → verificar ZIP estructura | — | FULLSTACK | Baja | 0.5h | Tareas 1-14 | → verificar: Criterios §5 [FULLSTACK] pasan todos; `tsc --noEmit` sin errores; `npm run lint` sin nuevos warnings |

**Tiempo total estimado:** 6.75 horas (0h de cmdk ya que se decide posponer)

---

## 🔮 Roadmap (NO implementar ahora)

1. **Command Palette global (cmdk):** Si el builder crece con más atajos (Ctrl+K para buscar herramientas, agentes, templates), instalar `cmdk` y crear `<CommandPalette />` global en el layout. No justificado aún.
2. **Virtual scrolling en ToolMultiSelect:** Si un workspace llega a 100+ tools (MCP pools grandes), implementar `@tanstack/react-virtual` en la lista de opciones. Actualmente `max-h-60 overflow-y-auto` es suficiente para <50 tools.
3. **Streaming en AgentPlayground:** Reemplazar polling (`GET /tasks/{id}` cada 2s) por SSE (`GET /tasks/{id}/stream`) cuando el backend lo soporte. Reduce latencia percibida de 2s a <100ms.
4. **Bundle size audit:** Ejecutar `@next/bundle-analyzer` para identificar oportunidades de tree-shaking. ReactFlow es el mayor contribuyente (~200KB) — evaluar `@reactflow/core` sin `minimap`/`controls` si no se usan.
5. **Memoización de nodos ReactFlow:** `AgentNode` y `TaskNode` ya usan `memo()`. Verificar si `nodes.map()` en `CrewCanvas.tsx:467-474` crea nuevas referencias en cada render — podría disparar re-renders de todos los nodos. Usar `useMemo` en el array mapeado.

