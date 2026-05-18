# Análisis Técnico — Paso 14: Optimización de UX y Rendimiento Frontend

**Agente:** dsf
**Paso:** 14
**Fase:** guiAgentGenerator
**Fecha:** 2026-05-18

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | `dashboard/hooks/useClickOutside.ts` existe | grep en `dashboard/hooks/` | ❌ DISCREPANCIA | No existe — el hook debe crearse |
| 2 | `dashboard/lib/template-mapper.ts` existe | glob en `dashboard/lib/` | ❌ DISCREPANCIA | No existe — mapeo está inline en `BuilderLayout.tsx:28-50` |
| 3 | `AgentForm.tsx` tiene `useEffect` sin dependencias: `watch('llmModel')` en línea 224-229 | lectura línea 224-229 | ✅ VERIFICADO | `useEffect` con eslint-disable comment (línea 228) |
| 4 | `ToolMultiSelect.tsx` tiene `useClickOutside` inline | lectura líneas 32-40 | ✅ VERIFICADO | Inline en `useEffect` con `mousedown` listener |
| 5 | `CrewCanvas.tsx` importa `reactflow/dist/style.css` directo | línea 48 | ✅ VERIFICADO | Import directo, no dinámico |
| 6 | `AgentForm.tsx` usa `useMemo` en `buildSingleAgentPayload` | No usa | ❌ DISCREPANCIA | `buildSingleAgentPayload` es función regular, recrea objeto en cada render |
| 7 | `ExportDialog.tsx` tiene fallback de clipboard | línea 94-99 | ✅ VERIFICADO | Fallback con toast descriptivo |
| 8 | `BuilderTabContext.tsx` usa Query Params | No usa | ❌ DISCREPANCIA | Usa solo `useState`, no URL search params |
| 9 | `lib/api.ts` tiene `fapDownload` hardcodeado a POST | línea 73 | ✅ VERIFICADO | `method: 'POST'` hardcodeado |
| 10 | `lib/constants.ts` tiene constantes de descarga | No tiene | ❌ DISCREPANCIA | No existen constantes HTTP_METHODS ni DOWNLOAD_* |
| 11 | `AgentForm.tsx` usa `cmdk` para tools | No usa | ✅ VERIFICADO | Usa `ToolMultiSelect` propio, no `cmdk` |
| 12 | `AgentForm.tsx` tiene debounce en cambios de texto | `register` directo sin debounce | ❌ DISCREPANCIA | `goal`, `backstory` cambian en cada keystroke sin debounce |
| 13 | `AgentPlayground.tsx` scroll ref usa `scrollRef.current.scrollTop = scrollRef.current.scrollHeight` | línea 60 | ⚠️ NO VERIFICABLE | Asumo que scroll container es ScrollArea, no div directo |
| 14 | `package.json` tiene `cmdk` | No tiene | ❌ DISCREPANCIA | No listado como dependencia |
| 15 | `ExportDialog.tsx` exporta `ExportDialogProps` sin método HTTP flexible | línea 37-46 | ✅ VERIFICADO | Prop `source` pero no `httpMethod` |
| 16 | `CrewCanvas.tsx` usa `useMemo` en payload | líneas 207-218 | ✅ VERIFICADO | `exportPayload`, `fullGraphJson`, `exportAgents` sí usan useMemo |
| 17 | `BuilderLayout.tsx` template mapper aislado | líneas 28-50 | ✅ VERIFICADO | Inline en BuilderLayout, no extraído |
| 18 | `dashboard/hooks/useClickOutside` existe | búsqueda completa | ❌ DISCREPANCIA | No existe — ToolMultiSelect tiene lógica inline |

### Discrepancias encontradas:

