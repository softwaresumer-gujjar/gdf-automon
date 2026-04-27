import { useState, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, CheckCircle } from "lucide-react";
import { apiFetch } from "@/api/client";
import { AuthCard } from "@/components/auth/AuthCard";

interface PasswordStrength {
  score: number;   // 0–4
  label: string;
  color: string;
}

function getPasswordStrength(pw: string): PasswordStrength {
  if (!pw) return { score: 0, label: "", color: "" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const capped = Math.min(score, 4) as 0 | 1 | 2 | 3 | 4;
  const labels = ["Too short", "Weak", "Fair", "Good", "Strong"];
  const colors = ["text-red-400", "text-red-400", "text-yellow-400", "text-blue-400", "text-emerald-400"];
  return { score: capped, label: labels[capped], color: colors[capped] };
}

function PasswordField({
  label,
  value,
  onChange,
  placeholder,
  showStrength = false,
  id,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  showStrength?: boolean;
  id: string;
}) {
  const [show, setShow] = useState(false);
  const strength = showStrength ? getPasswordStrength(value) : null;

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
          autoComplete={showStrength ? "new-password" : "current-password"}
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
      {showStrength && value && strength && (
        <div className="mt-1.5">
          <div className="flex gap-1 mb-1">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-colors ${
                  i <= strength.score
                    ? strength.score <= 1 ? "bg-red-400"
                      : strength.score === 2 ? "bg-yellow-400"
                      : strength.score === 3 ? "bg-blue-400"
                      : "bg-emerald-400"
                    : "bg-slate-700"
                }`}
              />
            ))}
          </div>
          <p className={`text-xs ${strength.color}`}>{strength.label}</p>
        </div>
      )}
    </div>
  );
}

export function Register() {
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const passwordStrength = getPasswordStrength(password);
  const passwordsMatch = password === confirm;
  const canSubmit = fullName.trim() && email && password.length >= 8 && passwordsMatch && !loading;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!passwordsMatch) {
      setError("Passwords do not match");
      return;
    }
    if (passwordStrength.score < 1) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      const data = await apiFetch<{ access_token: string; user: { full_name: string } }>(
        "/api/auth/register",
        { method: "POST", body: JSON.stringify({ full_name: fullName, email, password }) }
      );
      localStorage.setItem("gdf_token", data.access_token);
      setSuccess(true);
      // Brief success flash before navigating
      setTimeout(() => navigate("/", { replace: true }), 1200);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-c-bg">
        <div className="text-center">
          <CheckCircle size={48} className="text-emerald-400 mx-auto mb-3" />
          <p className="text-c-text font-semibold">Account created!</p>
          <p className="text-c-text-2 text-sm mt-1">Taking you to the dashboard…</p>
        </div>
      </div>
    );
  }

  return (
    <AuthCard title="Create account" subtitle="Join your farm monitoring team">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="full-name" className="block text-sm font-medium text-c-text-2 mb-1">
            Full name
          </label>
          <input
            id="full-name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            autoComplete="name"
            placeholder="Jane Farmer"
            className="input-field w-full"
          />
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-c-text-2 mb-1">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="jane@farm.com"
            className="input-field w-full"
          />
        </div>

        <PasswordField
          id="password"
          label="Password"
          value={password}
          onChange={setPassword}
          placeholder="Min. 8 characters"
          showStrength
        />

        <div>
          <label htmlFor="confirm" className="block text-sm font-medium text-c-text-2 mb-1">
            Confirm password
          </label>
          <div className="relative">
            <input
              id="confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              autoComplete="new-password"
              placeholder="Re-enter password"
              className={`input-field w-full ${confirm && !passwordsMatch ? "border-red-500 focus:ring-red-500" : ""}`}
            />
          </div>
          {confirm && !passwordsMatch && (
            <p className="text-xs text-red-400 mt-1">Passwords do not match</p>
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
          {loading ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="text-center text-sm text-c-text-2 mt-5">
        Already have an account?{" "}
        <Link to="/login" className="text-emerald-400 hover:text-emerald-300 font-medium">
          Sign in
        </Link>
      </p>
    </AuthCard>
  );
}
