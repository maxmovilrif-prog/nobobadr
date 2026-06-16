import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import LanguageSelector from '@/components/LanguageSelector';
import motoIconUrl from '@/assets/icons/moto-bee.png';
import carIconUrl from '@/assets/icons/car-bee.png';
import bikeIconUrl from '@/assets/icons/bike-bee.png';
import { ArrowLeft, MapPin, Flag, Clock, Route as RouteIcon, Calculator, Loader2, PackageCheck } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const VEHICLES = [
  { type: 'motorcycle', icon: motoIconUrl },
  { type: 'car', icon: carIconUrl },
  { type: 'bicycle', icon: bikeIconUrl },
];

export default function DeliveryQuote() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const tr = (k) => t(`deliveryQuote.${k}`);
  const rtl = i18n.language === 'ar';

  const [cities, setCities] = useState([]);
  const [originId, setOriginId] = useState('');
  const [destId, setDestId] = useState('');
  const [vehicle, setVehicle] = useState('motorcycle');
  const [currency, setCurrency] = useState('EUR');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    axios.get(`${API}/public/cities`)
      .then((res) => setCities(res.data.cities || []))
      .catch(() => setCities([]));
  }, []);

  const grouped = {
    ES: cities.filter((c) => c.country === 'ES'),
    MA: cities.filter((c) => c.country === 'MA'),
  };

  const handleCalculate = async () => {
    setError('');
    setResult(null);
    if (!originId || !destId) { setError(tr('selectOrigin')); return; }
    if (originId === destId) { setError(tr('sameError')); return; }
    const origin = cities.find((c) => c.id === originId);
    const dest = cities.find((c) => c.id === destId);
    setLoading(true);
    try {
      const res = await axios.post(`${API}/v1/calculate-delivery`, {
        origin_lat: origin.lat, origin_lng: origin.lng,
        destination_lat: dest.lat, destination_lng: dest.lng,
        vehicle_type: vehicle, currency,
      });
      setResult(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || tr('genericError'));
    } finally {
      setLoading(false);
    }
  };

  const handleOrderThis = () => {
    if (!result) return;
    const origin = cities.find((c) => c.id === originId);
    const dest = cities.find((c) => c.id === destId);
    localStorage.setItem('nubo_quote_prefill', JSON.stringify({
      originName: origin?.name, destName: dest?.name, destCityId: dest?.id,
      vehicle, fee: result.delivery_fee, currency: result.currency,
      distance: result.distance_km, eta: result.adjusted_eta_mins,
    }));
    const token = localStorage.getItem('token');
    navigate(token ? '/dashboard' : '/auth');
  };

  const feeText = result
    ? new Intl.NumberFormat(currency === 'EUR' ? 'es-ES' : 'ar-MA', { style: 'currency', currency, maximumFractionDigits: 2 }).format(result.delivery_fee)
    : '';

  return (
    <div dir={rtl ? 'rtl' : 'ltr'} className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50"
      data-testid="delivery-quote-page">
      <header className="glass sticky top-0 z-50 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Button data-testid="quote-back-btn" onClick={() => navigate('/')} variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-1" /> {tr('back')}
            </Button>
            <div>
              <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Calculator className="w-5 h-5 text-emerald-600" /> {tr('title')}
              </h1>
              <p className="text-xs text-gray-500">{tr('subtitle')}</p>
            </div>
          </div>
          <LanguageSelector variant="outline" />
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 grid lg:grid-cols-2 gap-6">
        {/* Form */}
        <Card className="border-0 shadow-lg">
          <CardContent className="p-6 space-y-5">
            <div>
              <label className="text-sm font-medium text-gray-700 flex items-center gap-1 mb-1">
                <MapPin className="w-4 h-4 text-emerald-600" /> {tr('origin')}
              </label>
              <select data-testid="quote-origin-select" value={originId} onChange={(e) => setOriginId(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500">
                <option value="">{tr('selectOrigin')}</option>
                <optgroup label={tr('morocco')}>
                  {grouped.MA.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </optgroup>
                <optgroup label={tr('spain')}>
                  {grouped.ES.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </optgroup>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 flex items-center gap-1 mb-1">
                <Flag className="w-4 h-4 text-emerald-600" /> {tr('destination')}
              </label>
              <select data-testid="quote-destination-select" value={destId} onChange={(e) => setDestId(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500">
                <option value="">{tr('selectDestination')}</option>
                <optgroup label={tr('morocco')}>
                  {grouped.MA.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </optgroup>
                <optgroup label={tr('spain')}>
                  {grouped.ES.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </optgroup>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">{tr('vehicle')}</label>
              <div className="grid grid-cols-3 gap-3">
                {VEHICLES.map((v) => (
                  <button key={v.type} type="button" data-testid={`quote-vehicle-${v.type}`}
                    onClick={() => setVehicle(v.type)}
                    className={`flex flex-col items-center gap-2 rounded-xl border p-3 transition-all ${
                      vehicle === v.type ? 'border-emerald-500 bg-emerald-50 ring-2 ring-emerald-200' : 'border-gray-200 hover:border-emerald-300'
                    }`}>
                    <img src={v.icon} alt={tr(v.type)} className="w-10 h-10" />
                    <span className="text-xs font-medium text-gray-700">{tr(v.type)}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-700">{currency}</span>
              <div className="flex items-center rounded-full bg-gray-100 p-1" data-testid="quote-currency-switch">
                {['EUR', 'MAD'].map((c) => (
                  <button key={c} type="button" onClick={() => setCurrency(c)} data-testid={`quote-currency-${c}`}
                    className={`px-3 py-1 text-xs rounded-full transition-colors ${currency === c ? 'bg-emerald-600 text-white' : 'text-gray-600'}`}>
                    {c === 'EUR' ? '€ EUR' : 'د.م MAD'}
                  </button>
                ))}
              </div>
            </div>

            <Button data-testid="quote-calculate-btn" onClick={handleCalculate} disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-700 gap-2">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
              {loading ? tr('calculating') : tr('calculate')}
            </Button>
            {error && <p data-testid="quote-error" className="text-sm text-red-600">{error}</p>}
          </CardContent>
        </Card>

        {/* Result */}
        <Card className="border-0 shadow-lg">
          <CardContent className="p-6">
            {!result ? (
              <div className="flex flex-col items-center justify-center h-full min-h-[260px] text-center gap-3">
                <Calculator className="w-10 h-10 text-emerald-300" />
                <p className="text-sm text-gray-500">{tr('subtitle')}</p>
              </div>
            ) : (
              <div data-testid="quote-result" className="space-y-5">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold text-gray-900">{tr('result')}</h2>
                  <Badge className="bg-emerald-100 text-emerald-700">{tr(result.vehicle_used)}</Badge>
                </div>
                <div className="text-center py-4">
                  <p className="text-xs text-gray-400">{tr('fee')}</p>
                  <p className="text-4xl font-bold text-emerald-700" data-testid="quote-fee">{feeText}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-gray-50 p-4">
                    <p className="text-[11px] text-gray-400 flex items-center gap-1"><RouteIcon className="w-3 h-3" /> {tr('distance')}</p>
                    <p className="text-lg font-semibold text-gray-800" data-testid="quote-distance">{result.distance_km} km</p>
                  </div>
                  <div className="rounded-xl bg-gray-50 p-4">
                    <p className="text-[11px] text-gray-400 flex items-center gap-1"><Clock className="w-3 h-3" /> {tr('eta')}</p>
                    <p className="text-lg font-semibold text-gray-800" data-testid="quote-eta">{result.adjusted_eta_mins} {tr('minutes')}</p>
                  </div>
                </div>
                <Button data-testid="quote-order-btn" onClick={handleOrderThis}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 gap-2">
                  <PackageCheck className="w-4 h-4" /> {tr('orderThis')}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