1. **ID-017:** `useClickOutside` hook no existe como hook reusable. `ToolMultiSelect.tsx:32-40` tiene lógica inline duplicable.
2. **ID-018:** `AgentForm.tsx:224-229` usa `eslint-disable` para `useEffect` que depende de `llmModel` vía `watch()`. Dependencias incorrectas.
3. **ID-019:** `CrewCanvas.tsx:48` importa CSS de ReactFlow directo, no lazy/dynamic.
4. **ID-046/ID-048:** `AgentForm.tsx:203-222` `buildSingleAgentPayload()` es función plana — recrea objeto en cada render, sin `useMemo`.
5. **ID-021:** `ToolMultiSelect` es implementación custom — no se usa `cmdk`.
6. **ID-034:** `AgentForm.tsx` campos `goal`, `backstory` sin debounce en onChange.
7. **ID-026:** `BuilderLayout.tsx:28-50` `mapTemplateToFormValues()` no está extraído a `lib/template-mapper.ts`.
8. **ID-035:** `AgentPlayground.tsx:56-62` scrollRef apunta a div dentro de ScrollArea — ScrollArea tiene su propio manejo de scroll. Posible fricción.
9. **ID-050:** `BuilderTabContext.tsx` usa solo `useState` — no sincroniza con URL `?tab=` query params.
10. **ID-042:** `fapDownload` en `api.ts:54-94` hardcodea `method: 'POST'`. No acepta método HTTP como parámetro.
11. **ID-043:** No hay constantes centralizadas para métodos HTTP ni config de descarga en `constants.ts`.
12. **ID-021-b:** `cmdk` no está en `package.json:12-48`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**No hay cambios de schema, migraciones ni modelos de datos.** Este paso es 100% frontend (TypeScript/React). No afecta DB.

- ✅ No se tocan tablas Supabase
- ✅ No se requieren migraciones
- ✅ No hay cambios de RLS
- ✅ No hay índices ni constraints
- ⚠️ El único archivo "data" en frontend es `lib/constants.ts` — se agregarán constantes de HTTP/descarga

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 2.1 Hook `useClickOutside`

**Archivo a crear:** `dashboard/hooks/useClickOutside.ts`
**Firma exacta:**
```typescript
export function useClickOutside(
  ref: React.RefObject<HTMLElement>,
  handler: () => void,
  enabled?: boolean
): void
```
**Patrón a seguir:** `ToolMultiSelect.tsx:32-40` — extraer lógica inline. Revisar pattern en hooks existentes como `use-theme.tsx` (Context + useEffect).
**Uso:** Reemplazar `useEffect` inline en `ToolMultiSelect.tsx` y futuros selectores.

### 2.2 `lib/template-mapper.ts`

**Archivo a crear:** `dashboard/lib/template-mapper.ts`
**Firma exacta:**
```typescript
import type { AgentFormData } from '@/components/builder/AgentForm'
import type { TemplateDetail } from '@/components/builder/TemplatePicker'

const VALID_PROVIDERS = ['groq', 'openai', 'anthropic', 'openrouter'] as const
type Provider = AgentFormData['llmProvider']

function mapProvider(provider?: string): Provider {
  return (VALID_PROVIDERS as readonly string[]).includes(provider ?? '')
    ? (provider as Provider)
    : 'groq'
}

export function mapTemplateToFormValues(
  template: TemplateDetail
): AgentFormData { ... }
```
**Patrón a seguir:** `BuilderLayout.tsx:28-50` — mover función exacta.
**Efecto:** `BuilderLayout.tsx` importa desde `@/lib/template-mapper` en lugar de definir localmente.

### 2.3 Debounce hook (ID-034)

**Archivo a crear o añadir a hook existente:** `dashboard/hooks/useDebounce.ts`
**Firma exacta:**
```typescript
export function useDebounce<T>(value: T, delay?: number): T
```
**Uso:** Envolver `watch('goal')`, `watch('backstory')` en AgentForm para evitar re-renders en cada keystroke.

### 2.4 Mejora useMemo en AgentForm (ID-046/ID-048)

**Archivo:** `dashboard/components/builder/AgentForm.tsx`
**Cambio:** Envolver `buildSingleAgentPayload` con `useCallback` para memoizar el objeto de exportación.
```typescript
const buildSingleAgentPayload = useCallback((): { agents: AgentExportItem[] } => {
  const values = getValues()
  return { agents: [{ ... }] }
}, [getValues])
```

