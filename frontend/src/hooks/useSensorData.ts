import { useQuery } from "@tanstack/react-query";
import { useSensorStore } from "@/store/sensorStore";
import type { Sensor, SensorReading, SensorType } from "@/types/sensor";

export function useSensors() {
  const setSensors = useSensorStore((s) => s.setSensors);

  return useQuery<Sensor[]>({
    queryKey: ["sensors"],
    queryFn: async () => {
      const res = await fetch("/api/sensors");
      if (!res.ok) throw new Error("Failed to fetch sensors");
      const data = await res.json();
      setSensors(data);
      return data;
    },
    refetchInterval: 30_000,
  });
}

export function useSensorTypes() {
  return useQuery<SensorType[]>({
    queryKey: ["sensor-types"],
    queryFn: async () => {
      const res = await fetch("/api/sensors/types");
      if (!res.ok) throw new Error("Failed to fetch sensor types");
      return res.json();
    },
    staleTime: Infinity, // Types don't change without a restart
  });
}

export function useTelemetry(sensorId: string, channel?: string, hours = 1) {
  return useQuery<SensorReading[]>({
    queryKey: ["telemetry", sensorId, channel, hours],
    queryFn: async () => {
      const start = new Date(Date.now() - hours * 3600_000).toISOString();
      const params = new URLSearchParams({ sensor_id: sensorId, start });
      if (channel) params.set("channel", channel);
      const res = await fetch(`/api/telemetry?${params}`);
      if (!res.ok) throw new Error("Failed to fetch telemetry");
      return res.json();
    },
    enabled: !!sensorId,
    refetchInterval: 60_000,
  });
}

export function useLatestReadings(sensorId: string) {
  return useQuery({
    queryKey: ["telemetry-latest", sensorId],
    queryFn: async () => {
      const res = await fetch(`/api/telemetry/latest?sensor_id=${sensorId}`);
      if (!res.ok) throw new Error("Failed to fetch latest readings");
      return res.json();
    },
    enabled: !!sensorId,
    refetchInterval: 30_000,
  });
}
