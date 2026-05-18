import * as z from 'zod'

export const agentFormSchema = z.object({
  role: z.string().min(1, 'Role is required'),
  goal: z.string().min(10, 'Goal must be at least 10 characters'),
  backstory: z.string().min(10, 'Backstory must be at least 10 characters'),
  llmProvider: z.string(),
  llmModel: z.string(),
  allowedTools: z.array(z.string()),
  maxIter: z.number().int().min(1).max(10),
  verbose: z.boolean(),
  reasoning: z.boolean(),
  injectDate: z.boolean(),
  memory: z.boolean(),
})

export type AgentFormData = z.infer<typeof agentFormSchema>
