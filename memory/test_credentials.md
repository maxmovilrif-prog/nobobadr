# Test Credentials — Nubo Express

## Admin (live map dashboard)
- email: admin@nuboexpress.com
- password: Admin1234
- role: admin → redirects to AdminDashboard (/admin)

## Demo Drivers (available, with location for admin map)
- bee.madrid@nubo.com / Driver1234
- bee.barcelona@nubo.com / Driver1234
- (and others created by /app/backend/seed_admin.py — all password Driver1234)

## Notes
- Seed script: `python /app/backend/seed_admin.py` (idempotent)
- Other customer/driver/business test accounts exist from earlier registration scripts.
- Google Maps API key (frontend/.env REACT_APP_GOOGLE_MAPS_API_KEY) currently returns InvalidKeyMapError — needs valid key with Maps JavaScript API + billing enabled.
