"""Real-time WebSocket manager + endpoint for live tracking and push events."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import List, Tuple, Optional

from auth import get_user_from_token


class ConnectionManager:
    def __init__(self):
        self.active: List[Tuple[WebSocket, dict]] = []

    async def connect(self, ws: WebSocket, user: dict):
        await ws.accept()
        self.active.append((ws, user))

    def disconnect(self, ws: WebSocket):
        self.active = [(w, u) for (w, u) in self.active if w is not ws]

    async def broadcast(self, message: dict):
        dead = []
        for (w, _u) in list(self.active):
            try:
                await w.send_json(message)
            except Exception:
                dead.append(w)
        for w in dead:
            self.disconnect(w)

    async def send_to_user(self, user_id: str, message: dict):
        for (w, u) in list(self.active):
            if u.get("id") == user_id:
                try:
                    await w.send_json(message)
                except Exception:
                    self.disconnect(w)

    def online_count(self) -> int:
        return len(self.active)


manager = ConnectionManager()

ws_router = APIRouter()


@ws_router.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket, token: Optional[str] = Query(default=None)):
    user = await get_user_from_token(token) if token else None
    if not user:
        await ws.close(code=4401)
        return
    await manager.connect(ws, user)
    try:
        await ws.send_json({"type": "connected", "user": {"id": user["id"], "role": user["role"]}})
        while True:
            data = await ws.receive_json()
            # Riders can stream their GPS location over the socket
            if data.get("type") == "location" and user.get("role") in ("rider", "admin", "dispatcher"):
                await manager.broadcast({
                    "type": "rider_location",
                    "rider_id": user["id"],
                    "name": user.get("name"),
                    "lat": data.get("lat"),
                    "lng": data.get("lng"),
                })
            elif data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
