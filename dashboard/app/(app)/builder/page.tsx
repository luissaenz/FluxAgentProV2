'use client'

import { Suspense } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { BuilderLayout } from '@/components/builder/BuilderLayout'
import { BuilderBreadcrumb } from '@/components/builder/BuilderBreadcrumb'
import { BuilderTabProvider } from '@/components/builder/BuilderTabContext'

function BuilderSkeleton() {
  return (
    <div className="flex h-full flex-col space-y-4 p-4">
      <Skeleton className="h-4 w-48" />
      <Skeleton className="h-8 w-64" />
      <div className="flex-1 rounded-lg border">
        <Skeleton className="h-full w-full" />
      </div>
    </div>
  )
}

function BuilderContent() {
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

export default function BuilderPage() {
  return (
    <Suspense fallback={<BuilderSkeleton />}>
      <BuilderContent />
    </Suspense>
  )
}
