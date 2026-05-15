'use client'

import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useApprovals } from '@/hooks/useApprovals'
import { useRealtimeDashboard } from '@/hooks/useRealtimeDashboard'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { orgs, currentOrg, switchOrg, orgId } = useCurrentOrg()
  const { data: approvals } = useApprovals(orgId)

  // Subscribe to realtime updates
  useRealtimeDashboard(orgId)

  const pendingCount = approvals?.filter((a) => a.status === 'pending').length || 0

  return (
    <div className="flex h-screen">
      <Sidebar pendingApprovals={pendingCount} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          orgs={orgs}
          currentOrg={currentOrg}
          onSwitchOrg={switchOrg}
        />
        <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
