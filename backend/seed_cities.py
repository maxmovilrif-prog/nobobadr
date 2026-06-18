import asyncio
import os
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

CITIES = [
    # España
    {"name": "Algeciras", "lat": 36.1408, "lng": -5.4562, "country": "ES"},
    {"name": "Tarifa", "lat": 36.0143, "lng": -5.6044, "country": "ES"},
    {"name": "La Línea de la Concepción", "lat": 36.1684, "lng": -5.3483, "country": "ES"},
    {"name": "Málaga", "lat": 36.7213, "lng": -4.4214, "country": "ES"},
    {"name": "Cádiz", "lat": 36.5271, "lng": -6.2886, "country": "ES"},
    {"name": "Sevilla", "lat": 37.3891, "lng": -5.9845, "country": "ES"},
    {"name": "Madrid", "lat": 40.4168, "lng": -3.7038, "country": "ES"},
    {"name": "Barcelona", "lat": 41.3851, "lng": 2.1734, "country": "ES"},
    # Marruecos
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
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    created = 0
    for c in CITIES:
        if await db.cities.find_one({'name': c['name']}):
            continue
        doc = {"id": str(uuid.uuid4()), **c}
        await db.cities.insert_one(doc)
        created += 1
    total = await db.cities.count_documents({})
    print(f"Seed ciudades: {created} nuevas | total en BD: {total}")


if __name__ == '__main__':
    asyncio.run(main())
