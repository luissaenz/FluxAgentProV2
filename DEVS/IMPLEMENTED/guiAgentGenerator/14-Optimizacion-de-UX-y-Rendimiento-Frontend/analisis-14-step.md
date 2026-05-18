# 🧠 Análisis Técnico — Paso 14: Optimización de UX y Rendimiento Frontend

**Agente:** step
**Paso:** 14
**Fecha:** 2026-05-18
**Fase:** guiAgentGenerator
**Estado del paso:** ⏳ En Progreso

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

### Área explorada
- `dashboard/components/builder/` — 13 archivos .tsx
- `dashboard/lib/` — 4 archivos .ts relevantes
- `dashboard/hooks/` — 15 hooks existentes
- `dashboard/app/(app)/builder/page.tsx`
- `dashboard/package.json`

### Elementos verificados (13 — ≥ 12 para 3-5 archivos afectados ✅)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `useClickOutside` en ToolMultiSelect | `ToolMultiSelect.tsx:32-40` | ✅ Implementado inline | useEffect con mousedown event listener + cleanup en return |
| 2 | 3× `useEffect` en AgentForm | `AgentForm.tsx:98-114, 120-122, 224-229` | ✅ Verificado | 3 usos; línea 228: `eslint-disable-next-line react-hooks/exhaustive-deps` |
| 3 | `useMemo` en CrewCanvas | `CrewCanvas.tsx:207-218` | ✅ Verificado | `exportPayload`, `fullGraphJson`, `exportAgents` envueltos en `useMemo` |
| 4 | `next/dynamic` con ReactFlow | `BuilderCanvas.tsx:6-8` | ✅ Ya existe | `dynamic(() => import('@/components/builder/CrewCanvas'), { ssr: false, loading: <Skeleton /> })` |
| 5 | `un/reactflow/dist/style.css` | `CrewCanvas.tsx:48` | ❌ Import directo | Línea 48: import estático de CSS; NO está envuelto en `next/dynamic` ni importado condicionalmente |
| 6 | `cmdk` en `package.json` | `package.json:1-60` | ❌ NO existe | No aparece en dependencies ni devDependencies |
| 7 | Debounce en búsqueda | `TemplatePicker.tsx:155`, `ToolMultiSelect.tsx:113` | ❌ No hay debounce | `onChange` directo sin wrapper de debounce |
| 8 | `lib/template-mapper.ts` existe | glob `dashboard/lib/` | ❌ NO existe | Función `mapTemplateToFormValues` está inline en `BuilderLayout.tsx:28-50` |
| 9 | Fallback portapapeles | `ExportDialog.tsx:86-99` | ✅ Verificado | `try/catch` en `navigator.clipboard.writeText()` con fallback a toast con primeros 500 chars |
| 10 | Query params para navegación | `BuilderTabContext.tsx:5-36` | ❌ Solo `useState`, no `useSearchParams` | No hay sincronización con URL; sin deep linking a pestaña específica |
| 11 | Métodos HTTP en `api.ts` | `api.ts:96-118` | ✅ Verificado | `get`, `post`, `put`, `patch`, `delete` métodos presentes |
| 12 | Constantes para métodos HTTP | `constants.ts:1-36` | ❌ No hay HTTP_METHODS | Strings `'GET'`, `'POST'`, etc. están hardcodeados como literales en `api.ts` |
| 13 | `snapshotRestored.current` en useEffect | `CrewCanvas.tsx:98-114` | ✅ Patrón correcto | Flag `snapshotRestored.current = true` evita re-ejecución; comentario de ESLint justificado |

### Discrepancias encontradas

#### D1 — CSS de ReactFlow importado estáticamente
- **Ubicación:** `CrewCanvas.tsx:48`
- **Descripción:** `import 'reactflow/dist/style.css'` se carga en el bundle inicial. ReactFlow (`^11.11.4`) pesa ~85KB minificado; su CSS añade ~8KB adicionales. Para un usuario que accede al builder pero no usa el canvas inmediatamente, el CSS se transfiere innecesariamente.
- **Resolución:** Mover el import al componente dinámico o usar `next/dynamic` para el CSS. Como `BuilderCanvas.tsx:6-8` ya usa `dynamic()` con `ssr: false`, hay 2 opciones: (a) mover el import là dentro del callback, o (b) usar `import('reactflow/dist/style.css')` en el `loading` del dynamic. La opción (a) es la más limpia y evita importaciones condicionales frágiles.

