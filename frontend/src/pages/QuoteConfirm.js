import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Truck, MapPin, Flag, Loader2, CheckCircle2, LogIn, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function QuoteConfirm() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const token = localStorage.getItem('token');
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState('');

  const fetchOrder = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    try {
      const res = await axios.get(`${API}/orders/${orderId}`, { headers: { Authorization: `Bearer ${token}` } });
      setOrder(res.data);
      if (res.data.status === 'pending' || res.data.status !== 'quoted') {
        // ya confirmado o en proceso
        if (res.data.status !== 'quoted') setConfirmed(res.data.status !== 'pending_quote');
      }
    } catch (e) {
      console.error('Error cargando cotización', e);
      setError(t('logistics.load_error'));
    } finally {
      setLoading(false);
    }
  }, [orderId, token]);

  useEffect(() => { fetchOrder(); }, [fetchOrder]);

  const confirm = async () => {
    setConfirming(true);
    setError('');
    try {
      await axios.post(`${API}/orders/${orderId}/confirm-quote`, {}, { headers: { Authorization: `Bearer ${token}` } });
      setConfirmed(true);
    } catch (e) {
      setError(e?.response?.data?.detail || t('logistics.load_error'));
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-0 shadow-xl" data-testid="quote-confirm-page">
        <CardContent className="p-8">
          <div className="flex flex-col items-center text-center gap-2 mb-6">
            <div className="w-14 h-14 rounded-2xl bg-slate-900 flex items-center justify-center">
              <Truck className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-lg font-bold text-gray-900">{t('logistics.confirm_title')}</h1>
          </div>

          {loading ? (
            <div className="py-10 text-center"><Loader2 className="w-7 h-7 mx-auto animate-spin text-emerald-500" /></div>
          ) : !token ? (
            <div className="text-center space-y-4" data-testid="quote-confirm-login">
              <p className="text-sm text-gray-600">{t('logistics.confirm_login')}</p>
              <Button onClick={() => navigate('/auth')} className="bg-emerald-600 hover:bg-emerald-700 gap-2" data-testid="quote-confirm-login-btn">
                <LogIn className="w-4 h-4" /> {t('logistics.login')}
              </Button>
            </div>
          ) : confirmed ? (
            <div className="text-center space-y-3" data-testid="quote-confirm-success">
              <CheckCircle2 className="w-14 h-14 mx-auto text-emerald-500" />
              <h2 className="font-semibold text-gray-900">{t('logistics.confirmed_title')} 🎉</h2>
              <p className="text-sm text-gray-600">{t('logistics.confirmed_msg')}</p>
              <Button onClick={() => navigate('/orders')} variant="outline" className="mt-2" data-testid="quote-confirm-go-orders">{t('logistics.view_orders')}</Button>
            </div>
          ) : order ? (
            <div className="space-y-4" data-testid="quote-confirm-detail">
              <div className="space-y-2 text-sm">
                <p className="flex items-center gap-2 text-gray-700"><MapPin className="w-4 h-4 text-emerald-600 shrink-0" /> {order.origin_name || '—'}</p>
                <p className="flex items-center gap-2 text-gray-700"><Flag className="w-4 h-4 text-slate-700 shrink-0" /> {order.destination_name || '—'}</p>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 text-center">
                <p className="text-xs text-gray-500">{t('logistics.final_price')}</p>
                <p className="text-3xl font-extrabold text-emerald-600" data-testid="quote-confirm-price">{order.total_amount} {order.currency || 'EUR'}</p>
                <Badge className="mt-2 bg-amber-100 text-amber-700">{t('logistics.price_set_admin')}</Badge>
              </div>
              {error && <p className="text-sm text-red-600 flex items-center gap-1" data-testid="quote-confirm-error"><AlertCircle className="w-4 h-4" />{error}</p>}
              <Button onClick={confirm} disabled={confirming} className="w-full bg-emerald-600 hover:bg-emerald-700 gap-2" data-testid="quote-confirm-btn">
                {confirming ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                {confirming ? t('logistics.confirming') : t('logistics.confirm_order')}
              </Button>
            </div>
          ) : (
            <div className="text-center space-y-3" data-testid="quote-confirm-notfound">
              <AlertCircle className="w-10 h-10 mx-auto text-amber-500" />
              <p className="text-sm text-gray-600">{error || t('logistics.not_found')}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
