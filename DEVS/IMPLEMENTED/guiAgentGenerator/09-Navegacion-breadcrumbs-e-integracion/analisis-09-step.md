# 🧠 Análisis Técnico — Paso 09: Navegación, breadcrumbs e integración (AGENTE: step)

## 📌 Contexto

**Proyecto:** FluxAgentPro-v2  
**Paso:** 09 — Navegación, breadcrumbs e integración  
**Agente:** step  
**Objetivo del paso:** Integrar el builder en la navegación del dashboard existente, con breadcrumbs, acceso desde el sidebar, y coherencia visual con el resto de páginas.  
**Fuente de verdad:** `proyecto-config.json` + código fuente real (`src/`, `dashboard/`)  
**Phase-state:** Fase `guiAgentGenerator` — 8/8 pasos completados ✅, Paso 09 pendiente ⬜

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

**Alcance del paso:** 3-5 archivos afectados → Mínimo verificado: ≥ 12 elementos

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | "Builder" en `defaultNavItems` de `nav-main.tsx` | `grep` en `nav-main.tsx:50` | ✅ | `{ title: 'Builder', url: '/builder', icon: Wand2 }` |
| 2 | `<NavMain />` renderizado por `app-sidebar.tsx` | Lectura `app-sidebar.tsx:64` | ✅ | `<NavMain />` sin prop items → usa `defaultNavItems` |
| 3 | `navMain` array local en `app-sidebar.tsx` (dead code) | Lectura `app-sidebar.tsx:28-38` | ❌ | Array local SIN "Builder". Nunca se usa: `<NavMain />` sin `items=`. Evita que el builder aparezca si NavMain cambiara su fallback |
| 4 | `<NavMain>` llamado SIN `items` prop | Lectura `app-sidebar.tsx:64` | ⚠️ | `<NavMain />` versus `NavMain({items: defaultNavItems})`. Si `NavMain` eliminara su fallback `items ?? defaultNavItems`, Builder desaparecería sin error visible |
| 5 | `Breadcrumb`, `BreadcrumbList`, `BreadcrumbLink`, etc. | Lectura `dashboard/components/ui/breadcrumb.tsx` | ✅ | Existe y exporta: `Breadcrumb`, `BreadcrumbList`, `BreadcrumbItem`, `BreadcrumbLink`, `BreadcrumbPage`, `BreadcrumbSeparator`, `BreadcrumbEllipsis` |
| 6 | `Breadcrumb` importado en algún archivo del proyecto | `grep` por `from '@/components/ui/breadcrumb'` | ❌ | **Ningún archivo en el dashboard importa breadcrumb.** Componente existe definido pero sin uso. Requiere implementación |
| 7 | `SiteHeader` usado en `AppLayout` | Lectura `dashboard/app/(app)/layout.tsx:19` | ✅ | `<SiteHeader />` en el layout de la app |
| 8 | `FloatingNav` en `SiteHeader` | Lectura `dashboard/components/site-header.tsx:12` | ✅ | Presente; es el patrón de navegación espacial actual |
| 9 | Builder Page existe | Lectura `dashboard/app/(app)/builder/page.tsx` | ✅ | 14 líneas; renderiza `<BuilderLayout />` |
| 10 | `loading.tsx` para la ruta `/builder` | `find` en `dashboard/app/(app)/builder/` | ❌ | No existe ningún `loading.tsx` en el proyecto entero |
| 11 | `error.tsx` para la ruta `/builder` | `find` en `dashboard/app/(app)/builder/` | ❌ | No existe ningún `error.tsx` en el proyecto entero |
| 12 | `BuilderCanvas` usa `next/dynamic` con `ssr: false` | Lectura `BuilderCanvas.tsx:6-9` | ✅ | `dynamic(() => import(...), { ssr: false, loading: () => <Skeleton.../> })` |
| 13 | `Skeleton` componente en página | Lectura `components/ui/skeleton.tsx` | ✅ | Exportado desde `@/components/ui/skeleton` |
| 14 | `PageHeader` componente importado por alguna página | `grep` por `PageHeader` | ✅ | Usado por `tickets/page.tsx:6,175` |
| 15 | `BackButton` componente importado por páginas de detalle | `grep` por `BackButton` | ✅ | Usado por `tickets/[id]/`, `tasks/[id]/`, `agents/[id]/`, `workflows/[id]/` |
| 16 | `AgentForm`: loading states | Lectura `AgentForm.tsx:29` | ✅ | `<Skeleton className="h-9 w-full" />` para tools |
| 17 | `TemplatePicker`: loading states | Lectura `TemplatePicker.tsx:27,106-112` | ✅ | Skeletons para cards de templates |
| 18 | `CrewCanvas`: loading states | Lectura `CrewCanvas.tsx:45,369` | ✅ | `<Skeleton className="h-16 w-full" />` para agentList |
| 19 | `usePathname` usado en `floating-nav.tsx` | Lectura `floating-nav.tsx:21` | ✅ | Controla el estado expandido/colapsado |
| 20 | `useQuery` para `GET /api/tools/available` en `AgentForm` | Lectura `AgentForm.tsx` | ✅ | Lista de tools cargada desde API |
| 21 | `useQuery` para `GET /api/templates` en `TemplatePicker` | Lectura `TemplatePicker.tsx` | ✅ | Templates cargados desde API |
| 22 | `<AppSidebar />` en `AppLayout` | Lectura `layout.tsx:17` | ✅ | Presente |
| 23 | Tab agent-form (60/40 split) en `BuilderLayout` | Lectura `BuilderLayout.tsx:105-123` | ✅ | Grid `lg:grid-cols-[60%_40%]` |
| 24 | Botón "Templates" en `BuilderLayout` | Lectura `BuilderLayout.tsx:94-101` | ✅ | `Dialog` con `<TemplatePicker>` |
| 25 | Botón "Playground" en `BuilderLayout` | Lectura `BuilderLayout.tsx:84-93` | ✅ | `Sheet side="right"` con `<AgentPlayground>` |

