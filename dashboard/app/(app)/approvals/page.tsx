'use client'

import { useState } from 'react'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useApprovals } from '@/hooks/useApprovals'
import { ApprovalList } from '@/components/approvals/ApprovalList'
import { ApprovalDetail } from '@/components/approvals/ApprovalDetail'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import type { Approval } from '@/lib/types'

export default function ApprovalsPage() {
  const { orgId } = useCurrentOrg()
  const { data: approvals, approve, reject, isLoading } = useApprovals(orgId)
  const [selected, setSelected] = useState<Approval | null>(null)

  const handleApprove = (task_id: string, notes?: string) => {
    approve.mutate(
      { task_id, notes },
      { onSuccess: () => setSelected(null) }
    )
  }

  const handleReject = (task_id: string, notes?: string) => {
    reject.mutate(
      { task_id, notes },
      { onSuccess: () => setSelected(null) }
    )
  }

  const pendingApprovals = approvals?.filter((a) => a.status === 'pending') || []

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold tracking-tight">Centro de Aprobaciones</h2>

      {isLoading ? (
        <LoadingSpinner label="Cargando aprobaciones..." />
      ) : pendingApprovals.length === 0 ? (
        <EmptyState title="Sin aprobaciones pendientes" description="No hay tareas que requieran tu aprobación" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <h3 className="mb-3 text-sm font-medium text-muted-foreground">
              Pendientes ({pendingApprovals.length})
            </h3>
            <ApprovalList
              approvals={pendingApprovals}
              selectedId={selected?.id}
              onSelect={setSelected}
            />
          </div>

          <div>
            {selected ? (
              <ApprovalDetail
                approval={selected}
                onApprove={handleApprove}
                onReject={handleReject}
                isLoading={approve.isPending || reject.isPending}
              />
            ) : (
              <EmptyState description="Selecciona una aprobación para ver el detalle" />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
