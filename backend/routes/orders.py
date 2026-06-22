"""Rutas de pedidos."""
import asyncio
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user, manager
from models import Order, OrderCreate, OrderStatusUpdate, ExpressOrderCreate
import telegram_alerts
import email_service
from assignments import auto_assign_order, release_driver
from accounting import record_order_income

router = APIRouter()


@router.get("/public/orders/{order_id}/tracking")
async def public_order_tracking(order_id: str):
    """Seguimiento público de un pedido (sin login): estado, ruta y ubicación del repartidor."""
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    driver_name = None
    driver_vehicle = None
    driver_location = None
    if order.get('driver_id'):
        d = await db.users.find_one({'id': order['driver_id']}, {'_id': 0})
        if d:
            driver_name = d.get('name')
            driver_vehicle = d.get('vehicle_type')
            loc = d.get('current_location')
            if loc and loc.get('lat') is not None:
                driver_location = {'lat': loc['lat'], 'lng': loc['lng']}

    # La ubicación en vivo (WebSocket) tiene prioridad si existe
    live = manager.get_driver_location(order_id)
    if live and live.get('lat') is not None:
        driver_location = {'lat': live['lat'], 'lng': live['lng']}

    origin = destination = None
    if order.get('origin_lat') is not None and order.get('destination_lat') is not None:
        origin = {'lat': order['origin_lat'], 'lng': order['origin_lng'], 'label': order.get('origin_name')}
        destination = {'lat': order['destination_lat'], 'lng': order['destination_lng'], 'label': order.get('destination_name')}

    return {
        'order_id': order['id'],
        'status': order['status'],
        'driver_name': driver_name,
        'driver_vehicle_type': driver_vehicle,
        'driver_location': driver_location,
        'origin': origin,
        'destination': destination,
        'price': order.get('total_amount'),
        'currency': order.get('currency') or 'EUR',
        'distance_km': order.get('distance_km'),
        'eta_mins': order.get('eta_mins'),
        'order_type': order.get('order_type', 'marketplace'),
        'updated_at': order.get('updated_at'),
    }


@router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers can create orders")

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

    # Alerta al administrador por Telegram (no bloquea la respuesta)
    await telegram_alerts.notify_new_order(doc)

    return order


@router.post("/orders/express", response_model=Order)
async def create_express_order(order_data: ExpressOrderCreate, current_user: dict = Depends(get_current_user)):
    """Crea un pedido exprés de mensajería punto a punto (A->B), sin negocio ni carrito."""
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers can create orders")

    city_name = None
    city_id = order_data.origin_city_id
    if city_id:
        city = await db.cities.find_one({'id': city_id}, {'_id': 0, 'name': 1})
        city_name = city['name'] if city else None

    order = Order(
        customer_id=current_user['id'],
        business_id=None,
        items=[],
        total_amount=order_data.fee,
        delivery_address=order_data.destination_name,
        city_id=city_id,
        city_name=city_name,
        status='pending',
        order_type='express',
        vehicle_type=order_data.vehicle_type,
        origin_name=order_data.origin_name,
        origin_lat=order_data.origin_lat,
        origin_lng=order_data.origin_lng,
        destination_name=order_data.destination_name,
        destination_lat=order_data.destination_lat,
        destination_lng=order_data.destination_lng,
        distance_km=order_data.distance_km,
        eta_mins=order_data.eta_mins,
        currency=order_data.currency,
    )
    doc = order.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()

    await db.orders.insert_one(doc)
    await telegram_alerts.notify_new_order(doc)

    # Despacho automático por proximidad: asigna la Abeja más cercana al origen (best-effort)
    try:
        await auto_assign_order(order.id)
    except Exception:
        pass
    # Notificación automática de confirmación al cliente (best-effort, no bloqueante)
    if current_user.get('email'):
        asyncio.create_task(email_service.send_order_confirmation(current_user['email'], doc))
    return order


