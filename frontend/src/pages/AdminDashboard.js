import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import { Package, RefreshCw, Crosshair, Loader2, MapPin, History, ArrowRightLeft, Download, Filter, Wallet } from 'lucide-react';
import CityManager from '@/components/CityManager';
import AdminLayout from '@/layouts/AdminLayout';
import OverviewSection from '@/pages/admin/OverviewSection';
import ContabilidadSection from '@/pages/admin/ContabilidadSection';

const SPAIN_CENTER = [37.5, -4.8];

// Custom green Bee marker 🐝
const beeIcon = L.divIcon({
  className: 'bee-marker',
  html: `<div style="
      width:38px;height:38px;border-radius:50%;
      background:#10b981;border:3px solid #fff;
      box-shadow:0 2px 8px rgba(0,0,0,.4);
      display:flex;align-items:center;justify-content:center;
      font-size:20px;">🐝</div>`,
  iconSize: [38, 38],
  iconAnchor: [19, 19],
  popupAnchor: [0, -20],
});

// Highlighted Bee marker (chosen driver) — gold pulsing ring 🐝
const beeIconHighlight = L.divIcon({
  className: 'bee-marker-highlight',
  html: `<div class="bee-pulse" style="
      width:46px;height:46px;border-radius:50%;
      background:#f59e0b;border:3px solid #fff;
      box-shadow:0 0 0 4px rgba(245,158,11,.45),0 2px 10px rgba(0,0,0,.5);
      display:flex;align-items:center;justify-content:center;
      font-size:24px;">🐝</div>`,
  iconSize: [46, 46],
  iconAnchor: [23, 23],
  popupAnchor: [0, -24],
});

