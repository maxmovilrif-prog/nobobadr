"""Rutas de administración: tracking de flota y estadísticas."""
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from core import db, manager, get_current_admin, get_current_manager_or_admin, hash_password, get_scope_city_ids
from accounting import ACCT_MAD_TO_EUR
import telegram_alerts

router = APIRouter()


# =========================
# GESTIÓN DE CUENTAS DE GESTOR (solo Fundador)
# =========================

class ManagerCreate(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    region_id: str = Field(min_length=1)


def _public_manager(u: dict) -> dict:
    return {
        'id': u['id'], 'name': u.get('name'), 'email': u.get('email'),
        'role': u.get('role'), 'is_active': u.get('is_active', True),
        'region_id': u.get('region_id'), 'region_name': u.get('region_name'),
        'created_at': u.get('created_at'),
    }


@router.post("/admin/managers")
async def create_manager(payload: ManagerCreate, current_user: dict = Depends(get_current_admin)):
    """El Fundador crea un Gestor Regional, vinculado a UNA región (aislamiento total)."""
    email = payload.email.strip().lower()
    existing = await db.users.find_one({'email': email}, {'_id': 0, 'id': 1})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")
    region = await db.regions.find_one({'id': payload.region_id}, {'_id': 0, 'id': 1, 'name': 1})
    if not region:
        raise HTTPException(status_code=400, detail="Región no válida")
    doc = {
        'id': str(uuid.uuid4()),
        'name': payload.name.strip(),
        'email': email,
        'role': 'manager',
        'password_hash': hash_password(payload.password),
        'is_active': True,
        'region_id': region['id'],
        'region_name': region['name'],
        'created_by': current_user.get('id'),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'is_available': False,
        'vehicle_type': None,
        'current_location': None,
    }
    await db.users.insert_one(doc)
    return _public_manager(doc)


@router.get("/admin/managers")
async def list_managers(current_user: dict = Depends(get_current_admin)):
    """Lista las cuentas de Gestor (solo Fundador)."""
    rows = await db.users.find({'role': 'manager'}, {'_id': 0}).sort('created_at', -1).to_list(500)
    return {'count': len(rows), 'managers': [_public_manager(u) for u in rows]}


@router.delete("/admin/managers/{manager_id}")
async def delete_manager(manager_id: str, current_user: dict = Depends(get_current_admin)):
    """Elimina una cuenta de Gestor (solo Fundador)."""
    res = await db.users.delete_one({'id': manager_id, 'role': 'manager'})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Gestor no encontrado")
    return {'message': 'Gestor eliminado', 'id': manager_id}

IDLE_THRESHOLD_SECONDS = 90


def _to_eur(amount, currency):
    amount = float(amount or 0)
    return round(amount * ACCT_MAD_TO_EUR, 2) if currency == 'MAD' else round(amount, 2)


def _parse_iso(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(v)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


@router.get("/admin/active-drivers")
async def admin_active_drivers(current_user: dict = Depends(get_current_manager_or_admin)):
    """
    Devuelve las 'Abejas' (conductores) activas en tiempo real.
    Aislamiento regional: un Gestor solo ve la flota y pedidos de SU región;
    el Fundador ve todo.
    """
    scope = await get_scope_city_ids(current_user)  # None = global (Fundador)
    region_id = current_user.get('region_id') if scope is not None else None
    fleet = []
    seen_order_ids = set()
    now = datetime.now(timezone.utc)

    # 1. Conductores en vivo (con pedido activo, ubicación por WebSocket)
    for order_id, loc in manager.driver_locations.items():
        order = await db.orders.find_one({'id': order_id}, {'_id': 0})
        # Aislamiento regional: omitir pedidos fuera de la región del Gestor
        if scope is not None and (not order or order.get('city_id') not in scope):
            continue
        seen_order_ids.add(order_id)
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

    # 2. Conductores disponibles registrados (filtrados por región si es Gestor)
    drv_query = {'role': 'driver', 'is_available': True}
    if region_id is not None:
        drv_query['region_id'] = region_id
    drivers = await db.users.find(
        drv_query,
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

    active_orders_q = {'status': 'in_transit'}
    if scope is not None:
        active_orders_q['city_id'] = {'$in': scope}
    active_orders = await db.orders.count_documents(active_orders_q)
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
async def admin_stats(current_user: dict = Depends(get_current_manager_or_admin)):
    scope = await get_scope_city_ids(current_user)  # None = global
    region_id = current_user.get('region_id') if scope is not None else None
    oq = {} if scope is None else {'city_id': {'$in': scope}}
    dq = {'role': 'driver'} if region_id is None else {'role': 'driver', 'region_id': region_id}
    total_orders = await db.orders.count_documents(oq)
    in_transit = await db.orders.count_documents({**oq, 'status': 'in_transit'})
    delivered = await db.orders.count_documents({**oq, 'status': 'delivered'})
    total_drivers = await db.users.count_documents(dq)
    available_drivers = await db.users.count_documents({**dq, 'is_available': True})
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


@router.get("/admin/kpis")
async def admin_kpis(current_user: dict = Depends(get_current_admin)):
    """Cuadro de mandos del Fundador: pedidos/día (7d), ingresos del mes,
    tiempo medio de entrega y ranking de Abejas más activas (30d)."""
    now = datetime.now(timezone.utc)
    today = now.date()
    month_start = today.replace(day=1)
    last_30 = now - timedelta(days=30)
    # Optimización: solo cargamos pedidos recientes (60d) para las ventanas de cálculo;
    # las entregas históricas se cuentan aparte con count_documents.
    window_cutoff = (now - timedelta(days=60)).isoformat()

    orders = await db.orders.find(
        {'created_at': {'$gte': window_cutoff}},
        {'_id': 0, 'status': 1, 'total_amount': 1, 'currency': 1,
         'created_at': 1, 'delivered_at': 1, 'driver_id': 1}
    ).to_list(50000)
    delivered_total = await db.orders.count_documents({'status': 'delivered'})

    # Serie de pedidos por día (últimos 7 días)
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    series = {d.isoformat(): {'date': d.isoformat(), 'orders': 0, 'delivered': 0} for d in days}
    orders_today = 0
    revenue_month_eur = 0.0
    delivery_durations = []
    bees = {}

    for o in orders:
        created = _parse_iso(o.get('created_at'))
        status = o.get('status')
        if created:
            ckey = created.date().isoformat()
            if ckey in series:
                series[ckey]['orders'] += 1
            if created.date() == today:
                orders_today += 1
        if status == 'delivered':
            delivered = _parse_iso(o.get('delivered_at'))
            # Ingresos del mes (pedidos entregados este mes)
            eff = delivered or created
            if eff and eff.date() >= month_start:
                revenue_month_eur += _to_eur(o.get('total_amount'), o.get('currency'))
            if delivered and delivered.date().isoformat() in series:
                series[delivered.date().isoformat()]['delivered'] += 1
            # Tiempo de entrega
            if created and delivered and delivered > created:
                mins = (delivered - created).total_seconds() / 60.0
                if 0 < mins < 60 * 24 * 7:  # descarta valores absurdos
                    delivery_durations.append(mins)
            # Ranking de Abejas (últimos 30 días)
            did = o.get('driver_id')
            if did and (delivered or created) and (delivered or created) >= last_30:
                b = bees.setdefault(did, {'driver_id': did, 'deliveries': 0, 'revenue_eur': 0.0})
                b['deliveries'] += 1
                b['revenue_eur'] = round(b['revenue_eur'] + _to_eur(o.get('total_amount'), o.get('currency')), 2)

    # Nombres de las Abejas del ranking
    top = sorted(bees.values(), key=lambda x: -x['deliveries'])[:5]
    if top:
        names = {}
        async for u in db.users.find({'id': {'$in': [b['driver_id'] for b in top]}}, {'_id': 0, 'id': 1, 'name': 1, 'vehicle_type': 1}):
            names[u['id']] = u
        for b in top:
            u = names.get(b['driver_id'], {})
            b['driver_name'] = u.get('name', 'Abeja')
            b['vehicle_type'] = u.get('vehicle_type')

    avg_delivery = round(sum(delivery_durations) / len(delivery_durations), 1) if delivery_durations else None

    return {
        'orders_today': orders_today,
        'orders_per_day': list(series.values()),
        'revenue_month_eur': round(revenue_month_eur, 2),
        'delivered_total': delivered_total,
        'avg_delivery_mins': avg_delivery,
        'top_bees': top,
        'as_of': now.isoformat(),
    }


@router.get("/admin/my-region/kpis")
async def my_region_kpis(current_user: dict = Depends(get_current_manager_or_admin)):
    """Mini-cuadro de mandos LOCAL del Gestor Regional (aislado a su delegación).
    No expone datos globales: solo pedidos/riders/ingresos de las ciudades de su región."""
    scope = await get_scope_city_ids(current_user)  # None = Fundador (global)
    if scope is None:
        # El Fundador usa su panel global (/admin/kpis); aquí no hay vista regional.
        return {'is_founder': True, 'region': None}

    region_id = current_user.get('region_id')
    region = await db.regions.find_one({'id': region_id}, {'_id': 0}) if region_id else None
    region_name = region.get('name') if region else None

    now = datetime.now(timezone.utc)
    today = now.date()
    month_start = today.replace(day=1)
    window_cutoff = (now - timedelta(days=60)).isoformat()
    oq = {'city_id': {'$in': scope}}

    orders = await db.orders.find(
        {**oq, 'created_at': {'$gte': window_cutoff}},
        {'_id': 0, 'status': 1, 'total_amount': 1, 'currency': 1, 'created_at': 1, 'delivered_at': 1}
    ).to_list(50000)

    orders_today = 0
    delivered_today = 0
    revenue_today_eur = 0.0
    revenue_month_eur = 0.0
    for o in orders:
        created = _parse_iso(o.get('created_at'))
        if created and created.date() == today:
            orders_today += 1
        if o.get('status') == 'delivered':
            eff = _parse_iso(o.get('delivered_at')) or created
            if eff and eff.date() == today:
                delivered_today += 1
                revenue_today_eur += _to_eur(o.get('total_amount'), o.get('currency'))
            if eff and eff.date() >= month_start:
                revenue_month_eur += _to_eur(o.get('total_amount'), o.get('currency'))

    in_transit = await db.orders.count_documents({**oq, 'status': 'in_transit'})
    total_riders = await db.users.count_documents({'role': 'driver', 'region_id': region_id})
    active_riders = await db.users.count_documents({'role': 'driver', 'region_id': region_id, 'is_available': True})

    return {
        'is_founder': False,
        'region': {'id': region_id, 'name': region_name, 'cities': region.get('city_ids', []) if region else []},
        'orders_today': orders_today,
        'delivered_today': delivered_today,
        'in_transit': in_transit,
        'active_riders': active_riders,
        'total_riders': total_riders,
        'revenue_today_eur': round(revenue_today_eur, 2),
        'revenue_month_eur': round(revenue_month_eur, 2),
        'as_of': now.isoformat(),
    }



# =========================
# TELEGRAM ALERTS CONFIG
# =========================

@router.get("/admin/telegram/status")
async def telegram_status(current_user: dict = Depends(get_current_admin)):
    return {"configured": telegram_alerts.is_configured()}


@router.post("/admin/telegram/test")
async def telegram_test(current_user: dict = Depends(get_current_admin)):
    if not telegram_alerts.is_configured():
        return {"sent": False, "detail": "Telegram no está configurado (faltan token/chat_id)."}
    ok = await telegram_alerts.send_telegram_message(
        "✅ <b>Nubo</b>: alertas de Telegram configuradas correctamente."
    )
    return {"sent": ok}


@router.get("/admin/telegram/chats")
async def telegram_chats(current_user: dict = Depends(get_current_admin)):
    """Lista los chats recientes que han escrito al bot (para encontrar el chat_id)."""
    chats = await telegram_alerts.get_recent_chats()
    return {"chats": chats}
