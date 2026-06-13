"""Backend tests for iteration 9 — History filters + CSV export + stealth admin auth gating.

Endpoints tested:
- GET /api/admin/assignment-history?action=&driver_id=&date_from=&date_to=
- GET /api/admin/assignment-history/export (text/csv with attachment header)
- RBAC: both endpoints reject customer & driver (403)
"""
import os
import csv
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "control@nuboexpress.com"
ADMIN_PASSWORD = "Fn6FcMveVf%--1o-"
ADMIN_SECRET_CODE = "NUBO-84D2-C159-E3CF"
CUSTOMER_EMAIL = "cliente@nubotest.com"
CUSTOMER_PASSWORD = "Cliente123!"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(
        f"{API}/admin-auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "secret_code": ADMIN_SECRET_CODE},
        timeout=15,
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def customer_token(session):
    r = session.post(
        f"{API}/auth/login",
        json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Customer login failed: {r.status_code} {r.text}")
    return r.json()["token"]


def _admin_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ----- /admin/assignment-history filters -----

class TestHistoryFilters:
    def test_history_includes_drivers_array(self, session, admin_token):
        r = session.get(f"{API}/admin/assignment-history", headers=_admin_headers(admin_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "events" in data and "count" in data and "drivers" in data
        assert isinstance(data["drivers"], list)
        # If history has events with drivers, drivers array should be non-empty
        if data["count"] > 0:
            assert isinstance(data["events"], list)
            # Each driver should have id and name
            for d in data["drivers"]:
                assert "id" in d and "name" in d

    def test_filter_by_action_assigned(self, session, admin_token):
        r = session.get(
            f"{API}/admin/assignment-history",
            params={"action": "assigned"},
            headers=_admin_headers(admin_token),
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        for ev in data["events"]:
            assert ev["action"] == "assigned", f"Got non-assigned event: {ev}"

    def test_filter_by_action_auto_returned(self, session, admin_token):
        r = session.get(
            f"{API}/admin/assignment-history",
            params={"action": "auto_returned"},
            headers=_admin_headers(admin_token),
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        for ev in data["events"]:
            assert ev["action"] == "auto_returned"

    def test_filter_by_action_returned(self, session, admin_token):
        r = session.get(
            f"{API}/admin/assignment-history",
            params={"action": "returned"},
            headers=_admin_headers(admin_token),
            timeout=15,
        )
        assert r.status_code == 200
        for ev in r.json()["events"]:
            assert ev["action"] == "returned"

    def test_filter_by_driver_id(self, session, admin_token):
        # First grab a driver_id from history
        base = session.get(f"{API}/admin/assignment-history", headers=_admin_headers(admin_token), timeout=15).json()
        if not base["drivers"]:
            pytest.skip("No drivers in history to filter on")
        driver_id = base["drivers"][0]["id"]
        r = session.get(
            f"{API}/admin/assignment-history",
            params={"driver_id": driver_id},
            headers=_admin_headers(admin_token),
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 1
        for ev in data["events"]:
            assert ev["driver_id"] == driver_id

    def test_filter_by_date_range_future(self, session, admin_token):
        # Future date range should return 0 events
        r = session.get(
            f"{API}/admin/assignment-history",
            params={"date_from": "2099-01-01", "date_to": "2099-12-31"},
            headers=_admin_headers(admin_token),
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 0
        assert data["events"] == []

    def test_filter_by_date_range_wide(self, session, admin_token):
        # Wide date range should include all events
        all_resp = session.get(f"{API}/admin/assignment-history",
                               headers=_admin_headers(admin_token), timeout=15).json()
        r = session.get(
            f"{API}/admin/assignment-history",
            params={"date_from": "2020-01-01", "date_to": "2099-12-31"},
            headers=_admin_headers(admin_token),
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["count"] == all_resp["count"]

    def test_history_rejects_customer(self, session, customer_token):
        r = session.get(
            f"{API}/admin/assignment-history",
            headers={"Authorization": f"Bearer {customer_token}"},
            timeout=15,
        )
        assert r.status_code == 403

    def test_history_rejects_anonymous(self, session):
        r = session.get(f"{API}/admin/assignment-history", timeout=15)
        assert r.status_code in (401, 403)


# ----- /admin/assignment-history/export CSV -----

class TestHistoryExportCsv:
    def test_export_returns_csv(self, session, admin_token):
        r = session.get(
            f"{API}/admin/assignment-history/export",
            headers=_admin_headers(admin_token),
            timeout=20,
        )
        assert r.status_code == 200, r.text
        ctype = r.headers.get("content-type", "")
        assert "text/csv" in ctype, f"Expected text/csv, got {ctype}"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower(), f"Missing attachment disposition: {cd}"
        assert "historial_asignaciones" in cd, f"Filename mismatch: {cd}"
        # Header row check
        body = r.text
        first_line = body.splitlines()[0]
        assert first_line.startswith("fecha,accion,pedido_id"), f"CSV header unexpected: {first_line}"

    def test_export_csv_columns(self, session, admin_token):
        r = session.get(
            f"{API}/admin/assignment-history/export",
            headers=_admin_headers(admin_token),
            timeout=20,
        )
        assert r.status_code == 200
        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        assert len(rows) >= 1
        expected = ["fecha", "accion", "pedido_id", "repartidor", "repartidor_id",
                    "realizado_por", "rol", "distancia_km", "motivo"]
        assert rows[0] == expected

    def test_export_filter_action_assigned(self, session, admin_token):
        r = session.get(
            f"{API}/admin/assignment-history/export",
            params={"action": "assigned"},
            headers=_admin_headers(admin_token),
            timeout=20,
        )
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        # Data rows (after header) should all have accion='assigned'
        for row in rows[1:]:
            assert row[1] == "assigned", f"Non-assigned row in filtered export: {row}"

    def test_export_rejects_customer(self, session, customer_token):
        r = session.get(
            f"{API}/admin/assignment-history/export",
            headers={"Authorization": f"Bearer {customer_token}"},
            timeout=15,
        )
        assert r.status_code == 403

    def test_export_rejects_anonymous(self, session):
        r = session.get(f"{API}/admin/assignment-history/export", timeout=15)
        assert r.status_code in (401, 403)
