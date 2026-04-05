'use client'

import { useState } from 'react'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useTasks } from '@/hooks/useTasks'
import { usePresentationConfigs } from '@/hooks/usePresentationConfig'
import { KanbanBoard } from '@/components/kanban/KanbanBoard'
import { PresentedTaskDetail } from '@/components/presentation/PresentedTaskDetail'
import { formatFlowType } from '@/lib/presentation/fallback'
import type { Task } from '@/lib/types'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'

export default function KanbanPage() {
  const { orgId } = useCurrentOrg()
  const { data, isLoading } = useTasks(orgId, { limit: 200 })
  const { data: configs } = usePresentationConfigs(orgId)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col space-y-4">
      <h2 className="text-2xl font-bold tracking-tight">Kanban</h2>

      {isLoading ? (
        <LoadingSpinner label="Cargando kanban..." />
      ) : (
        <div className="flex-1 overflow-hidden">
          <KanbanBoard
            tasks={data?.items || []}
            configs={configs}
            onTaskClick={setSelectedTask}
          />
        </div>
      )}

      {/* Task detail slide-over */}
      <Sheet open={!!selectedTask} onOpenChange={(open) => !open && setSelectedTask(null)}>
        <SheetContent side="right" className="w-[400px] sm:w-[540px]">
          <SheetHeader>
            <SheetTitle>Detalle de Tarea</SheetTitle>
            <SheetDescription>
              {selectedTask && formatFlowType(selectedTask.flow_type)}
            </SheetDescription>
          </SheetHeader>
          {selectedTask && (
            <div className="mt-6 space-y-4">
              <div className="space-y-2">
                <div>
                  <label className="text-xs font-medium text-muted-foreground">ID</label>
                  <p className="text-sm font-mono">{selectedTask.task_id}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Flow</label>
                  <p className="text-sm">{formatFlowType(selectedTask.flow_type)}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Estado</label>
                  <p className="text-sm">{selectedTask.status}</p>
                </div>
                {selectedTask.result && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Resultado</label>
                    <div className="mt-1">
                      <PresentedTaskDetail
                        result={selectedTask.result}
                        config={configs?.[selectedTask.flow_type]}
                      />
                    </div>
                  </div>
                )}
                {selectedTask.error && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Error</label>
                    <p className="text-sm text-destructive">{selectedTask.error}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
