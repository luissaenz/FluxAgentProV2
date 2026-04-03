'use client'

import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { createClient } from '@/lib/supabase'
import { Badge } from '@/components/ui/Badge'
import type { Agent } from '@/lib/types'
import Link from 'next/link'
import { Bot } from 'lucide-react'

export default function AgentsPage() {
  const { orgId } = useCurrentOrg()

  const { data: agents, isLoading } = useQuery<Agent[]>({
    queryKey: ['agents', orgId],
    queryFn: async () => {
      const supabase = createClient()
      const { data } = await supabase
        .from('agent_catalog')
        .select('*')
        .eq('org_id', orgId)
        .order('created_at', { ascending: false })
      return data || []
    },
    enabled: !!orgId,
  })

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Agentes</h2>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : !agents?.length ? (
        <div className="flex flex-col items-center justify-center py-12 text-gray-400 dark:text-gray-600">
          <Bot className="mb-2 h-12 w-12" />
          <p className="text-sm">No hay agentes configurados</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Link
              key={agent.id}
              href={`/agents/${agent.id}`}
              className="rounded-lg border bg-white p-4 transition-shadow hover:shadow-md dark:bg-gray-900 dark:border-gray-800 dark:hover:shadow-lg dark:hover:shadow-black/20 md:p-6"
            >
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">{agent.role}</h3>
                </div>
                <Badge
                  className={
                    agent.is_active
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
                      : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                  }
                >
                  {agent.is_active ? 'Activo' : 'Inactivo'}
                </Badge>
              </div>
              {agent.soul_json && (
                <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">
                  {(agent.soul_json as Record<string, string>).goal?.slice(0, 100) || 'Sin descripción'}
                </p>
              )}
              <div className="flex flex-wrap gap-1">
                {agent.allowed_tools?.slice(0, 3).map((tool) => (
                  <span
                    key={tool}
                    className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                  >
                    {tool}
                  </span>
                ))}
                {(agent.allowed_tools?.length || 0) > 3 && (
                  <span className="text-xs text-gray-400">
                    +{agent.allowed_tools.length - 3} más
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
