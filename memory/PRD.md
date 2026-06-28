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

## Implementado en esta sesión (2026-06-19/20) — Arquitectura multi-app + Regional
- **Separación total web pública / panel oculto**: `/` siempre Landing pública (sin login); panel admin oculto en `/nubo-control` con login propio (`AdminLogin.js`). `/admin` y `/dashboard` (admin) → `/nubo-control`. Web pública solo informativa con acceso discreto "Área de clientes" (navbar + footer) → `/auth`.
- **Sesiones aisladas**: `AdminAuthContext` (token `nubo_admin_token`) independiente del cliente (`token`) y del rider (`nubo_rider_token`). Resuelve fuga de sesión entre cliente/admin.
- **Enrutado por subdominio (1 despliegue)**: `frontend/src/lib/portal.js` → `director.noboexpress.com` (Fundador, role admin), `delegacion.noboexpress.com` (Gestores, role manager), `noboexpress.com` (clientes). Rutas ocultas como fallback. DNS lo gestiona el usuario con Soporte.
- **Arquitectura REGIONAL multi-tenant** (`routes/regions.py`, `core.get_scope_city_ids`): Delegaciones (`regions`: name + city_ids) creadas por el Fundador (`RegionManager.jsx`). Gestores (`manager`) vinculados a UNA región (`ManagerManager.jsx` con selector). Aislamiento estricto: gestor solo ve pedidos/riders/ops/stats de SU región; 403 en KPIs/Contabilidad/regiones/alta-gestores. Riders con `region_id`; Fundador o Gestor regional ven/regeneran código/QR (`routes/riders.py`, scoping `_get_rider_in_scope`).
- **Reset de contraseña por email** (Fundador + Gestores + **Clientes**): `POST /api/auth/forgot-password` (roles admin/manager/customer/business; enlace por rol → gestión `/nubo-control/recuperar`, clientes `/recuperar`) + `/auth/reset-password` (token sha256, TTL 1h, un solo uso, anti-enumeración) vía Resend. UI: "¿Olvidaste tu contraseña?" en login admin Y en `/auth` (clientes); páginas `/nubo-control/recuperar` y `/recuperar`. Riders excluidos (entran por QR → recuperación = regenerar código).
- **Reseteo de emergencia** `POST /api/admin/reset-password` (guardado por `ADMIN_RESET_SECRET`, crea admin si no existe) + formulario web `/nubo-control/reset` con ojo 👁️.
- **Stripe**: override `STRIPE_LIVE_KEY` + badge LIVE/TEST en panel. **MongoDB Atlas** producción: override `MONGO_URL_OVERRIDE`/`DB_NAME_OVERRIDE` (core.py), seed `seed_atlas.py` (16 ciudades + Fundador).
- ✅ Testeado: **140/140 pytest** + frontend e2e (iteration_10.json). Email Login normaliza a minúsculas.

## i18n profesional ES/AR + RTL + WhatsApp Twilio (2026-06-22)
- **Switcher de idioma 100% funcional**: ES y AR con PARIDAD COMPLETA (195 claves, AR 100% traducido, terminología logística profesional/corporativa). Internacionalizados: Landing (header, hero CTAs, why-us, features, CTA final), Footer, DeliveryQuote (flujo Camión), QuoteConfirm.
- **RTL automático en carga**: `i18n.js` ahora aplica `document.dir=rtl/ltr` y `lang` al iniciar y en `languageChanged` (antes solo se aplicaba al pulsar el switcher → bug corregido).
- **Terminología logística** (namespace `logistics`): "Camión / Logística Pesada"=شاحنة / الخدمات اللوجستية الثقيلة, "Solicitar Cotización"=طلب عرض أسعار, "Tarifa personalizada por la administración"=تعرفة مخصّصة تحدّدها الإدارة, etc.
- **WhatsApp Twilio** (`whatsapp_service.py`): lee TWILIO_ACCOUNT_SID/AUTH_TOKEN/WHATSAPP_FROM SOLO de os.environ (sin defaults), degrada elegantemente si falta config. Cableado al fijar precio (junto al email). Secrets configurados por el usuario en producción → enviará al desplegar. `twilio==9.10.9` en requirements.txt.
- **White screen Camión**: NO reproducible en preview (código actual correcto); era el deploy obsoleto en producción. Se resuelve al desplegar el código actual.
- Panel admin logística: 2 secciones (pending_quote "sin precio" + quoted "por confirmar"), endpoint `GET /admin/logistics-quotes?status=`.


