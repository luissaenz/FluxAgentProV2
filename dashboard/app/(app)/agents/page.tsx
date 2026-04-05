'use client'

import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { createClient } from '@/lib/supabase'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
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
      <h2 className="text-2xl font-bold tracking-tight">Agentes</h2>

      {isLoading ? (
        <LoadingSpinner label="Cargando agentes..." />
      ) : !agents?.length ? (
        <EmptyState
          icon={<Bot className="mb-2 h-12 w-12" />}
          title="No hay agentes configurados"
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Link
              key={agent.id}
              href={`/agents/${agent.id}`}
            >
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Bot className="h-5 w-5 text-muted-foreground" />
                      {agent.role}
                    </CardTitle>
                    <Badge variant={agent.is_active ? 'success' : 'secondary'}>
                      {agent.is_active ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </div>
                  {agent.soul_json && (
                    <CardDescription className="line-clamp-3">
                      {(agent.soul_json as Record<string, string>)?.goal || 'Sin descripción'}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1">
                    {agent.allowed_tools?.slice(0, 3).map((tool) => (
                      <Badge key={tool} variant="secondary">
                        {tool}
                      </Badge>
                    ))}
                    {(agent.allowed_tools?.length || 0) > 3 && (
                      <Badge variant="outline">
                        +{agent.allowed_tools!.length - 3} más
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
