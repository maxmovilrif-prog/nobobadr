"""
routes/admin_routes.py — Nubo Express
Endpoints exclusivos del módulo Super Admin.

Rutas cubiertas:
  GET  /admin/dashboard          → Métricas en tiempo real
  GET  /admin/map/live           → Posiciones GPS de couriers activos
  GET  /admin/users              → Listar usuarios paginados
  POST /admin/users              → Crear usuario
  PUT  /admin/users/{id}/status  → Activar / desactivar usuario
  PUT  /admin/users/{id}/permissions → Actualizar permisos
  GET  /admin/couriers           → Listar couriers
  POST /admin/couriers           → Registrar courier
  PUT  /admin/couriers/{id}      → Actualizar datos de courier
  GET  /admin/rates              → Ver tarifas de envío
  PUT  /admin/rates/{id}         → Editar tarifa
  GET  /admin/audit-logs         → Historial de auditoría

Seguridad:
  - Todas las rutas requieren token JWT válido (dep. get_current_user)
  - Los permisos granulares se comprueban con require_permission()
  - Los errores de lógica (ValueError) se traducen a HTTP 400/404
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from controllers.admin_controller import (
    CourierController,
    DashboardController,
    RateController,
    UserController,
)
from models.admin import (
    CourierCreate,
    CourierStatus,
    CourierUpdate,
    DashboardMetrics,
    PaginatedResponse,
    ShippingRateUpdate,
    UserCreate,
    UserPermissions,
    UserPublic,
    UserRole,
)

# ── Dependencias de autenticación (stubs — reemplaza con tu auth real) ──────
# En producción, estas funciones validan el JWT, consultan el usuario en Mongo
# y comprueban el permiso requerido. Aquí se dejan como stubs documentados.

async def get_db() -> AsyncIOMotorDatabase:
    """
    Stub: inyecta la conexión Motor a MongoDB.
    Reemplazar con:
        from database import get_database
        return get_database()
    """
    raise NotImplementedError("Configura tu conexión a MongoDB.")


async def get_current_user(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """
    Stub: valida el Bearer JWT del header Authorization.
    Devuelve el documento del usuario autenticado.
    Lanza HTTP 401 si el token es inválido o está expirado.
    """
    # Ejemplo de implementación real:
    # token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    # payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    # user = await db["users"].find_one({"_id": ObjectId(payload["sub"])})
    # if not user or not user["is_active"]:
    #     raise HTTPException(status_code=401, detail="No autorizado")
    # return user
    raise NotImplementedError("Implementa la validación JWT.")


def require_permission(permission: str):
    """
    Factoría de dependencias: devuelve una dep. que verifica
    que el usuario autenticado tenga el permiso solicitado.

    Uso:
        @router.get("/...", dependencies=[Depends(require_permission("can_edit_rates"))])
    """
    async def _check(current_user: dict = Depends(get_current_user)):
        perms = current_user.get("permissions", {})
        # Super Admin siempre tiene acceso total
        if current_user.get("role") == UserRole.SUPER_ADMIN:
            return current_user
        if not perms.get(permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: '{permission}'.",
            )
        return current_user
    return _check


def _get_actor(current_user: dict) -> tuple[str, str]:
    """Extrae actor_id y actor_email del usuario autenticado."""
    return str(current_user["_id"]), current_user["email"]


def _handle_value_error(exc: ValueError, not_found_keywords: tuple = ("no encontrado",)) -> HTTPException:
    """
    Convierte ValueError del controller en HTTPException apropiada:
      - 404 si el mensaje sugiere que el recurso no existe
      - 400 para cualquier otra validación de negocio
    """
    msg = str(exc).lower()
    code = status.HTTP_404_NOT_FOUND if any(k in msg for k in not_found_keywords) else status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=str(exc))


# ════════════════════════════════════════════════════════════════
#  ROUTER PRINCIPAL
# ════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
    # Todas las rutas requieren usuario autenticado por defecto
    dependencies=[Depends(get_current_user)],
)


# ════════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard",
    response_model=DashboardMetrics,
    summary="Métricas en tiempo real del Super Admin",
    dependencies=[Depends(require_permission("can_view_live_map"))],
)
async def get_dashboard(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Devuelve en una sola llamada:
    - Pedidos activos
    - Couriers en turno
    - Ingresos del día en MAD y EUR
    - Pagos pendientes a couriers
    - Balance de caja (efectivo MAD / EUR)
    - Lista de alertas automáticas
    """
    return await DashboardController.get_metrics(db)


# ════════════════════════════════════════════════════════════════
#  MAPA EN VIVO
# ════════════════════════════════════════════════════════════════

