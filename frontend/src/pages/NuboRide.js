import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import {
  ArrowLeft, MapPin, Navigation, Loader2, Car, Crown, Users, X,
  CheckCircle2, Clock, Search, LocateFixed,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const VEHICLES = {
  economy: { label: 'Economy', icon: Car, desc: 'Coche estándar · hasta 4' },
  comfort: { label: 'Comfort', icon: Crown, desc: 'Más espacio y confort' },
  xl: { label: 'XL / Van', icon: Users, desc: 'Grupos · hasta 6' },
};

const ESTADO_INFO = {
  buscando: { label: 'Buscando conductor…', color: 'bg-amber-100 text-amber-700', step: 1 },
  aceptado: { label: 'Conductor en camino', color: 'bg-blue-100 text-blue-700', step: 2 },
  en_curso: { label: 'Viaje en curso', color: 'bg-emerald-100 text-emerald-700', step: 3 },
  completado: { label: 'Viaje completado', color: 'bg-emerald-100 text-emerald-700', step: 4 },
  cancelado: { label: 'Viaje cancelado', color: 'bg-red-100 text-red-700', step: 0 },
};

const money = (amount, currency) =>
  currency === 'MAD' ? `${(amount ?? 0).toFixed(2)} د.م` : `€${(amount ?? 0).toFixed(2)}`;

export default function NuboRide() {
  const navigate = useNavigate();
  const { user, token } = useContext(AuthContext);
  const authHeaders = useCallback(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);

  const [cities, setCities] = useState([]);
  const [originId, setOriginId] = useState('');
  const [gpsOrigin, setGpsOrigin] = useState(null); // {lat,lng,label}
  const [destId, setDestId] = useState('');
  const [options, setOptions] = useState(null); // estimate options
  const [selectedVehicle, setSelectedVehicle] = useState('economy');
  const [estimating, setEstimating] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [activeRide, setActiveRide] = useState(null);
  const [loadingActive, setLoadingActive] = useState(true);
  const pollRef = useRef(null);

  const originCity = cities.find((c) => c.id === originId);
  const destCity = cities.find((c) => c.id === destId);
  const currency = (gpsOrigin ? 'EUR' : originCity?.country) === 'MA' ? 'MAD' : 'EUR';

  const originPoint = gpsOrigin
    ? gpsOrigin
    : originCity
      ? { lat: originCity.lat, lng: originCity.lng, label: originCity.name }
      : null;
  const destPoint = destCity ? { lat: destCity.lat, lng: destCity.lng, label: destCity.name } : null;

  useEffect(() => {
    axios.get(`${API}/public/cities`).then((res) => {
      setCities(res.data?.cities || res.data || []);
    }).catch(() => {});
  }, []);

  const loadActive = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/rides/active`, authHeaders());
      setActiveRide(res.data?.ride || null);
    } catch (e) { /* noop */ } finally {
      setLoadingActive(false);
    }
  }, [authHeaders]);

  useEffect(() => { loadActive(); }, [loadActive]);

  // Poll active ride while one exists or while searching
  useEffect(() => {
    if (activeRide && ['buscando', 'aceptado', 'en_curso'].includes(activeRide.estado)) {
      pollRef.current = setInterval(loadActive, 5000);
      return () => clearInterval(pollRef.current);
    }
  }, [activeRide, loadActive]);

  const useMyLocation = () => {
    if (!navigator.geolocation) { toast.error('Geolocalización no disponible'); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsOrigin({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: 'Mi ubicación' });
        setOriginId('');
        setOptions(null);
        toast.success('Ubicación detectada');
      },
      () => toast.error('No se pudo obtener tu ubicación'),
      { enableHighAccuracy: true, timeout: 12000 }
    );
  };

  const estimate = async () => {
    if (!originPoint || !destPoint) { toast.error('Elige origen y destino'); return; }
    setEstimating(true);
    setOptions(null);
    try {
      const res = await axios.post(`${API}/rides/estimate`, {
        origin_lat: originPoint.lat, origin_lng: originPoint.lng,
        destination_lat: destPoint.lat, destination_lng: destPoint.lng, currency,
      }, authHeaders());
      setOptions(res.data.options || []);
      setSelectedVehicle('economy');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudo calcular el precio');
    } finally {
      setEstimating(false);
    }
  };

  const requestRide = async () => {
    if (!originPoint || !destPoint) return;
    setRequesting(true);
    try {
      const res = await axios.post(`${API}/rides/request`, {
        origin_lat: originPoint.lat, origin_lng: originPoint.lng, origin_label: originPoint.label,
        destination_lat: destPoint.lat, destination_lng: destPoint.lng, destination_label: destPoint.label,
        vehicle_type: selectedVehicle, city_id: gpsOrigin ? null : originId, currency,
      }, authHeaders());
      setActiveRide(res.data);
      setOptions(null);
      toast.success('¡Viaje solicitado! Buscando conductor…');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudo solicitar el viaje');
    } finally {
      setRequesting(false);
    }
  };

  const cancelRide = async () => {
    if (!activeRide) return;
    try {
      await axios.post(`${API}/rides/${activeRide.id}/cancel`, { reason: 'cliente' }, authHeaders());
      toast.success('Viaje cancelado');
      setActiveRide(null);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudo cancelar');
    }
  };

  const showActive = activeRide && ['buscando', 'aceptado', 'en_curso'].includes(activeRide.estado);

  return (
    <div className="min-h-screen bg-gray-50" data-testid="nubo-ride-page">
      <header className="bg-gradient-to-r from-slate-900 to-emerald-900 text-white px-5 pt-6 pb-10 rounded-b-3xl">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <Button onClick={() => navigate('/dashboard')} size="icon" variant="ghost"
            className="text-white hover:bg-white/10" data-testid="ride-back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <p className="text-xs text-emerald-300/80 font-medium tracking-wide">NUBO EXPRESS</p>
            <h1 className="text-2xl font-bold leading-tight">Nubo Car 🚗</h1>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-5 -mt-6 pb-12 space-y-5">
        {loadingActive ? (
          <Card className="border-0 shadow-lg"><CardContent className="p-10 text-center">
            <Loader2 className="w-7 h-7 mx-auto text-emerald-500 animate-spin" />
          </CardContent></Card>
        ) : showActive ? (
          <ActiveRideCard ride={activeRide} onCancel={cancelRide} />
        ) : (
          <>
            {/* Origin / Destination form */}
            <Card className="border-0 shadow-lg" data-testid="ride-form">
              <CardContent className="p-5 space-y-4">
                <div>
                  <label className="text-xs font-semibold text-gray-500 mb-1.5 block">Origen</label>
                  <div className="flex gap-2">
                    <Select value={originId} onValueChange={(v) => { setOriginId(v); setGpsOrigin(null); setOptions(null); }}>
                      <SelectTrigger className="flex-1" data-testid="ride-origin-select">
                        <SelectValue placeholder={gpsOrigin ? '📍 Mi ubicación' : 'Elige ciudad de origen'} />
                      </SelectTrigger>
                      <SelectContent>
                        {cities.map((c) => (
                          <SelectItem key={c.id} value={c.id} data-testid={`ride-origin-${c.id}`}>
                            {c.name} {c.country === 'MA' ? '🇲🇦' : '🇪🇸'}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button type="button" variant="outline" size="icon" onClick={useMyLocation}
                      title="Usar mi ubicación" data-testid="ride-gps-btn">
                      <LocateFixed className={`w-5 h-5 ${gpsOrigin ? 'text-emerald-600' : 'text-gray-500'}`} />
                    </Button>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-gray-500 mb-1.5 block">Destino</label>
                  <Select value={destId} onValueChange={(v) => { setDestId(v); setOptions(null); }}>
                    <SelectTrigger data-testid="ride-dest-select">
                      <SelectValue placeholder="Elige ciudad de destino" />
                    </SelectTrigger>
                    <SelectContent>
                      {cities.map((c) => (
                        <SelectItem key={c.id} value={c.id} data-testid={`ride-dest-${c.id}`}>
                          {c.name} {c.country === 'MA' ? '🇲🇦' : '🇪🇸'}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Button onClick={estimate} disabled={estimating || !originPoint || !destPoint}
                  className="w-full h-12 bg-slate-900 hover:bg-slate-800 gap-2" data-testid="ride-estimate-btn">
                  {estimating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                  Ver precios
                </Button>
              </CardContent>
            </Card>

            {/* Vehicle options */}
            {options && (
              <div className="space-y-3" data-testid="ride-options">
                <h2 className="text-sm font-semibold text-gray-700 px-1">Elige tu vehículo</h2>
                {options[0]?.distance_km > 80 && (
                  <div className="flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-amber-800" data-testid="ride-intercity-note">
                    <Navigation className="w-4 h-4 mt-0.5 shrink-0" />
                    <p className="text-xs">Viaje interurbano de larga distancia ({options[0].distance_km} km). La tarifa refleja el trayecto completo.</p>
                  </div>
                )}
                {options.map((opt) => {
                  const meta = VEHICLES[opt.vehicle_type] || VEHICLES.economy;
                  const Icon = meta.icon;
                  const active = selectedVehicle === opt.vehicle_type;
                  return (
                    <Card key={opt.vehicle_type} onClick={() => setSelectedVehicle(opt.vehicle_type)}
                      data-testid={`ride-vehicle-${opt.vehicle_type}`}
                      className={`cursor-pointer border-2 transition-all ${active ? 'border-emerald-500 shadow-md' : 'border-transparent shadow-sm'}`}>
                      <CardContent className="p-4 flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${active ? 'bg-emerald-500 text-white' : 'bg-gray-100 text-gray-600'}`}>
                          <Icon className="w-6 h-6" />
                        </div>
                        <div className="flex-1">
                          <p className="font-bold text-gray-900">{meta.label}</p>
                          <p className="text-xs text-gray-500">{meta.desc} · {opt.distance_km} km · ~{opt.eta_mins} min</p>
                        </div>
                        <span className="text-lg font-bold text-emerald-700" data-testid={`ride-price-${opt.vehicle_type}`}>
                          {money(opt.estimated_price, opt.currency)}
                        </span>
                      </CardContent>
                    </Card>
                  );
                })}
                <Button onClick={requestRide} disabled={requesting}
                  className="w-full h-13 py-3 bg-emerald-600 hover:bg-emerald-700 gap-2 text-base" data-testid="ride-request-btn">
                  {requesting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Navigation className="w-5 h-5" />}
                  Pedir {VEHICLES[selectedVehicle].label}
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function ActiveRideCard({ ride, onCancel }) {
  const info = ESTADO_INFO[ride.estado] || ESTADO_INFO.buscando;
  const steps = ['Solicitud', 'Conductor', 'En curso', 'Llegada'];
  return (
    <Card className="border-0 shadow-lg" data-testid="ride-active-card">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <Badge className={info.color} data-testid="ride-active-estado">{info.label}</Badge>
          <span className="text-xs text-gray-400">#{ride.id.slice(0, 8)}</span>
        </div>

        {ride.estado === 'buscando' && (
          <div className="flex items-center gap-3 rounded-xl bg-amber-50 px-4 py-3">
            <Loader2 className="w-5 h-5 text-amber-500 animate-spin" />
            <p className="text-sm text-amber-800">Estamos asignando el conductor más cercano…</p>
          </div>
        )}

        {/* Progress */}
        <div className="flex items-center justify-between">
          {steps.map((s, i) => {
            const done = info.step >= i + 1;
            return (
              <React.Fragment key={s}>
                <div className="flex flex-col items-center gap-1">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${done ? 'bg-emerald-500 text-white' : 'bg-gray-200 text-gray-400'}`}>
                    {done ? <CheckCircle2 className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                  </div>
                  <span className={`text-[10px] ${done ? 'text-emerald-700 font-medium' : 'text-gray-400'}`}>{s}</span>
                </div>
                {i < steps.length - 1 && <div className={`flex-1 h-0.5 mx-1 ${info.step >= i + 2 ? 'bg-emerald-500' : 'bg-gray-200'}`} />}
              </React.Fragment>
            );
          })}
        </div>

        {/* Route */}
        <div className="rounded-xl bg-gray-50 p-4 space-y-2">
          <p className="flex items-center gap-2 text-sm text-gray-700">
            <MapPin className="w-4 h-4 text-emerald-600 shrink-0" /> {ride.origin?.label || 'Origen'}
          </p>
          <p className="flex items-center gap-2 text-sm text-gray-700">
            <Navigation className="w-4 h-4 text-slate-700 shrink-0" /> {ride.destination?.label || 'Destino'}
          </p>
          <div className="flex items-center justify-between pt-1 border-t border-gray-200 mt-1">
            <span className="text-xs text-gray-500">{ride.vehicle_type} · {ride.distance_km} km</span>
            <span className="text-base font-bold text-emerald-700" data-testid="ride-active-price">
              {money(ride.precio_estimado, ride.currency)}
            </span>
          </div>
        </div>

        {ride.estado !== 'en_curso' && (
          <Button onClick={onCancel} variant="outline"
            className="w-full border-red-200 text-red-600 hover:bg-red-50 gap-2" data-testid="ride-cancel-btn">
            <X className="w-4 h-4" /> Cancelar viaje
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
