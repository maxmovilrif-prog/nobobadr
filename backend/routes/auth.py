"""Rutas de autenticación."""
import os
import hmac
import uuid
import hashlib
import secrets
import logging
import traceback
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from core import (
    db, hash_password, verify_password, create_token, get_current_user,
    check_login_lockout, register_failed_login, clear_login_attempts,
)
from models import User, UserCreate, UserLogin, UserResponse
import email_service

router = APIRouter()
logger = logging.getLogger("nubo")

RESET_TOKEN_TTL_MINUTES = 60
APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://noboexpress.com").rstrip("/")


class PasswordResetRequest(BaseModel):
    email: str
    new_password: str
    secret: str


class ForgotPasswordRequest(BaseModel):
    email: str


class TokenResetRequest(BaseModel):
    token: str
    new_password: str


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PasswordResetRequest(BaseModel):
    email: str
    new_password: str
    secret: str


@router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    # Public registration cannot create privileged accounts
    if user_data.role not in ('customer', 'driver', 'business'):
        raise HTTPException(status_code=400, detail="Rol no válido")
    email_norm = user_data.email.strip().lower()
    existing = await db.users.find_one({'email': email_norm}, {'_id': 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_dict = user_data.model_dump()
    user_dict['email'] = user_dict['email'].strip().lower()
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
    email_norm = credentials.email.strip().lower()
    identifier = f"{ip}:{email_norm}"
    await check_login_lockout(identifier)

    user = await db.users.find_one({'email': email_norm}, {'_id': 0})
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


@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """Solicita un enlace de recuperación por email. Solo para cuentas de gestión
    (Fundador / Gestores regionales). Anti-enumeración: respuesta genérica siempre."""
    generic = {"message": "Si el email pertenece a una cuenta registrada, recibirás un enlace de recuperación."}
    email = payload.email.strip().lower()
    user = await db.users.find_one({'email': email}, {'_id': 0})
    # Cuentas con contraseña (los riders entran por QR → excluidos)
    if not user or user.get('role') not in ('admin', 'manager', 'customer', 'business') or not user.get('password_hash'):
        return generic

    raw = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    await db.password_reset_tokens.insert_one({
        'token_hash': _hash_token(raw),
        'user_id': user['id'],
        'email': email,
        'role': user.get('role'),
        'expires_at': expires_at,
        'used': False,
        'created_at': datetime.now(timezone.utc),
    })
    # El enlace apunta al panel correcto según el rol
    if user.get('role') in ('admin', 'manager'):
        reset_link = f"{APP_BASE_URL}/nubo-control/recuperar?token={raw}"
    else:
        reset_link = f"{APP_BASE_URL}/recuperar?token={raw}"
    result = await email_service.send_password_reset_email(email, reset_link, user.get('name', ''))
    if not result.get('sent'):
        logger.warning("forgot-password: email NO enviado a %s (%s)", email, result.get('reason'))
    return generic


@router.post("/auth/reset-password")
async def reset_password_with_token(payload: TokenResetRequest):
    """Restablece la contraseña usando el token recibido por email (un solo uso)."""
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    token_hash = _hash_token(payload.token.strip())
    now = datetime.now(timezone.utc)
    doc = await db.password_reset_tokens.find_one({'token_hash': token_hash})
    if not doc or doc.get('used'):
        raise HTTPException(status_code=400, detail="Enlace no válido o ya utilizado")
    exp = doc.get('expires_at')
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if not exp or exp < now:
        raise HTTPException(status_code=400, detail="El enlace ha caducado. Solicita uno nuevo.")

    await db.users.update_one(
        {'id': doc['user_id']},
        {'$set': {'password_hash': hash_password(payload.new_password)}}
    )
    await db.password_reset_tokens.update_one({'_id': doc['_id']}, {'$set': {'used': True}})
    # Limpia bloqueos de fuerza bruta de esa cuenta (best-effort)
    try:
        await db.login_attempts.delete_many({'identifier': {'$regex': f":{doc['email']}$"}})
    except Exception:
        pass
    return {'success': True, 'email': doc['email']}



@router.post("/admin/reset-password")
async def admin_reset_password(payload: PasswordResetRequest):
    """Reseteo de emergencia protegido por secreto (ADMIN_RESET_SECRET).

    Endpoint temporal: si la variable de entorno no está definida, queda
    desactivado (404) para que no sea una puerta trasera permanente.
    """
    expected = os.environ.get('ADMIN_RESET_SECRET', '').strip()
    if not expected:
        raise HTTPException(status_code=404, detail="Not found")
    # Comparación en tiempo constante; recortamos espacios/saltos invisibles a ambos lados
    if not hmac.compare_digest(payload.secret.strip(), expected):
        raise HTTPException(status_code=403, detail="Secreto inválido")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")

    email = payload.email.strip().lower()
    try:
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
        # Limpia bloqueos de fuerza bruta para esa cuenta (best-effort)
        try:
            await db.login_attempts.delete_many({'identifier': {'$regex': f':{email}$'}})
        except Exception:
            pass
        return {'success': True, 'email': email, 'role': user.get('role'), 'created': False}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("reset-password failed for %s: %s\n%s", email, exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Fallo interno: {type(exc).__name__}: {exc}")
