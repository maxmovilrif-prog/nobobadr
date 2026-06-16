"""Iteration 19 — tests for:
- POST /api/orders/express → POST /api/payments/create-checkout currency handling
- auto_assign_order using origin_lat/origin_lng for express orders
- Admin Cities CRUD (POST/PATCH/DELETE /api/admin/cities)
- Business bank_account field on POST /api/businesses
"""
import os
import uuid
import math
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "control@nuboexpress.com"
ADMIN_PASSWORD = "Fn6FcMveVf%--1o-"
ADMIN_SECRET = "NUBO-84D2-C159-E3CF"

CUSTOMER_EMAIL = "cliente@nubotest.com"
CUSTOMER_PASSWORD = "Cliente123!"

DRIVER_MADRID = "bee.madrid@nuboexpress.com"
DRIVER_PASSWORD = "Bee123!"

# Madrid centre
MAD_LAT, MAD_LNG = 40.4168, -3.7038
BCN_LAT, BCN_LNG = 41.3874, 2.1686


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    d = r.json()
    return d.get("token") or d.get("access_token")


def _admin_login():
    r = requests.post(
        f"{API}/admin-auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "secret_code": ADMIN_SECRET},
    )
    assert r.status_code == 200, r.text
    d = r.json()
    return d.get("token") or d.get("access_token")


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _admin_login()


@pytest.fixture(scope="module")
def customer_token():
    return _login(CUSTOMER_EMAIL, CUSTOMER_PASSWORD)


@pytest.fixture(scope="module")
def cities(admin_token):
    r = requests.get(f"{API}/cities", headers=_headers(admin_token))
    assert r.status_code == 200
    return r.json()["cities"]


# ============================
# CITY CRUD (admin)
# ============================
class TestAdminCities:
    created_ids = []

    def test_customer_cannot_create_city(self, customer_token):
        r = requests.post(
            f"{API}/admin/cities",
            json={"name": "TEST_FORBIDDEN_CITY", "country": "ES", "lat": 40.0, "lng": -3.0},
            headers=_headers(customer_token),
        )
        assert r.status_code == 403

    def test_create_city_ok(self, admin_token):
        name = f"TEST_City_{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/admin/cities",
            json={"name": name, "country": "MA", "lat": 35.5785, "lng": -5.3684},
            headers=_headers(admin_token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == name
        assert data["country"] == "MA"
        assert math.isclose(data["lat"], 35.5785, rel_tol=1e-6)
        assert "id" in data
        TestAdminCities.created_ids.append(data["id"])

        # GET verifies persistence
        r2 = requests.get(f"{API}/cities", headers=_headers(admin_token))
        names = [c["name"] for c in r2.json()["cities"]]
        assert name in names

    def test_create_duplicate_name_400(self, admin_token):
        name = f"TEST_Dup_{uuid.uuid4().hex[:6]}"
        r1 = requests.post(
            f"{API}/admin/cities",
            json={"name": name, "country": "ES", "lat": 1.0, "lng": 2.0},
            headers=_headers(admin_token),
        )
        assert r1.status_code == 200
        TestAdminCities.created_ids.append(r1.json()["id"])
        r2 = requests.post(
            f"{API}/admin/cities",
            json={"name": name, "country": "ES", "lat": 1.0, "lng": 2.0},
            headers=_headers(admin_token),
        )
        assert r2.status_code == 400

    def test_update_city(self, admin_token):
        # create
        name = f"TEST_Upd_{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/admin/cities",
            json={"name": name, "country": "ES", "lat": 10.0, "lng": 20.0},
            headers=_headers(admin_token),
        )
        cid = r.json()["id"]
        TestAdminCities.created_ids.append(cid)
        # patch
        new_name = name + "_v2"
        r2 = requests.patch(
            f"{API}/admin/cities/{cid}",
            json={"name": new_name, "lat": 11.5, "lng": 21.5},
            headers=_headers(admin_token),
        )
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["name"] == new_name
        assert math.isclose(d["lat"], 11.5)
        assert math.isclose(d["lng"], 21.5)

    def test_delete_city_with_active_order_400(self, admin_token, customer_token):
        # Create a city
        name = f"TEST_Del_{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/admin/cities",
            json={"name": name, "country": "ES", "lat": 40.0, "lng": -3.0},
            headers=_headers(admin_token),
        )
        cid = r.json()["id"]
        TestAdminCities.created_ids.append(cid)

        # Create an active express order in that city
        ro = requests.post(
            f"{API}/orders/express",
            json={
                "origin_name": "A", "origin_lat": 40.0, "origin_lng": -3.0,
                "destination_name": "B", "destination_lat": 41.0, "destination_lng": -4.0,
                "vehicle_type": "motorcycle", "fee": 5.0, "currency": "EUR",
                "origin_city_id": cid,
            },
            headers=_headers(customer_token),
        )
        assert ro.status_code == 200, ro.text
        order_id = ro.json()["id"]

        rd = requests.delete(f"{API}/admin/cities/{cid}", headers=_headers(admin_token))
        assert rd.status_code == 400, rd.text

        # Cleanup: cancel order (direct DB not accessible from here — try admin order patch)
        # Best-effort: leave order pending; remove from created_ids so we don't try deleting again
        TestAdminCities.created_ids.remove(cid)

    def test_delete_city_ok(self, admin_token):
        name = f"TEST_Clean_{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/admin/cities",
            json={"name": name, "country": "ES", "lat": 1.1, "lng": 2.2},
            headers=_headers(admin_token),
        )
        cid = r.json()["id"]
        rd = requests.delete(f"{API}/admin/cities/{cid}", headers=_headers(admin_token))
        assert rd.status_code == 200, rd.text

        # Verify gone
        r2 = requests.get(f"{API}/cities", headers=_headers(admin_token))
        ids = [c["id"] for c in r2.json()["cities"]]
        assert cid not in ids

    def test_zzz_cleanup(self, admin_token):
        for cid in list(TestAdminCities.created_ids):
            requests.delete(f"{API}/admin/cities/{cid}", headers=_headers(admin_token))


