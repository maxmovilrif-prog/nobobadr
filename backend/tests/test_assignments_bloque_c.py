"""Tests del BLOQUE C — Operaciones y Logística (asignación por proximidad).

Cobertura:
- GET /api/drivers/nearest devuelve la Abeja más cercana (índice 2dsphere).
- POST /api/orders/{id}/assign-nearest asigna atómicamente al más cercano y registra historial.
- POST /api/orders/{id}/return-to-queue devuelve el pedido y libera a la Abeja.
- GET /api/admin/ops/orders separa pendientes y activos.
- GET /api/admin/assignment-history filtra y lista eventos; export CSV.
- Control de acceso: cliente no puede asignar (403).
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@nubo.com"
ADMIN_PASS = "Admin1234!"
CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASS = "Test1234!"

# Punto de recogida de prueba (Madrid centro)
PICKUP = {"lat": 40.4168, "lng": -3.7038}


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


@pytest.fixture(scope="module")
def near_rider(admin_token):
    """Crea, activa y posiciona un rider disponible cerca del punto de recogida."""
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.post(f"{API}/admin/riders", headers=h,
                      json={"name": f"TEST_C_Rider_{uuid.uuid4().hex[:5]}",
                            "phone": "600999888", "vehicle_type": "motorcycle"})
    assert r.status_code == 200, r.text
    code = r.json()["activation_code"]
    rider_id = r.json()["id"]

    r = requests.post(f"{API}/rider/activate", json={"code": code})
    assert r.status_code == 200, r.text
    rt = r.json()["token"]
    rh = {"Authorization": f"Bearer {rt}"}

    assert requests.patch(f"{API}/rider/availability?is_available=true", headers=rh).status_code == 200
    assert requests.post(f"{API}/rider/location", headers=rh,
                         json={"lat": PICKUP["lat"] + 0.001, "lng": PICKUP["lng"] + 0.001}).status_code == 200
    return {"id": rider_id, "code": code}


@pytest.fixture
def express_order(customer_token):
    payload = {
        "vehicle_type": "moto", "origin_name": "TEST_C_ORIGIN", "origin_lat": PICKUP["lat"],
        "origin_lng": PICKUP["lng"], "destination_name": "TEST_C_DEST",
        "destination_lat": 35.7595, "destination_lng": -5.834, "fee": 50.0, "currency": "EUR",
    }
    r = requests.post(f"{API}/orders/express", headers={"Authorization": f"Bearer {customer_token}"}, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_nearest_finds_available_rider(admin_token, near_rider):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{API}/drivers/nearest?lat={PICKUP['lat']}&lng={PICKUP['lng']}&max_km=50", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    ids = [d["id"] for d in data["drivers"]]
    assert near_rider["id"] in ids
    me = next(d for d in data["drivers"] if d["id"] == near_rider["id"])
    assert me["distance_km"] < 1.0  # ~0.1 km


def test_nearest_requires_admin_or_business(customer_token):
    h = {"Authorization": f"Bearer {customer_token}"}
    r = requests.get(f"{API}/drivers/nearest?lat={PICKUP['lat']}&lng={PICKUP['lng']}", headers=h)
    assert r.status_code == 403


def test_assign_nearest_and_history(admin_token, near_rider, express_order):
    h = {"Authorization": f"Bearer {admin_token}"}
    oid = express_order["id"]

    r = requests.post(f"{API}/orders/{oid}/assign-nearest", headers=h, json={})
    assert r.status_code == 200, r.text
    assigned = r.json()
    assert assigned["driver"]["distance_km"] is not None
    assert assigned["order_id"] == oid

    # Historial registra el evento 'assigned'
    r = requests.get(f"{API}/admin/assignment-history?action=assigned", headers=h)
    assert r.status_code == 200
    events = r.json()["events"]
    assert any(e["order_id"] == oid and e["action"] == "assigned" for e in events)

    # Devolver a la cola
    r = requests.post(f"{API}/orders/{oid}/return-to-queue", headers=h)
    assert r.status_code == 200, r.text

    r = requests.get(f"{API}/admin/assignment-history?action=returned", headers=h)
    assert any(e["order_id"] == oid and e["action"] == "returned" for e in r.json()["events"])


def test_assign_nearest_forbidden_for_customer(customer_token, express_order):
    h = {"Authorization": f"Bearer {customer_token}"}
    r = requests.post(f"{API}/orders/{express_order['id']}/assign-nearest", headers=h, json={})
    assert r.status_code == 403


def test_assign_nearest_404_unknown_order(admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.post(f"{API}/orders/NOPE-{uuid.uuid4().hex[:6]}/assign-nearest", headers=h, json={})
    assert r.status_code == 404


def test_ops_orders_lists_pending(admin_token, express_order):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{API}/admin/ops/orders", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "pending" in data and "active" in data
    assert any(o["id"] == express_order["id"] for o in data["pending"])


def test_ops_orders_requires_admin(customer_token):
    h = {"Authorization": f"Bearer {customer_token}"}
    r = requests.get(f"{API}/admin/ops/orders", headers=h)
    assert r.status_code == 403


def test_history_export_csv(admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{API}/admin/assignment-history/export", headers=h)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "fecha,accion,pedido_id" in r.text.splitlines()[0]
