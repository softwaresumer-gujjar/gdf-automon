import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, CheckCircle, XCircle, Clock, AlertCircle,
  Paperclip, Trash2, Download, Image, Video, FileText, File,
  Users, Calendar, MessageSquare,
} from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";
import { apiFetch } from "@/api/client";
import { API_BASE } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { usePermissions } from "@/hooks/usePermissions";
import { ChatWindow } from "@/components/chat/ChatWindow";
import type { TaskDetail } from "@/types/plan";

const STATUS_CONFIG = {
  open: { label: "Open", icon: AlertCircle, color: "text-blue-400" },
  submitted: { label: "Under Review", icon: Clock, color: "text-yellow-400" },
  done: { label: "Done", icon: CheckCircle, color: "text-emerald-400" },
  rejected: { label: "Returned", icon: XCircle, color: "text-red-400" },
} as const;

function AttachmentIcon({ type }: { type: string }) {
  if (type === "image") return <Image size={16} className="text-blue-400" />;
  if (type === "video") return <Video size={16} className="text-purple-400" />;
  if (type === "document") return <FileText size={16} className="text-yellow-400" />;
  return <File size={16} className="text-c-text-2" />;
}

function formatBytes(n: number | null): string {
  if (n == null) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const { isAdmin } = usePermissions();
  const fileRef = useRef<HTMLInputElement>(null);

  const [tab, setTab] = useState<"details" | "chat">("details");
  const [chatRoomId, setChatRoomId] = useState<string | null>(null);
  const [submitNote, setSubmitNote] = useState("");
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [reviewNote, setReviewNote] = useState("");
  const [showReviewForm, setShowReviewForm] = useState(false);

  const { data: task, isLoading, error } = useQuery<TaskDetail>({
    queryKey: ["task", id],
    queryFn: () => apiFetch(`/api/tasks/${id}`),
  });

  const submit = useMutation({
    mutationFn: () =>
      apiFetch(`/api/tasks/${id}/submit`, { method: "POST", body: JSON.stringify({ completion_note: submitNote }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["task", id] }); qc.invalidateQueries({ queryKey: ["tasks"] }); setShowSubmitForm(false); },
  });

  const review = useMutation({
    mutationFn: (approved: boolean) =>
      apiFetch(`/api/tasks/${id}/review`, { method: "POST", body: JSON.stringify({ approved, review_note: reviewNote }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["task", id] }); qc.invalidateQueries({ queryKey: ["tasks"] }); setShowReviewForm(false); },
  });

  const uploadFile = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const token = localStorage.getItem("gdf_token");
      const res = await fetch(`${API_BASE}/api/tasks/${id}/attachments`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      });
      if (!res.ok) throw new Error("Upload failed");
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["task", id] }),
  });

  const deleteAttachment = useMutation({
    mutationFn: (attId: string) =>
      apiFetch(`/api/tasks/${id}/attachments/${attId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["task", id] }),
  });

  // Lazy-load chat room ID when tab is opened
  useEffect(() => {
    if (tab === "chat" && id && !chatRoomId) {
      apiFetch<{ id: string }>(`/api/chat/rooms/task/${id}`)
        .then((room) => setChatRoomId(room.id))
        .catch(() => {});
    }
  }, [tab, id, chatRoomId]);

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="p-6 text-center text-c-text-2">
        <p>Task not found.</p>
        <Link to="/tasks" className="text-emerald-400 text-sm mt-2 block">← Back to tasks</Link>
      </div>
    );
  }

  const cfg = STATUS_CONFIG[task.status];
  const Icon = cfg.icon;
  const isAssigned = task.assignees.some((a) => a.id === user?.id);
  const canSubmit = (isAssigned || isAdmin) && (task.status === "open" || task.status === "rejected");
  const canReview = isAdmin && task.status === "submitted";
  const isDone = task.status === "done";

  return (
    <div className="flex flex-col h-full">
      {/* Back + Tabs */}
      <div className="px-4 md:px-6 pt-4 md:pt-6 bg-c-bg border-b border-c-border shrink-0">
        <button type="button" onClick={() => navigate("/tasks")}
          className="flex items-center gap-1.5 text-sm text-c-text-2 hover:text-c-text mb-4 transition-colors">
          <ArrowLeft size={16} /> Back to tasks
        </button>
        <div className="flex gap-1">
          {(
            [
              { key: "details", label: "Details", icon: Paperclip },
              { key: "chat", label: "Chat", icon: MessageSquare },
            ] as const
          ).map(({ key, label, icon: TabIcon }) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                tab === key
                  ? "bg-c-surface text-emerald-400 border-b-2 border-emerald-500"
                  : "text-c-text-2 hover:text-c-text"
              }`}
            >
              <TabIcon size={14} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Chat tab */}
      {tab === "chat" && (
        <div className="flex-1 overflow-hidden">
          {chatRoomId ? (
            <ChatWindow roomId={chatRoomId} roomName={`Task: ${task?.title ?? ""}`} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
      )}

      {/* Details tab */}
      {tab === "details" && (
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pb-24 md:pb-6 w-full">

      {/* Header */}
      <div className="bg-c-surface border border-c-border rounded-xl p-5 mb-4">
        <div className="flex items-start gap-3 mb-3">
          <Icon size={20} className={`${cfg.color} mt-0.5 shrink-0`} />
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-bold text-c-text">{task.title}</h1>
            <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
          </div>
        </div>

        {task.description && (
          <p className="text-c-text-2 text-sm mb-3 whitespace-pre-wrap">{task.description}</p>
        )}

        <div className="space-y-1.5">
          {task.deadline && (
            <div className="flex items-center gap-2 text-xs text-c-text-2">
              <Calendar size={13} />
              <span>Due: {format(new Date(task.deadline), "PPP p")} ({formatDistanceToNow(new Date(task.deadline), { addSuffix: true })})</span>
            </div>
          )}
          {task.assignees.length > 0 && (
            <div className="flex items-center gap-2 text-xs text-c-text-2">
              <Users size={13} />
              <span>{task.assignees.map((a) => a.full_name).join(", ")}</span>
            </div>
          )}
          <p className="text-xs text-c-text-3">Created {formatDistanceToNow(new Date(task.created_at))} ago</p>
        </div>
      </div>

      {/* Completion note */}
      {task.completion_note && (
        <div className="bg-blue-950/40 border border-blue-800/50 rounded-xl p-4 mb-4">
          <p className="text-xs font-semibold text-blue-300 mb-1">Completion note</p>
          <p className="text-sm text-c-text-2">{task.completion_note}</p>
          {task.submitted_at && (
            <p className="text-xs text-c-text-3 mt-1">Submitted {format(new Date(task.submitted_at), "PPP")}</p>
          )}
        </div>
      )}

      {/* Review note */}
      {task.review_note && (
        <div className={`border rounded-xl p-4 mb-4 ${task.status === "done" ? "bg-emerald-950/30 border-emerald-800/50" : "bg-red-950/30 border-red-800/50"}`}>
          <p className={`text-xs font-semibold mb-1 ${task.status === "done" ? "text-emerald-300" : "text-red-300"}`}>
            {task.status === "done" ? "Approved" : "Returned"} — reviewer note
          </p>
          <p className="text-sm text-c-text-2">{task.review_note}</p>
          {task.reviewed_at && (
            <p className="text-xs text-c-text-3 mt-1">{format(new Date(task.reviewed_at), "PPP")}</p>
          )}
        </div>
      )}

      {/* Attachments */}
      <div className="bg-c-surface border border-c-border rounded-xl p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-c-text flex items-center gap-2">
            <Paperclip size={14} /> Attachments ({task.attachments.length})
          </h2>
          {!isDone && (
            <>
              <input ref={fileRef} type="file" className="hidden" multiple aria-label="Upload task attachment"
                onChange={(e) => {
                  Array.from(e.target.files ?? []).forEach((f) => uploadFile.mutate(f));
                  e.target.value = "";
                }}
              />
              <button type="button"
                onClick={() => fileRef.current?.click()}
                disabled={uploadFile.isPending}
                className="text-xs text-emerald-400 hover:text-emerald-300 disabled:opacity-50">
                {uploadFile.isPending ? "Uploading…" : "+ Add file"}
              </button>
            </>
          )}
        </div>

        {task.attachments.length === 0 ? (
          <p className="text-c-text-3 text-xs">No attachments</p>
        ) : (
          <ul className="space-y-2">
            {task.attachments.map((att) => (
              <li key={att.id} className="flex items-center gap-2 bg-c-surface-2 rounded-lg px-3 py-2">
                <AttachmentIcon type={att.file_type} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-c-text truncate">{att.original_name}</p>
                  <p className="text-xs text-c-text-3">{formatBytes(att.file_size)}</p>
                </div>
                <a
                  href={`${API_BASE}/api/tasks/${task.id}/attachments/${att.filename}`}
                  target="_blank"
                  rel="noreferrer"
                  aria-label="Download"
                  className="p-1 text-c-text-2 hover:text-c-text transition-colors"
                >
                  <Download size={14} />
                </a>
                {!isDone && (
                  <button type="button" aria-label="Delete attachment"
                    onClick={() => deleteAttachment.mutate(att.id)}
                    className="p-1 text-c-text-3 hover:text-red-400 transition-colors">
                    <Trash2 size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Submit completion (user action) */}
      {canSubmit && !showReviewForm && (
        <div className="bg-c-surface border border-c-border rounded-xl p-4 mb-4">
          <h2 className="text-sm font-semibold text-c-text mb-3">Mark as complete</h2>
          {showSubmitForm ? (
            <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }} className="space-y-3">
              <textarea placeholder="Add a completion note (optional)" value={submitNote} rows={3}
                onChange={(e) => setSubmitNote(e.target.value)}
                className="input-field w-full resize-none" />
              <div className="flex gap-2">
                <button type="submit" disabled={submit.isPending} className="btn-primary flex-1">
                  {submit.isPending ? "Submitting…" : "Submit for review"}
                </button>
                <button type="button" onClick={() => setShowSubmitForm(false)} className="btn-secondary flex-1">Cancel</button>
              </div>
            </form>
          ) : (
            <button type="button" onClick={() => setShowSubmitForm(true)} className="btn-primary w-full">
              Submit for review
            </button>
          )}
        </div>
      )}

      {/* Admin review */}
      {canReview && !showSubmitForm && (
        <div className="bg-c-surface border border-c-border rounded-xl p-4 mb-4">
          <h2 className="text-sm font-semibold text-c-text mb-3">Review submission</h2>
          {showReviewForm ? (
            <form className="space-y-3">
              <textarea placeholder="Review note (optional)" value={reviewNote} rows={2}
                onChange={(e) => setReviewNote(e.target.value)}
                className="input-field w-full resize-none" />
              <div className="flex gap-2">
                <button type="button"
                  onClick={() => review.mutate(true)}
                  disabled={review.isPending}
                  className="flex-1 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-c-text text-sm font-medium py-2 rounded-lg flex items-center justify-center gap-2">
                  <CheckCircle size={16} /> Approve
                </button>
                <button type="button"
                  onClick={() => review.mutate(false)}
                  disabled={review.isPending}
                  className="flex-1 bg-red-800 hover:bg-red-700 disabled:opacity-50 text-c-text text-sm font-medium py-2 rounded-lg flex items-center justify-center gap-2">
                  <XCircle size={16} /> Return
                </button>
              </div>
              <button type="button" onClick={() => setShowReviewForm(false)} className="btn-secondary w-full text-xs">Cancel</button>
            </form>
          ) : (
            <button type="button" onClick={() => setShowReviewForm(true)} className="btn-primary w-full">
              Review this submission
            </button>
          )}
        </div>
      )}
      </div>
      )} {/* end details tab */}
    </div>
  );
}
