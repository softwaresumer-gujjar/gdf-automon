import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import type { Role } from "@/types/user";

interface Props {
  children: React.ReactNode;
  /** If provided, also gate on minimum role level */
  minRole?: Role;
}

const ROLE_LEVEL: Record<Role, number> = {
  operator: 0,
  admin: 1,
  super_admin: 2,
};

export function ProtectedRoute({ children, minRole }: Props) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-c-bg">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  if (minRole && ROLE_LEVEL[user.role] < ROLE_LEVEL[minRole]) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