**Mínimo verificado: 25 elementos** (requerido: ≥ 18 para 6-10 archivos afectados) ✅

### Discrepancias encontradas

#### D-09-1 — `navMain` local en `app-sidebar.tsx` es dead code sin "Builder"

- **Hallazgo:** `app-sidebar.tsx:28-38` define un array `navMain` local que NO incluye "Builder". Luego línea 64 llama `<NavMain />` sin `items={}`.
- **Realidad actual:** `<NavMain />` recibe `items ?? defaultNavItems` → usa `defaultNavItems` (que SÍ incluye Builder). Funciona pero por accidente.
- **Riesgo:** Si alguien modifica `nav-main.tsx` para renombrar/eliminar `defaultNavItems`, Builder desaparece sin error de TypeScript. Dos arrays de navegación violan SSOT.
- **Resolución:** Eliminar el `navMain` local de `app-sidebar.tsx` y cambiar `<NavMain />` por `<NavMain items={defaultNavItems} />`.

#### D-09-2 — Breadcrumbs no implementados en el proyecto

- **Hallazgo:** El componente `Breadcrumb` de shadcn/ui **existe** en `dashboard/components/ui/breadcrumb.tsx` pero **ningún archivo** en todo el proyecto lo importa.
- **Plan requiere:** "Breadcrumbs: Dashboard > Builder > [New Agent | Crew Canvas | Templates]"
- **Resolución:** Integrar `<Breadcrumb>` en la ruta `/builder` (page.tsx o un componente `Header/BreadcrumbBar` en `BuilderLayout.tsx` o `page.tsx`). Las sub-páginas del builder son tabs internas dentro de `BuilderLayout` — el breadcrumb solo necesita "Dashboard > Builder" (las tabs no son sub-rutas).

#### D-09-3 — Ningún `loading.tsx` ni `error.tsx` existe en el proyecto

- **Hallazgo:** `find` confirmó que NO existen archivos de convención Next.js App Router (`loading.tsx`, `error.tsx`) en ninguna ruta de `dashboard/`.
- **Patrón actual del proyecto:** Loading states y error handling están implementados **dentro** de cada componente (LoadingSpinner, message fijo, fallback de tabla vacía). Ejemplos: `agents/[id]`, `page.tsx`, `approvals/page.tsx`, `workflows/[id]/page.tsx`.
- **Plan requiere:** "Loading skeletons mientras cargan tools/templates" ✅ ya cumplido a nivel componente; "Error boundaries para el canvas" → BuilderCanvas ya usa `ssr: false` + `Skeleton` en el componente `dynamic`, pero no tiene `error.tsx`.
- **Resolución:** 
  - `loading.tsx`: crear con skeleton que replica la estructura del builder (título + columna canvas + formulario).
  - `error.tsx`: crear con patrón estándar Next.js (`error`, `reset`). ◦ Importante: ReactFlow puede romper el árbol de hidratación en SSR si hay un error no capturado dentro de CrewCanvas.

