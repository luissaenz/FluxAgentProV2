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
  Ticket,
  type LucideIcon,
} from 'lucide-react'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useApprovals } from '@/hooks/useApprovals'

interface NavItem {
  title: string
  url: string
  icon: LucideIcon
}

interface NavMainProps {
  items?: NavItem[]
}

const defaultNavItems: NavItem[] = [
  { title: 'Overview', url: '/', icon: LayoutDashboard },
  { title: 'Kanban', url: '/kanban', icon: Columns3 },
  { title: 'Aprobaciones', url: '/approvals', icon: ShieldCheck },
  { title: 'Historial', url: '/tasks', icon: History },
  { title: 'Tickets', url: '/tickets', icon: Ticket },
  { title: 'Agentes', url: '/agents', icon: Bot },
  { title: 'Workflows', url: '/workflows', icon: Workflow },
  { title: 'Eventos', url: '/events', icon: Activity },
  { title: 'Chat MDC', url: '/architect', icon: MessageSquare },
]

export function NavMain({ items }: NavMainProps) {
  const pathname = usePathname()
  const { orgId } = useCurrentOrg()
  const { data: approvals } = useApprovals(orgId)
  const pendingCount = approvals?.filter((a) => a.status === 'pending').length || 0
  const navItems = items ?? defaultNavItems

  return (
    <SidebarGroup className="px-2 py-0">
      <SidebarGroupLabel>Navegación</SidebarGroupLabel>
      <SidebarMenu>
        {navItems.map((item) => {
          const isActive =
            item.url === '/'
              ? pathname === '/'
              : pathname.startsWith(item.url)
          return (
            <SidebarMenuItem key={item.url}>
              <SidebarMenuButton asChild isActive={isActive}>
                <Link href={item.url}>
                  <item.icon className="h-4 w-4" />
                  <span>{item.title}</span>
                  {item.url === '/approvals' && pendingCount > 0 && (
                    <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500 px-1.5 text-[10px] font-medium text-white">
                      {pendingCount}
                    </span>
                  )}
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )
        })}
      </SidebarMenu>
    </SidebarGroup>
  )
}
