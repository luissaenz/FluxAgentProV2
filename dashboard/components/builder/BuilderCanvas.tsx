'use client'

import dynamic from 'next/dynamic'
import { Skeleton } from '@/components/ui/skeleton'

const ReactFlowContainer = dynamic(
  () =>
    import('reactflow').then((mod) => {
      const { default: ReactFlow, Background, Controls, MiniMap } = mod
      return function FlowCanvas() {
        return (
          <div className="h-full w-full">
            <ReactFlow nodes={[]} edges={[]} fitView>
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
        )
      }
    }),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center">
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    ),
  }
)

import 'reactflow/dist/style.css'

export function BuilderCanvas() {
  return (
    <div className="flex h-full w-full flex-col rounded-lg border bg-muted/20">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <span className="text-sm font-medium">Agent Builder Canvas</span>
        <span className="text-xs text-muted-foreground">Placeholder for Step 07</span>
      </div>
      <div className="flex-1">
        <ReactFlowContainer />
      </div>
    </div>
  )
}
