'use client'

import type { Approval } from '@/lib/types'
import { Badge } from '@/components/ui/Badge'
import { STATUS_BADGES } from '@/lib/constants'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { ShieldCheck } from 'lucide-react'

interface ApprovalListProps {
  approvals: Approval[]
  selectedId?: string
  onSelect: (approval: Approval) => void
}

export function ApprovalList({ approvals, selectedId, onSelect }: ApprovalListProps) {
  if (approvals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400 dark:text-gray-600">
        <ShieldCheck className="mb-2 h-12 w-12" />
        <p className="text-sm">No hay aprobaciones pendientes</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {approvals.map((approval) => {
        const badge = STATUS_BADGES[approval.status] || STATUS_BADGES['pending']
        const isSelected = approval.id === selectedId

        return (
          <button
            key={approval.id}
            onClick={() => onSelect(approval)}
            className={`w-full rounded-lg border p-4 text-left transition-colors ${
              isSelected
                ? 'border-blue-300 bg-blue-50 dark:border-blue-900/50 dark:bg-blue-900/10'
                : 'border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-900 dark:hover:bg-gray-800'
            }`}
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {approval.description}
              </span>
              <Badge className={badge.className}>{badge.label}</Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span>{approval.flow_type}</span>
              <span>&middot;</span>
              <span>
                {formatDistanceToNow(new Date(approval.created_at), {
                  addSuffix: true,
                  locale: es,
                })}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
