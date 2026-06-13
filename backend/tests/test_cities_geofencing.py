"""Backend tests for Cities + Geofencing feature."""
import os
import asyncio
import uuid
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

CUSTOMER = {"email": "cliente@nubotest.com", "password": "Cliente123!"}
DRIVER = {"email": "driver.real@nubotest.com", "password": "Driver123!"}

# Coordinates
TANGER = (35.7595, -5.8340)
CASABLANCA = (33.5731, -7.5898)
MADRID = (40.4168, -3.7038)


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="module")
def customer_token():
    return _login(CUSTOMER)


@pytest.fixture(scope="module")
def driver_token():
    return _login(DRIVER)


@pytest.fixture(scope="module")
def cities(customer_token):
    r = requests.get(f"{API}/cities",
                     headers={"Authorization": f"Bearer {customer_token}"},
                     timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "cities" in data and isinstance(data["cities"], list)
    return data["cities"]


# ============== /api/cities ==============
class TestCities:
    def test_cities_returns_4_seeded(self, cities):
        names = sorted([c["name"] for c in cities])
        assert names == sorted(["Tánger", "Casablanca", "Meknes", "Nador"]), f"Got {names}"

    def test_cities_have_required_fields(self, cities):
        for c in cities:
            assert "id" in c and isinstance(c["id"], str)
            assert "name" in c
            assert "lat" in c and isinstance(c["lat"], (int, float))
            assert "lng" in c and isinstance(c["lng"], (int, float))

    def test_cities_no_mongo_id(self, cities):
        for c in cities:
            assert "_id" not in c

    def test_cities_requires_auth(self):
        r = requests.get(f"{API}/cities", timeout=15)
        assert r.status_code in (401, 403)


# ============== Order create with city_id ==============
class TestOrderWithCity:
    def test_create_order_resolves_city_name(self, customer_token, cities):
        tanger = next(c for c in cities if c["name"] == "Tánger")
        payload = {
            "business_id": "TEST_rest_city",
            "items": [{"product_id": "p1", "product_name": "TEST item", "price": 5.0, "quantity": 1}],
            "delivery_address": "TEST addr",
            "city_id": tanger["id"],
        }
        r = requests.post(f"{API}/orders", json=payload,
                          headers={"Authorization": f"Bearer {customer_token}"},
                          timeout=15)
        assert r.status_code == 200, r.text
        order = r.json()
        assert order["city_id"] == tanger["id"]
        assert order["city_name"] == "Tánger"

        # Cleanup
        asyncio.run(_cleanup_order(order["id"]))

    def test_create_order_without_city(self, customer_token):
        payload = {
            "business_id": "TEST_rest_nocity",
            "items": [{"product_id": "p1", "product_name": "TEST item", "price": 5.0, "quantity": 1}],
            "delivery_address": "TEST addr",
        }
        r = requests.post(f"{API}/orders", json=payload,
                          headers={"Authorization": f"Bearer {customer_token}"},
                          timeout=15)
        assert r.status_code == 200, r.text
        order = r.json()
        assert order.get("city_id") is None
        assert order.get("city_name") is None

        asyncio.run(_cleanup_order(order["id"]))


# ============== Geofencing ==============
async def _cleanup_order(order_id):
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    await db.orders.delete_one({'id': order_id})
    client.close()


async def _insert_paid_pending(city_id):
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    oid = str(uuid.uuid4())
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        'id': oid,
        'customer_id': 'TEST_customer_geo',
        'business_id': 'TEST_business_geo',
        'items': [{'product_id': 'p1', 'product_name': 'TEST geo item', 'price': 9.99, 'quantity': 1}],
        'total_amount': 9.99,
        'delivery_address': 'TEST geo addr',
        'status': 'pending',
        'payment_status': 'paid',
        'driver_id': None,
        'city_id': city_id,
        'created_at': now,
        'updated_at': now,
    }
    if city_id:
        city = await db.cities.find_one({'id': city_id}, {'_id': 0, 'name': 1})
        doc['city_name'] = city['name'] if city else None
    await db.orders.insert_one(doc)
    client.close()
    return oid


def _set_driver_loc(token, lat, lng):
    r = requests.patch(f"{API}/drivers/location",
                       json={"lat": lat, "lng": lng},
                       headers={"Authorization": f"Bearer {token}"},
                       timeout=15)
    assert r.status_code == 200, r.text


class TestGeofencingAvailableOrders:
    def test_driver_near_tanger_sees_tanger_order(self, driver_token, cities):
        tanger = next(c for c in cities if c["name"] == "Tánger")
        oid_tanger = asyncio.run(_insert_paid_pending(tanger["id"]))
        oid_nocity = asyncio.run(_insert_paid_pending(None))
        try:
            _set_driver_loc(driver_token, TANGER[0], TANGER[1])
            r = requests.get(f"{API}/drivers/available-orders",
                             headers={"Authorization": f"Bearer {driver_token}"},
                             timeout=15)
            assert r.status_code == 200
            ids = [o["id"] for o in r.json()]
            assert oid_tanger in ids, "Driver near Tánger should see Tánger order"
            assert oid_nocity in ids, "Driver near Tánger should also see no-city orders"
        finally:
            asyncio.run(_cleanup_order(oid_tanger))
            asyncio.run(_cleanup_order(oid_nocity))

    def test_driver_far_madrid_does_not_see_tanger_order(self, driver_token, cities):
        tanger = next(c for c in cities if c["name"] == "Tánger")
        oid_tanger = asyncio.run(_insert_paid_pending(tanger["id"]))
        oid_nocity = asyncio.run(_insert_paid_pending(None))
        try:
            _set_driver_loc(driver_token, MADRID[0], MADRID[1])
            r = requests.get(f"{API}/drivers/available-orders",
                             headers={"Authorization": f"Bearer {driver_token}"},
                             timeout=15)
            assert r.status_code == 200
            ids = [o["id"] for o in r.json()]
            assert oid_tanger not in ids, "Driver in Madrid must NOT see Tánger order"
            assert oid_nocity in ids, "Driver out of zone should still see no-city orders"
        finally:
            asyncio.run(_cleanup_order(oid_tanger))
            asyncio.run(_cleanup_order(oid_nocity))

    def test_driver_in_casablanca_does_not_see_tanger_order(self, driver_token, cities):
        tanger = next(c for c in cities if c["name"] == "Tánger")
        oid_tanger = asyncio.run(_insert_paid_pending(tanger["id"]))
        try:
            _set_driver_loc(driver_token, CASABLANCA[0], CASABLANCA[1])
            r = requests.get(f"{API}/drivers/available-orders",
                             headers={"Authorization": f"Bearer {driver_token}"},
                             timeout=15)
            assert r.status_code == 200
            ids = [o["id"] for o in r.json()]
            assert oid_tanger not in ids, "Driver in Casablanca must NOT see Tánger order"
        finally:
            asyncio.run(_cleanup_order(oid_tanger))
