import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Pause, Play, Trash2, Settings, ChevronRight } from "lucide-react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { useSensors } from "@/hooks/useSensorData";
import { apiFetch } from "@/api/client";
import { AddSensorWizard } from "@/components/sensors/AddSensorWizard";
import { usePermissions } from "@/hooks/usePermissions";
import type { Sensor } from "@/types/sensor";
import { clsx } from "clsx";

const STATUS_CFG = {
  active: { bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400", label: "Active" },
  paused: { bg: "bg-yellow-500/10", text: "text-yellow-400", dot: "bg-yellow-400", label: "Paused" },
  error:  { bg: "bg-red-500/10",    text: "text-red-400",    dot: "bg-red-400",    label: "Error" },
} as const;

function StatusBadge({ status }: { status: Sensor["status"] }) {
  const c = STATUS_CFG[status] ?? STATUS_CFG.error;
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full", c.bg, c.text)}>
      <span className={clsx("w-1.5 h-1.5 rounded-full", c.dot, status === "active" && "animate-pulse")} />
      {c.label}
    </span>
  );
}

export function SensorManagement() {
  const { isAdmin } = usePermissions();
  const { data: sensors = [], isLoading } = useSensors();
  const qc = useQueryClient();
  const [showWizard, setShowWizard] = useState(false);

  const toggleStatus = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "pause" | "resume" }) =>
      apiFetch(`/api/sensors/${id}/${action}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sensors"] }),
  });

  const deleteSensor = useMutation({
    mutationFn: (id: string) => apiFetch(`/api/sensors/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sensors"] }),
  });

  function confirmDelete(sensor: Sensor) {
    if (confirm(`Delete sensor "${sensor.name}"? This removes all its data.`)) {
      deleteSensor.mutate(sensor.id);
    }
  }

  return (
    <div className="flex-1 p-4 md:p-6 overflow-auto">
      {showWizard && <AddSensorWizard onClose={() => setShowWizard(false)} />}

      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-c-text">Sensors</h1>
          <p className="text-c-text-2 text-sm mt-0.5">
            {sensors.length} sensor{sensors.length !== 1 ? "s" : ""} ·{" "}
            {sensors.filter((s) => s.status === "active").length} active
          </p>
        </div>
        {isAdmin && (
          <button
            type="button"
            onClick={() => setShowWizard(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> Add Sensor
          </button>
        )}
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {(["active", "paused", "error"] as const).map((s) => {
          const c = STATUS_CFG[s];
          const count = sensors.filter((x) => x.status === s).length;
          return (
            <div key={s} className={clsx("rounded-xl border p-3", c.bg, "border-c-border")}>
              <p className={clsx("text-2xl font-bold tabular-nums", c.text)}>{count}</p>
              <p className="text-xs text-c-text-3 mt-0.5">{c.label}</p>
            </div>
          );
        })}
      </div>

      {/* Table */}
      <div className="bg-c-surface border border-c-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-c-border bg-c-surface-2/50">
                <th className="text-left px-4 py-3 font-medium text-c-text-2">Name</th>
                <th className="text-left px-4 py-3 font-medium text-c-text-2 hidden md:table-cell">Type</th>
                <th className="text-left px-4 py-3 font-medium text-c-text-2 hidden lg:table-cell">Protocol</th>
                <th className="text-left px-4 py-3 font-medium text-c-text-2 hidden lg:table-cell">Location</th>
                <th className="text-left px-4 py-3 font-medium text-c-text-2">Status</th>
                <th className="text-right px-4 py-3 font-medium text-c-text-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 4 }).map((_, i) => (
                    <tr key={i} className="border-b border-c-border animate-pulse">
                      <td className="px-4 py-3"><div className="h-4 bg-c-surface-2 rounded w-36" /></td>
                      <td className="px-4 py-3 hidden md:table-cell"><div className="h-4 bg-c-surface-2 rounded w-28" /></td>
                      <td className="px-4 py-3 hidden lg:table-cell"><div className="h-4 bg-c-surface-2 rounded w-16" /></td>
                      <td className="px-4 py-3 hidden lg:table-cell"><div className="h-4 bg-c-surface-2 rounded w-20" /></td>
                      <td className="px-4 py-3"><div className="h-5 bg-c-surface-2 rounded w-16" /></td>
                      <td className="px-4 py-3" />
                    </tr>
                  ))
                : sensors.map((sensor) => (
                    <tr key={sensor.id} className="border-b border-c-border hover:bg-c-surface-2/30 transition-colors last:border-0">
                      <td className="px-4 py-3">
                        <Link to={`/sensors/${sensor.id}`} className="text-c-text font-medium hover:text-emerald-400 transition-colors">
                          {sensor.name}
                        </Link>
                        {sensor.description && (
                          <p className="text-xs text-c-text-3 mt-0.5 truncate max-w-xs">{sensor.description}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-c-text-2 hidden md:table-cell capitalize">
                        {sensor.sensor_type.replace(/_/g, " ")}
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className="text-xs font-mono uppercase bg-c-surface-2 border border-c-border rounded px-1.5 py-0.5 text-c-text-2">
                          {sensor.protocol}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-c-text-2 hidden lg:table-cell text-xs">
                        {sensor.location ?? <span className="text-c-text-3">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={sensor.status} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 justify-end">
                          {isAdmin && (
                            sensor.status === "active" ? (
                              <button
                                type="button"
                                onClick={() => toggleStatus.mutate({ id: sensor.id, action: "pause" })}
                                title="Pause sensor"
                                className="p-1.5 text-c-text-2 hover:text-yellow-400 hover:bg-c-surface-2 rounded-lg transition-colors"
                              >
                                <Pause size={14} />
                              </button>
                            ) : (
                              <button
                                type="button"
                                onClick={() => toggleStatus.mutate({ id: sensor.id, action: "resume" })}
                                title="Resume sensor"
                                className="p-1.5 text-c-text-2 hover:text-emerald-400 hover:bg-c-surface-2 rounded-lg transition-colors"
                              >
                                <Play size={14} />
                              </button>
                            )
                          )}
                          <Link
                            to={`/sensors/${sensor.id}`}
                            title="View details"
                            className="p-1.5 text-c-text-2 hover:text-c-text hover:bg-c-surface-2 rounded-lg transition-colors"
                          >
                            <Settings size={14} />
                          </Link>
                          {isAdmin && (
                            <button
                              type="button"
                              onClick={() => confirmDelete(sensor)}
                              title="Delete sensor"
                              className="p-1.5 text-c-text-2 hover:text-red-400 hover:bg-c-surface-2 rounded-lg transition-colors"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                          <Link to={`/sensors/${sensor.id}`} className="p-1.5 text-c-text-3">
                            <ChevronRight size={14} />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>

        {!isLoading && sensors.length === 0 && (
          <div className="text-center py-16 text-c-text-3">
            <Settings size={40} className="mx-auto mb-3 opacity-30" />
            <p className="font-medium text-c-text">No sensors configured</p>
            <p className="text-sm mt-1">Add your first sensor using the button above.</p>
          </div>
        )}
      </div>
    </div>
  );
}
