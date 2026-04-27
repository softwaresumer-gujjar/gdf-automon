/**
 * MQTT → Socket.io bridge.
 * Subscribes to gdf/# on EMQX and emits sensor:reading events to
 * the per-sensor Socket.io room so only subscribed clients receive them.
 */
import mqtt, { MqttClient } from "mqtt";
import { Server } from "socket.io";
import { SensorReading } from "./types";

const MQTT_HOST = process.env.MQTT_HOST ?? "localhost";
const MQTT_PORT = parseInt(process.env.MQTT_PORT ?? "1883");
const MQTT_USERNAME = process.env.MQTT_USERNAME ?? "gdf_realtime";
const MQTT_PASSWORD = process.env.MQTT_PASSWORD ?? "realtime_secret";
const TOPIC_PREFIX = "gdf";

export function startMqttBridge(io: Server): MqttClient {
  const client = mqtt.connect(`mqtt://${MQTT_HOST}:${MQTT_PORT}`, {
    username: MQTT_USERNAME,
    password: MQTT_PASSWORD,
    clientId: `gdf-realtime-gateway-${Math.random().toString(16).slice(2, 8)}`,
    reconnectPeriod: 3000,
    keepalive: 60,
  });

  client.on("connect", () => {
    console.log(`[MQTT] Connected to ${MQTT_HOST}:${MQTT_PORT}`);
    client.subscribe(`${TOPIC_PREFIX}/#`, { qos: 1 }, (err) => {
      if (err) console.error("[MQTT] Subscribe error:", err);
      else console.log(`[MQTT] Subscribed to ${TOPIC_PREFIX}/#`);
    });
  });

  client.on("message", (topic: string, payload: Buffer) => {
    // Topic format: gdf/{sensor_id}/{channel}
    const parts = topic.split("/");
    if (parts.length !== 3 || parts[0] !== TOPIC_PREFIX) return;

    const [, sensor_id, channel] = parts;

    let value: number;
    let unit = "";
    let ts = new Date().toISOString();

    try {
      const data = JSON.parse(payload.toString());
      if (typeof data === "number") {
        value = data;
      } else {
        value = parseFloat(data.value);
        unit = data.unit ?? "";
        ts = data.ts ?? ts;
      }
    } catch {
      value = parseFloat(payload.toString());
      if (isNaN(value)) return;
    }

    const reading: SensorReading = { sensor_id, channel, value, unit, ts };

    // Emit to the sensor-specific room so only subscribed clients receive it
    io.to(`sensor:${sensor_id}`).emit("sensor:reading", reading);

    // Also emit to the "all" room for the main dashboard grid
    io.to("all").emit("sensor:reading", reading);
  });

  client.on("error", (err) => console.error("[MQTT] Error:", err));
  client.on("reconnect", () => console.log("[MQTT] Reconnecting..."));
  client.on("offline", () => console.warn("[MQTT] Client offline"));

  return client;
}
