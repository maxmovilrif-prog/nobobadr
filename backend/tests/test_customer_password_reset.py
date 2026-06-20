"""
Tests for the CUSTOMER password reset flow (iteration 11)

Covers:
  - POST /api/auth/forgot-password with a registered customer email
      -> generic response AND token doc created in password_reset_tokens with role='customer'
  - POST /api/auth/forgot-password with unknown email
      -> SAME generic response and NO token doc (anti-enumeration)
  - reset_link role-routing (verified at DB role level + source-code inspection)
  - POST /api/auth/reset-password full flow (success, single-use, short password)
  - Regression: admin/manager forgot-password still works (role='admin', link /nubo-control/recuperar)
  - Regression: customer login (qa_customer@nubo.com / Test1234!) still works

Final teardown restores qa_customer@nubo.com password back to 'Test1234!' and cleans
password_reset_tokens of test rows.
"""

import os
import sys
import time
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

# Load REACT_APP_BACKEND_URL from frontend/.env
def _read_env(file_path, key):
    try:
        with open(file_path, 'r') as f:
            for ln in f:
                ln = ln.strip()
                if ln.startswith(key + '='):
                    v = ln.split('=', 1)[1].strip()
                    return v.strip('"').strip("'")
    except FileNotFoundError:
        return None
    return None

BASE_URL = (_read_env('/app/frontend/.env', 'REACT_APP_BACKEND_URL') or '').rstrip('/')
MONGO_URL = _read_env('/app/backend/.env', 'MONGO_URL') or 'mongodb://localhost:27017'
DB_NAME = _read_env('/app/backend/.env', 'DB_NAME') or 'glovo_algeciras'

assert BASE_URL, "REACT_APP_BACKEND_URL must be set in /app/frontend/.env"

API = f"{BASE_URL}/api"

CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASSWORD = "Test1234!"
ADMIN_EMAIL = "badarbox1756@gmail.com"

_mongo = MongoClient(MONGO_URL)
_db = _mongo[DB_NAME]


def _sha256(t: str) -> str:
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module", autouse=True)
def ensure_customer_exists(http):
    """Make sure qa_customer@nubo.com exists with password Test1234!."""
    user = _db.users.find_one({"email": CUSTOMER_EMAIL})
    if not user:
        r = http.post(f"{API}/auth/register", json={
            "email": CUSTOMER_EMAIL,
            "password": CUSTOMER_PASSWORD,
            "name": "QA Customer",
            "phone": "+34600000000",
            "role": "customer",
        })
        assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    yield


# ---------- Tests ----------

# Customer forgot-password: registered email
def test_forgot_password_customer_creates_token(http):
    # Clean any prior token for this email so we can assert this run creates a new one
    _db.password_reset_tokens.delete_many({"email": CUSTOMER_EMAIL})

    r = http.post(f"{API}/auth/forgot-password", json={"email": CUSTOMER_EMAIL})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "message" in data
    assert "recibirás un enlace" in data["message"] or "enlace" in data["message"].lower()

    # Token doc must be created with role='customer'
    docs = list(_db.password_reset_tokens.find({"email": CUSTOMER_EMAIL}))
    assert len(docs) == 1, f"expected exactly 1 token doc for customer, got {len(docs)}"
    d = docs[0]
    assert d.get("role") == "customer"
    assert d.get("used") is False
    assert "token_hash" in d and isinstance(d["token_hash"], str) and len(d["token_hash"]) == 64
    assert "expires_at" in d


# Anti-enumeration: unknown email returns the SAME generic body AND no token created
def test_forgot_password_unknown_email_no_token(http):
    unknown = "definitely-not-registered-xyz@nubo-qa.com"
    _db.password_reset_tokens.delete_many({"email": unknown})

    # Get baseline response for customer to compare body
    r_known = http.post(f"{API}/auth/forgot-password", json={"email": CUSTOMER_EMAIL})
    r_unk = http.post(f"{API}/auth/forgot-password", json={"email": unknown})

    assert r_known.status_code == 200
    assert r_unk.status_code == 200
    assert r_known.json() == r_unk.json(), "anti-enumeration: response must be identical"

    cnt = _db.password_reset_tokens.count_documents({"email": unknown})
    assert cnt == 0, "no token must be created for unknown email"


