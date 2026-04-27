export interface SensorReading {
  sensor_id: string;
  channel: string;
  value: number;
  unit: string;
  ts: string;
}

export interface ChatMessagePayload {
  id: string;
  room_id: string;
  sender: { id: string | null; full_name: string; email: string };
  content: string | null;
  attachments: Array<{
    id: string;
    original_name: string;
    file_type: string;
    file_size: number;
    mime_type: string;
    url: string;
  }>;
  created_at: string;
}

export interface ServerToClientEvents {
  "sensor:reading": (reading: SensorReading) => void;
  "sensor:status": (data: { sensor_id: string; status: string }) => void;
  "chat:message": (message: ChatMessagePayload) => void;
}

export interface ClientToServerEvents {
  "subscribe:sensor": (sensor_id: string) => void;
  "unsubscribe:sensor": (sensor_id: string) => void;
  "chat:join": (room_id: string) => void;
  "chat:leave": (room_id: string) => void;
}
