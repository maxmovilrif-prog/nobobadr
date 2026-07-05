import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { ArrowLeft, BedDouble, MapPin, Calendar, Users, Loader2, Star, ExternalLink } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COUNTRY_LABEL = { ES: '🇪🇸 España', MA: '🇲🇦 Marruecos' };

export default function HotelSearch() {
  const navigate = useNavigate();
  const [destinations, setDestinations] = useState([]);
  const [destCode, setDestCode] = useState('');
  const [checkin, setCheckin] = useState('');
  const [checkout, setCheckout] = useState('');
  const [adults, setAdults] = useState(2);
  const [rooms, setRooms] = useState(1);
  const [loading, setLoading] = useState(false);
  const [offers, setOffers] = useState(null);
  const [isMock, setIsMock] = useState(false);
  const [redirectingId, setRedirectingId] = useState(null);

  useEffect(() => {
    axios.get(`${API}/bookings/hotels/destinations`)
      .then((res) => setDestinations(res.data.destinations || []))
      .catch(() => setDestinations([]));
  }, []);

  const grouped = useMemo(() => {
    const g = {};
    destinations.forEach((d) => { (g[d.country] = g[d.country] || []).push(d); });
    return g;
  }, [destinations]);

  const destName = (code) => destinations.find((d) => d.code === code)?.name || code;

  const buildQuery = () => ({
    destination_code: destCode,
    checkin,
    checkout,
    guests: { adults: Number(adults), children: 0, rooms: Number(rooms) },
  });

  const handleSearch = async () => {
    if (!destCode) { toast.error('Selecciona un destino'); return; }
    if (!checkin || !checkout) { toast.error('Selecciona las fechas de entrada y salida'); return; }
    if (checkout <= checkin) { toast.error('La salida debe ser posterior a la entrada'); return; }
    setLoading(true);
    setOffers(null);
    try {
      const res = await axios.post(`${API}/bookings/hotels/search`, buildQuery());
      setOffers(res.data.offers || []);
      setIsMock(!res.data.configured);
    } catch (e) {
      toast.error('No se pudo buscar hoteles. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const handleReserve = async (offer, idx) => {
    setRedirectingId(idx);
    try {
      const res = await axios.post(`${API}/bookings/hotels/redirect`, buildQuery());
      const url = res.data.deeplink || offer.deeplink;
      if (url) window.open(url, '_blank', 'noopener');
    } catch (e) {
      if (offer.deeplink) window.open(offer.deeplink, '_blank', 'noopener');
      else toast.error('No se pudo abrir la reserva');
    } finally {
      setRedirectingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="hotel-search-page">
      <div className="bg-gradient-to-r from-amber-600 to-orange-500 text-white">
        <div className="max-w-5xl mx-auto px-4 py-5 flex items-center gap-3">
          <button onClick={() => navigate('/')} data-testid="hotel-back-btn" className="p-2 rounded-full hover:bg-white/15 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <BedDouble className="w-7 h-7" />
          <div>
            <h1 className="text-xl font-bold leading-tight">Reserva tu Hotel</h1>
            <p className="text-sm text-white/80">Marruecos y España · mejores precios</p>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        <Card className="border-0 shadow-lg">
          <CardContent className="p-5 space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><MapPin className="w-4 h-4 text-amber-600" /> Destino</label>
              <select data-testid="hotel-dest-select" value={destCode} onChange={(e) => setDestCode(e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-amber-400 outline-none">
                <option value="">Selecciona destino…</option>
                {Object.keys(grouped).map((c) => (
                  <optgroup key={c} label={COUNTRY_LABEL[c] || c}>
                    {grouped[c].map((d) => <option key={d.code} value={d.code}>{d.name}</option>)}
                  </optgroup>
                ))}
              </select>
            </div>

            <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><Calendar className="w-4 h-4 text-amber-600" /> Entrada</label>
                <input type="date" data-testid="hotel-checkin-input" value={checkin} onChange={(e) => setCheckin(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-amber-400 outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><Calendar className="w-4 h-4 text-amber-600" /> Salida</label>
                <input type="date" data-testid="hotel-checkout-input" value={checkout} onChange={(e) => setCheckout(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-amber-400 outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><Users className="w-4 h-4 text-amber-600" /> Huéspedes</label>
                <input type="number" min="1" data-testid="hotel-adults-input" value={adults} onChange={(e) => setAdults(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-amber-400 outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><BedDouble className="w-4 h-4 text-amber-600" /> Habitaciones</label>
                <input type="number" min="1" data-testid="hotel-rooms-input" value={rooms} onChange={(e) => setRooms(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-amber-400 outline-none" />
              </div>
            </div>

            <Button onClick={handleSearch} disabled={loading} data-testid="hotel-search-btn"
              className="w-full bg-amber-600 hover:bg-amber-700 gap-2 h-11 text-base">
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <BedDouble className="w-5 h-5" />}
              Buscar hoteles
            </Button>
          </CardContent>
        </Card>

        {offers !== null && (
          <div className="space-y-3" data-testid="hotel-results">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-base font-semibold text-gray-700 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-amber-600" /> {destName(destCode)}
                <Badge className="bg-amber-100 text-amber-700">{offers.length} resultados</Badge>
              </h2>
              {isMock && (
                <Badge className="bg-amber-100 text-amber-700" data-testid="hotel-mock-badge">Datos de ejemplo · proveedor en pruebas</Badge>
              )}
            </div>

            {offers.length === 0 ? (
              <p className="text-sm text-gray-400 py-6 text-center">No hay hoteles para esa búsqueda.</p>
            ) : offers.map((o, idx) => (
              <Card key={idx} data-testid={`hotel-offer-${idx}`} className="border-0 shadow-sm hover:shadow-md transition-shadow">
                <CardContent className="p-4 flex items-center justify-between flex-wrap gap-4">
                  <div className="space-y-1">
                    <p className="font-semibold text-gray-800 flex items-center gap-2">
                      {o.name}
                      {o.stars && <span className="flex items-center text-amber-500">{Array.from({ length: o.stars }).map((_, i) => <Star key={i} className="w-3 h-3 fill-amber-400" />)}</span>}
                    </p>
                    {o.review_score && <p className="text-sm text-gray-500">Puntuación: <span className="font-medium text-emerald-600">{o.review_score}</span>/10</p>}
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-xs text-gray-400">desde / noche</p>
                      <p className="text-lg font-bold text-amber-700">{o.price_per_night} {o.currency}</p>
                    </div>
                    <Button onClick={() => handleReserve(o, idx)} disabled={redirectingId === idx}
                      data-testid={`hotel-reserve-${idx}`}
                      className="bg-orange-500 hover:bg-orange-600 gap-2">
                      {redirectingId === idx ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}
                      Reservar
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