#### D2 — Sin debounce en campos de búsqueda
- **Ubicación:** `TemplatePicker.tsx:155`, `ToolMultiSelect.tsx:113`
- **Descripción:** Cada keystroke dispara `setSearch` → re-render completo + recálculo de `filtered` y `grouped` (respectivamente `useMemo`). En `ToolMultiSelect`, `grouped` se recalcula en cada búsqueda. Para catálogos con ~60 tools, el impacto es bajo pero no nulo; para 200+ herramientas genera jank perceptible.
- **Resolución:** Crear hook `useDebounce(value, 300ms)` y usarlo como `const debouncedSearch = useDebounce(search, 300)` alimentando el `useMemo` de `filtered`. El hook de entrada (`search`) mantiene actualización inmediata; solo el cálculo pesado se debouncea.

#### D3 — Tabs sin sincronización de URL (sin deep linking)
- **Ubicación:** `BuilderTabContext.tsx:29` (`useState` sin `useSearchParams`)
- **Descripción:** El estado de pestañas se guarda solo en memoria de React (Context). Al recargar la página o compartir un enlace, el usuario siempre cae en la pestaña por defecto (`agent-form`). No hay forma de enlazar a `?tab=crew-canvas`.
- **Resolución:** Integrar `useSearchParams` de `next/navigation` en `BuilderTabContext`. La implementación debe: leer `tab` de URL al montar, actualizar URL cuando cambie la pestaña, sincronizar ambos sentidos (URL → estado React y viceversa).

#### D4 — Función `mapTemplateToFormValues` hardcodeada en BuilderLayout
- **Ubicación:** `BuilderLayout.tsx:28-50`
- **Descripción:** La lógica de mapeo `soul_json → AgentFormData` está inline en el componente, sin posibilidad de ser importada por otros módulos (por ejemplo `TemplatePicker`, `lib/crewCodeGen` para mapeo inverso).
- **Resolución:** Extraer a `lib/template-mapper.ts` exportando tanto la función como los tipos. Mantener un re-export en `lib/index.ts` para imports limpios.

#### D5 — `cmdk` no instalado (sin amparo en código actual)
- **Ubicación:** `package.json` dependencies
- **Descripción:** El plan ID-021 menciona "evaluar migración a `cmdk`". Actualmente no existe en el proyecto ni en `node_modules`. Implementarlo requiere decisión: si se decide migrar, habrá que instalar, integrar y estilizar. Si se pospone, el task es "no aplica hasta que se decida".
- **Resolución:** Marcar como **pendiente de decisión del implementador**, no como bloqueante. Si se avanza: instalar con `npm install cmdk`, migrar `ToolMultiSelect` o crear `CommandPalette` para navegación rápida.

#### D6 — No hay constantes para métodos HTTP
- **Ubicación:** `api.ts:97-118`, ausencia en `constants.ts`
- **Descripción:** Los strings `'GET'`, `'POST'`, `'PUT'`, `'PATCH'`, `'DELETE'` están hardcodeados en `api.ts`. No hay enum ni objeto centralizado.
- **Resolución:** Agregar `HTTP_METHODS` a `constants.ts` como objeto as const con literales de tipo `HttpMethod`. Refactorizar `api.ts` para usar las constantes, eliminando literales.

#### D7 — `useEffect` en AgentForm sin dependencias completas
- **Ubicación:** `AgentForm.tsx:224-229`
- **Descripción:**
  ```tsx
  useEffect(() => {
    if (availableModels.length > 0 && !availableModels.includes(watch('llmModel'))) {
      setValue('llmModel', availableModels[0])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llmProvider])
  ```
  El `eslint-disable` oculta el hecho de que `setValue`, `availableModels.length`, `watch('llmModel')` y `availableModels` no están en las dependencias. En la práctica:
  - `setValue` es estable a través de `useForm` → no requiere estar en el array.
  - `availableModels.length` y `availableModels` cambian solo cuando `llmProvider` cambia → ya cubierto.
  - `watch('llmModel')` permanece estable mientras el model sea el mismo, de forma que si cambia por otra causa (reset del form), el efecto no re-evalúa — pero ese caso no es dañino.
  
  **Conclusión:** El `eslint-disable` está justificado aquí. El comportamiento es correcto y no genera bug real. Mantener el comentario con justificación textual; no eliminar sin evaluar el impacto.

  **Recomendación:** Cambiar el comentario de una línea a:
  ```tsx
  // eslint-disable-next-line react-hooks/exhaustive-deps
  // setValue es estable; availableModels solo cambia con llmProvider;
  // watch('llmModel') en estado estable no necesita re-evaluar este efecto.
  ```

