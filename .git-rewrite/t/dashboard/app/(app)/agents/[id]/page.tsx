'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { createClient } from '@/lib/supabase'
import { Badge } from '@/components/ui/Badge'
import type { Agent } from '@/lib/types'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: agent, isLoading } = useQuery<Agent | null>({
    queryKey: ['agent', id],
    queryFn: async () => {
      const supabase = createClient()
      const { data } = await supabase
        .from('agent_catalog')
        .select('*')
        .eq('id', id)
        .single()
      return data
    },
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!agent) {
    return <p className="py-12 text-center text-gray-500">Agente no encontrado</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/agents" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h2 className="text-2xl font-bold text-gray-900">{agent.role}</h2>
        <Badge
          className={
            agent.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
          }
        >
          {agent.is_active ? 'Activo' : 'Inactivo'}
        </Badge>
      </div>

      <div className="rounded-lg border bg-white p-6">
        <h3 className="mb-4 font-semibold text-gray-900">SOUL Definition</h3>
        <pre className="overflow-x-auto rounded bg-gray-50 p-4 text-xs text-gray-600">
          {JSON.stringify(agent.soul_json, null, 2)}
        </pre>
      </div>

      <div className="rounded-lg border bg-white p-6">
        <h3 className="mb-4 font-semibold text-gray-900">Configuración</h3>
        <dl className="space-y-3">
          <div>
            <dt className="text-xs font-medium text-gray-500">Max Iteraciones</dt>
            <dd className="text-sm text-gray-900">{agent.max_iter}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-gray-500">Tools permitidos</dt>
            <dd className="mt-1 flex flex-wrap gap-1">
              {agent.allowed_tools?.map((tool) => (
                <span key={tool} className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                  {tool}
                </span>
              ))}
              {(!agent.allowed_tools || agent.allowed_tools.length === 0) && (
                <span className="text-xs text-gray-400">Ninguno configurado</span>
              )}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