### 2.5 Fix useEffect dependencies (ID-018)

**Archivo:** `dashboard/components/builder/AgentForm.tsx:224-229`
**Cambio:** Reemplazar `// eslint-disable-next-line` con dependencias correctas:
```typescript
const currentModel = watch('llmModel')
useEffect(() => {
  if (availableModels.length > 0 && !availableModels.includes(currentModel)) {
    setValue('llmModel', availableModels[0])
  }
}, [llmProvider, availableModels, currentModel, setValue])
```
O mejor: usar `useEffect` con ref para evitar el bucle.

### 2.6 Mejorar Error del `zodResolver` (ID-023 reference)

**Archivo:** `dashboard/components/builder/AgentForm.tsx`
**Contexto:** Ya resuelto en fase previa según phase-state.md. No requiere acción aquí.

### 2.7 Fix scroll ref (ID-035)

**Archivo:** `dashboard/components/builder/AgentPlayground.tsx:56-62`
**Problema:** `scrollRef` apunta a `div` dentro de `ScrollArea`. `ScrollArea` de Radix gestiona scroll interno mediante `viewportRef`. El scroll manual puede no funcionar.
**Solución propuesta:** Usar `useEffect` con ref del viewport interno o delegar scroll a `ScrollArea` nativo. Alternativa: reemplazar `ScrollArea` por div con `overflow-y-auto` para scroll manual directo.

### 2.8 Dynamic CSS loading (ID-019)

**Archivo:** `dashboard/components/builder/CrewCanvas.tsx:48`
**Problema:** `import 'reactflow/dist/style.css'` carga en SSR aunque el componente se renderiza solo en cliente via `dynamic()`.
**Solución:** Ya hay SSR guard (`ssr: false` en `BuilderCanvas.tsx`). Pero el import CSS aún se incluye en bundle. Se debe migrar a import dinámico:
```typescript
useEffect(() => {
  import('reactflow/dist/style.css')
}, [])
```

### 2.9 ToolMultiSelect con `cmdk` (ID-021)

**Evaluación:** `cmdk` no está en `package.json`. Implementación custom actual de `ToolMultiSelect.tsx` (156 líneas) es funcional pero no tiene:
- Atajos de teclado (arrow keys, enter)
- Accesibilidad ARIA completa
- Búsqueda fuzzy

`cmdk` (`@cmdk/core` o `cmdk`) resolvería esto. **Dependencia nueva:** `cmdk` en `package.json:dependencies`.

**Archivo:** `dashboard/components/builder/ToolMultiSelect.tsx`

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**No hay cambios de backend.** Este paso es exclusivamente frontend.

- ✅ No se tocan endpoints
- ✅ No se tocan servicios
- ✅ No se tocan middlewares
- ✅ No se tocan contratos API
- ⚠️ El único impacto backend es si `fapDownload` en `api.ts` se flexibiliza para métodos HTTP — esto NO cambia el backend, solo el cliente HTTP frontend.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
Usuario → Builder (página) → BuilderTabContext (activeTab)
                           → BuilderLayout (tabs, dialogs)
                              → AgentForm (crea/edita agente)
                              → BuilderCanvas (ReactFlow dinámico)
                                 → CrewCanvas (canvas completo)
                              → TemplatePicker (selecciona template)
                                 → mapTemplateToFormValues (mapeo)
                              → AgentPlayground (test agente)
                              → ExportDialog (export ZIP o JSON)
                                 → fapDownload (POST /api/bundles/export)
