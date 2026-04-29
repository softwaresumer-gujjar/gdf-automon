import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, MapPin, Activity, Settings2, ChevronDown, ChevronUp } from "lucide-react";
import { apiFetch } from "@/api/client";
import { usePermissions } from "@/hooks/usePermissions";
import type { Sensor } from "@/types/sensor";

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

function SensorCountBadge({ count, status }: { count: number; status: "active" | "paused" | "error" }) {
  const cfg = {
    active: { bg: "bg-emerald-500/10", text: "text-emerald-400" },
    paused: { bg: "bg-yellow-500/10",  text: "text-yellow-400"  },
    error:  { bg: "bg-red-500/10",     text: "text-red-400"     },
  }[status];
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.bg} ${cfg.text}`}>
      {count} {status}
    </span>
  );
}

function LocationCard({
  loc,
  sensors,
  canEdit,
  canDelete,
  onEdit,
  onDelete,
}: {
  loc: Location;
  sensors: Sensor[];
  canEdit: boolean;
  canDelete: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const locSensors = sensors.filter((s) => (s as Sensor & { location_id?: string }).location_id === loc.id);
  const active = locSensors.filter((s) => s.status === "active").length;
  const paused = locSensors.filter((s) => s.status === "paused").length;
  const error  = locSensors.filter((s) => s.status === "error").length;

  return (
    <li className="bg-c-surface border border-c-border rounded-xl overflow-hidden">
      <div className="px-4 py-4 flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-emerald-600/20 flex items-center justify-center shrink-0">
          <MapPin size={18} className="text-emerald-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-c-text font-semibold text-sm">{loc.name}</p>
            {locSensors.length > 0 && (
              <span className="text-xs bg-c-surface-2 border border-c-border rounded-full px-2 py-0.5 text-c-text-3">
                {locSensors.length} sensor{locSensors.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          {loc.description && <p className="text-c-text-2 text-xs mt-0.5">{loc.description}</p>}
          {loc.address && <p className="text-c-text-3 text-xs mt-0.5 flex items-center gap-1"><MapPin size={10} />{loc.address}</p>}

          {/* Sensor status summary */}
          {locSensors.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {active > 0 && <SensorCountBadge count={active} status="active" />}
              {paused > 0 && <SensorCountBadge count={paused} status="paused" />}
              {error  > 0 && <SensorCountBadge count={error}  status="error"  />}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {locSensors.length > 0 && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="p-1.5 text-c-text-2 hover:text-c-text hover:bg-c-surface-2 rounded-lg transition-colors"
              title={expanded ? "Hide sensors" : "Show sensors"}
            >
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          )}
          {canEdit && (
            <button type="button" onClick={onEdit} aria-label={`Edit ${loc.name}`}
              className="p-1.5 text-c-text-2 hover:text-c-text hover:bg-c-surface-2 rounded-lg transition-colors">
              <Pencil size={14} />
            </button>
          )}
          {canDelete && (
            <button type="button" onClick={onDelete} aria-label={`Delete ${loc.name}`}
              className="p-1.5 text-c-text-2 hover:text-red-400 hover:bg-c-surface-2 rounded-lg transition-colors">
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Expanded sensor list */}
      {expanded && locSensors.length > 0 && (
        <div className="border-t border-c-border bg-c-surface-2/40">
          <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide px-4 py-2">
            Sensors in this location
          </p>
          <div className="divide-y divide-c-border">
            {locSensors.map((s) => (
              <div key={s.id} className="flex items-center gap-3 px-4 py-2.5">
                <span className={`w-2 h-2 rounded-full shrink-0 ${
                  s.status === "active" ? "bg-emerald-400 animate-pulse" :
                  s.status === "paused" ? "bg-yellow-400" : "bg-red-400"
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-c-text">{s.name}</p>
                  <p className="text-xs text-c-text-3 capitalize">{s.sensor_type.replace(/_/g, " ")}</p>
                </div>
                <span className="text-xs font-mono uppercase bg-c-surface border border-c-border rounded px-1.5 py-0.5 text-c-text-3">
                  {s.protocol}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {expanded && locSensors.length === 0 && (
        <div className="border-t border-c-border px-4 py-4 text-center text-c-text-3 text-xs">
          No sensors assigned to this location
        </div>
      )}
    </li>
  );
}

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

  const { data: sensors = [] } = useQuery<Sensor[]>({
    queryKey: ["sensors"],
    queryFn: () => apiFetch("/api/sensors"),
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

  // Stats
  const totalSensors = sensors.length;
  const activeSensors = sensors.filter((s) => s.status === "active").length;

  return (
    <div className="p-4 md:p-6 pb-24 md:pb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-c-text">Locations</h1>
          <p className="text-c-text-2 text-sm mt-0.5">
            {locations.length} location{locations.length !== 1 ? "s" : ""} · {totalSensors} sensor{totalSensors !== 1 ? "s" : ""} total
          </p>
        </div>
        {canManageLocations && !showForm && (
          <button type="button" onClick={() => setShowForm(true)}
            className="btn-primary flex items-center gap-2">
            <Plus size={16} /> Add location
          </button>
        )}
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Locations",      value: locations.length, icon: MapPin,    color: "text-emerald-400" },
          { label: "Total Sensors",  value: totalSensors,     icon: Settings2, color: "text-blue-400" },
          { label: "Active Sensors", value: activeSensors,    icon: Activity,  color: "text-emerald-400" },
          { label: "Offline",        value: totalSensors - activeSensors, icon: Activity, color: "text-red-400" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-c-surface border border-c-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <Icon size={14} className={color} />
              <span className="text-xs text-c-text-3">{label}</span>
            </div>
            <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Create / Edit form */}
      {showForm && canManageLocations && (
        <form
          onSubmit={(e) => { e.preventDefault(); upsert.mutate(form); }}
          className="bg-c-surface border border-c-border rounded-xl p-4 mb-6 space-y-3"
        >
          <h2 className="text-sm font-semibold text-c-text">{editing ? "Edit location" : "New location"}</h2>
          <input required placeholder="Name *" value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="input-field w-full" />
          <input placeholder="Description" value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            className="input-field w-full" />
          <input placeholder="Address" value={form.address}
            onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
            className="input-field w-full" />
          <div className="flex gap-2">
            <button type="submit" disabled={upsert.isPending}
              className="btn-primary flex-1 disabled:opacity-50">
              {upsert.isPending ? "Saving…" : editing ? "Update" : "Create"}
            </button>
            <button type="button" onClick={cancel} className="btn-secondary flex-1">Cancel</button>
          </div>
        </form>
      )}

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : locations.length === 0 ? (
        <div className="text-center py-16 text-c-text-3">
          <MapPin size={40} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium text-c-text">No locations yet</p>
          <p className="text-sm mt-1">Add your first location to organise sensors by area.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {locations.map((loc) => (
            <LocationCard
              key={loc.id}
              loc={loc}
              sensors={sensors}
              canEdit={canManageLocations}
              canDelete={canDelete}
              onEdit={() => startEdit(loc)}
              onDelete={() => { if (confirm(`Delete "${loc.name}"?`)) remove.mutate(loc.id); }}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
