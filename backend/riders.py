"""Riders router: list couriers and update/query live GPS location."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from database import db
from auth import get_current_user, require_roles
from realtime import manager

router = APIRouter(prefix="/api/riders")


class LocationInput(BaseModel):
    lat: float
    lng: float


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_riders(user: dict = Depends(get_current_user)):
    riders = await db.users.find(
        {"role": "rider"},
        {"_id": 0, "password_hash": 0},
    ).to_list(500)
    # Attach last known location
    for r in riders:
        loc = await db.rider_locations.find_one({"rider_id": r["id"]}, {"_id": 0})
        r["location"] = loc
    return {"riders": riders}


@router.post("/location")
async def update_location(
    payload: LocationInput,
    user: dict = Depends(require_roles("rider", "admin", "dispatcher")),
):
    doc = {
        "rider_id": user["id"],
        "name": user.get("name"),
        "lat": payload.lat,
        "lng": payload.lng,
        "updated_at": _now(),
    }
    await db.rider_locations.update_one(
        {"rider_id": user["id"]}, {"$set": doc}, upsert=True
    )
    await manager.broadcast({"type": "rider_location", **doc})
    return doc


@router.get("/{rider_id}/location")
async def get_location(rider_id: str, user: dict = Depends(get_current_user)):
    loc = await db.rider_locations.find_one({"rider_id": rider_id}, {"_id": 0})
    return loc or {}
