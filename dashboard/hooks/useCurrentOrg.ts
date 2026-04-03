'use client'

import { useEffect, useState, useCallback } from 'react'
import { createClient } from '@/lib/supabase'
import type { Organization, OrgMember } from '@/lib/types'

export function useCurrentOrg() {
  const [orgs, setOrgs] = useState<Organization[]>([])
  const [currentOrg, setCurrentOrg] = useState<Organization | null>(null)
  const [membership, setMembership] = useState<OrgMember | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadOrgs()
  }, [])

  const loadOrgs = async () => {
    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    // Get user's org memberships
    const { data: members } = await supabase
      .from('org_members')
      .select('*')
      .eq('user_id', user.id)
      .eq('is_active', true)

    if (!members?.length) {
      setLoading(false)
      return
    }

    // Fetch organizations separately since RLS might block the join
    const { data: allOrgs } = await supabase
      .from('organizations')
      .select('*')

    const orgMap = new Map((allOrgs || []).map((o: Organization) => [o.id, o]))

    // Build org list from members + org data
    const orgList = members
      .map((m: Record<string, unknown>) => orgMap.get(m.org_id as string))
      .filter(Boolean) as Organization[]

    setOrgs(orgList)

    // Restore previously selected org or use first
    const savedOrgId = localStorage.getItem('organization_id') || localStorage.getItem('selected_org_id')
    const selectedOrg = orgList.find((o) => o.id === savedOrgId) || orgList[0]

    if (selectedOrg) {
      setCurrentOrg(selectedOrg)
      localStorage.setItem('organization_id', selectedOrg.id)
      const member = members.find(
        (m: Record<string, unknown>) => m.org_id === selectedOrg.id
      ) as OrgMember | undefined
      setMembership(member ?? null)
    }

    setLoading(false)
  }

  const switchOrg = useCallback((org: Organization) => {
    setCurrentOrg(org)
    localStorage.setItem('organization_id', org.id)
    // Membership will update on next loadOrgs or can be looked up
  }, [])

  return {
    orgs,
    currentOrg,
    membership,
    loading,
    switchOrg,
    orgId: currentOrg?.id || '',
  }
}
