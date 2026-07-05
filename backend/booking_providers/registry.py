"""Registro de proveedores de reservas. Selección por env (def: direct_ferries / booking_com)."""
import os

from .base import FerryProviderAdapter
from .direct_ferries import DirectFerriesAdapter
from .hotels import HotelProviderAdapter, BookingComAdapter

_FERRY_PROVIDERS = {
    "direct_ferries": DirectFerriesAdapter,
}

_HOTEL_PROVIDERS = {
    "booking_com": BookingComAdapter,
}


def get_ferry_adapter() -> FerryProviderAdapter:
    key = os.environ.get("BOOKINGS_FERRY_PROVIDER", "direct_ferries")
    cls = _FERRY_PROVIDERS.get(key, DirectFerriesAdapter)
    return cls()


def get_hotel_adapter() -> HotelProviderAdapter:
    key = os.environ.get("BOOKINGS_HOTEL_PROVIDER", "booking_com")
    cls = _HOTEL_PROVIDERS.get(key, BookingComAdapter)
    return cls()
