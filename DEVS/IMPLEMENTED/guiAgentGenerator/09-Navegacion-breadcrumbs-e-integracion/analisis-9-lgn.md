# Análisis Técnico - Paso 9: Navegación, breadcrumbs e integración

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Link "Builder" en sidebar (nav-main.tsx) | `grep` en `nav-main.tsx` | ✅ | `dashboard/components/nav-main.tsx:50` — `{ title: 'Builder', url: '/builder', icon: Wand2 }` |
| 2 | app-sidebar.tsx usa navMain interno sin Builder | `view_file` líneas 28-38 | ❌ | `dashboard/components/app-sidebar.tsx:28-38` — array `navMain` duplicado SIN "Builder" |
| 3 | NavMain renderizado sin prop items | `view_file` línea 64 | ⚠️ | `dashboard/components/app-sidebar.tsx:64` — `<NavMain />` sin `items={defaultNavItems}` |
| 4 | Componente Breadcrumb shadcn/ui | `view_file` | ✅ | `dashboard/components/ui/breadcrumb.tsx` — exporta `Breadcrumb`, `BreadcrumbList`, `BreadcrumbItem`, `BreadcrumbLink`, `BreadcrumbPage`, `BreadcrumbSeparator` |
| 5 | Builder page existe | `glob` | ✅ | `dashboard/app/(app)/builder/page.tsx` |
| 6 | loading.tsx para builder | `glob` | ❌ | No existe `dashboard/app/(app)/builder/loading.tsx` |
| 7 | error.tsx para builder | `glob` | ❌ | No existe `dashboard/app/(app)/builder/error.tsx` |
| 8 | BuilderCanvas usa dynamic ssr:false | `view_file` | ✅ | `dashboard/components/builder/BuilderCanvas.tsx:6-9` — `dynamic(() => import(...), { ssr: false })` |
| 9 | BuilderLayout renderizado en page | `view_file` | ✅ | `dashboard/app/(app)/builder/page.tsx:10` — `<BuilderLayout />` |

**Discrepancias encontradas:**
1. **Duplicación de menú de navegación:** `app-sidebar.tsx` tiene un array `navMain` interno (líneas 28-38) que NO incluye "Builder", pero `NavMain` es llamado sin pasar `items` prop, por lo que usa `defaultNavItems` de `nav-main.tsx` que SÍ incluye Builder. Resolución: Eliminar el array `navMain` de `app-sidebar.tsx` y pasar explícitamente `items={defaultNavItems}`.
2. **Falta de Error Boundaries y Loading States:** No existen `loading.tsx` ni `error.tsx` en `dashboard/app/(app)/builder/`. Resolución: Crear ambos archivos usando patrones estándar de Next.js App Router.
3. **Breadcrumbs no implementados:** El plan requiere "Dashboard > Builder > [New Agent | Crew Canvas | Templates]", pero no hay breadcrumbs en la page. Resolución: Agregar componente Breadcrumb usando shadcn/ui.

---

### 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema:** Sin cambios. Este paso es puramente frontend.
- ✅ **Integridad referencial:** N/A.
- ✅ **RLS policies:** N/A.
- ✅ **Índices necesarios:** N/A.
- ✅ **Tipos de datos:** N/A.

---

### 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Funciones/clases nuevas:**
  - `loading.tsx` — Componente de loading para ruta builder
  - `error.tsx` — Error boundary para ruta builder
  - Breadcrumb component integration

- ✅ **Patrones:**
  - Uso de `next/dynamic` con `ssr: false` para evitar hidratación fallida en ReactFlow (ya implementado en `BuilderCanvas.tsx`)
  - Uso de componentes `Breadcrumb*` de shadcn/ui para naveción espacial

- ✅ **Modularidad:** Separación de estados de carga/error a nivel de ruta Next.js

- ✅ **Calidad:** Eliminación de código duplicado (navMain en app-sidebar.tsx debe eliminarse)

- ✅ **Imports exactos:** 
  - `import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'`
  - `import { dynamic } from 'next/dynamic'`

**Firmas de componentes nuevos:**
```tsx
// dashboard/app/(app)/builder/loading.tsx
export default function BuilderLoading() {
  return (
    <div className="flex h-full flex-col space-y-4">
      <Skeleton className="h-8 w-48" />
      <div className="grid h-full gap-4 lg:grid-cols-[60%_40%]">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  )
}

// dashboard/app/(app)/builder/error.tsx
export default function BuilderError({ error, reset }: { error: Error & { digest?: string }, reset: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center space-y-4">
      <h2 className="text-lg font-semibold">Error loading Builder</h2>
      <p className="text-sm text-muted-foreground">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  )
}
```

---

### 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **APIs/endpoints:** Ninguno en este paso.
- ✅ **Middleware:** Ninguno en este paso.
- ✅ **Flujos:** N/A.
- ✅ **Contratos:** N/A.
- ✅ **Error handling:** N/A.

