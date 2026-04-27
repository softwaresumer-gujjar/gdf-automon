import { useState } from "react";
import { Plus, Pause, Play, Trash2, Settings } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useSensors } from "@/hooks/useSensorData";
import type { Sensor } from "@/types/sensor";
import { clsx } from "clsx";

export function SensorManagement() {
  const { data: sensors = [], isLoading } = useSensors();
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  async function setStatus(sensor: Sensor, action: "pause" | "resume") {
    await fetch(`/api/sensors/${sensor.id}/${action}`, { method: "POST" });
    queryClient.invalidateQueries({ queryKey: ["sensors"] });
  }

  async function deleteSensor(sensor: Sensor) {
    if (!confirm(`Delete sensor "${sensor.name}"? This removes all its data.`)) return;
    await fetch(`/api/sensors/${sensor.id}`, { method: "DELETE" });
    queryClient.invalidateQueries({ queryKey: ["sensors"] });
  }

  return (
    <div className="flex-1 p-4 md:p-6 overflow-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-c-text">Sensor Management</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-c-text text-sm font-medium px-3 py-2 rounded-lg transition-colors"
        >
          <Plus size={16} /> Add Sensor
        </button>
      </div>

      <div className="bg-c-surface border border-c-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-c-border text-c-text-2">
              <th className="text-left px-4 py-3 font-medium">Name</th>
              <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Type</th>
              <th className="text-left px-4 py-3 font-medium hidden lg:table-cell">Location</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-right px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <tr key={i} className="border-b border-c-border animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 bg-c-surface-2 rounded w-32" /></td>
                  <td className="px-4 py-3 hidden md:table-cell"><div className="h-4 bg-c-surface-2 rounded w-24" /></td>
                  <td className="px-4 py-3 hidden lg:table-cell"><div className="h-4 bg-c-surface-2 rounded w-20" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-c-surface-2 rounded w-16" /></td>
                  <td className="px-4 py-3" />
                </tr>
              ))
            ) : sensors.map((sensor) => (
              <tr key={sensor.id} className="border-b border-c-border hover:bg-c-surface-2/30 transition-colors">
                <td className="px-4 py-3 text-c-text font-medium">{sensor.name}</td>
                <td className="px-4 py-3 text-c-text-2 hidden md:table-cell">{sensor.sensor_type}</td>
                <td className="px-4 py-3 text-c-text-2 hidden lg:table-cell">{sensor.location ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={clsx("text-xs rounded-full px-2 py-0.5",
                    sensor.status === "active" ? "bg-brand-500/10 text-brand-400" :
                    sensor.status === "paused" ? "bg-yellow-500/10 text-yellow-400" :
                    "bg-red-500/10 text-red-400"
                  )}>
                    {sensor.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2 justify-end">
                    {sensor.status === "active" ? (
                      <button onClick={() => setStatus(sensor, "pause")} title="Pause"
                        className="text-c-text-2 hover:text-yellow-400 transition-colors">
                        <Pause size={16} />
                      </button>
                    ) : (
                      <button onClick={() => setStatus(sensor, "resume")} title="Resume"
                        className="text-c-text-2 hover:text-brand-400 transition-colors">
                        <Play size={16} />
                      </button>
                    )}
                    <button title="Configure" className="text-c-text-2 hover:text-c-text transition-colors">
                      <Settings size={16} />
                    </button>
                    <button onClick={() => deleteSensor(sensor)} title="Delete"
                      className="text-c-text-2 hover:text-red-400 transition-colors">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && sensors.length === 0 && (
          <div className="text-center py-12 text-c-text-3">
            No sensors configured. Add your first sensor above.
          </div>
        )}
      </div>

      {/* AddSensorWizard — placeholder for Phase 3 */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-c-surface border border-c-border rounded-xl p-6 w-full max-w-lg mx-4">
            <h2 className="text-lg font-bold text-c-text mb-4">Add Sensor</h2>
            <p className="text-c-text-2 text-sm mb-4">
              Full wizard (type picker → protocol config → test → save) coming in Phase 3.
              For now, use the API: <code className="text-brand-400">POST /api/sensors</code>
            </p>
            <button onClick={() => setShowAdd(false)}
              className="bg-c-surface-2 hover:bg-c-surface-2 text-c-text text-sm px-4 py-2 rounded-lg">
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
