import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useSensorStore } from "@/store/sensorStore";
import { useSensors } from "@/hooks/useSensorData";
import { HistoricalChart } from "@/components/dashboard/HistoricalChart";
import { SensorCard } from "@/components/dashboard/SensorCard";

export function SensorDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: sensors = [] } = useSensors();
  const sensor = sensors.find((s) => s.id === id);
  const liveReadings = useSensorStore((s) => s.liveReadings[id ?? ""] ?? {});

  if (!sensor) {
    return (
      <div className="flex-1 flex items-center justify-center text-c-text-2">
        Sensor not found.
      </div>
    );
  }

  const channels = Object.keys(liveReadings);

  return (
    <div className="flex-1 p-4 md:p-6 overflow-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/" className="text-c-text-2 hover:text-c-text transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-c-text">{sensor.name}</h1>
          <p className="text-sm text-c-text-2">{sensor.sensor_type} · {sensor.protocol}</p>
        </div>
      </div>

      {/* Live card */}
      <div className="max-w-xs mb-6">
        <SensorCard sensor={sensor} />
      </div>

      {/* Historical charts — one per channel */}
      <div className="space-y-4">
        {channels.length > 0 ? (
          channels.map((ch) => (
            <HistoricalChart
              key={ch}
              sensorId={sensor.id}
              channel={ch}
              unit={liveReadings[ch]?.unit}
              label={ch}
            />
          ))
        ) : (
          <div className="bg-c-surface border border-c-border rounded-xl p-6 text-c-text-2 text-sm text-center">
            No data yet — waiting for first reading.
          </div>
        )}
      </div>
    </div>
  );
}
