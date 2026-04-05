'use client'

import type { Task } from '@/lib/types'
import type { PresentationConfig } from '@/lib/presentation/types'
import { PresentedTaskCard } from '@/components/presentation/PresentedTaskCard'
import { cn } from '@/lib/utils'

interface KanbanColumnProps {
  id: string
  label: string
  color: string
  textColor: string
  tasks: Task[]
  configs?: Record<string, PresentationConfig>
  onTaskClick?: (task: Task) => void
  className?: string
}

export function KanbanColumn({
  label,
  color,
  textColor,
  tasks,
  configs,
  onTaskClick,
  className,
}: KanbanColumnProps) {
  return (
    <div className={cn('flex w-full flex-shrink-0 flex-col rounded-2xl border bg-muted/30 backdrop-blur-sm transition-colors md:w-72', className)}>
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2">
          <div className={cn('h-2 w-2 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.1)]', color)} />
          <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">{label}</h3>
        </div>
        <span
          className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-background/50 text-[10px] font-bold text-muted-foreground shadow-sm ring-1 ring-border"
        >
          {tasks.length}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-3">
        {tasks.length === 0 ? (
          <p className="py-8 text-center text-xs text-gray-400 dark:text-gray-500">Sin tareas</p>
        ) : (
          tasks.map((task) => (
            <PresentedTaskCard
              key={task.task_id}
              task={task}
              config={configs?.[task.flow_type]}
              onClick={onTaskClick}
            />
          ))
        )}
      </div>
    </div>
  )
}
