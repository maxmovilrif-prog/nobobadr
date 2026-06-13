"""Backend tests for separate Admin Portal (/api/admin-auth/login):
- Login success with email+password+secret_code
- Wrong secret returns 401
- Public /auth/login rejects admin (401)
- Brute-force lockout 429 after 5 failed attempts (uses throwaway email)
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "control@nuboexpress.com"
ADMIN_PASSWORD = "Fn6FcMveVf%--1o-"
ADMIN_SECRET = "NUBO-84D2-C159-E3CF"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


class TestAdminPortalLogin:
    def test_admin_login_success(self, session):
        r = session.post(
            f"{API}/admin-auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "secret_code": ADMIN_SECRET},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data and isinstance(data["token"], str) and len(data["token"]) > 20
        assert data.get("user", {}).get("role") == "admin"
        assert data["user"]["email"] == ADMIN_EMAIL
        assert "_id" not in data["user"]

    def test_admin_login_wrong_secret(self, session):
        r = session.post(
            f"{API}/admin-auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "secret_code": "WRONG_CODE"},
            timeout=15,
        )
        # Should not grant access (401 expected, could also be 403)
        assert r.status_code in (401, 403), r.text

    def test_admin_login_wrong_password(self, session):
        r = session.post(
            f"{API}/admin-auth/login",
            json={"email": ADMIN_EMAIL, "password": "definitely-wrong", "secret_code": ADMIN_SECRET},
            timeout=15,
        )
        assert r.status_code in (401, 403), r.text


class TestPublicLoginRejectsAdmin:
    def test_admin_cannot_use_public_login(self, session):
        r = session.post(
            f"{API}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15,
        )
        assert r.status_code == 401, r.text


class TestAdminBruteForceLockout:
    def test_lockout_after_5_failed_attempts(self, session):
        # Use throwaway email so we don't lock the real admin
        throwaway = f"junk-{uuid.uuid4().hex[:8]}@example.com"
        statuses = []
        for i in range(6):
            r = session.post(
                f"{API}/admin-auth/login",
                json={"email": throwaway, "password": "wrong", "secret_code": "wrong"},
                timeout=15,
            )
            statuses.append(r.status_code)
            time.sleep(0.2)
        # First 5 should be 401/403; 6th must be 429
        assert statuses[-1] == 429, f"Expected 429 on 6th attempt, got statuses={statuses}"
        for s in statuses[:5]:
            assert s in (401, 403), f"Unexpected status before lockout: {statuses}"
