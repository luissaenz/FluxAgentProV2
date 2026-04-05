'use client'

import type { Task } from '@/lib/types'
import type { PresentationConfig } from '@/lib/presentation/types'
import { STATUS_BADGES } from '@/lib/constants'
import { Badge } from '@/components/ui/badge'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { formatFlowType, extractCardSummary } from '@/lib/presentation/fallback'
import { resolvePath } from '@/lib/presentation/resolve'
import { formatValue } from '@/lib/presentation/format'

interface PresentedTaskCardProps {
  task: Task
  config?: PresentationConfig | null
  onClick?: (task: Task) => void
}

export function PresentedTaskCard({ task, config, onClick }: PresentedTaskCardProps) {
  const badge = STATUS_BADGES[task.status] || STATUS_BADGES['pending']
  const card = config?.card
  const result = task.result

  // Resolve card fields from config, fallback to defaults
  let icon: string | undefined
  let title: string
  let subtitle: string | null

  if (card && result) {
    // Icon
    if (card.icon) {
      const val = String(resolvePath(card.icon.from, result) ?? task.status)
      icon = card.icon.map[val]
    }

    // Title
    title = card.title
      ? String(resolvePath(card.title.from, result) ?? formatFlowType(task.flow_type))
      : formatFlowType(task.flow_type)

    // Amount / subtitle
    if (card.amount) {
      const raw = resolvePath(card.amount.from, result)
      subtitle = raw !== undefined ? formatValue(raw, card.amount.format) : null
    } else {
      subtitle = extractCardSummary(result)
    }
  } else {
    // Fallback (no config)
    title = formatFlowType(task.flow_type)
    subtitle = extractCardSummary(result)
  }

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
        {icon && <span className="mr-1">{icon}</span>}
        {title}
      </p>
      <p className="truncate text-xs text-gray-500 dark:text-gray-400">
        {subtitle || task.task_id.slice(0, 8) + '...'}
      </p>

      {task.error && (
        <p className="mt-2 truncate text-xs text-red-500">{task.error}</p>
      )}
    </div>
  )
}
