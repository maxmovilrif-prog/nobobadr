"""Administraciones regionales (multi-tenant): agrupan ciudades y aíslan datos.

- El Fundador crea/edita/borra regiones y asigna ciudades.
- Cada Gestor pertenece a UNA región; solo ve datos de las ciudades de su región.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_admin, get_current_manager_or_admin
from models import Region, RegionCreate, RegionUpdate

router = APIRouter()


def _public_region(r: dict) -> dict:
    return {
        'id': r.get('id'),
        'name': r.get('name'),
        'city_ids': r.get('city_ids', []),
        'created_at': r.get('created_at'),
    }


async def _with_cities(r: dict) -> dict:
    """Adjunta los nombres de las ciudades de la región."""
    out = _public_region(r)
    ids = out['city_ids']
    if ids:
        cities = await db.cities.find({'id': {'$in': ids}}, {'_id': 0, 'id': 1, 'name': 1, 'country': 1}).to_list(500)
        out['cities'] = cities
    else:
        out['cities'] = []
    out['managers_count'] = await db.users.count_documents({'role': 'manager', 'region_id': out['id']})
    out['riders_count'] = await db.users.count_documents({'role': 'driver', 'region_id': out['id']})
    return out


@router.post("/admin/regions")
async def create_region(payload: RegionCreate, current_user: dict = Depends(get_current_admin)):
    if await db.regions.find_one({'name': payload.name.strip()}):
        raise HTTPException(status_code=400, detail="Ya existe una región con ese nombre")
    region = Region(name=payload.name.strip(), city_ids=payload.city_ids or [])
    doc = region.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.regions.insert_one(doc)
    return await _with_cities(doc)


@router.get("/admin/regions")
async def list_regions(current_user: dict = Depends(get_current_admin)):
    rows = await db.regions.find({}, {'_id': 0}).sort('name', 1).to_list(500)
    return {'count': len(rows), 'regions': [await _with_cities(r) for r in rows]}


@router.put("/admin/regions/{region_id}")
async def update_region(region_id: str, payload: RegionUpdate, current_user: dict = Depends(get_current_admin)):
    region = await db.regions.find_one({'id': region_id}, {'_id': 0})
    if not region:
        raise HTTPException(status_code=404, detail="Región no encontrada")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if 'name' in updates:
        updates['name'] = updates['name'].strip()
        clash = await db.regions.find_one({'name': updates['name'], 'id': {'$ne': region_id}})
        if clash:
            raise HTTPException(status_code=400, detail="Ya existe una región con ese nombre")
    if updates:
        await db.regions.update_one({'id': region_id}, {'$set': updates})
    fresh = await db.regions.find_one({'id': region_id}, {'_id': 0})
    return await _with_cities(fresh)


@router.delete("/admin/regions/{region_id}")
async def delete_region(region_id: str, current_user: dict = Depends(get_current_admin)):
    in_use = await db.users.count_documents({'role': 'manager', 'region_id': region_id})
    if in_use:
        raise HTTPException(status_code=400, detail=f"No se puede borrar: {in_use} gestor(es) asignados a esta región")
    res = await db.regions.delete_one({'id': region_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Región no encontrada")
    return {'message': 'Región eliminada', 'id': region_id}


@router.get("/regions/mine")
async def my_region(current_user: dict = Depends(get_current_manager_or_admin)):
    """La región del Gestor actual (o None si es Fundador → acceso global)."""
    if current_user.get('role') == 'admin':
        return {'is_founder': True, 'region': None}
    region_id = current_user.get('region_id')
    if not region_id:
        return {'is_founder': False, 'region': None}
    region = await db.regions.find_one({'id': region_id}, {'_id': 0})
    return {'is_founder': False, 'region': await _with_cities(region) if region else None}