#### D8 — `useEffect` en CrewCanvas con comentario eslint justificado
- **Ubicación:** `CrewCanvas.tsx:113`
- **Descripción:** El efecto de restauración de snapshot on-mount usa `eslint-disable-next-line react-hooks/exhaustive-deps` sin lista de dependencias `[]`. El patrón es correcto: el snapshot debe restaurarse solo la primera vez (useRef `snapshotRestored` lo garantiza). Sin embargo, el `eslint-disable` actual no documenta por qué es seguro.
- **Resolución:** Agregar explicación en el comentario:
  ```tsx
  // eslint-disable-next-line react-hooks/exhaustive-deps
  // snapshot restore: una sola vez al montar, snapshotRestored.current = true lo garantiza
  ```

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**No aplica** — El Paso 14 no modifica el schema de base de datos, no crea tablas ni migraciones, ni altera tipos, RLS policies o constraints. Es una etapa pura de optimización frontend.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes afectados por el paso

| Componente / Archivo | Cambios | Tipo |
|---|---|---|
| `hooks/useClickOutside.ts` | Crear | Nuevo hook |
| `hooks/useDebounce.ts` | Crear | Nuevo hook |
| `lib/template-mapper.ts` | Extraer función + mover tipos | Refactor |
| `lib/constants.ts` | Agregar `HTTP_METHODS` | Incremental |
| `components/builder/BuilderTabContext.tsx` | Integrar `useSearchParams` + `useRouter` | Modificar |
| `components/builder/AgentForm.tsx` | Mejorar comentario eslint; sin cambios de lógica | Modificar |
| `components/builder/CrewCanvas.tsx` | Mover import CSS de ReactFlow a dynamic import | Modificar |
| `components/builder/TemplatePicker.tsx` | Aplicar `useDebounce` a búsqueda | Modificar |
| `components/builder/ToolMultiSelect.tsx` | Aplicar `useDebounce` + `useClickOutside` extraído | Modificar |
| `dashboard/app/(app)/builder/page.tsx` | Sin cambios (BuilderCanvas ya usa dynamic import) | Sin cambios |

### Nuevas firmas de API (interfaces públicas nuevas)

```typescript
// hooks/useClickOutside.ts
export function useClickOutside(
  ref: React.RefObject<HTMLElement | null>,
  handler: (event: MouseEvent | TouchEvent) => void,
): void
// Limpia el event listener automáticamente al desmontar.

// hooks/useDebounce.ts
export function useDebounce<T>(value: T, delay: number): T
// Retorna una versión del valor que solo se actualiza después de `delay` ms de inactividad.
// El valor original sigue actualizándose en cada render; `debouncedValue` se actualiza con setTimeout.

// lib/template-mapper.ts
export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData
// Mapea: TemplateDetail (API) → AgentFormData (formulario del builder)
// Maneja fallos de tipos con casts explícitos y defaults seguros.

export interface TemplateDetail {
  id: string
  name: string
  description: string | null
  category: string
  soul_json: Record<string, unknown>
  suggested_tools: string[]
  max_iter: number
  is_system: boolean
  created_at?: string
  updated_at?: string
}

// lib/constants.ts
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  PATCH: 'PATCH',
  DELETE: 'DELETE',
} as const
```

### Patrones existentes a copiar

| Artefacto | Patrón de referencia |
|---|---|
| Hook `useCurrentOrg` → estructura | `hooks/useCurrentOrg.ts:7-17` — función exported, sin props, retorna valor del contexto |
| Dynamic import con loading | `BuilderCanvas.tsx:6-8` — `next/dynamic()` con `ssr: false` y `loading: () => <Skeleton />` |
| Dynamic import ya existente | `BuilderCanvas.tsx:3` — `import dynamic from 'next/dynamic'` |
| `useMemo` para derivados costosos | `CrewCanvas.tsx:207` — `exportPayload = useMemo(() => ..., [nodes])` |
| `useRef` para flag one-shot | `CrewCanvas.tsx:84-85` — `saveRef`, `snapshotRestored` marcados como `true` en uso |

### Imports que se añadirán al importar las herramientas

