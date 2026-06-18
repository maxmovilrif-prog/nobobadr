"""Rutas de logística y operaciones (Bloque C): cercanía, asignación y historial."""
import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel

from core import db, get_current_user, get_current_admin
from assignments import (
    atomic_claim_nearest, release_driver, log_assignment, history_query,
)

router = APIRouter()


@router.get("/drivers/nearest")
async def nearest_drivers(lat: float, lng: float, max_km: Optional[float] = None,
                          limit: int = 5, current_user: dict = Depends(get_current_user)):
    """Repartidores disponibles más cercanos a un punto, ordenados por distancia (admin/business)."""
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
    lat: Optional[float] = None
    lng: Optional[float] = None
    max_km: Optional[float] = None


@router.post("/orders/{order_id}/assign-nearest")
async def assign_nearest_driver(order_id: str, req: AssignNearestRequest,
                                current_user: dict = Depends(get_current_user)):
    """Auto-asigna atómicamente el repartidor disponible más cercano al punto de recogida (admin/business).

    Si no se indican lat/lng, usa el origen del pedido exprés o el centro de su ciudad.
    """
    if current_user['role'] not in ('admin', 'business'):
        raise HTTPException(status_code=403, detail="Admin or business access required")

    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get('driver_id'):
        raise HTTPException(status_code=400, detail="Order already has a driver assigned")

    lat, lng = req.lat, req.lng
    if lat is None or lng is None:
        if order.get('order_type') == 'express' and order.get('origin_lat') is not None:
            lat, lng = order['origin_lat'], order['origin_lng']
        elif order.get('city_id'):
            city = await db.cities.find_one({'id': order['city_id']}, {'_id': 0, 'lat': 1, 'lng': 1})
            if city:
                lat, lng = city['lat'], city['lng']
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="No se puede determinar el punto de recogida del pedido")

    result = await atomic_claim_nearest(order_id, lat, lng, req.max_km, current_user)
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


@router.post("/orders/{order_id}/return-to-queue")
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
    await release_driver(prev_driver_id)
    await log_assignment(order_id, prev_driver, 'returned', current_user, reason='manual_return')
    return {'message': 'Order returned to queue', 'order_id': order_id}


@router.get("/admin/ops/orders")
async def ops_orders(current_user: dict = Depends(get_current_admin)):
    """Cola de operaciones (admin): pedidos pendientes sin Abeja y pedidos activos asignados."""
    pending = await db.orders.find(
        {'driver_id': None, 'status': {'$in': ['pending', 'assigned']}},
        {'_id': 0}
    ).sort('created_at', -1).to_list(200)
    active = await db.orders.find(
        {'driver_id': {'$ne': None}, 'status': {'$nin': ['delivered', 'cancelled']}},
        {'_id': 0}
    ).sort('updated_at', -1).to_list(200)

    driver_ids = [o['driver_id'] for o in active if o.get('driver_id')]
    drivers = {}
    if driver_ids:
        async for d in db.users.find({'id': {'$in': driver_ids}}, {'_id': 0, 'id': 1, 'name': 1, 'vehicle_type': 1}):
            drivers[d['id']] = d

    def _fmt(o, with_driver=False):
        item = {
            'id': o['id'],
            'status': o['status'],
            'order_type': o.get('order_type', 'marketplace'),
            'origin_name': o.get('origin_name'),
            'origin_lat': o.get('origin_lat'),
            'origin_lng': o.get('origin_lng'),
            'destination_name': o.get('destination_name') or o.get('delivery_address'),
            'city_id': o.get('city_id'),
            'city_name': o.get('city_name'),
            'total_amount': o.get('total_amount'),
            'currency': o.get('currency') or 'EUR',
            'distance_km': o.get('distance_km'),
            'created_at': o.get('created_at'),
        }
        if with_driver:
            d = drivers.get(o.get('driver_id'), {})
            item['driver_id'] = o.get('driver_id')
            item['driver_name'] = d.get('name', 'Abeja')
            item['driver_vehicle_type'] = d.get('vehicle_type')
        return item

    return {
        'pending': [_fmt(o) for o in pending],
        'active': [_fmt(o, with_driver=True) for o in active],
        'pending_count': len(pending),
        'active_count': len(active),
    }


@router.get("/admin/assignment-history")
async def get_assignment_history(
    limit: int = 50,
    action: Optional[str] = None,
    driver_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_admin),
):
    """Historial de asignaciones para trazabilidad total (admin). Soporta filtros."""
    query = history_query(action, driver_id, date_from, date_to)
    events = await db.assignment_history.find(query, {'_id': 0}).sort('created_at', -1).to_list(max(1, min(limit, 500)))
    raw = await db.assignment_history.find({}, {'_id': 0, 'driver_id': 1, 'driver_name': 1}).to_list(2000)
    seen, drivers_in_history = set(), []
    for r in raw:
        did = r.get('driver_id')
        if did and did not in seen:
            seen.add(did)
            drivers_in_history.append({'id': did, 'name': r.get('driver_name') or 'N/D'})
    return {'count': len(events), 'events': events, 'drivers': drivers_in_history}


@router.get("/admin/assignment-history/export")
async def export_assignment_history(
    action: Optional[str] = None,
    driver_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_admin),
):
    """Exporta el historial de asignaciones filtrado a CSV (admin)."""
    query = history_query(action, driver_id, date_from, date_to)
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