```

### Puntos de fricción actuales

1. **useClickOutside duplicado:** ToolMultiSelect tiene lógica inline. Si otro componente necesita click-outside, debe copiar/pegar.
2. **Template mapper acoplado:** `mapTemplateToFormValues` está en `BuilderLayout.tsx`. No se puede reusar en tests ni en otro contexto.
3. **Payload no memoizado:** `buildSingleAgentPayload()` en AgentForm recrea objeto en cada render → causa re-renders innecesarios en `ExportDialog`.
4. **useEffect con eslint-disable:** Señal de deuda técnica.
5. **CSS de ReactFlow en bundle principal:** Impacta performance de carga inicial.
6. **Sin deep linking:** Builder tabs no persisten en URL → refrescar página pierde pestaña activa.
7. **Sin debounce:** `goal` y `backstory` disparan re-render en cada letra.
8. **ToolMultiSelect sin accesibilidad:** No keyboard navigation, no ARIA.
9. **Scroll ref incorrecto:** `AgentPlayground` usa scroll manual dentro de `ScrollArea` de Radix.
10. **fapDownload rígido:** Hardcodeado a `POST`. No reusable para GET downloads u otros métodos.

### DX & Tooling

```
### Herramienta Propuesta: fap doctor frontend
- **Qué automatiza:** Diagnostica salud del frontend Builder — verifica deep linking (?tab=), detecta useEffect sin dependencias, checkea memoización faltante, valida accesibilidad de selectores, mide tamaño de bundle CSS de ReactFlow.
- **Tipo:** Comando CLI extendiendo `fap doctor` existente
- **Cómo se usa:** `fap doctor frontend --check-links --check-memo`
- **Impacto para el usuario final:** Detecta regresiones de UX antes de commit. Reduce revisión manual de 10 puntos a 1 comando.
- **Prioridad:** Media (Tarea 0b)
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] `useClickOutside` hook existe en `dashboard/hooks/useClickOutside.ts` con firma correcta
✅ [CODE] `ToolMultiSelect.tsx` usa `useClickOutside` en lugar de useEffect inline
✅ [CODE] `mapTemplateToFormValues` extraído a `dashboard/lib/template-mapper.ts`
✅ [CODE] `BuilderLayout.tsx` importa `mapTemplateToFormValues` desde `lib/template-mapper.ts`
✅ [CODE] `AgentForm.tsx` usa `useMemo`/`useCallback` en `buildSingleAgentPayload`
✅ [CODE] `AgentForm.tsx` useEffect de llmModel sin eslint-disable y con dependencias correctas
✅ [CODE] `AgentForm.tsx` usa `useDebounce` para `role`, `goal`, `backstory` (o campo con onChange)
✅ [CODE] `useDebounce` hook existe en `dashboard/hooks/useDebounce.ts`
✅ [CODE] `CrewCanvas.tsx` importa `reactflow/dist/style.css` dinámicamente (useEffect lazy)
✅ [CODE] `BuilderTabContext.tsx` sincroniza `activeTab` con `?tab=` query param
✅ [CODE] `BuilderPage` lee `?tab=` de URL en SSR y lo pasa como `defaultTab`
✅ [CODE] `fapDownload` acepta parámetro `method` opcional (default 'POST')
✅ [CODE] `constants.ts` tiene constantes `HTTP_METHODS` exportadas
✅ [CODE] `ToolMultiSelect.tsx` migrado a `cmdk` con keyboard navigation y ARIA (o alternativa evaluada documentada)
✅ [FULLSTACK] Refrescar página en `/builder?tab=crew-canvas` mantiene pestaña activa
✅ [FULLSTACK] `AgentPlayground.tsx` scroll automático funciona sin fricción con ScrollArea
✅ [DX] `fap doctor frontend` script creado (o aclaración de que se difiere)
✅ [DX] `tsc --noEmit` y `next lint` pasan sin errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| `cmdk` introduce breaking change en ToolMultiSelect | Alta | Migrar dropdown custom a `cmdk` puede romper binding con `react-hook-form` | Probar en aislamiento. Mantener implementación actual como fallback. Si el riesgo es alto, posponer a paso futuro. |
| Sincronización query params → `BuilderTabContext` causa loop infinito | Media | `useEffect` que escucha `useSearchParams()` y actualiza estado puede causar re-render loop | Usar `useEffect` controlado con ref de sincronización. Leer query param solo en SSR (page.tsx) y pasar como prop. |
| Scroll automático en `AgentPlayground` no funciona si ScrollArea de Radix cambia API | Media | ScrollArea interno depende de `ScrollAreaViewport` que puede cambiar en versiones de Radix | Invertir a div simple con `overflow-y-auto`. Documentar decisión. |
| `useDebounce` introduce latencia perceptible en UI | Baja | 300ms de debounce en `goal`/`backstory` puede sentirse lento | Usar 150ms para campos críticos. Aplicar solo a campos que no requieren feedback inmediato. |
| Fragmentación de hooks: `useClickOutside`, `useDebounce`, `useBuilderTab` | Baja | Múltiples hooks sin estandarización | Seguir el patrón de `use-theme.tsx`. Cada hook = un archivo. |
| Query params conflict with existing navigation state | Baja | Si ya hay otros query params en la página, `?tab=` puede ser sobrescrito | Usar `URLSearchParams` para merge, no reemplazo total. |

