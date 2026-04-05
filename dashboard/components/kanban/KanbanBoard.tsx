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
  const tabsContainerRef = useRef<HTMLDivElement>(null)
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  // Smooth scroll the active tab into center of the container (not the viewport)
  useEffect(() => {
    const container = tabsContainerRef.current
    const activeTab = tabRefs.current[activeColumnId]
    
    if (container && activeTab) {
      // Calculate the displacement to center the tab
      const containerHalfWidth = container.clientWidth / 2
      const tabHalfWidth = activeTab.clientWidth / 2
      const tabOffsetLeft = activeTab.offsetLeft
      
      const scrollValue = tabOffsetLeft - containerHalfWidth + tabHalfWidth
      
      container.scrollTo({
        left: scrollValue,
        behavior: 'smooth',
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
    <div className="flex h-full flex-col max-w-full overflow-x-hidden">
      {/* Mobile column selector */}
      <div 
        ref={tabsContainerRef}
        className="mb-4 flex w-full gap-2 overflow-x-auto px-4 pb-4 md:hidden scrollbar-hide no-scrollbar [-ms-overflow-style:none] [scrollbar-width:none]"
      >
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
                'flex flex-shrink-0 items-center justify-center gap-2 rounded-full px-5 py-2.5 text-[11px] font-bold uppercase tracking-widest transition-all border',
                isActive
                  ? 'border-primary bg-primary text-primary-foreground shadow-lg shadow-primary/20 scale-100'
                  : 'border-border bg-card text-muted-foreground/60 hover:border-muted-foreground/30'
              )}
            >
              {col.label}
              <span className={cn(
                'inline-flex h-5 min-w-5 items-center justify-center rounded-full text-[10px] font-bold',
                isActive ? 'bg-black/20 text-white' : 'bg-muted-foreground/5 text-muted-foreground/40'
              )}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Kanban Container */}
      <div className="flex-1 overflow-x-hidden max-w-full">
        {/* Mobile View: Single Active Column */}
        <div className="mx-auto flex h-full w-full justify-center md:hidden">
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
              className="w-full h-full max-w-[92vw]"
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
