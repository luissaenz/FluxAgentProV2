'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { createClient } from '@/lib/supabase'
import { Badge } from '@/components/ui/badge'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { BackButton } from '@/components/shared/BackButton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
          </dl>
        </CardContent>
      </Card>
    </div>
  )
}