@router.post("/orders/logistics-quote", response_model=Order)
async def create_logistics_quote(order_data: ExpressOrderCreate, current_user: dict = Depends(get_current_user)):
    """Solicitud de cotización para Camión / Logística Pesada.
    NO calcula precio automático: crea el pedido en estado 'pending_quote' (total 0)
    para que la administración fije la tarifa manualmente según el tipo de carga."""
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers can request quotes")

    city_name = None
    city_id = order_data.origin_city_id
    if city_id:
        city = await db.cities.find_one({'id': city_id}, {'_id': 0, 'name': 1})
        city_name = city['name'] if city else None

    order = Order(
        customer_id=current_user['id'],
        business_id=None,
        items=[],
        total_amount=0,
        delivery_address=order_data.destination_name,
        city_id=city_id,
        city_name=city_name,
        status='pending_quote',
        order_type='logistics',
        vehicle_type='truck',
        origin_name=order_data.origin_name,
        origin_lat=order_data.origin_lat,
        origin_lng=order_data.origin_lng,
        destination_name=order_data.destination_name,
        destination_lat=order_data.destination_lat,
        destination_lng=order_data.destination_lng,
        distance_km=order_data.distance_km,
        eta_mins=order_data.eta_mins,
        currency=order_data.currency,
    )
    doc = order.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.orders.insert_one(doc)
    await telegram_alerts.notify_new_order(doc)
    # Email automático de confirmación de cotización al cliente (best-effort, no bloqueante)
    if current_user.get('email'):
        asyncio.create_task(email_service.send_logistics_quote_received(current_user['email'], doc))
    return order


@router.patch("/orders/{order_id}/set-quote-price")
async def set_logistics_quote_price(order_id: str, payload: dict, current_user: dict = Depends(get_current_user)):
    """La administración (Fundador/Gestor) fija manualmente el precio de una cotización de logística."""
    if current_user.get('role') not in ('admin', 'manager'):
        raise HTTPException(status_code=403, detail="Solo la administración puede fijar el precio")
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if order.get('order_type') != 'logistics':
        raise HTTPException(status_code=400, detail="Este pedido no es una cotización de logística")
    try:
        price = float(payload.get('total_amount'))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="total_amount inválido")
    if price <= 0:
        raise HTTPException(status_code=400, detail="El precio debe ser mayor que 0")
    now = datetime.now(timezone.utc).isoformat()
    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'total_amount': price, 'status': 'quoted', 'updated_at': now}},
    )
    # Email automático al cliente con la tarifa final + enlace para confirmar (best-effort)
    customer = await db.users.find_one({'id': order.get('customer_id')}, {'_id': 0, 'email': 1})
    if customer and customer.get('email'):
        asyncio.create_task(email_service.send_logistics_quote_priced(
            customer['email'], {**order, 'total_amount': price, 'status': 'quoted'}
        ))
    return {'message': 'Precio fijado · cliente notificado', 'id': order_id, 'total_amount': price, 'status': 'quoted'}


@router.post("/orders/{order_id}/confirm-quote", response_model=Order)
async def confirm_logistics_quote(order_id: str, current_user: dict = Depends(get_current_user)):
    """El cliente confirma la cotización de logística ya cotizada → entra al flujo normal de despacho."""
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if order.get('customer_id') != current_user['id']:
        raise HTTPException(status_code=403, detail="No puedes confirmar este pedido")
    if order.get('status') != 'quoted':
        raise HTTPException(status_code=400, detail="Esta cotización no está lista para confirmar")
    now = datetime.now(timezone.utc).isoformat()
    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'status': 'pending', 'confirmed_at': now, 'updated_at': now}},
    )
    updated = await db.orders.find_one({'id': order_id}, {'_id': 0})
    await telegram_alerts.notify_new_order(updated)
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    return updated



@router.get("/orders", response_model=List[Order])
async def get_orders(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user['role'] == 'customer':
        query['customer_id'] = current_user['id']
    elif current_user['role'] == 'driver':
        query['driver_id'] = current_user['id']
    elif current_user['role'] == 'business':
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


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if isinstance(order.get('created_at'), str):
        order['created_at'] = datetime.fromisoformat(order['created_at'])
    if isinstance(order.get('updated_at'), str):
        order['updated_at'] = datetime.fromisoformat(order['updated_at'])
    return order


@router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, status_update: OrderStatusUpdate, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {'status': status_update.status, 'updated_at': now}
    if status_update.status == 'delivered':
        update_fields['delivered_at'] = now
    await db.orders.update_one({'id': order_id}, {'$set': update_fields})

    # Al entregar: registra el ingreso en contabilidad (idempotente) y libera la Abeja
    if status_update.status == 'delivered':
        await record_order_income({**order, **update_fields})
        # Notificación automática de entrega al cliente (best-effort)
        customer = await db.users.find_one({'id': order.get('customer_id')}, {'_id': 0, 'email': 1})
        if customer and customer.get('email'):
            asyncio.create_task(email_service.send_order_delivered(customer['email'], {**order, **update_fields}))
    if status_update.status in ('delivered', 'cancelled') and order.get('driver_id'):
        await release_driver(order.get('driver_id'))

    return {'message': 'Order status updated', 'status': status_update.status}


@router.post("/orders/{order_id}/assign-driver")
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
