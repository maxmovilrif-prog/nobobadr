"""Adapter de Direct Ferries (Fase 1: afiliación).

Credenciales (Secrets de producción, NUNCA hardcodear):
  - DIRECT_FERRIES_API_KEY        → clave de la API B2B/Connect (cuando se contrate)
  - DIRECT_FERRIES_AFFILIATE_ID   → ID de afiliado para el tracking de comisiones
  - DIRECT_FERRIES_DEEPLINK_BASE  → base del deeplink (def: https://www.directferries.es)
  - DIRECT_FERRIES_BASE_URL       → base de la API REST (cuando se active la búsqueda en vivo)

Mientras no haya credenciales, `search()` devuelve travesías de EJEMPLO (is_mock=True)
para poder desarrollar el frontend, y `build_affiliate_link()` ya construye un enlace válido.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlencode

from .base import FerryProviderAdapter, FerryPort, FerryOffer, FerrySearchQuery

logger = logging.getLogger("nubo.bookings.directferries")

# Puertos clave del corredor España–Marruecos (Estrecho) + Mediterráneo, seed inicial.
_PORTS: List[FerryPort] = [
    FerryPort(code="ALG", name="Algeciras", country="ES"),
    FerryPort(code="TARM", name="Tarifa", country="ES"),
    FerryPort(code="ALM", name="Almería", country="ES"),
    FerryPort(code="MOT", name="Motril", country="ES"),
    FerryPort(code="MLN", name="Melilla", country="ES"),
    FerryPort(code="BCN", name="Barcelona", country="ES"),
    FerryPort(code="TNG", name="Tánger Med", country="MA"),
    FerryPort(code="TNGV", name="Tánger Ville", country="MA"),
    FerryPort(code="NDR", name="Nador", country="MA"),
    FerryPort(code="CEU", name="Ceuta", country="ES"),
]
_PORT_INDEX = {p.code: p for p in _PORTS}

# Operadoras de referencia para los datos de ejemplo del Estrecho.
_SAMPLE_OPERATORS = ["FRS Iberia", "Balearia", "Trasmediterránea", "AML"]


class DirectFerriesAdapter(FerryProviderAdapter):
    name = "direct_ferries"

    def __init__(self):
        self.api_key = os.environ.get("DIRECT_FERRIES_API_KEY")
        self.affiliate_id = os.environ.get("DIRECT_FERRIES_AFFILIATE_ID")
        self.deeplink_base = os.environ.get("DIRECT_FERRIES_DEEPLINK_BASE", "https://www.directferries.es").rstrip("/")
        self.api_base = os.environ.get("DIRECT_FERRIES_BASE_URL")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def list_ports(self) -> List[FerryPort]:
        return list(_PORTS)

    async def search(self, query: FerrySearchQuery) -> List[FerryOffer]:
        if not self.is_configured():
            return self._mock_offers(query)
        # TODO(Fase 2 transaccional / Connect API): llamar a la API REST real de Direct Ferries.
        # Por ahora, aún configurado, devolvemos ejemplo marcado para no bloquear el flujo.
        logger.info("Direct Ferries configurado pero búsqueda en vivo no implementada aún; usando ejemplo.")
        return self._mock_offers(query)

    def build_affiliate_link(self, query: FerrySearchQuery, offer: Optional[FerryOffer] = None) -> str:
        origin = _PORT_INDEX.get(query.origin_code)
        dest = _PORT_INDEX.get(query.destination_code)
        slug = f"{(origin.name if origin else query.origin_code)}-{(dest.name if dest else query.destination_code)}".replace(" ", "-").lower()
        params = {
            "depart": query.depart_date,
            "adults": query.passengers.adults,
        }
        if query.return_date:
            params["return"] = query.return_date
        if query.passengers.vehicle:
            params["vehicle"] = query.passengers.vehicle
        if self.affiliate_id:
            params["affid"] = self.affiliate_id
        return f"{self.deeplink_base}/ferry/{slug}.htm?{urlencode(params)}"

    def _mock_offers(self, query: FerrySearchQuery) -> List[FerryOffer]:
        base_link = self.build_affiliate_link(query)
        try:
            depart = datetime.fromisoformat(query.depart_date)
        except ValueError:
            depart = datetime.utcnow()
        offers: List[FerryOffer] = []
        for i, op in enumerate(_SAMPLE_OPERATORS[:3]):
            dep = depart.replace(hour=8 + i * 4, minute=0, second=0, microsecond=0)
            arr = dep + timedelta(minutes=90 + i * 15)
            offers.append(FerryOffer(
                provider=self.name,
                operator=op,
                origin_code=query.origin_code,
                destination_code=query.destination_code,
                depart_at=dep.isoformat(),
                arrive_at=arr.isoformat(),
                duration_mins=90 + i * 15,
                price_from=round(38.0 + i * 12.5, 2),
                currency="EUR",
                deeplink=base_link,
                is_mock=True,
            ))
        return offers
