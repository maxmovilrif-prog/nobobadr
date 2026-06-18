"""Rutas de ciudades/zonas operativas y cálculo de tarifa de envío."""
from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user, get_current_admin
from models import City, CityCreate, CityUpdate, DeliveryQuoteRequest
import geo

router = APIRouter()


# ===== Lectura =====
@router.get("/public/cities")
async def public_list_cities():
    """Lista pública de ciudades/zonas (sin login) para la calculadora de envíos."""
    cities = await db.cities.find({}, {'_id': 0}).sort('name', 1).to_list(1000)
    return {'cities': cities}


@router.get("/cities")
async def list_cities(current_user: dict = Depends(get_current_user)):
    """Lista de ciudades/zonas disponibles (autenticado)."""
    cities = await db.cities.find({}, {'_id': 0}).sort('name', 1).to_list(1000)
    return {'cities': cities}


# ===== Cálculo de tarifa =====
@router.post("/v1/calculate-delivery")
async def calculate_delivery(req: DeliveryQuoteRequest):
    """Calcula la tarifa, distancia y ETA de un envío punto a punto (público)."""
    return geo.calculate_delivery_quote(
        req.origin_lat, req.origin_lng,
        req.destination_lat, req.destination_lng,
        req.vehicle_type, req.currency,
    )


# ===== Administración (CRUD) =====
@router.post("/admin/cities", response_model=City)
async def admin_create_city(data: CityCreate, current_user: dict = Depends(get_current_admin)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    if await db.cities.find_one({'name': name}):
        raise HTTPException(status_code=400, detail="Ya existe una ciudad con ese nombre")
    city = City(name=name, lat=data.lat, lng=data.lng, country=data.country)
    await db.cities.insert_one(city.model_dump())
    return city


@router.patch("/admin/cities/{city_id}", response_model=City)
async def admin_update_city(city_id: str, data: CityUpdate, current_user: dict = Depends(get_current_admin)):
    city = await db.cities.find_one({'id': city_id}, {'_id': 0})
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if 'name' in updates:
        updates['name'] = updates['name'].strip()
        if updates['name'] != city.get('name') and await db.cities.find_one({'name': updates['name']}):
            raise HTTPException(status_code=400, detail="Ya existe una ciudad con ese nombre")
    if updates:
        await db.cities.update_one({'id': city_id}, {'$set': updates})
    return City(**{**city, **updates})


@router.delete("/admin/cities/{city_id}")
async def admin_delete_city(city_id: str, current_user: dict = Depends(get_current_admin)):
    city = await db.cities.find_one({'id': city_id}, {'_id': 0})
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    active = await db.orders.count_documents(
        {'city_id': city_id, 'status': {'$nin': ['delivered', 'cancelled']}}
    )
    if active > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar: hay {active} pedido(s) activo(s) en esta ciudad")
    await db.cities.delete_one({'id': city_id})
    return {'message': 'City deleted', 'id': city_id}
