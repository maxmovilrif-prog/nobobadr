"""Backend tests for ATOMIC Nearest-Driver assignment + driver release.

Covers the recent change:
- POST /api/orders/{order_id}/assign-nearest now atomically claims the nearest
  driver via find_one_and_update (is_available True -> False, status 'busy'),
  retrying up to ASSIGN_MAX_ATTEMPTS (=3) excluding already-claimed drivers.
- A busy driver MUST NOT be re-assigned to another order.
- PATCH /api/orders/{id}/status with 'delivered' (or 'cancelled') releases the driver.
- POST /api/orders/{id}/return-to-queue releases the driver and re-pends the order.
- 404 when no available drivers nearby; 400 when order already assigned.
"""
import os
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

ADMIN_EMAIL = "control@nuboexpress.com"
ADMIN_PASSWORD = "Fn6FcMveVf%--1o-"
ADMIN_SECRET = "NUBO-84D2-C159-E3CF"

# Madrid centre (nearest to bee.madrid)
MADRID_LAT, MADRID_LNG = 40.4168, -3.7038
# Far Arctic point (no driver in the world is within 50 km of the North Pole region)
FAR_LAT, FAR_LNG = 85.0, 0.0


# -------------------- Helpers --------------------

async def _insert_paid_pending_order():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    oid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": oid,
        "customer_id": "TEST_customer_atomic",
        "business_id": "TEST_business_atomic",
        "items": [{"product_id": "p1", "product_name": "TEST atomic item", "price": 5.0, "quantity": 1}],
        "total_amount": 5.0,
        "delivery_address": "TEST atomic addr",
        "status": "pending",
        "payment_status": "paid",
        "driver_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.orders.insert_one(doc)
    client.close()
    return oid


async def _delete_order(order_id):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.orders.delete_one({"id": order_id})
    client.close()


async def _get_driver(driver_id):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    doc = await db.users.find_one({"id": driver_id}, {"_id": 0})
    client.close()
    return doc


