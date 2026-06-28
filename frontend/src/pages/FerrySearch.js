import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { ArrowLeft, Ship, MapPin, Flag, Calendar, Users, Car, Loader2, Clock, ArrowRightLeft, ExternalLink } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const VEHICLE_OPTIONS = [
  { value: '', label: 'Sin vehículo' },
  { value: 'car', label: 'Coche' },
  { value: 'motorcycle', label: 'Moto' },
  { value: 'van', label: 'Furgoneta' },
  { value: 'camper', label: 'Autocaravana' },
];

const COUNTRY_LABEL = { ES: '🇪🇸 España', MA: '🇲🇦 Marruecos', IT: '🇮🇹 Italia' };

export default function FerrySearch() {
  const navigate = useNavigate();
  const [ports, setPorts] = useState([]);
  const [originCode, setOriginCode] = useState('');
  const [destCode, setDestCode] = useState('');
  const [departDate, setDepartDate] = useState('');
  const [adults, setAdults] = useState(1);
  const [children, setChildren] = useState(0);
  const [vehicle, setVehicle] = useState('');
  const [loading, setLoading] = useState(false);
  const [offers, setOffers] = useState(null);
  const [isMock, setIsMock] = useState(false);
  const [redirectingId, setRedirectingId] = useState(null);

  useEffect(() => {
    axios.get(`${API}/bookings/ferries/ports`)
      .then((res) => setPorts(res.data.ports || []))
      .catch(() => setPorts([]));
  }, []);

  const grouped = useMemo(() => {
    const g = {};
    ports.forEach((p) => { (g[p.country] = g[p.country] || []).push(p); });
    return g;
  }, [ports]);

  const portName = (code) => ports.find((p) => p.code === code)?.name || code;

  const buildQuery = () => ({
    origin_code: originCode,
    destination_code: destCode,
    depart_date: departDate,
    passengers: { adults: Number(adults), children: Number(children), vehicle: vehicle || null },
  });

  const handleSearch = async () => {
    if (!originCode || !destCode) { toast.error('Selecciona puerto de origen y destino'); return; }
    if (originCode === destCode) { toast.error('El origen y el destino no pueden ser iguales'); return; }
    if (!departDate) { toast.error('Selecciona la fecha de salida'); return; }
    setLoading(true);
    setOffers(null);
    try {
      const res = await axios.post(`${API}/bookings/ferries/search`, buildQuery());
      setOffers(res.data.offers || []);
      setIsMock(!res.data.configured);
    } catch (e) {
      toast.error('No se pudo buscar travesías. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const handleReserve = async (offer, idx) => {
    setRedirectingId(idx);
    try {
      const res = await axios.post(`${API}/bookings/ferries/redirect`, buildQuery());
      const url = res.data.deeplink || offer.deeplink;
      if (url) window.open(url, '_blank', 'noopener');
    } catch (e) {
      const url = offer.deeplink;
      if (url) window.open(url, '_blank', 'noopener');
      else toast.error('No se pudo abrir la reserva');
    } finally {
      setRedirectingId(null);
    }
  };

  const fmtTime = (iso) => { try { return new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }); } catch { return '—'; } };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="ferry-search-page">
      {/* Header */}
      <div className="bg-gradient-to-r from-sky-700 to-cyan-600 text-white">
        <div className="max-w-5xl mx-auto px-4 py-5 flex items-center gap-3">
          <button onClick={() => navigate('/')} data-testid="ferry-back-btn" className="p-2 rounded-full hover:bg-white/15 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <Ship className="w-7 h-7" />
          <div>
            <h1 className="text-xl font-bold leading-tight">Reserva tu Ferry</h1>
            <p className="text-sm text-white/80">Estrecho de Gibraltar · España ⇄ Marruecos</p>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Search form */}
        <Card className="border-0 shadow-lg">
          <CardContent className="p-5 space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><MapPin className="w-4 h-4 text-sky-600" /> Origen</label>
                <select data-testid="ferry-origin-select" value={originCode} onChange={(e) => setOriginCode(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-sky-400 outline-none">
                  <option value="">Selecciona puerto…</option>
                  {Object.keys(grouped).map((c) => (
                    <optgroup key={c} label={COUNTRY_LABEL[c] || c}>
                      {grouped[c].map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
                    </optgroup>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><Flag className="w-4 h-4 text-cyan-600" /> Destino</label>
                <select data-testid="ferry-dest-select" value={destCode} onChange={(e) => setDestCode(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-sky-400 outline-none">
                  <option value="">Selecciona puerto…</option>
                  {Object.keys(grouped).map((c) => (
                    <optgroup key={c} label={COUNTRY_LABEL[c] || c}>
                      {grouped[c].map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
                    </optgroup>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><Calendar className="w-4 h-4 text-sky-600" /> Salida</label>
                <input type="date" data-testid="ferry-date-input" value={departDate} onChange={(e) => setDepartDate(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-sky-400 outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><Users className="w-4 h-4 text-sky-600" /> Adultos</label>
                <input type="number" min="1" data-testid="ferry-adults-input" value={adults} onChange={(e) => setAdults(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-sky-400 outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><Users className="w-4 h-4 text-gray-400" /> Niños</label>
                <input type="number" min="0" data-testid="ferry-children-input" value={children} onChange={(e) => setChildren(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-sky-400 outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600 flex items-center gap-1 mb-1"><Car className="w-4 h-4 text-sky-600" /> Vehículo</label>
                <select data-testid="ferry-vehicle-select" value={vehicle} onChange={(e) => setVehicle(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-sky-400 outline-none">
                  {VEHICLE_OPTIONS.map((v) => <option key={v.value} value={v.value}>{v.label}</option>)}
                </select>
              </div>
            </div>

            <Button onClick={handleSearch} disabled={loading} data-testid="ferry-search-btn"
              className="w-full bg-sky-600 hover:bg-sky-700 gap-2 h-11 text-base">
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Ship className="w-5 h-5" />}
              Buscar travesías
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        {offers !== null && (
          <div className="space-y-3" data-testid="ferry-results">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-base font-semibold text-gray-700 flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-sky-600" />
                {portName(originCode)} → {portName(destCode)}
                <Badge className="bg-sky-100 text-sky-700">{offers.length} resultados</Badge>
              </h2>
              {isMock && (
                <Badge className="bg-amber-100 text-amber-700" data-testid="ferry-mock-badge">Datos de ejemplo · proveedor en pruebas</Badge>
              )}
            </div>

            {offers.length === 0 ? (
              <p className="text-sm text-gray-400 py-6 text-center">No hay travesías para esa búsqueda.</p>
            ) : offers.map((o, idx) => (
              <Card key={idx} data-testid={`ferry-offer-${idx}`} className="border-0 shadow-sm hover:shadow-md transition-shadow">
                <CardContent className="p-4 flex items-center justify-between flex-wrap gap-4">
                  <div className="space-y-1">
                    <p className="font-semibold text-gray-800">{o.operator}</p>
                    <p className="text-sm text-gray-600 flex items-center gap-2">
                      <span className="font-medium">{fmtTime(o.depart_at)}</span>
                      <ArrowRightLeft className="w-3 h-3 text-gray-400" />
                      <span className="font-medium">{fmtTime(o.arrive_at)}</span>
                      {o.duration_mins && <span className="flex items-center gap-1 text-gray-400 text-xs"><Clock className="w-3 h-3" /> {o.duration_mins} min</span>}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-xs text-gray-400">desde</p>
                      <p className="text-lg font-bold text-sky-700">{o.price_from} {o.currency}</p>
                    </div>
                    <Button onClick={() => handleReserve(o, idx)} disabled={redirectingId === idx}
                      data-testid={`ferry-reserve-${idx}`}
                      className="bg-cyan-600 hover:bg-cyan-700 gap-2">
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
