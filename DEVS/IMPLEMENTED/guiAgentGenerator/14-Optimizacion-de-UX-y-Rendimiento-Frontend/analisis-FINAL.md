# 🔬 Análisis UNIFICADO — Paso 14: Optimización de UX y Rendimiento Frontend

**Fase:** guiAgentGenerator
**Paso:** 14
**Fecha:** 2026-05-18
**Agentes consolidados:** dsp, lgn, step, qwen, g3h, dsf, mm (7 análisis)
**Estado del paso:** ⏳ En Progreso

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| dsp | ✅ (30 items) | 12 | ✅ hooks + mapper | ✅ líneas exactas | 4.5 |
| lgn | ✅ (12 items) | 7 | ✅ hooks | ⚠️ limitada | 3.0 |
| step | ✅ (13 items) | 8 | ✅ hooks + HTTP_METHODS + cmdk eval | ✅ líneas + justificaciones | 4.0 |
| qwen | ✅ (24 items) | 8 | ✅ CLI `fap perf builder` + script TS | ✅ líneas | 3.0 |
| g3h | ✅ (29 items) | 5 | ✅ CLI `fap doctor frontend` | ⚠️ verificó DB innecesariamente | 2.5 |
| dsf | ✅ (18 items) | 12 | ✅ CLI `fap doctor frontend` | ✅ completa | 4.0 |
| mm | ✅ (12 items) | 6 | ✅ hooks | ⚠️ mínima | 2.5 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| D1 | `useClickOutside` no existe como hook reutilizable — lógica inline en `ToolMultiSelect.tsx:32-40` | TODOS (7/7) | ✅ `dashboard/components/builder/ToolMultiSelect.tsx:32-40` | Crear `dashboard/hooks/useClickOutside.ts`. Extraer lógica inline existente. |
| D2 | `useDebounce` no existe — sin debounce en búsquedas ni campos de texto | TODOS (7/7) | ✅ `TemplatePicker.tsx:155`, `ToolMultiSelect.tsx:113`, `AgentForm.tsx:240-264` | Crear `dashboard/hooks/useDebounce.ts`. Aplicar a TemplatePicker, ToolMultiSelect. En AgentForm solo para campos de búsqueda/validación asíncrona, no para `register()` de RHF. |
| D3 | ReactFlow CSS importado estáticamente en `CrewCanvas.tsx:48` | TODOS (7/7) | ✅ `import 'reactflow/dist/style.css'` — línea 48 | Mover a carga dinámica vía `useEffect(() => { import('reactflow/dist/style.css') }, [])` dentro del componente montado en cliente. Eliminar import estático. |
| D4 | `mapTemplateToFormValues` inline en `BuilderLayout.tsx:28-50` — no extraído a módulo | TODOS (7/7) | ✅ `BuilderLayout.tsx:28-50` | Extraer a `dashboard/lib/template-mapper.ts`. Eliminar función inline. `BuilderLayout.tsx` importa desde `@/lib/template-mapper`. |
| D5 | `BuilderTabContext` usa solo `useState` — sin sincronización vía `?tab=` query params | TODOS (7/7) | ✅ `BuilderTabContext.tsx:29` — `useState(defaultTab)` hardcodeado | Integrar `useSearchParams` + `useRouter.replace`. Leer `tab` de URL al montar, actualizar URL al cambiar pestaña. Envolver en `<Suspense>` en `page.tsx`. |
| D6 | `cmdk` no instalado — dependencia no existe en `package.json` | TODOS (7/7) | ✅ `dashboard/package.json` — sin `cmdk` | **POSPONER.** El `ToolMultiSelect` actual (60 líneas) funciona correctamente con búsqueda y agrupación vía `useMemo`. `cmdk` añade ~15KB al bundle sin beneficio inmediato. Re-evaluar si se necesita Command Palette global en futuro. |
| D7 | Sin constantes `HTTP_METHODS` en `constants.ts` — strings hardcodeados en `api.ts` | dsp, lgn, step, g3h, dsf, mm (6/7) | ✅ `dashboard/lib/api.ts:96-118` — literales `'GET'`/`'POST'`/etc. | Agregar `HTTP_METHODS` as const en `dashboard/lib/constants.ts`. Usar en `api.ts`. |
| D8 | `fapDownload` hardcodea `method: 'POST'` — inflexible para futuros endpoints | dsp, qwen, g3h, dsf (4/7) | ✅ `api.ts:73` — `method: 'POST'` fijo | Agregar parámetro opcional `method?: string` con default `'POST'`. Backward-compatible. |
| D9 | `useEffect` en `AgentForm.tsx:224-229` tiene `eslint-disable` sin justificación expandida | dsp, lgn, step, dsf (4/7) | ✅ `AgentForm.tsx:224-229` — `eslint-disable-next-line react-hooks/exhaustive-deps` | **El disable es CORRECTO.** `setValue` es estable, `availableModels` solo cambia con `llmProvider`, y `watch('llmModel')` en estado estable no requiere re-evaluar. Mejorar comentario justificativo. |
| D10 | Múltiples derivados NO memoizados en `CrewCanvas.tsx` | dsp, qwen (2/7) | ✅ `CrewCanvas.tsx:337-357` — `duplicatedRoles`, `nodesWithWarnings`, `sidebarAgents`, `hasAgentNodes`, `exportDisabled` | Memoizar SOLO los que iteran arrays: `duplicatedRoles` ([nodes]), `nodesWithWarnings` ([nodes, edges]), `sidebarAgents` ([agentsData]). NO memoizar `hasAgentNodes` ni `exportDisabled` (O(1), no justifica overhead). |
| D11 | `AgentPlayground.tsx` `scrollRef` apunta a `<div>` dentro de `<ScrollArea>` — posible conflicto | dsp, g3h, dsf (3/7) | ✅ `AgentPlayground.tsx:56-62` — scrollRef + ScrollArea Radix | Reemplazar `<ScrollArea>` por `<div className="flex-1 overflow-y-auto" ref={scrollRef}>` para control directo de scroll. |
| D12 | Límite `15` agents duplicado en frontend y backend — sin constante compartida | dsp (1/7) | ✅ `ExportDialog.tsx:72,112` y backend Pydantic `max_length=15` | Agregar `MAX_EXPORT_AGENTS = 15` en `dashboard/lib/constants.ts`. Importar en `ExportDialog.tsx`. |

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo:** Pulir la experiencia de usuario (UX) del Builder visual mediante optimizaciones de React (hooks reutilizables, memoización, lazy loading), mejoras de accesibilidad (debounce en búsquedas) y navegación robusta (deep linking vía query params). Sin nueva funcionalidad — solo optimización sobre lo ya construido en pasos 1-13.
- **Correcciones al plan original:**
  - ⚠️ El plan sugiere "evaluar migración a `cmdk`" (ID-021). 7/7 agentes confirman que `cmdk` no está instalado. Decisión unificada: **POSPONER**. El selector actual funciona, `cmdk` añade ~15KB sin justificación inmediata.
  - ⚠️ El plan menciona "debounce en cambios de campos de texto" (ID-034). Los agentes clarifican que el debounce NO debe aplicarse a `register()` de react-hook-form (rompería reactividad del formulario), sino a cálculos derivados como `filtered`/`grouped` en selectores.
  - ⚠️ El plan ID-046/ID-048 menciona `useMemo` en payload. El código ya lo tiene en `CrewCanvas.tsx:207-218`. La discrepancia real está en `AgentForm.tsx` (`buildSingleAgentPayload` sin memoizar) y en derivados sueltos de `CrewCanvas.tsx`.
