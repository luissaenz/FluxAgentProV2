'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'
import { ArrowLeft, Play } from 'lucide-react'

export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { orgId } = useCurrentOrg()
  const [inputJson, setInputJson] = useState('{}')
  const [triggerResult, setTriggerResult] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)

  const { data: workflow, isLoading } = useQuery({
    queryKey: ['workflow', id],
    queryFn: async () => {
      const workflows = await api.get('/workflows')
      const list = workflows.workflows || workflows || []
      return list.find((w: Record<string, string>) => w.id === id) || null
    },
    enabled: !!id,
  })

  const handleTrigger = async () => {
    if (!workflow?.flow_type) return
    setTriggering(true)
    setTriggerResult(null)
    try {
      const input = JSON.parse(inputJson)
      const result = await api.post('/webhooks/trigger', {
        flow_type: workflow.flow_type,
        input_data: input,
      })
      setTriggerResult(`Task aceptada: ${result.correlation_id}`)
    } catch (err) {
      setTriggerResult(`Error: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setTriggering(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!workflow) {
    return <p className="py-12 text-center text-gray-500">Workflow no encontrado</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/workflows" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h2 className="text-2xl font-bold text-gray-900">{workflow.name}</h2>
        <Badge
          className={
            workflow.status === 'active'
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-500'
          }
        >
          {workflow.status}
        </Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Definition */}
        <div className="rounded-lg border bg-white p-6">
          <h3 className="mb-4 font-semibold text-gray-900">Definición</h3>
          <pre className="overflow-x-auto rounded bg-gray-50 p-4 text-xs text-gray-600">
            {JSON.stringify(workflow.definition, null, 2)}
          </pre>
        </div>

        {/* Manual trigger */}
        <div className="rounded-lg border bg-white p-6">
          <h3 className="mb-4 font-semibold text-gray-900">Trigger Manual</h3>
          <p className="mb-2 text-sm text-gray-500">
            flow_type: <code className="rounded bg-gray-100 px-1">{workflow.flow_type}</code>
          </p>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            input_data (JSON)
          </label>
          <textarea
            value={inputJson}
            onChange={(e) => setInputJson(e.target.value)}
            className="mb-3 w-full rounded-lg border px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none"
            rows={6}
          />
          <button
            onClick={handleTrigger}
            disabled={triggering || workflow.status !== 'active'}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            {triggering ? 'Ejecutando...' : 'Ejecutar'}
          </button>
          {triggerResult && (
            <p className="mt-3 rounded bg-gray-50 p-2 text-sm text-gray-700">
              {triggerResult}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
