"""Tests del servicio de email transaccional (Resend) — solo Fundador.

Sin RESEND_API_KEY el servicio degrada con elegancia:
- /admin/email/status -> configured=false
- /admin/email/test -> 503 (no configurado)
- Acceso solo Fundador (cliente -> 403)
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


def test_email_status_founder():
    h = {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASS)}"}
    r = requests.get(f"{API}/admin/email/status", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "resend"
    assert "configured" in body and "sender" in body


def test_email_test_requires_config():
    h = {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASS)}"}
    r = requests.get(f"{API}/admin/email/status", headers=h)
    configured = r.json()["configured"]
    resp = requests.post(f"{API}/admin/email/test", headers=h, json={"to": "qa@example.com"})
    if not configured:
        assert resp.status_code == 503
    else:
        assert resp.status_code in (200, 502)


def test_email_status_blocked_for_customer():
    h = {"Authorization": f"Bearer {_token(CUSTOMER_EMAIL, CUSTOMER_PASS)}"}
    assert requests.get(f"{API}/admin/email/status", headers=h).status_code == 403
    assert requests.post(f"{API}/admin/email/test", headers=h, json={"to": "x@y.com"}).status_code == 403


def test_email_test_validates_recipient():
    h = {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASS)}"}
    # email inválido -> 422 (validación Pydantic) antes de comprobar config
    r = requests.post(f"{API}/admin/email/test", headers=h, json={"to": "no-es-email"})
    assert r.status_code == 422