#### D-09-4 — No existe patrón `BackButton` ni breadcrumb en páginas de listado (solo en detalle)

- **Hallazgo:** `PageHeader` se usa solo en `tickets/page.tsx`. `BackButton` se usa solo en páginas de detalle (`/agents/[id]`, `/tasks/[id]`, `/workflows/[id]`).
- **Builder page** es una página de edición/creación, similar a detalle: usa `<h2>` directamente en `page.tsx:8`.
- **Resolución:** `page.tsx` del builder ya usa `<h2>` y `<BuilderLayout>`. Para mantener consistencia con páginas de detalle, agregar BackButton o Breadcrumb arriba del título.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema:** Sin cambios. Este paso es puramente de frontend (integración de navegación).
- ✅ **Integridad referencial:** N/A.
- ✅ **RLS policies:** N/A.
- ✅ **Índices necesarios:** N/A.
- ✅ **Tipos de datos:** N/A.

**Impacto en datos:** Nulo. No hay migraciones, tablas ni modelos de datos involucrados.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/componentes nuevos a crear/modificar

| Artefacto | Nuevo/Modificar | Ruta |
|---|---|---|
| `BuilderLoading` | **Nuevo** | `dashboard/app/(app)/builder/loading.tsx` |
| `BuilderError` | **Nuevo** | `dashboard/app/(app)/builder/error.tsx` |
| Breadcrumb Bar | **Nuevo o modificar** `page.tsx` | `dashboard/app/(app)/builder/page.tsx` |

### Patrones existentes a seguir

#### Patrón 1 — Skeleton en componentes existentes (BuilderCanvas)
```
dashboard/components/builder/BuilderCanvas.tsx:8
loading: () => <Skeleton className="h-64 w-full rounded-lg" />
```
`loading.tsx` debe usar `Skeleton` para skeletonizar el layout completo:
```
<div className="flex h-full flex-col space-y-4">
  <Skeleton className="h-8 w-48" />                        {/* título */}
  <div className="grid h-full gap-4 lg:grid-cols-[60%_40%]">
    <Skeleton className="h-64 w-full rounded-lg" />        {/* canvas */}
    <Skeleton className="h-64 w-full rounded-lg" />        {/* formulario */}
  </div>
</div>
```

#### Patrón 2 — BackButton en páginas de detalle
```
dashboard/app/(app)/agents/[id]/page.tsx:92   <BackButton href="/agents" />
dashboard/app/(app)/workflows/[id]/page.tsx:63 <BackButton href="/workflows" />
```
Construido con `<Button variant="ghost" size="sm" asChild>` y `<ArrowLeft>`.

#### Patrón 3 — LoadingSpinner + fallback en componente
```
dashboard/app/(app)/workflows/[id]/page.tsx:53-54
if (isLoading) return <LoadingSpinner label="Cargando workflow..." />
```

### Calidad y modularidad

`app-sidebar.tsx:28-38` declara un `navMain` local sin usarse (dead code). Son 10 líneas sin función. Aumenta superficie de mantenimiento. Eliminarlas + pasar `items={defaultNavItems}` a `<NavMain />` es código más limpio sin comportamiento cambiado.

### Imports necesarios para cada artefacto nuevo

