import { Download, FileText, Film } from "lucide-react";
import type { ChatMessage } from "@/types/chat";
import { useAuth } from "@/contexts/AuthContext";

const REALTIME_BASE = import.meta.env.VITE_API_URL ?? "";

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

function AttachmentPreview({ att }: { att: ChatMessage["attachments"][number] }) {
  const url = `${REALTIME_BASE}${att.url}`;
  if (att.file_type === "image") {
    return (
      <a href={url} target="_blank" rel="noreferrer" className="block mt-1">
        <img
          src={url}
          alt={att.original_name}
          className="max-w-xs max-h-48 rounded-lg object-cover border border-c-border"
        />
      </a>
    );
  }
  if (att.file_type === "video") {
    return (
      <video
        src={url}
        controls
        className="mt-1 max-w-xs rounded-lg border border-c-border"
        style={{ maxHeight: 200 }}
      />
    );
  }
  const Icon = att.file_type === "document" ? FileText : Film;
  return (
    <a
      href={url}
      download={att.original_name}
      className="mt-1 flex items-center gap-2 bg-slate-700/50 hover:bg-c-surface-2 rounded-lg px-3 py-2 text-sm text-slate-200 transition-colors max-w-xs"
    >
      <Icon size={16} className="text-c-text-2 shrink-0" />
      <span className="truncate">{att.original_name}</span>
      <Download size={14} className="text-c-text-2 shrink-0 ml-auto" />
    </a>
  );
}

interface Props {
  message: ChatMessage;
  prevMessage?: ChatMessage;
}

export function ChatBubble({ message, prevMessage }: Props) {
  const { user } = useAuth();
  const isMine = user?.id === message.sender.id;

  const showDateDivider =
    !prevMessage ||
    formatDate(prevMessage.created_at) !== formatDate(message.created_at);

  const showSender =
    !isMine &&
    (!prevMessage || prevMessage.sender.id !== message.sender.id || showDateDivider);

  return (
    <div>
      {showDateDivider && (
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-c-surface-2" />
          <span className="text-xs text-c-text-3">{formatDate(message.created_at)}</span>
          <div className="flex-1 h-px bg-c-surface-2" />
        </div>
      )}

      <div className={`flex gap-2 mb-1 ${isMine ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        {!isMine && (
          <div className="w-7 h-7 rounded-full bg-emerald-700 flex items-center justify-center text-xs font-bold text-c-text shrink-0 mt-1">
            {message.sender.full_name.charAt(0).toUpperCase()}
          </div>
        )}

        <div className={`flex flex-col max-w-[72%] ${isMine ? "items-end" : "items-start"}`}>
          {showSender && (
            <span className="text-xs text-c-text-2 mb-0.5 ml-1">{message.sender.full_name}</span>
          )}

          <div
            className={`rounded-2xl px-3 py-2 text-sm leading-relaxed ${
              isMine
                ? "bg-emerald-600 text-c-text rounded-tr-sm"
                : "bg-c-surface-2 text-c-text rounded-tl-sm"
            }`}
          >
            {message.content && <p className="whitespace-pre-wrap break-words">{message.content}</p>}
            {message.attachments.map((a) => (
              <AttachmentPreview key={a.id} att={a} />
            ))}
          </div>

          <span className="text-xs text-c-text-3 mt-0.5 mx-1">
            {formatTime(message.created_at)}
          </span>
        </div>
      </div>
    </div>
  );
}
