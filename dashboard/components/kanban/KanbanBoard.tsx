'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
import { KANBAN_COLUMNS } from '@/lib/constants'
import { KanbanColumn } from './KanbanColumn'
import type { Task } from '@/lib/types'
import type { PresentationConfig } from '@/lib/presentation/types'
import { cn } from '@/lib/utils'

interface KanbanBoardProps {
  tasks: Task[]
  configs?: Record<string, PresentationConfig>
  onTaskClick?: (task: Task) => void
}

export function KanbanBoard({ tasks, configs, onTaskClick }: KanbanBoardProps) {
  const [activeColumnId, setActiveColumnId] = useState<string>(KANBAN_COLUMNS[0].id)
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  // Auto-scroll the active tab into view on mobile
  useEffect(() => {
    const activeTab = tabRefs.current[activeColumnId]
    if (activeTab) {
      activeTab.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      })
    }
  }, [activeColumnId])

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
    <div className="flex h-full flex-col">
      {/* Mobile column selector */}
      <div className="mb-4 flex w-full gap-2 overflow-x-auto pb-2 md:hidden">
        {KANBAN_COLUMNS.map((col) => {
          const isActive = activeColumnId === col.id
          const count = columns[col.id]?.length || 0
          return (
            <button
              key={col.id}
              ref={(el) => {
                tabRefs.current[col.id] = el
              }}
              onClick={() => setActiveColumnId(col.id)}
              className={cn(
                'flex flex-shrink-0 items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold whitespace-nowrap transition-all border',
                isActive
                  ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400'
              )}
            >
              {col.label}
              <span className={cn(
                'inline-flex h-5 min-w-5 items-center justify-center rounded-full text-[10px]',
                isActive ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500 dark:bg-slate-800'
              )}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Kanban Container */}
      <div className="flex-1 overflow-hidden">
        {/* Mobile View: Single Active Column */}
        <div className="h-full md:hidden">
          {KANBAN_COLUMNS.filter(c => c.id === activeColumnId).map((col) => (
             <KanbanColumn
              key={col.id}
              id={col.id}
              label={col.label}
              color={col.color}
              textColor={col.textColor}
              tasks={columns[col.id] || []}
              configs={configs}
              onTaskClick={onTaskClick}
              className="w-full h-full"
            />
          ))}
        </div>

        {/* Desktop View: Multi-column horizontal scroll */}
        <div className="hidden h-full gap-4 overflow-x-auto pb-4 md:flex">
          {KANBAN_COLUMNS.map((col) => (
            <KanbanColumn
              key={col.id}
              id={col.id}
              label={col.label}
              color={col.color}
              textColor={col.textColor}
              tasks={columns[col.id] || []}
              configs={configs}
              onTaskClick={onTaskClick}
              className="h-full"
            />
          ))}
        </div>
      </div>
    </div>
  )
}
