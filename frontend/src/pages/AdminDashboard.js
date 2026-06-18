import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import MapComponent from '@/components/MapComponent';
import CityManager from '@/components/CityManager';
import RiderManager from '@/components/RiderManager';
import OperationsManager from '@/components/OperationsManager';
import { LogOut, Truck, Package, CheckCircle2, Users, Activity, MapPin, RadioTower, Bell, BellOff, AlertTriangle, ShoppingBag, Send } from 'lucide-react';

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
  const [fleet, setFleet] = useState({ count: 0, live_count: 0, available_count: 0, idle_count: 0, drivers: [] });
  const [lastUpdate, setLastUpdate] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [alerts, setAlerts] = useState([]); // recent alert feed
  const [telegramConfigured, setTelegramConfigured] = useState(null);
  const [telegramTesting, setTelegramTesting] = useState(false);
  const intervalRef = useRef(null);
  const audioCtxRef = useRef(null);
  const prevOrdersRef = useRef(null);
  const idleAlertedRef = useRef(new Set());
  const firstLoadRef = useRef(true);

  // --- Sound (Web Audio API beep, no assets needed) ---
  const enableSound = () => {
    try {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      setSoundEnabled(true);
      playBeep(880, 0.12); // confirmation chirp
      toast.success('Alertas de sonido activadas');
    } catch (e) {
      toast.error('Tu navegador no permite alertas de sonido');
    }
  };

  const playBeep = (frequency = 880, duration = 0.15, type = 'sine') => {
    const ctx = audioCtxRef.current;
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = frequency;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.3, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  };

  const pushAlert = (type, message) => {
    setAlerts(prev => [{ id: Date.now() + Math.random(), type, message, time: new Date() }, ...prev].slice(0, 8));
  };

  const triggerNewOrderAlert = (count) => {
    playBeep(660, 0.18, 'triangle');
    setTimeout(() => playBeep(990, 0.18, 'triangle'), 180);
    toast.success(`🛍️ Nuevo pedido recibido (total: ${count})`, { duration: 6000 });
    pushAlert('order', `Nuevo pedido recibido (total: ${count})`);
  };

  const triggerIdleAlert = (driverName) => {
    playBeep(300, 0.3, 'sawtooth');
    toast.warning(`⚠️ ${driverName} lleva demasiado tiempo parada`, { duration: 8000 });
    pushAlert('idle', `${driverName} lleva demasiado tiempo parada`);
  };

  const fetchData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [statsRes, fleetRes] = await Promise.all([
        axios.get(`${API}/admin/stats`, { headers }),
        axios.get(`${API}/admin/active-drivers`, { headers }),
      ]);
      const newStats = statsRes.data;
      const newFleet = fleetRes.data;

      // --- New order detection ---
      const totalOrders = newStats.total_orders;
      if (!firstLoadRef.current && prevOrdersRef.current != null && totalOrders > prevOrdersRef.current) {
        triggerNewOrderAlert(totalOrders);
      }
      prevOrdersRef.current = totalOrders;

      // --- Idle bee detection ---
      const currentIdleKeys = new Set();
      (newFleet.drivers || []).forEach(d => {
        if (d.idle && d.live) {
          const key = d.order_id || d.driver_id || d.driver_name;
          currentIdleKeys.add(key);
          if (!firstLoadRef.current && !idleAlertedRef.current.has(key)) {
            triggerIdleAlert(d.driver_name);
          }
        }
      });
      // Clear alerted keys that are no longer idle so they can re-alert later
      idleAlertedRef.current = currentIdleKeys;

      firstLoadRef.current = false;
      setStats(newStats);
      setFleet(newFleet);
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

  // Telegram config status
  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` };
    axios.get(`${API}/admin/telegram/status`, { headers })
      .then(r => setTelegramConfigured(r.data.configured))
      .catch(() => setTelegramConfigured(false));
  }, [API, token]);

  const testTelegram = async () => {
    setTelegramTesting(true);
    try {
      const r = await axios.post(`${API}/admin/telegram/test`, {}, { headers: { Authorization: `Bearer ${token}` } });
      if (r.data.sent) toast.success('Mensaje de prueba enviado a Telegram');
      else toast.error(r.data.detail || 'Telegram no configurado');
    } catch (e) {
      toast.error('Error al probar Telegram');
    } finally {
      setTelegramTesting(false);
    }
  };

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
          <div className="flex items-center gap-2">
            <Button data-testid="admin-sound-toggle-btn" onClick={enableSound} variant={soundEnabled ? 'default' : 'outline'} size="sm" className={soundEnabled ? 'bg-emerald-600' : ''}>
              {soundEnabled ? <Bell className="w-4 h-4 mr-2" /> : <BellOff className="w-4 h-4 mr-2" />}
              {soundEnabled ? 'Alertas ON' : 'Activar alertas'}
            </Button>
            <Button data-testid="admin-logout-btn" onClick={logout} variant="outline" size="sm">
              <LogOut className="w-4 h-4 mr-2" />
              Salir
            </Button>
          </div>
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
          <div className="space-y-6">
            {/* Recent alerts feed */}
            <Card data-testid="admin-alerts" className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Bell className="w-5 h-5 text-emerald-600" />
                    Alertas recientes
                  </span>
                  {fleet.idle_count > 0 && (
                    <Badge data-testid="idle-count-badge" className="bg-amber-100 text-amber-700">{fleet.idle_count} paradas</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!soundEnabled && (
                  <p className="text-xs text-amber-600 mb-3 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Pulsa "Activar alertas" para oír el sonido.
                  </p>
                )}
                {alerts.length === 0 ? (
                  <p className="text-sm text-gray-500">Sin alertas por ahora.</p>
                ) : (
                  <div className="space-y-2 max-h-[160px] overflow-y-auto">
                    {alerts.map(a => (
                      <div key={a.id} data-testid={`alert-item-${a.type}`} className={`flex items-start gap-2 p-2 rounded-lg text-sm ${a.type === 'idle' ? 'bg-amber-50 text-amber-800' : 'bg-emerald-50 text-emerald-800'}`}>
                        {a.type === 'idle' ? <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> : <ShoppingBag className="w-4 h-4 mt-0.5 shrink-0" />}
                        <div className="flex-1 min-w-0">
                          <p>{a.message}</p>
                          <p className="text-xs opacity-60">{a.time.toLocaleTimeString('es-ES')}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Telegram alerts config */}
            <Card data-testid="admin-telegram" className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Send className="w-5 h-5 text-sky-600" />
                    Alertas Telegram
                  </span>
                  <Badge data-testid="telegram-status-badge" className={telegramConfigured ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}>
                    {telegramConfigured == null ? '...' : (telegramConfigured ? 'Activo' : 'Sin configurar')}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 mb-3">
                  Recibe avisos de <b>pedidos nuevos</b> y <b>Abejas paradas</b> en tu móvil, aunque el panel esté cerrado.
                </p>
                <Button
                  data-testid="telegram-test-btn"
                  onClick={testTelegram}
                  disabled={telegramTesting || !telegramConfigured}
                  size="sm"
                  className="bg-sky-600 hover:bg-sky-700"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {telegramTesting ? 'Enviando...' : 'Enviar prueba'}
                </Button>
                {telegramConfigured === false && (
                  <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Configura el bot para activar las alertas móviles.
                  </p>
                )}
              </CardContent>
            </Card>

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
                    <div key={d.order_id || d.driver_id || i} data-testid={`fleet-driver-${i}`} className={`flex items-center gap-3 p-3 rounded-lg border ${d.idle ? 'bg-amber-50 border-amber-200' : 'bg-white'}`}>
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center text-lg ${d.idle ? 'bg-amber-100' : (d.live ? 'bg-emerald-100' : 'bg-gray-100')}`}>
                        🐝
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">{d.driver_name}</p>
                        <p className="text-xs text-gray-500 truncate">
                          {d.idle ? `Parada hace ${d.idle_seconds}s` : (d.delivery_address ? d.delivery_address : (d.vehicle_type || 'Sin pedido activo'))}
                        </p>
                      </div>
                      <Badge className={d.idle ? 'bg-amber-100 text-amber-700' : (d.live ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600')}>
                        {d.idle ? 'Parada' : (d.live ? 'En vivo' : d.status)}
                      </Badge>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Operaciones y Logística (Bloque C): despacho por proximidad + historial */}
        <OperationsManager API={API} token={token} />

        {/* Gestión de zonas operativas (ciudades) */}
        <CityManager API={API} token={token} />

        {/* Gestión de conductores (Riders) + códigos QR */}
        <RiderManager API={API} token={token} />
      </div>
    </div>
  );
}
