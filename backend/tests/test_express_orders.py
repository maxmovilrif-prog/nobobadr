"""Backend tests for POST /api/orders/express (mensajería A→B exprés).

Cubre:
- Auth obligatoria (401 sin token)
- 403 para roles driver y business
- 200 para customer con todos los campos persistidos
- city_name se resuelve desde origin_city_id
- El pedido exprés aparece en GET /api/orders del cliente que lo creó
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nubo-express-preview.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CUSTOMER = {"email": "cliente@nubotest.com", "password": "Cliente123!"}
DRIVER = {"email": "bee.madrid@nuboexpress.com", "password": "Bee123!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    if r.status_code != 200:
        return None
    return r.json().get("token")


@pytest.fixture(scope="module")
def customer_token():
    tok = _login(CUSTOMER)
    if not tok:
        pytest.skip("No se pudo iniciar sesión como cliente")
    return tok


@pytest.fixture(scope="module")
def driver_token():
    tok = _login(DRIVER)
    if not tok:
        pytest.skip("No se pudo iniciar sesión como driver")
    return tok


@pytest.fixture(scope="module")
def business_token():
    # Try to create a business account on the fly
    email = "TEST_biz_express@nubotest.com"
    password = "Business123!"
    requests.post(f"{API}/auth/register", json={
        "email": email,
        "password": password,
        "name": "TEST Express Biz",
        "phone": "+34000000000",
        "role": "business",
    }, timeout=20)
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        pytest.skip("No se pudo crear/iniciar sesión como business")
    return r.json().get("token")


@pytest.fixture(scope="module")
def madrid_city_id():
    # Get a real Madrid city id from the public cities endpoint
    r = requests.get(f"{API}/public/cities", timeout=20)
    if r.status_code != 200:
        return None
    data = r.json()
    cities = data.get("cities") if isinstance(data, dict) else data
    if not cities:
        return None
    for c in cities:
        if (c.get("name") or "").lower() == "madrid":
            return c.get("id")
    return cities[0].get("id")


def _payload(city_id=None):
    return {
        "origin_name": "Tánger",
        "origin_lat": 35.7595,
        "origin_lng": -5.834,
        "destination_name": "Madrid",
        "destination_lat": 40.4168,
        "destination_lng": -3.7038,
        "origin_city_id": city_id,
        "vehicle_type": "motorcycle",
        "fee": 12.5,
        "currency": "EUR",
        "distance_km": 620,
        "eta_mins": 45,
    }


# --- 1. Auth ---
def test_express_requires_auth():
    r = requests.post(f"{API}/orders/express", json=_payload(), timeout=20)
    assert r.status_code in (401, 403), f"Esperado 401/403 sin token, obtenido {r.status_code}: {r.text[:200]}"


# --- 2. Solo customers pueden crear ---
def test_express_driver_forbidden(driver_token):
    r = requests.post(
        f"{API}/orders/express",
        json=_payload(),
        headers={"Authorization": f"Bearer {driver_token}"},
        timeout=20,
    )
    assert r.status_code == 403, f"Driver debería recibir 403, obtuvo {r.status_code}: {r.text[:200]}"


def test_express_business_forbidden(business_token):
    r = requests.post(
        f"{API}/orders/express",
        json=_payload(),
        headers={"Authorization": f"Bearer {business_token}"},
        timeout=20,
    )
    assert r.status_code == 403, f"Business debería recibir 403, obtuvo {r.status_code}: {r.text[:200]}"


# --- 3. Customer crea pedido exprés ---
def test_express_customer_creates_order(customer_token, madrid_city_id):
    payload = _payload(city_id=madrid_city_id)
    r = requests.post(
        f"{API}/orders/express",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"},
        timeout=30,
    )
    assert r.status_code == 200, f"Esperado 200, obtenido {r.status_code}: {r.text[:300]}"
    order = r.json()

    assert order.get("order_type") == "express"
    assert order.get("business_id") in (None, ""), f"business_id debería ser null, es {order.get('business_id')}"
    assert order.get("items") == []
    assert order.get("total_amount") == payload["fee"]
    assert order.get("delivery_address") == payload["destination_name"]
    assert order.get("vehicle_type") == "motorcycle"
    assert order.get("origin_name") == payload["origin_name"]
    assert order.get("origin_lat") == payload["origin_lat"]
    assert order.get("origin_lng") == payload["origin_lng"]
    assert order.get("destination_lat") == payload["destination_lat"]
    assert order.get("destination_lng") == payload["destination_lng"]
    assert order.get("distance_km") == payload["distance_km"]
    assert order.get("eta_mins") == payload["eta_mins"]
    assert order.get("currency") == "EUR"
    assert order.get("status") == "pending"
    assert "id" in order and isinstance(order["id"], str)

    # city_name resuelto desde origin_city_id
    if madrid_city_id:
        assert order.get("city_id") == madrid_city_id
        assert order.get("city_name") is not None and order["city_name"] != ""

    pytest.last_express_order_id = order["id"]


# --- 4. El pedido aparece en GET /api/orders del cliente ---
def test_express_appears_in_customer_orders(customer_token):
    order_id = getattr(pytest, "last_express_order_id", None)
    if not order_id:
        pytest.skip("No hay pedido creado previo")
    r = requests.get(
        f"{API}/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        timeout=20,
    )
    assert r.status_code == 200, f"GET /orders falló: {r.status_code}"
    orders = r.json()
    assert isinstance(orders, list)
    match = [o for o in orders if o.get("id") == order_id]
    assert len(match) == 1, f"El pedido exprés {order_id} no aparece en GET /api/orders del cliente"
    o = match[0]
    assert o.get("order_type") == "express"
    assert o.get("business_id") in (None, "")


# --- 5. city_name None cuando origin_city_id es inválido ---
def test_express_invalid_city_id_returns_null_city_name(customer_token):
    payload = _payload(city_id="non-existent-uuid-123")
    r = requests.post(
        f"{API}/orders/express",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"},
        timeout=20,
    )
    assert r.status_code == 200
    order = r.json()
    assert order.get("city_id") == "non-existent-uuid-123"
    assert order.get("city_name") in (None, "")


# --- 6. Sin origin_city_id, city_name es None ---
def test_express_no_city_id(customer_token):
    payload = _payload(city_id=None)
    r = requests.post(
        f"{API}/orders/express",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"},
        timeout=20,
    )
    assert r.status_code == 200
    order = r.json()
    assert order.get("city_id") in (None, "")
    assert order.get("city_name") in (None, "")
