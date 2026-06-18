"""Tests for the BLOQUE B public order tracking endpoint (no auth).

Coverage:
- GET /api/public/orders/{order_id}/tracking returns 404 for unknown ids.
- Creating an express order via /api/orders/express + tracking it publicly
  returns origin/destination/price/currency/status/order_id.
- Endpoint does NOT require Authorization header.
- driver_location is null when no driver is assigned and no WS live location exists.
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASS = "Test1234!"


@pytest.fixture(scope="module")
def customer_token():
    r = requests.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASS})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def express_order(customer_token):
    payload = {
        "vehicle_type": "moto",
        "origin_name": "TEST_ORIGIN Madrid",
        "origin_lat": 40.4168,
        "origin_lng": -3.7038,
        "destination_name": "TEST_DEST Tanger",
        "destination_lat": 35.7595,
        "destination_lng": -5.834,
        "fee": 42.5,
        "currency": "EUR",
        "distance_km": 870,
        "eta_mins": 720,
    }
    r = requests.post(
        f"{API}/orders/express",
        headers={"Authorization": f"Bearer {customer_token}"},
        json=payload,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_tracking_not_found_returns_404():
    bogus = f"NOPE-{uuid.uuid4().hex[:8]}"
    r = requests.get(f"{API}/public/orders/{bogus}/tracking")
    assert r.status_code == 404


def test_tracking_does_not_require_auth(express_order):
    # explicitly no Authorization header
    r = requests.get(f"{API}/public/orders/{express_order['id']}/tracking")
    assert r.status_code == 200, r.text


def test_tracking_returns_full_payload(express_order):
    r = requests.get(f"{API}/public/orders/{express_order['id']}/tracking")
    assert r.status_code == 200
    data = r.json()

    # Keys contract
    for k in (
        "order_id", "status", "origin", "destination", "price",
        "currency", "driver_name", "driver_vehicle_type", "driver_location",
    ):
        assert k in data, f"missing key: {k}"

    assert data["order_id"] == express_order["id"]
    assert data["status"] in ("pending", "accepted", "in_progress", "delivered")
    assert data["price"] == 42.5
    assert data["currency"] == "EUR"

    # Origin / destination shape
    assert data["origin"]["lat"] == 40.4168
    assert data["origin"]["lng"] == -3.7038
    assert data["origin"]["label"] == "TEST_ORIGIN Madrid"
    assert data["destination"]["lat"] == 35.7595
    assert data["destination"]["lng"] == -5.834
    assert data["destination"]["label"] == "TEST_DEST Tanger"

    # No driver assigned yet
    assert data["driver_name"] is None
    assert data["driver_vehicle_type"] is None
    assert data["driver_location"] is None


def test_tracking_response_excludes_mongo_id(express_order):
    r = requests.get(f"{API}/public/orders/{express_order['id']}/tracking")
    assert r.status_code == 200
    assert "_id" not in r.json()
