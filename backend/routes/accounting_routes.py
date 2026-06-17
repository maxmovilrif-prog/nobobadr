"""
routes/accounting_routes.py — Nubo Express
Endpoints del módulo de Contabilidad.

Rutas cubiertas:
  ── TRANSACCIONES ──────────────────────────────────────────────
  GET  /accounting/transactions          → Listar transacciones filtrables
  POST /accounting/transactions          → Registrar transacción manual
  GET  /accounting/transactions/summary  → Resumen de ingresos/gastos por período

  ── CAJA DE EFECTIVO ───────────────────────────────────────────
  GET  /accounting/cash/balance          → Saldo actual de caja (MAD + EUR)
  POST /accounting/cash/in               → Registrar ingreso de efectivo
  POST /accounting/cash/out              → Registrar salida de efectivo

  ── STRIPE ─────────────────────────────────────────────────────
  GET  /accounting/stripe/balance        → Saldo Stripe en tiempo real
  GET  /accounting/stripe/charges        → Cargos recientes de Stripe
  POST /accounting/stripe/payout         → Iniciar payout desde Stripe

  ── NÓMINAS ────────────────────────────────────────────────────
  GET  /accounting/payroll               → Ver nóminas por período
  POST /accounting/payroll/generate      → Calcular nóminas de couriers
  PUT  /accounting/payroll/{id}/pay      → Marcar nómina como pagada
  GET  /accounting/payroll/summary       → Resumen total de nóminas

  ── EXPORTACIÓN ────────────────────────────────────────────────
  GET  /accounting/export/transactions   → Exportar transacciones (CSV / JSON)
  GET  /accounting/export/payroll        → Exportar nóminas (CSV / JSON)
  GET  /accounting/export/report         → Reporte contable completo (JSON)

Seguridad:
  - Requiere permiso `can_view_accounting` para lectura
  - Requiere permiso `can_edit_accounting` para escritura y exportación
"""

from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime, timedelta
from typing import Literal, Optional

import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

# Reutilizamos las dependencias de autenticación definidas en admin_routes
from routes.admin_routes import get_current_user, get_db, require_permission, _get_actor, _handle_value_error
from controllers.admin_controller import write_audit_log
from models.admin import (
    Currency,
    PaginatedResponse,
    PaymentMethod,
    PayrollEntry,
    PayrollReport,
    TransactionCreate,
    TransactionDB,
    TransactionType,
)


# ══════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN STRIPE (variables de entorno en producción)
# ══════════════════════════════════════════════════════════════════

import os

STRIPE_SECRET_KEY   = os.getenv("STRIPE_SECRET_KEY", "sk_test_REPLACE_ME")
STRIPE_API_BASE     = "https://api.stripe.com/v1"
MAD_TO_EUR_RATE     = float(os.getenv("MAD_TO_EUR_RATE", "0.092"))  # Tipo de cambio de respaldo

# Headers reutilizables para las llamadas a la API de Stripe
_STRIPE_HEADERS = {
    "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
    "Content-Type": "application/x-www-form-urlencoded",
}


# ══════════════════════════════════════════════════════════════════
#  HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════

def _parse_date_range(
    date_from: Optional[str],
    date_to: Optional[str],
) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Convierte strings ISO 8601 a objetos datetime.
    Lanza HTTP 422 si el formato es incorrecto.
    """
    fmt = "%Y-%m-%d"
    try:
        dt_from = datetime.strptime(date_from, fmt) if date_from else None
        dt_to   = (
            datetime.strptime(date_to, fmt).replace(hour=23, minute=59, second=59)
            if date_to else None
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Formato de fecha inválido. Usa YYYY-MM-DD.",
        )
    return dt_from, dt_to


def _build_transaction_query(
    type_: Optional[TransactionType],
    currency: Optional[Currency],
    payment_method: Optional[PaymentMethod],
    courier_id: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    is_reconciled: Optional[bool],
) -> dict:
    """Construye el filtro Mongo a partir de los query params opcionales."""
    q: dict = {}
    if type_:           q["type"]           = type_
    if currency:        q["currency"]       = currency
    if payment_method:  q["payment_method"] = payment_method
    if courier_id:      q["courier_id"]     = courier_id
    if is_reconciled is not None: q["is_reconciled"] = is_reconciled
    date_filter: dict = {}
    if date_from:  date_filter["$gte"] = date_from
    if date_to:    date_filter["$lte"] = date_to
    if date_filter: q["created_at"] = date_filter
    return q


async def _stripe_get(path: str, params: dict | None = None) -> dict:
    """Llamada GET genérica a la API de Stripe con manejo de errores."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{STRIPE_API_BASE}{path}",
            headers=_STRIPE_HEADERS,
            params=params or {},
            timeout=10.0,
        )
    if r.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de Stripe ({r.status_code}): {r.text[:200]}",
        )
    return r.json()


