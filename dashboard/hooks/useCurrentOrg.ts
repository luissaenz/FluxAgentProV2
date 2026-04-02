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
      .select('*, organizations(*)')
      .eq('user_id', user.id)
      .eq('is_active', true)

    if (!members?.length) {
      setLoading(false)
      return
    }

    const orgList = members
      .map((m: Record<string, unknown>) => m.organizations as Organization)
      .filter(Boolean)

    setOrgs(orgList)

    // Restore previously selected org or use first
    const savedOrgId = localStorage.getItem('selected_org_id')
    const selectedOrg = orgList.find((o) => o.id === savedOrgId) || orgList[0]

    if (selectedOrg) {
      setCurrentOrg(selectedOrg)
      localStorage.setItem('selected_org_id', selectedOrg.id)
      const member = members.find(
        (m: Record<string, unknown>) => (m.organizations as Organization)?.id === selectedOrg.id
      ) as OrgMember | undefined
      setMembership(member ?? null)
    }

    setLoading(false)
  }

  const switchOrg = useCallback((org: Organization) => {
    setCurrentOrg(org)
    localStorage.setItem('selected_org_id', org.id)
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
