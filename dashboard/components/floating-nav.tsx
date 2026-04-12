'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Grid, PanelLeft } from 'lucide-react'
import { useSidebar } from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { defaultNavItems } from '@/components/nav-main'
import { cn } from '@/lib/utils'

export function FloatingNav() {
  const { state, isMobile, toggleSidebar } = useSidebar()
  const pathname = usePathname()

  // Si está expandido en desktop, mostramos el trigger normal que colapsa
  if (state === 'expanded' && !isMobile) {
    return (
      <Button 
        variant="ghost" 
        size="icon" 
        className="h-8 w-8 -ml-1" 
        onClick={toggleSidebar}
      >
        <PanelLeft className="h-4 w-4" />
        <span className="sr-only">Colapsar Sidebar</span>
      </Button>
    )
  }

  // Si está colapsado (u oculto en móvil), mostramos el menú flotante
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          size="icon" 
          className="h-8 w-8 -ml-1 hover:bg-sidebar-accent group relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <Grid className="h-4 w-4 transition-transform group-hover:scale-110" />
          <span className="sr-only">Menú Flotante</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent 
        align="start" 
        sideOffset={8}
        className="w-56 overflow-hidden rounded-2xl border-sidebar-border bg-sidebar/95 p-2 shadow-2xl backdrop-blur-xl animate-in fade-in-0 zoom-in-95 data-[side=bottom]:slide-in-from-top-2"
      >
        <DropdownMenuLabel className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-sidebar-foreground/50">
          Explorar
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="mb-1 opacity-20" />
        <div className="grid gap-1">
          {defaultNavItems.map((item) => {
            const isActive =
              item.url === '/'
                ? pathname === '/'
                : pathname.startsWith(item.url)
            
            return (
              <DropdownMenuItem 
                key={item.url} 
                asChild 
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-xl px-2.5 py-2 text-sm transition-all active:scale-95",
                  isActive 
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" 
                    : "hover:bg-sidebar-accent text-sidebar-foreground/80 hover:text-sidebar-foreground"
                )}
              >
                <Link href={item.url}>
                  <div className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
                    isActive ? "bg-white/20" : "bg-sidebar-accent group-hover:bg-sidebar-accent/50"
                  )}>
                    <item.icon className="h-4 w-4" />
                  </div>
                  <span className="font-medium">{item.title}</span>
                  {isActive && (
                    <div className="ml-auto h-1.5 w-1.5 rounded-full bg-white shadow-[0_0_8px_white]" />
                  )}
                </Link>
              </DropdownMenuItem>
            )
          })}
        </div>
        
        <DropdownMenuSeparator className="my-2 opacity-20" />
        
        <DropdownMenuItem 
          onClick={toggleSidebar}
          className="flex cursor-pointer items-center gap-3 rounded-xl px-2.5 py-2 text-xs text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-all"
        >
          <PanelLeft className="h-4 w-4" />
          <span>Expandir Sidebar Completa</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
