'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { GitCommit, Brain, Wrench, ChevronDown, ChevronUp } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Badge } from '@/components/ui/badge'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { cn } from '@/lib/utils'
import type { TranscriptEvent } from '@/hooks/useTranscriptTimeline'

// Mapa de estilos por tipo de evento - facil de extender para nuevos tipos
const EVENT_TYPE_CONFIG: Record<string, {
  icon: React.ElementType
  color: string
  badgeVariant: 'default' | 'secondary' | 'info' | 'warning' | 'success'
  label: string
}> = {
  flow_step: {
    icon: GitCommit,
    color: 'text-blue-500',
    badgeVariant: 'info',
    label: 'Paso',
  },
  agent_thought: {
    icon: Brain,
    color: 'text-purple-500',
    badgeVariant: 'secondary',
    label: 'Pensamiento',
  },
  tool_output: {
    icon: Wrench,
    color: 'text-amber-500',
    badgeVariant: 'warning',
    label: 'Herramienta',
  },
}

const FALLBACK_CONFIG = {
  icon: GitCommit,
  color: 'text-muted-foreground',
  badgeVariant: 'secondary' as const,
  label: 'Evento',
}

const THOUGHT_TRUNCATE_LIMIT = 200

interface TimelineEventProps {
  event: TranscriptEvent
  isLatest: boolean
  index: number
}

export function TimelineEvent({ event, isLatest, index }: TimelineEventProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const config = EVENT_TYPE_CONFIG[event.event_type] ?? FALLBACK_CONFIG
  const Icon = config.icon

  const timeLabel = event.created_at
    ? formatDistanceToNow(new Date(event.created_at), { addSuffix: true, locale: es })
    : ''

  // Renderizado especifico segun tipo de evento
  const renderContent = () => {
    if (event.event_type === 'agent_thought') {
      const thought = event.payload?.thought as string | undefined ?? ''
      const shouldTruncate = thought.length > THOUGHT_TRUNCATE_LIMIT
      const displayText = isExpanded || !shouldTruncate ? thought : `${thought.slice(0, THOUGHT_TRUNCATE_LIMIT)}...`

      return (
        <div className="mt-2 space-y-1">
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{displayText}</p>
          {shouldTruncate && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="h-3 w-3" />
                  Mostrar menos
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3" />
                  Mostrar mas
                </>
              )}
            </button>
          )}
        </div>
      )
    }

    if (event.event_type === 'tool_output') {
      const toolName = (event.payload?.tool_name as string | undefined) ??
                       (event.payload?.name as string | undefined) ??
                       event.event_type

      return (
        <div className="mt-2 space-y-2">
          <p className="text-xs text-muted-foreground">
            Herramienta: <code className="bg-muted px-1 py-0.5 rounded text-xs">{toolName}</code>
          </p>
          {event.payload && Object.keys(event.payload).length > 0 && (
            <CodeBlock code={event.payload} title={toolName} />
          )}
        </div>
      )
    }

    // flow_step o tipos desconocidos
    if (event.payload && Object.keys(event.payload).length > 0) {
      const stepName = (event.payload?.step as string | undefined) ??
                       (event.payload?.name as string | undefined) ??
                       event.event_type

      return (
        <div className="mt-2 space-y-2">
          <p className="text-xs text-muted-foreground">
            Paso: <code className="bg-muted px-1 py-0.5 rounded text-xs">{stepName}</code>
          </p>
          <CodeBlock code={event.payload} title={stepName} />
        </div>
      )
    }

    return null
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ 
        duration: 0.3, 
        delay: index * 0.05, // Staggered entrance
        layout: { duration: 0.2 } 
      }}
      className={cn(
        'flex gap-4 rounded-lg px-3 py-2 transition-all duration-200',
        isLatest && 'bg-blue-500/5 ring-1 ring-blue-500/20'
      )}
    >
      {/* Timeline dot + line */}
      <div className="flex flex-col items-center">
        <Icon className={cn('h-4 w-4', config.color)} />
        <div className="w-px flex-1 bg-border mt-2" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={config.badgeVariant} className="text-xs">
            {config.label}
          </Badge>
          <span className="text-xs text-muted-foreground">{timeLabel}</span>
        </div>

        <motion.div 
          layout="position"
          className="overflow-hidden"
        >
          {renderContent()}
        </motion.div>
      </div>
    </motion.div>
  )
}
