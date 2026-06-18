"""Rutas de contabilidad (Bloque D): libro de transacciones, caja MAD/EUR, nóminas y arqueo."""
import csv
import io
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field

from core import db, get_current_admin
from accounting import (
    ACCT_CURRENCIES, ACCT_INCOME_TYPES, ACCT_EXPENSE_TYPES, ACCT_MAD_TO_EUR, DEFAULT_COMMISSION_RATE,
    acct_create_txn, acct_date_query, compute_cash_balance, compute_daily_closing, acct_today,
    compute_earnings,
)

router = APIRouter()


class AcctTxnCreate(BaseModel):
    type: str
    amount: float = Field(gt=0)
    currency: str
    payment_method: str
    description: str = Field(min_length=2)
    reference_id: Optional[str] = None
    courier_id: Optional[str] = None
    customer_id: Optional[str] = None


class AcctCashMovement(BaseModel):
    amount: float = Field(gt=0)
    currency: str
    description: str = Field(min_length=2)


@router.get("/accounting/transactions")
async def acct_list_transactions(
    page: int = 1, per_page: int = 30,
    type: Optional[str] = None, currency: Optional[str] = None,
    payment_method: Optional[str] = None, courier_id: Optional[str] = None,
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_admin),
):
    """Libro de transacciones con filtros y paginación."""
    page = max(1, page)
    per_page = max(1, min(per_page, 200))
    q = acct_date_query(date_from, date_to)
    if type:
        q['type'] = type
    if currency:
        q['currency'] = currency
    if payment_method:
        q['payment_method'] = payment_method
    if courier_id:
        q['courier_id'] = courier_id
    total = await db.transactions.count_documents(q)
    rows = await db.transactions.find(q, {'_id': 0}).sort('created_at', -1) \
        .skip((page - 1) * per_page).limit(per_page).to_list(per_page)
    return {'total': total, 'page': page, 'per_page': per_page,
            'pages': math.ceil(total / per_page) if total else 0, 'data': rows}


@router.post("/accounting/transactions")
async def acct_create_transaction(payload: AcctTxnCreate, current_user: dict = Depends(get_current_admin)):
    """Registra una transacción contable manual (ingreso, ajuste, pago, devolución…)."""
    return await acct_create_txn(
        current_user, type_=payload.type, amount=payload.amount, currency=payload.currency,
        method=payload.payment_method, description=payload.description,
        reference_id=payload.reference_id, courier_id=payload.courier_id,
        customer_id=payload.customer_id, action='CREATE_TRANSACTION',
    )


@router.get("/accounting/transactions/summary")
async def acct_transactions_summary(date_from: Optional[str] = None, date_to: Optional[str] = None,
                                    current_user: dict = Depends(get_current_admin)):
    """Resumen del periodo: ingresos, gastos y balance neto por moneda + desglose por tipo/método."""
    q = acct_date_query(date_from, date_to)
    txns = await db.transactions.find(q, {'_id': 0}).to_list(50000)
    inc = {'MAD': 0.0, 'EUR': 0.0}
    exp = {'MAD': 0.0, 'EUR': 0.0}
    by_type, by_method = {}, {}
    for t in txns:
        cur = t.get('currency', 'EUR')
        amt = float(t.get('amount') or 0)
        tt = t.get('type')
        pm = t.get('payment_method', 'otro')
        by_type[tt] = round(by_type.get(tt, 0) + amt, 2)
        by_method[pm] = round(by_method.get(pm, 0) + amt, 2)
        if tt in ACCT_INCOME_TYPES:
            inc[cur] = round(inc.get(cur, 0) + amt, 2)
        elif tt in ACCT_EXPENSE_TYPES:
            exp[cur] = round(exp.get(cur, 0) + amt, 2)
    return {
        'period': {'from': date_from, 'to': date_to}, 'count': len(txns),
        'total_income': inc, 'total_expenses': exp,
        'net_balance': {'MAD': round(inc['MAD'] - exp['MAD'], 2), 'EUR': round(inc['EUR'] - exp['EUR'], 2)},
        'breakdown_by_type': by_type, 'breakdown_by_method': by_method,
    }


@router.get("/accounting/cash/balance")
async def acct_cash_balance(current_user: dict = Depends(get_current_admin)):
    """Saldo de caja en efectivo (MAD y EUR)."""
    return await compute_cash_balance()


@router.post("/accounting/cash/in")
async def acct_cash_in(payload: AcctCashMovement, current_user: dict = Depends(get_current_admin)):
    """Registra una entrada de efectivo en caja (MAD o EUR)."""
    if payload.currency not in ACCT_CURRENCIES:
        raise HTTPException(status_code=400, detail="Moneda inválida (MAD o EUR)")
    method = 'cash_mad' if payload.currency == 'MAD' else 'cash_eur'
    return await acct_create_txn(
        current_user, type_='cash_in', amount=payload.amount, currency=payload.currency,
        method=method, description=payload.description, action='CASH_IN',
    )


