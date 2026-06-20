"""Conexión a MongoDB compartida.

Antes, server.py y dropshipping_routes.py creaban CADA UNO su propio
AsyncIOMotorClient (dos pools de conexión distintos hacia la misma base de
datos). Ahora ambos importan la misma instancia desde aquí, y este módulo no
depende de server.py ni de ningún otro módulo de la app, así que se puede
importar en cualquier orden sin riesgo de import circular.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
