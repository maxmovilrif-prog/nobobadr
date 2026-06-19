import asyncio
import os
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import bcrypt

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

ADMIN_EMAIL = "badarbox1756@gmail.com"
ADMIN_PASSWORD = "Admin1234!"


async def main():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    existing = await db.users.find_one({'email': ADMIN_EMAIL})
    pw_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    if existing:
        await db.users.update_one(
            {'email': ADMIN_EMAIL},
            {'$set': {'role': 'admin', 'password_hash': pw_hash, 'name': 'Administrador Nubo'}}
        )
        print(f"Admin actualizado: {ADMIN_EMAIL}")
    else:
        doc = {
            'id': str(uuid.uuid4()),
            'email': ADMIN_EMAIL,
            'name': 'Administrador Nubo',
            'phone': '+34654242092',
            'role': 'admin',
            'password_hash': pw_hash,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'is_available': False,
            'vehicle_type': None,
            'current_location': None,
        }
        await db.users.insert_one(doc)
        print(f"Admin creado: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == '__main__':
    asyncio.run(main())
