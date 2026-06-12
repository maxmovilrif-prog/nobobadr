import React, { useState, useEffect, useContext, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import MapComponent from '@/components/MapComponent';
import { LogOut, Users, Bike, Store, ShoppingBag, Euro, Activity, RefreshCw } from 'lucide-react';

// Bee marker icon (yellow) as SVG data URL
const BEE_ICON = {
  url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 44 44">
      <circle cx="22" cy="22" r="14" fill="#FACC15" stroke="#0f172a" stroke-width="2"/>
      <rect x="14" y="14" width="16" height="4" fill="#0f172a"/>
      <rect x="14" y="22" width="16" height="4" fill="#0f172a"/>
      <ellipse cx="14" cy="16" rx="6" ry="4" fill="#ffffff" opacity="0.85" stroke="#0f172a" stroke-width="1"/>
      <ellipse cx="30" cy="16" rx="6" ry="4" fill="#ffffff" opacity="0.85" stroke="#0f172a" stroke-width="1"/>
    </svg>`),
};

const SPAIN_CENTER = { lat: 39.5, lng: -3.5 };

const StatCard = ({ icon: Icon, label, value, color, testid }) => (
  <Card data-testid={testid} className="border-none shadow-md">
    <CardContent className="p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <p className="text-sm text-slate-500">{label}</p>
      </div>
    </CardContent>
  </Card>
);

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { user, token, logout, API } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [drivers, setDrivers] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [statsRes, driversRes] = await Promise.all([
        axios.get(`${API}/admin/stats`, { headers }),
        axios.get(`${API}/admin/active-drivers`, { headers }),
      ]);
      setStats(statsRes.data);
      setDrivers(driversRes.data.drivers || []);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching admin data:', error);
    } finally {
      setLoading(false);
    }
  }, [API, token]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, [fetchData]);

  const markers = drivers.map((d) => ({
    lat: d.lat,
    lng: d.lng,
    title: `${d.name} (${d.vehicle_type || 'N/D'})`,
    icon: BEE_ICON,
  }));

  return (
    <div className="min-h-screen bg-slate-50" data-testid="admin-dashboard">
      {/* Header */}
      <header className="bg-slate-900 sticky top-0 z-50 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-yellow-500 rounded-xl flex items-center justify-center">
              <Activity className="w-5 h-5 text-slate-900" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Nubo Express · Admin</h1>
              <p className="text-xs text-slate-400">Panel de control en tiempo real</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden sm:block text-sm text-slate-300">{user?.name}</span>
            <Button data-testid="admin-logout-btn" variant="ghost" size="sm" className="text-slate-200 hover:text-white"
              onClick={() => { logout(); navigate('/'); }}>
              <LogOut className="w-4 h-4 mr-2" /> Salir
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="admin-stats-grid">
          <StatCard testid="stat-customers" icon={Users} label="Clientes" value={stats?.total_customers ?? '—'} color="bg-emerald-500" />
          <StatCard testid="stat-drivers" icon={Bike} label="Abejas activas" value={stats ? `${stats.available_drivers}/${stats.total_drivers}` : '—'} color="bg-amber-500" />
          <StatCard testid="stat-businesses" icon={Store} label="Negocios" value={stats?.total_businesses ?? '—'} color="bg-teal-500" />
          <StatCard testid="stat-orders" icon={ShoppingBag} label="Pedidos activos" value={stats ? `${stats.active_orders}/${stats.total_orders}` : '—'} color="bg-sky-500" />
          <StatCard testid="stat-delivered" icon={Activity} label="Entregados" value={stats?.delivered_orders ?? '—'} color="bg-indigo-500" />
          <StatCard testid="stat-revenue" icon={Euro} label="Ingresos" value={stats ? `${stats.revenue} €` : '—'} color="bg-rose-500" />
        </div>

        {/* Live map */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-800">Mapa en vivo de Abejas 🐝</h2>
              <p className="text-sm text-slate-500">
                {drivers.length} repartidores activos en España y Marruecos
                {lastUpdate && ` · actualizado ${lastUpdate.toLocaleTimeString('es-ES')}`}
              </p>
            </div>
            <Button data-testid="admin-refresh-btn" variant="outline" size="sm" onClick={fetchData} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} /> Actualizar
            </Button>
          </div>
          <div className="rounded-xl overflow-hidden shadow-md" style={{ height: 500 }} data-testid="admin-live-map">
            <MapComponent markers={markers} center={SPAIN_CENTER} zoom={6} />
          </div>
        </div>

        {/* Driver list */}
        <div>
          <h2 className="text-lg font-bold text-slate-800 mb-4">Abejas conectadas</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="admin-driver-list">
            {drivers.length === 0 && (
              <p className="text-sm text-slate-500 col-span-full">No hay repartidores activos en este momento.</p>
            )}
            {drivers.map((d) => (
              <Card key={d.driver_id} data-testid={`driver-card-${d.driver_id}`} className="border-none shadow-sm">
                <CardContent className="p-4 flex items-center gap-3">
                  <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center text-xl">🐝</div>
                  <div className="flex-1">
                    <p className="font-semibold text-slate-800">{d.name}</p>
                    <p className="text-xs text-slate-500">{d.lat.toFixed(3)}, {d.lng.toFixed(3)}</p>
                  </div>
                  <Badge className="bg-amber-100 text-amber-700">{d.vehicle_type || 'N/D'}</Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
