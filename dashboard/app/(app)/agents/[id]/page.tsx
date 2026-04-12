'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { createClient } from '@/lib/supabase'
import { useAgentDetail } from '@/hooks/useAgentDetail'
import { useAgentMetrics } from '@/hooks/useAgentMetrics'
import { BackButton } from '@/components/shared/BackButton'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { AgentPersonalityCard } from '@/components/agents/AgentPersonalityCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Skeleton } from '@/components/ui/skeleton'
import { Bot, Key, Coins } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import type { Agent } from '@/lib/types'
import Link from 'next/link'

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
  const { data: detail, isLoading: loadingDetail } = useAgentDetail(
    typeof agent?.org_id === 'string' ? agent.org_id : '',
    id || ''
  )

  const agentTokenUsage = agentMetrics?.find(
    (m) => m.agent_id === id || m.agent_role.toLowerCase() === agent?.role?.toLowerCase()
  )

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (!agent) {
    return (
      <p className="py-12 text-center text-muted-foreground">
        Agente no encontrado
      </p>
    )
  }

  const enrichedAgent = detail?.agent ?? agent
  const displayName = enrichedAgent?.display_name ?? agent.role

  const metrics = detail?.metrics
  const credentials = detail?.credentials || []
  const soul = agent.soul_json || {}
  const totalTokens = metrics?.total_tokens ?? agentTokenUsage?.tokens_used ?? 0

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <BackButton href="/agents" />
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bot className="h-6 w-6" />
            {displayName}
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={agent.is_active ? 'success' : 'secondary'}>
              {agent.is_active ? 'Activo' : 'Inactivo'}
            </Badge>
            {agent.model && (
              <Badge variant="outline">{agent.model}</Badge>
            )}
          </div>
        </div>
      </div>

      {/* Metricas rapidas */}
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label="Tokens totales"
          value={totalTokens.toLocaleString()}
          icon={<Coins className="h-4 w-4" />}
        />
        <MetricCard
          label="Tareas completadas"
          value={metrics?.tasks_by_status.completed ?? '—'}
        />
        <MetricCard
          label="Tareas fallidas"
          value={metrics?.tasks_by_status.failed ?? '—'}
        />
        <MetricCard
          label="Max iteraciones"
          value={agent.max_iter}
        />
      </div>

      <Tabs defaultValue="info">
        <TabsList>
          <TabsTrigger value="info">Informacion</TabsTrigger>
          <TabsTrigger value="tasks">
            Tareas {metrics?.recent_tasks?.length ? `(${metrics.recent_tasks.length})` : ''}
          </TabsTrigger>
          <TabsTrigger value="credentials">
            Credenciales ({credentials.length})
          </TabsTrigger>
        </TabsList>

        {/* Tab: Informacion */}
        <TabsContent value="info" className="space-y-4">
          <AgentPersonalityCard
            displayName={displayName}
            role={agent.role}
            soulNarrative={enrichedAgent?.soul_narrative ?? null}
            avatarUrl={enrichedAgent?.avatar_url ?? null}
            isLoading={loadingDetail}
          />

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Configuracion</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div><strong>Role:</strong> {agent.role}</div>
              <div><strong>Modelo:</strong> {agent.model || '—'}</div>
              <div><strong>Max iteraciones:</strong> {agent.max_iter}</div>
              <div>
                <strong>Herramientas:</strong>{' '}
                {(agent.allowed_tools || []).join(', ') || '—'}
              </div>
            </CardContent>
          </Card>

          <Accordion type="single" collapsible>
            <AccordionItem value="soul">
              <AccordionTrigger>SOUL Definition (Prompt)</AccordionTrigger>
              <AccordionContent>
                <CodeBlock code={soul} />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </TabsContent>

        {/* Tab: Tareas */}
        <TabsContent value="tasks">
          <Card>
            <CardHeader>
              <CardTitle>Tareas Recientes</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingDetail ? (
                <p className="text-sm text-muted-foreground">Cargando...</p>
              ) : !metrics?.recent_tasks?.length ? (
                <p className="text-sm text-muted-foreground">
                  Sin tareas para este agente.
                </p>
              ) : (
                <div className="space-y-2">
                  {metrics.recent_tasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between rounded border px-3 py-2 text-sm"
                    >
                      <div className="flex items-center gap-3">
                        <Link
                          href={`/tasks/${task.id}`}
                          className="font-mono text-primary hover:underline"
                        >
                          {task.id.slice(0, 8)}...
                        </Link>
                        <Badge variant="outline">{task.flow_type}</Badge>
                        <span>{task.tokens_used.toLocaleString()} tokens</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusLabel status={task.status} />
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(task.created_at), {
                            addSuffix: true,
                            locale: es,
                          })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Credenciales */}
        <TabsContent value="credentials">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Key className="h-4 w-4" />
                Credenciales en Vault
              </CardTitle>
            </CardHeader>
            <CardContent>
              {credentials.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Sin credenciales asociadas.
                </p>
              ) : (
                <div className="space-y-2">
                  {credentials.map((cred, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 rounded border px-3 py-2 text-sm"
                    >
                      <Key className="h-4 w-4 text-muted-foreground" />
                      <span className="font-mono">{cred.tool}</span>
                      {cred.description && (
                        <span className="text-xs text-muted-foreground">
                          — {cred.description}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-3">
                Solo se muestran los nombres de las herramientas que requieren credenciales.
                Los valores nunca se exponen.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string
  value: string | number
  icon?: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}
