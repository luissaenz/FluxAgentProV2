'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import {
  ChevronRight,
  ChevronDown,
  GitBranch,
  ArrowDown,
  FolderTree,
  AlertCircle,
} from 'lucide-react'
import type { FlowHierarchyNode, FlowHierarchyResponse } from '@/lib/types'
import { formatFlowType } from '@/lib/presentation/fallback'

/**
 * FlowHierarchyView — Visualización en árbol de la jerarquía de flows.
 *
 * Phase 4: Muestra cómo se conectan los flows de negocio,
 * agrupados por categoría y con indicadores de dependencia.
 */
export function FlowHierarchyView() {
  const { data, isLoading, error } = useQuery<FlowHierarchyResponse>({
    queryKey: ['flows-hierarchy'],
    queryFn: () => api.get('/flows/hierarchy'),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            <Skeleton className="h-5 w-48" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3 text-destructive">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-medium">Error al cargar la jerarquía</p>
              <p className="text-sm text-muted-foreground mt-1">
                {(error as Error).message || 'No se pudo obtener la jerarquía de flows.'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data || Object.keys(data.hierarchy).length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FolderTree className="mb-3 h-12 w-12 text-muted-foreground/50" />
            <p className="text-sm font-medium">Sin jerarquía de flows</p>
            <p className="mt-1 text-xs text-muted-foreground">
              No hay flows registrados o no tienen metadata de jerarquía.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <GitBranch className="h-4 w-4" />
          Jerarquía de Flows
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.entries(data.categories).map(([category, flowTypes]) => (
          <CategoryTree
            key={category}
            category={category}
            flowTypes={flowTypes}
            hierarchy={data.hierarchy}
          />
        ))}
      </CardContent>
    </Card>
  )
}

// ── Componente interno: Árbol por categoría ─────────────────────

interface CategoryTreeProps {
  category: string
  flowTypes: string[]
  hierarchy: Record<string, FlowHierarchyNode>
}

function CategoryTree({ category, flowTypes, hierarchy }: CategoryTreeProps) {
  const [isOpen, setIsOpen] = useState(true)

  const displayName =
    category === 'sin_categoria'
      ? 'Sin categoría'
      : category.charAt(0).toUpperCase() + category.slice(1).replace(/_/g, ' ')

  return (
    <div className="rounded-lg border">
      <Button
        variant="ghost"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
      >
        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          <FolderTree className="h-4 w-4 text-muted-foreground" />
          <span>{displayName}</span>
          <Badge variant="secondary" className="text-xs">
            {flowTypes.length}
          </Badge>
        </div>
      </Button>

      {isOpen && (
        <div className="px-3 pb-3">
          <div className="space-y-2 pl-6">
            {flowTypes.map((flowType) => {
              const node = hierarchy[flowType]
              if (!node) return null
              return <FlowNode key={flowType} node={node} hierarchy={hierarchy} />
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Componente interno: Nodo individual de flow ─────────────────

interface FlowNodeProps {
  node: FlowHierarchyNode
  hierarchy: Record<string, FlowHierarchyNode>
}

function FlowNode({ node, hierarchy }: FlowNodeProps) {
  const hasDependencies = node.depends_on && node.depends_on.length > 0
  const isDependencyOf = Object.values(hierarchy).filter((other) =>
    other.depends_on?.includes(node.flow_type)
  )

  return (
    <div className="relative">
      {/* Línea conectora vertical */}
      <div className="absolute left-[-16px] top-0 h-full w-px bg-border" />

      <div className="rounded-lg border bg-card p-3 space-y-2 hover:border-primary/50 transition-all">
        {/* Header del nodo */}
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-primary" />
          <span className="text-sm font-semibold">{formatFlowType(node.flow_type)}</span>
          {node.category && (
            <Badge variant="outline" className="text-xs">
              {node.category}
            </Badge>
          )}
        </div>

        {/* Dependencias upstream */}
        {hasDependencies && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <ArrowDown className="h-3 w-3 rotate-180" />
            <span>Depende de:</span>
            {node.depends_on.map((dep) => (
              <Badge key={dep} variant="secondary" className="text-xs">
                {formatFlowType(dep)}
              </Badge>
            ))}
          </div>
        )}

        {/* Dependencias downstream */}
        {isDependencyOf.length > 0 && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <ArrowDown className="h-3 w-3" />
            <span>Requerido por:</span>
            {isDependencyOf.map((other) => (
              <Badge key={other.flow_type} variant="secondary" className="text-xs">
                {formatFlowType(other.flow_type)}
              </Badge>
            ))}
          </div>
        )}

        {/* Sin dependencias */}
        {!hasDependencies && isDependencyOf.length === 0 && (
          <p className="text-xs text-muted-foreground italic">
            Flow independiente (sin dependencias)
          </p>
        )}
      </div>
    </div>
  )
}
