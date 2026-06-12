# Test Credentials — Nubo Express

## Admin (Live Map Dashboard)
- Email: admin@nuboexpress.com
- Password: Admin123!
- Route after login: /admin (live map of active "Bee" drivers across Spain)

## Customer (AI Smart Search)
- Email: cliente@nubotest.com
- Password: Cliente123!
- Route: /dashboard (AI search bar at top)

## Demo Drivers (Bees) — seeded, is_available=true with Spain locations
- bee.madrid@nuboexpress.com / Bee123!
- bee.barcelona@nuboexpress.com / Bee123!
- bee.valencia@nuboexpress.com / Bee123!
- bee.sevilla@nuboexpress.com / Bee123!
- bee.algeciras@nuboexpress.com / Bee123!
- bee.malaga@nuboexpress.com / Bee123!

Notes:
- Admin user and demo drivers are auto-seeded on backend startup (server.py seed_admin_and_drivers).
- AI Smart Search endpoint: POST /api/search/smart (no auth required), uses Emergent LLM Key (openai gpt-4o-mini).
