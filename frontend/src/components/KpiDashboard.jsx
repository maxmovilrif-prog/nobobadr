import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, Euro, Timer, Trophy, BarChart3, Package } from 'lucide-react';

const eur = (n) => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n || 0);
const DAY_LABEL = (iso) => {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('es-ES', { weekday: 'short' }).replace('.', '');
};
const fmtMins = (m) => {
  if (m == null) return '—';
  if (m < 60) return `${Math.round(m)} min`;
  const h = Math.floor(m / 60); const r = Math.round(m % 60);
  return `${h}h ${r}m`;
};
const MEDAL = ['🥇', '🥈', '🥉'];

const KpiTile = ({ icon: Icon, label, value, sub, color, testid }) => (
  <Card data-testid={testid} className="border-0 shadow-lg overflow-hidden">
    <CardContent className="p-5 flex items-start gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-gray-900 leading-tight">{value}</p>
        <p className="text-sm text-gray-600">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </CardContent>
  </Card>
);

export const KpiDashboard = ({ API, token }) => {
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const [kpi, setKpi] = useState(null);

  const fetchKpis = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/kpis`, auth);
      setKpi(res.data);
    } catch (e) { console.error('Error cargando KPIs', e); }
    // eslint-disable-next-line
  }, [API, token]);

  useEffect(() => { fetchKpis(); const t = setInterval(fetchKpis, 30000); return () => clearInterval(t); }, [fetchKpis]);

  const series = kpi?.orders_per_day || [];
  const maxOrders = Math.max(1, ...series.map((d) => d.orders));

  return (
    <div className="space-y-6" data-testid="kpi-dashboard">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-6 h-6 text-emerald-600" />
        <h2 className="text-xl font-bold text-gray-900">Cuadro de mandos</h2>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiTile testid="kpi-orders-today" icon={Package} color="bg-emerald-500"
          label="Pedidos hoy" value={kpi?.orders_today ?? '—'} sub="Creados hoy" />
        <KpiTile testid="kpi-revenue-month" icon={Euro} color="bg-teal-500"
          label="Ingresos del mes" value={kpi ? eur(kpi.revenue_month_eur) : '—'} sub="Pedidos entregados" />
        <KpiTile testid="kpi-avg-delivery" icon={Timer} color="bg-amber-500"
          label="Tiempo medio entrega" value={fmtMins(kpi?.avg_delivery_mins)} sub="De creación a entrega" />
        <KpiTile testid="kpi-delivered-total" icon={TrendingUp} color="bg-blue-500"
          label="Entregas totales" value={kpi?.delivered_total ?? '—'} sub="Histórico" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Gráfico pedidos/día */}
        <Card className="border-0 shadow-lg lg:col-span-2" data-testid="kpi-orders-chart">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="w-5 h-5 text-emerald-600" /> Pedidos por día (últimos 7 días)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between gap-3 h-48 pt-4">
              {series.map((d) => (
                <div key={d.date} className="flex-1 flex flex-col items-center gap-2" data-testid={`kpi-bar-${d.date}`}>
                  <span className="text-xs font-semibold text-gray-700">{d.orders}</span>
                  <div className="w-full flex flex-col justify-end" style={{ height: '150px' }}>
                    <div className="w-full rounded-t-md bg-emerald-200 relative overflow-hidden transition-all duration-500"
                      style={{ height: `${(d.orders / maxOrders) * 100}%`, minHeight: d.orders > 0 ? '6px' : '0' }}>
                      <div className="absolute bottom-0 left-0 right-0 bg-emerald-600 transition-all duration-500"
                        style={{ height: d.orders > 0 ? `${(d.delivered / Math.max(1, d.orders)) * 100}%` : '0' }} />
                    </div>
                  </div>
                  <span className="text-xs text-gray-500 capitalize">{DAY_LABEL(d.date)}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-4 text-xs text-gray-500">
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-emerald-600 inline-block" /> Entregados</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-emerald-200 inline-block" /> Totales</span>
            </div>
          </CardContent>
        </Card>

        {/* Ranking de Abejas */}
        <Card className="border-0 shadow-lg" data-testid="kpi-top-bees">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Trophy className="w-5 h-5 text-amber-500" /> Abejas más activas (30d)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(!kpi?.top_bees || kpi.top_bees.length === 0) ? (
              <p className="text-sm text-gray-500 text-center py-8">Aún no hay entregas registradas.</p>
            ) : kpi.top_bees.map((b, i) => (
              <div key={b.driver_id} data-testid={`kpi-bee-${i}`} className="flex items-center gap-3 p-2 rounded-lg bg-gray-50">
                <span className="text-lg w-6 text-center">{MEDAL[i] || `${i + 1}.`}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{b.driver_name}</p>
                  <p className="text-xs text-gray-500">{eur(b.revenue_eur)} generados</p>
                </div>
                <Badge className="bg-emerald-100 text-emerald-700">{b.deliveries} entregas</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default KpiDashboard;
