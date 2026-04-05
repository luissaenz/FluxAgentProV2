# Plan de Migración a shadcn/ui — FluxAgentPro-v2 Dashboard

## Estado Actual

El proyecto ya tiene **casi toda la infraestructura de shadcn/ui lista**:

| Requisito | Estado | Detalle |
|-----------|--------|---------|
| `cn()` helper en `lib/utils.ts` | ✅ Listo | Implementación estándar con `clsx` + `twMerge` |
| CSS Variables en `globals.css` | ✅ Listo | Tema completo light/dark con variables shadcn (`--background`, `--primary`, etc.) |
| `tailwind.config.ts` | ✅ Listo | `darkMode: 'class'`, paths correctos |
| `class-variance-authority` | ✅ Instalado | Pero no se usa activamente |
| Radix UI primitives | ✅ Parcial | `dialog`, `dropdown-menu`, `select`, `tabs`, `slot` instalados |
| `components/ui/Badge.tsx` | ⚠️ Parcial | Existe pero sin variantes CVA |
| `components.json` | ❌ Ausente | Archivo de config de shadcn CLI |

**Bloques shadcn a integrar**:
| Bloque | Reemplaza | Estado Actual | Archivos que genera |
|--------|-----------|---------------|---------------------|
| **dashboard-01** | `Sidebar.tsx` + `MobileMenu.tsx` + `app/(app)/layout.tsx` + `app/(app)/page.tsx` + Overview stat cards + recent tasks list | Custom sidebar raw HTML + manual layout + stat cards inline | `app-sidebar.tsx`, `site-header.tsx`, `section-cards.tsx`, `data-table.tsx`, `chart-area-interactive.tsx`, `nav-main.tsx`, `nav-documents.tsx`, `nav-secondary.tsx`, `nav-user.tsx`, `data.json` + UI components |
| **login-04** | `app/(auth)/login/page.tsx` | Form raw HTML (75 líneas) | `login-form.tsx` |

**Conclusión**: El 80% de la base ya está. La migración es principalmente instalar componentes y reemplazar patrones raw HTML. Los bloques dashboard-01 y login-04 se instalan vía CLI y reemplazarán completamente los componentes actuales de Sidebar, Layout, Overview y Login.

---

## Fase 0: Instalación y Configuración Base

### 0.1 Instalar shadcn CLI

```bash
cd dashboard
npx shadcn@latest init
```

Esto generará `components.json` con:
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "app/globals.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

> **Nota**: Como el proyecto ya tiene las CSS variables y el `cn()` helper, usar `style: "default"` y `cssVariables: true`.

### 0.2 Dependencias npm Adicionales

```bash
npm install @radix-ui/react-accordion @radix-ui/react-scroll-area @radix-ui/react-switch @radix-ui/react-label @radix-ui/react-toast vaul @hookform/resolvers react-hook-form lucide-react
```

| Paquete | Para qué |
|---------|----------|
| `@radix-ui/react-accordion` | AccordionSection |
| `@radix-ui/react-scroll-area` | Kanban columns scroll |
| `@radix-ui/react-switch` | Theme toggle |
| `@radix-ui/react-label` | Form labels consistentes |
| `@radix-ui/react-toast` | Notificaciones de éxito/error |
| `vaul` | Drawer (Sheet alternative) |
| `@hookform/resolvers` + `react-hook-form` | Validación de formularios |

### 0.3 Componentes shadcn a Instalar

```bash
# Core UI elements
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add textarea
npx shadcn@latest add label
npx shadcn@latest add select
npx shadcn@latest add dropdown-menu
npx shadcn@latest add table
npx shadcn@latest add card
npx shadcn@latest add dialog
npx shadcn@latest add accordion
npx shadcn@latest add skeleton
npx shadcn@latest add tabs
npx shadcn@latest add badge
npx shadcn@latest add separator
npx shadcn@latest add scroll-area
npx shadcn@latest add sheet
npx shadcn@latest add pagination
npx shadcn@latest add alert
npx shadcn@latest add avatar
npx shadcn@latest add switch
npx shadcn@latest add toast
npx shadcn@latest add sonner
npx shadcn@latest add tooltip
npx shadcn@latest add command
npx shadcn@latest add popover
```

### 0.4 Instalar Bloques shadcn (dashboard-01 + login-04)

Estos son **bloques completos** que reemplazarán componentes existentes. Se instalan vía CLI:

```bash
# Dashboard block — reemplaza Sidebar + Layout + Overview page
npx shadcn@latest add dashboard-01

# Login block — reemplaza login page
npx shadcn@latest add login-04
```

**Dependencias que instalará automáticamente dashboard-01**:
- `@shadcn/sidebar` (AppSidebar + SidebarProvider, SidebarInset, etc.)
- `@shadcn/breadcrumb`
- `@shadcn/scroll-area`
- `@shadcn/separator`
- `@shadcn/card`
- `@shadcn/table`
- `@shadcn/chart` (si incluye charts)
- `@tanstack/react-table` (para DataTable)
- `recharts` (para ChartAreaInteractive)
- `lucide-react` (ya instalado)

**Dependencias que instalará automáticamente login-04**:
- `@shadcn/button`
- `@shadcn/input`
- `@shadcn/label`
- `@shadcn/card`

#### dashboard-01 — Estructura que instalará

```
app/
  dashboard/
    page.tsx                    ← Template principal (adaptar a app/(app)/page.tsx)
    data.json                   ← Datos de ejemplo para DataTable

components/
  app-sidebar.tsx               ← Reemplaza components/layout/Sidebar.tsx + MobileMenu.tsx
  site-header.tsx               ← Reemplaza components/layout/Header.tsx
  section-cards.tsx             ← Reemplaza StatCards inline de Overview
  chart-area-interactive.tsx    ← Nuevo: chart placeholder (adaptar para FAP)
  data-table.tsx                ← Reemplaza tabla raw HTML de Tasks page
  nav-main.tsx                  ← Nav items principales (adaptar rutas FAP)
  nav-documents.tsx             ← Nav secundario (usar para agents/workflows)
  nav-secondary.tsx             ← Nav adicional (events, architect)
  nav-user.tsx                  ← User menu (reemplaza user email + sign-out)

  ui/
    sidebar.tsx                 ← Nuevo: SidebarProvider, SidebarInset, SidebarTrigger
    breadcrumb.tsx              ← Nuevo
    scroll-area.tsx             ← Nuevo
    separator.tsx               ← Nuevo
    card.tsx                    ← Nuevo
    table.tsx                   ← Nuevo
    chart.tsx                   ← Nuevo (si aplica)
```

**Estructura del bloque dashboard-01**:
```tsx
// Layout principal:
<SidebarProvider>
  <AppSidebar variant="inset" />
  <SidebarInset>
    <SiteHeader />              {/* Header con breadcrumb + user menu */}
    <div className="flex flex-1 flex-col">
      <SectionCards />          {/* Stat cards grid */}
      <ChartAreaInteractive />  {/* Chart placeholder */}
      <DataTable data={data} /> {/* Tabla con sorting, filtering, pagination */}
    </div>
  </SidebarInset>
</SidebarProvider>
```

