'use client'

import { Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: React.ReactNode
  title?: string
  description?: string
  className?: string
}

export function EmptyState({
  icon,
  title = 'Sin datos',
  description = 'No hay elementos para mostrar',
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center text-muted-foreground', className)}>
      {icon || <Inbox className="mb-4 h-12 w-12 opacity-50" />}
      <p className="text-sm font-medium">{title}</p>
      <p className="text-xs">{description}</p>
    </div>
  )
}