```typescript
// En ToolMultiSelect.tsx (después de extraer el hook)
import { useClickOutside } from '@/hooks/useClickOutside'
// Reemplaza el useEffect inline actual (líneas 32-40)

import { useDebounce } from '@/hooks/useDebounce'
// Para filtrar búsqueda con delay en TemplatePicker.tsx y ToolMultiSelect.tsx
```

### Calidad de código actual

- ✅ No hay funciones duplicadas (toda la lógica de mapeo está sola en `BuilderLayout.tsx:28-50`)
- ✅ Cohesión alta: cada archivo tiene una sola responsabilidad
- ✅ Acoplamiento bajo: `lib/template-mapper.ts` no tendrá dependencias de componentes React
- ⚠️ 1 `eslint-disable` sin justificación expandida: `AgentForm.tsx:228` — ver D7 en §0
- ⚠️ 1 `eslint-disable` sin justificación expandida: `CrewCanvas.tsx:113` — ver D8 en §0

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**No aplica** — El Paso 14 es 100% frontend. No se crean endpoints, no se modifica middleware, ni se alteran contratos del backend.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo del Builder (sin cambios arquitectónicos)

```
/dashboard/app/(app)/builder/page.tsx
  └── BuilderTabProvider [Context: useState, SIN useSearchParams]
        └── BuilderLayout
              ├── [Tab: Agent Form]
              │     ├── BuilderCanvas (dynamic import, ssr: false)
              │     │     └── CrewCanvas (ReactFlow)
              │     └── AgentForm
              │           ├── ToolMultiSelect [useClickOutside inline, SIN debounce]
              │           └── ExportDialog [fallback clipboard OK]
              └── [Tab: Crew Canvas]
                    └── BuilderCanvas
                          └── CrewCanvas (ReactFlow nodes/edges)
```

### Inconsistencias y Gaps

| # | Gap | Criticidad | Descripción |
|---|---|---|---|
| G1 | Deep linking roto | Media | URL no refleja la pestaña activa. No se puede compartir un enlace a `?tab=crew-canvas`. Cada recarga pierde el estado de navegación. |
| G2 | Búsqueda sin debounce | Baja | Keystroke → recalculo inmediato de agrupación de herramientas. No hay jank visible con ~60 herramientas, pero escala mal a 200+. |
| G3 | CSS ReactFlow en bundle inicial | Baja | `reactflow/dist/style.css` (≈8KB) se entrega en el primer chunk aunque el usuario nunca entre al builder. Desperdicio de bytes. |
| G4 | Hooks no reutilizables | Media | `useClickOutside` inline en ToolMultiSelect, `mapTemplateToFormValues` inline en BuilderLayout. Duplicación futura si otro componente necesita el mismo comportamiento. |
| G5 | Sin constantes HTTP | Baja | Strings `'GET'`/`'POST'` hardcodeados en `api.ts:98-118`. Cambiar un método requiere tocar código; con constantes el IDE ayuda con autocompletado. No es un bug, es DX pobre. |

### Criterios de alineación plan ↔ arquitectura

| Criterio del plan | Estado actual |
|---|---|
| ID-017 `useClickOutside` | ⚠️ Existe inline en `ToolMultiSelect`, NO en hook compartido |
| ID-018 dependencias de `useEffect` | ⚠️ 1 of 2 necesita mejora (ver D7, D8) |
| ID-019 dynamic CSS ReactFlow | ⚠️ CSS importado estáticamente en `CrewCanvas.tsx:48` |
| ID-046 `useMemo` en payload | ✅ Ya implementado en `CrewCanvas.tsx:207-218` |
| ID-048 `useMemo` en cálculos | ✅ Ya implementado (exportPayload, fullGraphJson, exportAgents) |
| ID-021 `cmdk` para herramientas | ❌ No instalado; sin evaluar implementación |
| ID-034 debounce en búsqueda | ❌ No implementado |
| ID-026 `lib/template-mapper.ts` | ❌ Función inline en `BuilderLayout.tsx:28-50` |
| ID-035 refs de scroll | ✅ `scrollRef` correctamente adjuntado en `AgentPlayground.tsx:56,182` |
| ID-038 warnings persistentes | ⚠️ 2× `eslint-disable` sin justificación expandida |
| ID-045 fallback portapapeles | ✅ Implementado en `ExportDialog.tsx:92-98` |
| ID-050 query params tabs | ❌ `BuilderTabContext` usa `useState` sin sincronización URL |
| ID-042 métodos HTTP helper | ✅ `api.ts` tiene get/post/put/patch/delete; pero sin constantes compartidas |
| ID-043 constantes centralizadas descargas | ❌ `fapDownload` en `api.ts:54-94` sin constantes exportadas |

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta 0 (Tarea 0 — PRIMERA): Hooks `useDebounce` + `useClickOutside`

