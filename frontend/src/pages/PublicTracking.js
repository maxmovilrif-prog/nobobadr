import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { GoogleMap, Marker, DirectionsRenderer, useJsApiLoader } from '@react-google-maps/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import LanguageSelector from '@/components/LanguageSelector';
import { Search, MapPin, Flag, Truck, Clock, Route as RouteIcon, ArrowLeft, Loader2, Share2, QrCode } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';

const EXCHANGE_RATE_MAD_EUR = 0.092;
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const S = {
  title: 'Seguimiento de pedido', subtitle: 'Sigue tu envío en tiempo real, sin registrarte',
  back: 'Volver', searchLabel: 'Introduce tu nº de pedido', searchPlaceholder: 'Ej. ORD-4821 o tu ID de pedido',
  search: 'Buscar', notFound: 'No encontramos ningún pedido con ese número.',
  searchingDriver: 'Buscando repartidor...', loading: 'Cargando mapa...',
  mapUnavailable: 'El mapa no está disponible (clave de Google Maps pendiente). Los datos del pedido sí se muestran.',
  noOrder: 'Busca un pedido para ver su estado y ruta.', from: 'Origen', to: 'Destino',
  distance: 'Distancia', duration: 'Tiempo', cost: 'Coste del envío', share: 'Compartir por WhatsApp',
  shareMessage: 'Sigue mi envío con Nubo Express:', lastUpdate: 'Última actualización',
};
const STATUS_LABEL = { pending: 'Pendiente', assigned: 'Asignado', in_transit: 'En camino', delivered: 'Entregado' };

const mapTrackingStatus = (s) => {
  if (s === 'in_transit') return 'in_transit';
  if (s === 'delivered') return 'delivered';
  if (['accepted', 'preparing', 'ready'].includes(s)) return 'assigned';
  return 'pending';
};
const VEHICLE_LABEL = { motorcycle: 'Moto', car: 'Coche', bicycle: 'Bici', truck: 'Camión' };
const vehicleLabel = (v) => VEHICLE_LABEL[v] || v || '—';

function formatCurrency(amount, currency = 'MAD') {
  if (currency === 'EUR') {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(amount * EXCHANGE_RATE_MAD_EUR);
  }
  return new Intl.NumberFormat('ar-MA', { style: 'currency', currency: 'MAD', maximumFractionDigits: 2 }).format(amount);
}

const STATUS_CLASS = {
  pending: 'bg-amber-100 text-amber-700', assigned: 'bg-blue-100 text-blue-700',
  in_transit: 'bg-emerald-100 text-emerald-700', delivered: 'bg-green-100 text-green-700',
};

const DEMO_ORDERS = {
  'ORD-4821': {
    order_id: 'ORD-4821', client_name: 'Ahmed Rachidi', delivery_status: 'in_transit',
    driver_name: 'Said Mzian', vehicle: 'Mercedes Sprinter • MA-4821-B', vehicle_type: 'truck', price: 850,
    origin: { lat: 35.7595, lng: -5.8340, label: 'Tánger Med, Marruecos' },
    destination: { lat: 36.5271, lng: -6.2886, label: 'Jerez de la Frontera, España' },
    current: { lat: 36.1408, lng: -5.4536 }, updated_at: '2026-06-15T14:22:00Z',
  },
  'ORD-4823': {
    order_id: 'ORD-4823', client_name: 'Youssef Alami', delivery_status: 'in_transit',
    driver_name: 'Karim Bennani', vehicle: 'Yamaha NMAX • MA-2231-D', vehicle_type: 'motorcycle', price: 180,
    origin: { lat: 35.5889, lng: -5.3626, label: 'Tetuán, Marruecos' },
    destination: { lat: 36.0143, lng: -5.6044, label: 'Tarifa, España' },
    current: { lat: 35.9, lng: -5.5 }, updated_at: '2026-06-15T15:10:00Z',
  },
};

const containerStyle = { width: '100%', height: '100%', minHeight: '480px' };

class MapErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false }; }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error) { console.error('Map render error:', error); }
  render() { return this.state.hasError ? this.props.fallback : this.props.children; }
}