- **Herramienta DX seleccionada:** **Hooks bundle `useClickOutside` + `useDebounce`** (Tarea 0 principal). Complemento opcional: script `perf-audit.ts` (Tarea 0b) para validación estática de regresiones de performance. Se descarta el CLI `fap doctor frontend` para este paso por solapamiento con `fap doctor builder` ya existente.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Usuario accede a `/dashboard/app/builder` (o con `?tab=crew-canvas` para deep linking directo).
2. `page.tsx` lee `searchParams.tab` y lo pasa como `defaultTab` a `BuilderTabProvider`.
3. `BuilderTabContext` inicializa `activeTab` desde URL. Si no hay param, default `agent-form`.
4. Usuario cambia de pestaña → `setActiveTab` actualiza URL vía `router.replace('?tab=X')` sin recarga de página.
5. En tab **Agent Form**: `AgentForm` se renderiza normalmente. Al escribir en `role`, los cálculos derivados (`toolOptions`, `availableModels`) están memoizados. `buildSingleAgentPayload` usa `useMemo`.
6. Usuario abre **TemplatePicker** → busca con debounce (300ms) → selecciona template → `mapTemplateToFormValues` (desde `lib/template-mapper.ts`) rellena el formulario.
7. Usuario cambia a tab **Crew Canvas** → `BuilderCanvas` carga `CrewCanvas` dinámicamente (`dynamic({ ssr: false })`). CSS de ReactFlow se inyecta vía `useEffect` al montar, no bloquea carga inicial.
8. En canvas: `duplicatedRoles`, `nodesWithWarnings`, `sidebarAgents` memoizados. Drag-and-drop fluido.
9. Usuario usa **ToolMultiSelect** → búsqueda con debounce (300ms), cierre al click fuera vía `useClickOutside` hook.
10. **ExportDialog** → `fapDownload` con `method` param (default POST). Clipboard fallback con `<Textarea>` + botón "Copy" en lugar de toast truncado.
11. **AgentPlayground** → scroll automático al final funciona correctamente (div nativo, sin ScrollArea).
12. Usuario refresca la página en `?tab=crew-canvas` → el canvas es la pestaña activa tras recarga.

### Edge Cases MVP

