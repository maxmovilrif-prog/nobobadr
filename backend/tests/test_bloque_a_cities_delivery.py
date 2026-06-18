"""Bloque A — cities, delivery quote, express orders, admin city CRUD."""
import os
import uuid

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN_EMAIL = "admin@nubo.com"
ADMIN_PASS = "Admin1234!"
CUSTOMER_EMAIL = "qa_customer@nubo.com"
CUSTOMER_PASS = "Test1234!"


# --------- fixtures ---------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(session, email, password):
    r = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token(session):
    return _login(session, ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def customer_token(session):
    return _login(session, CUSTOMER_EMAIL, CUSTOMER_PASS)


# --------- public cities ---------
class TestPublicCities:
    def test_public_cities_no_auth(self, session):
        r = session.get(f"{BASE_URL}/api/public/cities")
        assert r.status_code == 200
        data = r.json()
        assert "cities" in data
        cities = data["cities"]
        assert isinstance(cities, list)
        # 16 cities are seeded; allow >= 16 in case tests add some
        assert len(cities) >= 16, f"Expected >=16 cities, got {len(cities)}"

        names = {c["name"] for c in cities}
        for expected in ["Algeciras", "Tánger", "Casablanca", "Madrid", "Barcelona"]:
            assert expected in names, f"Missing seeded city {expected}"

        # countries
        countries = {c["country"] for c in cities}
        assert "ES" in countries and "MA" in countries

        # each city must have id, name, lat, lng, country and NOT _id
        for c in cities:
            assert {"id", "name", "lat", "lng", "country"}.issubset(c.keys())
            assert "_id" not in c
            assert isinstance(c["lat"], (int, float))
            assert isinstance(c["lng"], (int, float))

    def test_cities_requires_auth(self, session):
        r = requests.get(f"{BASE_URL}/api/cities")
        assert r.status_code in (401, 403), f"Expected 401/403 without token, got {r.status_code}"

    def test_cities_authenticated(self, session, customer_token):
        r = requests.get(f"{BASE_URL}/api/cities", headers={"Authorization": f"Bearer {customer_token}"})
        assert r.status_code == 200
        assert len(r.json()["cities"]) >= 16


# --------- delivery quote ---------
class TestDeliveryQuote:
    # Algeciras -> Tánger
    ROUTE = {
        "origin_lat": 36.1408, "origin_lng": -5.4562,
        "destination_lat": 35.7595, "destination_lng": -5.8340,
    }

    def test_motorcycle_eur(self, session):
        r = session.post(f"{BASE_URL}/api/v1/calculate-delivery", json={
            **self.ROUTE, "vehicle_type": "motorcycle", "currency": "EUR"
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["currency"] == "EUR"
        assert d["vehicle_used"] == "motorcycle"
        assert d["distance_km"] > 0
        assert d["delivery_fee"] > 0
        assert d["adjusted_eta_mins"] >= 5
        # base 3 + 0.80*distance
        expected = round(3.0 + 0.80 * d["distance_km"], 2)
        assert abs(d["delivery_fee"] - expected) < 0.05

    def test_car_eur(self, session):
        r = session.post(f"{BASE_URL}/api/v1/calculate-delivery", json={
            **self.ROUTE, "vehicle_type": "car", "currency": "EUR"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["vehicle_used"] == "car"
        expected = round(4.0 + 1.20 * d["distance_km"], 2)
        assert abs(d["delivery_fee"] - expected) < 0.05

    def test_bicycle_eur(self, session):
        r = session.post(f"{BASE_URL}/api/v1/calculate-delivery", json={
            **self.ROUTE, "vehicle_type": "bicycle", "currency": "EUR"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["vehicle_used"] == "bicycle"
        expected = round(2.0 + 0.50 * d["distance_km"], 2)
        assert abs(d["delivery_fee"] - expected) < 0.05

    def test_mad_conversion(self, session):
        eur_resp = session.post(f"{BASE_URL}/api/v1/calculate-delivery", json={
            **self.ROUTE, "vehicle_type": "motorcycle", "currency": "EUR"
        }).json()
        mad_resp = session.post(f"{BASE_URL}/api/v1/calculate-delivery", json={
            **self.ROUTE, "vehicle_type": "motorcycle", "currency": "MAD"
        }).json()
        assert mad_resp["currency"] == "MAD"
        # MAD should be ~10.87x EUR
        ratio = mad_resp["delivery_fee"] / eur_resp["delivery_fee"]
        assert 10.5 < ratio < 11.2, f"Expected MAD/EUR ratio ~10.87, got {ratio}"
        # distance unchanged regardless of currency
        assert mad_resp["distance_km"] == eur_resp["distance_km"]


# --------- express order ---------
class TestExpressOrder:
    PAYLOAD = {
        "origin_name": "Algeciras Centro",
        "origin_lat": 36.1408, "origin_lng": -5.4562,
        "destination_name": "Tánger Centro",
        "destination_lat": 35.7595, "destination_lng": -5.8340,
        "vehicle_type": "motorcycle",
        "fee": 27.10,
        "currency": "EUR",
        "distance_km": 30.13,
        "eta_mins": 59,
    }

    def test_customer_creates_express(self, customer_token):
        r = requests.post(
            f"{BASE_URL}/api/orders/express",
            json=self.PAYLOAD,
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert r.status_code == 200, r.text
        order = r.json()
        assert order["order_type"] == "express"
        assert order["business_id"] is None
        assert order["vehicle_type"] == "motorcycle"
        assert order["origin_name"] == "Algeciras Centro"
        assert order["destination_name"] == "Tánger Centro"
        assert order["distance_km"] == 30.13
        assert order["currency"] == "EUR"
        assert order["total_amount"] == 27.10
        assert order["status"] == "pending"
        assert "id" in order

        # GET to verify persistence
        g = requests.get(
            f"{BASE_URL}/api/orders/{order['id']}",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert g.status_code == 200
        assert g.json()["order_type"] == "express"

    def test_admin_cannot_create_order(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/orders/express",
            json=self.PAYLOAD,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 403

    def test_unauthenticated_cannot_create(self):
        r = requests.post(f"{BASE_URL}/api/orders/express", json=self.PAYLOAD)
        assert r.status_code in (401, 403)


# --------- admin city CRUD ---------
class TestAdminCityCRUD:
    @pytest.fixture
    def temp_city_payload(self):
        # unique name to avoid duplicates in re-runs
        return {
            "name": f"TEST_City_{uuid.uuid4().hex[:8]}",
            "lat": 35.0,
            "lng": -5.0,
            "country": "ES",
        }

    def test_non_admin_cannot_create(self, customer_token, temp_city_payload):
        r = requests.post(
            f"{BASE_URL}/api/admin/cities",
            json=temp_city_payload,
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert r.status_code == 403

    def test_admin_create_update_delete_city(self, admin_token, temp_city_payload):
        hdr = {"Authorization": f"Bearer {admin_token}"}

        # CREATE
        r = requests.post(f"{BASE_URL}/api/admin/cities", json=temp_city_payload, headers=hdr)
        assert r.status_code == 200, r.text
        city = r.json()
        assert city["name"] == temp_city_payload["name"]
        assert city["lat"] == temp_city_payload["lat"]
        assert "id" in city
        city_id = city["id"]

        # verify list contains
        listing = requests.get(f"{BASE_URL}/api/public/cities").json()["cities"]
        assert any(c["id"] == city_id for c in listing)

        # DUPLICATE
        dup = requests.post(f"{BASE_URL}/api/admin/cities", json=temp_city_payload, headers=hdr)
        assert dup.status_code == 400

        # UPDATE
        new_name = temp_city_payload["name"] + "_upd"
        u = requests.patch(
            f"{BASE_URL}/api/admin/cities/{city_id}",
            json={"name": new_name, "lat": 36.5},
            headers=hdr,
        )
        assert u.status_code == 200, u.text
        assert u.json()["name"] == new_name
        assert u.json()["lat"] == 36.5

        # verify update persisted
        listing2 = requests.get(f"{BASE_URL}/api/public/cities").json()["cities"]
        found = next((c for c in listing2 if c["id"] == city_id), None)
        assert found is not None
        assert found["name"] == new_name

        # DELETE
        d = requests.delete(f"{BASE_URL}/api/admin/cities/{city_id}", headers=hdr)
        assert d.status_code == 200

        # verify removed
        listing3 = requests.get(f"{BASE_URL}/api/public/cities").json()["cities"]
        assert not any(c["id"] == city_id for c in listing3)

    def test_non_admin_cannot_delete(self, customer_token):
        # Try delete with a random id; auth check should fire first -> 403
        r = requests.delete(
            f"{BASE_URL}/api/admin/cities/nonexistent",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert r.status_code == 403
