"""Modelos Pydantic compartidos para la API de Nubo."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict

from pydantic import BaseModel, Field, ConfigDict, EmailStr


# ===== Users =====
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    phone: str
    role: str  # customer, driver, business
    password_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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


# ===== Businesses =====
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


# ===== Products =====
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


# ===== Orders =====
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


# ===== Cities / Zones =====
class City(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    lat: float
    lng: float
    country: str = "ES"  # ES | MA


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


class DeliveryQuoteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    vehicle_type: str = "motorcycle"
    currency: str = "EUR"


# ===== Messages =====
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


# ===== Payments =====
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


# ===== Smart Search =====
class SmartSearchRequest(BaseModel):
    query: str
    language: Optional[str] = "es"


# ===== Dropshipping =====
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


# ===== Affiliate Links =====
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
