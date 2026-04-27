import { useState, useEffect, FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, CheckCircle, XCircle, Loader } from "lucide-react";
import { apiFetch } from "@/api/client";
import { AuthCard } from "@/components/auth/AuthCard";

function PasswordField({
  id,
  label,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-c-text-2 mb-1">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          required
          minLength={8}
          autoComplete="new-password"
          className="input-field w-full pr-10"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          aria-label={show ? "Hide password" : "Show password"}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-c-text-2 hover:text-c-text transition-colors"
        >
          {show ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    </div>
  );
}

type TokenStatus = "checking" | "valid" | "invalid";

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();

  const [tokenStatus, setTokenStatus] = useState<TokenStatus>("checking");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  // Validate token on mount
  useEffect(() => {
    if (!token) {
      setTokenStatus("invalid");
      return;
    }
    apiFetch<{ valid: boolean }>(`/api/auth/reset-password/validate?token=${encodeURIComponent(token)}`)
      .then(({ valid }) => setTokenStatus(valid ? "valid" : "invalid"))
      .catch(() => setTokenStatus("invalid"));
  }, [token]);

  const passwordsMatch = password === confirm;
  const canSubmit = password.length >= 8 && passwordsMatch && !loading;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!passwordsMatch) { setError("Passwords do not match"); return; }
    setLoading(true);
    try {
      await apiFetch("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      });
      setDone(true);
      setTimeout(() => navigate("/login", { replace: true }), 2500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to reset password");
    } finally {
      setLoading(false);
    }
  }

  // ── Checking token ─────────────────────────────────────────────────────────
  if (tokenStatus === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-c-bg">
        <Loader size={28} className="text-emerald-400 animate-spin" />
      </div>
    );
  }

  // ── Invalid / expired token ────────────────────────────────────────────────
  if (tokenStatus === "invalid") {
    return (
      <AuthCard title="Link expired or invalid" subtitle="">
        <div className="text-center py-4 space-y-3">
          <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center mx-auto">
            <XCircle size={28} className="text-red-400" />
          </div>
          <p className="text-c-text-2 text-sm">
            This password reset link is invalid or has already expired.
          </p>
          <Link
            to="/forgot-password"
            className="inline-block mt-2 btn-primary text-sm"
          >
            Request a new link
          </Link>
          <p className="text-c-text-3 text-xs">
            Reset links expire after 1 hour.
          </p>
        </div>
      </AuthCard>
    );
  }

  // ── Success ────────────────────────────────────────────────────────────────
  if (done) {
    return (
      <AuthCard title="Password updated!" subtitle="">
        <div className="text-center py-4 space-y-3">
          <div className="w-14 h-14 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto">
            <CheckCircle size={28} className="text-emerald-400" />
          </div>
          <p className="text-c-text-2 text-sm">
            Your password has been changed. Redirecting to sign in…
          </p>
          <Link to="/login" className="text-emerald-400 text-sm hover:text-emerald-300">
            Sign in now →
          </Link>
        </div>
      </AuthCard>
    );
  }

  // ── Reset form ─────────────────────────────────────────────────────────────
  return (
    <AuthCard
      title="Set new password"
      subtitle="Choose a strong password for your account."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <PasswordField
          id="new-password"
          label="New password"
          value={password}
          onChange={setPassword}
          placeholder="Min. 8 characters"
        />

        <div>
          <PasswordField
            id="confirm-password"
            label="Confirm new password"
            value={confirm}
            onChange={setConfirm}
            placeholder="Re-enter new password"
          />
          {confirm && !passwordsMatch && (
            <p className="text-xs text-red-400 mt-1">Passwords do not match</p>
          )}
          {confirm && passwordsMatch && password.length >= 8 && (
            <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
              <CheckCircle size={12} /> Passwords match
            </p>
          )}
        </div>

        {error && (
          <p className="text-red-400 text-sm bg-red-950/30 border border-red-800 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="btn-primary w-full disabled:opacity-50"
        >
          {loading ? "Updating…" : "Update password"}
        </button>
      </form>
    </AuthCard>
  );
}
