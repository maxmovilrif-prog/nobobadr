# Test Credentials — Nubo

## QA accounts (created by agent, known passwords)
- Customer: `qa_customer@nubo.com` / `Test1234!`
- Admin (Fundador): `badarbox1756@gmail.com` / `Admin1234!`  (role: admin → acceso TOTAL: KPIs, Contabilidad, Operaciones, Riders, Gestores). Login SOLO por la ruta oculta `/nubo-control`.

## Roles / RBAC (segregación)
- `admin` (Fundador): acceso total al panel `/admin`.
- `manager` (Gestor): login normal en `/auth` → `/admin` muestra SOLO Operaciones + flota + tarifas. Bloqueado (403) en KPIs, Contabilidad, alta de Riders y gestión de Gestores.
  - Los Gestores los crea el Fundador desde el panel (tarjeta "Equipo de Gestión") con email+password. NO hay gestores sembrados por script (se limpian tras los tests).
  - Para tests de RBAC se crean gestores efímeros vía `POST /api/admin/managers` (ver `tests/test_rbac_roles.py`).
- `driver` (Rider): app aislada `/rider`, entra por código/QR (sin password).

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
