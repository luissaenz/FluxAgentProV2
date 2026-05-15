'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
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

const navItems = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/kanban', label: 'Kanban', icon: Columns3 },
  { href: '/approvals', label: 'Aprobaciones', icon: ShieldCheck },
  { href: '/tasks', label: 'Historial', icon: History },
  { href: '/agents', label: 'Agentes', icon: Bot },
  { href: '/workflows', label: 'Workflows', icon: Workflow },
  { href: '/events', label: 'Eventos', icon: Activity },
  { href: '/architect', label: 'Chat MDC', icon: MessageSquare },
]

interface SidebarProps {
  pendingApprovals?: number
}

export function Sidebar({ pendingApprovals = 0 }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-white">
      <div className="flex h-16 items-center border-b px-6">
        <h1 className="text-lg font-bold text-blue-600">FluxAgentPro</h1>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive =
            item.href === '/'
              ? pathname === '/'
              : pathname.startsWith(item.href)
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
              {item.href === '/approvals' && pendingApprovals > 0 && (
                <span className="ml-auto inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500 px-1.5 text-xs font-medium text-white">
                  {pendingApprovals}
                </span>
              )}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
