"""Registro de proveedores de ferries. Selección por env BOOKINGS_FERRY_PROVIDER (def: direct_ferries)."""
import os

from .base import FerryProviderAdapter
from .direct_ferries import DirectFerriesAdapter

_PROVIDERS = {
    "direct_ferries": DirectFerriesAdapter,
}


def get_ferry_adapter() -> FerryProviderAdapter:
    key = os.environ.get("BOOKINGS_FERRY_PROVIDER", "direct_ferries")
    cls = _PROVIDERS.get(key, DirectFerriesAdapter)
    return cls()
