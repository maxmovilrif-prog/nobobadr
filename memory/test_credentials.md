# Test Credentials — Nubo

## QA accounts (created by agent, known passwords)
- Customer: `qa_customer@nubo.com` / `Test1234!`
- Admin (Fundador): `badarbox1756@gmail.com` / `Admin1234!`  (role: admin → acceso TOTAL: KPIs, Contabilidad, Operaciones, Riders, Gestores). Login SOLO por la ruta oculta `/nubo-control`.

## Roles / RBAC (segregación + multi-tenant regional)
- `admin` (Fundador / Director General): acceso TOTAL. Login por `/nubo-control` (oculto) o subdominio `director.noboexpress.com`.
- `manager` (Gestor Regional): vinculado a UNA Delegación (región). Solo ve pedidos/riders/operaciones de SU región. Bloqueado (403) en KPIs, Contabilidad. Login por `/nubo-control` o subdominio `delegacion.noboexpress.com`.
  - Los crea el Fundador desde "Equipo de Gestión" con email+password+delegación. Requiere `region_id`.
- `driver` (Rider): app aislada `/rider`, entra por código/QR (sin password). Vinculado a una región. El Fundador o su Gestor regional pueden ver/regenerar su código/QR desde el panel.

## Arquitectura regional (multi-tenant)
- Colección `regions`: {id, name, city_ids[]}. Una delegación agrupa varias ciudades.
- Endpoints: `POST/GET/PUT/DELETE /api/admin/regions` (Fundador), `GET /api/regions/mine` (Gestor).
- Aislamiento: helper `get_scope_city_ids` en core.py. Gestor scoped a su región en ops/orders, active-drivers, stats, riders.

## Recuperación de contraseña por email (Fundador + Gestores)
- `POST /api/auth/forgot-password` {email} → genera token (1h, TTL), envía email vía Resend. Anti-enumeración (respuesta genérica).
- `POST /api/auth/reset-password` {token, new_password} → token de un solo uso. UI: enlace en login admin + página `/nubo-control/recuperar?token=`.
- Riders NO usan email: su acceso se recupera regenerando el código/QR desde el panel (`POST /api/admin/riders/{id}/regenerate-code`).

## Enrutado por subdominio (1 despliegue)
- `director.noboexpress.com` → portal Fundador (solo role admin).
- `delegacion.noboexpress.com` → portal Gestores (solo role manager).
- `noboexpress.com` → app de clientes (Landing pública).
- Fallback rutas ocultas: `/nubo-control` (gestión), `/auth` (clientes). Detección en `frontend/src/lib/portal.js`.
- DNS de subdominios lo configura el usuario con Soporte (support@emergent.sh).

## Notes
- Other seeded accounts exist (cliente1@test.com, restaurante@test.com, repartidor@test.com, etc.) but their passwords are unknown.
- Register endpoint: POST /api/auth/register
- AI Smart Search endpoint: POST /api/search/smart  body: {"query": "tengo hambre"}

## Reseteo de emergencia (endpoint protegido)
- Endpoint: `POST /api/admin/reset-password`  body: `{"email","new_password","secret"}`
- Guardado por env `ADMIN_RESET_SECRET`. Si la env NO está definida → 404 (desactivado).
- PREVIEW secret: `nubo-preview-reset-7K9mQ2xP` (definido en backend/.env de preview).
- PRODUCCIÓN: el usuario debe definir su propio `ADMIN_RESET_SECRET` en los Secrets de producción y redeployar.
- Comparación de secreto en tiempo constante (hmac.compare_digest). Min 8 chars en nueva password.
