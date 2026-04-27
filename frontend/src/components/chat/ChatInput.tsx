import { useState, useRef, KeyboardEvent, ChangeEvent } from "react";
import { Send, Paperclip, X } from "lucide-react";
import { apiFetch } from "@/api/client";
import type { ChatMessage } from "@/types/chat";

interface Props {
  roomId: string;
  onSent: (msg: ChatMessage) => void;
}

export function ChatInput({ roomId, onSent }: Props) {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function send() {
    if (sending) return;
    if (!text.trim() && !file) return;
    setSending(true);
    try {
      let msg: ChatMessage;
      if (file) {
        const form = new FormData();
        form.append("file", file);
        if (text.trim()) form.append("content", text.trim());
        // Use raw fetch for multipart (apiFetch wraps JSON)
        const token = localStorage.getItem("gdf_token");
        const res = await fetch(
          `${import.meta.env.VITE_API_URL ?? ""}/api/chat/rooms/${roomId}/messages/upload`,
          {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: form,
          }
        );
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error((err as { detail?: string }).detail ?? "Upload failed");
        }
        msg = await res.json();
      } else {
        msg = await apiFetch<ChatMessage>(`/api/chat/rooms/${roomId}/messages`, {
          method: "POST",
          body: JSON.stringify({ content: text.trim() }),
        });
      }
      onSent(msg);
      setText("");
      setFile(null);
    } catch {
      // silently ignore; user can retry
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) setFile(f);
    e.target.value = "";
  }

  return (
    <div className="border-t border-c-border p-3 bg-c-surface">
      {file && (
        <div className="flex items-center gap-2 mb-2 bg-c-surface-2 rounded-lg px-3 py-2 text-sm text-slate-200">
          <Paperclip size={14} className="text-c-text-2 shrink-0" />
          <span className="truncate flex-1">{file.name}</span>
          <button onClick={() => setFile(null)} className="text-c-text-2 hover:text-c-text">
            <X size={14} />
          </button>
        </div>
      )}
      <div className="flex items-end gap-2">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="p-2 text-c-text-2 hover:text-c-text transition-colors shrink-0 mb-0.5"
          aria-label="Attach file"
        >
          <Paperclip size={18} />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*,video/*,.pdf,.doc,.docx,.txt"
          className="hidden"
          onChange={onFileChange}
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Message… (Enter to send, Shift+Enter for new line)"
          rows={1}
          className="flex-1 resize-none bg-c-surface-2 border border-c-border rounded-xl px-3 py-2 text-sm text-c-text placeholder:text-c-text-3 focus:outline-none focus:ring-1 focus:ring-emerald-500 max-h-28 overflow-y-auto"
          style={{ minHeight: 40 }}
        />
        <button
          type="button"
          onClick={send}
          disabled={sending || (!text.trim() && !file)}
          className="p-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 rounded-xl text-c-text transition-colors shrink-0 mb-0.5"
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
