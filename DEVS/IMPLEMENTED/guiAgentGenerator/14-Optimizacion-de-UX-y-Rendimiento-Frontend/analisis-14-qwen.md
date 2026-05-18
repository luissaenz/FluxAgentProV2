# Análisis Técnico — Paso 14: Optimización de UX y Rendimiento Frontend

**Agente:** qwen  
**Fecha:** 2026-05-18  
**Fase:** guiAgentGenerator  
**Origen:** Sugerencias 🔵 de validación (ID-017, ID-018, ID-019, ID-021, ID-026, ID-034, ID-035, ID-038, ID-044, ID-045, ID-046, ID-048, ID-050, ID-042, ID-043)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `useClickOutside` hook | grep en `dashboard/hooks/` | ❌ | NO EXISTE — lógica inline en `ToolMultiSelect.tsx:32-39` |
| 2 | ReactFlow CSS import directo | `CrewCanvas.tsx:48` | ✅ | `import 'reactflow/dist/style.css'` — carga síncrona en bundle principal |
| 3 | `useMemo` en `canvasToExportPayload` | `CrewCanvas.tsx:207` | ✅ | `useMemo(() => canvasToExportPayload(nodes), [nodes])` |
| 4 | `useMemo` en `nodesToSnapshot` | `CrewCanvas.tsx:209` | ✅ | `useMemo(() => nodesToSnapshot(nodes, edges), [nodes, edges])` |
| 5 | `useMemo` en `exportAgents` | `CrewCanvas.tsx:211-218` | ✅ | `useMemo` con dependencia `[exportPayload]` |
| 6 | `cmdk` dependency | `dashboard/package.json` | ❌ | NO instalado — no aparece en dependencies |
| 7 | Debounce en campos de texto | `AgentForm.tsx` | ❌ | Sin debounce — inputs controlados por react-hook-form sin delay |
| 8 | `lib/template-mapper.ts` | `dashboard/lib/` | ❌ | NO EXISTE — `mapTemplateToFormValues` inline en `BuilderLayout.tsx:28-50` |
| 9 | Query params para tabs (`?tab=`) | `BuilderTabContext.tsx` | ❌ | Usa `useState` local — sin sync con URL |
| 10 | `navigator.clipboard` fallback | `ExportDialog.tsx:91-99` | ✅ | Tiene try/catch con fallback toast |
| 11 | Scroll ref en AgentPlayground | `AgentPlayground.tsx:56-61` | ✅ | `useRef<HTMLDivElement>` + `useEffect` scroll auto |
| 12 | `duplicatedRoles` computed | `CrewCanvas.tsx:339-349` | ⚠️ | Calculado en cada render — NO memoizado |
| 13 | `nodesWithWarnings` computed | `CrewCanvas.tsx:354-357` | ⚠️ | Calculado en cada render — NO memoizado |
| 14 | `sidebarAgents` derived | `CrewCanvas.tsx:337` | ⚠️ | `agentsData?.agents ?? []` — NO memoizado |
| 15 | `hasAgentNodes` / `exportDisabled` | `CrewCanvas.tsx:351-352` | ⚠️ | Calculados inline en cada render |
| 16 | `filtered` en TemplatePicker | `TemplatePicker.tsx:74-84` | ✅ | `useMemo` correcto |
| 17 | `grouped` en ToolMultiSelect | `ToolMultiSelect.tsx:52-59` | ✅ | `useMemo` correcto |
| 18 | `toolOptions` en AgentForm | `AgentForm.tsx:135-139` | ❌ | Calculado en cada render — NO memoizado |
| 19 | `availableModels` en AgentForm | `AgentForm.tsx:141` | ❌ | Lookup directo en cada render — NO memoizado |
| 20 | `api.ts` soporta métodos HTTP | `api.ts:96-118` | ✅ | `get`, `post`, `put`, `patch`, `delete` |
| 21 | `fapDownload` hardcoded POST | `api.ts:54-94` | ⚠️ | Solo POST — no soporta GET para descargas |
| 22 | Constantes centralizadas | `lib/constants.ts` | ✅ | `PROVIDER_MODELS`, `TEMPLATE_CATEGORIES`, `TEMPLATE_CACHE_MS` |
| 23 | `eslint-disable` exhaustive-deps | `AgentForm.tsx:228`, `CrewCanvas.tsx:113` | ✅ | 2 instancias — justificables pero revisar |
| 24 | `BuilderCanvas` dynamic import SSR | `BuilderCanvas.tsx:6-8` | ✅ | `dynamic(..., { ssr: false })` |

