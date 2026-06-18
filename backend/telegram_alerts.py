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


async def _tg_api(method: str, payload: dict):
    """Llama a un método de la API de Telegram. No-op si no hay token."""
    if not core.TELEGRAM_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{core.TELEGRAM_BOT_TOKEN}/{method}"
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Telegram {method} error: {data}")
            return data
    except Exception as e:
        logger.error(f"Telegram {method} exception: {e}")
        return None


async def send_telegram_message(text: str, chat_id=None, reply_markup=None) -> bool:
    """Envía un mensaje. Usa chat_id explícito o el del admin (.env). No-op si falta token/destino."""
    target = chat_id or core.TELEGRAM_ADMIN_CHAT_ID
    if not core.TELEGRAM_BOT_TOKEN or not target:
        logger.info("Telegram no configurado; se omite el envío de alerta.")
        return False
    payload = {
        "chat_id": target,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    data = await _tg_api("sendMessage", payload)
    return bool(data and data.get("ok"))


async def _answer_callback(callback_id: str, text: str = "", show_alert: bool = False):
    await _tg_api("answerCallbackQuery", {"callback_query_id": callback_id, "text": text, "show_alert": show_alert})


async def _edit_message_text(chat_id, message_id, text: str, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    await _tg_api("editMessageText", payload)


async def notify_new_order(order: dict) -> None:
    """Notifica al admin cuando entra un pedido nuevo, con botones de acción inline."""
    try:
        full_id = str(order.get("id", ""))
        order_id = full_id[:8]
        total = order.get("total_amount", 0)
        address = order.get("delivery_address", "—")
        text = (
            "🛍️ <b>Nuevo pedido recibido</b>\n"
            f"📦 Pedido #{order_id}\n"
            f"💶 Total: €{total:.2f}\n"
            f"📍 Entrega: {address}"
        )
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ Asignar a Abeja", "callback_data": f"assign:{full_id}"},
                {"text": "👁 Ver pedido", "callback_data": f"view:{full_id}"},
            ]]
        }
        await send_telegram_message(text, reply_markup=reply_markup)
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
_pending_assign: dict = {}  # short_code -> {order_id, driver_id, driver_name}


async def _handle_callback(cq: dict) -> None:
    """Procesa los toques en los botones inline (ver/asignar/seleccionar Abeja)."""
    import uuid as _uuid
    cq_id = cq.get("id")
    data = cq.get("data") or ""
    message = cq.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")

    # Ver detalle del pedido
    if data.startswith("view:"):
        oid = data.split(":", 1)[1]
        order = await core.db.orders.find_one({"id": oid}, {"_id": 0})
        await _answer_callback(cq_id)
        if not order:
            await send_telegram_message("❌ Pedido no encontrado.", chat_id=chat_id)
            return
        items = "\n".join(f"• {i['quantity']}× {i['product_name']} (€{i['price']:.2f})" for i in order.get("items", []))
        driver = "Sin asignar"
        if order.get("driver_id"):
            d = await core.db.users.find_one({"id": order["driver_id"]}, {"_id": 0})
            driver = d.get("name", "Abeja") if d else "Abeja"
        await send_telegram_message(
            f"📦 <b>Pedido #{oid[:8]}</b>\n"
            f"Estado: {order.get('status')}\n"
            f"💶 Total: €{order.get('total_amount', 0):.2f}\n"
            f"📍 {order.get('delivery_address', '—')}\n"
            f"🐝 Abeja: {driver}\n\n<b>Artículos:</b>\n{items or '—'}",
            chat_id=chat_id,
        )
        return

    # Mostrar lista de Abejas disponibles para asignar
    if data.startswith("assign:"):
        oid = data.split(":", 1)[1]
        order = await core.db.orders.find_one({"id": oid}, {"_id": 0})
        if not order:
            await _answer_callback(cq_id, "Pedido no encontrado", show_alert=True)
            return
        if order.get("driver_id"):
            await _answer_callback(cq_id, "Este pedido ya está asignado", show_alert=True)
            return
        drivers = await core.db.users.find(
            {"role": "driver", "is_available": True}, {"_id": 0, "password_hash": 0}
        ).to_list(20)
        if not drivers:
            await _answer_callback(cq_id, "No hay Abejas disponibles ahora", show_alert=True)
            return
        await _answer_callback(cq_id)
        rows = []
        for d in drivers:
            code = _uuid.uuid4().hex[:8]
            _pending_assign[code] = {"order_id": oid, "driver_id": d["id"], "driver_name": d.get("name", "Abeja")}
            label = f"🐝 {d.get('name', 'Abeja')}"
            if d.get("vehicle_type"):
                label += f" ({d['vehicle_type']})"
            rows.append([{"text": label, "callback_data": f"drv:{code}"}])
        await _edit_message_text(
            chat_id, message_id,
            f"🐝 Elige la Abeja para el pedido #{oid[:8]}:",
            reply_markup={"inline_keyboard": rows},
        )
        return

    # Confirmar asignación a una Abeja concreta
    if data.startswith("drv:"):
        code = data.split(":", 1)[1]
        info = _pending_assign.get(code)
        if not info:
            await _answer_callback(cq_id, "Opción expirada, vuelve a intentarlo", show_alert=True)
            return
        order = await core.db.orders.find_one({"id": info["order_id"]}, {"_id": 0})
        if not order:
            await _answer_callback(cq_id, "Pedido no encontrado", show_alert=True)
            return
        if order.get("driver_id"):
            await _answer_callback(cq_id, "Ya estaba asignado", show_alert=True)
            await _edit_message_text(chat_id, message_id, f"⚠️ El pedido #{info['order_id'][:8]} ya estaba asignado.")
            return
        await core.db.orders.update_one(
            {"id": info["order_id"]},
            {"$set": {"driver_id": info["driver_id"], "status": "accepted",
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        await _answer_callback(cq_id, "✅ Asignado")
        await _edit_message_text(
            chat_id, message_id,
            f"✅ Pedido #{info['order_id'][:8]} asignado a 🐝 <b>{info['driver_name']}</b>.",
        )
        # Limpiar códigos de este pedido
        for k in [k for k, v in _pending_assign.items() if v["order_id"] == info["order_id"]]:
            _pending_assign.pop(k, None)
        return

    await _answer_callback(cq_id)


async def command_listener_loop() -> None:
    """Escucha comandos (/flota, /start, /help) y callbacks de botones vía long polling."""
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

                # Callbacks de botones inline
                if upd.get("callback_query"):
                    await _handle_callback(upd["callback_query"])
                    continue

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
                        "Recibirás avisos de pedidos nuevos (con botones para asignar) y de Abejas paradas.",
                        chat_id=chat_id,
                    )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"command_listener_loop error: {e}")
            await asyncio.sleep(5)
