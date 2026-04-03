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
  className?: string
}

export function KanbanColumn({
  label,
  color,
  textColor,
  tasks,
  onTaskClick,
  className,
}: KanbanColumnProps) {
  return (
    <div className={cn('flex w-full flex-shrink-0 flex-col rounded-xl border border-transparent bg-gray-50 dark:bg-gray-900/40 dark:border-gray-800/50 md:w-72', className)}>
      {/* Header with color indicator at the top */}
      <div className={cn('hidden h-1 items-center rounded-t-xl md:flex', color)} />

      <div className="hidden items-center justify-between bg-slate-100/30 px-4 py-3 dark:bg-gray-800/20 md:flex">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</h3>
        <span
          className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-slate-200/50 text-[10px] font-bold text-slate-600 dark:bg-slate-700/50 dark:text-slate-400"
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
