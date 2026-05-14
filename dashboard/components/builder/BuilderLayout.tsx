'use client'

import { useState } from 'react'

import { BuilderCanvas } from '@/components/builder/BuilderCanvas'
import { AgentForm, type AgentFormData } from '@/components/builder/AgentForm'
import { TemplatePicker } from '@/components/builder/TemplatePicker'
import type { TemplateDetail } from '@/components/builder/TemplatePicker'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Layers } from 'lucide-react'

function mapTemplateToFormValues(template: TemplateDetail): AgentFormData {
  const soul = template.soul_json ?? {}
  const valid = ['groq', 'openai', 'anthropic', 'openrouter'] as const
  type Provider = AgentFormData['llmProvider']

  function mapProvider(provider?: string): Provider {
    return valid.includes(provider as Provider) ? (provider as Provider) : 'groq'
  }

  return {
    role: (soul.role as string) ?? template.name ?? '',
    goal: (soul.goal as string) ?? '',
    backstory: (soul.backstory as string) ?? template.description ?? '',
    llmProvider: mapProvider(soul.llm_provider as string),
    llmModel: (soul.llm_model as string) ?? 'llama-3.1-70b-versatile',
    allowedTools: template.suggested_tools ?? [],
    maxIter: template.max_iter ?? 3,
    verbose: (soul.verbose as boolean) ?? false,
    reasoning: (soul.reasoning as boolean) ?? false,
    injectDate: (soul.inject_date as boolean) ?? false,
    memory: (soul.memory as boolean) ?? false,
  }
}

export function BuilderLayout() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [templateData, setTemplateData] = useState<AgentFormData | null>(null)

  function handleSelectTemplate(template: TemplateDetail) {
    const mapped = mapTemplateToFormValues(template)
    setTemplateData(mapped)
    setDialogOpen(false)
  }

  function handleClear() {
    setTemplateData(null)
  }

  return (
    <div className="grid h-full gap-4 lg:grid-cols-[60%_40%]">
      <div className="min-h-0">
        <BuilderCanvas />
      </div>
      <div className="flex flex-col overflow-hidden rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">Agent Configuration</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDialogOpen(true)}
          >
            <Layers className="mr-1.5 h-4 w-4" />
            Templates
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <AgentForm
            templateData={templateData}
            onClear={handleClear}
          />
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              Template Library
            </DialogTitle>
          </DialogHeader>
          <TemplatePicker onSelect={handleSelectTemplate} />
        </DialogContent>
      </Dialog>
    </div>
  )
}