**Adaptación necesaria para FAP**:

1. **`app-sidebar.tsx`** — Rutas de FAP:
   - Overview (`/`)
   - Kanban (`/kanban`)
   - Aprobaciones (`/approvals`) con badge pending count
   - Historial (`/tasks`)
   - Agentes (`/agents`)
   - Workflows (`/workflows`)
   - Eventos (`/events`)
   - Chat MDC (`/architect`)
   - Integrar con `useCurrentOrg` para OrgSelector
   - Integrar con `useApprovals` para pending count

2. **`site-header.tsx`** — Simplificar:
   - Breadcrumb con nombre de org
   - ThemeToggle
   - Eliminar user email (ya está en nav-user)

3. **`section-cards.tsx`** — Adaptar stat cards:
   - Total tareas
   - Completadas (% éxito)
   - Ejecutando
   - Errores
   - HITL pendientes

4. **`chart-area-interactive.tsx`** — Reemplazar o eliminar:
   - Opción A: Eliminar (FAP no tiene charts aún)
   - Opción B: Adaptar para mostrar métricas de bartenders (cuando se integre)

5. **`data-table.tsx`** — Adaptar para Tasks page:
   - Columnas: ID, Flow, Estado, Creado
   - Sorting por columna
   - Filtering por status y flow_type
   - Pagination

6. **`app/(app)/layout.tsx`** — Reemplazar con estructura dashboard-01:
   - Usar `SidebarProvider` + `SidebarInset`
   - Eliminar manual sidebar open/close state
   - Eliminar Header component actual

7. **`app/(app)/page.tsx`** — Reemplazar Overview:
   - Usar `SectionCards` para stat cards
   - Usar `DataTable` para recent tasks list
   - Eliminar StatCard inline function

#### login-04 — Estructura que instalará

```
components/
  login-form.tsx           ← Nuevo: formulario completo con validación
app/
  login/
    page.tsx               ← Reemplaza app/(auth)/login/page.tsx
```

**Estructura del bloque login-04**:
```tsx
// Layout centrado con bg-muted
// LoginForm component con:
// - Card wrapper con header
// - Email + Password inputs
// - Submit button con loading state
// - Dependencies: button, input, label
```

**Adaptación necesaria para FAP**:
- Integrar con `useAuth` hook existente (Supabase auth)
- Mantener `signIn(email, password)` logic
- Preservar error handling y redirect post-login

---

### 0.6 Decisiones de Diseño Resueltas

#### Decisión 1: PageHeader en Overview → NO agregar

`SectionCards` ya funciona como hero visual de la página. Agregar un `PageHeader` encima sería redundante y rompería el patrón visual del bloque dashboard-01 original.

```tsx
// app/(app)/page.tsx — Overview SIN PageHeader
export default function OverviewPage() {
  return (
    <>
      <SectionCards />          {/* Hero visual — no necesita título arriba */}
      <div className="px-4 lg:px-6">
        <h3 className="mb-4 text-lg font-semibold">Tareas recientes</h3>
        <DataTable ... />
      </div>
    </>
  )
}
```

**Excepción**: Todas las demás páginas SÍ usan `PageHeader` como patrón estándar.

---

#### Decisión 2: DataTable compone LoadingSpinner y EmptyState internamente

`DataTable` maneja sus propios estados de loading y empty. Las páginas no repiten esa lógica.

```tsx
interface DataTableProps<T> {
  data: T[]
  columns: ColumnDef<T>[]
  isLoading?: boolean
  emptyMessage?: string
  pageSize?: number
}

export function DataTable<T>({
  data, columns, isLoading, emptyMessage, pageSize = 10,
}: DataTableProps<T>) {
  if (isLoading) {
    return <LoadingSpinner label="Cargando datos..." />
  }

  if (!data.length) {
    return <EmptyState description={emptyMessage || 'No hay datos para mostrar'} />
  }

  // Render tabla normal con tanstack-table
  return (/* tabla con sorting, pagination, etc. */)
}
```

**Uso en páginas**: Solo pasan `isLoading` y `emptyMessage`. No repiten condicionales.

---

#### Decisión 3: chart-area-interactive.tsx → ELIMINAR

FAP no tiene charts actualmente. Mantener el archivo genera confusión y código muerto.

```bash
rm components/chart-area-interactive.tsx
rm app/dashboard/data.json
```

En `app/(app)/page.tsx` simplemente no importarlo. Dejar un comentario `// TODO: Agregar chart de métricas cuando se integre el módulo de bartenders` por si se quiere agregar charts en el futuro.

---

#### Decisión 4: OrgSelector → Integrar en nav-user.tsx

`nav-user.tsx` del bloque dashboard-01 ya tiene un dropdown en el footer del sidebar. Es el lugar natural para el org switcher. No tiene sentido tener dos dropdowns separados.

**Estructura de `nav-user.tsx` adaptada**:

```tsx
'use client'

import { ChevronsUpDown, LogOut, Building2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

export function NavUser() {
  const { signOut } = useAuth()
  const { orgs, currentOrg, switchOrg } = useCurrentOrg()

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton size="lg" className="data-[state=open]:bg-sidebar-accent">
              <Building2 className="h-4 w-4" />
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">{currentOrg?.name || 'Sin organización'}</span>
                <span className="truncate text-xs text-muted-foreground">{orgs.length} org{orgs.length !== 1 ? 's' : ''}</span>
              </div>
              <ChevronsUpDown className="ml-auto size-4" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>

          <DropdownMenuContent className="w-[--radix-dropdown-menu-trigger-width] min-w-56" side="right" align="end">
            {orgs.map((org) => (
              <DropdownMenuItem key={org.id} onClick={() => switchOrg(org.id)} className={currentOrg?.id === org.id ? 'bg-accent' : ''}>
                <Building2 className="mr-2 h-4 w-4" />
                {org.name}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => signOut()}>
              <LogOut className="mr-2 h-4 w-4" />
              Cerrar sesión
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
```

**Beneficios**:
- ✅ Un solo dropdown en el footer del sidebar
- ✅ Muestra org actual + permite cambiar
- ✅ Sign out integrado en el mismo menú
- ✅ Elimina `OrgSelector.tsx` como archivo separado

### 0.5 Mejorar Badge Existente con CVA

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        success:
          "border-transparent bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
        warning:
          "border-transparent bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
        info:
          "border-transparent bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
```

---

## Fase 1: Componentes Compartidos (Shared Utilities)

### Prioridad: 🔴 CRÍTICA — Se usan en toda la app

Estos componentes se usan en múltiples páginas y deben migrarse primero para que el resto de la migración los pueda usar.

**Nota**: `StatCard` NO va aquí — es reemplazado por `SectionCards` del bloque dashboard-01.

### 1.1 Crear `components/shared/BackButton.tsx`

**Ubicación actual**: Repetido en 4 detail pages (`tasks/[id]`, `agents/[id]`, `workflows/[id]`)

```tsx
'use client'

import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

interface BackButtonProps {
  href: string
  label?: string
}

