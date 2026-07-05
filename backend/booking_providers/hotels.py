"""Adapter de Hoteles (Fase 2: afiliación · Booking.com).

Patrón provider-adapter, igual que ferries. Mientras no haya `BOOKING_AFFILIATE_ID`
configurado, `search()` devuelve hoteles de EJEMPLO (is_mock=True) y `build_affiliate_link()`
ya construye un enlace de búsqueda de Booking.com con el parámetro de afiliado.

Secrets (producción, NUNCA hardcodear):
  - BOOKING_AFFILIATE_ID   → ID de afiliado (aid) de Booking.com (Awin/CJ)
  - BOOKING_DEEPLINK_BASE  → base del deeplink (def: https://www.booking.com)
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from urllib.parse import urlencode

from pydantic import BaseModel, Field

logger = logging.getLogger("nubo.bookings.hotels")


class HotelDestination(BaseModel):
    code: str
    name: str
    country: str  # ISO-2


class HotelGuests(BaseModel):
    adults: int = 2
    children: int = 0
    rooms: int = 1


class HotelSearchQuery(BaseModel):
    destination_code: str
    checkin: str   # 'YYYY-MM-DD'
    checkout: str  # 'YYYY-MM-DD'
    guests: HotelGuests = Field(default_factory=HotelGuests)


class HotelOffer(BaseModel):
    provider: str
    name: str
    destination_code: str
    stars: Optional[int] = None
    review_score: Optional[float] = None
    price_per_night: Optional[float] = None
    currency: str = "EUR"
    deeplink: Optional[str] = None
    is_mock: bool = False


class HotelProviderAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    async def list_destinations(self) -> List[HotelDestination]: ...

    @abstractmethod
    async def search(self, query: HotelSearchQuery) -> List[HotelOffer]: ...

    @abstractmethod
    def build_affiliate_link(self, query: HotelSearchQuery, offer: Optional[HotelOffer] = None) -> str: ...


# Destinos clave del corredor España–Marruecos + principales, seed inicial.
_DESTINATIONS: List[HotelDestination] = [
    HotelDestination(code="TNG", name="Tánger", country="MA"),
    HotelDestination(code="CAS", name="Casablanca", country="MA"),
    HotelDestination(code="RAK", name="Marrakech", country="MA"),
    HotelDestination(code="RBA", name="Rabat", country="MA"),
    HotelDestination(code="AGA", name="Agadir", country="MA"),
    HotelDestination(code="ALG", name="Algeciras", country="ES"),
    HotelDestination(code="MAD", name="Madrid", country="ES"),
    HotelDestination(code="BCN", name="Barcelona", country="ES"),
    HotelDestination(code="MLG", name="Málaga", country="ES"),
]
_DEST_INDEX = {d.code: d for d in _DESTINATIONS}

_SAMPLE_HOTELS = [
    ("Hotel Kenzi Solazur", 4, 8.6, 72.0),
    ("Riad Dar Nubo", 3, 9.1, 55.0),
    ("Hotel Barceló", 4, 8.9, 98.5),
]


class BookingComAdapter(HotelProviderAdapter):
    name = "booking_com"

    def __init__(self):
        self.affiliate_id = os.environ.get("BOOKING_AFFILIATE_ID")
        self.deeplink_base = os.environ.get("BOOKING_DEEPLINK_BASE", "https://www.booking.com").rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.affiliate_id)

    async def list_destinations(self) -> List[HotelDestination]:
        return list(_DESTINATIONS)

    async def search(self, query: HotelSearchQuery) -> List[HotelOffer]:
        # TODO(Fase 2): Booking.com Affiliate API real cuando esté aprobado el partner.
        base_link = self.build_affiliate_link(query)
        offers: List[HotelOffer] = []
        for name, stars, score, price in _SAMPLE_HOTELS:
            offers.append(HotelOffer(
                provider=self.name,
                name=name,
                destination_code=query.destination_code,
                stars=stars,
                review_score=score,
                price_per_night=price,
                currency="EUR",
                deeplink=base_link,
                is_mock=True,
            ))
        return offers

    def build_affiliate_link(self, query: HotelSearchQuery, offer: Optional[HotelOffer] = None) -> str:
        dest = _DEST_INDEX.get(query.destination_code)
        params = {
            "ss": dest.name if dest else query.destination_code,
            "checkin": query.checkin,
            "checkout": query.checkout,
            "group_adults": query.guests.adults,
            "group_children": query.guests.children,
            "no_rooms": query.guests.rooms,
        }
        if self.affiliate_id:
            params["aid"] = self.affiliate_id
        return f"{self.deeplink_base}/searchresults.html?{urlencode(params)}"
