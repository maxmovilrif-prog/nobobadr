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
- **Búsqueda con IA (lenguaje natural)** — `POST /api/search/smart`. Interpreta consultas como "tengo hambre" con `gpt-5.4-mini` (Emergent LLM Key) y devuelve negocios + productos relevantes. UI en CustomerDashboard (tab Negocios). ✅ Testeado.
- **Panel de Admin con Mapa de Flota en tiempo real** — `AdminDashboard.js`, ruta `/admin` y redirección por rol admin desde `/dashboard`. Endpoints `GET /api/admin/active-drivers` y `GET /api/admin/stats` (protegidos, solo rol admin → 403). ✅ Testeado.
- Guard de seguridad: `POST /api/auth/register` rechaza rol `admin` (400).
- Cuenta admin sembrada: `admin@nubo.com / Admin1234!` (script `/app/backend/seed_admin.py`).
- **Alertas en tiempo real (Admin)** — sonido (Web Audio API, sin assets) + toast + feed "Alertas recientes". Detecta: pedido nuevo (incremento de pedidos) y "Abeja parada" (backend marca `idle`/`idle_seconds` si una Abeja en vivo no envía señal en >90s; `idle_count` en la respuesta). Botón "Activar alertas". ✅ Testeado (pedido nuevo end-to-end).
- **Modularización de `server.py`** (1178 → 74 líneas): `core.py` (db, config, auth, ConnectionManager), `models.py`, y `routes/` (auth, businesses, search, orders, drivers, messages, payments, dropshipping, affiliate, tracking, admin). Sin cambios en contratos de API. ✅ 32/32 pytest, sin regresiones.
- **Alertas por Telegram (backend, panel cerrado)** — `telegram_alerts.py`: notifica al admin de **pedido nuevo** (en `POST /api/orders`) y **Abeja parada** (monitor en background cada 30s, umbral >90s). **Comando `/flota`** (listener long-polling de getUpdates): responde con resumen de Abejas en vivo/paradas, disponibles y pedidos en reparto/pendientes; `/start` y `/help` devuelven el chat_id y la ayuda. Endpoints admin: `telegram/status`, `telegram/test`, `telegram/chats` (chat_ids capturados en memoria por el listener). UI: tarjeta "Alertas Telegram" en AdminDashboard. ⏳ PENDIENTE token válido (`TELEGRAM_BOT_TOKEN` en backend/.env; chat_id se autodetecta con /start o se fija con `TELEGRAM_ADMIN_CHAT_ID`). Pipeline verificado; no-op seguro si no hay token.
- **Fix `POST /api/products`**: validación de rol movida a dependencia `get_current_business` → devuelve 403 antes que 422. ✅ Verificado.

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
