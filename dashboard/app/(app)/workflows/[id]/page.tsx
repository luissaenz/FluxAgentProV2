'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { BackButton } from '@/components/shared/BackButton'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Play } from 'lucide-react'

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
    return <LoadingSpinner label="Cargando workflow..." />
  }

  if (!workflow) {
    return <p className="py-12 text-center text-muted-foreground">Workflow no encontrado</p>
  }

  return (
    <div className="space-y-6">
      <BackButton href="/workflows" />

      <div className="flex items-center gap-3">
        <h2 className="text-2xl font-bold tracking-tight">{workflow.name}</h2>
        <Badge variant={workflow.status === 'active' ? 'success' : 'secondary'}>
          {workflow.status}
        </Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Definition */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Definición</CardTitle>
          </CardHeader>
          <CardContent>
            <CodeBlock code={workflow.definition} />
          </CardContent>
        </Card>

        {/* Manual trigger */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Trigger Manual</CardTitle>
            <CardDescription>
              flow_type: <code className="rounded bg-muted px-1">{workflow.flow_type}</code>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="input-data">input_data (JSON)</Label>
              <Textarea
                id="input-data"
                value={inputJson}
                onChange={(e) => setInputJson(e.target.value)}
                className="font-mono text-sm"
                rows={6}
              />
            </div>
            <Button
              onClick={handleTrigger}
              disabled={triggering || workflow.status !== 'active'}
            >
              <Play className="mr-2 h-4 w-4" />
              {triggering ? 'Ejecutando...' : 'Ejecutar'}
            </Button>
            {triggerResult && (
              <p className="rounded bg-muted p-2 text-sm text-muted-foreground">
                {triggerResult}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
