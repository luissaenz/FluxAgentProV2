'use client'

import { useState } from 'react'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useTasks } from '@/hooks/useTasks'
import { KanbanBoard } from '@/components/kanban/KanbanBoard'
import type { Task } from '@/lib/types'

export default function KanbanPage() {
  const { orgId } = useCurrentOrg()
  const { data, isLoading } = useTasks(orgId, { limit: 200 })
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Kanban</h2>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : (
        <KanbanBoard
          tasks={data?.items || []}
          onTaskClick={setSelectedTask}
        />
      )}

      {/* Task detail slide-over */}
      {selectedTask && (
        <div className="fixed inset-y-0 right-0 z-50 w-96 border-l bg-white shadow-xl dark:bg-gray-900 dark:border-gray-800">
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
              <p className="text-sm text-gray-900 dark:text-gray-100">{selectedTask.flow_type}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400">Status</label>
              <p className="text-sm text-gray-900 dark:text-gray-100">{selectedTask.status}</p>
            </div>
            {selectedTask.result && (
              <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400">Resultado</label>
                <pre className="mt-1 overflow-x-auto rounded bg-gray-50 p-2 text-xs dark:bg-gray-950 dark:text-gray-300">
                  {JSON.stringify(selectedTask.result, null, 2)}
                </pre>
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
