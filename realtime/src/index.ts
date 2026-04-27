import Fastify from "fastify";
import cors from "@fastify/cors";
import { Server } from "socket.io";
import { startMqttBridge } from "./mqtt-bridge";
import { startRedisSubscriber } from "./redis-subscriber";
import type { ServerToClientEvents, ClientToServerEvents } from "./types";

const PORT = parseInt(process.env.PORT ?? "3001");
const CORS_ORIGINS: string[] = JSON.parse(
  process.env.CORS_ORIGINS ?? '["http://localhost:5173"]'
);

async function main() {
  const fastify = Fastify({ logger: true });

  await fastify.register(cors, {
    origin: CORS_ORIGINS,
    credentials: true,
  });

  fastify.get("/health", async () => ({ status: "ok", service: "gdf-automon-realtime" }));

  await fastify.listen({ port: PORT, host: "0.0.0.0" });

  const io = new Server<ClientToServerEvents, ServerToClientEvents>(
    fastify.server,
    {
      cors: {
        origin: CORS_ORIGINS,
        methods: ["GET", "POST"],
        credentials: true,
      },
      transports: ["websocket", "polling"],
      pingInterval: 25000,
      pingTimeout: 60000,
    }
  );

  io.on("connection", (socket) => {
    console.log(`[Socket.io] Client connected: ${socket.id}`);

    // Auto-join "all" room for main dashboard
    socket.join("all");

    // ── Sensor rooms ──────────────────────────────────────────────────────
    socket.on("subscribe:sensor", (sensor_id: string) => {
      socket.join(`sensor:${sensor_id}`);
      console.log(`[Socket.io] ${socket.id} subscribed to sensor ${sensor_id}`);
    });

    socket.on("unsubscribe:sensor", (sensor_id: string) => {
      socket.leave(`sensor:${sensor_id}`);
    });

    // ── Chat rooms ────────────────────────────────────────────────────────
    socket.on("chat:join", (room_id: string) => {
      socket.join(`chat:${room_id}`);
      console.log(`[Socket.io] ${socket.id} joined chat room ${room_id}`);
    });

    socket.on("chat:leave", (room_id: string) => {
      socket.leave(`chat:${room_id}`);
    });

    socket.on("disconnect", (reason) => {
      console.log(`[Socket.io] Client disconnected: ${socket.id} (${reason})`);
    });
  });

  // Start MQTT → Socket.io bridge
  startMqttBridge(io);

  // Start Redis → Socket.io chat bridge
  startRedisSubscriber(io);

  console.log(`[GDF-AutoMon Realtime] Listening on port ${PORT}`);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
