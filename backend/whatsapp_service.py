"""Notificaciones WhatsApp vía Twilio (degradación elegante + plantillas de Meta).

Si TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_FROM no están
configurados, las funciones NO fallan: devuelven {'sent': False, 'reason': 'not_configured'}.
El SDK de Twilio es síncrono → se ejecuta con asyncio.to_thread para no bloquear el event loop.

PLANTILLAS (Content Template SID) — para el WhatsApp Business Sender aprobado por Meta:
    Los mensajes iniciados por el negocio requieren plantillas pre-aprobadas. Cuando Meta
    apruebe las plantillas de Nubo Express, basta con PEGAR el SID (HX...) en estos Secrets:
      - TWILIO_CONTENT_SID_QUOTE_PRICED  → plantilla enviada al CLIENTE con la tarifa.
      - TWILIO_CONTENT_SID_ADMIN_ALERT   → plantilla de alerta al ADMIN.
      - TWILIO_MESSAGING_SERVICE_SID     → (opcional) MG... si envías vía Messaging Service.
    Mientras NO haya SID configurado, se envía texto libre (`body=`), válido en el sandbox.
"""
import os
import json
import asyncio
import logging

logger = logging.getLogger("nubo.whatsapp")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
# Formato esperado: 'whatsapp:+14155238886' (sandbox) o número aprobado de WhatsApp Business
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
# Opcional: enviar a través de un Messaging Service (MG...) en lugar de from_
TWILIO_MESSAGING_SERVICE_SID = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")
# Content Template SIDs (HX...) — se rellenan cuando Meta apruebe las plantillas
TWILIO_CONTENT_SID_QUOTE_PRICED = os.environ.get("TWILIO_CONTENT_SID_QUOTE_PRICED")
TWILIO_CONTENT_SID_ADMIN_ALERT = os.environ.get("TWILIO_CONTENT_SID_ADMIN_ALERT")


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


def _send_sync(to: str, body: str | None = None, content_sid: str | None = None,
               content_variables: dict | None = None) -> dict:
    from twilio.rest import Client  # import perezoso para no romper si falta el paquete
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    kwargs = {"to": to}
    # Emisor: Messaging Service (MG...) tiene prioridad si está configurado; si no, el número.
    if TWILIO_MESSAGING_SERVICE_SID:
        kwargs["messaging_service_sid"] = TWILIO_MESSAGING_SERVICE_SID
    else:
        kwargs["from_"] = TWILIO_WHATSAPP_FROM
    if content_sid:
        kwargs["content_sid"] = content_sid
        if content_variables:
            kwargs["content_variables"] = json.dumps(content_variables, ensure_ascii=False)
    else:
        kwargs["body"] = body
    msg = client.messages.create(**kwargs)
    return {"sent": True, "sid": msg.sid, "channel": "template" if content_sid else "freeform"}


async def _dispatch(phone: str, body: str | None = None, content_sid: str | None = None,
                    content_variables: dict | None = None) -> dict:
    if not is_configured():
        return {"sent": False, "reason": "not_configured"}
    to = _normalize(phone)
    if not to:
        return {"sent": False, "reason": "no_phone"}
    try:
        return await asyncio.to_thread(_send_sync, to, body, content_sid, content_variables)
    except Exception as e:  # nunca debe tumbar el flujo principal
        logger.warning("Fallo enviando WhatsApp: %s", e)
        return {"sent": False, "reason": str(e)[:120]}


async def send_whatsapp(phone: str, body: str) -> dict:
    """Envío de texto libre (sandbox / conversaciones abiertas)."""
    return await _dispatch(phone, body=body)


async def send_whatsapp_template(phone: str, content_sid: str | None, content_variables: dict,
                                 fallback_body: str) -> dict:
    """Envía por plantilla (Content SID) si está configurada; si no, cae a texto libre.

    Así, cuando Meta apruebe la plantilla, solo hay que definir el Secret con el HX...
    sin reescribir la lógica de negocio.
    """
    if content_sid:
        return await _dispatch(phone, content_sid=content_sid, content_variables=content_variables)
    return await _dispatch(phone, body=fallback_body)


async def notify_logistics_quote_priced(phone: str, order: dict) -> dict:
    """WhatsApp con la tarifa final + enlace de confirmación del pedido de logística.

    Plantilla `TWILIO_CONTENT_SID_QUOTE_PRICED` — variables esperadas:
      {{1}} = nº de pedido corto · {{2}} = ruta origen→destino · {{3}} = precio+moneda · {{4}} = enlace de confirmación
    """
    base = os.environ.get("APP_BASE_URL", "https://noboexpress.com").rstrip("/")
    oid = str(order.get("id", ""))
    confirm_url = f"{base}/confirmar-cotizacion/{oid}"
    price = order.get("total_amount") or 0
    currency = order.get("currency") or "EUR"
    route = f"{order.get('origin_name') or '—'} → {order.get('destination_name') or '—'}"
    variables = {
        "1": oid[:8],
        "2": route,
        "3": f"{price} {currency}",
        "4": confirm_url,
    }
    fallback_body = (
        f"🚛 *Nubo Express* — Tu cotización #{oid[:8]} ya tiene precio.\n\n"
        f"📍 {route}\n"
        f"💶 Precio final: *{price} {currency}*\n\n"
        f"Confirma tu pedido aquí:\n{confirm_url}\n\n"
        f"Gracias por confiar en Nubo Express. 🐝"
    )
    return await send_whatsapp_template(phone, TWILIO_CONTENT_SID_QUOTE_PRICED, variables, fallback_body)


async def notify_admin_logistics_priced(admin_phone: str, order: dict, customer: dict | None = None) -> dict:
    """Alerta/copia al WhatsApp del admin cada vez que se fija una tarifa de logística.

    Plantilla `TWILIO_CONTENT_SID_ADMIN_ALERT` — variables esperadas:
      {{1}} = nº de pedido corto · {{2}} = cliente (nombre + teléfono) · {{3}} = ruta · {{4}} = precio+moneda
    """
    oid = str(order.get("id", ""))
    price = order.get("total_amount") or 0
    currency = order.get("currency") or "EUR"
    route = f"{order.get('origin_name') or '—'} → {order.get('destination_name') or '—'}"
    cust_txt = "—"
    cust_line = ""
    if customer:
        cname = customer.get("name") or "—"
        cphone = customer.get("phone") or "—"
        cust_txt = f"{cname} ({cphone})"
        cust_line = f"👤 Cliente: {cust_txt}\n"
    variables = {
        "1": oid[:8],
        "2": cust_txt,
        "3": route,
        "4": f"{price} {currency}",
    }
    fallback_body = (
        f"🔔 *Nubo Express · Alerta de gestión*\n"
        f"Tarifa logística fijada — pedido #{oid[:8]}\n\n"
        f"{cust_line}"
        f"📍 {route}\n"
        f"💶 Precio enviado: *{price} {currency}*\n\n"
        f"El cliente ya ha sido notificado. 🐝"
    )
    return await send_whatsapp_template(admin_phone, TWILIO_CONTENT_SID_ADMIN_ALERT, variables, fallback_body)
