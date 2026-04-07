export interface Task {
  task_id: string
  org_id: string
  flow_type: string
  status: TaskStatus
  result: Record<string, unknown> | null
  error: string | null
  created_at: string
  updated_at: string
}

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'awaiting_approval'
  | 'rejected'
  | 'cancelled'

export interface PaginatedTasks {
  items: Task[]
  total: number
}

export interface Approval {
  id: string
  org_id: string
  task_id: string
  flow_type: string
  description: string
  payload: Record<string, unknown>
  status: 'pending' | 'approved' | 'rejected'
  decided_by: string | null
  decided_at: string | null
  expires_at: string | null
  created_at: string
}

export interface DomainEvent {
  id: string
  org_id: string
  aggregate_type: string
  aggregate_id: string
  event_type: string
  payload: Record<string, unknown>
  actor: string
  sequence: number
  created_at: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
}

export interface OrgMember {
  id: string
  org_id: string
  user_id: string
  email: string
  role: OrgRole
  is_active: boolean
  created_at: string
}

export type OrgRole = 'fap_admin' | 'org_owner' | 'org_operator'

export interface WorkflowTemplate {
  id: string
  org_id: string
  name: string
  description: string
  flow_type: string
  definition: Record<string, unknown>
  version: number
  status: 'draft' | 'active' | 'archived'
  execution_count: number
  last_executed: string | null
  created_at: string
  updated_at: string
}

export interface Agent {
  id: string
  org_id: string
  role: string
  is_active: boolean
  soul_json: Record<string, unknown>
  allowed_tools: string[]
  max_iter: number
  model?: string
  created_at: string
  updated_at: string
}

// ── Metricas del sistema agentino ─────────────────────────

export interface OverviewMetrics {
  tasks: {
    total: number
    by_status: Record<string, number>
  }
  tokens: {
    total: number
  }
  approvals: {
    pending: number
  }
  events: {
    recent: DomainEvent[]
  }
}

export interface FlowTypeMetrics {
  flow_type: string
  total_runs: number
  completed: number
  failed: number
  running: number
  awaiting_approval: number
  pending: number
  total_tokens: number
  avg_tokens: number
  last_run_at: string | null
}

export interface FlowRun {
  id: string
  flow_type: string
  status: TaskStatus
  tokens_used: number
  created_at: string
  updated_at: string
  error: string | null
  correlation_id: string | null
}

// ── Tickets ─────────────────────────

export type TicketStatus =
  | 'backlog'
  | 'todo'
  | 'in_progress'
  | 'done'
  | 'blocked'
  | 'cancelled'

export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface Ticket {
  id: string
  org_id: string
  title: string
  description: string | null
  flow_type: string | null
  priority: TicketPriority
  status: TicketStatus
  input_data: Record<string, unknown> | null
  task_id: string | null
  created_by: string | null
  assigned_to: string | null
  notes: string | null
  created_at: string
  updated_at: string
  resolved_at: string | null
}

export interface TicketCreate {
  title: string
  description?: string
  flow_type?: string
  priority?: TicketPriority
  input_data?: Record<string, unknown>
  assigned_to?: string
}

export interface TicketUpdate {
  status?: TicketStatus
  notes?: string
  assigned_to?: string
}

// ── Agente detallado con metricas ─────────────────────────

export interface AgentDetail {
  agent: Agent
  metrics: {
    total_tokens: number
    tasks_by_status: Record<string, number>
    recent_tasks: Array<{
      id: string
      flow_type: string
      status: TaskStatus
      tokens_used: number
      created_at: string
      updated_at: string
      error: string | null
    }>
  }
  credentials: Array<{
    tool: string
    description: string | null
  }>
}
