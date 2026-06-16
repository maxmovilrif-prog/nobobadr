import React, { useEffect, useState, useContext } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { CheckCircle, Loader2, XCircle, MapPin } from 'lucide-react';

export default function OrderSuccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { token, API } = useContext(AuthContext);
  const [status, setStatus] = useState('loading'); // loading, success, failed
  const [orderDetails, setOrderDetails] = useState(null);
  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    if (sessionId) {
      pollPaymentStatus();
    } else {
      setStatus('failed');
    }
  }, [sessionId]);

  const pollPaymentStatus = async (attempts = 0) => {
    const maxAttempts = 5;
    const pollInterval = 2000;

    if (attempts >= maxAttempts) {
      setStatus('failed');
      return;
    }

    try {
      const response = await axios.get(`${API}/payments/status/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.data.payment_status === 'paid') {
        setStatus('success');
        setOrderDetails(response.data);
        return;
      } else if (response.data.status === 'expired') {
        setStatus('failed');
        return;
      }

      // Continue polling
      setTimeout(() => pollPaymentStatus(attempts + 1), pollInterval);
    } catch (error) {
      console.error('Error checking payment status:', error);
      setStatus('failed');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 flex items-center justify-center p-6">
      <Card data-testid="payment-status-card" className="max-w-md w-full border-0 shadow-2xl">
        <CardContent className="p-12 text-center">
          {status === 'loading' && (
            <>
              <Loader2 className="w-16 h-16 mx-auto mb-6 text-emerald-600 animate-spin" />
              <h2 className="text-2xl font-bold mb-2">Verificando pago...</h2>
              <p className="text-gray-600">Por favor espera mientras confirmamos tu pago</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="w-16 h-16 mx-auto mb-6 text-green-500" />
              <h2 className="text-2xl font-bold mb-2 text-green-700">¡Pago Exitoso!</h2>
              <p className="text-gray-600 mb-6">Tu pedido ha sido confirmado y está siendo procesado</p>
              {orderDetails && (
                <div className="bg-gray-50 rounded-lg p-4 mb-6">
                  <p className="text-sm text-gray-600 mb-1">Total pagado</p>
                  <p className="text-3xl font-bold text-emerald-600">€{orderDetails.amount.toFixed(2)}</p>
                </div>
              )}
              {orderDetails?.order_type === 'express' && orderDetails?.order_id && (
                <Button
                  data-testid="track-express-btn"
                  onClick={() => navigate(`/track?order=${orderDetails.order_id}`)}
                  className="w-full mb-3 bg-emerald-600 hover:bg-emerald-700 gap-2"
                >
                  <MapPin className="w-4 h-4" /> Seguir mi pedido en vivo
                </Button>
              )}
              <div className="flex gap-3">
                <Button
                  data-testid="view-orders-btn"
                  onClick={() => navigate('/orders')}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                >
                  Ver Mis Pedidos
                </Button>
                <Button
                  data-testid="continue-shopping-btn"
                  onClick={() => navigate('/dashboard')}
                  variant="outline"
                  className="flex-1"
                >
                  Seguir Comprando
                </Button>
              </div>
            </>
          )}

          {status === 'failed' && (
            <>
              <XCircle className="w-16 h-16 mx-auto mb-6 text-red-500" />
              <h2 className="text-2xl font-bold mb-2 text-red-700">Pago Fallido</h2>
              <p className="text-gray-600 mb-6">No se pudo procesar tu pago. Por favor inténtalo de nuevo.</p>
              <Button
                data-testid="retry-btn"
                onClick={() => navigate('/dashboard')}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
              >
                Volver al Inicio
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}