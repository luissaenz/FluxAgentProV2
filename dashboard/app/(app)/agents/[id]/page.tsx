'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { createClient } from '@/lib/supabase'
import { Badge } from '@/components/ui/badge'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { BackButton } from '@/components/shared/BackButton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAgentMetrics } from '@/hooks/useAgentMetrics'
import { Coins } from 'lucide-react'
import type { Agent } from '@/lib/types'

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

  const { data: agentMetrics, isLoading: loadingMetrics } = useAgentMetrics()

  const agentTokenUsage = agentMetrics?.find(
    (m) => m.agent_id === id || m.agent_role.toLowerCase() === agent?.role?.toLowerCase()
  )

  if (isLoading) {
    return <LoadingSpinner label="Cargando agente..." />
  }

  if (!agent) {
    return <p className="py-12 text-center text-muted-foreground">Agente no encontrado</p>
  }

  return (
    <div className="space-y-6">
      <BackButton href="/agents" />

      <div className="flex items-center gap-3">
        <h2 className="text-2xl font-bold tracking-tight">{agent.role}</h2>
        <Badge variant={agent.is_active ? 'success' : 'secondary'}>
          {agent.is_active ? 'Activo' : 'Inactivo'}
        </Badge>
      </div>

      {/* Panel de tokens */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Coins className="h-4 w-4" />
            Tokens Consumidos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loadingMetrics ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <div className="text-2xl font-bold">
              {(agentTokenUsage?.tokens_used || 0).toLocaleString()}
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            Total de tokens consumidos por este agente
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">SOUL Definition</CardTitle>
        </CardHeader>
        <CardContent>
          <CodeBlock code={agent.soul_json} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuración</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Max Iteraciones</dt>
              <dd className="text-sm">{agent.max_iter}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Tools permitidos</dt>
              <dd className="mt-1 flex flex-wrap gap-1">
                {agent.allowed_tools?.map((tool) => (
                  <Badge key={tool} variant="outline">
                    {tool}
                  </Badge>
                ))}
                {(!agent.allowed_tools || agent.allowed_tools.length === 0) && (
                  <span className="text-sm text-muted-foreground">Ninguno configurado</span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Credenciales</dt>
              <dd className="mt-1">
                <a
                  href="#"
                  className="text-sm text-blue-600 hover:underline"
                  onClick={(e) => {
                    e.preventDefault()
                    alert('Panel de Vault en desarrollo')
                  }}
                >
                  Ver secrets en Vault →
                </a>
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  )
}