---

## 7️⃣ Plan de Implementación

### Tarea 0 — DX & Tooling: Script de diagnóstico frontend

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Crear `fap doctor frontend` |
| **Artefacto** | `src/cli/commands/doctor_frontend.py` |
| **Interfaz exacta** | `def doctor_frontend(ctx: typer.Context, check_links: bool = False, check_memo: bool = False) -> None` |
| **Patrón a seguir** | `src/cli/commands/doctor_backend.py` — misma estructura de checks Rich |
| **Etapa** | DX |
| **Complejidad** | Media |
| **Tiempo Est.** | 1h |
| **Dependencias** | Ninguna |
| **Verificación** | `uv run fap doctor frontend --help` ejecuta sin errores |

### Tarea 1 — Crear hook `useClickOutside`

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Crear hook reusable `useClickOutside` |
| **Artefacto** | `dashboard/hooks/useClickOutside.ts` |
| **Interfaz exacta** | `export function useClickOutside(ref: React.RefObject<HTMLElement>, handler: () => void, enabled?: boolean): void` |
| **Patrón a seguir** | `dashboard/hooks/use-theme.tsx` — hook con useEffect, addEventListener/removeEventListener |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.3h |
| **Dependencias** | Tarea 0 |
| **Verificación** | `ToolMultiSelect` puede importarlo sin error TS |

### Tarea 2 — Refactor ToolMultiSelect con `useClickOutside`

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Reemplazar `useEffect` inline en ToolMultiSelect por `useClickOutside` |
| **Artefacto** | `dashboard/components/builder/ToolMultiSelect.tsx` (modificar) |
| **Interfaz exacta** | Reemplazar líneas 32-40 por `useClickOutside(containerRef, () => setOpen(false))` |
| **Patrón a seguir** | Tarea 1 (el hook recién creado) |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.2h |
| **Dependencias** | Tarea 1 |
| **Verificación** | ToolMultiSelect abre/cierra correctamente en UI |

### Tarea 3 — Extraer `mapTemplateToFormValues` a `lib/template-mapper.ts`

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Crear módulo con función de mapeo |
| **Artefacto** | `dashboard/lib/template-mapper.ts` (nuevo) + `dashboard/components/builder/BuilderLayout.tsx` (modificar) |
| **Interfaz exacta** | `export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData` |
| **Patrón a seguir** | `dashboard/lib/canvasUtils.ts` — función pura, importable, sin side effects |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.3h |
| **Dependencias** | Ninguna |
| **Verificación** | BuilderLayout importa desde `@/lib/template-mapper` sin error. Tests unitarios pueden importar la función. |

### Tarea 4 — Crear hook `useDebounce`

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Crear hook de debounce genérico |
| **Artefacto** | `dashboard/hooks/useDebounce.ts` (nuevo) |
| **Interfaz exacta** | `export function useDebounce<T>(value: T, delay?: number): T` |
| **Patrón a seguir** | Custom hooks existentes en `dashboard/hooks/` — hook puro con `useEffect` + `setTimeout` |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.3h |
| **Dependencias** | Tarea 0 |
| **Verificación** | Hook importable sin error TS |

