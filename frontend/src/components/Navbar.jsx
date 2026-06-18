import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Wallet, LayoutDashboard, Calculator, LogOut } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const link = (to, icon, label, testId) => (
    <NavLink
      to={to}
      data-testid={testId}
      className={({ isActive }) =>
        `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isActive ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100"
        }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <Wallet className="h-4 w-4" />
          </div>
          <span className="text-base font-bold tracking-tight text-slate-900">MoboExpress</span>
        </div>
        <nav className="flex items-center gap-1">
          {link("/", <LayoutDashboard className="h-4 w-4" />, "Operaciones", "nav-operaciones")}
          {link("/contabilidad", <Calculator className="h-4 w-4" />, "Contabilidad", "nav-contabilidad")}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {user && (
            <span className="hidden text-sm text-slate-500 sm:inline">
              {user.name} · <span className="font-medium capitalize text-slate-700">{user.role}</span>
            </span>
          )}
          <button
            data-testid="logout-btn"
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            <LogOut className="h-4 w-4" />
            Salir
          </button>
        </div>
      </div>
    </header>
  );
}
