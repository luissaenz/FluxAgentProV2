'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import type { WorkflowTemplate } from '@/lib/types'
import Link from 'next/link'
import { Workflow } from 'lucide-react'
import { RunFlowDialog } from '@/components/flows/RunFlowDialog'
import { FlowHierarchyView } from '@/components/flows/FlowHierarchyView'

const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'success'> = {
  draft: 'secondary',
  active: 'success',
  archived: 'default',
}

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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Workflows</h2>
        <RunFlowDialog />
      </div>

      <div className="flex gap-2">
        {['', 'active', 'draft', 'archived'].map((s) => (
          <Button
            key={s}
            variant={statusFilter === s ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter(s)}
          >
            {s || 'Todos'}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <LoadingSpinner label="Cargando workflows..." />
      ) : !workflows?.length ? (
        <EmptyState
          icon={<Workflow className="mb-2 h-12 w-12" />}
          title="No hay workflows"
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workflows.map((wf) => (
            <Link key={wf.id} href={`/workflows/${wf.id}`}>
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{wf.name}</CardTitle>
                    <Badge variant={statusVariants[wf.status] || 'secondary'}>
                      {wf.status}
                    </Badge>
                  </div>
                  <CardDescription>{wf.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>v{wf.version}</span>
                    <span>{wf.execution_count} ejecuciones</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <div className="mt-8">
        <FlowHierarchyView />
      </div>
    </div>
  )
}