- **URL sin param `?tab=`:** Comportamiento por defecto: `agent-form`.
- **URL con `?tab=valor-invalido`:** Ignorar y caer en `defaultTab="agent-form"`. Sin error ni redirect.
- **Navegación rápida entre tabs:** `router.replace` (no `push`) evita acumular entradas en historial.
- **`navigator.clipboard` no disponible (HTTP, iframe, permisos denegados):** Mostrar `<Textarea readOnly>` con JSON completo + botón "Copy" manual dentro del ExportDialog. NO toast truncado.
- **ReactFlow CSS carga lenta:** El skeleton de `BuilderCanvas` (ya implementado) cubre el FOUC hasta que CSS + componente están listos.
- **`agentsData` es `undefined` o `null` en CrewCanvas:** `sidebarAgents` usa `agentsData?.agents ?? []` (seguro con optional chaining + fallback).
- **Template sin `soul_json`:** `mapTemplateToFormValues` maneja `soul_json ?? {}` y aplica defaults seguros para cada campo.

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. `dashboard/hooks/useClickOutside.ts` — CREACIÓN

- **Tipo de cambio:** Creación
- **Descripción:** Hook reutilizable que detecta clicks fuera de un elemento. Extrae lógica existente en `ToolMultiSelect.tsx:32-40`.
- **Interfaz:**
```typescript
import { type RefObject, useEffect } from 'react'

export function useClickOutside(
  ref: RefObject<HTMLElement | null>,
  handler: () => void,
  enabled?: boolean
): void
```
- **Patrón a seguir:** `dashboard/hooks/useCurrentOrg.ts` — hook con `useEffect`, `addEventListener`/`removeEventListener`, cleanup en return.

#### 2. `dashboard/hooks/useDebounce.ts` — CREACIÓN

- **Tipo de cambio:** Creación
- **Descripción:** Hook genérico de debounce con `useState` + `useEffect` + `setTimeout`/`clearTimeout`. Retrasa actualización de valor hasta `delay` ms de inactividad.
- **Interfaz:**
```typescript
export function useDebounce<T>(value: T, delay: number): T
```
- **Patrón a seguir:** Hooks existentes en `dashboard/hooks/` — función nombrada exportada, sin default export.

#### 3. `dashboard/lib/template-mapper.ts` — CREACIÓN

- **Tipo de cambio:** Creación (extracción desde `BuilderLayout.tsx`)
- **Descripción:** Función pura que mapea `TemplateDetail` (respuesta API) → `AgentFormData` (valores del formulario). Sin dependencias de React.
- **Interfaz:**
```typescript
import type { AgentFormData } from '@/components/builder/AgentForm'
import type { TemplateDetail } from '@/components/builder/TemplatePicker'

export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData
```
- **Patrón a seguir:** `dashboard/lib/canvasUtils.ts` — funciones puras, named exports, sin side effects.
- **Cuerpo:** Idéntico a `BuilderLayout.tsx:28-50` actual. Incluye `VALID_PROVIDERS`, `mapProvider()` helper interno.

#### 4. `dashboard/lib/constants.ts` — MODIFICACIÓN

- **Tipo de cambio:** Modificación (añadir constantes)
- **Descripción:** Agregar constantes centralizadas para métodos HTTP y límite de exportación.
- **Adiciones:**
```typescript
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  PATCH: 'PATCH',
  DELETE: 'DELETE',
} as const

export const MAX_EXPORT_AGENTS = 15
```
- **Patrón a seguir:** `PROVIDER_MODELS`, `TEMPLATE_CATEGORIES` existentes en el mismo archivo.

#### 5. `dashboard/lib/api.ts` — MODIFICACIÓN

- **Tipo de cambio:** Modificación
- **Descripción:** Flexibilizar `fapDownload` aceptando parámetro `method` opcional. Usar `HTTP_METHODS.POST` como default.
- **Interfaz:**
```typescript
export async function fapDownload(
  path: string,
  body: unknown,
  method?: string
): Promise<Response>
```
- **Cambio en línea 73:** Reemplazar `'POST'` hardcodeado por `method ?? HTTP_METHODS.POST`.

#### 6. `dashboard/components/builder/ToolMultiSelect.tsx` — REFACTOR

- **Tipo de cambio:** Refactor
- **Descripción:** Reemplazar `useEffect` inline (líneas 32-40) por `useClickOutside(containerRef, () => setOpen(false))`. Aplicar `useDebounce` a `search` para alimentar `grouped` (líneas 52-59).
- **Interfaz (sin cambios):** Las props del componente no cambian.
- **Patrón a seguir:** El `useMemo` de `grouped` ya existe — solo cambia su entrada a `debouncedSearch`.

#### 7. `dashboard/components/builder/AgentForm.tsx` — MODIFICACIÓN

- **Tipo de cambio:** Modificación
- **Descripción:**
  - Envolver `toolOptions` (línea 135-139) en `useMemo` con deps `[toolsResponse]`.
  - Envolver `availableModels` (línea 141) en `useMemo` con deps `[llmProvider]`.
  - Envolver `buildSingleAgentPayload` (línea 203-222) en `useMemo` con deps de campos individuales vía `watch()`.
  - Mejorar comentario `eslint-disable` en línea 228: justificar por qué es seguro omitir dependencias.
  - NO aplicar debounce a `register()` de RHF — eso rompe la reactividad del formulario.
