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
- **Alertas por Telegram (backend, panel cerrado)** — `telegram_alerts.py`: notifica al admin de **pedido nuevo** (en `POST /api/orders`, con **botones inline** "✅ Asignar a Abeja" y "👁 Ver pedido") y **Abeja parada** (monitor background cada 30s, >90s). **Comando `/flota`** + `/start`/`/help` (devuelven chat_id) vía listener long-polling. **Callbacks inline**: asignar pedido → lista de Abejas disponibles → asignación en 1 toque (set driver_id + status `accepted`); ver pedido → detalle. Endpoints admin: `telegram/status`, `telegram/test`, `telegram/chats`. UI: tarjeta "Alertas Telegram". Lógica de asignación verificada por test directo; 32/32 pytest sin regresión. ⏳ PENDIENTE token válido en `backend/.env` (`TELEGRAM_BOT_TOKEN`); chat_id se autodetecta con /start o `TELEGRAM_ADMIN_CHAT_ID`. No-op seguro sin token.
- **Fix `POST /api/products`**: validación de rol movida a dependencia `get_current_business` → devuelve 403 antes que 422. ✅ Verificado.

## Bloque A — Envíos por distancia + cobertura por ciudades (2026-06-18) ✅
- Backend `geo.py` (haversine, moneda por país ES€/MA·MAD, tarifas por vehículo, `calculate_delivery_quote`). `routes/cities.py`: `GET /public/cities`, `GET /cities`, `POST /v1/calculate-delivery`, CRUD admin `/admin/cities`. `POST /orders/express` (pedido punto a punto). Modelos City/Express. `seed_cities.py` (16 ciudades ES+MA).
- Frontend `DeliveryQuote.js` (`/presupuesto`, público, €/MAD), `CityManager.jsx` (en AdminDashboard). Banner exprés en CustomerDashboard. ✅ 45/45 pytest + e2e.

## Arquitectura separada: Panel Fundador + App Riders (2026-06-18) ✅
- **App de Conductores (Riders)** en `/rider` (PWA mobile, token aislado `nubo_rider_token`): activación por **código/QR** (sin email/contraseña), home con perfil, disponibilidad, ubicación en vivo y pedidos asignados.
- **Sistema de riders backend** `routes/riders.py`: alta admin con **código `NUBO-XXXX` + QR (base64 PNG)**, `/rider/activate`, `/rider/me`, `/rider/location`, `/rider/availability`, suspender/reactivar, regenerar código. `get_current_rider`, `create_rider_token` (30 días), `generate_qr_data_url` (lib `qrcode`).
- **Seguridad capa Fundador**: login con **brute-force lockout** (5 intentos/15 min, IP real vía `X-Forwarded-For`). Registro público no crea admin. Consola admin exclusiva.
- **Gestión de riders en panel** `RiderManager.jsx` (alta + QR imprimible + suspender + regenerar). ✅ 58/58 pytest + frontend e2e 100%.
- **Escáner QR de cámara** en la app del rider (`html5-qrcode`): botón "Escanear QR" + overlay, además del código manual. ✅

## Bloque B — Seguimiento público de pedidos (2026-06-18) ✅
- Backend `GET /api/public/orders/{id}/tracking` (público): estado, ruta origen/destino, precio €/MAD, repartidor y ubicación (en vivo por WebSocket si existe).
- Frontend `PublicTracking.js` (`/track`, público): búsqueda por nº de pedido, mapa con ruta, switch €/MAD, compartir por WhatsApp, demos `ORD-4821`/`ORD-4823`, auto-refresco cada 15s, deep-link `?order=`. Botón "Seguir mi pedido" en CustomerDashboard. ✅ 62/62 pytest + frontend e2e 100%.

## Pendiente / Backlog (actualizado 2)
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
