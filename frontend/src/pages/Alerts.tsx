import { useState } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import {
  AlertTriangle, Bell, BellOff, CheckCircle, Clock,
  Filter, RefreshCw, Shield, ToggleLeft, ToggleRight,
} from "lucide-react";
import { format } from "date-fns";
import { apiFetch } from "@/api/client";
import { useActiveAlerts, useAlertRules } from "@/hooks/useAppData";
import { useAlertStore } from "@/store/alertStore";
import { usePermissions } from "@/hooks/usePermissions";
import type { ActiveAlert, AlertRule } from "@/types/alert";
import { clsx } from "clsx";

// ── helpers ────────────────────────────────────────────────────────────────

const SEV_CFG = {
  critical: {
    label:     "Critical",
    bg:        "bg-red-500/10",
    border:    "border-red-500/30",
    text:      "text-red-500",
    dot:       "bg-red-500",
    badgeBg:   "bg-red-100 dark:bg-red-500/20",
  },
  warning: {
    label:     "Warning",
    bg:        "bg-yellow-500/10",
    border:    "border-yellow-500/30",
    text:      "text-yellow-500",
    dot:       "bg-yellow-500",
    badgeBg:   "bg-yellow-100 dark:bg-yellow-500/20",
  },
  info: {
    label:     "Info",
    bg:        "bg-blue-500/10",
    border:    "border-blue-500/30",
    text:      "text-blue-500",
    dot:       "bg-blue-500",
    badgeBg:   "bg-blue-100 dark:bg-blue-500/20",
  },
} as const;

const CONDITION_LABELS: Record<string, string> = {
  gt:            "> (greater than)",
  lt:            "< (less than)",
  eq:            "= (equals)",
  outside_range: "Outside range",
};

function SeverityBadge({ severity }: { severity: keyof typeof SEV_CFG }) {
  const c = SEV_CFG[severity];
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full", c.badgeBg, c.text)}>
      <span className={clsx("w-1.5 h-1.5 rounded-full", c.dot)} />
      {c.label}
    </span>
  );
}

// ── Active Alert Card ──────────────────────────────────────────────────────

