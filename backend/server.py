from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header, WebSocket, WebSocketDisconnect, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from pymongo import ReturnDocument
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import sys
import hmac
import csv
import io
import httpx
from enum import Enum
sys.path.append(str(Path(__file__).parent))

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Conexión a MongoDB y autenticación: viven en db.py / auth.py (ver esos
# archivos) para que cualquier router de la app -incluido dropshipping_routes.py-
# pueda importarlos sin crear un import circular con server.py.
from db import client, db
from auth import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, security,
    hash_password, verify_password, create_token, get_current_user,
)

def db_error(endpoint: str, e: Exception) -> HTTPException:
    """Registra un error de base de datos con detalle (nombre de db, tipo y mensaje)
    y devuelve un HTTP 503 descriptivo. Útil para diagnosticar fallos de autorización
    de la MongoDB gestionada en producción (p.ej. 'not authorized on <db> ...')."""
    db_name = os.environ.get('DB_NAME', '?')
    logger.error(
        "DB ERROR en %s | base de datos='%s' | tipo=%s | detalle=%s",
        endpoint, db_name, type(e).__name__, str(e)
    )
    return HTTPException(
        status_code=503,
        detail=f"Error de base de datos en {endpoint} (db='{db_name}'): {type(e).__name__}: {e}"
    )

# Stripe Configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', 'sk_test_emergent')

# Emergent LLM Key (AI Smart Search)
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Separate Admin Portal Configuration
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
ADMIN_SECRET_CODE = os.environ.get('ADMIN_SECRET_CODE')
ADMIN_MAX_ATTEMPTS = 5
ADMIN_LOCKOUT_MINUTES = 15

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Router de dropshipping (productos, ciclo de vida de pedidos, comisiones).
# Ya no hay riesgo de import circular: dropshipping_routes.py importa `db`
# desde db.py y `get_current_user` desde auth.py, no desde este archivo.
from dropshipping_routes import router as dropshipping_router, create_dropship_orders_for_order


# =========================
# MODELS
# =========================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    phone: str
    role: str  # customer, driver, business
    password_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Driver specific
    is_available: bool = False
    status: str = "offline"  # available | busy | offline (estado operativo de la Abeja)
    vehicle_type: Optional[str] = None
    current_location: Optional[Dict[str, float]] = None

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    phone: str
    password: str
    role: str
    vehicle_type: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: str
    role: str
    is_available: bool = False
    vehicle_type: Optional[str] = None

