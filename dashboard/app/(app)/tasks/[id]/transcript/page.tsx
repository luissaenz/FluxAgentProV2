'use client'

import { useParams } from 'next/navigation'
import { useFlowTranscript } from '@/hooks/useFlowTranscript'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { BackButton } from '@/components/shared/BackButton'
import { StatusLabel } from '@/components/shared/StatusLabel'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, Radio, FileText } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import type { DomainEvent } from '@/lib/types'

interface TranscriptEvent extends DomainEvent {
  sequence: number
}

export default function TranscriptPage() {
  const { id } = useParams() as { id: string }
  const { orgId } = useCurrentOrg()
  const { events, flowType, status, isLoading, isLive } = useFlowTranscript(orgId, id)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <BackButton href={`/tasks/${id}`} />
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Transcript
          </h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
            {flowType && <Badge variant="outline">{flowType}</Badge>}
            {status && <StatusLabel status={status} />}
            {isLive && (
              <Badge variant="secondary" className="flex items-center gap-1">
                <Radio className="h-3 w-3 animate-pulse text-green-500" />
                En vivo
              </Badge>
            )}
          </div>
        </div>
      </div>

      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm">Eventos ({events.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[600px] px-4">
            {isLoading ? (
              <div className="flex items-center gap-2 py-8 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Cargando transcript...
              </div>
            ) : events.length === 0 ? (
              <p className="py-8 text-sm text-muted-foreground">Sin eventos aun.</p>
            ) : (
              <div className="space-y-2 py-2">
                {events.map((event, i) => (
                  <TranscriptEvent key={event.id} event={event} index={i} />
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}

function TranscriptEvent({
  event,
  index,
}: {
  event: TranscriptEvent
  index: number
}) {
  const time = event.created_at
    ? formatDistanceToNow(new Date(event.created_at), {
        addSuffix: false,
        locale: es,
      })
    : ''

  return (
    <div className="rounded border px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-muted-foreground">
          #{index + 1}
        </span>
        <code className="text-xs bg-muted px-1 py-0.5 rounded">
          {event.event_type}
        </code>
        <span className="text-xs text-muted-foreground ml-auto">{time}</span>
      </div>
      {event.payload && Object.keys(event.payload).length > 0 && (
        <div className="mt-1">
          <CodeBlock code={event.payload} />
        </div>
      )}
    </div>
  )
}
