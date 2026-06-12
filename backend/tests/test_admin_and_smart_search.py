"""Backend tests for Nubo Express new features:
- AI Smart Search (POST /api/search/smart)
- Admin login + admin dashboard endpoints
- Driver location update endpoint
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://delivery-hub-1041.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@nuboexpress.com"
ADMIN_PASSWORD = "Admin1234"
DRIVER_EMAIL = "bee.madrid@nubo.com"
DRIVER_PASSWORD = "Driver1234"


# ------------- fixtures -------------

@pytest.fixture(scope="session")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(http, email, password):
    r = http.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="session")
def admin_auth(http):
    return _login(http, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def driver_auth(http):
    return _login(http, DRIVER_EMAIL, DRIVER_PASSWORD)


@pytest.fixture(scope="session")
def customer_auth(http):
    # Register a fresh customer for negative tests
    email = f"test_customer_{uuid.uuid4().hex[:8]}@example.com"
    r = http.post(f"{API}/auth/register", json={
        "email": email,
        "password": "Customer1234",
        "name": "Test Customer",
        "phone": "+34600000000",
        "role": "customer",
    }, timeout=20)
    assert r.status_code in (200, 201), f"Customer register failed: {r.status_code} {r.text}"
    # register may not return token; login to obtain one
    return _login(http, email, "Customer1234")


# ------------- Admin login -------------

class TestAdminAuth:
    def test_admin_login_returns_admin_role(self, admin_auth):
        assert "token" in admin_auth, f"Missing token in login response: {admin_auth}"
        user = admin_auth.get("user", {})
        assert user.get("role") == "admin", f"Expected role=admin, got {user.get('role')}"
        assert user.get("email") == ADMIN_EMAIL


# ------------- Admin stats -------------

class TestAdminStats:
    def test_stats_with_admin_token(self, http, admin_auth):
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        r = http.get(f"{API}/admin/stats", headers=headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["total_customers", "total_drivers", "available_drivers",
                  "total_businesses", "total_orders", "active_orders",
                  "delivered_orders", "revenue"]:
            assert k in data, f"Missing field {k} in stats response: {data}"
        # types
        assert isinstance(data["total_customers"], int)
        assert isinstance(data["available_drivers"], int)
        assert data["available_drivers"] >= 7, f"Expected >=7 available drivers (seeded), got {data['available_drivers']}"
        assert isinstance(data["revenue"], (int, float))

    def test_stats_with_customer_token_forbidden(self, http, customer_auth):
        headers = {"Authorization": f"Bearer {customer_auth['token']}"}
        r = http.get(f"{API}/admin/stats", headers=headers, timeout=20)
        assert r.status_code == 403, f"Expected 403, got {r.status_code} - {r.text}"

    def test_stats_without_token_unauthorized(self, http):
        r = http.get(f"{API}/admin/stats", timeout=20)
        # Without token should be 401 or 403
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


# ------------- Admin active drivers -------------

class TestAdminActiveDrivers:
    def test_active_drivers_with_admin(self, http, admin_auth):
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        r = http.get(f"{API}/admin/active-drivers", headers=headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "count" in data and "drivers" in data
        assert isinstance(data["drivers"], list)
        assert data["count"] >= 7, f"Expected >=7 seeded drivers, got {data['count']}"
        # each driver shape
        sample = data["drivers"][0]
        for k in ["driver_id", "name", "vehicle_type", "lat", "lng"]:
            assert k in sample, f"Missing key {k} in driver: {sample}"
        assert isinstance(sample["lat"], (int, float))
        assert isinstance(sample["lng"], (int, float))

    def test_active_drivers_with_customer_forbidden(self, http, customer_auth):
        headers = {"Authorization": f"Bearer {customer_auth['token']}"}
        r = http.get(f"{API}/admin/active-drivers", headers=headers, timeout=20)
        assert r.status_code == 403


# ------------- Driver location update -------------

class TestDriverLocation:
    def test_driver_can_update_location(self, http, driver_auth):
        headers = {"Authorization": f"Bearer {driver_auth['token']}"}
        r = http.patch(f"{API}/drivers/location",
                       headers=headers,
                       json={"lat": 40.4, "lng": -3.7},
                       timeout=20)
        assert r.status_code == 200, r.text
        assert "message" in r.json()

    def test_customer_cannot_update_location(self, http, customer_auth):
        headers = {"Authorization": f"Bearer {customer_auth['token']}"}
        r = http.patch(f"{API}/drivers/location",
                       headers=headers,
                       json={"lat": 40.4, "lng": -3.7},
                       timeout=20)
        assert r.status_code == 403


# ------------- Smart Search -------------

class TestSmartSearch:
    def test_empty_query_returns_400(self, http):
        r = http.post(f"{API}/search/smart", json={"query": ""}, timeout=30)
        assert r.status_code == 400

    def test_whitespace_query_returns_400(self, http):
        r = http.post(f"{API}/search/smart", json={"query": "   "}, timeout=30)
        assert r.status_code == 400

    def test_smart_search_returns_suggestions(self, http):
        r = http.post(f"{API}/search/smart", json={"query": "tengo hambre"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "suggestions" in data
        assert "reason" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) <= 3
        # If any businesses exist, we should get items, each with id and name
        for biz in data["suggestions"]:
            assert "id" in biz
            assert "name" in biz
            # ensure no MongoDB _id leaked
            assert "_id" not in biz
        assert isinstance(data["reason"], str)
