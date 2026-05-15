'use client'

import { useMemo } from 'react'
import { KANBAN_COLUMNS } from '@/lib/constants'
import { KanbanColumn } from './KanbanColumn'
import type { Task } from '@/lib/types'

interface KanbanBoardProps {
  tasks: Task[]
  onTaskClick?: (task: Task) => void
}

export function KanbanBoard({ tasks, onTaskClick }: KanbanBoardProps) {
  const columns = useMemo(() => {
    const grouped: Record<string, Task[]> = {}
    for (const col of KANBAN_COLUMNS) {
      grouped[col.id] = []
    }
    for (const task of tasks) {
      const key = task.status in grouped ? task.status : 'pending'
      grouped[key].push(task)
    }
    return grouped
  }, [tasks])

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {KANBAN_COLUMNS.map((col) => (
        <KanbanColumn
          key={col.id}
          id={col.id}
          label={col.label}
          color={col.color}
          textColor={col.textColor}
          tasks={columns[col.id] || []}
          onTaskClick={onTaskClick}
        />
      ))}
    </div>
  )
}
