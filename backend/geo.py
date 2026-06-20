"""Helpers geográficos: distancia (haversine) y moneda por país/ciudad (España €/Marruecos MAD)."""
import math
from typing import Optional

# Ciudades marroquíes comunes (en minúsculas)
MOROCCAN_CITIES = {
    "tanger", "tangier", "tánger", "tanger med", "casablanca", "casa", "rabat", "marrakech",
    "marrakesh", "fes", "fez", "fès", "meknes", "meknès", "nador", "agadir",
    "oujda", "kenitra", "tetouan", "tétouan", "tetuan", "tetuán", "safi", "mohammedia", "el jadida",
    "eljadida", "beni mellal", "khouribga", "taza", "settat", "larache",
    "ksar el kebir", "guelmim", "berkane", "taourirt", "ouarzazate", "essaouira",
    "khemisset", "errachidia", "tiznit", "sale", "salé", "temara", "berrechid", "alhucemas",
    "al hoceima",
}

MOROCCO_COUNTRY = {"ma", "mar", "morocco", "maroc", "marruecos", "المغرب"}
EUR_COUNTRY = {
    "es", "esp", "spain", "espana", "españa", "fr", "fra", "france", "francia",
    "pt", "portugal", "it", "italy", "italia", "de", "germany", "nl", "be",
    "eu", "european union", "union europea",
}

# Tasa de cambio de referencia: 1 MAD = 0.092 EUR  ->  1 EUR ≈ 10.87 MAD
EUR_PER_MAD = 0.092
MAD_PER_EUR = 1 / EUR_PER_MAD

# Tarifas base por vehículo (en EUR): tarifa base + coste por km + velocidad media (km/h)
VEHICLE_PRICING = {
    "bicycle":    {"base": 2.0, "per_km": 0.50, "speed_kmh": 15, "label": "Bici"},
    "motorcycle": {"base": 3.0, "per_km": 0.80, "speed_kmh": 40, "label": "Moto"},
    "car":        {"base": 4.0, "per_km": 1.20, "speed_kmh": 50, "label": "Coche"},
    "truck":      {"base": 6.0, "per_km": 1.80, "speed_kmh": 45, "label": "Camión"},
}

# Factor de tráfico/ajuste aplicado al ETA teórico
ETA_TRAFFIC_FACTOR = 1.3

# ===== Nubo Ride (transporte de pasajeros) — tarifas específicas =====
# Tarifa base + coste por km + coste por minuto + tarifa mínima (todo en EUR).
RIDE_PRICING = {
    "economy": {"base": 1.50, "per_km": 0.90, "per_min": 0.20, "min_fare": 4.0, "speed_kmh": 40, "label": "Economy"},
    "comfort": {"base": 2.50, "per_km": 1.20, "per_min": 0.30, "min_fare": 6.0, "speed_kmh": 40, "label": "Comfort"},
    "xl":      {"base": 3.50, "per_km": 1.60, "per_min": 0.35, "min_fare": 9.0, "speed_kmh": 35, "label": "XL / Van"},
}

RIDE_VEHICLE_TYPES = set(RIDE_PRICING.keys())


def calculate_ride_quote(origin_lat: float, origin_lng: float,
                         destination_lat: float, destination_lng: float,
                         vehicle_type: str = "economy", currency: str = "EUR") -> dict:
    """Calcula la tarifa de un viaje de pasajeros (Nubo Ride) por distancia + tiempo, con tarifa mínima."""
    pricing = RIDE_PRICING.get(vehicle_type, RIDE_PRICING["economy"])
    distance_km = haversine_km(origin_lat, origin_lng, destination_lat, destination_lng)
    base_eta = (distance_km / pricing["speed_kmh"]) * 60 if pricing["speed_kmh"] else 0
    adjusted_eta = max(3, round(base_eta * ETA_TRAFFIC_FACTOR))
    fare_eur = pricing["base"] + pricing["per_km"] * distance_km + pricing["per_min"] * adjusted_eta
    fare_eur = max(pricing["min_fare"], fare_eur)
    price = convert_from_eur(fare_eur, currency)
    return {
        "distance_km": distance_km,
        "estimated_price": price,
        "currency": currency if currency in ("EUR", "MAD") else "EUR",
        "eta_mins": adjusted_eta,
        "vehicle_type": vehicle_type if vehicle_type in RIDE_PRICING else "economy",
        "vehicle_label": pricing["label"],
    }


def currency_for_location(country: Optional[str] = None, city: Optional[str] = None) -> str:
    """Devuelve MAD para Marruecos, EUR para España/UE. Por defecto EUR."""
    c = (country or "").strip().lower()
    city_l = (city or "").strip().lower()
    if city_l in MOROCCAN_CITIES:
        return "MAD"
    if c in MOROCCO_COUNTRY:
        return "MAD"
    if c in EUR_COUNTRY:
        return "EUR"
    if c:
        return "EUR"
    return "EUR"


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en km (gran círculo) entre dos puntos."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def convert_from_eur(amount_eur: float, currency: str) -> float:
    """Convierte un importe en EUR a la moneda solicitada (EUR o MAD)."""
    if currency == "MAD":
        return round(amount_eur * MAD_PER_EUR, 2)
    return round(amount_eur, 2)


def calculate_delivery_quote(origin_lat: float, origin_lng: float,
                             destination_lat: float, destination_lng: float,
                             vehicle_type: str, currency: str = "EUR") -> dict:
    """Calcula la tarifa de envío punto a punto según distancia, vehículo y moneda."""
    pricing = VEHICLE_PRICING.get(vehicle_type, VEHICLE_PRICING["motorcycle"])
    distance_km = haversine_km(origin_lat, origin_lng, destination_lat, destination_lng)
    fee_eur = pricing["base"] + pricing["per_km"] * distance_km
    delivery_fee = convert_from_eur(fee_eur, currency)
    base_eta = (distance_km / pricing["speed_kmh"]) * 60 if pricing["speed_kmh"] else 0
    adjusted_eta = max(5, round(base_eta * ETA_TRAFFIC_FACTOR))
    return {
        "distance_km": distance_km,
        "delivery_fee": delivery_fee,
        "currency": currency if currency in ("EUR", "MAD") else "EUR",
        "base_eta_mins": round(base_eta),
        "adjusted_eta_mins": adjusted_eta,
        "vehicle_used": vehicle_type if vehicle_type in VEHICLE_PRICING else "motorcycle",
    }
