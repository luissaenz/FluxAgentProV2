'use client'

import { useState } from 'react'
import type { Approval } from '@/lib/types'
import { Badge } from '@/components/ui/Badge'
import { STATUS_BADGES } from '@/lib/constants'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { CheckCircle, XCircle } from 'lucide-react'

interface ApprovalDetailProps {
  approval: Approval
  onApprove: (task_id: string, notes?: string) => void
  onReject: (task_id: string, notes?: string) => void
  isLoading?: boolean
}

export function ApprovalDetail({
  approval,
  onApprove,
  onReject,
  isLoading,
}: ApprovalDetailProps) {
  const [notes, setNotes] = useState('')
  const badge = STATUS_BADGES[approval.status] || STATUS_BADGES['pending']

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {approval.description}
          </h3>
          <p className="text-sm text-gray-500">
            {approval.flow_type} &middot;{' '}
            {formatDistanceToNow(new Date(approval.created_at), {
              addSuffix: true,
              locale: es,
            })}
          </p>
        </div>
        <Badge className={badge.className}>{badge.label}</Badge>
      </div>

      {/* Payload */}
      <div className="mb-4 rounded-lg bg-gray-50 p-4">
        <h4 className="mb-2 text-sm font-medium text-gray-700">Payload</h4>
        <pre className="overflow-x-auto text-xs text-gray-600">
          {JSON.stringify(approval.payload, null, 2)}
        </pre>
      </div>

      {approval.status === 'pending' && (
        <>
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Notas (opcional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              rows={2}
              placeholder="Agregar notas sobre la decisión..."
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => onApprove(approval.task_id, notes)}
              disabled={isLoading}
              className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              <CheckCircle className="h-4 w-4" />
              Aprobar
            </button>
            <button
              onClick={() => onReject(approval.task_id, notes)}
              disabled={isLoading}
              className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              <XCircle className="h-4 w-4" />
              Rechazar
            </button>
          </div>
        </>
      )}
    </div>
  )
}
