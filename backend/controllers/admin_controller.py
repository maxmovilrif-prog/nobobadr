"""
controllers/admin_controller.py — Nubo Express
Lógica de negocio del módulo Admin completamente separada de las rutas.
Cada función recibe los datos validados por Pydantic y devuelve resultados
listos para serializar. Los controllers NUNCA conocen Request/Response de FastAPI.

Módulos cubiertos:
  1. Gestión de Usuarios
  2. Gestión de Couriers
  3. Control de Tarifas
  4. Dashboard / Métricas en tiempo real
  5. Mapa en vivo
  6. Auditoría
"""

from __future__ import annotations

import math
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.admin import (
    AuditLogDB,
    CourierCreate,
    CourierDB,
    CourierStatus,
    CourierUpdate,
    Currency,
    DashboardMetrics,
    PaginatedResponse,
    ShippingRateUpdate,
    TransactionType,
    UserCreate,
    UserDB,
    UserPermissions,
    UserPublic,
    UserRole,
)


# ══════════════════════════════════════════════════════════════════
#  UTILIDADES INTERNAS
# ══════════════════════════════════════════════════════════════════

def _hash_password(password: str) -> str:
    """
    Hash simple con SHA-256 + salt.
    En producción real usa bcrypt o argon2 (passlib).
    """
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def _verify_password(plain: str, stored: str) -> bool:
    salt, hashed = stored.split(":", 1)
    return hashlib.sha256(f"{salt}{plain}".encode()).hexdigest() == hashed


def _paginate(page: int, per_page: int) -> tuple[int, int]:
    """Devuelve (skip, limit) para queries de Mongo."""
    skip = (page - 1) * per_page
    return skip, per_page


def _to_public_user(doc: dict) -> UserPublic:
    """Convierte documento Mongo a UserPublic (sin contraseña)."""
    return UserPublic(
        id=str(doc["_id"]),
        email=doc["email"],
        full_name=doc["full_name"],
        role=doc["role"],
        permissions=UserPermissions(**doc.get("permissions", {})),
        is_active=doc["is_active"],
        created_at=doc["created_at"],
        last_login=doc.get("last_login"),
    )


# ══════════════════════════════════════════════════════════════════
#  1. AUDITORÍA — se usa en todos los demás módulos
# ══════════════════════════════════════════════════════════════════

async def write_audit_log(
    db: AsyncIOMotorDatabase,
    *,
    actor_id: str,
    actor_email: str,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    error_msg: Optional[str] = None,
) -> None:
    """
    Inserta un log de auditoría inmutable en MongoDB.
    Se llama al final de cada operación de escritura importante.
    No lanza excepciones para no interrumpir el flujo principal.
    """
    try:
        log = AuditLogDB(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource=resource,
            resource_id=resource_id,
            before=before,
            after=after,
            ip_address=ip_address,
            success=success,
            error_msg=error_msg,
        )
        await db["audit_logs"].insert_one(log.dict(by_alias=True))
    except Exception:
        # El log nunca debe tumbar la operación principal
        pass


# ══════════════════════════════════════════════════════════════════
#  2. GESTIÓN DE USUARIOS
# ══════════════════════════════════════════════════════════════════

