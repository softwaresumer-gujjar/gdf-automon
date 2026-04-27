import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Users as UsersIcon } from "lucide-react";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import type { UserResponse, Role } from "@/types/user";

const ROLES: Role[] = ["operator", "admin", "super_admin"];
const ROLE_LABELS: Record<Role, string> = {
  operator: "Operator",
  admin: "Admin",
  super_admin: "Super Admin",
};
const ROLE_COLOR: Record<Role, string> = {
  operator: "bg-slate-700 text-c-text-2",
  admin: "bg-blue-900/60 text-blue-300",
  super_admin: "bg-emerald-900/60 text-emerald-300",
};

interface UserForm {
  email: string;
  full_name: string;
  password: string;
  role: Role;
}

const emptyForm: UserForm = { email: "", full_name: "", password: "", role: "operator" };

export function Users() {
  const qc = useQueryClient();
  const { user: me } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{ full_name: string; role: Role; is_active: boolean } | null>(null);
  const [newForm, setNewForm] = useState<UserForm>(emptyForm);

  const { data: users = [], isLoading } = useQuery<UserResponse[]>({
    queryKey: ["users"],
    queryFn: () => apiFetch("/api/users"),
  });

  const create = useMutation({
    mutationFn: (data: UserForm) =>
      apiFetch("/api/users", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setNewForm(emptyForm);
      setShowForm(false);
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: typeof editForm }) =>
      apiFetch(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setEditingId(null);
      setEditForm(null);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/api/users/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  function startEdit(u: UserResponse) {
    setEditingId(u.id);
    setEditForm({ full_name: u.full_name, role: u.role, is_active: u.is_active });
  }

  return (
    <div className="p-4 md:p-6 pb-24 md:pb-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-c-text">Users</h1>
          <p className="text-c-text-2 text-sm mt-0.5">Manage accounts and roles</p>
        </div>
        {!showForm && (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-c-text text-sm font-medium px-3 py-2 rounded-lg transition-colors"
          >
            <Plus size={16} /> Add user
          </button>
        )}
      </div>

      {showForm && (
        <form
          onSubmit={(e) => { e.preventDefault(); create.mutate(newForm); }}
          className="bg-c-surface border border-c-border rounded-xl p-4 mb-6 space-y-3"
        >
          <h2 className="text-sm font-semibold text-c-text">New user</h2>
          {[
            { key: "full_name", placeholder: "Full name *", type: "text" },
            { key: "email", placeholder: "Email *", type: "email" },
            { key: "password", placeholder: "Password *", type: "password" },
          ].map(({ key, placeholder, type }) => (
            <input
              key={key}
              required
              type={type}
              placeholder={placeholder}
              value={(newForm as never)[key]}
              onChange={(e) => setNewForm((f) => ({ ...f, [key]: e.target.value }))}
              className="w-full bg-c-surface-2 border border-c-border rounded-lg px-3 py-2 text-sm text-c-text placeholder:text-c-text-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          ))}
          <select
            aria-label="Role"
            value={newForm.role}
            onChange={(e) => setNewForm((f) => ({ ...f, role: e.target.value as Role }))}
            className="w-full bg-c-surface-2 border border-c-border rounded-lg px-3 py-2 text-sm text-c-text focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{ROLE_LABELS[r]}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={create.isPending}
              className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-c-text text-sm font-medium py-2 rounded-lg"
            >
              {create.isPending ? "Creating…" : "Create"}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setNewForm(emptyForm); }}
              className="flex-1 bg-c-surface-2 hover:bg-c-surface-2 text-c-text-2 text-sm font-medium py-2 rounded-lg"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <ul className="space-y-3">
          {users.map((u) => (
            <li key={u.id} className="bg-c-surface border border-c-border rounded-xl px-4 py-3">
              {editingId === u.id && editForm ? (
                <form
                  onSubmit={(e) => { e.preventDefault(); update.mutate({ id: u.id, data: editForm }); }}
                  className="space-y-3"
                >
                  <input
                    aria-label="Full name"
                    placeholder="Full name"
                    value={editForm.full_name}
                    onChange={(e) => setEditForm((f) => f && ({ ...f, full_name: e.target.value }))}
                    className="w-full bg-c-surface-2 border border-c-border rounded-lg px-3 py-1.5 text-sm text-c-text focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <div className="flex gap-2 items-center">
                    <select
                      aria-label="Role"
                      value={editForm.role}
                      onChange={(e) => setEditForm((f) => f && ({ ...f, role: e.target.value as Role }))}
                      className="flex-1 bg-c-surface-2 border border-c-border rounded-lg px-2 py-1.5 text-sm text-c-text focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                      ))}
                    </select>
                    <label className="flex items-center gap-1.5 text-sm text-c-text-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editForm.is_active}
                        onChange={(e) => setEditForm((f) => f && ({ ...f, is_active: e.target.checked }))}
                        className="accent-emerald-500"
                      />
                      Active
                    </label>
                  </div>
                  <div className="flex gap-2">
                    <button type="submit" disabled={update.isPending} className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-c-text text-xs font-medium py-1.5 rounded-lg">
                      {update.isPending ? "Saving…" : "Save"}
                    </button>
                    <button type="button" onClick={() => { setEditingId(null); setEditForm(null); }} className="flex-1 bg-c-surface-2 text-c-text-2 text-xs font-medium py-1.5 rounded-lg">
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm font-bold text-c-text shrink-0">
                    {u.full_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-c-text text-sm font-medium">{u.full_name}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${ROLE_COLOR[u.role]}`}>
                        {ROLE_LABELS[u.role]}
                      </span>
                      {!u.is_active && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-red-900/60 text-red-300">Disabled</span>
                      )}
                      {u.id === me?.id && (
                        <span className="text-xs text-c-text-3">(you)</span>
                      )}
                    </div>
                    <p className="text-c-text-3 text-xs">{u.email}</p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button
                      type="button"
                      aria-label={`Edit ${u.full_name}`}
                      onClick={() => startEdit(u)}
                      className="p-1.5 text-c-text-2 hover:text-c-text hover:bg-c-surface-2 rounded-lg transition-colors"
                    >
                      <Pencil size={14} />
                    </button>
                    {u.id !== me?.id && (
                      <button
                        type="button"
                        aria-label={`Delete ${u.full_name}`}
                        onClick={() => { if (confirm(`Delete user "${u.full_name}"?`)) remove.mutate(u.id); }}
                        className="p-1.5 text-c-text-2 hover:text-red-400 hover:bg-c-surface-2 rounded-lg transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {users.length === 0 && !isLoading && (
        <div className="text-center py-12 text-c-text-3">
          <UsersIcon size={40} className="mx-auto mb-3 opacity-40" />
          <p>No users found</p>
        </div>
      )}
    </div>
  );
}
