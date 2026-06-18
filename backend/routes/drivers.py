"""Rutas de conductores."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user
from models import Order

router = APIRouter()


@router.get("/drivers/available-orders", response_model=List[Order])
async def get_available_orders(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'driver':
        raise HTTPException(status_code=403, detail="Only drivers can view available orders")

    orders = await db.orders.find({'driver_id': None, 'status': 'pending', 'payment_status': 'paid'}, {'_id': 0}).to_list(1000)
    for order in orders:
        if isinstance(order.get('created_at'), str):
            order['created_at'] = datetime.fromisoformat(order['created_at'])
        if isinstance(order.get('updated_at'), str):
            order['updated_at'] = datetime.fromisoformat(order['updated_at'])
    return orders


@router.patch("/drivers/availability")
async def update_availability(is_available: bool, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'driver':
        raise HTTPException(status_code=403, detail="Only drivers can update availability")
    await db.users.update_one(
        {'id': current_user['id']},
        {'$set': {'is_available': is_available}}
    )
    return {'message': 'Availability updated', 'is_available': is_available}