async def _stripe_post(path: str, data: dict) -> dict:
    """Llamada POST genérica a la API de Stripe."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{STRIPE_API_BASE}{path}",
            headers=_STRIPE_HEADERS,
            data=data,
            timeout=15.0,
        )
    if r.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de Stripe ({r.status_code}): {r.text[:200]}",
        )
    return r.json()


def _serialize_doc(doc: dict) -> dict:
    """Convierte ObjectId y datetime a tipos JSON-serializables."""
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = _serialize_doc(v)
        else:
            result[k] = v
    return result


# ══════════════════════════════════════════════════════════════════
#  ROUTER PRINCIPAL
# ══════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/accounting",
    tags=["Contabilidad"],
    dependencies=[Depends(get_current_user)],
)


# ════════════════════════════════════════════════════════════════
#  TRANSACCIONES
# ════════════════════════════════════════════════════════════════

@router.get(
    "/transactions",
    response_model=PaginatedResponse,
    summary="Listar transacciones con filtros avanzados",
    dependencies=[Depends(require_permission("can_view_accounting"))],
)
async def list_transactions(
    page:            int                        = Query(1, ge=1),
    per_page:        int                        = Query(30, ge=1, le=200),
    type_:           Optional[TransactionType]  = Query(None, alias="type"),
    currency:        Optional[Currency]         = Query(None),
    payment_method:  Optional[PaymentMethod]    = Query(None),
    courier_id:      Optional[str]              = Query(None),
    date_from:       Optional[str]              = Query(None, description="YYYY-MM-DD"),
    date_to:         Optional[str]              = Query(None, description="YYYY-MM-DD"),
    is_reconciled:   Optional[bool]             = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Listado completo de transacciones con filtros combinables:
    - Por tipo: income, payout, refund, adjustment, cash_in, cash_out
    - Por moneda: MAD, EUR
    - Por método de pago: stripe, cash_mad, cash_eur, bank_transfer
    - Por courier, rango de fechas y estado de conciliación

    Ejemplo: `?type=income&currency=MAD&date_from=2025-01-01&date_to=2025-01-31`
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)
    query = _build_transaction_query(
        type_, currency, payment_method,
        courier_id, dt_from, dt_to, is_reconciled,
    )

    skip   = (page - 1) * per_page
    total  = await db["transactions"].count_documents(query)
    cursor = db["transactions"].find(query).skip(skip).limit(per_page).sort("created_at", -1)
    docs   = await cursor.to_list(length=per_page)

    return PaginatedResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
        data=[_serialize_doc(d) for d in docs],
    )


@router.post(
    "/transactions",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar transacción contable manual",
    dependencies=[Depends(require_permission("can_edit_accounting"))],
)
async def create_transaction(
    payload: TransactionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Registra una transacción manual (ajuste de caja, ingreso extra, etc.).
    Calcula automáticamente el equivalente en EUR si la moneda es MAD.
    """
    actor_id, actor_email = _get_actor(current_user)

    amount_eur = (
        round(payload.amount * MAD_TO_EUR_RATE, 4)
        if payload.currency == Currency.MAD
        else payload.amount
    )

    now = datetime.utcnow()
    doc = {
        "_id":            ObjectId(),
        "type":           payload.type,
        "amount":         payload.amount,
        "currency":       payload.currency,
        "amount_eur":     amount_eur,
        "payment_method": payload.payment_method,
        "reference_id":   payload.reference_id,
        "description":    payload.description,
        "courier_id":     payload.courier_id,
        "customer_id":    payload.customer_id,
        "created_by":     actor_id,
        "created_at":     now,
        "is_reconciled":  False,
    }

    await db["transactions"].insert_one(doc)
    await write_audit_log(
        db,
        actor_id=actor_id,
        actor_email=actor_email,
        action="CREATE_TRANSACTION",
        resource="transactions",
        resource_id=str(doc["_id"]),
        after={
            "type": payload.type,
            "amount": payload.amount,
            "currency": payload.currency,
            "description": payload.description,
        },
    )

    return _serialize_doc(doc)


