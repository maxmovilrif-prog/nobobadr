"""
Regression tests for Nubo backend modularization (server.py split into core/models/routes/*).
Verifies API contracts remained unchanged plus the new idle_count / idle / idle_seconds
fields on /api/admin/active-drivers.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN_EMAIL = "admin@nubo.com"
ADMIN_PASSWORD = "Admin1234!"
CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASSWORD = "Test1234!"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(api, email, password):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="session")
def admin_token(api):
    return _login(api, ADMIN_EMAIL, ADMIN_PASSWORD)["token"]


@pytest.fixture(scope="session")
def customer_token(api):
    return _login(api, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def customer_headers(customer_token):
    return {"Authorization": f"Bearer {customer_token}"}


# ---------- AUTH module ----------
class TestAuth:
    def test_register_customer_ok(self, api):
        unique = uuid.uuid4().hex[:8]
        payload = {
            "email": f"TEST_reg_{unique}@example.com",
            "password": "Test1234!",
            "name": "Test User",
            "phone": "+34123456789",
            "role": "customer",
        }
        r = api.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Register returns UserResponse (no token by contract)
        assert data["email"] == payload["email"]
        assert data["role"] == "customer"
        assert "id" in data

    def test_register_admin_role_rejected(self, api):
        payload = {
            "email": f"TEST_evil_{uuid.uuid4().hex[:6]}@example.com",
            "password": "Test1234!",
            "name": "Evil",
            "phone": "+341",
            "role": "admin",
        }
        r = api.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=30)
        assert r.status_code == 400, r.text

    def test_login_admin_ok(self, api):
        data = _login(api, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == ADMIN_EMAIL

    def test_login_customer_ok(self, api):
        data = _login(api, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        assert data["user"]["role"] == "customer"

    def test_login_wrong_password_401(self, api):
        r = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": CUSTOMER_EMAIL, "password": "wrong"}, timeout=30)
        assert r.status_code == 401, r.text

    def test_auth_me_with_admin(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/auth/me", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"

    def test_auth_me_no_token_403(self, api):
        r = api.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 403


# ---------- BUSINESSES / PRODUCTS module ----------
class TestBusinessesProducts:
    def test_get_businesses_public(self, api):
        r = api.get(f"{BASE_URL}/api/businesses", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected seeded businesses"
        b = data[0]
        for field in ("id", "name", "category", "owner_id"):
            assert field in b
        # save for next test
        TestBusinessesProducts.first_business_id = b["id"]

    def test_get_products_for_business(self, api):
        bid = getattr(TestBusinessesProducts, "first_business_id", None)
        if not bid:
            pytest.skip("No business id from previous test")
        r = api.get(f"{BASE_URL}/api/products/{bid}", timeout=30)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_create_product_as_customer_forbidden(self, api, customer_headers):
        payload = {
            "business_id": "fake-business-id",
            "name": "X",
            "description": "X",
            "price": 1.0,
            "category": "x",
            "image_url": "https://example.com/x.jpg",
            "stock": 0,
        }
        r = api.post(f"{BASE_URL}/api/products", json=payload, headers=customer_headers, timeout=30)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


# ---------- ORDERS module ----------
class TestOrders:
    def test_create_order_as_customer(self, api, customer_headers):
        # get a business
        bs = api.get(f"{BASE_URL}/api/businesses", timeout=30).json()
        assert bs, "No businesses available"
        bid = bs[0]["id"]
        payload = {
            "business_id": bid,
            "items": [
                {"product_id": "p1", "product_name": "Test", "quantity": 1, "price": 9.99}
            ],
            "delivery_address": "Calle Test 123, Algeciras",
        }
        r = api.post(f"{BASE_URL}/api/orders", json=payload, headers=customer_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["business_id"] == bid
        assert data["total_amount"] == 9.99
        assert data["status"] == "pending"
        assert "id" in data
        TestOrders.order_id = data["id"]

    def test_get_orders_as_customer(self, api, customer_headers):
        r = api.get(f"{BASE_URL}/api/orders", headers=customer_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        oid = getattr(TestOrders, "order_id", None)
        if oid:
            assert any(o["id"] == oid for o in data), "Just created order not present"

    def test_get_orders_no_auth_403(self, api):
        r = api.get(f"{BASE_URL}/api/orders", timeout=30)
        assert r.status_code == 403

    def test_create_order_no_auth_403(self, api):
        r = api.post(f"{BASE_URL}/api/orders", json={}, timeout=30)
        assert r.status_code == 403


# ---------- SEARCH module ----------
class TestSearch:
    def test_smart_search_hambre(self, api):
        r = api.post(f"{BASE_URL}/api/search/smart", json={"query": "tengo hambre"}, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        for f in ("message", "categories", "keywords", "businesses", "products"):
            assert f in data


# ---------- DROPSHIPPING module ----------
class TestDropshipping:
    def test_get_dropshipping_products(self, api):
        r = api.get(f"{BASE_URL}/api/dropshipping/products", timeout=30)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)


# ---------- AFFILIATE module ----------
class TestAffiliate:
    def test_get_affiliate_links(self, api):
        r = api.get(f"{BASE_URL}/api/affiliate-links", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Endpoint returns a dict of provider links (contract preserved)
        assert isinstance(data, dict)
        assert len(data) > 0


# ---------- ADMIN module (with new idle fields) ----------
class TestAdmin:
    def test_admin_stats_ok(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/stats", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        for k in ("total_orders", "in_transit", "delivered", "total_drivers",
                  "available_drivers", "total_businesses", "live_drivers"):
            assert k in data and isinstance(data[k], int)

    def test_admin_active_drivers_with_idle_fields(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/active-drivers", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # New top-level field
        assert "idle_count" in data, f"Missing idle_count field. Got keys: {list(data.keys())}"
        assert isinstance(data["idle_count"], int)
        # Pre-existing
        for f in ("count", "live_count", "available_count", "active_orders", "drivers"):
            assert f in data
        # Per-live-driver fields presence
        for d in data["drivers"]:
            if d.get("live"):
                assert "idle" in d, f"Live driver missing 'idle': {d}"
                assert "idle_seconds" in d, f"Live driver missing 'idle_seconds': {d}"
                assert isinstance(d["idle"], bool)

    def test_admin_stats_customer_token_403(self, api, customer_headers):
        r = api.get(f"{BASE_URL}/api/admin/stats", headers=customer_headers, timeout=30)
        assert r.status_code == 403

    def test_admin_active_drivers_no_auth_403(self, api):
        r = api.get(f"{BASE_URL}/api/admin/active-drivers", timeout=30)
        assert r.status_code == 403

    def test_admin_active_drivers_customer_token_403(self, api, customer_headers):
        r = api.get(f"{BASE_URL}/api/admin/active-drivers", headers=customer_headers, timeout=30)
        assert r.status_code == 403
