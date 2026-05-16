'use client'

import { BuilderLayout } from '@/components/builder/BuilderLayout'
import { BuilderBreadcrumb } from '@/components/builder/BuilderBreadcrumb'

export default function BuilderPage() {
  return (
    <div className="flex h-full flex-col space-y-4">
      <BuilderBreadcrumb activeTab="agent-form" />
      <h2 className="text-2xl font-bold tracking-tight">Agent Builder</h2>
      <div className="flex-1 min-h-0">
        <BuilderLayout />
      </div>
    </div>
  )
}
