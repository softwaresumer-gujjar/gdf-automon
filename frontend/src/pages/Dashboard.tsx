import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import ReactECharts from "echarts-for-react";
import {
  Activity, AlertTriangle, CheckCircle, Clock, Plus,
  TrendingUp, Wifi, WifiOff, Zap, ChevronRight,
  Thermometer, Weight, FlaskConical, Camera,
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { useSensors } from "@/hooks/useSensorData";
import { useActiveAlerts, useTasks, usePlans } from "@/hooks/useAppData";
import { useSocketIO } from "@/hooks/useSocketIO";
import { useTheme } from "@/contexts/ThemeContext";
import { SensorCard } from "@/components/dashboard/SensorCard";
import type { Sensor } from "@/types/sensor";
import type { ActiveAlert } from "@/types/alert";
import type { Task } from "@/types/plan";
import { clsx } from "clsx";

// ── helpers ────────────────────────────────────────────────────────────────

const SEVERITY_CFG = {
  critical: { label: "Critical", color: "text-red-500",    bg: "bg-red-500/10",    dot: "bg-red-500" },
  warning:  { label: "Warning",  color: "text-yellow-500", bg: "bg-yellow-500/10", dot: "bg-yellow-500" },
  info:     { label: "Info",     color: "text-blue-500",   bg: "bg-blue-500/10",   dot: "bg-blue-500" },
} as const;

const TASK_STATUS_CFG = {
  open:      { label: "Open",        color: "text-blue-500",    bg: "bg-blue-500/10" },
  submitted: { label: "Under Review", color: "text-yellow-500",  bg: "bg-yellow-500/10" },
  done:      { label: "Done",        color: "text-emerald-500", bg: "bg-emerald-500/10" },
  rejected:  { label: "Returned",    color: "text-red-500",     bg: "bg-red-500/10" },
} as const;

const CATEGORY_CFG: Record<string, { label: string; color: string; icon: typeof Thermometer }> = {
  temperature:   { label: "Temperature",   color: "#f97316", icon: Thermometer },
  weight:        { label: "Weight",        color: "#3b82f6", icon: Weight },
  milk_analyzer: { label: "Milk Analyzer", color: "#a855f7", icon: FlaskConical },
  camera:        { label: "Camera",        color: "#ec4899", icon: Camera },
};

// ── sub-components ─────────────────────────────────────────────────────────

function StatCard({
  label, value, sub, icon: Icon, trend, color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: typeof Activity;
  trend?: "up" | "down" | "neutral";
  color: string;
}) {
  return (
    <div className="card p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-c-text-2">{label}</p>
        <div className={clsx("w-9 h-9 rounded-lg flex items-center justify-center", color)}>
          <Icon size={18} className="text-white" />
        </div>
      </div>
      <div>
        <p className="text-2xl font-bold text-c-text tabular-nums">{value}</p>
        {sub && <p className="text-xs text-c-text-3 mt-0.5">{sub}</p>}
      </div>
      {trend && (
        <div className={clsx("flex items-center gap-1 text-xs font-medium",
          trend === "up" ? "text-emerald-500" : trend === "down" ? "text-red-500" : "text-c-text-3"
        )}>
          <TrendingUp size={12} />
          <span>{trend === "up" ? "All systems nominal" : trend === "down" ? "Needs attention" : "Stable"}</span>
        </div>
      )}
    </div>
  );
}

function AlertRow({ alert }: { alert: ActiveAlert }) {
  const cfg = SEVERITY_CFG[alert.severity];
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-c-border last:border-0">
      <span className={clsx("w-2 h-2 rounded-full mt-1.5 shrink-0", cfg.dot)} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-c-text truncate">{alert.message}</p>
        <p className="text-xs text-c-text-3 mt-0.5">
          {formatDistanceToNow(new Date(alert.triggered_at), { addSuffix: true })}
        </p>
      </div>
      <span className={clsx("text-xs px-2 py-0.5 rounded-full shrink-0", cfg.bg, cfg.color)}>
        {cfg.label}
      </span>
    </div>
  );
}

