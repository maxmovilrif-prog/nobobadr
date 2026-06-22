import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Truck, MapPin, Flag, Loader2, CheckCircle2, User } from 'lucide-react';

export const LogisticsQuotesManager = ({ API, token }) => {
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [prices, setPrices] = useState({});
  const [savingId, setSavingId] = useState(null);

  const fetchQuotes = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/logistics-quotes`, auth);
      setQuotes(res.data.quotes || []);
    } catch (e) {
      console.error('Error cargando cotizaciones de logística', e);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line
  }, [API, token]);

  useEffect(() => { fetchQuotes(); }, [fetchQuotes]);

  const setPrice = async (id) => {
    const value = parseFloat(prices[id]);
    if (!value || value <= 0) { toast.error('Introduce un precio válido (> 0)'); return; }
    setSavingId(id);
    try {
      await axios.patch(`${API}/orders/${id}/set-quote-price`, { total_amount: value }, auth);
      toast.success('Precio fijado · cliente notificado por email');
      setPrices((p) => ({ ...p, [id]: '' }));
      fetchQuotes();
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'No se pudo fijar el precio');
    } finally {
      setSavingId(null);
    }
  };

  return (
    <Card className="border-0 shadow-lg" data-testid="logistics-quotes-manager">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Truck className="w-5 h-5 text-slate-800" />
          Cotizaciones de Camión / Logística
          <Badge className="bg-amber-100 text-amber-700" data-testid="logistics-quotes-count">{quotes.length} pendiente(s)</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <div className="py-8 text-center"><Loader2 className="w-6 h-6 mx-auto animate-spin text-emerald-500" /></div>
        ) : quotes.length === 0 ? (
          <div className="py-10 text-center">
            <Truck className="w-10 h-10 mx-auto mb-3 text-gray-300" />
            <p className="text-sm text-gray-500">No hay solicitudes de cotización pendientes.</p>
          </div>
        ) : (
          quotes.map((q) => (
            <div key={q.id} data-testid={`logistics-quote-${q.id}`}
              className="rounded-xl border border-gray-200 p-4 space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="font-mono text-xs text-gray-500">#{q.id.slice(0, 8)}</span>
                <Badge className="bg-amber-100 text-amber-700">Pendiente de precio</Badge>
              </div>
              <div className="grid sm:grid-cols-2 gap-2 text-sm">
                <p className="flex items-center gap-2 text-gray-700"><MapPin className="w-4 h-4 text-emerald-600 shrink-0" /> {q.origin_name || '—'}</p>
                <p className="flex items-center gap-2 text-gray-700"><Flag className="w-4 h-4 text-slate-700 shrink-0" /> {q.destination_name || '—'}</p>
                <p className="flex items-center gap-2 text-gray-500"><User className="w-4 h-4 shrink-0" /> {q.customer_name || 'Cliente'} {q.customer_phone ? `· ${q.customer_phone}` : ''}</p>
                {q.distance_km != null && <p className="text-gray-500">Distancia aprox.: <b>{q.distance_km} km</b></p>}
              </div>
              <div className="flex items-center gap-2 pt-1">
                <Input type="number" min="0" step="0.01" placeholder={`Precio (${q.currency || 'EUR'})`}
                  data-testid={`logistics-price-input-${q.id}`}
                  value={prices[q.id] || ''}
                  onChange={(e) => setPrices((p) => ({ ...p, [q.id]: e.target.value }))}
                  className="max-w-[180px]" />
                <Button onClick={() => setPrice(q.id)} disabled={savingId === q.id}
                  data-testid={`logistics-set-price-${q.id}`}
                  className="bg-emerald-600 hover:bg-emerald-700 gap-2">
                  {savingId === q.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Fijar precio
                </Button>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
};

export default LogisticsQuotesManager;
