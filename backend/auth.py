"""JWT authentication: password hashing, token management, auth router, deps."""
import os
import uuid
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal

from database import db

JWT_ALGORITHM = "HS256"
ACCESS_MINUTES = 60 * 12  # 12h access token (mobile-friendly)
REFRESH_DAYS = 30

ROLES = ("admin", "dispatcher", "rider", "customer")


# ----------------------------- Password -----------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ----------------------------- Tokens -----------------------------
def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])


# ----------------------------- Models -----------------------------
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str
    role: Literal["rider", "customer", "dispatcher"] = "customer"
    phone: Optional[str] = None
    city: Optional[str] = None
    vehicle: Optional[str] = None


class LoginInput(BaseModel):
    email: EmailStr
    password: str


# ----------------------------- Helpers -----------------------------
def _public_user(u: dict) -> dict:
    u = dict(u)
    u.pop("password_hash", None)
    u.pop("_id", None)
    return u


def _set_cookies(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=False,
                        samesite="lax", max_age=ACCESS_MINUTES * 60, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=False,
                        samesite="lax", max_age=REFRESH_DAYS * 86400, path="/")


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("access_token")


async def get_current_user(request: Request) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Tipo de token inválido")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return _public_user(user)


def require_roles(*roles):
    async def dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Permiso denegado")
        return user
    return dep


async def get_user_from_token(token: str) -> Optional[dict]:
    """Used by WebSocket auth (token via query param)."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        return _public_user(user) if user else None
    except Exception:
        return None


# ----------------------------- Router -----------------------------
router = APIRouter(prefix="/api/auth")


@router.post("/register")
async def register(payload: RegisterInput, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": payload.name,
        "role": payload.role,
        "phone": payload.phone,
        "city": payload.city,
        "vehicle": payload.vehicle,
        "active": True,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    access = create_access_token(user["id"], email, user["role"])
    refresh = create_refresh_token(user["id"])
    _set_cookies(response, access, refresh)
    return {"access_token": access, "token_type": "bearer", "user": _public_user(user)}


@router.post("/login")
async def login(payload: LoginInput, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    access = create_access_token(user["id"], email, user["role"])
    refresh = create_refresh_token(user["id"])
    _set_cookies(response, access, refresh)
    return {"access_token": access, "token_type": "bearer", "user": _public_user(user)}


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Sin refresh token")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Tipo inválido")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh inválido")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    access = create_access_token(user["id"], user["email"], user["role"])
    response.set_cookie("access_token", access, httponly=True, secure=False,
                        samesite="lax", max_age=ACCESS_MINUTES * 60, path="/")
    return {"access_token": access, "token_type": "bearer", "user": _public_user(user)}


# ----------------------------- Seeding -----------------------------
async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@moboexpress.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": admin_email, "name": "Administrador",
            "role": "admin", "active": True,
            "password_hash": hash_password(admin_password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif not verify_password(admin_password, existing.get("password_hash", "")):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )

    # Seed a demo rider for testing
    rider_email = "rider@moboexpress.com"
    if await db.users.find_one({"email": rider_email}) is None:
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": rider_email, "name": "Amine (Rider)",
            "role": "rider", "active": True, "phone": "+212600000000",
            "city": "Tanger", "vehicle": "Moto",
            "password_hash": hash_password("rider123"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })


async def ensure_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id")