function TaskRow({ task }: { task: Task }) {
  const cfg = TASK_STATUS_CFG[task.status];
  return (
    <Link
      to={`/tasks/${task.id}`}
      className="flex items-center gap-3 py-2.5 border-b border-c-border last:border-0 hover:bg-c-surface-2 -mx-4 px-4 transition-colors rounded-lg"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm text-c-text truncate font-medium">{task.title}</p>
        {task.deadline && (
          <p className="text-xs text-c-text-3 mt-0.5">
            Due {format(new Date(task.deadline), "MMM d")}
          </p>
        )}
      </div>
      <span className={clsx("text-xs px-2 py-0.5 rounded-full shrink-0", cfg.bg, cfg.color)}>
        {cfg.label}
      </span>
      <ChevronRight size={14} className="text-c-text-3 shrink-0" />
    </Link>
  );
}

// ── main component ─────────────────────────────────────────────────────────

export function Dashboard() {
  const { data: sensors = [], isLoading: sensorsLoading } = useSensors();
  const { data: activeAlerts = [] } = useActiveAlerts();
  const { data: tasks = [] } = useTasks();
  const { data: plans = [] } = usePlans();
  const { subscribeToSensor } = useSocketIO();
  const { theme } = useTheme();

  useEffect(() => {
    const unsubs = sensors.map((s: Sensor) => subscribeToSensor(s.id));
    return () => unsubs.forEach((fn: () => void) => fn());
  }, [sensors, subscribeToSensor]);

  // ── computed stats ───────────────────────────────────────────────────────

  const onlineSensors = sensors.filter((s) => s.status === "active").length;
  const criticalAlerts = activeAlerts.filter((a) => a.severity === "critical").length;
  const warningAlerts  = activeAlerts.filter((a) => a.severity === "warning").length;
  const openTasks      = tasks.filter((t) => t.status === "open").length;
  const activePlans    = plans.filter((p) => p.enabled).length;

  // ── sensor category donut chart data ────────────────────────────────────

  const categoryData = useMemo(() => {
    const groups: Record<string, number> = {};
    for (const s of sensors) {
      groups[s.sensor_type] = (groups[s.sensor_type] ?? 0) + 1;
    }
    return Object.entries(groups).map(([type, count]) => ({
      name: CATEGORY_CFG[type]?.label ?? type,
      value: count,
      itemStyle: { color: CATEGORY_CFG[type]?.color ?? "#94a3b8" },
    }));
  }, [sensors]);

  const donutOption = useMemo(() => ({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} sensors ({d}%)",
      backgroundColor: theme === "dark" ? "#1e293b" : "#ffffff",
      borderColor: theme === "dark" ? "#334155" : "#e2e8f0",
      textStyle: { color: theme === "dark" ? "#f8fafc" : "#0f172a" },
    },
    legend: {
      orient: "vertical",
      right: 10,
      top: "center",
      textStyle: { color: theme === "dark" ? "#94a3b8" : "#64748b", fontSize: 12 },
    },
    series: [{
      type: "pie",
      radius: ["50%", "75%"],
      center: ["35%", "50%"],
      data: categoryData,
      label: { show: false },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,0.3)" },
      },
    }],
  }), [categoryData, theme]);

  // ── task status bar chart ────────────────────────────────────────────────

  const taskCounts = useMemo(() => {
    const c = { open: 0, submitted: 0, done: 0, rejected: 0 };
    for (const t of tasks) c[t.status]++;
    return c;
  }, [tasks]);

  const barOption = useMemo(() => ({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: theme === "dark" ? "#1e293b" : "#ffffff",
      borderColor: theme === "dark" ? "#334155" : "#e2e8f0",
      textStyle: { color: theme === "dark" ? "#f8fafc" : "#0f172a" },
    },
    grid: { top: 8, right: 8, bottom: 24, left: 32, containLabel: false },
    xAxis: {
      type: "category",
      data: ["Open", "Review", "Done", "Returned"],
      axisLabel: { color: theme === "dark" ? "#94a3b8" : "#64748b", fontSize: 11 },
      axisLine: { lineStyle: { color: theme === "dark" ? "#334155" : "#e2e8f0" } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: theme === "dark" ? "#94a3b8" : "#64748b", fontSize: 11 },
      splitLine: { lineStyle: { color: theme === "dark" ? "#1e293b" : "#f1f5f9" } },
    },
    series: [{
      type: "bar",
      barMaxWidth: 40,
      borderRadius: [4, 4, 0, 0],
      data: [
        { value: taskCounts.open,      itemStyle: { color: "#3b82f6" } },
        { value: taskCounts.submitted, itemStyle: { color: "#f59e0b" } },
        { value: taskCounts.done,      itemStyle: { color: "#22c55e" } },
        { value: taskCounts.rejected,  itemStyle: { color: "#ef4444" } },
      ],
    }],
  }), [taskCounts, theme]);

  // ── alert severity breakdown for stat card ───────────────────────────────

  const alertSub = criticalAlerts > 0
    ? `${criticalAlerts} critical, ${warningAlerts} warning`
    : warningAlerts > 0
      ? `${warningAlerts} warning`
      : "All clear";

  return (
    <div className="flex-1 p-4 md:p-6 overflow-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-c-text">Dashboard</h1>
          <p className="text-sm text-c-text-2">Farm monitoring overview</p>
        </div>
        <Link
          to="/sensors?add=true"
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium px-3 py-2 rounded-lg transition-colors"
        >
          <Plus size={16} />
          Add Sensor
        </Link>
      </div>

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <StatCard
          label="Sensors Online"
          value={`${onlineSensors}/${sensors.length}`}
          sub={sensorsLoading ? "Loading…" : `${sensors.length - onlineSensors} offline`}
          icon={onlineSensors === sensors.length ? Wifi : WifiOff}
          color={onlineSensors === sensors.length ? "bg-emerald-600" : "bg-yellow-600"}
          trend={onlineSensors === sensors.length ? "up" : "neutral"}
        />
        <StatCard
          label="Active Alerts"
          value={activeAlerts.length}
          sub={alertSub}
          icon={AlertTriangle}
          color={criticalAlerts > 0 ? "bg-red-600" : warningAlerts > 0 ? "bg-yellow-600" : "bg-emerald-600"}
          trend={criticalAlerts > 0 ? "down" : "neutral"}
        />
        <StatCard
          label="Open Tasks"
          value={openTasks}
          sub={`${tasks.filter(t => t.status === "submitted").length} under review`}
          icon={Clock}
          color="bg-blue-600"
          trend="neutral"
        />
        <StatCard
          label="Active Plans"
          value={activePlans}
          sub={`${plans.length - activePlans} paused`}
          icon={CheckCircle}
          color="bg-purple-600"
          trend="neutral"
        />
      </div>

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Sensor category donut */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-c-text">Sensors by Category</h2>
            <span className="text-xs text-c-text-3">{sensors.length} total</span>
          </div>
          {sensors.length > 0 ? (
            <>
              <ReactECharts option={donutOption} style={{ height: 180 }} notMerge />
              <div className="grid grid-cols-2 gap-2 mt-2">
                {categoryData.map((cat) => {
                  const sensorType = Object.keys(CATEGORY_CFG).find(
                    (k) => CATEGORY_CFG[k].label === cat.name
                  );
                  const cfg = sensorType ? CATEGORY_CFG[sensorType] : null;
                  const Icon = cfg?.icon ?? Activity;
                  return (
                    <div key={cat.name} className="flex items-center gap-2">
                      <Icon size={14} style={{ color: cat.itemStyle.color }} />
                      <span className="text-xs text-c-text-2">{cat.name}</span>
                      <span className="text-xs font-semibold text-c-text ml-auto">{cat.value}</span>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="h-40 flex items-center justify-center text-c-text-3 text-sm">No sensors yet</div>
          )}
        </div>

        {/* Task status bar chart */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-c-text">Task Status</h2>
            <Link to="/tasks" className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline">
              View all →
            </Link>
          </div>
          {tasks.length > 0 ? (
            <>
              <ReactECharts option={barOption} style={{ height: 180 }} notMerge />
              <div className="grid grid-cols-4 gap-1 mt-2 text-center">
                {[
                  { label: "Open",    count: taskCounts.open,      color: "text-blue-500" },
                  { label: "Review",  count: taskCounts.submitted,  color: "text-yellow-500" },
                  { label: "Done",    count: taskCounts.done,       color: "text-emerald-500" },
                  { label: "Returned",count: taskCounts.rejected,   color: "text-red-500" },
                ].map(({ label, count, color }) => (
                  <div key={label}>
                    <p className={clsx("text-lg font-bold tabular-nums", color)}>{count}</p>
                    <p className="text-xs text-c-text-3">{label}</p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-40 flex items-center justify-center text-c-text-3 text-sm">No tasks yet</div>
          )}
        </div>
      </div>

      {/* ── Widgets row ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Recent alerts */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-c-text flex items-center gap-2">
              <AlertTriangle size={14} className="text-red-500" />
              Recent Alerts
            </h2>
            <Link to="/alerts" className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline">
              View all →
            </Link>
          </div>
          {activeAlerts.length === 0 ? (
            <div className="py-6 text-center text-sm text-c-text-3">
              <CheckCircle size={24} className="text-emerald-500 mx-auto mb-2" />
              No active alerts
            </div>
          ) : (
            <div>
              {activeAlerts.slice(0, 4).map((a) => (
                <AlertRow key={a.id} alert={a} />
              ))}
              {activeAlerts.length > 4 && (
                <Link to="/alerts" className="block mt-2 text-xs text-c-text-3 hover:text-c-text-2 text-center">
                  +{activeAlerts.length - 4} more alerts
                </Link>
              )}
            </div>
          )}
        </div>

        {/* Recent tasks */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-c-text flex items-center gap-2">
              <Clock size={14} className="text-blue-500" />
              Tasks
            </h2>
            <Link to="/tasks" className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline">
              View all →
            </Link>
          </div>
          {tasks.length === 0 ? (
            <div className="py-6 text-center text-sm text-c-text-3">No tasks yet</div>
          ) : (
            tasks.slice(0, 4).map((t) => <TaskRow key={t.id} task={t} />)
          )}
        </div>

        {/* Active plans */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-c-text flex items-center gap-2">
              <Zap size={14} className="text-purple-500" />
              Active Plans
            </h2>
            <Link to="/planning" className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline">
              View all →
            </Link>
          </div>
          {plans.length === 0 ? (
            <div className="py-6 text-center text-sm text-c-text-3">No plans configured</div>
          ) : (
            <div className="space-y-2">
              {plans.filter(p => p.enabled).slice(0, 4).map((plan) => (
                <div key={plan.id} className="flex items-start gap-2 py-2 border-b border-c-border last:border-0">
                  <div className="w-2 h-2 rounded-full bg-purple-500 mt-1.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-c-text font-medium truncate">{plan.name}</p>
                    <p className="text-xs text-c-text-3 mt-0.5">
                      Target: {plan.target_value} {plan.target_unit ?? ""} · {plan.channel}
                    </p>
                  </div>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shrink-0">
                    Active
                  </span>
                </div>
              ))}
              {plans.filter(p => !p.enabled).length > 0 && (
                <p className="text-xs text-c-text-3 text-center pt-1">
                  +{plans.filter(p => !p.enabled).length} paused
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Live Sensor Grid ── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-c-text flex items-center gap-2">
            <Activity size={14} className="text-emerald-500" />
            Live Sensors
            <span className="text-xs text-c-text-3 font-normal">({sensors.length})</span>
          </h2>
          <Link to="/sensors" className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline">
            Manage →
          </Link>
        </div>

        {sensorsLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="card h-48 animate-pulse" />
            ))}
          </div>
        ) : sensors.length === 0 ? (
          <div className="card flex flex-col items-center justify-center py-12 text-center">
            <WifiOff size={32} className="text-c-text-3 mb-3" />
            <p className="text-c-text-2 font-medium mb-1">No sensors connected</p>
            <p className="text-c-text-3 text-sm mb-4">Add your first sensor to start monitoring</p>
            <Link to="/sensors?add=true" className="btn-primary">Add First Sensor</Link>
          </div>
        ) : (
          /* Group by category */
          Object.entries(
            sensors.reduce((acc: Record<string, typeof sensors>, s) => {
              (acc[s.sensor_type] ??= []).push(s);
              return acc;
            }, {})
          ).map(([type, group]) => {
            const cfg = CATEGORY_CFG[type];
            const Icon = cfg?.icon ?? Activity;
            return (
              <div key={type} className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <Icon size={14} style={{ color: cfg?.color ?? "#94a3b8" }} />
                  <span className="text-xs font-semibold text-c-text-2 uppercase tracking-wide">
                    {cfg?.label ?? type}
                  </span>
                  <span className="text-xs text-c-text-3">({group.length})</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {group.map((sensor) => (
                    <Link key={sensor.id} to={`/sensors/${sensor.id}`}>
                      <SensorCard sensor={sensor} />
                    </Link>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
