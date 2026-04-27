import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, Bell, BellOff } from "lucide-react";
import { apiFetch } from "@/api/client";

interface Pref {
  id: string;
  severity: string | null;
  location_id: string | null;
  sensor_id: string | null;
  push_enabled: boolean;
}

const SEVERITIES = ["info", "warning", "critical"];
const SEV_COLOR: Record<string, string> = {
  info: "text-blue-400",
  warning: "text-yellow-400",
  critical: "text-red-400",
};

export function NotificationSettings() {
  const qc = useQueryClient();

  const { data: prefs = [], isLoading } = useQuery<Pref[]>({
    queryKey: ["notif-prefs"],
    queryFn: () => apiFetch("/api/notifications/preferences"),
  });

  const toggle = useMutation({
    mutationFn: ({ id, push_enabled }: { id: string; push_enabled: boolean }) =>
      apiFetch(`/api/notifications/preferences/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ push_enabled }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notif-prefs"] }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/api/notifications/preferences/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notif-prefs"] }),
  });

  const addGlobal = useMutation({
    mutationFn: (severity: string) =>
      apiFetch("/api/notifications/preferences", {
        method: "POST",
        body: JSON.stringify({ severity, push_enabled: true }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notif-prefs"] }),
  });

  const reset = useMutation({
    mutationFn: () => apiFetch("/api/notifications/preferences/reset", { method: "PUT" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notif-prefs"] }),
  });

  function describeRule(pref: Pref): string {
    const parts: string[] = [];
    if (pref.severity) parts.push(`Severity: ${pref.severity}`);
    else parts.push("All severities");
    if (pref.sensor_id) parts.push(`Sensor: ${pref.sensor_id.slice(0, 8)}…`);
    else if (pref.location_id) parts.push(`Location: ${pref.location_id.slice(0, 8)}…`);
    else parts.push("All sensors");
    return parts.join(" · ");
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-c-text">Push notification rules</h2>
        <button
          type="button"
          onClick={() => { if (confirm("Reset all notification preferences to default?")) reset.mutate(); }}
          className="text-xs text-c-text-2 hover:text-red-400 transition-colors"
        >
          Reset all
        </button>
      </div>

      <div>
        <p className="text-xs text-c-text-2 mb-2">Quick-add global rule by severity:</p>
        <div className="flex gap-2">
          {SEVERITIES.map((sev) => (
            <button
              key={sev}
              type="button"
              onClick={() => addGlobal.mutate(sev)}
              className={`text-xs px-3 py-1.5 rounded-lg border border-c-border hover:border-slate-500 transition-colors capitalize ${SEV_COLOR[sev]}`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : prefs.length === 0 ? (
        <div className="text-center py-8 text-c-text-3 text-sm">
          <Bell size={28} className="mx-auto mb-2 opacity-40" />
          <p>No custom rules — all push notifications are enabled by default</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {prefs.map((pref) => (
            <li
              key={pref.id}
              className="flex items-center gap-3 bg-c-surface-2 border border-c-border rounded-lg px-3 py-2.5"
            >
              {pref.push_enabled ? (
                <Bell size={16} className="text-emerald-400 shrink-0" />
              ) : (
                <BellOff size={16} className="text-c-text-3 shrink-0" />
              )}
              <span className="flex-1 text-sm text-c-text-2 min-w-0 truncate">{describeRule(pref)}</span>
              <button
                type="button"
                onClick={() => toggle.mutate({ id: pref.id, push_enabled: !pref.push_enabled })}
                className={`text-xs px-2 py-1 rounded font-medium transition-colors ${
                  pref.push_enabled
                    ? "bg-emerald-900/50 text-emerald-300 hover:bg-emerald-900"
                    : "bg-slate-700 text-c-text-2 hover:bg-slate-600"
                }`}
              >
                {pref.push_enabled ? "On" : "Off"}
              </button>
              <button
                type="button"
                onClick={() => remove.mutate(pref.id)}
                className="p-1 text-c-text-3 hover:text-red-400 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
