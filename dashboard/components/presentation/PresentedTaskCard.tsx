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
import { cn } from '@/lib/utils'

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
      className="cursor-pointer rounded-xl border bg-card p-4 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 active:scale-[0.98] dark:bg-card/50 dark:backdrop-blur-sm dark:border-white/5 dark:hover:bg-card/80"
    >
      <div className="mb-3 flex items-center justify-between">
        <Badge variant={badge.variant} className="px-2 py-0 text-[10px] font-bold uppercase tracking-wider">
          {badge.label}
        </Badge>
        <span className="text-[10px] font-medium text-muted-foreground">
          {formatDistanceToNow(new Date(task.created_at), {
            addSuffix: true,
            locale: es,
          })}
        </span>
      </div>

      <p className="mb-1 text-sm font-semibold text-foreground line-clamp-1">
        {icon && <span className="mr-1.5">{icon}</span>}
        {title}
      </p>
      <p className="truncate text-xs text-muted-foreground">
        {subtitle || task.task_id.slice(0, 8) + '...'}
      </p>

      {task.error && (
        <p className="mt-2 truncate text-xs text-red-500">{task.error}</p>
      )}
    </div>
  )
}
