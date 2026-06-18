"""Rutas de autenticación."""
from fastapi import APIRouter, HTTPException, Depends, Request

from core import (
    db, hash_password, verify_password, create_token, get_current_user,
    check_login_lockout, register_failed_login, clear_login_attempts,
)
from models import User, UserCreate, UserLogin, UserResponse

router = APIRouter()


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
