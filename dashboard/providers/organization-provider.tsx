'use client'

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { createClient } from '@/lib/supabase'
import type { Organization, OrgMember } from '@/lib/types'
import { useQuery } from '@tanstack/react-query'

interface OrganizationContextType {
  orgs: Organization[]
  currentOrg: Organization | null
  membership: OrgMember | null
  loading: boolean
  orgId: string
  switchOrg: (org: Organization) => void
  refresh: () => Promise<void>
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined)

export function OrganizationProvider({ children }: { children: React.ReactNode }) {
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null)
  
  // Usamos React Query para centralizar la carga de datos de la sesión y orgs
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['session-orgs'],
    queryFn: async () => {
      const supabase = createClient()
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return { orgs: [], members: [] }

      // Obtener membresías
      const { data: members } = await supabase
        .from('org_members')
        .select('*')
        .eq('user_id', user.id)
        .eq('is_active', true)

      if (!members?.length) return { orgs: [], members: [] }

      // Obtener organizaciones
      const { data: allOrgs } = await supabase
        .from('organizations')
        .select('*')

      const orgMap = new Map((allOrgs || []).map((o: Organization) => [o.id, o]))
      const orgList = members
        .map((m) => orgMap.get(m.org_id))
        .filter(Boolean) as Organization[]

      return { orgs: orgList, members }
    },
    staleTime: 1000 * 60 * 5, // 5 minutos de cache
  })

  useEffect(() => {
    if (data?.orgs.length && !selectedOrgId) {
      const savedId = localStorage.getItem('organization_id') || localStorage.getItem('selected_org_id')
      const initialOrg = data.orgs.find(o => o.id === savedId) || data.orgs[0]
      setSelectedOrgId(initialOrg.id)
      localStorage.setItem('organization_id', initialOrg.id)
    }
  }, [data, selectedOrgId])

  const switchOrg = useCallback((org: Organization) => {
    setSelectedOrgId(org.id)
    localStorage.setItem('organization_id', org.id)
  }, [])

  const currentOrg = data?.orgs.find(o => o.id === selectedOrgId) || null
  const membership = data?.members.find(m => m.org_id === selectedOrgId) || null

  const value = {
    orgs: data?.orgs || [],
    currentOrg,
    membership: membership || null,
    loading: isLoading,
    orgId: selectedOrgId || '',
    switchOrg,
    refresh: async () => { await refetch() }
  }

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  )
}

export function useOrganization() {
  const context = useContext(OrganizationContext)
  if (context === undefined) {
    throw new Error('useOrganization must be used within an OrganizationProvider')
  }
  return context
}
