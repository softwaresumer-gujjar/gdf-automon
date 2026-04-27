import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, CheckCircle, Clock, XCircle, AlertCircle, ClipboardList, ChevronRight } from "lucide-react";
import { formatDistanceToNow, format, isPast, isWithinInterval, addHours } from "date-fns";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { usePermissions } from "@/hooks/usePermissions";
import type { Task } from "@/types/plan";
import type { UserResponse } from "@/types/user";

const STATUS_CONFIG = {
  open: { label: "Open", icon: AlertCircle, color: "text-blue-400", bg: "bg-blue-500/10" },
  submitted: { label: "Under Review", icon: Clock, color: "text-yellow-400", bg: "bg-yellow-500/10" },
  done: { label: "Done", icon: CheckCircle, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  rejected: { label: "Returned", icon: XCircle, color: "text-red-400", bg: "bg-red-500/10" },
} as const;

function DeadlineBadge({ deadline }: { deadline: string | null }) {
  if (!deadline) return null;
  const d = new Date(deadline);
  const past = isPast(d);
  const soon = !past && isWithinInterval(new Date(), { start: new Date(), end: addHours(d, 24) });

  return (
    <span className={`text-xs ${past ? "text-red-400" : soon ? "text-yellow-400" : "text-c-text-2"}`}>
      {past ? `Overdue · ${format(d, "MMM d")}` : `Due ${formatDistanceToNow(d, { addSuffix: true })}`}
    </span>
  );
}

interface CreateBody {
  title: string;
  description: string;
  deadline: string;
  assignee_ids: string[];
}

function CreateTaskModal({
  users,
  onClose,
}: {
  users: UserResponse[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<CreateBody>({ title: "", description: "", deadline: "", assignee_ids: [] });
  const [error, setError] = useState("");

  const create = useMutation({
    mutationFn: (data: CreateBody) =>
      apiFetch("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          ...data,
          deadline: data.deadline ? new Date(data.deadline).toISOString() : null,
        }),
      }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tasks"] }); onClose(); },
    onError: (e: Error) => setError(e.message),
  });

  function toggleUser(uid: string) {
    setForm((f) => ({
      ...f,
      assignee_ids: f.assignee_ids.includes(uid)
        ? f.assignee_ids.filter((id) => id !== uid)
        : [...f.assignee_ids, uid],
    }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/60 px-4 pb-4 md:pb-0">
      <div className="bg-c-surface border border-c-border rounded-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
        <div className="sticky top-0 bg-c-surface border-b border-c-border px-5 py-4 flex items-center justify-between">
          <h2 className="text-base font-bold text-c-text">New Task</h2>
          <button type="button" onClick={onClose} className="text-c-text-2 hover:text-c-text text-xl leading-none">&times;</button>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(form); }} className="p-5 space-y-4">
          <input required placeholder="Title *" value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            className="input-field w-full" />
          <textarea placeholder="Description" value={form.description} rows={3}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            className="input-field w-full resize-none" />
          <div>
            <label className="text-xs text-c-text-2 mb-1 block">Deadline</label>
            <input type="datetime-local" value={form.deadline}
              onChange={(e) => setForm((f) => ({ ...f, deadline: e.target.value }))}
              className="input-field w-full" />
          </div>
          <div>
            <p className="text-xs text-c-text-2 mb-2">Assign to users</p>
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {users.filter((u) => u.is_active).map((u) => (
                <label key={u.id} className="flex items-center gap-2 cursor-pointer hover:bg-c-surface-2 rounded-lg px-2 py-1.5">
                  <input type="checkbox" checked={form.assignee_ids.includes(u.id)}
                    onChange={() => toggleUser(u.id)} className="accent-emerald-500" />
                  <span className="text-sm text-c-text-2">{u.full_name}</span>
                  <span className="text-xs text-c-text-3">{u.email}</span>
                </label>
              ))}
            </div>
          </div>
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" disabled={create.isPending} className="btn-primary flex-1">
              {create.isPending ? "Creating…" : "Create task"}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function Tasks() {
  const { user } = useAuth();
  const { isAdmin } = usePermissions();
  const [showCreate, setShowCreate] = useState(false);
  const [filter, setFilter] = useState<"all" | "open" | "submitted" | "done">("all");

  const { data: tasks = [], isLoading } = useQuery<Task[]>({
    queryKey: ["tasks"],
    queryFn: () => apiFetch("/api/tasks"),
  });

  const { data: users = [] } = useQuery<UserResponse[]>({
    queryKey: ["users"],
    queryFn: () => apiFetch("/api/users"),
    enabled: isAdmin,
  });

  const filtered = tasks.filter((t) => filter === "all" || t.status === filter);

  const counts = {
    all: tasks.length,
    open: tasks.filter((t) => t.status === "open" || t.status === "rejected").length,
    submitted: tasks.filter((t) => t.status === "submitted").length,
    done: tasks.filter((t) => t.status === "done").length,
  };

  return (
    <div className="p-4 md:p-6 pb-24 md:pb-6 max-w-3xl mx-auto">
      {showCreate && isAdmin && (
        <CreateTaskModal users={users} onClose={() => setShowCreate(false)} />
      )}

      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-c-text">Tasks</h1>
          <p className="text-c-text-2 text-sm mt-0.5">Goals and assignments</p>
        </div>
        {isAdmin && (
          <button type="button" onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New task
          </button>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 bg-c-surface border border-c-border rounded-xl p-1 mb-5 overflow-x-auto">
        {(["all", "open", "submitted", "done"] as const).map((f) => (
          <button key={f} type="button"
            onClick={() => setFilter(f)}
            className={`flex-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
              filter === f ? "bg-emerald-600 text-c-text" : "text-c-text-2 hover:text-c-text"
            }`}
          >
            {f === "all" ? "All" : f === "open" ? "Active" : f.charAt(0).toUpperCase() + f.slice(1)}
            {" "}
            <span className="opacity-70">({counts[f]})</span>
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-c-text-3">
          <ClipboardList size={40} className="mx-auto mb-3 opacity-40" />
          <p>No tasks{filter !== "all" ? ` with status "${filter}"` : ""}</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {filtered.map((task) => {
            const cfg = STATUS_CONFIG[task.status];
            const Icon = cfg.icon;
            const isMyTask = task.submitted_by_id === user?.id;
            return (
              <li key={task.id}>
                <Link
                  to={`/tasks/${task.id}`}
                  className="flex items-center gap-3 bg-c-surface border border-c-border hover:border-c-border rounded-xl px-4 py-3 transition-colors"
                >
                  <Icon size={18} className={`${cfg.color} shrink-0`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-c-text text-sm font-medium truncate">{task.title}</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${cfg.bg} ${cfg.color}`}>
                        {cfg.label}
                      </span>
                      <DeadlineBadge deadline={task.deadline} />
                      {isMyTask && task.status === "submitted" && (
                        <span className="text-xs text-yellow-400">Awaiting review</span>
                      )}
                    </div>
                  </div>
                  <ChevronRight size={16} className="text-c-text-3 shrink-0" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
