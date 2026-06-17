import React from 'react';
import SidebarAdmin from '@/components/SidebarAdmin';

/**
 * AdminLayout — estructura base del Panel de Control de Nubo Express.
 * Une el SidebarAdmin (navegación) con una barra superior sticky y el
 * contenedor principal de contenido, de forma totalmente responsiva.
 *
 * Props:
 *  - active:     string  -> sección activa (se pasa al sidebar).
 *  - onNavigate: (id) => void  -> cambia de sección.
 *  - user:       { name, email }  -> datos del administrador.
 *  - onLogout:   () => void  -> cierra sesión.
 *  - title:      string  -> título de la barra superior (opcional; si no, se deriva de `active`).
 *  - subtitle:   string  -> subtítulo opcional bajo el título.
 *  - actions:    ReactNode  -> contenido alineado a la derecha de la barra (botones, filtros…).
 *  - items:      array  -> ítems de navegación personalizados (opcional).
 *  - children:   contenido de la sección.
 */

const SECTION_TITLES = {
  overview: 'Resumen',
  map: 'Mapa en vivo',
  orders: 'Pedidos',
  finances: 'Finanzas',
  cities: 'Zonas operativas',
  history: 'Historial',
};

export const AdminLayout = ({
  active = 'overview',
  onNavigate = () => {},
  user = {},
  onLogout = () => {},
  title,
  subtitle,
  actions = null,
  items,
  badges = {},
  children,
}) => {
  const headingTitle = title || SECTION_TITLES[active] || 'Panel de control';

  return (
    <div className="flex min-h-screen bg-slate-50" data-testid="admin-layout">
      <SidebarAdmin
        active={active}
        onNavigate={onNavigate}
        user={user}
        onLogout={onLogout}
        items={items}
        badges={badges}
      />

      {/* Columna principal */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Barra superior sticky */}
        <header
          data-testid="admin-layout-header"
          className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur-md"
        >
          <div className="flex min-h-16 flex-wrap items-center justify-between gap-3 px-4 py-3 pl-16 sm:px-6 lg:pl-6">
            <div className="min-w-0">
              <h1
                data-testid="admin-layout-title"
                className="truncate text-xl font-bold tracking-tight text-slate-900"
              >
                {headingTitle}
              </h1>
              {subtitle && (
                <p className="truncate text-sm text-slate-500">{subtitle}</p>
              )}
            </div>
            {actions && (
              <div className="flex flex-shrink-0 items-center gap-2" data-testid="admin-layout-actions">
                {actions}
              </div>
            )}
          </div>
        </header>

        {/* Contenido de la sección */}
        <main
          data-testid="admin-layout-main"
          className="flex-1 animate-[fadeIn_0.3s_ease-out] p-4 sm:p-6 lg:p-8"
        >
          <div className="mx-auto w-full max-w-7xl">{children}</div>
        </main>
      </div>

      {/* Animación de entrada del contenido (CSS-only) */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default AdminLayout;
