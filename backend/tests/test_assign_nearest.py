"""Backend tests for the 'Assign Nearest Driver' admin feature.

Covers:
- GET /api/admin/pending-orders (admin token returns list with business_name)
- POST /api/orders/{id}/assign-nearest (admin)
- Calling assign-nearest twice on the same order returns 400
- RBAC: pending-orders and assign-nearest reject non-admin/non-business (403)
- GET /api/drivers/nearest geospatial correctness (Madrid -> Abeja Madrid first ~0km,
  Sevilla with max_km=100 -> only nearby drivers)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "control@nuboexpress.com"
ADMIN_PASSWORD = "Fn6FcMveVf%--1o-"
ADMIN_SECRET = "NUBO-84D2-C159-E3CF"

CUSTOMER_EMAIL = "cliente@nubotest.com"
CUSTOMER_PASSWORD = "Cliente123!"

DRIVER_EMAIL = "bee.madrid@nuboexpress.com"
DRIVER_PASSWORD = "Bee123!"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(
        f"{API}/admin-auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "secret_code": ADMIN_SECRET},
        timeout=15,
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def customer_token(session):
    r = session.post(
        f"{API}/auth/login",
        json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Customer login failed: {r.status_code} {r.text}")
    return r.json()["token"]


@pytest.fixture(scope="session")
def driver_token(session):
    r = session.post(
        f"{API}/auth/login",
        json={"email": DRIVER_EMAIL, "password": DRIVER_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Driver login failed: {r.status_code} {r.text}")
    return r.json()["token"]


# --------- pending-orders ---------
class TestPendingOrders:
    def test_admin_can_list_pending_orders(self, session, admin_token):
        r = session.get(
            f"{API}/admin/pending-orders",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "count" in data and "orders" in data
        assert isinstance(data["orders"], list)
        assert data["count"] == len(data["orders"])
        # Expect at least the 3 seeded demo pending orders (per task context)
        assert data["count"] >= 1, "Expected at least 1 pending order seeded"
        # Validate shape of first order
        o = data["orders"][0]
        for key in ("id", "business_name", "delivery_address", "total_amount", "status", "created_at"):
            assert key in o, f"Missing key {key} in pending order: {o}"
        assert "_id" not in o

    def test_pending_orders_rejects_unauth(self, session):
        r = session.get(f"{API}/admin/pending-orders", timeout=15)
        assert r.status_code in (401, 403), r.text

    def test_pending_orders_rejects_customer(self, session, customer_token):
        r = session.get(
            f"{API}/admin/pending-orders",
            headers={"Authorization": f"Bearer {customer_token}"},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_pending_orders_rejects_driver(self, session, driver_token):
        r = session.get(
            f"{API}/admin/pending-orders",
            headers={"Authorization": f"Bearer {driver_token}"},
            timeout=15,
        )
        assert r.status_code == 403, r.text


# --------- drivers/nearest geospatial ---------
class TestDriversNearest:
    def test_nearest_from_madrid_returns_abeja_madrid_first(self, session, admin_token):
        # Madrid center
        r = session.get(
            f"{API}/drivers/nearest",
            params={"lat": 40.4168, "lng": -3.7038, "limit": 5},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["count"] >= 1
        first = data["drivers"][0]
        # First should be Abeja Madrid (or very close to 0 km)
        assert "Madrid" in first["name"], f"Expected Abeja Madrid first, got {first}"
        assert first["distance_km"] < 5.0, f"Expected ~0km, got {first['distance_km']}"
        # Sorted by distance ascending
        dists = [d["distance_km"] for d in data["drivers"]]
        assert dists == sorted(dists), f"Drivers not sorted by distance: {dists}"

    def test_nearest_sevilla_max_km_100(self, session, admin_token):
        # Sevilla center, only return drivers within 100km
        r = session.get(
            f"{API}/drivers/nearest",
            params={"lat": 37.3891, "lng": -5.9845, "max_km": 100, "limit": 10},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        for d in data["drivers"]:
            assert d["distance_km"] <= 100, f"Driver beyond max_km: {d}"
        # Madrid driver (~390km away) must NOT be in this list
        names = [d["name"] for d in data["drivers"]]
        assert not any("Madrid" in n for n in names), f"Madrid driver leaked into Sevilla 100km: {names}"

    def test_nearest_rejects_customer(self, session, customer_token):
        r = session.get(
            f"{API}/drivers/nearest",
            params={"lat": 40.4168, "lng": -3.7038},
            headers={"Authorization": f"Bearer {customer_token}"},
            timeout=15,
        )
        assert r.status_code == 403, r.text


# --------- assign-nearest ---------
class TestAssignNearest:
    def test_assign_then_double_assign_returns_400(self, session, admin_token):
        # Find a pending order
        r = session.get(
            f"{API}/admin/pending-orders",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200
        orders = r.json().get("orders", [])
        if not orders:
            pytest.skip("No pending orders available to test assign-nearest")
        order_id = orders[0]["id"]

        # 1st call: assign nearest from Madrid center
        r1 = session.post(
            f"{API}/orders/{order_id}/assign-nearest",
            json={"lat": 40.4168, "lng": -3.7038},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r1.status_code == 200, f"Assign failed: {r1.status_code} {r1.text}"
        body = r1.json()
        assert body.get("order_id") == order_id
        assert "driver" in body
        drv = body["driver"]
        assert "name" in drv and "distance_km" in drv
        assert isinstance(drv["distance_km"], (int, float))

        # Verify the order disappears from pending list
        r_after = session.get(
            f"{API}/admin/pending-orders",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r_after.status_code == 200
        ids_after = [o["id"] for o in r_after.json().get("orders", [])]
        assert order_id not in ids_after, "Assigned order still appears in pending list"

        # 2nd call on same order -> 400
        r2 = session.post(
            f"{API}/orders/{order_id}/assign-nearest",
            json={"lat": 40.4168, "lng": -3.7038},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r2.status_code == 400, f"Expected 400 on double-assign, got {r2.status_code}: {r2.text}"
        assert "already" in r2.text.lower()

    def test_assign_nearest_rejects_customer(self, session, customer_token):
        # Use a bogus order id; RBAC should reject before lookup
        r = session.post(
            f"{API}/orders/nonexistent-{uuid.uuid4().hex[:6]}/assign-nearest",
            json={"lat": 40.4168, "lng": -3.7038},
            headers={"Authorization": f"Bearer {customer_token}"},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_assign_nearest_rejects_driver(self, session, driver_token):
        r = session.post(
            f"{API}/orders/nonexistent-{uuid.uuid4().hex[:6]}/assign-nearest",
            json={"lat": 40.4168, "lng": -3.7038},
            headers={"Authorization": f"Bearer {driver_token}"},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_assign_nearest_404_for_missing_order(self, session, admin_token):
        r = session.post(
            f"{API}/orders/does-not-exist-{uuid.uuid4().hex[:6]}/assign-nearest",
            json={"lat": 40.4168, "lng": -3.7038},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 404, r.text
