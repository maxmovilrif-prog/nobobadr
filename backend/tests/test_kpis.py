"""Test del cuadro de mandos (KPIs) del Fundador — GET /api/admin/kpis."""
import os
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
ADMIN_EMAIL, ADMIN_PASS = "badarbox1756@gmail.com", "Admin1234!"
CUSTOMER_EMAIL, CUSTOMER_PASS = "qa_customer@nubo.com", "Test1234!"


def _token(email, pwd):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_kpis_contract():
    h = {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASS)}"}
    r = requests.get(f"{API}/admin/kpis", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("orders_today", "orders_per_day", "revenue_month_eur",
              "delivered_total", "avg_delivery_mins", "top_bees"):
        assert k in d, f"falta {k}"
    # serie de 7 días
    assert len(d["orders_per_day"]) == 7
    for day in d["orders_per_day"]:
        assert {"date", "orders", "delivered"} <= set(day.keys())
    # ranking ordenado desc por entregas
    deliveries = [b["deliveries"] for b in d["top_bees"]]
    assert deliveries == sorted(deliveries, reverse=True)
    assert len(d["top_bees"]) <= 5
    assert isinstance(d["orders_today"], int)
    assert isinstance(d["revenue_month_eur"], (int, float))


def test_kpis_requires_admin():
    h = {"Authorization": f"Bearer {_token(CUSTOMER_EMAIL, CUSTOMER_PASS)}"}
    r = requests.get(f"{API}/admin/kpis", headers=h)
    assert r.status_code == 403
