import React, { useState, useEffect, useContext, useCallback } from 'react';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Bike, Activity, Store, Package, Clock, RefreshCw, Loader2, ArrowRight,
} from 'lucide-react';

/**
 * OverviewSection — sección "Resumen" del Panel de Control de Nubo Express.
 * Muestra las métricas clave (KPIs) y un vistazo a los pedidos recientes.
 *
 * Props:
 *  - onNavigate: (id) => void  -> para saltar a otras secciones (p.ej. 'orders').
 */

const STATUS_STYLES = {
  pending: 'bg-amber-100 text-amber-700',
  accepted: 'bg-blue-100 text-blue-700',
  preparing: 'bg-indigo-100 text-indigo-700',
  ready: 'bg-cyan-100 text-cyan-700',
  in_transit: 'bg-emerald-100 text-emerald-700',
  delivered: 'bg-green-100 text-green-700',
  cancelled: 'bg-rose-100 text-rose-700',
};
const STATUS_LABELS = {
  pending: 'Pendiente', accepted: 'Aceptado', preparing: 'Preparando', ready: 'Listo',
  in_transit: 'En camino', delivered: 'Entregado', cancelled: 'Cancelado',
};

const KpiCard = ({ icon: Icon, label, value, accent, testid, loading }) => (
  <Card data-testid={testid} className="border-0 shadow-sm transition-shadow duration-200 hover:shadow-md">
    <CardContent className="flex items-center gap-4 p-5">
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${accent}`}>
        <Icon className="h-6 w-6" />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-slate-500">{label}</p>
        {loading ? (
          <div className="mt-1 h-7 w-12 animate-pulse rounded bg-slate-200" />
        ) : (
          <p className="text-2xl font-bold text-slate-900">{value}</p>
        )}
      </div>
    </CardContent>
  </Card>
);

export const OverviewSection = ({ onNavigate = () => {} }) => {
  const { API, token } = useContext(AuthContext);
  const [stats, setStats] = useState({ total_drivers: 0, active_drivers: 0, total_businesses: 0, total_orders: 0 });
  const [pendingCount, setPendingCount] = useState(0);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);

  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, p, o] = await Promise.all([
        axios.get(`${API}/admin/stats`, auth),
        axios.get(`${API}/admin/pending-orders`, auth),
        axios.get(`${API}/admin/orders`, { params: { limit: 6 }, ...auth }),
      ]);
      setStats(s.data);
      setPendingCount(p.data.count || 0);
      setRecent(o.data.orders || []);
    } catch (e) {
      /* el contenedor superior maneja la sesión; aquí solo evitamos romper la UI */
    } finally {
      setLoading(false);
    }
  }, [API, token]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const fmtMoney = (n) => `€${Number(n || 0).toFixed(2)}`;
  const fmtDate = (d) => d
    ? new Date(d).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div className="space-y-6" data-testid="overview-section">
      {/* Cabecera de la sección */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Vista general de la operación en tiempo real.</p>
        <Button
          data-testid="overview-refresh-btn"
          variant="outline"
          size="sm"
          onClick={fetchAll}
          disabled={loading}
          className="gap-2"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Actualizar
        </Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard testid="overview-kpi-drivers" icon={Bike} label="Abejas totales"
          value={stats.total_drivers} accent="bg-emerald-100 text-emerald-600" loading={loading} />
        <KpiCard testid="overview-kpi-active" icon={Activity} label="Abejas disponibles"
          value={stats.active_drivers} accent="bg-teal-100 text-teal-600" loading={loading} />
        <KpiCard testid="overview-kpi-businesses" icon={Store} label="Negocios"
          value={stats.total_businesses} accent="bg-indigo-100 text-indigo-600" loading={loading} />
        <KpiCard testid="overview-kpi-orders" icon={Package} label="Pedidos totales"
          value={stats.total_orders} accent="bg-amber-100 text-amber-600" loading={loading} />
      </div>

      {/* Banda de pedidos en cola */}
      <Card
        data-testid="overview-pending-banner"
        className="cursor-pointer border-0 bg-gradient-to-r from-slate-900 to-emerald-900 text-white shadow-md transition-transform duration-200 hover:-translate-y-0.5"
        onClick={() => onNavigate('orders')}
      >
        <CardContent className="flex items-center justify-between gap-4 p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10">
              <Clock className="h-6 w-6 text-emerald-300" />
            </div>
            <div>
              <p className="text-sm text-emerald-200/80">Pedidos en cola (sin Abeja asignada)</p>
              <p className="text-2xl font-bold" data-testid="overview-pending-count">{loading ? '—' : pendingCount}</p>
            </div>
          </div>
          <span className="flex items-center gap-1 text-sm font-medium text-emerald-300">
            Gestionar <ArrowRight className="h-4 w-4" />
          </span>
        </CardContent>
      </Card>

      {/* Pedidos recientes */}
      <Card className="border-0 shadow-sm" data-testid="overview-recent-orders">
        <CardContent className="p-0">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
              <Package className="h-5 w-5 text-slate-400" /> Pedidos recientes
            </h2>
            <button
              data-testid="overview-view-all-orders"
              onClick={() => onNavigate('orders')}
              className="flex items-center gap-1 text-sm font-medium text-emerald-600 transition-colors hover:text-emerald-700"
            >
              Ver todos <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th className="px-6 py-3 font-medium">Pedido</th>
                  <th className="px-6 py-3 font-medium">Negocio</th>
                  <th className="px-6 py-3 font-medium">Ciudad</th>
                  <th className="px-6 py-3 font-medium">Estado</th>
                  <th className="px-6 py-3 text-right font-medium">Importe</th>
                  <th className="px-6 py-3 font-medium">Fecha</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  [...Array(4)].map((_, i) => (
                    <tr key={i}>
                      <td colSpan="6" className="px-6 py-4">
                        <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                      </td>
                    </tr>
                  ))
                ) : recent.length === 0 ? (
                  <tr><td colSpan="6" className="px-6 py-10 text-center text-slate-500">No hay pedidos todavía.</td></tr>
                ) : (
                  recent.map((o) => (
                    <tr key={o.id} data-testid={`overview-order-${o.id}`} className="transition-colors hover:bg-slate-50">
                      <td className="px-6 py-3 font-mono text-xs text-slate-600">#{o.id.slice(0, 8)}</td>
                      <td className="px-6 py-3 text-slate-900">{o.business_name}</td>
                      <td className="px-6 py-3 text-slate-600">{o.city_name || '—'}</td>
                      <td className="px-6 py-3">
                        <Badge className={STATUS_STYLES[o.status] || STATUS_STYLES.pending}>
                          {STATUS_LABELS[o.status] || o.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-3 text-right font-semibold text-slate-900">{fmtMoney(o.total_amount)}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-xs text-slate-400">{fmtDate(o.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default OverviewSection;
