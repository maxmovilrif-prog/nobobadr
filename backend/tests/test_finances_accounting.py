"""Tests del BLOQUE D — Contabilidad y Finanzas.

Cobertura:
- Caja: cash_in/cash_out, validación de saldo insuficiente, balance y arqueo diario.
- Libro: transacción manual, resumen por moneda, export CSV.
- Flujo nómina: entrega de pedido → ingreso automático (idempotente) → comisión del repartidor
  en finances/summary y payroll → mark-paid registra un 'payout' en el libro.
- Control de acceso: cliente recibe 403 en endpoints de contabilidad/finanzas.
"""
import os
import uuid
import random
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL, ADMIN_PASS = "badarbox1756@gmail.com", "Admin1234!"
CUSTOMER_EMAIL, CUSTOMER_PASS = "qa_customer@nubo.com", "Test1234!"

PICKUP = {"lat": round(random.uniform(-55, 55), 4), "lng": round(random.uniform(-150, 150), 4)}  # aislado/aleatorio


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def customer_token():
    r = requests.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASS})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _ah(t):
    return {"Authorization": f"Bearer {t}"}


# ---------- Caja ----------

def test_cash_in_out_and_balance(admin_token):
    h = _ah(admin_token)
    r = requests.post(f"{API}/accounting/cash/in", headers=h,
                      json={"amount": 300, "currency": "EUR", "description": "TEST_D apertura"})
    assert r.status_code == 200, r.text
    assert r.json()["type"] == "cash_in" and r.json()["amount_eur"] == 300.0

    r = requests.get(f"{API}/accounting/cash/balance", headers=h)
    assert r.status_code == 200
    assert r.json()["cash_eur"]["balance"] >= 300.0

    # salida válida
    r = requests.post(f"{API}/accounting/cash/out", headers=h,
                      json={"amount": 50, "currency": "EUR", "description": "TEST_D gasto"})
    assert r.status_code == 200, r.text

    # salida con saldo insuficiente
    r = requests.post(f"{API}/accounting/cash/out", headers=h,
                      json={"amount": 9_999_999, "currency": "EUR", "description": "TEST_D over"})
    assert r.status_code == 400


def test_daily_closing(admin_token):
    r = requests.get(f"{API}/accounting/cash/daily-closing", headers=_ah(admin_token))
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("opening", "movements", "closing", "income", "expenses", "net"):
        assert k in data


