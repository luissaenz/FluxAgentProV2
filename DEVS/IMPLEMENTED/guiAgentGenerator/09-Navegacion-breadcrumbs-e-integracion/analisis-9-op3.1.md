# Análisis Técnico — Paso 9: Navegación, breadcrumbs e integración

> **Agente:** op3.1  
> **Paso:** 9  
> **Fecha:** 2026-05-15  
> **Fase:** `guiAgentGenerator`

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | Sidebar "Builder" ya existe en `nav-main.tsx` | Entrada `{ title: 'Builder', url: '/builder', icon: Wand2 }` | ✅ | `nav-main.tsx:50` |
| 2 | Sidebar "Builder" **NO existe** en `app-sidebar.tsx` | `app-sidebar.tsx:28-38` define `navMain` local SIN Builder, Tickets ni Wand2 | ❌ | `app-sidebar.tsx:28-38` — lista desincronizada |
| 3 | `app-sidebar.tsx` NO usa `defaultNavItems` de `nav-main.tsx` | Define array local `navMain` diferente al de `nav-main.tsx:43-64` | ❌ | `app-sidebar.tsx:28` vs `nav-main.tsx:43` |
| 4 | `NavMain` se invoca sin props en `app-sidebar.tsx:64` | Usa `defaultNavItems` internamente → SÍ muestra Builder | ✅ | `app-sidebar.tsx:64` — `<NavMain />` sin `items` prop |
| 5 | `app-sidebar.tsx:28-38` array `navMain` está **dead code** | Se declara pero nunca se pasa a `<NavMain />` | ❌ | `app-sidebar.tsx:28-38,64` — variable no usada |
| 6 | `floating-nav.tsx` usa `defaultNavItems` | Importa de `nav-main.tsx` → incluye Builder | ✅ | `floating-nav.tsx:16,62` |
| 7 | `Breadcrumb` componente UI existe | `dashboard/components/ui/breadcrumb.tsx` con 7 exports | ✅ | `breadcrumb.tsx:40` |
| 8 | Breadcrumbs NO se usan en ninguna página actual | `grep -r "breadcrumb" dashboard/app/` → 0 resultados | ✅ | Grep sin resultados |
| 9 | Builder page existe en `/builder` | `dashboard/app/(app)/builder/page.tsx` — 15 líneas | ✅ | `builder/page.tsx:1-15` |
| 10 | Builder page NO tiene breadcrumbs | Solo `<h2>Agent Builder</h2>` + `<BuilderLayout />` | ✅ | `builder/page.tsx:7-12` |
| 11 | `BuilderCanvas.tsx` usa `dynamic import ssr:false` | `dynamic(() => import(...), { ssr: false })` | ✅ | `BuilderCanvas.tsx:6-9` |
| 12 | NO existe `ErrorBoundary` en ningún componente | `grep "ErrorBoundary" dashboard/` → 0 resultados | ❌ | Sin error boundaries en proyecto |
| 13 | `PageHeader` componente compartido existe | `dashboard/components/shared/PageHeader.tsx` — title + description + action | ✅ | `PageHeader.tsx:9-21` |
| 14 | `Skeleton` loading ya usado en `BuilderCanvas` | `Skeleton className="h-64 w-full rounded-lg"` como fallback de dynamic import | ✅ | `BuilderCanvas.tsx:8` |
| 15 | `LoadingSpinner` compartido existe | `dashboard/components/shared/LoadingSpinner.tsx` — sm/md/lg sizes | ✅ | `LoadingSpinner.tsx:12` |
| 16 | Builder NO tiene sub-rutas (solo `page.tsx`) | `ls builder/` → solo `page.tsx`, sin layout.tsx ni carpetas hijas | ✅ | `ls` resultado |
| 17 | `BuilderLayout` tiene tabs "Agent Form" / "Crew Canvas" | `Tabs` con `TabsTrigger` valores `agent-form` y `crew-canvas` | ✅ | `BuilderLayout.tsx:72-83` |
| 18 | Nav sidebar NO tiene sub-items para Builder | Solo `{ title: 'Builder', url: '/builder', icon: Wand2 }` sin `items[]` | ✅ | `nav-main.tsx:50` |
| 19 | `Integraciones` SÍ tiene sub-items en nav | `items: [Catálogo, Bundles (Wizard), Historial Bundles]` | ✅ | `nav-main.tsx:53-62` |
| 20 | `site-header.tsx` NO tiene breadcrumbs | Solo `FloatingNav` + org name + theme toggle | ✅ | `site-header.tsx:7-31` |
| 21 | `react-error-boundary` NO está en `package.json` | No existe como dependencia | ✅ | `package.json:12-48` |
| 22 | Patrón de heading en páginas: `<h2 className="text-2xl font-bold tracking-tight">` | Consistente en `agents/page.tsx:33`, `workflows/page.tsx:41`, `builder/page.tsx:8` | ✅ | Múltiples archivos |

