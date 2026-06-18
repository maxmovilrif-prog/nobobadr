"""Rutas de negocios y productos."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user, get_current_business
from models import Business, BusinessCreate, Product, ProductCreate

router = APIRouter()


# ===== Businesses =====
@router.post("/businesses", response_model=Business)
async def create_business(business_data: BusinessCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'business':
        raise HTTPException(status_code=403, detail="Only business users can create businesses")

    business_dict = business_data.model_dump()
    business_dict['owner_id'] = current_user['id']

    business = Business(**business_dict)
    doc = business.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.businesses.insert_one(doc)
    return business


@router.get("/businesses", response_model=List[Business])
async def get_businesses(category: Optional[str] = None):
    query = {} if not category else {'category': category}
    businesses = await db.businesses.find(query, {'_id': 0}).to_list(1000)
    for business in businesses:
        if isinstance(business.get('created_at'), str):
            business['created_at'] = datetime.fromisoformat(business['created_at'])
    return businesses


@router.get("/businesses/{business_id}", response_model=Business)
async def get_business(business_id: str):
    business = await db.businesses.find_one({'id': business_id}, {'_id': 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    if isinstance(business.get('created_at'), str):
        business['created_at'] = datetime.fromisoformat(business['created_at'])
    return business


# ===== Products =====
@router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: dict = Depends(get_current_business)):
    # Role is enforced by get_current_business (returns 403 before body validation)
    business = await db.businesses.find_one({'id': product_data.business_id, 'owner_id': current_user['id']}, {'_id': 0})
    if not business:
        raise HTTPException(status_code=403, detail="Not authorized for this business")

    product = Product(**product_data.model_dump())
    doc = product.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.products.insert_one(doc)
    return product


@router.get("/products/{business_id}", response_model=List[Product])
async def get_products(business_id: str):
    products = await db.products.find({'business_id': business_id}, {'_id': 0}).to_list(1000)
    for product in products:
        if isinstance(product.get('created_at'), str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    return products
