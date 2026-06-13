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
import { LogOut, Bike, Store, Package, Users, RefreshCw, Crosshair, Loader2, MapPin } from 'lucide-react';

const SPAIN_CENTER = [40.0, -3.7];

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

const StatCard = ({ icon: Icon, label, value, testid }) => (
  <Card data-testid={testid} className="border-0 shadow-lg">
    <CardContent className="p-5 flex items-center gap-4">
      <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center">
        <Icon className="w-6 h-6 text-emerald-600" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </CardContent>
  </Card>
);

export default function AdminDashboard() {
  const { user, token, logout, API } = useContext(AuthContext);
  const [drivers, setDrivers] = useState([]);
  const [stats, setStats] = useState({ total_drivers: 0, active_drivers: 0, total_businesses: 0, total_orders: 0 });
  const [pendingOrders, setPendingOrders] = useState([]);
  const [assigningId, setAssigningId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [confirmData, setConfirmData] = useState(null); // { order, driver }
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [highlightId, setHighlightId] = useState(null);

  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const markersLayerRef = useRef(null);

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
      toast.success(`Asignado: ${assigned.name} (${assigned.distance_km} km)`);
      // Center map on the chosen driver and highlight it
      if (mapRef.current && driver.lat != null && driver.lng != null) {
        mapRef.current.flyTo([driver.lat, driver.lng], 11, { duration: 1.2 });
      }
      setHighlightId(assigned.id);
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

  // Privacy: keep the admin panel out of search engines while mounted
  useEffect(() => {
    const meta = document.createElement('meta');
    meta.name = 'robots';
    meta.content = 'noindex, nofollow, noarchive';
    document.head.appendChild(meta);
    return () => { document.head.removeChild(meta); };
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
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
    // eslint-disable-next-line
  }, []);

  return (
    <div className="min-h-screen bg-gray-50" data-testid="admin-dashboard">
      <header className="bg-gray-900 sticky top-0 z-[1000] shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center text-xl">🐝</div>
            <div>
              <h1 className="text-xl font-bold text-white">Nubo Express · Admin</h1>
              <p className="text-sm text-gray-400">Mapa de Abejas en vivo · {user?.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button data-testid="refresh-btn" onClick={fetchData} variant="outline" size="sm" className="bg-gray-800 text-white border-gray-700 hover:bg-gray-700">
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
            <Button data-testid="admin-logout-btn" onClick={logout} variant="outline" size="sm" className="bg-gray-800 text-white border-gray-700 hover:bg-gray-700">
              <LogOut className="w-4 h-4 mr-2" />
              Salir
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard testid="stat-active-drivers" icon={Bike} label="Abejas activas" value={stats.active_drivers} />
          <StatCard testid="stat-total-drivers" icon={Users} label="Total repartidores" value={stats.total_drivers} />
          <StatCard testid="stat-businesses" icon={Store} label="Negocios" value={stats.total_businesses} />
          <StatCard testid="stat-orders" icon={Package} label="Pedidos" value={stats.total_orders} />
        </div>

        <Card className="border-0 shadow-xl overflow-hidden">
          <CardContent className="p-0">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Mapa en vivo de España 🗺️</h2>
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

      {/* Confirmación de asignación */}
      <AlertDialog open={confirmOpen} onOpenChange={(o) => { if (!o) { setConfirmOpen(false); setConfirmData(null); } }}>
        <AlertDialogContent data-testid="assign-confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar asignación</AlertDialogTitle>
            <AlertDialogDescription data-testid="assign-confirm-text">
              {confirmData
                ? `¿Confirmar asignación a la Abeja ${confirmData.driver.name} a ${confirmData.driver.distance_km} km?`
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
    </div>
  );
}