**Discrepancias encontradas:**

1. **D1 — `app-sidebar.tsx` tiene array `navMain` dead code (líneas 28-38):** Se declara un array local con 9 items (sin Builder, sin Tickets) pero NUNCA se usa. `<NavMain />` se invoca sin props en línea 64, así que usa `defaultNavItems` que SÍ incluye Builder. **Resolución:** Eliminar el array dead code e imports no usados de `app-sidebar.tsx`.

2. **D2 — Sin `ErrorBoundary` en todo el proyecto:** El plan requiere "Error boundaries para el canvas (ReactFlow puede fallar en SSR)" pero no existe ningún ErrorBoundary. `react-error-boundary` no está instalado. **Resolución:** Crear `ErrorBoundary` class component nativo de React (sin dep externa), wrapping `BuilderCanvas`.

3. **D3 — Breadcrumbs existen como componente UI pero NO se usan en ninguna página:** El plan pide "Breadcrumbs: Dashboard > Builder > [New Agent | Crew Canvas | Templates]" pero el proyecto actual no tiene breadcrumbs en NINGUNA página. Implementar solo en Builder crearía inconsistencia visual. **Resolución:** Implementar breadcrumbs en Builder page usando componente existente `breadcrumb.tsx`. El breadcrumb será contextual según la tab activa.

4. **D4 — Builder no tiene sub-rutas en la navegación:** El plan dice breadcrumbs con "[New Agent | Crew Canvas | Templates]" sugiriendo sub-páginas, pero Builder usa tabs internas en `BuilderLayout.tsx`, no rutas separadas. **Resolución:** Breadcrumbs reflejarán la tab activa sin crear nuevas rutas. Formato: `Dashboard > Builder > Agent Form` o `Dashboard > Builder > Crew Canvas`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema y tablas

- ✅ **Sin cambios de schema:** Este paso es 100% frontend. No crea ni modifica tablas.
- ✅ **Sin migraciones:** No se necesitan nuevas migraciones SQL.
- ✅ **Sin cambios de RLS:** No se modifican políticas de acceso.

### Impacto en datos

- Sin impacto. El paso modifica solo componentes de navegación y UI del dashboard.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes a crear

#### 2.1 `BuilderBreadcrumb` — Breadcrumb contextual del Builder

- **Archivo:** `dashboard/components/builder/BuilderBreadcrumb.tsx`
- **Firma:** `export function BuilderBreadcrumb({ activeTab }: { activeTab: string }): JSX.Element`
- **Imports:**
  ```typescript
  import Link from 'next/link'
  import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
  ```
- **Lógica:** Mapea `activeTab` (`'agent-form'` | `'crew-canvas'`) a label legible: `{ 'agent-form': 'Agent Form', 'crew-canvas': 'Crew Canvas' }`.
- **Render:** `Dashboard > Builder > {activeTabLabel}`
- **Patrón a seguir:** Componentes `breadcrumb.tsx` existente (primitivas exportadas). Composición igual que ejemplo shadcn/ui.

