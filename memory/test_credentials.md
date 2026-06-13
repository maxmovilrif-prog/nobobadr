# Test Credentials — Nubo Express

## Admin Portal (SEPARATE, hidden) — /admin-nubo
- Login URL: /admin-nubo   (dashboard at /admin-nubo/panel)
- Email: control@nuboexpress.com
- Password: Fn6FcMveVf%--1o-
- Secret code (código secreto): NUBO-84D2-C159-E3CF
- Requires ALL THREE (email + password + secret_code) at POST /api/admin-auth/login.
- Brute-force: 5 failed attempts → 15 min lockout (HTTP 429).
- Admins CANNOT log in via the public /auth page (returns 401). Legacy admin@nuboexpress.com was removed.
- Stored in backend/.env: ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_SECRET_CODE.

## Customer (AI Smart Search)
- Email: cliente@nubotest.com
- Password: Cliente123!
- Route: /dashboard (AI search bar at top)

## Real Driver (live GPS → Admin map)
- driver.real@nubotest.com / Driver123!
- Toggle "Disponible" ON → browser sends GPS every 10s via PATCH /api/drivers/location → appears as a live Bee on /admin map.

## Demo Drivers (Bees) — seeded, is_available=true with Spain locations- bee.madrid@nuboexpress.com / Bee123!
- bee.barcelona@nuboexpress.com / Bee123!
- bee.valencia@nuboexpress.com / Bee123!
- bee.sevilla@nuboexpress.com / Bee123!
- bee.algeciras@nuboexpress.com / Bee123!
- bee.malaga@nuboexpress.com / Bee123!

Notes:
- Admin user and demo drivers are auto-seeded on backend startup (server.py seed_admin_and_drivers).
- AI Smart Search endpoint: POST /api/search/smart (no auth required), uses Emergent LLM Key (openai gpt-4o-mini).
