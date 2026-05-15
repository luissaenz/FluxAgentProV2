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
  created_at: string
  updated_at: string
}