- **Patrón a seguir:** `CrewCanvas.tsx:207-218` — `useMemo` para payloads derivados.

#### 8. `dashboard/components/builder/CrewCanvas.tsx` — MODIFICACIÓN

- **Tipo de cambio:** Modificación
- **Descripción:**
  - **Eliminar** `import 'reactflow/dist/style.css'` (línea 48).
  - **Agregar** `useEffect(() => { import('reactflow/dist/style.css') }, [])` al inicio del componente.
  - Envolver en `useMemo`: `duplicatedRoles` (línea 339, deps `[nodes]`), `nodesWithWarnings` (línea 354, deps `[nodes, edges]`), `sidebarAgents` (línea 337, deps `[agentsData]`).
  - NO memoizar `hasAgentNodes` ni `exportDisabled` — son operaciones O(1), el overhead de `useMemo` no se justifica.
  - Mejorar comentario `eslint-disable` en línea 113: documentar que `snapshotRestored.current = true` garantiza ejecución única al montar.
- **Patrón a seguir:** `CrewCanvas.tsx:207-218` — `useMemo` con dependencias explícitas.

#### 9. `dashboard/components/builder/BuilderTabContext.tsx` — MODIFICACIÓN

- **Tipo de cambio:** Modificación
- **Descripción:** Sincronizar estado de tabs con URL query params. Leer `tab` de `useSearchParams()` como valor inicial. Al cambiar pestaña, actualizar URL vía `useRouter().replace()`.
- **Interfaz modificada:** `BuilderTabProvider` acepta prop `defaultTab` desde `page.tsx`. El contexto expone mismo `activeTab | setActiveTab`.
- **Patrón a seguir:** Next.js 14 App Router — `useSearchParams` + `useRouter`.

#### 10. `dashboard/app/(app)/builder/page.tsx` — MODIFICACIÓN

- **Tipo de cambio:** Modificación
- **Descripción:** Leer `searchParams.tab` y pasarlo como `defaultTab` a `BuilderTabProvider`. Envolver provider en `<Suspense>` para cumplir con requerimiento de Next.js 14 sobre `useSearchParams`.
- **Patrón a seguir:** Implementación estándar de Next.js App Router con searchParams.

#### 11. `dashboard/components/builder/BuilderLayout.tsx` — REFACTOR

- **Tipo de cambio:** Refactor
- **Descripción:** Eliminar función `mapTemplateToFormValues` inline (líneas 28-50). Importar desde `@/lib/template-mapper`.
- **Interfaz (sin cambios):** El componente se comporta idéntico.

#### 12. `dashboard/components/builder/TemplatePicker.tsx` — MODIFICACIÓN

- **Tipo de cambio:** Modificación
- **Descripción:** Aplicar `useDebounce(search, 300)` para alimentar el `useMemo` de `filtered` (línea 74-84). El input mantiene `search` inmediato para respuesta visual.
- **Interfaz (sin cambios):** Props igual.

#### 13. `dashboard/components/builder/AgentPlayground.tsx` — MODIFICACIÓN

- **Tipo de cambio:** Modificación
- **Descripción:** Reemplazar `<ScrollArea>` por `<div className="flex-1 overflow-y-auto" ref={scrollRef}>` para control directo y predecible de `scrollTop`. El `ScrollArea` de Radix encapsula viewport interno que impide scroll manual confiable.
- **Patrón a seguir:** Contenedores scroll nativos — patrón estándar en componentes de chat.

#### 14. `dashboard/components/builder/ExportDialog.tsx` — MODIFICACIÓN

- **Tipo de cambio:** Modificación
- **Descripción:**
  - Reemplazar hardcodeos `15` por `MAX_EXPORT_AGENTS` importado de `@/lib/constants`.
  - Mejorar fallback de clipboard: en lugar de toast truncado (500 chars), mostrar `<Textarea readOnly>` con JSON completo + botón "Copy" manual.
- **Interfaz (sin cambios):** Props igual.

---

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: useClickOutside + useDebounce Hooks Bundle
- **Qué automatiza:** Extracción de lógica repetitiva de detección click-outside y debounce de valores. Evita que cada componente nuevo re-implemente `mousedown` listeners o `setTimeout` manualmente.
- **Tipo:** Hooks reutilizables (librería interna del dashboard)
- **Ubicación:** `dashboard/hooks/useClickOutside.ts`, `dashboard/hooks/useDebounce.ts`
- **Cómo se usa:**
  import { useClickOutside } from '@/hooks/useClickOutside'
  import { useDebounce } from '@/hooks/useDebounce'

  // En ToolMultiSelect — reemplaza useEffect inline líneas 32-40
  useClickOutside(containerRef, () => setOpen(false))

  // En TemplatePicker/ToolMultiSelect — búsqueda con delay
  const debouncedSearch = useDebounce(search, 300)
  const filtered = useMemo(() => items.filter(...), [debouncedSearch])
