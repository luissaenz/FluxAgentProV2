'use client'

import { useState } from 'react'
import { Bot, User } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

interface AgentPersonalityCardProps {
  displayName: string
  role: string
  soulNarrative: string | null
  avatarUrl: string | null
  isLoading: boolean
}

/**
 * AgentPersonalityCard
 * 
 * Presenta la identidad visual y narrativa del agente.
 * Se prioriza la visualización de la identidad básica (Nombre, Avatar, Rol)
 * incluso si falta la narrativa descriptiva.
 */
export function AgentPersonalityCard({
  displayName,
  role,
  soulNarrative,
  avatarUrl,
  isLoading,
}: AgentPersonalityCardProps) {
  const [avatarError, setAvatarError] = useState(false)

  if (isLoading) {
    return (
      <Card className="overflow-hidden border-none bg-gradient-to-br from-card to-muted/20 shadow-lg">
        <CardContent className="space-y-4 p-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-16 w-16 rounded-2xl" />
            <div className="space-y-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-5 w-24" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const initial = displayName ? displayName.charAt(0).toUpperCase() : '?'
  const showAvatarPlaceholder = avatarError || !avatarUrl || avatarUrl.length === 0
  const hasNarrative = soulNarrative && soulNarrative.trim().length > 0

  return (
    <Card className="overflow-hidden border-none bg-gradient-to-br from-card to-muted/20 shadow-md transition-all hover:shadow-lg">
      <CardContent className="p-6">
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          {/* Avatar Section */}
          <div className="relative shrink-0">
            {showAvatarPlaceholder ? (
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-2xl font-bold text-white shadow-inner">
                {initial}
              </div>
            ) : (
              <div className="h-16 w-16 overflow-hidden rounded-2xl shadow-md">
                <img
                  src={avatarUrl}
                  alt={displayName}
                  className="h-full w-full object-cover"
                  onError={() => setAvatarError(true)}
                />
              </div>
            )}
            <div className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-lg bg-background shadow-sm ring-1 ring-border">
              <Bot className="h-3.5 w-3.5 text-primary" />
            </div>
          </div>

          {/* Identity & Narrative */}
          <div className="flex-1 space-y-3 min-w-0">
            <div>
              <h3 className="text-xl font-bold tracking-tight text-foreground truncate">
                {displayName}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="secondary" className="font-medium bg-primary/10 text-primary border-none">
                  {role}
                </Badge>
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <User className="h-3 w-3" />
                  Identidad Verificada
                </span>
              </div>
            </div>

            {hasNarrative ? (
              <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-line italic">
                "{soulNarrative}"
              </p>
            ) : (
              <p className="text-sm text-muted-foreground/60 italic">
                Este agente opera bajo una directiva técnica estándar sin narrativa de personalidad adicional.
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
