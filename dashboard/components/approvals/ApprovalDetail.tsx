'use client'

import { useState } from 'react'
import type { Approval } from '@/lib/types'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { CheckCircle, XCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

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

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">{approval.description}</h3>
            <p className="text-sm text-muted-foreground">
              {approval.flow_type} &middot;{' '}
              {formatDistanceToNow(new Date(approval.created_at), {
                addSuffix: true,
                locale: es,
              })}
            </p>
          </div>
          <StatusLabel status={approval.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Payload */}
        <CodeBlock code={approval.payload} title="Payload" />

        {approval.status === 'pending' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="approval-notes">Notas (opcional)</Label>
              <Textarea
                id="approval-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Agregar notas sobre la decisión..."
                rows={2}
              />
            </div>

            <div className="flex gap-3">
              <Button
                onClick={() => onApprove(approval.task_id, notes)}
                disabled={isLoading}
                className="bg-green-600 hover:bg-green-700"
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Aprobar
              </Button>
              <Button
                onClick={() => onReject(approval.task_id, notes)}
                disabled={isLoading}
                variant="destructive"
              >
                <XCircle className="mr-2 h-4 w-4" />
                Rechazar
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
