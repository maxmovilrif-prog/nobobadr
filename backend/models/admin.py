"""
models/admin.py — Nubo Express
Esquemas Pydantic + modelos MongoDB para:
  - Usuarios / Roles
  - Couriers
  - Transacciones contables (MAD / EUR / Stripe)
  - Nóminas
  - Logs de auditoría
"""

from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from enum import Enum

from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId


# ──────────────────────────────────────────
#  Utilidades
# ──────────────────────────────────────────

class PyObjectId(ObjectId):
    """Convierte ObjectId de Mongo a str para JSON serialization."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("ObjectId inválido")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class MongoBase(BaseModel):
    """Base con id de Mongo serializable."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        populate_by_name = True


# ──────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────

class UserRole(str, Enum):
    SUPER_ADMIN  = "super_admin"
    ACCOUNTING   = "accounting"
    OPERATIONS   = "operations"
    COURIER      = "courier"
    CUSTOMER     = "customer"


class Currency(str, Enum):
    MAD = "MAD"
    EUR = "EUR"


class TransactionType(str, Enum):
    INCOME      = "income"       # Cobro de pedido
    PAYOUT      = "payout"       # Pago a courier
    REFUND      = "refund"       # Devolución al cliente
    ADJUSTMENT  = "adjustment"   # Ajuste manual de caja
    CASH_IN     = "cash_in"      # Ingreso efectivo
    CASH_OUT    = "cash_out"     # Salida efectivo


class CourierStatus(str, Enum):
    ACTIVE      = "active"
    INACTIVE    = "inactive"
    ON_SHIFT    = "on_shift"
    SUSPENDED   = "suspended"


class PaymentMethod(str, Enum):
    STRIPE      = "stripe"
    CASH_MAD    = "cash_mad"
    CASH_EUR    = "cash_eur"
    BANK        = "bank_transfer"


# ──────────────────────────────────────────
#  Usuario / Rol
# ──────────────────────────────────────────

class UserPermissions(BaseModel):
    """Permisos granulares por módulo."""
    can_view_accounting:  bool = False
    can_edit_accounting:  bool = False
    can_manage_couriers:  bool = False
    can_manage_users:     bool = False
    can_view_live_map:    bool = False
    can_export_data:      bool = False
    can_edit_rates:       bool = False


class UserDB(MongoBase):
    """Modelo de usuario almacenado en MongoDB."""
    email:        EmailStr
    full_name:    str
    role:         UserRole
    permissions:  UserPermissions = UserPermissions()
    is_active:    bool            = True
    created_at:   datetime        = Field(default_factory=datetime.utcnow)
    updated_at:   datetime        = Field(default_factory=datetime.utcnow)
    last_login:   Optional[datetime] = None

    class Config(MongoBase.Config):
        pass


class UserCreate(BaseModel):
    """Payload para crear usuario (sin hash de contraseña aquí)."""
    email:      EmailStr
    full_name:  str
    role:       UserRole
    password:   str  # Se hashea en el controller


class UserPublic(BaseModel):
    """Respuesta segura sin contraseña."""
    id:          str
    email:       EmailStr
    full_name:   str
    role:        UserRole
    permissions: UserPermissions
    is_active:   bool
    created_at:  datetime
    last_login:  Optional[datetime]


# ──────────────────────────────────────────
#  Courier
# ──────────────────────────────────────────

class CourierLocation(BaseModel):
    lat:  float
    lng:  float
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CourierDB(MongoBase):
    """Modelo de courier en MongoDB."""
    user_id:          str               # Referencia a UserDB._id
    phone:            str
    vehicle_type:     Literal["bike", "moto", "car", "foot"]
    zone:             str               # Zona de operación (p.ej. "Centro", "Palmones")
    status:           CourierStatus     = CourierStatus.INACTIVE
    location:         Optional[CourierLocation] = None
    base_rate_mad:    float             = 0.0   # Tarifa base por entrega en MAD
    hourly_rate_mad:  float             = 0.0
    total_deliveries: int               = 0
    rating:           float             = 5.0
    joined_at:        datetime          = Field(default_factory=datetime.utcnow)


class CourierCreate(BaseModel):
    user_id:       str
    phone:         str
    vehicle_type:  Literal["bike", "moto", "car", "foot"]
    zone:          str
    base_rate_mad: float = 30.0
    hourly_rate_mad: float = 10.0


