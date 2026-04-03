'use client'

import { useState } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useApprovals } from '@/hooks/useApprovals'
import { useRealtimeDashboard } from '@/hooks/useRealtimeDashboard'
import { cn } from '@/lib/utils'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { orgs, currentOrg, switchOrg, orgId } = useCurrentOrg()
  const { data: approvals } = useApprovals(orgId)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  // Subscribe to realtime updates
  useRealtimeDashboard(orgId)

  const pendingCount = approvals?.filter((a) => a.status === 'pending').length || 0

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 overflow-hidden">
      {/* Desktop Sidebar */}
      <div 
        className={cn(
          "hidden h-screen flex-shrink-0 border-r border-gray-100 bg-white dark:bg-gray-900 dark:border-gray-800/20 transition-all duration-300 md:block",
          isSidebarOpen ? "w-64" : "w-0 overflow-hidden border-none"
        )}
      >
        <Sidebar pendingApprovals={pendingCount} />
      </div>

      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          orgs={orgs}
          currentOrg={currentOrg}
          onSwitchOrg={switchOrg}
          pendingApprovals={pendingCount}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          isSidebarOpen={isSidebarOpen}
        />
        <main className="flex-1 overflow-y-auto bg-gray-50 p-4 dark:bg-gray-950 md:p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
