import React, { useState } from 'react';
import {
  LayoutDashboard, Map, Package, Wallet, MapPin, History,
  LogOut, ChevronLeft, Menu, X, Hexagon,
} from 'lucide-react';

/**
 * SidebarAdmin — navegación lateral del Panel de Control de Nubo Express.
 *
 * Props:
 *  - active:     string  -> id de la sección activa (resaltada).
 *  - onNavigate: (id) => void  -> callback al pulsar un elemento del menú.
 *  - user:       { name, email }  -> datos del administrador (pie del sidebar).
 *  - onLogout:   () => void  -> cierra sesión.
 *  - items:      [{ id, label, icon, badge? }]  -> opcional; usa NAV_ITEMS por defecto.
 *
 * Diseño: tema oscuro slate + acento esmeralda (marca Nubo 🐝). Colapsable en
 * escritorio (icono‑only) y drawer deslizante en móvil. Sin dependencias extra.
 */

const NAV_ITEMS = [
  { id: 'overview', label: 'Resumen', icon: LayoutDashboard },
  { id: 'map', label: 'Mapa en vivo', icon: Map },
  { id: 'orders', label: 'Pedidos', icon: Package },
  { id: 'finances', label: 'Finanzas', icon: Wallet },
  { id: 'cities', label: 'Zonas operativas', icon: MapPin },
  { id: 'history', label: 'Historial', icon: History },
];

export const SidebarAdmin = ({
  active = 'overview',
  onNavigate = () => {},
  user = {},
  onLogout = () => {},
  items = NAV_ITEMS,
  badges = {},
}) => {
  const [collapsed, setCollapsed] = useState(false); // colapsado en escritorio
  const [mobileOpen, setMobileOpen] = useState(false); // drawer en móvil

  const initial = (user?.name || user?.email || 'A').charAt(0).toUpperCase();

  const handleNavigate = (id) => {
    onNavigate(id);
    setMobileOpen(false);
  };

  const NavList = () => (
    <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" data-testid="admin-sidebar-nav">
      {items.map(({ id, label, icon: Icon, badge }) => {
        const isActive = active === id;
        const count = badge ?? badges[id]; // badge explícito o inyectado por `badges`
        const showBadge = typeof count === 'number' && count > 0;
        return (
          <button
            key={id}
            data-testid={`admin-nav-${id}`}
            onClick={() => handleNavigate(id)}
            title={collapsed ? label : undefined}
            className={[
              'group relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium',
              'transition-colors duration-200 outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/60',
              isActive
                ? 'bg-emerald-500/15 text-emerald-300'
                : 'text-slate-400 hover:bg-white/5 hover:text-slate-100',
            ].join(' ')}
            aria-current={isActive ? 'page' : undefined}
          >
            {/* Barra indicadora de activo */}
            <span
              className={[
                'absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-emerald-400',
                'transition-opacity duration-200',
                isActive ? 'opacity-100' : 'opacity-0',
              ].join(' ')}
            />
            <Icon
              className={[
                'h-5 w-5 shrink-0 transition-transform duration-200 group-hover:scale-110',
                isActive ? 'text-emerald-400' : '',
              ].join(' ')}
            />
            {!collapsed && <span className="truncate">{label}</span>}
            {!collapsed && showBadge && (
              <span
                data-testid={`admin-nav-badge-${id}`}
                className="ml-auto min-w-[20px] rounded-full bg-emerald-500/20 px-2 py-0.5 text-center text-[11px] font-semibold text-emerald-300 ring-1 ring-inset ring-emerald-500/30"
              >
                {count}
              </span>
            )}
            {/* Colapsado: punto indicador del badge */}
            {collapsed && showBadge && (
              <span
                data-testid={`admin-nav-dot-${id}`}
                className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-slate-900"
              />
            )}
          </button>
        );
      })}
    </nav>
  );

  const Brand = () => (
    <div className="flex items-center gap-2.5 px-5 h-16 border-b border-white/5 shrink-0">
      <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500 shadow-lg shadow-emerald-500/30">
        <Hexagon className="h-5 w-5 text-white" />
        <span className="absolute -bottom-1 -right-1 text-xs">🐝</span>
      </div>
      {!collapsed && (
        <div className="min-w-0">
          <p className="text-sm font-bold leading-tight text-white">Nubo Admin</p>
          <p className="text-[11px] leading-tight text-emerald-400/80">Panel de control</p>
        </div>
      )}
    </div>
  );

  const Footer = () => (
    <div className="border-t border-white/5 p-3 shrink-0">
      <div
        className={[
          'flex items-center gap-3 rounded-xl px-2 py-2',
          collapsed ? 'justify-center' : '',
        ].join(' ')}
        data-testid="admin-sidebar-user"
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-sm font-bold text-white">
          {initial}
        </div>
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{user?.name || 'Administrador'}</p>
            <p className="truncate text-[11px] text-slate-400">{user?.email || ''}</p>
          </div>
        )}
      </div>
      <button
        data-testid="admin-sidebar-logout"
        onClick={onLogout}
        title={collapsed ? 'Cerrar sesión' : undefined}
        className={[
          'mt-2 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium',
          'text-slate-400 transition-colors duration-200 hover:bg-red-500/10 hover:text-red-400',
          'focus-visible:ring-2 focus-visible:ring-red-400/50 outline-none',
          collapsed ? 'justify-center' : '',
        ].join(' ')}
      >
        <LogOut className="h-5 w-5 shrink-0" />
        {!collapsed && <span>Cerrar sesión</span>}
      </button>
    </div>
  );

  return (
    <>
      {/* Botón hamburguesa (solo móvil) */}
      <button
        data-testid="admin-sidebar-mobile-toggle"
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-40 flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white shadow-lg lg:hidden"
        aria-label="Abrir menú"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Overlay del drawer móvil */}
      {mobileOpen && (
        <div
          data-testid="admin-sidebar-overlay"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
        />
      )}

      {/* Sidebar */}
      <aside
        data-testid="admin-sidebar"
        className={[
          'z-50 flex flex-col bg-slate-900 text-slate-200 shadow-2xl',
          'transition-[width,transform] duration-300 ease-in-out',
          // Escritorio: fijo, ancho colapsable
          'lg:sticky lg:top-0 lg:h-screen',
          collapsed ? 'lg:w-20' : 'lg:w-64',
          // Móvil: drawer deslizante a pantalla completa de alto
          'fixed inset-y-0 left-0 w-64',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        ].join(' ')}
      >
        {/* Cerrar (móvil) */}
        <button
          data-testid="admin-sidebar-mobile-close"
          onClick={() => setMobileOpen(false)}
          className="absolute right-3 top-4 flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/5 hover:text-white lg:hidden"
          aria-label="Cerrar menú"
        >
          <X className="h-5 w-5" />
        </button>

        <Brand />
        <NavList />
        <Footer />

        {/* Colapsar / expandir (solo escritorio) */}
        <button
          data-testid="admin-sidebar-toggle"
          onClick={() => setCollapsed((c) => !c)}
          className="absolute -right-3 top-20 hidden h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-slate-800 text-slate-300 shadow-md transition-colors hover:bg-emerald-600 hover:text-white lg:flex"
          aria-label={collapsed ? 'Expandir menú' : 'Colapsar menú'}
        >
          <ChevronLeft
            className={['h-4 w-4 transition-transform duration-300', collapsed ? 'rotate-180' : ''].join(' ')}
          />
        </button>
      </aside>
    </>
  );
};

export default SidebarAdmin;
