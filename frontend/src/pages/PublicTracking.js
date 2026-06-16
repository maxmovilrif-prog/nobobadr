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
import { toast } from 'sonner';
import motoIconUrl from '@/assets/icons/moto-bee.png';
import carIconUrl from '@/assets/icons/car-bee.png';
import bikeIconUrl from '@/assets/icons/bike-bee.png';
import truckIconUrl from '@/assets/icons/truck-bee.png';
import { Search, MapPin, Flag, Truck, Clock, Route as RouteIcon, ArrowLeft, Loader2, Share2 } from 'lucide-react';

// 1 MAD = 0.092 EUR (tasa de referencia; se podrá actualizar vía API)
const EXCHANGE_RATE_MAD_EUR = 0.092;
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Mapea el estado del backend a los estados visuales del seguimiento
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
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 })
      .format(amount * EXCHANGE_RATE_MAD_EUR);
  }
  return new Intl.NumberFormat('ar-MA', { style: 'currency', currency: 'MAD', maximumFractionDigits: 2 }).format(amount);
}

const STATUS_CLASS = {
  pending: 'bg-amber-100 text-amber-700',
  assigned: 'bg-blue-100 text-blue-700',
  in_transit: 'bg-emerald-100 text-emerald-700',
  delivered: 'bg-green-100 text-green-700',
};

// Datos de demostración (se conectarán al backend real más adelante)
const DEMO_ORDERS = {
  'ORD-4821': {
    order_id: 'ORD-4821', client_name: 'أحمد الراشدي / Ahmed Rachidi', delivery_status: 'in_transit',
    driver_name: 'Said Mzian', vehicle: 'Mercedes Sprinter • MA-4821-B', vehicle_type: 'truck', price: 850,
    origin: { lat: 35.7595, lng: -5.8340, label_ar: 'طنجة ميد، المغرب', label_es: 'Tánger Med, Marruecos' },
    destination: { lat: 36.5271, lng: -6.2886, label_ar: 'خيريز دي لا فرونتيرا، إسبانيا', label_es: 'Jerez de la Frontera, España' },
    current: { lat: 36.1408, lng: -5.4536 }, updated_at: '2026-06-15T14:22:00Z',
  },
  'ORD-4822': {
    order_id: 'ORD-4822', client_name: 'فاطمة الزهراء / Fátima Zahara', delivery_status: 'assigned',
    driver_name: 'Reda Amine', vehicle: 'Peugeot 208 • MA-7734-C', vehicle_type: 'car', price: 450,
    origin: { lat: 33.5731, lng: -7.5898, label_ar: 'الدار البيضاء، المغرب', label_es: 'Casablanca, Marruecos' },
    destination: { lat: 40.4168, lng: -3.7038, label_ar: 'مدريد، إسبانيا', label_es: 'Madrid, España' },
    current: { lat: 35.7595, lng: -5.8340 }, updated_at: '2026-06-15T13:45:00Z',
  },
  'ORD-4823': {
    order_id: 'ORD-4823', client_name: 'يوسف العلمي / Youssef Alami', delivery_status: 'in_transit',
    driver_name: 'Karim Bennani', vehicle: 'Yamaha NMAX • MA-2231-D', vehicle_type: 'motorcycle', price: 180,
    origin: { lat: 35.5889, lng: -5.3626, label_ar: 'تطوان، المغرب', label_es: 'Tetuán, Marruecos' },
    destination: { lat: 36.0143, lng: -5.6044, label_ar: 'طريفة، إسبانيا', label_es: 'Tarifa, España' },
    current: { lat: 35.9, lng: -5.5 }, updated_at: '2026-06-15T15:10:00Z',
  },
  'ORD-4824': {
    order_id: 'ORD-4824', client_name: 'سلمى بناني / Salma Bennani', delivery_status: 'assigned',
    driver_name: 'Omar Fassi', vehicle: 'Bicicleta urbana • Repartidor', vehicle_type: 'bicycle', price: 90,
    origin: { lat: 35.7595, lng: -5.8340, label_ar: 'طنجة، المغرب', label_es: 'Tánger, Marruecos' },
    destination: { lat: 35.7806, lng: -5.8136, label_ar: 'وسط طنجة، المغرب', label_es: 'Centro de Tánger, Marruecos' },
    current: { lat: 35.77, lng: -5.82 }, updated_at: '2026-06-15T15:30:00Z',
  },
};

