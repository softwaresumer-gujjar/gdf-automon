/**
 * Data hooks for tasks, alerts, plans, and dashboard summaries.
 */
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { ActiveAlert, AlertRule } from "@/types/alert";
import type { Plan, Task } from "@/types/plan";

export function useTasks() {
  return useQuery<Task[]>({
    queryKey: ["tasks"],
    queryFn: () => apiFetch<Task[]>("/api/tasks"),
    refetchInterval: 60_000,
  });
}

export function useActiveAlerts() {
  return useQuery<ActiveAlert[]>({
    queryKey: ["alerts-active"],
    queryFn: () => apiFetch<ActiveAlert[]>("/api/alerts/active"),
    refetchInterval: 30_000,
  });
}

export function useAlertRules() {
  return useQuery<AlertRule[]>({
    queryKey: ["alerts-rules"],
    queryFn: () => apiFetch<AlertRule[]>("/api/alerts/rules"),
    refetchInterval: 60_000,
  });
}

export function usePlans() {
  return useQuery<Plan[]>({
    queryKey: ["plans"],
    queryFn: () => apiFetch<Plan[]>("/api/plans"),
    refetchInterval: 60_000,
  });
}
