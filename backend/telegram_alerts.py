"""Servicio de alertas por Telegram para el administrador.

Envía mensajes salientes mediante la API HTTP de Telegram (sin webhooks).
Incluye un monitor en segundo plano que detecta 'Abejas' (conductores) paradas
para que las alertas lleguen al móvil aunque el panel de admin esté cerrado.
"""
import asyncio
from datetime import datetime, timezone

import httpx

import core
from core import logger

IDLE_THRESHOLD_SECONDS = 90
IDLE_MONITOR_INTERVAL = 30  # cada cuánto revisa la flota
_idle_alerted: set = set()  # claves de Abejas ya avisadas como paradas


def is_configured() -> bool:
    return bool(core.TELEGRAM_BOT_TOKEN and core.TELEGRAM_ADMIN_CHAT_ID)


async def send_telegram_message(text: str) -> bool:
    """Envía un mensaje al chat del administrador. No-op si no está configurado."""
    if not is_configured():
        logger.info("Telegram no configurado; se omite el envío de alerta.")
        return False
    url = f"https://api.telegram.org/bot{core.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": core.TELEGRAM_ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"Telegram sendMessage error {resp.status_code}: {resp.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False


async def notify_new_order(order: dict) -> None:
    """Notifica al admin cuando entra un pedido nuevo."""
    try:
        order_id = str(order.get("id", ""))[:8]
        total = order.get("total_amount", 0)
        address = order.get("delivery_address", "—")
        text = (
            "🛍️ <b>Nuevo pedido recibido</b>\n"
            f"📦 Pedido #{order_id}\n"
            f"💶 Total: €{total:.2f}\n"
            f"📍 Entrega: {address}"
        )
        await send_telegram_message(text)
    except Exception as e:
        logger.error(f"notify_new_order error: {e}")


async def notify_idle_driver(driver_name: str, idle_seconds: int) -> None:
    """Notifica al admin cuando una Abeja lleva demasiado tiempo parada."""
    minutes = max(1, idle_seconds // 60)
    text = (
        "⚠️ <b>Abeja parada</b>\n"
        f"🐝 {driver_name} lleva ~{minutes} min sin moverse.\n"
        "Revisa el panel de flota."
    )
    await send_telegram_message(text)


async def idle_monitor_loop() -> None:
    """Bucle en segundo plano que detecta Abejas paradas y avisa por Telegram una sola vez."""
    while True:
        try:
            await asyncio.sleep(IDLE_MONITOR_INTERVAL)
            if not is_configured():
                continue
            now = datetime.now(timezone.utc)
            current_idle = set()
            for order_id, loc in list(core.manager.driver_locations.items()):
                ts = loc.get("timestamp")
                if not ts:
                    continue
                try:
                    last_seen = datetime.fromisoformat(ts)
                    if last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue
                idle_seconds = int((now - last_seen).total_seconds())
                if idle_seconds > IDLE_THRESHOLD_SECONDS:
                    current_idle.add(order_id)
                    if order_id not in _idle_alerted:
                        _idle_alerted.add(order_id)
                        await notify_idle_driver(loc.get("driver_name", "Abeja"), idle_seconds)
            # Limpiar avisos de Abejas que volvieron a moverse o terminaron
            _idle_alerted.intersection_update(current_idle)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"idle_monitor_loop error: {e}")


async def get_recent_chats() -> list:
    """Lee getUpdates para ayudar al admin a encontrar su chat_id tras escribir al bot."""
    if not core.TELEGRAM_BOT_TOKEN:
        return []
    url = f"https://api.telegram.org/bot{core.TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(url)
            data = resp.json()
            chats = {}
            for upd in data.get("result", []):
                msg = upd.get("message") or upd.get("edited_message") or {}
                chat = msg.get("chat")
                if chat:
                    chats[chat["id"]] = {
                        "chat_id": chat["id"],
                        "name": chat.get("first_name") or chat.get("title") or "",
                        "username": chat.get("username", ""),
                    }
            return list(chats.values())
    except Exception as e:
        logger.error(f"get_recent_chats error: {e}")
        return []
