'use client'

import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  Brain,
  Send,
  Loader2,
  MessageSquare,
  AlertCircle,
  ChevronRight,
  Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatMessage {
  role: 'user' | 'assistant' | 'error'
  content: string
  data?: Record<string, unknown>[]
  queryType?: string
  timestamp: Date
}

interface AnalyticalQuery {
  key: string
  description: string
}

/**
 * AnalyticalAssistantChat — Chat lateral para interactuar con el crew analítico.
 *
 * Phase 4: Permite hacer preguntas en lenguaje natural sobre datos históricos
 * y obtener respuestas con datos reales de la organización.
 */
export function AnalyticalAssistantChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const queryClient = useQueryClient()

  // Consultas disponibles
  const { data: queriesData, isLoading: loadingQueries } = useQuery<{
    queries: AnalyticalQuery[]
  }>({
    queryKey: ['analytical-queries'],
    queryFn: () => api.get('/analytical/queries'),
    staleTime: 5 * 60_000,
  })

  // Mutación para enviar pregunta
  const askMutation = useMutation({
    mutationFn: (question: string) =>
      // SUPUESTO: El servidor puede tardar por el procesamiento de IA, se aplica timeout de 30s.
      api.post('/analytical/ask', { question }, { signal: AbortSignal.timeout(30000) }),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.summary,
          data: data.data,
          queryType: data.query_type,
          timestamp: new Date(),
        },
      ])
      queryClient.invalidateQueries({ queryKey: ['analytical-queries'] })
    },
    onError: (error: any) => {
      console.error('Error in AnalyticalAssistant:', error)
      
      let errorMessage = 'Error al procesar la consulta.'
      
      // Manejo específico de errores según el contrato MVP
      if (error?.status === 429) {
        errorMessage = 'Demasiadas consultas analíticas. Esperá un momento.'
      } else if (error?.status === 400) {
        errorMessage = 'No puedo responder a esa pregunta específica. ¿Probás con una de las consultas rápidas?'
      } else if (error?.code === 'ECONNABORTED') {
        errorMessage = 'La consulta está tardando demasiado. Volvé a intentar en unos segundos.'
      } else {
        errorMessage = error?.detail?.message || error?.message || errorMessage
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'error',
          content: errorMessage,
          timestamp: new Date(),
        },
      ])
    },
  })

  // Auto-scroll al último mensaje
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || askMutation.isPending) return

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: trimmed, timestamp: new Date() },
    ])
    setInput('')
    askMutation.mutate(trimmed)
  }

  const handleQuickQuery = (queryKey: string) => {
    const query = queriesData?.queries.find((q) => q.key === queryKey)
    if (!query) return

    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: `Mostrame: ${query.description}`,
        timestamp: new Date(),
      },
    ])
    askMutation.mutate(query.description)
  }

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button
          variant="default"
          size="icon"
          className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full shadow-2xl hover:scale-110 transition-all duration-300 bg-primary text-primary-foreground border-none"
          title="Asistente Analítico"
        >
          <Brain className="h-6 w-6" />
          <span className="absolute -top-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-sky-500"></span>
          </span>
        </Button>
      </SheetTrigger>

      <SheetContent side="right" className="w-[480px] sm:w-[540px] flex flex-col">
        <SheetHeader className="px-2 pt-4 pb-2">
          <SheetTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Asistente Analítico
          </SheetTitle>
          <SheetDescription>
            Hacé preguntas sobre datos históricos de tu organización.
          </SheetDescription>
        </SheetHeader>

        <Separator className="my-2" />

        {/* Área de mensajes */}
        <ScrollArea ref={scrollRef} className="flex-1 px-2">
          {messages.length === 0 ? (
            <EmptyState
              queries={queriesData?.queries || []}
              loadingQueries={loadingQueries}
              onQuickQuery={handleQuickQuery}
            />
          ) : (
            <div className="space-y-3 py-2">
              {messages.map((msg, i) => (
                <ChatMessageBubble key={i} message={msg} />
              ))}
              {askMutation.isPending && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2 px-3">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Analizando datos...
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Input */}
        <form onSubmit={handleSubmit} className="px-2 py-3 border-t">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ej: ¿Cuál es el agente con mayor tasa de éxito?"
              disabled={askMutation.isPending}
              className="flex-1"
            />
            <Button
              type="submit"
              size="icon"
              disabled={askMutation.isPending || !input.trim()}
            >
              {askMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}

// ── Componente interno: Empty State ─────────────────────────────

interface EmptyStateProps {
  queries: AnalyticalQuery[]
  loadingQueries: boolean
  onQuickQuery: (key: string) => void
}

function EmptyState({ queries, loadingQueries, onQuickQuery }: EmptyStateProps) {
  return (
    <div className="py-8 space-y-4">
      <div className="flex flex-col items-center text-center space-y-2">
        <MessageSquare className="h-12 w-12 text-muted-foreground/50" />
        <p className="font-medium">Asistente Analítico</p>
        <p className="text-sm text-muted-foreground max-w-xs">
          Preguntá sobre métricas, rendimiento y datos históricos de tu
          organización.
        </p>
      </div>

      {loadingQueries ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : queries.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground px-1">
            Consultas rápidas
          </p>
          {queries.map((q) => (
            <button
              key={q.key}
              onClick={() => onQuickQuery(q.key)}
              className="flex items-center w-full gap-2 px-3 py-2 text-sm rounded-lg border hover:bg-muted/50 hover:border-primary/30 transition-all text-left"
            >
              <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
              <span>{q.description}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

// ── Componente interno: Chat Message Bubble ─────────────────────

interface ChatMessageBubbleProps {
  message: ChatMessage
}

function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === 'user'
  const isError = message.role === 'error'

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-3 py-2 text-sm',
          isUser && 'bg-primary text-primary-foreground',
          isError && 'bg-destructive/10 text-destructive border border-destructive/20',
          !isUser && !isError && 'bg-muted'
        )}
      >
        {/* Query type badge */}
        {message.queryType && (
          <Badge variant="secondary" className="text-xs mb-1">
            {message.queryType}
          </Badge>
        )}

        {/* Content */}
        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

        {/* Data preview (para respuestas del asistente) */}
        {!isUser && message.data && message.data.length > 0 && (
          <DataPreview data={message.data} />
        )}

        {/* Timestamp */}
        <p
          className={cn(
            'text-[10px] mt-1.5 opacity-60',
            isUser ? 'text-primary-foreground/60' : 'text-muted-foreground'
          )}
        >
          {message.timestamp.toLocaleTimeString('es-AR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  )
}

// ── Componente interno: Data Preview ────────────────────────────

interface DataPreviewProps {
  data: Record<string, unknown>[]
}

function DataPreview({ data }: DataPreviewProps) {
  const maxRows = 5
  const showMore = data.length > maxRows

  if (data.length === 0) return null

  // Obtener keys del primer objeto
  const keys = Object.keys(data[0]).filter((k) => k !== 'id')

  return (
    <div className="mt-2 rounded-lg border bg-background/50 overflow-hidden">
      <table className="w-full text-xs">
        <thead className="bg-muted/50">
          <tr>
            {keys.map((key) => (
              <th
                key={key}
                className="px-2 py-1 text-left font-medium text-muted-foreground"
              >
                {key.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, maxRows).map((row, i) => (
            <tr key={i} className="border-t">
              {keys.map((key) => (
                <td key={key} className="px-2 py-1 font-mono">
                  {String(row[key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {showMore && (
        <div className="px-2 py-1 text-xs text-muted-foreground bg-muted/30 text-center">
          +{data.length - maxRows} filas más
        </div>
      )}
    </div>
  )
}