#### 2.2 `BuilderErrorBoundary` — Error boundary para ReactFlow

- **Archivo:** `dashboard/components/builder/BuilderErrorBoundary.tsx`
- **Firma:**
  ```typescript
  interface Props { children: React.ReactNode; fallback?: React.ReactNode }
  interface State { hasError: boolean; error: Error | null }
  export class BuilderErrorBoundary extends React.Component<Props, State>
  ```
- **Métodos:**
  - `static getDerivedStateFromError(error: Error): State` → `{ hasError: true, error }`
  - `componentDidCatch(error: Error, info: React.ErrorInfo): void` → `console.error('[BuilderErrorBoundary]', error, info)`
  - `handleReset(): void` → `this.setState({ hasError: false, error: null })`
  - `render()` → fallback con mensaje + botón Retry, o `this.props.children`
- **Patrón a seguir:** React class component nativo. Sin dependencias externas. Consistente con `EmptyState.tsx` para el estilo del fallback.

### Componentes a modificar

#### 2.3 `builder/page.tsx` — Añadir breadcrumbs + loading states

- **Archivo:** `dashboard/app/(app)/builder/page.tsx`
- **Cambios:**
  - Importar `BuilderBreadcrumb` y `Suspense` de React
  - Añadir `BuilderBreadcrumb` encima del título
  - Wrappear `BuilderLayout` con `Suspense` + `LoadingSpinner` fallback
  - Pasar `activeTab` de `BuilderLayout` al breadcrumb (elevar estado o usar callback)
- **Patrón a seguir:** `agents/page.tsx` para estructura de página. `BuilderCanvas.tsx` para loading state pattern.

#### 2.4 `BuilderLayout.tsx` — Exponer `activeTab` + integrar error boundary

- **Archivo:** `dashboard/components/builder/BuilderLayout.tsx`
- **Cambios:**
  - Añadir prop `onTabChange?: (tab: string) => void`
  - Llamar `onTabChange?.(activeTab)` en `useEffect` cuando cambie
  - Wrappear `<BuilderCanvas />` con `<BuilderErrorBoundary>`
- **Firma actualizada:** `export function BuilderLayout({ onTabChange }: { onTabChange?: (tab: string) => void })`

#### 2.5 `app-sidebar.tsx` — Limpiar dead code

- **Archivo:** `dashboard/components/app-sidebar.tsx`
- **Cambios:**
  - Eliminar array `navMain` local (líneas 28-38) — dead code
  - Eliminar imports no usados: `LayoutDashboard, Columns3, ShieldCheck, History, Bot, Workflow, Activity, MessageSquare, Puzzle`
  - Eliminar import `usePathname` (no usado tras quitar array)

#### 2.6 `nav-main.tsx` — Añadir sub-items al Builder

- **Archivo:** `dashboard/components/nav-main.tsx`
- **Cambios:**
  - Añadir `items` array al Builder nav item para sub-navegación cuando la sección está activa:
    ```typescript
    {
      title: 'Builder',
      url: '/builder',
      icon: Wand2,
      items: [
        { title: 'Agent Form', url: '/builder?tab=agent-form' },
        { title: 'Crew Canvas', url: '/builder?tab=crew-canvas' },
      ]
    }
    ```
  - **Nota:** Los sub-items usan query params, no rutas separadas, consistente con la implementación por tabs.

### Patrones relevantes verificados

- **Heading pattern:** `<h2 className="text-2xl font-bold tracking-tight">` — usado en todas las páginas. Builder ya lo tiene.
- **Loading pattern:** `LoadingSpinner` + `Skeleton` — ambos disponibles y usados en builder.
- **Sub-items nav pattern:** `Integraciones` en `nav-main.tsx:53-62` — muestra sub-items cuando `isParentActive`.
- **Dynamic import SSR pattern:** `BuilderCanvas.tsx:6-9` — ya implementado correctamente.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints

