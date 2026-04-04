'use client'

import type { Task } from '@/lib/types'
import { STATUS_BADGES } from '@/lib/constants'
import { Badge } from '@/components/ui/Badge'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { formatFlowType, extractCardSummary } from '@/lib/presentation/fallback'

interface TaskCardProps {
  task: Task
  onClick?: (task: Task) => void
}

export function TaskCard({ task, onClick }: TaskCardProps) {
  const badge = STATUS_BADGES[task.status] || STATUS_BADGES['pending']

  return (
    <div
      onClick={() => onClick?.(task)}
      className="cursor-pointer rounded-lg border bg-white p-3 shadow-sm transition-shadow hover:shadow-md dark:bg-gray-800 dark:border-gray-700 dark:hover:shadow-lg dark:hover:shadow-black/20"
    >
      <div className="mb-2 flex items-center justify-between">
        <Badge className={badge.className}>{badge.label}</Badge>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {formatDistanceToNow(new Date(task.created_at), {
            addSuffix: true,
            locale: es,
          })}
        </span>
      </div>

      <p className="mb-1 text-sm font-medium text-gray-900 dark:text-gray-100">
        {formatFlowType(task.flow_type)}
      </p>
      <p className="truncate text-xs text-gray-500 dark:text-gray-400">
        {extractCardSummary(task.result) || task.task_id.slice(0, 8) + '...'}
      </p>

      {task.error && (
        <p className="mt-2 truncate text-xs text-red-500">{task.error}</p>
      )}
    </div>
  )
}
