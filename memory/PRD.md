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
- ✅ **Logística geoespacial:** índice 2dsphere en `users.geo_location`; endpoints `GET /api/drivers/nearest` y `POST /api/orders/{id}/assign-nearest` (admin/business). En el panel admin, card "Pedidos pendientes" + botón **"Asignar más cercano"** con **diálogo de confirmación** ("¿Confirmar asignación a {repartidor} a X km?") y, al confirmar, el mapa **vuela y resalta** la Abeja elegida (marcador dorado pulsante, auto-limpiado a los 15s).
- ✅ **Inicialización de esquema MongoDB:** colecciones + índices (email/id únicos, role, order indexes, 2dsphere) en `init_collections_and_indexes` al arranque.
- ✅ **Portal Admin separado y oculto** (`/admin-nubo`): login oscuro con email + contraseña + código secreto, bloqueo anti fuerza bruta (5/15min), validación en servidor. `/auth` rechaza admin. `robots.txt` + `noindex`. Credenciales en backend/.env. Panel en `/admin-nubo/panel`.
- ✅ Mensajes de error de Auth específicos (email duplicado, credenciales, conexión).
- ✅ GPS automático del repartidor (Disponible → geo_location en vivo).
- ✅ Búsqueda Inteligente IA (openai gpt-4o-mini) + Admin Live Map (Leaflet).
- (Sesiones previas) Páginas legales, WebSockets tracking, 7 idiomas, viajes afiliados, NuboRide, dropshipping.

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
