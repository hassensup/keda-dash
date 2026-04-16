import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LayoutDashboard, CalendarDays, LogOut, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Scaled Objects" },
  { to: "/cron-calendar", icon: CalendarDays, label: "Cron Calendar" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-60 bg-white border-r border-slate-200 flex flex-col z-40">
      <div className="p-5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-md bg-slate-900 flex items-center justify-center">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-900 tracking-tight leading-none">KEDA</h1>
            <p className="text-[10px] font-medium text-slate-500 uppercase tracking-[0.1em]">Dashboard</p>
          </div>
        </div>
      </div>
      <Separator />
      <nav className="flex-1 p-3 space-y-0.5" data-testid="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            data-testid={`nav-${item.label.toLowerCase().replace(/\s/g, "-")}`}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-all duration-150 ${
                isActive
                  ? "bg-slate-100 text-slate-900 font-medium"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`
            }
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <Separator />
      <div className="p-4 space-y-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-slate-900 truncate">{user?.name || "User"}</p>
          <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
        </div>
        <Button
          variant="outline"
          onClick={handleLogout}
          data-testid="logout-btn"
          className="w-full h-8 text-xs text-slate-600 hover:text-slate-900 gap-2"
        >
          <LogOut className="w-3.5 h-3.5" />
          Logout
        </Button>
      </div>
    </aside>
  );
}