export function BackButton({ href, label = 'Volver' }: BackButtonProps) {
  return (
    <Button variant="ghost" size="sm" asChild className="mb-4">
      <Link href={href}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        {label}
      </Link>
    </Button>
  )
}
```

### 1.2 Crear `components/shared/PageHeader.tsx`

**Ubicación actual**: `<h2 className="text-2xl font-bold ...">` repetido en ~11 páginas

```tsx
'use client'

interface PageHeaderProps {
  title: string
  description?: string
  action?: React.ReactNode
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
```

### 1.3 Crear `components/shared/CodeBlock.tsx`

**Ubicación actual**: `<pre className="overflow-x-auto rounded bg-gray-50 p-4 text-xs ...">` en ~5 archivos

```tsx
'use client'

interface CodeBlockProps {
  code: unknown
  title?: string
  className?: string
}

export function CodeBlock({ code, title, className }: CodeBlockProps) {
  return (
    <div className={className}>
      {title && (
        <h4 className="mb-2 text-sm font-medium">{title}</h4>
      )}
      <pre className="overflow-x-auto rounded-md bg-muted p-4 text-xs text-muted-foreground">
        {JSON.stringify(code, null, 2)}
      </pre>
    </div>
  )
}
```

### 1.4 Crear `components/shared/LoadingSpinner.tsx`

**Ubicación actual**: `h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent` en ~8 archivos

```tsx
'use client'

import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  label?: string
}

export function LoadingSpinner({ size = 'md', className, label }: LoadingSpinnerProps) {
  const sizeMap = { sm: 'h-4 w-4', md: 'h-8 w-8', lg: 'h-12 w-12' }
  return (
    <div className={cn('flex flex-col items-center justify-center gap-2', className)}>
      <Loader2 className={cn('animate-spin text-primary', sizeMap[size])} />
      {label && <p className="text-sm text-muted-foreground">{label}</p>}
    </div>
  )
}
```

### 1.5 Crear `components/shared/EmptyState.tsx`

**Ubicación actual**: `flex flex-col items-center justify-center py-12 text-gray-400` en ~5 archivos

```tsx
'use client'

import { Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: React.ReactNode
  title?: string
  description?: string
  className?: string
}

export function EmptyState({
  icon,
  title = 'Sin datos',
  description = 'No hay elementos para mostrar',
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center text-muted-foreground', className)}>
      {icon || <Inbox className="mb-4 h-12 w-12 opacity-50" />}
      <p className="text-sm font-medium">{title}</p>
      <p className="text-xs">{description}</p>
    </div>
  )
}
```

### 1.6 Crear `components/shared/StatusLabel.tsx`

**Reemplaza**: Uso manual de `STATUS_BADGES` con `Badge` raw

```tsx
'use client'

import { Badge } from '@/components/ui/badge'
import type { TaskStatus } from '@/lib/types'

const STATUS_CONFIG: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'info'; label: string }> = {
  pending:      { variant: 'info',      label: 'Pendiente' },
  running:      { variant: 'warning',   label: 'Ejecutando' },
  completed:    { variant: 'success',   label: 'Completado' },
  failed:       { variant: 'destructive', label: 'Error' },
  awaiting_approval: { variant: 'warning', label: 'HITL' },
  rejected:     { variant: 'destructive', label: 'Rechazado' },
  cancelled:    { variant: 'secondary', label: 'Cancelado' },
}

interface StatusLabelProps {
  status: string
}

export function StatusLabel({ status }: StatusLabelProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG['pending']
  return <Badge variant={config.variant}>{config.label}</Badge>
}
```

---

## Fase 2: Layout + Overview — Integración dashboard-01

### Prioridad: 🟠 ALTA — Base de toda la UI

### 2.0 Instalar y Adaptar dashboard-01 Block

**Este bloque reemplaza COMPLETAMENTE**:
- `components/layout/Sidebar.tsx` (eliminar)
- `components/layout/MobileMenu.tsx` (eliminar — dashboard-01 incluye responsive)
- `components/layout/Header.tsx` (reemplazar con site-header.tsx)
- `components/layout/OrgSelector.tsx` (integrar en nav-user.tsx)
- `app/(app)/layout.tsx` (reemplazar con estructura SidebarProvider)
- `app/(app)/page.tsx` (reemplazar Overview con SectionCards + DataTable)
- `components/chart-area-interactive.tsx` (eliminar — sin charts)
- `app/dashboard/data.json` (eliminar — datos reales de API)

#### Paso 1: Instalar el bloque

```bash
npx shadcn@latest add dashboard-01
```

Esto generará **~15 archivos** entre componentes y UI primitives:

| Archivo | Propósito en dashboard-01 | Uso en FAP |
|---------|---------------------------|------------|
| `app-sidebar.tsx` | Sidebar con navegación | Adaptar con rutas FAP + hooks |
| `site-header.tsx` | Header con breadcrumb + user menu | Simplificar + agregar ThemeToggle |
| `section-cards.tsx` | Stat cards del dashboard | Adaptar para métricas de FAP |
| `chart-area-interactive.tsx` | Chart de ejemplo | **ELIMINAR** — FAP no tiene charts |
| `data-table.tsx` | Tabla con sorting/filtering | Usar en Tasks page + Overview recent tasks |
| `nav-main.tsx` | Nav items principales | Adaptar rutas principales FAP |
| `nav-documents.tsx` | Nav secundario (documentos) | Adaptar para agents/workflows |
| `nav-secondary.tsx` | Nav adicional | Adaptar para events/architect |
| `nav-user.tsx` | User menu + settings | **Integrar OrgSelector + sign out** |
| `data.json` | Datos mock para tabla | **ELIMINAR** — usar datos reales de API |

#### Paso 2: Estructura del Layout (`app/(app)/layout.tsx`)

**Antes** (actual):
```tsx
<div className="flex h-screen overflow-hidden">
  <div className={cn("hidden h-screen border-r ...", isSidebarOpen ? "w-64" : "w-0")}>
    <Sidebar />
  </div>
  <div className="flex flex-1 flex-col overflow-hidden">
    <Header ... />
    <main className="flex-1 overflow-y-auto bg-gray-50 p-4">{children}</main>
  </div>
</div>
```

**Después** (con dashboard-01):
```tsx
'use client'

import { AppSidebar } from '@/components/app-sidebar'
import { SiteHeader } from '@/components/site-header'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { useRealtimeDashboard } from '@/hooks/useRealtimeDashboard'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { orgId } = useCurrentOrg()
  useRealtimeDashboard(orgId)

  return (
    <SidebarProvider>
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader />
        <main className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              {children}
            </div>
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
```

**Beneficios de dashboard-01**:
- ✅ **SidebarProvider** maneja open/close state automáticamente
- ✅ **SidebarInset** ajusta contenido con transiciones suaves
- ✅ **Responsive automático**: sidebar → drawer en mobile (sin MobileMenu)
- ✅ **Breadcrumb** integrado en SiteHeader
- ✅ **User menu** con nav-user (sign out integrado)
- ✅ **~70% menos código** en layout (~25 líneas vs ~65 actuales)
- ✅ Elimina `useState` para sidebar toggle

#### Paso 3: Adaptar `app-sidebar.tsx` para FAP

El bloque genera un sidebar genérico con nav-main, nav-documents, nav-secondary. Debe adaptarse:

```tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Columns3,
  ShieldCheck,
  History,
  Bot,
  Workflow,
  Activity,
  MessageSquare,
} from 'lucide-react'
import { NavMain } from '@/components/nav-main'
import { NavUser } from '@/components/nav-user'     {/* ← Incluye OrgSelector + Sign Out */}
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'

