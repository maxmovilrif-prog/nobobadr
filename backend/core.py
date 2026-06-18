"""Núcleo compartido: configuración, base de datos, auth y gestor de WebSockets."""
import os
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("nubo")

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Stripe Configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', 'sk_test_emergent')

# LLM Configuration (Emergent Universal Key)
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Telegram Bot (alertas al administrador)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_ADMIN_CHAT_ID = os.environ.get('TELEGRAM_ADMIN_CHAT_ID')

security = HTTPBearer()

# =========================
# AUTH HELPERS
# =========================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_token(user_id: str, role: str, hours: int = JWT_EXPIRATION_HOURS) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=hours)
    payload = {'user_id': user_id, 'role': role, 'exp': expiration}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Token de larga duración para el dispositivo del rider (app de conductores)
RIDER_TOKEN_HOURS = 24 * 30  # 30 días

def create_rider_token(user_id: str) -> str:
    return create_token(user_id, 'driver', hours=RIDER_TOKEN_HOURS)


# Protección anti fuerza bruta para el login del fundador (capa admin)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

async def check_login_lockout(identifier: str):
    """Lanza 429 si el identificador {ip:email} está bloqueado por intentos fallidos."""
    rec = await db.login_attempts.find_one({'identifier': identifier})
    if not rec:
        return
    if rec.get('count', 0) >= MAX_LOGIN_ATTEMPTS:
        locked_until = rec.get('locked_until')
        if locked_until:
            lu = datetime.fromisoformat(locked_until) if isinstance(locked_until, str) else locked_until
            if lu.tzinfo is None:
                lu = lu.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < lu:
                mins = int((lu - datetime.now(timezone.utc)).total_seconds() // 60) + 1
                raise HTTPException(status_code=429, detail=f"Demasiados intentos. Cuenta bloqueada {mins} min.")

async def register_failed_login(identifier: str):
    rec = await db.login_attempts.find_one({'identifier': identifier})
    count = (rec.get('count', 0) if rec else 0) + 1
    update = {'count': count, 'updated_at': datetime.now(timezone.utc).isoformat()}
    if count >= MAX_LOGIN_ATTEMPTS:
        update['locked_until'] = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
    await db.login_attempts.update_one({'identifier': identifier}, {'$set': update}, upsert=True)

async def clear_login_attempts(identifier: str):
    await db.login_attempts.delete_one({'identifier': identifier})


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload['user_id']
        user = await db.users.find_one({'id': user_id}, {'_id': 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Acceso solo para el Fundador")
    return current_user


async def get_current_manager_or_admin(current_user: dict = Depends(get_current_user)):
    """Permite acceso al Fundador (admin) y al equipo de Gestión (manager).
    Para endpoints operativos (despacho, cola de pedidos, tarifas), NO financieros."""
    if current_user.get('role') not in ('admin', 'manager'):
        raise HTTPException(status_code=403, detail="Acceso solo para Fundador o Gestores")
    return current_user


async def get_current_business(current_user: dict = Depends(get_current_user)):
    if current_user.get('role') != 'business':
        raise HTTPException(status_code=403, detail="Only business users can perform this action")
    return current_user


async def get_current_rider(current_user: dict = Depends(get_current_user)):
    if current_user.get('role') != 'driver':
        raise HTTPException(status_code=403, detail="Acceso solo para conductores")
    return current_user


def generate_qr_data_url(text: str) -> str:
    """Genera un QR como data URL PNG base64 (para mostrar/imprimir en la ficha del rider)."""
    import io
    import base64
    import qrcode
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# =========================
# WEBSOCKET CONNECTION MANAGER
# =========================

class ConnectionManager:
    """Gestiona las conexiones WebSocket activas para tracking en tiempo real"""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.driver_locations: Dict[str, Dict] = {}

    async def connect(self, order_id: str, websocket: WebSocket):
        await websocket.accept()
        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)
        logger.info(f"New WebSocket connection for order {order_id}")

    def disconnect(self, order_id: str, websocket: WebSocket):
        if order_id in self.active_connections:
            self.active_connections[order_id].remove(websocket)
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]
        logger.info(f"WebSocket disconnected for order {order_id}")

    async def broadcast_location(self, order_id: str, message: dict):
        """Envía la ubicación de la Abeja 🐝 a todos los clientes conectados"""
        if order_id in self.active_connections:
            self.driver_locations[order_id] = message
            for connection in self.active_connections[order_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")

    def get_driver_location(self, order_id: str):
        return self.driver_locations.get(order_id)


manager = ConnectionManager()