- **Impacto para el usuario final:** Menos bugs de UI (dropdowns que no cierran, búsquedas que disparan recálculos en cada keystroke). Desarrollo más rápido de nuevos selectores/dropdowns. Reducción de ~10 líneas de código inline por cada componente que necesite click-outside.
- **El implementador DEBE usar** estos hooks para completar las tareas 1..N del paso. El hook `useClickOutside` es pre-requisito para refactorizar `ToolMultiSelect`. El hook `useDebounce` es pre-requisito para optimizar `TemplatePicker` y `ToolMultiSelect`.
```

```
### Herramienta Complementaria: script perf-audit.ts (Tarea 0b)
- **Qué automatiza:** Escaneo estático de archivos TSX del builder para detectar regresiones de performance: (a) `useEffect` con lógica click-outside inline (debería usar hook), (b) cálculos derivados fuera de `useMemo`, (c) imports síncronos de CSS de librerías grandes.
- **Tipo:** Script TypeScript ejecutable con `npx tsx`
- **Ubicación:** `scripts/perf-audit.ts`
- **Cómo se usa:** `npx tsx scripts/perf-audit.ts --path dashboard/components/builder/`
- **Impacto para el usuario final:** Validación pre-commit que asegura que las optimizaciones del paso 14 se mantengan en el tiempo. Previene que código no optimizado llegue a producción.
- **Prioridad:** Complementaria — no bloquea el avance del paso si se posterga.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Hooks en `dashboard/hooks/` (no librería externa):** Los hooks `useClickOutside` y `useDebounce` se implementan como módulos internos del dashboard. No se instala `use-debounce` ni `react-use`. Justificación: el código es trivial (~15 líneas cada uno), cero dependencias externas, patrones consistentes con hooks existentes en el proyecto.
2. **Debounce solo en cálculos derivados, NO en `register()` de RHF:** Aplicar debounce a `register()` rompería la reactividad del formulario y la validación de Zod. El debounce se aplica exclusivamente a valores que alimentan `useMemo` de filtrado (TemplatePicker, ToolMultiSelect). Para formularios, se depende del `mode: 'onBlur'` de RHF si se necesita lazy validation.
3. **Memoización selectiva en CrewCanvas:** Solo se memoizan `duplicatedRoles`, `nodesWithWarnings` y `sidebarAgents` (iteran arrays, O(n)). `hasAgentNodes` y `exportDisabled` son O(1) — memoizarlos añadiría overhead de `useMemo` sin beneficio medible. Criterio: memoizar solo cuando el cálculo itera colecciones.
4. **Corrección al plan — `cmdk` pospuesto:** El plan ID-021 sugiere "evaluar migración a `cmdk`". 7/7 agentes confirman que `cmdk` no está instalado. `ToolMultiSelect` actual (60 líneas, `useMemo` para agrupación) funciona correctamente. `cmdk` añadiría ~15KB al bundle sin beneficio inmediato. Se re-evaluará cuando se necesite Command Palette global.
5. **`<div>` nativo reemplaza `<ScrollArea>` de Radix en AgentPlayground:** El `ScrollArea` de Radix encapsula el viewport real, haciendo que `scrollRef.current.scrollTop = scrollRef.current.scrollHeight` falle o sea inestable. Un `<div>` con `overflow-y-auto` da control directo y predecible del scroll. El estilo visual se mantiene idéntico con Tailwind.
6. **⚠️ El plan dice "añadir debounce en campos de texto" pero el código usa `register()` de RHF.** No se puede aplicar debounce a `register()` sin romper el binding del formulario. Se aplica debounce a los valores de `watch()` que alimentan cálculos derivados, no a los inputs del formulario.
7. **⚠️ El plan menciona ID-046/ID-048 como `useMemo` en payloads de export.** El código YA tiene `useMemo` en `CrewCanvas.tsx:207-218` para `exportPayload`, `fullGraphJson`, `exportAgents`. La optimización pendiente está en `AgentForm.tsx` (`buildSingleAgentPayload` sin memoizar) y en `toolOptions`/`availableModels` sin memoizar.
8. **Sincronización tabs↔URL con `router.replace` (no `push`):** Usar `replace` evita acumular entradas en el historial del navegador por cada cambio de pestaña. El botón "atrás" del navegador debe llevar al usuario a la página anterior al builder, no a la pestaña anterior.
9. **Límite `MAX_EXPORT_AGENTS = 15` centralizado en `constants.ts`:** Actualmente duplicado en `ExportDialog.tsx:72,112` y en backend (Pydantic `max_length=15`). Centralizar en frontend permite mantener sincronía parcial. Idealmente en futuro se expondría vía endpoint de configuración para sincronizar frontend↔backend.
10. **`eslint-disable` en AgentForm.tsx:228 es CORRECTO y se mantiene:** El análisis de `step` confirma que `setValue` es estable, `availableModels` solo cambia con `llmProvider`, y `watch('llmModel')` en estado estable no necesita re-evaluar. Solo se mejora el comentario justificativo.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] Hook `useClickOutside` exportado desde `dashboard/hooks/useClickOutside.ts` con firma: (ref: RefObject<HTMLElement | null>, handler: () => void, enabled?: boolean): void
✅ [CODE] Hook `useDebounce` exportado desde `dashboard/hooks/useDebounce.ts` con firma: <T>(value: T, delay: number): T
✅ [CODE] `ToolMultiSelect.tsx` usa `useClickOutside` — sin `useEffect` + `mousedown` inline (líneas 32-40 eliminadas)
✅ [CODE] `mapTemplateToFormValues` exportada desde `dashboard/lib/template-mapper.ts` con firma exacta
✅ [CODE] `BuilderLayout.tsx` importa `mapTemplateToFormValues` desde `@/lib/template-mapper` — sin función inline (líneas 28-50 eliminadas)
✅ [CODE] `constants.ts` exporta `HTTP_METHODS` (as const) y `MAX_EXPORT_AGENTS = 15`
✅ [CODE] `api.ts` `fapDownload` acepta parámetro `method?: string` con default `'POST'` — backward-compatible
✅ [CODE] `ExportDialog.tsx` usa `MAX_EXPORT_AGENTS` (no hardcodeo `15`) y tiene fallback clipboard con `<Textarea>` + botón "Copy"
✅ [PERF] `CrewCanvas.tsx` NO tiene `import 'reactflow/dist/style.css'` estático (línea 48 eliminada). CSS carga vía `useEffect` dinámico.
✅ [PERF] `CrewCanvas.tsx` tiene `useMemo` en `duplicatedRoles`, `nodesWithWarnings`, `sidebarAgents`
✅ [PERF] `AgentForm.tsx` tiene `useMemo` en `toolOptions`, `availableModels`, `buildSingleAgentPayload`
✅ [PERF] `TemplatePicker.tsx` y `ToolMultiSelect.tsx` usan `useDebounce(search, 300)` para alimentar `useMemo` de filtrado
✅ [UX] `AgentPlayground.tsx` usa `<div>` nativo con `overflow-y-auto` (no ScrollArea) — scroll automático funciona
✅ [UX] `AgentForm.tsx:228` `eslint-disable` tiene comentario expandido justificando seguridad
✅ [UX] `CrewCanvas.tsx:113` `eslint-disable` tiene comentario expandido justificando ejecución única al montar
✅ [FULLSTACK] `BuilderTabContext` sincroniza `activeTab` con URL `?tab=agent-form|crew-canvas`
✅ [FULLSTACK] URL `/builder?tab=crew-canvas` abre directamente Crew Canvas
✅ [FULLSTACK] Cambiar pestaña en UI actualiza URL vía `router.replace` sin recargar página
✅ [FULLSTACK] Refrescar página preserva pestaña activa desde URL
✅ [FULLSTACK] `<Suspense>` boundary envuelve `BuilderTabProvider` en `page.tsx` para `useSearchParams`
✅ [DX] Herramienta `useClickOutside` + `useDebounce` hooks bundle creada, funcional y usada en ≥2 componentes
✅ [DX] `cmdk` NO instalado — decisión de posponer documentada en §4

