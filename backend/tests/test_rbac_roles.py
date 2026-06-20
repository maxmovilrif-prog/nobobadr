"""Tests de segregación de roles (RBAC): Fundador vs Gestor.

- El Fundador (admin) crea cuentas de Gestor (manager) con email+password.
- El Gestor entra por /auth/login y SOLO accede a Operaciones (pedidos, despacho, tarifas).
- El Gestor está BLOQUEADO (403) en Finanzas, KPIs, alta de Riders y gestión de Gestores.
- Email duplicado al crear Gestor -> 400.
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
ADMIN_EMAIL, ADMIN_PASS = "badarbox1756@gmail.com", "Admin1234!"
CUSTOMER_EMAIL, CUSTOMER_PASS = "qa_customer@nubo.com", "Test1234!"


def _token(email, pwd):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASS)}"}


@pytest.fixture(scope="module")
def region(admin_h):
    cities = requests.get(f"{API}/public/cities").json()
    cities = cities if isinstance(cities, list) else cities.get("cities", [])
    city_ids = [c["id"] for c in cities[:2]]
    r = requests.post(f"{API}/admin/regions", headers=admin_h,
                      json={"name": f"QA Región {uuid.uuid4().hex[:6]}", "city_ids": city_ids})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def manager(admin_h, region):
    email = f"gestor_{uuid.uuid4().hex[:8]}@nubo.com"
    pwd = "Gestor1234"
    r = requests.post(f"{API}/admin/managers", headers=admin_h,
                      json={"name": "QA Gestor", "email": email, "password": pwd, "region_id": region["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "manager"
    assert r.json()["region_id"] == region["id"]
    assert "password_hash" not in r.json()
    h = {"Authorization": f"Bearer {_token(email, pwd)}"}
    return {"email": email, "id": r.json()["id"], "h": h, "region_id": region["id"]}


def test_founder_creates_and_lists_manager(admin_h, manager):
    r = requests.get(f"{API}/admin/managers", headers=admin_h)
    assert r.status_code == 200
    assert any(m["id"] == manager["id"] for m in r.json()["managers"])


def test_duplicate_manager_email_rejected(admin_h, manager, region):
    r = requests.post(f"{API}/admin/managers", headers=admin_h,
                      json={"name": "Dup", "email": manager["email"], "password": "Otra1234", "region_id": region["id"]})
    assert r.status_code == 400


@pytest.mark.parametrize("path", [
    "/admin/ops/orders", "/admin/stats", "/admin/active-drivers", "/admin/assignment-history",
])
def test_manager_can_access_operations(manager, path):
    r = requests.get(f"{API}{path}", headers=manager["h"])
    assert r.status_code == 200, f"{path} -> {r.status_code}"


@pytest.mark.parametrize("path", [
    "/admin/kpis", "/accounting/transactions/summary", "/admin/finances/summary",
    "/accounting/cash/balance", "/admin/managers",
])
def test_manager_blocked_from_finance_and_admin(manager, path):
    r = requests.get(f"{API}{path}", headers=manager["h"])
    assert r.status_code == 403, f"{path} -> {r.status_code} (debería ser 403)"


def test_manager_can_manage_own_riders_but_not_managers(manager):
    # El Gestor SÍ puede crear riders en SU delegación (quedan vinculados a su región)
    r = requests.post(f"{API}/admin/riders", headers=manager["h"],
                      json={"name": "Rider QA", "phone": "600000000", "vehicle_type": "car"})
    assert r.status_code == 200, r.text
    assert r.json()["region_id"] == manager["region_id"]
    # Pero NO puede crear cuentas de Gestor (solo el Fundador)
    r = requests.post(f"{API}/admin/managers", headers=manager["h"],
                      json={"name": "y", "email": "z@z.com", "password": "123456", "region_id": manager["region_id"]})
    assert r.status_code == 403


def test_manager_can_dispatch(manager):
    # acceso al endpoint de despacho (404 porque el pedido no existe, NO 403)
    r = requests.post(f"{API}/orders/NOPE-{uuid.uuid4().hex[:6]}/assign-nearest",
                      headers=manager["h"], json={})
    assert r.status_code == 404


def test_customer_cannot_create_managers():
    h = {"Authorization": f"Bearer {_token(CUSTOMER_EMAIL, CUSTOMER_PASS)}"}
    r = requests.post(f"{API}/admin/managers", headers=h,
                      json={"name": "x", "email": "a@b.com", "password": "123456"})
    assert r.status_code == 403


def test_delete_manager(admin_h, region):
    email = f"gestor_del_{uuid.uuid4().hex[:8]}@nubo.com"
    r = requests.post(f"{API}/admin/managers", headers=admin_h,
                      json={"name": "Para Borrar", "email": email, "password": "Borrar1234", "region_id": region["id"]})
    mid = r.json()["id"]
    r = requests.delete(f"{API}/admin/managers/{mid}", headers=admin_h)
    assert r.status_code == 200
    r = requests.delete(f"{API}/admin/managers/{mid}", headers=admin_h)
    assert r.status_code == 404
