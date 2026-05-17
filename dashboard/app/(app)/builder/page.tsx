'use client'

import { BuilderLayout } from '@/components/builder/BuilderLayout'
import { BuilderBreadcrumb } from '@/components/builder/BuilderBreadcrumb'
import { BuilderTabProvider } from '@/components/builder/BuilderTabContext'

export default function BuilderPage() {
  return (
    <BuilderTabProvider defaultTab="agent-form">
      <div className="flex h-full flex-col space-y-4">
        <BuilderBreadcrumb />
        <h2 className="text-2xl font-bold tracking-tight">Agent Builder</h2>
        <div className="flex-1 min-h-0">
          <BuilderLayout />
        </div>
      </div>
    </BuilderTabProvider>
  )
}
