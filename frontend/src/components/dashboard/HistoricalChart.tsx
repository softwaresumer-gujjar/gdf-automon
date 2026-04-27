/**
 * Historical time-series chart using Apache ECharts.
 * Supports 1h / 24h / 7d / 30d range selector.
 */
import { useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import { useTelemetry } from "@/hooks/useSensorData";

interface Props {
  sensorId: string;
  channel: string;
  unit?: string;
  label?: string;
}

const RANGES = [
  { label: "1H", hours: 1 },
  { label: "24H", hours: 24 },
  { label: "7D", hours: 168 },
  { label: "30D", hours: 720 },
];

export function HistoricalChart({ sensorId, channel, unit = "", label = channel }: Props) {
  const [hours, setHours] = useState(1);
  const { data = [], isLoading } = useTelemetry(sensorId, channel, hours);

  const option = useMemo(() => ({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", formatter: (params: unknown[]) => {
      const p = (params as { value: [string, number] }[])[0];
      return `${new Date(p.value[0]).toLocaleTimeString()}<br/>${p.value[1].toFixed(2)} ${unit}`;
    }},
    grid: { left: 50, right: 16, top: 16, bottom: 30 },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: "#334155" } },
      axisLabel: { color: "#94a3b8", fontSize: 11 },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: unit,
      nameTextStyle: { color: "#64748b", fontSize: 11 },
      axisLine: { show: false },
      axisLabel: { color: "#94a3b8", fontSize: 11 },
      splitLine: { lineStyle: { color: "#1e293b" } },
    },
    series: [{
      type: "line",
      data: data.map((r) => [r.time, r.value]),
      smooth: 0.3,
      symbol: "none",
      lineStyle: { color: "#22c55e", width: 2 },
      areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: "rgba(34,197,94,0.2)" }, { offset: 1, color: "rgba(34,197,94,0)" }] } },
    }],
  }), [data, unit]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-white capitalize">{label}</h3>
        <div className="flex gap-1">
          {RANGES.map(({ label: rl, hours: h }) => (
            <button
              key={h}
              onClick={() => setHours(h)}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                hours === h ? "bg-brand-500 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              {rl}
            </button>
          ))}
        </div>
      </div>
      {isLoading ? (
        <div className="h-48 flex items-center justify-center text-slate-500 text-sm">Loading...</div>
      ) : (
        <ReactECharts option={option} style={{ height: 200 }} />
      )}
    </div>
  );
}
