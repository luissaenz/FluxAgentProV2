'use client'

import { useState } from 'react'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useApprovals } from '@/hooks/useApprovals'
import { ApprovalList } from '@/components/approvals/ApprovalList'
import { ApprovalDetail } from '@/components/approvals/ApprovalDetail'
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

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Centro de Aprobaciones</h2>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : (
        <div className="grid gap-4 md:gap-6 lg:grid-cols-2">
          <div>
            <h3 className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
              Pendientes ({approvals?.filter((a) => a.status === 'pending').length || 0})
            </h3>
            <ApprovalList
              approvals={approvals || []}
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
              <div className="flex items-center justify-center rounded-lg border border-dashed py-12 text-sm text-gray-400 dark:border-gray-800 dark:text-gray-600">
                Selecciona una aprobación para ver el detalle
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
