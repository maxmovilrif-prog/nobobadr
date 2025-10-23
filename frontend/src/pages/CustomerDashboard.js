import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { LogOut, ShoppingBag, Package, Clock, Store, MapPin, Plus, Minus, ShoppingCart, CreditCard, Car } from 'lucide-react';
import VehicleCard from '@/components/VehicleCard';
import VehicleFilters from '@/components/VehicleFilters';

export default function CustomerDashboard() {
  const navigate = useNavigate();
  const { user, token, logout, API } = useContext(AuthContext);
  const [businesses, setBusinesses] = useState([]);
  const [orders, setOrders] = useState([]);
  const [selectedBusiness, setSelectedBusiness] = useState(null);
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const [vehicleFilters, setVehicleFilters] = useState({
    priceRange: [0, 50000],
    brand: 'all',
    fuel: 'all',
    type: 'all',
    sortBy: 'name'
  });
  const [vehicleSearchTerm, setVehicleSearchTerm] = useState('');

  useEffect(() => {
    fetchBusinesses();
    fetchOrders();
  }, []);

  const fetchBusinesses = async () => {
    try {
      const response = await axios.get(`${API}/businesses`);
      setBusinesses(response.data);
    } catch (error) {
      console.error('Error fetching businesses:', error);
    }
  };

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${API}/orders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOrders(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    }
  };

  const fetchProducts = async (businessId) => {
    try {
      const response = await axios.get(`${API}/products/${businessId}`);
      setProducts(response.data);
      setSelectedBusiness(businesses.find(b => b.id === businessId));
    } catch (error) {
      toast.error('Error al cargar productos');
    }
  };

  const addToCart = (product) => {
    const existing = cart.find(item => item.product_id === product.id);
    if (existing) {
      setCart(cart.map(item =>
        item.product_id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, {
        product_id: product.id,
        product_name: product.name,
        quantity: 1,
        price: product.price
      }]);
    }
    toast.success(`${product.name} añadido al carrito`);
  };

  const removeFromCart = (productId) => {
    const existing = cart.find(item => item.product_id === productId);
    if (existing && existing.quantity > 1) {
      setCart(cart.map(item =>
        item.product_id === productId
          ? { ...item, quantity: item.quantity - 1 }
          : item
      ));
    } else {
      setCart(cart.filter(item => item.product_id !== productId));
    }
  };

  const createOrder = async () => {
    if (!deliveryAddress) {
      toast.error('Por favor ingresa una dirección de entrega');
      return;
    }
    if (cart.length === 0) {
      toast.error('El carrito está vacío');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/orders`, {
        business_id: selectedBusiness.id,
        items: cart,
        delivery_address: deliveryAddress
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const orderId = response.data.id;
      
      // Create payment session
      const paymentResponse = await axios.post(
        `${API}/payments/create-checkout?order_id=${orderId}`,
        {},
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            Origin: window.location.origin
          }
        }
      );

      // Redirect to Stripe
      window.location.href = paymentResponse.data.url;
    } catch (error) {
      toast.error('Error al crear el pedido');
    } finally {
      setLoading(false);
    }
  };

  // Filter and search for vehicles
  const filterVehicleProducts = (prods) => {
    let filtered = [...prods];

    // Apply search
    if (vehicleSearchTerm) {
      filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(vehicleSearchTerm.toLowerCase()) ||
        p.description.toLowerCase().includes(vehicleSearchTerm.toLowerCase()) ||
        p.category.toLowerCase().includes(vehicleSearchTerm.toLowerCase())
      );
    }

    // Apply price range
    filtered = filtered.filter(p => 
      p.price >= vehicleFilters.priceRange[0] && 
      p.price <= vehicleFilters.priceRange[1]
    );

    // Apply brand filter
    if (vehicleFilters.brand !== 'all') {
      filtered = filtered.filter(p => p.name.includes(vehicleFilters.brand));
    }

    // Apply fuel type filter
    if (vehicleFilters.fuel !== 'all') {
      filtered = filtered.filter(p => p.category === vehicleFilters.fuel);
    }

    // Apply vehicle type filter
    if (vehicleFilters.type !== 'all') {
      filtered = filtered.filter(p => p.category === vehicleFilters.type);
    }

    // Apply sorting
    switch (vehicleFilters.sortBy) {
      case 'price-asc':
        filtered.sort((a, b) => a.price - b.price);
        break;
      case 'price-desc':
        filtered.sort((a, b) => b.price - a.price);
        break;
      case 'name':
        filtered.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'newest':
        filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        break;
      default:
        break;
    }

    return filtered;
  };

  const displayedProducts = filter === 'vehicles' && products.length > 0
    ? filterVehicleProducts(products)
    : products;

  const filteredBusinesses = filter === 'all' 
    ? businesses 
    : businesses.filter(b => b.category === filter);

  const cartTotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

  const getStatusBadge = (status) => {
    const variants = {
      pending: 'bg-yellow-100 text-yellow-700',
      accepted: 'bg-blue-100 text-blue-700',
      preparing: 'bg-purple-100 text-purple-700',
      in_transit: 'bg-orange-100 text-orange-700',
      delivered: 'bg-green-100 text-green-700',
      cancelled: 'bg-red-100 text-red-700'
    };
    return <Badge className={variants[status] || ''}>{status}</Badge>;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      {/* Header */}
      <header className="glass sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
              <ShoppingBag className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Nubo</h1>
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
        <Tabs defaultValue="businesses" className="w-full">
          <TabsList className="mb-8">
            <TabsTrigger data-testid="businesses-tab" value="businesses">Negocios</TabsTrigger>
            <TabsTrigger data-testid="my-orders-tab" value="orders">Mis Pedidos</TabsTrigger>
          </TabsList>

          <TabsContent value="businesses">
            {/* Category Filter */}
            <div className="flex gap-4 mb-6 overflow-x-auto pb-2">
              {[
                { value: 'all', label: 'Todos', icon: Store },
                { value: 'restaurant', label: 'Restaurantes', icon: ShoppingBag },
                { value: 'supermarket', label: 'Supermercados', icon: Package },
                { value: 'courier', label: 'Paquetería', icon: Package },
                { value: 'vehicles', label: 'Vehículos', icon: ShoppingCart }
              ].map(cat => (
                <Button
                  key={cat.value}
                  data-testid={`filter-${cat.value}-btn`}
                  onClick={() => setFilter(cat.value)}
                  variant={filter === cat.value ? 'default' : 'outline'}
                  className={filter === cat.value ? 'bg-emerald-600' : ''}
                >
                  <cat.icon className="w-4 h-4 mr-2" />
                  {cat.label}
                </Button>
              ))}
            </div>

            {/* Vehicle Filters - Only show when vehicles category is selected */}
            {filter === 'vehicles' && (
              <VehicleFilters
                onFilterChange={setVehicleFilters}
                onSearchChange={setVehicleSearchTerm}
              />
            )}

            {/* Businesses Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredBusinesses.map(business => (
                <Card key={business.id} data-testid={`business-card-${business.id}`} className="hover-lift cursor-pointer border-0 shadow-lg" onClick={() => fetchProducts(business.id)}>
                  <div className="aspect-video bg-gradient-to-br from-emerald-400 to-teal-500 rounded-t-lg overflow-hidden">
                    <img src={business.image_url} alt={business.name} className="w-full h-full object-cover" />
                  </div>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      {business.category === 'vehicles' && <Car className="w-5 h-5 text-emerald-600" />}
                      <h3 className="text-lg font-semibold text-gray-900">{business.name}</h3>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{business.description}</p>
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center text-gray-600">
                        <Clock className="w-4 h-4 mr-1" />
                        {business.delivery_time}
                      </span>
                      <Badge className="bg-emerald-100 text-emerald-700">{business.category}</Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Products Dialog */}
            <Dialog open={selectedBusiness !== null} onOpenChange={() => setSelectedBusiness(null)}>
              <DialogContent data-testid="products-dialog" className="max-w-4xl max-h-[90vh]">
                <DialogHeader>
                  <DialogTitle className="text-2xl">{selectedBusiness?.name}</DialogTitle>
                </DialogHeader>
                <div className="grid md:grid-cols-3 gap-6">
                  <ScrollArea className="md:col-span-2 h-[500px]">
                    <div className="grid gap-4 pr-4">
                      {displayedProducts.length === 0 ? (
                        <div className="text-center py-12">
                          <Car className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                          <p className="text-gray-600">No se encontraron vehículos con los filtros seleccionados</p>
                        </div>
                      ) : displayedProducts.map(product => (
                        selectedBusiness?.category === 'vehicles' ? (
                          <Card key={product.id} data-testid={`product-card-${product.id}`} className="overflow-hidden">
                            <div className="grid md:grid-cols-2 gap-4">
                              <img src={product.image_url} alt={product.name} className="w-full h-48 object-cover" />
                              <CardContent className="p-4">
                                <Badge className="mb-2">{product.category}</Badge>
                                <h4 className="font-bold text-lg text-gray-900 mb-2">{product.name}</h4>
                                <p className="text-sm text-gray-600 mb-3">{product.description}</p>
                                <div className="flex items-center justify-between">
                                  <div>
                                    <span className="text-2xl font-bold text-emerald-600">€{product.price.toLocaleString('es-ES')}</span>
                                    <p className="text-xs text-gray-500">Desde €{Math.round(product.price / 60)}/mes</p>
                                  </div>
                                  <Button data-testid={`add-to-cart-${product.id}`} onClick={() => addToCart(product)} size="sm" className="bg-emerald-600">
                                    Consultar
                                  </Button>
                                </div>
                              </CardContent>
                            </div>
                          </Card>
                        ) : (
                          <Card key={product.id} data-testid={`product-card-${product.id}`}>
                            <CardContent className="p-4 flex gap-4">
                              <img src={product.image_url} alt={product.name} className="w-24 h-24 object-cover rounded-lg" />
                              <div className="flex-1">
                                <h4 className="font-semibold text-gray-900">{product.name}</h4>
                                <p className="text-sm text-gray-600 mb-2">{product.description}</p>
                                <div className="flex items-center justify-between">
                                  <span className="text-lg font-bold text-emerald-600">€{product.price.toFixed(2)}</span>
                                  <Button data-testid={`add-to-cart-${product.id}`} onClick={() => addToCart(product)} size="sm" className="bg-emerald-600">
                                    <Plus className="w-4 h-4" />
                                  </Button>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        )
                      ))}
                    </div>
                  </ScrollArea>

                  {/* Cart */}
                  <div className="border-l pl-6">
                    <h3 className="text-lg font-semibold mb-4">Carrito</h3>
                    {cart.length === 0 ? (
                      <p className="text-gray-500 text-sm">Carrito vacío</p>
                    ) : (
                      <>
                        <ScrollArea className="h-[300px] mb-4">
                          {cart.map(item => (
                            <div key={item.product_id} data-testid={`cart-item-${item.product_id}`} className="flex items-center justify-between mb-3 pb-3 border-b">
                              <div className="flex-1">
                                <p className="font-medium text-sm">{item.product_name}</p>
                                <p className="text-sm text-gray-600">€{item.price.toFixed(2)}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button data-testid={`decrease-qty-${item.product_id}`} size="sm" variant="outline" onClick={() => removeFromCart(item.product_id)}>
                                  <Minus className="w-3 h-3" />
                                </Button>
                                <span className="text-sm font-medium">{item.quantity}</span>
                                <Button data-testid={`increase-qty-${item.product_id}`} size="sm" variant="outline" onClick={() => addToCart(products.find(p => p.id === item.product_id))}>
                                  <Plus className="w-3 h-3" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </ScrollArea>
                        <div className="space-y-3">
                          <Input
                            data-testid="delivery-address-input"
                            placeholder="Dirección de entrega"
                            value={deliveryAddress}
                            onChange={(e) => setDeliveryAddress(e.target.value)}
                          />
                          <div className="flex items-center justify-between py-2 border-t">
                            <span className="font-semibold">Total:</span>
                            <span className="text-xl font-bold text-emerald-600">€{cartTotal.toFixed(2)}</span>
                          </div>
                          <Button data-testid="checkout-btn" onClick={createOrder} disabled={loading} className="w-full bg-emerald-600">
                            {loading ? 'Procesando...' : (
                              <>
                                <CreditCard className="w-4 h-4 mr-2" />
                                Pagar Pedido
                              </>
                            )}
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </TabsContent>

          <TabsContent value="orders">
            <div className="grid gap-4">
              {orders.length === 0 ? (
                <Card>
                  <CardContent className="p-8 text-center">
                    <Package className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    <p className="text-gray-600">No tienes pedidos aún</p>
                  </CardContent>
                </Card>
              ) : (
                orders.map(order => (
                  <Card key={order.id} data-testid={`order-card-${order.id}`} className="hover-lift cursor-pointer" onClick={() => navigate(`/order-tracking/${order.id}`)}>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="font-semibold text-lg">Pedido #{order.id.slice(0, 8)}</h3>
                          <p className="text-sm text-gray-600">{new Date(order.created_at).toLocaleDateString('es-ES')}</p>
                        </div>
                        <div className="text-right">
                          {getStatusBadge(order.status)}
                          <p className="text-lg font-bold text-emerald-600 mt-1">€{order.total_amount.toFixed(2)}</p>
                        </div>
                      </div>
                      <div className="flex items-center text-sm text-gray-600">
                        <MapPin className="w-4 h-4 mr-2" />
                        {order.delivery_address}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}