const navMain = [
  { title: 'Overview', url: '/', icon: LayoutDashboard },
  { title: 'Kanban', url: '/kanban', icon: Columns3 },
  { title: 'Aprobaciones', url: '/approvals', icon: ShieldCheck },
  { title: 'Historial', url: '/tasks', icon: History },
  { title: 'Agentes', url: '/agents', icon: Bot },
  { title: 'Workflows', url: '/workflows', icon: Workflow },
  { title: 'Eventos', url: '/events', icon: Activity },
  { title: 'Chat MDC', url: '/architect', icon: MessageSquare },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { currentOrg } = useCurrentOrg()
  const pathname = usePathname()

  return (
    <Sidebar variant="inset" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <span className="text-xs font-bold">FP</span>
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">FluxAgentPro</span>
                  <span className="truncate text-xs">V2</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <NavMain
          items={navMain.map(item => ({
            ...item,
            isActive: item.url === '/'
              ? pathname === '/'
              : pathname.startsWith(item.url),
          }))}
        />
      </SidebarContent>

      <SidebarFooter>
        {/* NavUser integra OrgSelector + Sign Out — ver Decisión 4 */}
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  )
}
```

#### Paso 4: Adaptar `section-cards.tsx` para FAP

**Antes** (StatCard inline en `app/(app)/page.tsx`):
```tsx
function StatCard({ icon, label, value, subtext, highlight }) {
  return (
    <div className={`rounded-lg border bg-white p-4 ...`}>
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  )
}
```

**Después** (con SectionCards de dashboard-01):
```tsx
'use client'

import { useTasks } from '@/hooks/useTasks'
import { useApprovals } from '@/hooks/useApprovals'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LayoutDashboard, CheckCircle, Clock, AlertTriangle, ShieldCheck } from 'lucide-react'

export function SectionCards() {
  const { orgId } = useCurrentOrg()
  const { data: tasksData } = useTasks(orgId)
  const { data: approvals } = useApprovals(orgId)

  const tasks = tasksData?.items || []
  const pendingApprovals = approvals?.filter(a => a.status === 'pending').length || 0

  const stats = {
    total: tasks.length,
    completed: tasks.filter(t => t.status === 'completed').length,
    running: tasks.filter(t => t.status === 'running').length,
    failed: tasks.filter(t => t.status === 'failed').length,
    successRate: tasks.length > 0
      ? Math.round((tasks.filter(t => t.status === 'completed').length / tasks.length) * 100)
      : 0,
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total tareas</CardTitle>
          <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.total}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Completadas</CardTitle>
          <CheckCircle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.completed}</div>
          <p className="text-xs text-muted-foreground">{stats.successRate}% éxito</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Ejecutando</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.running}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Errores</CardTitle>
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.failed}</div>
        </CardContent>
      </Card>

      <Card className={pendingApprovals > 0 ? 'border-amber-300 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-900/10' : ''}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">HITL pendientes</CardTitle>
          <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{pendingApprovals}</div>
        </CardContent>
      </Card>
    </div>
  )
}
```

#### Paso 5: Adaptar `site-header.tsx`

El bloque genera un header con breadcrumb + user menu. Adaptar para FAP:

```tsx
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import { ThemeToggle } from '@/components/theme-toggle'
import { NavUser } from '@/components/nav-user'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'

export function SiteHeader() {
  const { currentOrg } = useCurrentOrg()

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem className="hidden md:block">
            <BreadcrumbLink href="/">FluxAgentPro</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator className="hidden md:block" />
          <BreadcrumbItem>
            <BreadcrumbPage>{currentOrg?.name || 'Dashboard'}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <NavUser />
      </div>
    </header>
  )
}
```

#### Paso 6: Reemplazar `app/(app)/page.tsx` (Overview)

**Nota**: Overview NO usa `PageHeader` — `SectionCards` ya funciona como hero visual.
Todas las demás páginas SÍ usan `PageHeader` como patrón estándar.

**Después**:
```tsx
'use client'

import { SectionCards } from '@/components/section-cards'
import { DataTable } from '@/components/data-table'
import { useTasks } from '@/hooks/useTasks'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'

// Columnas para la tabla de recent tasks
const columns = [
  { accessorKey: 'task_id', header: 'ID', cell: ({ row }) => row.getValue('task_id').slice(0, 12) + '...' },
  { accessorKey: 'flow_type', header: 'Flow' },
  { accessorKey: 'status', header: 'Estado', cell: ({ row }) => <StatusLabel status={row.getValue('status')} /> },
  { accessorKey: 'created_at', header: 'Creado', cell: ({ row }) => formatDistanceToNow(new Date(row.getValue('created_at')), { addSuffix: true }) },
]

export default function OverviewPage() {
  const { orgId, currentOrg } = useCurrentOrg()
  const { data: tasksData, isLoading } = useTasks(orgId)
  const tasks = tasksData?.items?.slice(0, 10) || []

  return (
    <>
      {/* SectionCards actúa como hero — no necesita PageHeader arriba */}
      <SectionCards />
      <div className="px-4 lg:px-6">
        <h3 className="mb-4 text-lg font-semibold">Tareas recientes</h3>
        <DataTable
          data={tasks}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No hay tareas aún"
        />
      </div>
    </>
  )
}
```

#### Paso 7: Archivos a eliminar

```bash
# Estos archivos ya no se necesitan
rm components/layout/Sidebar.tsx
rm components/layout/MobileMenu.tsx
rm components/layout/Header.tsx
rm components/layout/OrgSelector.tsx        # Integrado en nav-user.tsx
rm components/chart-area-interactive.tsx    # Sin charts en FAP
rm app/dashboard/data.json                  # Datos mock (usar API real)
rm components/shared/StatCard.tsx           # Reemplazado por SectionCards
```

**Resumen de reemplazos**:
| Componente Actual | Reemplazado Por | Tipo |
|-------------------|-----------------|------|
| `Sidebar.tsx` | `app-sidebar.tsx` + `nav-main.tsx` | dashboard-01 |
| `MobileMenu.tsx` | Integrado en sidebar (responsive automático) | Eliminado |
| `Header.tsx` | `site-header.tsx` | dashboard-01 |
| `OrgSelector.tsx` | Integrado en `nav-user.tsx` | dashboard-01 |
| `StatCard` (inline) | `section-cards.tsx` | dashboard-01 |
| `chart-area-interactive.tsx` | No existe en FAP | Eliminado |
| `data.json` | No existe en FAP | Eliminado |
| `app/(app)/layout.tsx` | `SidebarProvider` structure | Refactor |
| `app/(app)/page.tsx` | `SectionCards` + `DataTable` | Refactor |

---

### 2.1 `components/layout/OrgSelector.tsx` → Integrar en AppSidebar

**Estado actual**: Manual `useState(open)` + `<div>` absoluto (no accesible, no cierra con click outside)

**Antes**:
```tsx
<div className="relative">
  <button onClick={() => setOpen(!open)} className="...">
    {currentOrg?.name}
  </button>
  {open && (
    <div className="absolute left-0 top-full z-50 mt-1 w-56 ...">
      {orgs.map(org => (
        <button onClick={() => { onSelect(org); setOpen(false) }}>
          {org.name}
        </button>
      ))}
    </div>
  )}
