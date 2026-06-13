"""Backend tests for NEW logistics features (iteration 8):
- Assignment history endpoint (GET /api/admin/assignment-history)
- Auto-return on driver unavailable (PATCH /api/drivers/availability?is_available=false)
- Manual return to queue (POST /api/orders/{id}/return-to-queue)
- Each event logged with correct action/reason/driver_name/actor/timestamp
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "control@nuboexpress.com"
ADMIN_PASSWORD = "Fn6FcMveVf%--1o-"
ADMIN_SECRET_CODE = "NUBO-84D2-C159-E3CF"
DRIVER_REAL_EMAIL = "driver.real@nubotest.com"
DRIVER_REAL_PASSWORD = "Driver123!"
CUSTOMER_EMAIL = "cliente@nubotest.com"
CUSTOMER_PASSWORD = "Cliente123!"
DRIVER_MADRID_EMAIL = "bee.madrid@nuboexpress.com"
DRIVER_MADRID_PASSWORD = "Bee123!"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _public_login(session, email, password):
    return session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)


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
def driver_real_token(session):
    r = _public_login(session, DRIVER_REAL_EMAIL, DRIVER_REAL_PASSWORD)
    assert r.status_code == 200, f"driver.real login failed: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="session")
def driver_madrid_token(session):
    r = _public_login(session, DRIVER_MADRID_EMAIL, DRIVER_MADRID_PASSWORD)
    assert r.status_code == 200, f"driver.madrid login failed: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="session")
def customer_token(session):
    r = _public_login(session, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
    if r.status_code != 200:
        session.post(
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
        r = _public_login(session, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
    assert r.status_code == 200, f"customer login failed: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- GET /admin/assignment-history ----------
class TestAssignmentHistoryEndpoint:
    def test_history_admin_ok_sorted_newest_first(self, session, admin_token):
        r = session.get(f"{API}/admin/assignment-history", headers=_hdr(admin_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "count" in data and "events" in data
        assert isinstance(data["events"], list)
        assert data["count"] == len(data["events"])
        if len(data["events"]) >= 2:
            ts = [e["created_at"] for e in data["events"]]
            assert ts == sorted(ts, reverse=True), "events must be sorted newest-first"
        if data["events"]:
            e = data["events"][0]
            for k in ("id", "order_id", "action", "created_at"):
                assert k in e, f"missing key {k} in event"
            assert e["action"] in ("assigned", "returned", "auto_returned")
            assert "_id" not in e

    def test_history_rejects_customer(self, session, customer_token):
        r = session.get(f"{API}/admin/assignment-history", headers=_hdr(customer_token), timeout=15)
        assert r.status_code == 403, r.text

    def test_history_rejects_driver(self, session, driver_real_token):
        r = session.get(f"{API}/admin/assignment-history", headers=_hdr(driver_real_token), timeout=15)
        assert r.status_code == 403, r.text

    def test_history_rejects_unauth(self, session):
        r = session.get(f"{API}/admin/assignment-history", timeout=15)
        assert r.status_code in (401, 403)


# ---------- Auto-return on driver unavailable ----------
class TestAutoReturnOnUnavailable:
    def test_auto_return_flow(self, session, admin_token, driver_real_token):
        """Assign to driver.real near (40.97,-5.66) → driver toggles unavailable → order returns to queue + history logged."""
        # First make sure driver.real is available
        rav = session.patch(
            f"{API}/drivers/availability",
            params={"is_available": "true"},
            headers=_hdr(driver_real_token),
            timeout=15,
        )
        assert rav.status_code == 200, rav.text

        # Get a pending order (must exist - 4 seeded)
        pend = session.get(f"{API}/admin/pending-orders", headers=_hdr(admin_token), timeout=15)
        assert pend.status_code == 200, pend.text
        orders = pend.json()["orders"]
        assert len(orders) >= 1, "Need at least 1 pending order to assign"
        order_id = orders[0]["id"]

        # Assign nearest to driver.real's location
        asn = session.post(
            f"{API}/orders/{order_id}/assign-nearest",
            params={},
            json={"lat": 40.9701, "lng": -5.6635, "max_km": None},
            headers=_hdr(admin_token),
            timeout=15,
        )
        assert asn.status_code == 200, asn.text
        assigned_driver_id = asn.json()["driver"]["id"]

        # Resolve driver.real's id via /auth/me
        me = session.get(f"{API}/auth/me", headers=_hdr(driver_real_token), timeout=15).json()
        driver_real_id = me["id"]

        # Snapshot history count BEFORE driver goes unavailable
        h_before = session.get(f"{API}/admin/assignment-history", headers=_hdr(admin_token), timeout=15).json()
        before_count = h_before["count"]

        # Verify we have an 'assigned' event for this order
        assigned_events = [e for e in h_before["events"] if e["order_id"] == order_id and e["action"] == "assigned"]
        assert len(assigned_events) >= 1, "Assigned event not logged"
        assert assigned_events[0].get("driver_id") == assigned_driver_id
        assert assigned_events[0].get("distance_km") is not None

        # If the nearest was NOT driver.real, manually return and skip auto-return assertion
        if assigned_driver_id != driver_real_id:
            session.post(
                f"{API}/orders/{order_id}/return-to-queue",
                headers=_hdr(admin_token),
                timeout=15,
            )
            pytest.skip(f"Nearest driver was {assigned_driver_id}, not driver.real {driver_real_id}")

        # Driver.real toggles unavailable → orders should auto-return
        toggle = session.patch(
            f"{API}/drivers/availability",
            params={"is_available": "false"},
            headers=_hdr(driver_real_token),
            timeout=15,
        )
        assert toggle.status_code == 200, toggle.text
        body = toggle.json()
        assert body["is_available"] is False
        assert body.get("orders_returned_to_queue", 0) >= 1, f"expected >=1 orders returned, got {body}"

        # Order should reappear in pending
        pend2 = session.get(f"{API}/admin/pending-orders", headers=_hdr(admin_token), timeout=15).json()
        ids = [o["id"] for o in pend2["orders"]]
        assert order_id in ids, "Order did not reappear in pending queue after auto-return"

        # History should now have an auto_returned event
        h_after = session.get(f"{API}/admin/assignment-history", headers=_hdr(admin_token), timeout=15).json()
        assert h_after["count"] > before_count
        auto_ev = [
            e for e in h_after["events"]
            if e["order_id"] == order_id and e["action"] == "auto_returned"
        ]
        assert len(auto_ev) >= 1, "auto_returned event was not logged"
        assert auto_ev[0].get("reason") == "driver_unavailable"

        # Cleanup: re-enable driver.real availability
        reset = session.patch(
            f"{API}/drivers/availability",
            params={"is_available": "true"},
            headers=_hdr(driver_real_token),
            timeout=15,
        )
        assert reset.status_code == 200


def _get_user_id_by_email(session, admin_token, email):
    """Resolve user id from a known driver — uses active-drivers list."""
    r = session.get(f"{API}/admin/active-drivers", headers=_hdr(admin_token), timeout=15)
    if r.status_code != 200:
        return None
    for d in r.json().get("drivers", []):
        if d.get("email") == email:
            return d["id"]
    return None


# ---------- Manual return to queue ----------
class TestManualReturnToQueue:
    def test_manual_return_success_logs_event(self, session, admin_token):
        # Get a pending order
        pend = session.get(f"{API}/admin/pending-orders", headers=_hdr(admin_token), timeout=15)
        assert pend.status_code == 200
        orders = pend.json()["orders"]
        if not orders:
            pytest.skip("No pending orders available for manual return test")
        order_id = orders[0]["id"]

        # Assign nearest
        asn = session.post(
            f"{API}/orders/{order_id}/assign-nearest",
            json={"lat": 40.4168, "lng": -3.7038, "max_km": None},
            headers=_hdr(admin_token),
            timeout=15,
        )
        assert asn.status_code == 200, asn.text

        h_before = session.get(f"{API}/admin/assignment-history", headers=_hdr(admin_token), timeout=15).json()["count"]

        # Manual return
        ret = session.post(
            f"{API}/orders/{order_id}/return-to-queue",
            headers=_hdr(admin_token),
            timeout=15,
        )
        assert ret.status_code == 200, ret.text

        # Verify reappears
        pend2 = session.get(f"{API}/admin/pending-orders", headers=_hdr(admin_token), timeout=15).json()
        assert order_id in [o["id"] for o in pend2["orders"]]

        # Verify returned event logged
        h_after = session.get(f"{API}/admin/assignment-history", headers=_hdr(admin_token), timeout=15).json()
        assert h_after["count"] > h_before
        returned = [e for e in h_after["events"] if e["order_id"] == order_id and e["action"] == "returned"]
        assert len(returned) >= 1
        assert returned[0].get("reason") == "manual_return"

    def test_manual_return_400_if_no_driver(self, session, admin_token):
        pend = session.get(f"{API}/admin/pending-orders", headers=_hdr(admin_token), timeout=15).json()
        if not pend["orders"]:
            pytest.skip("No pending orders to test 400")
        order_id = pend["orders"][0]["id"]
        # order has no driver, should 400
        r = session.post(f"{API}/orders/{order_id}/return-to-queue", headers=_hdr(admin_token), timeout=15)
        assert r.status_code == 400, r.text

    def test_manual_return_404_unknown_order(self, session, admin_token):
        r = session.post(
            f"{API}/orders/00000000-0000-0000-0000-000000000000/return-to-queue",
            headers=_hdr(admin_token),
            timeout=15,
        )
        assert r.status_code == 404

    def test_manual_return_403_customer(self, session, customer_token):
        r = session.post(
            f"{API}/orders/any-id/return-to-queue",
            headers=_hdr(customer_token),
            timeout=15,
        )
        assert r.status_code == 403

    def test_manual_return_403_driver(self, session, driver_real_token):
        r = session.post(
            f"{API}/orders/any-id/return-to-queue",
            headers=_hdr(driver_real_token),
            timeout=15,
        )
        assert r.status_code == 403
