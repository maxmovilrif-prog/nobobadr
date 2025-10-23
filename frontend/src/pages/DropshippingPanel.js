import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { ShoppingCart, ExternalLink, DollarSign, Package, TrendingUp, ArrowLeft, Plus, Copy } from 'lucide-react';

export default function DropshippingPanel() {
  const navigate = useNavigate();
  const { user, token, API } = useContext(AuthContext);
  const [ordersToPurchase, setOrdersToPurchase] = useState([]);
  const [stats, setStats] = useState(null);
  const [products, setProducts] = useState([]);
  const [showAddProduct, setShowAddProduct] = useState(false);
  const [loading, setLoading] = useState(false);

  const [newProduct, setNewProduct] = useState({
    name: '',
    description: '',
    original_price: '',
    commission_percentage: '20',
    platform: 'alibaba',
    product_url: '',
    image_url: '',
    category: '',
    shipping_time: '15-25 días'
  });

  useEffect(() => {
    if (user && user.role === 'business') {
      fetchOrdersToPurchase();
      fetchStats();
      fetchProducts();
    }
  }, [user]);

  const fetchOrdersToPurchase = async () => {
    try {
      const response = await axios.get(`${API}/dropshipping/orders-to-purchase`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOrdersToPurchase(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dropshipping/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API}/dropshipping/products`);
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const handleAddProduct = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/dropshipping/products`, {
        ...newProduct,
        original_price: parseFloat(newProduct.original_price),
        commission_percentage: parseFloat(newProduct.commission_percentage)
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Producto añadido exitosamente');
      setShowAddProduct(false);
      setNewProduct({
        name: '',
        description: '',
        original_price: '',
        commission_percentage: '20',
        platform: 'alibaba',
        product_url: '',
        image_url: '',
        category: '',
        shipping_time: '15-25 días'
      });
      fetchProducts();
    } catch (error) {
      toast.error('Error al añadir producto');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copiado al portapapeles');
  };

  const getPlatformBadge = (platform) => {
    const colors = {
      alibaba: 'bg-orange-100 text-orange-700',
      temu: 'bg-purple-100 text-purple-700',
      aliexpress: 'bg-red-100 text-red-700'
    };
    return colors[platform] || 'bg-gray-100 text-gray-700';
  };

  if (!user || user.role !== 'business') {
    return (
      <div className=\"min-h-screen flex items-center justify-center\">
        <p>Acceso solo para cuentas de negocio</p>
      </div>
    );
  }

  return (
    <div className=\"min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50\">
      {/* Header */}
      <header className=\"glass sticky top-0 z-50 shadow-md\">
        <div className=\"max-w-7xl mx-auto px-6 py-4 flex items-center justify-between\">
          <Button data-testid=\"back-btn\" onClick={() => navigate('/dashboard')} variant=\"ghost\">
            <ArrowLeft className=\"w-4 h-4 mr-2\" />
            Volver al Dashboard
          </Button>
          <h1 className=\"text-2xl font-bold text-gray-900\">Panel Dropshipping</h1>
          <div className=\"w-32\"></div>
        </div>
      </header>

      <div className=\"max-w-7xl mx-auto px-6 py-8\">
        {/* Stats Cards */}
        {stats && (
          <div className=\"grid md:grid-cols-3 gap-6 mb-8\">
            <Card className=\"border-0 shadow-lg\">
              <CardContent className=\"p-6\">
                <div className=\"flex items-center justify-between\">
                  <div>
                    <p className=\"text-sm text-gray-600\">Pedidos Totales</p>
                    <p className=\"text-3xl font-bold text-gray-900\">{stats.total_orders}</p>
                  </div>
                  <Package className=\"w-12 h-12 text-emerald-600\" />
                </div>
              </CardContent>
            </Card>

            <Card className=\"border-0 shadow-lg\">
              <CardContent className=\"p-6\">
                <div className=\"flex items-center justify-between\">
                  <div>
                    <p className=\"text-sm text-gray-600\">Comisión Total</p>
                    <p className=\"text-3xl font-bold text-emerald-600\">€{stats.total_commission.toFixed(2)}</p>
                  </div>
                  <DollarSign className=\"w-12 h-12 text-emerald-600\" />
                </div>
              </CardContent>
            </Card>

            <Card className=\"border-0 shadow-lg\">
              <CardContent className=\"p-6\">
                <div className=\"flex items-center justify-between\">
                  <div>
                    <p className=\"text-sm text-gray-600\">Productos Activos</p>
                    <p className=\"text-3xl font-bold text-gray-900\">{products.length}</p>
                  </div>
                  <TrendingUp className=\"w-12 h-12 text-emerald-600\" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue=\"orders\" className=\"w-full\">
          <TabsList className=\"mb-6\">
            <TabsTrigger data-testid=\"orders-tab\" value=\"orders\">Pedidos Pendientes</TabsTrigger>
            <TabsTrigger data-testid=\"products-tab\" value=\"products\">Mis Productos</TabsTrigger>
          </TabsList>

          {/* Orders to Purchase */}
          <TabsContent value=\"orders\">
            <div className=\"flex justify-between items-center mb-6\">
              <h2 className=\"text-2xl font-bold\">Pedidos para Comprar</h2>
              <Badge className=\"bg-red-500 text-white text-lg px-4 py-2\">
                {ordersToPurchase.length} pendientes
              </Badge>
            </div>

            {ordersToPurchase.length === 0 ? (
              <Card>
                <CardContent className=\"p-12 text-center\">
                  <ShoppingCart className=\"w-16 h-16 mx-auto mb-4 text-gray-400\" />
                  <p className=\"text-gray-600\">No hay pedidos pendientes de compra</p>
                </CardContent>
              </Card>
            ) : (
              <div className=\"grid gap-6\">
                {ordersToPurchase.map((order, idx) => (
                  <Card key={idx} data-testid={`order-${idx}`} className=\"border-l-4 border-l-emerald-500 shadow-lg\">
                    <CardHeader>
                      <div className=\"flex items-center justify-between\">
                        <CardTitle>Pedido #{order.order_id.slice(0, 8)}</CardTitle>
                        <Badge className={getPlatformBadge(order.platform)}>
                          {order.platform.toUpperCase()}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className=\"grid md:grid-cols-2 gap-6\">
                        {/* Product Info */}
                        <div>
                          <h4 className=\"font-semibold text-lg mb-3\">{order.product_name}</h4>
                          <div className=\"space-y-2 text-sm\">
                            <p><span className=\"font-medium\">Cantidad:</span> {order.quantity} unidades</p>
                            <p><span className=\"font-medium\">Precio Original:</span> €{order.original_price.toFixed(2)} c/u</p>
                            <p><span className=\"font-medium text-red-600\">Total a Pagar:</span> €{order.total_to_pay.toFixed(2)}</p>
                            <p><span className=\"font-medium text-emerald-600\">Tu Comisión:</span> €{order.commission_earned.toFixed(2)}</p>
                          </div>

                          <div className=\"mt-4\">
                            <Label className=\"text-sm font-medium mb-1 block\">URL del Producto:</Label>
                            <div className=\"flex gap-2\">
                              <Input 
                                value={order.product_url} 
                                readOnly 
                                className=\"text-sm\"
                              />
                              <Button 
                                size=\"sm\"
                                variant=\"outline\"
                                onClick={() => copyToClipboard(order.product_url)}
                              >
                                <Copy className=\"w-4 h-4\" />
                              </Button>
                              <Button
                                size=\"sm\"
                                onClick={() => window.open(order.product_url, '_blank')}
                                className=\"bg-emerald-600\"
                              >
                                <ExternalLink className=\"w-4 h-4\" />
                              </Button>
                            </div>
                          </div>
                        </div>

                        {/* Customer Info */}
                        <div className=\"bg-gray-50 rounded-lg p-4\">
                          <h5 className=\"font-semibold mb-3\">Información del Cliente</h5>
                          <div className=\"space-y-2 text-sm\">
                            <p><span className=\"font-medium\">Nombre:</span> {order.customer_name}</p>
                            <p><span className=\"font-medium\">Email:</span> {order.customer_email}</p>
                            <p><span className=\"font-medium\">Teléfono:</span> {order.customer_phone}</p>
                            <div className=\"pt-2 border-t mt-3\">
                              <p className=\"font-medium mb-1\">Dirección de Envío:</p>
                              <p className=\"text-gray-700\">{order.delivery_address}</p>
                              <Button
                                size=\"sm\"
                                variant=\"outline\"
                                className=\"mt-2\"
                                onClick={() => copyToClipboard(order.delivery_address)}
                              >
                                <Copy className=\"w-3 h-3 mr-2\" />
                                Copiar Dirección
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className=\"mt-4 p-4 bg-blue-50 rounded-lg\">
                        <p className=\"text-sm text-blue-900\">
                          <strong>Instrucciones:</strong> Compra este producto en {order.platform.toUpperCase()} 
                          usando el enlace de arriba. Envíalo a la dirección del cliente y marca como enviado en el sistema.
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Products Management */}
          <TabsContent value=\"products\">
            <div className=\"flex justify-between items-center mb-6\">
              <h2 className=\"text-2xl font-bold\">Mis Productos Dropshipping</h2>
              <Dialog open={showAddProduct} onOpenChange={setShowAddProduct}>
                <DialogTrigger asChild>
                  <Button data-testid=\"add-product-btn\" className=\"bg-emerald-600\">
                    <Plus className=\"w-4 h-4 mr-2\" />
                    Añadir Producto
                  </Button>
                </DialogTrigger>
                <DialogContent className=\"max-w-2xl\">
                  <DialogHeader>
                    <DialogTitle>Añadir Producto de Alibaba/Temu/AliExpress</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleAddProduct} className=\"space-y-4\">
                    <div className=\"grid md:grid-cols-2 gap-4\">
                      <div>
                        <Label>Nombre del Producto</Label>
                        <Input
                          value={newProduct.name}
                          onChange={(e) => setNewProduct({...newProduct, name: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Categoría</Label>
                        <Input
                          value={newProduct.category}
                          onChange={(e) => setNewProduct({...newProduct, category: e.target.value})}
                          placeholder=\"Ej: Electrónica\"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <Label>Descripción</Label>
                      <Textarea
                        value={newProduct.description}
                        onChange={(e) => setNewProduct({...newProduct, description: e.target.value})}
                        required
                      />
                    </div>

                    <div className=\"grid md:grid-cols-3 gap-4\">
                      <div>
                        <Label>Precio Original (€)</Label>
                        <Input
                          type=\"number\"
                          step=\"0.01\"
                          value={newProduct.original_price}
                          onChange={(e) => setNewProduct({...newProduct, original_price: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Comisión (%)</Label>
                        <Input
                          type=\"number\"
                          step=\"1\"
                          value={newProduct.commission_percentage}
                          onChange={(e) => setNewProduct({...newProduct, commission_percentage: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Precio de Venta</Label>
                        <Input
                          value={newProduct.original_price && newProduct.commission_percentage ? 
                            `€${(parseFloat(newProduct.original_price) * (1 + parseFloat(newProduct.commission_percentage) / 100)).toFixed(2)}` : 
                            '€0.00'}
                          readOnly
                          className=\"bg-gray-100\"
                        />
                      </div>
                    </div>

                    <div className=\"grid md:grid-cols-2 gap-4\">
                      <div>
                        <Label>Plataforma</Label>
                        <Select value={newProduct.platform} onValueChange={(value) => setNewProduct({...newProduct, platform: value})}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value=\"alibaba\">Alibaba</SelectItem>
                            <SelectItem value=\"temu\">Temu</SelectItem>
                            <SelectItem value=\"aliexpress\">AliExpress</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Tiempo de Envío</Label>
                        <Input
                          value={newProduct.shipping_time}
                          onChange={(e) => setNewProduct({...newProduct, shipping_time: e.target.value})}
                        />
                      </div>
                    </div>

                    <div>
                      <Label>URL del Producto</Label>
                      <Input
                        value={newProduct.product_url}
                        onChange={(e) => setNewProduct({...newProduct, product_url: e.target.value})}
                        placeholder=\"https://www.alibaba.com/product/...\"
                        required
                      />
                    </div>

                    <div>
                      <Label>URL de Imagen</Label>
                      <Input
                        value={newProduct.image_url}
                        onChange={(e) => setNewProduct({...newProduct, image_url: e.target.value})}
                        placeholder=\"https://...\"
                        required
                      />
                    </div>

                    <Button type=\"submit\" disabled={loading} className=\"w-full bg-emerald-600\">
                      {loading ? 'Añadiendo...' : 'Añadir Producto'}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
            </div>

            <div className=\"grid md:grid-cols-2 lg:grid-cols-3 gap-6\">
              {products.map(product => (
                <Card key={product.id} className=\"hover-lift\">
                  <div className=\"aspect-square bg-gray-100 overflow-hidden rounded-t-lg\">
                    <img src={product.image_url} alt={product.name} className=\"w-full h-full object-cover\" />
                  </div>
                  <CardContent className=\"p-4\">
                    <Badge className={getPlatformBadge(product.platform)} size=\"sm\">
                      {product.platform.toUpperCase()}
                    </Badge>
                    <h3 className=\"font-semibold text-lg mt-2\">{product.name}</h3>
                    <p className=\"text-sm text-gray-600 mt-1\">{product.category}</p>
                    <div className=\"mt-3 space-y-1 text-sm\">
                      <div className=\"flex justify-between\">
                        <span>Precio Original:</span>
                        <span>€{product.original_price.toFixed(2)}</span>
                      </div>
                      <div className=\"flex justify-between\">
                        <span>Comisión ({product.commission_percentage}%):</span>
                        <span className=\"text-emerald-600\">€{(product.selling_price - product.original_price).toFixed(2)}</span>
                      </div>
                      <div className=\"flex justify-between font-semibold border-t pt-1\">
                        <span>Precio de Venta:</span>
                        <span className=\"text-lg text-emerald-600\">€{product.selling_price.toFixed(2)}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