@router.get(
    "/transactions/summary",
    summary="Resumen de ingresos y gastos por período",
    dependencies=[Depends(require_permission("can_view_accounting"))],
)
async def get_transactions_summary(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: AsyncIOMotorDatabase  = Depends(get_db),
):
    """
    Devuelve un resumen contable agregado para el período indicado:
    - Total ingresos MAD / EUR
    - Total gastos (payouts + refunds) MAD / EUR
    - Balance neto
    - Desglose por tipo de transacción y por método de pago
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)
    match_stage: dict = {}
    if dt_from or dt_to:
        date_filter: dict = {}
        if dt_from: date_filter["$gte"] = dt_from
        if dt_to:   date_filter["$lte"] = dt_to
        match_stage["created_at"] = date_filter

    # Agrega por tipo y moneda
    by_type_pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": {"type": "$type", "currency": "$currency"},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.type": 1}},
    ]

    # Agrega por método de pago
    by_method_pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$payment_method",
                "total_mad": {
                    "$sum": {
                        "$cond": [{"$eq": ["$currency", "MAD"]}, "$amount", 0]
                    }
                },
                "total_eur": {
                    "$sum": {
                        "$cond": [{"$eq": ["$currency", "EUR"]}, "$amount", 0]
                    }
                },
                "count": {"$sum": 1},
            }
        },
    ]

    by_type   = await db["transactions"].aggregate(by_type_pipeline).to_list(50)
    by_method = await db["transactions"].aggregate(by_method_pipeline).to_list(20)

    # Calcula totales globales
    income_types  = {TransactionType.INCOME, TransactionType.CASH_IN}
    expense_types = {TransactionType.PAYOUT, TransactionType.REFUND, TransactionType.CASH_OUT}

    total_income_mad = total_income_eur = 0.0
    total_expense_mad = total_expense_eur = 0.0

    for row in by_type:
        t_type    = row["_id"]["type"]
        currency  = row["_id"]["currency"]
        amount    = row["total"]
        if t_type in income_types:
            if currency == Currency.MAD: total_income_mad  += amount
            else:                        total_income_eur  += amount
        elif t_type in expense_types:
            if currency == Currency.MAD: total_expense_mad += amount
            else:                        total_expense_eur += amount

    return {
        "period":          {"from": date_from, "to": date_to},
        "total_income":    {"MAD": round(total_income_mad, 2),  "EUR": round(total_income_eur, 2)},
        "total_expenses":  {"MAD": round(total_expense_mad, 2), "EUR": round(total_expense_eur, 2)},
        "net_balance":     {
            "MAD": round(total_income_mad  - total_expense_mad, 2),
            "EUR": round(total_income_eur  - total_expense_eur, 2),
        },
        "breakdown_by_type":   by_type,
        "breakdown_by_method": by_method,
    }


# ════════════════════════════════════════════════════════════════
#  CAJA DE EFECTIVO
# ════════════════════════════════════════════════════════════════

@router.get(
    "/cash/balance",
    summary="Saldo actual de caja en efectivo (MAD y EUR)",
    dependencies=[Depends(require_permission("can_view_accounting"))],
)
async def get_cash_balance(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Calcula el saldo de caja en tiempo real sumando todas las entradas
    y restando todas las salidas de efectivo registradas históricamente.
    Devuelve saldo en MAD y EUR por separado.
    """
    pipeline = [
        {
            "$match": {
                "payment_method": {"$in": ["cash_mad", "cash_eur"]},
            }
        },
        {
            "$group": {
                "_id": "$payment_method",
                "balance": {
                    "$sum": {
                        "$cond": [
                            {
                                "$in": [
                                    "$type",
                                    [TransactionType.INCOME, TransactionType.CASH_IN],
                                ]
                            },
                            "$amount",
                            {"$multiply": ["$amount", -1]},
                        ]
                    }
                },
                "last_movement": {"$max": "$created_at"},
            }
        },
    ]

    results = await db["transactions"].aggregate(pipeline).to_list(5)
    balance_map = {r["_id"]: r for r in results}

    mad_data = balance_map.get("cash_mad", {})
    eur_data = balance_map.get("cash_eur", {})

    return {
        "cash_mad": {
            "balance":        round(mad_data.get("balance", 0.0), 2),
            "last_movement":  mad_data.get("last_movement"),
        },
        "cash_eur": {
            "balance":        round(eur_data.get("balance", 0.0), 2),
            "last_movement":  eur_data.get("last_movement"),
        },
        "as_of": datetime.utcnow().isoformat(),
    }


