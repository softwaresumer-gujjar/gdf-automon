import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, MapPin } from "lucide-react";
import { apiFetch } from "@/api/client";
import { usePermissions } from "@/hooks/usePermissions";

interface Location {
  id: string;
  name: string;
  description: string | null;
  address: string | null;
}

interface LocationForm {
  name: string;
  description: string;
  address: string;
}

const empty: LocationForm = { name: "", description: "", address: "" };

export function Locations() {
  const qc = useQueryClient();
  const { canManageLocations, canDelete } = usePermissions();
  const [form, setForm] = useState<LocationForm>(empty);
  const [editing, setEditing] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const { data: locations = [], isLoading } = useQuery<Location[]>({
    queryKey: ["locations"],
    queryFn: () => apiFetch("/api/locations"),
  });

  const upsert = useMutation({
    mutationFn: (data: LocationForm) =>
      editing
        ? apiFetch(`/api/locations/${editing}`, { method: "PATCH", body: JSON.stringify(data) })
        : apiFetch("/api/locations", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["locations"] });
      setForm(empty);
      setEditing(null);
      setShowForm(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/api/locations/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["locations"] }),
  });

  function startEdit(loc: Location) {
    setForm({ name: loc.name, description: loc.description ?? "", address: loc.address ?? "" });
    setEditing(loc.id);
    setShowForm(true);
  }

  function cancel() {
    setForm(empty);
    setEditing(null);
    setShowForm(false);
  }

  return (
    <div className="p-4 md:p-6 pb-24 md:pb-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-c-text">Locations</h1>
          <p className="text-c-text-2 text-sm mt-0.5">Farm areas and zones</p>
        </div>
        {canManageLocations && !showForm && (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-c-text text-sm font-medium px-3 py-2 rounded-lg transition-colors"
          >
            <Plus size={16} /> Add location
          </button>
        )}
      </div>

      {showForm && canManageLocations && (
        <form
          onSubmit={(e) => { e.preventDefault(); upsert.mutate(form); }}
          className="bg-c-surface border border-c-border rounded-xl p-4 mb-6 space-y-3"
        >
          <h2 className="text-sm font-semibold text-c-text">
            {editing ? "Edit location" : "New location"}
          </h2>
          <input
            required
            placeholder="Name *"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="w-full bg-c-surface-2 border border-c-border rounded-lg px-3 py-2 text-sm text-c-text placeholder:text-c-text-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <input
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            className="w-full bg-c-surface-2 border border-c-border rounded-lg px-3 py-2 text-sm text-c-text placeholder:text-c-text-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <input
            placeholder="Address"
            value={form.address}
            onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
            className="w-full bg-c-surface-2 border border-c-border rounded-lg px-3 py-2 text-sm text-c-text placeholder:text-c-text-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={upsert.isPending}
              className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-c-text text-sm font-medium py-2 rounded-lg transition-colors"
            >
              {upsert.isPending ? "Saving…" : editing ? "Update" : "Create"}
            </button>
            <button
              type="button"
              onClick={cancel}
              className="flex-1 bg-c-surface-2 hover:bg-c-surface-2 text-c-text-2 text-sm font-medium py-2 rounded-lg transition-colors"
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
      ) : locations.length === 0 ? (
        <div className="text-center py-12 text-c-text-3">
          <MapPin size={40} className="mx-auto mb-3 opacity-40" />
          <p>No locations yet</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {locations.map((loc) => (
            <li key={loc.id} className="bg-c-surface border border-c-border rounded-xl px-4 py-3 flex items-start gap-3">
              <MapPin size={18} className="text-emerald-400 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-c-text font-medium text-sm">{loc.name}</p>
                {loc.description && <p className="text-c-text-2 text-xs mt-0.5">{loc.description}</p>}
                {loc.address && <p className="text-c-text-3 text-xs">{loc.address}</p>}
              </div>
              {canManageLocations && (
                <div className="flex gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => startEdit(loc)}
                    className="p-1.5 text-c-text-2 hover:text-c-text hover:bg-c-surface-2 rounded-lg transition-colors"
                  >
                    <Pencil size={14} />
                  </button>
                  {canDelete && (
                    <button
                      type="button"
                      onClick={() => { if (confirm(`Delete "${loc.name}"?`)) remove.mutate(loc.id); }}
                      className="p-1.5 text-c-text-2 hover:text-red-400 hover:bg-c-surface-2 rounded-lg transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
