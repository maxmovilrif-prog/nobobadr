"""Test del despacho automático por proximidad (auto_assign_order).

Al crear un pedido exprés, si hay una Abeja disponible y cercana al origen,
debe asignarse automáticamente (sin intervención del admin) y registrarse en el
historial con motivo 'auto_dispatch'.
"""
import os
import uuid
import random
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL, ADMIN_PASS = "admin@nubo.com", "Admin1234!"
CUSTOMER_EMAIL, CUSTOMER_PASS = "qa_customer@nubo.com", "Test1234!"

# Punto único y aislado aleatorio para este test (evita colisión con riders previos)
PICKUP = {"lat": round(random.uniform(-55, 55), 4), "lng": round(random.uniform(-150, 150), 4)}


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


def _spawn_near_rider(admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.post(f"{API}/admin/riders", headers=h,
                      json={"name": f"TEST_AUTO_{uuid.uuid4().hex[:5]}",
                            "phone": "600000111", "vehicle_type": "car"})
    assert r.status_code == 200, r.text
    code, rid = r.json()["activation_code"], r.json()["id"]
    rt = requests.post(f"{API}/rider/activate", json={"code": code}).json()["token"]
    rh = {"Authorization": f"Bearer {rt}"}
    requests.patch(f"{API}/rider/availability?is_available=true", headers=rh)
    requests.post(f"{API}/rider/location", headers=rh,
                  json={"lat": PICKUP["lat"] + 0.0008, "lng": PICKUP["lng"] + 0.0008})
    return rid


def test_express_order_auto_dispatches_to_nearest(admin_token, customer_token):
    rid = _spawn_near_rider(admin_token)

    payload = {
        "vehicle_type": "car", "origin_name": "TEST_AUTO_ORIGIN",
        "origin_lat": PICKUP["lat"], "origin_lng": PICKUP["lng"],
        "destination_name": "TEST_AUTO_DEST", "destination_lat": 36.72, "destination_lng": -4.42,
        "fee": 60.0, "currency": "EUR",
    }
    r = requests.post(f"{API}/orders/express",
                      headers={"Authorization": f"Bearer {customer_token}"}, json=payload)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]

    # El pedido debe estar ya asignado automáticamente (status accepted, driver_id = nuestro rider)
    r = requests.get(f"{API}/public/orders/{oid}/tracking")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "accepted", data
    assert data["driver_name"] is not None

    # El historial registra el evento automático
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{API}/admin/assignment-history?driver_id={rid}", headers=h)
    assert r.status_code == 200
    events = r.json()["events"]
    assert any(e["order_id"] == oid and e["reason"] == "auto_dispatch" for e in events), events
