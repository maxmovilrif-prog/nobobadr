"""Contratos base del módulo de reservas (Fase 1: ferries por afiliación).

Patrón provider-adapter: cada proveedor (Direct Ferries, Ferryhopper, ...) implementa
`FerryProviderAdapter`. El módulo `/api/bookings` solo conoce esta interfaz, nunca el
proveedor concreto → cambiar/añadir proveedores sin tocar la lógica de negocio.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field


class FerryPort(BaseModel):
    code: str
    name: str
    country: str  # ISO-2: ES, MA, IT, ...


class FerryPassengers(BaseModel):
    adults: int = 1
    children: int = 0
    # Vehículo que viaja con el pasajero (afecta tarifa). none | car | motorcycle | van | camper
    vehicle: Optional[str] = None


class FerrySearchQuery(BaseModel):
    origin_code: str
    destination_code: str
    depart_date: str  # ISO date 'YYYY-MM-DD'
    return_date: Optional[str] = None
    passengers: FerryPassengers = Field(default_factory=FerryPassengers)


class FerryOffer(BaseModel):
    provider: str
    operator: str
    origin_code: str
    destination_code: str
    depart_at: str
    arrive_at: Optional[str] = None
    duration_mins: Optional[int] = None
    price_from: Optional[float] = None
    currency: str = "EUR"
    deeplink: Optional[str] = None  # enlace de afiliado para completar la reserva
    is_mock: bool = False  # True cuando el proveedor no está configurado (datos de ejemplo)


class FerryProviderAdapter(ABC):
    """Interfaz que todo proveedor de ferries debe implementar."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """¿Hay credenciales/afiliado configurados para envíos reales?"""

    @abstractmethod
    async def list_ports(self) -> List[FerryPort]:
        """Puertos soportados (para los selectores de origen/destino)."""

    @abstractmethod
    async def search(self, query: FerrySearchQuery) -> List[FerryOffer]:
        """Busca travesías. Si el proveedor no está configurado devuelve datos de ejemplo (is_mock)."""

    @abstractmethod
    def build_affiliate_link(self, query: FerrySearchQuery, offer: Optional[FerryOffer] = None) -> str:
        """Construye el enlace de afiliado (con tracking) para redirigir al cliente."""