## Historial de notificaciones + reenvío (2026-06-22, sesión fork)
- **Registro de envíos**: helper `_dispatch_quote_notifications(order_id, priced_order, customer)` en `orders.py` envía email + WhatsApp cliente + WhatsApp admin, captura el resultado de cada canal `{sent, reason/via}` y lo persiste en `db.orders` vía `$push` al array `notifications` (+ `last_notified_at`). `set-quote-price` lo lanza en background (respuesta rápida).
- **Reenvío manual**: `POST /api/orders/{id}/resend-quote-notification` (admin/manager, solo estado 'quoted') reenvía y devuelve el registro (awaited). Añade nueva entrada al historial.
- **UI admin** (`LogisticsQuotesManager.jsx`): cada cotización valorada muestra "Historial de notificaciones" con badges por canal (Email / WA cliente / WA admin, verde=enviado, rojo=fallo con tooltip de motivo), fecha de último envío, contador de envíos, y botón "Reenviar notificación".
- ✅ Verificado E2E en preview: curl (crear→fijar precio→historial registrado→reenviar 2ª entrada) + screenshot del panel. Email=gmail OK, WhatsApp=not_configured en preview (esperado).

## Opción B: Alerta WhatsApp admin + número oficial unificado (2026-06-22, sesión fork)
- **Número admin oficial unificado a `+34612284215`** en TODO el sistema (reemplaza antiguos `+34654242092` y `+34654232573`, eliminados por completo):
  - `seed_admin.py`: phone en creación Y actualización del admin.
  - Frontend: `WhatsAppButton.js` (fallback) y `App.js` L178 (botón flotante WhatsApp).
  - DB de preview actualizada vía seed; producción al redeploy.
- **Opción B — alerta WhatsApp al admin** (`whatsapp_service.notify_admin_logistics_priced`): al fijar precio (`PATCH /orders/{id}/set-quote-price`) el sistema notifica al CLIENTE (email + WhatsApp) Y envía copia/alerta al WhatsApp del admin (`role:'admin'` leído dinámicamente de DB → `whatsapp:+34612284215`). Best-effort vía `asyncio.create_task`, no bloquea respuesta. Proyección del cliente incluye `name` para la alerta.
- ✅ Testeado: testing_agent 5/5 backend GREEN (iteration_15.json). Flujo crear→fijar precio→notificar cliente+admin→confirmar sin errores.
- **Producción noboexpress.com**: deploy estabilizado (MONGO_URL corregido a `cluster0.6isx6d9.mongodb.net`, había typo `1nubo` que tumbó un deploy). Secrets Twilio + APP_BASE_URL configurados por el usuario. Backend+DB verificados en vivo (cities 200, set-quote-price persiste 'quoted', admin/kpis 200).
- ⚠️ **PENDIENTE entrega real WhatsApp**: el sandbox Twilio dio "Failed to join" en el móvil admin → entrega NO confirmada (limitación sandbox: solo entrega a números con `join` activo). Código y backend OK. Solución definitiva: activar WhatsApp Sender aprobado (WhatsApp Business) en Twilio para entregar sin `join`.


