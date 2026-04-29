import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, ChevronDown, ChevronRight, Target, Trash2, Zap } from "lucide-react";
import { apiFetch } from "@/api/client";
import { usePermissions } from "@/hooks/usePermissions";
import type { Plan, PlanAction } from "@/types/plan";

const ACTION_TYPES = ["notification", "reminder", "sms", "call"] as const;
const TRIGGER_OPTIONS = [
  { value: "any_breach", label: "Any breach" },
  { value: "above_upper", label: "Above upper limit" },
  { value: "below_lower", label: "Below lower limit" },
  { value: "outside_range", label: "Outside range" },
] as const;

const ACTION_COLOR: Record<string, string> = {
  notification: "text-blue-400",
  reminder: "text-emerald-400",
  sms: "text-yellow-400",
  call: "text-red-400",
};

interface SensorOption { id: string; name: string; sensor_type: string }

// ── Plan form ─────────────────────────────────────────────────────────────────

function PlanForm({
  sensors,
  initial,
  onSave,
  onCancel,
}: {
  sensors: SensorOption[];
  initial?: Partial<Plan>;
  onSave: (data: Partial<Plan>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    name: initial?.name ?? "",
    description: initial?.description ?? "",
    sensor_id: initial?.sensor_id ?? (sensors[0]?.id ?? ""),
    channel: initial?.channel ?? "temperature",
    target_value: initial?.target_value ?? 0,
    target_unit: initial?.target_unit ?? "",
    lower_limit: initial?.lower_limit ?? "",
    upper_limit: initial?.upper_limit ?? "",
    enabled: initial?.enabled ?? true,
  });

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSave(form as Partial<Plan>); }}
      className="bg-c-surface-2 border border-c-border rounded-xl p-4 space-y-3"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input required placeholder="Plan name *" value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          className="input-field col-span-full" />
        <select required aria-label="Sensor" value={form.sensor_id}
          onChange={(e) => setForm((f) => ({ ...f, sensor_id: e.target.value }))}
          className="input-field">
          {sensors.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <input required placeholder="Channel (e.g. temperature)" value={form.channel}
          onChange={(e) => setForm((f) => ({ ...f, channel: e.target.value }))}
          className="input-field" />
        <input required type="number" step="any" placeholder="Target value *" value={form.target_value}
          onChange={(e) => setForm((f) => ({ ...f, target_value: parseFloat(e.target.value) }))}
          className="input-field" />
        <input placeholder="Unit (e.g. °C)" value={form.target_unit}
          onChange={(e) => setForm((f) => ({ ...f, target_unit: e.target.value }))}
          className="input-field" />
        <input type="number" step="any" placeholder="Lower limit" value={form.lower_limit}
          onChange={(e) => setForm((f) => ({ ...f, lower_limit: e.target.value }))}
          className="input-field" />
        <input type="number" step="any" placeholder="Upper limit" value={form.upper_limit}
          onChange={(e) => setForm((f) => ({ ...f, upper_limit: e.target.value }))}
          className="input-field" />
        <input placeholder="Description" value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          className="input-field col-span-full" />
      </div>
      <div className="flex gap-2">
        <button type="submit" className="btn-primary flex-1">Save plan</button>
        <button type="button" onClick={onCancel} className="btn-secondary flex-1">Cancel</button>
      </div>
    </form>
  );
}

// ── Action form ───────────────────────────────────────────────────────────────

function ActionForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<PlanAction>;
  onSave: (data: Partial<PlanAction>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    action_type: initial?.action_type ?? "notification",
    trigger_on: initial?.trigger_on ?? "any_breach",
    message_template: initial?.message_template ?? "Sensor {sensor} {channel}: {value} breached target {target} {unit}",
    config_phone: initial?.config?.phone ?? "",
    enabled: initial?.enabled ?? true,
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSave({
          action_type: form.action_type as PlanAction["action_type"],
          trigger_on: form.trigger_on as PlanAction["trigger_on"],
          message_template: form.message_template,
          config: form.config_phone ? { phone: form.config_phone } : {},
          enabled: form.enabled,
        });
      }}
      className="bg-c-surface border border-slate-600 rounded-lg p-3 space-y-2 mt-2"
    >
      <div className="grid grid-cols-2 gap-2">
        <select aria-label="Action type" value={form.action_type}
          onChange={(e) => setForm((f) => ({ ...f, action_type: e.target.value as PlanAction["action_type"] }))}
          className="input-field text-xs">
          {ACTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select aria-label="Trigger condition" value={form.trigger_on}
          onChange={(e) => setForm((f) => ({ ...f, trigger_on: e.target.value as PlanAction["trigger_on"] }))}
          className="input-field text-xs">
          {TRIGGER_OPTIONS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>
      <input placeholder="Message template" value={form.message_template}
        onChange={(e) => setForm((f) => ({ ...f, message_template: e.target.value }))}
        className="input-field text-xs w-full" />
      {(form.action_type === "sms" || form.action_type === "call") && (
        <input placeholder="Phone number (e.g. +15551234567)" value={form.config_phone}
          onChange={(e) => setForm((f) => ({ ...f, config_phone: e.target.value }))}
          className="input-field text-xs w-full" />
      )}
      <div className="flex gap-2">
        <button type="submit" className="btn-primary flex-1 text-xs py-1.5">Add action</button>
        <button type="button" onClick={onCancel} className="btn-secondary flex-1 text-xs py-1.5">Cancel</button>
      </div>
    </form>
  );
}

// ── Plan card with expandable actions ─────────────────────────────────────────

