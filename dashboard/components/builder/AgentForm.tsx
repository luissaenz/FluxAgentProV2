'use client'

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { toast } from 'sonner'

import { api } from '@/lib/api'
import { PROVIDER_MODELS } from '@/lib/constants'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Skeleton } from '@/components/ui/skeleton'
import { ToolMultiSelect } from '@/components/builder/ToolMultiSelect'

const agentFormSchema = z.object({
  role: z.string().min(1, 'Role is required'),
  goal: z.string().min(1, 'Goal is required'),
  backstory: z.string().min(1, 'Backstory is required'),
  llmProvider: z.enum(['groq', 'openai', 'anthropic', 'openrouter']),
  llmModel: z.string(),
  allowedTools: z.array(z.string()),
  maxIter: z.number().int().min(1).max(10),
  verbose: z.boolean(),
  reasoning: z.boolean(),
  injectDate: z.boolean(),
  memory: z.boolean(),
})

export type AgentFormData = z.infer<typeof agentFormSchema>

interface AgentFormProps {
  onSave?: (data: AgentFormData) => Promise<void>
  onClear?: () => void
  initialValues?: Partial<AgentFormData>
  templateData?: AgentFormData | null
}

interface ToolInfo {
  name: string
  label: string
  source: string
}

export function AgentForm({
  onSave,
  onClear,
  initialValues,
  templateData,
}: AgentFormProps) {
  const { orgId } = useCurrentOrg()

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AgentFormData>({
    resolver: zodResolver(agentFormSchema),
    defaultValues: {
      role: initialValues?.role ?? '',
      goal: initialValues?.goal ?? '',
      backstory: initialValues?.backstory ?? '',
      llmProvider: initialValues?.llmProvider ?? 'groq',
      llmModel: initialValues?.llmModel ?? 'llama-3.1-70b-versatile',
      allowedTools: initialValues?.allowedTools ?? [],
      maxIter: initialValues?.maxIter ?? 3,
      verbose: initialValues?.verbose ?? false,
      reasoning: initialValues?.reasoning ?? false,
      injectDate: initialValues?.injectDate ?? false,
      memory: initialValues?.memory ?? false,
    },
  })

  useEffect(() => {
    if (templateData) {
      reset({
        role: templateData.role,
        goal: templateData.goal,
        backstory: templateData.backstory,
        llmProvider: templateData.llmProvider,
        llmModel: templateData.llmModel,
        allowedTools: templateData.allowedTools,
        maxIter: templateData.maxIter,
        verbose: templateData.verbose,
        reasoning: templateData.reasoning,
        injectDate: templateData.injectDate,
        memory: templateData.memory,
      })
    }
  }, [templateData, reset])

  const llmProvider = watch('llmProvider')
  const allowedTools = watch('allowedTools')

  const {
    data: toolsResponse,
    isLoading: toolsLoading,
    isError: toolsError,
    refetch: refetchTools,
  } = useQuery<{ tools: ToolInfo[] }>({
    queryKey: ['tools-available', orgId],
    queryFn: () => api.get('/api/tools/available'),
    enabled: !!orgId,
  })

  const toolOptions = (toolsResponse?.tools ?? []).map((t) => ({
    value: t.name,
    label: t.label || t.name,
    source: t.source || 'local',
  }))

  const availableModels = PROVIDER_MODELS[llmProvider] ?? []

  async function onSubmit(data: AgentFormData) {
    if (!orgId) {
      toast.error('Select an organization first')
      return
    }

    const payload = {
      role: data.role,
      soul_json: {
        goal: data.goal,
        backstory: data.backstory,
        llm_provider: data.llmProvider,
        llm_model: data.llmModel,
        verbose: data.verbose,
        reasoning: data.reasoning,
        inject_date: data.injectDate,
        memory: data.memory,
      },
      allowed_tools: data.allowedTools,
      max_iter: data.maxIter,
    }

    try {
      if (onSave) {
        await onSave(data)
      } else {
        await api.post('/agents', payload)
      }
      toast.success('Agent saved')
      reset()
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to save agent'
      if (message.toLowerCase().includes('already exists')) {
        toast.error(`Role already exists in this organization`)
      } else if (message.toLowerCase().includes('connection')) {
        toast.error('Failed to save agent. Check your connection.')
      } else {
        toast.error(message)
      }
    }
  }

  function handleClear() {
    reset({
      role: '',
      goal: '',
      backstory: '',
      llmProvider: 'groq',
      llmModel: 'llama-3.1-70b-versatile',
      allowedTools: [],
      maxIter: 3,
      verbose: false,
      reasoning: false,
      injectDate: false,
      memory: false,
    })
    onClear?.()
  }

  useEffect(() => {
    if (availableModels.length > 0 && !availableModels.includes(watch('llmModel'))) {
      setValue('llmModel', availableModels[0])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llmProvider])

  if (!orgId) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
        <p className="text-sm">Select an organization first</p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 overflow-y-auto px-1">
      <div className="space-y-1.5">
        <Label htmlFor="role">Role *</Label>
        <Input id="role" placeholder="Code Reviewer" {...register('role')} />
        {errors.role && (
          <p className="text-xs text-destructive">{errors.role.message}</p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="goal">Goal *</Label>
        <Textarea id="goal" placeholder="Review pull requests for security issues" rows={2} {...register('goal')} />
        {errors.goal && (
          <p className="text-xs text-destructive">{errors.goal.message}</p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="backstory">Backstory *</Label>
        <Textarea id="backstory" placeholder="Senior security engineer with 10 years experience" rows={2} {...register('backstory')} />
        {errors.backstory && (
          <p className="text-xs text-destructive">{errors.backstory.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>LLM Provider</Label>
          <Select
            value={llmProvider}
            onValueChange={(v) => setValue('llmProvider', v as AgentFormData['llmProvider'])}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              {Object.keys(PROVIDER_MODELS).map((provider) => (
                <SelectItem key={provider} value={provider}>
                  {provider}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label>LLM Model</Label>
          <Select
            value={watch('llmModel')}
            onValueChange={(v) => setValue('llmModel', v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {availableModels.map((model) => (
                <SelectItem key={model} value={model}>
                  {model}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label>Tools</Label>
        {toolsLoading ? (
          <Skeleton className="h-9 w-full" />
        ) : toolsError ? (
          <div className="flex items-center gap-2">
            <p className="text-xs text-muted-foreground">Failed to load tools.</p>
            <Button type="button" variant="outline" size="sm" onClick={() => refetchTools()}>
              Retry
            </Button>
          </div>
        ) : (
          <ToolMultiSelect
            options={toolOptions}
            values={allowedTools}
            onChange={(v) => setValue('allowedTools', v)}
          />
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="maxIter">Max Iterations</Label>
        <Input
          id="maxIter"
          type="number"
          min={1}
          max={10}
          {...register('maxIter', { valueAsNumber: true })}
        />
        {errors.maxIter && (
          <p className="text-xs text-destructive">{errors.maxIter.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label>Toggles</Label>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="verbose" className="cursor-pointer text-sm font-normal">Verbose</Label>
            <Switch
              id="verbose"
              checked={watch('verbose')}
              onCheckedChange={(v) => setValue('verbose', v)}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="reasoning" className="cursor-pointer text-sm font-normal">Reasoning</Label>
            <Switch
              id="reasoning"
              checked={watch('reasoning')}
              onCheckedChange={(v) => setValue('reasoning', v)}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="injectDate" className="cursor-pointer text-sm font-normal">Inject Date</Label>
            <Switch
              id="injectDate"
              checked={watch('injectDate')}
              onCheckedChange={(v) => setValue('injectDate', v)}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="memory" className="cursor-pointer text-sm font-normal">Memory</Label>
            <Switch
              id="memory"
              checked={watch('memory')}
              onCheckedChange={(v) => setValue('memory', v)}
            />
          </div>
        </div>
      </div>

      <div className="flex gap-2 pt-2">
        <Button type="submit" disabled={isSubmitting} className="flex-1">
          {isSubmitting ? <LoadingSpinner size="sm" className="mr-2" /> : null}
          Save Agent
        </Button>
        <Button type="button" variant="outline" onClick={handleClear}>
          Clear
        </Button>
      </div>
    </form>
  )
}

