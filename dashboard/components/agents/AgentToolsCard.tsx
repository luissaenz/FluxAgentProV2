'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { getToolMetadata, type ToolMetadata } from '@/lib/tool-registry-metadata'
import { Wrench, Clock, Shield, Key, AlertTriangle } from 'lucide-react'

interface AgentToolsCardProps {
  /** Lista de nombres técnicos de herramientas permitidas */
  allowedTools: string[]
  /** Credenciales asociadas al agente (del backend) */
  credentials: Array<{ tool: string; description: string | null }>
  isLoading?: boolean
}

/**
 * AgentToolsCard - Muestra las herramientas de un agente como un grid de tarjetas inteligentes.
 * 
 * Cada tarjeta muestra:
 * - Nombre legible (mapeado desde registry o formateado)
 * - Descripción narrativa
 * - Badges de "Requiere Aprobación", "Timeout", "Requiere Credencial"
 * 
 * SUPUESTO: Las herramientas con credenciales son aquellas que aparecen en el array
 * `credentials` del backend. Si una herramienta está en allowed_tools pero no en
 * credentials, no requiere credencial explícita.
 */
export function AgentToolsCard({
  allowedTools,
  credentials,
  isLoading = false,
}: AgentToolsCardProps) {
  // Crear un set de herramientas que requieren credencial
  const toolsWithCredentials = new Set(credentials.map(cred => cred.tool))

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            <Skeleton className="h-5 w-48" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!allowedTools || allowedTools.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Wrench className="mb-3 h-12 w-12 text-muted-foreground/50" />
            <p className="text-sm font-medium">Sin herramientas configuradas</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Este agente no tiene herramientas asignadas aún.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Agrupar herramientas por tags para mejor organización visual
  const toolsByCategory = groupToolsByCategory(allowedTools)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Wrench className="h-4 w-4" />
          Herramientas y Capacidades
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.entries(toolsByCategory).map(([category, tools]) => (
          <div key={category} className="space-y-2">
            {category !== 'Sin categoría' && (
              <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {category}
              </h4>
            )}
            <div className="grid gap-3 md:grid-cols-2">
              {tools.map((toolName) => {
                const metadata = getToolMetadata(toolName)
                const requiresCredential = toolsWithCredentials.has(toolName)
                const credential = credentials.find(
                  cred => cred.tool === toolName
                )

                return (
                  <ToolCard
                    key={toolName}
                    toolName={toolName}
                    metadata={metadata}
                    requiresCredential={requiresCredential}
                    credentialDescription={credential?.description}
                  />
                )
              })}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// ── Componente interno para cada tarjeta de herramienta ───────────────────

interface ToolCardProps {
  toolName: string
  metadata: ToolMetadata
  requiresCredential: boolean
  credentialDescription: string | null | undefined
}

function ToolCard({
  toolName,
  metadata,
  requiresCredential,
  credentialDescription,
}: ToolCardProps) {
  return (
    <div className="rounded-lg border p-3 space-y-2 hover:border-primary/50 transition-colors">
      {/* Header: nombre y badges */}
      <div className="flex items-start justify-between gap-2">
        <h5 className="text-sm font-semibold leading-tight">
          {metadata.displayName}
        </h5>
        <div className="flex shrink-0 flex-wrap items-center gap-1">
          {metadata.requiresApproval && (
            <Badge
              variant="outline"
              className="text-[10px] bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800"
            >
              <Shield className="mr-1 h-3 w-3" />
              Aprobación
            </Badge>
          )}
          {requiresCredential && (
            <Badge
              variant="outline"
              className="text-[10px] bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800"
            >
              <Key className="mr-1 h-3 w-3" />
              Credencial
            </Badge>
          )}
        </div>
      </div>

      {/* Descripción */}
      <p className="text-xs text-muted-foreground leading-relaxed">
        {metadata.description}
      </p>

      {/* Footer: tags y timeout */}
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-1">
          {metadata.tags?.slice(0, 3).map((tag) => (
            <Badge
              key={tag}
              variant="secondary"
              className="text-[10px] px-1.5 py-0"
            >
              {tag}
            </Badge>
          ))}
          {metadata.tags && metadata.tags.length > 3 && (
            <Badge
              variant="secondary"
              className="text-[10px] px-1.5 py-0"
            >
              +{metadata.tags.length - 3}
            </Badge>
          )}
        </div>
        {metadata.timeoutSeconds && (
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <Clock className="h-3 w-3" />
            {metadata.timeoutSeconds}s
          </span>
        )}
      </div>

      {/* Descripción de credencial si existe */}
      {credentialDescription && (
        <div className="mt-1 flex items-start gap-1 rounded bg-muted/50 px-2 py-1.5">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" />
          <p className="text-[10px] text-muted-foreground leading-snug">
            {credentialDescription}
          </p>
        </div>
      )}
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────

/**
 * Agrupa herramientas por su primer tag para organización visual.
 * Si no tiene tags, las pone en "Sin categoría".
 */
function groupToolsByCategory(tools: string[]): Record<string, string[]> {
  const grouped: Record<string, string[]> = {}

  for (const toolName of tools) {
    const metadata = getToolMetadata(toolName)
    const category = metadata.tags?.[0] ?? 'Sin categoría'
    
    if (!grouped[category]) {
      grouped[category] = []
    }
    grouped[category].push(toolName)
  }

  return grouped
}
