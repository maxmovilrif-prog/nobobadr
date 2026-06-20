from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

# db.py y auth.py no dependen de server.py (ni de ningún otro router), así
# que esto se puede importar en cualquier orden sin riesgo de import
# circular, sea cual sea el comando usado para arrancar la app
# (uvicorn server:app, python server.py, tests, etc.).
from db import db
from auth import get_current_user

from models_dropshipping import DropshippingProduct, DropshippingOrder

router = APIRouter(prefix="/dropshipping", tags=["dropshipping"])

ALLOWED_ORDER_STATUSES = {"pending_purchase", "purchased", "shipped", "delivered"}


class ProductCreate(BaseModel):
    name: str
    description: str
    original_price: float
    commission_percentage: float
    platform: str
    product_url: str
    image_url: str
    category: str
    shipping_time: str = "15-30 días"


class OrderStatusUpdate(BaseModel):
    status: str
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


# =========================
# PRODUCTS
# =========================

@router.post("/products", response_model=DropshippingProduct)
async def create_dropshipping_product(product_data: ProductCreate, current_user: dict = Depends(get_current_user)):
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


@router.get("/products", response_model=List[DropshippingProduct])
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


@router.get("/products/{product_id}", response_model=DropshippingProduct)
async def get_dropshipping_product(product_id: str):
    product = await db.dropshipping_products.find_one({'id': product_id}, {'_id': 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if isinstance(product.get('created_at'), str):
        product['created_at'] = datetime.fromisoformat(product['created_at'])

    return product


# =========================
# ORDERS (lógica interna reutilizable)
# =========================

async def create_dropship_orders_for_order(order_id: str) -> int:
    """Crea los DropshippingOrder correspondientes a un pedido ya pagado.
    Es idempotente: si ya existen registros para este order_id, no duplica nada.
    Pensada para ser llamada internamente (al confirmarse el pago) o desde el
    endpoint manual de abajo."""

    # Idempotencia: evita duplicar comisiones si el pago se confirma más de una vez
    # (reintentos de webhook, polling de estado, marcado manual de admin, etc.)
    already_exists = await db.dropshipping_orders.find_one({'order_id': order_id}, {'_id': 0, 'id': 1})
    if already_exists:
        return 0

    main_order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not main_order:
        return 0

    customer = await db.users.find_one({'id': main_order.get('customer_id')}, {'_id': 0})

    created = 0
    for item in main_order.get('items', []):
        dropship_product = await db.dropshipping_products.find_one({'id': item['product_id']}, {'_id': 0})
        if not dropship_product:
            continue

        commission = dropship_product['selling_price'] - dropship_product['original_price']

        dropship_order = DropshippingOrder(
            order_id=order_id,
            product_id=item['product_id'],
            product_name=item['product_name'],
            product_url=dropship_product['product_url'],
            platform=dropship_product['platform'],
            original_price=dropship_product['original_price'],
            selling_price=dropship_product['selling_price'],
            commission_earned=commission * item['quantity'],
            quantity=item['quantity'],
            customer_info={
                'name': customer.get('name', 'Desconocido') if customer else 'Desconocido',
                'email': customer.get('email', '') if customer else '',
                'phone': customer.get('phone', '') if customer else '',
                'address': main_order.get('delivery_address', ''),
            },
        )

        doc = dropship_order.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()

        await db.dropshipping_orders.insert_one(doc)
        created += 1

    return created


@router.post("/orders/{order_id}")
async def create_dropshipping_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """Disparo manual (negocio/admin) para generar los pedidos de dropshipping
    de un pedido ya pagado. En condiciones normales esto ya ocurre solo en
    cuanto el pago se confirma (ver server.py), así que este endpoint sirve
    sobre todo como herramienta de respaldo/reintento."""
    if current_user['role'] not in ('business', 'admin'):
        raise HTTPException(status_code=403, detail="Only business or admin users can do this")

    main_order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not main_order:
        raise HTTPException(status_code=404, detail="Order not found")

    created = await create_dropship_orders_for_order(order_id)
    return {'message': 'Dropshipping orders created', 'orders': created}


@router.get("/orders", response_model=List[DropshippingOrder])
async def get_dropshipping_orders(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = None
):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can view dropshipping orders")

    query = {}
    if status:
        query['status'] = status

    orders = await db.dropshipping_orders.find(query, {'_id': 0}).to_list(1000)

    for order in orders:
        if isinstance(order.get('created_at'), str):
            order['created_at'] = datetime.fromisoformat(order['created_at'])
        if isinstance(order.get('updated_at'), str):
            order['updated_at'] = datetime.fromisoformat(order['updated_at'])
        if order.get('purchased_at') and isinstance(order['purchased_at'], str):
            order['purchased_at'] = datetime.fromisoformat(order['purchased_at'])

    return orders


@router.patch("/orders/{order_id}/status")
async def update_dropshipping_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can update orders")

    if status_update.status not in ALLOWED_ORDER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(ALLOWED_ORDER_STATUSES))}"
        )

    existing = await db.dropshipping_orders.find_one({'id': order_id}, {'_id': 0, 'id': 1})
    if not existing:
        raise HTTPException(status_code=404, detail="Dropshipping order not found")

    update_data = {
        'status': status_update.status,
        'updated_at': datetime.now(timezone.utc).isoformat()
    }

    if status_update.tracking_number:
        update_data['tracking_number'] = status_update.tracking_number

    if status_update.notes:
        update_data['notes'] = status_update.notes

    if status_update.status == 'purchased':
        update_data['purchased_at'] = datetime.now(timezone.utc).isoformat()

    await db.dropshipping_orders.update_one(
        {'id': order_id},
        {'$set': update_data}
    )

    return {'message': 'Order updated successfully'}


# =========================
# STATS
# =========================

@router.get("/stats/commissions")
async def get_commission_stats(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can view stats")

    orders = await db.dropshipping_orders.find({}, {'_id': 0}).to_list(10000)

    total_commission = sum(order['commission_earned'] for order in orders)
    pending_commission = sum(
        order['commission_earned']
        for order in orders
        if order['status'] in ('pending_purchase', 'purchased')
    )
    earned_commission = sum(
        order['commission_earned']
        for order in orders
        if order['status'] == 'delivered'
    )

    by_platform = {}
    for platform in ('alibaba', 'temu', 'aliexpress'):
        by_platform[platform] = round(
            sum(o['commission_earned'] for o in orders if o['platform'] == platform), 2
        )

    return {
        'total_orders': len(orders),
        'total_commission': round(total_commission, 2),
        'pending_commission': round(pending_commission, 2),
        'earned_commission': round(earned_commission, 2),
        'by_platform': by_platform
    }
