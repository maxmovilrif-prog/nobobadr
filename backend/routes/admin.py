"""Rutas de administración: tracking de flota y estadísticas."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from core import db, manager, get_current_admin

router = APIRouter()

IDLE_THRESHOLD_SECONDS = 90


@router.get("/admin/active-drivers")
async def admin_active_drivers(current_user: dict = Depends(get_current_admin)):
    """
    Devuelve todas las 'Abejas' (conductores) activas en tiempo real.
    Combina las ubicaciones en vivo (WebSocket) con los conductores disponibles.
    """
    fleet = []
    seen_order_ids = set()
    now = datetime.now(timezone.utc)

    # 1. Conductores en vivo (con pedido activo, ubicación por WebSocket)
    for order_id, loc in manager.driver_locations.items():
        seen_order_ids.add(order_id)
        order = await db.orders.find_one({'id': order_id}, {'_id': 0})
        idle_seconds = None
        idle = False
        ts = loc.get("timestamp")
        if ts:
            try:
                last_seen = datetime.fromisoformat(ts)
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                idle_seconds = int((now - last_seen).total_seconds())
                idle = idle_seconds > IDLE_THRESHOLD_SECONDS
            except (ValueError, TypeError):
                pass
        fleet.append({
            "order_id": order_id,
            "driver_name": loc.get("driver_name", "Abeja"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "status": loc.get("status", "en_camino"),
            "timestamp": loc.get("timestamp"),
            "idle_seconds": idle_seconds,
            "idle": idle,
            "delivery_address": order.get("delivery_address") if order else None,
            "live": True,
        })

    # 2. Conductores disponibles registrados (pueden no tener pedido activo)
    drivers = await db.users.find(
        {'role': 'driver', 'is_available': True},
        {'_id': 0, 'password_hash': 0}
    ).to_list(500)
    for d in drivers:
        loc = d.get('current_location')
        fleet.append({
            "driver_id": d.get("id"),
            "driver_name": d.get("name", "Abeja"),
            "lat": loc.get("lat") if loc else None,
            "lng": loc.get("lng") if loc else None,
            "vehicle_type": d.get("vehicle_type"),
            "status": "disponible",
            "live": False,
        })

    active_orders = await db.orders.count_documents({'status': 'in_transit'})
    idle_count = sum(1 for d in fleet if d.get("idle"))

    return {
        "count": len(fleet),
        "live_count": len(seen_order_ids),
        "available_count": len(drivers),
        "idle_count": idle_count,
        "active_orders": active_orders,
        "drivers": fleet,
    }


@router.get("/admin/stats")
async def admin_stats(current_user: dict = Depends(get_current_admin)):
    total_orders = await db.orders.count_documents({})
    in_transit = await db.orders.count_documents({'status': 'in_transit'})
    delivered = await db.orders.count_documents({'status': 'delivered'})
    total_drivers = await db.users.count_documents({'role': 'driver'})
    available_drivers = await db.users.count_documents({'role': 'driver', 'is_available': True})
    total_businesses = await db.businesses.count_documents({})
    return {
        "total_orders": total_orders,
        "in_transit": in_transit,
        "delivered": delivered,
        "total_drivers": total_drivers,
        "available_drivers": available_drivers,
        "total_businesses": total_businesses,
        "live_drivers": len(manager.driver_locations),
    }
