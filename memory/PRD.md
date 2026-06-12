# Nubo Express — PRD

## Problem statement
Glovo-like multi-service marketplace for **España y Marruecos**. Stack: React (PWA) + FastAPI + MongoDB.
Features: customer ordering (food, courier, electronics, vehicles), NuboRide ride-sharing, dropshipping,
affiliate travel bookings (flights/ferries/hotels), multi-language (es/en/fr/nl/de/ar/pt), real-time driver
("Bee") tracking via WebSockets, Stripe + Google Maps integration. User language: **Spanish**.

## Roles
- customer, driver, business, **admin** (new)

## Implemented (2026-06-12)
- **AI Smart Search** (Emergent LLM, gpt-4o-mini): `POST /api/search/smart` returns top-3 businesses for a
  natural-language query + reason. UI card in CustomerDashboard (smart-search-*). Tested ✅.
- **Admin Dashboard** (`/admin`, role=admin → AdminDashboard.js): live Google map of all active Bees +
  stats cards (`GET /api/admin/stats`, `GET /api/admin/active-drivers`). Auto-refresh 10s. Tested ✅ (map
  needs valid Google key).
- **Driver location push**: `PATCH /api/drivers/location` stores current_location; DriverDashboard sends on
  availability + during delivery. Tested ✅.
- **Marruecos re-added** alongside España across Landing/Privacy/Terms/locales/CustomerDashboard texts.
- **Google Maps key** set from user value (InvalidKeyMapError — needs Maps JS API + billing enabled).
- Seed: `python /app/backend/seed_admin.py` → admin + 7 demo drivers (idempotent).
- Pytest suite: `/app/backend/tests/test_admin_and_smart_search.py` (11/11 pass).

## Backlog / Next
- P1: User must enable a valid Google Maps API key (Maps JavaScript API + billing) so maps render.
- P2: Real-time admin map via WebSocket push (currently 10s polling).
- P2: Migrate google.maps.Marker → AdvancedMarkerElement (deprecation warning).
- Future: PostgreSQL migration (deferred; MongoDB working).

## Key creds
See /app/memory/test_credentials.md. Admin: admin@nuboexpress.com / Admin1234.
