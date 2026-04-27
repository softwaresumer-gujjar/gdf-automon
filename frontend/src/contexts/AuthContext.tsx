import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import type { CurrentUser } from "@/types/user";
import { apiLogin, apiFetch } from "@/api/client";

interface AuthState {
  user: CurrentUser | null;
  token: string | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Refresh current user profile from server (call after profile update) */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: localStorage.getItem("gdf_token"),
    isLoading: true,
  });

  // Rehydrate user from stored token on mount
  useEffect(() => {
    const token = localStorage.getItem("gdf_token");
    if (!token) {
      setState({ user: null, token: null, isLoading: false });
      return;
    }
    apiFetch<CurrentUser>("/api/auth/me")
      .then((user) => setState({ user, token, isLoading: false }))
      .catch(() => {
        localStorage.removeItem("gdf_token");
        setState({ user: null, token: null, isLoading: false });
      });
  }, []);

  async function login(email: string, password: string) {
    const data = await apiLogin(email, password);
    localStorage.setItem("gdf_token", data.access_token);
    setState({ user: data.user, token: data.access_token, isLoading: false });
  }

  async function logout() {
    // Call backend for audit logging (fire-and-forget)
    apiFetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    localStorage.removeItem("gdf_token");
    setState({ user: null, token: null, isLoading: false });
  }

  async function refreshUser() {
    try {
      const user = await apiFetch<CurrentUser>("/api/auth/me");
      setState((s) => ({ ...s, user }));
    } catch {
      // ignore
    }
  }

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