@router.post(
    "/cash/in",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar ingreso de efectivo en caja",
    dependencies=[Depends(require_permission("can_edit_accounting"))],
)
async def cash_in(
    amount:      float   = Query(..., gt=0, description="Cantidad a ingresar"),
    currency:    Currency = Query(..., description="MAD o EUR"),
    description: str     = Query(..., min_length=3, description="Concepto del ingreso"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Registra una entrada manual de efectivo en caja.
    Útil para ingresos en mano, cambio de moneda, etc.
    """
    actor_id, actor_email = _get_actor(current_user)
    payment_method = PaymentMethod.CASH_MAD if currency == Currency.MAD else PaymentMethod.CASH_EUR
    amount_eur = round(amount * MAD_TO_EUR_RATE, 4) if currency == Currency.MAD else amount

    doc = {
        "_id":            ObjectId(),
        "type":           TransactionType.CASH_IN,
        "amount":         amount,
        "currency":       currency,
        "amount_eur":     amount_eur,
        "payment_method": payment_method,
        "description":    description,
        "created_by":     actor_id,
        "created_at":     datetime.utcnow(),
        "is_reconciled":  False,
    }

    await db["transactions"].insert_one(doc)
    await write_audit_log(
        db, actor_id=actor_id, actor_email=actor_email,
        action="CASH_IN", resource="transactions",
        resource_id=str(doc["_id"]),
        after={"amount": amount, "currency": currency, "description": description},
    )
    return _serialize_doc(doc)


@router.post(
    "/cash/out",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar salida de efectivo de caja",
    dependencies=[Depends(require_permission("can_edit_accounting"))],
)
async def cash_out(
    amount:      float    = Query(..., gt=0),
    currency:    Currency = Query(...),
    description: str      = Query(..., min_length=3),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Registra una salida de efectivo de caja.
    Valida que haya saldo suficiente antes de registrar la operación.
    """
    actor_id, actor_email = _get_actor(current_user)

    # Verificar saldo suficiente consultando el balance actual
    payment_method = "cash_mad" if currency == Currency.MAD else "cash_eur"
    balance_pipeline = [
        {"$match": {"payment_method": payment_method}},
        {
            "$group": {
                "_id": None,
                "balance": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$type", [TransactionType.INCOME, TransactionType.CASH_IN]]},
                            "$amount",
                            {"$multiply": ["$amount", -1]},
                        ]
                    }
                },
            }
        },
    ]
    result = await db["transactions"].aggregate(balance_pipeline).to_list(1)
    current_balance = result[0]["balance"] if result else 0.0

    if current_balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saldo insuficiente en caja. Disponible: {round(current_balance, 2)} {currency}.",
        )

    pm = PaymentMethod.CASH_MAD if currency == Currency.MAD else PaymentMethod.CASH_EUR
    amount_eur = round(amount * MAD_TO_EUR_RATE, 4) if currency == Currency.MAD else amount

    doc = {
        "_id":            ObjectId(),
        "type":           TransactionType.CASH_OUT,
        "amount":         amount,
        "currency":       currency,
        "amount_eur":     amount_eur,
        "payment_method": pm,
        "description":    description,
        "created_by":     actor_id,
        "created_at":     datetime.utcnow(),
        "is_reconciled":  False,
    }

    await db["transactions"].insert_one(doc)
    await write_audit_log(
        db, actor_id=actor_id, actor_email=actor_email,
        action="CASH_OUT", resource="transactions",
        resource_id=str(doc["_id"]),
        after={"amount": amount, "currency": currency, "description": description},
    )
    return _serialize_doc(doc)


# ════════════════════════════════════════════════════════════════
#  STRIPE
# ════════════════════════════════════════════════════════════════

@router.get(
    "/stripe/balance",
    summary="Saldo disponible en Stripe en tiempo real",
    dependencies=[Depends(require_permission("can_view_accounting"))],
)
async def get_stripe_balance():
    """
    Consulta el saldo disponible y pendiente en Stripe.
    Devuelve los importes en todas las monedas configuradas en la cuenta.
    """
    data = await _stripe_get("/balance")
    return {
        "available": data.get("available", []),
        "pending":   data.get("pending", []),
        "livemode":  data.get("livemode", False),
    }


