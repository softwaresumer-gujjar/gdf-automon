import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, Thermometer, Droplets, Weight, Milk, Zap,
  Wifi, WifiOff, RefreshCw,
  Power, Camera,
} from "lucide-react";
import { apiFetch } from "@/api/client";
import { clsx } from "clsx";
import type { Sensor } from "@/types/sensor";

// ── Types ─────────────────────────────────────────────────────────────────────

interface LatestReading {
  channel: string;
  value: number;
  unit: string;
  ts: string;
}

interface MonitorCard {
  sensor: Sensor;
  readings: LatestReading[];
  lastSeen: string | null;
  online: boolean;
}

// ── Channel icon map ──────────────────────────────────────────────────────────

const CHANNEL_ICONS: Record<string, React.ElementType> = {
  temperature: Thermometer,
  humidity: Droplets,
  weight: Weight,
  milk_volume: Milk,
  power: Zap,
  status: Power,
};

function ChannelIcon({ channel, size = 16 }: { channel: string; size?: number }) {
  const Icon = CHANNEL_ICONS[channel] ?? Activity;
  return <Icon size={size} />;
}

// ── Sensor monitor card ───────────────────────────────────────────────────────

function SensorMonitorCard({ card }: { card: MonitorCard }) {
  const { sensor, readings, online } = card;

  const isCamera = sensor.sensor_type === "camera" || sensor.protocol === "rtsp";

  return (
    <div className={clsx(
      "bg-c-surface border rounded-xl overflow-hidden transition-all",
      online ? "border-c-border" : "border-red-500/30 opacity-75"
    )}>
      {/* Card header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-c-border bg-c-surface-2/50">
        <div className="flex items-center gap-2 min-w-0">
          <span className={clsx(
            "w-2 h-2 rounded-full shrink-0",
            online ? "bg-emerald-400 animate-pulse" : "bg-red-400"
          )} />
          <p className="text-sm font-medium text-c-text truncate">{sensor.name}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-c-text-3 capitalize hidden sm:block">
            {sensor.sensor_type.replace(/_/g, " ")}
          </span>
          {online ? (
            <Wifi size={14} className="text-emerald-400" />
          ) : (
            <WifiOff size={14} className="text-red-400" />
          )}
        </div>
      </div>

      {/* Camera stream placeholder */}
      {isCamera && (
        <div className="relative bg-black aspect-video flex items-center justify-center">
          <div className="text-center text-c-text-3">
            <Camera size={32} className="mx-auto mb-2 opacity-40" />
            <p className="text-xs">Live stream available via RTSP</p>
            <p className="text-xs mt-1 opacity-60">
              {(sensor.config?.rtsp_url as string) ?? "Configure RTSP URL in sensor settings"}
            </p>
          </div>
        </div>
      )}

      {/* Readings grid */}
      {!isCamera && (
        <div className={clsx(
          "grid gap-px bg-c-border",
          readings.length === 1 ? "grid-cols-1" :
          readings.length === 2 ? "grid-cols-2" :
          "grid-cols-2 sm:grid-cols-3"
        )}>
          {readings.length === 0 ? (
            <div className="col-span-full px-4 py-8 text-center text-c-text-3">
              <Activity size={24} className="mx-auto mb-2 opacity-30" />
              <p className="text-xs">No readings yet</p>
            </div>
          ) : (
            readings.map((r) => (
              <div key={r.channel} className="bg-c-surface px-4 py-4">
                <div className="flex items-center gap-1.5 text-c-text-3 mb-1">
                  <ChannelIcon channel={r.channel} size={12} />
                  <span className="text-xs capitalize">{r.channel.replace(/_/g, " ")}</span>
                </div>
                <p className="text-2xl font-bold tabular-nums text-c-text leading-none">
                  {typeof r.value === "number" ? r.value.toFixed(1) : String(r.value)}
                </p>
                <p className="text-xs text-c-text-3 mt-0.5">{r.unit}</p>
              </div>
            ))
          )}
        </div>
      )}

      {/* Last seen */}
      <div className="px-4 py-2 text-xs text-c-text-3 flex items-center justify-between border-t border-c-border bg-c-surface-2/30">
        <span>
          {card.lastSeen
            ? `Updated ${new Date(card.lastSeen).toLocaleTimeString()}`
            : "Never seen"}
        </span>
        <span className="capitalize">{sensor.protocol}</span>
      </div>
    </div>
  );
}

// ── Device status list (motors, machines, etc.) ───────────────────────────────

const DEVICE_STATUSES = [
  { name: "Milk Chiller #1", type: "chiller", on: true,  location: "Processing Room" },
  { name: "Milk Chiller #2", type: "chiller", on: false, location: "Processing Room" },
  { name: "Motor Pump A",    type: "motor",   on: true,  location: "Barn A" },
  { name: "Motor Pump B",    type: "motor",   on: true,  location: "Barn B" },
  { name: "Milk Packing Machine", type: "machine", on: false, location: "Packing Floor" },
  { name: "Barn Ventilation", type: "motor",  on: true,  location: "Barn A" },
];

