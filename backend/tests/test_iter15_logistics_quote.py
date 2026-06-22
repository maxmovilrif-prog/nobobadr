"""Iter 15 — Logistics Quote (Camión) flow + admin WhatsApp alert (Option B).

Validates:
- Backend health (/api/public/cities)
- Admin login + admin DB record has phone +34612284215
- Customer creates logistics quote -> order_type='logistics', status='pending_quote', total_amount==0
- Admin PATCH /set-quote-price (200, status=quoted, total_amount updated)
- Non-admin (customer) gets 403 on set-quote-price
- Invalid/<=0 total_amount returns 400
- Notifications best-effort: response message present even with Twilio NOT configured
- Customer confirms -> status='pending'; non-owner gets 403
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nubo-abejas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "badarbox1756@gmail.com"
ADMIN_PASS = "Admin1234!"
CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASS = "Test1234!"


# ---------------- helpers ----------------
def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"no token in login response: {data}"
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _make_quote_payload() -> dict:
    return {
        "origin_name": "Algeciras, ES",
        "origin_lat": 36.1408,
        "origin_lng": -5.4562,
        "destination_name": "Tánger, MA",
        "destination_lat": 35.7595,
        "destination_lng": -5.8340,
        "vehicle_type": "truck",
        "fee": 0,
        "currency": "EUR",
        "distance_km": 45.0,
        "eta_mins": 90,
    }


# ---------------- fixtures ----------------
@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def customer_token() -> str:
    return _login(CUSTOMER_EMAIL, CUSTOMER_PASS)


# ---------------- tests ----------------
class TestHealth:
    def test_public_cities_ok(self):
        r = requests.get(f"{API}/public/cities", timeout=15)
        assert r.status_code == 200
        body = r.json()
        # endpoint can return either a list or {cities: [...]}
        cities = body if isinstance(body, list) else body.get("cities") or body.get("items") or []
        assert isinstance(cities, list)
        assert len(cities) > 0, "no cities returned"


class TestAdminIdentity:
    def test_admin_login_and_phone(self, admin_token):
        # /api/auth/me should expose the logged-in admin profile incl. phone
        r = requests.get(f"{API}/auth/me", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200, r.text
        me = r.json()
        assert me.get("role") == "admin", f"expected admin role, got {me.get('role')}"
        assert me.get("email", "").lower() == ADMIN_EMAIL
        assert me.get("phone") == "+34612284215", f"admin phone mismatch: {me.get('phone')}"


class TestLogisticsQuoteFlow:
    """Full Camión / heavy-logistics quote flow + Option B admin WhatsApp alert."""

    def test_full_flow(self, admin_token, customer_token):
        # 1) Customer creates a logistics quote
        payload = _make_quote_payload()
        r = requests.post(
            f"{API}/orders/logistics-quote",
            json=payload,
            headers=_auth(customer_token),
            timeout=20,
        )
        assert r.status_code == 200, f"create logistics quote failed: {r.status_code} {r.text}"
        order = r.json()
        order_id = order["id"]
        assert order["order_type"] == "logistics"
        assert order["status"] == "pending_quote"
        assert float(order["total_amount"]) == 0.0
        assert order.get("vehicle_type") == "truck"

        # 2) Non-admin (customer) attempting to set price must be 403
        r403 = requests.patch(
            f"{API}/orders/{order_id}/set-quote-price",
            json={"total_amount": 150.0},
            headers=_auth(customer_token),
            timeout=20,
        )
        assert r403.status_code == 403, f"expected 403 for non-admin, got {r403.status_code}: {r403.text}"

        # 3) Admin sets invalid price (<=0) → 400
        rbad = requests.patch(
            f"{API}/orders/{order_id}/set-quote-price",
            json={"total_amount": 0},
            headers=_auth(admin_token),
            timeout=20,
        )
        assert rbad.status_code == 400, f"expected 400 for price<=0, got {rbad.status_code}: {rbad.text}"

        rbad2 = requests.patch(
            f"{API}/orders/{order_id}/set-quote-price",
            json={"total_amount": "abc"},
            headers=_auth(admin_token),
            timeout=20,
        )
        assert rbad2.status_code == 400, f"expected 400 for invalid total_amount, got {rbad2.status_code}"

        # 4) Admin sets a valid price → 200, status=quoted, notifications best-effort
        rok = requests.patch(
            f"{API}/orders/{order_id}/set-quote-price",
            json={"total_amount": 220.50},
            headers=_auth(admin_token),
            timeout=25,
        )
        assert rok.status_code == 200, f"set-quote-price failed: {rok.status_code} {rok.text}"
        body = rok.json()
        assert body.get("status") == "quoted"
        assert float(body.get("total_amount")) == 220.50
        assert body.get("message") == "Precio fijado · cliente notificado", \
            f"unexpected message: {body.get('message')}"

        # Small delay to let best-effort async tasks run (they MUST NOT crash the server)
        time.sleep(1.5)

        # Verify persisted via GET
        rg = requests.get(f"{API}/orders/{order_id}", headers=_auth(admin_token), timeout=15)
        assert rg.status_code == 200
        persisted = rg.json()
        assert persisted["status"] == "quoted"
        assert float(persisted["total_amount"]) == 220.50

        # 5) A different (non-owner) user cannot confirm — re-using admin token as a non-owner
        rconf_forbidden = requests.post(
            f"{API}/orders/{order_id}/confirm-quote",
            headers=_auth(admin_token),
            timeout=15,
        )
        assert rconf_forbidden.status_code == 403, \
            f"non-owner should be 403 on confirm, got {rconf_forbidden.status_code}: {rconf_forbidden.text}"

        # 6) Customer confirms the quote → status='pending'
        rconf = requests.post(
            f"{API}/orders/{order_id}/confirm-quote",
            headers=_auth(customer_token),
            timeout=20,
        )
        assert rconf.status_code == 200, f"confirm-quote failed: {rconf.status_code} {rconf.text}"
        confirmed = rconf.json()
        assert confirmed.get("status") == "pending", f"expected pending after confirm, got {confirmed.get('status')}"
        assert confirmed.get("id") == order_id

    def test_set_price_on_nonexistent_order_404(self, admin_token):
        fake_id = f"nope-{uuid.uuid4()}"
        r = requests.patch(
            f"{API}/orders/{fake_id}/set-quote-price",
            json={"total_amount": 100},
            headers=_auth(admin_token),
            timeout=15,
        )
        assert r.status_code == 404


class TestWhatsAppDegradation:
    """Confirm whatsapp_service degrades gracefully when Twilio env vars are absent."""

    def test_whatsapp_service_not_configured(self):
        import sys
        sys.path.insert(0, "/app/backend")
        import importlib
        import whatsapp_service as ws
        importlib.reload(ws)
        # In preview Twilio creds are NOT set
        assert ws.is_configured() is False, "preview must NOT have Twilio configured"

        import asyncio
        res = asyncio.get_event_loop().run_until_complete(
            ws.send_whatsapp("+34612284215", "test")
        ) if False else asyncio.run(ws.send_whatsapp("+34612284215", "test"))
        assert res == {"sent": False, "reason": "not_configured"}

        res2 = asyncio.run(
            ws.notify_admin_logistics_priced("+34612284215", {"id": "x", "total_amount": 10, "currency": "EUR"}, {"name": "a", "phone": "+34000"})
        )
        assert res2 == {"sent": False, "reason": "not_configured"}
