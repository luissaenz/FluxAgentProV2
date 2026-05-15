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
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Bot } from 'lucide-react'

const MAX_VISIBLE_TOOLS = 3

const AgentNode = memo(function AgentNode({
  data,
}: NodeProps<{
  role: string
  goal: string
  tools: string[]
  model?: string
}>) {
  const visibleTools = data.tools.slice(0, MAX_VISIBLE_TOOLS)
  const remainingCount = data.tools.length - MAX_VISIBLE_TOOLS
  const tooltipTools = data.tools.join(', ') || 'No tools assigned'

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground" />
      <Tooltip>
        <TooltipTrigger asChild>
          <Card className="min-w-[200px] max-w-[260px] border-2 shadow-sm hover:shadow-md transition-shadow cursor-grab active:cursor-grabbing">
            <CardHeader className="pb-1 pt-3 px-3">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-muted-foreground shrink-0" />
                <CardTitle className="text-sm font-semibold truncate">
                  {data.role}
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="px-3 pb-3 pt-0 space-y-2">
              <p className="text-xs text-muted-foreground line-clamp-2">
                {data.goal || 'No goal defined'}
              </p>
              {visibleTools.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {visibleTools.map((tool) => (
                    <Badge key={tool} variant="secondary" className="text-[10px] px-1.5 py-0">
                      {tool}
                    </Badge>
                  ))}
                  {remainingCount > 0 && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      +{remainingCount}
                    </Badge>
                  )}
                </div>
              )}
              {data.model && (
                <p className="text-[10px] text-muted-foreground">
                  {data.model}
                </p>
              )}
            </CardContent>
          </Card>
        </TooltipTrigger>
        <TooltipContent side="right" className="max-w-[280px]">
          <div className="space-y-1">
            <p className="font-semibold">{data.role}</p>
            <p className="text-[10px] opacity-80">{data.goal}</p>
            <p className="text-[10px] opacity-60">Tools: {tooltipTools}</p>
          </div>
        </TooltipContent>
      </Tooltip>
      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground" />
    </>
  )
})

export { AgentNode }