# Source-code level check that reset_link routes by role
def test_reset_link_routes_by_role_in_source():
    with open('/app/backend/routes/auth.py', 'r') as f:
        src = f.read()
    # Admin/manager link
    assert "/nubo-control/recuperar?token=" in src
    # Customer/business link
    assert "/recuperar?token=" in src
    # And the branching logic must check admin/manager
    assert "if user.get('role') in ('admin', 'manager')" in src or 'role" in ("admin", "manager")' in src


# End-to-end reset for a customer: inject a token directly in DB (preview has no email)
def test_reset_password_customer_full_flow(http):
    # Generate a known token, store its hash so we can reset and then re-login
    raw = secrets.token_urlsafe(32)
    user = _db.users.find_one({"email": CUSTOMER_EMAIL})
    assert user, "customer must exist"
    _db.password_reset_tokens.insert_one({
        "token_hash": _sha256(raw),
        "user_id": user["id"],
        "email": CUSTOMER_EMAIL,
        "role": "customer",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        "used": False,
        "created_at": datetime.now(timezone.utc),
    })

    new_pwd = "NewQAPwd987!"

    # Short password -> 400
    r_short = http.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": "abc"})
    assert r_short.status_code == 400, r_short.text

    # Success
    r_ok = http.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": new_pwd})
    assert r_ok.status_code == 200, r_ok.text
    body = r_ok.json()
    assert body.get("success") is True
    assert body.get("email") == CUSTOMER_EMAIL

    # Token now used → second use must fail
    r_reuse = http.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": new_pwd})
    assert r_reuse.status_code == 400

    # Login with NEW password works
    r_login = http.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": new_pwd})
    assert r_login.status_code == 200, r_login.text
    assert r_login.json().get("user", {}).get("role") == "customer"

    # Restore canonical Test1234! by issuing another reset token + reset
    raw2 = secrets.token_urlsafe(32)
    _db.password_reset_tokens.insert_one({
        "token_hash": _sha256(raw2),
        "user_id": user["id"],
        "email": CUSTOMER_EMAIL,
        "role": "customer",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        "used": False,
        "created_at": datetime.now(timezone.utc),
    })
    r_restore = http.post(f"{API}/auth/reset-password", json={"token": raw2, "new_password": CUSTOMER_PASSWORD})
    assert r_restore.status_code == 200, r_restore.text

    # Final login with Test1234! must work
    r_final = http.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
    assert r_final.status_code == 200


# Regression: admin/manager forgot-password creates a token with role='admin'
def test_forgot_password_admin_regression(http):
    _db.password_reset_tokens.delete_many({"email": ADMIN_EMAIL})

    r = http.post(f"{API}/auth/forgot-password", json={"email": ADMIN_EMAIL})
    assert r.status_code == 200

    docs = list(_db.password_reset_tokens.find({"email": ADMIN_EMAIL}))
    assert len(docs) == 1
    assert docs[0].get("role") == "admin"


# Regression: customer login still works at /auth/login
def test_customer_login_regression(http):
    r = http.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and isinstance(data["token"], str)
    assert data["user"]["email"] == CUSTOMER_EMAIL
    assert data["user"]["role"] == "customer"


# Reset endpoint: invalid token -> 400
def test_reset_invalid_token(http):
    r = http.post(f"{API}/auth/reset-password", json={"token": "obviously-not-a-real-token", "new_password": "Whatever123!"})
    assert r.status_code == 400


# Cleanup: remove test tokens
def test_zz_cleanup():
    _db.password_reset_tokens.delete_many({"email": CUSTOMER_EMAIL})
    _db.password_reset_tokens.delete_many({"email": ADMIN_EMAIL})
    _db.password_reset_tokens.delete_many({"email": "definitely-not-registered-xyz@nubo-qa.com"})
    # Ensure customer password is Test1234! (restored above; double-check by login)
    # No-op if login already works
