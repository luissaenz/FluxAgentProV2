'use client'

import { useState, useRef, useEffect } from 'react'
import { api } from '@/lib/api'
import { Send } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ArchitectPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const response = await api.post('/chat/architect', {
        message: userMsg,
        conversation_id: conversationId,
      })

      setConversationId(response.conversation_id)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.reply || response.status },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <h2 className="mb-4 text-2xl font-bold tracking-tight">Chat MDC (Architect)</h2>

      <div className="flex-1 overflow-hidden rounded-lg border">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Describe el workflow que necesitas y el Arquitecto lo generará
          </div>
        ) : (
          <ScrollArea className="h-full p-4">
            <div className="space-y-4">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}
                >
                  <Card
                    className={cn(
                      'max-w-[80%]',
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    )}
                  >
                    <CardContent className="p-3">
                      <pre className="whitespace-pre-wrap font-sans text-sm">{msg.content}</pre>
                    </CardContent>
                  </Card>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-lg bg-muted px-4 py-2 text-sm text-muted-foreground">
                    Pensando...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        )}
      </div>

      <div className="mt-4 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Describe tu workflow..."
          disabled={loading}
          className="flex-1"
        />
        <Button onClick={handleSend} disabled={loading || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
