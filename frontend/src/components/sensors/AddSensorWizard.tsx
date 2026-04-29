import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  X, ChevronRight, ChevronLeft, CheckCircle, Loader, Thermometer,
  Weight, Droplets, Camera, Cpu, Wifi, AlertCircle, Plus,
} from "lucide-react";
import { apiFetch } from "@/api/client";
import { useSensorTypes } from "@/hooks/useSensorData";
import { useQuery } from "@tanstack/react-query";
import type { SensorType } from "@/types/sensor";

// ── Icon map ─────────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, React.ElementType> = {
  thermometer: Thermometer,
  weight: Weight,
  droplets: Droplets,
  camera: Camera,
  cpu: Cpu,
};

function SensorIcon({ icon, size = 24 }: { icon: string; size?: number }) {
  const Icon = ICON_MAP[icon] ?? Cpu;
  return <Icon size={size} />;
}

// ── Config schema → form fields ───────────────────────────────────────────────

interface SchemaProperty {
  type?: string;
  title?: string;
  description?: string;
  default?: unknown;
  enum?: string[];
  minimum?: number;
  maximum?: number;
}

function SchemaField({
  name,
  prop,
  value,
  onChange,
}: {
  name: string;
  prop: SchemaProperty;
  value: unknown;
  onChange: (val: unknown) => void;
}) {
  const label = prop.title ?? name;
  const placeholder = prop.description ?? prop.title ?? name;
  const baseClass = "input-field w-full";

  if (prop.enum) {
    return (
      <div>
        <label className="block text-xs text-c-text-2 mb-1">{label}</label>
        <select
          aria-label={label}
          value={String(value ?? prop.default ?? prop.enum[0])}
          onChange={(e) => onChange(e.target.value)}
          className={baseClass}
        >
          {prop.enum.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
        {prop.description && <p className="text-xs text-c-text-3 mt-0.5">{prop.description}</p>}
      </div>
    );
  }

  if (prop.type === "boolean") {
    return (
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={Boolean(value ?? prop.default ?? false)}
          onChange={(e) => onChange(e.target.checked)}
          className="accent-emerald-500"
        />
        <span className="text-sm text-c-text">{label}</span>
      </label>
    );
  }

  if (prop.type === "number" || prop.type === "integer") {
    return (
      <div>
        <label className="block text-xs text-c-text-2 mb-1">{label}</label>
        <input
          type="number"
          step={prop.type === "integer" ? "1" : "any"}
          min={prop.minimum}
          max={prop.maximum}
          value={String(value ?? prop.default ?? "")}
          onChange={(e) => onChange(prop.type === "integer" ? parseInt(e.target.value) : parseFloat(e.target.value))}
          className={baseClass}
          placeholder={placeholder}
        />
        {prop.description && <p className="text-xs text-c-text-3 mt-0.5">{prop.description}</p>}
      </div>
    );
  }

  return (
    <div>
      <label className="block text-xs text-c-text-2 mb-1">{label}</label>
      <input
        type="text"
        value={String(value ?? prop.default ?? "")}
        onChange={(e) => onChange(e.target.value)}
        className={baseClass}
        placeholder={placeholder}
      />
      {prop.description && <p className="text-xs text-c-text-3 mt-0.5">{prop.description}</p>}
    </div>
  );
}

// ── Step indicators ───────────────────────────────────────────────────────────

function Steps({ current }: { current: number }) {
  const steps = ["Select Type", "Configure", "Test & Save"];
  return (
    <div className="flex items-center gap-0 mb-6">
      {steps.map((label, i) => (
        <div key={label} className="flex items-center flex-1">
          <div className={`flex items-center gap-1.5 ${i < current ? "text-emerald-400" : i === current ? "text-c-text" : "text-c-text-3"}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0
              ${i < current ? "bg-emerald-600" : i === current ? "bg-emerald-700 ring-2 ring-emerald-500" : "bg-c-surface-2"}`}>
              {i < current ? <CheckCircle size={12} /> : i + 1}
            </div>
            <span className="text-xs font-medium hidden sm:block">{label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-px mx-2 ${i < current ? "bg-emerald-600" : "bg-c-border"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Protocol badge ────────────────────────────────────────────────────────────

const PROTOCOL_COLOR: Record<string, string> = {
  mqtt: "bg-blue-500/15 text-blue-400",
  http: "bg-green-500/15 text-green-400",
  modbus: "bg-orange-500/15 text-orange-400",
  serial: "bg-yellow-500/15 text-yellow-400",
  rtsp: "bg-purple-500/15 text-purple-400",
};

// ── Wizard main component ─────────────────────────────────────────────────────

interface Location {
  id: string;
  name: string;
}

export function AddSensorWizard({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const { data: sensorTypes = [], isLoading: typesLoading } = useSensorTypes();
  const { data: locations = [] } = useQuery<Location[]>({
    queryKey: ["locations"],
    queryFn: () => apiFetch("/api/locations"),
  });

  const [step, setStep] = useState(0);
  const [selectedType, setSelectedType] = useState<SensorType | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [locationId, setLocationId] = useState("");
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [testState, setTestState] = useState<"idle" | "testing" | "ok" | "fail">("idle");
  const [testMessage, setTestMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  // Initialise config defaults from schema when a type is picked
  function selectType(t: SensorType) {
    setSelectedType(t);
    const defaults: Record<string, unknown> = {};
    const props = (t.config_schema?.properties ?? {}) as Record<string, SchemaProperty>;
    for (const [key, prop] of Object.entries(props)) {
      if (prop.default !== undefined) defaults[key] = prop.default;
    }
    setConfig(defaults);
    setStep(1);
  }

  const setConfigField = useCallback((key: string, val: unknown) => {
    setConfig((c) => ({ ...c, [key]: val }));
  }, []);

  async function handleTest() {
    if (!selectedType) return;
    setTestState("testing");
    setTestMessage("");
    try {
      // Create a temporary sensor to test against
      const sensor = await apiFetch<{ id: string }>("/api/sensors", {
        method: "POST",
        body: JSON.stringify({
          name: name || "test-sensor",
          sensor_type: selectedType.sensor_type,
          protocol: selectedType.protocol,
          config,
          location_id: locationId || null,
          description,
        }),
      });
      const result = await apiFetch<{ ok: boolean; message: string }>(`/api/sensors/${sensor.id}/test`);
      // Delete the temporary test sensor
      await apiFetch(`/api/sensors/${sensor.id}`, { method: "DELETE" });
      if (result.ok) {
        setTestState("ok");
        setTestMessage(result.message);
      } else {
        setTestState("fail");
        setTestMessage(result.message);
      }
    } catch (e) {
      setTestState("fail");
      setTestMessage(e instanceof Error ? e.message : "Test failed");
    }
  }

  async function handleSave() {
    if (!selectedType || !name.trim()) return;
    setSaving(true);
    setSaveError("");
    try {
      await apiFetch("/api/sensors", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          sensor_type: selectedType.sensor_type,
          protocol: selectedType.protocol,
          config,
          location_id: locationId || null,
          description: description.trim() || null,
        }),
      });
      qc.invalidateQueries({ queryKey: ["sensors"] });
      onClose();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save sensor");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-c-surface border border-c-border rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-c-border shrink-0">
          <div className="flex items-center gap-2">
            <Plus size={18} className="text-emerald-400" />
            <h2 className="text-base font-bold text-c-text">Add Sensor</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-c-text-3 hover:text-c-text transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <Steps current={step} />

          {/* ── Step 0: Select type ─────────────────────────────────────── */}
          {step === 0 && (
            <div>
              <p className="text-sm text-c-text-2 mb-4">Choose the type of sensor you want to add.</p>
              {typesLoading ? (
                <div className="flex justify-center py-12">
                  <Loader size={24} className="animate-spin text-emerald-400" />
                </div>
              ) : sensorTypes.length === 0 ? (
                <div className="text-center py-12 text-c-text-3">
                  <Cpu size={40} className="mx-auto mb-3 opacity-40" />
                  <p>No sensor types available</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {sensorTypes.map((t) => (
                    <button
                      key={t.sensor_type}
                      type="button"
                      onClick={() => selectType(t)}
                      className="flex items-start gap-3 p-4 bg-c-surface-2 border border-c-border rounded-xl text-left hover:border-emerald-500/50 hover:bg-emerald-500/5 transition-all group"
                    >
                      <div className="w-10 h-10 rounded-lg bg-emerald-600/20 flex items-center justify-center text-emerald-400 shrink-0 group-hover:bg-emerald-600/30 transition-colors">
                        <SensorIcon icon={t.icon} size={20} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-c-text">{t.display_name}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${PROTOCOL_COLOR[t.protocol] ?? "bg-c-border text-c-text-3"}`}>
                            {t.protocol.toUpperCase()}
                          </span>
                        </div>
                        {t.data_channels.length > 0 && (
                          <p className="text-xs text-c-text-3 mt-1">
                            Channels: {t.data_channels.map((c) => c.label).join(", ")}
                          </p>
                        )}
                      </div>
                      <ChevronRight size={16} className="text-c-text-3 mt-1 shrink-0 group-hover:text-emerald-400 transition-colors" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Step 1: Configure ───────────────────────────────────────── */}
          {step === 1 && selectedType && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                <div className="w-9 h-9 rounded-lg bg-emerald-600/20 flex items-center justify-center text-emerald-400 shrink-0">
                  <SensorIcon icon={selectedType.icon} size={18} />
                </div>
                <div>
                  <p className="text-sm font-medium text-c-text">{selectedType.display_name}</p>
                  <p className="text-xs text-c-text-3 capitalize">{selectedType.protocol} protocol</p>
                </div>
              </div>

              {/* Basic info */}
              <div className="space-y-3">
                <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide">Basic Info</p>
                <input
                  required
                  placeholder="Sensor name *"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-field w-full"
                />
                <input
                  placeholder="Description (optional)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="input-field w-full"
                />
                <div>
                  <label className="block text-xs text-c-text-2 mb-1">Location</label>
                  <select
                    aria-label="Location"
                    value={locationId}
                    onChange={(e) => setLocationId(e.target.value)}
                    className="input-field w-full"
                  >
                    <option value="">— No location —</option>
                    {locations.map((l) => (
                      <option key={l.id} value={l.id}>{l.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Protocol config */}
              {Object.keys(selectedType.config_schema?.properties ?? {}).length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide">
                    {selectedType.protocol.toUpperCase()} Configuration
                  </p>
                  {Object.entries(
                    (selectedType.config_schema?.properties ?? {}) as Record<string, SchemaProperty>
                  ).map(([key, prop]) => (
                    <SchemaField
                      key={key}
                      name={key}
                      prop={prop}
                      value={config[key]}
                      onChange={(val) => setConfigField(key, val)}
                    />
                  ))}
                </div>
              )}

              {/* Data channels preview */}
              {selectedType.data_channels.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide mb-2">Data Channels</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedType.data_channels.map((ch) => (
                      <span key={ch.name} className="text-xs bg-c-surface-2 border border-c-border rounded-full px-2.5 py-1">
                        <span className="font-medium text-c-text">{ch.label}</span>
                        <span className="text-c-text-3"> ({ch.unit})</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Step 2: Test & Save ─────────────────────────────────────── */}
          {step === 2 && selectedType && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="bg-c-surface-2 border border-c-border rounded-xl p-4 space-y-2">
                <p className="text-xs font-semibold text-c-text-2 uppercase tracking-wide mb-3">Summary</p>
                <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-sm">
                  <span className="text-c-text-3">Name</span>
                  <span className="text-c-text font-medium">{name}</span>
                  <span className="text-c-text-3">Type</span>
                  <span className="text-c-text">{selectedType.display_name}</span>
                  <span className="text-c-text-3">Protocol</span>
                  <span className="text-c-text capitalize">{selectedType.protocol}</span>
                  {locationId && (
                    <>
                      <span className="text-c-text-3">Location</span>
                      <span className="text-c-text">{locations.find((l) => l.id === locationId)?.name ?? "—"}</span>
                    </>
                  )}
                  {description && (
                    <>
                      <span className="text-c-text-3">Description</span>
                      <span className="text-c-text">{description}</span>
                    </>
                  )}
                </div>
                {Object.entries(config).length > 0 && (
                  <>
                    <div className="border-t border-c-border my-2" />
                    <p className="text-xs text-c-text-2 font-medium mb-1">Configuration</p>
                    <div className="grid grid-cols-2 gap-y-1 gap-x-4 text-xs">
                      {Object.entries(config).map(([k, v]) => (
                        <span key={k} className="contents">
                          <span className="text-c-text-3">{k}</span>
                          <span className="text-c-text font-mono">{String(v)}</span>
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {/* Test connection */}
              <div className="border border-c-border rounded-xl p-4">
                <p className="text-sm font-medium text-c-text mb-3">Test Connection (Optional)</p>
                <p className="text-xs text-c-text-3 mb-3">
                  Creates a temporary sensor, tests the connection, then removes it. Skipping this will save directly.
                </p>
                <button
                  type="button"
                  onClick={handleTest}
                  disabled={testState === "testing"}
                  className="btn-secondary flex items-center gap-2 disabled:opacity-50"
                >
                  {testState === "testing" ? (
                    <><Loader size={14} className="animate-spin" /> Testing…</>
                  ) : (
                    <><Wifi size={14} /> Test Connection</>
                  )}
                </button>
                {(testState === "ok" || testState === "fail") && (
                  <div className={`mt-3 flex items-center gap-2 text-sm ${testState === "ok" ? "text-emerald-400" : "text-red-400"}`}>
                    {testState === "ok" ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                    {testMessage}
                  </div>
                )}
              </div>

              {saveError && (
                <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                  <AlertCircle size={14} />
                  {saveError}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer navigation */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-c-border shrink-0 gap-3">
          <button
            type="button"
            onClick={() => step === 0 ? onClose() : setStep((s) => s - 1)}
            className="btn-secondary flex items-center gap-1.5"
          >
            {step === 0 ? <X size={14} /> : <ChevronLeft size={14} />}
            {step === 0 ? "Cancel" : "Back"}
          </button>

          <div className="flex items-center gap-2">
            {step === 2 && (
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !name.trim()}
                className="btn-primary flex items-center gap-1.5 disabled:opacity-50"
              >
                {saving ? <Loader size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                {saving ? "Saving…" : "Save Sensor"}
              </button>
            )}
            {step < 2 && (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                disabled={step === 1 && !name.trim()}
                className="btn-primary flex items-center gap-1.5 disabled:opacity-50"
              >
                Next
                <ChevronRight size={14} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