## Ciclo Cotización→Venta de Logística (2026-06-22)
- **Flujo de estados**: pending_quote → (admin fija precio) → **quoted** (+email al cliente con tarifa y botón Confirmar) → (cliente confirma) → **pending** (entra a despacho + alerta Telegram).
- Backend: `PATCH /api/orders/{id}/set-quote-price` ahora pone status='quoted' y envía `email_service.send_logistics_quote_priced` (precio + enlace `${APP_BASE_URL}/confirmar-cotizacion/{id}`). Nuevo `POST /api/orders/{id}/confirm-quote` (cliente dueño, idempotente: 400 si ya no está 'quoted').
- Frontend: nueva página `QuoteConfirm.js` en ruta `/confirmar-cotizacion/:orderId` (muestra ruta + precio + botón Confirmar; si no hay sesión → login). Verificado E2E (curl + screenshot).
- NOTA: WhatsApp automático al cliente NO implementado (requiere integración WhatsApp Business API / Twilio, no configurada). Solo email automático por ahora.


## Email logística + UI admin cotizaciones + Desacople DB (2026-06-22)
- **Email automático** al crear cotización de Camión: `email_service.send_logistics_quote_received()` ("Hemos recibido tu solicitud..."), llamado best-effort en `create_logistics_quote`. Usa Resend si RESEND_API_KEY está, si no Gmail SMTP (configurado en preview). Para Resend en producción: añadir RESEND_API_KEY en Deploy Secrets.
- **UI admin** `LogisticsQuotesManager.jsx` (integrado en AdminDashboard, visible Fundador + Gestor): lista cotizaciones `pending_quote` con datos del cliente y permite fijar precio. Backend: `GET /api/admin/logistics-quotes` (scope regional) + `PATCH /api/orders/{id}/set-quote-price`. Verificado E2E (curl + screenshot).
- **Preview DESACOPLADO de producción**: removidos MONGO_URL_OVERRIDE/DB_NAME_OVERRIDE del .env de preview → usa Mongo local (glovo_algeciras). Producción intacta. Sembrado local: 16 ciudades + admin + qa_customer.


## Vehículos & Logística en Delivery (2026-06-22)
- **Flujo "Calcula tu envío" (`/presupuesto`, DeliveryQuote.js)**: opciones de vehículo ahora son **Moto / Coche / Camión** (eliminada "Bici"). Icono de Moto = imagen de motocicleta generada (URL en MOTO_ICON).
- **Camión / Logística Pesada**: NO calcula precio automático. Muestra mensaje "El precio final será determinado por la administración basado en el tipo de carga..." + badge, y botón **"Solicitar Cotización"** → `POST /api/orders/logistics-quote` (crea order order_type='logistics', status='pending_quote', total_amount=0, vehicle_type='truck' + alerta Telegram). Si no hay sesión → redirige a /auth.
- **Admin fija precio**: `PATCH /api/orders/{id}/set-quote-price` (admin/manager) → total_amount + status='pending'. Verificado por curl. PENDIENTE: UI admin para fijar el precio de cotizaciones de logística (actualmente solo vía API).
- Nubo Car (`/ride`) sigue SOLO pasajeros (economy/comfort/xl), sin camión.
- White screen Casablanca→Meknés: era caché de producción (código antiguo); no requirió cambios de código (preview calcula bien).


