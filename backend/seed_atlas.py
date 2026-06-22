"""Seed one-off para el clúster Atlas de producción de Nubo.

Uso (las credenciales se leen SOLO de variables de entorno, nunca del código):
    ATLAS_URL="mongodb+srv://..." ATLAS_DB="nubo_produccion" \
    ADMIN_EMAIL="tu-admin@dominio.com" ADMIN_PASSWORD="********" \
    python3 seed_atlas.py
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone

import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient

CITIES = [
    {"name": "Algeciras", "lat": 36.1408, "lng": -5.4562, "country": "ES"},
    {"name": "Tarifa", "lat": 36.0143, "lng": -5.6044, "country": "ES"},
    {"name": "La Línea de la Concepción", "lat": 36.1684, "lng": -5.3483, "country": "ES"},
    {"name": "Málaga", "lat": 36.7213, "lng": -4.4214, "country": "ES"},
    {"name": "Cádiz", "lat": 36.5271, "lng": -6.2886, "country": "ES"},
    {"name": "Sevilla", "lat": 37.3891, "lng": -5.9845, "country": "ES"},
    {"name": "Madrid", "lat": 40.4168, "lng": -3.7038, "country": "ES"},
    {"name": "Barcelona", "lat": 41.3851, "lng": 2.1734, "country": "ES"},
    {"name": "Tánger", "lat": 35.7595, "lng": -5.8340, "country": "MA"},
    {"name": "Tánger Med", "lat": 35.8838, "lng": -5.4980, "country": "MA"},
    {"name": "Tetuán", "lat": 35.5785, "lng": -5.3684, "country": "MA"},
    {"name": "Nador", "lat": 35.1681, "lng": -2.9335, "country": "MA"},
    {"name": "Casablanca", "lat": 33.5731, "lng": -7.5898, "country": "MA"},
    {"name": "Rabat", "lat": 34.0209, "lng": -6.8416, "country": "MA"},
    {"name": "Meknés", "lat": 33.8935, "lng": -5.5473, "country": "MA"},
    {"name": "Alhucemas", "lat": 35.2517, "lng": -3.9372, "country": "MA"},
]


async def main():
    url = os.environ["ATLAS_URL"]
    db_name = os.environ.get("ATLAS_DB", "nubo_produccion")
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        raise SystemExit("Faltan ADMIN_EMAIL y/o ADMIN_PASSWORD en las variables de entorno.")

    client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=20000)
    db = client[db_name]

    # 1) Ciudades
    created = 0
    for c in CITIES:
        if await db.cities.find_one({"name": c["name"]}):
            continue
        await db.cities.insert_one({"id": str(uuid.uuid4()), **c})
        created += 1
    print(f"Ciudades: {created} nuevas | total: {await db.cities.count_documents({})}")

    # 2) Índice geoespacial para auto-despacho
    try:
        await db.users.create_index([("geo_location", "2dsphere")])
        print("Índice 2dsphere en users.geo_location: OK")
    except Exception as e:
        print("Índice 2dsphere:", e)

    # 3) Cuenta de Fundador
    pw_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    existing = await db.users.find_one({"email": admin_email})
    if existing:
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"role": "admin", "password_hash": pw_hash, "name": "Administrador Nubo"}},
        )
        print(f"Fundador actualizado: {admin_email}")
    else:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "name": "Administrador Nubo",
            "phone": "",
            "role": "admin",
            "password_hash": pw_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_available": False,
            "vehicle_type": None,
            "current_location": None,
        })
        print(f"Fundador creado: {admin_email}")


if __name__ == "__main__":
    asyncio.run(main())
