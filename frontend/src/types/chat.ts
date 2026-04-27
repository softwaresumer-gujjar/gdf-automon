export interface ChatSender {
  id: string | null;
  full_name: string;
  email: string;
}

export interface ChatAttachment {
  id: string;
  original_name: string;
  file_type: "image" | "video" | "document" | "other";
  file_size: number;
  mime_type: string;
  url: string;
}

export interface ChatMessage {
  id: string;
  room_id: string;
  sender: ChatSender;
  content: string | null;
  attachments: ChatAttachment[];
  created_at: string;
}

export interface ChatRoom {
  id: string;
  name: string;
  room_type: "task" | "topic" | "general";
  task_id: string | null;
  created_at: string;
  message_count: number;
  last_message: { content: string | null; created_at: string } | null;
}

export interface ChatRoomDetail extends ChatRoom {
  members: Array<{ id: string; full_name: string; email: string }>;
}
