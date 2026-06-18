"""Test de seguridad: el bloqueo anti-fuerza-bruta del login es efectivo a través
del ingress de Kubernetes (usa X-Forwarded-For, no la IP del proxy).

Se usa un email inexistente y único para no afectar a cuentas reales: el identificador
de bloqueo es {ip:email}, así que solo se bloquea esa combinación durante el test.
"""
import os
import uuid
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"


def test_login_lockout_triggers_through_public_url():
    email = f"bruteforce_{uuid.uuid4().hex[:10]}@nope.nubo"
    payload = {"email": email, "password": "wrong-on-purpose"}

    # 5 intentos fallidos -> 401
    statuses = []
    for _ in range(5):
        r = requests.post(f"{API}/auth/login", json=payload)
        statuses.append(r.status_code)
    assert all(s == 401 for s in statuses), statuses

    # 6º intento -> 429 (cuenta/identificador bloqueado)
    r = requests.post(f"{API}/auth/login", json=payload)
    assert r.status_code == 429, f"esperado 429, recibido {r.status_code}: {r.text}"
    assert "bloquead" in r.json().get("detail", "").lower()