class Business(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    name: str
    category: str  # restaurant, supermarket, courier
    description: str
    address: str
    phone: str
    image_url: str
    rating: float = 0.0
    delivery_time: str
    is_open: bool = True
    bank_account: Optional[str] = None  # IBAN / cuenta para el pago de comisiones
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BusinessCreate(BaseModel):
    name: str
    category: str
    description: str
    address: str
    phone: str
    image_url: str
    delivery_time: str
    bank_account: Optional[str] = None

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    business_id: str
    name: str
    description: str
    price: float
    image_url: str
    category: str
    available: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    business_id: str
    name: str
    description: str
    price: float
    image_url: str
    category: str

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    price: float

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    business_id: Optional[str] = None
    driver_id: Optional[str] = None
    items: List[OrderItem] = []
    total_amount: float
    delivery_address: str
    city_id: Optional[str] = None
    city_name: Optional[str] = None
    status: str  # pending, accepted, preparing, ready, in_transit, delivered, cancelled
    payment_status: str = "pending"  # pending, paid, failed
    payment_session_id: Optional[str] = None
    # Pedido exprés (mensajería punto a punto A->B)
    order_type: str = "marketplace"  # marketplace | express
    vehicle_type: Optional[str] = None
    origin_name: Optional[str] = None
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_name: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    distance_km: Optional[float] = None
    eta_mins: Optional[int] = None
    currency: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    business_id: str
    items: List[OrderItem]
    delivery_address: str
    city_id: Optional[str] = None

class ExpressOrderCreate(BaseModel):
    origin_name: str
    origin_lat: float
    origin_lng: float
    destination_name: str
    destination_lat: float
    destination_lng: float
    origin_city_id: Optional[str] = None
    vehicle_type: str
    fee: float
    currency: str = "EUR"
    distance_km: Optional[float] = None
    eta_mins: Optional[int] = None

class OrderStatusUpdate(BaseModel):
    status: str

class City(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    lat: float
    lng: float
    country: str = "ES"

class CityCreate(BaseModel):
    name: str
    lat: float
    lng: float
    country: str = "ES"

class CityUpdate(BaseModel):
    name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    country: Optional[str] = None

# Radio de zona de trabajo (km) para el geofencing de repartidores
CITY_ZONE_RADIUS_KM = 10
# Máx. intentos de la asignación atómica del repartidor (anti condición de carrera)
ASSIGN_MAX_ATTEMPTS = 3

def haversine_km(lat1, lng1, lat2, lng2):
    """Distancia en km entre dos puntos (lat/lng)."""
    R = 6371.0
    from math import radians, sin, cos, sqrt, atan2
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

async def get_driver_city(driver):
    """Determina la ciudad/zona del repartidor según su GPS (centro de ciudad ≤ radio)."""
    loc = (driver or {}).get('current_location') or {}
    lat, lng = loc.get('lat'), loc.get('lng')
    if lat is None or lng is None:
        return None
    cities = await db.cities.find({}, {'_id': 0}).to_list(1000)
    best, best_dist = None, None
    for c in cities:
        d = haversine_km(lat, lng, c['lat'], c['lng'])
        if d <= CITY_ZONE_RADIUS_KM and (best_dist is None or d < best_dist):
            best, best_dist = c, d
    return best

class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    sender_id: str
    sender_role: str
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MessageCreate(BaseModel):
    order_id: str
    message: str

class PaymentTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    order_id: str
    user_id: str
    amount: float
    currency: str
    payment_status: str
    metadata: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Nota: hash_password, verify_password, create_token y get_current_user ya
# no se definen aquí — se importan de auth.py al principio del archivo.

# =========================
# AUTH ENDPOINTS
# =========================

@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({'email': user_data.email}, {'_id': 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = user_data.model_dump()
    password = user_dict.pop('password')
    user_dict['password_hash'] = hash_password(password)
    
    user = User(**user_dict)
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    return UserResponse(**user.model_dump())

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({'email': credentials.email}, {'_id': 0})
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Admin accounts cannot authenticate via the public login. They must use the
    # separate, hidden admin portal (/admin-nubo). Return a generic error to avoid
    # revealing that the account exists or is an admin.
    if user.get('role') == 'admin':
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user['id'], user['role'])
    user.pop('password_hash')
    
    return {'token': token, 'user': user}

# =========================
# SEPARATE ADMIN PORTAL AUTH (hidden, server-side protected)
# =========================

class AdminLogin(BaseModel):
    email: EmailStr
    password: str
    secret_code: str

async def _admin_check_lockout(email: str):
    """Devuelve los minutos restantes de bloqueo si la cuenta está bloqueada, si no None."""
    rec = await db.admin_login_attempts.find_one({'email': email}, {'_id': 0})
    if rec and rec.get('locked_until'):
        locked_until = datetime.fromisoformat(rec['locked_until'])
        now = datetime.now(timezone.utc)
        if locked_until > now:
            return max(1, int((locked_until - now).total_seconds() // 60) + 1)
    return None

async def _admin_record_failure(email: str):
    """Incrementa intentos fallidos y bloquea tras ADMIN_MAX_ATTEMPTS."""
    rec = await db.admin_login_attempts.find_one({'email': email}, {'_id': 0})
    count = (rec.get('failed_count', 0) if rec else 0) + 1
    update = {'email': email, 'failed_count': count, 'updated_at': datetime.now(timezone.utc).isoformat(), 'locked_until': None}
    if count >= ADMIN_MAX_ATTEMPTS:
        update['locked_until'] = (datetime.now(timezone.utc) + timedelta(minutes=ADMIN_LOCKOUT_MINUTES)).isoformat()
        update['failed_count'] = 0  # reset counter once locked
    await db.admin_login_attempts.update_one({'email': email}, {'$set': update}, upsert=True)
    return max(0, ADMIN_MAX_ATTEMPTS - count)

async def _admin_reset_attempts(email: str):
    await db.admin_login_attempts.delete_one({'email': email})

@api_router.post("/admin-auth/login")
async def admin_login(credentials: AdminLogin):
    """Login exclusivo del portal admin: email + contraseña + código secreto.
    Incluye bloqueo anti fuerza bruta. Validación 100% en servidor."""
    email = credentials.email.lower().strip()

    try:
        locked_minutes = await _admin_check_lockout(email)
        if locked_minutes:
            raise HTTPException(status_code=429, detail=f"Demasiados intentos. Cuenta bloqueada {locked_minutes} min.")

        user = await db.users.find_one({'email': email}, {'_id': 0})

        password_ok = bool(user) and user.get('role') == 'admin' and verify_password(credentials.password, user['password_hash'])
        code_ok = bool(ADMIN_SECRET_CODE) and hmac.compare_digest(str(credentials.secret_code), str(ADMIN_SECRET_CODE))

        if not (password_ok and code_ok):
            remaining = await _admin_record_failure(email)
            detail = "Credenciales o código de acceso inválidos."
            if remaining <= 2 and remaining > 0:
                detail += f" Te quedan {remaining} intento(s) antes del bloqueo."
            raise HTTPException(status_code=401, detail=detail)

        await _admin_reset_attempts(email)
        token = create_token(user['id'], user['role'])
        user.pop('password_hash', None)
        return {'token': token, 'user': user}
    except HTTPException:
        raise
    except Exception as e:
        raise db_error("POST /admin-auth/login", e)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

# =========================
# BUSINESS ENDPOINTS
# =========================

@api_router.post("/businesses", response_model=Business)
async def create_business(business_data: BusinessCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can create businesses")
    
    business_dict = business_data.model_dump()
    business_dict['owner_id'] = current_user['id']
    
    business = Business(**business_dict)
    doc = business.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.businesses.insert_one(doc)
    return business

@api_router.get("/businesses", response_model=List[Business])
async def get_businesses(category: Optional[str] = None):
    query = {} if not category else {'category': category}
    businesses = await db.businesses.find(query, {'_id': 0}).to_list(1000)
    
    for business in businesses:
        if isinstance(business.get('created_at'), str):
            business['created_at'] = datetime.fromisoformat(business['created_at'])
    
    return businesses

@api_router.get("/businesses/{business_id}", response_model=Business)
async def get_business(business_id: str):
    business = await db.businesses.find_one({'id': business_id}, {'_id': 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    if isinstance(business.get('created_at'), str):
        business['created_at'] = datetime.fromisoformat(business['created_at'])
    
    return business

# =========================
# PRODUCT ENDPOINTS
# =========================

@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can create products")
    
    # Verify business ownership
    business = await db.businesses.find_one({'id': product_data.business_id, 'owner_id': current_user['id']}, {'_id': 0})
    if not business:
        raise HTTPException(status_code=403, detail="Not authorized for this business")
    
    product = Product(**product_data.model_dump())
    doc = product.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.products.insert_one(doc)
    return product

@api_router.get("/products/{business_id}", response_model=List[Product])
async def get_products(business_id: str):
    products = await db.products.find({'business_id': business_id}, {'_id': 0}).to_list(1000)
    
    for product in products:
        if isinstance(product.get('created_at'), str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    
    return products

# =========================
# ORDER ENDPOINTS
# =========================

@api_router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers can create orders")

    if not order_data.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    # Seguridad: el precio NUNCA se confía del cliente. order_data.items[i].price
    # venía directamente del JSON enviado por el navegador, así que cualquiera
    # podía manipularlo (p.ej. mandar price=0.01) y pagar lo que quisiera vía
    # Stripe, ya que el total se usaba tal cual en create_checkout_session.
    # Aquí se recalcula cada precio a partir del producto real en la base de
    # datos, ignorando por completo lo que mande el cliente.
    verified_items = []
    total = 0.0
    for item in order_data.items:
        if item.quantity < 1:
            raise HTTPException(status_code=400, detail="Quantity must be at least 1")

        product = await db.products.find_one(
            {'id': item.product_id, 'business_id': order_data.business_id}, {'_id': 0}
        )
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found for this business")
        if not product.get('available', True):
            raise HTTPException(status_code=400, detail=f"Product '{product['name']}' is not available")

        real_price = product['price']
        verified_items.append(OrderItem(
            product_id=product['id'],
            product_name=product['name'],
            quantity=item.quantity,
            price=real_price
        ))
        total += real_price * item.quantity

    order_dict = order_data.model_dump()
    order_dict['items'] = [vi.model_dump() for vi in verified_items]
    order_dict['customer_id'] = current_user['id']
    order_dict['total_amount'] = round(total, 2)
    order_dict['status'] = 'pending'
    try:
        # Resolver nombre de ciudad si se indicó city_id
        if order_dict.get('city_id'):
            city = await db.cities.find_one({'id': order_dict['city_id']}, {'_id': 0, 'name': 1})
            order_dict['city_name'] = city['name'] if city else None

        order = Order(**order_dict)
        doc = order.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()

        await db.orders.insert_one(doc)
        return order
    except Exception as e:
        raise db_error("POST /orders", e)

@api_router.post("/orders/express", response_model=Order)
async def create_express_order(order_data: ExpressOrderCreate, current_user: dict = Depends(get_current_user)):
    """Crea un pedido exprés de mensajería punto a punto (A->B), sin negocio ni carrito."""
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers can create orders")

    # Resolver la ciudad de origen (para el geofencing / auto-despacho)
    try:
        city_name = None
        city_id = order_data.origin_city_id
        if city_id:
            city = await db.cities.find_one({'id': city_id}, {'_id': 0, 'name': 1})
            city_name = city['name'] if city else None

        order = Order(
            customer_id=current_user['id'],
            business_id=None,
            items=[],
            total_amount=order_data.fee,
            delivery_address=order_data.destination_name,
            city_id=city_id,
            city_name=city_name,
            status='pending',
            order_type='express',
            vehicle_type=order_data.vehicle_type,
            origin_name=order_data.origin_name,
            origin_lat=order_data.origin_lat,
            origin_lng=order_data.origin_lng,
            destination_name=order_data.destination_name,
            destination_lat=order_data.destination_lat,
            destination_lng=order_data.destination_lng,
            distance_km=order_data.distance_km,
            eta_mins=order_data.eta_mins,
            currency=order_data.currency,
        )
        doc = order.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()

        await db.orders.insert_one(doc)
        return order
    except Exception as e:
        raise db_error("POST /orders/express", e)

@api_router.get("/orders", response_model=List[Order])
async def get_orders(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user['role'] == 'customer':
        query['customer_id'] = current_user['id']
    elif current_user['role'] == 'driver':
        query['driver_id'] = current_user['id']
    elif current_user['role'] == 'business':
        # Get businesses owned by user
        businesses = await db.businesses.find({'owner_id': current_user['id']}, {'_id': 0}).to_list(100)
        business_ids = [b['id'] for b in businesses]
        query['business_id'] = {'$in': business_ids}
    
    orders = await db.orders.find(query, {'_id': 0}).to_list(1000)
    
    for order in orders:
        if isinstance(order.get('created_at'), str):
            order['created_at'] = datetime.fromisoformat(order['created_at'])
        if isinstance(order.get('updated_at'), str):
            order['updated_at'] = datetime.fromisoformat(order['updated_at'])
    
    return orders

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if isinstance(order.get('created_at'), str):
        order['created_at'] = datetime.fromisoformat(order['created_at'])
    if isinstance(order.get('updated_at'), str):
        order['updated_at'] = datetime.fromisoformat(order['updated_at'])
    
    return order

@api_router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, status_update: OrderStatusUpdate, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Autorización: solo admin, el repartidor asignado o el dueño del negocio del pedido
    role = current_user['role']
    allowed = role == 'admin' or (role == 'driver' and order.get('driver_id') == current_user['id'])
    if not allowed and role == 'business':
        biz = await db.businesses.find_one({'id': order.get('business_id')}, {'_id': 0, 'owner_id': 1})
        allowed = bool(biz) and biz.get('owner_id') == current_user['id']
    if not allowed:
        raise HTTPException(status_code=403, detail="Not authorized to update this order")

    update_fields = {'status': status_update.status, 'updated_at': datetime.now(timezone.utc).isoformat()}
    # Marca de tiempo de entrega para los reportes financieros (pagos por repartidor)
    if status_update.status == 'delivered' and not order.get('delivered_at'):
        update_fields['delivered_at'] = datetime.now(timezone.utc).isoformat()
    await db.orders.update_one({'id': order_id}, {'$set': update_fields})

    # Contabilidad: registrar el ingreso del pedido automáticamente al entregarse (interno, idempotente)
    if status_update.status == 'delivered':
        await _acct_record_order_income({**order, **update_fields})

    # La Abeja vuelve a estar disponible al cerrar el pedido (entregado o cancelado)
    if status_update.status in ('delivered', 'cancelled') and order.get('driver_id'):
        await release_driver(order.get('driver_id'))

    return {'message': 'Order status updated', 'status': status_update.status}

@api_router.post("/orders/{order_id}/assign-driver")
async def assign_driver(order_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'driver':
        raise HTTPException(status_code=403, detail="Only drivers can accept orders")
    
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get('driver_id'):
        raise HTTPException(status_code=400, detail="Order already assigned")
    
    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'driver_id': current_user['id'], 'status': 'accepted', 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )
    await log_assignment(order_id, current_user, 'assigned', current_user, reason='driver_self_accept')
    
    return {'message': 'Order assigned successfully'}

# =========================
# DRIVER ENDPOINTS
# =========================

# Estados de pedido que pueden volver a la cola si la Abeja queda libre
RETURNABLE_STATUSES = ['accepted', 'assigned', 'preparing']

async def log_assignment(order_id, driver, action, actor, distance_km=None, reason=None):
    """Registra un evento de asignación para trazabilidad total."""
    drv = driver if isinstance(driver, dict) else None
    await db.assignment_history.insert_one({
        'id': str(uuid.uuid4()),
        'order_id': order_id,
        'driver_id': (drv or {}).get('id'),
        'driver_name': (drv or {}).get('name'),
        'action': action,  # assigned | returned | auto_returned
        'actor_id': (actor or {}).get('id'),
        'actor_role': (actor or {}).get('role'),
        'actor_name': (actor or {}).get('name'),
        'distance_km': distance_km,
        'reason': reason,
        'created_at': datetime.now(timezone.utc).isoformat(),
    })

async def release_driver(driver_id):
    """Libera al repartidor (vuelve a 'available') tras entregar o devolver el pedido a la cola."""
    if not driver_id:
        return
    await db.users.update_one(
        {'id': driver_id, 'role': 'driver'},
        {'$set': {'is_available': True, 'status': 'available',
                  'updated_at': datetime.now(timezone.utc).isoformat()}}
    )

async def release_driver(driver_id):
    """Libera al repartidor (vuelve a 'available') tras entregar o devolver el pedido a la cola."""
    if not driver_id:
        return
    await db.users.update_one(
        {'id': driver_id, 'role': 'driver'},
        {'$set': {'is_available': True, 'status': 'available',
                  'updated_at': datetime.now(timezone.utc).isoformat()}}
    )

async def _atomic_claim_nearest(order_id, lat, lng, max_km, actor, reason=None):
    """Núcleo de la asignación atómica del repartidor más cercano (anti condición de carrera).
    Hasta ASSIGN_MAX_ATTEMPTS intentos, excluyendo Abejas que otro proceso cogió primero.
    Devuelve dict {driver, distance_km, excluded} si asignó, o None si no fue posible."""
    excluded_driver_ids: List[str] = []
    chosen = None
    for _ in range(ASSIGN_MAX_ATTEMPTS):
        query = {'role': 'driver', 'is_available': True}
        if excluded_driver_ids:
            query['id'] = {'$nin': excluded_driver_ids}
        geo_near = {
            'near': {'type': 'Point', 'coordinates': [lng, lat]},
            'distanceField': 'distance_m',
            'spherical': True,
            'query': query,
        }
        if max_km:
            geo_near['maxDistance'] = max_km * 1000
        pipeline = [{'$geoNear': geo_near}, {'$limit': 1}, {'$project': {'_id': 0, 'password_hash': 0}}]
        nearest = await db.users.aggregate(pipeline).to_list(1)
        if not nearest:
            break
        candidate = nearest[0]
        claimed = await db.users.find_one_and_update(
            {'id': candidate['id'], 'role': 'driver', 'is_available': True},
            {'$set': {'is_available': False, 'status': 'busy',
                      'updated_at': datetime.now(timezone.utc).isoformat()}},
            return_document=ReturnDocument.AFTER,
        )
        if not claimed:
            excluded_driver_ids.append(candidate['id'])
            continue
        chosen = candidate
        break
    if not chosen:
        return None
    order_claim = await db.orders.find_one_and_update(
        {'id': order_id, 'driver_id': None},
        {'$set': {'driver_id': chosen['id'], 'status': 'accepted',
                  'updated_at': datetime.now(timezone.utc).isoformat()}},
        return_document=ReturnDocument.AFTER,
    )
    if not order_claim:
        await release_driver(chosen['id'])
        return None
    distance_km = round(chosen.get('distance_m', 0) / 1000, 2)
    await log_assignment(order_id, chosen, 'assigned', actor, distance_km=distance_km, reason=reason)
    await notify_driver_new_order(chosen['id'], order_claim)
    return {'driver': chosen, 'distance_km': distance_km, 'excluded': len(excluded_driver_ids)}

async def auto_assign_order(order_id):
    """Despacho automático: intenta asignar la Abeja más cercana en cuanto el pedido está pagado.
    Usa el centro de la ciudad del pedido como punto de recogida y respeta el radio de zona.
    Silencioso: si no hay ciudad o no hay Abejas libres, el pedido queda en la cola (pending)."""
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order or order.get('driver_id') or order.get('status') != 'pending':
        return None
    if order.get('payment_status') != 'paid':
        return None
    # Punto de recogida: para exprés usamos el origen real (A); para marketplace, el centro de la ciudad.
    if order.get('order_type') == 'express' and order.get('origin_lat') is not None and order.get('origin_lng') is not None:
        pickup_lat, pickup_lng = order['origin_lat'], order['origin_lng']
    else:
        city_id = order.get('city_id')
        if not city_id:
            return None  # sin ciudad no podemos geolocalizar la recogida -> queda en la cola
        city = await db.cities.find_one({'id': city_id}, {'_id': 0, 'lat': 1, 'lng': 1})
        if not city:
            return None
        pickup_lat, pickup_lng = city['lat'], city['lng']
    return await _atomic_claim_nearest(
        order_id, pickup_lat, pickup_lng, CITY_ZONE_RADIUS_KM, actor=None, reason='auto_dispatch'
    )

def _history_query(action=None, driver_id=None, date_from=None, date_to=None):
    """Construye el filtro de MongoDB para el historial de asignaciones."""
    q = {}
    if action:
        q['action'] = action
    if driver_id:
        q['driver_id'] = driver_id
    created = {}
    if date_from:
        created['$gte'] = f"{date_from}T00:00:00"
    if date_to:
        created['$lte'] = f"{date_to}T23:59:59.999999"
    if created:
        q['created_at'] = created
    return q

@api_router.get("/cities")
async def list_cities(current_user: dict = Depends(get_current_user)):
    """Lista de ciudades/zonas disponibles."""
    try:
        cities = await db.cities.find({}, {'_id': 0}).sort('name', 1).to_list(1000)
        return {'cities': cities}
    except Exception as e:
        raise db_error("GET /cities", e)

@api_router.post("/admin/cities", response_model=City)
async def admin_create_city(data: CityCreate, current_user: dict = Depends(get_current_user)):
    """Crea una ciudad/zona operativa (admin)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    if await db.cities.find_one({'name': name}):
        raise HTTPException(status_code=400, detail="Ya existe una ciudad con ese nombre")
    city = City(name=name, lat=data.lat, lng=data.lng, country=data.country)
    await db.cities.insert_one(city.model_dump())
    return city

@api_router.patch("/admin/cities/{city_id}", response_model=City)
async def admin_update_city(city_id: str, data: CityUpdate, current_user: dict = Depends(get_current_user)):
    """Edita una ciudad/zona operativa (admin)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    city = await db.cities.find_one({'id': city_id}, {'_id': 0})
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if 'name' in updates:
        updates['name'] = updates['name'].strip()
        if updates['name'] != city.get('name') and await db.cities.find_one({'name': updates['name']}):
            raise HTTPException(status_code=400, detail="Ya existe una ciudad con ese nombre")
    if updates:
        await db.cities.update_one({'id': city_id}, {'$set': updates})
    return City(**{**city, **updates})

@api_router.delete("/admin/cities/{city_id}")
async def admin_delete_city(city_id: str, current_user: dict = Depends(get_current_user)):
    """Elimina una ciudad/zona operativa (admin). Bloquea si hay pedidos activos en ella."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    city = await db.cities.find_one({'id': city_id}, {'_id': 0})
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    active = await db.orders.count_documents(
        {'city_id': city_id, 'status': {'$nin': ['delivered', 'cancelled']}}
    )
    if active > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar: hay {active} pedido(s) activo(s) en esta ciudad")
    await db.cities.delete_one({'id': city_id})
    return {'message': 'City deleted', 'id': city_id}

@api_router.get("/drivers/available-orders", response_model=List[Order])
async def get_available_orders(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'driver':
        raise HTTPException(status_code=403, detail="Only drivers can view available orders")

    # Zona del repartidor según su GPS (geofencing de ciudad)
    driver = await db.users.find_one({'id': current_user['id']}, {'_id': 0, 'current_location': 1})
    driver_city = await get_driver_city(driver)

    query = {'driver_id': None, 'status': 'pending', 'payment_status': 'paid'}
    if driver_city:
        # Pedidos de su ciudad + pedidos sin ciudad asignada (no quedan huérfanos)
        query['$or'] = [{'city_id': driver_city['id']}, {'city_id': None}, {'city_id': {'$exists': False}}]
    else:
        # Fuera de toda zona: solo ve pedidos sin ciudad asignada
        query['$or'] = [{'city_id': None}, {'city_id': {'$exists': False}}]
    orders = await db.orders.find(query, {'_id': 0}).to_list(1000)
    
    for order in orders:
        if isinstance(order.get('created_at'), str):
            order['created_at'] = datetime.fromisoformat(order['created_at'])
        if isinstance(order.get('updated_at'), str):
            order['updated_at'] = datetime.fromisoformat(order['updated_at'])
    
    return orders

@api_router.patch("/drivers/availability")
async def update_availability(is_available: bool, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'driver':
        raise HTTPException(status_code=403, detail="Only drivers can update availability")

    await db.users.update_one(
        {'id': current_user['id']},
        {'$set': {'is_available': is_available,
                  'status': 'available' if is_available else 'offline'}}
    )

    returned = 0
    # Si la Abeja queda libre (No disponible), sus pedidos pre-entrega vuelven a la cola
    if not is_available:
        pending_of_driver = await db.orders.find(
            {'driver_id': current_user['id'], 'status': {'$in': RETURNABLE_STATUSES}},
            {'_id': 0, 'id': 1}
        ).to_list(1000)
        for o in pending_of_driver:
            await db.orders.update_one(
                {'id': o['id']},
                {'$set': {'driver_id': None, 'status': 'pending', 'updated_at': datetime.now(timezone.utc).isoformat()}}
            )
            await log_assignment(o['id'], current_user, 'auto_returned', current_user, reason='driver_unavailable')
            returned += 1

    return {'message': 'Availability updated', 'is_available': is_available, 'orders_returned_to_queue': returned}

# =========================
# CHAT ENDPOINTS
# =========================

@api_router.post("/messages", response_model=Message)
async def send_message(message_data: MessageCreate, current_user: dict = Depends(get_current_user)):
    message_dict = message_data.model_dump()
    message_dict['sender_id'] = current_user['id']
    message_dict['sender_role'] = current_user['role']
    
    message = Message(**message_dict)
    doc = message.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.messages.insert_one(doc)
    return message

@api_router.get("/messages/{order_id}", response_model=List[Message])
async def get_messages(order_id: str, current_user: dict = Depends(get_current_user)):
    messages = await db.messages.find({'order_id': order_id}, {'_id': 0}).sort('created_at', 1).to_list(1000)
    
    for message in messages:
        if isinstance(message.get('created_at'), str):
            message['created_at'] = datetime.fromisoformat(message['created_at'])
    
    return messages

# =========================
# PAYMENT ENDPOINTS
# =========================

@api_router.post("/payments/create-checkout")
async def create_checkout_session(order_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    # Get order
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order['customer_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get host URL from request
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    
    # Initialize Stripe
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Get origin from request headers
    origin = request.headers.get('origin', host_url.rstrip('/'))
    
    # Create checkout session
    success_url = f"{origin}/order-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/orders"
    
    # Moneda del pedido (exprés puede ser MAD; marketplace por defecto EUR)
    currency = (order.get('currency') or 'eur').lower()

    checkout_request = CheckoutSessionRequest(
        amount=float(order['total_amount']),
        currency=currency,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'order_id': order_id,
            'user_id': current_user['id']
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction
    transaction = PaymentTransaction(
        session_id=session.session_id,
        order_id=order_id,
        user_id=current_user['id'],
        amount=float(order['total_amount']),
        currency=currency,
        payment_status="pending",
        metadata={'order_id': order_id}
    )
    
    doc = transaction.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.payment_transactions.insert_one(doc)
    
    # Update order with session_id
    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'payment_session_id': session.session_id}}
    )
    
    return {'url': session.url, 'session_id': session.session_id}

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    # Get transaction
    transaction = await db.payment_transactions.find_one({'session_id': session_id}, {'_id': 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if already processed
    if transaction['payment_status'] == 'paid':
        order = await db.orders.find_one({'id': transaction['order_id']}, {'_id': 0, 'order_type': 1})
        return {**transaction, 'order_id': transaction['order_id'],
                'order_type': (order or {}).get('order_type', 'marketplace')}
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Get status from Stripe
    status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction
    await db.payment_transactions.update_one(
        {'session_id': session_id},
        {'$set': {
            'payment_status': status.payment_status,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update order if paid
    order_type = 'marketplace'
    if status.payment_status == 'paid':
        await db.orders.update_one(
            {'id': transaction['order_id']},
            {'$set': {'payment_status': 'paid'}}
        )
        # Despacho automático: asigna la Abeja más cercana al instante
        await auto_assign_order(transaction['order_id'])
        # Genera los pedidos de dropshipping (si el pedido contiene productos dropshipping)
        await _create_dropship_orders_safe(transaction['order_id'])
        od = await db.orders.find_one({'id': transaction['order_id']}, {'_id': 0, 'order_type': 1})
        order_type = (od or {}).get('order_type', 'marketplace')
    
    return {
        'session_id': session_id,
        'order_id': transaction['order_id'],
        'order_type': order_type,
        'payment_status': status.payment_status,
        'status': status.status,
        'amount': status.amount_total / 100,  # Convert from cents
        'currency': status.currency
    }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    try:
        host_url = str(request.base_url)
        webhook_url = f"{host_url}api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Update transaction based on webhook
        if webhook_response.payment_status == 'paid':
            transaction = await db.payment_transactions.find_one({'session_id': webhook_response.session_id}, {'_id': 0})
            if transaction and transaction['payment_status'] != 'paid':
                await db.payment_transactions.update_one(
                    {'session_id': webhook_response.session_id},
                    {'$set': {'payment_status': 'paid', 'updated_at': datetime.now(timezone.utc).isoformat()}}
                )
                
                await db.orders.update_one(
                    {'id': transaction['order_id']},
                    {'$set': {'payment_status': 'paid'}}
                )
                # Despacho automático: asigna la Abeja más cercana al instante
                await auto_assign_order(transaction['order_id'])
                # Genera los pedidos de dropshipping (si el pedido contiene productos dropshipping)
                await _create_dropship_orders_safe(transaction['order_id'])
        
        return {'status': 'success'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/admin/orders/{order_id}/mark-paid")
async def admin_mark_order_paid(order_id: str, current_user: dict = Depends(get_current_user)):
    """Marca un pedido como pagado SIN pasar por Stripe y dispara el auto-despacho.
    Herramienta interna (solo admin) para pruebas/operación manual del flujo completo."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get('payment_status') == 'paid':
        raise HTTPException(status_code=400, detail="Order is already paid")
    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'payment_status': 'paid', 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )
    # Despacho automático: asigna la Abeja más cercana (origen real en exprés, centro de ciudad en marketplace)
    result = await auto_assign_order(order_id)
    # Genera los pedidos de dropshipping (si el pedido contiene productos dropshipping)
    await _create_dropship_orders_safe(order_id)
    assigned = None
    if result:
        chosen = result['driver']
        assigned = {'id': chosen['id'], 'name': chosen.get('name', 'Abeja'),
                    'distance_km': result['distance_km']}
    return {'message': 'Order marked as paid', 'order_id': order_id,
            'payment_status': 'paid', 'auto_assigned': assigned}

# =========================
# DROPSHIPPING — productos y workflow de pedidos
# =========================
# NOTA: la creación/listado de productos y el ciclo de vida completo de los
# pedidos de dropshipping (purchased/shipped/delivered, tracking, comisiones
# por plataforma) viven ahora en dropshipping_routes.py, montado más abajo
# vía `api_router.include_router(dropshipping_router)`. Aquí solo se quedan
# los endpoints que no duplican esa funcionalidad.

@api_router.get("/dropshipping/orders-to-purchase")
async def get_orders_to_purchase(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users")
    
    # Get paid orders with dropshipping products
    orders = await db.orders.find({
        'payment_status': 'paid',
        'status': {'$in': ['pending', 'accepted']}
    }, {'_id': 0}).to_list(1000)
    
    if not orders:
        return []
    
    # Batch fetch: Get all unique product IDs and customer IDs
    product_ids = set()
    customer_ids = set()
    for order in orders:
        customer_ids.add(order['customer_id'])
        for item in order['items']:
            product_ids.add(item['product_id'])
    
    # Fetch all products and customers in batch
    dropship_products = await db.dropshipping_products.find(
        {'id': {'$in': list(product_ids)}}, {'_id': 0}
    ).to_list(None)
    products_map = {prod['id']: prod for prod in dropship_products}
    
    customers = await db.users.find(
        {'id': {'$in': list(customer_ids)}}, {'_id': 0}
    ).to_list(None)
    customers_map = {cust['id']: cust for cust in customers}
    
    # Build purchase list with cached data
    purchase_list = []
    for order in orders:
        customer = customers_map.get(order['customer_id'])
        for item in order['items']:
            dropship_prod = products_map.get(item['product_id'])
            if dropship_prod:
                commission = dropship_prod['selling_price'] - dropship_prod['original_price']
                
                purchase_list.append({
                    'order_id': order['id'],
                    'product_name': item['product_name'],
                    'quantity': item['quantity'],
                    'platform': dropship_prod['platform'],
                    'product_url': dropship_prod['product_url'],
                    'original_price': dropship_prod['original_price'],
                    'total_to_pay': dropship_prod['original_price'] * item['quantity'],
                    'commission_earned': commission * item['quantity'],
                    'customer_name': customer['name'] if customer else 'Unknown',
                    'customer_email': customer['email'] if customer else '',
                    'customer_phone': customer['phone'] if customer else '',
                    'delivery_address': order['delivery_address'],
                    'order_date': order['created_at']
                })
    
    return purchase_list

@api_router.get("/dropshipping/stats")
async def get_dropshipping_stats(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users")
    
    # Get all paid orders
    orders = await db.orders.find({'payment_status': 'paid'}, {'_id': 0}).to_list(10000)
    
    if not orders:
        return {
            'total_orders': 0,
            'total_commission': 0.0,
            'currency': 'EUR'
        }
    
    # Batch fetch: Get all unique product IDs
    product_ids = set()
    for order in orders:
        for item in order['items']:
            product_ids.add(item['product_id'])
    
    # Fetch all dropshipping products in batch
    dropship_products = await db.dropshipping_products.find(
        {'id': {'$in': list(product_ids)}}, {'_id': 0}
    ).to_list(None)
    products_map = {prod['id']: prod for prod in dropship_products}
    
    # Calculate stats with cached data
    total_commission = 0
    orders_count = 0
    
    for order in orders:
        for item in order['items']:
            dropship_prod = products_map.get(item['product_id'])
            if dropship_prod:
                commission = (dropship_prod['selling_price'] - dropship_prod['original_price']) * item['quantity']
                total_commission += commission
                orders_count += 1
    
    return {
        'total_orders': orders_count,
        'total_commission': round(total_commission, 2),
        'currency': 'EUR'
    }

# =========================
# AFFILIATE LINKS MODELS & ROUTES
# =========================

class AffiliateLinks(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    flights_url: Optional[str] = None
    flights_provider: Optional[str] = "Skyscanner"
    ferries_url: Optional[str] = None
    ferries_provider: Optional[str] = "Direct Ferries"
    hotels_url: Optional[str] = None
    hotels_provider: Optional[str] = "Booking.com"
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AffiliateLinksUpdate(BaseModel):
    flights_url: Optional[str] = None
    flights_provider: Optional[str] = None
    ferries_url: Optional[str] = None
    ferries_provider: Optional[str] = None
    hotels_url: Optional[str] = None
    hotels_provider: Optional[str] = None

@api_router.get("/affiliate-links", response_model=AffiliateLinks)
async def get_affiliate_links():
    """Get current affiliate links configuration"""
    links = await db.affiliate_links.find_one({}, {'_id': 0})
    if not links:
        # Return default empty links
        default_links = AffiliateLinks()
        return default_links
    return AffiliateLinks(**links)

@api_router.put("/affiliate-links")
async def update_affiliate_links(links_data: AffiliateLinksUpdate, current_user: dict = Depends(get_current_user)):
    """Update affiliate links (admin/business only)"""
    if current_user['role'] not in ['business', 'admin']:
        raise HTTPException(status_code=403, detail="Only business/admin can update affiliate links")
    
    # Get existing or create new
    existing = await db.affiliate_links.find_one({})
    
    update_data = {k: v for k, v in links_data.dict().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    if existing:
        await db.affiliate_links.update_one(
            {'id': existing['id']},
            {'$set': update_data}
        )
    else:
        new_links = AffiliateLinks(**update_data)
        await db.affiliate_links.insert_one(new_links.dict())
    
    return {"message": "Affiliate links updated successfully"}

# =========================
# AI SMART SEARCH
# =========================

class SmartSearchRequest(BaseModel):
    query: str

@api_router.post("/search/smart")
async def smart_search(req: SmartSearchRequest):
    """Búsqueda inteligente con IA: interpreta lenguaje natural y devuelve los mejores negocios."""
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    businesses = await db.businesses.find({}, {'_id': 0}).to_list(1000)
    if not businesses:
        return {"reply": "No hay negocios disponibles todavía.", "results": []}

    # Build compact catalog for the LLM
    catalog = [
        {
            "id": b["id"],
            "name": b.get("name", ""),
            "category": b.get("category", ""),
            "description": b.get("description", ""),
            "delivery_time": b.get("delivery_time", "")
        }
        for b in businesses
    ]

    system_message = (
        "Eres el asistente de búsqueda de Nubo Express, un marketplace de delivery en España. "
        "El usuario describe lo que quiere en lenguaje natural (puede estar en español, árabe o inglés). "
        "A partir del catálogo JSON de negocios, selecciona hasta 3 negocios más relevantes ordenados de mejor a peor. "
        "Prioriza coincidencia de categoría/intención (ej. 'tengo hambre' -> restaurantes rápidos) y menor tiempo de entrega. "
        "Responde SOLO con JSON válido con este formato exacto: "
        '{"reply": "<frase corta y amable en el idioma del usuario>", "ids": ["id1","id2","id3"]}. '
        "No incluyas texto fuera del JSON."
    )

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"smart-search-{uuid.uuid4()}",
            system_message=system_message
        ).with_model("openai", "gpt-4o-mini")

        user_msg = UserMessage(
            text=f"Consulta del usuario: \"{query}\"\n\nCatálogo de negocios (JSON):\n{json.dumps(catalog, ensure_ascii=False)}"
        )
        raw = await chat.send_message(user_msg)
    except Exception as e:
        logger.error(f"Smart search LLM error: {e}")
        # Fallback: simple keyword match
        ql = query.lower()
        matched = [b for b in businesses if ql in b.get("name", "").lower() or ql in b.get("description", "").lower() or ql in b.get("category", "").lower()]
        results = (matched or businesses)[:3]
        for b in results:
            if isinstance(b.get('created_at'), str):
                b['created_at'] = b['created_at']
        return {"reply": "Esto es lo que encontré para ti:", "results": results}

    # Parse LLM JSON response
    reply = "Esto es lo que encontré para ti:"
    ids = []
    try:
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip().strip("`").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
        parsed = json.loads(text)
        reply = parsed.get("reply", reply)
        ids = parsed.get("ids", []) or []
    except Exception as e:
        logger.error(f"Smart search parse error: {e} | raw: {raw}")

    by_id = {b["id"]: b for b in businesses}
    seen = set()
    results = []
    for i in ids:
        if i in by_id and i not in seen:
            seen.add(i)
            results.append(by_id[i])
        if len(results) >= 3:
            break
    if not results:
        results = businesses[:3]

    return {"reply": reply, "results": results}

# =========================
# DRIVER LOCATION & ADMIN
# =========================

class DriverLocationUpdate(BaseModel):
    lat: float
    lng: float

@api_router.patch("/drivers/location")
async def update_driver_location(loc: DriverLocationUpdate, current_user: dict = Depends(get_current_user)):
    """El repartidor (Abeja 🐝) actualiza su ubicación actual.
    Guarda current_location (lat/lng para el frontend) y geo_location (GeoJSON para 2dsphere)."""
    if current_user['role'] != 'driver':
        raise HTTPException(status_code=403, detail="Only drivers can update location")
    await db.users.update_one(
        {'id': current_user['id']},
        {'$set': {
            'current_location': {'lat': loc.lat, 'lng': loc.lng},
            'geo_location': {'type': 'Point', 'coordinates': [loc.lng, loc.lat]},
        }}
    )
    return {'message': 'Location updated', 'lat': loc.lat, 'lng': loc.lng}

@api_router.get("/drivers/nearest")
async def nearest_drivers(lat: float, lng: float, max_km: Optional[float] = None,
                          limit: int = 5, current_user: dict = Depends(get_current_user)):
    """Devuelve los repartidores disponibles más cercanos a un punto, ordenados por distancia.
    Usa el índice 2dsphere (consulta $geoNear). Solo admin o negocio."""
    if current_user['role'] not in ('admin', 'business'):
        raise HTTPException(status_code=403, detail="Admin or business access required")
    geo_near = {
        'near': {'type': 'Point', 'coordinates': [lng, lat]},
        'distanceField': 'distance_m',
        'spherical': True,
        'query': {'role': 'driver', 'is_available': True},
    }
    if max_km:
        geo_near['maxDistance'] = max_km * 1000
    pipeline = [
        {'$geoNear': geo_near},
        {'$limit': max(1, min(limit, 50))},
        {'$project': {'_id': 0, 'password_hash': 0, 'geo_location': 0}},
    ]
    docs = await db.users.aggregate(pipeline).to_list(50)
    result = [{
        'id': d['id'],
        'name': d.get('name', 'Abeja'),
        'vehicle_type': d.get('vehicle_type'),
        'lat': (d.get('current_location') or {}).get('lat'),
        'lng': (d.get('current_location') or {}).get('lng'),
        'distance_km': round(d.get('distance_m', 0) / 1000, 2),
    } for d in docs]
    return {'count': len(result), 'drivers': result}

class AssignNearestRequest(BaseModel):
    lat: float
    lng: float
    max_km: Optional[float] = None

@api_router.post("/orders/{order_id}/assign-nearest")
async def assign_nearest_driver(order_id: str, req: AssignNearestRequest,
                                current_user: dict = Depends(get_current_user)):
    """Auto-asigna atómicamente el repartidor disponible más cercano al punto de recogida.
    Solo admin o negocio.

    Algoritmo (equivalente a SELECT ... FOR UPDATE de SQL, sobre MongoDB):
    - Hasta ASSIGN_MAX_ATTEMPTS (3) intentos.
    - En cada intento busca el más cercano disponible ($geoNear), excluyendo a los ya descartados.
    - Reclama al candidato con find_one_and_update atómico (is_available True -> False, status 'busy').
      Si otro proceso lo cogió primero, lo excluye y reintenta con el siguiente.
    - Reclama el pedido también de forma atómica (driver_id None -> driver). Si ya tenía repartidor,
      libera de nuevo a la Abeja y aborta.
    """
    if current_user['role'] not in ('admin', 'business'):
        raise HTTPException(status_code=403, detail="Admin or business access required")

    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get('driver_id'):
        raise HTTPException(status_code=400, detail="Order already has a driver assigned")

    result = await _atomic_claim_nearest(order_id, req.lat, req.lng, req.max_km, current_user)
    if not result:
        raise HTTPException(status_code=404, detail="No available drivers nearby")

    chosen = result['driver']
    return {
        'message': 'Nearest driver assigned',
        'order_id': order_id,
        'attempts_excluded': result['excluded'],
        'driver': {
            'id': chosen['id'],
            'name': chosen.get('name', 'Abeja'),
            'vehicle_type': chosen.get('vehicle_type'),
            'distance_km': result['distance_km'],
        }
    }

@api_router.post("/orders/{order_id}/return-to-queue")
async def return_order_to_queue(order_id: str, current_user: dict = Depends(get_current_user)):
    """Devuelve manualmente un pedido asignado a la cola (admin/business)."""
    if current_user['role'] not in ('admin', 'business'):
        raise HTTPException(status_code=403, detail="Admin or business access required")
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.get('driver_id'):
        raise HTTPException(status_code=400, detail="Order is already in the queue (no driver assigned)")

    prev_driver_id = order.get('driver_id')
    prev_driver = await db.users.find_one({'id': prev_driver_id}, {'_id': 0, 'id': 1, 'name': 1})
    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'driver_id': None, 'status': 'pending', 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )
    # La Abeja queda libre de nuevo para recibir otro pedido
    await release_driver(prev_driver_id)
    await log_assignment(order_id, prev_driver, 'returned', current_user, reason='manual_return')
    return {'message': 'Order returned to queue', 'order_id': order_id}

@api_router.get("/admin/assignment-history")
async def get_assignment_history(
    limit: int = 50,
    action: Optional[str] = None,
    driver_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Historial de asignaciones para trazabilidad total (admin). Soporta filtros."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    query = _history_query(action, driver_id, date_from, date_to)
    events = await db.assignment_history.find(query, {'_id': 0}).sort('created_at', -1).to_list(max(1, min(limit, 500)))
    # Lista de repartidores presentes en el historial (para el filtro del frontend)
    raw = await db.assignment_history.find({}, {'_id': 0, 'driver_id': 1, 'driver_name': 1}).to_list(2000)
    seen, drivers_in_history = set(), []
    for r in raw:
        did = r.get('driver_id')
        if did and did not in seen:
            seen.add(did)
            drivers_in_history.append({'id': did, 'name': r.get('driver_name') or 'N/D'})
    return {'count': len(events), 'events': events, 'drivers': drivers_in_history}

@api_router.get("/admin/assignment-history/export")
async def export_assignment_history(
    action: Optional[str] = None,
    driver_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Exporta el historial de asignaciones filtrado a CSV (admin)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    query = _history_query(action, driver_id, date_from, date_to)
    events = await db.assignment_history.find(query, {'_id': 0}).sort('created_at', -1).to_list(5000)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['fecha', 'accion', 'pedido_id', 'repartidor', 'repartidor_id',
                     'realizado_por', 'rol', 'distancia_km', 'motivo'])
    for e in events:
        writer.writerow([
            e.get('created_at', ''), e.get('action', ''), e.get('order_id', ''),
            e.get('driver_name', ''), e.get('driver_id', ''), e.get('actor_name', ''),
            e.get('actor_role', ''), e.get('distance_km', ''), e.get('reason', ''),
        ])
    filename = f"historial_asignaciones_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        content=buf.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

# =========================
# FINANCES — Pagos / comisiones por repartidor (Abeja)
# =========================

DEFAULT_COMMISSION_RATE = 0.10  # 10% del importe del pedido por defecto

class MarkPaidRequest(BaseModel):
    driver_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    rate: float = DEFAULT_COMMISSION_RATE

def _payout_key(driver_id, start_date, end_date):
    """Clave única de un ciclo de pago: repartidor + periodo."""
    return {'driver_id': driver_id, 'period_start': start_date or '', 'period_end': end_date or ''}

def _order_eff_date(o):
    """Fecha efectiva de entrega para los reportes (delivered_at > updated_at > created_at)."""
    return (o.get('delivered_at') or o.get('updated_at') or o.get('created_at') or '')[:10]

def _in_range(d, start_date, end_date):
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True

async def _compute_earnings(query, start_date, end_date, rate):
    """Agrega entregas y comisiones por repartidor a partir de pedidos 'delivered'."""
    orders = await db.orders.find(query, {'_id': 0, 'driver_id': 1, 'total_amount': 1,
                                          'delivered_at': 1, 'updated_at': 1, 'created_at': 1}).to_list(50000)
    per = {}
    for o in orders:
        if not _in_range(_order_eff_date(o), start_date, end_date):
            continue
        did = o.get('driver_id')
        if not did:
            continue
        amt = float(o.get('total_amount') or 0)
        e = per.setdefault(did, {'deliveries': 0, 'revenue': 0.0})
        e['deliveries'] += 1
        e['revenue'] += amt
    return per

@api_router.get("/admin/finances/summary")
async def finances_summary(start_date: Optional[str] = None, end_date: Optional[str] = None,
                           rate: float = DEFAULT_COMMISSION_RATE,
                           current_user: dict = Depends(get_current_user)):
    """Pagos por repartidor en un periodo (tabla agregada)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    per = await _compute_earnings({'status': 'delivered', 'driver_id': {'$ne': None}}, start_date, end_date, rate)
    names = {}
    if per:
        async for u in db.users.find({'id': {'$in': list(per.keys())}}, {'_id': 0, 'id': 1, 'name': 1}):
            names[u['id']] = u.get('name')
    rows = []
    for did, v in per.items():
        rows.append({
            'driver_id': did,
            'driver_name': names.get(did, 'N/D'),
            'total_deliveries': v['deliveries'],
            'total_revenue': round(v['revenue'], 2),
            'total_earnings': round(v['revenue'] * rate, 2),
        })
    rows.sort(key=lambda r: -r['total_earnings'])
    # Anota el estado de pago (Pagado/Pendiente) de este periodo para cada repartidor
    paid_map = {}
    async for p in db.driver_payouts.find(
        {'period_start': start_date or '', 'period_end': end_date or '', 'status': 'paid'}, {'_id': 0}
    ):
        paid_map[p['driver_id']] = p
    for r in rows:
        p = paid_map.get(r['driver_id'])
        r['payment_status'] = 'paid' if p else 'pending'
        r['paid_at'] = p.get('paid_at') if p else None
    totals = {
        'deliveries': sum(r['total_deliveries'] for r in rows),
        'revenue': round(sum(r['total_revenue'] for r in rows), 2),
        'earnings': round(sum(r['total_earnings'] for r in rows), 2),
        'paid_earnings': round(sum(r['total_earnings'] for r in rows if r['payment_status'] == 'paid'), 2),
        'pending_earnings': round(sum(r['total_earnings'] for r in rows if r['payment_status'] == 'pending'), 2),
    }
    return {
        'period': f"{start_date or 'inicio'} → {end_date or 'hoy'}",
        'rate': rate, 'currency': 'EUR', 'rows': rows, 'totals': totals,
    }

@api_router.get("/admin/finances/report/{driver_id}")
async def bee_earnings_report(driver_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
                              rate: float = DEFAULT_COMMISSION_RATE,
                              current_user: dict = Depends(get_current_user)):
    """Reporte de comisiones de un repartidor concreto en un periodo."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    per = await _compute_earnings({'status': 'delivered', 'driver_id': driver_id}, start_date, end_date, rate)
    v = per.get(driver_id, {'deliveries': 0, 'revenue': 0.0})
    driver = await db.users.find_one({'id': driver_id}, {'_id': 0, 'id': 1, 'name': 1})
    return {
        'driver_id': driver_id,
        'driver_name': driver.get('name') if driver else 'N/D',
        'period': f"{start_date or 'inicio'} → {end_date or 'hoy'}",
        'total_deliveries': v['deliveries'],
        'total_revenue': round(v['revenue'], 2),
        'total_earnings': round(v['revenue'] * rate, 2),
        'rate': rate, 'currency': 'EUR',
    }

@api_router.get("/admin/finances/export")
async def finances_export(start_date: Optional[str] = None, end_date: Optional[str] = None,
                          rate: float = DEFAULT_COMMISSION_RATE,
                          current_user: dict = Depends(get_current_user)):
    """Exporta los pagos por repartidor a CSV (admin)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    summary = await finances_summary(start_date, end_date, rate, current_user)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['repartidor', 'repartidor_id', 'entregas', 'ingresos_eur', 'comision_eur', 'tasa', 'estado_pago'])
    for r in summary['rows']:
        writer.writerow([r['driver_name'], r['driver_id'], r['total_deliveries'],
                         r['total_revenue'], r['total_earnings'], rate,
                         'Pagado' if r.get('payment_status') == 'paid' else 'Pendiente'])
    t = summary['totals']
    writer.writerow([])
    writer.writerow(['TOTAL', '', t['deliveries'], t['revenue'], t['earnings'], rate])
    filename = f"pagos_repartidores_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
    return Response(content=buf.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})

@api_router.post("/admin/finances/mark-paid")
async def mark_driver_paid(req: MarkPaidRequest, current_user: dict = Depends(get_current_user)):
    """Marca como PAGADO el ciclo de comisiones de un repartidor en el periodo indicado.
    Recalcula el importe en servidor (no confía en el cliente) y guarda una instantánea."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    per = await _compute_earnings({'status': 'delivered', 'driver_id': req.driver_id},
                                  req.start_date, req.end_date, req.rate)
    v = per.get(req.driver_id, {'deliveries': 0, 'revenue': 0.0})
    key = _payout_key(req.driver_id, req.start_date, req.end_date)
    now = datetime.now(timezone.utc).isoformat()
    snapshot = {
        **key, 'status': 'paid', 'rate': req.rate,
        'deliveries': v['deliveries'], 'revenue': round(v['revenue'], 2),
        'amount': round(v['revenue'] * req.rate, 2),
        'paid_at': now, 'marked_by': current_user.get('id'),
        'marked_by_name': current_user.get('name'), 'updated_at': now,
    }
    await db.driver_payouts.update_one(
        key, {'$set': snapshot, '$setOnInsert': {'id': str(uuid.uuid4()), 'created_at': now}}, upsert=True
    )
    return {'message': 'Pago registrado', **snapshot}

@api_router.post("/admin/finances/mark-pending")
async def mark_driver_pending(req: MarkPaidRequest, current_user: dict = Depends(get_current_user)):
    """Revierte el pago: el ciclo de comisiones vuelve a PENDIENTE (elimina el registro de pago)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    await db.driver_payouts.delete_one(_payout_key(req.driver_id, req.start_date, req.end_date))
    return {'message': 'Marcado como pendiente', 'driver_id': req.driver_id, 'status': 'pending'}

@api_router.get("/admin/finances/payouts")
async def list_payouts(driver_id: Optional[str] = None, limit: int = 200,
                       current_user: dict = Depends(get_current_user)):
    """Historial de pagos registrados (instantáneas de ciclos cerrados)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    q = {'status': 'paid'}
    if driver_id:
        q['driver_id'] = driver_id
    payouts = await db.driver_payouts.find(q, {'_id': 0}).sort('paid_at', -1).to_list(max(1, min(limit, 1000)))
    # Resuelve el nombre actual del repartidor para mostrarlo en el historial
    ids = list({p['driver_id'] for p in payouts})
    names = {}
    if ids:
        async for u in db.users.find({'id': {'$in': ids}}, {'_id': 0, 'id': 1, 'name': 1}):
            names[u['id']] = u.get('name')
    for p in payouts:
        p['driver_name'] = names.get(p['driver_id'], 'N/D')
    return {'count': len(payouts), 'payouts': payouts}

# ============================================================
# MÓDULO DE CONTABILIDAD — /api/accounting/*
# Caja MAD/EUR, libro de transacciones, nóminas y exportación.
# Adaptado al stack: Pydantic v2 + UUID + auth admin + datetime UTC ISO.
# ============================================================

ACCT_MAD_TO_EUR = 0.092  # 1 MAD = 0.092 EUR (tipo de cambio de referencia)
ACCT_TXN_TYPES = {'income', 'payout', 'refund', 'adjustment', 'cash_in', 'cash_out'}
ACCT_INCOME_TYPES = {'income', 'cash_in'}
ACCT_EXPENSE_TYPES = {'payout', 'refund', 'cash_out'}
ACCT_CURRENCIES = {'MAD', 'EUR'}
ACCT_METHODS = {'stripe', 'cash_mad', 'cash_eur', 'bank_transfer'}

class AcctTxnCreate(BaseModel):
    type: str
    amount: float = Field(gt=0)
    currency: str
    payment_method: str
    description: str = Field(min_length=2)
    reference_id: Optional[str] = None
    courier_id: Optional[str] = None
    customer_id: Optional[str] = None

class AcctCashMovement(BaseModel):
    amount: float = Field(gt=0)
    currency: str  # 'MAD' | 'EUR'
    description: str = Field(min_length=2)

def _acct_amount_eur(amount: float, currency: str) -> float:
    """Equivalente en EUR de cualquier importe (almacenamos siempre la conversión)."""
    return round(amount * ACCT_MAD_TO_EUR, 4) if currency == 'MAD' else round(amount, 2)

def _acct_validate(type_: str, currency: str, method: str):
    if type_ not in ACCT_TXN_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Usa uno de: {sorted(ACCT_TXN_TYPES)}")
    if currency not in ACCT_CURRENCIES:
        raise HTTPException(status_code=400, detail="Moneda inválida (MAD o EUR)")
    if method not in ACCT_METHODS:
        raise HTTPException(status_code=400, detail=f"Método inválido. Usa uno de: {sorted(ACCT_METHODS)}")

async def _acct_audit(current_user: dict, action: str, resource_id: str, after: dict):
    """Registro de auditoría ligero de acciones contables."""
    try:
        await db.audit_logs.insert_one({
            'id': str(uuid.uuid4()),
            'actor_id': current_user.get('id'),
            'actor_email': current_user.get('email'),
            'actor_name': current_user.get('name'),
            'action': action,
            'resource': 'transactions',
            'resource_id': resource_id,
            'after': after,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': True,
        })
    except Exception:
        pass  # la auditoría no debe bloquear la operación principal

def _acct_date_query(date_from: Optional[str], date_to: Optional[str]) -> dict:
    """Filtro de rango sobre created_at (ISO string) por fecha YYYY-MM-DD."""
    q = {}
    if date_from:
        q['$gte'] = date_from
    if date_to:
        q['$lte'] = date_to + '\uffff'  # incluye todo el día indicado
    return {'created_at': q} if q else {}

async def _acct_create_txn(current_user: dict, *, type_: str, amount: float, currency: str,
                           method: str, description: str, reference_id=None,
                           courier_id=None, customer_id=None, action: str) -> dict:
    _acct_validate(type_, currency, method)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        'id': str(uuid.uuid4()),
        'type': type_,
        'amount': round(float(amount), 2),
        'currency': currency,
        'amount_eur': _acct_amount_eur(amount, currency),
        'payment_method': method,
        'reference_id': reference_id,
        'description': description,
        'courier_id': courier_id,
        'customer_id': customer_id,
        'created_by': current_user.get('id'),
        'created_by_name': current_user.get('name'),
        'created_at': now,
        'is_reconciled': False,
    }
    try:
        await db.transactions.insert_one({**doc})
    except Exception as e:
        raise db_error("POST /accounting (transacción)", e)
    await _acct_audit(current_user, action, doc['id'],
                      {'type': type_, 'amount': doc['amount'], 'currency': currency, 'description': description})
    doc.pop('_id', None)
    return doc

async def _acct_record_order_income(order: dict) -> bool:
    """Registra automáticamente un ingreso en el libro contable al completarse un pedido.
    100% interno e idempotente: si ya existe un ingreso con ese reference_id, no duplica.
    Devuelve True si crea la transacción."""
    if not order:
        return False
    order_id = order.get('id')
    try:
        exists = await db.transactions.find_one(
            {'reference_id': order_id, 'type': 'income'}, {'_id': 0, 'id': 1}
        )
        if exists:
            return False
        amount = float(order.get('total_amount') or 0)
        if amount <= 0:
            return False
        currency = order.get('currency') or 'EUR'
        if currency not in ACCT_CURRENCIES:
            currency = 'EUR'
        is_express = order.get('order_type') == 'express'
        label = 'Pedido exprés' if is_express else 'Pedido'
        desc = f"{label} #{str(order_id)[:8]}"
        if order.get('city_name'):
            desc += f" · {order['city_name']}"
        # actor del sistema (el pedido pudo cerrarlo un repartidor; el ingreso es de la empresa)
        system_actor = {'id': 'system', 'name': 'Sistema (auto)', 'email': None}
        await _acct_create_txn(
            system_actor, type_='income', amount=amount, currency=currency,
            method='stripe', description=desc, reference_id=order_id,
            customer_id=order.get('customer_id'), action='AUTO_INCOME_ORDER',
        )
        return True
    except Exception:
        return False  # nunca bloquear el cierre del pedido por la contabilidad


@api_router.get("/accounting/transactions")
async def acct_list_transactions(
    page: int = 1, per_page: int = 30,
    type: Optional[str] = None, currency: Optional[str] = None,
    payment_method: Optional[str] = None, courier_id: Optional[str] = None,
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Libro de transacciones con filtros (tipo, moneda, método, courier, rango de fechas) y paginación."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    page = max(1, page)
    per_page = max(1, min(per_page, 200))
    q = _acct_date_query(date_from, date_to)
    if type:
        q['type'] = type
    if currency:
        q['currency'] = currency
    if payment_method:
        q['payment_method'] = payment_method
    if courier_id:
        q['courier_id'] = courier_id
    try:
        total = await db.transactions.count_documents(q)
        rows = await db.transactions.find(q, {'_id': 0}).sort('created_at', -1) \
            .skip((page - 1) * per_page).limit(per_page).to_list(per_page)
    except Exception as e:
        raise db_error("GET /accounting/transactions", e)
    import math as _math
    return {'total': total, 'page': page, 'per_page': per_page,
            'pages': _math.ceil(total / per_page) if total else 0, 'data': rows}

@api_router.post("/accounting/transactions")
async def acct_create_transaction(payload: AcctTxnCreate, current_user: dict = Depends(get_current_user)):
    """Registra una transacción contable manual (ingreso, ajuste, pago, devolución…)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return await _acct_create_txn(
        current_user, type_=payload.type, amount=payload.amount, currency=payload.currency,
        method=payload.payment_method, description=payload.description,
        reference_id=payload.reference_id, courier_id=payload.courier_id,
        customer_id=payload.customer_id, action='CREATE_TRANSACTION',
    )

@api_router.get("/accounting/transactions/summary")
async def acct_transactions_summary(date_from: Optional[str] = None, date_to: Optional[str] = None,
                                    current_user: dict = Depends(get_current_user)):
    """Resumen contable del periodo: ingresos, gastos y balance neto por moneda + desglose por tipo/método."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    q = _acct_date_query(date_from, date_to)
    try:
        txns = await db.transactions.find(q, {'_id': 0}).to_list(50000)
    except Exception as e:
        raise db_error("GET /accounting/transactions/summary", e)
    inc = {'MAD': 0.0, 'EUR': 0.0}
    exp = {'MAD': 0.0, 'EUR': 0.0}
    by_type, by_method = {}, {}
    for t in txns:
        cur = t.get('currency', 'EUR')
        amt = float(t.get('amount') or 0)
        tt = t.get('type')
        pm = t.get('payment_method', 'otro')
        by_type[tt] = round(by_type.get(tt, 0) + amt, 2)
        by_method[pm] = round(by_method.get(pm, 0) + amt, 2)
        if tt in ACCT_INCOME_TYPES:
            inc[cur] = round(inc.get(cur, 0) + amt, 2)
        elif tt in ACCT_EXPENSE_TYPES:
            exp[cur] = round(exp.get(cur, 0) + amt, 2)
    return {
        'period': {'from': date_from, 'to': date_to},
        'count': len(txns),
        'total_income': inc,
        'total_expenses': exp,
        'net_balance': {'MAD': round(inc['MAD'] - exp['MAD'], 2), 'EUR': round(inc['EUR'] - exp['EUR'], 2)},
        'breakdown_by_type': by_type,
        'breakdown_by_method': by_method,
    }

@api_router.get("/accounting/cash/balance")
async def acct_cash_balance(current_user: dict = Depends(get_current_user)):
    """Saldo de caja en efectivo (MAD y EUR) calculado a partir de los movimientos cash_in/cash_out."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        txns = await db.transactions.find(
            {'payment_method': {'$in': ['cash_mad', 'cash_eur']}}, {'_id': 0}
        ).to_list(50000)
    except Exception as e:
        raise db_error("GET /accounting/cash/balance", e)
    bal = {'cash_mad': 0.0, 'cash_eur': 0.0}
    last = {'cash_mad': None, 'cash_eur': None}
    for t in txns:
        pm = t.get('payment_method')
        if pm not in bal:
            continue
        amt = float(t.get('amount') or 0)
        sign = 1 if t.get('type') in ACCT_INCOME_TYPES else -1
        bal[pm] = round(bal[pm] + sign * amt, 2)
        ca = t.get('created_at')
        if ca and (last[pm] is None or ca > last[pm]):
            last[pm] = ca
    return {
        'cash_mad': {'balance': bal['cash_mad'], 'last_movement': last['cash_mad']},
        'cash_eur': {'balance': bal['cash_eur'], 'last_movement': last['cash_eur']},
        'as_of': datetime.now(timezone.utc).isoformat(),
    }

@api_router.post("/accounting/cash/in")
async def acct_cash_in(payload: AcctCashMovement, current_user: dict = Depends(get_current_user)):
    """Registra una entrada de efectivo en caja (MAD o EUR)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    if payload.currency not in ACCT_CURRENCIES:
        raise HTTPException(status_code=400, detail="Moneda inválida (MAD o EUR)")
    method = 'cash_mad' if payload.currency == 'MAD' else 'cash_eur'
    return await _acct_create_txn(
        current_user, type_='cash_in', amount=payload.amount, currency=payload.currency,
        method=method, description=payload.description, action='CASH_IN',
    )

@api_router.post("/accounting/cash/out")
async def acct_cash_out(payload: AcctCashMovement, current_user: dict = Depends(get_current_user)):
    """Registra una salida de efectivo de caja, validando que haya saldo suficiente."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    if payload.currency not in ACCT_CURRENCIES:
        raise HTTPException(status_code=400, detail="Moneda inválida (MAD o EUR)")
    method = 'cash_mad' if payload.currency == 'MAD' else 'cash_eur'
    # Validar saldo disponible
    balance = await acct_cash_balance(current_user)
    available = balance['cash_mad']['balance'] if payload.currency == 'MAD' else balance['cash_eur']['balance']
    if payload.amount > available:
        raise HTTPException(status_code=400,
                            detail=f"Saldo insuficiente en caja {payload.currency}: disponible {available}, solicitado {payload.amount}")
    return await _acct_create_txn(
        current_user, type_='cash_out', amount=payload.amount, currency=payload.currency,
        method=method, description=payload.description, action='CASH_OUT',
    )

@api_router.get("/accounting/payroll")
async def acct_payroll(start_date: Optional[str] = None, end_date: Optional[str] = None,
                       rate: float = DEFAULT_COMMISSION_RATE,
                       current_user: dict = Depends(get_current_user)):
    """Nóminas de couriers (Abejas) en un periodo: entregas, comisión EUR y equivalente MAD, con estado de pago."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        per = await _compute_earnings({'status': 'delivered', 'driver_id': {'$ne': None}}, start_date, end_date, rate)
        names = {}
        if per:
            async for u in db.users.find({'id': {'$in': list(per.keys())}}, {'_id': 0, 'id': 1, 'name': 1}):
                names[u['id']] = u.get('name')
        paid_map = {}
        async for p in db.driver_payouts.find(
            {'period_start': start_date or '', 'period_end': end_date or '', 'status': 'paid'}, {'_id': 0}
        ):
            paid_map[p['driver_id']] = p
    except Exception as e:
        raise db_error("GET /accounting/payroll", e)
    eur_per_mad = round(1 / ACCT_MAD_TO_EUR, 4)  # ~10.87
    entries = []
    for did, v in per.items():
        earnings_eur = round(v['revenue'] * rate, 2)
        p = paid_map.get(did)
        entries.append({
            'courier_id': did,
            'courier_name': names.get(did, 'N/D'),
            'total_deliveries': v['deliveries'],
            'gross_revenue_eur': round(v['revenue'], 2),
            'net_amount_eur': earnings_eur,
            'net_amount_mad': round(earnings_eur * eur_per_mad, 2),
            'is_paid': bool(p),
            'paid_at': p.get('paid_at') if p else None,
        })
    entries.sort(key=lambda r: -r['net_amount_eur'])
    total_eur = round(sum(e['net_amount_eur'] for e in entries), 2)
    return {
        'period': {'from': start_date, 'to': end_date},
        'rate': rate,
        'entries': entries,
        'total_net_eur': total_eur,
        'total_net_mad': round(total_eur * eur_per_mad, 2),
        'paid_net_eur': round(sum(e['net_amount_eur'] for e in entries if e['is_paid']), 2),
        'pending_net_eur': round(sum(e['net_amount_eur'] for e in entries if not e['is_paid']), 2),
    }

class AcctPayrollPay(BaseModel):
    courier_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    rate: float = DEFAULT_COMMISSION_RATE

@api_router.post("/accounting/payroll/pay")
async def acct_payroll_pay(req: AcctPayrollPay, current_user: dict = Depends(get_current_user)):
    """Marca como pagada la nómina de un courier (Abeja) en el periodo y registra el pago
    como transacción 'payout' (EUR, transferencia) en el libro contable. Pago 100% interno."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        per = await _compute_earnings({'status': 'delivered', 'driver_id': req.courier_id},
                                      req.start_date, req.end_date, req.rate)
        v = per.get(req.courier_id, {'deliveries': 0, 'revenue': 0.0})
        earnings_eur = round(v['revenue'] * req.rate, 2)
        if earnings_eur <= 0:
            raise HTTPException(status_code=400, detail="No hay comisiones que pagar en el periodo")
        key = {'driver_id': req.courier_id, 'period_start': req.start_date or '', 'period_end': req.end_date or ''}
        existing = await db.driver_payouts.find_one(key, {'_id': 0, 'status': 1})
        if existing and existing.get('status') == 'paid':
            raise HTTPException(status_code=400, detail="Esta nómina ya está pagada")
        now = datetime.now(timezone.utc).isoformat()
        await db.driver_payouts.update_one(
            key,
            {'$set': {**key, 'status': 'paid', 'rate': req.rate, 'deliveries': v['deliveries'],
                      'revenue': round(v['revenue'], 2), 'amount': earnings_eur, 'paid_at': now,
                      'marked_by': current_user.get('id'), 'marked_by_name': current_user.get('name'),
                      'updated_at': now},
             '$setOnInsert': {'id': str(uuid.uuid4()), 'created_at': now}},
            upsert=True,
        )
        driver = await db.users.find_one({'id': req.courier_id}, {'_id': 0, 'name': 1})
    except HTTPException:
        raise
    except Exception as e:
        raise db_error("POST /accounting/payroll/pay", e)
    # Registrar el pago en el libro contable (EUR, transferencia: no afecta a la caja en efectivo)
    await _acct_create_txn(
        current_user, type_='payout', amount=earnings_eur, currency='EUR',
        method='bank_transfer', description=f"Nómina {driver.get('name') if driver else req.courier_id}",
        reference_id=req.courier_id, courier_id=req.courier_id, action='PAY_PAYROLL',
    )
    return {'message': 'Nómina pagada', 'courier_id': req.courier_id, 'amount_eur': earnings_eur}


@api_router.get("/accounting/export/transactions")
async def acct_export_transactions(date_from: Optional[str] = None, date_to: Optional[str] = None,
                                   current_user: dict = Depends(get_current_user)):
    """Exporta las transacciones del periodo a CSV (admin)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    q = _acct_date_query(date_from, date_to)
    try:
        rows = await db.transactions.find(q, {'_id': 0}).sort('created_at', -1).to_list(50000)
    except Exception as e:
        raise db_error("GET /accounting/export/transactions", e)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['fecha', 'tipo', 'importe', 'moneda', 'importe_eur', 'metodo', 'descripcion', 'referencia', 'creado_por'])
    for t in rows:
        w.writerow([t.get('created_at', ''), t.get('type', ''), t.get('amount', 0), t.get('currency', ''),
                    t.get('amount_eur', 0), t.get('payment_method', ''), t.get('description', ''),
                    t.get('reference_id', '') or '', t.get('created_by_name', '') or ''])
    filename = f"transacciones_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
    return Response(content=buf.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})

# ─── Cierre de caja diario (arqueo MAD/EUR) ───────────────────────

async def _acct_compute_daily_closing(date_str: str) -> dict:
    """Calcula el arqueo de caja de un día: saldo inicial, movimientos (entradas/salidas)
    por moneda, saldo final esperado, e ingresos/gastos del día. Fechas ISO en string."""
    cash_methods = ['cash_mad', 'cash_eur']
    day_gte = date_str
    day_lte = date_str + '\uffff'
    # Saldo inicial = movimientos de efectivo ANTES del día
    opening = {'cash_mad': 0.0, 'cash_eur': 0.0}
    async for t in db.transactions.find(
        {'payment_method': {'$in': cash_methods}, 'created_at': {'$lt': day_gte}},
        {'_id': 0, 'payment_method': 1, 'type': 1, 'amount': 1}
    ):
        pm = t['payment_method']
        sign = 1 if t.get('type') in ACCT_INCOME_TYPES else -1
        opening[pm] = round(opening[pm] + sign * float(t.get('amount') or 0), 2)
    # Movimientos del día
    day = await db.transactions.find(
        {'created_at': {'$gte': day_gte, '$lte': day_lte}}, {'_id': 0}
    ).to_list(50000)
    mov = {'cash_mad': {'in': 0.0, 'out': 0.0}, 'cash_eur': {'in': 0.0, 'out': 0.0}}
    inc = {'MAD': 0.0, 'EUR': 0.0}
    exp = {'MAD': 0.0, 'EUR': 0.0}
    for t in day:
        amt = float(t.get('amount') or 0)
        tt = t.get('type')
        pm = t.get('payment_method')
        cur = t.get('currency', 'EUR')
        if tt in ACCT_INCOME_TYPES:
            inc[cur] = round(inc.get(cur, 0) + amt, 2)
        elif tt in ACCT_EXPENSE_TYPES:
            exp[cur] = round(exp.get(cur, 0) + amt, 2)
        if pm in mov:
            if tt in ACCT_INCOME_TYPES:
                mov[pm]['in'] = round(mov[pm]['in'] + amt, 2)
            else:
                mov[pm]['out'] = round(mov[pm]['out'] + amt, 2)
    closing = {
        'cash_mad': round(opening['cash_mad'] + mov['cash_mad']['in'] - mov['cash_mad']['out'], 2),
        'cash_eur': round(opening['cash_eur'] + mov['cash_eur']['in'] - mov['cash_eur']['out'], 2),
    }
    return {
        'date': date_str,
        'opening': opening,
        'movements': mov,
        'closing': closing,
        'income': inc,
        'expenses': exp,
        'net': {'MAD': round(inc['MAD'] - exp['MAD'], 2), 'EUR': round(inc['EUR'] - exp['EUR'], 2)},
        'transactions_count': len(day),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

def _acct_today() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')

@api_router.get("/accounting/cash/daily-closing")
async def acct_daily_closing(date: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Arqueo de caja del día indicado (por defecto hoy). Saldo inicial, movimientos y cierre esperado."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    date_str = date or _acct_today()
    try:
        return await _acct_compute_daily_closing(date_str)
    except Exception as e:
        raise db_error("GET /accounting/cash/daily-closing", e)

@api_router.get("/accounting/cash/closing/export")
async def acct_daily_closing_export(date: Optional[str] = None, format: str = 'pdf',
                                    current_user: dict = Depends(get_current_user)):
    """Exporta el arqueo de caja del día a CSV o PDF (admin)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    date_str = date or _acct_today()
    try:
        data = await _acct_compute_daily_closing(date_str)
    except Exception as e:
        raise db_error("GET /accounting/cash/closing/export", e)

    if format == 'csv':
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['Arqueo de caja Nubo Express', date_str])
        w.writerow([])
        w.writerow(['Concepto', 'MAD', 'EUR'])
        w.writerow(['Saldo inicial efectivo', data['opening']['cash_mad'], data['opening']['cash_eur']])
        w.writerow(['Entradas de caja', data['movements']['cash_mad']['in'], data['movements']['cash_eur']['in']])
        w.writerow(['Salidas de caja', data['movements']['cash_mad']['out'], data['movements']['cash_eur']['out']])
        w.writerow(['Saldo final esperado', data['closing']['cash_mad'], data['closing']['cash_eur']])
        w.writerow([])
        w.writerow(['Ingresos del día', data['income']['MAD'], data['income']['EUR']])
        w.writerow(['Gastos del día', data['expenses']['MAD'], data['expenses']['EUR']])
        w.writerow(['Balance neto del día', data['net']['MAD'], data['net']['EUR']])
        w.writerow([])
        w.writerow(['Nº de transacciones', data['transactions_count']])
        w.writerow(['Generado', data['generated_at']])
        return Response(content=buf.getvalue(), media_type='text/csv',
                        headers={'Content-Disposition': f'attachment; filename="arqueo_{date_str}.csv"'})

    # PDF (fpdf2) — informe con identidad Nubo Express
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(16, 122, 87)   # emerald
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 14, 'Nubo Express - Arqueo de caja', new_x='LMARGIN', new_y='NEXT', fill=True)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, f"Fecha: {date_str}", new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    def section(title):
        pdf.set_text_color(16, 122, 87)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 9, title, new_x='LMARGIN', new_y='NEXT')
        pdf.set_text_color(40, 40, 40)
        pdf.set_font('Helvetica', '', 11)

    def row(label, mad, eur, bold=False):
        pdf.set_font('Helvetica', 'B' if bold else '', 11)
        pdf.cell(95, 8, str(label), border='B')
        pdf.cell(45, 8, f"{mad:,.2f} MAD", border='B', align='R')
        pdf.cell(45, 8, f"{eur:,.2f} EUR", border='B', align='R', new_x='LMARGIN', new_y='NEXT')

    section('Efectivo en caja')
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(95, 7, 'Concepto', border='B')
    pdf.cell(45, 7, 'MAD', border='B', align='R')
    pdf.cell(45, 7, 'EUR', border='B', align='R', new_x='LMARGIN', new_y='NEXT')
    pdf.set_text_color(40, 40, 40)
    row('Saldo inicial', data['opening']['cash_mad'], data['opening']['cash_eur'])
    row('(+) Entradas de caja', data['movements']['cash_mad']['in'], data['movements']['cash_eur']['in'])
    row('(-) Salidas de caja', data['movements']['cash_mad']['out'], data['movements']['cash_eur']['out'])
    row('Saldo final esperado', data['closing']['cash_mad'], data['closing']['cash_eur'], bold=True)
    pdf.ln(5)

    section('Resultado del dia')
    row('Ingresos del dia', data['income']['MAD'], data['income']['EUR'])
    row('Gastos del dia', data['expenses']['MAD'], data['expenses']['EUR'])
    row('Balance neto del dia', data['net']['MAD'], data['net']['EUR'], bold=True)
    pdf.ln(6)

    pdf.set_text_color(120, 120, 120)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, f"Transacciones del dia: {data['transactions_count']}", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f"Generado: {data['generated_at']}  |  Por: {current_user.get('name', 'Admin')}", new_x='LMARGIN', new_y='NEXT')

    out = pdf.output()
    pdf_bytes = bytes(out)
    return Response(content=pdf_bytes, media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="arqueo_{date_str}.pdf"'})



# ============================================================
# CÁLCULO DE ENTREGA (precio + ETA por tipo de vehículo)
# Usa Google Distance Matrix para distancia/tiempo reales.
# ============================================================
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

class VehicleType(str, Enum):
    motorcycle = "motorcycle"
    car = "car"
    bicycle = "bicycle"

# Tarifas por tipo de vehículo (base + por km) y factor de velocidad sobre el ETA de Maps
PRICING_CONFIG = {
    VehicleType.bicycle:    {"base_fare": 1.5, "per_km_fare": 0.4, "speed_factor": 1.1},
    VehicleType.motorcycle: {"base_fare": 2.0, "per_km_fare": 0.5, "speed_factor": 0.85},
    VehicleType.car:        {"base_fare": 4.0, "per_km_fare": 1.0, "speed_factor": 1.0},
}

class DeliveryRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    vehicle_type: VehicleType
    currency: str = "EUR"

@api_router.get("/public/cities")
async def list_public_cities():
    """Ciudades operativas (público) para la calculadora de tarifa: id, name, lat, lng, country."""
    try:
        cities = await db.cities.find(
            {}, {'_id': 0, 'id': 1, 'name': 1, 'lat': 1, 'lng': 1, 'country': 1}
        ).sort('name', 1).to_list(1000)
        return {'cities': cities}
    except Exception as e:
        raise db_error("GET /public/cities", e)

@api_router.get("/public/orders/{order_id}/tracking")
async def public_order_tracking(order_id: str):
    """Seguimiento público de un pedido (sin login). Devuelve origen/destino, estado,
    repartidor y su ubicación en vivo. Pensado para pedidos exprés A->B."""
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    driver = None
    if order.get('driver_id'):
        driver = await db.users.find_one(
            {'id': order['driver_id']},
            {'_id': 0, 'name': 1, 'vehicle_type': 1, 'current_location': 1}
        )
    origin = None
    if order.get('origin_lat') is not None and order.get('origin_lng') is not None:
        origin = {'lat': order['origin_lat'], 'lng': order['origin_lng'], 'label': order.get('origin_name')}
    destination = None
    if order.get('destination_lat') is not None and order.get('destination_lng') is not None:
        destination = {'lat': order['destination_lat'], 'lng': order['destination_lng'], 'label': order.get('destination_name')}
    cur = (driver or {}).get('current_location') if driver else None
    driver_location = {'lat': cur['lat'], 'lng': cur['lng']} if (cur and cur.get('lat') is not None) else None
    return {
        'order_id': order['id'],
        'order_type': order.get('order_type', 'marketplace'),
        'status': order.get('status', 'pending'),
        'origin': origin,
        'destination': destination,
        'driver_name': (driver or {}).get('name') if driver else None,
        'driver_vehicle_type': (driver or {}).get('vehicle_type') if driver else order.get('vehicle_type'),
        'driver_location': driver_location,
        'price': order.get('total_amount'),
        'currency': order.get('currency') or 'EUR',
        'distance_km': order.get('distance_km'),
        'eta_mins': order.get('eta_mins'),
        'updated_at': order.get('updated_at'),
    }

# Tasa de referencia: 1 MAD = 0.092 EUR -> 1 EUR = ~10.87 MAD
MAD_PER_EUR = round(1 / 0.092, 4)

@api_router.post("/v1/calculate-delivery")
async def calculate_delivery(req: DeliveryRequest):
    """Calcula la tarifa de entrega y el ETA según la distancia/tiempo reales (Google
    Routes API) y el tipo de vehículo. Endpoint público (presupuesto)."""
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=503, detail="Google Maps API key no configurada en el servidor")

    # Routes API (nueva, sustituye a Distance Matrix legacy). Bici -> BICYCLE, resto -> DRIVE.
    travel_mode = "BICYCLE" if req.vehicle_type == VehicleType.bicycle else "DRIVE"
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration",
    }
    body = {
        "origin": {"location": {"latLng": {"latitude": req.origin_lat, "longitude": req.origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": req.destination_lat, "longitude": req.destination_lng}}},
        "travelMode": travel_mode,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=body)
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al contactar Google Maps: {str(e)}")

    if resp.status_code != 200:
        msg = (data.get("error") or {}).get("message") if isinstance(data, dict) else None
        raise HTTPException(status_code=502, detail=f"Google Maps error: {msg or resp.text[:200]}")
    routes = data.get("routes") or []
    if not routes:
        raise HTTPException(status_code=400, detail="No se pudo calcular la ruta entre los puntos indicados")

    distance_km = routes[0].get("distanceMeters", 0) / 1000.0
    duration_minutes = float(str(routes[0].get("duration", "0s")).rstrip("s") or 0) / 60.0

    config = PRICING_CONFIG[req.vehicle_type]
    total_price = config["base_fare"] + distance_km * config["per_km_fare"]  # en EUR
    estimated_eta = round(duration_minutes * config["speed_factor"])
    # Convierte a la divisa solicitada (las tarifas base están en EUR)
    if req.currency.upper() == "MAD":
        total_price *= MAD_PER_EUR
    total_price = round(total_price, 2)

    return {
        "status": "success",
        "vehicle_used": req.vehicle_type.value,
        "distance_km": round(distance_km, 2),
        "original_duration_mins": round(duration_minutes),
        "adjusted_eta_mins": estimated_eta,
        "delivery_fee": total_price,
        "currency": req.currency.upper(),
    }

@api_router.get("/admin/active-drivers")
async def get_active_drivers(current_user: dict = Depends(get_current_user)):
    """Devuelve todas las Abejas 🐝 activas con ubicación para el mapa del Admin."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    drivers = await db.users.find(
        {'role': 'driver', 'is_available': True, 'current_location': {'$ne': None}},
        {'_id': 0, 'password_hash': 0}
    ).to_list(1000)
    result = []
    for d in drivers:
        loc = d.get('current_location') or {}
        if loc.get('lat') is None or loc.get('lng') is None:
            continue
        result.append({
            'id': d['id'],
            'name': d.get('name', 'Abeja'),
            'vehicle_type': d.get('vehicle_type'),
            'lat': loc['lat'],
            'lng': loc['lng'],
        })
    return {'count': len(result), 'drivers': result}

@api_router.get("/admin/pending-orders")
async def get_pending_orders(current_user: dict = Depends(get_current_user)):
    """Pedidos pendientes sin repartidor asignado (para asignación manual desde el mapa)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    orders = await db.orders.find(
        {'$or': [{'driver_id': None}, {'driver_id': {'$exists': False}}]},
        {'_id': 0}
    ).sort('created_at', -1).to_list(200)

    # Resolve business names without N+1
    biz_ids = list({o.get('business_id') for o in orders if o.get('business_id')})
    biz_map = {}
    if biz_ids:
        async for b in db.businesses.find({'id': {'$in': biz_ids}}, {'_id': 0, 'id': 1, 'name': 1}):
            biz_map[b['id']] = b.get('name')

    result = []
    for o in orders:
        pickup = o.get('pickup_location') or {}
        coords = pickup.get('coordinates') if isinstance(pickup, dict) else None
        result.append({
            'id': o['id'],
            'business_name': biz_map.get(o.get('business_id'), 'Negocio'),
            'delivery_address': o.get('delivery_address', ''),
            'city_name': o.get('city_name'),
            'total_amount': o.get('total_amount', 0),
            'status': o.get('status', 'pending'),
            'created_at': o.get('created_at'),
        })
    return {'count': len(result), 'orders': result}

@api_router.get("/admin/orders")
async def admin_all_orders(status: Optional[str] = None, city_id: Optional[str] = None,
                           limit: int = 200, current_user: dict = Depends(get_current_user)):
    """Todos los pedidos para el panel admin, con filtros opcionales por estado y ciudad."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    q = {}
    if status:
        q['status'] = status
    if city_id:
        q['city_id'] = city_id
    orders = await db.orders.find(q, {'_id': 0}).sort('created_at', -1).to_list(max(1, min(limit, 1000)))

    driver_ids = list({o['driver_id'] for o in orders if o.get('driver_id')})
    biz_ids = list({o['business_id'] for o in orders if o.get('business_id')})
    driver_map, biz_map = {}, {}
    if driver_ids:
        async for u in db.users.find({'id': {'$in': driver_ids}}, {'_id': 0, 'id': 1, 'name': 1}):
            driver_map[u['id']] = u.get('name')
    if biz_ids:
        async for b in db.businesses.find({'id': {'$in': biz_ids}}, {'_id': 0, 'id': 1, 'name': 1}):
            biz_map[b['id']] = b.get('name')

    rows = [{
        'id': o['id'],
        'business_name': biz_map.get(o.get('business_id'), 'Negocio'),
        'driver_name': driver_map.get(o.get('driver_id')) if o.get('driver_id') else None,
        'city_name': o.get('city_name'),
        'delivery_address': o.get('delivery_address', ''),
        'total_amount': o.get('total_amount', 0),
        'status': o.get('status', 'pending'),
        'payment_status': o.get('payment_status', 'pending'),
        'created_at': o.get('created_at'),
    } for o in orders]
    return {'count': len(rows), 'orders': rows}

@api_router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Métricas rápidas para el dashboard del Admin."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    total_drivers = await db.users.count_documents({'role': 'driver'})
    active_drivers = await db.users.count_documents({'role': 'driver', 'is_available': True})
    total_businesses = await db.businesses.count_documents({})
    total_orders = await db.orders.count_documents({})
    return {
        'total_drivers': total_drivers,
        'active_drivers': active_drivers,
        'total_businesses': total_businesses,
        'total_orders': total_orders,
    }

# =========================
# WEBSOCKET REAL-TIME TRACKING
# =========================

class ConnectionManager:
    """Gestiona las conexiones WebSocket activas para tracking en tiempo real"""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.driver_locations: Dict[str, Dict] = {}

    async def connect(self, order_id: str, websocket: WebSocket):
        await websocket.accept()
        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)
        logger.info(f"New WebSocket connection for order {order_id}")

    def disconnect(self, order_id: str, websocket: WebSocket):
        if order_id in self.active_connections:
            self.active_connections[order_id].remove(websocket)
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]
        logger.info(f"WebSocket disconnected for order {order_id}")

    async def broadcast_location(self, order_id: str, message: dict):
        """Envía la ubicación de la Abeja 🐝 a todos los clientes conectados"""
        if order_id in self.active_connections:
            # Store last known location
            self.driver_locations[order_id] = message
            
            for connection in self.active_connections[order_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")

    def get_driver_location(self, order_id: str):
        """Obtiene la última ubicación conocida del conductor"""
        return self.driver_locations.get(order_id)

manager = ConnectionManager()

class DriverNotifier:
    """Canal WebSocket por repartidor para avisos en tiempo real (pedido auto-asignado, etc.)."""
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(driver_id, []).append(websocket)
        logger.info(f"Driver WS connected: {driver_id}")

    def disconnect(self, driver_id: str, websocket: WebSocket):
        conns = self.connections.get(driver_id)
        if conns and websocket in conns:
            conns.remove(websocket)
            if not conns:
                del self.connections[driver_id]
        logger.info(f"Driver WS disconnected: {driver_id}")

    async def notify(self, driver_id: str, message: dict):
        for ws in list(self.connections.get(driver_id, [])):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error notifying driver {driver_id}: {e}")

driver_notifier = DriverNotifier()

async def notify_driver_new_order(driver_id: str, order: dict):
    """Avisa a la Abeja de un pedido recién asignado (manual o automático)."""
    if not driver_id or not order:
        return
    biz = await db.businesses.find_one(
        {'id': order.get('business_id')}, {'_id': 0, 'name': 1, 'address': 1}
    )
    await driver_notifier.notify(driver_id, {
        'type': 'new_order',
        'order_id': order.get('id'),
        'business_name': (biz or {}).get('name', 'Negocio'),
        'pickup_address': (biz or {}).get('address'),
        'delivery_address': order.get('delivery_address'),
        'city_name': order.get('city_name'),
        'total_amount': order.get('total_amount'),
        'status': order.get('status'),
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })

@app.websocket("/ws/driver/{driver_id}")
async def websocket_driver_endpoint(websocket: WebSocket, driver_id: str):
    """Canal persistente de avisos para una Abeja. Recibe {type:'new_order', ...} al asignarle pedidos."""
    await driver_notifier.connect(driver_id, websocket)
    try:
        while True:
            # Mantiene viva la conexión (ping/keepalive del cliente)
            await websocket.receive_text()
    except WebSocketDisconnect:
        driver_notifier.disconnect(driver_id, websocket)
    except Exception as e:
        logger.error(f"Driver WS error: {e}")
        driver_notifier.disconnect(driver_id, websocket)

@app.websocket("/ws/tracking/{order_id}")
async def websocket_tracking_endpoint(websocket: WebSocket, order_id: str):
    """
    WebSocket endpoint para tracking en tiempo real de pedidos.
    Los conductores envían su ubicación y los clientes la reciben en tiempo real.
    """
    await manager.connect(order_id, websocket)
    
    try:
        # Send last known location if exists
        last_location = manager.get_driver_location(order_id)
        if last_location:
            await websocket.send_json(last_location)
        
        while True:
            # Recibir ubicación del conductor (lat, lng)
            data = await websocket.receive_json()
            
            # Broadcast a todos los clientes conectados
            await manager.broadcast_location(order_id, {
                "order_id": order_id,
                "lat": data.get("lat"),
                "lng": data.get("lng"),
                "driver_name": data.get("driver_name", "Conductor"),
                "status": data.get("status", "en_camino"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(order_id, websocket)
        logger.info(f"Client disconnected from order {order_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(order_id, websocket)

@api_router.get("/tracking/location/{order_id}")
async def get_driver_location(order_id: str):
    """REST endpoint alternativo para obtener última ubicación conocida"""
    location = manager.get_driver_location(order_id)
    if location:
        return location
    raise HTTPException(status_code=404, detail="No location data available")

# =========================
# APP CONFIGURATION
# =========================

async def _create_dropship_orders_safe(order_id: str):
    """Wrapper de create_dropship_orders_for_order que nunca debe poder romper
    el flujo de confirmación de pago si algo falla generando los pedidos de
    dropshipping (p.ej. producto dropshipping borrado, datos inconsistentes)."""
    try:
        await create_dropship_orders_for_order(order_id)
    except Exception as e:
        logger.error(f"No se pudieron generar los pedidos de dropshipping para order_id={order_id}: {e}")

api_router.include_router(dropshipping_router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def seed_admin_and_drivers():
    """Crea el admin exclusivo y Abejas 🐝 demo con ubicación en España si no existen."""
    try:
        # Remove the legacy/insecure admin account if it exists
        await db.users.delete_many({'email': 'admin@nuboexpress.com'})

        # Seed/refresh the dedicated admin from env (idempotent)
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            admin_email = ADMIN_EMAIL.lower().strip()
            existing_admin = await db.users.find_one({'email': admin_email})
            if not existing_admin:
                admin_user = User(
                    email=admin_email,
                    name='Centro de Control Nubo',
                    phone='+34 654 24 20 92',
                    role='admin',
                    password_hash=hash_password(ADMIN_PASSWORD)
                )
                doc = admin_user.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.users.insert_one(doc)
                logger.info(f"Seeded dedicated admin {admin_email}")
            elif not verify_password(ADMIN_PASSWORD, existing_admin['password_hash']):
                await db.users.update_one(
                    {'email': admin_email},
                    {'$set': {'password_hash': hash_password(ADMIN_PASSWORD), 'role': 'admin'}}
                )
                logger.info(f"Updated admin password for {admin_email}")

        # Demo drivers (Abejas) across Spain so the admin map shows activity
        demo_drivers = [
            {'email': 'bee.madrid@nuboexpress.com', 'name': 'Abeja Madrid', 'lat': 40.4168, 'lng': -3.7038, 'vehicle_type': 'motorcycle'},
            {'email': 'bee.barcelona@nuboexpress.com', 'name': 'Abeja Barcelona', 'lat': 41.3874, 'lng': 2.1686, 'vehicle_type': 'bike'},
            {'email': 'bee.valencia@nuboexpress.com', 'name': 'Abeja Valencia', 'lat': 39.4699, 'lng': -0.3763, 'vehicle_type': 'car'},
            {'email': 'bee.sevilla@nuboexpress.com', 'name': 'Abeja Sevilla', 'lat': 37.3891, 'lng': -5.9845, 'vehicle_type': 'motorcycle'},
            {'email': 'bee.algeciras@nuboexpress.com', 'name': 'Abeja Algeciras', 'lat': 36.1408, 'lng': -5.4562, 'vehicle_type': 'bike'},
            {'email': 'bee.malaga@nuboexpress.com', 'name': 'Abeja Málaga', 'lat': 36.7213, 'lng': -4.4214, 'vehicle_type': 'car'},
        ]
        for d in demo_drivers:
            existing = await db.users.find_one({'email': d['email']})
            if not existing:
                driver = User(
                    email=d['email'],
                    name=d['name'],
                    phone='+34 600 000 000',
                    role='driver',
                    vehicle_type=d['vehicle_type'],
                    is_available=True,
                    current_location={'lat': d['lat'], 'lng': d['lng']},
                    password_hash=hash_password('Bee123!')
                )
                doc = driver.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                doc['geo_location'] = {'type': 'Point', 'coordinates': [d['lng'], d['lat']]}
                await db.users.insert_one(doc)
        logger.info("Seeded demo drivers")
    except Exception as e:
        logger.error(f"Seed error: {e}")

@app.on_event("startup")
async def init_collections_and_indexes():
    """Inicializa el 'esquema' MongoDB: crea colecciones e índices (Users, Orders, Drivers, etc.).
    En MongoDB las colecciones son schemaless y se crean al primer insert; aquí las creamos
    explícitamente y añadimos índices para rendimiento e integridad."""
    try:
        existing = await db.list_collection_names()
        for coll in ['users', 'orders', 'businesses', 'products', 'messages',
                     'payment_transactions', 'affiliate_links', 'admin_login_attempts',
                     'assignment_history', 'cities', 'driver_payouts']:
            if coll not in existing:
                await db.create_collection(coll)

        # Users (incluye clientes, repartidores/Drivers, negocios y admin)
        await db.users.create_index('email', unique=True)
        await db.users.create_index('id', unique=True)
        await db.users.create_index('role')
        # Drivers: consultas del mapa admin (repartidores disponibles)
        await db.users.create_index([('role', 1), ('is_available', 1)])
        # Drivers: índice geoespacial 2dsphere para "repartidor más cercano"
        await db.users.create_index([('geo_location', '2dsphere')])

        # Backfill: genera geo_location (GeoJSON) para drivers que solo tienen current_location
        async for d in db.users.find({'role': 'driver', 'current_location': {'$ne': None}, 'geo_location': {'$exists': False}}, {'id': 1, 'current_location': 1}):
            loc = d.get('current_location') or {}
            if loc.get('lat') is not None and loc.get('lng') is not None:
                await db.users.update_one(
                    {'id': d['id']},
                    {'$set': {'geo_location': {'type': 'Point', 'coordinates': [loc['lng'], loc['lat']]}}}
                )

        # Orders
        await db.orders.create_index('id', unique=True)
        await db.orders.create_index('customer_id')
        await db.orders.create_index('driver_id')
        await db.orders.create_index('status')
        await db.orders.create_index('created_at')

        # Businesses / Products
        await db.businesses.create_index('id', unique=True)
        await db.businesses.create_index('category')
        await db.products.create_index('business_id')

        # Seguridad: bloqueo de login admin por email
        await db.admin_login_attempts.create_index('email', unique=True)

        # Historial de asignaciones (trazabilidad)
        await db.assignment_history.create_index('created_at')
        await db.assignment_history.create_index('order_id')

        # Pagos de comisiones por repartidor (ciclos cerrados Pagado/Pendiente)
        await db.driver_payouts.create_index(
            [('driver_id', 1), ('period_start', 1), ('period_end', 1)], unique=True
        )
        await db.driver_payouts.create_index('paid_at')

        # Ciudades / zonas + seed inicial (con coordenadas del centro)
        await db.cities.create_index('name', unique=True)
        seed_cities = [
            # Marruecos
            {'name': 'Tánger', 'lat': 35.7595, 'lng': -5.8340, 'country': 'MA'},
            {'name': 'Casablanca', 'lat': 33.5731, 'lng': -7.5898, 'country': 'MA'},
            {'name': 'Meknes', 'lat': 33.8935, 'lng': -5.5473, 'country': 'MA'},
            {'name': 'Nador', 'lat': 35.1681, 'lng': -2.9335, 'country': 'MA'},
            # España
            {'name': 'Algeciras', 'lat': 36.1408, 'lng': -5.4562, 'country': 'ES'},
            {'name': 'Madrid', 'lat': 40.4168, 'lng': -3.7038, 'country': 'ES'},
            {'name': 'Barcelona', 'lat': 41.3874, 'lng': 2.1686, 'country': 'ES'},
            {'name': 'Málaga', 'lat': 36.7213, 'lng': -4.4214, 'country': 'ES'},
        ]
        for c in seed_cities:
            existing_city = await db.cities.find_one({'name': c['name']})
            if not existing_city:
                await db.cities.insert_one({'id': str(uuid.uuid4()), **c})
            elif not existing_city.get('country'):
                await db.cities.update_one({'name': c['name']}, {'$set': {'country': c['country']}})
        logger.info("Seeded/verified cities (ES + MA)")

        logger.info("DB collections & indexes initialized")
    except Exception as e:
        logger.error(f"Index init error: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()