No aplica para este paso. Todo ocurre en el frontend.

---

### 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo:** Usuario navega a `/builder` desde el sidebar, ve breadcrumbs (Dashboard > Builder), percibe loading state, y cualquier fallo queda contenido en error boundary sin romper la SPA.
- ✅ **Coherencia:** Uso de `shadcn/ui` (Breadcrumb, Skeleton, Button) garantiza look & feel idéntico.
- ✅ **Alineación:** Factible con Next.js App Router.
- ✅ **Gaps:** El framework de Next.js renderiza loading/error automáticamente.

### Herramienta Propuesta: Next.js Boundary Validator
- **Qué automatiza:** Revisa todas las rutas en `dashboard/app/` y verifica si tienen `loading.tsx` y `error.tsx` para evitar fallbacks genéricos.
- **Tipo:** script CLI de validación Python
- **Cómo se usa:** `python scripts/check_nextjs_boundaries.py --dir dashboard/app`
- **Impacto para el usuario final:** Garantiza que fallos o latencias muestren UI controlada en vez de página en blanco.
- **Prioridad:** Tarea 0 — implementar primero.

---

### 5️⃣ Criterios de Aceptación

✅ [FULLSTACK] Sidebar muestra "Builder" usando `defaultNavItems` de `nav-main.tsx`
✅ [FULLSTACK] Breadcrumbs visibles: `Dashboard > Builder`
✅ [FULLSTACK] `loading.tsx` muestra skeleton mientras carga
✅ [FULLSTACK] `error.tsx` muestra error bound sin crash
✅ [FULLSTACK] Canvas usa `next/dynamic` con `ssr: false` (ya implementado)
✅ [CODE] `app-sidebar.tsx` usa `items={defaultNavItems}` sin array interno duplicado
✅ [DX] `check_nextjs_boundaries.py` ejecuta sin errores

---

### 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Fallo en la hidratación de ReactFlow | Alta | Renderizar el Canvas en el lado del servidor | Ya resuelto: `BuilderCanvas` usa `dynamic(ssr:false)` |
| Inconsistencia de menú | Media | Múltiples fuentes de verdad para `navMain` | Usar `items={defaultNavItems}` en `NavMain` |
| Bloqueo total de la UI por fallo no capturado | Alta | Excepciones no controladas en el builder | `error.tsx` envuelve la ruta completa |

---

### 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Next.js Boundary Validator | `scripts/check_nextjs_boundaries.py` | `def main(): cli.run()` | Similar a `scripts/bundle_validator.py` | DX | Baja | 0.5h | Ninguna | → verificar: `python scripts/check_nextjs_boundaries.py --help` |
| 1 | Refactorizar app-sidebar.tsx | `dashboard/components/app-sidebar.tsx` | Eliminar array `navMain`, importar `defaultNavItems`, pasar a `<NavMain items={defaultNavItems} />` | Ver línea 64 actual | CODE | Baja | 0.25h | Tarea 0 | → verificar: Sidebar sigue funcionando y "Builder" aparece |
| 2 | Implementar Loading State | `dashboard/app/(app)/builder/loading.tsx` | `export default function BuilderLoading()` | `dashboard/components/shared/LoadingSpinner.tsx` | CODE | Baja | 0.25h | Ninguna | → verificar: Navegar a `/builder` muestra skeleton brevemente |
| 3 | Implementar Error Boundary | `dashboard/app/(app)/builder/error.tsx` | `export default function BuilderError({ error, reset }: ... )` | Patrón Next.js App Router estándar | CODE | Baja | 0.25h | Ninguna | → verificar: Forzar error muestra componente error |
| 4 | Integrar Breadcrumbs | `dashboard/app/(app)/builder/page.tsx` | Agregar `<Breadcrumb>` con items Dashboard > Builder | `dashboard/components/ui/breadcrumb.tsx` | FULLSTACK | Baja | 0.25h | Tareas 2-3 | → verificar: Breadcrumbs visibles en página |

**Tiempo total estimado:** 1.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Breadcrumbs dinámicos: `Dashboard > Builder > [Agent Form | Crew Canvas]` basado en tab activo
- Persistencia de última pestaña activa en localStorage

---

## 🚫 Reglas de Oro

- ✅ Análisis accionable y específico, no genérico
- ✅ TODO verificado contra código, no supuestos
- ✅ Si algo no está definido → señalar como ambigüedad + resolución concreta
- ✅ Si el plan contradice el código → el código gana + documentar discrepancia
- ✅ Nivel CTO exigente en rigor y profundidad
- ✅ Coherente con phase-state.md
- ✅ TODO el paso, incluyendo sub-pasos
- ✅ Etapas secuenciales — data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta
- ✅ Tareas atómicas: una tarea = un artefacto
- ✅ El implementador no decide nada