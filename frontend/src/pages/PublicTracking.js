import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { GoogleMap, Marker, DirectionsRenderer, useJsApiLoader } from '@react-google-maps/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import LanguageSelector from '@/components/LanguageSelector';
import { Search, MapPin, Flag, Truck, Clock, Route as RouteIcon, ArrowLeft, Loader2 } from 'lucide-react';

// 1 MAD = 0.092 EUR (tasa de referencia; se podrá actualizar vía API)
const EXCHANGE_RATE_MAD_EUR = 0.092;

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
    driver_name: 'Said Mzian', vehicle: 'Mercedes Sprinter • MA-4821-B', price: 850,
    origin: { lat: 35.7595, lng: -5.8340, label_ar: 'طنجة ميد، المغرب', label_es: 'Tánger Med, Marruecos' },
    destination: { lat: 36.5271, lng: -6.2886, label_ar: 'خيريز دي لا فرونتيرا، إسبانيا', label_es: 'Jerez de la Frontera, España' },
    current: { lat: 36.1408, lng: -5.4536 }, updated_at: '2026-06-15T14:22:00Z',
  },
  'ORD-4822': {
    order_id: 'ORD-4822', client_name: 'فاطمة الزهراء / Fátima Zahara', delivery_status: 'assigned',
    driver_name: 'Reda Amine', vehicle: 'Renault Master • MA-7734-C', price: 450,
    origin: { lat: 33.5731, lng: -7.5898, label_ar: 'الدار البيضاء، المغرب', label_es: 'Casablanca, Marruecos' },
    destination: { lat: 40.4168, lng: -3.7038, label_ar: 'مدريد، إسبانيا', label_es: 'Madrid, España' },
    current: { lat: 35.7595, lng: -5.8340 }, updated_at: '2026-06-15T13:45:00Z',
  },
};

const BEE_MARKER_SVG = encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="40" height="40">
    <circle cx="20" cy="20" r="18" fill="#10B981" opacity="0.2"/>
    <circle cx="20" cy="20" r="11" fill="#059669"/>
    <circle cx="20" cy="20" r="4" fill="#ffffff"/>
  </svg>`
);
const BEE_MARKER_URL = `data:image/svg+xml;charset=UTF-8,${BEE_MARKER_SVG}`;

const containerStyle = { width: '100%', height: '100%', minHeight: '480px' };

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
  const mapRef = useRef(null);

  const { t, i18n } = useTranslation();
  const tr = (k) => t(`publicTracking.${k}`);
  const rtl = i18n.language === 'ar';

  const drawRoute = useCallback((orderData) => {
    if (!isLoaded || !orderData) return;
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
  }, [isLoaded]);

  // Redibuja la ruta cuando cambia el idioma o se carga el mapa con un pedido activo
  useEffect(() => {
    if (order && isLoaded) drawRoute(order);
    // eslint-disable-next-line
  }, [isLoaded]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!search.trim()) return;
    setLoading(true);
    setError('');
    setRouteInfo(null);
    setDirections(null);
    // Simula latencia de red (se reemplazará por la llamada real al backend)
    await new Promise((r) => setTimeout(r, 600));
    const found = DEMO_ORDERS[search.trim().toUpperCase()];
    if (!found) {
      setError(tr('notFound'));
      setOrder(null);
    } else {
      setOrder(found);
      drawRoute(found);
    }
    setLoading(false);
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
                        <Marker position={order.current} title={order.driver_name}
                          icon={isLoaded ? { url: BEE_MARKER_URL, scaledSize: new window.google.maps.Size(40, 40), anchor: new window.google.maps.Point(20, 20) } : undefined} />
                      </>
                    )}
                  </GoogleMap>
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
