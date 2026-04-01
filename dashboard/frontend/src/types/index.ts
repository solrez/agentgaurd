export type ActionType = 'api_call' | 'db_query' | 'file_write' | 'file_read' | 'send_message' | 'code_execution' | 'tool_call' | 'http_request' | 'custom'
export type Decision = 'execute' | 'block' | 'modify' | 'escalate'

export interface AuditEntry {
  timestamp: number
  timestamp_iso: string
  trace_id: string
  agent_id: string
  action_type: ActionType
  target: string
  decision: Decision
  reasons: string[]
  validators_run: string[]
  pipeline_latency_ms: number
  metadata: Record<string, unknown>
}

export interface AuditListResponse {
  entries: AuditEntry[]
  total: number
  page: number
  page_size: number
}

export interface OverviewMetrics {
  total_actions: number
  block_rate: number
  avg_latency_ms: number
  active_agents: number
  actions_last_hour: number
}

export interface DecisionDistribution {
  decision: string
  count: number
}

export interface TimeseriesPoint {
  timestamp: string
  count: number
}

export interface TopTarget {
  target: string
  block_count: number
  total_count: number
  block_rate: number
}

export interface ValidatorEffectiveness {
  validator_name: string
  times_run: number
  blocks_triggered: number
}

export interface LatencyBucket {
  range_label: string
  count: number
}

export interface ValidatorConfig {
  type: string
  enabled: boolean
  settings: Record<string, unknown>
}

export interface GuardConfig {
  guard: Record<string, unknown>
  validators: ValidatorConfig[]
  audit: Record<string, unknown>
  llm: Record<string, unknown> | null
  raw_yaml: string
}

export interface EscalationEntry {
  trace_id: string
  timestamp: number
  timestamp_iso: string
  agent_id: string
  action_type: string
  target: string
  reasons: string[]
  metadata: Record<string, unknown>
  status: string
}