def test_manual_transaction_and_summary(admin_token):
    h = _ah(admin_token)
    r = requests.post(f"{API}/accounting/transactions", headers=h,
                      json={"type": "adjustment", "amount": 12.5, "currency": "EUR",
                            "payment_method": "bank_transfer", "description": "TEST_D ajuste"})
    assert r.status_code == 200, r.text

    r = requests.get(f"{API}/accounting/transactions?type=adjustment", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = requests.get(f"{API}/accounting/transactions/summary", headers=h)
    assert r.status_code == 200
    assert "net_balance" in r.json()


def test_export_transactions_csv(admin_token):
    r = requests.get(f"{API}/accounting/export/transactions", headers=_ah(admin_token))
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "fecha,tipo,importe" in r.text.splitlines()[0]


def test_invalid_transaction_type_rejected(admin_token):
    r = requests.post(f"{API}/accounting/transactions", headers=_ah(admin_token),
                      json={"type": "nope", "amount": 10, "currency": "EUR",
                            "payment_method": "stripe", "description": "tipo invalido"})
    assert r.status_code == 400


# ---------- Flujo nómina: entrega -> ingreso -> comisión -> pago ----------

def test_delivery_income_payroll_and_payout(admin_token, customer_token):
    ah = _ah(admin_token)

    # 1. rider disponible y cercano
    r = requests.post(f"{API}/admin/riders", headers=ah,
                      json={"name": f"TEST_D_{uuid.uuid4().hex[:5]}", "phone": "600222333", "vehicle_type": "car"})
    assert r.status_code == 200, r.text
    code, rid = r.json()["activation_code"], r.json()["id"]
    rt = requests.post(f"{API}/rider/activate", json={"code": code}).json()["token"]
    rh = _ah(rt)
    requests.patch(f"{API}/rider/availability?is_available=true", headers=rh)
    requests.post(f"{API}/rider/location", headers=rh,
                  json={"lat": PICKUP["lat"] + 0.0007, "lng": PICKUP["lng"] + 0.0007})

    # 2. pedido express (auto-asignado al rider)
    payload = {
        "vehicle_type": "car", "origin_name": "TEST_D_ORIGIN", "origin_lat": PICKUP["lat"],
        "origin_lng": PICKUP["lng"], "destination_name": "TEST_D_DEST",
        "destination_lat": 41.0, "destination_lng": 2.0, "fee": 100.0, "currency": "EUR",
    }
    r = requests.post(f"{API}/orders/express", headers=_ah(customer_token), json=payload)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]

    # confirmar que se auto-asignó al rider
    tr = requests.get(f"{API}/public/orders/{oid}/tracking").json()
    assert tr["status"] == "accepted", tr

    # 3. entregar el pedido (registra ingreso automático)
    r = requests.patch(f"{API}/orders/{oid}/status", headers=ah, json={"status": "delivered"})
    assert r.status_code == 200, r.text

    # 4. el ingreso aparece en el libro (idempotente: una sola transacción income)
    r = requests.get(f"{API}/accounting/transactions?type=income", headers=ah)
    incomes = [t for t in r.json()["data"] if t.get("reference_id") == oid]
    assert len(incomes) == 1, incomes
    assert incomes[0]["amount"] == 100.0

    # entregar de nuevo no duplica el ingreso
    requests.patch(f"{API}/orders/{oid}/status", headers=ah, json={"status": "delivered"})
    r = requests.get(f"{API}/accounting/transactions?type=income", headers=ah)
    assert len([t for t in r.json()["data"] if t.get("reference_id") == oid]) == 1

    # 5. comisión del repartidor en finances/summary (10% de 100 = 10€)
    r = requests.get(f"{API}/admin/finances/summary", headers=ah)
    rows = r.json()["rows"]
    me = next((x for x in rows if x["driver_id"] == rid), None)
    assert me is not None, rows
    assert me["total_earnings"] == 10.0
    assert me["payment_status"] == "pending"

    # payroll equivalente
    r = requests.get(f"{API}/accounting/payroll", headers=ah)
    entry = next((e for e in r.json()["entries"] if e["courier_id"] == rid), None)
    assert entry and entry["net_amount_eur"] == 10.0 and entry["is_paid"] is False

    # 6. pagar nómina -> crea transacción 'payout' y marca pagado
    r = requests.post(f"{API}/accounting/payroll/pay", headers=ah, json={"courier_id": rid})
    assert r.status_code == 200, r.text
    assert r.json()["amount_eur"] == 10.0

    r = requests.get(f"{API}/accounting/transactions?type=payout&courier_id={rid}", headers=ah)
    assert any(t.get("courier_id") == rid for t in r.json()["data"])

    r = requests.get(f"{API}/admin/finances/summary", headers=ah)
    me = next(x for x in r.json()["rows"] if x["driver_id"] == rid)
    assert me["payment_status"] == "paid"

    # pagar de nuevo el mismo ciclo -> 400
    r = requests.post(f"{API}/accounting/payroll/pay", headers=ah, json={"courier_id": rid})
    assert r.status_code == 400


# ---------- Control de acceso ----------

@pytest.mark.parametrize("path", [
    "/accounting/transactions", "/accounting/cash/balance",
    "/accounting/payroll", "/admin/finances/summary",
])
def test_accounting_requires_admin(customer_token, path):
    r = requests.get(f"{API}{path}", headers=_ah(customer_token))
    assert r.status_code == 403
