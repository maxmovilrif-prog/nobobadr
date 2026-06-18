# Nubo — PRD & Estado del Proyecto

## Problema / Visión
Nubo (antes "Glovo Algeciras") es un marketplace multiservicio (FastAPI + React + MongoDB, PWA) para España: delivery, paquetería/courier, dropshipping, NuboRide (transporte con conductor) y reservas de viaje (afiliados). Idioma principal del usuario: **Español**. Soporta i18n en 7 idiomas (es, en, fr, nl, de, ar, pt).

## Stack
- Backend: FastAPI, MongoDB (motor), JWT auth, WebSockets (tracking en tiempo real), Stripe, emergentintegrations (LLM + pagos).
- Frontend: React, Shadcn UI, i18next, Google Maps (@react-google-maps/api).
- Roles: customer, driver, business, **admin** (nuevo).

## Implementado (histórico)
- Auth JWT, dashboards (customer/driver/business), pedidos, pagos Stripe, chat.
- i18n 7 idiomas, logos Visa/Mastercard, páginas legales (Privacy/Terms).
- TravelBooking + AffiliateSettings (links de afiliados).
- WebSocket tracking en vivo (`/ws/tracking/{order_id}`), marcador "Abeja" 🐝 en el mapa.
- Contacto global: exprenobo@hotmail.com / +34 654 24 20 92.

## Implementado en esta sesión (2026-06-18)
- **Búsqueda con IA (lenguaje natural)** — `POST /api/search/smart`. Interpreta consultas como "tengo hambre" con `gpt-5.4-mini` (Emergent LLM Key) y devuelve negocios + productos relevantes. UI en CustomerDashboard (tab Negocios). ✅ Testeado (10/10 backend, frontend OK).
- **Panel de Admin con Mapa de Flota en tiempo real** — `AdminDashboard.js`, ruta `/admin` y redirección por rol admin desde `/dashboard`. Endpoints `GET /api/admin/active-drivers` y `GET /api/admin/stats` (protegidos, solo rol admin → 403 si no). Muestra estadísticas, lista de "Abejas" activas y mapa con marcadores verdes. ✅ Testeado.
- Guard de seguridad: `POST /api/auth/register` rechaza rol `admin` (400).
- Cuenta admin sembrada: `admin@nubo.com / Admin1234!` (script `/app/backend/seed_admin.py`).

## Pendiente / Backlog
- **P0/Infra**: Dominio personalizado **nuboexpress.com** (bloqueado, requiere acción del usuario en UI de Emergent o soporte). Contraseña "Emergent Code Server" ($PASSWORD vacío en entorno — es tema de plataforma).
- **P1**: Configurar clave real de Google Maps (`REACT_APP_GOOGLE_MAPS_API_KEY`) — actualmente placeholder, el mapa muestra error de Google (esperado).
- **P2 (calidad)**: `server.py` ~1159 líneas; conviene modularizar (auth, orders, admin, search). Considerar persistir `current_location` de conductores en BD para mostrarlos en el mapa aunque no tengan pedido activo.

## Endpoints clave nuevos
- `POST /api/search/smart` body `{query, language?}` → `{message, categories, keywords, businesses, products}`
- `GET /api/admin/active-drivers` (admin) → `{count, live_count, available_count, active_orders, drivers[]}`
- `GET /api/admin/stats` (admin)

## Notas
- App usa MongoDB (NO PostgreSQL).
- Tests: `/app/backend/tests/test_nubo_features.py`. Credenciales: `/app/memory/test_credentials.md`.
