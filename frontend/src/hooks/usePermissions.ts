import { useAuth } from "@/contexts/AuthContext";
import type { Role } from "@/types/user";

export function usePermissions() {
  const { user } = useAuth();
  const role: Role = user?.role ?? "operator";

  return {
    role,
    isSuperAdmin: role === "super_admin",
    isAdmin: role === "admin" || role === "super_admin",
    isOperator: role === "operator",
    /** Can create/edit/pause sensors */
    canManageSensors: role === "admin" || role === "super_admin",
    /** Can create/edit locations */
    canManageLocations: role === "admin" || role === "super_admin",
    /** Can manage users and assign permissions */
    canManageUsers: role === "super_admin",
    /** Can delete sensors/locations */
    canDelete: role === "super_admin",
  };
}
