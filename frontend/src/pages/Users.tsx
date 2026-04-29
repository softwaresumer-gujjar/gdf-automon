import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus, Pencil, Trash2, Users as UsersIcon, Phone, MapPin,
  Clock, Briefcase, ChevronDown, ChevronRight, Shield, Settings2,
  X, Check,
} from "lucide-react";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import type { UserResponse, Role } from "@/types/user";
import type { Sensor } from "@/types/sensor";

const ROLES: Role[] = ["operator", "admin", "super_admin"];
const ROLE_LABELS: Record<Role, string> = {
  operator:    "Operator",
  admin:       "Admin",
  super_admin: "Super Admin",
};
const ROLE_COLOR: Record<Role, string> = {
  operator:    "bg-slate-700 text-c-text-2",
  admin:       "bg-blue-900/60 text-blue-300",
  super_admin: "bg-emerald-900/60 text-emerald-300",
};

interface Location { id: string; name: string }
interface PermissionData { location_ids: string[]; sensor_ids: string[] }

interface UserForm {
  email: string;
  full_name: string;
  password: string;
  role: Role;
  phone: string;
  current_location: string;
  working_hours: string;
  duty: string;
}

const emptyForm: UserForm = {
  email: "", full_name: "", password: "", role: "operator",
  phone: "", current_location: "", working_hours: "", duty: "",
};

// ── User profile card ──────────────────────────────────────────────────────