@router.post("/accounting/cash/out")
async def acct_cash_out(payload: AcctCashMovement, current_user: dict = Depends(get_current_admin)):
    """Registra una salida de efectivo de caja, validando saldo suficiente."""
    if payload.currency not in ACCT_CURRENCIES:
        raise HTTPException(status_code=400, detail="Moneda inválida (MAD o EUR)")
    method = 'cash_mad' if payload.currency == 'MAD' else 'cash_eur'
    balance = await compute_cash_balance()
    available = balance['cash_mad']['balance'] if payload.currency == 'MAD' else balance['cash_eur']['balance']
    if payload.amount > available:
        raise HTTPException(status_code=400,
                            detail=f"Saldo insuficiente en caja {payload.currency}: disponible {available}, solicitado {payload.amount}")
    return await acct_create_txn(
        current_user, type_='cash_out', amount=payload.amount, currency=payload.currency,
        method=method, description=payload.description, action='CASH_OUT',
    )


@router.get("/accounting/payroll")
async def acct_payroll(start_date: Optional[str] = None, end_date: Optional[str] = None,
                       rate: float = DEFAULT_COMMISSION_RATE,
                       current_user: dict = Depends(get_current_admin)):
    """Nóminas de couriers (Abejas) en un periodo: entregas, comisión EUR y equivalente MAD."""
    per = await compute_earnings({'status': 'delivered', 'driver_id': {'$ne': None}}, start_date, end_date, rate)
    names = {}
    if per:
        async for u in db.users.find({'id': {'$in': list(per.keys())}}, {'_id': 0, 'id': 1, 'name': 1}):
            names[u['id']] = u.get('name')
    paid_map = {}
    async for p in db.driver_payouts.find(
        {'period_start': start_date or '', 'period_end': end_date or '', 'status': 'paid'}, {'_id': 0}
    ):
        paid_map[p['driver_id']] = p
    eur_per_mad = round(1 / ACCT_MAD_TO_EUR, 4)
    entries = []
    for did, v in per.items():
        earnings_eur = round(v['revenue'] * rate, 2)
        p = paid_map.get(did)
        entries.append({
            'courier_id': did, 'courier_name': names.get(did, 'N/D'),
            'total_deliveries': v['deliveries'], 'gross_revenue_eur': round(v['revenue'], 2),
            'net_amount_eur': earnings_eur, 'net_amount_mad': round(earnings_eur * eur_per_mad, 2),
            'is_paid': bool(p), 'paid_at': p.get('paid_at') if p else None,
        })
    entries.sort(key=lambda r: -r['net_amount_eur'])
    total_eur = round(sum(e['net_amount_eur'] for e in entries), 2)
    return {
        'period': {'from': start_date, 'to': end_date}, 'rate': rate, 'entries': entries,
        'total_net_eur': total_eur, 'total_net_mad': round(total_eur * eur_per_mad, 2),
        'paid_net_eur': round(sum(e['net_amount_eur'] for e in entries if e['is_paid']), 2),
        'pending_net_eur': round(sum(e['net_amount_eur'] for e in entries if not e['is_paid']), 2),
    }


class AcctPayrollPay(BaseModel):
    courier_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    rate: float = DEFAULT_COMMISSION_RATE


@router.post("/accounting/payroll/pay")
async def acct_payroll_pay(req: AcctPayrollPay, current_user: dict = Depends(get_current_admin)):
    """Marca como pagada la nómina de un courier y la registra como 'payout' en el libro contable."""
    per = await compute_earnings({'status': 'delivered', 'driver_id': req.courier_id},
                                 req.start_date, req.end_date, req.rate)
    v = per.get(req.courier_id, {'deliveries': 0, 'revenue': 0.0})
    earnings_eur = round(v['revenue'] * req.rate, 2)
    if earnings_eur <= 0:
        raise HTTPException(status_code=400, detail="No hay comisiones que pagar en el periodo")
    key = {'driver_id': req.courier_id, 'period_start': req.start_date or '', 'period_end': req.end_date or ''}
    existing = await db.driver_payouts.find_one(key, {'_id': 0, 'status': 1})
    if existing and existing.get('status') == 'paid':
        raise HTTPException(status_code=400, detail="Esta nómina ya está pagada")
    now = datetime.now(timezone.utc).isoformat()
    await db.driver_payouts.update_one(
        key,
        {'$set': {**key, 'status': 'paid', 'rate': req.rate, 'deliveries': v['deliveries'],
                  'revenue': round(v['revenue'], 2), 'amount': earnings_eur, 'paid_at': now,
                  'marked_by': current_user.get('id'), 'marked_by_name': current_user.get('name'),
                  'updated_at': now},
         '$setOnInsert': {'id': str(uuid.uuid4()), 'created_at': now}},
        upsert=True,
    )
    driver = await db.users.find_one({'id': req.courier_id}, {'_id': 0, 'name': 1})
    await acct_create_txn(
        current_user, type_='payout', amount=earnings_eur, currency='EUR',
        method='bank_transfer', description=f"Nómina {driver.get('name') if driver else req.courier_id}",
        reference_id=req.courier_id, courier_id=req.courier_id, action='PAY_PAYROLL',
    )
    return {'message': 'Nómina pagada', 'courier_id': req.courier_id, 'amount_eur': earnings_eur}


