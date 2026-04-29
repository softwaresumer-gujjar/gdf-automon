import { useQuery } from "@tanstack/react-query";
import { useSensorStore } from "@/store/sensorStore";
import { apiFetch } from "@/api/client";
import type { Sensor, SensorReading, SensorType } from "@/types/sensor";

export function useSensors() {
  const setSensors = useSensorStore((s) => s.setSensors);

  return useQuery<Sensor[]>({
    queryKey: ["sensors"],
    queryFn: async () => {
      const data = await apiFetch<Sensor[]>("/api/sensors");
      setSensors(data);
      return data;
    },
    refetchInterval: 30_000,
  });
}

export function useSensorTypes() {
  return useQuery<SensorType[]>({
    queryKey: ["sensor-types"],
    queryFn: () => apiFetch<SensorType[]>("/api/sensors/types"),
    staleTime: Infinity,
  });
}

export function useTelemetry(sensorId: string, channel?: string, hours = 1) {
  return useQuery<SensorReading[]>({
    queryKey: ["telemetry", sensorId, channel, hours],
    queryFn: () => {
      const start = new Date(Date.now() - hours * 3600_000).toISOString();
      const params = new URLSearchParams({ sensor_id: sensorId, start });
      if (channel) params.set("channel", channel);
      return apiFetch<SensorReading[]>(`/api/telemetry?${params}`);
    },
    enabled: !!sensorId,
    refetchInterval: 60_000,
  });
}

export function useLatestReadings(sensorId: string) {
  return useQuery({
    queryKey: ["telemetry-latest", sensorId],
    queryFn: () => apiFetch(`/api/telemetry/latest?sensor_id=${sensorId}`),
    enabled: !!sensorId,
    refetchInterval: 30_000,
  });
}