// Iconos PNG de marca (la Abeja sobre cada vehículo) según el tipo de vehículo.
const VEHICLE_ICON_URL = {
  motorcycle: motoIconUrl,
  car: carIconUrl,
  bicycle: bikeIconUrl,
  truck: truckIconUrl,
};

// Devuelve el icono del marcador con guarda segura (no construye Size si Maps no cargó).
function getVehicleIcon(vehicleType) {
  if (!window.google?.maps?.Size) return undefined;
  const url = VEHICLE_ICON_URL[vehicleType] || motoIconUrl;
  const sizePx = vehicleType === 'car' || vehicleType === 'truck' ? 46 : 42;
  return { url, scaledSize: new window.google.maps.Size(sizePx, sizePx), anchor: new window.google.maps.Point(sizePx / 2, sizePx / 2) };
}

const containerStyle = { width: '100%', height: '100%', minHeight: '480px' };

// Aísla los fallos de render del mapa de Google (p.ej. APIs no habilitadas) para que
// NO tumben el resto de la página (datos del pedido, botón de compartir, etc.).
class MapErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false }; }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error) { console.error('Map render error (contenido):', error); }
  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

export default function PublicTracking() {
  const navigate = useNavigate();
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.REACT_APP_GOOGLE_MAPS_API_KEY || 'YOUR_API_KEY_HERE',
  });

  const [currency, setCurrency] = useState('MAD');
  const [search, setSearch] = useState('');
  const [order, setOrder] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);
  const [directions, setDirections] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [liveId, setLiveId] = useState(null); // id de pedido real para refresco en vivo
  const mapRef = useRef(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const { t, i18n } = useTranslation();
  const tr = (k) => t(`publicTracking.${k}`);
  const rtl = i18n.language === 'ar';

  const drawRoute = useCallback((orderData) => {
    if (!isLoaded || !orderData || !window.google?.maps?.DirectionsService) return;
    try {
      const service = new window.google.maps.DirectionsService();
      service.route(
        {
          origin: orderData.origin,
          destination: orderData.destination,
          travelMode: window.google.maps.TravelMode.DRIVING,
        },
        (result, status) => {
          if (status === 'OK') {
            setDirections(result);
            const leg = result.routes[0].legs[0];
            setRouteInfo({ distance: leg.distance.text, duration: leg.duration.text });
          } else {
            setDirections(null);
            setRouteInfo(null);
          }
        }
      );
      if (mapRef.current) {
        const bounds = new window.google.maps.LatLngBounds();
        [orderData.origin, orderData.destination, orderData.current].forEach((p) =>
          bounds.extend(new window.google.maps.LatLng(p.lat, p.lng))
        );
        mapRef.current.fitBounds(bounds, 60);
      }
    } catch (err) {
      // El mapa no está totalmente disponible (APIs bloqueadas): seguimos sin ruta
      console.error('drawRoute error:', err);
      setDirections(null);
      setRouteInfo(null);
    }
  }, [isLoaded]);

  // Busca un pedido: primero datos demo (ORD-XXXX), luego pedido real (exprés) por id.
  const lookupOrder = async (rawId) => {
    const raw = (rawId || '').trim();
    if (!raw) return;
    setLoading(true);
    setError('');
    setRouteInfo(null);
    setDirections(null);
    // 1) Pedidos demo (formato ORD-XXXX)
    const demo = DEMO_ORDERS[raw.toUpperCase()];
    if (demo) {
      setLiveId(null);
      setOrder(demo);
      drawRoute(demo);
      setLoading(false);
      return;
    }
    // 2) Pedido real (exprés) por id vía backend público
    try {
      const res = await axios.get(`${API}/public/orders/${encodeURIComponent(raw)}/tracking`);
      const d = res.data;
      if (!d.origin || !d.destination) {
        setError(tr('notFound'));
        setOrder(null);
        setLiveId(null);
        setLoading(false);
        return;
      }
      const priceMad = d.currency === 'EUR' ? (d.price || 0) / EXCHANGE_RATE_MAD_EUR : (d.price || 0);
      const mapped = {
        order_id: d.order_id,
        client_name: '',
        delivery_status: mapTrackingStatus(d.status),
        driver_name: d.driver_name || tr('searchingDriver'),
        vehicle: vehicleLabel(d.driver_vehicle_type),
        vehicle_type: d.driver_vehicle_type || 'motorcycle',
        price: priceMad,
        origin: { lat: d.origin.lat, lng: d.origin.lng, label_es: d.origin.label, label_ar: d.origin.label },
        destination: { lat: d.destination.lat, lng: d.destination.lng, label_es: d.destination.label, label_ar: d.destination.label },
        current: d.driver_location || { lat: d.origin.lat, lng: d.origin.lng },
        updated_at: d.updated_at || new Date().toISOString(),
      };
      setLiveId(d.order_id);
      setOrder(mapped);
      drawRoute(mapped);
    } catch (e) {
      setError(tr('notFound'));
      setOrder(null);
      setLiveId(null);
    } finally {
      setLoading(false);
    }
  };

  // Refresco en vivo: actualiza ubicación del repartidor y estado sin recolocar el mapa
  const refreshLive = useCallback(async (id) => {
    try {
      const res = await axios.get(`${API}/public/orders/${encodeURIComponent(id)}/tracking`);
      const d = res.data;
      setOrder((prev) => prev ? {
        ...prev,
        delivery_status: mapTrackingStatus(d.status),
        driver_name: d.driver_name || prev.driver_name,
        vehicle: d.driver_vehicle_type ? vehicleLabel(d.driver_vehicle_type) : prev.vehicle,
        vehicle_type: d.driver_vehicle_type || prev.vehicle_type,
        current: d.driver_location || prev.current,
        updated_at: d.updated_at || prev.updated_at,
      } : prev);
    } catch (e) { /* noop */ }
  }, []);

  // Sondeo periódico (cada 15s) mientras se sigue un pedido real
  useEffect(() => {
    if (!liveId) return;
    const t = setInterval(() => refreshLive(liveId), 15000);
    return () => clearInterval(t);
  }, [liveId, refreshLive]);

  // Auto-carga si llega ?order=ORD-XXXX (enlace compartido)
  useEffect(() => {
    const qp = searchParams.get('order');
    if (qp) {
      setSearch(qp);
      lookupOrder(qp);
    }
    // eslint-disable-next-line
  }, []);

  // Redibuja la ruta cuando se carga el mapa con un pedido activo
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
    const text = `${tr('shareMessage')} ${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  };

  const statusClass = order ? (STATUS_CLASS[order.delivery_status] || STATUS_CLASS.pending) : '';

  return (
    <div dir={rtl ? 'rtl' : 'ltr'} className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50"
      data-testid="public-tracking-page">
      {/* Header */}
      <header className="glass sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Button data-testid="tracking-back-btn" onClick={() => navigate('/')} variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-1" /> {tr('back')}
            </Button>
            <div>
              <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Truck className="w-5 h-5 text-emerald-600" /> {tr('title')}
              </h1>
              <p className="text-xs text-gray-500">{tr('subtitle')}</p>
            </div>
          </div>
          {/* Switchers: idioma global (i18next) + divisa (página) */}
          <div className="flex items-center gap-2">
            <LanguageSelector variant="outline" />
            <div className="flex items-center rounded-full bg-white border border-gray-200 p-1" data-testid="currency-switch">
              {['MAD', 'EUR'].map((c) => (
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
        {/* Search */}
        <form onSubmit={handleSearch} className="mb-6 max-w-xl">
          <label className="text-sm font-medium text-gray-700">{tr('searchLabel')}</label>
          <div className="flex gap-2 mt-1">
            <Input data-testid="tracking-search-input" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder={tr('searchPlaceholder')} className="font-mono tracking-wide bg-white" />
            <Button data-testid="tracking-search-btn" type="submit" disabled={loading} className="bg-emerald-600 hover:bg-emerald-700">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 mr-1" />}
              {!loading && tr('search')}
            </Button>
          </div>
          {error && <p data-testid="tracking-error" className="text-sm text-red-600 mt-2">{error}</p>}
        </form>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Map */}
          <div className="lg:col-span-2">
            <Card className="border-0 shadow-lg overflow-hidden">
              <CardContent className="p-0 relative" style={{ minHeight: 480 }} data-testid="tracking-map">
                {loadError ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-100 p-6 text-center">
                    <div>
                      <p className="text-red-600 font-semibold mb-1">Error al cargar Google Maps</p>
                      <p className="text-sm text-gray-600">Verifica la clave de API (REACT_APP_GOOGLE_MAPS_API_KEY)</p>
                    </div>
                  </div>
                ) : !isLoaded ? (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-gray-50">
                    <Loader2 className="w-7 h-7 animate-spin text-emerald-600" />
                    <p className="text-sm text-gray-500">{tr('loading')}</p>
                  </div>
                ) : (
                  <MapErrorBoundary fallback={
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-100 p-6 text-center" data-testid="map-fallback">
                      <div>
                        <MapPin className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-600 max-w-xs">{tr('mapUnavailable')}</p>
                      </div>
                    </div>
                  }>
                    <GoogleMap
                      mapContainerStyle={containerStyle}
                      center={{ lat: 35.9, lng: -5.6 }}
                      zoom={6}
                      onLoad={(m) => { mapRef.current = m; }}
                      options={{ streetViewControl: false, mapTypeControl: false, fullscreenControl: true, zoomControl: true }}
                    >
                      {directions && (
                        <DirectionsRenderer directions={directions}
                          options={{ suppressMarkers: true, polylineOptions: { strokeColor: '#10B981', strokeWeight: 4, strokeOpacity: 0.85 } }} />
                      )}
                      {order && (
                        <>
                          <Marker position={order.origin} label={{ text: 'A', color: '#fff', fontWeight: 'bold' }}
                            title={rtl ? order.origin.label_ar : order.origin.label_es} />
                          <Marker position={order.destination} label={{ text: 'B', color: '#fff', fontWeight: 'bold' }}
                            title={rtl ? order.destination.label_ar : order.destination.label_es} />
                          <Marker position={order.current} title={`${order.driver_name} · ${order.vehicle}`}
                            icon={getVehicleIcon(order.vehicle_type)} />
                        </>
                      )}
                    </GoogleMap>
                  </MapErrorBoundary>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-4" data-testid="tracking-sidebar">
            {!order ? (
              <Card className="border-0 shadow-lg">
                <CardContent className="flex flex-col items-center justify-center h-52 gap-3 text-center">
                  <MapPin className="w-8 h-8 text-emerald-400" />
                  <p className="text-sm text-gray-500">{tr('noOrder')}</p>
                </CardContent>
              </Card>
            ) : (
              <>
                <Card className="border-0 shadow-lg">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-emerald-700" data-testid="tracking-order-id">{order.order_id}</span>
                      <Badge className={statusClass} data-testid="tracking-status">{tr(`statuses.${order.delivery_status}`)}</Badge>
                    </div>
                    <p className="text-sm text-gray-600 mt-2">{order.client_name}</p>
                  </CardContent>
                </Card>

                <Button data-testid="tracking-share-btn" onClick={handleShare}
                  className="w-full bg-[#25D366] hover:bg-[#1ebe5b] text-white gap-2">
                  <Share2 className="w-4 h-4" /> {tr('share')}
                </Button>

                <Card className="border-0 shadow-lg">
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-[11px] text-gray-400">{tr('from')}</p>
                        <p className="text-sm font-medium text-gray-800">{rtl ? order.origin.label_ar : order.origin.label_es}</p>
                      </div>
                    </div>
                    <div className="border-l-2 border-dashed border-gray-200 h-3 ml-2" />
                    <div className="flex items-start gap-2">
                      <Flag className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-[11px] text-gray-400">{tr('to')}</p>
                        <p className="text-sm font-medium text-gray-800">{rtl ? order.destination.label_ar : order.destination.label_es}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {routeInfo && (
                  <div className="grid grid-cols-2 gap-3" data-testid="tracking-route-info">
                    <Card className="border-0 shadow-lg">
                      <CardContent className="p-3">
                        <p className="text-[11px] text-gray-400 flex items-center gap-1"><RouteIcon className="w-3 h-3" /> {tr('distance')}</p>
                        <p className="text-base font-semibold text-gray-800">{routeInfo.distance}</p>
                      </CardContent>
                    </Card>
                    <Card className="border-0 shadow-lg">
                      <CardContent className="p-3">
                        <p className="text-[11px] text-gray-400 flex items-center gap-1"><Clock className="w-3 h-3" /> {tr('duration')}</p>
                        <p className="text-base font-semibold text-gray-800">{routeInfo.duration}</p>
                      </CardContent>
                    </Card>
                  </div>
                )}

                <Card className="border-0 shadow-lg">
                  <CardContent className="p-4">
                    <p className="text-[11px] text-gray-400">{tr('cost')}</p>
                    <p className="text-2xl font-bold text-emerald-700" data-testid="tracking-cost-main">
                      {formatCurrency(order.price, currency)}
                    </p>
                    <p className="text-xs text-gray-500">
                      ≈ {formatCurrency(order.price, currency === 'MAD' ? 'EUR' : 'MAD')}
                    </p>
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
                  {tr('lastUpdate')}: {new Date(order.updated_at).toLocaleString(rtl ? 'ar-MA' : 'es-ES')}
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
