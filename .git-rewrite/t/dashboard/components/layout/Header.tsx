'use client'

import { useAuth } from '@/hooks/useAuth'
import { OrgSelector } from './OrgSelector'
import type { Organization } from '@/lib/types'
import { LogOut } from 'lucide-react'

interface HeaderProps {
  orgs: Organization[]
  currentOrg: Organization | null
  onSwitchOrg: (org: Organization) => void
}

export function Header({ orgs, currentOrg, onSwitchOrg }: HeaderProps) {
  const { user, signOut } = useAuth()

  return (
    <header className="flex h-16 items-center justify-between border-b bg-white px-6">
      <div className="flex items-center gap-4">
        <OrgSelector
          orgs={orgs}
          currentOrg={currentOrg}
          onSelect={onSwitchOrg}
        />
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-500">{user?.email}</span>
        <button
          onClick={signOut}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100"
        >
          <LogOut className="h-4 w-4" />
          Salir
        </button>
      </div>
    </header>
  )
}
