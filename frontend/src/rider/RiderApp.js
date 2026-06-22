import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { ScanLine, LogOut, MapPin, Package, Power, Loader2, Bike, Car, Truck, Zap, ShieldAlert, Camera, X, Banknote, Route, Navigation, CheckCircle2, Play, Flag } from 'lucide-react';
import { Html5Qrcode } from 'html5-qrcode';

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
  const [rideData, setRideData] = useState({ ride: null, available: [] });
  const [rideBusy, setRideBusy] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [scanning, setScanning] = useState(false);
  const watchIdRef = useRef(null);
  const scannerRef = useRef(null);

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
    } catch (e) { console.error('Error cargando pedidos del rider', e); }
  }, [authHeaders]);

  useEffect(() => {
    if (rider) loadOrders();
  }, [rider, loadOrders]);

  const loadRides = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/rides/active`, authHeaders());
      setRideData({ ride: res.data?.ride || null, available: res.data?.available || [] });
    } catch (e) { console.error('Error cargando viajes Nubo Ride', e); }
  }, [authHeaders]);

  useEffect(() => {
    if (!rider) return;
    loadRides();
    const t = setInterval(loadRides, 8000);
    return () => clearInterval(t);
  }, [rider, loadRides]);

  const acceptRide = async (rideId) => {
    setRideBusy(true);
    try {
      await axios.post(`${API}/rides/accept`, { ride_id: rideId }, authHeaders());
      toast.success('¡Viaje aceptado!');
      await loadRides();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudo aceptar');
      await loadRides();
    } finally { setRideBusy(false); }
  };

  const rideAction = async (rideId, action, okMsg) => {
    setRideBusy(true);
    try {
      await axios.post(`${API}/rides/${rideId}/${action}`, {}, authHeaders());
      toast.success(okMsg);
      await loadRides();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error');
    } finally { setRideBusy(false); }
  };

  const activateWithCode = async (rawCode) => {
    const c = (rawCode || '').trim().toUpperCase();
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

  const handleActivate = async (e) => {
    e.preventDefault();
    await activateWithCode(code);
  };

  const stopScan = useCallback(async () => {
    if (scannerRef.current) {
      try { await scannerRef.current.stop(); await scannerRef.current.clear(); } catch (e) { console.debug('Scanner ya detenido', e); }
      scannerRef.current = null;
    }
    setScanning(false);
  }, []);

  const startScan = () => {
    setScanning(true);
    setTimeout(async () => {
      try {
        const html5 = new Html5Qrcode('qr-reader');
        scannerRef.current = html5;
        await html5.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: 220 },
          async (decodedText) => {
            await stopScan();
            setCode(decodedText.trim().toUpperCase());
            activateWithCode(decodedText);
          },
          () => {}
        );
      } catch (e) {
        toast.error('No se pudo abrir la cámara. Escribe el código manualmente.');
        setScanning(false);
      }
    }, 150);
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
    axios.post(`${API}/rider/location`, { lat, lng }, authHeaders()).catch((e) => console.warn('No se pudo enviar ubicación', e));
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

  useEffect(() => () => { stopSharing(); stopScan(); }, [stopScan]);

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
            <div className="flex items-center gap-3 text-white/30 text-xs">
              <div className="flex-1 h-px bg-white/15" /> o <div className="flex-1 h-px bg-white/15" />
            </div>
            <Button data-testid="rider-scan-btn" type="button" onClick={startScan} variant="outline"
              className="w-full h-12 bg-transparent border-white/20 text-white hover:bg-white/10 gap-2">
              <Camera className="w-5 h-5" /> Escanear QR con la cámara
            </Button>
          </form>

          {scanning && (
            <div className="fixed inset-0 z-[60] bg-black/95 flex flex-col items-center justify-center p-6" data-testid="rider-scanner">
              <p className="text-white text-sm mb-4">Apunta la cámara al código QR</p>
              <div id="qr-reader" className="w-full max-w-xs rounded-xl overflow-hidden bg-black" />
              <Button data-testid="rider-scan-cancel" onClick={stopScan} variant="outline"
                className="mt-6 bg-transparent border-white/30 text-white hover:bg-white/10 gap-2">
                <X className="w-4 h-4" /> Cancelar
              </Button>
            </div>
          )}
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

        {/* Nubo Ride — viajes de pasajeros */}
        <div data-testid="rider-rides-section">
          <h2 className="text-sm font-semibold text-gray-700 mb-2 px-1 flex items-center gap-1.5">
            <Car className="w-4 h-4 text-emerald-600" /> Nubo Car · Viajes
          </h2>

          {rideData.ride ? (
            <Card className="border-0 shadow-md ring-1 ring-emerald-200" data-testid="rider-active-ride">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-gray-900">Viaje #{rideData.ride.id.slice(0, 8)}</span>
                  <Badge className={rideData.ride.estado === 'en_curso' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}>
                    {rideData.ride.estado === 'en_curso' ? 'En curso' : 'Aceptado'}
                  </Badge>
                </div>
                <p className="text-sm text-gray-700 flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-emerald-600" />{rideData.ride.origin?.label || 'Origen'}</p>
                <p className="text-sm text-gray-700 flex items-center gap-1.5"><Navigation className="w-3.5 h-3.5 text-slate-700" />{rideData.ride.destination?.label || 'Destino'}</p>
                <div className="mt-3 flex items-center justify-between rounded-xl bg-emerald-50 px-3 py-2">
                  <span className="text-xs text-gray-500">{rideData.ride.vehicle_type} · {rideData.ride.distance_km} km</span>
                  <span className="text-lg font-bold text-emerald-700" data-testid="rider-ride-price">
                    {rideData.ride.currency === 'MAD' ? `${(rideData.ride.precio_estimado ?? 0).toFixed(2)} د.م` : `€${(rideData.ride.precio_estimado ?? 0).toFixed(2)}`}
                  </span>
                </div>
                {rideData.ride.estado === 'aceptado' ? (
                  <Button onClick={() => rideAction(rideData.ride.id, 'start', 'Viaje iniciado')} disabled={rideBusy}
                    className="w-full mt-3 bg-emerald-600 hover:bg-emerald-700 gap-2" data-testid="rider-ride-start">
                    {rideBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Iniciar viaje
                  </Button>
                ) : (
                  <Button onClick={() => rideAction(rideData.ride.id, 'complete', 'Viaje completado')} disabled={rideBusy}
                    className="w-full mt-3 bg-slate-900 hover:bg-slate-800 gap-2" data-testid="rider-ride-complete">
                    {rideBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Flag className="w-4 h-4" />} Completar viaje
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : rideData.available.length === 0 ? (
            <Card className="border-0 shadow-sm">
              <CardContent className="p-6 text-center text-gray-400">
                <Car className="w-9 h-9 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">No hay solicitudes de viaje ahora.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {rideData.available.map((r) => (
                <Card key={r.id} data-testid={`rider-available-ride-${r.id}`} className="border-0 shadow-sm">
                  <CardContent className="p-4">
                    <p className="text-sm text-gray-700 flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-emerald-600" />{r.origin?.label || 'Origen'}</p>
                    <p className="text-sm text-gray-700 flex items-center gap-1.5"><Navigation className="w-3.5 h-3.5 text-slate-700" />{r.destination?.label || 'Destino'}</p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-xs text-gray-500 flex items-center gap-1"><Route className="w-3 h-3" />{r.vehicle_type} · {r.distance_km} km · ~{r.eta_mins} min</span>
                      <span className="text-base font-bold text-emerald-700">
                        {r.currency === 'MAD' ? `${(r.precio_estimado ?? 0).toFixed(2)} د.م` : `€${(r.precio_estimado ?? 0).toFixed(2)}`}
                      </span>
                    </div>
                    <Button onClick={() => acceptRide(r.id)} disabled={rideBusy}
                      className="w-full mt-3 bg-emerald-600 hover:bg-emerald-700 gap-2" data-testid={`rider-accept-ride-${r.id}`}>
                      {rideBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Aceptar viaje
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

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
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-gray-900">#{o.id.slice(0, 8)}</span>
                      <Badge className="bg-emerald-100 text-emerald-700">{o.status}</Badge>
                    </div>
                    <p className="text-sm text-gray-600 flex items-start gap-1">
                      <MapPin className="w-3.5 h-3.5 mt-0.5 text-emerald-600 shrink-0" />
                      <span>{o.origin_name ? `${o.origin_name} → ` : ''}{o.destination_name || o.delivery_address}</span>
                    </p>
                    {/* Tarifa de entrega — transparencia financiera */}
                    <div className="mt-3 flex items-center justify-between rounded-xl bg-emerald-50 px-3 py-2">
                      <div className="flex items-center gap-2">
                        <Banknote className="w-4 h-4 text-emerald-600" />
                        <span className="text-xs text-gray-500">Tarifa de entrega</span>
                      </div>
                      <span className="text-lg font-bold text-emerald-700" data-testid={`rider-order-price-${o.id}`}>
                        {o.currency === 'MAD' ? `${(o.total_amount ?? 0).toFixed(2)} د.م` : `€${(o.total_amount ?? 0).toFixed(2)}`}
                      </span>
                    </div>
                    {o.distance_km != null && (
                      <p className="text-xs text-gray-500 mt-1.5 flex items-center gap-1" data-testid={`rider-order-distance-${o.id}`}>
                        <Route className="w-3 h-3" /> {o.distance_km} km{o.eta_mins != null ? ` · ~${o.eta_mins} min` : ''}
                      </p>
                    )}
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
