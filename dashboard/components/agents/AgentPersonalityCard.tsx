'use client'

import { Bot, User } from 'lucide-react'
import { motion } from 'framer-motion'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar'

interface AgentPersonalityCardProps {
  displayName: string
  role: string
  soulNarrative: string | null
  avatarUrl: string | null
  isLoading: boolean
}

/**
 * AgentPersonalityCard (SOUL UI - Refined)
 * 
 * Presenta la identidad visual y narrativa del agente usando estándares Premium.
 * - Animaciones: Fade-in-up con Framer Motion.
 * - Avatar: Gestión de fallbacks con Radix UI.
 * - Estilo: Glassmorphism y gradientes sutiles.
 */
export function AgentPersonalityCard({
  displayName,
  role,
  soulNarrative,
  avatarUrl,
  isLoading,
}: AgentPersonalityCardProps) {
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
  const hasNarrative = soulNarrative && soulNarrative.trim().length > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      <Card className="overflow-hidden border-none bg-gradient-to-br from-card to-muted/20 shadow-md transition-all hover:shadow-lg">
        <CardContent className="p-6">
          <div className="flex flex-col gap-6 md:flex-row md:items-start">
            {/* Avatar Section */}
            <div className="relative shrink-0">
              <Avatar className="h-16 w-16 rounded-2xl shadow-md ring-1 ring-border/50">
                <AvatarImage 
                  src={avatarUrl || ''} 
                  alt={displayName} 
                  className="object-cover"
                />
                <AvatarFallback className="bg-gradient-to-tr from-violet-600 to-indigo-600 text-2xl font-bold text-white">
                  {initial}
                </AvatarFallback>
              </Avatar>
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
                  <span className="text-xs text-muted-foreground/80 flex items-center gap-1">
                    <User className="h-3 w-3" />
                    Identidad Verificada
                  </span>
                </div>
              </div>

              <div className="relative">
                {hasNarrative ? (
                  <p className="text-sm leading-relaxed text-muted-foreground/90 whitespace-pre-line italic relative z-10 px-1 border-l-2 border-primary/20">
                    "{soulNarrative}"
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground/60 italic">
                    Este agente opera bajo una directiva técnica estándar sin narrativa de personalidad adicional.
                  </p>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

