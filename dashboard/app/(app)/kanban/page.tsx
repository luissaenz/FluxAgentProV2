'use client'

import { useState } from 'react'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useTasks } from '@/hooks/useTasks'
import { usePresentationConfigs } from '@/hooks/usePresentationConfig'
import { KanbanBoard } from '@/components/kanban/KanbanBoard'
import { PresentedTaskDetail } from '@/components/presentation/PresentedTaskDetail'
import { formatFlowType } from '@/lib/presentation/fallback'
import type { Task } from '@/lib/types'

export default function KanbanPage() {
  const { orgId } = useCurrentOrg()
  const { data, isLoading } = useTasks(orgId, { limit: 200 })
  const { data: configs } = usePresentationConfigs(orgId)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  return (
    <div className="flex h-[calc(100vh-theme(spacing.16)-theme(spacing.12))] flex-col space-y-4">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Kanban</h2>

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
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
      {selectedTask && (
        <div className="fixed inset-y-0 right-0 z-50 w-full border-l bg-white shadow-xl dark:bg-gray-900 dark:border-gray-800 sm:w-80 md:w-96">
          <div className="flex items-center justify-between border-b p-4 dark:border-gray-800">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Detalle de tarea</h3>
            <button
              onClick={() => setSelectedTask(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              &times;
            </button>
          </div>
          <div className="space-y-4 p-4">
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400">ID</label>
              <p className="text-sm text-gray-900 dark:text-gray-100">{selectedTask.task_id}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400">Flow</label>
              <p className="text-sm text-gray-900 dark:text-gray-100">{formatFlowType(selectedTask.flow_type)}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400">Status</label>
              <p className="text-sm text-gray-900 dark:text-gray-100">{selectedTask.status}</p>
            </div>
            {selectedTask.result && (
              <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400">Resultado</label>
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
                <label className="text-xs font-medium text-gray-500">Error</label>
                <p className="text-sm text-red-600">{selectedTask.error}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
