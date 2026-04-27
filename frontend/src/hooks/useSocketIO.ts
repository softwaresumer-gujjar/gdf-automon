/**
 * Socket.io hook — connects to the realtime gateway and routes
 * incoming sensor readings to the Zustand store.
 * Components subscribe to specific sensors via subscribeToSensor().
 */
import { useEffect, useRef, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import { useSensorStore } from "@/store/sensorStore";
import type { LiveReading } from "@/types/sensor";

const REALTIME_URL = import.meta.env.VITE_REALTIME_URL ?? "";

type IOSocket = Socket<
  { "sensor:reading": (r: LiveReading) => void },
  { "subscribe:sensor": (id: string) => void; "unsubscribe:sensor": (id: string) => void }
>;

let globalSocket: IOSocket | null = null;

function getSocket(): IOSocket {
  if (!globalSocket) {
    globalSocket = io(REALTIME_URL, {
      path: "/socket.io",
      transports: ["websocket"],
      reconnectionDelay: 1000,
      reconnectionAttempts: Infinity,
    }) as IOSocket;
  }
  return globalSocket;
}

export function useSocketIO() {
  const socketRef = useRef<IOSocket | null>(null);
  const updateLiveReading = useSensorStore((s) => s.updateLiveReading);

  useEffect(() => {
    const socket = getSocket();
    socketRef.current = socket;

    socket.on("sensor:reading", updateLiveReading);

    return () => {
      socket.off("sensor:reading", updateLiveReading);
    };
  }, [updateLiveReading]);

  const subscribeToSensor = useCallback((sensorId: string) => {
    socketRef.current?.emit("subscribe:sensor", sensorId);
    return () => { socketRef.current?.emit("unsubscribe:sensor", sensorId); };
  }, []);

  return { subscribeToSensor };
}
