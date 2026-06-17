/**
 * components/SidebarAdmin.jsx — Nubo Express
 *
 * Menú de navegación lateral del panel de administración.
 * Características:
 *   - Acceso por módulo según rol (super_admin / accounting / operations)
 *   - Colapsable en desktop (modo icono) y drawer en mobile
 *   - Badge de alertas en tiempo real
 *   - Indicador de estado del usuario (online/away)
 *   - Highlight del item activo con suave borde izquierdo ámbar
 *   - Totalmente accesible (aria, keyboard nav, focus visible)
 *
 * Props:
 *   currentPath   {string}  — Ruta activa, ej. "/dashboard"
 *   userRole      {string}  — 'super_admin' | 'accounting' | 'operations'
 *   userName      {string}  — Nombre completo del usuario
 *   userEmail     {string}  — Email del usuario
 *   alertCount    {number}  — Nº de alertas activas (badge rojo)
 *   onNavigate    {Function} — Callback(path) al pulsar un ítem
 *   onLogout      {Function} — Callback al cerrar sesión
 */

import { useState, useCallback, useEffect, useRef } from "react";

// ─────────────────────────────────────────────────────────────────
//  ICONOS SVG INLINE (sin dependencias externas)
// ─────────────────────────────────────────────────────────────────

const Icon = {
  Logo: () => (
    <svg viewBox="0 0 32 32" fill="none" className="w-7 h-7" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#F59E0B" />
      <path d="M7 22 L16 10 L25 22" stroke="#0F172A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="16" cy="22" r="2.5" fill="#0F172A" />
    </svg>
  ),
  Dashboard: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <rect x="2" y="2" width="7" height="7" rx="1.5" />
      <rect x="11" y="2" width="7" height="7" rx="1.5" />
      <rect x="2" y="11" width="7" height="7" rx="1.5" />
      <rect x="11" y="11" width="7" height="7" rx="1.5" />
    </svg>
  ),
  Map: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <polygon points="1,4 7,1 13,4 19,1 19,16 13,19 7,16 1,19" />
      <line x1="7" y1="1" x2="7" y2="16" />
      <line x1="13" y1="4" x2="13" y2="19" />
    </svg>
  ),
  Users: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <circle cx="8" cy="6" r="3" />
      <path d="M2 18c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <path d="M14 3.3a3 3 0 010 5.4M18 18c0-2.5-1.5-4.7-3.7-5.7" />
    </svg>
  ),
  Courier: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <circle cx="5.5" cy="15.5" r="1.8" />
      <circle cx="14.5" cy="15.5" r="1.8" />
      <path d="M1 6h8l2.5 6H3.5" />
      <path d="M12.7 8H17l2 4.5H14" />
    </svg>
  ),
  Accounting: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <rect x="2" y="3" width="16" height="14" rx="2" />
      <path d="M6 3v14M10 8h4M10 12h4M6 8h.01M6 12h.01" />
    </svg>
  ),
  Rates: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <path d="M3 10h14M3 5h14M3 15h8" />
      <circle cx="16" cy="15" r="2.5" />
      <line x1="16" y1="12.5" x2="16" y2="10" />
    </svg>
  ),
  Payroll: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <rect x="2" y="4" width="16" height="13" rx="2" />
      <path d="M2 8h16" />
      <path d="M6 12h3M6 15h2M13 11.5a1.5 1.5 0 110 3 1.5 1.5 0 010-3z" />
    </svg>
  ),
  Audit: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <path d="M9 4H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V9" />
      <path d="M15 2l3 3-7 7H8v-3L15 2z" />
    </svg>
  ),
  Chevron: ({ dir = "right" }) => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      className={`w-3.5 h-3.5 transition-transform duration-200 ${dir === "left" ? "rotate-180" : ""}`} aria-hidden="true">
      <polyline points="6,3 11,8 6,13" />
    </svg>
  ),
  Logout: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]" aria-hidden="true">
      <path d="M13 3h4a1 1 0 011 1v12a1 1 0 01-1 1h-4M8 14l4-4-4-4M12 10H3" />
    </svg>
  ),
  Menu: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="w-5 h-5" aria-hidden="true">
      <line x1="3" y1="6" x2="17" y2="6" />
      <line x1="3" y1="10" x2="17" y2="10" />
      <line x1="3" y1="14" x2="17" y2="14" />
    </svg>
  ),
  Close: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="w-5 h-5" aria-hidden="true">
      <line x1="5" y1="5" x2="15" y2="15" />
      <line x1="15" y1="5" x2="5" y2="15" />
    </svg>
  ),
};

