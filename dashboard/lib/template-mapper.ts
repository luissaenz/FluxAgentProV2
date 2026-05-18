import type { AgentFormData } from '@/lib/agent-schema'
import type { TemplateDetail } from '@/components/builder/TemplatePicker'

const VALID_PROVIDERS = ['groq', 'openai', 'anthropic', 'openrouter'] as const
type Provider = AgentFormData['llmProvider']

function mapProvider(provider?: string): Provider {
  return (VALID_PROVIDERS as readonly string[]).includes(provider ?? '')
    ? (provider as Provider)
    : 'groq'
}

export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData {
  const soul = template.soul_json ?? {}

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
