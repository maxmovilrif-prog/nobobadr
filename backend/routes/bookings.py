"""Rutas del módulo de Reservas (Fase 1: Ferries por afiliación).

Endpoints públicos de búsqueda/redirección + listado admin de clics (para medir comisiones).
La lógica concreta del proveedor vive en `booking_providers/` (patrón adapter).
"""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from core import db, get_current_admin
from booking_providers.base import FerrySearchQuery
from booking_providers.hotels import HotelSearchQuery
from booking_providers.registry import get_ferry_adapter, get_hotel_adapter

logger = logging.getLogger("nubo.bookings")
router = APIRouter()


@router.get("/bookings/ferries/provider-status")
async def ferry_provider_status():
    """¿El proveedor de ferries está configurado (credenciales/afiliado)?"""
    adapter = get_ferry_adapter()
    return {"provider": adapter.name, "configured": adapter.is_configured()}


@router.get("/bookings/ferries/ports")
async def ferry_ports():
    """Puertos soportados para los selectores de origen/destino."""
    adapter = get_ferry_adapter()
    ports = await adapter.list_ports()
    return {"ports": [p.model_dump() for p in ports]}


@router.post("/bookings/ferries/search")
async def ferry_search(query: FerrySearchQuery):
    """Busca travesías de ferry. Devuelve ofertas (is_mock=True si el proveedor no está configurado)."""
    adapter = get_ferry_adapter()
    offers = await adapter.search(query)
    return {
        "provider": adapter.name,
        "configured": adapter.is_configured(),
        "count": len(offers),
        "offers": [o.model_dump() for o in offers],
    }


@router.post("/bookings/ferries/redirect")
async def ferry_redirect(query: FerrySearchQuery):
    """Genera el enlace de afiliado y registra el clic (best-effort) para medir conversión/comisión."""
    adapter = get_ferry_adapter()
    deeplink = adapter.build_affiliate_link(query)
    click = {
        "id": str(uuid.uuid4()),
        "vertical": "ferry",
        "provider": adapter.name,
        "origin_code": query.origin_code,
        "destination_code": query.destination_code,
        "depart_date": query.depart_date,
        "return_date": query.return_date,
        "passengers": query.passengers.model_dump(),
        "deeplink": deeplink,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.booking_clicks.insert_one({**click})
    except Exception as e:  # noqa: BLE001 - no romper la redirección si falla el log
        logger.warning("No se pudo registrar el clic de ferry: %s", e)
    return {"deeplink": deeplink, "click_id": click["id"]}


@router.get("/admin/bookings/ferry-clicks")
async def admin_ferry_clicks(current_user: dict = Depends(get_current_admin)):
    """Listado de clics de afiliado de ferries (Fundador) para seguimiento de comisiones."""
    rows = await db.booking_clicks.find(
        {"vertical": "ferry"}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return {"count": len(rows), "clicks": rows}


# =========================
# HOTELES (Fase 2 · afiliación Booking.com)
# =========================

@router.get("/bookings/hotels/provider-status")
async def hotel_provider_status():
    adapter = get_hotel_adapter()
    return {"provider": adapter.name, "configured": adapter.is_configured()}


@router.get("/bookings/hotels/destinations")
async def hotel_destinations():
    adapter = get_hotel_adapter()
    dests = await adapter.list_destinations()
    return {"destinations": [d.model_dump() for d in dests]}


@router.post("/bookings/hotels/search")
async def hotel_search(query: HotelSearchQuery):
    adapter = get_hotel_adapter()
    offers = await adapter.search(query)
    return {
        "provider": adapter.name,
        "configured": adapter.is_configured(),
        "count": len(offers),
        "offers": [o.model_dump() for o in offers],
    }


@router.post("/bookings/hotels/redirect")
async def hotel_redirect(query: HotelSearchQuery):
    """Genera el enlace de afiliado de Booking.com y registra el clic (best-effort)."""
    adapter = get_hotel_adapter()
    deeplink = adapter.build_affiliate_link(query)
    click = {
        "id": str(uuid.uuid4()),
        "vertical": "hotel",
        "provider": adapter.name,
        "destination_code": query.destination_code,
        "checkin": query.checkin,
        "checkout": query.checkout,
        "guests": query.guests.model_dump(),
        "deeplink": deeplink,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.booking_clicks.insert_one({**click})
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo registrar el clic de hotel: %s", e)
    return {"deeplink": deeplink, "click_id": click["id"]}


@router.get("/admin/bookings/hotel-clicks")
async def admin_hotel_clicks(current_user: dict = Depends(get_current_admin)):
    rows = await db.booking_clicks.find(
        {"vertical": "hotel"}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return {"count": len(rows), "clicks": rows}