# ============================
# EXPRESS ORDER + CHECKOUT CURRENCY
# ============================
class TestExpressCheckout:
    def _create_express(self, customer_token, currency="EUR"):
        payload = {
            "origin_name": "Madrid centro", "origin_lat": MAD_LAT, "origin_lng": MAD_LNG,
            "destination_name": "Barcelona centro", "destination_lat": BCN_LAT, "destination_lng": BCN_LNG,
            "vehicle_type": "motorcycle",
            "fee": 12.5,
            "currency": currency,
            "distance_km": 620, "eta_mins": 45,
        }
        r = requests.post(f"{API}/orders/express", json=payload, headers=_headers(customer_token))
        assert r.status_code == 200, r.text
        return r.json()

    def test_express_checkout_eur(self, customer_token):
        order = self._create_express(customer_token, "EUR")
        assert order["order_type"] == "express"
        assert order["business_id"] is None
        assert order["currency"] == "EUR"

        r = requests.post(
            f"{API}/payments/create-checkout",
            params={"order_id": order["id"]},
            headers=_headers(customer_token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "url" in data and data["url"].startswith("https://")
        assert "session_id" in data and data["session_id"]
        # Indirectly verify currency persisted in tx
        # (no admin tx endpoint — rely on Stripe url being created)

    def test_express_checkout_mad(self, customer_token):
        order = self._create_express(customer_token, "MAD")
        assert order["currency"] == "MAD"
        r = requests.post(
            f"{API}/payments/create-checkout",
            params={"order_id": order["id"]},
            headers=_headers(customer_token),
        )
        # If Stripe rejects MAD currency, this will 500/400. Document outcome.
        assert r.status_code == 200, f"MAD checkout failed: {r.status_code} {r.text}"
        d = r.json()
        assert "url" in d and "session_id" in d


# ============================
# AUTO ASSIGN — uses origin for express
# ============================
class TestAutoAssignExpress:
    def test_express_paid_assigned_to_nearby_driver(self, customer_token):
        # Ensure Madrid driver is available and located near Madrid
        drv_token = _login(DRIVER_MADRID, DRIVER_PASSWORD)
        # Set GPS to Madrid centre
        rg = requests.patch(
            f"{API}/drivers/location",
            json={"lat": MAD_LAT, "lng": MAD_LNG},
            headers=_headers(drv_token),
        )
        assert rg.status_code in (200, 204), rg.text
        # Ensure availability ON
        ra = requests.patch(
            f"{API}/drivers/availability",
            json={"is_available": True},
            headers=_headers(drv_token),
        )
        # accept 200 or 404 if endpoint different — we'll log
        # Create express order with origin in Madrid
        payload = {
            "origin_name": "Madrid Sol", "origin_lat": MAD_LAT, "origin_lng": MAD_LNG,
            "destination_name": "Madrid Atocha", "destination_lat": 40.4070, "destination_lng": -3.6907,
            "vehicle_type": "motorcycle",
            "fee": 8.0, "currency": "EUR",
            "distance_km": 3, "eta_mins": 10,
        }
        ro = requests.post(f"{API}/orders/express", json=payload, headers=_headers(customer_token))
        assert ro.status_code == 200, ro.text
        order_id = ro.json()["id"]

        # We cannot mark paid without Stripe webhook. Use admin endpoint if available,
        # otherwise trigger auto-dispatch through the test-only helper if exists.
        admin_token = _admin_login()
        # Try a maintenance/test endpoint
        mark = requests.post(
            f"{API}/admin/orders/{order_id}/mark-paid",
            headers=_headers(admin_token),
        )
        if mark.status_code == 404:
            pytest.skip("No admin mark-paid endpoint to simulate Stripe webhook; skipping auto-assign verification")
        assert mark.status_code in (200, 204), mark.text

        # wait briefly for auto_assign
        time.sleep(2)
        rget = requests.get(f"{API}/orders/{order_id}", headers=_headers(customer_token))
        assert rget.status_code == 200
        od = rget.json()
        assert od.get("driver_id") is not None, f"Order not auto-assigned: {od}"
        assert od.get("status") in ("accepted", "assigned"), od


# ============================
# BUSINESS bank_account
# ============================
class TestBusinessBank:
    def _register_business(self):
        email = f"TEST_biz_bank_{uuid.uuid4().hex[:6]}@nubotest.com"
        password = "Business123!"
        r = requests.post(
            f"{API}/auth/register",
            json={
                "email": email,
                "password": password,
                "name": "TEST Biz Bank",
                "role": "business",
                "phone": "+34600000000",
            },
        )
        assert r.status_code in (200, 201), r.text
        token = _login(email, password)
        return token, email

    def test_create_business_with_iban_persists(self):
        token, _ = self._register_business()
        iban = "ES7620770024003102575766"
        r = requests.post(
            f"{API}/businesses",
            json={
                "name": "TEST Pizza IBAN",
                "category": "restaurant",
                "description": "test",
                "address": "calle ficticia 1",
                "phone": "+34600000001",
                "image_url": "https://example.com/i.png",
                "delivery_time": "30 min",
                "bank_account": iban,
            },
            headers=_headers(token),
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("bank_account") == iban

        # GET listing
        r2 = requests.get(f"{API}/businesses")
        assert r2.status_code == 200
        names = [b for b in r2.json() if b.get("name") == "TEST Pizza IBAN"]
        assert names and names[0].get("bank_account") == iban
