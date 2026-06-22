"""Notificaciones WhatsApp vía Twilio (degradación elegante).

Si TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_FROM no están
configurados, las funciones NO fallan: devuelven {'sent': False, 'reason': 'not_configured'}.
El SDK de Twilio es síncrono → se ejecuta con asyncio.to_thread para no bloquear el event loop.
"""
import os
import asyncio
import logging

logger = logging.getLogger("nubo.whatsapp")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
# Formato esperado: 'whatsapp:+14155238886' (sandbox) o número aprobado de WhatsApp Business
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")


def is_configured() -> bool:
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM)


def _normalize(phone: str) -> str:
    """Devuelve el destino en formato 'whatsapp:+E164'."""
    p = (phone or "").strip().replace(" ", "")
    if not p:
        return ""
    if p.startswith("whatsapp:"):
        return p
    if not p.startswith("+"):
        p = "+" + p
    return f"whatsapp:{p}"


def _send_sync(to: str, body: str) -> dict:
    from twilio.rest import Client  # import perezoso para no romper si falta el paquete
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    msg = client.messages.create(from_=TWILIO_WHATSAPP_FROM, to=to, body=body)
    return {"sent": True, "sid": msg.sid}


async def send_whatsapp(phone: str, body: str) -> dict:
    if not is_configured():
        return {"sent": False, "reason": "not_configured"}
    to = _normalize(phone)
    if not to:
        return {"sent": False, "reason": "no_phone"}
    try:
        return await asyncio.to_thread(_send_sync, to, body)
    except Exception as e:  # nunca debe tumbar el flujo principal
        logger.warning("Fallo enviando WhatsApp: %s", e)
        return {"sent": False, "reason": str(e)[:120]}


async def notify_logistics_quote_priced(phone: str, order: dict) -> dict:
    """WhatsApp con la tarifa final + enlace de confirmación del pedido de logística."""
    base = os.environ.get("APP_BASE_URL", "https://noboexpress.com").rstrip("/")
    oid = str(order.get("id", ""))
    confirm_url = f"{base}/confirmar-cotizacion/{oid}"
    price = order.get("total_amount") or 0
    currency = order.get("currency") or "EUR"
    body = (
        f"🚛 *Nubo Express* — Tu cotización #{oid[:8]} ya tiene precio.\n\n"
        f"📍 {order.get('origin_name') or '—'} → {order.get('destination_name') or '—'}\n"
        f"💶 Precio final: *{price} {currency}*\n\n"
        f"Confirma tu pedido aquí:\n{confirm_url}\n\n"
        f"Gracias por confiar en Nubo Express. 🐝"
    )
    return await send_whatsapp(phone, body)
