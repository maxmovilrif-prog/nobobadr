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
- ✅ **Aviso en tiempo real a la Abeja (WebSocket + sonido + vibración):** canal `/ws/driver/{driver_id}` (`DriverNotifier`). Al asignar un pedido (manual o auto-despacho), `notify_driver_new_order` envía `{type:'new_order', business_name, delivery_address, city_name, total_amount, ...}`. El `DriverDashboard` mantiene una conexión persistente con keepalive + reconexión automática y, al recibir `new_order`, reproduce un doble "beep" (Web Audio API, sin archivos), vibra el móvil (`navigator.vibrate`), muestra un toast y refresca pedidos al instante (sin recargar). Entrega WS verificada e2e.
- ✅ **Despacho automático (auto-asignación al instante):** en cuanto un pedido pasa a `payment_status='paid'` (confirmación de pago `get_payment_status` y `stripe_webhook`), `auto_assign_order` asigna automáticamente la Abeja más cercana usando el centro de la ciudad del pedido como punto de recogida y respetando el radio de zona (`CITY_ZONE_RADIUS_KM=10`). Reutiliza el núcleo atómico `_atomic_claim_nearest` (mismo loop anti-carrera). Silencioso: sin ciudad o sin Abejas libres, el pedido queda en la cola. Verificado e2e (pedido Madrid → Abeja Madrid, status 'busy').
- ✅ **Asignación atómica del repartidor (anti-condición-de-carrera):** `POST /orders/{id}/assign-nearest` usa bucle de hasta 3 intentos (`ASSIGN_MAX_ATTEMPTS=3`), excluye Abejas ya descartadas y reclama al candidato con `find_one_and_update` atómico (`is_available True→False`, `status='busy'`); también reclama el pedido atómicamente (`driver_id None→driver`). Helper `release_driver` libera a la Abeja (`is_available=True`, `status='available'`) al entregar/cancelar (`update_order_status`) o devolver a la cola. Campo `status` en User (available|busy|offline). Verificado 19/19 (test_atomic_assignment.py + test_assign_nearest.py).
- ✅ **España + Marruecos:** 8 ciudades activas (🇲🇦 Tánger, Casablanca, Meknes, Nador · 🇪🇸 Algeciras, Madrid, Barcelona, Málaga) con seed idempotente. Textos de región actualizados a "España y Marruecos" en los 7 idiomas + Landing/TravelBooking; mapa admin re-centrado para ver ambos países.
- ✅ **Panel admin "Todos los pedidos":** `GET /api/admin/orders` (filtros por estado y ciudad) + tabla en el panel (id, negocio, ciudad, repartidor, estado, importe, fecha). Verificado (backend curl + selectores frontend).
- ✅ **Ciudades + Geofencing:** colección `cities` (Tánger, Casablanca, Meknes, Nador con coords). `GET /api/cities`. El cliente elige ciudad al pedir (`order.city_id`/`city_name`). El repartidor solo ve pedidos **de su ciudad**, detectada por GPS (≤10 km del centro); fuera de zona ve solo pedidos sin ciudad. Badge "Tu zona" en el panel del repartidor. Verificado 9/9.
- ✅ **Pagos por repartidor (comisiones):** panel admin con rango de fechas, % comisión configurable, tabla por Abeja (entregas/ingresos/comisión) + totales + CSV. Endpoints `/admin/finances/summary`, `/report/{driver_id}`, `/export`. `delivered_at` se registra al entregar. Verificado 13/13.
- ✅ **Fix seguridad:** `PATCH /orders/{id}/status` ahora solo admin / repartidor asignado / dueño del negocio (antes cualquiera podía marcar "delivered").
- ✅ **Historial: filtros + exportación CSV** (`GET /api/admin/assignment-history` con filtros action/driver/fechas + `/export` CSV). Card con selects de acción/repartidor, rango de fechas, Limpiar y "Exportar CSV". Verificado 14/14.
- ✅ **Stealth redirect:** un usuario no-admin que entre a `/admin-nubo` va a `/dashboard`; solo visitantes anónimos ven el login admin. El código secreto se valida 100% en servidor (nunca se expone al navegador).
- ✅ **Retorno automático a la cola** (Abeja "No disponible" → sus pedidos pre-entrega vuelven a pendientes) + devolución manual (`/orders/{id}/return-to-queue`).
- ✅ **Historial de asignaciones** (colección `assignment_history`): registra assigned/auto_returned/returned con quién, qué, cuándo, distancia y motivo.
- ✅ **Logística geoespacial 2dsphere:** `/drivers/nearest`, `/orders/{id}/assign-nearest`; botón "Asignar más cercano" con confirmación + el mapa vuela y resalta la Abeja elegida.
- ✅ **Inicialización de esquema MongoDB** (colecciones + índices) al arranque.
- ✅ **Portal Admin separado/oculto** (`/admin-nubo`): login oscuro email+contraseña+código secreto, bloqueo anti fuerza bruta, robots/noindex; `/auth` rechaza admin.
- ✅ Mensajes de error de Auth específicos · GPS automático del repartidor · Búsqueda IA · Admin Live Map (Leaflet).
- (Sesiones previas) Páginas legales, WebSockets tracking, 7 idiomas, viajes afiliados, NuboRide, dropshipping.

## Producción
- Dominio en vivo: https://noboexpress.com (los cambios requieren Redeploy).

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
