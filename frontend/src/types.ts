export type TaskLane = 'now' | 'next' | 'later';

export type TaskStatus = 'pending_approval' | 'approved' | 'auto_approved' | 'rejected';

export type ExecutionStatus = 'idle' | 'executing' | 'executed' | 'draft_ready' | 'failed' | 'no_executor';

export interface TokenUsage {
  audio?: number;
  text?: number;
  candidate?: number;
  total?: number;
}

export interface Task {
  id: string;
  task: string;
  lane: TaskLane;
  class: string;
  status: TaskStatus;
  execution_status?: ExecutionStatus;
  artifact?: string | null;
  grounded?: boolean;
  sources?: string[];
  condition?: string;
  check_after?: number;
  evidence?: string;
  correlation_id?: string;
  created_at?: string | number | null;
  executed_at?: string | number | null;
  execution_error?: string | null;
  execution_seconds?: number;
  execution_usage?: TokenUsage;
  usage?: TokenUsage;
}

export interface TaskSummary {
  total: number;
  pending: number;
  watching: number;
  auto_classes: string[];
  correlation_id: string;
}

export interface ProcessAudioResponse {
  tasks: Task[];
  auto_execute?: Array<{ id: string; data: Task; correlation_id: string }>;
  summary?: TaskSummary;
  usage?: TokenUsage;
  error?: string;
  raw?: string;
}

export interface ClassInfo {
  class: string;
  label: string;
  // fields from registry.describe()
  has_executor: boolean;
  executor_kind: string | null;
  draft_only: boolean;
  reversibility: string;
  ui_label: string;
  ui_description: string;
  ui_output_label: string;
  ui_icon_name: string;
  description?: string;
  approvals: number;
  auto: boolean;
  threshold?: number | 'never';
}

export interface TrustLadderMap {
  [taskClass: string]: number;
}