```typescript
// hooks/useClickOutside.ts
import { useEffect } from 'react'

export function useClickOutside(
  ref: React.RefObject<HTMLElement | null>,
  handler: (event: MouseEvent | TouchEvent) => void,
): void

// hooks/useDebounce.ts
import { useEffect, useState } from 'react'

export function useDebounce<T>(value: T, delay: number): T
```

- **Qué automatiza:** Elimina el código repetido de detección de click-fuera y la lógica de retardo de búsqueda inline. Cualquier componente nuevo del builder puede importarlas sin reescribir la lógica.
- **Tipo:** hooks reutilizables del dashboard
- **Cómo se usa:**
  ```tsx
  // useClickOutside — ya inline en ToolMultiSelect
  useClickOutside(containerRef, () => setOpen(false))

  // useDebounce — nuevo en TemplatePicker y ToolMultiSelect
  const debouncedSearch = useDebounce(search, 300)
  ```
- **Impacto para el usuario final:** Reducción de re-renders innecesarios en búsquedas. Menos código inline = menor probabilidad de errores en componentes nuevos. Uso de `useClickOutside` en ToolMultiSelect reduce 10 líneas de useEffect inline por componente.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso

#### Herramienta Propuesta 1: `HTTP_METHODS` en `constants.ts`

```typescript
// lib/constants.ts
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  PATCH: 'PATCH',
  DELETE: 'DELETE',
} as const
```

- **Qué automatiza:** Centraliza literales de métodos HTTP para eliminar cadenas mágicas en `api.ts`. El IDE autocompleta, el linter detecta typos, y cambiar un método requiere una sola edición.
- **Tipo:** constante compartida
- **Cómo se usa:**
  ```typescript
  // api.ts
  const { data, error } = await supabase
    .from('table')
    .select('*')
    .eq('id', id) as const  // ← ya centralizado por Supabase client

  // En fetch manual:
  fetch(url, { method: HTTP_METHODS.GET, ... })
  ```
- **Prioridad:** Baja — no es un riesgo técnico, solo mejora DX

#### Herramienta Propuesta 2 (evaluación): `cmdk` para navegación de herramientas

```typescript
// Si se decide migrar:
import { Command, CommandInput, CommandList, CommandGroup, CommandItem } from 'cmdk'
```

- **Qué automatiza:** Reemplaza el dropdown manual de `ToolMultiSelect` por un buscador con navegación por teclado (↑↓ Enter). El usuario puede buscar y seleccionar herramientas sin tocar el ratón. Ventaja sobre custom select: accesibilidad nativa (WAI-ARIA),API de filtrado, comportamiento de portapapeles.
- **Tipo:** biblioteca de componente (evaluación)
- **Cómo se usa:** Reemplazar el panel desplegable de `ToolMultiSelect` por un `<Command>` que reciba el mismo `options` y `onChange`. El comando se cierra solo al seleccionar (escape handling nativo).
- **Prioridad:** Opcional — requiere decisión de implementación; no bloquear el paso

---

## 5️⃣ Criterios de Aceptación

```
✅ [AX] Hook useClickOutside exportado desde hooks/useClickOutside.ts
✅ [AX] Hook useDebounce exportado desde hooks/useDebounce.ts
✅ [CODE] useEffect en AgentForm tiene dependencias correctas (sin warnings de eslint sin justificar)
✅ [CODE] useEffect en CrewCanvas tiene comentario eslint justificado
✅ [CODE] CSS ReactFlow no bloquea el render inicial (no warning SSR)
✅ [CODE] useMemo en TemplatePicker consulta valor debounced, no raw search
✅ [FULLSTACK] ?tab=crew-canvas carga BuilderLayout en pestaña Crew Canvas
✅ [FULLSTACK] Cambiar pestaña actualiza la URL (sin recarga de página completa)
✅ [FULLSTACK] Refrescar página preserva la pestaña activa desde URL
✅ [CODE] mapTemplateToFormValues exportada desde lib/template-mapper.ts
✅ [CODE] HTTP_METHODS agregado a lib/constants.ts y usado en api.ts
✅ [STRUCTURE] ToolMultiSelect usa useClickOutside desde hook (no inline)
✅ [INTERFACE] ExportDialog.handleCopyJSON() no crashea en navegadores sin clipboard API
```

