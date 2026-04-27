export type AlertCondition = "gt" | "lt" | "eq" | "outside_range";
export type AlertSeverity = "info" | "warning" | "critical";

export interface AlertRule {
  id: string;
  sensor_id: string;
  channel: string;
  condition: AlertCondition;
  threshold?: number;
  threshold_max?: number;
  severity: AlertSeverity;
  enabled: boolean;
}

export interface ActiveAlert {
  id: string;
  rule_id: string;
  sensor_id: string;
  channel: string;
  triggered_value: number;
  severity: AlertSeverity;
  message: string;
  triggered_at: string;
  resolved_at?: string;
}
