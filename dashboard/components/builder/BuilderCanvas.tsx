'use client'

import dynamic from 'next/dynamic'
import { Skeleton } from '@/components/ui/skeleton'

const CrewCanvasDynamic = dynamic(
  () => import('@/components/builder/CrewCanvas').then((mod) => ({ default: mod.CrewCanvas })),
  { ssr: false, loading: () => <Skeleton className="h-64 w-full rounded-lg" /> },
)

export function BuilderCanvas() {
  return (
    <div className="h-full w-full rounded-lg border bg-muted/20">
      <CrewCanvasDynamic />
    </div>
  )
}
