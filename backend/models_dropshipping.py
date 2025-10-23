from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid

class DropshippingProduct(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    business_id: str
    name: str
    description: str
    original_price: float  # Precio en la plataforma original
    selling_price: float   # Precio + comisión
    commission_percentage: float  # Porcentaje de comisión (15-25)
    platform: str  # alibaba, temu, aliexpress
    product_url: str  # URL del producto original
    image_url: str
    category: str
    stock_status: str = "available"  # available, out_of_stock
    shipping_time: str = "15-30 días"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DropshippingOrder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str  # ID del pedido principal
    product_id: str
    product_name: str
    product_url: str  # URL para comprar en plataforma original
    platform: str
    original_price: float
    selling_price: float
    commission_earned: float
    quantity: int
    customer_info: dict
    status: str = "pending_purchase"  # pending_purchase, purchased, shipped, delivered
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    purchased_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