class CourierUpdate(BaseModel):
    """Campos actualizables del courier."""
    phone:          Optional[str]      = None
    vehicle_type:   Optional[str]      = None
    zone:           Optional[str]      = None
    status:         Optional[CourierStatus] = None
    base_rate_mad:  Optional[float]    = None
    hourly_rate_mad: Optional[float]   = None


# ──────────────────────────────────────────
#  Contabilidad — Transacciones
# ──────────────────────────────────────────

class TransactionDB(MongoBase):
    """Registro contable individual."""
    type:            TransactionType
    amount:          float
    currency:        Currency
    amount_eur:      Optional[float]    = None   # Siempre almacenamos equivalente EUR
    payment_method:  PaymentMethod
    reference_id:    Optional[str]      = None   # order_id, payout_id, stripe charge id
    stripe_charge_id: Optional[str]    = None
    description:     str
    courier_id:      Optional[str]      = None   # Si aplica a un pago de courier
    customer_id:     Optional[str]      = None
    created_by:      str                         # admin user_id
    created_at:      datetime           = Field(default_factory=datetime.utcnow)
    is_reconciled:   bool               = False


class TransactionCreate(BaseModel):
    type:            TransactionType
    amount:          float
    currency:        Currency
    payment_method:  PaymentMethod
    description:     str
    reference_id:    Optional[str] = None
    courier_id:      Optional[str] = None
    customer_id:     Optional[str] = None


# ──────────────────────────────────────────
#  Nóminas de Couriers
# ──────────────────────────────────────────

class PayrollEntry(BaseModel):
    """Línea de nómina por courier en un período."""
    courier_id:       str
    courier_name:     str
    period_start:     datetime
    period_end:       datetime
    total_deliveries: int
    base_earnings:    float       # deliveries × base_rate
    bonus:            float = 0.0
    deductions:       float = 0.0
    net_amount:       float       # base_earnings + bonus - deductions
    currency:         Currency    = Currency.MAD
    is_paid:          bool        = False
    paid_at:          Optional[datetime] = None
    payment_method:   Optional[PaymentMethod] = None


class PayrollReport(BaseModel):
    """Reporte consolidado de nóminas."""
    period_start:    datetime
    period_end:      datetime
    entries:         list[PayrollEntry]
    total_net_mad:   float
    total_net_eur:   float
    generated_at:    datetime = Field(default_factory=datetime.utcnow)
    generated_by:    str


# ──────────────────────────────────────────
#  Tarifas de Envío
# ──────────────────────────────────────────

class ShippingRateDB(MongoBase):
    """Tarifa configurable por zona / tipo de vehículo."""
    zone_from:         str
    zone_to:           str
    vehicle_type:      str
    base_price_mad:    float
    price_per_km_mad:  float
    min_price_mad:     float
    is_active:         bool     = True
    updated_by:        str
    updated_at:        datetime = Field(default_factory=datetime.utcnow)


class ShippingRateUpdate(BaseModel):
    base_price_mad:   Optional[float] = None
    price_per_km_mad: Optional[float] = None
    min_price_mad:    Optional[float] = None
    is_active:        Optional[bool]  = None


# ──────────────────────────────────────────
#  Log de Auditoría
# ──────────────────────────────────────────

class AuditLogDB(MongoBase):
    """Registro inmutable de todas las acciones administrativas."""
    actor_id:     str
    actor_email:  str
    action:       str            # "UPDATE_RATE", "CREATE_USER", "APPROVE_PAYROLL"…
    resource:     str            # Colección afectada
    resource_id:  Optional[str] = None
    before:       Optional[dict] = None   # Estado anterior
    after:        Optional[dict] = None   # Estado posterior
    ip_address:   Optional[str] = None
    user_agent:   Optional[str] = None
    timestamp:    datetime       = Field(default_factory=datetime.utcnow)
    success:      bool           = True
    error_msg:    Optional[str]  = None


# ──────────────────────────────────────────
#  Respuestas genéricas
# ──────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """Wrapper de paginación estándar."""
    total:    int
    page:     int
    per_page: int
    pages:    int
    data:     list


class DashboardMetrics(BaseModel):
    """Métricas del dashboard de Super Admin."""
    active_orders:        int
    active_couriers:      int
    daily_revenue_mad:    float
    daily_revenue_eur:    float
    pending_payouts:      float
    cash_balance_mad:     float
    cash_balance_eur:     float
    alerts:               list[str]
    as_of:                datetime = Field(default_factory=datetime.utcnow)
