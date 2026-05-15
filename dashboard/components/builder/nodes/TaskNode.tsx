'use client'

import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'

import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { ClipboardList } from 'lucide-react'

const TaskNode = memo(function TaskNode({
  data,
}: NodeProps<{
  description: string
  expectedOutput: string
  assignedAgent?: string
}>) {
  return (
    <>
      <Handle type="target" position={Position.Left} className="!bg-muted-foreground" />
      <Card className="min-w-[200px] max-w-[260px] border-2 shadow-sm hover:shadow-md transition-shadow">
        <CardHeader className="pb-1 pt-3 px-3">
          <div className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-muted-foreground shrink-0" />
            <CardTitle className="text-sm font-semibold line-clamp-1">
              {data.description || 'Untitled Task'}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="px-3 pb-3 pt-0 space-y-2">
          <p className="text-xs text-muted-foreground line-clamp-1">
            {data.expectedOutput || '—'}
          </p>
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-muted-foreground">Assigned:</span>
            {data.assignedAgent ? (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                {data.assignedAgent}
              </Badge>
            ) : (
              <span className="text-[10px] text-muted-foreground">—</span>
            )}
          </div>
        </CardContent>
      </Card>
      <Handle type="source" position={Position.Right} className="!bg-muted-foreground" />
    </>
  )
})

export { TaskNode }
