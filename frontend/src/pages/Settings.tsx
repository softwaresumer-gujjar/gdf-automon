import { Bell, BellOff, Smartphone, User } from "lucide-react";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { useAuth } from "@/contexts/AuthContext";
import { NotificationSettings } from "./NotificationSettings";

export function Settings() {
  const { state, subscribe } = usePushNotifications();
  const { user } = useAuth();

  return (
    <div className="flex-1 p-4 md:p-6 pb-24 md:pb-6 overflow-auto max-w-2xl">
      <h1 className="text-xl font-bold text-c-text mb-6">Settings</h1>

      {/* Account info */}
      <section className="bg-c-surface border border-c-border rounded-xl p-5 mb-4">
        <h2 className="text-sm font-semibold text-c-text mb-3 flex items-center gap-2">
          <User size={16} /> Account
        </h2>
        <div className="space-y-1">
          <p className="text-sm text-c-text-2">{user?.full_name}</p>
          <p className="text-xs text-c-text-3">{user?.email}</p>
          <p className="text-xs text-c-text-3 capitalize">{user?.role?.replace("_", " ")}</p>
        </div>
      </section>

      {/* Push toggle */}
      <section className="bg-c-surface border border-c-border rounded-xl p-5 mb-4">
        <h2 className="text-sm font-semibold text-c-text mb-4 flex items-center gap-2">
          <Bell size={16} /> Push Notifications
        </h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-c-text-2">Browser push notifications</p>
            <p className="text-xs text-c-text-3 mt-0.5">
              Receive alerts when sensor thresholds are breached, even when the app is in the background.
            </p>
          </div>
          <div className="ml-4 flex-shrink-0">
            {state === "subscribed" ? (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full">
                <Bell size={12} /> Enabled
              </span>
            ) : state === "denied" ? (
              <span className="flex items-center gap-1.5 text-xs text-red-400 bg-red-500/10 px-3 py-1.5 rounded-full">
                <BellOff size={12} /> Blocked
              </span>
            ) : state === "unsupported" ? (
              <span className="text-xs text-c-text-3">Not supported</span>
            ) : (
              <button
                type="button"
                onClick={subscribe}
                className="bg-emerald-600 hover:bg-emerald-500 text-c-text text-xs px-4 py-2 rounded-lg transition-colors"
              >
                Enable Notifications
              </button>
            )}
          </div>
        </div>
        {state === "denied" && (
          <p className="text-xs text-c-text-3 mt-3 bg-c-surface-2 rounded-lg p-3">
            Notifications are blocked. Click the lock icon in your browser's address bar and allow
            notifications for this site, then reload.
          </p>
        )}
      </section>

      {/* Per-user notification preference rules */}
      {state === "subscribed" && (
        <section className="bg-c-surface border border-c-border rounded-xl p-5 mb-4">
          <NotificationSettings />
        </section>
      )}

      {/* PWA install hint */}
      <section className="bg-c-surface border border-c-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-c-text mb-4 flex items-center gap-2">
          <Smartphone size={16} /> Install as App
        </h2>
        <p className="text-sm text-c-text-2">
          GDF AutoMon is a Progressive Web App. Install it from your browser's address bar
          (look for the "Install" or "Add to Home Screen" prompt) to use it like a native app —
          works offline and receives push notifications on all platforms.
        </p>
      </section>
    </div>
  );
}
