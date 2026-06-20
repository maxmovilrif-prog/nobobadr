"""Iteration 10 — Regional multi-tenant + password reset + admin/customer session isolation.

Covers:
- Regions CRUD (admin only)
- Manager creation linked to a region
- Manager RBAC: 403 on KPIs, regions list, manager creation
- Rider scoping by region (list, create, regenerate code)
- Forgot/Reset password flow (anti-enumeration, token one-shot)
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "badarbox1756@gmail.com"
ADMIN_PASSWORD = "Admin1234!"
CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASSWORD = "Test1234!"

RUN_ID = uuid.uuid4().hex[:8]
STATE: dict = {}


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["user"]["role"] == "admin"
    return body["token"]


@pytest.fixture(scope="module")
def customer_token(s):
    # Ensure customer exists
    s.post(f"{API}/auth/register", json={
        "email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD,
        "name": "QA Customer", "phone": "600000000", "role": "customer",
    })
    r = s.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
    assert r.status_code == 200, f"Customer login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def H(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- Cities (needed for region creation) ----------
@pytest.fixture(scope="module")
def some_city_ids(s, admin_token):
    r = s.get(f"{API}/public/cities")
    assert r.status_code == 200, f"public/cities failed: {r.status_code}"
    cities = r.json().get("cities", [])
    assert len(cities) >= 4, f"Need at least 4 cities for region tests, got {len(cities)}"
    return [c["id"] for c in cities[:4]]


# ---------- Regions CRUD ----------
class TestRegionsCRUD:
    def test_admin_create_region(self, s, admin_token, some_city_ids, request):
        name = f"TEST_Reg_A_{RUN_ID}"
        r = s.post(f"{API}/admin/regions", json={"name": name, "city_ids": some_city_ids[:2]},
                   headers=H(admin_token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == name
        assert len(body["city_ids"]) == 2
        assert "cities" in body and len(body["cities"]) == 2
        assert body["managers_count"] == 0
        assert body["riders_count"] == 0
        # store for later
        STATE['region_a_id'] = body["id"]
        STATE['region_a_city_ids'] = body["city_ids"]

    def test_admin_create_region_b(self, s, admin_token, some_city_ids, request):
        name = f"TEST_Reg_B_{RUN_ID}"
        r = s.post(f"{API}/admin/regions", json={"name": name, "city_ids": some_city_ids[2:4]},
                   headers=H(admin_token))
        assert r.status_code == 200, r.text
        STATE['region_b_id'] = r.json()["id"]
        STATE['region_b_city_ids'] = r.json()["city_ids"]

    def test_admin_list_regions(self, s, admin_token, request):
        r = s.get(f"{API}/admin/regions", headers=H(admin_token))
        assert r.status_code == 200
        body = r.json()
        ids = [x["id"] for x in body["regions"]]
        assert STATE['region_a_id'] in ids
        assert STATE['region_b_id'] in ids

    def test_customer_cannot_list_regions(self, s, customer_token):
        r = s.get(f"{API}/admin/regions", headers=H(customer_token))
        assert r.status_code == 403


# ---------- Manager creation + RBAC ----------
class TestManagerRBAC:
    def test_admin_create_manager(self, s, admin_token, request):
        email = f"qa_mgr_a_{RUN_ID}@nubo-qa.com"
        password = "MgrPass123!"
        r = s.post(f"{API}/admin/managers", json={
            "name": "QA Manager A", "email": email, "password": password,
            "region_id": STATE['region_a_id'],
        }, headers=H(admin_token))
        assert r.status_code == 200, r.text
        body = r.json()
        # tolerate either {manager:{...}} or flat
        m = body.get("manager", body)
        assert m.get("email") == email
        assert m.get("role") == "manager"
        assert m.get("region_id") == STATE['region_a_id']
        STATE['mgr_a_email'] = email
        STATE['mgr_a_password'] = password
        STATE['mgr_a_id'] = m.get("id")

    def test_admin_create_manager_b(self, s, admin_token, request):
        email = f"qa_mgr_b_{RUN_ID}@nubo-qa.com"
        password = "MgrPass123!"
        r = s.post(f"{API}/admin/managers", json={
            "name": "QA Manager B", "email": email, "password": password,
            "region_id": STATE['region_b_id'],
        }, headers=H(admin_token))
        assert r.status_code == 200, r.text
        STATE['mgr_b_email'] = email
        STATE['mgr_b_password'] = password

    def test_manager_login(self, s, request):
        r = s.post(f"{API}/auth/login", json={
            "email": STATE['mgr_a_email'],
            "password": STATE['mgr_a_password'],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user"]["role"] == "manager"
        assert body["user"].get("region_id") == STATE['region_a_id']
        STATE['mgr_a_token'] = body["token"]

    def test_manager_login_b(self, s, request):
        r = s.post(f"{API}/auth/login", json={
            "email": STATE['mgr_b_email'],
            "password": STATE['mgr_b_password'],
        })
        assert r.status_code == 200
        STATE['mgr_b_token'] = r.json()["token"]

    def test_manager_403_kpis(self, s, request):
        r = s.get(f"{API}/admin/kpis", headers=H(STATE['mgr_a_token']))
        assert r.status_code == 403

    def test_manager_403_regions_list(self, s, request):
        r = s.get(f"{API}/admin/regions", headers=H(STATE['mgr_a_token']))
        assert r.status_code == 403

    def test_manager_403_create_manager(self, s, request):
        r = s.post(f"{API}/admin/managers", json={
            "name": "X", "email": f"qa_x_{RUN_ID}@nubo-qa.com", "password": "Aaaa1234!",
            "region_id": STATE['region_a_id'],
        }, headers=H(STATE['mgr_a_token']))
        assert r.status_code == 403

    def test_manager_regions_mine(self, s, request):
        r = s.get(f"{API}/regions/mine", headers=H(STATE['mgr_a_token']))
        assert r.status_code == 200
        body = r.json()
        assert body.get("is_founder") is False
        assert body.get("region", {}).get("id") == STATE['region_a_id']

    def test_admin_regions_mine(self, s, admin_token):
        r = s.get(f"{API}/regions/mine", headers=H(admin_token))
        assert r.status_code == 200
        body = r.json()
        assert body.get("is_founder") is True


# ---------- Riders scoped by region ----------
class TestRidersScoped:
    def test_admin_create_rider_in_region_a(self, s, admin_token, request):
        r = s.post(f"{API}/admin/riders", json={
            "name": f"TEST_RiderA_{RUN_ID}",
            "phone": "600100100",
            "vehicle_type": "motorcycle",
            "region_id": STATE['region_a_id'],
        }, headers=H(admin_token))
        assert r.status_code == 200, r.text
        body = r.json()
        rider = body.get("rider", body)
        assert rider.get("region_id") == STATE['region_a_id']
        assert rider.get("region_name", "").startswith("TEST_Reg_A_")
        assert rider.get("activation_code"), "missing activation_code"
        assert rider.get("qr_data_url", "").startswith("data:image/png;base64"), "missing qr_data_url"
        STATE['rider_a_id'] = rider["id"]
        STATE['rider_a_code'] = rider["activation_code"]

    def test_admin_create_rider_in_region_b(self, s, admin_token, request):
        r = s.post(f"{API}/admin/riders", json={
            "name": f"TEST_RiderB_{RUN_ID}",
            "phone": "600200200",
            "vehicle_type": "bicycle",
            "region_id": STATE['region_b_id'],
        }, headers=H(admin_token))
        assert r.status_code == 200, r.text
        STATE['rider_b_id'] = r.json().get("rider", r.json())["id"]

    def test_manager_a_sees_only_region_a_riders(self, s, request):
        r = s.get(f"{API}/admin/riders", headers=H(STATE['mgr_a_token']))
        assert r.status_code == 200
        body = r.json()
        riders = body.get("riders", body if isinstance(body, list) else [])
        # Must include rider A
        ids = [x.get("id") for x in riders]
        assert STATE['rider_a_id'] in ids
        # Must NOT include rider B
        assert STATE['rider_b_id'] not in ids
        # All returned riders must be in region A
        for rd in riders:
            assert rd.get("region_id") == STATE['region_a_id'], f"leak: {rd}"

    def test_admin_regenerate_code(self, s, admin_token, request):
        r = s.post(f"{API}/admin/riders/{STATE['rider_a_id']}/regenerate-code",
                   headers=H(admin_token))
        assert r.status_code == 200, r.text
        body = r.json()
        new_code = body.get("rider", body).get("activation_code") or body.get("activation_code")
        assert new_code, f"missing new code: {body}"
        assert new_code != STATE['rider_a_code']
        qr = body.get("rider", body).get("qr_data_url") or body.get("qr_data_url")
        assert qr and qr.startswith("data:image/png;base64")

    def test_manager_b_cannot_regenerate_other_region_rider(self, s, request):
        # mgr_b should NOT be able to touch rider in region A
        r = s.post(f"{API}/admin/riders/{STATE['rider_a_id']}/regenerate-code",
                   headers=H(STATE['mgr_b_token']))
        assert r.status_code in (403, 404), f"expected 403/404, got {r.status_code} {r.text}"

    def test_manager_a_can_regenerate_own_region_rider(self, s, request):
        r = s.post(f"{API}/admin/riders/{STATE['rider_a_id']}/regenerate-code",
                   headers=H(STATE['mgr_a_token']))
        assert r.status_code == 200, r.text


# ---------- Password reset flow ----------
class TestPasswordReset:
    def test_forgot_password_customer_creates_token(self, s):
        # Iter11: customer role IS now supported (reset link /recuperar, not /nubo-control/recuperar).
        # Anti-enumeration is still preserved with the same generic message.
        before = _count_tokens_for(CUSTOMER_EMAIL)
        r = s.post(f"{API}/auth/forgot-password", json={"email": CUSTOMER_EMAIL})
        assert r.status_code == 200
        assert "Si el email" in r.json().get("message", "")
        after = _count_tokens_for(CUSTOMER_EMAIL)
        assert after == before + 1, f"Customer token should be created (before={before}, after={after})"

    def test_forgot_password_admin_creates_token(self, s):
        before = _count_tokens_for(ADMIN_EMAIL)
        r = s.post(f"{API}/auth/forgot-password", json={"email": ADMIN_EMAIL})
        assert r.status_code == 200
        # generic message expected
        assert "Si el email" in r.json().get("message", "")
        after = _count_tokens_for(ADMIN_EMAIL)
        assert after == before + 1, f"Admin token not created (before={before}, after={after})"

    def test_forgot_password_unknown_email_generic(self, s):
        r = s.post(f"{API}/auth/forgot-password", json={"email": f"nope_{RUN_ID}@nope.com"})
        assert r.status_code == 200
        assert "Si el email" in r.json().get("message", "")

    def test_reset_password_invalid_token(self, s):
        r = s.post(f"{API}/auth/reset-password", json={"token": "this-is-not-a-real-token", "new_password": "NewPass1234!"})
        assert r.status_code == 400

    def test_reset_password_short_password(self, s):
        r = s.post(f"{API}/auth/reset-password", json={"token": "x", "new_password": "short"})
        assert r.status_code == 400

    def test_reset_password_token_one_shot(self, s, request):
        """Inject a known token in DB to validate full reset + one-shot semantics
        without depending on real email delivery (preview has no RESEND_API_KEY)."""
        import hashlib
        from pymongo import MongoClient
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'glovo_algeciras')
        mc = MongoClient(mongo_url)
        dbm = mc[db_name]

        # Pick an existing manager (just created in TestManagerRBAC). If unavailable, skip.
        mgr_email = STATE.get('mgr_a_email')
        if not mgr_email:
            pytest.skip("No manager created in this run")
        user = dbm.users.find_one({'email': mgr_email})
        assert user, "manager user not in DB"

        raw = f"qa_reset_token_{RUN_ID}"
        thash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        dbm.password_reset_tokens.insert_one({
            'token_hash': thash,
            'user_id': user['id'],
            'email': mgr_email,
            'role': 'manager',
            'expires_at': _dt.now(_tz.utc) + _td(minutes=30),
            'used': False,
            'created_at': _dt.now(_tz.utc),
        })

        new_password = "NewMgrPass1234!"
        r = s.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": new_password})
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True

        # New login works
        r2 = s.post(f"{API}/auth/login", json={"email": mgr_email, "password": new_password})
        assert r2.status_code == 200, f"new password login failed: {r2.text}"

        # Reusing the same token must fail (one-shot)
        r3 = s.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": "Another1234!"})
        assert r3.status_code == 400


def _count_tokens_for(email: str) -> int:
    from pymongo import MongoClient
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'glovo_algeciras')
    mc = MongoClient(mongo_url)
    return mc[db_name].password_reset_tokens.count_documents({'email': email.strip().lower()})


# ---------- Cleanup (best-effort) ----------
def test_zz_cleanup(s, admin_token, request):
    """Delete TEST_ data created in this run."""
    from pymongo import MongoClient
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'glovo_algeciras')
    dbm = MongoClient(mongo_url)[db_name]
    # Delete riders
    for k in ("rider_a_id", "rider_b_id"):
        rid = STATE.get(k)
        if rid:
            dbm.users.delete_one({"id": rid})
    # Delete managers
    for k in ("mgr_a_email", "mgr_b_email"):
        em = STATE.get(k)
        if em:
            dbm.users.delete_one({"email": em})
    # Delete regions
    for k in ("region_a_id", "region_b_id"):
        rid = STATE.get(k)
        if rid:
            dbm.regions.delete_one({"id": rid})
    # Delete forgot tokens we created
    dbm.password_reset_tokens.delete_many({"email": {"$regex": f"_{RUN_ID}"}})
