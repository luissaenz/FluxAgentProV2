'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import {
  Radio,
  WifiOff,
  Loader2,
  FileText,
  RefreshCw,
  ArrowDown,
  AlertTriangle,
  Activity,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useTranscriptTimeline, type ConnectionStatus } from '@/hooks/useTranscriptTimeline'
import { TimelineEvent } from './TimelineEvent'

const AUTO_SCROLL_THRESHOLD = 80 // px desde el fondo para considerar "al fondo"

interface TranscriptTimelineProps {
  taskId: string
  orgId: string
}

export function TranscriptTimeline({ taskId, orgId }: TranscriptTimelineProps) {
  const {
    events,
    isLoading,
    isRunning,
    isLive,
    connectionStatus,
    hasMore,
    loadMore,
    reconnect,
    flowType,
    status,
  } = useTranscriptTimeline(taskId, orgId)

  const scrollRef = useRef<HTMLDivElement>(null)
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const autoScrollRef = useRef(true)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const [newEventCount, setNewEventCount] = useState(0)

  // Setup viewport reference for scroll detection
  useEffect(() => {
    if (!scrollRef.current) return

    // SUPUESTO: El ScrollArea de shadcn tiene un [data-radix-scroll-area-viewport]
    // como hijo directo. Esto es un detalle de implementacion de Radix.
    const viewport = scrollRef.current.querySelector<HTMLDivElement>(
      '[data-radix-scroll-area-viewport]'
    )
    if (!viewport) return
    viewportRef.current = viewport

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = viewport
      const distanceToBottom = scrollHeight - scrollTop - clientHeight
      const isAtBottom = distanceToBottom < AUTO_SCROLL_THRESHOLD

      if (isAtBottom) {
        autoScrollRef.current = true
        setShowScrollButton(false)
        setNewEventCount(0)
      } else {
        autoScrollRef.current = false
        setShowScrollButton(true)
      }
    }

    viewport.addEventListener('scroll', handleScroll, { passive: true })
    return () => viewport.removeEventListener('scroll', handleScroll)
  }, [isLoading])

  // Auto-scroll al recibir nuevos eventos
  const prevEventCount = useRef(events.length)
  useEffect(() => {
    if (events.length > prevEventCount.current && autoScrollRef.current) {
      scrollToBottom()
    }
    prevEventCount.current = events.length
  }, [events.length])

  // Contar eventos nuevos cuando el usuario no esta al fondo
  useEffect(() => {
    if (events.length > prevEventCount.current && !autoScrollRef.current) {
      setNewEventCount((prev) => prev + (events.length - prevEventCount.current))
    }
  }, [events.length])

  const scrollToBottom = useCallback(() => {
    if (!viewportRef.current) return
    viewportRef.current.scrollTo({
      top: viewportRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [])

  const handleScrollToBottom = useCallback(() => {
    scrollToBottom()
    autoScrollRef.current = true
    setShowScrollButton(false)
    setNewEventCount(0)
  }, [scrollToBottom])

  // Estado de error del backend
  const isBackendError = connectionStatus === 'error' && !isLive

  return (
    <div className="space-y-3">
      {/* Header con info de estado y conexion */}
      <div className="flex items-center gap-2 flex-wrap">
        {flowType && (
          <Badge variant="outline" className="text-xs">{flowType}</Badge>
        )}
        {status && (
          <Badge variant="secondary" className="text-xs">{status}</Badge>
        )}
        {isRunning && (
          <Badge variant="default" className="flex items-center gap-1.5 text-xs">
            <motion.div
              animate={{ 
                scale: [1, 1.2, 1],
                opacity: [0.7, 1, 0.7]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="h-2 w-2 rounded-full bg-green-400"
            />
            En vivo
          </Badge>
        )}
        <ConnectionStatusBadge status={connectionStatus} />
      </div>

      {/* Banner de error de conexion */}
      {isBackendError && (
        <div className="flex items-center gap-2 rounded-md bg-yellow-500/10 px-3 py-2 text-sm text-yellow-400">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span className="flex-1">
            Error de conexion en tiempo real. Los eventos historicos siguen disponibles.
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={reconnect}
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Reintentar
          </Button>
        </div>
      )}

      {/* Banner de reconexion en progreso */}
      {connectionStatus === 'connecting' && isRunning && (
        <div className="flex items-center gap-2 rounded-md bg-blue-500/10 px-3 py-2 text-sm text-blue-400">
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          <span>Conectando en tiempo real...</span>
        </div>
      )}

      {/* Boton de cargar anteriores */}
      {hasMore && (
        <div className="flex justify-center">
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            onClick={loadMore}
          >
            Cargar anteriores
          </Button>
        </div>
      )}

      {/* Timeline de eventos */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Timeline de Eventos
            <span className="text-muted-foreground font-normal">
              ({events.length} eventos)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea ref={scrollRef} className="h-[calc(100vh-320px)] min-h-[400px]">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mb-2" />
                <p className="text-sm">Cargando transcript...</p>
              </div>
            ) : events.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <Activity className="h-10 w-10 mb-3 opacity-50" />
                <p className="text-sm">
                  {isRunning
                    ? 'Esperando eventos del agente...'
                    : 'Sin eventos para esta tarea.'}
                </p>
              </div>
            ) : (
              <div className="px-4 py-2 space-y-0">
                <AnimatePresence initial={false}>
                  {events.map((event, i) => (
                    <TimelineEvent
                      key={event.id}
                      event={event}
                      index={i}
                      isLatest={i === events.length - 1}
                    />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Boton flotante "Ir al final" */}
      {showScrollButton && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-center"
        >
          <Button
            size="sm"
            variant="secondary"
            className="shadow-lg flex items-center gap-1"
            onClick={handleScrollToBottom}
          >
            <ArrowDown className="h-4 w-4" />
            Ir al final
            {newEventCount > 0 && (
              <Badge variant="default" className="ml-1 h-5 min-w-5 flex items-center justify-center rounded-full px-1.5 text-xs">
                {newEventCount}
              </Badge>
            )}
          </Button>
        </motion.div>
      )}
    </div>
  )
}

// Componente interno para el badge de estado de conexion
function ConnectionStatusBadge({ status }: { status: ConnectionStatus }) {
  if (status === 'connected') return null

  if (status === 'disconnected') {
    return (
      <Badge variant="outline" className="flex items-center gap-1 text-xs text-muted-foreground">
        <WifiOff className="h-3 w-3" />
        Sin tiempo real
      </Badge>
    )
  }

  if (status === 'error') {
    return (
      <Badge variant="destructive" className="flex items-center gap-1 text-xs">
        <WifiOff className="h-3 w-3" />
        Desconectado
      </Badge>
    )
  }

  // connecting
  return (
    <Badge variant="outline" className="flex items-center gap-1 text-xs text-muted-foreground">
      <Loader2 className="h-3 w-3 animate-spin" />
      Conectando...
    </Badge>
  )
}