---

## 6️⃣ Riesgos

| # | Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|---|
| R1 | Romper sincronización URL/tab durante navegación | **Alta** | Introducir `useSearchParams` sin sincronizar el flujo URL→React puede dejar el estado desfasado | Primero implementar lectura de URL → estado, luego escritura del estado → URL. Verificar en dev con cambios manuales de URL |
| R2 | Dynamic import CSS ReactFlow rompe hidratación o estilos FOUC | **Media** | `ssr: false` en `BuilderCanvas.tsx:8` ya previene el crash de SSR; pero mover el CSS import al dynamic podría dejar un blink sin estilos durante la carga | Probar en dev + prod build. Mantener skeleton de loading mientras el CSS carga |
| R3 | `useDebounce` causa desincronización entre input y valor filtrado | **Baja** | El 300ms de delay puede sentirse lento en catálogos con búsqueda instantánea | Utilizar `debouncedValue` solo para el cálculo pesado de `filtered`, mantener `search` para el valor del input |
| R4 | Extraer `mapTemplateToFormValues` rompe imports existentes | **Baja** | `BuilderLayout.tsx` importa `TemplateDetail` desde `TemplatePicker`; el tipo `TemplateDetail` no está exportado desde `TemplatePicker` | Exportar `TemplateDetail` de `TemplatePicker.tsx` o moverla a `lib/template-mapper.ts` junto al mapper |
| R5 | `eslint-disable` sin justificación documentada se convierte en deuda técnica | Media | El `eslint-disable` de `AgentForm.tsx:228` oculta una justificación que solo está en la cabeza del autor | Ampliar el comentario con la justificación en D7 del §0 |

---

## 7️⃣ Plan de Implementación

> [!CRITICAL]
> **Reglas de segmentación atómica:**
> 1. Una tarea = un artefacto. Si toca dos artefactos → dividir.
> 2. Cada tarea incluye la firma exacta del artefacto a crear/modificar.
> 3. Patrón de referencia explícito por tarea.
> 4. Verificación inline con comando o check concreto.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear hooks `useClickOutside` y `useDebounce` | `dashboard/hooks/useClickOutside.ts`, `dashboard/hooks/useDebounce.ts` | `useClickOutside(ref: RefObject<HTMLElement\|null>, handler: (e) => void): void` / `useDebounce<T>(value: T, delay: number): T` | `hooks/useCurrentOrg.ts` (estructura hook estándar) | DX | Baja | 0.5h | Ninguna | → verificar: `tsc --noEmit` sin errores; `grep -n "export function useClickOutside" hooks/useClickOutside.ts` devuelve 1 match |
| 1 | Extraer `mapTemplateToFormValues` a `lib/template-mapper.ts` | `dashboard/lib/template-mapper.ts` | `export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData` | `BuilderLayout.tsx:28-50` (lógica actual a extraer) | CODE | Baja | 0.5h | Tarea 0 | → verificar: import de `BuilderLayout.tsx` desde `lib/template-mapper.ts` resuelve sin error |
| 2 | Agregar `HTTP_METHODS` a `lib/constants.ts` | `dashboard/lib/constants.ts` (línea 36-42) | `HTTP_METHODS = { GET: 'GET', POST: 'POST', PUT: 'PUT', PATCH: 'PATCH', DELETE: 'DELETE' } as const` | `PROVIDER_MODELS` en `constants.ts:20-25` (mismo patrón de objeto as const) | CODE | Baja | 0.25h | Ninguna | → verificar: `grep -n "HTTP_METHODS" dashboard/lib/constants.ts` devuelve la constante |
| 3 | Sincronizar BuilderTabContext con URL (query params) | `dashboard/components/builder/BuilderTabContext.tsx` | `useSearchParams` de `next/navigation` + `useRouter().push()`; `BuilderTabProvider` recibe y expone `activeTab | setActiveTab` sincronizados con `?tab=` | Patrón de navegación de Next.js App Router | FULLSTACK | Media | 1h | Ninguna | → verificar: navegar a `?tab=crew-canvas` cambia pestaña; cambiar pestaña actualiza URL; recargar preserva pestaña |
| 4 | Aplicar `useDebounce` en TemplatePicker y ToolMultiSelect | `TemplatePicker.tsx`, `ToolMultiSelect.tsx` | `const debouncedSearch = useDebounce(search, 300)` alimentando `useMemo` de filtrado | Patrón `useMemo` existente en ambos archivos | CODE | Baja | 0.5h | Tarea 0 | → verificar: `grep -n "useDebounce" TemplatePicker.tsx ToolMultiSelect.tsx`; filtrar por búsqueda tarda 300ms en reflejarse |
| 5 | Extraer `useClickOutside` inline de ToolMultiSelect a hook | `ToolMultiSelect.tsx` | Remover useEffect inline (líneas 32-40); reemplazar por `useClickOutside(containerRef, () => setOpen(false))` | Tarea 0 (nuevo hook `useClickOutside`) | CODE | Baja | 0.25h | Tarea 0 | → verificar: `grep -n "useClickOutside" ToolMultiSelect.tsx` devuelve 1 match y NO hay `useEffect` con `mousedown` en ese archivo |
| 6 | Ampliar justificación del `eslint-disable` en AgentForm | `AgentForm.tsx:228` | Cambiar `// eslint-disable-next-line react-hooks/exhaustive-deps` por comentario multilínea explicando por qué las dependencias adicionales son innecesarias | — | CODE | Baja | 0.1h | Ninguna | → verificar: `grep -A3 "eslint-disable" AgentForm.tsx` muestra la justificación expandida |
| 7 | Ampliar justificación del `eslint-disable` en CrewCanvas | `CrewCanvas.tsx:113` | Cambiar `// eslint-disable-next-line react-hooks/exhaustive-deps -- snapshot restore only on mount` por comentario multilínea | — | CODE | Baja | 0.1h | Ninguna | → verificar: `grep -A2 "eslint-disable" CrewCanvas.tsx` muestra la justificación expandida |
| 8 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 0-7 | → verificar: criterios §5 [FULLSTACK] y [AX] pasan todos; `tsc --noEmit` sin errores |

