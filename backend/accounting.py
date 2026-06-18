"""Núcleo de Contabilidad y Finanzas (Bloque D).

- Comisiones/nóminas de repartidores (Abejas) a partir de pedidos entregados.
- Libro de transacciones (ingresos, pagos, devoluciones, ajustes, caja MAD/EUR).
- Caja en efectivo (cash_in/cash_out), arqueo diario y auditoría ligera.
Todo 100% interno (Modo Pruebas Internas), Pydantic v2 + UUID + datetime UTC ISO.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from core import db

# Comisión por defecto del repartidor (10% del importe del pedido)
DEFAULT_COMMISSION_RATE = 0.10

# Tipo de cambio de referencia: 1 MAD = 0.092 EUR
ACCT_MAD_TO_EUR = 0.092

ACCT_TXN_TYPES = {'income', 'payout', 'refund', 'adjustment', 'cash_in', 'cash_out'}
ACCT_INCOME_TYPES = {'income', 'cash_in'}
ACCT_EXPENSE_TYPES = {'payout', 'refund', 'cash_out'}
ACCT_CURRENCIES = {'MAD', 'EUR'}
ACCT_METHODS = {'stripe', 'cash_mad', 'cash_eur', 'bank_transfer'}


# =========================
# Comisiones / nóminas
# =========================

def payout_key(driver_id, start_date, end_date):
    """Clave única de un ciclo de pago: repartidor + periodo."""
    return {'driver_id': driver_id, 'period_start': start_date or '', 'period_end': end_date or ''}


def _order_eff_date(o):
    """Fecha efectiva de entrega (delivered_at > updated_at > created_at)."""
    return (o.get('delivered_at') or o.get('updated_at') or o.get('created_at') or '')[:10]


def _in_range(d, start_date, end_date):
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True


async def compute_earnings(query, start_date, end_date, rate):
    """Agrega entregas e ingresos por repartidor a partir de pedidos 'delivered'."""
    orders = await db.orders.find(query, {'_id': 0, 'driver_id': 1, 'total_amount': 1,
                                          'delivered_at': 1, 'updated_at': 1, 'created_at': 1}).to_list(50000)
    per = {}
    for o in orders:
        if not _in_range(_order_eff_date(o), start_date, end_date):
            continue
        did = o.get('driver_id')
        if not did:
            continue
        amt = float(o.get('total_amount') or 0)
        e = per.setdefault(did, {'deliveries': 0, 'revenue': 0.0})
        e['deliveries'] += 1
        e['revenue'] += amt
    return per


# =========================
# Libro de transacciones
# =========================

def acct_amount_eur(amount: float, currency: str) -> float:
    """Equivalente en EUR de cualquier importe (almacenamos siempre la conversión)."""
    return round(amount * ACCT_MAD_TO_EUR, 4) if currency == 'MAD' else round(amount, 2)


def acct_validate(type_: str, currency: str, method: str):
    if type_ not in ACCT_TXN_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Usa uno de: {sorted(ACCT_TXN_TYPES)}")
    if currency not in ACCT_CURRENCIES:
        raise HTTPException(status_code=400, detail="Moneda inválida (MAD o EUR)")
    if method not in ACCT_METHODS:
        raise HTTPException(status_code=400, detail=f"Método inválido. Usa uno de: {sorted(ACCT_METHODS)}")


async def acct_audit(current_user: dict, action: str, resource_id: str, after: dict):
    """Registro de auditoría ligero de acciones contables (no bloqueante)."""
    try:
        await db.audit_logs.insert_one({
            'id': str(uuid.uuid4()),
            'actor_id': current_user.get('id'),
            'actor_email': current_user.get('email'),
            'actor_name': current_user.get('name'),
            'action': action,
            'resource': 'transactions',
            'resource_id': resource_id,
            'after': after,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': True,
        })
    except Exception:
        pass


def acct_date_query(date_from: Optional[str], date_to: Optional[str]) -> dict:
    """Filtro de rango sobre created_at (ISO string) por fecha YYYY-MM-DD."""
    q = {}
    if date_from:
        q['$gte'] = date_from
    if date_to:
        q['$lte'] = date_to + '\uffff'  # incluye todo el día indicado
    return {'created_at': q} if q else {}


async def acct_create_txn(current_user: dict, *, type_: str, amount: float, currency: str,
                          method: str, description: str, reference_id=None,
                          courier_id=None, customer_id=None, action: str) -> dict:
    acct_validate(type_, currency, method)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        'id': str(uuid.uuid4()),
        'type': type_,
        'amount': round(float(amount), 2),
        'currency': currency,
        'amount_eur': acct_amount_eur(amount, currency),
        'payment_method': method,
        'reference_id': reference_id,
        'description': description,
        'courier_id': courier_id,
        'customer_id': customer_id,
        'created_by': current_user.get('id'),
        'created_by_name': current_user.get('name'),
        'created_at': now,
        'is_reconciled': False,
    }
    await db.transactions.insert_one({**doc})
    await acct_audit(current_user, action, doc['id'],
                     {'type': type_, 'amount': doc['amount'], 'currency': currency, 'description': description})
    doc.pop('_id', None)
    return doc


async def record_order_income(order: dict) -> bool:
    """Registra automáticamente un ingreso en el libro al completarse un pedido.
    Idempotente: si ya existe un ingreso con ese reference_id, no duplica."""
    if not order:
        return False
    order_id = order.get('id')
    try:
        exists = await db.transactions.find_one({'reference_id': order_id, 'type': 'income'}, {'_id': 0, 'id': 1})
        if exists:
            return False
        amount = float(order.get('total_amount') or 0)
        if amount <= 0:
            return False
        currency = order.get('currency') or 'EUR'
        if currency not in ACCT_CURRENCIES:
            currency = 'EUR'
        is_express = order.get('order_type') == 'express'
        label = 'Pedido exprés' if is_express else 'Pedido'
        desc = f"{label} #{str(order_id)[:8]}"
        if order.get('city_name'):
            desc += f" · {order['city_name']}"
        system_actor = {'id': 'system', 'name': 'Sistema (auto)', 'email': None}
        await acct_create_txn(
            system_actor, type_='income', amount=amount, currency=currency,
            method='stripe', description=desc, reference_id=order_id,
            customer_id=order.get('customer_id'), action='AUTO_INCOME_ORDER',
        )
        return True
    except Exception:
        return False


# =========================
# Caja / arqueo diario
# =========================

async def compute_cash_balance() -> dict:
    """Saldo de caja en efectivo (MAD y EUR) a partir de cash_in/cash_out."""
    txns = await db.transactions.find(
        {'payment_method': {'$in': ['cash_mad', 'cash_eur']}}, {'_id': 0}
    ).to_list(50000)
    bal = {'cash_mad': 0.0, 'cash_eur': 0.0}
    last = {'cash_mad': None, 'cash_eur': None}
    for t in txns:
        pm = t.get('payment_method')
        if pm not in bal:
            continue
        amt = float(t.get('amount') or 0)
        sign = 1 if t.get('type') in ACCT_INCOME_TYPES else -1
        bal[pm] = round(bal[pm] + sign * amt, 2)
        ca = t.get('created_at')
        if ca and (last[pm] is None or ca > last[pm]):
            last[pm] = ca
    return {
        'cash_mad': {'balance': bal['cash_mad'], 'last_movement': last['cash_mad']},
        'cash_eur': {'balance': bal['cash_eur'], 'last_movement': last['cash_eur']},
        'as_of': datetime.now(timezone.utc).isoformat(),
    }


async def compute_daily_closing(date_str: str) -> dict:
    """Arqueo de caja de un día: saldo inicial, movimientos por moneda, cierre e ingresos/gastos."""
    cash_methods = ['cash_mad', 'cash_eur']
    day_gte = date_str
    day_lte = date_str + '\uffff'
    opening = {'cash_mad': 0.0, 'cash_eur': 0.0}
    async for t in db.transactions.find(
        {'payment_method': {'$in': cash_methods}, 'created_at': {'$lt': day_gte}},
        {'_id': 0, 'payment_method': 1, 'type': 1, 'amount': 1}
    ):
        pm = t['payment_method']
        sign = 1 if t.get('type') in ACCT_INCOME_TYPES else -1
        opening[pm] = round(opening[pm] + sign * float(t.get('amount') or 0), 2)
    day = await db.transactions.find({'created_at': {'$gte': day_gte, '$lte': day_lte}}, {'_id': 0}).to_list(50000)
    mov = {'cash_mad': {'in': 0.0, 'out': 0.0}, 'cash_eur': {'in': 0.0, 'out': 0.0}}
    inc = {'MAD': 0.0, 'EUR': 0.0}
    exp = {'MAD': 0.0, 'EUR': 0.0}
    for t in day:
        amt = float(t.get('amount') or 0)
        tt = t.get('type')
        pm = t.get('payment_method')
        cur = t.get('currency', 'EUR')
        if tt in ACCT_INCOME_TYPES:
            inc[cur] = round(inc.get(cur, 0) + amt, 2)
        elif tt in ACCT_EXPENSE_TYPES:
            exp[cur] = round(exp.get(cur, 0) + amt, 2)
        if pm in mov:
            if tt in ACCT_INCOME_TYPES:
                mov[pm]['in'] = round(mov[pm]['in'] + amt, 2)
            else:
                mov[pm]['out'] = round(mov[pm]['out'] + amt, 2)
    closing = {
        'cash_mad': round(opening['cash_mad'] + mov['cash_mad']['in'] - mov['cash_mad']['out'], 2),
        'cash_eur': round(opening['cash_eur'] + mov['cash_eur']['in'] - mov['cash_eur']['out'], 2),
    }
    return {
        'date': date_str, 'opening': opening, 'movements': mov, 'closing': closing,
        'income': inc, 'expenses': exp,
        'net': {'MAD': round(inc['MAD'] - exp['MAD'], 2), 'EUR': round(inc['EUR'] - exp['EUR'], 2)},
        'transactions_count': len(day),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }


def acct_today() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')
