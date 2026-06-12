"""Seed an admin account and demo available drivers with locations across España y Marruecos.
Idempotent: safe to run multiple times.
Run: python /app/backend/seed_admin.py
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


ADMIN = {
    'email': 'admin@nuboexpress.com',
    'name': 'Administrador Nubo',
    'phone': '+34654242092',
    'password': 'Admin1234',
    'role': 'admin',
}

DEMO_DRIVERS = [
    {'name': 'Abeja Madrid', 'email': 'bee.madrid@nubo.com', 'lat': 40.4168, 'lng': -3.7038, 'vehicle': 'moto'},
    {'name': 'Abeja Barcelona', 'email': 'bee.barcelona@nubo.com', 'lat': 41.3874, 'lng': 2.1686, 'vehicle': 'bici'},
    {'name': 'Abeja Valencia', 'email': 'bee.valencia@nubo.com', 'lat': 39.4699, 'lng': -0.3763, 'vehicle': 'moto'},
    {'name': 'Abeja Sevilla', 'email': 'bee.sevilla@nubo.com', 'lat': 37.3891, 'lng': -5.9845, 'vehicle': 'coche'},
    {'name': 'Abeja Algeciras', 'email': 'bee.algeciras@nubo.com', 'lat': 36.1408, 'lng': -5.4534, 'vehicle': 'moto'},
    {'name': 'Abeja Tánger', 'email': 'bee.tanger@nubo.com', 'lat': 35.7595, 'lng': -5.8340, 'vehicle': 'moto'},
    {'name': 'Abeja Bilbao', 'email': 'bee.bilbao@nubo.com', 'lat': 43.2630, 'lng': -2.9350, 'vehicle': 'bici'},
]

DRIVER_PASSWORD = 'Driver1234'


async def main():
    # Admin
    existing = await db.users.find_one({'email': ADMIN['email']})
    if not existing:
        doc = {
            'id': str(uuid.uuid4()),
            'email': ADMIN['email'],
            'name': ADMIN['name'],
            'phone': ADMIN['phone'],
            'role': 'admin',
            'password_hash': hash_password(ADMIN['password']),
            'is_available': False,
            'vehicle_type': None,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(doc)
        print(f"Created admin: {ADMIN['email']} / {ADMIN['password']}")
    else:
        print(f"Admin already exists: {ADMIN['email']}")

    # Demo drivers
    for d in DEMO_DRIVERS:
        existing = await db.users.find_one({'email': d['email']})
        location = {'lat': d['lat'], 'lng': d['lng']}
        if not existing:
            doc = {
                'id': str(uuid.uuid4()),
                'email': d['email'],
                'name': d['name'],
                'phone': '+34654242092',
                'role': 'driver',
                'password_hash': hash_password(DRIVER_PASSWORD),
                'is_available': True,
                'vehicle_type': d['vehicle'],
                'current_location': location,
                'location_updated_at': datetime.now(timezone.utc).isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            await db.users.insert_one(doc)
            print(f"Created driver: {d['email']}")
        else:
            await db.users.update_one(
                {'email': d['email']},
                {'$set': {'is_available': True, 'current_location': location,
                          'location_updated_at': datetime.now(timezone.utc).isoformat()}}
            )
            print(f"Updated driver location: {d['email']}")

    print("Seed complete.")


if __name__ == '__main__':
    asyncio.run(main())
