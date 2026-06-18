# Auth Testing Playbook — Nubo

This project uses **Bearer-token JWT** auth (not cookies). Token in `Authorization: Bearer <token>`.

## Accounts
- Founder/Admin: `admin@nubo.com` / `Admin1234!` (role=admin, exclusive console)
- Customer: `qa_customer@nubo.com` / `Test1234!`

## Founder login (brute-force protected)
```
curl -X POST $URL/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@nubo.com","password":"Admin1234!"}'
```
- 5 failed attempts per {ip:email} → 15 min lockout (429).

## Rider activation by code (no email/password)
1. Admin creates rider: `POST /api/admin/riders` (admin token) → returns rider + `activation_code` (e.g. NUBO-7F3K) + `qr_data_url`.
2. Rider activates: `POST /api/rider/activate` body `{"code":"NUBO-7F3K"}` → returns `{token, rider}` (long-lived driver JWT).
3. Rider uses token: `GET /api/rider/me`, `POST /api/rider/location`.

## Admin rider management
- `GET /api/admin/riders` (admin) — list with status.
- `PATCH /api/admin/riders/{id}` (admin) — update contract_status / vehicle_type.
- `GET /api/admin/riders/{id}/qr` (admin) — QR data URL for the code.
