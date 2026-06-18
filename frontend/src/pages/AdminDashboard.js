import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import MapComponent from '@/components/MapComponent';
import { LogOut, Truck, Package, CheckCircle2, Users, Activity, MapPin, RadioTower } from 'lucide-react';

const SPAIN_CENTER = { lat: 40.4168, lng: -3.7038 };

const GREEN_BEE_ICON = {
  url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 44 44">
      <circle cx="22" cy="22" r="20" fill="#10b981" stroke="#065f46" stroke-width="3"/>
      <text x="22" y="31" font-size="24" text-anchor="middle">🐝</text>
    </svg>`),
  scaledSize: { width: 44, height: 44 },
};

const StatCard = ({ icon: Icon, label, value, color, testid }) => (
  <Card data-testid={testid} className="border-0 shadow-md">
    <CardContent className="p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-600">{label}</p>
      </div>
    </CardContent>
  </Card>
);

export default function AdminDashboard() {
  const { user, token, logout, API } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [fleet, setFleet] = useState({ count: 0, live_count: 0, available_count: 0, drivers: [] });
  const [lastUpdate, setLastUpdate] = useState(null);
  const intervalRef = useRef(null);

  const fetchData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [statsRes, fleetRes] = await Promise.all([
        axios.get(`${API}/admin/stats`, { headers }),
        axios.get(`${API}/admin/active-drivers`, { headers }),
      ]);
      setStats(statsRes.data);
      setFleet(fleetRes.data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching admin data:', error);
    }
  };

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, 5000);
    return () => clearInterval(intervalRef.current);
  }, []);

  const markers = fleet.drivers
    .filter(d => d.lat != null && d.lng != null)
    .map(d => ({
      lat: d.lat,
      lng: d.lng,
      title: `🐝 ${d.driver_name}`,
      icon: GREEN_BEE_ICON,
    }));

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <header className="glass sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
              <RadioTower className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Nubo Admin</h1>
              <p className="text-sm text-gray-600">Panel de Control · {user?.name}</p>
            </div>
          </div>
          <Button data-testid="admin-logout-btn" onClick={logout} variant="outline" size="sm">
            <LogOut className="w-4 h-4 mr-2" />
            Salir
          </Button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats */}
        <div data-testid="admin-stats" className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard testid="stat-active-orders" icon={Truck} label="En reparto" value={stats?.in_transit ?? '—'} color="bg-orange-500" />
          <StatCard testid="stat-live-drivers" icon={Activity} label="Abejas en vivo" value={fleet.live_count} color="bg-emerald-500" />
          <StatCard testid="stat-available-drivers" icon={Users} label="Conductores disponibles" value={stats?.available_drivers ?? '—'} color="bg-teal-500" />
          <StatCard testid="stat-delivered" icon={CheckCircle2} label="Entregados" value={stats?.delivered ?? '—'} color="bg-blue-500" />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Map */}
          <div className="lg:col-span-2">
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-emerald-600" />
                    Mapa de Flota en Tiempo Real
                  </span>
                  <span className="flex items-center gap-2 text-sm font-normal text-gray-500">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    {lastUpdate ? `Actualizado ${lastUpdate.toLocaleTimeString('es-ES')}` : 'Conectando...'}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <MapComponent markers={markers} center={SPAIN_CENTER} zoom={6} />
                {markers.length === 0 && (
                  <p className="mt-3 text-sm text-gray-500 text-center">
                    No hay abejas con ubicación activa en el mapa ahora mismo.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Live driver list */}
          <div>
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-emerald-600" />
                  Abejas Activas ({fleet.count})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 max-h-[460px] overflow-y-auto">
                {fleet.drivers.length === 0 ? (
                  <div className="text-center py-10">
                    <Package className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                    <p className="text-gray-500 text-sm">No hay conductores activos en este momento.</p>
                  </div>
                ) : (
                  fleet.drivers.map((d, i) => (
                    <div key={d.order_id || d.driver_id || i} data-testid={`fleet-driver-${i}`} className="flex items-center gap-3 p-3 rounded-lg border bg-white">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center text-lg ${d.live ? 'bg-emerald-100' : 'bg-gray-100'}`}>
                        🐝
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">{d.driver_name}</p>
                        <p className="text-xs text-gray-500 truncate">
                          {d.delivery_address ? d.delivery_address : (d.vehicle_type || 'Sin pedido activo')}
                        </p>
                      </div>
                      <Badge className={d.live ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}>
                        {d.live ? 'En vivo' : d.status}
                      </Badge>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