## Despliegue a PRODUCCIÓN — RESUELTO y EN VIVO (2026-06-22)
- 🟢 **https://noboexpress.com LIVE y certificado.** Frontend 200 + API 200.
- **Bloqueo resuelto**: el deploy fallaba siempre con `external MongoDB connection test failed: bad auth SCRAM-SHA-1`. Causa raíz: el panel de Secrets de Emergent doble-codificaba el `@` de la contraseña (`Ninite@2030` → `%40` → `%2540`) y además un campo Mongo URL bloqueado/cacheado en la pestaña Database. Soporte (support@emergent.sh) desbloqueó el campo cacheado.
- **Fix definitivo**: nuevo usuario Atlas `nubo_prod` con contraseña ALFANUMÉRICA pura (`yMiURAXoF1zOxb6c`) → sin caracteres que codificar. Verificado con PING OK desde preview antes de desplegar.
- **E2E de producción PASADO (curl en vivo)**: auth admin+cliente OK; Nubo Car ciclo completo (estimate→request 'buscando'→admin lo ve→cancelar) OK; AI Smart Search (LLM) OK; `/api/orders` 200; `/api/public/cities` 200. Frontend: landing con 4 tarjetas incl. **Nubo Car** (coche de lujo) + Maps renderizan.
- **Plan B DigitalOcean** (carpeta `/deploy` + `.github/workflows/deploy.yml`): blueprint completo commiteado a GitHub (Docker + Nginx + SSL Let's Encrypt + CI/CD + backup_mongo.sh). Listo como respaldo.
- NOTA tipos de vehículo Nubo Car: `economy`, `comfort`, `xl` (NO `car`).
- Quedó 1 ride de prueba CANCELADO en `nubo_produccion` (se elimina con cleanup_production.py cuando el usuario diga "limpia la base").


## Pendiente / Backlog
- DNS de subdominios (director./delegacion.) → usuario + Soporte Emergent.
- Producción: añadir secrets `MONGO_URL_OVERRIDE`, `DB_NAME_OVERRIDE`, `STRIPE_LIVE_KEY`, `RESEND_API_KEY`, `ADMIN_RESET_SECRET`, `REACT_APP_GOOGLE_MAPS_API_KEY` (vía Soporte si la UI los bloquea).
- (P2) Auto-despacho restringido a la región del pedido (riders de la misma delegación). (P2) Cron nocturno KPIs por email. (P3) Apps nativas store (React Native/Capacitor).


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

## Bloque D — Contabilidad y Finanzas + Auto-despacho + Ficha de activación (2026-06-18) ✅
- **Auto-despacho por proximidad**: al crear un pedido exprés (`POST /orders/express`) y al confirmarse el pago (Stripe status/webhook) se asigna automáticamente la Abeja más cercana (`auto_assign_order`), registrando `reason='auto_dispatch'` en el historial. Al entregar (`status='delivered'`) se libera la Abeja.
- **Contabilidad** (`accounting.py` + `routes/accounting.py`): libro de transacciones (`/accounting/transactions` CRUD + filtros + paginación), resumen por moneda (`/transactions/summary`), caja MAD/EUR (`/cash/balance`, `/cash/in`, `/cash/out` con validación de saldo), arqueo diario (`/cash/daily-closing`) con export CSV y **PDF** (fpdf2), export CSV de transacciones. Ingreso automático e idempotente al entregar un pedido (`record_order_income`). Auditoría ligera (`audit_logs`).
- **Finanzas/Nóminas** (`routes/finances.py`): comisión 10% por repartidor (`/admin/finances/summary`, `/report/{id}`, export CSV, mark-paid/mark-pending, payouts) y nóminas (`/accounting/payroll`, `/payroll/pay` que registra un `payout` en el libro). Pagar dos veces el mismo ciclo → 400.
- **Frontend**: `AccountingManager.jsx` en AdminDashboard (resumen ingresos/gastos/balance, control de caja con entrada/salida y arqueo CSV/PDF, tabla de nóminas con botón Pagar, libro de transacciones con export). `OperationsManager.jsx` (Bloque C).
- **Ficha de activación del rider** (`RiderManager.jsx`): `printQr` genera una **hoja imprimible profesional** con marca Nubo Express, nombre, ID único `NUBO-XXXX`, tipo de vehículo, datos (teléfono/DNI/matrícula), QR e instrucciones de activación. El diálogo muestra QR + código + badge de vehículo. El rider escanea el QR y la app se autoconfigura con nombre/perfil/vehículo.
- ✅ 82/82 pytest + frontend e2e 100% (iteration_8.json). Tests nuevos: `test_finances_accounting.py`, `test_auto_assign.py`, `test_login_lockout_security.py`.
- **Mejoras finales (2026-06-18)**: (a) **Doble QR** en la hoja de activación del rider — QR 1 descarga la app (PWA `/rider`) + QR 2 activación; onboarding en 2 escaneos. (b) **Selector de periodo** en `AccountingManager` (Desde/Hasta + presets Hoy/Semana/Mes/Todo) que filtra resumen, nóminas, libro y todos los exports (CSV/PDF). Filtrado por fecha verificado en backend.

## Comunicaciones: Email (Resend) + WhatsApp + Telegram (2026-06-18) ✅/⏳
- **Email transaccional (Resend)** ✅ construido: `email_service.py` (envío async-safe vía `asyncio.to_thread`, plantilla HTML, degradación elegante si falta `RESEND_API_KEY`). El email de **confirmación embebe un QR de seguimiento clicable** (adjunto inline CID → compatible con Gmail) que abre `APP_BASE_URL/track?order=...`. Endpoints Fundador: `GET /api/admin/email/status`, `POST /api/admin/email/test`. Notificaciones automáticas: confirmación al crear pedido exprés y aviso al entregar (best-effort, no bloqueante). Env: `RESEND_API_KEY` (pendiente clave real), `SENDER_EMAIL`, `SENDER_NAME`, `APP_BASE_URL`. Tests: `test_email_resend.py`. Helpers QR en core: `generate_qr_base64` (nuevo) + `generate_qr_data_url`.
- **WhatsApp** ✅ botón click-to-chat actualizado a `+34654232573` (configurable por `REACT_APP_WHATSAPP_NUMBER`).
- **Telegram** ⏳ código listo (bot HTTP API: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ADMIN_CHAT_ID`); el usuario aún no facilitó el token real de @BotFather (pegó texto de ejemplo). Nota: `api_id/api_hash` NO sirven para el bot actual.
- ✅ 103/103 pytest verdes.

## Segregación de roles / RBAC (2026-06-18) ✅
- 3 niveles: **Fundador** (`admin`) acceso total · **Gestor** (`manager`) solo Operaciones + tarifas · **Rider** (`driver`) app aislada.
- Backend: nueva dependencia `get_current_manager_or_admin` (core.py). Operaciones (ops/orders, assign-nearest, nearest, return-to-queue, assignment-history, stats, active-drivers) permiten admin+manager. Finanzas/KPIs/Contabilidad/alta-Riders quedan **solo Fundador** (`get_current_admin`).
- Endpoints Fundador para gestionar Gestores: `POST/GET /api/admin/managers`, `DELETE /api/admin/managers/{id}` (email+password bcrypt, sin sembrado por script).
- Frontend: `AdminDashboard` renderiza condicional por `isFounder`. Gestor ve "Panel de Gestión" (stats + flota + Operaciones); KPIs/Contabilidad/Ciudades/Riders/Telegram/Gestores ocultos. Nuevo `ManagerManager.jsx` (tarjeta del Fundador). App.js permite rol `manager` en `/admin` y `/dashboard`.
- ✅ 99/99 pytest (incl. `test_rbac_roles.py`, 15 casos) + verificación visual de ambas vistas (Fundador vs Gestor).

## Cuadro de mandos (KPIs) del Fundador (2026-06-18) ✅
- Backend `GET /api/admin/kpis` (admin): pedidos hoy, serie de pedidos/entregas por día (7d), ingresos del mes (EUR, convierte MAD), entregas totales, **tiempo medio de entrega** (creación→entrega) y **ranking de Abejas más activas (30d)** con entregas e ingresos generados.
- Frontend `KpiDashboard.jsx` en la portada del AdminDashboard: 4 tarjetas KPI, gráfico de barras de 7 días (entregados vs totales) y ranking con medallas. Auto-refresco cada 30s.
- ✅ 84/84 pytest (`test_kpis.py`) + smoke e2e OK. Cierra la fase de desarrollo interno (Bloques A–D + KPIs).

## Bloque C — Operaciones y Logística + QR seguimiento (2026-06-18) ✅
- **Asignación por proximidad** (`assignments.py` + `routes/assignments.py`): reclamo atómico del repartidor más cercano vía MongoDB `$geoNear` sobre índice **2dsphere** (`users.geo_location`, creado al arrancar), hasta 3 intentos anti condición de carrera, geofencing por ciudad (radio 10 km). `/rider/location` ahora guarda `geo_location` GeoJSON.
- **Endpoints**: `GET /api/drivers/nearest`, `POST /api/orders/{id}/assign-nearest` (admin/business; si no pasas lat/lng usa origen exprés o centro de ciudad), `POST /api/orders/{id}/return-to-queue`, `GET /api/admin/ops/orders` (cola pendientes + activos), `GET /api/admin/assignment-history` (filtros action/driver/fecha) y `/export` CSV. Control de acceso: cliente 403, pedido inexistente 404.
- **Historial de asignaciones** (`assignment_history`): trazabilidad total (assigned/returned/auto_returned, distancia km, actor).
- **Panel de Operaciones** (`OperationsManager.jsx` en AdminDashboard): cola de despacho con botón "Asignar cercana", pedidos en reparto con "Devolver", e historial con filtros + export CSV.
- **QR en seguimiento público** (`PublicTracking.js`): tarjeta con QR (`qrcode.react`) que codifica `…/track?order=<id>` para escanear/compartir desde el móvil.
- **Seguridad**: confirmado que el bloqueo anti-fuerza-bruta del login es efectivo a través del ingress de K8s (usa `X-Forwarded-For`); blindado con test `test_login_lockout_security.py`. ✅ 71/71 pytest + frontend e2e 100% (iteration_7.json).

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

## Nubo Ride — Transporte de pasajeros (Backend) (2026-06-20) ✅
- **Tarifas específicas de pasajeros** (`geo.py` → `RIDE_PRICING` + `calculate_ride_quote`): economy/comfort/xl con base + €/km + €/min + tarifa mínima, ETA con tráfico, EUR/MAD.
- **Modelos** (`models.py`): `Ride`, `RideRequest`, `RideEstimateRequest`, `RideAccept`, `RideCancel`, `GeoPoint`.
- **Endpoints** (`routes/rides.py`): `estimate`, `request`, `accept` (reclamo atómico + aislamiento regional), `active` (por rol), `start`, `complete`, `cancel`.
- **🚕 Telegram en `request`** (`telegram_alerts.py` → `notify_new_ride` + callbacks `rideview`/`rideassign`/`ridedrv`): el despacho recibe la solicitud y asigna conductor disponible de la región en 1 toque (reclamo atómico, no-op sin token).
- **FRONTEND (2026-06-20)**: Cliente `pages/NuboRide.js` (ruta `/ride`, solo customer): selección de ciudad origen/destino + GPS, `POST /rides/estimate` (3 tarjetas economy/comfort/xl), `POST /rides/request`, seguimiento en vivo (polling 5s) con barra de progreso (buscando→aceptado→en_curso→completado) y cancelar. Banner "Nubo Ride" en `CustomerDashboard` (`nubo-ride-btn`). Conductor en `rider/RiderApp.js`: sección "Nubo Ride · Viajes" con lista de viajes disponibles (Aceptar), viaje activo con Iniciar/Completar (polling 8s). Aviso de viaje interurbano si distancia > 80 km.
- ✅ **Verificado iter_12**: Backend 7/7 + Frontend e2e **16/16** (cliente pide → rider acepta/inicia/completa → cancelar → validación viaje único).
- ✅ **155/155 pytest** (148 previos + 7 en `test_nubo_ride.py`). Sin regresiones.
- ⏳ Pendiente: Frontend de Nubo Ride (UI cliente + app conductor).

## Producción / Deploy (2026-06-20)
- MongoDB Atlas validado: cadena `mongodb+srv://badarbox1756_db_user:***@cluster0.6isx6d9.mongodb.net/` autentica OK. **Datos (16 ciudades + Fundador) en DB `nubo_produccion`** → Secrets de prod requieren `MONGO_URL_OVERRIDE` + `DB_NAME_OVERRIDE=nubo_produccion`. El usuario pulsa Redeploy en la UI de Emergent (el agente no despliega).

## Separación total: Web pública vs Panel oculto (2026-06-19) ✅
- **Web pública** en `/` (`Landing.js`): SIEMPRE informativa, sin login (aunque haya sesión). Navbar con "Seguir pedido" (`/track`) y "Calcular precio" (`/presupuesto`); se quitó el botón de login/registro de clientes. CTAs del hero/footer → `/presupuesto` y `/track`.
- **Panel de administración oculto** en `/nubo-control` (no enlazado desde la web pública): login dedicado `AdminLogin.js` (marca "Nubo Control · Acceso restringido", tema oscuro glass). Valida rol admin/manager ANTES de iniciar sesión; cliente → "Acceso no autorizado". Tras login → `AdminDashboard`.
- `/admin` redirige a `/nubo-control`; `/dashboard` para admin/manager redirige a `/nubo-control`. `/auth` (login/registro de clientes) sigue existiendo pero NO enlazado en público.
- **Email del Fundador** cambiado a `badarbox1756@gmail.com` (en preview; en prod se provisiona vía endpoint de reseteo).
- **Normalización de email**: `register` y `login` ahora hacen `.strip().lower()` (coherente con el endpoint de reseteo) → evita fallos de login por mayúsculas.
- **Stripe**: badge 🟢 LIVE / 🟡 TEST + botón "Verificar estado" en el panel del Fundador (`GET /api/admin/payments/status`). En preview → TEST.
- **Reseteo de emergencia**: `POST /api/admin/reset-password` (guardado por `ADMIN_RESET_SECRET`, hmac.compare_digest, 404 si la env no existe). Crea la cuenta de admin si no existe (`created:true`) → permite provisionar el Fundador real en producción.
- ✅ 114/114 pytest + frontend e2e 18/18 (iteration_9.json).

## P2 — Módulo Reservas (BACKLOG, decidido 2026-06-22)
- **Decisión del usuario:** arrancar 100% por **FERRIES** como primer vertical (corredor España–Marruecos / Estrecho, base en Algeciras). Modelo inicial **AFILIACIÓN** (Fase 1: cero coste API, sin licencias) → transaccional según demanda (Fase 2).
- **Proveedor ferries recomendado:** **Direct Ferries Connect** (4.400+ rutas, 300+ operadoras, cubre Algeciras–Tánger / Tarifa–Tánger, REST/JSON, hasta 50% comisión CPS). Alternativa MVP rápido: **Ferryhopper** (widgets + API, sin coste setup, foco Mediterráneo).
- **Arquitectura:** módulo unificado `/api/bookings` con patrón **provider adapter** (`FerryAdapter`, luego `BookingAdapter` hoteles, `FlightAdapter` vuelos) → cambiar/añadir proveedores sin tocar la lógica. Reusar infra de afiliados existente (`AffiliateSettings` + `TravelBooking`).
- **Fases:** F1 Ferries afiliación (búsqueda + redirección con tracking comisión) → F2 Hoteles (Booking.com Affiliate vía Awin/CJ) + Vuelos (Travelpayouts/Skyscanner afiliación → Duffel/Kiwi transaccional) → F3 reservas in-app + pago Stripe + panel admin de reservas/comisiones.
- **Verticales 2026 (notas):** Hoteles → Booking.com **Affiliate** (Connectivity pausado). Vuelos → Amadeus Self-Service en cierre (ir a Enterprise) o Duffel/Kiwi transaccional. Ferries → Direct Ferries Connect / Ferryhopper.

## Pendiente operativo (producción)
- **Twilio WhatsApp entrega real:** sandbox dio "Failed to join" en móvil admin +34612284215. Acción: reenviar `join <palabra>` (o `leave` y luego `join`) desde el móvil, o activar **WhatsApp Sender aprobado** (WhatsApp Business) en Twilio para entrega sin restricción de sandbox. El código ya lee `TWILIO_WHATSAPP_FROM` y registra el estado en el historial de notificaciones.
