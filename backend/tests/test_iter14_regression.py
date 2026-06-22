"""Iteration 14 regression: validates refactored KPI endpoints, Nubo Car flow, RBAC,
AI smart search, and auth after the admin.py refactor + Google Maps region='MA' change.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nubo-abejas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "badarbox1756@gmail.com"
ADMIN_PASS = "Admin1234!"
CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASS = "Test1234!"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("user", {}).get("role") == "admin"
    return data["token"]


@pytest.fixture(scope="module")
def customer_token():
    r = requests.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASS}, timeout=20)
    assert r.status_code == 200, f"customer login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("user", {}).get("role") == "customer"
    return data["token"]


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Backend KPIs (refactor regression) ----------
class TestAdminKpis:
    def test_admin_kpis_structure(self, admin_token):
        r = requests.get(f"{API}/admin/kpis", headers=H(admin_token), timeout=20)
        assert r.status_code == 200, f"unexpected {r.status_code}: {r.text[:300]}"
        d = r.json()
        # Required keys after refactor
        for k in ("orders_today", "orders_per_day", "revenue_month_eur",
                  "delivered_total", "avg_delivery_mins", "top_bees", "as_of"):
            assert k in d, f"missing key {k} in /admin/kpis response"
        assert isinstance(d["orders_per_day"], list)
        assert len(d["orders_per_day"]) == 7, "orders_per_day must have 7 days"
        for row in d["orders_per_day"]:
            assert set(row.keys()) >= {"date", "orders", "delivered"}
        assert isinstance(d["orders_today"], int)
        assert isinstance(d["delivered_total"], int)
        assert isinstance(d["revenue_month_eur"], (int, float))
        assert isinstance(d["top_bees"], list)

    def test_admin_kpis_forbidden_for_customer(self, customer_token):
        r = requests.get(f"{API}/admin/kpis", headers=H(customer_token), timeout=20)
        assert r.status_code in (401, 403)


# ---------- Active fleet refactor regression ----------
class TestActiveDrivers:
    def test_active_drivers_structure(self, admin_token):
        r = requests.get(f"{API}/admin/active-drivers", headers=H(admin_token), timeout=20)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("count", "live_count", "available_count", "idle_count", "active_orders", "drivers"):
            assert k in d
        assert isinstance(d["drivers"], list)
        assert d["count"] == len(d["drivers"])
        assert isinstance(d["live_count"], int)
        assert isinstance(d["available_count"], int)
        assert isinstance(d["idle_count"], int)
        assert isinstance(d["active_orders"], int)


# ---------- Regional KPI (Founder shortcut) ----------
class TestMyRegionKpis:
    def test_my_region_kpis_for_founder(self, admin_token):
        r = requests.get(f"{API}/admin/my-region/kpis", headers=H(admin_token), timeout=20)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("is_founder") is True
        assert d.get("region") is None


# ---------- Nubo Car full ciclo ----------
class TestNuboCar:
    # Algeciras → Algeciras (~5km) keeps price realistic
    PAYLOAD_ESTIMATE = {
        "origin_lat": 36.131, "origin_lng": -5.452,
        "destination_lat": 36.140, "destination_lng": -5.460,
        "currency": "EUR",
    }

    def test_estimate_returns_three_options(self, customer_token):
        r = requests.post(f"{API}/rides/estimate", headers=H(customer_token),
                          json=self.PAYLOAD_ESTIMATE, timeout=20)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("currency") == "EUR"
        opts = d.get("options", [])
        vts = {o.get("vehicle_type") for o in opts}
        assert {"economy", "comfort", "xl"}.issubset(vts), f"missing vehicle types: {vts}"
        for o in opts:
            assert o.get("estimated_price", 0) > 0
            assert o.get("distance_km", -1) >= 0

    def test_request_active_and_cancel(self, customer_token):
        # cleanup: cancel any pre-existing active ride
        ar = requests.get(f"{API}/rides/active", headers=H(customer_token), timeout=20)
        if ar.status_code == 200 and ar.json().get("ride"):
            rid = ar.json()["ride"]["id"]
            requests.post(f"{API}/rides/{rid}/cancel", headers=H(customer_token),
                          json={"reason": "cleanup"}, timeout=20)

        body = {
            **self.PAYLOAD_ESTIMATE,
            "vehicle_type": "economy",
            "origin_label": "Algeciras Centro",
            "destination_label": "Algeciras Puerto",
        }
        r = requests.post(f"{API}/rides/request", headers=H(customer_token), json=body, timeout=20)
        assert r.status_code == 200, r.text[:300]
        ride = r.json()
        rid = ride["id"]
        assert ride["estado"] == "buscando"
        assert ride["vehicle_type"] == "economy"

        # GET /rides/active shows it
        r2 = requests.get(f"{API}/rides/active", headers=H(customer_token), timeout=20)
        assert r2.status_code == 200
        active = r2.json().get("ride")
        assert active and active["id"] == rid

        # duplicate active blocked (400)
        r3 = requests.post(f"{API}/rides/request", headers=H(customer_token), json=body, timeout=20)
        assert r3.status_code == 400

        # cancel
        r4 = requests.post(f"{API}/rides/{rid}/cancel", headers=H(customer_token),
                           json={"reason": "test regression"}, timeout=20)
        assert r4.status_code == 200
        assert r4.json()["estado"] == "cancelado"

    def test_invalid_vehicle_type_rejected(self, customer_token):
        body = {**self.PAYLOAD_ESTIMATE, "vehicle_type": "car"}  # 'car' was old/invalid
        r = requests.post(f"{API}/rides/request", headers=H(customer_token), json=body, timeout=20)
        # Either pydantic 422 or app 400
        assert r.status_code in (400, 422), f"expected 400/422 got {r.status_code}: {r.text[:200]}"


# ---------- Nubo Car RBAC ----------
class TestNuboCarRbac:
    def test_customer_cannot_accept(self, customer_token):
        r = requests.post(f"{API}/rides/accept", headers=H(customer_token),
                          json={"ride_id": "non-existent-id"}, timeout=20)
        assert r.status_code == 403, f"expected 403 got {r.status_code}"


# ---------- AI Smart Search ----------
class TestSmartSearch:
    def test_smart_search_returns_categories(self):
        r = requests.post(f"{API}/search/smart", json={"query": "tengo hambre"}, timeout=45)
        assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
        d = r.json()
        # response should include categories or keywords from LLM
        assert ("categories" in d) or ("keywords" in d), f"unexpected payload: {d}"


# ---------- Auth basics ----------
class TestAuthBasics:
    def test_admin_login_ok(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"

    def test_customer_login_ok(self):
        r = requests.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASS}, timeout=20)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "customer"

    def test_admin_endpoint_rejects_anonymous(self):
        r = requests.get(f"{API}/admin/kpis", timeout=20)
        assert r.status_code in (401, 403)
