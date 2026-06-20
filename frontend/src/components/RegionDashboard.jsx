import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Building2, Package, Truck, BikeIcon, Euro, Clock, CheckCircle2 } from 'lucide-react';

const Stat = ({ icon: Icon, label, value, accent, testid }) => (
  <Card className="border-0 shadow-sm" data-testid={testid}>
    <CardContent className="p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${accent}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-gray-900 leading-none">{value}</p>
        <p className="text-xs text-gray-500 mt-1">{label}</p>
      </div>
    </CardContent>
  </Card>
);

export const RegionDashboard = ({ API, token }) => {
  const [kpi, setKpi] = useState(null);

  const fetchKpi = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/admin/my-region/kpis`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.data.is_founder) setKpi(r.data);
    } catch (e) { /* noop */ }
  }, [API, token]);

  useEffect(() => {
    fetchKpi();
    const id = setInterval(fetchKpi, 15000);
    return () => clearInterval(id);
  }, [fetchKpi]);

  if (!kpi) return null;

  return (
    <div className="mb-6" data-testid="region-dashboard">
      <div className="flex items-center gap-2 mb-3">
        <Building2 className="w-5 h-5 text-emerald-600" />
        <h2 className="text-lg font-semibold text-gray-900">Mi Delegación</h2>
        <Badge className="bg-emerald-100 text-emerald-700" data-testid="region-dashboard-name">{kpi.region?.name || 'Sin región'}</Badge>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat testid="rkpi-orders-today" icon={Package} label="Pedidos hoy" value={kpi.orders_today} accent="bg-blue-100 text-blue-600" />
        <Stat testid="rkpi-in-transit" icon={Truck} label="En reparto ahora" value={kpi.in_transit} accent="bg-amber-100 text-amber-600" />
        <Stat testid="rkpi-active-riders" icon={BikeIcon} label={`Riders activos (de ${kpi.total_riders})`} value={kpi.active_riders} accent="bg-emerald-100 text-emerald-600" />
        <Stat testid="rkpi-delivered-today" icon={CheckCircle2} label="Entregados hoy" value={kpi.delivered_today} accent="bg-teal-100 text-teal-600" />
        <Stat testid="rkpi-revenue-today" icon={Euro} label="Ingresos hoy (zona)" value={`${kpi.revenue_today_eur} €`} accent="bg-indigo-100 text-indigo-600" />
        <Stat testid="rkpi-revenue-month" icon={Clock} label="Ingresos mes (zona)" value={`${kpi.revenue_month_eur} €`} accent="bg-purple-100 text-purple-600" />
      </div>
    </div>
  );
};

export default RegionDashboard;