function ActiveAlertCard({ alert }: { alert: ActiveAlert }) {
  const c = SEV_CFG[alert.severity];
  return (
    <div className={clsx("card p-4 border", c.border)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className={clsx("w-2 h-2 rounded-full mt-2 shrink-0 animate-pulse", c.dot)} />
          <div className="min-w-0">
            <p className="text-sm font-medium text-c-text">{alert.message}</p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
              <span className="text-xs text-c-text-3">
                <Clock size={10} className="inline mr-1" />
                {format(new Date(alert.triggered_at), "MMM d, HH:mm")}
              </span>
              <span className="text-xs text-c-text-3">
                Value: <span className="font-mono font-medium text-c-text">{alert.triggered_value}</span>
              </span>
            </div>
          </div>
        </div>
        <SeverityBadge severity={alert.severity} />
      </div>
    </div>
  );
}

// ── Alert Rule Row ─────────────────────────────────────────────────────────

function AlertRuleRow({ rule, canEdit }: { rule: AlertRule; canEdit: boolean }) {
  const qc = useQueryClient();
  const c = SEV_CFG[rule.severity];

  const toggle = useMutation({
    mutationFn: () =>
      apiFetch(`/api/alerts/rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !rule.enabled }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts-rules"] }),
  });

  const conditionStr = rule.condition === "outside_range"
    ? `Outside [${rule.threshold} – ${rule.threshold_max}]`
    : `${CONDITION_LABELS[rule.condition] ?? rule.condition} ${rule.threshold}`;

  return (
    <div className={clsx("card p-3 flex items-center gap-3 transition-opacity", !rule.enabled && "opacity-50")}>
      <span className={clsx("w-2 h-2 rounded-full shrink-0", c.dot)} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-c-text font-medium truncate">
          {rule.channel} · {conditionStr}
        </p>
        <p className="text-xs text-c-text-3 mt-0.5">
          Sensor {rule.sensor_id.slice(0, 8)}…
        </p>
      </div>
      <SeverityBadge severity={rule.severity} />
      {canEdit && (
        <button
          type="button"
          onClick={() => toggle.mutate()}
          disabled={toggle.isPending}
          className="text-c-text-3 hover:text-c-text transition-colors ml-1"
          title={rule.enabled ? "Disable rule" : "Enable rule"}
        >
          {rule.enabled
            ? <ToggleRight size={20} className="text-emerald-500" />
            : <ToggleLeft size={20} />}
        </button>
      )}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────

type Severity = "all" | "critical" | "warning" | "info";

export function Alerts() {
  const [activeTab, setActiveTab] = useState<"active" | "rules">("active");
  const [severityFilter, setSeverityFilter] = useState<Severity>("all");
  const { data: activeAlerts = [], isLoading: alertsLoading, refetch: refetchAlerts } = useActiveAlerts();
  const { data: rules = [], isLoading: rulesLoading } = useAlertRules();
  const { isAdmin } = usePermissions();
  const markRead = useAlertStore((s) => s.markRead);

  // Mark all as read when this page mounts
  useState(() => { markRead(); });

  const filteredAlerts = severityFilter === "all"
    ? activeAlerts
    : activeAlerts.filter((a) => a.severity === severityFilter);

  const criticalCount = activeAlerts.filter((a) => a.severity === "critical").length;
  const warningCount  = activeAlerts.filter((a) => a.severity === "warning").length;
  const infoCount     = activeAlerts.filter((a) => a.severity === "info").length;

  return (
    <div className="flex-1 p-4 md:p-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-xl font-bold text-c-text flex items-center gap-2">
            <Bell size={20} className="text-yellow-500" />
            Alerts
          </h1>
          <p className="text-sm text-c-text-2 mt-0.5">
            {activeAlerts.length} active · {rules.length} rules configured
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetchAlerts()}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { sev: "critical" as const, count: criticalCount, icon: AlertTriangle },
          { sev: "warning"  as const, count: warningCount,  icon: Shield },
          { sev: "info"     as const, count: infoCount,     icon: Bell },
        ].map(({ sev, count, icon: Icon }) => (
          <button
            key={sev}
            type="button"
            onClick={() => setSeverityFilter(severityFilter === sev ? "all" : sev)}
            className={clsx(
              "card p-3 text-left transition-all",
              SEV_CFG[sev].bg,
              severityFilter === sev && "ring-2 ring-offset-1",
              sev === "critical" && severityFilter === sev && "ring-red-500",
              sev === "warning"  && severityFilter === sev && "ring-yellow-500",
              sev === "info"     && severityFilter === sev && "ring-blue-500",
            )}
          >
            <div className="flex items-center gap-2 mb-1">
              <Icon size={14} className={SEV_CFG[sev].text} />
              <span className={clsx("text-xs font-medium", SEV_CFG[sev].text)}>
                {SEV_CFG[sev].label}
              </span>
            </div>
            <p className={clsx("text-2xl font-bold tabular-nums", SEV_CFG[sev].text)}>{count}</p>
          </button>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-c-surface-2 p-1 rounded-lg w-fit">
        {[
          { key: "active" as const, label: "Active Alerts", count: activeAlerts.length },
          { key: "rules"  as const, label: "Alert Rules",   count: rules.length },
        ].map(({ key, label, count }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={clsx(
              "px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-2",
              activeTab === key
                ? "bg-c-surface text-c-text shadow-sm"
                : "text-c-text-2 hover:text-c-text"
            )}
          >
            {label}
            <span className={clsx(
              "text-xs rounded-full px-1.5 py-0.5",
              activeTab === key ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400" : "bg-c-border text-c-text-3"
            )}>
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* Active Alerts tab */}
      {activeTab === "active" && (
        <div className="space-y-3">
          {/* Filter bar */}
          {activeAlerts.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <Filter size={14} className="text-c-text-3" />
              {(["all", "critical", "warning", "info"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSeverityFilter(s)}
                  className={clsx(
                    "text-xs px-3 py-1 rounded-full border transition-colors capitalize",
                    severityFilter === s
                      ? "bg-emerald-600 text-white border-emerald-600"
                      : "border-c-border text-c-text-2 hover:border-c-text-2"
                  )}
                >
                  {s === "all" ? "All" : SEV_CFG[s].label}
                </button>
              ))}
            </div>
          )}

          {alertsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <div key={i} className="card h-20 animate-pulse" />)}
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="card flex flex-col items-center justify-center py-16 text-center">
              <CheckCircle size={40} className="text-emerald-500 mb-3" />
              <p className="text-c-text font-medium">No active alerts</p>
              <p className="text-c-text-3 text-sm mt-1">
                {severityFilter !== "all" ? `No ${severityFilter} alerts at this time` : "All systems are operating normally"}
              </p>
            </div>
          ) : (
            <>
              {criticalCount > 0 && severityFilter === "all" && (
                <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide">
                  Critical ({criticalCount})
                </p>
              )}
              {filteredAlerts
                .sort((a, b) => {
                  const order = { critical: 0, warning: 1, info: 2 };
                  return order[a.severity] - order[b.severity];
                })
                .map((alert) => (
                  <ActiveAlertCard key={alert.id} alert={alert} />
                ))}
            </>
          )}
        </div>
      )}

      {/* Alert Rules tab */}
      {activeTab === "rules" && (
        <div className="space-y-2">
          {rulesLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => <div key={i} className="card h-16 animate-pulse" />)}
            </div>
          ) : rules.length === 0 ? (
            <div className="card flex flex-col items-center justify-center py-16 text-center">
              <BellOff size={40} className="text-c-text-3 mb-3" />
              <p className="text-c-text font-medium">No alert rules configured</p>
              <p className="text-c-text-3 text-sm mt-1">Alert rules are managed in the Sensors section</p>
            </div>
          ) : (
            <>
              <p className="text-xs text-c-text-3 mb-2">{rules.length} rules · {rules.filter(r => r.enabled).length} enabled</p>
              {["critical", "warning", "info"].map((sev) => {
                const group = rules.filter((r) => r.severity === sev);
                if (group.length === 0) return null;
                return (
                  <div key={sev}>
                    <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide mt-4 mb-2">
                      {SEV_CFG[sev as keyof typeof SEV_CFG].label} ({group.length})
                    </p>
                    {group.map((rule) => (
                      <div key={rule.id} className="mb-2">
                        <AlertRuleRow rule={rule} canEdit={isAdmin} />
                      </div>
                    ))}
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}
    </div>
  );
}
