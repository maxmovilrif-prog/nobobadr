"""Backend tests for Nubo Express new features:
- AI Smart Search (POST /api/search/smart) — no auth
- Admin Live Map APIs (/api/admin/active-drivers, /api/admin/stats) — admin auth
- Driver location update (PATCH /api/drivers/location) — driver auth
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nubo-express-preview.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@nuboexpress.com"
ADMIN_PASSWORD = "Admin123!"
CUSTOMER_EMAIL = "cliente@nubotest.com"
CUSTOMER_PASSWORD = "Cliente123!"
DRIVER_EMAIL = "bee.madrid@nuboexpress.com"
DRIVER_PASSWORD = "Bee123!"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    return r


@pytest.fixture(scope="session")
def admin_token(session):
    r = _login(session, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data or "access_token" in data
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="session")
def driver_token(session):
    r = _login(session, DRIVER_EMAIL, DRIVER_PASSWORD)
    assert r.status_code == 200, f"Driver login failed: {r.status_code} {r.text}"
    data = r.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="session")
def customer_token(session):
    # Try login; if user does not exist, register and login
    r = _login(session, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
    if r.status_code != 200:
        reg = session.post(
            f"{API}/auth/register",
            json={
                "email": CUSTOMER_EMAIL,
                "password": CUSTOMER_PASSWORD,
                "name": "Cliente Test",
                "phone": "+34 600 111 222",
                "role": "customer",
            },
            timeout=15,
        )
        # Either 200 or 400 if already exists
        r = _login(session, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
    assert r.status_code == 200, f"Customer login failed: {r.status_code} {r.text}"
    data = r.json()
    return data.get("token") or data.get("access_token")


# ---------- Smart Search ----------
class TestSmartSearch:
    def test_smart_search_food_returns_results(self, session):
        r = session.post(f"{API}/search/smart", json={"query": "tengo hambre, comida rapida"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "reply" in data and isinstance(data["reply"], str) and len(data["reply"]) > 0
        assert "results" in data and isinstance(data["results"], list)
        assert len(data["results"]) <= 3
        # Should return at least one business if any exist
        if data["results"]:
            b = data["results"][0]
            assert "id" in b and "name" in b
            assert "_id" not in b  # Mongo ObjectId must be excluded

    def test_smart_search_courier_query(self, session):
        r = session.post(f"{API}/search/smart", json={"query": "necesito enviar un paquete urgente"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "reply" in data
        assert "results" in data and isinstance(data["results"], list)
        assert len(data["results"]) <= 3

    def test_smart_search_empty_query_returns_400(self, session):
        r = session.post(f"{API}/search/smart", json={"query": ""}, timeout=15)
        assert r.status_code == 400


# ---------- Admin Active Drivers / Stats ----------
class TestAdminEndpoints:
    def test_active_drivers_admin(self, session, admin_token):
        r = session.get(
            f"{API}/admin/active-drivers",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "count" in data and "drivers" in data
        assert isinstance(data["drivers"], list)
        assert data["count"] >= 6, f"Expected at least 6 active drivers, got {data['count']}"
        # Each driver must have id, name, lat, lng
        for d in data["drivers"]:
            assert "id" in d and "name" in d
            assert isinstance(d.get("lat"), (int, float))
            assert isinstance(d.get("lng"), (int, float))

    def test_admin_stats(self, session, admin_token):
        r = session.get(
            f"{API}/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("total_drivers", "active_drivers", "total_businesses", "total_orders"):
            assert k in data
            assert isinstance(data[k], int)
        assert data["active_drivers"] >= 6

    def test_active_drivers_forbidden_for_non_admin(self, session, customer_token):
        r = session.get(
            f"{API}/admin/active-drivers",
            headers={"Authorization": f"Bearer {customer_token}"},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_admin_stats_forbidden_for_driver(self, session, driver_token):
        r = session.get(
            f"{API}/admin/stats",
            headers={"Authorization": f"Bearer {driver_token}"},
            timeout=15,
        )
        assert r.status_code == 403, r.text


# ---------- Driver Location ----------
class TestDriverLocation:
    def test_driver_location_update_ok(self, session, driver_token):
        r = session.patch(
            f"{API}/drivers/location",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"lat": 40.0, "lng": -3.0},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("lat") == 40.0
        assert data.get("lng") == -3.0

    def test_driver_location_forbidden_for_non_driver(self, session, customer_token):
        r = session.patch(
            f"{API}/drivers/location",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"lat": 40.0, "lng": -3.0},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_driver_location_after_change_appears_in_active_drivers(self, session, driver_token, admin_token):
        # Move madrid bee somewhere unique
        unique_lat = 41.1234
        unique_lng = -2.5678
        r = session.patch(
            f"{API}/drivers/location",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"lat": unique_lat, "lng": unique_lng},
            timeout=15,
        )
        assert r.status_code == 200
        # Verify via admin endpoint
        r2 = session.get(
            f"{API}/admin/active-drivers",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r2.status_code == 200
        drivers = r2.json().get("drivers", [])
        matched = [d for d in drivers if abs(d["lat"] - unique_lat) < 1e-4 and abs(d["lng"] - unique_lng) < 1e-4]
        assert len(matched) >= 1, "Driver location update did not persist / not visible in admin endpoint"
        # Reset back to Madrid coords
        session.patch(
            f"{API}/drivers/location",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"lat": 40.4168, "lng": -3.7038},
            timeout=15,
        )
