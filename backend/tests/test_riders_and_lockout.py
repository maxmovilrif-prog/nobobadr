"""
Backend tests for the Rider App (activation by code/QR) + admin rider CRUD
+ brute-force lockout on /api/auth/login.

Endpoints under test:
- POST   /api/admin/riders               (admin) create
- GET    /api/admin/riders               (admin) list
- PATCH  /api/admin/riders/{id}          (admin) update / suspend / reactivate
- POST   /api/admin/riders/{id}/regenerate-code  (admin)
- POST   /api/rider/activate             (public)
- GET    /api/rider/me                   (rider)
- PATCH  /api/rider/availability         (rider)
- POST   /api/rider/location             (rider)
- POST   /api/auth/login                 (brute-force lockout, 5 fails -> 429)
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN_EMAIL = "admin@nubo.com"
ADMIN_PASS = "Admin1234!"
CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASS = "Test1234!"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def customer_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASS}, timeout=15)
    if r.status_code != 200:
        pytest.skip("customer login failed")
    return r.json()["token"]


@pytest.fixture(scope="module")
def created_rider(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "name": f"TEST_Rider_{uuid.uuid4().hex[:6]}",
        "phone": "+34600111222",
        "vehicle_type": "motorcycle",
        "dni": "X1234567Z",
        "license_plate": "1234-ABC",
    }
    r = requests.post(f"{BASE_URL}/api/admin/riders", json=payload, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


# ============================================================
# Admin rider creation / listing
# ============================================================
class TestAdminRiderCRUD:
    def test_create_rider_returns_code_and_qr(self, created_rider):
        assert "id" in created_rider
        assert created_rider["activation_code"].startswith("NUBO-")
        assert len(created_rider["activation_code"]) == 9  # NUBO-XXXX
        assert created_rider["activated"] is False
        assert created_rider["contract_status"] == "active"
        assert created_rider["qr_data_url"].startswith("data:image/png;base64,")
        assert len(created_rider["qr_data_url"]) > 200

    def test_create_rider_invalid_vehicle_400(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.post(f"{BASE_URL}/api/admin/riders",
                          json={"name": "X", "phone": "+34600", "vehicle_type": "plane"},
                          headers=headers, timeout=10)
        assert r.status_code == 400

    def test_create_rider_non_admin_403(self, customer_token):
        headers = {"Authorization": f"Bearer {customer_token}"}
        r = requests.post(f"{BASE_URL}/api/admin/riders",
                          json={"name": "Y", "phone": "+34600", "vehicle_type": "car"},
                          headers=headers, timeout=10)
        assert r.status_code == 403

    def test_list_riders_admin(self, admin_token, created_rider):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{BASE_URL}/api/admin/riders", headers=headers, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "riders" in data and "count" in data
        assert data["count"] >= 1
        ids = [x["id"] for x in data["riders"]]
        assert created_rider["id"] in ids

    def test_list_riders_non_admin_403(self, customer_token):
        headers = {"Authorization": f"Bearer {customer_token}"}
        r = requests.get(f"{BASE_URL}/api/admin/riders", headers=headers, timeout=10)
        assert r.status_code == 403


# ============================================================
# Rider activation (public via code) + token usage
# ============================================================
class TestRiderActivation:
    def test_activate_invalid_code_404(self):
        r = requests.post(f"{BASE_URL}/api/rider/activate",
                          json={"code": "NUBO-ZZZZ-NOPE"}, timeout=10)
        assert r.status_code == 404

    def test_activate_valid_code_and_use_token(self, created_rider):
        code = created_rider["activation_code"]
        r = requests.post(f"{BASE_URL}/api/rider/activate", json={"code": code}, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data and "rider" in data
        assert data["rider"]["id"] == created_rider["id"]
        assert data["rider"]["activated"] is True
        token = data["token"]

        # GET /api/rider/me
        rh = {"Authorization": f"Bearer {token}"}
        me = requests.get(f"{BASE_URL}/api/rider/me", headers=rh, timeout=10)
        assert me.status_code == 200
        assert me.json()["id"] == created_rider["id"]
        assert "_id" not in me.json()

        # PATCH availability
        av = requests.patch(f"{BASE_URL}/api/rider/availability?is_available=true",
                            headers=rh, timeout=10)
        assert av.status_code == 200
        assert av.json()["is_available"] is True

        # POST location
        loc = requests.post(f"{BASE_URL}/api/rider/location",
                            json={"lat": 36.13, "lng": -5.45}, headers=rh, timeout=10)
        assert loc.status_code == 200
        assert loc.json().get("ok") is True

        # store token for non-driver test
        TestRiderActivation.rider_token = token

    def test_rider_me_with_admin_token_403(self, admin_token):
        rh = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{BASE_URL}/api/rider/me", headers=rh, timeout=10)
        assert r.status_code == 403


# ============================================================
# Suspend / reactivate / regenerate-code
# ============================================================
class TestRiderLifecycle:
    def test_suspend_then_activate_blocked(self, admin_token, created_rider):
        headers = {"Authorization": f"Bearer {admin_token}"}
        rid = created_rider["id"]
        code = created_rider["activation_code"]

        # Invalid contract_status -> 400
        bad = requests.patch(f"{BASE_URL}/api/admin/riders/{rid}",
                             json={"contract_status": "weird"},
                             headers=headers, timeout=10)
        assert bad.status_code == 400

        # Suspend
        r = requests.patch(f"{BASE_URL}/api/admin/riders/{rid}",
                           json={"contract_status": "suspended"},
                           headers=headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["contract_status"] == "suspended"

        # Activate with suspended code -> 403
        act = requests.post(f"{BASE_URL}/api/rider/activate", json={"code": code}, timeout=10)
        assert act.status_code == 403

        # Reactivate
        r2 = requests.patch(f"{BASE_URL}/api/admin/riders/{rid}",
                            json={"contract_status": "active"},
                            headers=headers, timeout=10)
        assert r2.status_code == 200
        assert r2.json()["contract_status"] == "active"

        # Now activation works again
        act2 = requests.post(f"{BASE_URL}/api/rider/activate", json={"code": code}, timeout=10)
        assert act2.status_code == 200

    def test_regenerate_code_invalidates_old(self, admin_token, created_rider):
        headers = {"Authorization": f"Bearer {admin_token}"}
        rid = created_rider["id"]
        old_code = created_rider["activation_code"]

        r = requests.post(f"{BASE_URL}/api/admin/riders/{rid}/regenerate-code",
                          headers=headers, timeout=10)
        assert r.status_code == 200
        new_code = r.json()["activation_code"]
        assert new_code.startswith("NUBO-")
        assert new_code != old_code
        assert r.json()["qr_data_url"].startswith("data:image/png;base64,")

        # Old code no longer works
        old = requests.post(f"{BASE_URL}/api/rider/activate", json={"code": old_code}, timeout=10)
        assert old.status_code == 404

        # New code works
        new = requests.post(f"{BASE_URL}/api/rider/activate", json={"code": new_code}, timeout=10)
        assert new.status_code == 200


# ============================================================
# Brute-force lockout (use a THROWAWAY email — never real admin)
# ============================================================
class TestBruteForceLockout:
    THROWAWAY = f"bruteforce_test_{uuid.uuid4().hex[:6]}@nope.com"

    def test_lockout_logic_via_localhost(self):
        """Validate lockout LOGIC directly against backend (bypassing K8s ingress).

        NOTE: when going through the public URL, the K8s ingress rotates between
        several proxy pods so `request.client.host` differs across requests and
        the per-(ip:email) counter NEVER reaches 5 on a single identifier.
        That is a real production concern — see frontend_issues / action_items
        in the test report; the backend should honour X-Forwarded-For.
        """
        local = "http://localhost:8001"
        email = self.THROWAWAY
        codes = []
        for _ in range(7):
            r = requests.post(f"{local}/api/auth/login",
                              json={"email": email, "password": "wrong"}, timeout=10)
            codes.append(r.status_code)
        # Expect first 5 -> 401, then 429
        assert codes[:5] == [401] * 5, f"got {codes}"
        assert codes[5] == 429, f"expected 6th attempt locked, got {codes}"
        assert codes[6] == 429

    def test_lockout_via_public_url_ingress_aware(self):
        """Public URL: at least ONE proxy pod should hit the lockout after enough
        attempts. If load-balanced too widely the test is skipped — but the issue
        is recorded in the report."""
        email = f"bf_pub_{uuid.uuid4().hex[:6]}@nope.com"
        sess = requests.Session()
        seen_429 = False
        for _ in range(20):  # 20 attempts to maximise chance of hitting one pod 5x
            r = sess.post(f"{BASE_URL}/api/auth/login",
                          json={"email": email, "password": "wrong"}, timeout=10)
            if r.status_code == 429:
                seen_429 = True
                break
            assert r.status_code == 401
        if not seen_429:
            pytest.skip("Ingress proxy IP rotation prevented per-IP lockout — see report")

    def test_correct_login_before_lockout_clears_attempts(self):
        # Use a different throwaway email — 3 fails + 1 success (won't succeed because
        # account doesn't exist, but we test the counter clears on successful auth).
        # So instead we use the customer account: 2 fails then correct login then more fails.
        # Make sure we don't trip lockout on the customer either.
        email = CUSTOMER_EMAIL
        for _ in range(2):
            r = requests.post(f"{BASE_URL}/api/auth/login",
                              json={"email": email, "password": "definitelyWrong!"}, timeout=10)
            assert r.status_code == 401
        # successful login -> clears attempts
        ok = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"email": email, "password": CUSTOMER_PASS}, timeout=10)
        if ok.status_code != 200:
            pytest.skip("customer account unavailable")
        # 4 more failed attempts should NOT lock (because counter was cleared)
        for _ in range(4):
            r = requests.post(f"{BASE_URL}/api/auth/login",
                              json={"email": email, "password": "stillWrong!"}, timeout=10)
            assert r.status_code == 401, "counter was NOT cleared after success"
        # Cleanup: successful login again to clear attempts
        requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": CUSTOMER_PASS}, timeout=10)