// ─────────────────────────────────────────────────────────────────
//  DEFINICIÓN DE NAVEGACIÓN POR ROL
// ─────────────────────────────────────────────────────────────────

/**
 * Cada grupo agrupa ítems por área funcional.
 * `roles` define qué roles pueden ver ese ítem.
 * `badge` activa el indicador de alertas en ese ítem.
 */
const NAV_GROUPS = [
  {
    label: "General",
    items: [
      {
        path: "/dashboard",
        label: "Dashboard",
        icon: Icon.Dashboard,
        roles: ["super_admin", "accounting", "operations"],
        badge: true,   // muestra alertCount aquí
      },
      {
        path: "/map",
        label: "Mapa en vivo",
        icon: Icon.Map,
        roles: ["super_admin", "operations"],
        pulse: true,   // punto verde animado = datos en tiempo real
      },
    ],
  },
  {
    label: "Operaciones",
    items: [
      {
        path: "/users",
        label: "Usuarios",
        icon: Icon.Users,
        roles: ["super_admin"],
      },
      {
        path: "/couriers",
        label: "Couriers",
        icon: Icon.Courier,
        roles: ["super_admin", "operations"],
      },
      {
        path: "/rates",
        label: "Tarifas",
        icon: Icon.Rates,
        roles: ["super_admin"],
      },
    ],
  },
  {
    label: "Finanzas",
    items: [
      {
        path: "/accounting",
        label: "Contabilidad",
        icon: Icon.Accounting,
        roles: ["super_admin", "accounting"],
      },
      {
        path: "/payroll",
        label: "Nóminas",
        icon: Icon.Payroll,
        roles: ["super_admin", "accounting"],
      },
    ],
  },
  {
    label: "Sistema",
    items: [
      {
        path: "/audit",
        label: "Auditoría",
        icon: Icon.Audit,
        roles: ["super_admin"],
      },
    ],
  },
];

// ─────────────────────────────────────────────────────────────────
//  UTILIDADES
// ─────────────────────────────────────────────────────────────────

/** Devuelve las iniciales del nombre para el avatar */
function getInitials(name = "") {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

/** Filtra ítems según el rol del usuario */
function filterByRole(groups, role) {
  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => item.roles.includes(role)),
    }))
    .filter((group) => group.items.length > 0);
}

// ─────────────────────────────────────────────────────────────────
//  SUBCOMPONENTE: NavItem
// ─────────────────────────────────────────────────────────────────

function NavItem({ item, isActive, collapsed, alertCount, onClick }) {
  const IconComp = item.icon;
  const showBadge = item.badge && alertCount > 0;
  const showPulse = item.pulse;

  return (
    <li>
      <button
        onClick={() => onClick(item.path)}
        aria-current={isActive ? "page" : undefined}
        title={collapsed ? item.label : undefined}
        className={[
          "group relative w-full flex items-center gap-3 rounded-lg px-3 py-2.5",
          "text-sm font-medium transition-all duration-150 outline-none",
          "focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900",
          isActive
            ? "bg-slate-800 text-white"
            : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100",
        ].join(" ")}
      >
        {/* Borde izquierdo ámbar — elemento signature del diseño */}
        {isActive && (
          <span
            className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-amber-400 rounded-r-full"
            aria-hidden="true"
          />
        )}

        {/* Icono con posición relativa para el badge */}
        <span className="relative flex-shrink-0 flex items-center justify-center w-5 h-5">
          <IconComp />

          {/* Badge de alertas */}
          {showBadge && (
            <span className="absolute -top-1.5 -right-1.5 min-w-[14px] h-[14px] px-[3px] rounded-full bg-red-500 text-[9px] font-bold text-white flex items-center justify-center leading-none">
              {alertCount > 9 ? "9+" : alertCount}
            </span>
          )}

          {/* Pulso tiempo real */}
          {showPulse && !isActive && (
            <span className="absolute -top-1 -right-1 w-2 h-2">
              <span className="absolute inline-flex w-full h-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
              <span className="relative inline-flex w-2 h-2 rounded-full bg-emerald-500" />
            </span>
          )}
        </span>

        {/* Label — se oculta cuando el sidebar está colapsado */}
        {!collapsed && (
          <span className="flex-1 text-left truncate leading-tight">
            {item.label}
          </span>
        )}

        {/* Tooltip en modo colapsado */}
        {collapsed && (
          <span className="pointer-events-none absolute left-full ml-3 px-2 py-1 rounded-md bg-slate-700 text-white text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-50 shadow-lg">
            {item.label}
            {showBadge && ` (${alertCount})`}
          </span>
        )}
      </button>
    </li>
  );
}

