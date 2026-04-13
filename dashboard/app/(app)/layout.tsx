'use client'

import { AppSidebar } from '@/components/app-sidebar'
import { SiteHeader } from '@/components/site-header'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useRealtimeDashboard } from '@/hooks/useRealtimeDashboard'

import { AnalyticalAssistantChat } from '@/components/analytical/AnalyticalAssistantChat'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { orgId } = useCurrentOrg()
  useRealtimeDashboard(orgId)

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="overflow-x-hidden">
        <SiteHeader />
        <main className="flex flex-1 flex-col overflow-x-hidden">
          <div className="@container/main flex flex-1 flex-col gap-2 overflow-x-hidden">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6 px-4 lg:px-6">
              {children}
            </div>
          </div>
        </main>
      </SidebarInset>
      <AnalyticalAssistantChat />
    </SidebarProvider>
  )
}
