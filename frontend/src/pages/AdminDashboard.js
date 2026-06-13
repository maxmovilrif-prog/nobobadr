import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
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

  const assignNearest = async (orderId) => {
    if (!mapRef.current) return;
    const c = mapRef.current.getCenter();
    setAssigningId(orderId);
    try {
      const res = await axios.post(
        `${API}/orders/${orderId}/assign-nearest`,
        { lat: c.lat, lng: c.lng },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const drv = res.data.driver;
      toast.success(`Asignado: ${drv.name} (${drv.distance_km} km)`);
      fetchData();
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(
        detail === 'No available drivers nearby'
          ? 'No hay repartidores disponibles cerca de este punto.'
          : (typeof detail === 'string' ? detail : 'No se pudo asignar el repartidor.')
      );
    } finally {
      setAssigningId(null);
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

  // Update markers whenever drivers change
  useEffect(() => {
    const layer = markersLayerRef.current;
    if (!layer) return;
    layer.clearLayers();
    drivers.forEach((driver) => {
      L.marker([driver.lat, driver.lng], { icon: beeIcon })
        .bindPopup(
          `<div style="font-size:13px"><strong>🐝 ${driver.name}</strong><br/>Vehículo: ${driver.vehicle_type || 'N/D'}<br/>Estado: <span style="color:#10b981;font-weight:600">Activo</span></div>`
        )
        .addTo(layer);
    });
  }, [drivers]);

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
                        onClick={() => assignNearest(order.id)}
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
    </div>
  );
}
