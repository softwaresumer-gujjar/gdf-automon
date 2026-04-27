import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Settings2, Bell, Activity, MapPin, Users,
  LogOut, Target, ClipboardList, MessageSquare, Sun, Moon,
} from "lucide-react";
import { useAlertStore } from "@/store/alertStore";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { usePermissions } from "@/hooks/usePermissions";
import { clsx } from "clsx";

export function Sidebar() {
  const unread = useAlertStore((s) => s.unreadCount);
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { isAdmin, canManageUsers } = usePermissions();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const nav = [
    { to: "/",          icon: LayoutDashboard, label: "Dashboard", show: true },
    { to: "/sensors",   icon: Settings2,       label: "Sensors",   show: true },
    { to: "/tasks",     icon: ClipboardList,   label: "Tasks",     show: true },
    { to: "/alerts",    icon: Bell,            label: "Alerts",    show: true, badge: unread },
    { to: "/chat",      icon: MessageSquare,   label: "Chat",      show: true },
    { to: "/planning",  icon: Target,          label: "Planning",  show: isAdmin },
    { to: "/locations", icon: MapPin,          label: "Locations", show: isAdmin },
    { to: "/users",     icon: Users,           label: "Users",     show: canManageUsers },
    { to: "/settings",  icon: Activity,        label: "Settings",  show: true },
  ].filter((n) => n.show);

  return (
    <aside className="hidden md:flex flex-col w-16 xl:w-60 bg-c-surface border-r border-c-border h-screen sticky top-0 transition-colors">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-c-border">
        <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
          G
        </div>
        <span className="hidden xl:block text-c-text font-semibold text-sm">GDF AutoMon</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-0.5 px-2 overflow-y-auto">
        {nav.map(({ to, icon: Icon, label, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors relative",
                isActive
                  ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                  : "text-c-text-2 hover:text-c-text hover:bg-c-surface-2"
              )
            }
          >
            <Icon size={18} className="shrink-0" />
            <span className="hidden xl:block">{label}</span>
            {badge != null && badge > 0 && (
              <span className="ml-auto hidden xl:flex bg-red-500 text-white text-xs rounded-full w-5 h-5 items-center justify-center font-bold">
                {badge > 9 ? "9+" : badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Theme toggle + User + Logout */}
      <div className="border-t border-c-border px-2 py-3 space-y-1">
        {/* Theme toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-c-text-2 hover:text-c-text hover:bg-c-surface-2 transition-colors"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={18} className="shrink-0" /> : <Moon size={18} className="shrink-0" />}
          <span className="hidden xl:block">{theme === "dark" ? "Light mode" : "Dark mode"}</span>
        </button>

        {/* User info */}
        <div className="hidden xl:flex items-center gap-2 px-3 py-2">
          <div className="w-6 h-6 rounded-full bg-emerald-700 flex items-center justify-center text-xs font-bold text-white shrink-0">
            {user?.full_name?.charAt(0).toUpperCase() ?? "?"}
          </div>
          <div className="min-w-0">
            <p className="text-xs text-c-text font-medium truncate">{user?.full_name}</p>
            <p className="text-xs text-c-text-3 capitalize">{user?.role?.replace("_", " ")}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-c-text-2 hover:text-red-500 hover:bg-c-surface-2 transition-colors"
        >
          <LogOut size={18} className="shrink-0" />
          <span className="hidden xl:block">Sign out</span>
        </button>
      </div>
    </aside>
  );
}