</div>
```

**Después**:
```tsx
'use client'

import { Building2, ChevronDown } from 'lucide-react'
import type { Organization } from '@/lib/types'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface OrgSelectorProps {
  orgs: Organization[]
  currentOrg: Organization | null
  onSelect: (org: Organization) => void
}

export function OrgSelector({ orgs, currentOrg, onSelect }: OrgSelectorProps) {
  if (orgs.length <= 1) {
    return (
      <div className="flex items-center gap-2 text-sm font-medium">
        <Building2 className="h-4 w-4" />
        {currentOrg?.name || 'Sin organización'}
      </div>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Building2 className="h-4 w-4" />
          {currentOrg?.name || 'Seleccionar org'}
          <ChevronDown className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {orgs.map((org) => (
          <DropdownMenuItem
            key={org.id}
            onClick={() => onSelect(org)}
            className={cn(
              org.id === currentOrg?.id && 'bg-accent text-accent-foreground font-medium'
            )}
          >
            {org.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
```

**Beneficios**:
- ✅ Click outside cierra automáticamente
- ✅ Navegación por teclado
- ✅ ARIA attributes
- ✅ Animaciones consistentes

---

### 2.2 `components/layout/MobileMenu.tsx` → shadcn Dialog

**Estado actual**: Ya usa Radix Dialog directamente. Solo necesita wrapper de shadcn.

**Cambios menores**:
- Reemplazar `Dialog.Portal` → `DialogContent` de shadcn
- Agregar `DialogHeader`, `DialogDescription`
- Usar clases de shadcn en overlay y content

---

### 2.3 `components/layout/Sidebar.tsx` → Custom con shadcn styling

**No hay shadcn Sidebar equivalente**. Mantener custom pero:

**Cambios**:
- Reemplazar raw `<button>` → `Button` de shadcn con `variant="ghost"`
- Reemplazar badge count manual → `Badge` con `variant="default"`
- Usar `Separator` entre secciones
- Usar `Tooltip` para modo colapsado

**Antes**:
```tsx
<Link href={item.href} className={cn(
  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
  isActive
    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400'
    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
)}>
  <item.icon className="h-5 w-5" />
  {item.label}
</Link>
```

**Después**:
```tsx
<Link href={item.href} className={cn(
  isActive && 'bg-accent text-accent-foreground'
)}>
  <Button variant={isActive ? 'secondary' : 'ghost'} size="sm" className="w-full justify-start gap-3" asChild>
    <span>
      <item.icon className="h-5 w-5" />
      {item.label}
      {item.badgeCount && <Badge variant="destructive" className="ml-auto">{item.badgeCount}</Badge>}
    </span>
  </Button>
</Link>
```

---

### 2.4 `components/layout/Header.tsx` → Minor tweaks

**Cambios**:
- Usar `Separator` entre secciones
- Usar `Button variant="ghost"` para sign-out
- Usar `Tooltip` en botones icon

---

### 2.5 `components/theme-toggle.tsx` → shadcn Switch

**Antes**: Raw `<button>` con animación absoluta de iconos

**Después** (opción A — simple):
```tsx
'use client'

import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/hooks/use-theme'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme}>
      {theme === 'dark' ? (
        <Sun className="h-5 w-5" />
      ) : (
        <Moon className="h-5 w-5" />
      )}
    </Button>
  )
}
```

---

## Fase 3: Form Components — Integración login-04

### Prioridad: 🔴 CRÍTICA — Login, Tasks, Approvals, Architect

### 3.0 Instalar y Adaptar login-04 Block

**Este bloque reemplaza COMPLETAMENTE**:
- `app/(auth)/login/page.tsx` (reemplazar)

#### Paso 1: Instalar el bloque

```bash
npx shadcn@latest add login-04
```

Esto generará:
- `components/login-form.tsx` — Formulario de login completo
- `app/login/page.tsx` — Page wrapper (adaptar a `app/(auth)/login/page.tsx`)

#### Paso 2: Adaptar `login-form.tsx` para FAP

El bloque genera un form genérico. Debe adaptarse para usar Supabase auth:

**Después** (adaptado para FAP):
```tsx
'use client'

import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, AlertCircle } from 'lucide-react'

export function LoginForm({ className, ...props }: React.ComponentPropsWithoutRef<'div'>) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { signIn } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await signIn(email, password)
      router.push('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={cn('flex flex-col gap-6', className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl text-primary">FluxAgentPro</CardTitle>
          <CardDescription>Dashboard de Orquestación de Agentes IA</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="usuario@empresa.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col">
            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {loading ? 'Iniciando sesión...' : 'Iniciar sesión'}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
```

#### Paso 3: Adaptar `app/(auth)/login/page.tsx`

```tsx
import { LoginForm } from '@/components/login-form'

export default function LoginPage() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted p-6 md:p-10">
      <div className="w-full max-w-sm md:max-w-lg">
        <LoginForm />
      </div>
    </div>
  )
}
```

**Beneficios de login-04**:
- ✅ **Card component** wrapper semántico (CardHeader, CardContent, CardFooter)
- ✅ **Label** con `htmlFor` accesible
- ✅ **Input** con focus ring y dark mode automáticos
- ✅ **Alert** component para errores (vs raw div)
- ✅ **Button** con loading spinner integrado
- ✅ **Responsive**: `max-w-sm` en mobile, `max-w-lg` en desktop
- ✅ **bg-muted** consistente con tema shadcn

---

### 3.1 `app/(app)/tasks/page.tsx` → shadcn Select + Input + Table + Pagination

**Migración por sección**:

#### Filters
**Antes**:
```tsx
<select onChange={...} className="rounded-lg border px-3 py-2 text-sm ...">
  <option value="">Todos los estados</option>
  ...
</select>
<input onChange={...} placeholder="Filtrar..." className="rounded-lg border px-3 py-2 ..." />
```

**Después**:
```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'

<Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(0) }}>
  <SelectTrigger className="w-[200px]">
    <SelectValue placeholder="Estado" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">Todos los estados</SelectItem>
    <SelectItem value="pending">Pendiente</SelectItem>
    <SelectItem value="running">Ejecutando</SelectItem>
    <SelectItem value="awaiting_approval">HITL</SelectItem>
    <SelectItem value="completed">Completado</SelectItem>
    <SelectItem value="failed">Error</SelectItem>
    <SelectItem value="rejected">Rechazado</SelectItem>
  </SelectContent>
</Select>

<Input
  value={flowFilter}
  onChange={(e) => { setFlowFilter(e.target.value); setPage(0) }}
  placeholder="Filtrar por flow_type..."
  className="w-[250px]"
/>
```

#### Table
**Antes**: Raw `<table>` con clases manuales

**Después**:
```tsx
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

<div className="rounded-lg border">
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>ID</TableHead>
        <TableHead>Flow</TableHead>
        <TableHead>Estado</TableHead>
        <TableHead>Creado</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {isLoading ? (
        <TableRow>
          <TableCell colSpan={4} className="h-24 text-center">
            <LoadingSpinner label="Cargando tareas..." />
          </TableCell>
        </TableRow>
      ) : tasks.length === 0 ? (
        <TableRow>
          <TableCell colSpan={4} className="h-24 text-center">
            <EmptyState description="No hay tareas" />
          </TableCell>
        </TableRow>
      ) : (
        tasks.map((task) => (
          <TableRow key={task.task_id} className="cursor-pointer">
            <TableCell>
              <Link href={`/tasks/${task.task_id}`} className="font-medium text-primary hover:underline">
                {task.task_id.slice(0, 12)}...
              </Link>
            </TableCell>
            <TableCell>{task.flow_type}</TableCell>
            <TableCell><StatusLabel status={task.status} /></TableCell>
            <TableCell className="text-muted-foreground">
              {formatDistanceToNow(new Date(task.created_at), { addSuffix: true, locale: es })}
            </TableCell>
          </TableRow>
        ))
      )}
    </TableBody>
  </Table>
</div>
```

#### Pagination
**Antes**: Botones manuales

**Después**:
```tsx
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'

{totalPages > 1 && (
  <div className="flex items-center justify-between">
    <p className="text-sm text-muted-foreground">
      {total} tareas en total
    </p>
    <Pagination>
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious
            href="#"
            onClick={(e) => { e.preventDefault(); setPage(Math.max(0, page - 1)) }}
            className={page === 0 ? 'pointer-events-none opacity-50' : ''}
          />
        </PaginationItem>
        <PaginationItem>
          <PaginationLink href="#">{page + 1}</PaginationLink>
        </PaginationItem>
        {totalPages > 3 && <PaginationEllipsis />}
        <PaginationItem>
          <PaginationNext
            href="#"
            onClick={(e) => { e.preventDefault(); setPage(Math.min(totalPages - 1, page + 1)) }}
            className={page >= totalPages - 1 ? 'pointer-events-none opacity-50' : ''}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  </div>
)}
```

---

### 3.3 `components/approvals/ApprovalDetail.tsx` → shadcn Textarea + Button + Card

**Antes**: Raw `<textarea>`, `<button>`, `<pre>`

**Después**:
```tsx
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { CodeBlock } from '@/components/shared/CodeBlock'

<div className="mb-4">
  <Label htmlFor="approval-notes">Notas (opcional)</Label>
  <Textarea
    id="approval-notes"
    value={notes}
    onChange={(e) => setNotes(e.target.value)}
    placeholder="Agregar notas sobre la decisión..."
    rows={2}
  />
</div>

<div className="flex gap-3">
  <Button onClick={() => onApprove(approval.task_id, notes)} disabled={isLoading} variant="default" className="bg-green-600 hover:bg-green-700">
    <CheckCircle className="mr-2 h-4 w-4" />
    Aprobar
  </Button>
  <Button onClick={() => onReject(approval.task_id, notes)} disabled={isLoading} variant="destructive">
    <XCircle className="mr-2 h-4 w-4" />
    Rechazar
  </Button>
</div>
```

---

### 3.4 `app/(app)/architect/page.tsx` → shadcn Input + Button + Card + ScrollArea

**Chat bubbles** → Usar `Card` para cada mensaje:

```tsx
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

<div className="flex-1 overflow-hidden">
  <ScrollArea className="h-full rounded-lg border p-4">
    {messages.map((msg, i) => (
      <div key={i} className={cn('mb-4 flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
        <Card className={cn('max-w-[80%]', msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted')}>
          <CardContent className="p-3">
            <pre className="whitespace-pre-wrap font-sans text-sm">{msg.content}</pre>
          </CardContent>
        </Card>
      </div>
    ))}
    <div ref={messagesEndRef} />
  </ScrollArea>
</div>

<div className="mt-4 flex gap-2">
  <Input
    value={input}
    onChange={(e) => setInput(e.target.value)}
    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
    placeholder="Describe tu workflow..."
    disabled={loading}
    className="flex-1"
  />
  <Button onClick={handleSend} disabled={loading || !input.trim()}>
    <Send className="h-4 w-4" />
  </Button>
</div>
```

---

## Fase 4: Kanban Components

### Prioridad: 🟡 MEDIA — Componentes de dominio, migración parcial

### 4.1 `components/kanban/KanbanBoard.tsx` → shadcn Tabs (mobile)

**Mobile column selector** → shadcn `Tabs`:

**Antes**: Raw `<button>` tabs con `useRef` scroll-into-view

**Después**:
```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

{/* Mobile View */}
<div className="mb-4 md:hidden">
  <Tabs value={activeColumnId} onValueChange={setActiveColumnId}>
    <TabsList className="w-full overflow-x-auto">
      {KANBAN_COLUMNS.map((col) => (
        <TabsTrigger key={col.id} value={col.id} className="gap-2">
          {col.label}
          <span className="h-5 min-w-5 rounded-full bg-white/20 px-1 text-[10px]">
            {columns[col.id]?.length || 0}
          </span>
        </TabsTrigger>
      ))}
    </TabsList>
    {KANBAN_COLUMNS.map((col) => (
      <TabsContent key={col.id} value={col.id} className="mt-4">
        <KanbanColumn ... />
      </TabsContent>
    ))}
  </Tabs>
</div>
```

### 4.2 `components/kanban/KanbanColumn.tsx` → shadcn Card + ScrollArea

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'

<Card className="h-full min-w-[300px] max-w-[350px] flex-shrink-0">
  <CardHeader className={`p-4 pb-2 ${color} rounded-t-lg`}>
    <CardTitle className={`flex items-center justify-between text-sm ${textColor}`}>
      <span>{label}</span>
      <Badge variant="outline">{tasks.length}</Badge>
    </CardTitle>
  </CardHeader>
  <CardContent className="p-2">
    <ScrollArea className="h-[calc(100vh-280px)]">
      <div className="space-y-2 pr-2">
        {tasks.map(task => <TaskCard key={task.task_id} task={task} />)}
        {tasks.length === 0 && <EmptyState className="py-8" />}
      </div>
    </ScrollArea>
  </CardContent>
</Card>
```

### 4.3 Kanban Task Detail Slide-over → shadcn Sheet

**Archivo**: `app/(app)/kanban/page.tsx`

**Antes**: `fixed inset-y-0 right-0 z-50` div manual

**Después**:
```tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'

<Sheet open={!!selectedTask} onOpenChange={(open) => !open && setSelectedTask(null)}>
  <SheetContent side="right" className="w-[400px] sm:w-[540px]">
    <SheetHeader>
      <SheetTitle>Detalle de Tarea</SheetTitle>
    </SheetHeader>
    {selectedTask && <PresentedTaskDetail task={selectedTask} />}
  </SheetContent>
</Sheet>
```

---

## Fase 5: Presentation System

### Prioridad: 🟡 MEDIA — Sistema interno, migración selectiva

### 5.1 `components/presentation/sections/AccordionSection.tsx` → shadcn Accordion

**Antes**: Manual `useState(open)` + `<button>` con chevron rotation

**Después**:
```tsx
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

export function AccordionSection({ section, data }: AccordionSectionProps) {
  const content = resolvePath(section.from, data)
  if (content === null || content === undefined) return null

  return (
    <Accordion type="single" collapsible defaultValue={section.default !== 'collapsed' ? 'item' : undefined}>
      <AccordionItem value="item" className="border-x-0">
        <AccordionTrigger className="text-sm font-semibold">
          {section.title || 'Detalle'}
        </AccordionTrigger>
        <AccordionContent>
          {typeof content === 'object' && !Array.isArray(content) ? (
            <dl className="space-y-1">
              {Object.entries(content as Record<string, unknown>).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-xs text-muted-foreground">{snakeCaseToTitle(k)}</dt>
                  <dd className="text-sm">{v === null || v === undefined ? '\u2014' : String(v)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="whitespace-pre-wrap text-sm">{String(content)}</p>
          )}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
```

### 5.2 `components/presentation/ResultKeyValueTable.tsx` → shadcn Table

**Antes**: Raw `<table>` con lógica de anidación

**Después**: Usar `Table`, `TableBody`, `TableCell`, `TableRow` de shadcn con las mismas clases semánticas.

### 5.3 `components/presentation/sections/TableSection.tsx` → shadcn Table

Mismo patrón que 5.2. Reemplazar raw `<table>` → shadcn `Table`.

### 5.4 `components/presentation/PresentedTaskCard.tsx` → shadcn Card + Badge

**Migrar contenedores raw** → `Card` de shadcn.

### 5.5 `FieldsSection`, `KeyValueListSection` → Semantic HTML + shadcn styling

Estos componentes ya usan HTML semántico (`<dl>`, `<dt>`, `<dd>`, `<ul>`, `<li>`). Solo agregar clases de shadcn para consistencia.

---

## Fase 6: Events Component

### Prioridad: 🟢 BAJA — Componente simple

### 6.1 `components/events/EventTimeline.tsx` → shadcn Card + Badge

- Contenedores de timeline items → `Card`
- Status indicators → `Badge` con variantes
- JSON payloads → `CodeBlock` shared component

---

## Fase 7: Agent & Workflow Pages

### Prioridad: 🟢 BAJA — Páginas de detalle simple

### 7.1 `app/(app)/agents/page.tsx` → shadcn Card Grid

**Antes**: Manual grid con `rounded-lg border bg-white p-4`

**Después**:
```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
  {agents.map(agent => (
    <Card key={agent.id} className="cursor-pointer hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>{agent.name}</CardTitle>
        <CardDescription>{agent.role}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <StatusLabel status={agent.status} />
          <p className="text-sm text-muted-foreground line-clamp-3">{agent.goal}</p>
          <div className="flex flex-wrap gap-1">
            {agent.tools.map(tool => (
              <Badge key={tool} variant="secondary">{tool}</Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  ))}
</div>
```

### 7.2 `app/(app)/agents/[id]/page.tsx` → shadcn Card + CodeBlock

- SOUL JSON → `CodeBlock`
- Config dl → styled con clases shadcn
- Tool tags → `Badge variant="secondary"`

### 7.3 `app/(app)/workflows/page.tsx` → shadcn Card Grid

Mismo patrón que agents.

### 7.4 `app/(app)/workflows/[id]/page.tsx` → shadcn Textarea + Button + Card

- Definition JSON → `CodeBlock`
- Trigger textarea → `Textarea`
- Execute button → `Button` con loading state

---

## Fase 8: Overview Page

### Prioridad: 🟠 ALTA — Página principal

### 8.1 `app/(app)/page.tsx` → StatCard + shadcn Card

**Ya migrado en Fase 1** (StatCard shared component).

**Cambios adicionales**:
- Recent tasks list → `Card` container
- Status badges → `StatusLabel`
- Empty state → `EmptyState`

---

## Fase 9: Notificaciones y UX Polish

### 9.1 Agregar Toast Notifications

**Configurar `Sonner`** en `app/providers.tsx`:

```tsx
import { Toaster } from '@/components/ui/sonner'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster richColors position="top-right" />
      </QueryClientProvider>
    </ThemeProvider>
  )
}
```

**Usar en**:
- `ApprovalDetail`: `toast.success('Aprobado')` / `toast.error('Rechazado')`
- `LoginPage`: `toast.error(error)` en lugar de inline error div
- `Workflows/[id]`: `toast.success('Workflow ejecutado')`
- `Architect`: `toast.error()` en catch

### 9.2 Agregar Skeleton Loading States

**Reemplazar** inline "Cargando..." text con `Skeleton`:

```tsx
import { Skeleton } from '@/components/ui/skeleton'

// Stat cards loading
<div className="grid gap-4 md:grid-cols-5">
  {Array.from({ length: 5 }).map((_, i) => (
    <Card key={i}>
      <CardContent className="p-4">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="mt-2 h-4 w-32" />
      </CardContent>
    </Card>
  ))}
</div>
```

---

## Resumen de Migración por Fases

| Fase | Componentes | Archivos Afectados | Esfuerzo | Prioridad |
|------|-------------|-------------------|----------|-----------|
| **0. Base** | Instalar shadcn CLI + 26 componentes + **dashboard-01** + **login-04** + dependencias + **Decisiones de Diseño** | package.json, globals.css | 1h | 🔴 |
| **1. Shared** | BackButton, PageHeader, CodeBlock, LoadingSpinner, EmptyState, StatusLabel | 6 archivos nuevos | 1.5h | 🔴 |
| **2. Layout** | **dashboard-01 block** → AppSidebar + SiteHeader + SectionCards + DataTable + nav-user (OrgSelector) + layout refactor + Overview refactor | Sidebar.tsx (eliminar), MobileMenu.tsx (eliminar), Header.tsx (eliminar), OrgSelector.tsx (eliminar), chart-area-interactive.tsx (eliminar), data.json (eliminar), app/(app)/layout.tsx (reemplazar), app/(app)/page.tsx (reemplazar) | 4h | 🟠 |
| **3. Forms** | **login-04 block** → LoginForm + login page refactor, Tasks table, ApprovalDetail, Architect chat | login/page.tsx (reemplazar), tasks/page, ApprovalDetail, Architect | 3h | 🔴 |
| **4. Kanban** | Tabs mobile, Sheet slide-over, ScrollArea | 3 archivos | 2h | 🟡 |
| **5. Present.** | AccordionSection, TableSection, KeyValueTable | 5 archivos | 2h | 🟡 |
| **6. Events** | EventTimeline | 1 archivo | 30 min | 🟢 |
| **7. Pages** | Agents list/detail, Workflows list/detail | 4 páginas | 2h | 🟢 |
| **8. Polish** | Toasts, Skeletons | Global | 1h | 🟡 |

**Total estimado**: ~16-18 horas de trabajo

---

## Archivo de Migración: Before → After

### Patrones Globales a Reemplazar

| Patrón Raw HTML | Reemplazo shadcn | Frecuencia |
|-----------------|------------------|------------|
| `<button className="rounded-lg bg-blue-600 ...">` | `<Button>` | ~20 |
| `<input className="rounded-lg border px-4 py-2 ...">` | `<Input>` | ~10 |
| `<textarea className="rounded-lg border ...">` | `<Textarea>` | ~4 |
| `<select className="rounded-lg border ...">` | `<Select>` | ~3 |
| `rounded-lg border bg-white p-4 dark:bg-gray-900` | `<Card>` | ~15 |
| `<pre className="bg-gray-50 p-4 text-xs">` | `<CodeBlock>` (shared) | ~5 |
| `h-8 w-8 animate-spin rounded-full border-4` | `<LoadingSpinner>` (shared) | ~8 |
| `flex items-center justify-center py-12 text-gray-400` | `<EmptyState>` (shared) | ~5 |
| `<span className="rounded-full px-2.5 py-0.5 text-xs">` | `<Badge>` | ~12 |
| `text-2xl font-bold text-gray-900` | `<PageHeader>` (shared) | ~11 |
| `<label className="mb-1 block text-sm font-medium">` | `<Label>` | ~8 |

---

## Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Breaking change en shadcn v2** | Medio | Usar versión estable actual, pin version en package.json |
| **Conflictos con CSS variables existentes** | Bajo | El tema ya es compatible, solo verificar nombres |
| **Regresiones en dark mode** | Medio | Test manual en cada fase con toggle de tema |
| **Performance degradation** | Bajo | shadcn es headless (Radix), no agrega JS runtime |
| **Bundle size increase** | Bajo | Solo se importan componentes usados (tree-shakeable) |
| **Pérdida de customizations** | Bajo | Todos los componentes shadcn son editables localmente |

---

## Checklist de Verificación Post-Migración

### Funcional
- [ ] Login funciona con Supabase auth
- [ ] OrgSelector cambia org y persiste
- [ ] Kanban muestra todas las columnas correctamente
- [ ] Task detail slide-over abre y cierra
- [ ] Approvals: approve/reject con notas funciona
- [ ] Tasks: filtros y paginación funcionan
- [ ] Architect: chat envía y recibe mensajes
- [ ] Theme toggle light/dark funciona
- [ ] Realtime updates siguen llegando

### Visual
- [ ] Dark mode consistente en todas las páginas
- [ ] Hover states en botones y links
- [ ] Focus rings accesibles (tab navigation)
- [ ] Responsive en mobile (320px+)
- [ ] Spacing consistente entre componentes
- [ ] Tipografía legible (no overlap, no overflow)

### Accesibilidad
- [ ] Tab navigation funciona en todos los forms
- [ ] ARIA labels en icon buttons
- [ ] Screen reader announce Dialog/Sheet correctamente
- [ ] Color contrast ratio > 4.5:1 en todos los textos
- [ ] Keyboard shortcuts (Escape cierra modals)

### Performance
- [ ] Lighthouse score > 90 en Performance
- [ ] Lighthouse score > 95 en Accessibility
- [ ] Bundle size no creció > 10%
- [ ] No layout shifts (CLS < 0.1)

---

## Recomendación de Orden de Ejecución

1. **Semana 1**: Fases 0-1 (base + shared components)
2. **Semana 2**: Fases 2-3 (layout + forms críticos)
3. **Semana 3**: Fases 4-5 (kanban + presentation system)
4. **Semana 4**: Fases 6-9 (resto + polish)

**Total**: 4 semanas a ritmo moderado, o 2 semanas a ritmo intenso.

---

## Notas Finales

### ¿Por qué migrar?

| Beneficio | Impacto |
|-----------|---------|
| **Accesibilidad** | ARIA, keyboard nav, screen readers automáticos |
| **Consistencia** | Mismos componentes, mismos estilos en toda la app |
| **Maintainability** | Cambiar un Button cambia en toda la app |
| **Developer Experience** | API declarativa vs raw Tailwind en cada sitio |
| **Dark mode** | Variables CSS automáticas, sin clases `dark:` manuales |
| **Mobile** | Componentes ya optimizados para touch |

### ¿Cuánto código se reduce?

| Métrica | Antes | Después | Reducción |
|---------|-------|---------|-----------|
| Clases Tailwind repetidas | ~500+ | ~200 | ~60% |
| Componentes duplicados | ~15 patrones | 7 shared | ~53% |
| Líneas de CSS custom | ~200 | ~50 | ~75% |
| Estado manual (open/close) | ~8 componentes | 0 (Radix maneja) | 100% |

### Componentes que NO deben migrarse

| Componente | Razón |
|-----------|-------|
| ~~`Sidebar.tsx`~~ | **REEMPLAZADO por dashboard-01 block** |
| ~~`MobileMenu.tsx`~~ | **ELIMINADO — dashboard-01 incluye responsive** |
| ~~`Header.tsx`~~ | **REEMPLAZADO por site-header.tsx** |
| ~~`OrgSelector.tsx`~~ | **INTEGRADO en nav-user.tsx** |
| ~~`StatCard` (inline)~~ | **REEMPLAZADO por section-cards.tsx** |
| ~~`chart-area-interactive.tsx`~~ | **ELIMINADO — sin charts en FAP** |
| `EventTimeline.tsx` | Timeline es dominio-specific |
| `KanbanBoard.tsx` | Layout logic es dominio-specific |
| `TaskCard.tsx` | Domain card con presentación custom |
| `SectionRenderer.tsx` | Router de presentación, no UI genérica |
| Todos los hooks | Capa de datos, no UI |

### Componentes REEMPLAZADOS por Bloques shadcn

| Bloque shadcn | Reemplaza | Archivos Eliminados | Archivos Nuevos |
|---------------|-----------|---------------------|-----------------|
| **dashboard-01** | Sidebar + MobileMenu + Header + OrgSelector + Layout + Overview + StatCards + DataTable | `Sidebar.tsx`, `MobileMenu.tsx`, `Header.tsx`, `OrgSelector.tsx` | `app-sidebar.tsx`, `site-header.tsx`, `section-cards.tsx`, `data-table.tsx`, `nav-main.tsx`, `nav-documents.tsx`, `nav-secondary.tsx`, `nav-user.tsx` + 10 UI components |
| **login-04** | Login form raw HTML | — (adaptar `login/page.tsx`) | `login-form.tsx` |

---

*Plan actualizado el 4 de Abril de 2026. Cambios: sidebar-03 → dashboard-01 + 4 decisiones de diseño resueltas (PageHeader, DataTable, chart, OrgSelector).*