**Discrepancias encontradas:**
1. **`useClickOutside` no existe como hook reutilizable** — lógica duplicada inline en `ToolMultiSelect.tsx`. Debe extraerse.
2. **ReactFlow CSS carga síncrona** — `import 'reactflow/dist/style.css'` en `CrewCanvas.tsx:48` bloquea render inicial. Debe ser dynamic.
3. **`cmdk` no instalado** — plan sugiere migrar selector de herramientas a `cmdk` (CommandPalette), pero dependencia no existe.
4. **Sin debounce en AgentForm** — campos de texto largos (goal, backstory) disparan re-renders en cada keystroke.
5. **`mapTemplateToFormValues` no modularizado** — inline en `BuilderLayout.tsx:28-50`, debería estar en `lib/template-mapper.ts`.
6. **Tabs sin sync con URL** — `BuilderTabContext` usa `useState` puro. No permite deep linking ni compartir URLs con tab activo.
7. **Múltiples derivados no memoizados en CrewCanvas** — `duplicatedRoles`, `nodesWithWarnings`, `hasAgentNodes`, `exportDisabled`, `sidebarAgents` se recalculan en cada render.
8. **`fapDownload` solo soporta POST** — si en futuro se necesita GET para descarga (ej: export GET), requiere refactor.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

Este paso NO toca schema de DB directamente. Es puramente frontend. Impacto en datos:

- **Sin cambios de schema.**
- **localStorage existente:** `fap_crew_canvas_snapshot` en `CrewCanvas.tsx:50` — patrón de autosave cada 30s. No se modifica.
- **Query params propuestos:** `?tab=` para deep linking de tabs. No requiere DB, solo URL state.
- **Sin RLS, índices, ni constraints afectados.**

**Impacto indirecto:**
- Si `cmdk` se integra para selector de herramientas, las queries a `GET /api/tools/available` siguen igual — solo cambia UI.
- Debounce en campos reduce cantidad de `watch()` triggers en react-hook-form — mejora performance sin cambiar datos.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/Hooks nuevos requeridos:

#### 2.1 `useClickOutside` hook
**Archivo:** `dashboard/hooks/useClickOutside.ts`  
**Firma:**
```typescript
function useClickOutside(
  ref: RefObject<HTMLElement | null>,
  handler: (event: MouseEvent) => void
): void
```
**Patrón a seguir:** Hook estándar de click-outside. Referencia: patrón común en React docs.  
**Uso:** Reemplazar lógica inline en `ToolMultiSelect.tsx:32-39`.

#### 2.2 `useDebounce` hook
**Archivo:** `dashboard/hooks/useDebounce.ts`  
**Firma:**
```typescript
function useDebounce<T>(value: T, delay: number): T
```
**Patrón a seguir:** Hook estándar de debounce con `setTimeout` + cleanup.  
**Uso:** Debounce en campos de texto de `AgentForm` (goal, backstory, role).

#### 2.3 `mapTemplateToFormValues` → `lib/template-mapper.ts`
**Archivo:** `dashboard/lib/template-mapper.ts`  
**Firma:**
```typescript
function mapTemplateToFormValues(template: TemplateDetail): AgentFormData
```
**Patrón a seguir:** Extraer exactamente la función de `BuilderLayout.tsx:28-50` sin cambios de lógica.  
**Imports:** `import type { TemplateDetail } from '@/components/builder/TemplatePicker'`, `import type { AgentFormData } from '@/components/builder/AgentForm'`.

### Funciones existentes a optimizar:

