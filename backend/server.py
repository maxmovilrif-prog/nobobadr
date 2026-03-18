from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import sys
sys.path.append(str(Path(__file__).parent))

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Stripe Configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', 'sk_test_emergent')

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BusinessCreate(BaseModel):
    name: str
    category: str
    description: str
    address: str
    phone: str
    image_url: str
    delivery_time: str

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
    business_id: str
    driver_id: Optional[str] = None
    items: List[OrderItem]
    total_amount: float
    delivery_address: str
    status: str  # pending, accepted, preparing, ready, in_transit, delivered, cancelled
    payment_status: str = "pending"  # pending, paid, failed
    payment_session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    business_id: str
    items: List[OrderItem]
    delivery_address: str

class OrderStatusUpdate(BaseModel):
    status: str

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

# =========================
# AUTH HELPERS
# =========================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, role: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload['user_id']
        user = await db.users.find_one({'id': user_id}, {'_id': 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

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
    
    token = create_token(user['id'], user['role'])
    user.pop('password_hash')
    
    return {'token': token, 'user': user}

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
    
    # Calculate total
    total = sum(item.price * item.quantity for item in order_data.items)
    
    order_dict = order_data.model_dump()
    order_dict['customer_id'] = current_user['id']
    order_dict['total_amount'] = total
    order_dict['status'] = 'pending'
    
    order = Order(**order_dict)
    doc = order.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.orders.insert_one(doc)
    return order

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
    
    # Update order status
    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'status': status_update.status, 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )
    
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
    
    return {'message': 'Order assigned successfully'}

# =========================
# DRIVER ENDPOINTS
# =========================

@api_router.get("/drivers/available-orders", response_model=List[Order])
async def get_available_orders(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'driver':
        raise HTTPException(status_code=403, detail="Only drivers can view available orders")
    
    orders = await db.orders.find({'driver_id': None, 'status': 'pending', 'payment_status': 'paid'}, {'_id': 0}).to_list(1000)
    
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
        {'$set': {'is_available': is_available}}
    )
    
    return {'message': 'Availability updated', 'is_available': is_available}

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
    
    checkout_request = CheckoutSessionRequest(
        amount=float(order['total_amount']),
        currency="eur",
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
        currency="eur",
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
        return transaction
    
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
    if status.payment_status == 'paid':
        await db.orders.update_one(
            {'id': transaction['order_id']},
            {'$set': {'payment_status': 'paid'}}
        )
    
    return {
        'session_id': session_id,
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
        
        return {'status': 'success'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================
# DROPSHIPPING MODELS & ROUTES
# =========================

class DropshippingProduct(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    business_id: str
    name: str
    description: str
    original_price: float
    selling_price: float
    commission_percentage: float
    platform: str  # alibaba, temu, aliexpress
    product_url: str
    image_url: str
    category: str
    stock_status: str = "available"
    shipping_time: str = "15-30 días"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DropshippingProductCreate(BaseModel):
    name: str
    description: str
    original_price: float
    commission_percentage: float
    platform: str
    product_url: str
    image_url: str
    category: str
    shipping_time: str = "15-30 días"

class DropshippingOrderStatusUpdate(BaseModel):
    status: str
    tracking_number: Optional[str] = None
    notes: Optional[str] = None

@api_router.post("/dropshipping/products", response_model=DropshippingProduct)
async def create_dropshipping_product(product_data: DropshippingProductCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can create products")
    
    selling_price = product_data.original_price * (1 + product_data.commission_percentage / 100)
    
    product_dict = product_data.model_dump()
    product_dict['business_id'] = current_user['id']
    product_dict['selling_price'] = round(selling_price, 2)
    
    product = DropshippingProduct(**product_dict)
    doc = product.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.dropshipping_products.insert_one(doc)
    return product

@api_router.get("/dropshipping/products", response_model=List[DropshippingProduct])
async def get_dropshipping_products(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    query = {}
    if platform:
        query['platform'] = platform
    if category:
        query['category'] = category
    if min_price is not None:
        query['selling_price'] = {'$gte': min_price}
    if max_price is not None:
        query.setdefault('selling_price', {})['$lte'] = max_price
    
    products = await db.dropshipping_products.find(query, {'_id': 0}).to_list(1000)
    
    for product in products:
        if isinstance(product.get('created_at'), str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    
    return products

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
# APP CONFIGURATION
# =========================

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()