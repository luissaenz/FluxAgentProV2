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
  X,
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
  onClose?: () => void
}

export function Sidebar({ pendingApprovals = 0, onClose }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside className="flex h-full w-full flex-col bg-white dark:bg-gray-900">
      <div className="flex h-16 items-center justify-between border-b px-6 dark:border-gray-800">
        <h1 className="text-lg font-bold text-blue-600">FluxAgentPro V2</h1>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100 md:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        )}
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
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100'
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
