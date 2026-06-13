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
- ✅ **Portal Admin separado y oculto** (`/admin-nubo`): login oscuro independiente con email + contraseña + **código secreto**, bloqueo anti fuerza bruta (5 intentos/15 min), validación 100% en servidor (`POST /api/admin-auth/login`). El login público `/auth` RECHAZA el rol admin. Sin enlaces públicos, `robots.txt` Disallow + meta `noindex`. Credenciales nuevas exclusivas en backend/.env (ADMIN_EMAIL/PASSWORD/SECRET_CODE). Admin antiguo eliminado. Panel en `/admin-nubo/panel`.
- ✅ Mensajes de error de Auth específicos (email duplicado, credenciales inválidas, conexión).
- ✅ GPS automático del repartidor (Disponible → PATCH /api/drivers/location cada 10s → Abeja en vivo en el mapa).
- ✅ Búsqueda Inteligente IA: POST /api/search/smart (openai gpt-4o-mini). Barra en CustomerDashboard.
- ✅ Admin Live Map Dashboard: mapa Leaflet de España con Abejas 🐝 verdes + métricas. Auto-refresh 10s.
- (Sesiones previas) Páginas legales, WebSockets tracking, 7 idiomas, reservas de viajes afiliados, NuboRide, dropshipping.

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
