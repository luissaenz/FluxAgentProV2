'use client'

import { useState } from 'react'
import type { Organization } from '@/lib/types'
import { Building2, ChevronDown } from 'lucide-react'

interface OrgSelectorProps {
  orgs: Organization[]
  currentOrg: Organization | null
  onSelect: (org: Organization) => void
}

export function OrgSelector({ orgs, currentOrg, onSelect }: OrgSelectorProps) {
  const [open, setOpen] = useState(false)

  if (orgs.length <= 1) {
    return (
      <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
        <Building2 className="h-4 w-4" />
        {currentOrg?.name || 'Sin organización'}
      </div>
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:border-gray-800 dark:hover:bg-gray-800"
      >
        <Building2 className="h-4 w-4" />
        {currentOrg?.name || 'Seleccionar org'}
        <ChevronDown className="h-4 w-4" />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-lg border bg-white py-1 shadow-lg dark:bg-gray-900 dark:border-gray-800">
          {orgs.map((org) => (
            <button
              key={org.id}
              onClick={() => {
                onSelect(org)
                setOpen(false)
              }}
              className={`flex w-full items-center gap-2 px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-800 ${
                org.id === currentOrg?.id 
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' 
                  : 'text-gray-700 dark:text-gray-300'
              }`}
            >
              {org.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
