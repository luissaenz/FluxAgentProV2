'use client'

import { useState } from 'react'
import { Bot } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'

interface AgentPersonalityCardProps {
  displayName: string
  role: string
  soulNarrative: string | null
  avatarUrl: string | null
  isLoading: boolean
}

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
      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="flex items-center gap-3">
            <Skeleton className="h-12 w-12 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-24" />
            </div>
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    )
  }

  const hasNarrative = soulNarrative != null && soulNarrative.trim().length > 0

  if (!hasNarrative) {
    return (
      <EmptyState
        icon={<Bot className="mb-4 h-12 w-12 opacity-50" />}
        title="Sin personalidad definida"
        description="Este agente aún no tiene una personalidad narrativa definida."
      />
    )
  }

  const initial = displayName.charAt(0).toUpperCase()
  const showAvatarPlaceholder = avatarError || avatarUrl == null || avatarUrl.length === 0

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <div className="flex items-center gap-3">
          {showAvatarPlaceholder ? null : (
            <img
              src={avatarUrl}
              alt={displayName}
              className="h-12 w-12 rounded-full object-cover"
              onError={() => setAvatarError(true)}
            />
          )}
          {showAvatarPlaceholder && (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-600">
              <span className="text-lg font-semibold text-white">{initial}</span>
            </div>
          )}
          <div className="min-w-0">
            <div className="text-lg font-semibold leading-none">{displayName}</div>
            <Badge variant="outline" className="mt-1">
              {role}
            </Badge>
          </div>
        </div>
        <p className="text-sm text-muted-foreground whitespace-pre-line">
          {soulNarrative}
        </p>
      </CardContent>
    </Card>
  )
}