// ─────────────────────────────────────────────────────────────────
//  SUBCOMPONENTE: UserCard
// ─────────────────────────────────────────────────────────────────

function UserCard({ userName, userEmail, userRole, collapsed, onLogout }) {
  const roleLabels = {
    super_admin: "Super Admin",
    accounting:  "Contabilidad",
    operations:  "Operaciones",
  };
  const roleColors = {
    super_admin: "text-amber-400",
    accounting:  "text-sky-400",
    operations:  "text-emerald-400",
  };

  return (
    <div className={[
      "flex items-center gap-3 px-3 py-3 rounded-xl",
      "bg-slate-800/50 border border-slate-700/50",
      collapsed ? "justify-center" : "",
    ].join(" ")}>
      {/* Avatar con iniciales */}
      <div className="relative flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-slate-900 text-xs font-bold tracking-wide select-none">
          {getInitials(userName)}
        </div>
        {/* Indicador online */}
        <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-slate-900" aria-label="En línea" />
      </div>

      {!collapsed && (
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-100 truncate leading-tight">
            {userName}
          </p>
          <p className={`text-[11px] font-medium mt-0.5 ${roleColors[userRole] ?? "text-slate-400"}`}>
            {roleLabels[userRole] ?? userRole}
          </p>
        </div>
      )}

      {/* Botón logout */}
      {!collapsed && (
        <button
          onClick={onLogout}
          title="Cerrar sesión"
          className="flex-shrink-0 p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
        >
          <Icon.Logout />
        </button>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  COMPONENTE PRINCIPAL
// ─────────────────────────────────────────────────────────────────

export default function SidebarAdmin({
  currentPath  = "/dashboard",
  userRole     = "super_admin",
  userName     = "Admin",
  userEmail    = "",
  alertCount   = 0,
  onNavigate   = () => {},
  onLogout     = () => {},
}) {
  // Estado de colapso en desktop
  const [collapsed, setCollapsed] = useState(false);

  // Estado de drawer en mobile
  const [mobileOpen, setMobileOpen] = useState(false);

  // Ref para cerrar drawer al hacer click fuera
  const drawerRef = useRef(null);

  // Filtrar navegación según rol
  const navGroups = filterByRole(NAV_GROUPS, userRole);

  // Cerrar drawer al navegar
  const handleNavigate = useCallback((path) => {
    onNavigate(path);
    setMobileOpen(false);
  }, [onNavigate]);

  // Cerrar con Escape
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Bloquear scroll del body cuando el drawer está abierto
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  // ── Contenido compartido del sidebar ──────────────────────────

  const SidebarContent = ({ isMobile = false }) => (
    <div className="flex flex-col h-full">

      {/* ── Encabezado: Logo + nombre + toggle ── */}
      <div className={[
        "flex items-center h-16 px-4 border-b border-slate-700/60 flex-shrink-0",
        collapsed && !isMobile ? "justify-center" : "gap-3",
      ].join(" ")}>
        <button
          onClick={() => handleNavigate("/dashboard")}
          className="flex items-center gap-2.5 min-w-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 rounded-lg"
          aria-label="Nubo Express — Ir al dashboard"
        >
          <Icon.Logo />
          {(!collapsed || isMobile) && (
            <div className="min-w-0">
              <span className="block text-sm font-bold text-white tracking-tight leading-none">
                Nubo Express
              </span>
              <span className="block text-[10px] text-slate-500 tracking-widest uppercase mt-0.5">
                Admin Panel
              </span>
            </div>
          )}
        </button>

        {/* Toggle colapso — solo desktop */}
        {!isMobile && (
          <button
            onClick={() => setCollapsed((v) => !v)}
            className={[
              "ml-auto p-1.5 rounded-lg text-slate-500 hover:text-slate-200",
              "hover:bg-slate-700/60 transition-colors duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400",
            ].join(" ")}
            aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
          >
            <Icon.Chevron dir={collapsed ? "right" : "left"} />
          </button>
        )}
      </div>

      {/* ── Navegación ── */}
      <nav
        className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4 space-y-5 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent"
        aria-label="Menú principal"
      >
        {navGroups.map((group) => (
          <div key={group.label}>
            {/* Etiqueta de grupo — solo visible cuando expandido */}
            {(!collapsed || isMobile) && (
              <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-600 select-none">
                {group.label}
              </p>
            )}

            {/* Separador sutil en modo colapsado */}
            {collapsed && !isMobile && (
              <div className="mx-3 mb-2 h-px bg-slate-700/50" aria-hidden="true" />
            )}

            <ul className="space-y-0.5" role="list">
              {group.items.map((item) => (
                <NavItem
                  key={item.path}
                  item={item}
                  isActive={currentPath === item.path}
                  collapsed={collapsed && !isMobile}
                  alertCount={alertCount}
                  onClick={handleNavigate}
                />
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* ── Footer: tarjeta de usuario ── */}
      <div className="px-3 pb-4 pt-2 border-t border-slate-700/60 flex-shrink-0">
        {collapsed && !isMobile ? (
          /* En modo colapsado: solo avatar + botón logout apilados */
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-slate-900 text-xs font-bold select-none">
              {getInitials(userName)}
            </div>
            <button
              onClick={onLogout}
              title="Cerrar sesión"
              className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
            >
              <Icon.Logout />
            </button>
          </div>
        ) : (
          <UserCard
            userName={userName}
            userEmail={userEmail}
            userRole={userRole}
            collapsed={false}
            onLogout={onLogout}
          />
        )}
      </div>
    </div>
  );

  // ─────────────────────────────────────────────────────────────
  //  RENDER
  // ─────────────────────────────────────────────────────────────

  return (
    <>
      {/* ══ BOTÓN HAMBURGUESA — solo mobile ══════════════════════ */}
      <button
        className={[
          "fixed top-4 left-4 z-50 p-2 rounded-xl",
          "bg-slate-900 border border-slate-700/80 text-slate-300",
          "shadow-lg hover:bg-slate-800 hover:text-white",
          "transition-colors duration-150 lg:hidden",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400",
        ].join(" ")}
        onClick={() => setMobileOpen((v) => !v)}
        aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}
        aria-expanded={mobileOpen}
        aria-controls="sidebar-drawer"
      >
        {mobileOpen ? <Icon.Close /> : <Icon.Menu />}

        {/* Badge de alerta en el botón hamburguesa */}
        {alertCount > 0 && !mobileOpen && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-[9px] font-bold text-white flex items-center justify-center">
            {alertCount > 9 ? "9+" : alertCount}
          </span>
        )}
      </button>

      {/* ══ OVERLAY — mobile drawer ══════════════════════════════ */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          aria-hidden="true"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ══ DRAWER MOBILE ════════════════════════════════════════ */}
      <aside
        id="sidebar-drawer"
        ref={drawerRef}
        role="navigation"
        aria-label="Menú lateral"
        className={[
          "fixed inset-y-0 left-0 z-40 w-64",
          "bg-slate-900 border-r border-slate-700/60 shadow-2xl",
          "transform transition-transform duration-300 ease-in-out",
          "lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <SidebarContent isMobile={true} />
      </aside>

      {/* ══ SIDEBAR DESKTOP ══════════════════════════════════════ */}
      <aside
        role="navigation"
        aria-label="Menú lateral"
        className={[
          "hidden lg:flex flex-col",
          "fixed inset-y-0 left-0 z-30",
          "bg-slate-900 border-r border-slate-700/60",
          "transition-[width] duration-300 ease-in-out",
          collapsed ? "w-[68px]" : "w-60",
        ].join(" ")}
      >
        <SidebarContent isMobile={false} />
      </aside>

      {/* ══ SPACER — empuja el contenido principal a la derecha ══ */}
      {/* Añade esto a tu layout: className={`lg:pl-${collapsed ? 17 : 60}`} */}
    </>
  );
}

// ─────────────────────────────────────────────────────────────────
//  EXPORTACIONES AUXILIARES
// ─────────────────────────────────────────────────────────────────

/**
 * Hook para sincronizar el padding del layout con el estado del sidebar.
 * Úsalo en tu componente Layout raíz.
 *
 * @example
 *   const { sidebarClass } = useSidebarLayout()
 *   <main className={`${sidebarClass} p-6`}>...</main>
 */
export function useSidebarLayout() {
  const [collapsed, setCollapsed] = useState(false);
  return {
    collapsed,
    setCollapsed,
    // Clase de padding para el <main> del layout
    sidebarClass: collapsed
      ? "lg:pl-[68px] transition-[padding] duration-300"
      : "lg:pl-60 transition-[padding] duration-300",
  };
}
