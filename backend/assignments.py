"""Assignments router: assign orders to riders and track acceptance."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Literal

from database import db
from auth import get_current_user, require_roles
from realtime import manager

router = APIRouter(prefix="/api/assignments")


class AssignInput(BaseModel):
    order_id: str
    rider_id: str


class RespondInput(BaseModel):
    status: Literal["accepted", "rejected", "completed"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("")
async def assign_order(
    payload: AssignInput,
    user: dict = Depends(require_roles("admin", "dispatcher")),
):
    order = await db.orders.find_one({"id": payload.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    rider = await db.users.find_one({"id": payload.rider_id, "role": "rider"}, {"_id": 0})
    if not rider:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")

    assignment = {
        "id": str(uuid.uuid4()),
        "order_id": payload.order_id,
        "order_code": order.get("code"),
        "rider_id": payload.rider_id,
        "rider_name": rider.get("name"),
        "status": "assigned",
        "assigned_by": user["id"],
        "assigned_at": _now(),
        "responded_at": None,
    }
    await db.assignments.insert_one(assignment)
    await db.orders.update_one(
        {"id": payload.order_id},
        {"$set": {"assigned_rider_id": payload.rider_id, "status": "assigned",
                  "updated_at": _now()}},
    )
    assignment.pop("_id", None)
    # Push to the specific rider + dispatchers
    await manager.send_to_user(payload.rider_id, {"type": "assignment_new", "assignment": assignment})
    await manager.broadcast({"type": "order_assigned", "order_id": payload.order_id,
                             "rider_id": payload.rider_id})
    return assignment


@router.get("")
async def list_assignments(
    rider_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
):
    q = {}
    if user.get("role") == "rider":
        q["rider_id"] = user["id"]
    elif rider_id:
        q["rider_id"] = rider_id
    if status:
        q["status"] = status
    raw = await db.assignments.find(q, {"_id": 0}).sort("assigned_at", -1).to_list(500)
    return {"assignments": raw}


@router.patch("/{assignment_id}/respond")
async def respond_assignment(
    assignment_id: str,
    payload: RespondInput,
    user: dict = Depends(get_current_user),
):
    assignment = await db.assignments.find_one({"id": assignment_id}, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    if user.get("role") == "rider" and assignment["rider_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="No es tu asignación")

    await db.assignments.update_one(
        {"id": assignment_id},
        {"$set": {"status": payload.status, "responded_at": _now()}},
    )

    # Reflect on the order
    if payload.status == "rejected":
        await db.orders.update_one(
            {"id": assignment["order_id"]},
            {"$set": {"assigned_rider_id": None, "status": "pending", "updated_at": _now()}},
        )
    elif payload.status == "accepted":
        await db.orders.update_one(
            {"id": assignment["order_id"]},
            {"$set": {"status": "picked_up", "updated_at": _now()}},
        )

    updated = await db.assignments.find_one({"id": assignment_id}, {"_id": 0})
    await manager.broadcast({"type": "assignment_update", "assignment": updated})
    return updated
