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
