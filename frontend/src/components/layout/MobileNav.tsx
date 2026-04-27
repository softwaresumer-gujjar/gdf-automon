import { NavLink } from "react-router-dom";
import { LayoutDashboard, Settings2, Bell, ClipboardList, MessageSquare } from "lucide-react";
import { useAlertStore } from "@/store/alertStore";
import { clsx } from "clsx";

export function MobileNav() {
  const unread = useAlertStore((s) => s.unreadCount);

  const nav = [
    { to: "/",        icon: LayoutDashboard, label: "Home",    badge: 0 },
    { to: "/tasks",   icon: ClipboardList,   label: "Tasks",   badge: 0 },
    { to: "/chat",    icon: MessageSquare,   label: "Chat",    badge: 0 },
    { to: "/alerts",  icon: Bell,            label: "Alerts",  badge: unread },
    { to: "/sensors", icon: Settings2,       label: "Sensors", badge: 0 },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-c-surface border-t border-c-border flex safe-b transition-colors">
      {nav.map(({ to, icon: Icon, label, badge }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            clsx(
              "flex-1 flex flex-col items-center gap-0.5 py-2 text-xs font-medium transition-colors relative",
              isActive ? "text-emerald-600 dark:text-emerald-400" : "text-c-text-3"
            )
          }
        >
          <div className="relative">
            <Icon size={20} />
            {badge > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[9px] rounded-full w-4 h-4 flex items-center justify-center font-bold">
                {badge > 9 ? "9+" : badge}
              </span>
            )}
          </div>
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