function PlanCard({ plan, canEdit }: { plan: Plan; canEdit: boolean }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [showActionForm, setShowActionForm] = useState(false);

  const { data: actions = [] } = useQuery<PlanAction[]>({
    queryKey: ["plan-actions", plan.id],
    queryFn: () => apiFetch(`/api/plans/${plan.id}/actions`),
    enabled: open,
  });

  const addAction = useMutation({
    mutationFn: (data: Partial<PlanAction>) =>
      apiFetch(`/api/plans/${plan.id}/actions`, { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plan-actions", plan.id] });
      setShowActionForm(false);
    },
  });

  const deleteAction = useMutation({
    mutationFn: (actionId: string) =>
      apiFetch(`/api/plans/${plan.id}/actions/${actionId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plan-actions", plan.id] }),
  });

  const deletePlan = useMutation({
    mutationFn: () => apiFetch(`/api/plans/${plan.id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plans"] }),
  });

  return (
    <div className="bg-c-surface border border-c-border rounded-xl overflow-hidden">
      <div className="flex items-start gap-3 p-4">
        <Target size={18} className="text-emerald-400 mt-0.5 shrink-0" />
        <button
          type="button"
          className="flex-1 min-w-0 text-left"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open ? "true" : "false"}
        >
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-c-text font-medium text-sm">{plan.name}</span>
            {!plan.enabled && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-c-text-2">Disabled</span>
            )}
          </div>
          <p className="text-c-text-2 text-xs mt-0.5">
            Target: <span className="text-c-text">{plan.target_value} {plan.target_unit ?? ""}</span>
            {plan.lower_limit != null && ` · Min: ${plan.lower_limit}`}
            {plan.upper_limit != null && ` · Max: ${plan.upper_limit}`}
          </p>
          <p className="text-c-text-3 text-xs">Channel: {plan.channel}</p>
        </button>
        <div className="flex items-center gap-1 shrink-0">
          {canEdit && (
            <button
              type="button"
              aria-label="Delete plan"
              onClick={() => { if (confirm(`Delete plan "${plan.name}"?`)) deletePlan.mutate(); }}
              className="p-1 text-c-text-3 hover:text-red-400 transition-colors"
            >
              <Trash2 size={14} />
            </button>
          )}
          {open ? <ChevronDown size={16} className="text-c-text-2" /> : <ChevronRight size={16} className="text-c-text-2" />}
        </div>
      </div>

      {open && (
        <div className="border-t border-c-border p-4 space-y-2">
          {plan.description && <p className="text-c-text-2 text-xs mb-3">{plan.description}</p>}
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide">Actions</p>
            {canEdit && !showActionForm && (
              <button type="button" onClick={() => setShowActionForm(true)}
                className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300">
                <Plus size={12} /> Add action
              </button>
            )}
          </div>
          {showActionForm && (
            <ActionForm
              onSave={(data) => addAction.mutate(data)}
              onCancel={() => setShowActionForm(false)}
            />
          )}
          {actions.length === 0 && !showActionForm && (
            <p className="text-c-text-3 text-xs">No actions configured</p>
          )}
          {actions.map((a) => (
            <div key={a.id} className="flex items-center gap-2 bg-c-surface-2 rounded-lg px-3 py-2">
              <Zap size={14} className={ACTION_COLOR[a.action_type] ?? "text-c-text-2"} />
              <div className="flex-1 min-w-0">
                <span className={`text-xs font-medium capitalize ${ACTION_COLOR[a.action_type]}`}>{a.action_type}</span>
                <span className="text-c-text-3 text-xs"> · {TRIGGER_OPTIONS.find((t) => t.value === a.trigger_on)?.label}</span>
                {!a.enabled && <span className="text-xs text-c-text-3"> (disabled)</span>}
              </div>
              {canEdit && (
                <button
                  type="button"
                  aria-label="Delete action"
                  onClick={() => deleteAction.mutate(a.id)}
                  className="p-1 text-c-text-3 hover:text-red-400 transition-colors shrink-0"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function Planning() {
  const qc = useQueryClient();
  const { canManageSensors } = usePermissions();
  const [showForm, setShowForm] = useState(false);

  const { data: plans = [], isLoading } = useQuery<Plan[]>({
    queryKey: ["plans"],
    queryFn: () => apiFetch("/api/plans"),
  });

  const { data: sensors = [] } = useQuery<SensorOption[]>({
    queryKey: ["sensors-list"],
    queryFn: () => apiFetch("/api/sensors"),
  });

  const createPlan = useMutation({
    mutationFn: (data: Partial<Plan>) =>
      apiFetch("/api/plans", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plans"] });
      setShowForm(false);
    },
  });

  return (
    <div className="p-4 md:p-6 pb-24 md:pb-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-c-text">Planning</h1>
          <p className="text-c-text-2 text-sm mt-0.5">Define metric targets and automated actions</p>
        </div>
        {canManageSensors && !showForm && (
          <button type="button" onClick={() => setShowForm(true)}
            className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New plan
          </button>
        )}
      </div>

      {showForm && canManageSensors && (
        <div className="mb-6">
          <PlanForm
            sensors={sensors}
            onSave={(data) => createPlan.mutate(data)}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : plans.length === 0 ? (
        <div className="text-center py-12 text-c-text-3">
          <Target size={40} className="mx-auto mb-3 opacity-40" />
          <p className="mb-1">No plans yet</p>
          <p className="text-xs">Create a plan to define metric targets and automated alerts.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {plans.map((p) => (
            <PlanCard key={p.id} plan={p} canEdit={canManageSensors} />
          ))}
        </div>
      )}
    </div>
  );
}