export default function AdminDashboard() {
  const { user, token, logout, API } = useContext(AuthContext);
  const [drivers, setDrivers] = useState([]);
  const [stats, setStats] = useState({ total_drivers: 0, active_drivers: 0, total_businesses: 0, total_orders: 0 });
  const [pendingOrders, setPendingOrders] = useState([]);
  const [history, setHistory] = useState([]);
  const [historyDrivers, setHistoryDrivers] = useState([]);
  const [historyFilters, setHistoryFilters] = useState({ action: '', driver_id: '', date_from: '', date_to: '' });
  const [exporting, setExporting] = useState(false);
  const [assigningId, setAssigningId] = useState(null);
  // Finanzas — pagos por repartidor
  const [finance, setFinance] = useState({ rows: [], totals: { deliveries: 0, revenue: 0, earnings: 0 } });
  const [financeFilters, setFinanceFilters] = useState({ start_date: '', end_date: '', rate_pct: 10 });
  const [financeLoading, setFinanceLoading] = useState(false);
  const [financeExporting, setFinanceExporting] = useState(false);
  const [markingDriverId, setMarkingDriverId] = useState(null);
  const [payouts, setPayouts] = useState([]);
  // Todos los pedidos
  const [allOrders, setAllOrders] = useState([]);
  const [ordersFilters, setOrdersFilters] = useState({ status: '', city_id: '' });
  const [citiesList, setCitiesList] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [confirmData, setConfirmData] = useState(null); // { order, driver }
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [highlightId, setHighlightId] = useState(null);
  const [section, setSection] = useState('overview'); // sección activa del sidebar

  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const markersLayerRef = useRef(null);
  const filtersRef = useRef({ action: '', driver_id: '', date_from: '', date_to: '' });

  const buildHistoryParams = () => {
    const f = filtersRef.current;
    const p = { limit: 100 };
    if (f.action) p.action = f.action;
    if (f.driver_id) p.driver_id = f.driver_id;
    if (f.date_from) p.date_from = f.date_from;
    if (f.date_to) p.date_to = f.date_to;
    return p;
  };

  const fetchHistory = async () => {
    try {
      const h = await axios.get(`${API}/admin/assignment-history`, {
        params: buildHistoryParams(),
        headers: { Authorization: `Bearer ${token}` },
      });
      setHistory(h.data.events || []);
      setHistoryDrivers(h.data.drivers || []);
    } catch (e) { /* noop */ }
  };

  const applyFilter = (patch) => {
    const next = { ...filtersRef.current, ...patch };
    filtersRef.current = next;
    setHistoryFilters(next);
    fetchHistory();
  };

  const clearFilters = () => {
    const empty = { action: '', driver_id: '', date_from: '', date_to: '' };
    filtersRef.current = empty;
    setHistoryFilters(empty);
    fetchHistory();
  };

  const exportCsv = async () => {
    setExporting(true);
    try {
      const params = { ...buildHistoryParams() };
      delete params.limit;
      const res = await axios.get(`${API}/admin/assignment-history/export`, {
        params,
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `historial_asignaciones_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('CSV exportado');
    } catch (e) {
      toast.error('No se pudo exportar el CSV');
    } finally {
      setExporting(false);
    }
  };

  const buildFinanceParams = () => {
    const f = financeFilters;
    const p = { rate: (Number(f.rate_pct) || 0) / 100 };
    if (f.start_date) p.start_date = f.start_date;
    if (f.end_date) p.end_date = f.end_date;
    return p;
  };

  const fetchFinance = async () => {
    setFinanceLoading(true);
    try {
      const res = await axios.get(`${API}/admin/finances/summary`, {
        params: buildFinanceParams(),
        headers: { Authorization: `Bearer ${token}` },
      });
      setFinance({ rows: res.data.rows || [], totals: res.data.totals || { deliveries: 0, revenue: 0, earnings: 0 } });
    } catch (e) {
      toast.error('No se pudo calcular los pagos');
    } finally {
      setFinanceLoading(false);
    }
  };

  const exportFinanceCsv = async () => {
    setFinanceExporting(true);
    try {
      const res = await axios.get(`${API}/admin/finances/export`, {
        params: buildFinanceParams(),
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `pagos_repartidores_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('CSV de pagos exportado');
    } catch (e) {
      toast.error('No se pudo exportar el CSV');
    } finally {
      setFinanceExporting(false);
    }
  };

  const toggleDriverPayment = async (row) => {
    const markPaid = row.payment_status !== 'paid';
    setMarkingDriverId(row.driver_id);
    try {
      const f = financeFilters;
      const body = {
        driver_id: row.driver_id,
        rate: (Number(f.rate_pct) || 0) / 100,
      };
      if (f.start_date) body.start_date = f.start_date;
      if (f.end_date) body.end_date = f.end_date;
      await axios.post(`${API}/admin/finances/${markPaid ? 'mark-paid' : 'mark-pending'}`, body, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(markPaid
        ? `Pago registrado para 🐝 ${row.driver_name} (€${Number(row.total_earnings).toFixed(2)})`
        : `🐝 ${row.driver_name} marcado como Pendiente`);
      fetchFinance();
      fetchPayouts();
    } catch (e) {
      toast.error('No se pudo actualizar el estado de pago');
    } finally {
      setMarkingDriverId(null);
    }
  };

  const fetchPayouts = async () => {
    try {
      const res = await axios.get(`${API}/admin/finances/payouts`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setPayouts(res.data.payouts || []);
    } catch (e) {
      // noop
    }
  };

  const fetchCitiesList = async () => {
    try {
      const res = await axios.get(`${API}/cities`, { headers: { Authorization: `Bearer ${token}` } });
      setCitiesList(res.data.cities || []);
    } catch (e) { /* noop */ }
  };

  const fetchAllOrders = async (filters) => {
    const f = filters || ordersFilters;
    setOrdersLoading(true);
    try {
      const params = { limit: 200 };
      if (f.status) params.status = f.status;
      if (f.city_id) params.city_id = f.city_id;
      const res = await axios.get(`${API}/admin/orders`, {
        params, headers: { Authorization: `Bearer ${token}` },
      });
      setAllOrders(res.data.orders || []);
    } catch (e) {
      toast.error('No se pudieron cargar los pedidos');
    } finally {
      setOrdersLoading(false);
    }
  };

  const applyOrdersFilter = (patch) => {
    const next = { ...ordersFilters, ...patch };
    setOrdersFilters(next);
    fetchAllOrders(next);
  };

  const fetchData = async () => {
    setRefreshing(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [d, s, p] = await Promise.all([
        axios.get(`${API}/admin/active-drivers`, { headers }),
        axios.get(`${API}/admin/stats`, { headers }),
        axios.get(`${API}/admin/pending-orders`, { headers }),
      ]);
      setDrivers(d.data.drivers || []);
      setStats(s.data);
      setPendingOrders(p.data.orders || []);
      fetchHistory();
    } catch (error) {
      console.error('Error fetching admin data:', error);
    } finally {
      setRefreshing(false);
    }
  };

  // Step 1: preview the nearest available driver to the current map center
  const requestAssign = async (order) => {
    if (!mapRef.current) return;
    const c = mapRef.current.getCenter();
    setAssigningId(order.id);
    try {
      const res = await axios.get(`${API}/drivers/nearest`, {
        params: { lat: c.lat, lng: c.lng, limit: 1 },
        headers: { Authorization: `Bearer ${token}` },
      });
      const nearest = (res.data.drivers || [])[0];
      if (!nearest) {
        toast.error('No hay repartidores disponibles cerca de este punto.');
        return;
      }
      setConfirmData({ order, driver: { ...nearest, ref: { lat: c.lat, lng: c.lng } } });
      setConfirmOpen(true);
    } catch (error) {
      toast.error('No se pudo buscar el repartidor más cercano.');
    } finally {
      setAssigningId(null);
    }
  };

  // Step 2: commit the assignment, then center + highlight the chosen driver
  const confirmAssign = async () => {
    if (!confirmData) return;
    const { order, driver } = confirmData;
    setAssigningId(order.id);
    try {
      const res = await axios.post(
        `${API}/orders/${order.id}/assign-nearest`,
        { lat: driver.ref.lat, lng: driver.ref.lng },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const assigned = res.data.driver;
      toast.success(`Asignado: ${assigned.name} (${assigned.distance_km} km)`, { duration: 4000 });
      // Center map on the chosen driver and highlight it
      if (mapRef.current && driver.lat != null && driver.lng != null) {
        mapRef.current.flyTo([driver.lat, driver.lng], 11, { duration: 1.2 });
      }
      setHighlightId(assigned.id);
      setTimeout(() => setHighlightId((cur) => (cur === assigned.id ? null : cur)), 15000);
      await fetchData();
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(
        detail === 'No available drivers nearby'
          ? 'No hay repartidores disponibles cerca de este punto.'
          : (typeof detail === 'string' ? detail : 'No se pudo asignar el repartidor.')
      );
    } finally {
      setAssigningId(null);
      setConfirmOpen(false);
      setConfirmData(null);
    }
  };

  // Privacy: keep the admin panel out of search engines + private tab title while mounted
  useEffect(() => {
    const prevTitle = document.title;
    document.title = 'Nuboexpress - Private Control';
    const meta = document.createElement('meta');
    meta.name = 'robots';
    meta.content = 'noindex, nofollow, noarchive';
    document.head.appendChild(meta);
    return () => { document.head.removeChild(meta); document.title = prevTitle; };
  }, []);

  // Initialize Leaflet map manually (StrictMode-safe with proper teardown)
  useEffect(() => {
    if (mapElRef.current && !mapRef.current) {
      const map = L.map(mapElRef.current, { scrollWheelZoom: true }).setView(SPAIN_CENTER, 6);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map);
      markersLayerRef.current = L.layerGroup().addTo(map);
      mapRef.current = map;
    }
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        markersLayerRef.current = null;
      }
    };
  }, []);

  // Update markers whenever drivers or the highlighted driver change
  useEffect(() => {
    const layer = markersLayerRef.current;
    if (!layer) return;
    layer.clearLayers();
    drivers.forEach((driver) => {
      const isHi = driver.id === highlightId;
      const m = L.marker([driver.lat, driver.lng], { icon: isHi ? beeIconHighlight : beeIcon, zIndexOffset: isHi ? 1000 : 0 })
        .bindPopup(
          `<div style="font-size:13px"><strong>🐝 ${driver.name}</strong><br/>Vehículo: ${driver.vehicle_type || 'N/D'}<br/>Estado: <span style="color:${isHi ? '#f59e0b' : '#10b981'};font-weight:600">${isHi ? 'Asignado ahora' : 'Activo'}</span></div>`
        )
        .addTo(layer);
      if (isHi) m.openPopup();
    });
  }, [drivers, highlightId]);

  // Poll data
  useEffect(() => {
    fetchData();
    fetchFinance();
    fetchPayouts();
    fetchCitiesList();
    fetchAllOrders();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
    // eslint-disable-next-line
  }, []);

  // El mapa Leaflet vive oculto (display:none) cuando no es la sección activa;
  // al volver a "Mapa en vivo" recalculamos su tamaño para que renderice bien.
  useEffect(() => {
    if (section === 'map' && mapRef.current) {
      const id = setTimeout(() => { if (mapRef.current) mapRef.current.invalidateSize(); }, 120);
      return () => clearTimeout(id);
    }
  }, [section]);

  return (
    <AdminLayout
      active={section}
      onNavigate={setSection}
      user={user}
      onLogout={logout}
      badges={{ orders: pendingOrders.length }}
      actions={
        <Button data-testid="refresh-btn" onClick={fetchData} variant="outline" size="sm" className="gap-2">
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} /> Actualizar
        </Button>
      }
    >
      {/* RESUMEN */}
      <div hidden={section !== 'overview'} data-testid="section-overview">
        <OverviewSection onNavigate={setSection} />
      </div>

      {/* MAPA EN VIVO */}
      <div hidden={section !== 'map'} data-testid="section-map" className="space-y-8">
        <Card className="border-0 shadow-xl overflow-hidden">
          <CardContent className="p-0">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Mapa en vivo · España y Marruecos 🗺️</h2>
              <span data-testid="active-bees-count" className="text-sm font-medium text-emerald-600">
                {drivers.length} abejas en ruta
              </span>
            </div>
            <div ref={mapElRef} style={{ height: '560px', width: '100%' }} data-testid="admin-map" />
          </CardContent>
        </Card>

        {/* Pedidos pendientes — asignación manual desde el mapa */}
        <Card className="border-0 shadow-xl mt-8" data-testid="pending-orders-card">
          <CardContent className="p-0">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Pedidos pendientes</h2>
              <span data-testid="pending-orders-count" className="text-sm font-medium text-amber-600">
                {pendingOrders.length} sin asignar
              </span>
            </div>
            <div className="px-6 py-3 bg-amber-50 text-amber-800 text-sm flex items-center gap-2">
              <Crosshair className="w-4 h-4 flex-shrink-0" />
              Centra el mapa sobre la zona de recogida y pulsa "Asignar más cercano".
            </div>
            <div className="divide-y" data-testid="pending-orders-list">
              {pendingOrders.length === 0 ? (
                <div className="px-6 py-10 text-center text-gray-500">
                  <Package className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                  No hay pedidos pendientes de asignar.
                </div>
              ) : (
                pendingOrders.map((order) => (
                  <div key={order.id} data-testid={`pending-order-${order.id}`} className="px-6 py-4 flex items-center justify-between gap-4">
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 truncate">
                        #{order.id.slice(0, 8)} · {order.business_name}
                      </p>
                      <p className="text-sm text-gray-500 flex items-center gap-1 truncate">
                        <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
                        {order.delivery_address || 'Sin dirección'}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <span className="text-emerald-600 font-semibold">€{Number(order.total_amount).toFixed(2)}</span>
                      <Button
                        data-testid={`assign-nearest-${order.id}`}
                        size="sm"
                        onClick={() => requestAssign(order)}
                        disabled={assigningId === order.id}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white"
                      >
                        {assigningId === order.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Crosshair className="w-4 h-4 mr-2" />}
                        {assigningId === order.id ? '' : 'Asignar más cercano'}
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* HISTORIAL */}
      <div hidden={section !== 'history'} data-testid="section-history">
        {/* Historial de asignaciones — trazabilidad */}
        <Card className="border-0 shadow-xl" data-testid="assignment-history-card">
          <CardContent className="p-0">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <History className="w-5 h-5 text-gray-500" /> Historial de asignaciones
              </h2>
              <span data-testid="history-count" className="text-sm font-medium text-gray-500">
                {history.length} eventos
              </span>
            </div>

            {/* Filtros + exportación */}
            <div className="px-6 py-3 border-b bg-gray-50 flex flex-wrap items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                data-testid="filter-action"
                value={historyFilters.action}
                onChange={(e) => applyFilter({ action: e.target.value })}
                className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white"
              >
                <option value="">Todas las acciones</option>
                <option value="assigned">Asignado</option>
                <option value="auto_returned">Retorno automático</option>
                <option value="returned">Devuelto a cola</option>
              </select>
              <select
                data-testid="filter-driver"
                value={historyFilters.driver_id}
                onChange={(e) => applyFilter({ driver_id: e.target.value })}
                className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white"
              >
                <option value="">Todos los repartidores</option>
                {historyDrivers.map((dv) => (
                  <option key={dv.id} value={dv.id}>{dv.name}</option>
                ))}
              </select>
              <input
                data-testid="filter-date-from"
                type="date"
                value={historyFilters.date_from}
                onChange={(e) => applyFilter({ date_from: e.target.value })}
                className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white"
              />
              <span className="text-gray-400 text-sm">→</span>
              <input
                data-testid="filter-date-to"
                type="date"
                value={historyFilters.date_to}
                onChange={(e) => applyFilter({ date_to: e.target.value })}
                className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white"
              />
              <Button data-testid="clear-filters-btn" onClick={clearFilters} variant="outline" size="sm">
                Limpiar
              </Button>
              <Button
                data-testid="export-csv-btn"
                onClick={exportCsv}
                disabled={exporting}
                size="sm"
                className="bg-gray-900 hover:bg-gray-800 text-white ml-auto"
              >
                {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
                {exporting ? '' : 'Exportar CSV'}
              </Button>
            </div>
            <div className="divide-y max-h-[420px] overflow-y-auto" data-testid="assignment-history-list">
              {history.length === 0 ? (
                <div className="px-6 py-10 text-center text-gray-500">
                  <History className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                  Aún no hay eventos de asignación.
                </div>
              ) : (
                history.map((ev) => {
                  const meta = ev.action === 'assigned'
                    ? { label: 'Asignado', cls: 'bg-emerald-100 text-emerald-700' }
                    : ev.action === 'auto_returned'
                      ? { label: 'Retorno automático', cls: 'bg-amber-100 text-amber-700' }
                      : { label: 'Devuelto a cola', cls: 'bg-gray-200 text-gray-700' };
                  return (
                    <div key={ev.id} data-testid={`history-event-${ev.id}`} className="px-6 py-3 flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3 min-w-0">
                        <ArrowRightLeft className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm text-gray-900 truncate">
                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium mr-2 ${meta.cls}`}>{meta.label}</span>
                            Pedido #{ev.order_id?.slice(0, 8)} · 🐝 {ev.driver_name || 'N/D'}
                          </p>
                          <p className="text-xs text-gray-500 truncate">
                            por {ev.actor_name || ev.actor_role || 'sistema'}
                            {ev.distance_km != null ? ` · ${ev.distance_km} km` : ''}
                            {ev.reason ? ` · ${ev.reason}` : ''}
                          </p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-400 whitespace-nowrap flex-shrink-0">
                        {ev.created_at ? new Date(ev.created_at).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* FINANZAS */}
      <div hidden={section !== 'finances'} data-testid="section-finances" className="space-y-8">
        {/* Pagos por repartidor (comisiones) */}
        <Card className="border-0 shadow-xl" data-testid="finance-card">
          <CardContent className="p-0">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Wallet className="w-5 h-5 text-emerald-600" /> Pagos por repartidor
              </h2>
              <span className="text-sm font-medium text-emerald-700" data-testid="finance-total-earnings">
                Total comisiones: €{Number(finance.totals.earnings).toFixed(2)}
              </span>
            </div>

            <div className="px-6 py-3 border-b bg-gray-50 flex flex-wrap items-end gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Desde</label>
                <input data-testid="finance-date-from" type="date" value={financeFilters.start_date}
                  onChange={(e) => setFinanceFilters({ ...financeFilters, start_date: e.target.value })}
                  className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Hasta</label>
                <input data-testid="finance-date-to" type="date" value={financeFilters.end_date}
                  onChange={(e) => setFinanceFilters({ ...financeFilters, end_date: e.target.value })}
                  className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Comisión (%)</label>
                <input data-testid="finance-rate" type="number" min="0" max="100" step="0.5" value={financeFilters.rate_pct}
                  onChange={(e) => setFinanceFilters({ ...financeFilters, rate_pct: e.target.value })}
                  className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white w-24" />
              </div>
              <Button data-testid="finance-calc-btn" onClick={fetchFinance} disabled={financeLoading}
                size="sm" className="bg-emerald-600 hover:bg-emerald-500 text-white">
                {financeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Calcular'}
              </Button>
              <Button data-testid="finance-export-btn" onClick={exportFinanceCsv} disabled={financeExporting}
                size="sm" variant="outline" className="ml-auto">
                {financeExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
                {financeExporting ? '' : 'Exportar CSV'}
              </Button>
            </div>

            <div className="overflow-x-auto" data-testid="finance-table">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-left">
                  <tr>
                    <th className="px-6 py-3 font-medium">Repartidor</th>
                    <th className="px-6 py-3 font-medium text-right">Entregas</th>
                    <th className="px-6 py-3 font-medium text-right">Ingresos</th>
                    <th className="px-6 py-3 font-medium text-right">Comisión</th>
                    <th className="px-6 py-3 font-medium text-center">Estado</th>
                    <th className="px-6 py-3 font-medium text-right">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {finance.rows.length === 0 ? (
                    <tr><td colSpan="6" className="px-6 py-10 text-center text-gray-500">
                      No hay entregas en este periodo.
                    </td></tr>
                  ) : (
                    finance.rows.map((r) => {
                      const isPaid = r.payment_status === 'paid';
                      return (
                      <tr key={r.driver_id} data-testid={`finance-row-${r.driver_id}`}>
                        <td className="px-6 py-3 text-gray-900">🐝 {r.driver_name}</td>
                        <td className="px-6 py-3 text-right text-gray-700">{r.total_deliveries}</td>
                        <td className="px-6 py-3 text-right text-gray-700">€{Number(r.total_revenue).toFixed(2)}</td>
                        <td className="px-6 py-3 text-right font-semibold text-emerald-700">€{Number(r.total_earnings).toFixed(2)}</td>
                        <td className="px-6 py-3 text-center">
                          <span
                            data-testid={`finance-status-${r.driver_id}`}
                            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                              isPaid ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                            }`}>
                            {isPaid ? 'Pagado' : 'Pendiente'}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-right">
                          <Button
                            data-testid={`finance-toggle-${r.driver_id}`}
                            onClick={() => toggleDriverPayment(r)}
                            disabled={markingDriverId === r.driver_id}
                            size="sm"
                            variant={isPaid ? 'outline' : 'default'}
                            className={isPaid ? '' : 'bg-emerald-600 hover:bg-emerald-700 text-white'}>
                            {markingDriverId === r.driver_id
                              ? <Loader2 className="w-4 h-4 animate-spin" />
                              : (isPaid ? 'Marcar pendiente' : 'Marcar pagado')}
                          </Button>
                        </td>
                      </tr>
                    );})
                  )}
                </tbody>
                {finance.rows.length > 0 && (
                  <tfoot className="bg-gray-50 font-semibold text-gray-900">
                    <tr>
                      <td className="px-6 py-3">Total</td>
                      <td className="px-6 py-3 text-right">{finance.totals.deliveries}</td>
                      <td className="px-6 py-3 text-right">€{Number(finance.totals.revenue).toFixed(2)}</td>
                      <td className="px-6 py-3 text-right text-emerald-700">€{Number(finance.totals.earnings).toFixed(2)}</td>
                      <td className="px-6 py-3 text-center text-xs font-normal text-gray-500" colSpan="2">
                        <span className="text-emerald-700" data-testid="finance-total-paid">Pagado €{Number(finance.totals.paid_earnings || 0).toFixed(2)}</span>
                        {' · '}
                        <span className="text-amber-700" data-testid="finance-total-pending">Pendiente €{Number(finance.totals.pending_earnings || 0).toFixed(2)}</span>
                      </td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Historial de pagos (registro contable) */}
        <Card className="border-0 shadow-xl mt-8" data-testid="payouts-card">
          <CardContent className="p-0">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <History className="w-5 h-5 text-emerald-600" /> Historial de pagos
              </h2>
              <span data-testid="payouts-count" className="text-sm font-medium text-gray-500">
                {payouts.length} {payouts.length === 1 ? 'pago' : 'pagos'}
              </span>
            </div>
            <div className="overflow-x-auto" data-testid="payouts-table">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-left">
                  <tr>
                    <th className="px-6 py-3 font-medium">Repartidor</th>
                    <th className="px-6 py-3 font-medium">Periodo</th>
                    <th className="px-6 py-3 font-medium text-right">Entregas</th>
                    <th className="px-6 py-3 font-medium text-right">Importe</th>
                    <th className="px-6 py-3 font-medium text-right">Tasa</th>
                    <th className="px-6 py-3 font-medium">Pagado el</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {payouts.length === 0 ? (
                    <tr><td colSpan="6" className="px-6 py-10 text-center text-gray-500">
                      Aún no hay pagos registrados.
                    </td></tr>
                  ) : (
                    payouts.map((p) => (
                      <tr key={p.id} data-testid={`payout-row-${p.id}`}>
                        <td className="px-6 py-3 text-gray-900">🐝 {p.driver_name}</td>
                        <td className="px-6 py-3 text-gray-700">
                          {(p.period_start || 'inicio')} → {(p.period_end || 'hoy')}
                        </td>
                        <td className="px-6 py-3 text-right text-gray-700">{p.deliveries}</td>
                        <td className="px-6 py-3 text-right font-semibold text-emerald-700">€{Number(p.amount).toFixed(2)}</td>
                        <td className="px-6 py-3 text-right text-gray-500">{Math.round((p.rate || 0) * 100)}%</td>
                        <td className="px-6 py-3 text-gray-600">
                          {p.paid_at ? new Date(p.paid_at).toLocaleString('es-ES') : '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* CONTABILIDAD */}
      <div hidden={section !== 'accounting'} data-testid="section-accounting">
        <ContabilidadSection />
      </div>

      {/* ZONAS OPERATIVAS */}
      <div hidden={section !== 'cities'} data-testid="section-cities">
        {/* Gestor de zonas operativas (ciudades) */}
        <CityManager API={API} token={token} onChanged={fetchCitiesList} />
      </div>

      {/* PEDIDOS */}
      <div hidden={section !== 'orders'} data-testid="section-orders">
        {/* Todos los pedidos */}
        <Card className="border-0 shadow-xl" data-testid="all-orders-card">
          <CardContent className="p-0">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Package className="w-5 h-5 text-gray-500" /> Todos los pedidos
              </h2>
              <span data-testid="all-orders-count" className="text-sm font-medium text-gray-500">
                {allOrders.length} pedidos
              </span>
            </div>

            <div className="px-6 py-3 border-b bg-gray-50 flex flex-wrap items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select data-testid="orders-filter-status" value={ordersFilters.status}
                onChange={(e) => applyOrdersFilter({ status: e.target.value })}
                className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white">
                <option value="">Todos los estados</option>
                <option value="pending">Pendiente</option>
                <option value="accepted">Aceptado</option>
                <option value="preparing">Preparando</option>
                <option value="ready">Listo</option>
                <option value="in_transit">En camino</option>
                <option value="delivered">Entregado</option>
                <option value="cancelled">Cancelado</option>
              </select>
              <select data-testid="orders-filter-city" value={ordersFilters.city_id}
                onChange={(e) => applyOrdersFilter({ city_id: e.target.value })}
                className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white">
                <option value="">Todas las ciudades</option>
                {citiesList.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              {ordersLoading && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
            </div>

            <div className="overflow-x-auto max-h-[480px] overflow-y-auto" data-testid="all-orders-table">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-left sticky top-0">
                  <tr>
                    <th className="px-4 py-3 font-medium">Pedido</th>
                    <th className="px-4 py-3 font-medium">Negocio</th>
                    <th className="px-4 py-3 font-medium">Ciudad</th>
                    <th className="px-4 py-3 font-medium">Repartidor</th>
                    <th className="px-4 py-3 font-medium">Estado</th>
                    <th className="px-4 py-3 font-medium text-right">Importe</th>
                    <th className="px-4 py-3 font-medium">Fecha</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {allOrders.length === 0 ? (
                    <tr><td colSpan="7" className="px-6 py-10 text-center text-gray-500">No hay pedidos.</td></tr>
                  ) : (
                    allOrders.map((o) => (
                      <tr key={o.id} data-testid={`order-row-${o.id}`}>
                        <td className="px-4 py-3 font-mono text-xs text-gray-700">#{o.id.slice(0, 8)}</td>
                        <td className="px-4 py-3 text-gray-900">{o.business_name}</td>
                        <td className="px-4 py-3 text-gray-700">{o.city_name || '—'}</td>
                        <td className="px-4 py-3 text-gray-700">{o.driver_name ? `🐝 ${o.driver_name}` : '—'}</td>
                        <td className="px-4 py-3">
                          <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">{o.status}</span>
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-gray-900">€{Number(o.total_amount).toFixed(2)}</td>
                        <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">
                          {o.created_at ? new Date(o.created_at).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Confirmación de asignación */}
      <AlertDialog open={confirmOpen} onOpenChange={(o) => { if (!o) { setConfirmOpen(false); setConfirmData(null); } }}>
        <AlertDialogContent data-testid="assign-confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar asignación</AlertDialogTitle>
            <AlertDialogDescription data-testid="assign-confirm-text">
              {confirmData
                ? `¿Confirmar asignación a ${confirmData.driver.name} a ${confirmData.driver.distance_km} km?`
                : ''}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="assign-cancel-btn">Cancelar</AlertDialogCancel>
            <AlertDialogAction
              data-testid="assign-confirm-btn"
              onClick={confirmAssign}
              className="bg-emerald-600 hover:bg-emerald-500"
            >
              Confirmar asignación
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
