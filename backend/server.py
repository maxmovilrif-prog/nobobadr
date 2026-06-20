"""Punto de entrada de la API de Nubo. Monta todos los routers y el WebSocket."""
import os
from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware

from core import client, manager, logger, db
import telegram_alerts
from routes import (
    auth, businesses, search, orders, drivers,
    messages, payments, dropshipping, affiliate, tracking, admin, cities, riders, assignments,
    finances, accounting, email, regions,
)

app = FastAPI(title="Nubo API")
api_router = APIRouter(prefix="/api")

# Montar todos los routers bajo /api
for module in (auth, businesses, search, orders, drivers, messages,
               payments, dropshipping, affiliate, tracking, admin, cities, riders, assignments,
               finances, accounting, email, regions):
    api_router.include_router(module.router)


# =========================
# WEBSOCKET REAL-TIME TRACKING
# =========================

@app.websocket("/ws/tracking/{order_id}")
async def websocket_tracking_endpoint(websocket: WebSocket, order_id: str):
    """
    WebSocket endpoint para tracking en tiempo real de pedidos.
    Los conductores envían su ubicación y los clientes la reciben en tiempo real.
    """
    await manager.connect(order_id, websocket)
    try:
        last_location = manager.get_driver_location(order_id)
        if last_location:
            await websocket.send_json(last_location)

        while True:
            data = await websocket.receive_json()
            await manager.broadcast_location(order_id, {
                "order_id": order_id,
                "lat": data.get("lat"),
                "lng": data.get("lng"),
                "driver_name": data.get("driver_name", "Conductor"),
                "status": data.get("status", "en_camino"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(order_id, websocket)
        logger.info(f"Client disconnected from order {order_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(order_id, websocket)


# =========================
# APP CONFIGURATION
# =========================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


import asyncio


@app.on_event("startup")
async def start_background_tasks():
    """Crea índices geoespaciales y arranca el monitor de Abejas + listener de Telegram."""
    # Índice 2dsphere para la asignación por proximidad ($geoNear)
    try:
        await db.users.create_index([("geo_location", "2dsphere")])
        logger.info("2dsphere index ensured on users.geo_location")
    except Exception as e:
        logger.error(f"Could not create 2dsphere index: {e}")
    # Índice TTL: los tokens de recuperación caducan automáticamente
    try:
        await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    except Exception as e:
        logger.error(f"Could not create TTL index on password_reset_tokens: {e}")
    app.state.idle_monitor_task = asyncio.create_task(telegram_alerts.idle_monitor_loop())
    app.state.telegram_listener_task = asyncio.create_task(telegram_alerts.command_listener_loop())
    logger.info("Background tasks started (idle monitor + telegram listener)")


@app.on_event("shutdown")
async def shutdown_db_client():
    for attr in ("idle_monitor_task", "telegram_listener_task"):
        task = getattr(app.state, attr, None)
        if task:
            task.cancel()
    client.close()