### Tarea 5 — Aplicar debounce en AgentForm

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Envolver campos de texto con `useDebounce` para evitar re-renders |
| **Artefacto** | `dashboard/components/builder/AgentForm.tsx` (modificar) |
| **Interfaz exacta** | `const debouncedRole = useDebounce(watch('role'), 150)` y usar debouncedRole en onRoleChange |
| **Patrón a seguir** | Tarea 4 (el hook recién creado) |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.2h |
| **Dependencias** | Tarea 4 |
| **Verificación** | onRoleChange se dispara con 150ms de retraso tras dejar de escribir |

### Tarea 6 — Memoizar `buildSingleAgentPayload` con `useCallback`

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Envolver buildSingleAgentPayload con useCallback |
| **Artefacto** | `dashboard/components/builder/AgentForm.tsx` (modificar) |
| **Interfaz exacta** | `const buildSingleAgentPayload = useCallback((): { agents: AgentExportItem[] } => { ... }, [getValues])` |
| **Patrón a seguir** | `CrewCanvas.tsx:207-218` — useMemo/useCallback pattern existente |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.2h |
| **Dependencias** | Ninguna |
| **Verificación** | Referencia de `buildSingleAgentPayload` no cambia entre renders si getValues no cambia |

### Tarea 7 — Fix useEffect dependencies en AgentForm

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Eliminar eslint-disable en useEffect y arreglar dependencias |
| **Artefacto** | `dashboard/components/builder/AgentForm.tsx` (modificar, líneas 224-229) |
| **Interfaz exacta** | Eliminar comentario eslint-disable. Agregar dependencias correctas. Opcional: usar ref para evitar re-ejecución en bucle. |
| **Patrón a seguir** | Extraer `llmModel` watch antes del efecto: `const currentModel = watch('llmModel')` |
| **Etapa** | CODE |
| **Complejidad** | Media |
| **Tiempo Est.** | 0.3h |
| **Dependencias** | Ninguna |
| **Verificación** | `next lint` no reporta warning de exhaustive-deps en este useEffect |

### Tarea 8 — Dynamic CSS loading para ReactFlow

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Mover import CSS de ReactFlow a carga dinámica |
| **Artefacto** | `dashboard/components/builder/CrewCanvas.tsx` (modificar línea 48) |
| **Interfaz exacta** | Reemplazar `import 'reactflow/dist/style.css'` por `useEffect(() => { import('reactflow/dist/style.css') }, [])` dentro de `FlowCanvas` |
| **Patrón a seguir** | `BuilderCanvas.tsx` ya usa `dynamic(..., { ssr: false })` — complementar con lazy CSS |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.2h |
| **Dependencias** | Ninguna |
| **Verificación** | ReactFlow CSS se carga solo cuando CrewCanvas se monta en cliente |

### Tarea 9 — Sincronizar BuilderTabContext con Query Params

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Agregar sincronización bidireccional entre `activeTab` y URL `?tab=` |
| **Artefacto** | `dashboard/components/builder/BuilderTabContext.tsx` (modificar) + `dashboard/app/(app)/builder/page.tsx` (modificar) |
| **Interfaz exacta** | `BuilderTabProvider` acepta `defaultTab` desde `page.tsx` que lee `searchParams.tab`. `setActiveTab` actualiza `useSearchParams` vía `useRouter.replace`. |
| **Patrón a seguir** | Next.js `useSearchParams()` + `useRouter` |
| **Etapa** | FULLSTACK |
| **Complejidad** | Media |
| **Tiempo Est.** | 0.5h |
| **Dependencias** | Ninguna |
| **Verificación** | Navegar a `/builder?tab=crew-canvas` muestra la pestaña Crew Canvas activa. Cambiar pestaña actualiza URL. |

