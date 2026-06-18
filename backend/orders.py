"""Orders router: lifecycle + COD(cash) -> automatic cash-closing entry."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

from database import db
from auth import get_current_user, require_roles
from geo import currency_for_location, haversine_km
from realtime import manager

router = APIRouter(prefix="/api/orders")

ORDER_STATUSES = ("pending", "assigned", "picked_up", "in_transit", "delivered", "cancelled")


class GeoPoint(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None


class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    address: str
    city: Optional[str] = None
    country: Optional[str] = None
    amount: float = Field(..., ge=0)
    payment_method: Literal["cod_cash", "card", "prepaid"] = "cod_cash"
    items: Optional[List[str]] = None
    pickup: Optional[GeoPoint] = None
    dropoff: Optional[GeoPoint] = None
    notes: Optional[str] = None


class StatusUpdate(BaseModel):
    status: Literal["pending", "assigned", "picked_up", "in_transit", "delivered", "cancelled"]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _public(o: dict) -> dict:
    o = dict(o)
    o.pop("_id", None)
    return o


@router.post("")
async def create_order(payload: OrderCreate, user: dict = Depends(get_current_user)):
    currency = currency_for_location(payload.country, payload.city)
    distance_km = None
    if payload.pickup and payload.dropoff and None not in (
        payload.pickup.lat, payload.pickup.lng, payload.dropoff.lat, payload.dropoff.lng
    ):
        distance_km = haversine_km(
            payload.pickup.lat, payload.pickup.lng,
            payload.dropoff.lat, payload.dropoff.lng,
        )

    order = {
        "id": str(uuid.uuid4()),
        "code": "ORD-" + uuid.uuid4().hex[:6].upper(),
        "customer_name": payload.customer_name,
        "customer_phone": payload.customer_phone,
        "address": payload.address,
        "city": payload.city,
        "country": payload.country,
        "amount": round(payload.amount, 2),
        "currency": currency,
        "payment_method": payload.payment_method,
        "items": payload.items or [],
        "pickup": payload.pickup.model_dump() if payload.pickup else None,
        "dropoff": payload.dropoff.model_dump() if payload.dropoff else None,
        "distance_km": distance_km,
        "notes": payload.notes,
        "status": "pending",
        "paid": False,
        "assigned_rider_id": None,
        "cash_movement_id": None,
        "created_by": user["id"],
        "created_at": _now(),
        "updated_at": _now(),
        "delivered_at": None,
    }
    await db.orders.insert_one(order)
    await manager.broadcast({"type": "order_created", "order": _public(order)})
    return _public(order)


@router.get("")
async def list_orders(
    status: Optional[str] = Query(default=None),
    rider_id: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
):
    q = {}
    if status:
        q["status"] = status
    if rider_id:
        q["assigned_rider_id"] = rider_id
    # Riders only see their own orders
    if user.get("role") == "rider":
        q["assigned_rider_id"] = user["id"]
    raw = await db.orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"orders": raw}


@router.get("/{order_id}")
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return order


async def _create_cod_cash_entry(order: dict) -> Optional[str]:
    """When a COD-cash order is delivered, register an automatic cash 'entrada'."""
    if order.get("payment_method") != "cod_cash" or order.get("paid"):
        return None
    movement = {
        "id": str(uuid.uuid4()),
        "date": _today(),
        "type": "entrada",
        "concept": f"Pedido {order['code']} (COD efectivo) - {order.get('customer_name', '')}".strip(),
        "amount": round(order["amount"], 2),
        "method": "efectivo",
        "currency": order.get("currency", "MAD"),
        "order_id": order["id"],
        "created_at": _now(),
    }
    await db.cash_movements.insert_one(movement)
    return movement["id"]


@router.patch("/{order_id}/status")
async def update_status(order_id: str, payload: StatusUpdate, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    updates = {"status": payload.status, "updated_at": _now()}
    cash_entry_id = None

    if payload.status == "delivered" and order.get("status") != "delivered":
        updates["delivered_at"] = _now()
        cash_entry_id = await _create_cod_cash_entry(order)
        if cash_entry_id:
            updates["paid"] = True
            updates["cash_movement_id"] = cash_entry_id

    await db.orders.update_one({"id": order_id}, {"$set": updates})
    new_order = await db.orders.find_one({"id": order_id}, {"_id": 0})

    await manager.broadcast({"type": "order_status", "order": new_order})
    if cash_entry_id:
        await manager.broadcast({
            "type": "cash_entry_created",
            "order_id": order_id,
            "amount": new_order["amount"],
            "currency": new_order.get("currency"),
            "date": _today(),
        })
    return new_order