@router.get(
    "/map/live",
    summary="Posiciones GPS en tiempo real de couriers activos",
    dependencies=[Depends(require_permission("can_view_live_map"))],
)
async def get_live_map(
    zone: Optional[str] = Query(None, description="Filtrar por zona (ej. 'Centro')"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Devuelve la lista de couriers en turno cuya posición GPS
    fue actualizada en los últimos 10 minutos.
    Diseñado para polling cada 15–30 segundos desde el frontend.

    Incluye por courier:
      id, nombre, teléfono, vehículo, zona, estado, lat, lng,
      timestamp de última actualización, total_entregas, rating.
    """
    couriers = await CourierController.get_live_courier_positions(db, zone=zone)
    return {
        "count": len(couriers),
        "couriers": couriers,
    }


# ════════════════════════════════════════════════════════════════
#  USUARIOS
# ════════════════════════════════════════════════════════════════

@router.post(
    "/users",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario",
    dependencies=[Depends(require_permission("can_manage_users"))],
)
async def create_user(
    payload: UserCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Crea un usuario con rol y permisos por defecto según su rol.
    - Solo el Super Admin puede crear otros Super Admins.
    - La contraseña se hashea antes de almacenarse.
    """
    # Protección extra: solo super_admin puede crear otro super_admin
    if payload.role == UserRole.SUPER_ADMIN and current_user.get("role") != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un Super Admin puede crear otro Super Admin.",
        )

    actor_id, actor_email = _get_actor(current_user)
    try:
        return await UserController.create_user(db, payload, actor_id, actor_email)
    except ValueError as e:
        raise _handle_value_error(e)


@router.get(
    "/users",
    response_model=PaginatedResponse,
    summary="Listar usuarios con filtros y paginación",
    dependencies=[Depends(require_permission("can_manage_users"))],
)
async def list_users(
    page: int     = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Resultados por página"),
    role: Optional[UserRole]   = Query(None, description="Filtrar por rol"),
    is_active: Optional[bool]  = Query(None, description="Filtrar por estado activo"),
    search: Optional[str]      = Query(None, description="Buscar por nombre o email"),
    db: AsyncIOMotorDatabase   = Depends(get_db),
):
    """
    Devuelve usuarios paginados. Combina filtros libremente:
    `?role=courier&is_active=true&search=ahmed&page=2`
    """
    return await UserController.list_users(
        db,
        page=page,
        per_page=per_page,
        role=role,
        is_active=is_active,
        search=search,
    )


@router.put(
    "/users/{user_id}/status",
    response_model=UserPublic,
    summary="Activar o desactivar un usuario",
    dependencies=[Depends(require_permission("can_manage_users"))],
)
async def toggle_user_status(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Alterna el estado `is_active` del usuario indicado.
    Un admin no puede desactivar su propia cuenta.
    """
    actor_id, actor_email = _get_actor(current_user)
    try:
        return await UserController.toggle_user_status(db, user_id, actor_id, actor_email)
    except ValueError as e:
        raise _handle_value_error(e)


@router.put(
    "/users/{user_id}/permissions",
    response_model=UserPublic,
    summary="Actualizar permisos granulares de un usuario",
    dependencies=[Depends(require_permission("can_manage_users"))],
)
async def update_user_permissions(
    user_id: str,
    permissions: UserPermissions,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Sobreescribe el objeto `permissions` del usuario.
    Envía solo los permisos que deseas activar como `true`.
    Los no enviados se desactivan.
    """
    actor_id, actor_email = _get_actor(current_user)
    try:
        return await UserController.update_permissions(
            db, user_id, permissions, actor_id, actor_email
        )
    except ValueError as e:
        raise _handle_value_error(e)


# ════════════════════════════════════════════════════════════════
#  COURIERS
# ════════════════════════════════════════════════════════════════

@router.post(
    "/couriers",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo perfil de courier",
    dependencies=[Depends(require_permission("can_manage_couriers"))],
)
async def create_courier(
    payload: CourierCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Crea el perfil operativo del courier vinculado a un usuario existente
    con rol `courier`. Configura zona, vehículo y tarifas base.
    """
    actor_id, actor_email = _get_actor(current_user)
    try:
        return await CourierController.create_courier(db, payload, actor_id, actor_email)
    except ValueError as e:
        raise _handle_value_error(e)


@router.get(
    "/couriers",
    response_model=PaginatedResponse,
    summary="Listar couriers con filtros y paginación",
    dependencies=[Depends(require_permission("can_manage_couriers"))],
)
async def list_couriers(
    page: int                      = Query(1, ge=1),
    per_page: int                  = Query(20, ge=1, le=100),
    status: Optional[CourierStatus] = Query(None, description="Filtrar por estado"),
    zone: Optional[str]            = Query(None, description="Filtrar por zona"),
    db: AsyncIOMotorDatabase       = Depends(get_db),
):
    """
    Lista couriers con datos de usuario enriquecidos (nombre, email).
    Filtra por estado operativo y/o zona de cobertura.
    """
    return await CourierController.list_couriers(
        db,
        page=page,
        per_page=per_page,
        status=status,
        zone=zone,
    )


@router.put(
    "/couriers/{courier_id}",
    summary="Actualizar datos de un courier",
    dependencies=[Depends(require_permission("can_manage_couriers"))],
)
async def update_courier(
    courier_id: str,
    payload: CourierUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    PATCH semántico: actualiza solo los campos enviados en el payload.
    Útil para cambiar zona, vehículo, tarifas o estado sin tocar el resto.
    """
    actor_id, actor_email = _get_actor(current_user)
    try:
        return await CourierController.update_courier(
            db, courier_id, payload, actor_id, actor_email
        )
    except ValueError as e:
        raise _handle_value_error(e)


# ════════════════════════════════════════════════════════════════
#  TARIFAS DE ENVÍO
# ════════════════════════════════════════════════════════════════

@router.get(
    "/rates",
    summary="Listar tarifas de envío configuradas",
    dependencies=[Depends(require_permission("can_edit_rates"))],
)
async def list_rates(
    only_active: bool = Query(True, description="Mostrar solo tarifas activas"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Devuelve todas las tarifas de envío por zona y tipo de vehículo.
    Por defecto filtra solo las activas.
    """
    return await RateController.list_rates(db, only_active=only_active)


@router.put(
    "/rates/{rate_id}",
    summary="Actualizar una tarifa de envío",
    dependencies=[Depends(require_permission("can_edit_rates"))],
)
async def update_rate(
    rate_id: str,
    payload: ShippingRateUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Actualiza precio base, precio por km o precio mínimo de una tarifa.
    Todos los cambios quedan registrados en el log de auditoría
    con estado antes/después.
    """
    actor_id, actor_email = _get_actor(current_user)
    try:
        return await RateController.update_rate(
            db, rate_id, payload, actor_id, actor_email
        )
    except ValueError as e:
        raise _handle_value_error(e)


# ════════════════════════════════════════════════════════════════
#  LOGS DE AUDITORÍA
# ════════════════════════════════════════════════════════════════

@router.get(
    "/audit-logs",
    response_model=PaginatedResponse,
    summary="Historial de auditoría de acciones administrativas",
    dependencies=[Depends(require_permission("can_manage_users"))],
)
async def list_audit_logs(
    page: int             = Query(1, ge=1),
    per_page: int         = Query(50, ge=1, le=200),
    actor_id: Optional[str]  = Query(None, description="Filtrar por actor (user_id)"),
    action: Optional[str]    = Query(None, description="Filtrar por tipo de acción"),
    resource: Optional[str]  = Query(None, description="Filtrar por colección afectada"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Devuelve el historial de auditoría paginado, ordenado del más reciente
    al más antiguo. Combina filtros libremente:
    `?action=UPDATE_SHIPPING_RATE&resource=shipping_rates`
    """
    import math
    from bson import ObjectId

    query: dict = {}
    if actor_id:
        query["actor_id"] = actor_id
    if action:
        query["action"] = {"$regex": action, "$options": "i"}
    if resource:
        query["resource"] = resource

    skip = (page - 1) * per_page
    total = await db["audit_logs"].count_documents(query)
    cursor = (
        db["audit_logs"]
        .find(query, {"before": 0, "after": 0})   # Excluye payloads pesados del listado
        .skip(skip)
        .limit(per_page)
        .sort("timestamp", -1)
    )
    docs = await cursor.to_list(length=per_page)
    for d in docs:
        d["_id"] = str(d["_id"])

    return PaginatedResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
        data=docs,
    )


@router.get(
    "/audit-logs/{log_id}",
    summary="Detalle completo de un log de auditoría (incluye before/after)",
    dependencies=[Depends(require_permission("can_manage_users"))],
)
async def get_audit_log_detail(
    log_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Devuelve el log completo incluyendo los campos `before` y `after`
    para inspección detallada de cambios.
    """
    from bson import ObjectId

    try:
        doc = await db["audit_logs"].find_one({"_id": ObjectId(log_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID de log inválido.")

    if not doc:
        raise HTTPException(status_code=404, detail="Log no encontrado.")

    doc["_id"] = str(doc["_id"])
    return doc
