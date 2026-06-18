"""Rutas de dropshipping."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user
from models import DropshippingProduct, DropshippingProductCreate

router = APIRouter()


@router.post("/dropshipping/products", response_model=DropshippingProduct)
async def create_dropshipping_product(product_data: DropshippingProductCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can create products")

    selling_price = product_data.original_price * (1 + product_data.commission_percentage / 100)

    product_dict = product_data.model_dump()
    product_dict['business_id'] = current_user['id']
    product_dict['selling_price'] = round(selling_price, 2)

    product = DropshippingProduct(**product_dict)
    doc = product.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.dropshipping_products.insert_one(doc)
    return product


@router.get("/dropshipping/products", response_model=List[DropshippingProduct])
async def get_dropshipping_products(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    query = {}
    if platform:
        query['platform'] = platform
    if category:
        query['category'] = category
    if min_price is not None:
        query['selling_price'] = {'$gte': min_price}
    if max_price is not None:
        query.setdefault('selling_price', {})['$lte'] = max_price

    products = await db.dropshipping_products.find(query, {'_id': 0}).to_list(1000)
    for product in products:
        if isinstance(product.get('created_at'), str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    return products


@router.get("/dropshipping/orders-to-purchase")
async def get_orders_to_purchase(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users")

    orders = await db.orders.find({
        'payment_status': 'paid',
        'status': {'$in': ['pending', 'accepted']}
    }, {'_id': 0}).to_list(1000)

    if not orders:
        return []

    product_ids = set()
    customer_ids = set()
    for order in orders:
        customer_ids.add(order['customer_id'])
        for item in order['items']:
            product_ids.add(item['product_id'])

    dropship_products = await db.dropshipping_products.find(
        {'id': {'$in': list(product_ids)}}, {'_id': 0}
    ).to_list(None)
    products_map = {prod['id']: prod for prod in dropship_products}

    customers = await db.users.find(
        {'id': {'$in': list(customer_ids)}}, {'_id': 0}
    ).to_list(None)
    customers_map = {cust['id']: cust for cust in customers}

    purchase_list = []
    for order in orders:
        customer = customers_map.get(order['customer_id'])
        for item in order['items']:
            dropship_prod = products_map.get(item['product_id'])
            if dropship_prod:
                commission = dropship_prod['selling_price'] - dropship_prod['original_price']
                purchase_list.append({
                    'order_id': order['id'],
                    'product_name': item['product_name'],
                    'quantity': item['quantity'],
                    'platform': dropship_prod['platform'],
                    'product_url': dropship_prod['product_url'],
                    'original_price': dropship_prod['original_price'],
                    'total_to_pay': dropship_prod['original_price'] * item['quantity'],
                    'commission_earned': commission * item['quantity'],
                    'customer_name': customer['name'] if customer else 'Unknown',
                    'customer_email': customer['email'] if customer else '',
                    'customer_phone': customer['phone'] if customer else '',
                    'delivery_address': order['delivery_address'],
                    'order_date': order['created_at']
                })
    return purchase_list


@router.get("/dropshipping/stats")
async def get_dropshipping_stats(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users")

    orders = await db.orders.find({'payment_status': 'paid'}, {'_id': 0}).to_list(10000)
    if not orders:
        return {'total_orders': 0, 'total_commission': 0.0, 'currency': 'EUR'}

    product_ids = set()
    for order in orders:
        for item in order['items']:
            product_ids.add(item['product_id'])

    dropship_products = await db.dropshipping_products.find(
        {'id': {'$in': list(product_ids)}}, {'_id': 0}
    ).to_list(None)
    products_map = {prod['id']: prod for prod in dropship_products}

    total_commission = 0
    orders_count = 0
    for order in orders:
        for item in order['items']:
            dropship_prod = products_map.get(item['product_id'])
            if dropship_prod:
                commission = (dropship_prod['selling_price'] - dropship_prod['original_price']) * item['quantity']
                total_commission += commission
                orders_count += 1

    return {'total_orders': orders_count, 'total_commission': round(total_commission, 2), 'currency': 'EUR'}
