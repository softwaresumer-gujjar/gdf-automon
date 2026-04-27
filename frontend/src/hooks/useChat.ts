/**
 * Real-time chat hook.
 * Fetches message history via REST, joins the Socket.io room for the given
 * room_id, and appends live messages as they arrive.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { io, Socket } from "socket.io-client";
import { apiFetch } from "@/api/client";
import type { ChatMessage } from "@/types/chat";

const REALTIME_URL = import.meta.env.VITE_REALTIME_URL ?? "";

type ChatSocket = Socket<
  { "chat:message": (msg: ChatMessage) => void },
  { "chat:join": (id: string) => void; "chat:leave": (id: string) => void }
>;

let chatSocket: ChatSocket | null = null;

function getChatSocket(): ChatSocket {
  if (!chatSocket) {
    chatSocket = io(REALTIME_URL, {
      path: "/socket.io",
      transports: ["websocket"],
      reconnectionDelay: 1000,
      reconnectionAttempts: Infinity,
    }) as ChatSocket;
  }
  return chatSocket;
}

export function useChat(roomId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const socketRef = useRef<ChatSocket | null>(null);

  // Fetch initial history
  useEffect(() => {
    if (!roomId) return;
    setMessages([]);
    setHasMore(true);
    setLoading(true);
    apiFetch<ChatMessage[]>(`/api/chat/rooms/${roomId}/messages?limit=50`)
      .then((msgs) => {
        setMessages(msgs);
        setHasMore(msgs.length === 50);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [roomId]);

  // Join socket room
  useEffect(() => {
    if (!roomId) return;
    const socket = getChatSocket();
    socketRef.current = socket;

    socket.emit("chat:join", roomId);

    const handler = (msg: ChatMessage) => {
      if (msg.room_id !== roomId) return;
      setMessages((prev) => {
        // Deduplicate
        if (prev.some((m) => m.id === msg.id)) return prev;
        return [...prev, msg];
      });
    };
    socket.on("chat:message", handler);

    return () => {
      socket.emit("chat:leave", roomId);
      socket.off("chat:message", handler);
    };
  }, [roomId]);

  // Load older messages (cursor-based pagination)
  const loadMore = useCallback(async () => {
    if (!roomId || !hasMore || loading || messages.length === 0) return;
    setLoading(true);
    try {
      const oldest = messages[0];
      const older = await apiFetch<ChatMessage[]>(
        `/api/chat/rooms/${roomId}/messages?limit=50&before_id=${oldest.id}`
      );
      setHasMore(older.length === 50);
      setMessages((prev) => [...older, ...prev]);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [roomId, hasMore, loading, messages]);

  // Optimistic append after sending
  const appendMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => {
      if (prev.some((m) => m.id === msg.id)) return prev;
      return [...prev, msg];
    });
  }, []);

  return { messages, loading, hasMore, loadMore, appendMessage };
}
