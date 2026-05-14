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
  Puzzle,
  Wand2,
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
  items?: {
    title: string
    url: string
  }[]
}

interface NavMainProps {
  items?: NavItem[]
}

export const defaultNavItems: NavItem[] = [
  { title: 'Overview', url: '/', icon: LayoutDashboard },
  { title: 'Kanban', url: '/kanban', icon: Columns3 },
  { title: 'Aprobaciones', url: '/approvals', icon: ShieldCheck },
  { title: 'Historial', url: '/tasks', icon: History },
  { title: 'Tickets', url: '/tickets', icon: Ticket },
  { title: 'Agentes', url: '/agents', icon: Bot },
  { title: 'Builder', url: '/builder', icon: Wand2 },
  { title: 'Workflows', url: '/workflows', icon: Workflow },
  { title: 'Eventos', url: '/events', icon: Activity },
  { 
    title: 'Integraciones', 
    url: '/integrations', 
    icon: Puzzle,
    items: [
      { title: 'Catálogo', url: '/integrations' },
      { title: 'Bundles (Wizard)', url: '/integrations/bundles' },
      { title: 'Historial Bundles', url: '/integrations/bundles/history' },
    ]
  },
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
          const isParentActive =
            item.url === '/'
              ? pathname === '/'
              : pathname.startsWith(item.url)
          
          return (
            <SidebarMenuItem key={item.url}>
              <SidebarMenuButton asChild isActive={isParentActive}>
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
              {item.items && item.items.length > 0 && isParentActive && (
                <div className="ml-6 mt-1 flex flex-col gap-1 border-l pl-2">
                  {item.items.map((subItem) => {
                    const isSubActive = pathname === subItem.url
                    return (
                      <Link
                        key={subItem.url}
                        href={subItem.url}
                        className={`text-xs py-1 px-2 rounded-md transition-colors ${
                          isSubActive 
                            ? 'bg-secondary text-secondary-foreground font-medium' 
                            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                        }`}
                      >
                        {subItem.title}
                      </Link>
                    )
                  })}
                </div>
              )}
            </SidebarMenuItem>
          )
        })}
      </SidebarMenu>
    </SidebarGroup>
  )
}
