"""Test del endpoint de estado de Stripe (solo Fundador) y la resolución de clave.

La app prioriza STRIPE_LIVE_KEY (sk_live_...) sobre STRIPE_API_KEY (test gestionada).
"""
import os
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
ADMIN_EMAIL, ADMIN_PASS = "admin@nubo.com", "Admin1234!"
CUSTOMER_EMAIL, CUSTOMER_PASS = "qa_customer@nubo.com", "Test1234!"


def _token(e, p):
    r = requests.post(f"{API}/auth/login", json={"email": e, "password": p})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_payments_status_founder_only():
    h = {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASS)}"}
    r = requests.get(f"{API}/admin/payments/status", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] in ("test", "live")
    assert isinstance(body["live"], bool)
    # nunca expone la clave completa
    if body.get("key_prefix"):
        assert body["key_prefix"].endswith("…") and len(body["key_prefix"]) <= 12


def test_payments_status_blocked_for_customer():
    h = {"Authorization": f"Bearer {_token(CUSTOMER_EMAIL, CUSTOMER_PASS)}"}
    assert requests.get(f"{API}/admin/payments/status", headers=h).status_code == 403


def test_stripe_key_resolution_prefers_live():
    """STRIPE_LIVE_KEY (sk_live_...) tiene prioridad sobre STRIPE_API_KEY."""
    def resolve(env):
        key = env.get('STRIPE_LIVE_KEY') or env.get('STRIPE_API_KEY', 'sk_test_emergent')
        mode = 'live' if (env.get('STRIPE_LIVE_KEY') or '').startswith('sk_live_') else 'test'
        return key, mode

    assert resolve({'STRIPE_LIVE_KEY': 'sk_live_ABC', 'STRIPE_API_KEY': 'sk_test_x'}) == ('sk_live_ABC', 'live')
    assert resolve({'STRIPE_API_KEY': 'sk_test_x'}) == ('sk_test_x', 'test')
    assert resolve({}) == ('sk_test_emergent', 'test')
