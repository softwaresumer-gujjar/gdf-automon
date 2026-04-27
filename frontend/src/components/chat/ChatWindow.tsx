import { useEffect, useRef } from "react";
import { Loader, ChevronUp } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { ChatBubble } from "./ChatBubble";
import { ChatInput } from "./ChatInput";
import type { ChatMessage } from "@/types/chat";

interface Props {
  roomId: string;
  roomName: string;
}

export function ChatWindow({ roomId, roomName }: Props) {
  const { messages, loading, hasMore, loadMore, appendMessage } = useChat(roomId);
  const bottomRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  function handleSent(msg: ChatMessage) {
    appendMessage(msg);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-c-border bg-c-surface shrink-0">
        <h2 className="font-semibold text-c-text text-sm truncate">{roomName}</h2>
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-0.5">
        {hasMore && (
          <div className="flex justify-center mb-2">
            <button
              onClick={loadMore}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
            >
              {loading ? (
                <Loader size={12} className="animate-spin" />
              ) : (
                <ChevronUp size={12} />
              )}
              Load older messages
            </button>
          </div>
        )}

        {loading && messages.length === 0 && (
          <div className="flex justify-center py-8">
            <Loader size={20} className="text-emerald-400 animate-spin" />
          </div>
        )}

        {!loading && messages.length === 0 && (
          <div className="text-center text-c-text-3 text-sm py-12">
            No messages yet. Start the conversation!
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatBubble
            key={msg.id}
            message={msg}
            prevMessage={i > 0 ? messages[i - 1] : undefined}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      <ChatInput roomId={roomId} onSent={handleSent} />
    </div>
  );
}
