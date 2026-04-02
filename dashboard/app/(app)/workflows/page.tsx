'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/Badge'
import type { WorkflowTemplate } from '@/lib/types'
import Link from 'next/link'
import { Workflow } from 'lucide-react'

export default function WorkflowsPage() {
  const { orgId } = useCurrentOrg()
  const [statusFilter, setStatusFilter] = useState<string>('')

  const { data: workflows, isLoading } = useQuery<WorkflowTemplate[]>({
    queryKey: ['workflows', orgId, statusFilter],
    queryFn: async () => {
      const params = statusFilter ? `?status=${statusFilter}` : ''
      const result = await api.get(`/workflows${params}`)
      return result.workflows || result || []
    },
    enabled: !!orgId,
  })

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    archived: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Workflows</h2>
      </div>

      <div className="flex gap-2">
        {['', 'active', 'draft', 'archived'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
              statusFilter === s
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-800'
            }`}
          >
            {s || 'Todos'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : !workflows?.length ? (
        <div className="flex flex-col items-center justify-center py-12 text-gray-400 dark:text-gray-600">
          <Workflow className="mb-2 h-12 w-12" />
          <p className="text-sm">No hay workflows</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workflows.map((wf) => (
            <Link
              key={wf.id}
              href={`/workflows/${wf.id}`}
              className="rounded-lg border bg-white p-6 transition-shadow hover:shadow-md dark:bg-gray-900 dark:border-gray-800 dark:hover:shadow-lg dark:hover:shadow-black/20"
            >
              <div className="mb-2 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">{wf.name}</h3>
                <Badge className={statusColors[wf.status] || statusColors['draft']}>
                  {wf.status}
                </Badge>
              </div>
              <p className="mb-3 text-sm text-gray-600 dark:text-gray-400">{wf.description}</p>
              <div className="flex items-center gap-4 text-xs text-gray-400 dark:text-gray-500">
                <span>v{wf.version}</span>
                <span>{wf.execution_count} ejecuciones</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
