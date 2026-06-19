"""Servicio de email transaccional con Resend (Bloque de Comunicaciones).

Degradación elegante: si RESEND_API_KEY no está configurada, las funciones no
fallan; simplemente no envían y devuelven {'sent': False, 'reason': 'not_configured'}.
El SDK de Resend es síncrono → se ejecuta en hilo con asyncio.to_thread para no
bloquear el event loop de FastAPI.
"""
import os
import asyncio
import logging

import resend

logger = logging.getLogger("nubo.email")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
SENDER_NAME = os.environ.get("SENDER_NAME", "Nubo Express")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def is_configured() -> bool:
    return bool(RESEND_API_KEY)


def _from() -> str:
    return f"{SENDER_NAME} <{SENDER_EMAIL}>"


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


async def send_email(to: str, subject: str, html: str, wrap: bool = True) -> dict:
    """Envía un email transaccional. No lanza excepción: degrada con {'sent': False}."""
    if not is_configured():
        return {"sent": False, "reason": "not_configured"}
    params = {
        "from": _from(),
        "to": [to],
        "subject": subject,
        "html": _wrap(subject, html) if wrap else html,
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        return {"sent": True, "id": result.get("id") if isinstance(result, dict) else getattr(result, "id", None)}
    except Exception as e:
        logger.error(f"Resend send failed: {e}")
        return {"sent": False, "reason": str(e)}


def _money(amount, currency) -> str:
    if amount is None:
        return "—"
    return f"{amount:.2f} MAD" if currency == "MAD" else f"€{amount:.2f}"


async def send_order_confirmation(to: str, order: dict) -> dict:
    """Notificación automática: confirmación de pedido al cliente."""
    oid = str(order.get("id", ""))[:8]
    body = f"""
      <p>¡Hemos recibido tu pedido! 🎉</p>
      <table style="width:100%;border-collapse:collapse;margin-top:8px;">
        <tr><td style="padding:6px 0;color:#6b7280;">Pedido</td><td style="padding:6px 0;text-align:right;font-weight:bold;">#{oid}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Recogida</td><td style="padding:6px 0;text-align:right;">{order.get('origin_name') or '—'}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Entrega</td><td style="padding:6px 0;text-align:right;">{order.get('destination_name') or order.get('delivery_address') or '—'}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Importe</td><td style="padding:6px 0;text-align:right;font-weight:bold;color:#047857;">{_money(order.get('total_amount'), order.get('currency'))}</td></tr>
      </table>
      <p style="margin-top:16px;">Puedes seguir tu pedido en vivo desde tu enlace de seguimiento.</p>
    """
    return await send_email(to, f"Confirmación de pedido #{oid} · Nubo Express", body)


async def send_order_delivered(to: str, order: dict) -> dict:
    """Notificación automática: pedido entregado."""
    oid = str(order.get("id", ""))[:8]
    body = f"""
      <p>✅ Tu pedido <b>#{oid}</b> ha sido <b>entregado</b>.</p>
      <p>Importe: <b>{_money(order.get('total_amount'), order.get('currency'))}</b></p>
      <p style="margin-top:16px;">¡Gracias por confiar en Nubo Express! 🐝</p>
    """
    return await send_email(to, f"Pedido #{oid} entregado · Nubo Express", body)