#### 2.4 Memoización en `CrewCanvas.tsx`
- `duplicatedRoles` (línea 339-349) → envolver en `useMemo` con deps `[nodes]`
- `nodesWithWarnings` (línea 354-357) → envolver en `useMemo` con deps `[nodes, edges]`
- `hasAgentNodes` (línea 351) → envolver en `useMemo` con deps `[nodes]`
- `exportDisabled` (línea 352) → envolver en `useMemo` con deps `[hasAgentNodes, duplicatedRoles]`
- `sidebarAgents` (línea 337) → envolver en `useMemo` con deps `[agentsData]`

#### 2.5 Memoización en `AgentForm.tsx`
- `toolOptions` (línea 135-139) → envolver en `useMemo` con deps `[toolsResponse]`
- `availableModels` (línea 141) → envolver en `useMemo` con deps `[llmProvider]`

#### 2.6 Dynamic CSS de ReactFlow
**Archivo:** `dashboard/components/builder/CrewCanvas.tsx`  
**Cambio:** Reemplazar `import 'reactflow/dist/style.css'` (línea 48) con import dinámico:
```typescript
useEffect(() => {
  import('reactflow/dist/style.css')
}, [])
```
O mejor: mover a `BuilderCanvas.tsx` (el wrapper dynamic) para que CSS cargue solo cuando CrewCanvas se monta en cliente.

### Patrones existentes a seguir:
- **Hook pattern:** `dashboard/hooks/useCurrentOrg.ts` — hook simple con return de valor.
- **Memo pattern:** `CrewCanvas.tsx:87-90` (`orgId` con `useMemo`) — referencia para derivados.
- **Dynamic import pattern:** `BuilderCanvas.tsx:6-8` — referencia para CSS lazy load.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Sin cambios en backend.** Este paso es 100% frontend.

**Contratos existentes que se mantienen:**
- `GET /api/tools/available` — sin cambios
- `GET /api/templates` — sin cambios
- `POST /api/bundles/export` — sin cambios
- `POST /agents/{role}/run` — sin cambios

**API helper `api.ts`:**
- `fapDownload` (línea 54-94) — actualmente hardcoded POST. Para soporte de métodos HTTP variables (ID-042), agregar parámetro `method`:
```typescript
export async function fapDownload(
  path: string,
  body: unknown,
  method: 'POST' | 'GET' = 'POST'
): Promise<Response>
```
Pero esto es opcional — el paso 14 no requiere cambio de método para export actual.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end:

```
[URL con ?tab=crew-canvas]
  → BuilderTabContext lee query param → activa tab correcto
  → BuilderLayout renderiza CrewCanvas
  → CrewCanvas carga ReactFlow CSS dinámicamente (no bloquea)
  → Nodos memoizados → re-render mínimo al drag/drop
  → ToolMultiSelect usa useClickOutside (hook reutilizable)
  → AgentForm usa debounce en goal/backstory
  → TemplatePicker usa mapTemplateToFormValues desde lib/template-mapper.ts
  → Export → fapDownload POST /bundles/export → ZIP descarga
```

### Coherencia:
- Query params para tabs permite compartir URLs de builder con tab específico activo. Coherente con Next.js routing.
- Dynamic CSS de ReactFlow mejora FCP sin afectar funcionalidad.
- Memoización de derivados en CrewCanvas reduce re-renders innecesarios durante drag-and-drop.
- `useClickOutside` extraído permite reuso futuro en cualquier dropdown/selector.

### Gaps identificados:
1. **Tabs sin URL sync** — usuario no puede compartir link a "Crew Canvas" tab directamente.
2. **ReactFlow CSS bloqueante** — impacta LCP en página builder.
3. **Derivados no memoizados** — cada keystroke en formulario recalcula `duplicatedRoles`, `nodesWithWarnings`, etc.
4. **Template mapper inline** — dificulta testing unitario y reuso.

### DX & Tooling — OBLIGATORIO:

