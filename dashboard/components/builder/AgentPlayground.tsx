'use client'

import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Send, Play } from 'lucide-react'

import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import type { Task } from '@/lib/types'

// Post-MVP: tool calls interface para cuando tool_calls se persistan en tasks (columna JSONB + ToolCallTracer extendido)
interface ToolCallInfo {
  name: string
  count: number
}

interface PlaygroundMessage {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  toolCalls?: ToolCallInfo[]
  tokensUsed?: number
  timestamp: Date
}

interface AgentPlaygroundProps {
  role: string
}

function formatResult(result: unknown): string {
  if (typeof result === 'string') return result
  if (typeof result === 'object' && result !== null) {
    return JSON.stringify(result, null, 2)
  }
  return String(result ?? '')
}

function generateId(): string {
  return Math.random().toString(36).substring(2, 9)
}

export function AgentPlayground({ role }: AgentPlaygroundProps) {
  const [messages, setMessages] = useState<PlaygroundMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [startTime, setStartTime] = useState<number | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const encodedRole = encodeURIComponent(role)

  const runMutation = useMutation({
    mutationFn: (message: string) =>
      api.post(`/agents/${encodedRole}/run`, { input_data: { message } }),
    onSuccess: (data: { task_id: string; status: string }) => {
      setCurrentTaskId(data.task_id)
      setStartTime(Date.now())
    },
    onError: (error: Error) => {
      toast.error(error.message)
      const errorMsg: PlaygroundMessage = {
        id: generateId(),
        role: 'error',
        content: `Failed to run agent: ${error.message}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMsg])
    },
  })

  const POLLING_INTERVAL = 2000
  const POLLING_TIMEOUT = 120000

  const taskQuery = useQuery<Task>({
    queryKey: ['agent-playground-task', currentTaskId],
    queryFn: () => api.get(`/tasks/${currentTaskId}`),
    enabled: !!currentTaskId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return POLLING_INTERVAL
      if (data.status === 'completed' || data.status === 'failed') return false
      const elapsed = startTime ? Date.now() - startTime : 0
      if (elapsed > POLLING_TIMEOUT) return false
      return POLLING_INTERVAL
    },
    staleTime: 0,
    retry: 1,
  })

  const taskData = taskQuery.data
  const isRunning = currentTaskId !== null && (!taskData || taskData.status === 'pending' || taskData.status === 'running')

  useEffect(() => {
    if (!taskData) return
    const elapsed = startTime ? (Date.now() - startTime) : 0
    if (elapsed > POLLING_TIMEOUT && (taskData.status === 'pending' || taskData.status === 'running')) {
      setCurrentTaskId(null)
      setStartTime(null)
      const timeoutMsg: PlaygroundMessage = {
        id: generateId(),
        role: 'error',
        content: 'Agent is taking too long. Try again or check the backend.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, timeoutMsg])
      return
    }

    if (taskData.status === 'completed') {
      const content = formatResult(taskData.result)
      const assistantMsg: PlaygroundMessage = {
        id: generateId(),
        role: 'assistant',
        content,
        tokensUsed: taskData.tokens_used,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setCurrentTaskId(null)
      setStartTime(null)
    } else if (taskData.status === 'failed') {
      const errorContent = taskData.error || 'Agent execution failed'
      const errorMsg: PlaygroundMessage = {
        id: generateId(),
        role: 'error',
        content: errorContent,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMsg])
      setCurrentTaskId(null)
      setStartTime(null)
    }
    // `startTime` solo cambia via `setStartTime(null)` cuando `currentTaskId` se limpia,
    // que ocurre dentro de este mismo efecto. Agregarlo como dep crearia loop infinito.
    // El valor es estable durante la vida util del polling. Seguro omitir.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskData])

  function handleSend() {
    const trimmed = inputValue.trim()
    if (!trimmed || currentTaskId) return

    const userMsg: PlaygroundMessage = {
      id: generateId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInputValue('')
    runMutation.mutate(trimmed)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-1 pb-3 border-b">
        <Play className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-semibold">Agent Playground</span>
        <span className="text-xs text-muted-foreground ml-auto truncate max-w-[200px]">
          {role}
        </span>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-1 space-y-3 py-3 min-h-0">
          {messages.length === 0 && !isRunning && (
            <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
              <Play className="h-8 w-8 mb-2 opacity-40" />
              <p className="text-sm">Send a message to test your agent</p>
              <p className="text-xs mt-1">Responses appear here in real-time</p>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {isRunning && (
            <div className="flex items-center gap-2 py-2">
              <LoadingSpinner size="sm" />
              <span className="text-xs text-muted-foreground">
                Agent is thinking...
              </span>
            </div>
          )}
      </div>

      <div className="flex gap-2 pt-3 border-t">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={currentTaskId ? 'Agent is running...' : 'Type a message...'}
          disabled={!!currentTaskId}
          className="flex-1"
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={!inputValue.trim() || !!currentTaskId || runMutation.isPending}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: PlaygroundMessage }) {
  const [showFull, setShowFull] = useState(false)
  const isUser = message.role === 'user'
  const isError = message.role === 'error'
  const isLong = message.content.length > 2000
  const displayContent = isLong && !showFull
    ? message.content.slice(0, 2000)
    : message.content

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : isError
              ? 'bg-destructive/10 text-destructive border border-destructive/20'
              : 'bg-muted text-foreground'
        }`}
      >
        <div className="whitespace-pre-wrap break-words">{displayContent}</div>
        {isLong && (
          <Collapsible open={showFull} onOpenChange={setShowFull}>
            <CollapsibleTrigger asChild>
              <Button variant="link" size="sm" className="h-auto p-0 text-xs mt-1">
                {showFull ? 'Show less' : 'Show more'}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="whitespace-pre-wrap break-words mt-1">
                {message.content.slice(2000)}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
        {message.tokensUsed !== undefined && !isUser && (
          <div className="text-xs text-muted-foreground mt-1">
            Tokens: {message.tokensUsed}
          </div>
        )}
      </div>
    </div>
  )
}
