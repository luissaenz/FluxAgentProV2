'use client'

import type { Task } from '@/lib/types'
import { TaskCard } from './TaskCard'
import { cn } from '@/lib/utils'

interface KanbanColumnProps {
  id: string
  label: string
  color: string
  textColor: string
  tasks: Task[]
  onTaskClick?: (task: Task) => void
}

export function KanbanColumn({
  label,
  color,
  textColor,
  tasks,
  onTaskClick,
}: KanbanColumnProps) {
  return (
    <div className="flex w-72 flex-shrink-0 flex-col rounded-lg bg-gray-50 dark:bg-gray-900/50">
      <div className={cn('flex items-center justify-between rounded-t-lg px-4 py-3', color)}>
        <h3 className={cn('text-sm font-semibold', textColor)}>{label}</h3>
        <span
          className={cn(
            'inline-flex h-6 min-w-6 items-center justify-center rounded-full text-xs font-medium',
            color,
            textColor
          )}
        >
          {tasks.length}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-2">
        {tasks.length === 0 ? (
          <p className="py-8 text-center text-xs text-gray-400 dark:text-gray-500">Sin tareas</p>
        ) : (
          tasks.map((task) => (
            <TaskCard key={task.task_id} task={task} onClick={onTaskClick} />
          ))
        )}
      </div>
    </div>
  )
}
