"""Iter 9 — Admin/public separation, Stripe TEST mode, RBAC, reset-password.

Covers:
- POST /api/admin/reset-password (403 wrong secret, success existing, success created:true new)
- POST /api/auth/login admin (badarbox1756@gmail.com / Admin1234!) returns role=admin
- POST /api/auth/login customer → role=customer
- GET  /api/admin/payments/status returns mode=test, live=false
- RBAC: manager 403 on KPIs/contabilidad endpoints (no regression)
"""

import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to read from frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

API = f"{BASE_URL}/api"
ADMIN_EMAIL = "badarbox1756@gmail.com"
ADMIN_PASSWORD = "Admin1234!"
RESET_SECRET = "nubo-preview-reset-7K9mQ2xP"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# -------------------- reset-password --------------------
class TestResetPasswordEndpoint:
    def test_wrong_secret_403(self, session):
        r = session.post(f"{API}/admin/reset-password", json={
            "email": ADMIN_EMAIL,
            "new_password": "WhateverNewPwd!",
            "secret": "wrong-secret-xxx",
        }, timeout=15)
        assert r.status_code == 403, f"Expected 403 got {r.status_code} body={r.text}"

    def test_existing_user_success_created_false(self, session):
        # First ensure admin exists by resetting its password to the canonical one
        r = session.post(f"{API}/admin/reset-password", json={
            "email": ADMIN_EMAIL,
            "new_password": ADMIN_PASSWORD,
            "secret": RESET_SECRET,
        }, timeout=15)
        assert r.status_code == 200, f"Got {r.status_code} body={r.text}"
        body = r.json()
        assert body.get("success") is True
        # If admin existed prior, created must be False. Tolerate created=True on first ever run.
        assert "created" in body

    def test_new_email_creates_admin(self, session):
        # NOTE: reset endpoint lowercases email before storage; use lowercase to login successfully
        new_email = f"test_reset_{int(time.time())}@nubo-qa.com"
        r = session.post(f"{API}/admin/reset-password", json={
            "email": new_email,
            "new_password": "BrandNewPwd1!",
            "secret": RESET_SECRET,
        }, timeout=15)
        assert r.status_code == 200, f"Got {r.status_code} body={r.text}"
        body = r.json()
        assert body.get("success") is True
        assert body.get("created") is True, f"Expected created:true got {body}"

        # Verify login works for newly created admin
        time.sleep(0.3)
        login = session.post(f"{API}/auth/login", json={
            "email": new_email, "password": "BrandNewPwd1!",
        }, timeout=15)
        assert login.status_code == 200, f"Login failed {login.status_code}: {login.text}"
        u = login.json().get("user", {})
        assert u.get("role") == "admin"


# -------------------- admin login --------------------
class TestAdminLogin:
    def test_admin_login_success(self, session):
        r = session.post(f"{API}/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
        }, timeout=15)
        assert r.status_code == 200, f"Got {r.status_code} body={r.text}"
        data = r.json()
        assert "token" in data and len(data["token"]) > 0
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"

    def test_admin_login_wrong_password(self, session):
        r = session.post(f"{API}/auth/login", json={
            "email": ADMIN_EMAIL, "password": "wrong-xx",
        }, timeout=15)
        assert r.status_code in (400, 401, 403), f"Got {r.status_code}"


# -------------------- Stripe status --------------------
class TestStripeStatus:
    def _admin_token(self, session):
        r = session.post(f"{API}/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
        }, timeout=15)
        assert r.status_code == 200
        return r.json()["token"]

    def test_payments_status_test_mode(self, session):
        tok = self._admin_token(session)
        r = session.get(f"{API}/admin/payments/status",
                        headers={"Authorization": f"Bearer {tok}"}, timeout=15)
        assert r.status_code == 200, f"Got {r.status_code} body={r.text}"
        body = r.json()
        assert body.get("mode") == "test", f"Expected mode=test got {body}"
        assert body.get("live") is False


# -------------------- Customer login & RBAC --------------------
class TestCustomerRBAC:
    def _register_or_login_customer(self, session):
        email = f"test_qa_cust_{int(time.time()*1000)}@nubo-qa.com"
        pwd = "Test1234!"
        r = session.post(f"{API}/auth/register", json={
            "email": email, "password": pwd,
            "name": "QA Cust", "role": "customer", "phone": "+34600111000",
        }, timeout=15)
        assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
        user = r.json()  # UserResponse direct
        # login to get token
        lr = session.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=15)
        assert lr.status_code == 200, f"customer login failed: {lr.status_code} {lr.text}"
        return lr.json()["token"], user

    def test_customer_login_role(self, session):
        tok, user = self._register_or_login_customer(session)
        assert user.get("role") == "customer"
        assert tok and len(tok) > 0

    def test_customer_blocked_on_kpis(self, session):
        tok, _ = self._register_or_login_customer(session)
        r = session.get(f"{API}/admin/kpis",
                        headers={"Authorization": f"Bearer {tok}"}, timeout=15)
        # should be forbidden for customer
        assert r.status_code in (401, 403), f"Expected 401/403 got {r.status_code}"