@router.get("/accounting/export/transactions")
async def acct_export_transactions(date_from: Optional[str] = None, date_to: Optional[str] = None,
                                   current_user: dict = Depends(get_current_admin)):
    """Exporta las transacciones del periodo a CSV (admin)."""
    q = acct_date_query(date_from, date_to)
    rows = await db.transactions.find(q, {'_id': 0}).sort('created_at', -1).to_list(50000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['fecha', 'tipo', 'importe', 'moneda', 'importe_eur', 'metodo', 'descripcion', 'referencia', 'creado_por'])
    for t in rows:
        w.writerow([t.get('created_at', ''), t.get('type', ''), t.get('amount', 0), t.get('currency', ''),
                    t.get('amount_eur', 0), t.get('payment_method', ''), t.get('description', ''),
                    t.get('reference_id', '') or '', t.get('created_by_name', '') or ''])
    filename = f"transacciones_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
    return Response(content=buf.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@router.get("/accounting/cash/daily-closing")
async def acct_daily_closing(date: Optional[str] = None, current_user: dict = Depends(get_current_admin)):
    """Arqueo de caja del día indicado (por defecto hoy)."""
    return await compute_daily_closing(date or acct_today())


@router.get("/accounting/cash/closing/export")
async def acct_daily_closing_export(date: Optional[str] = None, format: str = 'pdf',
                                    current_user: dict = Depends(get_current_admin)):
    """Exporta el arqueo de caja del día a CSV o PDF (admin)."""
    date_str = date or acct_today()
    data = await compute_daily_closing(date_str)

    if format == 'csv':
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['Arqueo de caja Nubo Express', date_str])
        w.writerow([])
        w.writerow(['Concepto', 'MAD', 'EUR'])
        w.writerow(['Saldo inicial efectivo', data['opening']['cash_mad'], data['opening']['cash_eur']])
        w.writerow(['Entradas de caja', data['movements']['cash_mad']['in'], data['movements']['cash_eur']['in']])
        w.writerow(['Salidas de caja', data['movements']['cash_mad']['out'], data['movements']['cash_eur']['out']])
        w.writerow(['Saldo final esperado', data['closing']['cash_mad'], data['closing']['cash_eur']])
        w.writerow([])
        w.writerow(['Ingresos del día', data['income']['MAD'], data['income']['EUR']])
        w.writerow(['Gastos del día', data['expenses']['MAD'], data['expenses']['EUR']])
        w.writerow(['Balance neto del día', data['net']['MAD'], data['net']['EUR']])
        w.writerow([])
        w.writerow(['Nº de transacciones', data['transactions_count']])
        w.writerow(['Generado', data['generated_at']])
        return Response(content=buf.getvalue(), media_type='text/csv',
                        headers={'Content-Disposition': f'attachment; filename="arqueo_{date_str}.csv"'})

    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(16, 122, 87)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 14, 'Nubo Express - Arqueo de caja', new_x='LMARGIN', new_y='NEXT', fill=True)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, f"Fecha: {date_str}", new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    def section(title):
        pdf.set_text_color(16, 122, 87)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 9, title, new_x='LMARGIN', new_y='NEXT')
        pdf.set_text_color(40, 40, 40)
        pdf.set_font('Helvetica', '', 11)

    def row(label, mad, eur, bold=False):
        pdf.set_font('Helvetica', 'B' if bold else '', 11)
        pdf.cell(95, 8, str(label), border='B')
        pdf.cell(45, 8, f"{mad:,.2f} MAD", border='B', align='R')
        pdf.cell(45, 8, f"{eur:,.2f} EUR", border='B', align='R', new_x='LMARGIN', new_y='NEXT')

    section('Efectivo en caja')
    row('Saldo inicial', data['opening']['cash_mad'], data['opening']['cash_eur'])
    row('(+) Entradas de caja', data['movements']['cash_mad']['in'], data['movements']['cash_eur']['in'])
    row('(-) Salidas de caja', data['movements']['cash_mad']['out'], data['movements']['cash_eur']['out'])
    row('Saldo final esperado', data['closing']['cash_mad'], data['closing']['cash_eur'], bold=True)
    pdf.ln(5)
    section('Resultado del dia')
    row('Ingresos del dia', data['income']['MAD'], data['income']['EUR'])
    row('Gastos del dia', data['expenses']['MAD'], data['expenses']['EUR'])
    row('Balance neto del dia', data['net']['MAD'], data['net']['EUR'], bold=True)
    pdf.ln(6)
    pdf.set_text_color(120, 120, 120)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, f"Transacciones del dia: {data['transactions_count']}", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f"Generado: {data['generated_at']}  |  Por: {current_user.get('name', 'Admin')}", new_x='LMARGIN', new_y='NEXT')

    pdf_bytes = bytes(pdf.output())
    return Response(content=pdf_bytes, media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="arqueo_{date_str}.pdf"'})