function DeviceStatusPanel() {
  return (
    <div className="bg-c-surface border border-c-border rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-c-border flex items-center gap-2">
        <Power size={16} className="text-emerald-400" />
        <h2 className="text-sm font-semibold text-c-text">Device Status</h2>
        <span className="text-xs text-c-text-3 ml-1">
          ({DEVICE_STATUSES.filter((d) => d.on).length} ON / {DEVICE_STATUSES.filter((d) => !d.on).length} OFF)
        </span>
      </div>
      <div className="divide-y divide-c-border">
        {DEVICE_STATUSES.map((device) => (
          <div key={device.name} className="flex items-center gap-3 px-4 py-3 hover:bg-c-surface-2/30 transition-colors">
            <span className={clsx(
              "w-2.5 h-2.5 rounded-full shrink-0",
              device.on ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
            )} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-c-text">{device.name}</p>
              <p className="text-xs text-c-text-3">{device.location}</p>
            </div>
            <span className={clsx(
              "text-xs font-medium px-2 py-0.5 rounded-full",
              device.on
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-slate-700/50 text-c-text-3"
            )}>
              {device.on ? "ON" : "OFF"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function Monitoring() {
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const { data: sensors = [], isLoading: sensorsLoading, refetch } = useQuery<Sensor[]>({
    queryKey: ["sensors-monitor"],
    queryFn: () => apiFetch("/api/sensors"),
    refetchInterval: 30_000,
  });

  const [latestMap, setLatestMap] = useState<Record<string, LatestReading[]>>({});

  // Fetch latest readings for each sensor
  useEffect(() => {
    if (sensors.length === 0) return;
    const fetchAll = async () => {
      const results: Record<string, LatestReading[]> = {};
      await Promise.allSettled(
        sensors.map(async (s) => {
          try {
            const data = await apiFetch<LatestReading[]>(`/api/telemetry/latest?sensor_id=${s.id}`);
            results[s.id] = Array.isArray(data) ? data : [];
          } catch {
            results[s.id] = [];
          }
        })
      );
      setLatestMap(results);
      setLastRefresh(new Date());
    };
    fetchAll();
    const interval = setInterval(fetchAll, 30_000);
    return () => clearInterval(interval);
  }, [sensors]);

  const cards: MonitorCard[] = sensors.map((s) => {
    const readings = latestMap[s.id] ?? [];
    const lastTs = readings.length > 0
      ? readings.reduce((latest, r) => (r.ts > latest ? r.ts : latest), readings[0].ts)
      : null;
    const online = lastTs ? (Date.now() - new Date(lastTs).getTime()) < 5 * 60 * 1000 : false;
    return { sensor: s, readings, lastSeen: lastTs, online };
  });

  const onlineCount = cards.filter((c) => c.online).length;

  return (
    <div className="flex-1 p-4 md:p-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-xl font-bold text-c-text flex items-center gap-2">
            <Activity size={20} className="text-emerald-400" />
            Monitoring
          </h1>
          <p className="text-sm text-c-text-2 mt-0.5">
            {onlineCount} of {cards.length} sensors online · Last updated {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <button
          type="button"
          onClick={() => { refetch(); }}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Total Sensors", value: cards.length, color: "text-c-text" },
          { label: "Online", value: onlineCount, color: "text-emerald-400" },
          { label: "Offline", value: cards.length - onlineCount, color: "text-red-400" },
          { label: "Devices ON", value: DEVICE_STATUSES.filter((d) => d.on).length, color: "text-blue-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-c-surface border border-c-border rounded-xl p-4">
            <p className={clsx("text-2xl font-bold tabular-nums", color)}>{value}</p>
            <p className="text-xs text-c-text-3 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Sensor cards */}
        <div className="xl:col-span-3">
          {sensorsLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-c-surface border border-c-border rounded-xl animate-pulse h-48" />
              ))}
            </div>
          ) : cards.length === 0 ? (
            <div className="bg-c-surface border border-c-border rounded-xl flex flex-col items-center justify-center py-20 text-center">
              <Activity size={48} className="text-c-text-3 mb-4 opacity-30" />
              <p className="text-c-text font-medium">No sensors configured</p>
              <p className="text-c-text-3 text-sm mt-1">Add sensors in the Sensors section to start monitoring</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {cards.map((card) => (
                <SensorMonitorCard key={card.sensor.id} card={card} />
              ))}
            </div>
          )}
        </div>

        {/* Device status panel */}
        <div className="xl:col-span-1">
          <DeviceStatusPanel />
        </div>
      </div>
    </div>
  );
}