```tsx
// loading.tsx
import { Skeleton } from '@/components/ui/skeleton'

// error.tsx  
import { Button } from '@/components/ui/button'

// page.tsx (breadcrumb)
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **APIs/endpoints:** Ninguno nuevo o modificado en este paso.
- ✅ **Middleware:** N/A.
- ✅ **Flujos:** N/A.
- ✅ **Contratos:** N/A.
- ✅ **Error handling:** N/A.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

1. Usuario hace clic en "Builder" en sidebar → navega a `/builder`
2. Next.js App Router dispara `loading.tsx` mientras `page.tsx` evalúa
3. `page.tsx` renderiza `<BuilderLayout />` dentro de `AppLayout`
4. `BuilderLayout` monta sus dos tabs: "Agent Form" y "Crew Canvas"
5. "Agent Form" → `AgentForm` hace `useQuery` `GET /api/tools/available`, `TemplatePicker` hace `useQuery` `GET /api/templates`
6. "Crew Canvas" → `BuilderCanvas` monta `CrewCanvas` vía `dynamic import` (`ssr: false`)
7. Navegación entre tabs, abrir Templates, abrir Playground → todo dentro del mismo árbol

### Cobertura de criterios del plan

| Criterio plan | Cobertura real | Acción requerida |
|---|---|---|
| Builder accesible desde sidebar | ✅ `nav-main.tsx:50` | D-09-1 dead code limpiar |
| Breadcrumbs funcionales | ❌ No implementados | D-09-2: crear Breadcrumb Bar |
| Estilo visual consistente | ✅ shadcn/ui + Tailwind | Sin acción |
| Canvas no rompa en SSR | ✅ `dynamic` `ssr:false` + `Skeleton` | Sin acción |
| Loading skeletons | ✅ Skeletons en componentes | D-09-3: crear `loading.tsx` |

### Gaps

1. **Breadcrumb en ruta Tornillo:** Si el builder es la última ruta implementada, el resto de las rutas tampoco tienen breadcrumbs. Pero el análisis se limita al paso.
2. **Espacialidad del builder:** El breadcrumb "Dashboard > Builder" es estático — no hay sub-rutas. Las subsecciones "New Agent", "Crew Canvas", "Templates" son vistas internas dentro de `BuilderLayout` (tabs), no rutas de Next.js, por lo que NO necesitan breadcrumb de ruta.

### Herramienta Propuesta: Next.js Boundary Validator

- **Qué automatiza:** El proyecto no tiene convención `loading.tsx` / `error.tsx` en ninguna ruta (confirmado por `find`). Esta herramienta valida que toda ruta de `app/(app)/` tenga ambos archivos o marque cuáles faltan como excepciones documentadas.
- **Tipo:** Script CLI Python
- **Cómo se usa:**
  ```bash
  python scripts/check_nextjs_boundaries.py --dir dashboard/app\(app\) --report-md DEVS/IN_PROGRESS/boundaries_report.md
  ```
  Output: Tabla con rutas que tienen/nofaltan `loading.tsx` y `error.tsx`. Código de salida 0=OK, 1=faltan archivos.
- **Impacto para el usuario final:** Sin `error.tsx`, un error en la hidratación de ReactFlow o un fallo de import en el builder muestra la página de error global de Next.js (interfaz roja genérica). Con error boundary local, el usuario ve un mensaje localizado + botón "Try again" y el resto del dashboard permanece funcional. Esta herramienta detecta antes de implementar qué rutas carecen de protección.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Sub-paso | Etapa |
|---|---|---|---|
| ✅ | [DATA] Sin cambios en DB/schema | — | — |
| ✅ | [CODE] `loading.tsx` existe en `/builder/` exportando `BuilderLoading` | Tarea 1 | CODE |
| ✅ | [CODE] `error.tsx` existe en `/builder/` exportando `BuilderError` | Tarea 2 | CODE |
| ✅ | [CODE] Breadcrumb `Dashboard > Builder` visible en `/builder/page.tsx` | Tarea 3 | CODE |
| ✅ | [CODE] `app-sidebar.tsx` llama `<NavMain items={defaultNavItems} />` sin dead code | Tarea 4 | CODE |
| ✅ | [BACKEND] Sin cambios en backend | — | — |
| ✅ | [FULLSTACK] Navegar desde sidebar a `/builder` no rompe el árbol de hidratación | Tarea 5 | FULLSTACK |
| ✅ | [FULLSTACK] Skeleton visible brevemente al cargar `/builder` | Tarea 1 | FULLSTACK |
| ✅ | [FULLSTACK] Si ReactFlow lanza error, se ve el error boundary, no pantalla roja global | Tarea 2 | FULLSTACK |
| ✅ | [DX] `check_nextjs_boundaries.py --help` ejecuta sin errores | Tarea 0 | DX |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ReactFlow error no capturado rompe árbol | Alta | CrewCanvas se renderiza en cliente (`ssr:false`), errores devueltos no tienen error boundary hasta ahora | Crear `error.tsx` específico para `/builder/` |
| Duplicación de `navMain` genera builder fantasma | Media | Si `nav-main.tsx` se edita sin darse cuenta del array duplicado en `app-sidebar.tsx`, Builder sale de un menú pero no del otro | Eliminar `navMain` local → SSOT en `defaultNavItems` |
| Breadcrumbs sin patrón establecido | Baja | No hay ningún archivo usando `<Breadcrumb>` → sin precedente a seguir | Seguir especificación de shadcn/ui docs; implementar en `page.tsx` con `usePathname` |
| Inconsistencia de estilos entre tabs builder vs resto | Baja | `BuilderLayout` y `AgentForm` tienen su propia h2 vs `PageHeader` | Usar componentes shadcn/ui existentes (PageHeader/BackButton) |

---

## 7️⃣ Plan de Implementación

> [!CRITICAL] Tarea 0 siempre = DX & Tooling. El implementador la ejecuta primero.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Next.js Boundary Validator | `scripts/check_nextjs_boundaries.py` | `def check_boundaries(dir: str) -> dict[str, list[str]]`, `def main()` | `scripts/sanitize_codebase.py:44-64` (patrón argparse + subprocess runner) | DX | Media | 0.5h | Ninguna | → verificar: `python scripts/check_nextjs_boundaries.py --help` ejecuta sin errores |
| 1 | Implementar `loading.tsx` para ruta `/builder/` | `dashboard/app/(app)/builder/loading.tsx` | `export default function BuilderLoading()` | `Skeleton` patterns en `BuuilderCanvas.tsx:8`, `CrewCanvas.tsx:369` + `section-cards.tsx:66` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `Dashboard > Builder` muestra skeleton por ≥50ms durante carga |
| 2 | Implementar `error.tsx` para ruta `/builder/` | `dashboard/app/(app)/builder/error.tsx` | `export default function BuilderError({ error, reset }: { error: Error & { digest?: string }, reset: () => void })` | Patrón oficial Next.js App Router `error.tsx` + `Button` de `@/components/ui/button` | CODE | Baja | 0.5h | Tarea 0 | → verificar: Lanzar `throw new Error('test')` en `page.tsx` muestra error boundary con texto del error y botón |
| 3 | Integrar breadcrumb "Dashboard > Builder" en `page.tsx` | `dashboard/app/(app)/builder/page.tsx` | Agregar antes de `<h2>`: `<Breadcrumb><BreadcrumbList><BreadcrumbItem><BreadcrumbLink href="/">Dashboard</BreadcrumbLink></BreadcrumbItem><BreadcrumbSeparator/> <BreadcrumbItem><BreadcrumbPage>Builder</BreadcrumbPage></BreadcrumbItem></BreadcrumbList></Breadcrumb>` | `dashboard/components/ui/breadcrumb.tsx` API; shadcn/ui doc | CODE | Baja | 0.5h | Tarea 2 | → verificar: Navegar a `/builder` muestra "Dashboard / Builder" como breadcrumb |
| 4 | Limpiar `app-sidebar.tsx` — eliminar `navMain` local + pasar `items={defaultNavItems}` | `dashboard/components/app-sidebar.tsx` | Remover líneas 6-15 (imports iconos) + líneas 28-38 (`const navMain = [...]`) + cambiar `<NavMain />` por `<NavMain items={defaultNavItems} />` | `nav-main.tsx:43-64` (`defaultNavItems` array) | CODE | Baja | 0.3h | Ninguna | → verificar: Sidebar continúa mostrando "Builder"; `grep -c "Builder" app-sidebar.tsx` = 0 (no se menciona directamente) |
| 5 | Validar integración end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-4 | → verificar: Todos los criterios §5 [FULLSTACK] y [CODE] pasan |

**Tiempo total estimado:** 2.5h

### Notas importantes sobre arquitectura

- **Breadcrumb NO navegable:** "Builder" en el breadcrumb puede ser un `<Link href="/builder">` (igual que el resto de rutas) o puede ser estático si hay una sola ruta. Aquí se hace navegable (Link) para consistencia con el resto del proyecto.
- **No hay sub-rutas:** Las secciones "Agent Form", "Crew Canvas", "Templates" son tabs de `BuilderLayout.tsx`, no rutas Next.js. El breadcrumb solo necesita 2 niveles: `Dashboard > Builder`. No se extiende a las tabs.
- **`loading.tsx` reemplaza completamente el árbol mientras se evalúa:** No aparecen los skeletons de AgentForm/TemplatePicker durante ese tiempo — el skeleton de `loading.tsx` se muestra primero, luego los skeletons internos al montar.

---

### 📁 Estructura después del paso

```
dashboard/app/(app)/
├── builder/
│   ├── page.tsx              ← ya existe, agregar Breadcrumb + PageHeader
│   ├── loading.tsx           ← NUEVO
│   └── error.tsx             ← NUEVO
├── agents/[id]/page.tsx      ← sin cambiarsin cambios (modelo de sub-página)
└── workflows/[id]/page.tsx   ← sin cambios
```

---

*Archivo de entrada único. Solo este archivo debe ser modificado durante el análisis.*