function UserCard({
  u,
  isMe,
  sensors,
  locations,
}: {
  u: UserResponse;
  isMe: boolean;
  sensors: Sensor[];
  locations: Location[];
}) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    full_name: u.full_name,
    role: u.role as Role,
    is_active: u.is_active,
    phone: u.phone ?? "",
    current_location: u.current_location ?? "",
    working_hours: u.working_hours ?? "",
    duty: u.duty ?? "",
  });
  const [showPermissions, setShowPermissions] = useState(false);

  const { data: perms, refetch: refetchPerms } = useQuery<PermissionData>({
    queryKey: ["user-permissions", u.id],
    queryFn: () => apiFetch(`/api/users/${u.id}/permissions`),
    enabled: showPermissions,
  });

  const update = useMutation({
    mutationFn: (data: typeof editForm) =>
      apiFetch(`/api/users/${u.id}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setEditing(false);
    },
  });

  const remove = useMutation({
    mutationFn: () => apiFetch(`/api/users/${u.id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const toggleSensorPerm = useMutation({
    mutationFn: async ({ sensorId, add }: { sensorId: string; add: boolean }) => {
      if (add) {
        await apiFetch(`/api/users/${u.id}/permissions/sensors/${sensorId}`, { method: "POST" });
      } else {
        await apiFetch(`/api/users/${u.id}/permissions/sensors/${sensorId}`, { method: "DELETE" });
      }
    },
    onSuccess: () => refetchPerms(),
  });

  const toggleLocationPerm = useMutation({
    mutationFn: async ({ locationId, add }: { locationId: string; add: boolean }) => {
      if (add) {
        await apiFetch(`/api/users/${u.id}/permissions/locations/${locationId}`, { method: "POST" });
      } else {
        await apiFetch(`/api/users/${u.id}/permissions/locations/${locationId}`, { method: "DELETE" });
      }
    },
    onSuccess: () => refetchPerms(),
  });

  return (
    <li className="bg-c-surface border border-c-border rounded-xl overflow-hidden">
      {/* Summary row */}
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="w-10 h-10 rounded-full bg-emerald-700/30 flex items-center justify-center text-sm font-bold text-emerald-300 shrink-0">
          {u.full_name.charAt(0).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-c-text text-sm font-medium">{u.full_name}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${ROLE_COLOR[u.role as Role]}`}>
              {ROLE_LABELS[u.role as Role]}
            </span>
            {!u.is_active && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-red-900/60 text-red-300">Disabled</span>
            )}
            {isMe && <span className="text-xs text-c-text-3">(you)</span>}
          </div>
          <div className="flex items-center gap-3 mt-0.5 flex-wrap">
            <p className="text-c-text-3 text-xs">{u.email}</p>
            {u.phone && (
              <span className="text-xs text-c-text-3 flex items-center gap-1">
                <Phone size={10} /> {u.phone}
              </span>
            )}
            {u.duty && (
              <span className="text-xs text-c-text-3 flex items-center gap-1">
                <Briefcase size={10} /> {u.duty}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            aria-label={`Edit ${u.full_name}`}
            onClick={() => { setEditing((v) => !v); setExpanded(true); }}
            className="p-1.5 text-c-text-2 hover:text-c-text hover:bg-c-surface-2 rounded-lg transition-colors"
          >
            <Pencil size={14} />
          </button>
          {!isMe && (
            <button
              type="button"
              aria-label={`Delete ${u.full_name}`}
              onClick={() => { if (confirm(`Delete user "${u.full_name}"?`)) remove.mutate(); }}
              className="p-1.5 text-c-text-2 hover:text-red-400 hover:bg-c-surface-2 rounded-lg transition-colors"
            >
              <Trash2 size={14} />
            </button>
          )}
          <button
            type="button"
            aria-label={expanded ? "Collapse" : "Expand"}
            onClick={() => setExpanded((v) => !v)}
            className="p-1.5 text-c-text-2 hover:text-c-text hover:bg-c-surface-2 rounded-lg transition-colors"
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </div>
      </div>

      {/* Expanded: edit form or profile details */}
      {expanded && (
        <div className="border-t border-c-border bg-c-surface-2/40 p-4">
          {editing ? (
            <form
              onSubmit={(e) => { e.preventDefault(); update.mutate(editForm); }}
              className="space-y-3"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-c-text-2 mb-1">Full name</label>
                  <input
                    aria-label="Full name"
                    value={editForm.full_name}
                    onChange={(e) => setEditForm((f) => ({ ...f, full_name: e.target.value }))}
                    className="input-field w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs text-c-text-2 mb-1">Role</label>
                  <select
                    aria-label="Role"
                    value={editForm.role}
                    onChange={(e) => setEditForm((f) => ({ ...f, role: e.target.value as Role }))}
                    className="input-field w-full"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-c-text-2 mb-1">Phone</label>
                  <input
                    aria-label="Phone"
                    placeholder="+92300..."
                    value={editForm.phone}
                    onChange={(e) => setEditForm((f) => ({ ...f, phone: e.target.value }))}
                    className="input-field w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs text-c-text-2 mb-1">Working hours</label>
                  <input
                    aria-label="Working hours"
                    placeholder="e.g. 9am–5pm Mon–Fri"
                    value={editForm.working_hours}
                    onChange={(e) => setEditForm((f) => ({ ...f, working_hours: e.target.value }))}
                    className="input-field w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs text-c-text-2 mb-1">Duty / Role description</label>
                  <input
                    aria-label="Duty"
                    placeholder="e.g. Milking supervisor"
                    value={editForm.duty}
                    onChange={(e) => setEditForm((f) => ({ ...f, duty: e.target.value }))}
                    className="input-field w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs text-c-text-2 mb-1">Current location</label>
                  <input
                    aria-label="Current location"
                    placeholder="e.g. Barn A"
                    value={editForm.current_location}
                    onChange={(e) => setEditForm((f) => ({ ...f, current_location: e.target.value }))}
                    className="input-field w-full"
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer text-sm text-c-text-2">
                <input
                  type="checkbox"
                  checked={editForm.is_active}
                  onChange={(e) => setEditForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="accent-emerald-500"
                />
                Account active
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={update.isPending}
                  className="btn-primary flex-1 disabled:opacity-50 flex items-center justify-center gap-1">
                  <Check size={14} /> {update.isPending ? "Saving…" : "Save"}
                </button>
                <button type="button" onClick={() => setEditing(false)} className="btn-secondary flex-1 flex items-center justify-center gap-1">
                  <X size={14} /> Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              {/* Profile details */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                {u.phone && (
                  <div className="flex items-center gap-2 text-c-text-2">
                    <Phone size={12} className="text-c-text-3 shrink-0" />
                    <span>{u.phone}</span>
                  </div>
                )}
                {u.working_hours && (
                  <div className="flex items-center gap-2 text-c-text-2">
                    <Clock size={12} className="text-c-text-3 shrink-0" />
                    <span>{u.working_hours}</span>
                  </div>
                )}
                {u.duty && (
                  <div className="flex items-center gap-2 text-c-text-2">
                    <Briefcase size={12} className="text-c-text-3 shrink-0" />
                    <span>{u.duty}</span>
                  </div>
                )}
                {u.current_location && (
                  <div className="flex items-center gap-2 text-c-text-2">
                    <MapPin size={12} className="text-c-text-3 shrink-0" />
                    <span>{u.current_location}</span>
                  </div>
                )}
              </div>

              {/* Permissions section — operators */}
              {u.role === "operator" && (
                <div>
                  <button
                    type="button"
                    onClick={() => setShowPermissions((v) => !v)}
                    className="flex items-center gap-2 text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
                  >
                    <Shield size={12} />
                    {showPermissions ? "Hide" : "Manage"} access permissions
                  </button>

                  {showPermissions && (
                    <div className="mt-3 space-y-4">
                      {/* Location permissions */}
                      {locations.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-c-text-2 mb-2 flex items-center gap-1">
                            <MapPin size={10} /> Locations
                          </p>
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                            {locations.map((loc) => {
                              const has = perms?.location_ids.includes(loc.id) ?? false;
                              return (
                                <label key={loc.id} className="flex items-center gap-2 cursor-pointer text-xs bg-c-surface border border-c-border rounded-lg px-2.5 py-1.5 hover:border-emerald-500/40 transition-colors">
                                  <input
                                    type="checkbox"
                                    checked={has}
                                    onChange={(e) => toggleLocationPerm.mutate({ locationId: loc.id, add: e.target.checked })}
                                    className="accent-emerald-500"
                                  />
                                  <span className="text-c-text-2 truncate">{loc.name}</span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Sensor permissions */}
                      {sensors.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-c-text-2 mb-2 flex items-center gap-1">
                            <Settings2 size={10} /> Sensors
                          </p>
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                            {sensors.map((s) => {
                              const has = perms?.sensor_ids.includes(s.id) ?? false;
                              return (
                                <label key={s.id} className="flex items-center gap-2 cursor-pointer text-xs bg-c-surface border border-c-border rounded-lg px-2.5 py-1.5 hover:border-emerald-500/40 transition-colors">
                                  <input
                                    type="checkbox"
                                    checked={has}
                                    onChange={(e) => toggleSensorPerm.mutate({ sensorId: s.id, add: e.target.checked })}
                                    className="accent-emerald-500"
                                  />
                                  <span className="text-c-text-2 truncate">{s.name}</span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </li>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export function Users() {
  const qc = useQueryClient();
  const { user: me } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [newForm, setNewForm] = useState<UserForm>(emptyForm);
  const [formError, setFormError] = useState("");

  const { data: users = [], isLoading } = useQuery<UserResponse[]>({
    queryKey: ["users"],
    queryFn: () => apiFetch("/api/users"),
  });

  const { data: sensors = [] } = useQuery<Sensor[]>({
    queryKey: ["sensors"],
    queryFn: () => apiFetch("/api/sensors"),
  });

  const { data: locations = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ["locations"],
    queryFn: () => apiFetch("/api/locations"),
  });

  const create = useMutation({
    mutationFn: (data: UserForm) =>
      apiFetch("/api/users", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setNewForm(emptyForm);
      setShowForm(false);
      setFormError("");
    },
    onError: (e: Error) => setFormError(e.message),
  });

  const roleGroups: Record<string, UserResponse[]> = {
    super_admin: users.filter((u) => u.role === "super_admin"),
    admin:       users.filter((u) => u.role === "admin"),
    operator:    users.filter((u) => u.role === "operator"),
  };

  return (
    <div className="p-4 md:p-6 pb-24 md:pb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-c-text">Users</h1>
          <p className="text-c-text-2 text-sm mt-0.5">
            {users.length} user{users.length !== 1 ? "s" : ""} ·{" "}
            {users.filter((u) => u.is_active).length} active
          </p>
        </div>
        {!showForm && (
          <button type="button" onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> Add user
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { label: "Super Admins", count: roleGroups.super_admin.length, color: "text-emerald-400" },
          { label: "Admins",       count: roleGroups.admin.length,       color: "text-blue-400" },
          { label: "Operators",    count: roleGroups.operator.length,    color: "text-c-text-2" },
        ].map(({ label, count, color }) => (
          <div key={label} className="bg-c-surface border border-c-border rounded-xl p-4">
            <p className={`text-2xl font-bold tabular-nums ${color}`}>{count}</p>
            <p className="text-xs text-c-text-3 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* New user form */}
      {showForm && (
        <form
          onSubmit={(e) => { e.preventDefault(); create.mutate(newForm); }}
          className="bg-c-surface border border-c-border rounded-xl p-4 mb-6 space-y-3"
        >
          <h2 className="text-sm font-semibold text-c-text">New user</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { key: "full_name", placeholder: "Full name *", type: "text" },
              { key: "email",     placeholder: "Email *",     type: "email" },
              { key: "password",  placeholder: "Password *",  type: "password" },
              { key: "phone",     placeholder: "Phone (+92…)", type: "text" },
              { key: "working_hours", placeholder: "Working hours", type: "text" },
              { key: "duty",      placeholder: "Duty / Role description", type: "text" },
              { key: "current_location", placeholder: "Current location", type: "text" },
            ].map(({ key, placeholder, type }) => (
              <input
                key={key}
                required={["full_name", "email", "password"].includes(key)}
                type={type}
                placeholder={placeholder}
                value={(newForm as never)[key]}
                onChange={(e) => setNewForm((f) => ({ ...f, [key]: e.target.value }))}
                className="input-field"
              />
            ))}
            <select
              aria-label="Role"
              value={newForm.role}
              onChange={(e) => setNewForm((f) => ({ ...f, role: e.target.value as Role }))}
              className="input-field"
            >
              {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
            </select>
          </div>
          {formError && <p className="text-red-400 text-xs">{formError}</p>}
          <div className="flex gap-2">
            <button type="submit" disabled={create.isPending} className="btn-primary flex-1 disabled:opacity-50">
              {create.isPending ? "Creating…" : "Create"}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setNewForm(emptyForm); setFormError(""); }}
              className="btn-secondary flex-1">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* User list grouped by role */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : users.length === 0 ? (
        <div className="text-center py-12 text-c-text-3">
          <UsersIcon size={40} className="mx-auto mb-3 opacity-40" />
          <p>No users found</p>
        </div>
      ) : (
        <div className="space-y-6">
          {(["super_admin", "admin", "operator"] as Role[]).map((role) => {
            const group = roleGroups[role];
            if (group.length === 0) return null;
            return (
              <div key={role}>
                <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide mb-3 flex items-center gap-2">
                  {ROLE_LABELS[role]}
                  <span className="text-c-text-3 font-normal normal-case tracking-normal">({group.length})</span>
                </p>
                <ul className="space-y-2">
                  {group.map((u) => (
                    <UserCard
                      key={u.id}
                      u={u}
                      isMe={u.id === me?.id}
                      sensors={sensors}
                      locations={locations}
                    />
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
