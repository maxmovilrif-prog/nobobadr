"""Geo helpers: city/country -> currency, and distance calculation."""
import math

# Common Moroccan cities (lowercase, no accents where possible)
MOROCCAN_CITIES = {
    "tanger", "tangier", "tánger", "casablanca", "casa", "rabat", "marrakech",
    "marrakesh", "fes", "fez", "fès", "meknes", "meknès", "nador", "agadir",
    "oujda", "kenitra", "tetouan", "tétouan", "safi", "mohammedia", "el jadida",
    "eljadida", "beni mellal", "khouribga", "taza", "settat", "larache",
    "ksar el kebir", "guelmim", "berkane", "taourirt", "ouarzazate", "essaouira",
    "khemisset", "errachidia", "tiznit", "sale", "salé", "temara", "berrechid",
}

# Country synonyms that map to MAD
MOROCCO_COUNTRY = {"ma", "mar", "morocco", "maroc", "marruecos", "المغرب"}
# Country synonyms that map to EUR (Spain / EU)
EUR_COUNTRY = {
    "es", "esp", "spain", "espana", "españa", "fr", "fra", "france", "francia",
    "pt", "portugal", "it", "italy", "italia", "de", "germany", "nl", "be",
    "eu", "european union", "union europea",
}


def currency_for_location(country: str | None = None, city: str | None = None) -> str:
    """Return MAD for Morocco, EUR for Spain/EU. Defaults to MAD (app origin)."""
    c = (country or "").strip().lower()
    city_l = (city or "").strip().lower()

    if city_l in MOROCCAN_CITIES:
        return "MAD"
    if c in MOROCCO_COUNTRY:
        return "MAD"
    if c in EUR_COUNTRY:
        return "EUR"
    # If a (non-Moroccan, non-EU listed) country is provided, default to EUR
    if c:
        return "EUR"
    return "MAD"


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometers."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)
