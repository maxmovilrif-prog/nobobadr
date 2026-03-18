# 📊 Database Schema - Nubo Express

## 🗄️ Base de Datos: MongoDB

**Estado:** ✅ Implementado y funcionando

---

## 📁 Collections (Tablas)

### 1. **users** 👤

Almacena todos los usuarios: clientes, conductores (Abejas 🐝) y negocios.

```javascript
{
  _id: ObjectId,
  id: "uuid-v4",  // String UUID
  name: "José García",
  email: "jose@example.com",  // Único
  phone: "+34654242092",
  password: "bcrypt_hash",  // Encriptado
  role: "customer|driver|business",
  
  // Solo para drivers (Abejas 🐝):
  vehicle_type: "bike|motorcycle|car|van",
  is_available: true|false,
  
  created_at: "2025-01-20T10:30:00Z"
}
```

**Índices:**
- `email` (único)
- `role`
- `id` (único)

---

### 2. **businesses** 🏪

Negocios: restaurantes, supermercados, tiendas, etc.

```javascript
{
  _id: ObjectId,
  id: "uuid-v4",
  owner_id: "user-uuid",  // Referencia a users
  name: "Restaurante El Patio",
  category: "restaurant|supermarket|courier|vehicles|electronics|transport",
  description: "Comida tradicional española",
  address: "Calle Mayor 1, Madrid",
  image_url: "https://...",
  created_at: "2025-01-20T10:30:00Z"
}
```

**Índices:**
- `owner_id`
- `category`
- `id` (único)

---

### 3. **products** 🍕

Productos de cada negocio.

```javascript
{
  _id: ObjectId,
  id: "uuid-v4",
  business_id: "business-uuid",  // Referencia a businesses
  name: "Pizza Margarita",
  description: "Tomate, mozzarella, albahaca",
  price: 12.50,
  category: "food|electronics|vehicles|other",
  image_url: "https://...",
  available: true,
  created_at: "2025-01-20T10:30:00Z"
}
```

**Índices:**
- `business_id`
- `category`
- `available`

---

### 4. **orders** 📦

Pedidos de clientes.

```javascript
{
  _id: ObjectId,
  id: "uuid-v4",
  customer_id: "user-uuid",  // Cliente que hace el pedido
  driver_id: "user-uuid",  // Conductor asignado (Abeja 🐝)
  business_id: "business-uuid",  // Negocio del pedido
  
  items: [
    {
      product_id: "product-uuid",
      product_name: "Pizza Margarita",
      quantity: 2,
      price: 12.50
    }
  ],
  
  total: 25.00,
  delivery_address: "Calle Sol 5, Madrid",
  
  // Coordenadas GPS para tracking:
  pickup_location: {
    address: "Restaurante...",
    coordinates: { lat: 40.4167, lng: -3.7038 }
  },
  delivery_location: {
    address: "Cliente...",
    coordinates: { lat: 40.4200, lng: -3.7050 }
  },
  
  status: "pending|accepted|preparing|in_transit|delivered|cancelled",
  payment_status: "unpaid|paid",
  stripe_session_id: "cs_test_...",
  
  created_at: "2025-01-20T10:30:00Z",
  updated_at: "2025-01-20T10:35:00Z"
}
```

**Índices:**
- `customer_id`
- `driver_id`
- `status`
- `payment_status`

---

### 5. **messages** 💬

Chat entre cliente y conductor.

```javascript
{
  _id: ObjectId,
  id: "uuid-v4",
  order_id: "order-uuid",
  sender_id: "user-uuid",
  sender_role: "customer|driver",
  message: "Ya voy de camino",
  created_at: "2025-01-20T10:30:00Z"
}
```

**Índices:**
- `order_id`
- `created_at`

---

### 6. **dropshipping_products** 🌐

Productos de dropshipping (Alibaba, AliExpress, Temu).

```javascript
{
  _id: ObjectId,
  id: "uuid-v4",
  business_id: "business-uuid",
  name: "Smartwatch XYZ",
  platform: "alibaba|aliexpress|temu",
  original_price: 20.00,  // Precio del proveedor
  selling_price: 25.00,  // Precio al cliente
  commission: 5.00,  // Ganancia (15-25%)
  product_url: "https://alibaba.com/...",
  shipping_time: "15-25 días",
  category: "electronics|clothing|home|other",
  created_at: "2025-01-20T10:30:00Z"
}
```

**Índices:**
- `business_id`
- `platform`

---

### 7. **affiliate_links** ✈️

Enlaces de afiliados para viajes (vuelos, ferries, hoteles).