class UserController:

    # ── Crear usuario ────────────────────────────────────────────
    @staticmethod
    async def create_user(
        db: AsyncIOMotorDatabase,
        payload: UserCreate,
        actor_id: str,
        actor_email: str,
    ) -> UserPublic:
        """
        Crea un nuevo usuario con rol y permisos predeterminados según su rol.
        Lanza ValueError si el email ya existe.
        """
        # 1. Comprobar duplicado
        existing = await db["users"].find_one({"email": payload.email})
        if existing:
            raise ValueError(f"El email '{payload.email}' ya está registrado.")

        # 2. Permisos por defecto según rol
        default_permissions = _default_permissions_for_role(payload.role)

        # 3. Construir documento
        now = datetime.utcnow()
        user_doc = {
            "_id": ObjectId(),
            "email": payload.email,
            "full_name": payload.full_name,
            "role": payload.role,
            "password_hash": _hash_password(payload.password),
            "permissions": default_permissions.dict(),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
        }

        # 4. Insertar
        await db["users"].insert_one(user_doc)

        # 5. Auditoría
        after_safe = {k: v for k, v in user_doc.items() if k != "password_hash"}
        after_safe["_id"] = str(after_safe["_id"])
        await write_audit_log(
            db,
            actor_id=actor_id,
            actor_email=actor_email,
            action="CREATE_USER",
            resource="users",
            resource_id=str(user_doc["_id"]),
            after=after_safe,
        )

        return _to_public_user(user_doc)

    # ── Listar usuarios paginados ────────────────────────────────
    @staticmethod
    async def list_users(
        db: AsyncIOMotorDatabase,
        page: int = 1,
        per_page: int = 20,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse:
        """Devuelve usuarios paginados con filtros opcionales."""
        query: dict = {}
        if role:
            query["role"] = role
        if is_active is not None:
            query["is_active"] = is_active
        if search:
            query["$or"] = [
                {"full_name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]

        skip, limit = _paginate(page, per_page)
        total = await db["users"].count_documents(query)
        cursor = db["users"].find(query).skip(skip).limit(limit).sort("created_at", -1)
        docs = await cursor.to_list(length=limit)

        return PaginatedResponse(
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if total else 0,
            data=[_to_public_user(d) for d in docs],
        )

    # ── Activar / desactivar usuario ────────────────────────────
    @staticmethod
    async def toggle_user_status(
        db: AsyncIOMotorDatabase,
        user_id: str,
        actor_id: str,
        actor_email: str,
    ) -> UserPublic:
        """Alterna is_active del usuario. No se puede desactivar a sí mismo."""
        if user_id == actor_id:
            raise ValueError("No puedes desactivar tu propia cuenta.")

        doc = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not doc:
            raise ValueError("Usuario no encontrado.")

        new_status = not doc["is_active"]
        before = {"is_active": doc["is_active"]}

        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": new_status, "updated_at": datetime.utcnow()}},
        )

        await write_audit_log(
            db,
            actor_id=actor_id,
            actor_email=actor_email,
            action="TOGGLE_USER_STATUS",
            resource="users",
            resource_id=user_id,
            before=before,
            after={"is_active": new_status},
        )

        doc["is_active"] = new_status
        return _to_public_user(doc)

    # ── Actualizar permisos ──────────────────────────────────────
    @staticmethod
    async def update_permissions(
        db: AsyncIOMotorDatabase,
        user_id: str,
        permissions: UserPermissions,
        actor_id: str,
        actor_email: str,
    ) -> UserPublic:
        """Sobreescribe los permisos granulares de un usuario."""
        doc = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not doc:
            raise ValueError("Usuario no encontrado.")

        before = {"permissions": doc.get("permissions", {})}
        new_perms = permissions.dict()

        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"permissions": new_perms, "updated_at": datetime.utcnow()}},
        )

        await write_audit_log(
            db,
            actor_id=actor_id,
            actor_email=actor_email,
            action="UPDATE_PERMISSIONS",
            resource="users",
            resource_id=user_id,
            before=before,
            after={"permissions": new_perms},
        )

        doc["permissions"] = new_perms
        return _to_public_user(doc)


# ══════════════════════════════════════════════════════════════════
#  3. GESTIÓN DE COURIERS
# ══════════════════════════════════════════════════════════════════

