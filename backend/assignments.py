"""Núcleo de logística y operaciones (Bloque C).

Asignación atómica del repartidor (Abeja) más cercano por proximidad usando el
índice geoespacial 2dsphere de MongoDB ($geoNear), geofencing por ciudad y
trazabilidad completa mediante el historial de asignaciones.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pymongo import ReturnDocument

from core import db
from geo import haversine_km

# Radio de zona de trabajo (km) para el geofencing de repartidores
CITY_ZONE_RADIUS_KM = 10
# Máx. intentos de la asignación atómica (anti condición de carrera)
ASSIGN_MAX_ATTEMPTS = 3
# Estados de pedido que pueden volver a la cola si la Abeja queda libre
RETURNABLE_STATUSES = ['accepted', 'assigned', 'preparing']


async def get_driver_city(driver: dict) -> Optional[dict]:
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


async def atomic_claim_nearest(order_id, lat, lng, max_km, actor, reason=None):
    """Asignación atómica del repartidor más cercano (anti condición de carrera).

    Hasta ASSIGN_MAX_ATTEMPTS intentos, excluyendo Abejas que otro proceso cogió primero.
    Devuelve dict {driver, distance_km, excluded} si asignó, o None si no fue posible.
    """
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
    return {'driver': chosen, 'distance_km': distance_km, 'excluded': len(excluded_driver_ids)}


async def auto_assign_order(order_id):
    """Despacho automático: asigna la Abeja más cercana al punto de recogida.

    Para exprés usa el origen real (A); para marketplace, el centro de la ciudad.
    Silencioso: si no hay punto de recogida o no hay Abejas libres, el pedido queda en la cola.
    """
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order or order.get('driver_id') or order.get('status') != 'pending':
        return None
    if order.get('order_type') == 'express' and order.get('origin_lat') is not None and order.get('origin_lng') is not None:
        pickup_lat, pickup_lng = order['origin_lat'], order['origin_lng']
    else:
        city_id = order.get('city_id')
        if not city_id:
            return None
        city = await db.cities.find_one({'id': city_id}, {'_id': 0, 'lat': 1, 'lng': 1})
        if not city:
            return None
        pickup_lat, pickup_lng = city['lat'], city['lng']
    return await atomic_claim_nearest(
        order_id, pickup_lat, pickup_lng, CITY_ZONE_RADIUS_KM, actor=None, reason='auto_dispatch'
    )


def history_query(action=None, driver_id=None, date_from=None, date_to=None):
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
