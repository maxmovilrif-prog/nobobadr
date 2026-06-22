"""Servicio de email transaccional con Resend (Bloque de Comunicaciones).

Degradación elegante: si RESEND_API_KEY no está configurada, las funciones no
fallan; simplemente no envían y devuelven {'sent': False, 'reason': 'not_configured'}.
El SDK de Resend es síncrono → se ejecuta en hilo con asyncio.to_thread para no
bloquear el event loop de FastAPI.
"""
import os
import asyncio
import logging
import smtplib
from email.message import EmailMessage

import resend

logger = logging.getLogger("nubo.email")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
SENDER_NAME = os.environ.get("SENDER_NAME", "Nubo Express")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://noboexpress.com").rstrip("/")

# Gmail SMTP (alternativa a Resend): requiere App Password de Gmail
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = (os.environ.get("MAIL_PASSWORD") or "").replace(" ", "")
MAIL_FROM = os.environ.get("MAIL_FROM", MAIL_USERNAME or SENDER_EMAIL)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def _gmail_configured() -> bool:
    return bool(MAIL_USERNAME and MAIL_PASSWORD)


def is_configured() -> bool:
    return _gmail_configured() or bool(RESEND_API_KEY)


def _from() -> str:
    return f"{SENDER_NAME} <{SENDER_EMAIL}>"


