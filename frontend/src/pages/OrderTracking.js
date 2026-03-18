import React, { useState, useEffect, useContext, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import DeliveryMap from '@/components/DeliveryMap';
import { toast } from 'sonner';
import { ArrowLeft, Package, MapPin, Clock, MessageCircle, Send, Navigation } from 'lucide-react';

export default function OrderTracking() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { user, token, API } = useContext(AuthContext);
  const [order, setOrder] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [driverLocation, setDriverLocation] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    fetchOrder();
    fetchMessages();
    connectWebSocket();
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [orderId]);

  const connectWebSocket = () => {
    // Get WebSocket URL from backend URL
    const wsUrl = API.replace('http', 'ws').replace('https', 'wss');
    ws.current = new WebSocket(`${wsUrl}/ws/tracking/${orderId}`);

    ws.current.onopen = () => {
      console.log('🐝 WebSocket conectado - Tracking en tiempo real activo');
      setWsConnected(true);
      toast.success('Tracking en tiempo real conectado 🐝');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('📍 Ubicación recibida:', data);
      setDriverLocation({
        lat: data.lat,
        lng: data.lng,
        driver_name: data.driver_name,
        status: data.status,
        timestamp: data.timestamp
      });
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    ws.current.onclose = () => {
      console.log('WebSocket desconectado');
      setWsConnected(false);
      // Reconnect after 5 seconds
      setTimeout(() => {
        if (order && order.status !== 'delivered') {
          connectWebSocket();
        }
      }, 5000);
    };
  };

  const fetchOrder = async () => {
    try {
      const response = await axios.get(`${API}/orders/${orderId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOrder(response.data);
    } catch (error) {
      console.error('Error fetching order:', error);
      toast.error('Error al cargar pedido');
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await axios.get(`${API}/messages/${orderId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessages(response.data);
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    try {
      await axios.post(`${API}/messages`, {
        order_id: orderId,
        message: newMessage
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNewMessage('');
      fetchMessages();
    } catch (error) {
      toast.error('Error al enviar mensaje');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Pedido no encontrado</p>
      </div>
    );
  }

  const statusSteps = [
    { key: 'pending', label: 'Pendiente', completed: true },
    { key: 'accepted', label: 'Aceptado', completed: ['accepted', 'preparing', 'ready', 'in_transit', 'delivered'].includes(order.status) },
    { key: 'preparing', label: 'Preparando', completed: ['preparing', 'ready', 'in_transit', 'delivered'].includes(order.status) },
    { key: 'in_transit', label: 'En camino', completed: ['in_transit', 'delivered'].includes(order.status) },
    { key: 'delivered', label: 'Entregado', completed: order.status === 'delivered' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <header className="glass sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Button data-testid="back-btn" onClick={() => navigate('/dashboard')} variant="ghost">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver
          </Button>
          <h1 className="text-xl font-bold">Seguimiento de Pedido</h1>
          <div className="w-20"></div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Order Details */}
          <div className="lg:col-span-2 space-y-6">
            <Card data-testid="order-details-card" className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Pedido #{order.id.slice(0, 8)}</span>
                  <Badge className={order.status === 'delivered' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}>
                    {order.status}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-start">
                    <MapPin className="w-5 h-5 text-emerald-600 mr-3 mt-0.5" />
                    <div>
                      <p className="font-medium">Dirección de entrega</p>
                      <p className="text-gray-600">{order.delivery_address}</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <Clock className="w-5 h-5 text-emerald-600 mr-3 mt-0.5" />
                    <div>
                      <p className="font-medium">Hora del pedido</p>
                      <p className="text-gray-600">{new Date(order.created_at).toLocaleString('es-ES')}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Google Maps */}
            <DeliveryMap 
              order={order}
              deliveryAddress={order.delivery_address}
            />

            {/* Status Timeline */}
            <Card data-testid="status-timeline" className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle>Estado del Pedido</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {statusSteps.map((step, idx) => (
                    <div key={step.key} className="flex items-center gap-4">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                        step.completed ? 'bg-emerald-500' : 'bg-gray-300'
                      }`}>
                        {step.completed && (
                          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                      <div className="flex-1">
                        <p className={`font-medium ${
                          step.completed ? 'text-emerald-700' : 'text-gray-500'
                        }`}>{step.label}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Order Items */}
            <Card data-testid="order-items-card" className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle>Detalles del Pedido</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {order.items.map((item, idx) => (
                    <div key={idx} data-testid={`order-item-${idx}`} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div>
                        <p className="font-medium">{item.product_name}</p>
                        <p className="text-sm text-gray-600">Cantidad: {item.quantity}</p>
                      </div>
                      <p className="font-semibold">€{(item.price * item.quantity).toFixed(2)}</p>
                    </div>
                  ))}
                  <div className="flex items-center justify-between pt-4 border-t-2">
                    <p className="text-lg font-semibold">Total</p>
                    <p className="text-2xl font-bold text-emerald-600">€{order.total_amount.toFixed(2)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Chat */}
          <div>
            <Card data-testid="chat-card" className="border-0 shadow-lg h-[600px] flex flex-col">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MessageCircle className="w-5 h-5 mr-2" />
                  Chat
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col p-0">
                <ScrollArea className="flex-1 px-6">
                  {messages.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">No hay mensajes aún</p>
                  ) : (
                    <div className="space-y-3 py-4">
                      {messages.map(msg => (
                        <div
                          key={msg.id}
                          data-testid={`message-${msg.id}`}
                          className={`flex ${
                            msg.sender_id === user.id ? 'justify-end' : 'justify-start'
                          }`}
                        >
                          <div className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                            msg.sender_id === user.id
                              ? 'bg-emerald-500 text-white'
                              : 'bg-gray-200 text-gray-900'
                          }`}>
                            <p className="text-xs opacity-75 mb-1">{msg.sender_role}</p>
                            <p>{msg.message}</p>
                            <p className="text-xs opacity-75 mt-1">
                              {new Date(msg.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
                <form onSubmit={sendMessage} className="p-4 border-t">
                  <div className="flex gap-2">
                    <Input
                      data-testid="message-input"
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Escribe un mensaje..."
                      className="flex-1"
                    />
                    <Button data-testid="send-message-btn" type="submit" size="icon" className="bg-emerald-600">
                      <Send className="w-4 h-4" />
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}