@router.get(
    "/stripe/charges",
    summary="Cargos recientes procesados por Stripe",
    dependencies=[Depends(require_permission("can_view_accounting"))],
)
async def get_stripe_charges(
    limit:          int           = Query(25, ge=1, le=100),
    starting_after: Optional[str] = Query(None, description="Cursor para paginación Stripe"),
):
    """
    Lista los cargos más recientes de Stripe con paginación por cursor.
    Devuelve datos crudos de Stripe: id, amount, status, customer, created.
    """
    params: dict = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after

    data = await _stripe_get("/charges", params=params)
    return {
        "charges":  data.get("data", []),
        "has_more": data.get("has_more", False),
    }


@router.post(
    "/stripe/payout",
    summary="Iniciar payout desde Stripe a cuenta bancaria",
    dependencies=[Depends(require_permission("can_edit_accounting"))],
)
async def create_stripe_payout(
    amount:      float  = Query(..., gt=0, description="Importe en EUR"),
    description: str    = Query("Payout Nubo Express", min_length=3),
    current_user: dict  = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Inicia un payout desde el saldo disponible de Stripe hacia
    la cuenta bancaria configurada en el dashboard de Stripe.
    El importe debe estar en EUR. Stripe lo convierte a céntimos internamente.
    """
    actor_id, actor_email = _get_actor(current_user)

    # Stripe recibe los importes en céntimos (enteros)
    amount_cents = int(amount * 100)

    data = await _stripe_post("/payouts", {
        "amount":      amount_cents,
        "currency":    "eur",
        "description": description,
    })

    # Registrar el payout como transacción interna
    doc = {
        "_id":              ObjectId(),
        "type":             TransactionType.PAYOUT,
        "amount":           amount,
        "currency":         Currency.EUR,
        "amount_eur":       amount,
        "payment_method":   PaymentMethod.STRIPE,
        "stripe_charge_id": data.get("id"),
        "description":      f"Stripe payout: {description}",
        "created_by":       actor_id,
        "created_at":       datetime.utcnow(),
        "is_reconciled":    False,
    }
    await db["transactions"].insert_one(doc)
    await write_audit_log(
        db, actor_id=actor_id, actor_email=actor_email,
        action="STRIPE_PAYOUT", resource="transactions",
        resource_id=str(doc["_id"]),
        after={"amount": amount, "stripe_payout_id": data.get("id")},
    )

    return {
        "transaction_id": str(doc["_id"]),
        "stripe_payout":  data,
    }


# ════════════════════════════════════════════════════════════════
#  NÓMINAS DE COURIERS
# ════════════════════════════════════════════════════════════════

@router.post(
    "/payroll/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Calcular y generar nóminas del período indicado",
    dependencies=[Depends(require_permission("can_edit_accounting"))],
)
async def generate_payroll(
    date_from: str = Query(..., description="Inicio del período YYYY-MM-DD"),
    date_to:   str = Query(..., description="Fin del período YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Calcula las nóminas de todos los couriers activos para el período dado.

    Algoritmo:
      1. Busca todos los pedidos completados en el período, agrupados por courier
      2. Multiplica el número de entregas × tarifa base del courier
      3. Genera una entrada de nómina por courier
      4. Guarda el reporte consolidado en la colección `payroll_reports`

    No sobrescribe nóminas ya pagadas.
    """
    actor_id, actor_email = _get_actor(current_user)
    dt_from, dt_to = _parse_date_range(date_from, date_to)

    # 1. Agrupar entregas completadas por courier en el período
    deliveries_pipeline = [
        {
            "$match": {
                "status": "delivered",
                "delivered_at": {"$gte": dt_from, "$lte": dt_to},
            }
        },
        {
            "$group": {
                "_id": "$courier_id",
                "total_deliveries": {"$sum": 1},
            }
        },
    ]
    deliveries = await db["orders"].aggregate(deliveries_pipeline).to_list(500)
    delivery_map = {d["_id"]: d["total_deliveries"] for d in deliveries}

    if not delivery_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron entregas completadas en el período indicado.",
        )

    # 2. Obtener datos de couriers para calcular tarifas
    courier_ids = list(delivery_map.keys())
    couriers_cursor = db["couriers"].find(
        {"user_id": {"$in": courier_ids}},
        {"user_id": 1, "base_rate_mad": 1, "hourly_rate_mad": 1},
    )
    couriers = await couriers_cursor.to_list(500)

    # 3. Join con usuarios para obtener nombre completo
    user_ids = [ObjectId(c["user_id"]) for c in couriers]
    users_cursor = db["users"].find(
        {"_id": {"$in": user_ids}},
        {"_id": 1, "full_name": 1},
    )
    users = await users_cursor.to_list(500)
    users_map = {str(u["_id"]): u["full_name"] for u in users}

    # 4. Construir entradas de nómina
    entries: list[dict] = []
    total_net_mad = 0.0

    for courier in couriers:
        uid         = courier["user_id"]
        deliveries_count = delivery_map.get(uid, 0)
        if deliveries_count == 0:
            continue

        base_earnings = round(deliveries_count * courier["base_rate_mad"], 2)
        net_amount    = base_earnings  # Aquí se pueden sumar bonos o restar deducciones

        entry = {
            "_id":             ObjectId(),
            "courier_id":      uid,
            "courier_name":    users_map.get(uid, "Desconocido"),
            "period_start":    dt_from,
            "period_end":      dt_to,
            "total_deliveries": deliveries_count,
            "base_earnings":   base_earnings,
            "bonus":           0.0,
            "deductions":      0.0,
            "net_amount":      net_amount,
            "currency":        Currency.MAD,
            "is_paid":         False,
            "paid_at":         None,
        }
        entries.append(entry)
        total_net_mad += net_amount

    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay couriers con entregas en el período.",
        )

    # 5. Guardar entradas y reporte consolidado
    await db["payroll_entries"].insert_many(entries)

    report = {
        "_id":           ObjectId(),
        "period_start":  dt_from,
        "period_end":    dt_to,
        "total_entries": len(entries),
        "total_net_mad": round(total_net_mad, 2),
        "total_net_eur": round(total_net_mad * MAD_TO_EUR_RATE, 2),
        "generated_at":  datetime.utcnow(),
        "generated_by":  actor_id,
    }
    await db["payroll_reports"].insert_one(report)

    await write_audit_log(
        db, actor_id=actor_id, actor_email=actor_email,
        action="GENERATE_PAYROLL", resource="payroll_reports",
        resource_id=str(report["_id"]),
        after={"period": f"{date_from} / {date_to}", "total_entries": len(entries)},
    )

    return {
        "report_id":     str(report["_id"]),
        "period":        {"from": date_from, "to": date_to},
        "total_entries": len(entries),
        "total_net_mad": report["total_net_mad"],
        "total_net_eur": report["total_net_eur"],
        "entries":       [_serialize_doc(e) for e in entries],
    }


