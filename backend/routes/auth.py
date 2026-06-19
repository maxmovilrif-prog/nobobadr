"""Rutas de autenticación."""
import os
import hmac
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from core import (
    db, hash_password, verify_password, create_token, get_current_user,
    check_login_lockout, register_failed_login, clear_login_attempts,
)
from models import User, UserCreate, UserLogin, UserResponse

router = APIRouter()


class PasswordResetRequest(BaseModel):
    email: str
    new_password: str
    secret: str


@router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    # Public registration cannot create privileged accounts
    if user_data.role not in ('customer', 'driver', 'business'):
        raise HTTPException(status_code=400, detail="Rol no válido")
    existing = await db.users.find_one({'email': user_data.email}, {'_id': 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_dict = user_data.model_dump()
    password = user_dict.pop('password')
    user_dict['password_hash'] = hash_password(password)

    user = User(**user_dict)
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.users.insert_one(doc)
    return UserResponse(**user.model_dump())


@router.post("/auth/login")
async def login(credentials: UserLogin, request: Request):
    # Detrás del ingress de K8s, request.client.host es la IP del proxy; usar X-Forwarded-For
    fwd = request.headers.get('x-forwarded-for', '')
    ip = fwd.split(',')[0].strip() if fwd else (request.client.host if request.client else "unknown")
    identifier = f"{ip}:{credentials.email.lower()}"
    await check_login_lockout(identifier)

    user = await db.users.find_one({'email': credentials.email}, {'_id': 0})
    if not user or not verify_password(credentials.password, user['password_hash']):
        await register_failed_login(identifier)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await clear_login_attempts(identifier)
    token = create_token(user['id'], user['role'])
    user.pop('password_hash')
    return {'token': token, 'user': user}


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)


@router.post("/admin/reset-password")
async def admin_reset_password(payload: PasswordResetRequest):
    """Reseteo de emergencia protegido por secreto (ADMIN_RESET_SECRET).

    Endpoint temporal: si la variable de entorno no está definida, queda
    desactivado (404) para que no sea una puerta trasera permanente.
    """
    expected = os.environ.get('ADMIN_RESET_SECRET', '')
    if not expected:
        raise HTTPException(status_code=404, detail="Not found")
    # Comparación en tiempo constante para evitar timing attacks
    if not hmac.compare_digest(payload.secret, expected):
        raise HTTPException(status_code=403, detail="Secreto inválido")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")

    email = payload.email.strip().lower()
    user = await db.users.find_one({'email': email}, {'_id': 0})
    if not user:
        # Provisiona una cuenta de Fundador si no existe (alta de admin real)
        doc = {
            'id': str(uuid.uuid4()),
            'email': email,
            'name': 'Administrador Nubo',
            'phone': '',
            'role': 'admin',
            'password_hash': hash_password(payload.new_password),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'is_available': False,
            'vehicle_type': None,
            'current_location': None,
        }
        await db.users.insert_one(doc)
        return {'success': True, 'email': email, 'role': 'admin', 'created': True}

    await db.users.update_one(
        {'email': email},
        {'$set': {'password_hash': hash_password(payload.new_password)}}
    )
    # Limpia bloqueos de fuerza bruta para esa cuenta
    await db.login_attempts.delete_many({'identifier': {'$regex': f':{email}$'}})
    return {'success': True, 'email': email, 'role': user.get('role'), 'created': False}
