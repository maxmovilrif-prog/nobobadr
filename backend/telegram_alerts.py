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


async def send_telegram_message(text: str, chat_id=None) -> bool:
    """Envía un mensaje. Usa chat_id explícito o el del admin (.env). No-op si falta token/destino."""
    target = chat_id or core.TELEGRAM_ADMIN_CHAT_ID
    if not core.TELEGRAM_BOT_TOKEN or not target:
        logger.info("Telegram no configurado; se omite el envío de alerta.")
        return False
    url = f"https://api.telegram.org/bot{core.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": target,
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
    """Devuelve los chats que han escrito al bot (capturados por el listener de comandos)."""
    return list(_seen_chats.values())


_seen_chats: dict = {}


async def build_fleet_summary() -> str:
    """Construye un resumen de la flota para el comando /flota."""
    now = datetime.now(timezone.utc)
    in_transit = await core.db.orders.count_documents({'status': 'in_transit'})
    pending = await core.db.orders.count_documents({'status': 'pending'})
    available = await core.db.users.count_documents({'role': 'driver', 'is_available': True})
    live = len(core.manager.driver_locations)
    idle = 0
    for loc in core.manager.driver_locations.values():
        ts = loc.get("timestamp")
        if not ts:
            continue
        try:
            last_seen = datetime.fromisoformat(ts)
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            if int((now - last_seen).total_seconds()) > IDLE_THRESHOLD_SECONDS:
                idle += 1
        except (ValueError, TypeError):
            pass
    return (
        "🐝 <b>Estado de la flota Nubo</b>\n"
        f"📡 Abejas en vivo: {live}\n"
        f"⚠️ Abejas paradas: {idle}\n"
        f"✅ Conductores disponibles: {available}\n"
        f"🚚 Pedidos en reparto: {in_transit}\n"
        f"🕐 Pedidos pendientes: {pending}"
    )


_command_offset = 0


async def command_listener_loop() -> None:
    """Escucha comandos entrantes (/flota, /start, /help) vía long polling de getUpdates."""
    global _command_offset
    while True:
        try:
            if not core.TELEGRAM_BOT_TOKEN:
                await asyncio.sleep(5)
                continue
            url = f"https://api.telegram.org/bot{core.TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"timeout": 25, "offset": _command_offset}
            async with httpx.AsyncClient(timeout=35) as http:
                resp = await http.get(url, params=params)
                data = resp.json()
            if not data.get("ok"):
                await asyncio.sleep(5)
                continue
            for upd in data.get("result", []):
                _command_offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message") or {}
                text = (msg.get("text") or "").strip().lower()
                chat = msg.get("chat") or {}
                chat_id = chat.get("id")
                if not chat_id or not text:
                    continue
                _seen_chats[chat_id] = {
                    "chat_id": chat_id,
                    "name": chat.get("first_name") or chat.get("title") or "",
                    "username": chat.get("username", ""),
                }
                if text.startswith("/flota"):
                    await send_telegram_message(await build_fleet_summary(), chat_id=chat_id)
                elif text.startswith("/start") or text.startswith("/help"):
                    await send_telegram_message(
                        "👋 <b>Bot de alertas de Nubo</b>\n"
                        f"Tu chat_id es: <code>{chat_id}</code>\n\n"
                        "Comandos disponibles:\n"
                        "/flota — resumen de Abejas y pedidos\n"
                        "/help — esta ayuda\n\n"
                        "Recibirás avisos de pedidos nuevos y Abejas paradas.",
                        chat_id=chat_id,
                    )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"command_listener_loop error: {e}")
            await asyncio.sleep(5)
