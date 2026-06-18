import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import {
  Radar, Package, Bike, RotateCcw, Loader2, History, Download, RefreshCw, MapPin, Filter,
} from 'lucide-react';

const VLABEL = { bicycle: 'Bici', motorcycle: 'Moto', car: 'Coche', truck: 'Camión' };
const ACTION_LABEL = { assigned: 'Asignado', returned: 'Devuelto', auto_returned: 'Auto-devuelto' };
const ACTION_CLASS = {
  assigned: 'bg-emerald-100 text-emerald-700',
  returned: 'bg-amber-100 text-amber-700',
  auto_returned: 'bg-gray-100 text-gray-600',
};
const ACTOR_ROLE = {
  admin: { label: 'Fundador', cls: 'bg-purple-100 text-purple-700' },
  manager: { label: 'Gestor', cls: 'bg-blue-100 text-blue-700' },
};

const fmtMoney = (amt, cur) => {
  if (amt == null) return '—';
  try {
    return new Intl.NumberFormat(cur === 'MAD' ? 'ar-MA' : 'es-ES', { style: 'currency', currency: cur || 'EUR' }).format(amt);
  } catch { return `${amt} ${cur || ''}`; }
};

export const OperationsManager = ({ API, token }) => {
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const [ops, setOps] = useState({ pending: [], active: [], pending_count: 0, active_count: 0 });
  const [history, setHistory] = useState({ events: [], drivers: [] });
  const [assigningId, setAssigningId] = useState(null);
  const [returningId, setReturningId] = useState(null);
  const [filterAction, setFilterAction] = useState('');
  const [filterDriver, setFilterDriver] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const fetchOps = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/ops/orders`, auth);
      setOps(res.data);
    } catch (e) { /* noop */ }
    // eslint-disable-next-line
  }, [API, token]);

  const fetchHistory = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filterAction) params.set('action', filterAction);
      if (filterDriver) params.set('driver_id', filterDriver);
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      const res = await axios.get(`${API}/admin/assignment-history?${params.toString()}`, auth);
      setHistory(res.data);
    } catch (e) { /* noop */ }
    // eslint-disable-next-line
  }, [API, token, filterAction, filterDriver, dateFrom, dateTo]);

  useEffect(() => { fetchOps(); const t = setInterval(fetchOps, 12000); return () => clearInterval(t); }, [fetchOps]);
  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const assignNearest = async (orderId) => {
    setAssigningId(orderId);
    try {
      const res = await axios.post(`${API}/orders/${orderId}/assign-nearest`, {}, auth);
      const d = res.data.driver;
      toast.success(`Asignado a ${d.name} (${d.distance_km} km)`);
      fetchOps(); fetchHistory();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No hay Abejas disponibles cerca');
    } finally { setAssigningId(null); }
  };

  const returnToQueue = async (orderId) => {
    setReturningId(orderId);
    try {
      await axios.post(`${API}/orders/${orderId}/return-to-queue`, {}, auth);
      toast.success('Pedido devuelto a la cola');
      fetchOps(); fetchHistory();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No se pudo devolver el pedido');
    } finally { setReturningId(null); }
  };

  const exportCsv = async () => {
    try {
      const params = new URLSearchParams();
      if (filterAction) params.set('action', filterAction);
      if (filterDriver) params.set('driver_id', filterDriver);
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      const res = await axios.get(`${API}/admin/assignment-history/export?${params.toString()}`, { ...auth, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url; a.download = 'historial_asignaciones.csv';
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { toast.error('No se pudo exportar'); }
  };

  return (
    <div className="mt-8 space-y-6" data-testid="operations-manager">
      <div className="flex items-center gap-2">
        <Radar className="w-6 h-6 text-emerald-600" />
        <h2 className="text-xl font-bold text-gray-900">Operaciones y Logística</h2>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Cola de despacho — pendientes */}
        <Card className="border-0 shadow-lg" data-testid="ops-pending-card">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span className="flex items-center gap-2"><Package className="w-5 h-5 text-amber-600" /> Cola de despacho</span>
              <Badge className="bg-amber-100 text-amber-700" data-testid="ops-pending-count">{ops.pending_count} sin asignar</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 max-h-[420px] overflow-y-auto">
            {ops.pending.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">No hay pedidos pendientes de asignar.</p>
            ) : ops.pending.map((o) => (
              <div key={o.id} data-testid={`ops-pending-${o.id}`} className="p-3 rounded-lg border bg-white">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-gray-500 truncate">{o.id.slice(0, 8)}</span>
                  <Badge className="bg-gray-100 text-gray-600">{o.order_type === 'express' ? 'Exprés' : 'Marketplace'}</Badge>
                </div>
                <div className="flex items-start gap-1 mt-2 text-sm text-gray-700">
                  <MapPin className="w-3.5 h-3.5 mt-0.5 text-emerald-600 shrink-0" />
                  <span className="truncate">{o.origin_name || o.city_name || 'Recogida'} → {o.destination_name || '—'}</span>
                </div>
                {o.distance_km != null && (
                  <p className="text-xs text-gray-500 mt-1 ml-5" data-testid={`ops-pending-distance-${o.id}`}>Distancia: {o.distance_km} km</p>
                )}
                <div className="flex items-center justify-between mt-2">
                  <span className="text-sm font-semibold text-emerald-700" data-testid={`ops-pending-price-${o.id}`}>{fmtMoney(o.total_amount, o.currency)}</span>
                  <Button
                    data-testid={`ops-assign-btn-${o.id}`}
                    size="sm" className="bg-emerald-600 hover:bg-emerald-700"
                    disabled={assigningId === o.id}
                    onClick={() => assignNearest(o.id)}>
                    {assigningId === o.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bike className="w-4 h-4 mr-1" />}
                    {assigningId === o.id ? '' : 'Asignar cercana'}
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Pedidos activos */}
        <Card className="border-0 shadow-lg" data-testid="ops-active-card">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span className="flex items-center gap-2"><Bike className="w-5 h-5 text-emerald-600" /> En reparto</span>
              <Badge className="bg-emerald-100 text-emerald-700" data-testid="ops-active-count">{ops.active_count} activos</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 max-h-[420px] overflow-y-auto">
            {ops.active.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">No hay pedidos en reparto.</p>
            ) : ops.active.map((o) => (
              <div key={o.id} data-testid={`ops-active-${o.id}`} className="p-3 rounded-lg border bg-emerald-50/40">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-gray-500 truncate">{o.id.slice(0, 8)}</span>
                  <Badge className="bg-emerald-100 text-emerald-700">{o.status}</Badge>
                </div>
                <p className="text-sm text-gray-800 mt-2 flex items-center gap-1">
                  🐝 <span className="font-medium">{o.driver_name}</span>
                  <span className="text-xs text-gray-500">· {VLABEL[o.driver_vehicle_type] || o.driver_vehicle_type || ''}</span>
                </p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-sm font-semibold text-emerald-700" data-testid={`ops-active-price-${o.id}`}>{fmtMoney(o.total_amount, o.currency)}</span>
                  {o.distance_km != null && <span className="text-xs text-gray-500">{o.distance_km} km</span>}
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-gray-500 truncate">{o.destination_name || '—'}</span>
                  <Button
                    data-testid={`ops-return-btn-${o.id}`}
                    size="sm" variant="outline"
                    disabled={returningId === o.id}
                    onClick={() => returnToQueue(o.id)}>
                    {returningId === o.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4 mr-1" />}
                    {returningId === o.id ? '' : 'Devolver'}
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Historial de asignaciones */}
      <Card className="border-0 shadow-lg" data-testid="ops-history-card">
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base flex-wrap gap-2">
            <span className="flex items-center gap-2"><History className="w-5 h-5 text-emerald-600" /> Historial de asignaciones</span>
            <div className="flex items-center gap-2">
              <Button data-testid="ops-history-refresh" size="sm" variant="outline" onClick={fetchHistory}>
                <RefreshCw className="w-4 h-4 mr-1" /> Actualizar
              </Button>
              <Button data-testid="ops-history-export" size="sm" className="bg-teal-600 hover:bg-teal-700" onClick={exportCsv}>
                <Download className="w-4 h-4 mr-1" /> CSV
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3 mb-4">
            <div>
              <label className="text-xs text-gray-500 flex items-center gap-1"><Filter className="w-3 h-3" /> Acción</label>
              <select data-testid="ops-filter-action" value={filterAction} onChange={(e) => setFilterAction(e.target.value)}
                className="mt-1 text-sm border rounded-md px-2 py-1.5 bg-white">
                <option value="">Todas</option>
                <option value="assigned">Asignado</option>
                <option value="returned">Devuelto</option>
                <option value="auto_returned">Auto-devuelto</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Abeja</label>
              <select data-testid="ops-filter-driver" value={filterDriver} onChange={(e) => setFilterDriver(e.target.value)}
                className="mt-1 text-sm border rounded-md px-2 py-1.5 bg-white max-w-[160px]">
                <option value="">Todas</option>
                {history.drivers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Desde</label>
              <Input data-testid="ops-filter-from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="mt-1 h-9 text-sm" />
            </div>
            <div>
              <label className="text-xs text-gray-500">Hasta</label>
              <Input data-testid="ops-filter-to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="mt-1 h-9 text-sm" />
            </div>
          </div>

          {history.events.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">Sin eventos de asignación todavía.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="ops-history-table">
                <thead>
                  <tr className="text-left text-xs text-gray-400 border-b">
                    <th className="py-2 pr-3">Fecha</th><th className="py-2 pr-3">Acción</th>
                    <th className="py-2 pr-3">Abeja</th><th className="py-2 pr-3">Pedido</th>
                    <th className="py-2 pr-3">Dist.</th><th className="py-2 pr-3">Realizado por</th>
                  </tr>
                </thead>
                <tbody>
                  {history.events.map((e) => (
                    <tr key={e.id} className="border-b last:border-0">
                      <td className="py-2 pr-3 text-xs text-gray-500 whitespace-nowrap">{new Date(e.created_at).toLocaleString('es-ES')}</td>
                      <td className="py-2 pr-3"><Badge className={ACTION_CLASS[e.action] || 'bg-gray-100'}>{ACTION_LABEL[e.action] || e.action}</Badge></td>
                      <td className="py-2 pr-3 truncate max-w-[120px]">{e.driver_name || '—'}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{(e.order_id || '').slice(0, 8)}</td>
                      <td className="py-2 pr-3">{e.distance_km != null ? `${e.distance_km} km` : '—'}</td>
                      <td className="py-2 pr-3" data-testid={`ops-history-actor-${e.id}`}>
                        {e.actor_name ? (
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs text-gray-700 truncate max-w-[110px]">{e.actor_name}</span>
                            {ACTOR_ROLE[e.actor_role] && (
                              <Badge className={`${ACTOR_ROLE[e.actor_role].cls} text-[10px] px-1.5 py-0`}>{ACTOR_ROLE[e.actor_role].label}</Badge>
                            )}
                          </div>
                        ) : (
                          <Badge className="bg-gray-100 text-gray-500 text-[10px] px-1.5 py-0">{e.reason === 'auto_dispatch' ? '🤖 Auto-despacho' : '—'}</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default OperationsManager;
