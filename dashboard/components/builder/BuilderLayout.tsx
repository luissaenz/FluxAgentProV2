'use client'

import { BuilderCanvas } from '@/components/builder/BuilderCanvas'
import { AgentForm } from '@/components/builder/AgentForm'

export function BuilderLayout() {
  return (
    <div className="grid h-full gap-4 lg:grid-cols-[60%_40%]">
      <div className="min-h-0">
        <BuilderCanvas />
      </div>
      <div className="flex flex-col overflow-hidden rounded-lg border bg-card p-4">
        <h3 className="mb-3 text-sm font-semibold">Agent Configuration</h3>
        <div className="flex-1 overflow-y-auto">
          <AgentForm />
        </div>
      </div>
    </div>
  )
}