```javascript
{
  _id: ObjectId,
  id: "uuid-v4",
  flights_url: "https://skyscanner.com/?aid=...",
  flights_provider: "Skyscanner",
  ferries_url: "https://directferries.com/?aid=...",
  ferries_provider: "Direct Ferries",
  hotels_url: "https://booking.com/?aid=...",
  hotels_provider: "Booking.com",
  updated_at: "2025-01-20T10:30:00Z"
}
```

**Nota:** Solo existe 1 documento (configuración global).

---

## 🐝 **Tracking en Tiempo Real (In-Memory)**

### **driver_locations** (ConnectionManager)

**No se guarda en BD, solo en memoria del servidor:**

```python
{
  "order-uuid-123": {
    "lat": 40.4167,
    "lng": -3.7038,
    "driver_name": "José García",
    "status": "en_camino",
    "timestamp": "2025-01-20T10:30:00Z"
  }
}
```

**Por qué en memoria:**
- ✅ Actualización cada 5 segundos
- ✅ No saturar la base de datos
- ✅ Más rápido para WebSockets
- ✅ Se pierde al reiniciar (normal, no importa)

**Alternativa (si quieres persistencia):**

Crear collection `driver_tracking`:
```javascript
{
  order_id: "uuid",
  driver_id: "uuid",
  lat: 40.4167,
  lng: -3.7038,
  timestamp: "2025-01-20T10:30:00Z"
}
```

---

## 🔄 **Equivalencia SQL vs MongoDB Actual**

### **Tu Schema SQL → Nubo Express MongoDB**

| SQL Table | MongoDB Collection | Estado |
|-----------|-------------------|--------|
| users | users | ✅ Implementado |
| bees | users (role=driver) | ✅ Implementado |
| orders | orders | ✅ Implementado |
| - | businesses | ✅ Extra |
| - | products | ✅ Extra |
| - | messages | ✅ Extra |
| - | dropshipping_products | ✅ Extra |
| - | affiliate_links | ✅ Extra |

---

## 📊 **Relaciones (Referencias)**

```
users (customer)
  └─> orders (customer_id)
      └─> businesses (business_id)
          └─> products (business_id)
      └─> users (driver_id) [Abeja 🐝]
      └─> messages (order_id)
```

---

## 🚀 **Optimizaciones Implementadas**

### **1. Batch Fetching (Anti N+1)**
```python
# ✅ CORRECTO - Una sola query
products_map = {p['id']: p for p in await db.products.find({'id': {'$in': product_ids}})}

# ❌ INCORRECTO - Query por cada producto
for item in items:
    product = await db.products.find_one({'id': item.product_id})
```

### **2. Índices**
- `users.email` (único)
- `orders.status`
- `orders.customer_id`
- `products.business_id`

---

## 💾 **Migración a PostgreSQL (Opcional)**

Si en el futuro quieres PostgreSQL, aquí está el schema SQL completo:

```sql
-- Users (Usuarios + Drivers + Business)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) CHECK (role IN ('customer', 'driver', 'business')),
    vehicle_type VARCHAR(50),
    is_available BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Businesses (Negocios)
CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    address TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products (Productos)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50),
    image_url TEXT,
    available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders (Pedidos)
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES users(id),
    driver_id UUID REFERENCES users(id),
    business_id UUID REFERENCES businesses(id),
    items JSONB NOT NULL,  -- Array de productos
    total DECIMAL(10, 2) NOT NULL,
    delivery_address TEXT NOT NULL,
    pickup_location JSONB,  -- {address, coordinates}
    delivery_location JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    payment_status VARCHAR(20) DEFAULT 'unpaid',
    stripe_session_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages (Chat)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id),
    sender_id UUID REFERENCES users(id),
    sender_role VARCHAR(20),
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_driver ON orders(driver_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_products_business ON products(business_id);
CREATE INDEX idx_messages_order ON messages(order_id);
```

---

## ✅ **Resumen**

**Estado Actual:**
- ✅ MongoDB implementado y funcionando
- ✅ Todos los schemas necesarios creados
- ✅ Optimizado para producción
- ✅ WebSocket tracking funcionando
- ✅ Sin problemas

**Recomendación:**
- ✅ **Mantener MongoDB** (más fácil, ya funciona)
- ⚠️ Migrar a PostgreSQL solo si tienes razones específicas

---

**📧 Contacto:** exprenobo@hotmail.com  
**📱 Teléfono:** +34 654 24 20 92  
**🌐 Dominio:** noboexpress.com
