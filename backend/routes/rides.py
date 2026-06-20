"""Nubo Ride — transporte de pasajeros (tipo Uber/Cabify). Respeta el aislamiento regional."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user, get_scope_city_ids
from models import Ride, RideRequest, RideEstimateRequest, RideAccept, RideCancel, GeoPoint
from geo import calculate_ride_quote, currency_for_location, RIDE_VEHICLE_TYPES, RIDE_PRICING
import telegram_alerts

router = APIRouter()

ACTIVE_STATES = ("buscando", "aceptado", "en_curso")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deserialize(ride: dict) -> dict:
    """Convierte fechas ISO a datetime para el response_model Ride."""
    for k in ("created_at", "updated_at"):
        if isinstance(ride.get(k), str):
            ride[k] = datetime.fromisoformat(ride[k])
    return ride


async def _region_for_city(city_id):
    if not city_id:
        return None
    region = await db.regions.find_one({"city_ids": city_id}, {"_id": 0, "id": 1})
    return region["id"] if region else None


@router.post("/rides/estimate")
async def estimate_ride(data: RideEstimateRequest, current_user: dict = Depends(get_current_user)):
    """Devuelve el precio estimado para cada tipo de vehículo de pasajeros."""
    options = []
    for vt in RIDE_PRICING:
        q = calculate_ride_quote(
            data.origin_lat, data.origin_lng,
            data.destination_lat, data.destination_lng,
            vehicle_type=vt, currency=data.currency,
        )
        options.append(q)
    return {"currency": data.currency if data.currency in ("EUR", "MAD") else "EUR", "options": options}


@router.post("/rides/request", response_model=Ride)
async def request_ride(data: RideRequest, current_user: dict = Depends(get_current_user)):
    """El cliente solicita un viaje. Crea el Ride en estado 'buscando'."""
    if current_user.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Solo los clientes pueden solicitar viajes")
    if data.vehicle_type not in RIDE_VEHICLE_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de vehículo no válido")

    # Evita viajes activos duplicados del mismo cliente
    existing = await db.rides.find_one(
        {"client_id": current_user["id"], "estado": {"$in": list(ACTIVE_STATES)}}, {"_id": 0, "id": 1}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Ya tienes un viaje en curso")

    currency = data.currency if data.currency in ("EUR", "MAD") else "EUR"
    quote = calculate_ride_quote(
        data.origin_lat, data.origin_lng,
        data.destination_lat, data.destination_lng,
        vehicle_type=data.vehicle_type, currency=currency,
    )
    region_id = await _region_for_city(data.city_id)

    ride = Ride(
        client_id=current_user["id"],
        origin=GeoPoint(lat=data.origin_lat, lng=data.origin_lng, label=data.origin_label),
        destination=GeoPoint(lat=data.destination_lat, lng=data.destination_lng, label=data.destination_label),
        vehicle_type=data.vehicle_type,
        distance_km=quote["distance_km"],
        eta_mins=quote["eta_mins"],
        precio_estimado=quote["estimated_price"],
        currency=currency,
        estado="buscando",
        region_id=region_id,
        city_id=data.city_id,
    )
    doc = ride.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await db.rides.insert_one(doc)

    # Alerta al despacho por Telegram (no bloquea la respuesta): botón para asignar conductor
    await telegram_alerts.notify_new_ride(doc)

    return ride


@router.post("/rides/accept", response_model=Ride)
async def accept_ride(data: RideAccept, current_user: dict = Depends(get_current_user)):
    """Un conductor (rider) acepta un viaje en estado 'buscando' (reclamo atómico)."""
    if current_user.get("role") != "driver":
        raise HTTPException(status_code=403, detail="Solo los conductores pueden aceptar viajes")

    ride = await db.rides.find_one({"id": data.ride_id}, {"_id": 0})
    if not ride:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    # Aislamiento regional: el conductor solo acepta viajes de su delegación
    driver_region = current_user.get("region_id")
    if ride.get("region_id") and driver_region and ride["region_id"] != driver_region:
        raise HTTPException(status_code=403, detail="Este viaje no pertenece a tu delegación")

    # El conductor no puede tener otro viaje activo
    busy = await db.rides.find_one(
        {"conductor_id": current_user["id"], "estado": {"$in": ["aceptado", "en_curso"]}}, {"_id": 0, "id": 1}
    )
    if busy:
        raise HTTPException(status_code=400, detail="Ya tienes un viaje activo")

    now = _now()
    result = await db.rides.update_one(
        {"id": data.ride_id, "estado": "buscando", "conductor_id": None},
        {"$set": {"conductor_id": current_user["id"], "estado": "aceptado",
                  "accepted_at": now, "updated_at": now}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=409, detail="El viaje ya fue aceptado o cancelado")

    updated = await db.rides.find_one({"id": data.ride_id}, {"_id": 0})
    return _deserialize(updated)


@router.get("/rides/active")
async def get_active_rides(current_user: dict = Depends(get_current_user)):
    """Devuelve el/los viaje(s) activo(s) según el rol del usuario."""
    role = current_user.get("role")

    if role == "customer":
        ride = await db.rides.find_one(
            {"client_id": current_user["id"], "estado": {"$in": list(ACTIVE_STATES)}}, {"_id": 0}
        )
        return {"ride": ride}

    if role == "driver":
        ride = await db.rides.find_one(
            {"conductor_id": current_user["id"], "estado": {"$in": ["aceptado", "en_curso"]}}, {"_id": 0}
        )
        # Viajes disponibles en su región para aceptar
        avail_query = {"estado": "buscando", "conductor_id": None}
        if current_user.get("region_id"):
            avail_query["$or"] = [{"region_id": current_user["region_id"]}, {"region_id": None}]
        available = await db.rides.find(avail_query, {"_id": 0}).sort("created_at", -1).to_list(50)
        return {"ride": ride, "available": available}

    if role in ("admin", "manager"):
        query = {"estado": {"$in": list(ACTIVE_STATES)}}
        scope = await get_scope_city_ids(current_user)
        if scope is not None:  # gestor regional
            query["city_id"] = {"$in": scope}
        rides = await db.rides.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
        return {"rides": rides, "count": len(rides)}

    raise HTTPException(status_code=403, detail="Rol no autorizado")


async def _get_ride_for_driver(ride_id: str, current_user: dict) -> dict:
    if current_user.get("role") != "driver":
        raise HTTPException(status_code=403, detail="Solo los conductores pueden hacer esto")
    ride = await db.rides.find_one({"id": ride_id}, {"_id": 0})
    if not ride:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    if ride.get("conductor_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Este viaje no es tuyo")
    return ride


@router.post("/rides/{ride_id}/start", response_model=Ride)
async def start_ride(ride_id: str, current_user: dict = Depends(get_current_user)):
    """El conductor inicia el viaje (aceptado → en_curso)."""
    ride = await _get_ride_for_driver(ride_id, current_user)
    if ride["estado"] != "aceptado":
        raise HTTPException(status_code=400, detail="El viaje no está en estado 'aceptado'")
    now = _now()
    await db.rides.update_one({"id": ride_id}, {"$set": {"estado": "en_curso", "started_at": now, "updated_at": now}})
    updated = await db.rides.find_one({"id": ride_id}, {"_id": 0})
    return _deserialize(updated)


@router.post("/rides/{ride_id}/complete", response_model=Ride)
async def complete_ride(ride_id: str, current_user: dict = Depends(get_current_user)):
    """El conductor completa el viaje (en_curso → completado)."""
    ride = await _get_ride_for_driver(ride_id, current_user)
    if ride["estado"] != "en_curso":
        raise HTTPException(status_code=400, detail="El viaje no está en curso")
    now = _now()
    await db.rides.update_one({"id": ride_id}, {"$set": {"estado": "completado", "completed_at": now, "updated_at": now}})
    updated = await db.rides.find_one({"id": ride_id}, {"_id": 0})
    return _deserialize(updated)


@router.post("/rides/{ride_id}/cancel", response_model=Ride)
async def cancel_ride(ride_id: str, data: RideCancel, current_user: dict = Depends(get_current_user)):
    """Cancela un viaje. Permitido al cliente dueño, al conductor asignado o al Fundador/Gestor."""
    ride = await db.rides.find_one({"id": ride_id}, {"_id": 0})
    if not ride:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    role = current_user.get("role")
    allowed = (
        (role == "customer" and ride.get("client_id") == current_user["id"]) or
        (role == "driver" and ride.get("conductor_id") == current_user["id"]) or
        role == "admin" or role == "manager"
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="No puedes cancelar este viaje")
    if ride["estado"] in ("completado", "cancelado"):
        raise HTTPException(status_code=400, detail="El viaje ya está finalizado")

    now = _now()
    await db.rides.update_one(
        {"id": ride_id},
        {"$set": {"estado": "cancelado", "cancel_reason": data.reason, "cancelled_at": now, "updated_at": now}},
    )
    updated = await db.rides.find_one({"id": ride_id}, {"_id": 0})
    return _deserialize(updated)
