"""Endpoint REST para obtener la última ubicación conocida del conductor."""
from fastapi import APIRouter, HTTPException

from core import manager

router = APIRouter()


@router.get("/tracking/location/{order_id}")
async def get_driver_location(order_id: str):
    """REST endpoint alternativo para obtener última ubicación conocida"""
    location = manager.get_driver_location(order_id)
    if location:
        return location
    raise HTTPException(status_code=404, detail="No location data available")
