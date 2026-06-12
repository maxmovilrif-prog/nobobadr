# Nubo Express — PRD

## Problema original
Marketplace multiservicio tipo Glovo para España ("Nubo Express"): delivery de comida/paquetería, ride-sharing (NuboRide), dropshipping y reservas de viajes por afiliados. Stack: FastAPI + React + MongoDB. Idioma del usuario: **Español** (a veces Darija). Responder siempre en español.

## Arquitectura
- backend/server.py — rutas /api, WebSockets de tracking, dropshipping, afiliados, búsqueda IA, admin
- frontend/src — React + Tailwind + Shadcn, i18next (7 idiomas), PWA
- DB: MongoDB (Motor), IDs UUID Pydantic. NO migrar a PostgreSQL.

## Integraciones
- Stripe (pagos) — sk_test_emergent
- Google Maps (placeholder key) — el Admin map usa **Leaflet/OpenStreetMap** (sin key)
- Emergent LLM Key (búsqueda IA) — openai gpt-4o-mini

## Implementado (Jun 2026)
- ✅ Búsqueda Inteligente IA: POST /api/search/smart (lenguaje natural → top 3 negocios). Barra en CustomerDashboard (ai-search-card/input/btn/results).
- ✅ Admin Live Map Dashboard: /admin (rol admin), mapa Leaflet de España con Abejas 🐝 verdes en vivo. Endpoints /api/admin/active-drivers, /api/admin/stats. Auto-refresh 10s.
- ✅ PATCH /api/drivers/location (repartidor actualiza ubicación).
- ✅ Seed automático: admin@nuboexpress.com + 6 drivers demo con ubicación en España.
- (Sesiones previas) Páginas legales, WebSockets tracking con icono Bee, 7 idiomas, reservas de viajes afiliados, NuboRide, dropshipping.

## Credenciales de prueba
Ver /app/memory/test_credentials.md

## Backlog / Próximas tareas
- P1: Campo de cuenta bancaria en BusinessDashboard para seguimiento de comisiones (acordado, pendiente).
- P2: Guía publicación Google Play / App Store (PWA → TWA/Capacitor).
- P2: Verificar cambio de dominio a noboexpress.com (support agent, pendiente verificación usuario).
- Refactor: server.py >700 líneas → dividir en routers (auth, businesses, orders, admin, search).

## Estado de pruebas
- Backend: 10/10 pytest PASS (/app/backend/tests/test_nubo_features.py) — iteration_2.
- Frontend: Búsqueda IA + Admin map 100% (iteration_2, iteration_3).
