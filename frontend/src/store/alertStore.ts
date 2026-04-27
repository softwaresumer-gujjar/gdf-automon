import { create } from "zustand";
import type { ActiveAlert } from "@/types/alert";

interface AlertState {
  activeAlerts: ActiveAlert[];
  unreadCount: number;
  setAlerts: (alerts: ActiveAlert[]) => void;
  markRead: () => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  activeAlerts: [],
  unreadCount: 0,

  setAlerts: (alerts) =>
    set((state) => ({
      activeAlerts: alerts,
      unreadCount: state.unreadCount + Math.max(0, alerts.length - state.activeAlerts.length),
    })),

  markRead: () => set({ unreadCount: 0 }),
}));
