"""
Backend tests for new features in Nubo:
  1. AI Smart Search (POST /api/search/smart) — uses Emergent LLM key
  2. Admin Fleet Dashboard (GET /api/admin/stats, GET /api/admin/active-drivers)
  3. Public register guard (POST /api/auth/register cannot create admin)
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nubo-abejas.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "badarbox1756@gmail.com"
ADMIN_PASSWORD = "Admin1234!"
CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASSWORD = "Test1234!"


# -------- Fixtures --------
@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(api, email, password):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="session")
def admin_token(api):
    return _login(api, ADMIN_EMAIL, ADMIN_PASSWORD)["token"]


@pytest.fixture(scope="session")
def customer_token(api):
    return _login(api, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)["token"]


# -------- Smart Search Tests --------
class TestSmartSearch:
    def test_smart_search_hambre(self, api):
        """'tengo hambre' should return restaurant/supermarket related categories."""
        r = api.post(f"{BASE_URL}/api/search/smart", json={"query": "tengo hambre"}, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        # Required fields
        for field in ("message", "categories", "keywords", "businesses", "products"):
            assert field in data, f"Missing field: {field}"
        assert isinstance(data["categories"], list)
        assert isinstance(data["keywords"], list)
        assert isinstance(data["businesses"], list)
        assert isinstance(data["products"], list)
        assert isinstance(data["message"], str) and len(data["message"]) > 0
        # Categories should include food-related (restaurant or supermarket)
        food_cats = {"restaurant", "supermarket"}
        assert any(c in food_cats for c in data["categories"]), (
            f"Expected food category in {data['categories']}"
        )

    def test_smart_search_empty_query_400(self, api):
        r = api.post(f"{BASE_URL}/api/search/smart", json={"query": ""}, timeout=30)
        assert r.status_code == 400, f"Expected 400 got {r.status_code}: {r.text}"

    def test_smart_search_courier(self, api):
        """'quiero enviar un paquete' should classify as courier."""
        r = api.post(f"{BASE_URL}/api/search/smart", json={"query": "quiero enviar un paquete"}, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "courier" in data["categories"], (
            f"Expected 'courier' in categories, got {data['categories']}"
        )


# -------- Admin endpoints --------
class TestAdminEndpoints:
    def test_admin_stats_with_admin(self, api, admin_token):
        r = api.get(f"{BASE_URL}/api/admin/stats", headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        expected = {"total_orders", "in_transit", "delivered", "total_drivers",
                    "available_drivers", "total_businesses", "live_drivers"}
        missing = expected - set(data.keys())
        assert not missing, f"Missing fields: {missing}"
        for k in expected:
            assert isinstance(data[k], int), f"{k} should be int, got {type(data[k])}"

    def test_admin_active_drivers_with_admin(self, api, admin_token):
        r = api.get(f"{BASE_URL}/api/admin/active-drivers",
                    headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for field in ("count", "live_count", "available_count", "active_orders", "drivers"):
            assert field in data, f"Missing field: {field}"
        assert isinstance(data["drivers"], list)

    def test_admin_stats_no_auth_returns_403(self, api):
        r = api.get(f"{BASE_URL}/api/admin/stats", timeout=30)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"

    def test_admin_stats_customer_token_returns_403(self, api, customer_token):
        r = api.get(f"{BASE_URL}/api/admin/stats",
                    headers={"Authorization": f"Bearer {customer_token}"}, timeout=30)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"

    def test_admin_active_drivers_no_auth_returns_403(self, api):
        r = api.get(f"{BASE_URL}/api/admin/active-drivers", timeout=30)
        assert r.status_code == 403

    def test_admin_active_drivers_customer_token_returns_403(self, api, customer_token):
        r = api.get(f"{BASE_URL}/api/admin/active-drivers",
                    headers={"Authorization": f"Bearer {customer_token}"}, timeout=30)
        assert r.status_code == 403


# -------- Register guard --------
class TestRegisterGuard:
    def test_register_admin_role_rejected(self, api):
        """Public registration must reject role='admin' with HTTP 400."""
        payload = {
            "email": "TEST_evil_admin@example.com",
            "password": "Test1234!",
            "name": "Evil Admin",
            "phone": "+34123456789",
            "role": "admin",
        }
        r = api.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=30)
        assert r.status_code == 400, f"Expected 400 got {r.status_code}: {r.text}"
