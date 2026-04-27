import { useState, useEffect } from "react";
import { MessageSquare, Plus, Hash, Layers, Loader, Users } from "lucide-react";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { ChatWindow } from "@/components/chat/ChatWindow";
import type { ChatRoom } from "@/types/chat";

const ROOM_ICONS = {
  task: Layers,
  topic: Hash,
  general: MessageSquare,
};

// ── Create Room Modal ─────────────────────────────────────────────────────────
function CreateRoomModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState("");
  const [roomType, setRoomType] = useState<"topic" | "general">("topic");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCreate() {
    if (!name.trim()) return;
    setError("");
    setLoading(true);
    try {
      await apiFetch("/api/chat/rooms", {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), room_type: roomType }),
      });
      onCreated();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create room");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-c-surface border border-c-border rounded-xl p-6 w-full max-w-sm">
        <h3 className="font-semibold text-c-text mb-4">New Chat Room</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-c-text-2 mb-1">Room name</label>
            <input
              className="input-field w-full"
              placeholder="e.g. Milking Team"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-c-text-2 mb-1">Type</label>
            <select
              className="input-field w-full"
              value={roomType}
              onChange={(e) => setRoomType(e.target.value as "topic" | "general")}
            >
              <option value="topic">Topic (invite-only)</option>
              <option value="general">General (all users)</option>
            </select>
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="btn-secondary flex-1">Cancel</button>
          <button
            onClick={handleCreate}
            disabled={loading || !name.trim()}
            className="btn-primary flex-1 disabled:opacity-50"
          >
            {loading ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Room list item ────────────────────────────────────────────────────────────
function RoomItem({
  room,
  active,
  onClick,
}: {
  room: ChatRoom;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = ROOM_ICONS[room.room_type] ?? MessageSquare;
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
        active ? "bg-emerald-600/20 border border-emerald-600/40" : "hover:bg-c-surface-2"
      }`}
    >
      <Icon size={16} className={`mt-0.5 shrink-0 ${active ? "text-emerald-400" : "text-c-text-2"}`} />
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium truncate ${active ? "text-emerald-300" : "text-slate-200"}`}>
          {room.name}
        </p>
        {room.last_message && (
          <p className="text-xs text-c-text-3 truncate mt-0.5">
            {room.last_message.content ?? "📎 Attachment"}
          </p>
        )}
      </div>
      {room.message_count > 0 && (
        <span className="text-xs text-c-text-3 shrink-0 mt-0.5">
          {room.message_count}
        </span>
      )}
    </button>
  );
}

// ── Main Chat page ────────────────────────────────────────────────────────────
export function Chat() {
  const { user } = useAuth();
  const [rooms, setRooms] = useState<ChatRoom[]>([]);
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const isAdmin = user?.role === "admin" || user?.role === "super_admin";

  async function loadRooms() {
    try {
      const data = await apiFetch<ChatRoom[]>("/api/chat/rooms");
      setRooms(data);
      if (!activeRoomId && data.length > 0) setActiveRoomId(data[0].id);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadRooms(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const activeRoom = rooms.find((r) => r.id === activeRoomId);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader size={24} className="text-emerald-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-0px)] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 flex flex-col bg-c-surface border-r border-c-border">
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-border">
          <h1 className="font-semibold text-c-text text-sm">Chat</h1>
          {isAdmin && (
            <button
              onClick={() => setShowCreate(true)}
              className="p-1 text-c-text-2 hover:text-c-text transition-colors"
              aria-label="New room"
            >
              <Plus size={16} />
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {rooms.length === 0 ? (
            <p className="text-xs text-c-text-3 text-center py-6">No rooms yet</p>
          ) : (
            rooms.map((room) => (
              <RoomItem
                key={room.id}
                room={room}
                active={room.id === activeRoomId}
                onClick={() => setActiveRoomId(room.id)}
              />
            ))
          )}
        </div>

        {/* Room type legend */}
        <div className="px-3 py-3 border-t border-c-border space-y-1">
          {(
            [
              { Icon: Layers, label: "Task room", color: "text-blue-400" },
              { Icon: Hash, label: "Topic room", color: "text-purple-400" },
              { Icon: Users, label: "General room", color: "text-c-text-2" },
            ] as const
          ).map(({ Icon, label, color }) => (
            <div key={label} className="flex items-center gap-2 text-xs text-c-text-3">
              <Icon size={12} className={color} />
              {label}
            </div>
          ))}
        </div>
      </aside>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeRoom ? (
          <ChatWindow roomId={activeRoom.id} roomName={activeRoom.name} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-c-text-3 gap-3">
            <MessageSquare size={40} className="text-slate-700" />
            <p className="text-sm">Select a room to start chatting</p>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateRoomModal
          onClose={() => setShowCreate(false)}
          onCreated={loadRooms}
        />
      )}
    </div>
  );
}