### Tarea 10 — Flexibilizar `fapDownload` con método HTTP

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Agregar parámetro `method` a `fapDownload` |
| **Artefacto** | `dashboard/lib/api.ts` (modificar, líneas 54-94) |
| **Interfaz exacta** | `export async function fapDownload(path: string, body: unknown, method?: string): Promise<Response>` donde `method` por defecto es `'POST'` |
| **Patrón a seguir** | `fapFetch` que ya acepta `options.method` genérico |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.2h |
| **Dependencias** | Ninguna |
| **Verificación** | `fapDownload('/path', {}, 'GET')` funciona sin cambiar comportamiento existente |

### Tarea 11 — Centralizar constantes HTTP

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Agregar constantes HTTP a `constants.ts` |
| **Artefacto** | `dashboard/lib/constants.ts` (modificar) |
| **Interfaz exacta** | `export const HTTP_METHODS = { GET: 'GET', POST: 'POST', PUT: 'PUT', PATCH: 'PATCH', DELETE: 'DELETE' } as const` |
| **Patrón a seguir** | `TEMPLATE_CATEGORIES`, `PROVIDER_MODELS` ya en constants.ts |
| **Etapa** | CODE |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.1h |
| **Dependencias** | Tarea 10 |
| **Verificación** | Importable sin error. Usado en `api.ts` en lugar de string 'POST'. |

### Tarea 12 — Fix scroll en AgentPlayground

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Reemplazar ScrollArea o corregir scroll ref |
| **Artefacto** | `dashboard/components/builder/AgentPlayground.tsx` (modificar, líneas 56-62 y 181-204) |
| **Interfaz exacta** | Opción A: reemplazar `<ScrollArea>` por `<div className="flex-1 overflow-y-auto">` con scrollRef directo. Opción B: usar `ScrollArea.Viewport` ref si Radix lo expone. |
| **Patrón a seguir** | Patrón de scroll manual sin ScrollArea (revisar otros componentes en dashboard para ejemplo) |
| **Etapa** | CODE |
| **Complejidad** | Media |
| **Tiempo Est.** | 0.3h |
| **Dependencias** | Ninguna |
| **Verificación** | Scroll automático al final funciona al recibir mensajes nuevos |

### Tarea 13 — Evaluar/migrar ToolMultiSelect a `cmdk` (opcional)

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Evaluar migración a `cmdk` para ToolMultiSelect |
| **Artefacto** | `dashboard/package.json` (modificar, agregar cmdk) + `dashboard/components/builder/ToolMultiSelect.tsx` (modificar) |
| **Interfaz exacta** | Usar `Command` de `cmdk` para search + select con teclado |
| **Patrón a seguir** | shadcn/ui combobox pattern (Command + Popover) |
| **Etapa** | CODE |
| **Complejidad** | Alta |
| **Tiempo Est.** | 1.5h |
| **Dependencias** | Tarea 1 (useClickOutside aún necesario para cerrar dropdown) |
| **Verificación** | ToolMultiSelect navegable con arrow keys + Enter. ARIA correcta. `npm run build` sin errores. |
| **Nota** | Si el riesgo de regresión es alto, documentar evaluación y posponer a paso futuro. |

### Tarea 14 — Validar flujo completo y criterios

| Aspecto | Detalle |
|---------|---------|
| **Tarea** | Verificar que todos los criterios de aceptación se cumplen |
| **Artefacto** | — (validación) |
| **Interfaz exacta** | Ejecutar `next lint`, `tsc --noEmit`, verificar deep linking, scroll, memo, debounce |
| **Patrón a seguir** | — |
| **Etapa** | FULLSTACK |
| **Complejidad** | Baja |
| **Tiempo Est.** | 0.5h |
| **Dependencias** | Todas las tareas 1-13 |
| **Verificación** | Todos los criterios de §5 pasan |

**Tiempo total estimado:** 5.8h (con cmdk) / 4.3h (sin cmdk)

---

## 🔮 Roadmap

- **Paso 15** (Expansión de Cobertura y DX de Tests) puede agregar tests unitarios para los hooks y funciones creadas aquí
- La migración a `cmdk` podría unificarse con el paso 15 si se decide posponer
- `fap doctor frontend` como herramienta DX complementaria a `fap doctor builder` y `fap doctor backend`
