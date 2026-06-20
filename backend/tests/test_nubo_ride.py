"""Tests de Nubo Ride (transporte de pasajeros): ciclo completo + RBAC + aislamiento."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
ADMIN_EMAIL, ADMIN_PASS = "badarbox1756@gmail.com", "Admin1234!"
CUSTOMER_EMAIL, CUSTOMER_PASS = "qa_customer@nubo.com", "Test1234!"

ORIGIN = {"lat": 36.1408, "lng": -5.4562}
DEST = {"lat": 36.1850, "lng": -5.4000}


def _token(email, pwd):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_h():
    return _h(_token(ADMIN_EMAIL, ADMIN_PASS))


@pytest.fixture(scope="module")
def customer_h():
    return _h(_token(CUSTOMER_EMAIL, CUSTOMER_PASS))


@pytest.fixture(scope="module")
def driver_h(admin_h):
    """Crea un rider de prueba vía admin y lo activa para obtener token de conductor."""
    r = requests.post(f"{API}/admin/riders", headers=admin_h, json={
        "name": f"RideQA {uuid.uuid4().hex[:5]}", "phone": "600000000", "vehicle_type": "car",
    })
    assert r.status_code == 200, r.text
    code = r.json()["activation_code"]
    act = requests.post(f"{API}/rider/activate", json={"code": code})
    assert act.status_code == 200, act.text
    return _h(act.json()["token"])


def _clear_active(customer_h):
    """Cancela cualquier viaje activo del cliente para empezar limpio."""
    a = requests.get(f"{API}/rides/active", headers=customer_h).json()
    if a.get("ride"):
        requests.post(f"{API}/rides/{a['ride']['id']}/cancel", headers=customer_h, json={"reason": "cleanup"})


def test_estimate_returns_three_tiers(customer_h):
    r = requests.post(f"{API}/rides/estimate", headers=customer_h, json={
        "origin_lat": ORIGIN["lat"], "origin_lng": ORIGIN["lng"],
        "destination_lat": DEST["lat"], "destination_lng": DEST["lng"], "currency": "EUR",
    })
    assert r.status_code == 200, r.text
    opts = r.json()["options"]
    assert {o["vehicle_type"] for o in opts} == {"economy", "comfort", "xl"}
    assert all(o["estimated_price"] > 0 for o in opts)


def test_full_ride_lifecycle(customer_h, driver_h):
    _clear_active(customer_h)
    # 1) Cliente solicita
    req = requests.post(f"{API}/rides/request", headers=customer_h, json={
        "origin_lat": ORIGIN["lat"], "origin_lng": ORIGIN["lng"], "origin_label": "A",
        "destination_lat": DEST["lat"], "destination_lng": DEST["lng"], "destination_label": "B",
        "vehicle_type": "economy", "currency": "EUR",
    })
    assert req.status_code == 200, req.text
    ride = req.json()
    assert ride["estado"] == "buscando"
    rid = ride["id"]

    # 2) Conductor acepta
    acc = requests.post(f"{API}/rides/accept", headers=driver_h, json={"ride_id": rid})
    assert acc.status_code == 200, acc.text
    assert acc.json()["estado"] == "aceptado"

    # Segundo accept -> 409
    acc2 = requests.post(f"{API}/rides/accept", headers=driver_h, json={"ride_id": rid})
    assert acc2.status_code in (400, 409)

    # 3) Iniciar
    st = requests.post(f"{API}/rides/{rid}/start", headers=driver_h)
    assert st.status_code == 200, st.text
    assert st.json()["estado"] == "en_curso"

    # 4) Completar
    comp = requests.post(f"{API}/rides/{rid}/complete", headers=driver_h)
    assert comp.status_code == 200, comp.text
    assert comp.json()["estado"] == "completado"


def test_request_requires_customer(driver_h):
    r = requests.post(f"{API}/rides/request", headers=driver_h, json={
        "origin_lat": ORIGIN["lat"], "origin_lng": ORIGIN["lng"],
        "destination_lat": DEST["lat"], "destination_lng": DEST["lng"],
    })
    assert r.status_code == 403


def test_accept_requires_driver(customer_h):
    r = requests.post(f"{API}/rides/accept", headers=customer_h, json={"ride_id": "x"})
    assert r.status_code == 403


def test_customer_cancel(customer_h):
    _clear_active(customer_h)
    req = requests.post(f"{API}/rides/request", headers=customer_h, json={
        "origin_lat": ORIGIN["lat"], "origin_lng": ORIGIN["lng"],
        "destination_lat": DEST["lat"], "destination_lng": DEST["lng"], "vehicle_type": "comfort",
    })
    assert req.status_code == 200, req.text
    rid = req.json()["id"]
    can = requests.post(f"{API}/rides/{rid}/cancel", headers=customer_h, json={"reason": "ya no lo necesito"})
    assert can.status_code == 200, can.text
    assert can.json()["estado"] == "cancelado"


def test_no_duplicate_active_ride(customer_h):
    _clear_active(customer_h)
    body = {
        "origin_lat": ORIGIN["lat"], "origin_lng": ORIGIN["lng"],
        "destination_lat": DEST["lat"], "destination_lng": DEST["lng"], "vehicle_type": "economy",
    }
    r1 = requests.post(f"{API}/rides/request", headers=customer_h, json=body)
    assert r1.status_code == 200, r1.text
    r2 = requests.post(f"{API}/rides/request", headers=customer_h, json=body)
    assert r2.status_code == 400
    _clear_active(customer_h)


def test_admin_sees_active_rides(customer_h, admin_h):
    _clear_active(customer_h)
    requests.post(f"{API}/rides/request", headers=customer_h, json={
        "origin_lat": ORIGIN["lat"], "origin_lng": ORIGIN["lng"],
        "destination_lat": DEST["lat"], "destination_lng": DEST["lng"], "vehicle_type": "economy",
    })
    r = requests.get(f"{API}/rides/active", headers=admin_h)
    assert r.status_code == 200, r.text
    assert "rides" in r.json()
    _clear_active(customer_h)
