/**
 * Redis Pub/Sub subscriber for chat message broadcasting.
 * Subscribes to "chat:*" channels published by the FastAPI backend
 * and re-emits them to the appropriate Socket.io room.
 */
import Redis from "ioredis";
import { Server } from "socket.io";
import type { ServerToClientEvents, ClientToServerEvents } from "./types";

const REDIS_URL = process.env.REDIS_URL ?? "redis://localhost:6379/0";

export function startRedisSubscriber(
  io: Server<ClientToServerEvents, ServerToClientEvents>
): void {
  const sub = new Redis(REDIS_URL, { lazyConnect: true });

  sub.connect().catch((err: Error) => {
    console.error("[Redis] Connection error:", err.message);
  });

  sub.on("connect", () => {
    console.log("[Redis] Connected for chat pub/sub");
    sub.psubscribe("chat:*", (err) => {
      if (err) console.error("[Redis] psubscribe error:", err);
      else console.log("[Redis] Subscribed to chat:* channels");
    });
  });

  sub.on("pmessage", (_pattern: string, channel: string, message: string) => {
    // channel format: "chat:{room_id}"
    const roomId = channel.slice("chat:".length);
    try {
      const data = JSON.parse(message);
      io.to(`chat:${roomId}`).emit("chat:message", data);
    } catch (e) {
      console.error("[Redis] Failed to parse chat message:", e);
    }
  });

  sub.on("error", (err: Error) => console.error("[Redis] Error:", err.message));
  sub.on("reconnecting", () => console.log("[Redis] Reconnecting..."));
}
