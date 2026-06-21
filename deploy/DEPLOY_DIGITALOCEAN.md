# 🚀 Nubo — Despliegue en DigitalOcean (Plan B / Control Total)

Blueprint completo con **Docker Compose + Nginx + SSL (Let's Encrypt)** para desplegar Nubo
(FastAPI + React + MongoDB Atlas) en un VPS propio. **MongoDB sigue en Atlas** (no se instala en el VPS).

> Úsalo solo si el soporte de Emergent no desbloquea el contenedor a tiempo. El código del preview NO cambia.

---

## 0. Lo que vas a necesitar
- Una cuenta en **DigitalOcean**.
- Tu dominio **noboexpress.com** (acceso al panel DNS donde lo gestionas).
- Las **mismas claves** que ya usas (MongoDB Atlas, Stripe, Resend, Google Maps, etc.).

---

## 1. Crear el Droplet (VPS)
1. DigitalOcean → **Create → Droplets**.
2. Imagen: **Ubuntu 24.04 LTS**.
3. Plan: **Basic → Regular → 2 GB RAM / 1 vCPU** (mínimo recomendado; 2 vCPU si esperas tráfico).
4. Región: **Frankfurt o London** (cercana a Algeciras).
5. Autenticación: **SSH Key** (recomendado) o password.
6. Hostname: `nubo-prod`. → **Create Droplet**. Anota la **IP pública**.

---

## 2. Apuntar el dominio al Droplet (DNS)
En el panel DNS de tu dominio crea dos registros **A**:

| Tipo | Nombre | Valor (apunta a)      |
|------|--------|-----------------------|
| A    | `@`    | IP_DE_TU_DROPLET      |
| A    | `www`  | IP_DE_TU_DROPLET      |

> ⚠️ Si el dominio está detrás de **Cloudflare**, pon la nube **GRIS (DNS only)** mientras emites el SSL,
> para que Let's Encrypt valide directo contra tu VPS. Luego puedes reactivar el proxy naranja.

Espera a que propague (`ping noboexpress.com` debe devolver tu IP).

---

## 3. Preparar el servidor
Conéctate por SSH: `ssh root@IP_DE_TU_DROPLET`

```bash
# Actualizar e instalar Docker + Compose plugin
apt-get update && apt-get upgrade -y
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin git ufw

# Firewall
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable
```

---

## 4. Subir el código al servidor
Opción A (recomendada) — usa el botón **"Save to GitHub"** del chat de Emergent y luego:
```bash
cd /opt
git clone https://github.com/TU_USUARIO/TU_REPO.git nubo
cd nubo
```
Opción B — sube por `scp` la carpeta del proyecto a `/opt/nubo`.

> Todo el blueprint de despliegue vive en la carpeta **`/deploy`** del repo.

---

## 5. Configurar las variables de entorno (secrets)
```bash
cd /opt/nubo

# Backend
cp deploy/backend.env.example deploy/backend.env
nano deploy/backend.env      # rellena MONGO_URL, JWT_SECRET, STRIPE, RESEND, etc.

# Frontend (clave de Google Maps para el build)
cp deploy/.env.example deploy/.env
nano deploy/.env             # pon tu REACT_APP_GOOGLE_MAPS_API_KEY
```
> Recuerda: la contraseña de Mongo va con `@` codificada como `%40` →
> `...:Ninite%402030@cluster0...`

---

## 6. Arrancar (build + SSL automático)
```bash
cd /opt/nubo
chmod +x deploy/init-server.sh

# docker compose lee deploy/.env automáticamente si lo invocas con --env-file
docker compose --env-file deploy/.env -f deploy/docker-compose.yml build
bash deploy/init-server.sh
```
El script:
1. Levanta el backend.
2. Levanta nginx (HTTP) para la validación ACME.
3. Pide el certificado SSL a Let's Encrypt para `noboexpress.com` + `www`.
4. Reinicia nginx con HTTPS activo.

---

## 7. Verificar
```bash
curl -I https://noboexpress.com/                       # 200 (React)
curl -s https://noboexpress.com/api/public/cities       # JSON de ciudades
docker compose -f deploy/docker-compose.yml ps          # estado de contenedores
docker compose -f deploy/docker-compose.yml logs -f backend   # LOGS del backend en vivo
```
✅ Si `/api/public/cities` devuelve JSON → **producción operativa en tu VPS**.

---

## 8. Operación diaria
```bash
cd /opt/nubo

# Ver logs del backend (aquí SÍ verás el traceback exacto, a diferencia del panel de Emergent)
docker compose -f deploy/docker-compose.yml logs --tail=200 backend

# Reiniciar un servicio
docker compose -f deploy/docker-compose.yml restart backend

# Desplegar cambios nuevos (tras git pull)
git pull
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build

# Parar todo
docker compose -f deploy/docker-compose.yml down
```
El SSL se **renueva solo** (contenedor `certbot` cada 12h).

---

## 9. Diagnóstico clave (el 520 que tienes ahora)
En el VPS **sí ves los logs reales**. Con `docker compose logs backend` sabrás al instante si es:
- `pymongo ... auth failed` → credenciales/usuario de Atlas.
- `ServerSelectionTimeoutError` → Network Access de Atlas no permite la IP del VPS (añade `0.0.0.0/0`).
- `ModuleNotFoundError` → falta una dependencia en `requirements.txt`.

> Esto es exactamente lo que el panel de Emergent no te deja ver y por lo que migrar te da control total.

---

## 10. Archivos de este blueprint (carpeta `/deploy`)
| Archivo | Para qué sirve |
|---|---|
| `backend.Dockerfile` | Imagen del API FastAPI (uvicorn:8001, 2 workers) |
| `frontend.Dockerfile` | Build de React (craco) + Nginx que sirve el SPA |
| `nginx/default.conf` | Reverse proxy: `/api`→backend, `/ws`→WebSocket, `/`→SPA, SSL |
| `docker-compose.yml` | Orquesta backend + frontend(nginx) + certbot |
| `backend.env.example` | Plantilla de secrets del backend → copia a `backend.env` |
| `.env.example` | Plantilla de la clave de Maps → copia a `.env` |
| `init-server.sh` | Arranque inicial + emisión de SSL |

---

### ¿Y MongoDB?
Se queda en **Atlas** tal cual. Solo asegúrate de que en **Atlas → Network Access** esté permitida
la IP del Droplet (o `0.0.0.0/0`). No se instala Mongo en el VPS.
