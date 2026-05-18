'use client'

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Search,
  Inbox,
  AlertTriangle,
  Layers,
} from 'lucide-react'

import { api } from '@/lib/api'
import { TEMPLATE_CATEGORIES, TEMPLATE_CACHE_MS } from '@/lib/constants'
import { useDebounce } from '@/hooks/useDebounce'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'

interface TemplateInfo {
  id: string
  name: string
  description: string | null
  category: string
  suggested_tools: string[]
  max_iter: number
  is_system: boolean
  created_at?: string
}

export interface TemplateDetail extends TemplateInfo {
  soul_json: Record<string, unknown>
  updated_at?: string
}

interface TemplatePickerProps {
  onSelect: (template: TemplateDetail) => void
}

interface TemplateListResponse {
  templates: TemplateInfo[]
  count: number
}

export function TemplatePicker({ onSelect }: TemplatePickerProps) {
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [loadingId, setLoadingId] = useState<string | null>(null)

  const debouncedSearch = useDebounce(search, 300)

  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery<TemplateListResponse>({
    queryKey: ['templates'],
    queryFn: () => api.get('/api/templates'),
    staleTime: TEMPLATE_CACHE_MS,
  })

  const templates = useMemo(() => data?.templates ?? [], [data])

  const filtered = useMemo(() => {
    let result = templates
    if (selectedCategory) {
      result = result.filter((t) => t.category === selectedCategory)
    }
    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase()
      result = result.filter((t) => t.name.toLowerCase().includes(q))
    }
    return result
  }, [templates, selectedCategory, debouncedSearch])

  async function handleUseTemplate(template: TemplateInfo) {
    setLoadingId(template.id)
    try {
      const detail: TemplateDetail = await api.get(
        `/api/templates/${template.id}`
      )
      onSelect(detail)
    } catch {
      toast.error('Failed to load template details')
    } finally {
      setLoadingId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-2/3" />
            </CardHeader>
            <CardContent>
              <div className="flex gap-1">
                <Skeleton className="h-5 w-16" />
                <Skeleton className="h-5 w-12" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3">
        <EmptyState
          icon={<AlertTriangle className="mb-2 h-12 w-12" />}
          title="Failed to load templates"
          description="Check your connection and try again."
        />
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    )
  }

  if (!templates.length) {
    return (
      <EmptyState
        icon={<Inbox className="mb-2 h-12 w-12" />}
        title="No templates available"
        description="Run: fap templates seed"
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search templates..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <Badge
          variant={selectedCategory === null ? 'default' : 'secondary'}
          className="cursor-pointer"
          onClick={() => setSelectedCategory(null)}
        >
          All
        </Badge>
        {TEMPLATE_CATEGORIES.map((cat) => (
          <Badge
            key={cat}
            variant={selectedCategory === cat ? 'default' : 'secondary'}
            className="cursor-pointer"
            onClick={() => setSelectedCategory(cat)}
          >
            {cat}
          </Badge>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Search className="mb-2 h-12 w-12" />}
          title="No templates match your search"
        />
      ) : (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((template) => (
            <Card key={template.id}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Layers className="h-4 w-4 text-muted-foreground shrink-0" />
                  {template.name}
                </CardTitle>
                {template.description && (
                  <CardDescription className="line-clamp-2">
                    {template.description}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="info">{template.category}</Badge>
                  {template.suggested_tools.slice(0, 3).map((tool) => (
                    <Badge key={tool} variant="secondary">
                      {tool}
                    </Badge>
                  ))}
                  {template.suggested_tools.length > 3 && (
                    <Badge variant="outline">
                      +{template.suggested_tools.length - 3}
                    </Badge>
                  )}
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  variant="default"
                  size="sm"
                  className="w-full"
                  disabled={loadingId === template.id}
                  onClick={() => handleUseTemplate(template)}
                >
                  {loadingId === template.id ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    'Use Template'
                  )}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
