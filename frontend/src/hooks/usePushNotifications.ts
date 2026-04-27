/**
 * Web Push notification subscription lifecycle hook.
 * Requests permission, subscribes the browser, and sends the
 * subscription to the backend (authenticated) for storage.
 */
import { useState, useCallback } from "react";
import { apiFetch } from "@/api/client";

export type PushState = "unsupported" | "denied" | "default" | "subscribed";

export function usePushNotifications() {
  const [state, setState] = useState<PushState>(
    !("Notification" in window) || !("serviceWorker" in navigator)
      ? "unsupported"
      : (Notification.permission as PushState)
  );

  const subscribe = useCallback(async () => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setState("unsupported");
      return;
    }

    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      setState("denied");
      return;
    }

    try {
      const { publicKey } = await apiFetch<{ publicKey: string }>("/api/push/vapid-public-key");

      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });

      await apiFetch("/api/push/subscribe", {
        method: "POST",
        body: JSON.stringify({
          endpoint: subscription.endpoint,
          keys: {
            p256dh: arrayBufferToBase64(subscription.getKey("p256dh")!),
            auth: arrayBufferToBase64(subscription.getKey("auth")!),
          },
        }),
      });

      setState("subscribed");
    } catch (err) {
      console.error("Push subscription failed:", err);
    }
  }, []);

  return { state, subscribe };
}

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const buf = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) buf[i] = rawData.charCodeAt(i);
  return buf.buffer;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}
