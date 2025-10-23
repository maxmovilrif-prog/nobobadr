from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

# Import from main server for get_current_user
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

try:
    from models_dropshipping import DropshippingProduct, DropshippingOrder
except:
    # Define models inline if import fails
    from pydantic import Field, ConfigDict
    import uuid
    
    class DropshippingProduct(BaseModel):
        model_config = ConfigDict(extra="ignore")
        id: str = Field(default_factory=lambda: str(uuid.uuid4()))
        business_id: str
        name: str
        description: str
        original_price: float
        selling_price: float
        commission_percentage: float
        platform: str
        product_url: str
        image_url: str
        category: str
        stock_status: str = "available"
        shipping_time: str = "15-30 días"
        created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class DropshippingOrder(BaseModel):
        model_config = ConfigDict(extra="ignore")
        id: str = Field(default_factory=lambda: str(uuid.uuid4()))
        order_id: str
        product_id: str
        product_name: str
        product_url: str
        platform: str
        original_price: float
        selling_price: float
        commission_earned: float
        quantity: int
        customer_info: dict
        status: str = "pending_purchase"
        tracking_number: Optional[str] = None
        notes: Optional[str] = None
        purchased_at: Optional[datetime] = None
        created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
        updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter(prefix="/dropshipping", tags=["dropshipping"])

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

# CREATE DROPSHIPPING PRODUCT
@router.post("/products", response_model=DropshippingProduct)
async def create_dropshipping_product(product_data: ProductCreate, current_user: dict):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can create products")
    
    # Calculate selling price with commission
    selling_price = product_data.original_price * (1 + product_data.commission_percentage / 100)
    
    product_dict = product_data.model_dump()
    product_dict['business_id'] = current_user['id']
    product_dict['selling_price'] = round(selling_price, 2)
    
    product = DropshippingProduct(**product_dict)
    doc = product.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.dropshipping_products.insert_one(doc)
    return product

# GET ALL DROPSHIPPING PRODUCTS
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

# GET DROPSHIPPING PRODUCT BY ID
@router.get("/products/{product_id}", response_model=DropshippingProduct)
async def get_dropshipping_product(product_id: str):
    product = await db.dropshipping_products.find_one({'id': product_id}, {'_id': 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if isinstance(product.get('created_at'), str):
        product['created_at'] = datetime.fromisoformat(product['created_at'])
    
    return product

# CREATE DROPSHIPPING ORDER (when customer places order)
@router.post("/orders")
async def create_dropshipping_order(order_id: str, current_user: dict):
    # Get the main order
    main_order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not main_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get customer info
    customer = await db.users.find_one({'id': main_order['customer_id']}, {'_id': 0})
    
    dropship_orders = []
    
    # Create dropshipping order for each item
    for item in main_order['items']:
        # Check if it's a dropshipping product
        dropship_product = await db.dropshipping_products.find_one({'id': item['product_id']}, {'_id': 0})
        
        if dropship_product:
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
                    'name': customer['name'],
                    'email': customer['email'],
                    'phone': customer['phone'],
                    'address': main_order['delivery_address']
                }
            )
            
            doc = dropship_order.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            
            await db.dropshipping_orders.insert_one(doc)
            dropship_orders.append(dropship_order)
    
    return {'message': 'Dropshipping orders created', 'orders': len(dropship_orders)}

# GET DROPSHIPPING ORDERS (for business owner)
@router.get("/orders", response_model=List[DropshippingOrder])
async def get_dropshipping_orders(
    current_user: dict,
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

# UPDATE DROPSHIPPING ORDER STATUS
@router.patch("/orders/{order_id}/status")
async def update_dropshipping_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: dict
):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can update orders")
    
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

# GET COMMISSION STATISTICS
@router.get("/stats/commissions")
async def get_commission_stats(current_user: dict):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can view stats")
    
    # Get all dropshipping orders
    orders = await db.dropshipping_orders.find({}, {'_id': 0}).to_list(10000)
    
    total_commission = sum(order['commission_earned'] for order in orders)
    pending_commission = sum(
        order['commission_earned'] 
        for order in orders 
        if order['status'] in ['pending_purchase', 'purchased']
    )
    earned_commission = sum(
        order['commission_earned'] 
        for order in orders 
        if order['status'] == 'delivered'
    )
    
    return {
        'total_orders': len(orders),
        'total_commission': round(total_commission, 2),
        'pending_commission': round(pending_commission, 2),
        'earned_commission': round(earned_commission, 2),
        'by_platform': {
            'alibaba': sum(o['commission_earned'] for o in orders if o['platform'] == 'alibaba'),
            'temu': sum(o['commission_earned'] for o in orders if o['platform'] == 'temu'),
            'aliexpress': sum(o['commission_earned'] for o in orders if o['platform'] == 'aliexpress')
        }
    }