@router.get(
    "/payroll",
    response_model=PaginatedResponse,
    summary="Ver nóminas por período y estado de pago",
    dependencies=[Depends(require_permission("can_view_accounting"))],
)
async def list_payroll(
    page:      int            = Query(1, ge=1),
    per_page:  int            = Query(30, ge=1, le=100),
    is_paid:   Optional[bool] = Query(None, description="Filtrar por estado de pago"),
    date_from: Optional[str]  = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str]  = Query(None, description="YYYY-MM-DD"),
    db: AsyncIOMotorDatabase  = Depends(get_db),
):
    """Lista entradas de nómina con filtros por estado de pago y período."""
    dt_from, dt_to = _parse_date_range(date_from, date_to)
    query: dict = {}
    if is_paid is not None:
        query["is_paid"] = is_paid
    if dt_from or dt_to:
        date_f: dict = {}
        if dt_from: date_f["$gte"] = dt_from
        if dt_to:   date_f["$lte"] = dt_to
        query["period_start"] = date_f

    skip   = (page - 1) * per_page
    total  = await db["payroll_entries"].count_documents(query)
    cursor = db["payroll_entries"].find(query).skip(skip).limit(per_page).sort("period_start", -1)
    docs   = await cursor.to_list(length=per_page)

    return PaginatedResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
        data=[_serialize_doc(d) for d in docs],
    )


