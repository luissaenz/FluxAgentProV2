'use client'

import { useOrganization } from '../providers/organization-provider'

export function useCurrentOrg() {
  return useOrganization()
}