**Funcionales:**
- [ ] TemplatePicker aplica template correctamente usando `mapTemplateToFormValues` desde `lib/template-mapper.ts`
- [ ] ToolMultiSelect abre/cierra correctamente con click-outside vía hook
- [ ] Búsqueda en TemplatePicker y ToolMultiSelect responde con 300ms de debounce
- [ ] ExportDialog muestra textarea con JSON completo si falla clipboard API
- [ ] AgentPlayground hace scroll automático al recibir nuevos mensajes
- [ ] Navegación entre tabs del builder refleja y persiste en URL

**Técnicos:**
- [ ] `tsc --noEmit` sin errores en `dashboard/`
- [ ] `npm run lint` sin nuevos warnings en componentes builder
- [ ] `grep -rn "eslint-disable" dashboard/components/builder/` muestra solo ocurrencias con justificación
- [ ] `grep -rn "import 'reactflow/dist/style.css'" dashboard/components/builder/CrewCanvas.tsx` NO devuelve matches
- [ ] `grep -rn "function mapTemplateToFormValues" dashboard/components/builder/BuilderLayout.tsx` NO devuelve matches
- [ ] Flujo completo builder (crear agente → templates → playground → canvas → export) funciona sin regresiones
```

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear hooks `useClickOutside` (`dashboard/hooks/useClickOutside.ts`) y `useDebounce` (`dashboard/hooks/useDebounce.ts`) | Baja | 0.5h | Ninguna |
| 0b | **DX Complementaria:** Crear script `scripts/perf-audit.ts` — escaneo estático de regresiones de performance en builder | Media | 1.0h | Ninguna |
| 1 | Refactorizar `ToolMultiSelect.tsx` — reemplazar `useEffect` inline (líneas 32-40) por `useClickOutside(containerRef, () => setOpen(false))`. Aplicar `useDebounce` a búsqueda. | Baja | 0.25h | Tarea 0 |
| 2 | Aplicar `useDebounce(search, 300)` en `TemplatePicker.tsx` — alimentar `useMemo` de `filtered` con valor debounced | Baja | 0.25h | Tarea 0 |
| 3 | Extraer `mapTemplateToFormValues` a `dashboard/lib/template-mapper.ts` — cuerpo idéntico a `BuilderLayout.tsx:28-50` | Baja | 0.5h | Ninguna |
| 4 | Actualizar `BuilderLayout.tsx` — eliminar función inline (líneas 28-50), importar desde `@/lib/template-mapper` | Baja | 0.25h | Tarea 3 |
| 5 | Agregar `useMemo` en `AgentForm.tsx`: `toolOptions` ([toolsResponse]), `availableModels` ([llmProvider]), `buildSingleAgentPayload` (campos vía `watch()`) | Media | 0.75h | Ninguna |
| 6 | Agregar `useMemo` selectivo en `CrewCanvas.tsx`: `duplicatedRoles` ([nodes]), `nodesWithWarnings` ([nodes, edges]), `sidebarAgents` ([agentsData]). NO memoizar `hasAgentNodes` ni `exportDisabled`. | Baja | 0.5h | Ninguna |
| 7 | Mover CSS de ReactFlow a carga dinámica: eliminar `import 'reactflow/dist/style.css'` (línea 48), agregar `useEffect(() => { import('reactflow/dist/style.css') }, [])` en `CrewCanvas.tsx` | Media | 0.5h | Ninguna |
| 8 | Mejorar comentarios `eslint-disable`: `AgentForm.tsx:228` (justificar estabilidad de dependencias), `CrewCanvas.tsx:113` (documentar `snapshotRestored` guard) | Baja | 0.1h | Ninguna |
| 9 | Sincronizar `BuilderTabContext` con query params: leer `tab` de `useSearchParams()` en inicialización, actualizar URL vía `router.replace()` al cambiar pestaña. Envolver en `<Suspense>` en `page.tsx`. | Media | 1.0h | Ninguna |
| 10 | Agregar `HTTP_METHODS` y `MAX_EXPORT_AGENTS` a `dashboard/lib/constants.ts` | Baja | 0.25h | Ninguna |
| 11 | Flexibilizar `fapDownload` en `api.ts`: agregar parámetro `method?: string` con default `'POST'`. Usar `HTTP_METHODS.POST` como default. | Baja | 0.25h | Tarea 10 |
| 12 | Actualizar `ExportDialog.tsx`: usar `MAX_EXPORT_AGENTS` (reemplazar hardcodeos `15`), mejorar fallback clipboard con `<Textarea>` + botón "Copy" | Baja | 0.5h | Tarea 10 |
| 13 | Corregir scroll en `AgentPlayground.tsx`: reemplazar `<ScrollArea>` por `<div className="flex-1 overflow-y-auto" ref={scrollRef}>` | Media | 0.5h | Ninguna |
| 14 | Validar flujo end-to-end sin regresiones: `tsc --noEmit`, `npm run lint`, flujo manual builder completo | Baja | 0.5h | Tareas 1-13 |
| **TOTAL** | | | **7.0h** | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutar hooks bundle primero y usar `useClickOutside`/`useDebounce` para las tareas 1-2. La tarea 0b (`perf-audit.ts`) es complementaria — puede ejecutarse en paralelo o postergarse sin bloquear el resto.
>
> **Todas las tareas son atómicas:** una tarea = un artefacto (archivo). Cada tarea incluye interfaz exacta en §3.

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `useSearchParams` necesita `<Suspense>` en Next.js 14 — error de hidratación si no se envuelve | Alta | `page.tsx` tiene `'use client'` pero `BuilderTabProvider` se renderiza inicialmente en servidor. `useSearchParams()` requiere `Suspense` boundary. | Envolver `<BuilderTabProvider>` en `<Suspense fallback={<BuilderSkeleton />}>` dentro de `page.tsx`. Verificar hidratación sin errores en consola. |
| Bucle infinito tabs↔URL: `useState` → `useSearchParams` → `setActiveTab` → `router.replace` → re-lectura de `useSearchParams` | Media | Si el efecto de sincronización no tiene guardia, cada `replace` dispara re-lectura de `searchParams` que dispara `setActiveTab` que dispara `replace`... | Implementar con flag `initialized` ref. Leer `searchParams` solo en montaje inicial. Escribir con `router.replace` sin disparar re-lectura (Next.js 14 `useSearchParams` retorna objeto inmutable). |
| FOUC (Flash of Unstyled Content) al cargar CSS de ReactFlow dinámicamente | Media | CSS carga asíncrona → nodos del canvas se renderizan sin estilo durante ~100-200ms | El skeleton de `BuilderCanvas` (ya implementado con `dynamic({ ssr: false, loading: <Skeleton /> })`) cubre este gap. El CSS se inyecta ANTES de que el componente se monte completamente. |
| `useDebounce` aplicado incorrectamente a campos `register()` de RHF rompe formulario | Media | `register('role')` vincula directamente al DOM. Si el valor se debouncea antes de llegar al input, el usuario ve lag de escritura. | **Regla estricta:** debounce SOLO en valores de `watch()` que alimentan `useMemo`. Nunca en `register()`. El input del usuario siempre es inmediato; solo el cálculo pesado derivado se retrasa. |
| Regresión en flujo de exportación al cambiar `fapDownload` signature | Baja | Agregar parámetro `method` podría romper calls existentes si no es backward-compatible | Parámetro `method` opcional con default `'POST'`. Todos los call sites existentes (`ExportDialog.tsx`) no necesitan modificación. |
| `mapTemplateToFormValues` extraído rompe import si `TemplateDetail` no está exportado desde `TemplatePicker` | Baja | `TemplatePicker.tsx` podría no exportar el tipo `TemplateDetail` | Verificar export de `TemplateDetail` en `TemplatePicker.tsx`. Si no existe, agregar `export interface TemplateDetail { ... }` o mover la interfaz a `lib/template-mapper.ts`. |
| Reemplazar `ScrollArea` por `<div>` en `AgentPlayground` cambia estilos visuales | Baja | `ScrollArea` de Radix aplica estilos de scrollbar. Un `<div>` nativo usa scrollbar del navegador. | Agregar clases Tailwind para estilizar scrollbar (`scrollbar-thin`, `scrollbar-thumb-gray-400`) o mantener consistencia visual con el resto del dashboard. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Hook `useClickOutside` cierra dropdown al click fuera | Renderizar ToolMultiSelect abierto, hacer click en área externa | `setOpen(false)` llamado. Dropdown no visible. |
| TP-2 | Hook `useClickOutside` NO cierra al click dentro | Renderizar ToolMultiSelect abierto, hacer click en option interna | `setOpen(false)` NO llamado. Dropdown sigue visible. |
| TP-3 | Hook `useDebounce` retrasa actualización | `useDebounce('test', 300)` — cambiar valor a 'testing' inmediatamente | Valor retornado es `'test'` hasta 300ms después de la última tecla. Luego cambia a `'testing'`. |
| TP-4 | `mapTemplateToFormValues` mapea template completo | TemplateDetail con todos los campos definidos | AgentFormData con todos los campos mapeados correctamente (role, goal, backstory, llmProvider, llmModel, allowedTools, maxIter, toggles) |
| TP-5 | `mapTemplateToFormValues` maneja template sin `soul_json` | TemplateDetail con `soul_json: null` | AgentFormData con defaults seguros (role='', goal='', backstory=description, llmProvider='groq', llmModel='llama-3.1-70b-versatile') |
| TP-6 | Deep linking `?tab=crew-canvas` abre Crew Canvas | Navegar a `/builder?tab=crew-canvas` | `activeTab === 'crew-canvas'`. CrewCanvas visible. URL muestra `?tab=crew-canvas`. |
| TP-7 | Cambiar pestaña actualiza URL | Click en tab "Crew Canvas" desde Agent Form | URL cambia a `?tab=crew-canvas`. Sin recarga de página. `router.replace` usado (no push). |
| TP-8 | Refrescar página preserva pestaña | Abrir `/builder?tab=crew-canvas`, refrescar (F5) | Crew Canvas sigue siendo pestaña activa tras recarga. |
| TP-9 | ReactFlow CSS no bloquea carga de página | Medir FCP en `/builder` con Lighthouse | CSS de ReactFlow NO aparece en critical rendering path. FCP no degradado respecto a pre-optimización. |
| TP-10 | `fapDownload` con método custom | `fapDownload('/path', body, 'GET')` | Fetch ejecutado con `method: 'GET'`. Call existente sin `method` sigue usando `'POST'`. |
| TP-11 | Clipboard fallback muestra textarea | Mock `navigator.clipboard.writeText` para que rechace (simular HTTP) | ExportDialog muestra `<Textarea readOnly>` con JSON completo + botón "Copy" funcional. NO toast truncado. |
| TP-12 | Scroll automático en AgentPlayground | Enviar mensaje en playground, agente responde con texto largo | Viewport hace scroll al final automáticamente. Último mensaje visible sin scroll manual. |

**Comando para ejecutar tests:** `uv run pytest tests/unit/ -v --timeout=60` (unitarios) / `uv run pytest tests/integration/ -v --timeout=60` (integración)

**Verificación de lint y tipos:** `npm run lint` (dashboard) / `tsc --noEmit` (dashboard) — ambos deben pasar sin errores ni warnings nuevos.

---

## 📊 Métrica de Calidad del FINAL

| Métrica | Estado |
|:---|:---|
| `proyecto-config.json` leído antes de generar | ✅ |
| Discrepancias consolidadas con resolución | 12/12 detectadas (100%) |
| Correcciones al plan documentadas | 3 correcciones explícitas en §1 y §4 |
| Propuesta DX incluida en §3 y Tarea 0 en §6 | ✅ hooks bundle + perf-audit.ts |
| Criterio DX en §5 | ✅ 2 criterios DX |
| Secciones completadas | 9 secciones (0-8) |
| Casos de testing | 12 casos concretos (≥3 mínimo) |
| Tiempo estimado por tarea | 100% (14 tareas + 2 DX) |

---

*Documento unificado generado a partir de 7 análisis de agentes (dsp, lgn, step, qwen, g3h, dsf, mm). Idioma: Español 🇪🇸*
