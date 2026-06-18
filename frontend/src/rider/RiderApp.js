import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { ScanLine, LogOut, MapPin, Package, Power, Loader2, Bike, Car, Truck, Zap, ShieldAlert } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const RIDER_TOKEN_KEY = 'nubo_rider_token';

const VEHICLE_ICON = { bicycle: Bike, motorcycle: Zap, car: Car, truck: Truck };
const VEHICLE_LABEL = { bicycle: 'Bici', motorcycle: 'Moto', car: 'Coche', truck: 'Camión' };

export default function RiderApp() {
  const [token, setToken] = useState(localStorage.getItem(RIDER_TOKEN_KEY));
  const [rider, setRider] = useState(null);
  const [loading, setLoading] = useState(!!token);
  const [code, setCode] = useState('');
  const [activating, setActivating] = useState(false);
  const [orders, setOrders] = useState([]);
  const [sharing, setSharing] = useState(false);
  const watchIdRef = useRef(null);

  const authHeaders = useCallback(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);

  const loadProfile = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/rider/me`, { headers: { Authorization: `Bearer ${token}` } });
      setRider(res.data);
    } catch (e) {
      localStorage.removeItem(RIDER_TOKEN_KEY);
      setToken(null);
      setRider(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) loadProfile();
  }, [token, loadProfile]);

  const loadOrders = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/orders`, authHeaders());
      setOrders(res.data || []);
    } catch (e) { /* noop */ }
  }, [authHeaders]);

  useEffect(() => {
    if (rider) loadOrders();
  }, [rider, loadOrders]);

  const handleActivate = async (e) => {
    e.preventDefault();
    const c = code.trim().toUpperCase();
    if (!c) return;
    setActivating(true);
    try {
      const res = await axios.post(`${API}/rider/activate`, { code: c });
      localStorage.setItem(RIDER_TOKEN_KEY, res.data.token);
      setToken(res.data.token);
      setRider(res.data.rider);
      toast.success(`¡Bienvenido, ${res.data.rider.name}!`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Código no válido');
    } finally {
      setActivating(false);
    }
  };

  const logout = () => {
    stopSharing();
    localStorage.removeItem(RIDER_TOKEN_KEY);
    setToken(null);
    setRider(null);
    setCode('');
  };

  const toggleAvailability = async (val) => {
    try {
      await axios.patch(`${API}/rider/availability?is_available=${val}`, {}, authHeaders());
      setRider((r) => ({ ...r, is_available: val }));
    } catch (e) { toast.error('No se pudo actualizar'); }
  };

  const sendLocation = useCallback((lat, lng) => {
    axios.post(`${API}/rider/location`, { lat, lng }, authHeaders()).catch(() => {});
  }, [authHeaders]);

  const startSharing = () => {
    if (!navigator.geolocation) { toast.error('Geolocalización no disponible'); return; }
    setSharing(true);
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => sendLocation(pos.coords.latitude, pos.coords.longitude),
      () => { toast.error('No se pudo obtener tu ubicación'); setSharing(false); },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
    );
    toast.success('Compartiendo ubicación en tiempo real');
  };

  const stopSharing = () => {
    if (watchIdRef.current != null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    setSharing(false);
  };

  useEffect(() => () => stopSharing(), []);

  // ---- Loading ----
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
      </div>
    );
  }

  // ---- Activation screen ----
  if (!rider) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-gray-900 to-emerald-950 px-6" data-testid="rider-activation">
        <div className="w-full max-w-sm text-center">
          <div className="w-20 h-20 mx-auto mb-6 rounded-3xl bg-emerald-500 flex items-center justify-center shadow-2xl shadow-emerald-500/30">
            <span className="text-4xl">🐝</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-1">Nubo Riders</h1>
          <p className="text-emerald-200/70 text-sm mb-8">Introduce el código que te dio administración</p>
          <form onSubmit={handleActivate} className="space-y-4">
            <Input
              data-testid="rider-code-input"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="NUBO-XXXX"
              className="text-center text-lg tracking-widest bg-white/10 border-white/20 text-white placeholder:text-white/30 h-14"
            />
            <Button data-testid="rider-activate-btn" type="submit" disabled={activating}
              className="w-full h-12 bg-emerald-500 hover:bg-emerald-600 text-white gap-2">
              {activating ? <Loader2 className="w-5 h-5 animate-spin" /> : <ScanLine className="w-5 h-5" />}
              Activar mi app
            </Button>
          </form>
          <p className="text-white/30 text-xs mt-8">Escanea tu QR o escribe el código. Solo conductores autorizados.</p>
        </div>
      </div>
    );
  }

  // ---- Suspended ----
  if (rider.contract_status === 'suspended') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-900 px-6 text-center" data-testid="rider-suspended">
        <ShieldAlert className="w-14 h-14 text-amber-400 mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Cuenta suspendida</h2>
        <p className="text-white/60 text-sm mb-6">Contacta con administración para reactivar tu cuenta.</p>
        <Button onClick={logout} variant="outline" data-testid="rider-logout-btn">Salir</Button>
      </div>
    );
  }

  // ---- Rider home ----
  const VIcon = VEHICLE_ICON[rider.vehicle_type] || Zap;
  return (
    <div className="min-h-screen bg-gray-50 pb-10" data-testid="rider-home">
      <header className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-5 pt-8 pb-12 rounded-b-3xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-white/20 flex items-center justify-center">
              <VIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <p className="font-bold text-lg leading-tight" data-testid="rider-name">{rider.name}</p>
              <p className="text-white/70 text-xs">{VEHICLE_LABEL[rider.vehicle_type]} {rider.license_plate ? `· ${rider.license_plate}` : ''}</p>
            </div>
          </div>
          <Button onClick={logout} size="icon" variant="ghost" className="text-white hover:bg-white/10" data-testid="rider-logout-btn">
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </header>

      <div className="px-5 -mt-6 space-y-4">
        {/* Availability */}
        <Card className="border-0 shadow-lg">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Power className={`w-5 h-5 ${rider.is_available ? 'text-emerald-500' : 'text-gray-400'}`} />
              <div>
                <p className="font-medium text-gray-900">Disponible</p>
                <p className="text-xs text-gray-500">{rider.is_available ? 'Recibiendo pedidos' : 'Fuera de servicio'}</p>
              </div>
            </div>
            <Switch data-testid="rider-availability-switch" checked={!!rider.is_available} onCheckedChange={toggleAvailability} />
          </CardContent>
        </Card>

        {/* Location sharing */}
        <Card className="border-0 shadow-lg">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <MapPin className={`w-5 h-5 ${sharing ? 'text-emerald-500 animate-pulse' : 'text-gray-400'}`} />
              <div>
                <p className="font-medium text-gray-900">Ubicación en vivo</p>
                <p className="text-xs text-gray-500">{sharing ? 'Compartiendo con central' : 'Detenida'}</p>
              </div>
            </div>
            {sharing ? (
              <Button data-testid="rider-stop-location" onClick={stopSharing} size="sm" variant="outline">Detener</Button>
            ) : (
              <Button data-testid="rider-start-location" onClick={startSharing} size="sm" className="bg-emerald-600">Activar</Button>
            )}
          </CardContent>
        </Card>

        {/* Assigned orders */}
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-2 px-1">Mis pedidos asignados</h2>
          {orders.length === 0 ? (
            <Card className="border-0 shadow-sm">
              <CardContent className="p-8 text-center text-gray-400">
                <Package className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">No tienes pedidos asignados ahora.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {orders.map((o) => (
                <Card key={o.id} data-testid={`rider-order-${o.id}`} className="border-0 shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-gray-900">#{o.id.slice(0, 8)}</span>
                      <Badge className="bg-emerald-100 text-emerald-700">{o.status}</Badge>
                    </div>
                    <p className="text-sm text-gray-600 flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> {o.delivery_address}
                    </p>
                    <p className="text-sm font-medium text-gray-800 mt-1">
                      {(o.currency === 'MAD' ? `${o.total_amount} د.م` : `€${o.total_amount?.toFixed(2)}`)}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
