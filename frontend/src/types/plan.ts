export interface Plan {
  id: string;
  name: string;
  description: string | null;
  sensor_id: string;
  channel: string;
  target_value: number;
  target_unit: string | null;
  lower_limit: number | null;
  upper_limit: number | null;
  enabled: boolean;
}

export interface PlanAction {
  id: string;
  plan_id: string;
  action_type: "notification" | "sms" | "call" | "reminder";
  trigger_on: "above_upper" | "below_lower" | "outside_range" | "any_breach";
  message_template: string;
  recipient_user_ids: string[] | null;
  config: Record<string, string>;
  enabled: boolean;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  deadline: string | null;
  status: "open" | "submitted" | "done" | "rejected";
  created_by_id: string | null;
  reviewed_by_id: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  submitted_by_id: string | null;
  submitted_at: string | null;
  completion_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskAttachment {
  id: string;
  task_id: string;
  filename: string;
  original_name: string;
  file_type: "image" | "video" | "document" | "other";
  file_size: number | null;
}

export interface TaskDetail extends Task {
  assignees: { id: string; full_name: string; email: string }[];
  attachments: TaskAttachment[];
}
