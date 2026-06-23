import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Truck, MapPin, Flag, Loader2, CheckCircle2, User, Clock, Send, Mail, MessageCircle, ShieldCheck, XCircle } from 'lucide-react';

export const LogisticsQuotesManager = ({ API, token }) => {
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const [pending, setPending] = useState([]);
  const [quoted, setQuoted] = useState([]);
  const [loading, setLoading] = useState(true);
  const [prices, setPrices] = useState({});
  const [savingId, setSavingId] = useState(null);
  const [resendingId, setResendingId] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [p, q] = await Promise.all([
        axios.get(`${API}/admin/logistics-quotes?status=pending_quote`, auth),
        axios.get(`${API}/admin/logistics-quotes?status=quoted`, auth),
      ]);
      setPending(p.data.quotes || []);
      setQuoted(q.data.quotes || []);
    } catch (e) {
      console.error('Error cargando cotizaciones de logística', e);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line
  }, [API, token]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const setPrice = async (id) => {
    const value = parseFloat(prices[id]);
    if (!value || value <= 0) { toast.error('Introduce un precio válido (> 0)'); return; }
    setSavingId(id);
    try {
      await axios.patch(`${API}/orders/${id}/set-quote-price`, { total_amount: value }, auth);
      toast.success('Precio fijado · cliente notificado por email y WhatsApp');
      setPrices((prev) => ({ ...prev, [id]: '' }));
      setTimeout(fetchAll, 1500);
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'No se pudo fijar el precio');
    } finally {
      setSavingId(null);
    }
  };

  const resend = async (id) => {
    setResendingId(id);
    try {
      await axios.post(`${API}/orders/${id}/resend-quote-notification`, {}, auth);
      toast.success('Notificación reenviada al cliente y al admin');
      fetchAll();
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'No se pudo reenviar la notificación');
    } finally {
      setResendingId(null);
    }
  };

  const ChannelBadge = ({ icon: Icon, label, result }) => {
    const sent = result?.sent;
    return (
      <span
        title={sent ? 'Enviado' : (result?.reason || 'No enviado')}
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${sent ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-600'}`}
      >
        <Icon className="w-3 h-3" />
        {label}
        {sent ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
      </span>
    );
  };

  const NotifHistory = ({ q }) => {
    const list = Array.isArray(q.notifications) ? q.notifications : [];
    const last = list.length ? list[list.length - 1] : null;
    return (
      <div className="rounded-lg bg-white/70 border border-blue-100 p-3 space-y-2" data-testid={`notif-history-${q.id}`}>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <span className="text-xs font-semibold text-gray-600">Historial de notificaciones</span>
          {q.last_notified_at && (
            <span className="text-xs text-gray-400" data-testid={`notif-last-at-${q.id}`}>
              Último envío: {new Date(q.last_notified_at).toLocaleString('es-ES')}
            </span>
          )}
        </div>
        {last ? (
          <div className="flex flex-wrap gap-2">
            <ChannelBadge icon={Mail} label="Email" result={last.channels?.email} />
            <ChannelBadge icon={MessageCircle} label="WA cliente" result={last.channels?.customer_whatsapp} />
            <ChannelBadge icon={ShieldCheck} label="WA admin" result={last.channels?.admin_whatsapp} />
            {list.length > 1 && <span className="text-xs text-gray-400 self-center">· {list.length} envíos</span>}
          </div>
        ) : (
          <p className="text-xs text-gray-400">Aún sin registro de envío (puede tardar unos segundos en aparecer).</p>
        )}
      </div>
    );
  };

  const CustomerLine = ({ q }) => (
    <p className="flex items-center gap-2 text-gray-500 text-sm"><User className="w-4 h-4 shrink-0" /> {q.customer_name || 'Cliente'} {q.customer_phone ? `· ${q.customer_phone}` : ''}</p>
  );

  return (
    <Card className="border-0 shadow-lg" data-testid="logistics-quotes-manager">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 flex-wrap">
          <Truck className="w-5 h-5 text-slate-800" />
          Cotizaciones de Camión / Logística
          <Badge className="bg-amber-100 text-amber-700" data-testid="logistics-pending-count">{pending.length} sin precio</Badge>
          <Badge className="bg-blue-100 text-blue-700" data-testid="logistics-quoted-count">{quoted.length} por confirmar</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {loading ? (
          <div className="py-8 text-center"><Loader2 className="w-6 h-6 mx-auto animate-spin text-emerald-500" /></div>
        ) : (
          <>
            {/* Pendientes de precio */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-700">Pendientes de precio</h3>
              {pending.length === 0 ? (
                <p className="text-sm text-gray-400 py-2">No hay solicitudes sin precio.</p>
              ) : pending.map((q) => (
                <div key={q.id} data-testid={`logistics-quote-${q.id}`} className="rounded-xl border border-gray-200 p-4 space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="font-mono text-xs text-gray-500">#{q.id.slice(0, 8)}</span>
                    <Badge className="bg-amber-100 text-amber-700">Pendiente de precio</Badge>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2 text-sm">
                    <p className="flex items-center gap-2 text-gray-700"><MapPin className="w-4 h-4 text-emerald-600 shrink-0" /> {q.origin_name || '—'}</p>
                    <p className="flex items-center gap-2 text-gray-700"><Flag className="w-4 h-4 text-slate-700 shrink-0" /> {q.destination_name || '—'}</p>
                  </div>
                  <CustomerLine q={q} />
                  <div className="flex items-center gap-2 pt-1">
                    <Input type="number" min="0" step="0.01" placeholder={`Precio (${q.currency || 'EUR'})`}
                      data-testid={`logistics-price-input-${q.id}`}
                      value={prices[q.id] || ''}
                      onChange={(e) => setPrices((prev) => ({ ...prev, [q.id]: e.target.value }))}
                      className="max-w-[180px]" />
                    <Button onClick={() => setPrice(q.id)} disabled={savingId === q.id}
                      data-testid={`logistics-set-price-${q.id}`}
                      className="bg-emerald-600 hover:bg-emerald-700 gap-2">
                      {savingId === q.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                      Fijar precio
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            {/* Enviadas · pendientes de confirmar */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-700">Enviadas · pendientes de confirmar por el cliente</h3>
              {quoted.length === 0 ? (
                <p className="text-sm text-gray-400 py-2">No hay cotizaciones esperando confirmación.</p>
              ) : quoted.map((q) => (
                <div key={q.id} data-testid={`logistics-quoted-${q.id}`} className="rounded-xl border border-blue-100 bg-blue-50/40 p-4 space-y-2">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="font-mono text-xs text-gray-500">#{q.id.slice(0, 8)}</span>
                    <Badge className="bg-blue-100 text-blue-700 gap-1"><Clock className="w-3 h-3" /> Esperando confirmación</Badge>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2 text-sm">
                    <p className="flex items-center gap-2 text-gray-700"><MapPin className="w-4 h-4 text-emerald-600 shrink-0" /> {q.origin_name || '—'}</p>
                    <p className="flex items-center gap-2 text-gray-700"><Flag className="w-4 h-4 text-slate-700 shrink-0" /> {q.destination_name || '—'}</p>
                  </div>
                  <CustomerLine q={q} />
                  <p className="text-sm font-semibold text-emerald-700">Precio enviado: {q.total_amount} {q.currency || 'EUR'}</p>
                  <NotifHistory q={q} />
                  <div className="flex justify-end pt-1">
                    <Button onClick={() => resend(q.id)} disabled={resendingId === q.id}
                      variant="outline" size="sm"
                      data-testid={`logistics-resend-${q.id}`}
                      className="gap-2 border-blue-300 text-blue-700 hover:bg-blue-100">
                      {resendingId === q.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                      Reenviar notificación
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default LogisticsQuotesManager;