- ✅ **Sin cambios de backend:** Este paso es 100% frontend (navegación y UI).
- ✅ **Sin nuevos endpoints:** No se crean ni modifican endpoints.
- ✅ **Sin cambios de middleware:** Auth no se modifica.

### Flujo de datos

- El flujo backend→frontend existente no cambia. Los endpoints `GET /api/tools/available`, `GET /api/templates`, `POST /agents`, etc., siguen funcionando igual.
- La navegación por breadcrumbs y sidebar es puramente client-side (Next.js routing + query params).

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
Sidebar → click "Builder" → /builder
   ├── Breadcrumb: Dashboard > Builder > Agent Form (default)
   ├── Tab "Agent Form" → breadcrumb actualiza a "Agent Form"
   ├── Tab "Crew Canvas" → breadcrumb actualiza a "Crew Canvas"
   │    └── ErrorBoundary wraps ReactFlow canvas
   ├── Botón "Templates" → Dialog modal (sin cambio de ruta)
   └── Botón "Playground" → Sheet lateral (sin cambio de ruta)
```

### Coherencia

- ✅ Las tabs internas del Builder son el mecanismo correcto. No tiene sentido crear sub-rutas `/builder/agent-form` y `/builder/crew-canvas` porque la UX es un split panel con switching instantáneo.
- ✅ Los breadcrumbs reflejan la tab activa, dando contexto sin fragmentar la navegación.
- ✅ El sidebar sub-items (como Integraciones) permite acceso directo a tabs específicas via query params.

### Gaps identificados

1. **Sin consistencia global de breadcrumbs:** Solo Builder los tendrá. Otras páginas no los usan. Aceptable para MVP — las demás páginas son flat (sin sub-niveles).
2. **Query param `?tab=` no implementado:** `BuilderLayout` no lee query params. Se necesita sincronización tab↔URL.
3. **Skeleton loading en `BuilderCanvas` es minimal:** Solo `h-64` — insuficiente cuando el canvas ocupa pantalla completa.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: `fap builder check`
- **Qué automatiza:** Verifica que la navegación del Builder está correctamente integrada: sidebar entry existe, breadcrumb component importado, error boundary wrapping canvas, dynamic import con ssr:false, y consistencia entre nav-main.tsx y app-sidebar.tsx.
- **Tipo:** script CLI validador
- **Cómo se usa:** `uv run python scripts/validate_builder_nav.py`
- **Impacto para el usuario final:** Detecta regresiones de navegación (ej: sidebar entry eliminada por merge conflict, error boundary removido) antes de que lleguen a producción.
- **Prioridad:** Tarea 0 — ejecutar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] `app-sidebar.tsx` sin dead code: array `navMain` local eliminado, imports limpiados
✅ [CODE] `BuilderBreadcrumb` componente existe con firma `({ activeTab }: { activeTab: string })`
✅ [CODE] `BuilderErrorBoundary` class component existe con `getDerivedStateFromError` + `handleReset`
✅ [CODE] `BuilderLayout` acepta prop `onTabChange?: (tab: string) => void` y la invoca al cambiar tab
✅ [CODE] `BuilderCanvas` wrapeado en `BuilderErrorBoundary` dentro de `BuilderLayout`
✅ [FULLSTACK] Builder accesible desde sidebar con ícono Wand2 + label "Builder"
✅ [FULLSTACK] Builder accesible desde floating-nav (usa `defaultNavItems`)
✅ [FULLSTACK] Breadcrumb visible: "Dashboard > Builder > Agent Form" en tab agent-form
✅ [FULLSTACK] Breadcrumb visible: "Dashboard > Builder > Crew Canvas" en tab crew-canvas
✅ [FULLSTACK] Breadcrumb "Dashboard" es link clickable a `/`
✅ [FULLSTACK] Breadcrumb "Builder" es link clickable a `/builder`
✅ [FULLSTACK] Sidebar sub-items para Builder muestran "Agent Form" y "Crew Canvas" cuando Builder está activo
✅ [FULLSTACK] Canvas NO rompe en SSR (dynamic import con `ssr: false` preservado)
✅ [FULLSTACK] ErrorBoundary muestra fallback con mensaje + botón "Retry" si ReactFlow crashea
✅ [FULLSTACK] Loading skeleton visible mientras carga el canvas (dynamic import fallback)
✅ [FULLSTACK] Estilo visual consistente con resto del dashboard (mismos colores, tipografía, spacing)
✅ [DX] Script `validate_builder_nav.py` ejecuta sin errores y valida integración de navegación
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| Breadcrumbs solo en Builder crea inconsistencia visual con el resto del dashboard | Media | Ninguna otra página usa breadcrumbs | Aceptar para MVP. Breadcrumbs solo añaden valor cuando hay jerarquía (Builder tiene tabs). Documentar para estandarización futura. |
| `BuilderErrorBoundary` como class component en proyecto funcional | Baja | React no soporta `getDerivedStateFromError` en function components (a fecha de React 18) | Estándar de React. Class component es la única opción para error boundaries. Encapsulado y aislado. |
| Sub-items con query params `?tab=` pueden no sincronizarse con estado interno de `BuilderLayout` | Media | `BuilderLayout` usa `useState` para `activeTab`, no lee de URL | Implementar lectura de `searchParams` en `page.tsx` y pasar como prop `defaultTab` a `BuilderLayout`. |
| Merge conflict en `nav-main.tsx` con pasos futuros (Paso 10 tests) | Baja | Builder entry ya existe, solo se añaden sub-items | Cambio aditivo (agregar `items` array a objeto existente). Bajo riesgo de conflicto. |
| Dead code cleanup en `app-sidebar.tsx` puede romper si otro componente lo importa | Baja | El array `navMain` local no se exporta | Verificar con grep que no hay imports externos antes de eliminar. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|--------------|-------------|
| 0 | **DX & Tooling**: Script validador de navegación Builder | `scripts/validate_builder_nav.py` | `def main() -> None` — verifica: 1) `nav-main.tsx` contiene `Builder` entry, 2) `breadcrumb.tsx` existe, 3) `BuilderErrorBoundary.tsx` existe, 4) `BuilderCanvas.tsx` tiene `ssr: false`, 5) `app-sidebar.tsx` no tiene array `navMain` local | `scripts/validate_cli_structure.py` — script de validación existente | DX | Baja | 0.5h | Ninguna | → verificar: `uv run python scripts/validate_builder_nav.py` ejecuta sin errores |
| 1 | Limpiar dead code en `app-sidebar.tsx` | `dashboard/components/app-sidebar.tsx` | Eliminar líneas 4 (`usePathname`), 6-15 (icon imports no usados), 28-38 (array `navMain` local). Preservar líneas 3, 16-27, 40-73. Eliminar `const pathname = usePathname()` línea 41. | Archivo actual tras limpieza | CODE | Baja | 0.25h | Ninguna | → verificar: `grep "const navMain" dashboard/components/app-sidebar.tsx` retorna vacío + `npm run build` sin errores |
| 2 | Crear `BuilderErrorBoundary` | `dashboard/components/builder/BuilderErrorBoundary.tsx` | `class BuilderErrorBoundary extends React.Component<{children: React.ReactNode, fallback?: React.ReactNode}, {hasError: boolean, error: Error \| null}>` con `getDerivedStateFromError`, `componentDidCatch`, `handleReset()`, `render()`. Fallback: Card con AlertTriangle icon + mensaje + botón "Retry". | `dashboard/components/shared/EmptyState.tsx` para estilo de fallback | CODE | Baja | 0.5h | Ninguna | → verificar: `grep "BuilderErrorBoundary" dashboard/components/builder/BuilderErrorBoundary.tsx` retorna class |
| 3 | Crear `BuilderBreadcrumb` | `dashboard/components/builder/BuilderBreadcrumb.tsx` | `export function BuilderBreadcrumb({ activeTab }: { activeTab: string }): JSX.Element`. Usa `Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator` de `@/components/ui/breadcrumb`. Tab label map: `{'agent-form': 'Agent Form', 'crew-canvas': 'Crew Canvas'}`. Links: Dashboard→`/`, Builder→`/builder`, tab actual como `BreadcrumbPage`. | `dashboard/components/ui/breadcrumb.tsx` — primitivas existentes | CODE | Baja | 0.5h | Ninguna | → verificar: `grep "BreadcrumbPage" dashboard/components/builder/BuilderBreadcrumb.tsx` retorna uso |
| 4 | Modificar `BuilderLayout` — exponer `activeTab` + error boundary | `dashboard/components/builder/BuilderLayout.tsx` | Añadir prop `onTabChange?: (tab: string) => void` al interface. Añadir `useEffect` que llame `onTabChange?.(activeTab)` cuando cambie. Wrappear ambas instancias de `<BuilderCanvas />` (líneas 108 y 126) con `<BuilderErrorBoundary>`. Import: `BuilderErrorBoundary` de `./BuilderErrorBoundary`. | `BuilderLayout.tsx` actual — mismo estilo, añadir prop + useEffect + wrapper | CODE | Baja | 0.5h | Tareas 2 | → verificar: `grep "onTabChange" dashboard/components/builder/BuilderLayout.tsx` retorna prop + useEffect |
| 5 | Modificar `builder/page.tsx` — integrar breadcrumbs + loading | `dashboard/app/(app)/builder/page.tsx` | Añadir `useState<string>('agent-form')` para `activeTab`. Importar y renderizar `<BuilderBreadcrumb activeTab={activeTab} />` antes del `<h2>`. Pasar `onTabChange={setActiveTab}` a `<BuilderLayout>`. Añadir `Suspense` wrapper con `<LoadingSpinner label="Loading builder..." />` como fallback. | `dashboard/app/(app)/agents/page.tsx` para estructura de página + `builder/page.tsx` actual | FULLSTACK | Baja | 0.5h | Tareas 3, 4 | → verificar: `grep "BuilderBreadcrumb" dashboard/app/(app)/builder/page.tsx` retorna import + uso |
| 6 | Añadir sub-items al Builder en `nav-main.tsx` | `dashboard/components/nav-main.tsx` | Modificar línea 50: añadir `items: [{ title: 'Agent Form', url: '/builder?tab=agent-form' }, { title: 'Crew Canvas', url: '/builder?tab=crew-canvas' }]` al objeto Builder. | `nav-main.tsx:53-62` — patrón de Integraciones con sub-items | FULLSTACK | Baja | 0.25h | Ninguna | → verificar: `grep "Agent Form" dashboard/components/nav-main.tsx` retorna sub-item |
| 7 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-6 | → verificar: criterios §5 [FULLSTACK] y [DX] pasan todos + `npm run build` sin errores |

**Tiempo total estimado:** 3.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Breadcrumbs globales:** Estandarizar breadcrumbs en todas las páginas del dashboard (agents, workflows, integrations, etc.) usando un hook `useBreadcrumbs()` basado en `usePathname()`.
- **URL sync para tabs:** Sincronizar tab activa con `searchParams` (`?tab=crew-canvas`) para deep-linking y navegación por URL directa. Requiere `useSearchParams()` en `page.tsx`.
- **Skeleton mejorado para canvas:** Reemplazar `Skeleton h-64` por un skeleton que simule la estructura del canvas (sidebar + grid + toolbar).
- **`react-error-boundary` package:** Post-MVP, migrar `BuilderErrorBoundary` a usar `react-error-boundary` (library estándar) para obtener `useErrorBoundary()` hook y reset automático.
- **Nav items dinámicos:** Extraer `defaultNavItems` a un archivo de configuración separado para facilitar feature flags y control de visibilidad por rol/permisos.
