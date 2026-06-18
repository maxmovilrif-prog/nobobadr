"""Rutas de finanzas (Bloque D): comisiones y pagos por repartidor (Abeja)."""
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel

from core import db, get_current_admin
from accounting import DEFAULT_COMMISSION_RATE, compute_earnings, payout_key

router = APIRouter()


class MarkPaidRequest(BaseModel):
    driver_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    rate: float = DEFAULT_COMMISSION_RATE


async def _summary_rows(start_date, end_date, rate):
    per = await compute_earnings({'status': 'delivered', 'driver_id': {'$ne': None}}, start_date, end_date, rate)
    names = {}
    if per:
        async for u in db.users.find({'id': {'$in': list(per.keys())}}, {'_id': 0, 'id': 1, 'name': 1}):
            names[u['id']] = u.get('name')
    rows = []
    for did, v in per.items():
        rows.append({
            'driver_id': did, 'driver_name': names.get(did, 'N/D'),
            'total_deliveries': v['deliveries'], 'total_revenue': round(v['revenue'], 2),
            'total_earnings': round(v['revenue'] * rate, 2),
        })
    rows.sort(key=lambda r: -r['total_earnings'])
    paid_map = {}
    async for p in db.driver_payouts.find(
        {'period_start': start_date or '', 'period_end': end_date or '', 'status': 'paid'}, {'_id': 0}
    ):
        paid_map[p['driver_id']] = p
    for r in rows:
        p = paid_map.get(r['driver_id'])
        r['payment_status'] = 'paid' if p else 'pending'
        r['paid_at'] = p.get('paid_at') if p else None
    return rows


@router.get("/admin/finances/summary")
async def finances_summary(start_date: Optional[str] = None, end_date: Optional[str] = None,
                           rate: float = DEFAULT_COMMISSION_RATE,
                           current_user: dict = Depends(get_current_admin)):
    """Pagos por repartidor en un periodo (tabla agregada)."""
    rows = await _summary_rows(start_date, end_date, rate)
    totals = {
        'deliveries': sum(r['total_deliveries'] for r in rows),
        'revenue': round(sum(r['total_revenue'] for r in rows), 2),
        'earnings': round(sum(r['total_earnings'] for r in rows), 2),
        'paid_earnings': round(sum(r['total_earnings'] for r in rows if r['payment_status'] == 'paid'), 2),
        'pending_earnings': round(sum(r['total_earnings'] for r in rows if r['payment_status'] == 'pending'), 2),
    }
    return {'period': f"{start_date or 'inicio'} → {end_date or 'hoy'}",
            'rate': rate, 'currency': 'EUR', 'rows': rows, 'totals': totals}


@router.get("/admin/finances/report/{driver_id}")
async def bee_earnings_report(driver_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
                              rate: float = DEFAULT_COMMISSION_RATE,
                              current_user: dict = Depends(get_current_admin)):
    """Reporte de comisiones de un repartidor concreto en un periodo."""
    per = await compute_earnings({'status': 'delivered', 'driver_id': driver_id}, start_date, end_date, rate)
    v = per.get(driver_id, {'deliveries': 0, 'revenue': 0.0})
    driver = await db.users.find_one({'id': driver_id}, {'_id': 0, 'id': 1, 'name': 1})
    return {
        'driver_id': driver_id, 'driver_name': driver.get('name') if driver else 'N/D',
        'period': f"{start_date or 'inicio'} → {end_date or 'hoy'}",
        'total_deliveries': v['deliveries'], 'total_revenue': round(v['revenue'], 2),
        'total_earnings': round(v['revenue'] * rate, 2), 'rate': rate, 'currency': 'EUR',
    }


@router.get("/admin/finances/export")
async def finances_export(start_date: Optional[str] = None, end_date: Optional[str] = None,
                          rate: float = DEFAULT_COMMISSION_RATE,
                          current_user: dict = Depends(get_current_admin)):
    """Exporta los pagos por repartidor a CSV (admin)."""
    rows = await _summary_rows(start_date, end_date, rate)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['repartidor', 'repartidor_id', 'entregas', 'ingresos_eur', 'comision_eur', 'tasa', 'estado_pago'])
    for r in rows:
        writer.writerow([r['driver_name'], r['driver_id'], r['total_deliveries'],
                         r['total_revenue'], r['total_earnings'], rate,
                         'Pagado' if r.get('payment_status') == 'paid' else 'Pendiente'])
    writer.writerow([])
    writer.writerow(['TOTAL', '', sum(r['total_deliveries'] for r in rows),
                     round(sum(r['total_revenue'] for r in rows), 2),
                     round(sum(r['total_earnings'] for r in rows), 2), rate])
    filename = f"pagos_repartidores_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
    return Response(content=buf.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@router.post("/admin/finances/mark-paid")
async def mark_driver_paid(req: MarkPaidRequest, current_user: dict = Depends(get_current_admin)):
    """Marca como PAGADO el ciclo de comisiones de un repartidor en el periodo (recalcula en servidor)."""
    per = await compute_earnings({'status': 'delivered', 'driver_id': req.driver_id},
                                 req.start_date, req.end_date, req.rate)
    v = per.get(req.driver_id, {'deliveries': 0, 'revenue': 0.0})
    key = payout_key(req.driver_id, req.start_date, req.end_date)
    now = datetime.now(timezone.utc).isoformat()
    snapshot = {
        **key, 'status': 'paid', 'rate': req.rate,
        'deliveries': v['deliveries'], 'revenue': round(v['revenue'], 2),
        'amount': round(v['revenue'] * req.rate, 2),
        'paid_at': now, 'marked_by': current_user.get('id'),
        'marked_by_name': current_user.get('name'), 'updated_at': now,
    }
    await db.driver_payouts.update_one(
        key, {'$set': snapshot, '$setOnInsert': {'id': str(uuid.uuid4()), 'created_at': now}}, upsert=True
    )
    return {'message': 'Pago registrado', **snapshot}


@router.post("/admin/finances/mark-pending")
async def mark_driver_pending(req: MarkPaidRequest, current_user: dict = Depends(get_current_admin)):
    """Revierte el pago: el ciclo vuelve a PENDIENTE."""
    await db.driver_payouts.delete_one(payout_key(req.driver_id, req.start_date, req.end_date))
    return {'message': 'Marcado como pendiente', 'driver_id': req.driver_id, 'status': 'pending'}


@router.get("/admin/finances/payouts")
async def list_payouts(driver_id: Optional[str] = None, limit: int = 200,
                       current_user: dict = Depends(get_current_admin)):
    """Historial de pagos registrados (instantáneas de ciclos cerrados)."""
    q = {'status': 'paid'}
    if driver_id:
        q['driver_id'] = driver_id
    payouts = await db.driver_payouts.find(q, {'_id': 0}).sort('paid_at', -1).to_list(max(1, min(limit, 1000)))
    ids = list({p['driver_id'] for p in payouts})
    names = {}
    if ids:
        async for u in db.users.find({'id': {'$in': ids}}, {'_id': 0, 'id': 1, 'name': 1}):
            names[u['id']] = u.get('name')
    for p in payouts:
        p['driver_name'] = names.get(p['driver_id'], 'N/D')
    return {'count': len(payouts), 'payouts': payouts}
