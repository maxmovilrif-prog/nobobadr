"""End-to-end backend tests: auth, riders, orders, assignments, COD->cash, RBAC."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = BASE_URL + "/api"


# ----------------------------- Fixtures -----------------------------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "admin@moboexpress.com", "password": "admin123"},
                      timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data and "user" in data
    assert data["user"]["role"] == "admin"
    return data["access_token"]


@pytest.fixture(scope="module")
def rider_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "rider@moboexpress.com", "password": "rider123"},
                      timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def rider_id(admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{API}/riders", headers=h, timeout=15)
    assert r.status_code == 200
    riders = r.json()["riders"]
    demo = [x for x in riders if x["email"] == "rider@moboexpress.com"]
    assert demo, "Demo rider missing"
    return demo[0]["id"]


# ----------------------------- Auth -----------------------------
class TestAuth:
    def test_login_admin(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 10

    def test_me_with_bearer(self, admin_token):
        r = requests.get(f"{API}/auth/me",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == "admin@moboexpress.com"
        assert u["role"] == "admin"
        assert "password_hash" not in u

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "admin@moboexpress.com", "password": "wrong"},
                          timeout=15)
        assert r.status_code == 401

    def test_register_new_rider(self):
        email = f"test_rider_{uuid.uuid4().hex[:6]}@moboexpress.com"
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "test123", "name": "Test Rider",
            "role": "rider", "city": "Tanger", "vehicle": "Moto",
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == email
        assert data["user"]["role"] == "rider"
        assert "password_hash" not in data["user"]

    def test_register_duplicate(self):
        r = requests.post(f"{API}/auth/register", json={
            "email": "admin@moboexpress.com", "password": "x12345",
            "name": "x", "role": "customer",
        }, timeout=15)
        assert r.status_code == 400


# ----------------------------- Riders -----------------------------
class TestRiders:
    def test_list_riders_includes_demo(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{API}/riders", headers=h, timeout=15)
        assert r.status_code == 200
        emails = [x["email"] for x in r.json()["riders"]]
        assert "rider@moboexpress.com" in emails

    def test_riders_requires_auth(self):
        r = requests.get(f"{API}/riders", timeout=15)
        assert r.status_code == 401


# ----------------------------- Orders -----------------------------
class TestOrdersCurrency:
    def test_tanger_morocco_assigns_mad(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "customer_name": "TEST_Cust_MAD", "address": "Av Mohammed V 123",
            "city": "Tanger", "country": "Morocco", "amount": 250.0,
            "payment_method": "cod_cash",
            "pickup": {"lat": 35.7595, "lng": -5.834, "address": "Tienda"},
            "dropoff": {"lat": 35.7700, "lng": -5.8000, "address": "Cliente"},
        }
        r = requests.post(f"{API}/orders", json=payload, headers=h, timeout=15)
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["currency"] == "MAD"
        assert o["status"] == "pending"
        assert o["distance_km"] is not None and o["distance_km"] > 0
        assert o["code"].startswith("ORD-")
        # Verify via GET
        g = requests.get(f"{API}/orders/{o['id']}", headers=h, timeout=15)
        assert g.status_code == 200
        assert g.json()["currency"] == "MAD"

    def test_algeciras_spain_assigns_eur(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "customer_name": "TEST_Cust_EUR", "address": "Calle Real 5",
            "city": "Algeciras", "country": "Spain", "amount": 80.0,
            "payment_method": "card",
        }
        r = requests.post(f"{API}/orders", json=payload, headers=h, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["currency"] == "EUR"


# ----------------------------- Assignments + RBAC -----------------------------
class TestAssignmentsRBAC:
    def _create_order(self, token, **extra):
        h = {"Authorization": f"Bearer {token}"}
        base = {
            "customer_name": "TEST_AssignCust", "address": "X 1",
            "city": "Tanger", "country": "Morocco", "amount": 100.0,
            "payment_method": "cod_cash",
        }
        base.update(extra)
        r = requests.post(f"{API}/orders", json=base, headers=h, timeout=15)
        assert r.status_code == 200
        return r.json()

    def test_admin_can_assign(self, admin_token, rider_id):
        order = self._create_order(admin_token)
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.post(f"{API}/assignments",
                          json={"order_id": order["id"], "rider_id": rider_id},
                          headers=h, timeout=15)
        assert r.status_code == 200, r.text
        a = r.json()
        assert a["order_id"] == order["id"]
        assert a["rider_id"] == rider_id
        # Verify order updated
        g = requests.get(f"{API}/orders/{order['id']}", headers=h, timeout=15)
        ord_data = g.json()
        assert ord_data["status"] == "assigned"
        assert ord_data["assigned_rider_id"] == rider_id

    def test_rider_cannot_assign(self, rider_token, admin_token, rider_id):
        order = self._create_order(admin_token)
        h = {"Authorization": f"Bearer {rider_token}"}
        r = requests.post(f"{API}/assignments",
                          json={"order_id": order["id"], "rider_id": rider_id},
                          headers=h, timeout=15)
        assert r.status_code == 403

    def test_rider_only_sees_own_orders(self, rider_token, admin_token, rider_id):
        # Create one assigned to rider and one not
        h_admin = {"Authorization": f"Bearer {admin_token}"}
        assigned = self._create_order(admin_token, customer_name="TEST_OwnA")
        unassigned = self._create_order(admin_token, customer_name="TEST_OwnB")
        requests.post(f"{API}/assignments",
                      json={"order_id": assigned["id"], "rider_id": rider_id},
                      headers=h_admin, timeout=15)

        h_rider = {"Authorization": f"Bearer {rider_token}"}
        r = requests.get(f"{API}/orders", headers=h_rider, timeout=15)
        assert r.status_code == 200
        ids = [o["id"] for o in r.json()["orders"]]
        assert assigned["id"] in ids
        assert unassigned["id"] not in ids


# ----------------------------- COD -> Cash Closing -----------------------------
class TestCodToCash:
    def _create_and_deliver(self, token, payment_method, city="Tanger",
                            country="Morocco", amount=150.0):
        h = {"Authorization": f"Bearer {token}"}
        c = requests.post(f"{API}/orders", json={
            "customer_name": f"TEST_COD_{uuid.uuid4().hex[:5]}",
            "address": "Test addr", "city": city, "country": country,
            "amount": amount, "payment_method": payment_method,
        }, headers=h, timeout=15)
        assert c.status_code == 200
        order = c.json()
        u = requests.patch(f"{API}/orders/{order['id']}/status",
                           json={"status": "delivered"}, headers=h, timeout=15)
        assert u.status_code == 200, u.text
        return u.json()

    def test_cod_cash_delivered_creates_entry(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        delivered = self._create_and_deliver(admin_token, "cod_cash", amount=175.5)
        assert delivered["status"] == "delivered"
        assert delivered["paid"] is True
        assert delivered["cash_movement_id"] is not None
        assert delivered["currency"] == "MAD"

        # Verify movement appears in today's cash closing
        r = requests.get(f"{API}/accounting/cash-closing", headers=h, timeout=15)
        assert r.status_code == 200
        summary = r.json()
        matching = [m for m in summary["movimientos"]
                    if m.get("order_id") == delivered["id"]]
        assert len(matching) == 1
        mv = matching[0]
        assert mv["type"] == "entrada"
        assert mv["method"] == "efectivo"
        assert mv["currency"] == "MAD"
        assert abs(mv["amount"] - 175.5) < 0.01
        assert mv["id"] == delivered["cash_movement_id"]

    def test_card_delivered_no_entry(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        delivered = self._create_and_deliver(admin_token, "card",
                                             city="Algeciras", country="Spain",
                                             amount=99.0)
        assert delivered["status"] == "delivered"
        assert delivered["paid"] is False
        assert delivered["cash_movement_id"] is None
        # Ensure no movement references this order
        r = requests.get(f"{API}/accounting/cash-closing", headers=h, timeout=15)
        assert r.status_code == 200
        refs = [m for m in r.json()["movimientos"]
                if m.get("order_id") == delivered["id"]]
        assert refs == []

    def test_eur_cod_cash_creates_eur_entry(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        delivered = self._create_and_deliver(admin_token, "cod_cash",
                                             city="Algeciras", country="Spain",
                                             amount=42.0)
        assert delivered["currency"] == "EUR"
        assert delivered["cash_movement_id"] is not None
        r = requests.get(f"{API}/accounting/cash-closing", headers=h, timeout=15)
        m = [x for x in r.json()["movimientos"] if x.get("order_id") == delivered["id"]][0]
        assert m["currency"] == "EUR"
