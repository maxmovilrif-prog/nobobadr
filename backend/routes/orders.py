"""Rutas de pedidos."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user
from models import Order, OrderCreate, OrderStatusUpdate
import telegram_alerts

router = APIRouter()


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
    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'status': status_update.status, 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )
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