### Herramienta Propuesta: `fap perf builder`
- **Qué automatiza:** Diagnóstico de performance del builder frontend — detecta componentes sin memoización, hooks inline que deberían ser reutilizables, imports síncronos bloqueantes, y ausencia de debounce en inputs.
- **Tipo:** CLI command
- **Cómo se usa:** `uv run fap perf builder --scan dashboard/components/builder/`
- **Impacto para el usuario final:** Antes de cada PR al builder, el desarrollador ejecuta un check automático que identifica regresiones de performance (derivados no memoizados, re-renders excesivos). Evita que código no optimizado llegue a producción.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

### Herramienta Propuesta: `perf-audit.ts` (script de validación)
- **Qué automatiza:** Escaneo estático de archivos TSX del builder para detectar: (1) `useEffect` con lógica de click-outside que debería ser hook, (2) cálculos derivados fuera de `useMemo`, (3) imports de CSS de librerías grandes sin dynamic import.
- **Tipo:** Script TypeScript ejecutable con `npx tsx`
- **Cómo se usa:** `npx tsx scripts/perf-audit.ts --path dashboard/components/builder/`
- **Impacto para el usuario final:** Validación pre-commit que asegura que las optimizaciones del paso 14 se mantengan en el tiempo.
- **Prioridad:** Tarea 0b — complementar a `fap perf builder`.

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] Hook `useClickOutside` existe en `dashboard/hooks/useClickOutside.ts` con firma correcta
✅ [CODE] Hook `useDebounce` existe en `dashboard/hooks/useDebounce.ts` con firma correcta
✅ [CODE] `mapTemplateToFormValues` exportada desde `dashboard/lib/template-mapper.ts`
✅ [CODE] `ToolMultiSelect.tsx` usa `useClickOutside` en lugar de lógica inline
✅ [CODE] `CrewCanvas.tsx` — `duplicatedRoles`, `nodesWithWarnings`, `hasAgentNodes`, `exportDisabled`, `sidebarAgents` memoizados con `useMemo`
✅ [CODE] `AgentForm.tsx` — `toolOptions` y `availableModels` memoizados con `useMemo`
✅ [PERF] ReactFlow CSS cargado dinámicamente (no en import síncrono de `CrewCanvas.tsx`)
✅ [PERF] Debounce de 300ms aplicado a campos `goal`, `backstory`, `role` en `AgentForm.tsx`
✅ [UX] `BuilderTabContext` sincroniza con query param `?tab=` (deep linking funcional)
✅ [UX] URL `/builder?tab=crew-canvas` abre directamente en tab Crew Canvas
✅ [DX] `cmdk` instalado como dependencia (`npm install cmdk`)
✅ [DX] Script `perf-audit.ts` ejecuta sin errores y detecta al menos 1 issue en código pre-optimización
✅ [FULLSTACK] `tsc --noEmit` sin errores en todo el dashboard
✅ [FULLSTACK] Builder funciona end-to-end: crear agente → cambiar tab → exportar → descargar ZIP
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Deep linking con `?tab=` rompe navegación existente | Media | `BuilderTabContext` actual no maneja URL; añadir query param puede conflictuar con `defaultTab` prop | Leer query param solo en `page.tsx`, pasar como `defaultTab` al provider. Sin cambios en context internals. |
| Debounce en react-hook-form causa latencia percibida | Baja | Delay de 300ms en validación puede hacer que usuario piense que no se registró el input | Usar debounce solo en `watch()` values, no en `register()`. Validación Zod se mantiene síncrona en submit. |
| Dynamic CSS de ReactFlow causa FOUC (flash of unstyled content) | Media | CSS carga después del mount inicial | Mover dynamic import a `BuilderCanvas.tsx` (wrapper ya dynamic con skeleton loading). Skeleton se muestra hasta que CSS + componente estén listos. |
| `cmdk` introduce breaking changes en ToolMultiSelect | Media | API de `cmdk` diferente al dropdown custom actual | Implementar `cmdk` como componente separado `ToolCommandPalette.tsx`, mantener `ToolMultiSelect` como fallback. Migración gradual. |
| Memoización excesiva causa stale closures | Baja | `useMemo` con deps incorrectos puede cachear valores viejos | Revisar deps de cada `useMemo` contra variables usadas en el cálculo. Test visual de drag-and-drop post-cambio. |
| `mapTemplateToFormValues` movido rompe import en `BuilderLayout.tsx` | Baja | Import path cambia | Actualizar import en `BuilderLayout.tsx`. Verificar con `tsc --noEmit`. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Script `perf-audit.ts` | `scripts/perf-audit.ts` | `#!/usr/bin/env node` — escanea directorio, imprime issues | `scripts/validate_builder_nav.py` (estructura de scan + reporte) | DX | Media | 2h | Ninguna | → verificar: `npx tsx scripts/perf-audit.ts --path dashboard/components/builder/` imprime ≥1 issue |
| 1 | Crear hook `useClickOutside` | `dashboard/hooks/useClickOutside.ts` | `function useClickOutside(ref: RefObject<HTMLElement \| null>, handler: (e: MouseEvent) => void): void` | `dashboard/hooks/useCurrentOrg.ts` (hook simple con export default) | CODE | Baja | 0.5h | Tarea 0 | → verificar: `import { useClickOutside } from '@/hooks/useClickOutside'` sin error de tipo |
| 2 | Refactorizar `ToolMultiSelect` para usar `useClickOutside` | `dashboard/components/builder/ToolMultiSelect.tsx` | Reemplazar líneas 32-39 con `useClickOutside(containerRef, () => setOpen(false))` | `ToolMultiSelect.tsx` existente (mismo componente, solo swap de lógica) | CODE | Baja | 0.5h | Tarea 1 | → verificar: dropdown se cierra al click fuera, no se cierra al click dentro |
| 3 | Crear hook `useDebounce` | `dashboard/hooks/useDebounce.ts` | `function useDebounce<T>(value: T, delay: number): T` | `dashboard/hooks/useCurrentOrg.ts` (hook simple) | CODE | Baja | 0.5h | Tarea 0 | → verificar: `import { useDebounce } from '@/hooks/useDebounce'` sin error de tipo |
| 4 | Aplicar debounce en `AgentForm` campos de texto | `dashboard/components/builder/AgentForm.tsx` | `const debouncedRole = useDebounce(watch('role'), 300)` — igual para goal, backstory | `AgentForm.tsx` existente — añadir `useDebounce` calls después de `watch()` calls (línea 116-118) | CODE | Baja | 1h | Tarea 3 | → verificar: escribir rápido en campo goal → valor debounceado se actualiza tras 300ms de inactividad |
| 5 | Extraer `mapTemplateToFormValues` a `lib/template-mapper.ts` | `dashboard/lib/template-mapper.ts` | `export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData` — cuerpo idéntico a `BuilderLayout.tsx:28-50` | `dashboard/lib/canvasUtils.ts` (funciones puras exportadas) | CODE | Baja | 0.5h | Tarea 0 | → verificar: `import { mapTemplateToFormValues } from '@/lib/template-mapper'` sin error + template se aplica igual en builder |
| 6 | Actualizar `BuilderLayout.tsx` para importar mapper | `dashboard/components/builder/BuilderLayout.tsx` | `import { mapTemplateToFormValues } from '@/lib/template-mapper'` — eliminar función local línea 28-50 | `BuilderLayout.tsx` existente — solo cambiar import + borrar función inline | CODE | Baja | 0.25h | Tarea 5 | → verificar: `tsc --noEmit` sin errores + template picker rellena formulario correctamente |
| 7 | Memoizar derivados en `CrewCanvas.tsx` | `dashboard/components/builder/CrewCanvas.tsx` | `const duplicatedRoles = useMemo(() => { ... }, [nodes])` — igual para `nodesWithWarnings` ([nodes, edges]), `hasAgentNodes` ([nodes]), `exportDisabled` ([hasAgentNodes, duplicatedRoles]), `sidebarAgents` ([agentsData]) | `CrewCanvas.tsx:87-90` (`orgId` con `useMemo`) — mismo patrón | CODE | Media | 1h | Tarea 0 | → verificar: React DevTools Profiler muestra menos re-renders al hacer drag de agente al canvas |
| 8 | Memoizar derivados en `AgentForm.tsx` | `dashboard/components/builder/AgentForm.tsx` | `const toolOptions = useMemo(() => (toolsResponse?.tools ?? []).map(...), [toolsResponse])` — `const availableModels = useMemo(() => PROVIDER_MODELS[llmProvider] ?? [], [llmProvider])` | `CrewCanvas.tsx:207` (`exportPayload` con `useMemo`) — mismo patrón | CODE | Baja | 0.5h | Tarea 0 | → verificar: cambiar provider → models se recalculan una sola vez, no en cada render |
| 9 | Dynamic CSS de ReactFlow | `dashboard/components/builder/CrewCanvas.tsx` + `BuilderCanvas.tsx` | Eliminar `import 'reactflow/dist/style.css'` de `CrewCanvas.tsx:48`. Añadir `useEffect(() => { import('reactflow/dist/style.css') }, [])` en `FlowCanvas` o mover a `BuilderCanvas.tsx` | `BuilderCanvas.tsx:6-8` (dynamic import pattern) | CODE | Baja | 0.5h | Tarea 0 | → verificar: builder carga sin FOUC, ReactFlow nodes estilizados correctamente |
| 10 | Sincronizar tabs con query params `?tab=` | `dashboard/app/(app)/builder/page.tsx` + `dashboard/components/builder/BuilderTabContext.tsx` | En `page.tsx`: leer `searchParams` → pasar `defaultTab` al provider. En `BuilderTabContext.tsx`: añadir `onTabChange` callback que actualiza URL via `window.history.pushState` | Next.js pattern: `useSearchParams` hook + `useEffect` para sync bidireccional | FULLSTACK | Media | 1.5h | Tarea 0 | → verificar: navegar a `/builder?tab=crew-canvas` abre tab Crew Canvas; cambiar tab actualiza URL |
| 11 | Instalar `cmdk` | `dashboard/package.json` | `npm install cmdk` | — | DX | Baja | 0.25h | Ninguna | → verificar: `import { Command } from 'cmdk'` sin error de tipo |
| 12 | Evaluar migración ToolMultiSelect a `cmdk` | `dashboard/components/builder/ToolCommandPalette.tsx` (nuevo) | Componente con `Command`, `CommandInput`, `CommandList`, `CommandItem` — misma interfaz props que `ToolMultiSelect` | `cmdk` docs examples + `ToolMultiSelect.tsx` (mismas props: options, values, onChange) | UX | Alta | 3h | Tarea 11 | → verificar: selector de herramientas funciona con búsqueda + selección múltiple vía cmdk |
| 13 | Añadir soporte método HTTP en `fapDownload` | `dashboard/lib/api.ts` | `export async function fapDownload(path: string, body: unknown, method: 'POST' \| 'GET' = 'POST'): Promise<Response>` — usar `method` param en fetch options | `api.ts:54-94` existente — añadir param + condicional para body (GET no lleva body) | CODE | Baja | 0.5h | Tarea 0 | → verificar: `fapDownload('/test', null, 'GET')` ejecuta GET sin error |
| 14 | Validación end-to-end | — | Ejecutar flujo completo: crear agente → cambiar tab vía URL → usar template → exportar → descargar | — | FULLSTACK | Baja | 1h | Tareas 1-13 | → verificar: todos los criterios §5 pasan |

**Tiempo total estimado:** 13 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Virtualización de lista de agentes** en sidebar de CrewCanvas — si org tiene 100+ agentes, el scroll se degrada. Usar `@tanstack/react-virtual`.
- **WebSocket para AgentPlayground** — reemplazar polling de 2s por streaming SSE/WebSocket para respuesta en tiempo real.
- **Service Worker para cache de templates/tools** — reducir llamadas a API en sesiones repetidas.
- **Keyboard shortcuts en Builder** — `Ctrl+S` para guardar agente, `Ctrl+E` para export, `Ctrl+T` para abrir template picker.
- **Undo/Redo en CrewCanvas** — historial de estados del grafo con `useReducer` + localStorage.
- **Colaboración en tiempo real** — múltiples usuarios editando el mismo crew canvas simultáneamente (Yjs + WebSocket).
