import { create } from "zustand";
import type { Sensor, LiveReading } from "@/types/sensor";

interface SensorState {
  sensors: Sensor[];
  liveReadings: Record<string, Record<string, LiveReading>>; // sensor_id → channel → reading
  setSensors: (sensors: Sensor[]) => void;
  updateSensorStatus: (id: string, status: Sensor["status"]) => void;
  updateLiveReading: (reading: LiveReading) => void;
}

export const useSensorStore = create<SensorState>((set) => ({
  sensors: [],
  liveReadings: {},

  setSensors: (sensors) => set({ sensors }),

  updateSensorStatus: (id, status) =>
    set((state) => ({
      sensors: state.sensors.map((s) => (s.id === id ? { ...s, status } : s)),
    })),

  updateLiveReading: (reading) =>
    set((state) => ({
      liveReadings: {
        ...state.liveReadings,
        [reading.sensor_id]: {
          ...(state.liveReadings[reading.sensor_id] ?? {}),
          [reading.channel]: reading,
        },
      },
    })),
}));
