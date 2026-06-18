"""Rutas de la App de Conductores (Riders): alta desde admin, QR/código y activación por dispositivo."""
import random
import string
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from core import (
    db, get_current_admin, get_current_rider,
    create_rider_token, generate_qr_data_url,
)
from models import RiderCreate, RiderUpdate, RiderActivate, RiderLocation

router = APIRouter()

VALID_VEHICLES = {"bicycle", "motorcycle", "car", "truck"}


def _public_rider(u: dict) -> dict:
    """Devuelve un rider sin campos sensibles."""
    return {
        "id": u.get("id"),
        "name": u.get("name"),
        "phone": u.get("phone"),
        "vehicle_type": u.get("vehicle_type"),
        "dni": u.get("dni"),
        "license_plate": u.get("license_plate"),
        "city_id": u.get("city_id"),
        "activation_code": u.get("activation_code"),
        "activated": u.get("activated", False),
        "activated_at": u.get("activated_at"),
        "contract_status": u.get("contract_status", "active"),
        "is_available": u.get("is_available", False),
        "current_location": u.get("current_location"),
        "created_at": u.get("created_at"),
    }


async def _generate_unique_code() -> str:
    """Genera un código corto único tipo NUBO-7F3K."""
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = "NUBO-" + "".join(random.choices(alphabet, k=4))
        if not await db.users.find_one({"activation_code": code}):
            return code
    # fallback improbable
    return "NUBO-" + uuid.uuid4().hex[:6].upper()


# =========================
# ADMIN — gestión de riders
# =========================

@router.post("/admin/riders")
async def admin_create_rider(data: RiderCreate, current_user: dict = Depends(get_current_admin)):
    if data.vehicle_type not in VALID_VEHICLES:
        raise HTTPException(status_code=400, detail="Tipo de vehículo no válido")
    code = await _generate_unique_code()
    rider = {
        "id": str(uuid.uuid4()),
        "email": f"rider_{uuid.uuid4().hex[:10]}@rider.nubo",  # placeholder interno (no usado para login)
        "name": data.name.strip(),
        "phone": data.phone.strip(),
        "role": "driver",
        "password_hash": "",  # los riders NO usan contraseña: entran por código/QR
        "vehicle_type": data.vehicle_type,
        "dni": data.dni,
        "license_plate": data.license_plate,
        "city_id": data.city_id,
        "activation_code": code,
        "activated": False,
        "activated_at": None,
        "contract_status": "active",
        "is_available": False,
        "current_location": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(rider)
    result = _public_rider(rider)
    result["qr_data_url"] = generate_qr_data_url(code)
    return result


@router.get("/admin/riders")
async def admin_list_riders(current_user: dict = Depends(get_current_admin)):
    riders = await db.users.find({"role": "driver"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return {"riders": [_public_rider(r) for r in riders], "count": len(riders)}


@router.get("/admin/riders/{rider_id}/qr")
async def admin_rider_qr(rider_id: str, current_user: dict = Depends(get_current_admin)):
    rider = await db.users.find_one({"id": rider_id, "role": "driver"}, {"_id": 0})
    if not rider:
        raise HTTPException(status_code=404, detail="Rider no encontrado")
    return {
        "activation_code": rider.get("activation_code"),
        "qr_data_url": generate_qr_data_url(rider.get("activation_code", "")),
    }


@router.patch("/admin/riders/{rider_id}")
async def admin_update_rider(rider_id: str, data: RiderUpdate, current_user: dict = Depends(get_current_admin)):
    rider = await db.users.find_one({"id": rider_id, "role": "driver"}, {"_id": 0})
    if not rider:
        raise HTTPException(status_code=404, detail="Rider no encontrado")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if "vehicle_type" in updates and updates["vehicle_type"] not in VALID_VEHICLES:
        raise HTTPException(status_code=400, detail="Tipo de vehículo no válido")
    if "contract_status" in updates and updates["contract_status"] not in ("active", "suspended"):
        raise HTTPException(status_code=400, detail="Estado de contrato no válido")
    if updates:
        await db.users.update_one({"id": rider_id}, {"$set": updates})
    rider.update(updates)
    return _public_rider(rider)


@router.post("/admin/riders/{rider_id}/regenerate-code")
async def admin_regenerate_code(rider_id: str, current_user: dict = Depends(get_current_admin)):
    rider = await db.users.find_one({"id": rider_id, "role": "driver"}, {"_id": 0})
    if not rider:
        raise HTTPException(status_code=404, detail="Rider no encontrado")
    code = await _generate_unique_code()
    await db.users.update_one({"id": rider_id}, {"$set": {"activation_code": code, "activated": False, "activated_at": None}})
    return {"activation_code": code, "qr_data_url": generate_qr_data_url(code)}


# =========================
# RIDER — activación y app
# =========================

@router.post("/rider/activate")
async def rider_activate(data: RiderActivate):
    """El conductor escanea/introduce su código y su dispositivo queda vinculado (emite token)."""
    code = (data.code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Código requerido")
    rider = await db.users.find_one({"activation_code": code, "role": "driver"}, {"_id": 0})
    if not rider:
        raise HTTPException(status_code=404, detail="Código no válido")
    if rider.get("contract_status") == "suspended":
        raise HTTPException(status_code=403, detail="Tu cuenta está suspendida. Contacta con administración.")
    if not rider.get("activated"):
        await db.users.update_one(
            {"id": rider["id"]},
            {"$set": {"activated": True, "activated_at": datetime.now(timezone.utc).isoformat()}},
        )
        rider["activated"] = True
    token = create_rider_token(rider["id"])
    return {"token": token, "rider": _public_rider(rider)}


@router.get("/rider/me")
async def rider_me(current_user: dict = Depends(get_current_rider)):
    if current_user.get("contract_status") == "suspended":
        raise HTTPException(status_code=403, detail="Cuenta suspendida")
    return _public_rider(current_user)


@router.patch("/rider/availability")
async def rider_availability(is_available: bool, current_user: dict = Depends(get_current_rider)):
    await db.users.update_one({"id": current_user["id"]}, {"$set": {"is_available": is_available}})
    return {"is_available": is_available}


@router.post("/rider/location")
async def rider_location(loc: RiderLocation, current_user: dict = Depends(get_current_rider)):
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "current_location": {"lat": loc.lat, "lng": loc.lng,
                                 "updated_at": datetime.now(timezone.utc).isoformat()},
            # GeoJSON para consultas de proximidad ($geoNear sobre índice 2dsphere)
            "geo_location": {"type": "Point", "coordinates": [loc.lng, loc.lat]},
        }},
    )
    return {"ok": True}