async def _release_all_drivers():
    """Reset all bees to available and the 'Repartidor Real' back to offline (cleanup)."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.users.update_many(
        {"role": "driver", "email": {"$regex": "^bee\\."}},
        {"$set": {"is_available": True, "status": "available"}},
    )
    # Repartidor Real may have been incidentally claimed by a test; restore to offline
    await db.users.update_one(
        {"email": "driver.real@nubotest.com"},
        {"$set": {"is_available": False, "status": "offline"}},
    )
    client.close()


async def _find_order(oid):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    doc = await db.orders.find_one({"id": oid}, {"_id": 0})
    client.close()
    return doc


# -------------------- Fixtures --------------------

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
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(autouse=True)
def _reset_bees():
    """Make sure all demo bees are available before each test, and again at the end."""
    asyncio.run(_release_all_drivers())
    yield
    asyncio.run(_release_all_drivers())


# -------------------- Tests --------------------

class TestAtomicAssignment:
    """Atomic claim of the nearest driver: is_available->False, status='busy'."""

    def test_assign_nearest_marks_driver_busy_and_hides_from_nearest(self, session, admin_headers):
        order_id = asyncio.run(_insert_paid_pending_order())
        try:
            r = session.post(
                f"{API}/orders/{order_id}/assign-nearest",
                json={"lat": MADRID_LAT, "lng": MADRID_LNG},
                headers=admin_headers, timeout=15,
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["order_id"] == order_id
            assert "driver" in body and body["driver"].get("id")
            chosen_id = body["driver"]["id"]
            # Madrid is closest -> distance ~0
            assert body["driver"]["distance_km"] < 5.0
            assert "Madrid" in body["driver"]["name"]

            # DB-side: driver is busy + unavailable
            drv = asyncio.run(_get_driver(chosen_id))
            assert drv is not None
            assert drv.get("is_available") is False, f"Driver still available: {drv}"
            assert drv.get("status") == "busy", f"Driver status not 'busy': {drv.get('status')}"

            # /api/drivers/nearest must not list this driver anymore
            r2 = session.get(
                f"{API}/drivers/nearest",
                params={"lat": MADRID_LAT, "lng": MADRID_LNG, "limit": 20},
                headers=admin_headers, timeout=15,
            )
            assert r2.status_code == 200, r2.text
            ids = [d["id"] for d in r2.json().get("drivers", [])]
            assert chosen_id not in ids, f"Busy driver leaked into /drivers/nearest: {ids}"
        finally:
            asyncio.run(_delete_order(order_id))

    def test_no_double_assignment_to_same_driver(self, session, admin_headers):
        """Two orders assigned in a row at Madrid coords must go to DIFFERENT drivers."""
        oid1 = asyncio.run(_insert_paid_pending_order())
        oid2 = asyncio.run(_insert_paid_pending_order())
        try:
            r1 = session.post(
                f"{API}/orders/{oid1}/assign-nearest",
                json={"lat": MADRID_LAT, "lng": MADRID_LNG},
                headers=admin_headers, timeout=15,
            )
            assert r1.status_code == 200, r1.text
            d1 = r1.json()["driver"]["id"]

            r2 = session.post(
                f"{API}/orders/{oid2}/assign-nearest",
                json={"lat": MADRID_LAT, "lng": MADRID_LNG},
                headers=admin_headers, timeout=15,
            )
            # Either it assigns a DIFFERENT bee (200) or 404 if Madrid is the only one
            assert r2.status_code in (200, 404), r2.text
            if r2.status_code == 200:
                d2 = r2.json()["driver"]["id"]
                assert d2 != d1, "Same driver assigned twice (race not prevented!)"
        finally:
            asyncio.run(_delete_order(oid1))
            asyncio.run(_delete_order(oid2))

    def test_already_assigned_returns_400(self, session, admin_headers):
        oid = asyncio.run(_insert_paid_pending_order())
        try:
            r1 = session.post(
                f"{API}/orders/{oid}/assign-nearest",
                json={"lat": MADRID_LAT, "lng": MADRID_LNG},
                headers=admin_headers, timeout=15,
            )
            assert r1.status_code == 200, r1.text
            r2 = session.post(
                f"{API}/orders/{oid}/assign-nearest",
                json={"lat": MADRID_LAT, "lng": MADRID_LNG},
                headers=admin_headers, timeout=15,
            )
            assert r2.status_code == 400, r2.text
            assert "already" in r2.text.lower()
        finally:
            asyncio.run(_delete_order(oid))

    def test_no_drivers_nearby_returns_404(self, session, admin_headers):
        oid = asyncio.run(_insert_paid_pending_order())
        try:
            r = session.post(
                f"{API}/orders/{oid}/assign-nearest",
                json={"lat": FAR_LAT, "lng": FAR_LNG, "max_km": 50},
                headers=admin_headers, timeout=15,
            )
            assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"
            assert "no available" in r.text.lower()
        finally:
            asyncio.run(_delete_order(oid))


class TestDriverRelease:
    """Driver must be freed on delivered / cancelled / return-to-queue."""

    def test_release_on_delivered(self, session, admin_headers):
        oid = asyncio.run(_insert_paid_pending_order())
        try:
            r = session.post(
                f"{API}/orders/{oid}/assign-nearest",
                json={"lat": MADRID_LAT, "lng": MADRID_LNG},
                headers=admin_headers, timeout=15,
            )
            assert r.status_code == 200, r.text
            chosen_id = r.json()["driver"]["id"]

            # Driver should be busy now
            drv = asyncio.run(_get_driver(chosen_id))
            assert drv["is_available"] is False and drv["status"] == "busy"

            # Mark delivered (admin)
            r2 = session.patch(
                f"{API}/orders/{oid}/status",
                json={"status": "delivered"},
                headers=admin_headers, timeout=15,
            )
            assert r2.status_code == 200, r2.text

            # Driver released
            drv2 = asyncio.run(_get_driver(chosen_id))
            assert drv2["is_available"] is True, f"Driver not released on delivered: {drv2}"
            assert drv2["status"] == "available", f"Driver status not 'available': {drv2['status']}"

            # And reappears in /drivers/nearest
            r3 = session.get(
                f"{API}/drivers/nearest",
                params={"lat": MADRID_LAT, "lng": MADRID_LNG, "limit": 20},
                headers=admin_headers, timeout=15,
            )
            assert r3.status_code == 200
            ids = [d["id"] for d in r3.json().get("drivers", [])]
            assert chosen_id in ids, f"Released driver missing from /drivers/nearest: {ids}"
        finally:
            asyncio.run(_delete_order(oid))

    def test_release_on_cancelled(self, session, admin_headers):
        oid = asyncio.run(_insert_paid_pending_order())
        try:
            r = session.post(
                f"{API}/orders/{oid}/assign-nearest",
                json={"lat": MADRID_LAT, "lng": MADRID_LNG},
                headers=admin_headers, timeout=15,
            )
            assert r.status_code == 200, r.text
            chosen_id = r.json()["driver"]["id"]

            r2 = session.patch(
                f"{API}/orders/{oid}/status",
                json={"status": "cancelled"},
                headers=admin_headers, timeout=15,
            )
            assert r2.status_code == 200, r2.text

            drv2 = asyncio.run(_get_driver(chosen_id))
            assert drv2["is_available"] is True
            assert drv2["status"] == "available"
        finally:
            asyncio.run(_delete_order(oid))

    def test_return_to_queue_releases_driver_and_repends_order(self, session, admin_headers):
        oid = asyncio.run(_insert_paid_pending_order())
        try:
            r = session.post(
                f"{API}/orders/{oid}/assign-nearest",
                json={"lat": MADRID_LAT, "lng": MADRID_LNG},
                headers=admin_headers, timeout=15,
            )
            assert r.status_code == 200, r.text
            chosen_id = r.json()["driver"]["id"]

            r2 = session.post(
                f"{API}/orders/{oid}/return-to-queue",
                headers=admin_headers, timeout=15,
            )
            assert r2.status_code == 200, r2.text

            # Driver released
            drv2 = asyncio.run(_get_driver(chosen_id))
            assert drv2["is_available"] is True
            assert drv2["status"] == "available"

            # Order is pending again with driver_id=None
            order = asyncio.run(_find_order(oid))
            assert order["status"] == "pending"
            assert order.get("driver_id") in (None, "")
        finally:
            asyncio.run(_delete_order(oid))

    def test_return_to_queue_400_when_no_driver(self, session, admin_headers):
        oid = asyncio.run(_insert_paid_pending_order())
        try:
            r = session.post(
                f"{API}/orders/{oid}/return-to-queue",
                headers=admin_headers, timeout=15,
            )
            assert r.status_code == 400, r.text
        finally:
            asyncio.run(_delete_order(oid))