class CourierController:

    # ── Registrar courier ────────────────────────────────────────
    @staticmethod
    async def create_courier(
        db: AsyncIOMotorDatabase,
        payload: CourierCreate,
        actor_id: str,
        actor_email: str,
    ) -> dict:
        """
        Crea el perfil de courier vinculado a un usuario existente.
        Un usuario solo puede tener un perfil de courier.
        """
        # Verificar que el usuario existe y tiene rol courier
        user = await db["users"].find_one({"_id": ObjectId(payload.user_id)})
        if not user:
            raise ValueError("Usuario base no encontrado.")
        if user["role"] != UserRole.COURIER:
            raise ValueError("El usuario debe tener rol 'courier'.")

        existing = await db["couriers"].find_one({"user_id": payload.user_id})
        if existing:
            raise ValueError("Este usuario ya tiene un perfil de courier.")

        now = datetime.utcnow()
        doc = {
            "_id": ObjectId(),
            "user_id": payload.user_id,
            "phone": payload.phone,
            "vehicle_type": payload.vehicle_type,
            "zone": payload.zone,
            "status": CourierStatus.INACTIVE,
            "location": None,
            "base_rate_mad": payload.base_rate_mad,
            "hourly_rate_mad": payload.hourly_rate_mad,
            "total_deliveries": 0,
            "rating": 5.0,
            "joined_at": now,
        }

        await db["couriers"].insert_one(doc)
        await write_audit_log(
            db,
            actor_id=actor_id,
            actor_email=actor_email,
            action="CREATE_COURIER",
            resource="couriers",
            resource_id=str(doc["_id"]),
            after={"user_id": payload.user_id, "zone": payload.zone},
        )

        doc["_id"] = str(doc["_id"])
        return doc

    # ── Listar couriers ──────────────────────────────────────────
    @staticmethod
    async def list_couriers(
        db: AsyncIOMotorDatabase,
        page: int = 1,
        per_page: int = 20,
        status: Optional[CourierStatus] = None,
        zone: Optional[str] = None,
    ) -> PaginatedResponse:
        """Lista couriers con sus datos de usuario en un solo pipeline."""
        query: dict = {}
        if status:
            query["status"] = status
        if zone:
            query["zone"] = {"$regex": zone, "$options": "i"}

        skip, limit = _paginate(page, per_page)
        total = await db["couriers"].count_documents(query)

        # Join con la colección de usuarios para nombre y email
        pipeline = [
            {"$match": query},
            {"$skip": skip},
            {"$limit": limit},
            {"$addFields": {"user_object_id": {"$toObjectId": "$user_id"}}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_object_id",
                    "foreignField": "_id",
                    "as": "user_info",
                }
            },
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "user_id": 1,
                    "full_name": "$user_info.full_name",
                    "email": "$user_info.email",
                    "phone": 1,
                    "vehicle_type": 1,
                    "zone": 1,
                    "status": 1,
                    "location": 1,
                    "base_rate_mad": 1,
                    "hourly_rate_mad": 1,
                    "total_deliveries": 1,
                    "rating": 1,
                    "joined_at": 1,
                }
            },
            {"$sort": {"joined_at": -1}},
        ]

        docs = await db["couriers"].aggregate(pipeline).to_list(length=limit)

        return PaginatedResponse(
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if total else 0,
            data=docs,
        )

    # ── Actualizar courier ───────────────────────────────────────
    @staticmethod
    async def update_courier(
        db: AsyncIOMotorDatabase,
        courier_id: str,
        payload: CourierUpdate,
        actor_id: str,
        actor_email: str,
    ) -> dict:
        """Actualiza campos del courier. Solo los campos enviados (PATCH semántico)."""
        doc = await db["couriers"].find_one({"_id": ObjectId(courier_id)})
        if not doc:
            raise ValueError("Courier no encontrado.")

        updates = payload.dict(exclude_none=True)
        if not updates:
            raise ValueError("No hay campos para actualizar.")

        before = {k: doc.get(k) for k in updates}
        updates["updated_at"] = datetime.utcnow()

        await db["couriers"].update_one(
            {"_id": ObjectId(courier_id)}, {"$set": updates}
        )

        await write_audit_log(
            db,
            actor_id=actor_id,
            actor_email=actor_email,
            action="UPDATE_COURIER",
            resource="couriers",
            resource_id=courier_id,
            before=before,
            after=updates,
        )

        doc.update(updates)
        doc["_id"] = str(doc["_id"])
        return doc

    # ── Posiciones en tiempo real (mapa) ─────────────────────────
    @staticmethod
    async def get_live_courier_positions(
        db: AsyncIOMotorDatabase,
        zone: Optional[str] = None,
    ) -> list[dict]:
        """
        Devuelve couriers activos con su última posición GPS.
        Diseñado para el mapa en vivo del Super Admin.
        Solo incluye couriers con location actualizada en los últimos 10 min.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        query: dict = {
            "status": {"$in": [CourierStatus.ON_SHIFT, CourierStatus.ACTIVE]},
            "location.updated_at": {"$gte": cutoff},
        }
        if zone:
            query["zone"] = zone

        pipeline = [
            {"$match": query},
            {"$addFields": {"user_object_id": {"$toObjectId": "$user_id"}}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_object_id",
                    "foreignField": "_id",
                    "as": "user_info",
                }
            },
            {"$unwind": "$user_info"},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "full_name": "$user_info.full_name",
                    "phone": 1,
                    "vehicle_type": 1,
                    "zone": 1,
                    "status": 1,
                    "lat": "$location.lat",
                    "lng": "$location.lng",
                    "location_updated": "$location.updated_at",
                    "total_deliveries": 1,
                    "rating": 1,
                }
            },
        ]

        return await db["couriers"].aggregate(pipeline).to_list(length=200)


# ══════════════════════════════════════════════════════════════════
#  4. CONTROL DE TARIFAS
# ══════════════════════════════════════════════════════════════════

class RateController:

    @staticmethod
    async def list_rates(
        db: AsyncIOMotorDatabase,
        only_active: bool = False,
    ) -> list[dict]:
        """Lista todas las tarifas de envío configuradas."""
        query = {"is_active": True} if only_active else {}
        cursor = db["shipping_rates"].find(query).sort("zone_from", 1)
        docs = await cursor.to_list(length=500)
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    @staticmethod
    async def update_rate(
        db: AsyncIOMotorDatabase,
        rate_id: str,
        payload: ShippingRateUpdate,
        actor_id: str,
        actor_email: str,
    ) -> dict:
        """Actualiza una tarifa de envío. Registra antes/después en auditoría."""
        doc = await db["shipping_rates"].find_one({"_id": ObjectId(rate_id)})
        if not doc:
            raise ValueError("Tarifa no encontrada.")

        updates = payload.dict(exclude_none=True)
        if not updates:
            raise ValueError("No hay campos para actualizar.")

        before = {k: doc.get(k) for k in updates}
        updates["updated_by"] = actor_id
        updates["updated_at"] = datetime.utcnow()

        await db["shipping_rates"].update_one(
            {"_id": ObjectId(rate_id)}, {"$set": updates}
        )

        await write_audit_log(
            db,
            actor_id=actor_id,
            actor_email=actor_email,
            action="UPDATE_SHIPPING_RATE",
            resource="shipping_rates",
            resource_id=rate_id,
            before=before,
            after=updates,
        )

        doc.update(updates)
        doc["_id"] = str(doc["_id"])
        return doc


# ══════════════════════════════════════════════════════════════════
#  5. DASHBOARD — MÉTRICAS EN TIEMPO REAL
# ══════════════════════════════════════════════════════════════════

class DashboardController:

    # Tipo de cambio de respaldo (en producción: llamar a una FX API)
    _MAD_TO_EUR = 0.092

    @staticmethod
    async def get_metrics(db: AsyncIOMotorDatabase) -> DashboardMetrics:
        """
        Agrega en paralelo todas las métricas clave del Super Admin.
        Usa aggregation pipelines para minimizar round-trips a Mongo.
        """
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # ── Pedidos activos ──────────────────────────────────────
        active_orders = await db["orders"].count_documents(
            {"status": {"$in": ["pending", "picked_up", "in_transit"]}}
        )

        # ── Couriers en turno ────────────────────────────────────
        active_couriers = await db["couriers"].count_documents(
            {"status": {"$in": [CourierStatus.ON_SHIFT, CourierStatus.ACTIVE]}}
        )

        # ── Ingresos del día ─────────────────────────────────────
        revenue_pipeline = [
            {
                "$match": {
                    "type": TransactionType.INCOME,
                    "created_at": {"$gte": today_start},
                }
            },
            {
                "$group": {
                    "_id": "$currency",
                    "total": {"$sum": "$amount"},
                }
            },
        ]
        revenue_results = await db["transactions"].aggregate(revenue_pipeline).to_list(10)
        daily_rev: dict[str, float] = {r["_id"]: r["total"] for r in revenue_results}

        # ── Pagos pendientes a couriers ──────────────────────────
        payout_pipeline = [
            {"$match": {"is_paid": False}},
            {"$group": {"_id": None, "total": {"$sum": "$net_amount"}}},
        ]
        payout_result = await db["payroll_entries"].aggregate(payout_pipeline).to_list(1)
        pending_payouts = payout_result[0]["total"] if payout_result else 0.0

        # ── Balance de caja (efectivo) ───────────────────────────
        cash_pipeline = [
            {
                "$match": {
                    "payment_method": {
                        "$in": ["cash_mad", "cash_eur"]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$payment_method",
                    "total": {
                        "$sum": {
                            "$cond": [
                                {"$in": ["$type", [TransactionType.INCOME, TransactionType.CASH_IN]]},
                                "$amount",
                                {"$multiply": ["$amount", -1]},
                            ]
                        }
                    },
                }
            },
        ]
        cash_results = await db["transactions"].aggregate(cash_pipeline).to_list(10)
        cash_map = {r["_id"]: r["total"] for r in cash_results}

        # ── Alertas automáticas ──────────────────────────────────
        alerts = await DashboardController._build_alerts(db, today_start)

        mad_revenue = daily_rev.get(Currency.MAD, 0.0)
        eur_revenue = daily_rev.get(Currency.EUR, 0.0)

        return DashboardMetrics(
            active_orders=active_orders,
            active_couriers=active_couriers,
            daily_revenue_mad=round(mad_revenue, 2),
            daily_revenue_eur=round(eur_revenue, 2),
            pending_payouts=round(pending_payouts, 2),
            cash_balance_mad=round(cash_map.get("cash_mad", 0.0), 2),
            cash_balance_eur=round(cash_map.get("cash_eur", 0.0), 2),
            alerts=alerts,
        )

    @staticmethod
    async def _build_alerts(
        db: AsyncIOMotorDatabase,
        today_start: datetime,
    ) -> list[str]:
        """
        Genera alertas contextuales para el panel del Super Admin.
        Añade una alerta por cada condición anómala detectada.
        """
        alerts: list[str] = []

        # Couriers sin actividad en > 30 min durante turno
        stale_cutoff = datetime.utcnow() - timedelta(minutes=30)
        stale_couriers = await db["couriers"].count_documents(
            {
                "status": CourierStatus.ON_SHIFT,
                "location.updated_at": {"$lt": stale_cutoff},
            }
        )
        if stale_couriers:
            alerts.append(
                f"{stale_couriers} courier(s) sin actualizar ubicación en más de 30 min."
            )

        # Nóminas no pagadas con más de 7 días de antigüedad
        overdue_cutoff = datetime.utcnow() - timedelta(days=7)
        overdue_payroll = await db["payroll_entries"].count_documents(
            {
                "is_paid": False,
                "period_end": {"$lt": overdue_cutoff},
            }
        )
        if overdue_payroll:
            alerts.append(
                f"{overdue_payroll} nómina(s) pendientes de pago con más de 7 días."
            )

        # Pedidos bloqueados (sin cambio de estado en > 2h)
        stuck_cutoff = datetime.utcnow() - timedelta(hours=2)
        stuck_orders = await db["orders"].count_documents(
            {
                "status": "in_transit",
                "updated_at": {"$lt": stuck_cutoff},
            }
        )
        if stuck_orders:
            alerts.append(
                f"{stuck_orders} pedido(s) en tránsito sin actualización en más de 2h."
            )

        return alerts


# ══════════════════════════════════════════════════════════════════
#  HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════

def _default_permissions_for_role(role: UserRole) -> UserPermissions:
    """
    Asigna permisos por defecto según el rol.
    El Super Admin obtiene todos los permisos; el resto, mínimos.
    """
    presets: dict[UserRole, UserPermissions] = {
        UserRole.SUPER_ADMIN: UserPermissions(
            can_view_accounting=True,
            can_edit_accounting=True,
            can_manage_couriers=True,
            can_manage_users=True,
            can_view_live_map=True,
            can_export_data=True,
            can_edit_rates=True,
        ),
        UserRole.ACCOUNTING: UserPermissions(
            can_view_accounting=True,
            can_edit_accounting=True,
            can_export_data=True,
        ),
        UserRole.OPERATIONS: UserPermissions(
            can_manage_couriers=True,
            can_view_live_map=True,
        ),
        UserRole.COURIER: UserPermissions(),
        UserRole.CUSTOMER: UserPermissions(),
    }
    return presets.get(role, UserPermissions())
