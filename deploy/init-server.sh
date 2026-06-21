#!/usr/bin/env bash
# ============================================================
#  Nubo - Arranque inicial en DigitalOcean (obtiene SSL + levanta todo)
#  Ejecutar UNA sola vez la primera vez. Despues usa: docker compose up -d
# ============================================================
set -e

DOMAIN="noboexpress.com"
EMAIL="badarbox1756@gmail.com"   # <-- tu email para Let's Encrypt

echo "==> 1/5  Creando carpetas de certbot..."
mkdir -p certbot/www certbot/conf

echo "==> 2/5  Levantando SOLO el backend (no necesita SSL)..."
docker compose up -d backend

echo "==> 3/5  Levantando nginx temporal en HTTP para validar el dominio..."
# nginx servira /.well-known/acme-challenge en el puerto 80
docker compose up -d frontend

echo "==> 4/5  Solicitando certificado SSL a Let's Encrypt..."
docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
  --email $EMAIL --agree-tos --no-eff-email \
  -d $DOMAIN -d www.$DOMAIN" certbot

echo "==> 5/5  Reiniciando nginx para activar HTTPS..."
docker compose restart frontend

echo ""
echo "LISTO. Verifica:"
echo "  curl -I https://$DOMAIN/"
echo "  curl -I https://$DOMAIN/api/public/cities"
