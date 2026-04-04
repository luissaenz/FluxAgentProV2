'use client'

import { useQuery } from '@tanstack/react-query'
import { createClient } from '@/lib/supabase'
import type { FlowPresentation, PresentationConfig } from '@/lib/presentation/types'

/**
 * Fetch all presentation configs for the current org.
 * Returns a map of flow_type -> PresentationConfig.
 */
export function usePresentationConfigs(orgId: string) {
  return useQuery<Record<string, PresentationConfig>>({
    queryKey: ['presentation-configs', orgId],
    queryFn: async () => {
      const supabase = createClient()
      const { data, error } = await supabase
        .from('flow_presentations')
        .select('*')
        .eq('org_id', orgId)

      if (error) throw error

      const map: Record<string, PresentationConfig> = {}
      for (const row of (data || []) as FlowPresentation[]) {
        map[row.flow_type] = row.presentation_config
      }
      return map
    },
    enabled: !!orgId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
