/**
 * Generic sensor card — renders any sensor type based on its channels.
 * Shows live value, sparkline, status badge, and last-updated time.
 */
import { useEffect, useRef, memo } from "react";
import { createChart, IChartApi, ISeriesApi, LineData } from "lightweight-charts";
import { Wifi, Pause, AlertCircle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useSensorStore } from "@/store/sensorStore";
import { useSocketIO } from "@/hooks/useSocketIO";
import { useTheme } from "@/contexts/ThemeContext";
import type { Sensor } from "@/types/sensor";
import { clsx } from "clsx";

interface Props {
  sensor: Sensor;
  primaryChannel?: string;
}

const STATUS_ICONS = {
  active: <Wifi size={14} className="text-brand-400" />,
  paused: <Pause size={14} className="text-yellow-400" />,
  error: <AlertCircle size={14} className="text-red-400" />,
};

const STATUS_LABELS = { active: "Live", paused: "Paused", error: "Error" };

export const SensorCard = memo(function SensorCard({ sensor, primaryChannel }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<"Line"> | null>(null);
  const { subscribeToSensor } = useSocketIO();
  const { theme } = useTheme();
  const liveReadings = useSensorStore((s) => s.liveReadings[sensor.id] ?? {});

  const channel = primaryChannel ?? Object.keys(liveReadings)[0] ?? "value";
  const live = liveReadings[channel];

  useEffect(() => {
    return subscribeToSensor(sensor.id);
  }, [sensor.id, subscribeToSensor]);

  useEffect(() => {
    if (!chartRef.current) return;
    chart.current = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 60,
      layout: { background: { color: "transparent" }, textColor: "transparent" },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: { mode: 0 },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: false },
      timeScale: { visible: false },
      handleScroll: false,
      handleScale: false,
    });
    series.current = chart.current.addSeries("Line" as never, {
      color: "#22c55e",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    } as never);
    return () => { chart.current?.remove(); chart.current = null; };
  }, []);

  // Update chart line color for theme changes
  useEffect(() => {
    if (!series.current) return;
    (series.current as unknown as { applyOptions: (o: object) => void }).applyOptions?.({
      color: theme === "dark" ? "#22c55e" : "#16a34a",
    });
  }, [theme]);

  useEffect(() => {
    if (!live || !series.current) return;
    series.current.update({
      time: Math.floor(new Date(live.ts).getTime() / 1000) as LineData["time"],
      value: live.value,
    });
  }, [live]);

  return (
    <div className={clsx(
      "card p-4 flex flex-col gap-3 transition-all hover:shadow-md",
      sensor.status !== "active" && "opacity-60"
    )}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-c-text truncate">{sensor.name}</p>
          {sensor.location && (
            <p className="text-xs text-c-text-3 truncate">{sensor.location}</p>
          )}
        </div>
        <span className={clsx(
          "flex items-center gap-1.5 text-xs rounded-full px-2 py-0.5 shrink-0",
          sensor.status === "active"  ? "bg-brand-500/10 text-emerald-600 dark:text-brand-400" :
          sensor.status === "paused"  ? "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400" :
                                        "bg-red-500/10 text-red-600 dark:text-red-400"
        )}>
          {STATUS_ICONS[sensor.status]}
          {STATUS_LABELS[sensor.status]}
        </span>
      </div>

      {/* Live value */}
      <div className="flex items-end gap-1">
        <span className="text-3xl font-bold text-c-text tabular-nums">
          {live ? live.value.toFixed(live.value < 10 ? 2 : 1) : "—"}
        </span>
        <span className="text-sm text-c-text-2 mb-1">{live?.unit ?? ""}</span>
      </div>

      {/* Sparkline */}
      <div ref={chartRef} className="h-[60px] w-full" />

      {/* Last updated */}
      <p className="text-xs text-c-text-3">
        {live ? `Updated ${formatDistanceToNow(new Date(live.ts))} ago` : "No data yet"}
      </p>
    </div>
  );
});
