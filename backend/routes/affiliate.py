"""Rutas de enlaces de afiliados (viajes)."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user
from models import AffiliateLinks, AffiliateLinksUpdate

router = APIRouter()


@router.get("/affiliate-links", response_model=AffiliateLinks)
async def get_affiliate_links():
    """Get current affiliate links configuration"""
    links = await db.affiliate_links.find_one({}, {'_id': 0})
    if not links:
        return AffiliateLinks()
    return AffiliateLinks(**links)


@router.put("/affiliate-links")
async def update_affiliate_links(links_data: AffiliateLinksUpdate, current_user: dict = Depends(get_current_user)):
    """Update affiliate links (admin/business only)"""
    if current_user['role'] not in ['business', 'admin']:
        raise HTTPException(status_code=403, detail="Only business/admin can update affiliate links")

    existing = await db.affiliate_links.find_one({})
    update_data = {k: v for k, v in links_data.dict().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()

    if existing:
        await db.affiliate_links.update_one({'id': existing['id']}, {'$set': update_data})
    else:
        new_links = AffiliateLinks(**update_data)
        await db.affiliate_links.insert_one(new_links.dict())

    return {"message": "Affiliate links updated successfully"}