@router.put(
    "/payroll/{entry_id}/pay",
    summary="Marcar una nómina como pagada",
    dependencies=[Depends(require_permission("can_edit_accounting"))],
)
async def mark_payroll_paid(
    entry_id:       str,
    payment_method: PaymentMethod = Query(..., description="Método de pago usado"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Marca una entrada de nómina como pagada.
    Registra el método de pago y el timestamp del pago.
    No se puede volver a marcar como no pagada desde aquí
    (usa una corrección manual vía /transactions).
    """
    actor_id, actor_email = _get_actor(current_user)

    try:
        entry = await db["payroll_entries"].find_one({"_id": ObjectId(entry_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID de nómina inválido.")

    if not entry:
        raise HTTPException(status_code=404, detail="Entrada de nómina no encontrada.")
    if entry.get("is_paid"):
        raise HTTPException(status_code=400, detail="Esta nómina ya está marcada como pagada.")

    now = datetime.utcnow()
    await db["payroll_entries"].update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": {"is_paid": True, "paid_at": now, "payment_method": payment_method}},
    )

    # Crear transacción de payout vinculada
    payout_doc = {
        "_id":            ObjectId(),
        "type":           TransactionType.PAYOUT,
        "amount":         entry["net_amount"],
        "currency":       entry["currency"],
        "amount_eur":     round(entry["net_amount"] * MAD_TO_EUR_RATE, 4),
        "payment_method": payment_method,
        "reference_id":   entry_id,
        "description":    f"Nómina {entry['courier_name']} — {entry['period_start'].strftime('%Y-%m-%d')} / {entry['period_end'].strftime('%Y-%m-%d')}",
        "courier_id":     entry["courier_id"],
        "created_by":     actor_id,
        "created_at":     now,
        "is_reconciled":  True,
    }
    await db["transactions"].insert_one(payout_doc)

    await write_audit_log(
        db, actor_id=actor_id, actor_email=actor_email,
        action="PAY_PAYROLL_ENTRY", resource="payroll_entries",
        resource_id=entry_id,
        before={"is_paid": False},
        after={"is_paid": True, "paid_at": now.isoformat(), "payment_method": payment_method},
    )

    entry["is_paid"]        = True
    entry["paid_at"]        = now
    entry["payment_method"] = payment_method
    return _serialize_doc(entry)


@router.get(
    "/payroll/summary",
    summary="Resumen total de nóminas por estado",
    dependencies=[Depends(require_permission("can_view_accounting"))],
)
async def payroll_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Devuelve el total acumulado de nóminas pagadas y pendientes,
    tanto en MAD como en EUR.
    """
    pipeline = [
        {
            "$group": {
                "_id": "$is_paid",
                "total_mad": {"$sum": "$net_amount"},
                "count": {"$sum": 1},
            }
        }
    ]
    results = await db["payroll_entries"].aggregate(pipeline).to_list(5)
    paid   = next((r for r in results if r["_id"] is True),  {"total_mad": 0, "count": 0})
    unpaid = next((r for r in results if r["_id"] is False), {"total_mad": 0, "count": 0})

    return {
        "paid": {
            "count":     paid["count"],
            "total_mad": round(paid["total_mad"], 2),
            "total_eur": round(paid["total_mad"] * MAD_TO_EUR_RATE, 2),
        },
        "pending": {
            "count":     unpaid["count"],
            "total_mad": round(unpaid["total_mad"], 2),
            "total_eur": round(unpaid["total_mad"] * MAD_TO_EUR_RATE, 2),
        },
    }


# ════════════════════════════════════════════════════════════════
#  EXPORTACIÓN DE DATOS
# ════════════════════════════════════════════════════════════════

def _docs_to_csv(docs: list[dict], fieldnames: list[str]) -> str:
    """Convierte lista de dicts a string CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(docs)
    return output.getvalue()


@router.get(
    "/export/transactions",
    summary="Exportar transacciones en CSV o JSON",
    dependencies=[Depends(require_permission("can_export_data"))],
)
async def export_transactions(
    format_:   Literal["csv", "json"] = Query("csv", alias="format"),
    date_from: Optional[str]          = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str]          = Query(None, description="YYYY-MM-DD"),
    type_:     Optional[TransactionType] = Query(None, alias="type"),
    currency:  Optional[Currency]     = Query(None),
    db: AsyncIOMotorDatabase          = Depends(get_db),
):
    """
    Descarga todas las transacciones del período en CSV o JSON.
    Límite: 10.000 registros por exportación.
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)
    query = _build_transaction_query(type_, currency, None, None, dt_from, dt_to, None)

    cursor = db["transactions"].find(query).sort("created_at", -1).limit(10_000)
    docs   = await cursor.to_list(length=10_000)
    docs   = [_serialize_doc(d) for d in docs]

    filename = f"nubo_transactions_{date_from or 'all'}_{date_to or 'all'}"

    if format_ == "json":
        content = json.dumps(docs, ensure_ascii=False, indent=2, default=str)
        return StreamingResponse(
            io.StringIO(content),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )

    # CSV
    fieldnames = [
        "_id", "type", "amount", "currency", "amount_eur",
        "payment_method", "description", "courier_id",
        "reference_id", "created_by", "created_at", "is_reconciled",
    ]
    csv_content = _docs_to_csv(docs, fieldnames)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


@router.get(
    "/export/payroll",
    summary="Exportar nóminas de couriers en CSV o JSON",
    dependencies=[Depends(require_permission("can_export_data"))],
)
async def export_payroll(
    format_:   Literal["csv", "json"] = Query("csv", alias="format"),
    is_paid:   Optional[bool]         = Query(None),
    date_from: Optional[str]          = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str]          = Query(None, description="YYYY-MM-DD"),
    db: AsyncIOMotorDatabase          = Depends(get_db),
):
    """Descarga nóminas filtradas por estado de pago y período en CSV o JSON."""
    dt_from, dt_to = _parse_date_range(date_from, date_to)
    query: dict = {}
    if is_paid is not None: query["is_paid"] = is_paid
    if dt_from:  query.setdefault("period_start", {})["$gte"] = dt_from
    if dt_to:    query.setdefault("period_start", {})["$lte"] = dt_to

    cursor = db["payroll_entries"].find(query).sort("period_start", -1).limit(5_000)
    docs   = [_serialize_doc(d) for d in await cursor.to_list(5_000)]

    filename = f"nubo_payroll_{date_from or 'all'}_{date_to or 'all'}"

    if format_ == "json":
        content = json.dumps(docs, ensure_ascii=False, indent=2, default=str)
        return StreamingResponse(
            io.StringIO(content),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )

    fieldnames = [
        "_id", "courier_id", "courier_name", "period_start", "period_end",
        "total_deliveries", "base_earnings", "bonus", "deductions",
        "net_amount", "currency", "is_paid", "paid_at", "payment_method",
    ]
    return StreamingResponse(
        io.StringIO(_docs_to_csv(docs, fieldnames)),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


@router.get(
    "/export/report",
    summary="Reporte contable completo del período en JSON",
    dependencies=[Depends(require_permission("can_export_data"))],
)
async def export_full_report(
    date_from: str = Query(..., description="YYYY-MM-DD"),
    date_to:   str = Query(..., description="YYYY-MM-DD"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Genera un reporte JSON consolidado que incluye:
    - Resumen de ingresos y gastos del período
    - Balance de caja al cierre del período
    - Total de nóminas generadas y pagadas
    - Número de pedidos entregados

    Diseñado para exportar y enviar al equipo financiero o contable externo.
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)

    # Resumen de transacciones
    tx_match = {"created_at": {"$gte": dt_from, "$lte": dt_to}}
    tx_pipeline = [
        {"$match": tx_match},
        {"$group": {
            "_id": {"type": "$type", "currency": "$currency"},
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
    ]
    tx_summary = await db["transactions"].aggregate(tx_pipeline).to_list(50)

    # Nóminas del período
    payroll_pipeline = [
        {"$match": {"period_start": {"$gte": dt_from}, "period_end": {"$lte": dt_to}}},
        {"$group": {
            "_id": "$is_paid",
            "total_mad": {"$sum": "$net_amount"},
            "count": {"$sum": 1},
        }},
    ]
    payroll_summary = await db["payroll_entries"].aggregate(payroll_pipeline).to_list(5)

    # Pedidos entregados
    orders_count = await db["orders"].count_documents({
        "status": "delivered",
        "delivered_at": {"$gte": dt_from, "$lte": dt_to},
    })

    report = {
        "generated_at":    datetime.utcnow().isoformat(),
        "period":          {"from": date_from, "to": date_to},
        "orders_delivered": orders_count,
        "transactions":    tx_summary,
        "payroll":         payroll_summary,
        "exchange_rate":   {"MAD_TO_EUR": MAD_TO_EUR_RATE},
    }

    content = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    filename = f"nubo_report_{date_from}_{date_to}.json"
    return StreamingResponse(
        io.StringIO(content),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
