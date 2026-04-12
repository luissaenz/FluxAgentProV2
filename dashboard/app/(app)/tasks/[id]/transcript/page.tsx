'use client'

import { useParams } from 'next/navigation'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { BackButton } from '@/components/shared/BackButton'
import { FileText } from 'lucide-react'
import { TranscriptTimeline } from '@/components/transcripts/TranscriptTimeline'

export default function TranscriptPage() {
  const { id } = useParams() as { id: string }
  const { orgId } = useCurrentOrg()

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <BackButton href={`/tasks/${id}`} />
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Transcript
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Timeline en tiempo real de la ejecucion
          </p>
        </div>
      </div>

      <TranscriptTimeline taskId={id} orgId={orgId} />
    </div>
  )
}
