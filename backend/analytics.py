"""Analytics router: profitability by rider & city + COD cash audit."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from typing import Optional

from database import db
from auth import require_roles

router = APIRouter(prefix="/api/analytics")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _month_start() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-01")


def _empty_money():
    return {"MAD": 0.0, "EUR": 0.0}


def _add(bucket: dict, currency: str, amount: float):
    cur = currency if currency in ("MAD", "EUR") else "MAD"
    bucket[cur] = round(bucket.get(cur, 0.0) + amount, 2)


@router.get("/profitability")
async def profitability(
    start: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    user: dict = Depends(require_roles("admin", "dispatcher")),
):
    start = start or _month_start()
    end = end or _today()

    orders = await db.orders.find(
        {"created_at": {"$gte": start, "$lte": end + "T23:59:59"}},
        {"_id": 0},
    ).to_list(5000)

    # Fallback: some created_at are full ISO; filter by date prefix to be safe
    orders = [o for o in orders if (o.get("created_at", "")[:10] >= start and o.get("created_at", "")[:10] <= end)]

    riders = await db.users.find({"role": "rider"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    rider_name = {r["id"]: r.get("name", "—") for r in riders}

    by_rider = {}
    by_city = {}
    totals = {
        "orders": 0, "delivered": 0, "cancelled": 0,
        "revenue": _empty_money(), "cod_cash": _empty_money(),
    }

    def rider_bucket(rid):
        if rid not in by_rider:
            by_rider[rid] = {
                "rider_id": rid, "rider_name": rider_name.get(rid, "Sin asignar"),
                "orders": 0, "delivered": 0, "cancelled": 0, "active": 0,
                "revenue": _empty_money(), "cod_cash": _empty_money(),
                "distance_sum": 0.0, "distance_count": 0,
            }
        return by_rider[rid]

    def city_bucket(city):
        key = city or "Sin ciudad"
        if key not in by_city:
            by_city[key] = {
                "city": key, "orders": 0, "delivered": 0,
                "revenue": _empty_money(), "cod_cash": _empty_money(),
            }
        return by_city[key]

    for o in orders:
        cur = o.get("currency", "MAD")
        amount = float(o.get("amount", 0) or 0)
        status = o.get("status")
        rid = o.get("assigned_rider_id") or "unassigned"
        rb = rider_bucket(rid)
        cb = city_bucket(o.get("city"))

        totals["orders"] += 1
        rb["orders"] += 1
        cb["orders"] += 1

        if o.get("distance_km") is not None:
            rb["distance_sum"] += float(o["distance_km"])
            rb["distance_count"] += 1

        if status == "delivered":
            totals["delivered"] += 1
            rb["delivered"] += 1
            cb["delivered"] += 1
            _add(totals["revenue"], cur, amount)
            _add(rb["revenue"], cur, amount)
            _add(cb["revenue"], cur, amount)
            if o.get("payment_method") == "cod_cash":
                _add(totals["cod_cash"], cur, amount)
                _add(rb["cod_cash"], cur, amount)
                _add(cb["cod_cash"], cur, amount)
        elif status == "cancelled":
            totals["cancelled"] += 1
            rb["cancelled"] += 1
        elif status in ("assigned", "picked_up", "in_transit"):
            rb["active"] += 1

    # finalize riders
    rider_rows = []
    for rb in by_rider.values():
        rb["avg_distance_km"] = round(rb["distance_sum"] / rb["distance_count"], 2) if rb["distance_count"] else None
        rb["delivery_rate"] = round(rb["delivered"] / rb["orders"] * 100, 1) if rb["orders"] else 0.0
        rb.pop("distance_sum", None)
        rb.pop("distance_count", None)
        rider_rows.append(rb)
    rider_rows.sort(key=lambda r: r["cod_cash"]["MAD"] + r["cod_cash"]["EUR"] + r["revenue"]["MAD"] + r["revenue"]["EUR"], reverse=True)

    city_rows = sorted(
        by_city.values(),
        key=lambda c: c["revenue"]["MAD"] + c["revenue"]["EUR"],
        reverse=True,
    )

    # ----- COD cash audit: expected (from delivered cod orders) vs registered (cash entradas) -----
    cod_expected = _empty_money()
    for o in orders:
        if o.get("status") == "delivered" and o.get("payment_method") == "cod_cash":
            _add(cod_expected, o.get("currency", "MAD"), float(o.get("amount", 0) or 0))

    cash_entries = await db.cash_movements.find(
        {"date": {"$gte": start, "$lte": end}, "method": "efectivo",
         "order_id": {"$ne": None}},
        {"_id": 0},
    ).to_list(5000)
    cod_registered = _empty_money()
    for m in cash_entries:
        _add(cod_registered, m.get("currency", "MAD"), float(m.get("amount", 0) or 0))

    audit = []
    for cur in ("MAD", "EUR"):
        exp = round(cod_expected.get(cur, 0.0), 2)
        reg = round(cod_registered.get(cur, 0.0), 2)
        diff = round(reg - exp, 2)
        audit.append({
            "currency": cur,
            "cod_expected": exp,
            "cod_registered": reg,
            "diferencia": diff,
            "estado": "ok" if abs(diff) < 0.005 else ("fuga" if diff < 0 else "exceso"),
        })

    return {
        "range": {"start": start, "end": end},
        "totals": totals,
        "by_rider": rider_rows,
        "by_city": city_rows,
        "cash_audit": audit,
    }
