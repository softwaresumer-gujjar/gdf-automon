export type SensorStatus = "active" | "paused" | "error";

export interface Channel {
  name: string;
  label: string;
  unit: string;
  value_type: "float" | "int" | "bool" | "string";
  min_value?: number;
  max_value?: number;
}

export interface SensorType {
  sensor_type: string;
  display_name: string;
  protocol: string;
  icon: string;
  config_schema: Record<string, unknown>;
  data_channels: Channel[];
}

export interface Sensor {
  id: string;
  name: string;
  sensor_type: string;
  protocol: string;
  config: Record<string, unknown>;
  status: SensorStatus;
  location?: string;
  description?: string;
}

export interface SensorReading {
  time: string;
  sensor_id: string;
  channel: string;
  value: number;
  unit: string;
}

export interface LiveReading {
  sensor_id: string;
  channel: string;
  value: number;
  unit: string;
  ts: string;
}
