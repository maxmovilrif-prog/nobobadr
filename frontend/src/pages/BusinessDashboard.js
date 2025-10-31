import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { LogOut, Store, Package, ShoppingBag, Plus, Globe } from 'lucide-react';

export default function BusinessDashboard() {
  const { user, token, logout, API } = useContext(AuthContext);
  const [businesses, setBusinesses] = useState([]);
  const [selectedBusiness, setSelectedBusiness] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [showBusinessDialog, setShowBusinessDialog] = useState(false);
  const [showProductDialog, setShowProductDialog] = useState(false);
  
  const [businessForm, setBusinessForm] = useState({
    name: '',
    category: 'restaurant',
    description: '',
    address: '',
    phone: '',
    image_url: '',
    delivery_time: '30-45 min'
  });

  const [productForm, setProductForm] = useState({
    name: '',
    description: '',
    price: '',
    image_url: '',
    category: ''
  });

  useEffect(() => {
    fetchBusinesses();
  }, []);

  useEffect(() => {
    if (selectedBusiness) {
      fetchProducts(selectedBusiness.id);
      fetchOrders();
    }
  }, [selectedBusiness]);

  const fetchBusinesses = async () => {
    try {
      const response = await axios.get(`${API}/businesses`);
      const myBusinesses = response.data.filter(b => b.owner_id === user.id);
      setBusinesses(myBusinesses);
      if (myBusinesses.length > 0) {
        setSelectedBusiness(myBusinesses[0]);
      }
    } catch (error) {
      console.error('Error fetching businesses:', error);
    }
  };

  const fetchProducts = async (businessId) => {
    try {
      const response = await axios.get(`${API}/products/${businessId}`);
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
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

  const createBusiness = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/businesses`, businessForm, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Negocio creado exitosamente');
      setShowBusinessDialog(false);
      fetchBusinesses();
      setBusinessForm({
        name: '',
        category: 'restaurant',
        description: '',
        address: '',
        phone: '',
        image_url: '',
        delivery_time: '30-45 min'
      });
    } catch (error) {
      toast.error('Error al crear negocio');
    }
  };

  const createProduct = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/products`, {
        ...productForm,
        business_id: selectedBusiness.id,
        price: parseFloat(productForm.price)
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Producto creado exitosamente');
      setShowProductDialog(false);
      fetchProducts(selectedBusiness.id);
      setProductForm({
        name: '',
        description: '',
        price: '',
        image_url: '',
        category: ''
      });
    } catch (error) {
      toast.error('Error al crear producto');
    }
  };

  const updateOrderStatus = async (orderId, status) => {
    try {
      await axios.patch(`${API}/orders/${orderId}/status`, { status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Estado actualizado');
      fetchOrders();
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
              <Store className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Panel de Negocio</h1>
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
        {businesses.length === 0 ? (
          <Card className="text-center p-12">
            <Store className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h2 className="text-2xl font-bold mb-2">No tienes negocios registrados</h2>
            <p className="text-gray-600 mb-6">Crea tu primer negocio para empezar</p>
            <Dialog open={showBusinessDialog} onOpenChange={setShowBusinessDialog}>
              <DialogTrigger asChild>
                <Button data-testid="create-first-business-btn" className="bg-emerald-600">
                  <Plus className="w-4 h-4 mr-2" />
                  Crear Negocio
                </Button>
              </DialogTrigger>
              <DialogContent data-testid="business-dialog">
                <DialogHeader>
                  <DialogTitle>Crear Nuevo Negocio</DialogTitle>
                </DialogHeader>
                <form onSubmit={createBusiness} className="space-y-4">
                  <div>
                    <Label>Nombre</Label>
                    <Input
                      data-testid="business-name-input"
                      value={businessForm.name}
                      onChange={(e) => setBusinessForm({ ...businessForm, name: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label>Categoría</Label>
                    <Select value={businessForm.category} onValueChange={(value) => setBusinessForm({ ...businessForm, category: value })}>
                      <SelectTrigger data-testid="business-category-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="restaurant">Restaurante</SelectItem>
                        <SelectItem value="supermarket">Supermercado</SelectItem>
                        <SelectItem value="courier">Paquetería</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Descripción</Label>
                    <Textarea
                      data-testid="business-description-input"
                      value={businessForm.description}
                      onChange={(e) => setBusinessForm({ ...businessForm, description: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label>Dirección</Label>
                    <Input
                      data-testid="business-address-input"
                      value={businessForm.address}
                      onChange={(e) => setBusinessForm({ ...businessForm, address: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label>Teléfono</Label>
                    <Input
                      data-testid="business-phone-input"
                      value={businessForm.phone}
                      onChange={(e) => setBusinessForm({ ...businessForm, phone: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label>URL de Imagen</Label>
                    <Input
                      data-testid="business-image-input"
                      value={businessForm.image_url}
                      onChange={(e) => setBusinessForm({ ...businessForm, image_url: e.target.value })}
                      placeholder="https://..."
                      required
                    />
                  </div>
                  <Button data-testid="submit-business-btn" type="submit" className="w-full bg-emerald-600">Crear Negocio</Button>
                </form>
              </DialogContent>
            </Dialog>
          </Card>
        ) : (
          <Tabs defaultValue="products" className="w-full">
            <div className="flex items-center justify-between mb-6">
              <TabsList>
                <TabsTrigger data-testid="products-tab" value="products">Productos</TabsTrigger>
                <TabsTrigger data-testid="orders-tab" value="orders">Pedidos</TabsTrigger>
              </TabsList>
              {selectedBusiness && (
                <div className="flex items-center gap-3">
                  <Badge className="bg-emerald-100 text-emerald-700">{selectedBusiness.name}</Badge>
                </div>
              )}
            </div>

            <TabsContent value="products">
              <div className="flex justify-end mb-6">
                <Dialog open={showProductDialog} onOpenChange={setShowProductDialog}>
                  <DialogTrigger asChild>
                    <Button data-testid="add-product-btn" className="bg-emerald-600">
                      <Plus className="w-4 h-4 mr-2" />
                      Añadir Producto
                    </Button>
                  </DialogTrigger>
                  <DialogContent data-testid="product-dialog">
                    <DialogHeader>
                      <DialogTitle>Crear Nuevo Producto</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={createProduct} className="space-y-4">
                      <div>
                        <Label>Nombre</Label>
                        <Input
                          data-testid="product-name-input"
                          value={productForm.name}
                          onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <Label>Descripción</Label>
                        <Textarea
                          data-testid="product-description-input"
                          value={productForm.description}
                          onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <Label>Precio (€)</Label>
                        <Input
                          data-testid="product-price-input"
                          type="number"
                          step="0.01"
                          value={productForm.price}
                          onChange={(e) => setProductForm({ ...productForm, price: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <Label>Categoría</Label>
                        <Input
                          data-testid="product-category-input"
                          value={productForm.category}
                          onChange={(e) => setProductForm({ ...productForm, category: e.target.value })}
                          placeholder="Pizza, Bebidas, etc."
                          required
                        />
                      </div>
                      <div>
                        <Label>URL de Imagen</Label>
                        <Input
                          data-testid="product-image-input"
                          value={productForm.image_url}
                          onChange={(e) => setProductForm({ ...productForm, image_url: e.target.value })}
                          placeholder="https://..."
                          required
                        />
                      </div>
                      <Button data-testid="submit-product-btn" type="submit" className="w-full bg-emerald-600">Crear Producto</Button>
                    </form>
                  </DialogContent>
                </Dialog>
              </div>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {products.map(product => (
                  <Card key={product.id} data-testid={`product-card-${product.id}`} className="hover-lift">
                    <div className="aspect-square bg-gradient-to-br from-emerald-400 to-teal-500 rounded-t-lg overflow-hidden">
                      <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
                    </div>
                    <CardContent className="p-4">
                      <h3 className="font-semibold text-lg mb-1">{product.name}</h3>
                      <p className="text-sm text-gray-600 mb-2">{product.description}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-xl font-bold text-emerald-600">€{product.price.toFixed(2)}</span>
                        <Badge>{product.category}</Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="orders">
              <div className="space-y-4">
                {orders.length === 0 ? (
                  <Card>
                    <CardContent className="p-12 text-center">
                      <Package className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                      <p className="text-gray-600">No hay pedidos aún</p>
                    </CardContent>
                  </Card>
                ) : (
                  orders.map(order => (
                    <Card key={order.id} data-testid={`order-card-${order.id}`} className="hover-lift">
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <h3 className="font-semibold text-lg">Pedido #{order.id.slice(0, 8)}</h3>
                            <p className="text-sm text-gray-600">{new Date(order.created_at).toLocaleString('es-ES')}</p>
                          </div>
                          <div className="text-right">
                            <Badge>{order.status}</Badge>
                            <p className="text-lg font-bold text-emerald-600 mt-1">€{order.total_amount.toFixed(2)}</p>
                          </div>
                        </div>
                        <div className="mb-4">
                          <p className="text-sm font-medium mb-2">Items:</p>
                          {order.items.map((item, idx) => (
                            <p key={idx} className="text-sm text-gray-600">
                              {item.quantity}x {item.product_name} - €{(item.price * item.quantity).toFixed(2)}
                            </p>
                          ))}
                        </div>
                        {order.status === 'pending' && (
                          <div className="flex gap-2">
                            <Button
                              data-testid={`accept-order-${order.id}`}
                              onClick={() => updateOrderStatus(order.id, 'preparing')}
                              className="flex-1 bg-emerald-600"
                              size="sm"
                            >
                              Aceptar
                            </Button>
                            <Button
                              data-testid={`reject-order-${order.id}`}
                              onClick={() => updateOrderStatus(order.id, 'cancelled')}
                              variant="outline"
                              size="sm"
                            >
                              Rechazar
                            </Button>
                          </div>
                        )}
                        {order.status === 'preparing' && (
                          <Button
                            data-testid={`mark-ready-${order.id}`}
                            onClick={() => updateOrderStatus(order.id, 'ready')}
                            className="w-full bg-blue-600"
                            size="sm"
                          >
                            Marcar como Listo
                          </Button>
                        )}
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}