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
import { NavUser } from '@/components/nav-user'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

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
  const pathname = usePathname()

  return (
    <Sidebar variant="floating" collapsible="offcanvas" {...props}>
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
        <NavMain />
      </SidebarContent>

      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  )
}
