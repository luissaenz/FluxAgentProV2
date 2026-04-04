'use client'

import { useAuth } from '@/hooks/useAuth'
import { OrgSelector } from './OrgSelector'
import type { Organization } from '@/lib/types'
import { cn } from '@/lib/utils'
import { LogOut, PanelLeft } from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'

import { MobileMenu } from './MobileMenu'

interface HeaderProps {
  orgs: Organization[]
  currentOrg: Organization | null
  onSwitchOrg: (org: Organization) => void
  pendingApprovals?: number
  onToggleSidebar?: () => void
  isSidebarOpen?: boolean
}

export function Header({ 
  orgs, 
  currentOrg, 
  onSwitchOrg, 
  pendingApprovals = 0,
  onToggleSidebar,
  isSidebarOpen
}: HeaderProps) {
  const { user, signOut } = useAuth()

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 dark:bg-gray-900 dark:border-gray-800/50 md:px-6">
      <div className="flex items-center gap-2 md:gap-4">
        <div className="md:hidden">
          <MobileMenu pendingApprovals={pendingApprovals} />
        </div>

        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="hidden rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100 md:block"
            title={isSidebarOpen ? "Ocultar menú" : "Mostrar menú"}
          >
            <PanelLeft className={cn("h-5 w-5 transition-transform", !isSidebarOpen && "rotate-180")} />
          </button>
        )}
        
        <div className="hidden md:block">
          <OrgSelector
            orgs={orgs}
            currentOrg={currentOrg}
            onSelect={onSwitchOrg}
          />
        </div>
        
        <div className="md:hidden">
           <OrgSelector
            orgs={orgs}
            currentOrg={currentOrg}
            onSelect={onSwitchOrg}
          />
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        <ThemeToggle />
        <span className="hidden text-sm text-gray-500 dark:text-gray-400 sm:block">{user?.email}</span>
        <button
          onClick={signOut}
          className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 md:px-3"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden md:inline">Salir</span>
        </button>
      </div>
    </header>
  )
}