def _send_gmail_sync(to: str, subject: str, html_full: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{SENDER_NAME} <{MAIL_FROM}>"
    msg["To"] = to
    msg.set_content("Tu cliente de correo no soporta HTML. Abre este mensaje en un cliente compatible.")
    msg.add_alternative(html_full, subtype="html")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(msg)


def _wrap(title: str, body_html: str) -> str:
    """Plantilla HTML con CSS inline (compatible con clientes de correo)."""
    return f"""
    <div style="background:#f3f4f6;padding:24px;font-family:Arial,Helvetica,sans-serif;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;">
        <tr><td style="background:#047857;padding:20px 28px;color:#ffffff;">
          <span style="font-size:22px;font-weight:bold;">🐝 Nubo Express</span>
        </td></tr>
        <tr><td style="padding:28px;color:#111827;">
          <h2 style="margin:0 0 12px;font-size:18px;color:#047857;">{title}</h2>
          <div style="font-size:14px;line-height:1.7;color:#374151;">{body_html}</div>
        </td></tr>
        <tr><td style="padding:16px 28px;background:#f9fafb;color:#9ca3af;font-size:11px;text-align:center;">
          Este es un mensaje automático de Nubo Express · noboexpress.com
        </td></tr>
      </table>
    </div>
    """


async def send_email(to: str, subject: str, html: str, wrap: bool = True, attachments: list = None) -> dict:
    """Envía un email transaccional. No lanza excepción: degrada con {'sent': False}.
    `attachments`: lista opcional de adjuntos Resend (soporta inline vía content_id)."""
    if not is_configured():
        return {"sent": False, "reason": "not_configured"}
    html_full = _wrap(subject, html) if wrap else html
    # Preferir Gmail SMTP si está configurado (atachments inline no soportados por esta vía)
    if _gmail_configured():
        try:
            await asyncio.to_thread(_send_gmail_sync, to, subject, html_full)
            return {"sent": True, "via": "gmail"}
        except Exception as e:
            logger.error(f"Gmail SMTP send failed: {e}")
            if not RESEND_API_KEY:
                return {"sent": False, "reason": str(e)}
            # si hay Resend, continúa como fallback
    params = {
        "from": _from(),
        "to": [to],
        "subject": subject,
        "html": html_full,
    }
    if attachments:
        params["attachments"] = attachments
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        return {"sent": True, "via": "resend", "id": result.get("id") if isinstance(result, dict) else getattr(result, "id", None)}
    except Exception as e:
        logger.error(f"Resend send failed: {e}")
        return {"sent": False, "reason": str(e)}


def _money(amount, currency) -> str:
    if amount is None:
        return "—"
    return f"{amount:.2f} MAD" if currency == "MAD" else f"€{amount:.2f}"


async def send_order_confirmation(to: str, order: dict) -> dict:
    """Notificación automática: confirmación de pedido al cliente, con QR de seguimiento embebido."""
    from core import generate_qr_base64
    order_id = str(order.get("id", ""))
    oid = order_id[:8]
    tracking_url = f"{APP_BASE_URL}/track?order={order_id}"

    qr_b64 = generate_qr_base64(tracking_url)
    attachments = [{
        "filename": "seguimiento-nubo.png",
        "content": qr_b64,
        "content_type": "image/png",
        "content_id": "trackingqr",
    }]

    body = f"""
      <p>¡Hemos recibido tu pedido! 🎉</p>
      <table style="width:100%;border-collapse:collapse;margin-top:8px;">
        <tr><td style="padding:6px 0;color:#6b7280;">Pedido</td><td style="padding:6px 0;text-align:right;font-weight:bold;">#{oid}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Recogida</td><td style="padding:6px 0;text-align:right;">{order.get('origin_name') or '—'}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Entrega</td><td style="padding:6px 0;text-align:right;">{order.get('destination_name') or order.get('delivery_address') or '—'}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Importe</td><td style="padding:6px 0;text-align:right;font-weight:bold;color:#047857;">{_money(order.get('total_amount'), order.get('currency'))}</td></tr>
      </table>
      <div style="margin-top:24px;text-align:center;background:#f9fafb;border-radius:12px;padding:20px;">
        <p style="margin:0 0 12px;font-weight:bold;color:#047857;">Sigue tu pedido en vivo 📍</p>
        <a href="{tracking_url}" style="text-decoration:none;">
          <img src="cid:trackingqr" alt="QR de seguimiento" width="180" height="180" style="border:8px solid #ecfdf5;border-radius:12px;display:block;margin:0 auto;" />
        </a>
        <p style="margin:12px 0 0;font-size:12px;color:#6b7280;">Escanea el código o pulsa el botón</p>
        <a href="{tracking_url}" style="display:inline-block;margin-top:12px;background:#047857;color:#ffffff;text-decoration:none;padding:10px 22px;border-radius:999px;font-weight:bold;font-size:14px;">Ver seguimiento en vivo</a>
      </div>
    """
    return await send_email(
        to, f"Confirmación de pedido #{oid} · Nubo Express", body, attachments=attachments
    )


async def send_order_delivered(to: str, order: dict) -> dict:
    """Notificación automática: pedido entregado."""
    oid = str(order.get("id", ""))[:8]
    body = f"""
      <p>✅ Tu pedido <b>#{oid}</b> ha sido <b>entregado</b>.</p>
      <p>Importe: <b>{_money(order.get('total_amount'), order.get('currency'))}</b></p>
      <p style="margin-top:16px;">¡Gracias por confiar en Nubo Express! 🐝</p>
    """
    return await send_email(to, f"Pedido #{oid} entregado · Nubo Express", body)


async def send_logistics_quote_priced(to: str, order: dict) -> dict:
    """Notificación con la tarifa final + botón para confirmar el pedido de logística."""
    oid = str(order.get("id", ""))
    short = oid[:8]
    confirm_url = f"{APP_BASE_URL}/confirmar-cotizacion/{oid}"
    currency = order.get("currency") or "EUR"
    price = order.get("total_amount") or 0
    body = f"""
      <p>¡Buenas noticias! Tu cotización de Camión / Logística Pesada ya tiene precio. 🚛</p>
      <table style="width:100%;border-collapse:collapse;margin-top:8px;">
        <tr><td style="padding:6px 0;color:#6b7280;">Referencia</td><td style="padding:6px 0;text-align:right;font-weight:bold;">#{short}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Recogida</td><td style="padding:6px 0;text-align:right;">{order.get('origin_name') or '—'}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Entrega</td><td style="padding:6px 0;text-align:right;">{order.get('destination_name') or '—'}</td></tr>
      </table>
      <div style="margin:18px 0;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:12px;padding:18px;text-align:center;">
        <p style="margin:0;color:#6b7280;font-size:13px;">Precio final</p>
        <p style="margin:4px 0 0;font-size:28px;font-weight:800;color:#059669;">{price} {currency}</p>
      </div>
      <div style="text-align:center;margin-top:22px;">
        <a href="{confirm_url}" style="display:inline-block;background:#059669;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:9999px;font-weight:700;">Confirmar Pedido</a>
      </div>
      <p style="margin-top:18px;font-size:12px;color:#9ca3af;text-align:center;">O copia este enlace: {confirm_url}</p>
      <p style="margin-top:16px;">Gracias por confiar en Nubo Express. 🐝</p>
    """
    return await send_email(to, f"Tu cotización #{short} ya tiene precio · Nubo Express", body)


async def send_logistics_quote_received(to: str, order: dict) -> dict:
    """Notificación automática: solicitud de cotización de Camión/Logística recibida."""
    oid = str(order.get("id", ""))[:8]
    body = f"""
      <p>¡Hemos recibido tu solicitud de cotización! 🚛</p>
      <p>Nuestro equipo de logística está revisando los detalles de tu carga y te enviaremos el <b>precio personalizado</b> en breve.</p>
      <table style="width:100%;border-collapse:collapse;margin-top:8px;">
        <tr><td style="padding:6px 0;color:#6b7280;">Referencia</td><td style="padding:6px 0;text-align:right;font-weight:bold;">#{oid}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Recogida</td><td style="padding:6px 0;text-align:right;">{order.get('origin_name') or '—'}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Entrega</td><td style="padding:6px 0;text-align:right;">{order.get('destination_name') or '—'}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Servicio</td><td style="padding:6px 0;text-align:right;">Camión / Logística Pesada</td></tr>
      </table>
      <div style="margin-top:20px;background:#f9fafb;border-radius:12px;padding:16px;">
        <p style="margin:0;font-size:13px;color:#374151;">El precio final dependerá del tipo de carga (carga completa o paquetes pequeños por kilo) y la ubicación logística. Te contactaremos con la tarifa cuanto antes.</p>
      </div>
      <p style="margin-top:18px;">Gracias por confiar en Nubo Express para tu logística pesada. 🐝</p>
    """
    return await send_email(to, f"Solicitud de cotización recibida #{oid} · Nubo Express", body)


async def send_password_reset_email(to: str, reset_link: str, name: str = "") -> dict:
    """Recuperación de contraseña: enlace seguro de un solo uso (válido 1 hora)."""
    saludo = f"Hola {name}," if name else "Hola,"
    body = f"""
      <p>{saludo}</p>
      <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta de gestión en Nubo Express.</p>
      <div style="margin:24px 0;text-align:center;">
        <a href="{reset_link}" style="display:inline-block;background:#047857;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:999px;font-weight:bold;font-size:15px;">Restablecer contraseña</a>
      </div>
      <p style="font-size:13px;color:#6b7280;">Este enlace caduca en <b>1 hora</b> y solo puede usarse una vez. Si no solicitaste este cambio, ignora este correo; tu contraseña seguirá siendo la misma.</p>
      <p style="font-size:12px;color:#9ca3af;margin-top:18px;word-break:break-all;">Si el botón no funciona, copia este enlace:<br>{reset_link}</p>
    """
    return await send_email(to, "Recuperación de contraseña · Nubo Express", body)

