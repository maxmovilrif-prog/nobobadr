import React, { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { LogOut, Package, MapPin, Clock, Euro, Truck, Navigation } from 'lucide-react';

export default function DriverDashboard() {
  const navigate = useNavigate();
  const { user, token, logout, API } = useContext(AuthContext);
  const [availableOrders, setAvailableOrders] = useState([]);
  const [myOrders, setMyOrders] = useState([]);
  const [isAvailable, setIsAvailable] = useState(user.is_available || false);
  const [loading, setLoading] = useState(false);
  const [locationSharing, setLocationSharing] = useState(false);
  const [currentLocation, setCurrentLocation] = useState(null);
  const wsConnections = useRef({});
  const geoWatchId = useRef(null);

  useEffect(() => {
    if (isAvailable) {
      fetchAvailableOrders();
    }
    fetchMyOrders();
  }, [isAvailable]);

  // Start location sharing for active deliveries
  useEffect(() => {
    const activeDeliveries = myOrders.filter(order => 
      order.status === 'in_transit' && order.driver_id === user.id
    );

    if (activeDeliveries.length > 0 && !locationSharing) {
      startLocationSharing(activeDeliveries);
    } else if (activeDeliveries.length === 0 && locationSharing) {
      stopLocationSharing();
    }

    return () => {
      stopLocationSharing();
    };
  }, [myOrders]);

  const startLocationSharing = (activeOrders) => {
    if (!navigator.geolocation) {
      toast.error('Geolocalización no disponible');
      return;
    }

    setLocationSharing(true);
    console.log('🐝 Iniciando compartir ubicación para', activeOrders.length, 'pedidos');

    // Watch position
    geoWatchId.current = navigator.geolocation.watchPosition(
      (position) => {
        const location = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        };
        setCurrentLocation(location);

        // Send location to all active order tracking websockets
        activeOrders.forEach(order => {
          sendLocationToWebSocket(order.id, location);
        });
      },
      (error) => {
        console.error('Error obteniendo ubicación:', error);
        toast.error('Error al obtener ubicación GPS');
      },
      {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 5000
      }
    );
  };

  const stopLocationSharing = () => {
    if (geoWatchId.current) {
      navigator.geolocation.clearWatch(geoWatchId.current);
      geoWatchId.current = null;
    }

    // Close all WebSocket connections
    Object.values(wsConnections.current).forEach(ws => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });
    wsConnections.current = {};
    setLocationSharing(false);
    console.log('🐝 Ubicación compartida detenida');
  };

  const sendLocationToWebSocket = (orderId, location) => {
    const wsUrl = API.replace('http', 'ws').replace('https', 'wss');
    
    if (!wsConnections.current[orderId]) {
      // Create new WebSocket connection
      const ws = new WebSocket(`${wsUrl}/ws/tracking/${orderId}`);
      
      ws.onopen = () => {
        console.log(`🐝 WebSocket conectado para pedido ${orderId}`);
        ws.send(JSON.stringify({
          lat: location.lat,
          lng: location.lng,
          driver_name: user.name,
          status: 'en_camino'
        }));
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log(`WebSocket cerrado para pedido ${orderId}`);
        delete wsConnections.current[orderId];
      };

      wsConnections.current[orderId] = ws;
    } else {
      // Send location through existing connection
      const ws = wsConnections.current[orderId];
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          lat: location.lat,
          lng: location.lng,
          driver_name: user.name,
          status: 'en_camino'
        }));
      }
    }
  };

  const fetchAvailableOrders = async () => {
    try {
      const response = await axios.get(`${API}/drivers/available-orders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAvailableOrders(response.data);
    } catch (error) {
      console.error('Error fetching available orders:', error);
    }
  };

  const fetchMyOrders = async () => {
    try {
      const response = await axios.get(`${API}/orders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMyOrders(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    }
  };

  const toggleAvailability = async (checked) => {
    try {
      await axios.patch(`${API}/drivers/availability?is_available=${checked}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsAvailable(checked);
      toast.success(checked ? 'Ahora estás disponible' : 'Ahora estás no disponible');
    } catch (error) {
      toast.error('Error al actualizar disponibilidad');
    }
  };

  const acceptOrder = async (orderId) => {
    setLoading(true);
    try {
      await axios.post(`${API}/orders/${orderId}/assign-driver`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Pedido aceptado');
      fetchAvailableOrders();
      fetchMyOrders();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al aceptar pedido');
    } finally {
      setLoading(false);
    }
  };

  const updateOrderStatus = async (orderId, status) => {
    try {
      await axios.patch(`${API}/orders/${orderId}/status`, { status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Estado actualizado');
      fetchMyOrders();
    } catch (error) {
      toast.error('Error al actualizar estado');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <header className="glass sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
              <Truck className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Panel Repartidor</h1>
              <p className="text-sm text-gray-600">Hola, {user.name}</p>
            </div>
          </div>
          <Button data-testid="logout-btn" onClick={logout} variant="outline" size="sm">
            <LogOut className="w-4 h-4 mr-2" />
            Salir
          </Button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Availability Toggle */}
        <Card className="mb-8 border-0 shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="availability" className="text-lg font-semibold">Estado de Disponibilidad</Label>
                <p className="text-sm text-gray-600 mt-1">
                  {isAvailable ? 'Recibirás notificaciones de nuevos pedidos' : 'No recibirás nuevos pedidos'}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-sm font-medium ${isAvailable ? 'text-emerald-600' : 'text-gray-500'}`}>
                  {isAvailable ? 'Disponible' : 'No disponible'}
                </span>
                <Switch
                  id="availability"
                  data-testid="availability-switch"
                  checked={isAvailable}
                  onCheckedChange={toggleAvailability}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Location Sharing Indicator */}
        {locationSharing && (
          <Card className="mb-8 border-emerald-200 bg-emerald-50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  <div>
                    <p className="font-semibold text-emerald-900 flex items-center gap-2">
                      <Navigation className="w-4 h-4" />
                      🐝 Ubicación compartida en tiempo real
                    </p>
                    <p className="text-sm text-emerald-700">
                      {currentLocation ? 
                        `Lat: ${currentLocation.lat.toFixed(6)}, Lng: ${currentLocation.lng.toFixed(6)}` : 
                        'Obteniendo ubicación GPS...'}
                    </p>
                  </div>
                </div>
                <Badge className="bg-emerald-600 text-white">
                  {myOrders.filter(o => o.status === 'in_transit').length} entregas activas
                </Badge>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Available Orders */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Pedidos Disponibles</h2>
            {!isAvailable ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Package className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-600">Activa tu disponibilidad para ver pedidos</p>
                </CardContent>
              </Card>
            ) : availableOrders.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Package className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-600">No hay pedidos disponibles</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {availableOrders.map(order => (
                  <Card key={order.id} data-testid={`available-order-${order.id}`} className="hover-lift">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="font-semibold text-lg">Pedido #{order.id.slice(0, 8)}</h3>
                          <p className="text-sm text-gray-600 flex items-center mt-1">
                            <Clock className="w-4 h-4 mr-1" />
                            {new Date(order.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                          </p>
                        </div>
                        <Badge className="bg-emerald-100 text-emerald-700 text-lg px-3 py-1">
                          <Euro className="w-4 h-4 mr-1" />
                          {order.total_amount.toFixed(2)}
                        </Badge>
                      </div>
                      <div className="flex items-start text-sm text-gray-600 mb-4">
                        <MapPin className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                        <span>{order.delivery_address}</span>
                      </div>
                      <Button
                        data-testid={`accept-order-${order.id}`}
                        onClick={() => acceptOrder(order.id)}
                        disabled={loading}
                        className="w-full bg-emerald-600 hover:bg-emerald-700"
                      >
                        Aceptar Pedido
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* My Orders */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Mis Entregas</h2>
            {myOrders.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Package className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-600">No tienes entregas asignadas</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {myOrders.map(order => (
                  <Card key={order.id} data-testid={`my-order-${order.id}`} className="hover-lift">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="font-semibold text-lg">Pedido #{order.id.slice(0, 8)}</h3>
                          <Badge className="mt-2">{order.status}</Badge>
                        </div>
                        <span className="text-lg font-bold text-emerald-600">€{order.total_amount.toFixed(2)}</span>
                      </div>
                      <div className="flex items-start text-sm text-gray-600 mb-4">
                        <MapPin className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                        <span>{order.delivery_address}</span>
                      </div>
                      {order.status !== 'delivered' && order.status !== 'cancelled' && (
                        <div className="flex gap-2">
                          {order.status === 'accepted' && (
                            <Button
                              data-testid={`mark-in-transit-${order.id}`}
                              onClick={() => updateOrderStatus(order.id, 'in_transit')}
                              className="flex-1 bg-blue-600"
                              size="sm"
                            >
                              En camino
                            </Button>
                          )}
                          {order.status === 'in_transit' && (
                            <Button
                              data-testid={`mark-delivered-${order.id}`}
                              onClick={() => updateOrderStatus(order.id, 'delivered')}
                              className="flex-1 bg-green-600"
                              size="sm"
                            >
                              Entregado
                            </Button>
                          )}
                          <Button
                            data-testid={`view-order-${order.id}`}
                            onClick={() => navigate(`/order-tracking/${order.id}`)}
                            variant="outline"
                            size="sm"
                          >
                            Ver Detalles
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}