**Tiempo total estimado:** 3.75h (~4h redondeado)

---

## 🔮 Roadmap (NO implementar ahora)

- [ ] **`cmdk` Command Palette:** Evaluar después de que el Paso 15 cubra tests E2E. Si se migra `ToolMultiSelect` a `cmdk`, se gana navegación por teclado y accesibilidad nativa (WAI-ARIA roles, focus trap, escape handling).
- [ ] **React.memo en AgentNode y TaskNode:** Para canvases con >10 nodos, envueltos en `memo` ya están. Considerar memoizar también props derivadas (ej: `tooltipTools` en `AgentNode` actualmente se re-concatena en cada render).
- [ ] **Zustand / Jotai para estado global del builder:** Si el builder crece más de 3 tabs con estado compartido, Context API genera re-renders innecesarios. Evaluar transición a Zustand.
- [ ] **`fap builder perf` CLI:** Script que detecta componentes sin `React.memo`, `useMemo` faltante en rutas de búsqueda, y `eslint-disable` sin justificar. Idea de herramienta DX para el día a día del equipo.
- [ ] **Lazy-loading de imágenes y assets de ReactFlow:** Si se usan iconos pesados en nodos, cargarlos con `next/image` con `loading="lazy"`.
- [ ] **Pre-fetching de tools API:** Usar `useQuery` con `prefetchQuery` en `AgentForm` cuando el usuario entra al builder para ocultar latencia.

---

## 🚫 Reglas de Oro

- ✅ Análisis basado en código fuente real, no solo en plan.md
- ✅ 13 elementos verificados ≥ 12 (umbral 3-5 archivos afectados)
- ✅ 8 discrepancias documentadas con resolución propuesta
- ✅ Todo verificado contra código existente
- ✅ 1 herramienta DX obligatoria (hooks useDebounce + useClickOutside)
- ✅ Tareas atómicas (1 artefacto por tarea, interfaz completa, patrón explícito)
- ✅ Implementador no debe inferir decisiones de diseño
- ✅ Criterios de aceptación binarios (sí/no)
- ✅ Etapas secuenciales: code → fullstack+DX (data y backend no aplican)

---

*Este análisis fue generado por el agente `step` siguiendo las instrucciones de `DEVS/1_ANALISIS.md` para el `Paso 14` de la fase `guiAgentGenerator`.*