export default function PublicTracking() {
  const navigate = useNavigate();
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.REACT_APP_GOOGLE_MAPS_API_KEY || 'YOUR_API_KEY_HERE',
  });

  const { i18n } = useTranslation();
  const rtl = i18n.language === 'ar';

  const [currency, setCurrency] = useState('EUR');
  const [search, setSearch] = useState('');
  const [order, setOrder] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);
  const [directions, setDirections] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [liveId, setLiveId] = useState(null);
  const mapRef = useRef(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const drawRoute = useCallback((orderData) => {
    if (!isLoaded || !orderData || !window.google?.maps?.DirectionsService) return;
    try {
      const service = new window.google.maps.DirectionsService();
      service.route({ origin: orderData.origin, destination: orderData.destination, travelMode: window.google.maps.TravelMode.DRIVING },
        (result, status) => {
          if (status === 'OK') {
            setDirections(result);
            const leg = result.routes[0].legs[0];
            setRouteInfo({ distance: leg.distance.text, duration: leg.duration.text });
          } else { setDirections(null); setRouteInfo(null); }
        });
      if (mapRef.current) {
        const bounds = new window.google.maps.LatLngBounds();
        [orderData.origin, orderData.destination, orderData.current].forEach((p) => bounds.extend(new window.google.maps.LatLng(p.lat, p.lng)));
        mapRef.current.fitBounds(bounds, 60);
      }
    } catch (err) { setDirections(null); setRouteInfo(null); }
  }, [isLoaded]);

  const lookupOrder = async (rawId) => {
    const raw = (rawId || '').trim();
    if (!raw) return;
    setLoading(true); setError(''); setRouteInfo(null); setDirections(null);
    const demo = DEMO_ORDERS[raw.toUpperCase()];
    if (demo) { setLiveId(null); setOrder(demo); drawRoute(demo); setLoading(false); return; }
    try {
      const res = await axios.get(`${API}/public/orders/${encodeURIComponent(raw)}/tracking`);
      const d = res.data;
      if (!d.origin || !d.destination) { setError(S.notFound); setOrder(null); setLiveId(null); setLoading(false); return; }
      const priceMad = d.currency === 'EUR' ? (d.price || 0) / EXCHANGE_RATE_MAD_EUR : (d.price || 0);
      const mapped = {
        order_id: d.order_id, client_name: '', delivery_status: mapTrackingStatus(d.status),
        driver_name: d.driver_name || S.searchingDriver, vehicle: vehicleLabel(d.driver_vehicle_type),
        vehicle_type: d.driver_vehicle_type || 'motorcycle', price: priceMad,
        distance_km: d.distance_km, eta_mins: d.eta_mins, order_type: d.order_type,
        origin: { lat: d.origin.lat, lng: d.origin.lng, label: d.origin.label },
        destination: { lat: d.destination.lat, lng: d.destination.lng, label: d.destination.label },
        current: d.driver_location || { lat: d.origin.lat, lng: d.origin.lng },
        updated_at: d.updated_at || new Date().toISOString(),
      };
      setLiveId(d.order_id); setOrder(mapped); drawRoute(mapped);
    } catch (e) { setError(S.notFound); setOrder(null); setLiveId(null); }
    finally { setLoading(false); }
  };

  const refreshLive = useCallback(async (id) => {
    try {
      const res = await axios.get(`${API}/public/orders/${encodeURIComponent(id)}/tracking`);
      const d = res.data;
      setOrder((prev) => prev ? {
        ...prev, delivery_status: mapTrackingStatus(d.status),
        driver_name: d.driver_name || prev.driver_name,
        vehicle: d.driver_vehicle_type ? vehicleLabel(d.driver_vehicle_type) : prev.vehicle,
        vehicle_type: d.driver_vehicle_type || prev.vehicle_type,
        current: d.driver_location || prev.current, updated_at: d.updated_at || prev.updated_at,
      } : prev);
    } catch (e) { /* noop */ }
  }, []);

  useEffect(() => {
    if (!liveId) return;
    const t = setInterval(() => refreshLive(liveId), 15000);
    return () => clearInterval(t);
  }, [liveId, refreshLive]);

  useEffect(() => {
    const qp = searchParams.get('order');
    if (qp) { setSearch(qp); lookupOrder(qp); }
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    if (order && isLoaded) drawRoute(order);
    // eslint-disable-next-line
  }, [isLoaded]);

  const handleSearch = (e) => {
    e.preventDefault();
    const q = search.trim();
    if (!q) return;
    setSearchParams({ order: q });
    lookupOrder(q);
  };

  const handleShare = () => {
    if (!order) return;
    const url = `${window.location.origin}/track?order=${order.order_id}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(`${S.shareMessage} ${url}`)}`, '_blank');
  };

  const statusClass = order ? (STATUS_CLASS[order.delivery_status] || STATUS_CLASS.pending) : '';

  return (
    <div dir={rtl ? 'rtl' : 'ltr'} className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50" data-testid="public-tracking-page">
      <header className="glass sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Button data-testid="tracking-back-btn" onClick={() => navigate('/')} variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-1" /> {S.back}
            </Button>
            <div>
              <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Truck className="w-5 h-5 text-emerald-600" /> {S.title}
              </h1>
              <p className="text-xs text-gray-500">{S.subtitle}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <LanguageSelector variant="outline" />
            <div className="flex items-center rounded-full bg-white border border-gray-200 p-1" data-testid="currency-switch">
              {['EUR', 'MAD'].map((c) => (
                <button key={c} onClick={() => setCurrency(c)} data-testid={`currency-${c}`}
                  className={`px-3 py-1 text-xs rounded-full transition-colors ${currency === c ? 'bg-emerald-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}>
                  {c === 'MAD' ? 'د.م' : '€'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <form onSubmit={handleSearch} className="mb-6 max-w-xl">
          <label className="text-sm font-medium text-gray-700">{S.searchLabel}</label>
          <div className="flex gap-2 mt-1">
            <Input data-testid="tracking-search-input" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder={S.searchPlaceholder} className="font-mono tracking-wide bg-white" />
            <Button data-testid="tracking-search-btn" type="submit" disabled={loading} className="bg-emerald-600 hover:bg-emerald-700">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 mr-1" />}
              {!loading && S.search}
            </Button>
          </div>
          {error && <p data-testid="tracking-error" className="text-sm text-red-600 mt-2">{error}</p>}
        </form>

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card className="border-0 shadow-lg overflow-hidden">
              <CardContent className="p-0 relative" style={{ minHeight: 480 }} data-testid="tracking-map">
                {loadError ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-100 p-6 text-center">
                    <div>
                      <MapPin className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                      <p className="text-sm text-gray-600">{S.mapUnavailable}</p>
                    </div>
                  </div>
                ) : !isLoaded ? (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-gray-50">
                    <Loader2 className="w-7 h-7 animate-spin text-emerald-600" />
                    <p className="text-sm text-gray-500">{S.loading}</p>
                  </div>
                ) : (
                  <MapErrorBoundary fallback={
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-100 p-6 text-center" data-testid="map-fallback">
                      <div>
                        <MapPin className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-600 max-w-xs">{S.mapUnavailable}</p>
                      </div>
                    </div>
                  }>
                    <GoogleMap mapContainerStyle={containerStyle} center={{ lat: 35.9, lng: -5.6 }} zoom={6}
                      onLoad={(m) => { mapRef.current = m; }}
                      options={{ streetViewControl: false, mapTypeControl: false, fullscreenControl: true, zoomControl: true }}>
                      {directions && (
                        <DirectionsRenderer directions={directions}
                          options={{ suppressMarkers: true, polylineOptions: { strokeColor: '#10B981', strokeWeight: 4, strokeOpacity: 0.85 } }} />
                      )}
                      {order && (
                        <>
                          <Marker position={order.origin} label={{ text: 'A', color: '#fff', fontWeight: 'bold' }} title={order.origin.label} />
                          <Marker position={order.destination} label={{ text: 'B', color: '#fff', fontWeight: 'bold' }} title={order.destination.label} />
                          <Marker position={order.current} title={`${order.driver_name} · ${order.vehicle}`} />
                        </>
                      )}
                    </GoogleMap>
                  </MapErrorBoundary>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4" data-testid="tracking-sidebar">
            {!order ? (
              <Card className="border-0 shadow-lg">
                <CardContent className="flex flex-col items-center justify-center h-52 gap-3 text-center">
                  <MapPin className="w-8 h-8 text-emerald-400" />
                  <p className="text-sm text-gray-500">{S.noOrder}</p>
                  <p className="text-xs text-gray-400">Prueba con <span className="font-mono">ORD-4821</span></p>
                </CardContent>
              </Card>
            ) : (
              <>
                <Card className="border-0 shadow-lg">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-emerald-700" data-testid="tracking-order-id">{order.order_id}</span>
                      <Badge className={statusClass} data-testid="tracking-status">{STATUS_LABEL[order.delivery_status]}</Badge>
                    </div>
                    {order.client_name && <p className="text-sm text-gray-600 mt-2">{order.client_name}</p>}
                  </CardContent>
                </Card>

                <Button data-testid="tracking-share-btn" onClick={handleShare} className="w-full bg-[#25D366] hover:bg-[#1ebe5b] text-white gap-2">
                  <Share2 className="w-4 h-4" /> {S.share}
                </Button>

                <Card className="border-0 shadow-lg" data-testid="tracking-qr-card">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shrink-0">
                      <QRCodeCanvas
                        data-testid="tracking-qr-code"
                        value={`${window.location.origin}/track?order=${order.order_id}`}
                        size={92}
                        fgColor="#047857"
                        level="M"
                        includeMargin={false}
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-800 flex items-center gap-1">
                        <QrCode className="w-4 h-4 text-emerald-600" /> Escanea para seguir
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        Apunta con la cámara del móvil para abrir el seguimiento en vivo de este pedido.
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                      <div><p className="text-[11px] text-gray-400">{S.from}</p>
                        <p className="text-sm font-medium text-gray-800">{order.origin.label}</p></div>
                    </div>
                    <div className="border-l-2 border-dashed border-gray-200 h-3 ml-2" />
                    <div className="flex items-start gap-2">
                      <Flag className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                      <div><p className="text-[11px] text-gray-400">{S.to}</p>
                        <p className="text-sm font-medium text-gray-800">{order.destination.label}</p></div>
                    </div>
                  </CardContent>
                </Card>

                {routeInfo && (
                  <div className="grid grid-cols-2 gap-3" data-testid="tracking-route-info">
                    <Card className="border-0 shadow-lg"><CardContent className="p-3">
                      <p className="text-[11px] text-gray-400 flex items-center gap-1"><RouteIcon className="w-3 h-3" /> {S.distance}</p>
                      <p className="text-base font-semibold text-gray-800">{routeInfo.distance}</p></CardContent></Card>
                    <Card className="border-0 shadow-lg"><CardContent className="p-3">
                      <p className="text-[11px] text-gray-400 flex items-center gap-1"><Clock className="w-3 h-3" /> {S.duration}</p>
                      <p className="text-base font-semibold text-gray-800">{routeInfo.duration}</p></CardContent></Card>
                  </div>
                )}

                <Card className="border-0 shadow-lg" data-testid="tracking-cost-card">
                  <CardContent className="p-4">
                    <p className="text-[11px] text-gray-400">{S.cost}</p>
                    <p className="text-2xl font-bold text-emerald-700" data-testid="tracking-cost-main">{formatCurrency(order.price, currency)}</p>
                    <p className="text-xs text-gray-500" data-testid="tracking-cost-alt">≈ {formatCurrency(order.price, currency === 'MAD' ? 'EUR' : 'MAD')}</p>
                    {order.distance_km != null && (
                      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between" data-testid="tracking-distance-breakdown">
                        <span className="text-xs text-gray-400 flex items-center gap-1"><RouteIcon className="w-3 h-3" /> {S.distance} (tarifa)</span>
                        <span className="text-sm font-semibold text-gray-700">{order.distance_km} km</span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-emerald-600 text-white flex items-center justify-center font-semibold shrink-0">
                      {order.driver_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{order.driver_name}</p>
                      <p className="text-xs text-gray-500 truncate">{order.vehicle}</p>
                    </div>
                    <Badge className="ml-auto bg-emerald-100 text-emerald-700 gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> LIVE
                    </Badge>
                  </CardContent>
                </Card>

                <p className="text-xs text-gray-400 text-center">
                  {S.lastUpdate}: {new Date(order.updated_at).toLocaleString('es-ES')}
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
